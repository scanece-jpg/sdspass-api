"""
Substance Lookup Service
========================
İki kaynaklı madde veritabanı:
  substances_annex_vi.json  → 4155 madde (EU CLP Annex VI resmi listesi, salt okunur)
  substances_custom.json    → kullanıcı eklemeleri (Annex VI dışı, düzenlenebilir)

Annex VI güncellenince sadece substances_annex_vi.json değiştirilir;
custom liste etkilenmez.
"""
import json, os, threading
from typing import Optional, Dict

_BASE = os.path.join(os.path.dirname(__file__), '..', '..', 'data')
_ANNEX_PATH  = os.path.join(_BASE, 'substances_annex_vi.json')
_CUSTOM_PATH = os.path.join(_BASE, 'substances_custom.json')
_OEL_PATH    = os.path.join(_BASE, 'tr_oel_limits.json')

_SUBSTANCE_DB: Optional[Dict] = None   # merge: annex_vi + custom
_CUSTOM_DB:    Optional[Dict] = None   # sadece custom (yazma için)
_OEL_DB:       Optional[Dict] = None
_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Yükleme
# ---------------------------------------------------------------------------

def _load_db() -> Dict:
    global _SUBSTANCE_DB, _CUSTOM_DB
    if _SUBSTANCE_DB is None:
        with _lock:
            if _SUBSTANCE_DB is None:   # double-check
                annex  = _read_json(_ANNEX_PATH)
                custom = _read_json(_CUSTOM_PATH)
                _CUSTOM_DB = custom
                merged = {}
                merged.update(annex)    # annex_vi önce
                merged.update(custom)   # custom üzerine yazar (override mümkün)
                _SUBSTANCE_DB = merged
    return _SUBSTANCE_DB


def _load_custom() -> Dict:
    global _CUSTOM_DB
    if _CUSTOM_DB is None:
        _load_db()
    return _CUSTOM_DB


def _load_oel() -> Dict:
    global _OEL_DB
    if _OEL_DB is None:
        with _lock:
            if _OEL_DB is None:
                _OEL_DB = _read_json(_OEL_PATH)
    return _OEL_DB


def _read_json(path: str) -> Dict:
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def lookup_substance(cas: str) -> Optional[Dict]:
    """CAS numarasına göre madde bilgisi döndür (Annex VI + Custom)."""
    db = _load_db()
    return db.get(cas.strip())


def search_substances(query: str, limit: int = 20) -> list:
    """İsim veya CAS'a göre madde arama (min 2 karakter)."""
    db = _load_db()
    q = query.strip().lower()
    if len(q) < 2:
        return []
    results = []
    for cas, data in db.items():
        name = (data.get('name') or '').lower()
        if q in cas.lower() or q in name:
            results.append({
                'cas': cas,
                'name': data.get('name', ''),
                'ec_no': data.get('ec_no', ''),
                'annex_vi': data.get('annex_vi', False),
                'hazard_count': len(data.get('hazards', [])),
                'h_codes': [h['h_code'] for h in data.get('hazards', []) if h.get('h_code')],
            })
        if len(results) >= limit:
            break
    # Annex VI önce, sonra isim sırasına göre
    results.sort(key=lambda x: (not x['annex_vi'], x['name'].lower()))
    return results[:limit]


def save_custom_substance(cas: str, entry: Dict) -> bool:
    """
    Annex VI dışı maddeyi substances_custom.json'a kaydet.
    entry örnek: {
        "name": "water",
        "ec_no": "231-791-2",
        "annex_vi": False,
        "signal": "",
        "pictograms": [],
        "hazards": [],
        "m_factors": {},
        "index_no": "",
        "atp": "custom"
    }
    Dönüş: True=yeni eklendi, False=zaten vardı (güncellendi)
    """
    global _SUBSTANCE_DB, _CUSTOM_DB
    with _lock:
        custom = _load_custom()
        is_new = cas not in custom
        entry['annex_vi'] = False   # custom her zaman False
        if 'atp' not in entry:
            entry['atp'] = 'custom'
        custom[cas] = entry
        # Dosyaya yaz (okunabilir format)
        with open(_CUSTOM_PATH, 'w', encoding='utf-8') as f:
            json.dump(custom, f, ensure_ascii=False, indent=2)
        # Bellek cache'ini güncelle
        _CUSTOM_DB = custom
        if _SUBSTANCE_DB is not None:
            _SUBSTANCE_DB[cas] = entry
    return is_new


def is_annex_vi(cas: str) -> bool:
    """Madde Annex VI listesinde mi?"""
    annex = _read_json(_ANNEX_PATH)
    return cas.strip() in annex


def get_oel(cas: str) -> Optional[Dict]:
    """TR OEL limitlerini döndür."""
    return _load_oel().get(cas.strip())


def get_substance_count() -> int:
    return len(_load_db())


def get_custom_count() -> int:
    return len(_load_custom())


def get_oel_count() -> int:
    return len(_load_oel())
