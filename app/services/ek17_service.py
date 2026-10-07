"""KKDİK Ek-17 (kısıtlamalar) — CAS → kısıtlama girişi. Veri: data/kkdik_ek17_cas.json
(scripts/build_ek17_cas.py ile bilgi tabanındaki Ek-17 ve eklerinden üretilir).
Not: KKDİK Ek-14 (izne tabi maddeler) yönetmelik metninde boştur; Bakanlık sitesinde yayımlanır."""
import json
import os
from typing import Dict, List

_DB = None


def db() -> Dict[str, List[dict]]:
    global _DB
    if _DB is None:
        p = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'kkdik_ek17_cas.json')
        try:
            _DB = json.load(open(p, encoding='utf-8'))['cas']
        except Exception:
            _DB = {}
    return _DB


def lookup(cas: str) -> List[dict]:
    return db().get((cas or '').strip(), [])


def section15_lines(components: list, lang: str = 'TR') -> List[str]:
    """15.1 için Ek-17 kapsamındaki bileşenlerin satırları; kapsamda bileşen yoksa boş liste."""
    tr = lang == 'TR'
    rows, seen = [], set()
    for c in components or []:
        cas = (c.get('cas') or c.get('cas_no') or '').strip()
        if not cas or cas in seen:
            continue
        seen.add(cas)
        recs = lookup(cas)
        if not recs:
            continue
        name = (c.get('name_tr') if tr else '') or c.get('name') or cas
        name = ('İ' if tr and name[0] == 'i' else name[0].upper()) + name[1:]
        refs = '; '.join(r['kaynak'].replace('KKDİK ', '') if tr else
                         r['kaynak'].replace('KKDİK Ek-17 madde', 'KKDİK Annex 17 entry')
                                    .replace('KKDİK Ek-17 Ek-', 'KKDİK Annex 17 Appendix ')
                                    .replace('Giriş', 'Entry')
                         for r in recs)
        rows.append(f'• {name} (CAS {cas}): {refs}')
    if not rows:
        return []
    if tr:
        return (['KKDİK Ek-17 (kısıtlamalar) kapsamında listelenen bileşenler:'] + rows +
                ['Bu maddelerin piyasaya arzı ve kullanımı, KKDİK Ek-17\'nin ilgili maddesinde belirtilen '
                 'koşullara tabidir.'])
    return (['Components listed in KKDİK Annex 17 (restrictions):'] + rows +
            ['Placing on the market and use of these substances are subject to the conditions of the relevant '
             'entry of KKDİK Annex 17.'])
