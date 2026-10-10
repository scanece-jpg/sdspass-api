"""GBF 15 — BEKRA, ozon tabakasını incelten maddeler, kalıcı organik kirleticiler ve tehlikeli kimyasalların
ithalat/ihracatı (Rotterdam/ÖBK) (KKDİK Ek-2 Bölüm 15 girişi ve 15.1: ürünün bu mevzuata "tabi olup olmadığı"). Veri: data/tr_reg15_lists.json (scripts/build_reg15_lists.py).

Karar kuralları:
- Ozon / KOK: bileşen CAS'ı listede ise "içerir" (kesin). Listede CAS'ı verilmeyen aileler (izomerler, "ve
  diğerleri") adla eşleşirse "olası — KDU doğrulamalı". H420/EUH059 sınıflı bileşen de ozon kapsamında sayılır.
  Hiçbiri yoksa "listelenen maddeleri içermez".
- BEKRA Ek-1 Bölüm 1: karışımın SEA sınıflandırmasından (zararlılık kategorisi). Bölüm 2: adlandırılmış madde CAS'ı
  veya adı. Yükümlülük kuruluştaki toplam miktara bağlıdır — işletmeci değerlendirir.
"""
import json
import os
import re
from typing import List

_DB = None


def _db() -> dict:
    global _DB
    if _DB is None:
        p = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'tr_reg15_lists.json')
        try:
            _DB = json.load(open(p, encoding='utf-8'))
        except Exception:
            _DB = {'kok': {}, 'ozon': {}, 'bekra2': {}, 'pic': {}, 'kaynak': {}}
    return _DB


# Ozon Ek-5'te CAS'ı verilmeyen izomer aileleri (CFC/HCFC/HBFC, halonlar) — ad ile
_OZ_FAM = re.compile(
    r'(?i)\b(?:h?cfc|hbfc)-?\d|\bhalon\b|freon|'
    r'(?:chloro|kloro|klor|bromo|brom)\w*?(?:fluoro|floro|flor)\w*?(?:methan|metan|ethan|etan|propan)|'
    r'(?:fluoro|floro|flor)\w*?(?:chloro|kloro|klor|bromo|brom)\w*?(?:methan|metan|ethan|etan|propan)')
# KOK Ek-1/Ek-2'de "ve diğerleri" ile verilen aileler — ad ile
_KOK_FAM = re.compile(
    r'(?i)brom\w*\s*-?\s*difenil\s*eter|bromodiphenyl\s*ether|\bpbde\b|perfl[uo]+ro-?\s*okta?n|perfluorooctan|'
    r'\bpfos\b|\bpfoa\b|poliklorlu\s*bifenil|polychlorinated\s*biphenyl|\bpcb\b|poliklorlu\s*naftalin|'
    r'polychlorinated\s*naphthalen|klorlu\s*parafin|chlorinated\s*paraffin|alkanes,?\s*c10-13,?\s*chloro|'
    r'pentaklorofenol|pentachlorophenol|hekzabromosiklododekan|hexabromocyclododecan|\bhbcdd?\b|'
    r'dibenzo-?p?-?dioks|dibenzo-?p?-?diox|dibenzofuran')
# ÖBK/PIC (Bazı Zararlı Kimyasalların İhracatı ve İthalatı) Ek-1/Ek-2'de bileşik grubu olarak verilenler — ad ile.
# "Bitki özleri" girişi bitki koruma ürünlerine aittir; ad eşleşmesi yanıltıcı olacağından alınmadı.
_PIC_FAM = re.compile(
    r'(?i)kurşun|\blead\b|kadmiyum|cadmium|arsenik|arsenic|cıva|mercury|mercuric|mercurous|organotin|organokalay|'
    r'tribut\w*\s*tin|tribütil\s*kalay|dibut\w*\s*tin|dibütil\s*kalay|dioct\w*\s*tin|dioktil\s*kalay|'
    r'nonilfenol|nonylphenol|perfl[uo]+ro-?\s*okta?n|perfluorooctan|\bpfos\b|\bpfoa\b|benzidin|naftilamin|'
    r'naphthylamin|aminobifenil|aminobiphenyl|hexabromocyclododec|hekzabromosiklododek|\b2,4,5-t\b|dinoseb')
# BEKRA Ek-1 Bölüm 2 — CAS'ı verilmeyen adlandırılmış maddeler
_BEKRA2_NAMES = [
    (re.compile(r'(?i)amonyum\s*nitrat|ammonium\s*nitrate'), 'Amonyum nitrat (Ek-1 Bölüm 2, Not 13–16)'),
    (re.compile(r'(?i)potasyum\s*nitrat|potassium\s*nitrate'), 'Potasyum nitrat (Ek-1 Bölüm 2, Not 17–18)'),
    (re.compile(r'(?i)benzin|nafta|naphtha|kerosen|kerosine|dizel|diesel|motorin|gas\s*oil|fuel\s*oil|fuel-oil'),
     'Petrol ürünleri ve alternatif yakıtlar (Ek-1 Bölüm 2)'),
    (re.compile(r'(?i)\blpg\b|liquefied\s*petroleum|sıvılaştırılmış\s*petrol|doğal\s*gaz|natural\s*gas'),
     'Sıvılaştırılmış alevlenir gazlar / doğalgaz (Ek-1 Bölüm 2, Not 19)'),
]
_BEKRA2_EXTRA_CAS = {'6484-52-2': 'Amonyum nitrat (Ek-1 Bölüm 2, Not 13–16)',
                     '7757-79-1': 'Potasyum nitrat (Ek-1 Bölüm 2, Not 17–18)'}


def _cas(c) -> str:
    return str(c.get('cas_no') or c.get('cas') or '').strip()


def _names(c) -> str:
    return f"{c.get('name_tr') or ''} {c.get('name') or ''}".strip()


def _conc(c) -> float:
    for k in ('concMax', 'conc_max', 'concentration', 'conc'):
        try:
            if c.get(k) not in (None, ''):
                return float(c.get(k))
        except (TypeError, ValueError):
            pass
    return 0.0


def _hz(c) -> set:
    return {str(h.get('h_code') or '').replace('*', '').strip()[:6].upper() for h in (c.get('hazards') or [])}


def ozone_kok(components: list) -> dict:
    db = _db()
    out = {'ozon': [], 'ozon_olasi': [], 'kok': [], 'kok_olasi': [], 'pic': [], 'pic_olasi': []}
    for c in components or []:
        cas, nm = _cas(c), _names(c) or _cas(c)
        if cas in db['ozon']:
            out['ozon'].append(f"{nm} ({cas}; {db['ozon'][cas]['ek']})")
        elif _hz(c) & {'H420', 'EUH059'}:
            out['ozon'].append(f"{nm} ({cas}; H420 — ozon tabakası için zararlı)")
        elif _OZ_FAM.search(nm):
            out['ozon_olasi'].append(f'{nm} ({cas})')
        if cas in db['kok']:
            out['kok'].append(f"{nm} ({cas}; {db['kok'][cas]['ek']})")
        elif _KOK_FAM.search(nm):
            out['kok_olasi'].append(f'{nm} ({cas})')
        if cas in db.get('pic', {}):
            out['pic'].append(f"{nm} ({cas}; {db['pic'][cas]['ek']})")
        elif _PIC_FAM.search(nm):
            out['pic_olasi'].append(f'{nm} ({cas})')
    return out


# BEKRA Ek-1 Bölüm 2 kaydı maddenin belirli hâlini adlandırıyorsa ("Hidrojen klorür (Sıvılaştırılmış gaz)",
# "Susuz amonyak") yalnız o hâlde uygulanır — sulu çözelti (hidroklorik asit, amonyak çözeltisi) kapsam dışıdır.
_BEKRA2_HAL = re.compile(r'(?i)sıvılaştırılmış\s*gaz|susuz')


def bekra(h_codes, passed=None, euh_codes=(), components=None, form: str = None) -> dict:
    """{'bolum1': [(kod, açıklama)], 'bolum2': [ad]}"""
    hs = {str(h).split()[0][:4].upper() for h in (h_codes or [])}
    eu = {str(e).upper() for e in (euh_codes or [])}
    cls = ' '.join(str(p.get('h_class') or '') for p in (passed or []))
    b1 = []
    if hs & {'H300', 'H310', 'H330'}:
        if re.search(r'(?:Acute Tox\.|Akut Tok\w*\.?)\s*1\b', cls):
            b1.append(('H1', 'Akut toksik Kategori 1'))
        elif re.search(r'(?:Acute Tox\.|Akut Tok\w*\.?)\s*2\b', cls):
            b1.append(('H2', 'Akut toksik Kategori 2'))
        else:
            b1.append(('H1/H2', 'Akut toksik Kategori 1 veya 2'))
    if 'H331' in hs and not any(k.startswith('H2') for k, _ in b1):
        b1.append(('H2', 'Akut toksik Kategori 3, soluma yoluyla'))
    if 'H370' in hs:
        b1.append(('H3', 'BHOT — tek maruz kalma Kategori 1'))
    if hs & {'H200', 'H201', 'H202', 'H203', 'H205'}:
        b1.append(('P1a', 'Patlayıcılar'))
    if 'H204' in hs:
        b1.append(('P1b', 'Patlayıcılar, Kısım 1.4'))
    if hs & {'H220', 'H221'}:
        b1.append(('P2', 'Alevlenir gazlar Kategori 1 veya 2'))
    if hs & {'H222', 'H223'}:
        b1.append(('P3a/P3b', 'Alevlenir aerosoller Kategori 1 veya 2 (içeriğe göre)'))
    if 'H270' in hs:
        b1.append(('P4', 'Oksitleyici gazlar Kategori 1'))
    if 'H224' in hs:
        b1.append(('P5a', 'Alevlenir sıvılar Kategori 1'))
    if hs & {'H225', 'H226'}:
        b1.append(('P5c', 'Alevlenir sıvılar Kategori 2 veya 3 (özel proses koşullarında P5a/P5b)'))
    if hs & {'H240', 'H241'}:
        b1.append(('P6a', 'Kendinden reaktif maddeler / organik peroksitler Tip A veya B'))
    if 'H242' in hs:
        b1.append(('P6b', 'Kendinden reaktif maddeler / organik peroksitler Tip C–F'))
    if 'H250' in hs:
        b1.append(('P7', 'Piroforik sıvılar veya katılar Kategori 1'))
    if hs & {'H271', 'H272'}:
        b1.append(('P8', 'Oksitleyici sıvılar veya katılar Kategori 1, 2 veya 3'))
    if hs & {'H400', 'H410'}:
        b1.append(('E1', 'Sucul ortam için zararlı Akut 1 veya Kronik 1'))
    if 'H411' in hs:
        b1.append(('E2', 'Sucul ortam için zararlı Kronik 2'))
    if 'EUH014' in eu:
        b1.append(('O1', 'EUH014'))
    if 'H260' in hs:
        b1.append(('O2', 'Su ile temas ettiğinde alevlenir gaz çıkaran Kategori 1'))
    if 'EUH029' in eu:
        b1.append(('O3', 'EUH029'))

    db = _db()
    b2 = []
    for c in components or []:
        cas, nm = _cas(c), _names(c)
        if cas == '50-00-0' and _conc(c) < 90:       # formaldehit yalnız ≥ %90
            continue
        if cas in db['bekra2']:
            if _BEKRA2_HAL.search(db['bekra2'][cas]) and form and form != 'gas':
                continue                                    # sulu çözelti / sıvı ürün — o hâl değil
            b2.append(db['bekra2'][cas])
        elif cas in _BEKRA2_EXTRA_CAS:
            b2.append(_BEKRA2_EXTRA_CAS[cas])
        else:
            for rx, lbl in _BEKRA2_NAMES:
                if rx.search(nm):
                    b2.append(lbl)
                    break
        if cas == '7681-52-9':
            b2.append('Sodyum hipoklorit karışımları (Ek-1 Bölüm 2 — %5\'ten az aktif klor ve yalnız Sucul Akut 1 '
                      'koşuluyla)')
    return {'bolum1': b1, 'bolum2': list(dict.fromkeys(b2))}


def section15_lines(h_codes, passed, euh_codes, components, lang: str = 'TR', form: str = None) -> List[str]:
    if lang != 'TR':
        return []
    src = _db().get('kaynak', {})
    oz = ozone_kok(components)
    bk = bekra(h_codes, passed, euh_codes, components, form=form)
    out = []
    # BEKRA
    b1 = '; '.join(f'{k} ({d})' for k, d in bk['bolum1'])
    b2 = '; '.join(bk['bolum2'])
    if not b1 and not b2:
        out.append(f"{src.get('bekra', 'BEKRA Yönetmeliği')}: ürün, Bölüm 1 zararlılık kategorilerinin hiçbirinde "
                   'yer almaz ve Bölüm 2\'de adlandırılmış madde içermez.')
    else:
        out.append(f"{src.get('bekra', 'BEKRA Yönetmeliği')}: "
                   + (f'Bölüm 1 zararlılık kategorisi: {b1}. ' if b1 else '')
                   + (f'Bölüm 2 adlandırılmış madde: {b2}. ' if b2 else '')
                   + 'Alt/üst seviyeli kuruluş yükümlülükleri, kuruluşta bulunan toplam miktara göre işletmeci '
                     'tarafından değerlendirilmelidir.')
    # Ozon
    if oz['ozon']:
        out.append(f"{src.get('ozon')}: ürün listelenen maddeleri içerir — {', '.join(oz['ozon'])}. "
                   'Yönetmelik hükümleri uygulanır.')
    elif oz['ozon_olasi']:
        out.append(f"{src.get('ozon')}: {', '.join(oz['ozon_olasi'])} bileşeni listedeki izomer gruplarından "
                   'birine girebilir — KDU tarafından doğrulanmalıdır.')
    else:
        out.append(f"{src.get('ozon')}: ürün, bu eklerde listelenen maddeleri içermez.")
    # KOK
    if oz['kok']:
        out.append(f"{src.get('kok')}: ürün listelenen maddeleri içerir — {', '.join(oz['kok'])}. "
                   'Yönetmelik hükümleri uygulanır.')
    elif oz['kok_olasi']:
        out.append(f"{src.get('kok')}: {', '.join(oz['kok_olasi'])} bileşeni listedeki madde gruplarından birine "
                   'girebilir — KDU tarafından doğrulanmalıdır.')
    else:
        out.append(f"{src.get('kok')}: ürün, bu eklerde listelenen maddeleri içermez.")
    # ÖBK / PIC (Rotterdam Sözleşmesi)
    if src.get('pic'):
        if oz['pic']:
            out.append(f"{src['pic']}: ürün listelenen maddeleri içerir — {', '.join(oz['pic'])}. İhracatta Md.8 "
                       'ihracat bildirimi ve Md.10 yıllık miktar bildirimi (31 Mart) yükümlülükleri uygulanır.')
        elif oz['pic_olasi']:
            out.append(f"{src['pic']}: {', '.join(oz['pic_olasi'])} bileşeni listedeki bileşik gruplarından birine "
                       'girebilir — KDU tarafından doğrulanmalıdır.')
        else:
            out.append(f"{src['pic']}: ürün, bu eklerde listelenen maddeleri içermez.")
    return out
