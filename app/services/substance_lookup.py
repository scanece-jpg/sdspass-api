"""
Substance Lookup Service — Per-Dosya Mimarisi
=============================================
"Sıfır Render Kilidi" — Hiçbir zaman büyük JSON yüklenmez.
Her CAS lookup → tek küçük dosya açılır (~1-2 KB).

Arama Hiyerarşisi:
  Sıra 1 — data/cl/{xx}/{cas}.json        SEA Ek-6  (Türk kanunu, mutlak)
  Sıra 2 — data/annex6/{xx}/{cas}.json    CLP Annex VI (AB uyumlaştırılmış)
  Sıra 3 — substances_custom.json         Tedarikçi/kullanıcı girişi

Eski büyük JSON dosyaları (substances_sea_ek6.json, substances_annex_vi.json)
artık lookup'ta kullanılmıyor; yalnızca generate_cl_files.py tarafından
kaynak olarak tüketildi.
"""
import json, os, threading, re
from typing import Optional, Dict

_BASE        = os.path.join(os.path.dirname(__file__), '..', '..', 'data')
_CL_DIR      = os.path.join(_BASE, 'cl')       # SEA Ek-6 per-dosya
_ANNEX6_DIR  = os.path.join(_BASE, 'annex6')   # CLP Annex VI per-dosya
_CUSTOM_PATH = os.path.join(_BASE, 'substances_custom.json')
_OEL_PATH    = os.path.join(_BASE, 'tr_oel_limits.json')

_CUSTOM_DB: Optional[Dict] = None
_OEL_DB:    Optional[Dict] = None
_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Per-dosya okuyucu
# ---------------------------------------------------------------------------

def _read_cl_file(directory: str, cas: str) -> Optional[Dict]:
    """data/cl/{xx}/{cas}.json veya data/annex6/{xx}/{cas}.json oku."""
    path = os.path.join(directory, cas[:2], f'{cas}.json')
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except Exception:
        return None


def _cl_to_legacy(entry: dict, priority: int, source_label: str) -> dict:
    """
    Per-dosya formatını (classification/labelling) eski API formatına çevir.
    main.py endpoint'i 'hazards', 'signal', 'pictograms' bekliyor.
    """
    cl = entry.get('classification', {})
    lb = entry.get('labelling', {})

    # classification.hazards → [{h_class, h_code}] formatına çevir
    hazards = [
        {'h_class': h.get('class', ''), 'h_code': h.get('h_code', '')}
        for h in cl.get('hazards', [])
    ]

    return {
        'cas'            : entry.get('cas', ''),
        'name'           : entry.get('name', ''),
        'name_tr'        : entry.get('name_tr', ''),
        'ec_no'          : entry.get('ec_no', ''),
        'index_no'       : entry.get('index_no', ''),
        'atp'            : entry.get('atp', ''),
        'notes'          : entry.get('notes', []),
        'signal'         : lb.get('signal', ''),
        'pictograms'     : lb.get('pictograms', []),
        'hazards'        : hazards,
        'suppl_hazards'  : lb.get('suppl_h', []),
        'm_factors'      : cl.get('m_factors', {}),
        'scl'            : [
            {
                'h_code' : s.get('h_code', ''),
                'h_class': s.get('class', ''),
                'c_min'  : s.get('c_min'),
                'c_max'  : s.get('c_max'),
            }
            for s in cl.get('scl_limits', [])
        ],
        'sea_ek6'        : priority == 1,
        'annex_vi'       : priority <= 2,
        'source'         : source_label,
        'source_priority': priority,
    }


# ---------------------------------------------------------------------------
# Custom (tedarikçi) DB — küçük, JSON yüklemek sorun değil
# ---------------------------------------------------------------------------

def _load_custom() -> Dict:
    global _CUSTOM_DB
    if _CUSTOM_DB is None:
        with _lock:
            if _CUSTOM_DB is None:
                try:
                    with open(_CUSTOM_PATH, encoding='utf-8') as f:
                        _CUSTOM_DB = json.load(f)
                except Exception:
                    _CUSTOM_DB = {}
    return _CUSTOM_DB


def _load_oel() -> Dict:
    global _OEL_DB
    if _OEL_DB is None:
        with _lock:
            if _OEL_DB is None:
                try:
                    with open(_OEL_PATH, encoding='utf-8') as f:
                        _OEL_DB = json.load(f)
                except Exception:
                    _OEL_DB = {}
    return _OEL_DB


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def lookup_substance(cas: str) -> Optional[Dict]:
    """
    CAS numarasına göre madde bilgisi döndür.
    Sıra 1: SEA Ek-6 (cl/)  →  Sıra 2: Annex VI (annex6/)  →  Sıra 3: Custom
    """
    cas = cas.strip()

    # Sıra 1 — SEA Ek-6
    entry = _read_cl_file(_CL_DIR, cas)
    if entry:
        return _cl_to_legacy(entry, 1, f'SEA Ek-6 ({entry.get("atp","?")})')

    # Sıra 2 — CLP Annex VI
    entry = _read_cl_file(_ANNEX6_DIR, cas)
    if entry:
        return _cl_to_legacy(entry, 2, f'CLP Annex VI ({entry.get("atp","?")})')

    # Sıra 3 — Custom (tedarikçi/kullanıcı)
    custom = _load_custom()
    c = custom.get(cas)
    if c:
        e = dict(c)
        e.setdefault('sea_ek6', False)
        e.setdefault('annex_vi', False)
        e.setdefault('source', 'Tedarikçi/Kullanıcı Girişi')
        e['source_priority'] = 4
        return e

    return None


def search_substances(query: str, limit: int = 20) -> list:
    """
    İsim veya CAS'a göre madde arama.
    cl/ klasöründeki dosyaları tarar — sadece dosya adları (CAS) kontrol edilir,
    isim araması için CAS eşleşmesi + açık dosya okuma yapılır.
    """
    q = query.strip().lower()
    if len(q) < 2:
        return []

    results = []

    # cl/ ve annex6/ klasörlerini tara
    for directory, priority, src in [
        (_CL_DIR,     1, 'SEA Ek-6'),
        (_ANNEX6_DIR, 2, 'CLP Annex VI'),
    ]:
        if not os.path.isdir(directory):
            continue
        for prefix_dir in os.listdir(directory):
            prefix_path = os.path.join(directory, prefix_dir)
            if not os.path.isdir(prefix_path):
                continue
            for fname in os.listdir(prefix_path):
                if not fname.endswith('.json'):
                    continue
                cas = fname[:-5]  # .json kaldır
                # Önce CAS eşleşmesine bak (dosya açmadan)
                if q in cas.lower():
                    entry = _read_cl_file(directory, cas)
                    if entry:
                        results.append(_build_search_result(cas, entry, priority, src))
                        if len(results) >= limit * 3:
                            break
            # İsim araması için dosya açmak gerekiyor (sınırlı tut)
            if q not in ('-', '.') and len(results) < limit:
                for fname in os.listdir(prefix_path):
                    if not fname.endswith('.json'):
                        continue
                    cas = fname[:-5]
                    if q in cas.lower():
                        continue  # Zaten üstte eklendi
                    entry = _read_cl_file(directory, cas)
                    if entry and q in (entry.get('name', '') or '').lower():
                        results.append(_build_search_result(cas, entry, priority, src))
                    if len(results) >= limit * 3:
                        break

    # Custom'a da bak
    for cas, data in _load_custom().items():
        name = (data.get('name') or '').lower()
        if q in cas.lower() or q in name:
            results.append({
                'cas': cas, 'name': data.get('name', ''),
                'ec_no': data.get('ec_no', ''),
                'sea_ek6': False, 'annex_vi': False,
                'source': 'Tedarikçi/Kullanıcı Girişi',
                'source_priority': 4,
                'hazard_count': len(data.get('hazards', [])),
                'h_codes': [h['h_code'] for h in data.get('hazards', []) if h.get('h_code')],
            })

    results.sort(key=lambda x: (x['source_priority'], x['name'].lower()))
    return results[:limit]


def _build_search_result(cas: str, entry: dict, priority: int, src: str) -> dict:
    cl = entry.get('classification', {})
    lb = entry.get('labelling', {})
    h_codes = lb.get('h_codes', [cl_h.get('h_code', '') for cl_h in cl.get('hazards', [])])
    return {
        'cas'            : cas,
        'name'           : entry.get('name', ''),
        'ec_no'          : entry.get('ec_no', ''),
        'sea_ek6'        : priority == 1,
        'annex_vi'       : priority <= 2,
        'source'         : f'{src} ({entry.get("atp","?")})',
        'source_priority': priority,
        'hazard_count'   : len(cl.get('hazards', [])),
        'h_codes'        : [c for c in h_codes if c],
    }


def save_custom_substance(cas: str, entry: Dict) -> bool:
    """Tedarikçi/kullanıcı maddesini substances_custom.json'a kaydet."""
    global _CUSTOM_DB
    with _lock:
        custom = _load_custom()
        is_new = cas not in custom
        entry['annex_vi']        = False
        entry['sea_ek6']         = False
        entry['source_priority'] = 4
        entry.setdefault('atp', 'custom')
        custom[cas] = entry
        with open(_CUSTOM_PATH, 'w', encoding='utf-8') as f:
            json.dump(custom, f, ensure_ascii=False, indent=2)
        _CUSTOM_DB = custom
    return is_new


def is_annex_vi(cas: str) -> bool:
    """Madde SEA Ek-6 veya Annex VI'da mı?"""
    cas = cas.strip()
    return (
        os.path.exists(os.path.join(_CL_DIR,     cas[:2], f'{cas}.json')) or
        os.path.exists(os.path.join(_ANNEX6_DIR, cas[:2], f'{cas}.json'))
    )


def is_sea_ek6(cas: str) -> bool:
    """Madde SEA Ek-6'da mı?"""
    cas = cas.strip()
    return os.path.exists(os.path.join(_CL_DIR, cas[:2], f'{cas}.json'))


def get_oel(cas: str) -> Optional[Dict]:
    """TR OEL limitlerini döndür."""
    return _load_oel().get(cas.strip())


def get_substance_count() -> int:
    """data/cl/ + data/annex6/ + custom toplam madde sayısı."""
    count = 0
    for d in [_CL_DIR, _ANNEX6_DIR]:
        if os.path.isdir(d):
            for sub in os.listdir(d):
                sub_path = os.path.join(d, sub)
                if os.path.isdir(sub_path):
                    count += sum(1 for f in os.listdir(sub_path) if f.endswith('.json'))
    count += len(_load_custom())
    return count


def get_custom_count() -> int:
    return len(_load_custom())


def get_oel_count() -> int:
    return len(_load_oel())
