"""
Substance Lookup Service
========================
Birleşik madde veritabanından CAS → EC, REACH, sınıflandırma bilgisi.
Kaynak: ECHA C&L + Annex VI + CLP Full Data (4,234 madde)
"""
import json, os
from typing import Optional, Dict

_DB_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'substances_unified.json')
_OEL_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'tr_oel_limits.json')

# Lazy load
_SUBSTANCE_DB: Optional[Dict] = None
_OEL_DB: Optional[Dict] = None


def _load_db():
    global _SUBSTANCE_DB
    if _SUBSTANCE_DB is None:
        try:
            with open(_DB_PATH, encoding='utf-8') as f:
                _SUBSTANCE_DB = json.load(f)
        except Exception:
            _SUBSTANCE_DB = {}
    return _SUBSTANCE_DB


def _load_oel():
    global _OEL_DB
    if _OEL_DB is None:
        try:
            with open(_OEL_PATH, encoding='utf-8') as f:
                _OEL_DB = json.load(f)
        except Exception:
            _OEL_DB = {}
    return _OEL_DB


def lookup_substance(cas: str) -> Optional[Dict]:
    """
    CAS numarasına göre madde bilgisi döndür.
    Returns: {name, ec_no, annex_vi, signal, hazards, m_factors} veya None
    """
    db = _load_db()
    cas = cas.strip()
    return db.get(cas)


def search_substances(query: str, limit: int = 20) -> list:
    """
    İsim veya CAS'a göre madde arama.
    query: en az 3 karakter
    """
    db = _load_db()
    q = query.strip().lower()
    if len(q) < 2:
        return []
    results = []
    for cas, data in db.items():
        name = data.get('name', '').lower()
        if q in cas.lower() or q in name:
            results.append({
                'cas': cas,
                'name': data.get('name',''),
                'ec_no': data.get('ec_no',''),
                'annex_vi': data.get('annex_vi', False),
                'hazard_count': len(data.get('hazards',[])),
                'h_codes': [h['h_code'] for h in data.get('hazards',[]) if h.get('h_code')],
            })
        if len(results) >= limit:
            break
    # Annex VI önce, sonra isim sırasına göre
    results.sort(key=lambda x: (not x['annex_vi'], x['name'].lower()))
    return results[:limit]


def get_oel(cas: str) -> Optional[Dict]:
    """TR OEL limitlerini döndür."""
    oel = _load_oel()
    return oel.get(cas.strip())


def get_substance_count() -> int:
    return len(_load_db())


def get_oel_count() -> int:
    return len(_load_oel())
