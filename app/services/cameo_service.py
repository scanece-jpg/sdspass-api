"""
CAMEOService — PubChem üzerinden Bölüm 10.5 uyumsuzluk verisi

PubChem "Stability and Reactivity" bölümünden:
  - Reactivity Profile  : serbest metin (İngilizce), section 10.5 için kaynak
  - Reactive Group      : CAMEO sınıfı (amin, asit, baz vs.) — Türkçe özet üretmek için

Sonuç önbelleğe alınır (lru_cache — process ömrü boyunca).
Ağ hatalarında boş dict döner; çağıran her zaman fallback'i kullanır.
"""

import json
import re
import urllib.request
from functools import lru_cache
from typing import Dict, List

_PUBCHEM_BASE = 'https://pubchem.ncbi.nlm.nih.gov/rest'
_TIMEOUT = 8


@lru_cache(maxsize=256)
def _get_cid(cas: str) -> int | None:
    """CAS numarasından PubChem CID döndür."""
    url = f'{_PUBCHEM_BASE}/pug/compound/name/{cas}/property/IUPACName/JSON'
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'SDSPass/1.0'})
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as r:
            d = json.loads(r.read())
            return d['PropertyTable']['Properties'][0].get('CID')
    except Exception:
        return None


@lru_cache(maxsize=256)
def _get_stability_section(cid: int) -> dict:
    """PubChem CID için Stability and Reactivity bölümünü çek."""
    url = (f'{_PUBCHEM_BASE}/pug_view/data/compound/{cid}/JSON/'
           f'?heading=Stability+and+Reactivity')
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'SDSPass/1.0'})
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as r:
            return json.loads(r.read())
    except Exception:
        return {}


def _extract_strings(obj, results=None):
    if results is None:
        results = []
    if isinstance(obj, str) and len(obj) > 20:
        results.append(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            _extract_strings(v, results)
    elif isinstance(obj, list):
        for v in obj:
            _extract_strings(v, results)
    return results


# CAMEO reaktif grup → Türkçe kısa uyumsuzluk listesi
_GROUP_INCOMPAT_TR: Dict[str, List[str]] = {
    'Amines, Phosphines, and Pyridines': [
        'kuvvetli asitler', 'güçlü oksitleyiciler', 'klorlu bileşikler',
    ],
    'Bases, Strong': [
        'asitler', 'güçlü oksitleyiciler',
    ],
    'Acids, Strong': [
        'bazlar', 'güçlü oksitleyiciler', 'aktif metaller',
    ],
    'Oxidizing Agents, Strong': [
        'yanıcı maddeler', 'indirgeyici maddeler', 'asitler',
    ],
    'Alcohols and Polyols': [
        'güçlü oksitleyiciler', 'kuvvetli asitler', 'alkali metaller',
    ],
    'Ketones': [
        'güçlü oksitleyiciler', 'klorlu bileşikler',
    ],
    'Halogenated Organic Compounds': [
        'güçlü bazlar', 'alkali metaller',
    ],
    'Flammable and Combustible Materials': [
        'güçlü oksitleyiciler',
    ],
}


def get_incompatibilities(cas: str) -> Dict:
    """
    CAS numarası için uyumsuzluk verisi döndür.

    Returns:
        {
          'reactive_group': str,         # CAMEO reaktif grup adı (İngilizce)
          'incompat_tr': [str],          # Türkçe uyumsuzluk listesi
          'reactivity_text': str,        # PubChem serbest metin (İngilizce)
          'source': 'pubchem' | 'none',
        }
    """
    cid = _get_cid(cas)
    if not cid:
        return {'reactive_group': '', 'incompat_tr': [], 'reactivity_text': '', 'source': 'none'}

    data = _get_stability_section(cid)
    if not data:
        return {'reactive_group': '', 'incompat_tr': [], 'reactivity_text': '', 'source': 'none'}

    texts = _extract_strings(data)

    # Reaktif grup — "Amines, Phosphines..." gibi kısa satırlar
    reactive_group = ''
    for t in texts:
        if any(kw in t for kw in ('Amines', 'Bases, Strong', 'Acids, Strong',
                                   'Oxidizing', 'Alcohols', 'Ketones',
                                   'Halogenated', 'Flammable')):
            if len(t) < 80:
                reactive_group = t
                break

    # Reaktivite profili — uzun cümle, "Reacts with" veya "is a base/acid" içeriyor
    reactivity_text = ''
    for t in texts:
        if len(t) > 80 and any(kw in t.lower() for kw in
                                ('reacts with', 'is a base', 'is an acid',
                                 'incompatible', 'oxidizing', 'acids')):
            reactivity_text = t
            break

    incompat_tr = _GROUP_INCOMPAT_TR.get(reactive_group, [])

    # Reaktivite metninden ek çıkarım — "kuvvetli oksitleyiciler" gibi terimleri bul
    text_lower = (reactivity_text or '').lower()
    if 'oxidiz' in text_lower or 'oxidis' in text_lower:
        if 'güçlü oksitleyiciler' not in incompat_tr:
            incompat_tr = list(incompat_tr) + ['güçlü oksitleyiciler']
    if 'strong acid' in text_lower or 'inorganic acid' in text_lower:
        if 'kuvvetli asitler' not in incompat_tr:
            incompat_tr = list(incompat_tr) + ['kuvvetli asitler']
    if 'strong base' in text_lower or 'alkali' in text_lower:
        if 'güçlü bazlar' not in incompat_tr:
            incompat_tr = list(incompat_tr) + ['güçlü bazlar']

    return {
        'reactive_group': reactive_group,
        'incompat_tr':    incompat_tr,
        'reactivity_text': reactivity_text,
        'source':          'pubchem' if (reactive_group or reactivity_text) else 'none',
    }


def get_mixture_incompatibilities(components: list) -> List[str]:
    """
    Bileşen listesi için birleşik uyumsuzluk kümesi döndür.
    Her bileşen: {'cas_no': str} veya {'cas': str}

    Returns: Türkçe uyumsuzluk ifadeleri listesi
    """
    combined: set = set()
    for comp in components:
        cas = (comp.get('cas_no') or comp.get('cas') or '').strip()
        if not cas:
            continue
        result = get_incompatibilities(cas)
        for item in result.get('incompat_tr', []):
            combined.add(item)
    return sorted(combined)
