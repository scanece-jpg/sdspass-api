"""
ECHA API Servisi
CAS numarasından C&L, REACH, EC bilgilerini çeker.
Önce lokal DB'ye bakar, bulamazsa ECHA'dan çeker ve cache'ler.
"""

import httpx
import asyncio
import json
import os
from pathlib import Path

# Lokal cache dosyası
CACHE_FILE = Path(__file__).parent / 'echa_cache.json'

# Lokal CLP veritabanları
_cl_data = None
_av_data = None


def _load_local_dbs():
    global _cl_data, _av_data
    if _cl_data is None:
        try:
            p = Path(__file__).parent.parent.parent.parent / 'clp_cl_data.json'
            with open(p) as f:
                _cl_data = json.load(f)
        except Exception:
            _cl_data = {}
    if _av_data is None:
        try:
            p = Path(__file__).parent.parent.parent.parent / 'annex_vi_lookup.json'
            with open(p) as f:
                _av_data = json.load(f)
        except Exception:
            _av_data = {}


def _load_cache() -> dict:
    try:
        if CACHE_FILE.exists():
            with open(CACHE_FILE) as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _save_cache(cache: dict):
    try:
        with open(CACHE_FILE, 'w') as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def lookup_local(cas: str) -> dict | None:
    """Lokal DB'de CAS ara"""
    _load_local_dbs()
    cas = cas.strip()

    # Annex VI (öncelikli — resmi)
    if cas in _av_data:
        entry = _av_data[cas]
        return {
            'cas': cas,
            'name': entry.get('n', ''),
            'source': 'Annex VI',
            'h_codes': [h.get('h', '') for h in entry.get('h', []) if h.get('h')],
            'hazard_classes': [h.get('c', '') for h in entry.get('h', [])],
        }

    # C&L (bildirim bazlı)
    if cas in _cl_data:
        entry = _cl_data[cas]
        return {
            'cas': cas,
            'name': entry.get('n', ''),
            'source': 'C&L Inventory',
            'h_codes': [h.get('h', '') for h in entry.get('h', []) if h.get('h')],
            'hazard_classes': [h.get('c', '') for h in entry.get('h', [])],
        }

    return None


async def lookup_echa_api(cas: str) -> dict | None:
    """
    ECHA C&L Inventory API'den madde bilgisi çek.
    Ücretsiz, kayıt gerektirmez.
    """
    cas = cas.strip()
    cache = _load_cache()

    # Cache'de var mı?
    if cas in cache:
        return cache[cas]

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            # ECHA C&L API
            resp = await client.get(
                'https://echa.europa.eu/cl-inventory-api/substances',
                params={'cas_rn': cas},
                headers={'Accept': 'application/json'}
            )

            if resp.status_code == 200:
                data = resp.json()
                substances = data.get('substances', []) or data.get('results', [])

                if substances:
                    sub = substances[0]
                    h_codes = []
                    hazard_classes = []

                    for notif in sub.get('clNotifications', []):
                        hc = notif.get('hazardClass', '')
                        hs = notif.get('hazardStatement', '')
                        if hc:
                            hazard_classes.append(hc)
                        if hs and hs not in h_codes:
                            h_codes.append(hs)

                    result = {
                        'cas': cas,
                        'name': sub.get('substanceName', sub.get('name', '')),
                        'ec_no': sub.get('ecNumber', ''),
                        'source': 'ECHA C&L API',
                        'h_codes': h_codes,
                        'hazard_classes': hazard_classes,
                    }

                    # Cache'e kaydet
                    cache[cas] = result
                    _save_cache(cache)
                    return result

    except Exception as e:
        print(f"[ECHA API] {cas}: {e}")

    return None


async def lookup_pubchem(cas: str) -> dict | None:
    """PubChem'den EC no ve isim bilgisi çek"""
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(
                f'https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{cas}/property/IUPACName,InChIKey/JSON'
            )
            if resp.status_code == 200:
                data = resp.json()
                props = data.get('PropertyTable', {}).get('Properties', [])
                if props:
                    return {
                        'cas': cas,
                        'iupac_name': props[0].get('IUPACName', ''),
                        'source': 'PubChem',
                    }
    except Exception:
        pass
    return None


async def lookup_substance(cas: str) -> dict:
    """
    Ana lookup fonksiyonu.
    Sıra: Lokal DB → ECHA Cache → ECHA API → PubChem → Boş sonuç
    """
    cas = cas.strip()

    # 1. Lokal DB
    local = lookup_local(cas)
    if local:
        # EC ve REACH no ekle
        from app.services.reach_db import get_ec_no, get_reg_no
        local['ec_no'] = get_ec_no(cas) or ''
        local['reach_no'] = get_reg_no(cas) or ''
        return local

    # 2. ECHA API
    echa = await lookup_echa_api(cas)
    if echa:
        from app.services.reach_db import get_ec_no, get_reg_no
        echa['ec_no'] = echa.get('ec_no') or get_ec_no(cas) or ''
        echa['reach_no'] = get_reg_no(cas) or ''
        return echa

    # 3. Boş sonuç
    from app.services.reach_db import get_ec_no, get_reg_no
    return {
        'cas': cas,
        'name': '',
        'ec_no': get_ec_no(cas) or '',
        'reach_no': get_reg_no(cas) or '',
        'source': 'not_found',
        'h_codes': [],
        'hazard_classes': [],
    }


# Sync wrapper (non-async ortamlar için)
def lookup_substance_sync(cas: str) -> dict:
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # FastAPI içinde — await kullan
            return lookup_local(cas) or {
                'cas': cas, 'name': '', 'ec_no': '', 'reach_no': '',
                'source': 'not_found', 'h_codes': [], 'hazard_classes': []
            }
        return loop.run_until_complete(lookup_substance(cas))
    except Exception:
        return lookup_local(cas) or {
            'cas': cas, 'name': '', 'ec_no': '', 'reach_no': '',
            'source': 'not_found', 'h_codes': [], 'hazard_classes': []
        }
