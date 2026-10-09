"""
SEA Md.6(1)(c) — Ek-6 (uyumlaştırılmış) sınıflandırma ile ECHA C&L öz-sınıflandırma bildirimlerinin birleştirilmesi.

Ek-6'da yer alan bir madde için ECHA bildirimlerinden YALNIZ Ek-6 girişinde bulunmayan tehlike sınıfları veya
farklılaştırmaları (akut toksisitede maruziyet yolu, üreme toksisitesinde F/D etkisi, BHOT Kat. 3'te solunum yolu
tahrişi / narkotik etki) eklenir. Ek-6'da bulunan bir sınıfın ECHA'daki farklı kategorisi eklenmez: önceden H kodları
karşılaştırıldığı için klor (Ek-6 Akut Tok. 3, H331) ECHA'dan Akut Tok. 2 (H330) alıyordu (2026-10-09).

ECHA'daki kategori Ek-6'dakinden daha ağırsa hesaba katılmaz; yalnız KDU'ya bilgi olarak döner (Ek-6 girişi asgari
sınıflandırma "*" ise ve daha ağır kategoriyi destekleyen veri varsa KDU uygular — SEA Ek-6 Bölüm 1.2.1).
"""
import re
from typing import List, Optional, Tuple

_AT_ROUTE = {'H300': 'oral', 'H301': 'oral', 'H302': 'oral', 'H310': 'dermal', 'H311': 'dermal', 'H312': 'dermal',
             'H330': 'inh', 'H331': 'inh', 'H332': 'inh'}
_AT_DEFAULT_CAT = {'H300': 1.5, 'H310': 1.5, 'H330': 1.5, 'H301': 3, 'H311': 3, 'H331': 3,
                   'H302': 4, 'H312': 4, 'H332': 4}
# H kodu → (aile, kategori); kategori küçük = daha ağır
_FIXED = {
    'H314': ('Skin', 1), 'H315': ('Skin', 2), 'H318': ('Eye', 1), 'H319': ('Eye', 2),
    'H317': ('SkinSens', 1), 'H334': ('RespSens', 1),
    'H340': ('Muta', 1), 'H341': ('Muta', 2), 'H350': ('Carc', 1), 'H351': ('Carc', 2), 'H362': ('Lact', 1),
    'H370': ('STOT SE 1-2', 1), 'H371': ('STOT SE 1-2', 2), 'H335': ('STOT SE 3 RTI', 3), 'H336': ('STOT SE 3 NE', 3),
    'H372': ('STOT RE', 1), 'H373': ('STOT RE', 2), 'H304': ('Asp', 1),
    'H400': ('AqAcute', 1), 'H410': ('AqChronic', 1), 'H411': ('AqChronic', 2), 'H412': ('AqChronic', 3),
    'H413': ('AqChronic', 4), 'H420': ('Ozone', 1),
    'H220': ('FlamGas', 1), 'H221': ('FlamGas', 2), 'H222': ('Aerosol', 1), 'H223': ('Aerosol', 2),
    'H229': ('Aerosol', 3), 'H224': ('FlamLiq', 1), 'H225': ('FlamLiq', 2), 'H226': ('FlamLiq', 3),
    'H228': ('FlamSol', 1.5), 'H270': ('OxGas', 1), 'H280': ('PressGas', 1), 'H281': ('PressGas', 1),
    'H290': ('MetCorr', 1), 'H250': ('Pyr', 1), 'H251': ('SelfHeat', 1), 'H252': ('SelfHeat', 2),
    'H260': ('WaterReact', 1), 'H261': ('WaterReact', 2),
}


def _cat_from_class(h_class: str) -> Optional[float]:
    m = re.search(r'(\d)\s*([ABC])?\s*\*?\s*$', (h_class or '').strip())
    if not m:
        return None
    return int(m.group(1)) + ({'A': 0.0, 'B': 0.1, 'C': 0.2}.get(m.group(2) or '', 0.0))


def families(h_class: str, h_code: str) -> List[Tuple[str, float]]:
    """Bir sınıflandırma satırının (aile, kategori) listesi. Üreme toksisitesi F/D etkisine göre ayrılır."""
    code = (h_code or '').replace('*', '').strip()
    c4 = code[:4]
    if c4 in _AT_ROUTE:
        return [('Acute Tox ' + _AT_ROUTE[c4], _cat_from_class(h_class) or _AT_DEFAULT_CAT[c4])]
    if c4 in ('H360', 'H361'):
        base = 1 if c4 == 'H360' else 2
        suf = code[4:]
        if not suf:
            return [('Repr-?', base)]
        out = []
        for ch in suf:
            if ch in 'FD':
                out.append((f'Repr-{ch}', 1 if base == 1 else 2))
            elif ch in 'fd':
                out.append((f'Repr-{ch.upper()}', 2))
        return out or [('Repr-?', base)]
    if c4 in ('H271', 'H272'):
        fam = 'OxSol' if 'Sol' in (h_class or '') or 'Katı' in (h_class or '') else 'OxLiq'
        return [(fam, 1 if c4 == 'H271' else (_cat_from_class(h_class) or 2.5))]
    if c4 in ('H240', 'H241', 'H242'):
        return [('SelfReact/OrgPerox', {'H240': 1, 'H241': 2, 'H242': 3}[c4])]
    if c4.startswith('H20'):
        return [('Expl', 1)]
    if c4 in _FIXED:
        fam, cat = _FIXED[c4]
        if fam in ('Skin', 'FlamSol'):
            cat = _cat_from_class(h_class) or cat
        return [(fam, cat)]
    return [(code or (h_class or ''), 1)]


def split_echa(ek6_hazards: list, echa_hazards: list) -> Tuple[list, list]:
    """(eklenecekler, ek6_daha_agir).
    eklenecekler: Ek-6 girişinde ailesi olmayan ECHA satırları (SEA Md.6(1)(c)).
    ek6_daha_agir: Ek-6'da ailesi olan ama ECHA'da daha ağır kategorideki satırlar — hesaba katılmaz,
    {'h_code','h_class','ek6_h_code','ek6_h_class'} olarak KDU bilgisine döner."""
    ek6 = {}
    for h in ek6_hazards or []:
        for fam, cat in families(h.get('h_class', ''), h.get('h_code', '')):
            if fam not in ek6 or cat < ek6[fam][0]:
                ek6[fam] = (cat, h)
    ek6_repr = {f: v for f, v in ek6.items() if f.startswith('Repr-')}
    extra, agir = [], []
    ek6_codes = {(h.get('h_code') or '').replace('*', '').strip() for h in ek6_hazards or []}
    for h in echa_hazards or []:
        code = (h.get('h_code') or '').replace('*', '').strip()
        if not code or code in ek6_codes:
            continue
        fams = families(h.get('h_class', ''), code)
        yeni, daha_agir = False, None
        for fam, cat in fams:
            hit = ek6.get(fam)
            if fam == 'Repr-?' and ek6_repr:
                hit = min(ek6_repr.values(), key=lambda v: v[0])
            if hit is None:
                yeni = True
            elif cat < hit[0]:
                daha_agir = hit[1]
        if yeni:
            extra.append(h)
        elif daha_agir is not None:
            agir.append({'h_code': code, 'h_class': h.get('h_class', ''),
                         'ek6_h_code': daha_agir.get('h_code', ''), 'ek6_h_class': daha_agir.get('h_class', '')})
    return extra, agir
