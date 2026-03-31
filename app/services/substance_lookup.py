"""
Substance Lookup Service
========================
Üç katmanlı madde veritabanı (TR SDS öncelik sırası):

  Sıra 1 — substances_sea_ek6.json   : SEA Yönetmeliği Ek-6 (TR, mutlak)
  Sıra 2 — substances_annex_vi.json  : AB CLP Annex VI (global, ATP güncel)
  Sıra 4 — substances_custom.json    : Tedarikçi/kullanıcı girişi

Birleştirme kuralı (aynı CAS her iki kaynakta varsa):
  - H kodları / sinyal kelimesi / piktogram → SEA Ek-6 (TR hukuki öncelik)
  - M-faktörü / SCL eşikleri               → ATP versiyonu daha yüksek olan
  - İsim / EC No / index_no                → SEA Ek-6, yoksa AB

ATP sıralaması: CLP00 < ATP01 < ATP02 ... < ATP14 < ATP15 ...
"""
import json, os, threading, re
from typing import Optional, Dict

_BASE     = os.path.join(os.path.dirname(__file__), '..', '..', 'data')
_SEA_PATH    = os.path.join(_BASE, 'substances_sea_ek6.json')
_ANNEX_PATH  = os.path.join(_BASE, 'substances_annex_vi.json')
_CUSTOM_PATH = os.path.join(_BASE, 'substances_custom.json')
_OEL_PATH    = os.path.join(_BASE, 'tr_oel_limits.json')

_SEA_DB:       Optional[Dict] = None
_ANNEX_DB:     Optional[Dict] = None
_CUSTOM_DB:    Optional[Dict] = None
_OEL_DB:       Optional[Dict] = None
_MERGED_DB:    Optional[Dict] = None  # birleşik cache (hızlı lookup için)
_lock = threading.Lock()


# ---------------------------------------------------------------------------
# ATP versiyon karşılaştırması
# ---------------------------------------------------------------------------

def _atp_rank(atp: str) -> int:
    """'CLP00'→0, 'ATP01'→1, 'ATP14'→14, 'ATP15'→15 ..."""
    if not atp:
        return -1
    m = re.search(r'(\d+)', str(atp))
    return int(m.group(1)) if m else 0


# ---------------------------------------------------------------------------
# Birleştirme: SEA Ek-6 + AB Annex VI → tek kayıt
# ---------------------------------------------------------------------------

def _merge_entries(sea: dict, ab: dict) -> dict:
    """
    Aynı CAS için SEA Ek-6 ve AB Annex VI kayıtlarını birleştir.

    H kodları / sinyal / piktogram  → SEA Ek-6 (TR hukuki kaynak)
    M-faktörü / SCL eşikleri        → ATP versiyonu daha yüksek olan
    İsim / EC / index_no             → SEA Ek-6, yoksa AB
    """
    sea_rank = _atp_rank(sea.get('atp', ''))
    ab_rank  = _atp_rank(ab.get('atp', ''))
    newer    = ab if ab_rank > sea_rank else sea  # eşik/M-faktörü için

    merged = dict(sea)  # temel olarak SEA al

    # M-faktörü: daha güncel ATP'den
    if newer.get('m_factors'):
        merged['m_factors'] = newer['m_factors']

    # SCL (specific concentration limits): daha güncel ATP'den
    if newer.get('scl'):
        merged['scl'] = newer['scl']

    # İsim/EC: SEA'da boşsa AB'den al
    if not merged.get('name') and ab.get('name'):
        merged['name'] = ab['name']
    if not merged.get('ec_no') and ab.get('ec_no'):
        merged['ec_no'] = ab['ec_no']

    # Kaynak bilgisi
    if ab_rank > sea_rank:
        merged['source']     = f'SEA Ek-6 (H/sinyal) + CLP {ab.get("atp","Annex VI")} (M-faktörü/eşik)'
        merged['atp_note']   = f'SEA:{sea.get("atp","?")} < AB:{ab.get("atp","?")} — eşik AB\'den alındı'
    else:
        merged['source']     = f'SEA Ek-6 ({sea.get("atp","?")})'
        merged['atp_note']   = ''

    merged['sea_ek6']    = True
    merged['annex_vi']   = True  # geriye dönük uyumluluk
    merged['source_priority'] = 1
    return merged


# ---------------------------------------------------------------------------
# Yükleme
# ---------------------------------------------------------------------------

def _read_json(path: str) -> Dict:
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def _load_sea() -> Dict:
    global _SEA_DB
    if _SEA_DB is None:
        with _lock:
            if _SEA_DB is None:
                _SEA_DB = _read_json(_SEA_PATH)
    return _SEA_DB


def _load_annex() -> Dict:
    global _ANNEX_DB
    if _ANNEX_DB is None:
        with _lock:
            if _ANNEX_DB is None:
                _ANNEX_DB = _read_json(_ANNEX_PATH)
    return _ANNEX_DB


def _load_custom() -> Dict:
    global _CUSTOM_DB
    if _CUSTOM_DB is None:
        with _lock:
            if _CUSTOM_DB is None:
                _CUSTOM_DB = _read_json(_CUSTOM_PATH)
    return _CUSTOM_DB


def _load_oel() -> Dict:
    global _OEL_DB
    if _OEL_DB is None:
        with _lock:
            if _OEL_DB is None:
                _OEL_DB = _read_json(_OEL_PATH)
    return _OEL_DB


def _load_db() -> Dict:
    """Birleşik cache: SEA Ek-6 > AB Annex VI > Custom"""
    global _MERGED_DB
    if _MERGED_DB is None:
        with _lock:
            if _MERGED_DB is None:
                sea    = _load_sea()
                annex  = _load_annex()
                custom = _load_custom()

                merged = {}

                # Tüm CAS'ları topla
                all_cas = set(sea) | set(annex) | set(custom)

                for cas in all_cas:
                    s = sea.get(cas)
                    a = annex.get(cas)
                    c = custom.get(cas)

                    if s and a:
                        # Her iki resmi kaynakta var → birleştir
                        merged[cas] = _merge_entries(s, a)
                    elif s:
                        # Sadece SEA Ek-6
                        e = dict(s)
                        e['sea_ek6'] = True
                        e['annex_vi'] = True
                        e['source'] = f'SEA Ek-6 ({s.get("atp","?")})'
                        e['source_priority'] = 1
                        merged[cas] = e
                    elif a:
                        # Sadece AB Annex VI (SEA'da yok)
                        e = dict(a)
                        e['sea_ek6'] = False
                        e['annex_vi'] = True
                        e['source'] = f'CLP Annex VI ({a.get("atp","?")})'
                        e['source_priority'] = 2
                        merged[cas] = e
                    elif c:
                        # Sadece custom (tedarikçi/kullanıcı)
                        e = dict(c)
                        e['sea_ek6'] = False
                        e['annex_vi'] = False
                        e['source'] = 'Tedarikçi/Kullanıcı Girişi'
                        e['source_priority'] = 4
                        merged[cas] = e

                _MERGED_DB = merged
    return _MERGED_DB


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def lookup_substance(cas: str) -> Optional[Dict]:
    """CAS numarasına göre madde bilgisi döndür."""
    return _load_db().get(cas.strip())


def search_substances(query: str, limit: int = 20) -> list:
    """İsim veya CAS'a göre madde arama."""
    db = _load_db()
    q = query.strip().lower()
    if len(q) < 2:
        return []
    results = []
    for cas, data in db.items():
        name = (data.get('name') or '').lower()
        if q in cas.lower() or q in name:
            results.append({
                'cas'          : cas,
                'name'         : data.get('name', ''),
                'ec_no'        : data.get('ec_no', ''),
                'sea_ek6'      : data.get('sea_ek6', False),
                'annex_vi'     : data.get('annex_vi', False),
                'source'       : data.get('source', ''),
                'source_priority': data.get('source_priority', 9),
                'hazard_count' : len(data.get('hazards', [])),
                'h_codes'      : [h['h_code'] for h in data.get('hazards', []) if h.get('h_code')],
            })
        if len(results) >= limit * 2:
            break
    # SEA Ek-6 önce, sonra AB, sonra custom; eşitlikte isim sırası
    results.sort(key=lambda x: (x['source_priority'], x['name'].lower()))
    return results[:limit]


def save_custom_substance(cas: str, entry: Dict) -> bool:
    """
    Tedarikçi/kullanıcı maddesini substances_custom.json'a kaydet.
    Dönüş: True=yeni eklendi, False=güncellendi.
    """
    global _CUSTOM_DB, _MERGED_DB
    with _lock:
        custom = _load_custom()
        is_new = cas not in custom
        entry['annex_vi']      = False
        entry['sea_ek6']       = False
        entry['source_priority'] = 4
        if 'atp' not in entry:
            entry['atp'] = 'custom'
        custom[cas] = entry
        with open(_CUSTOM_PATH, 'w', encoding='utf-8') as f:
            json.dump(custom, f, ensure_ascii=False, indent=2)
        _CUSTOM_DB = custom
        _MERGED_DB = None  # cache'i sıfırla — bir sonraki lookup yeniden birleştirir
    return is_new


def is_annex_vi(cas: str) -> bool:
    """Madde SEA Ek-6 veya AB Annex VI listesinde mi?"""
    return cas.strip() in _load_sea() or cas.strip() in _load_annex()


def is_sea_ek6(cas: str) -> bool:
    """Madde SEA Ek-6 listesinde mi?"""
    return cas.strip() in _load_sea()


def get_oel(cas: str) -> Optional[Dict]:
    """TR OEL limitlerini döndür."""
    return _load_oel().get(cas.strip())


def get_substance_count() -> int:
    return len(_load_db())


def get_custom_count() -> int:
    return len(_load_custom())


def get_oel_count() -> int:
    return len(_load_oel())
