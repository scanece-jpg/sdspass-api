"""
CAMEOService — PubChem üzerinden Bölüm 10.5 uyumsuzluk verisi

PubChem "Stability and Reactivity" bölümünden:
  - Reactivity Profile  : serbest metin (İngilizce), section 10.5 için kaynak
  - Reactive Group      : CAMEO sınıfı (amin, asit, baz vs.) — Türkçe özet üretmek için

Sonuç iki katmanda önbelleğe alınır:
  1. data/cameo_cache.json — kalıcı dosya (process restart'ta korunur)
  2. lru_cache            — aynı process içinde tekrar disk okuma engellenir
Ağ hatalarında boş dict döner; çağıran her zaman fallback'i kullanır.
"""

import json
import os
import re
import urllib.request
from functools import lru_cache
from typing import Dict, List

_PUBCHEM_BASE = 'https://pubchem.ncbi.nlm.nih.gov/rest'
_TIMEOUT = 8

_CACHE_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'cameo_cache.json')

# ── Dosya önbelleği ───────────────────────────────────────────────────────────

def _load_disk_cache() -> dict:
    try:
        with open(_CACHE_PATH, encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}

def _save_disk_cache(cache: dict) -> None:
    try:
        os.makedirs(os.path.dirname(_CACHE_PATH), exist_ok=True)
        tmp = _CACHE_PATH + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
        os.replace(tmp, _CACHE_PATH)  # atomic — yarım yazma riski yok
    except Exception:
        pass

_disk_cache: dict = _load_disk_cache()


# ── PubChem sorguları ─────────────────────────────────────────────────────────

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


# ── Ana sorgu fonksiyonu ──────────────────────────────────────────────────────

def get_incompatibilities(cas: str) -> Dict:
    """
    CAS numarası için uyumsuzluk verisi döndür.
    Önce dosya cache'e bakar; yoksa PubChem'den çeker ve cache'e yazar.

    Returns:
        {
          'reactive_group': str,
          'incompat_tr': [str],
          'reactivity_text': str,
          'source': 'cache' | 'pubchem' | 'none',
        }
    """
    global _disk_cache

    # 1. Dosya önbelleği
    if cas in _disk_cache:
        entry = _disk_cache[cas]
        return {**entry, 'source': 'cache'}

    # 2. PubChem sorgusu
    _empty = {'reactive_group': '', 'incompat_tr': [], 'reactivity_text': ''}

    cid = _get_cid(cas)
    if not cid:
        _disk_cache[cas] = _empty
        _save_disk_cache(_disk_cache)
        return {**_empty, 'source': 'none'}

    data = _get_stability_section(cid)
    if not data:
        _disk_cache[cas] = _empty
        _save_disk_cache(_disk_cache)
        return {**_empty, 'source': 'none'}

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

    # Reaktivite profili — uzun cümle
    reactivity_text = ''
    for t in texts:
        if len(t) > 80 and any(kw in t.lower() for kw in
                                ('reacts with', 'is a base', 'is an acid',
                                 'incompatible', 'oxidizing', 'acids')):
            reactivity_text = t
            break

    incompat_tr = list(_GROUP_INCOMPAT_TR.get(reactive_group, []))

    text_lower = (reactivity_text or '').lower()
    if 'oxidiz' in text_lower or 'oxidis' in text_lower:
        if 'güçlü oksitleyiciler' not in incompat_tr:
            incompat_tr.append('güçlü oksitleyiciler')
    if 'strong acid' in text_lower or 'inorganic acid' in text_lower:
        if 'kuvvetli asitler' not in incompat_tr:
            incompat_tr.append('kuvvetli asitler')
    if 'strong base' in text_lower or 'alkali' in text_lower:
        if 'güçlü bazlar' not in incompat_tr:
            incompat_tr.append('güçlü bazlar')

    # 3. Dosya önbelleğine yaz
    cache_entry = {
        'reactive_group':  reactive_group,
        'incompat_tr':     incompat_tr,
        'reactivity_text': reactivity_text,
    }
    _disk_cache[cas] = cache_entry
    _save_disk_cache(_disk_cache)

    return {
        **cache_entry,
        'source': 'pubchem' if (reactive_group or reactivity_text) else 'none',
        'unmatched_group': reactive_group if (reactive_group and reactive_group not in _GROUP_INCOMPAT_TR) else None,
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
