"""
build_sea_ek6_tr.py — SEA Ek-6 Üçüncü Bölüm (uyumlaştırılmış sınıflandırma) tablosunu
data/sea_ek6_tr.json'a SIFIRDAN çevirir. Sonradan düzeltme betiği gerektirmez.

Kaynak : sds-knowledge/tr/7.5.19108-Ek.docx
         = mevzuat.gov.tr SEA ekleri (7.5.19108-Ek.doc, RG 10.12.2020 / 31330 Mükerrer),
           Word ile .docx'e kaydedilmiş hâli (eski .doc biçimi doğrudan okunamıyor).
Çıktı  : data/sea_ek6_tr.json   — CAS anahtarlı; ek anahtarlar:
           "<CAS>-AQ"     gaz/susuz kaydın çözelti varyantı (aynı liste no kökü, Not B)
           "<liste no>"   CAS'ı olmayan grup kayıtları (örn. 006-007-00-5)
           {"_alias": X}  aynı kayıttaki ek CAS numaraları
         data/sea_ek6_build_report.md — kaynaktaki eksik/uyumsuz satırlar ve yapılan tamamlamalar

Sınıf ↔ H kodu eşleşmesi sıraya göre DEĞİL, anlama göre yapılır (resmî tabloda sıra
kaymaları ve eksik hücreler var). Kaynakta eksik kalan sınıf/kod AB Annex VI kopyasındaki
(data/substance_db.json) aynı liste numarasından tamamlanır ve 'derived' ile işaretlenir.

Kullanım: python scripts/build_sea_ek6_tr.py [kaynak.docx]
"""

import json
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT      = Path(__file__).parent.parent
SRC_DEF   = ROOT / 'sds-knowledge' / 'tr' / '7.5.19108-Ek.docx'
OUT_PATH  = ROOT / 'data' / 'sea_ek6_tr.json'
EU_PATH   = ROOT / 'data' / 'substance_db.json'
REPORT    = ROOT / 'data' / 'sea_ek6_build_report.md'
SOURCE_LABEL = 'SEA Ek-6 (RG 10.12.2020/31330)'

NS  = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
IDX = re.compile(r'^[‘’\'"`\s]*(\d{3}-\d{3}-\d{2}-[\dX])\s*$')
CAS = re.compile(r'\b\d{2,7}-\d{2}-\d\b')
EC  = re.compile(r'\b\d{3}-\d{3}-\d\b')
HCODE = re.compile(r'H\d{3}[A-Za-z]{0,3}(?:\s*\([^)]*\))?')


# ─── Word tablosu okuma ──────────────────────────────────────────────────────

def _cell_lines(tc) -> list:
    out = []
    for p in tc.findall('.//w:p', NS):
        cur = []
        for el in p.iter():
            tag = el.tag.split('}')[-1]
            if tag == 't':
                cur.append(el.text or '')
            elif tag in ('br', 'cr'):
                out.append(''.join(cur)); cur = []
            elif tag == 'tab':
                cur.append(' ')
        out.append(''.join(cur))
    return [re.sub(r'\s+', ' ', l.replace('\xa0', ' ')).strip() for l in out if l.replace('\xa0', ' ').strip()]


def read_rows(src: Path) -> list:
    xml = zipfile.ZipFile(src).read('word/document.xml')
    root = ET.fromstring(xml)
    best, best_n = None, 0
    for tbl in root.findall('.//w:tbl', NS):
        n = 0
        for tr in tbl.findall('w:tr', NS):
            tc = tr.find('w:tc', NS)
            if tc is not None and IDX.match(' '.join(_cell_lines(tc))):
                n += 1
        if n > best_n:
            best, best_n = tbl, n
    rows = []
    for tr in best.findall('w:tr', NS):
        cells = [_cell_lines(tc) for tc in tr.findall('w:tc', NS)]
        if len(cells) == 12 and cells[0] and IDX.match(cells[0][0]):
            rows.append(cells)
    return rows


# ─── Sınıf adı: Türkçe kısaltma → CLP kanonik İngilizce ───────────────────────
# Kaynaktaki 69 yazım varyantına göre (nokta/boşluk farkları sıkıştırılmış anahtarla eşlenir).
# Sıra önemli: daha uzun/özel önekler önce.
_BASES = [
    ('akut',        'Acute Tox.'),
    ('alevkatı',    'Flam. Sol.'),
    ('alevsıvı',    'Flam. Liq.'),
    ('alevgaz',     'Flam. Gas'),
    ('asptok',      'Asp. Tox.'),
    ('bhottekr',    'STOT RE'),
    ('bhottek',     'STOT SE'),
    ('basınçgaz',   'Press. Gas'),
    ('ciltaşnd',    'Skin Corr.'),
    ('ciltasnd',    'Skin Corr.'),
    ('ciltha',      'Skin Sens.'),
    ('ciltta',      'Skin Irrit.'),
    ('ciltth',      'Skin Irrit.'),
    ('emz',         'Lact.'),
    ('gözhasar',    'Eye Dam.'),
    ('gözhsr',      'Eye Dam.'),
    ('göztah',      'Eye Irrit.'),
    ('gözthr',      'Eye Irrit.'),
    ('kans',        'Carc.'),
    ('karpat',      'Unst. Expl.'),
    ('kendısınan',  'Self-heat.'),
    ('kendtepgrn',  'Self-react.'),
    ('metaşnd',     'Met. Corr.'),
    ('muta',        'Muta.'),
    ('oksitgaz',    'Ox. Gas'),
    ('oksitkatı',   'Ox. Sol.'),
    ('oksitsıvı',   'Ox. Liq.'),
    ('orgperoksit', 'Org. Perox.'),
    ('ozon',        'Ozone'),
    ('pirokatı',    'Pyr. Sol.'),
    ('pirosıvı',    'Pyr. Liq.'),
    ('solnmhassas', 'Resp. Sens.'),
    ('sutepk',      'Water-react.'),
    ('sucul akut',  'Aquatic Acute'),
    ('sucul kronik','Aquatic Chronic'),
    ('ürmsistok',   'Repr.'),
    ('pat',         'Expl.'),
]
_NO_CAT = {'Press. Gas', 'Lact.', 'Unst. Expl.'}


def _tr_lower(s: str) -> str:
    return s.replace('İ', 'i').replace('I', 'ı').lower()


def classify_name(tr: str):
    """'Ürm.Sis.Tok. 1B' → ('Repr.', '1B'); tanınmazsa (None, None)."""
    low = _tr_lower(tr).strip()
    m = re.match(r'^pat\.?\s*(1\.\d)', low)
    if m:
        return 'Expl.', m.group(1)
    if low.startswith('sucul'):
        key = 'sucul ' + ('akut' if 'akut' in low else 'kronik')
        cat = re.search(r'(\d)\s*$', low)
        return dict(_BASES)[key], (cat.group(1) if cat else '')
    compact = re.sub(r'[\s.\-]', '', low)
    for pre, en in _BASES:
        if pre.startswith('sucul'):
            continue
        if compact.startswith(pre):
            rest = compact[len(pre):]
            rest = re.sub(r'^[a-zçğıöşü]*?(?=\d|$)', '', rest) if en not in ('Org. Perox.', 'Self-react.') else rest
            if en in ('Org. Perox.', 'Self-react.'):
                cat = rest[-1:].upper() if rest else ''
            else:
                m = re.search(r'(\d[a-c]?)$', rest)
                cat = m.group(1).upper() if m else ''
            if en == 'Ozone' and not cat:
                cat = '1'
            return en, ('' if en in _NO_CAT else cat)
    return None, None


def en_name(base: str, cat: str) -> str:
    return f'{base} {cat}'.strip() if cat else base


# Kaynakta birleşik yazılmış sınıflar: "Org. Peroksit E Cilt Tah. 2"
_SPLIT_AT = re.compile(r'(?<![Ss]ucul)\s+(?=(?:Cilt|Göz|Akut|Sucul|BHOT|Kans|Muta|Ürm|Solnm|Asp|Alev|Oksit)\b)')


def split_classes(lines: list) -> list:
    out = []
    for l in lines:
        out.extend(p.strip() for p in _SPLIT_AT.split(l) if p.strip())
    return out


# ─── Sınıf → izin verilen H kodları ──────────────────────────────────────────

def allowed_codes(base: str, cat: str) -> set:
    c = cat
    A = {
        'Acute Tox.':   {'1': {'H300', 'H310', 'H330'}, '2': {'H300', 'H310', 'H330'},
                         '3': {'H301', 'H311', 'H331'}, '4': {'H302', 'H312', 'H332'}},
        'STOT SE':      {'1': {'H370'}, '2': {'H371'}, '3': {'H335', 'H336'}},
        'STOT RE':      {'1': {'H372'}, '2': {'H373'}},
        'Aquatic Chronic': {'1': {'H410'}, '2': {'H411'}, '3': {'H412'}, '4': {'H413'}},
        'Flam. Gas':    {'1': {'H220'}, '2': {'H221'}},
        'Flam. Liq.':   {'1': {'H224'}, '2': {'H225'}, '3': {'H226'}},
        'Ox. Liq.':     {'1': {'H271'}, '2': {'H272'}, '3': {'H272'}},
        'Ox. Sol.':     {'1': {'H271'}, '2': {'H272'}, '3': {'H272'}},
        'Self-heat.':   {'1': {'H251'}, '2': {'H252'}},
        'Water-react.': {'1': {'H260'}, '2': {'H261'}, '3': {'H261'}},
        'Org. Perox.':  {'A': {'H240'}, 'B': {'H241'}, 'C': {'H242'}, 'D': {'H242'}, 'E': {'H242'}, 'F': {'H242'}},
        'Self-react.':  {'A': {'H240'}, 'B': {'H241'}, 'C': {'H242'}, 'D': {'H242'}, 'E': {'H242'}, 'F': {'H242'}},
        'Expl.':        {'1.1': {'H201'}, '1.2': {'H202'}, '1.3': {'H203'}, '1.4': {'H204'}, '1.5': {'H205'}},
    }
    if base in A:
        return A[base].get(c) or set().union(*A[base].values())
    single = {
        'Skin Corr.': {'H314'}, 'Skin Irrit.': {'H315'}, 'Eye Dam.': {'H318'}, 'Eye Irrit.': {'H319'},
        'Skin Sens.': {'H317'}, 'Resp. Sens.': {'H334'}, 'Asp. Tox.': {'H304'}, 'Aquatic Acute': {'H400'},
        'Ozone': {'H420'}, 'Flam. Sol.': {'H228'}, 'Press. Gas': {'H280', 'H281'}, 'Ox. Gas': {'H270'},
        'Pyr. Liq.': {'H250'}, 'Pyr. Sol.': {'H250'}, 'Met. Corr.': {'H290'}, 'Unst. Expl.': {'H200'},
        'Lact.': {'H362'},
    }
    if base in single:
        return single[base]
    if base == 'Muta.':
        return {'H341'} if c == '2' else ({'H340'} if c else {'H340', 'H341'})
    if base == 'Carc.':
        return {'H351'} if c == '2' else ({'H350'} if c else {'H350', 'H351'})
    if base == 'Repr.':
        return {'H361'} if c == '2' else ({'H360'} if c else {'H360', 'H361'})
    return set()


def code4(code: str) -> str:
    return code.strip()[:4].upper()


def fits(base, cat, code) -> bool:
    return code4(code) in allowed_codes(base, cat)


# ─── SCL / M / ATE sütunu ────────────────────────────────────────────────────

_NUM = r'(\d+(?:[.,]\d+)?)'
_RE_M   = re.compile(r'M\s*(?:\(\s*(akut|kronik|acute|chronic)\s*\))?\s*=\s*(\d[\d  .]*)', re.I)
_RE_ATE = re.compile(r'(oral|dermal|inhalation|ağızdan|ağız|soluma|solunum|cilt|deri)\s*[:;]\s*ATE\s*(?:\(\s*\))?\s*=\s*'
                     + _NUM + r'\s*(mg\s*/\s*kg|mg\s*/\s*L|ppm)(?:[^()\n]*?\(([^)]*)\))?', re.I)
_CLASS_START = (r'(?:Akut|Alev|Asp|BHOT|Basınç|Cilt|cilt|Emz|Göz|Kans|Kar\.|Kend|Met\.|Muta|Oksit|Org\.|'
                r'Ozon|Pat\.|Piro|Solnm|Su-|Sucul|sucul|Ürm)')
_RE_SCL = re.compile(r'(?:(?P<cls>' + _CLASS_START + r'[^;:]*?)\s*;?\s*)?'
                     r'(?P<h>EUH\d{3}|H\d{3}[A-Za-z]{0,3})\s*(?:\([^)]*\))?\s*:')


def _num(s: str) -> float:
    return float(s.replace(',', '.'))


def _parse_cond(s: str):
    t = s.replace(',', '.').replace('%', '').replace(' ', '').replace('>=', '≥').replace('<=', '≤')
    m = re.search(r'(\d+(?:\.\d+)?)≤C<(\d+(?:\.\d+)?)', t)
    if m:
        return 'range', _num(m.group(1)), _num(m.group(2))
    m = re.search(r'C[≥>](\d+(?:\.\d+)?)', t)
    if m:
        return '>=', _num(m.group(1)), None
    m = re.search(r'C[<≤](\d+(?:\.\d+)?)', t)
    if m:
        return '<', None, _num(m.group(1))
    return None


def parse_limits(lines: list, aq_acute1: bool, aq_chronic1: bool, issues: list):
    text = '\n'.join(lines)
    m_typed, m_bare, ate = {}, [], {}
    for m in _RE_M.finditer(text):
        val = int(re.sub(r'[\s  .]', '', m.group(2)))
        kind = (m.group(1) or '').lower()
        if kind in ('akut', 'acute'):
            m_typed['acute'] = val
        elif kind in ('kronik', 'chronic'):
            m_typed['chronic'] = val
        else:
            m_bare.append(val)
    m_factors = dict(m_typed)
    if m_bare and not m_typed:
        if len(m_bare) >= 2:
            m_factors = {'acute': m_bare[0], 'chronic': m_bare[1]}
        elif aq_acute1 and aq_chronic1:
            m_factors = {'acute': m_bare[0], 'chronic': m_bare[0]}
        elif aq_acute1:
            m_factors = {'acute': m_bare[0]}
        elif aq_chronic1:
            m_factors = {'chronic': m_bare[0]}
        else:
            m_factors = {'acute': m_bare[0], 'chronic': m_bare[0]}
            issues.append(f'M={m_bare[0]} var ama Sucul Akut/Kronik 1 sınıfı yok')

    route_map = {'ağızdan': 'oral', 'ağız': 'oral', 'soluma': 'inhalation', 'solunum': 'inhalation',
                 'cilt': 'dermal', 'deri': 'dermal'}
    for a in _RE_ATE.finditer(text):
        route = route_map.get(a.group(1).lower(), a.group(1).lower())
        e = {'value': _num(a.group(2)), 'unit': re.sub(r'\s', '', a.group(3)).replace('mg/l', 'mg/L')}
        if a.group(4):
            e['form'] = a.group(4).strip()
        ate[route] = e

    rest = re.sub(r'\s+', ' ', _RE_ATE.sub(' ', _RE_M.sub(' ', text)))
    scl, euh_limits = [], []
    starts = list(_RE_SCL.finditer(rest))
    for i, m in enumerate(starts):
        cond_txt = rest[m.end(): starts[i + 1].start() if i + 1 < len(starts) else len(rest)]
        cond = _parse_cond(cond_txt)
        code = m.group('h')
        if not cond:
            issues.append(f'Sınır değer okunamadı: {m.group(0).strip()} {cond_txt.strip()[:50]}')
            continue
        if code.startswith('EUH'):
            euh_limits.append({'code': code, 'op': cond[0], 'min': cond[1], 'max': cond[2], 'unit': '%'})
            continue
        cls_tr = (m.group('cls') or '').strip()
        base, cat = classify_name(cls_tr) if cls_tr else (None, None)
        scl.append({'h_code': code, 'class': cls_tr, 'class_en': en_name(base, cat) if base else '',
                    'op': cond[0], 'min': cond[1], 'max': cond[2], 'unit': '%'})
    leftover = re.sub(r'\s+', ' ', _RE_SCL.sub(' ', rest)).strip(' ;:')
    if not starts and re.search(r'\d', leftover):
        issues.append(f'Sınır değer sütununda okunamayan metin: {leftover[:80]}')
    return scl, m_factors, ate, euh_limits


# ─── Satır → kayıt ───────────────────────────────────────────────────────────

def load_eu() -> dict:
    eu = json.loads(EU_PATH.read_text(encoding='utf-8'))
    by_idx = {}
    for e in eu.values():
        if isinstance(e, dict) and e.get('index_no'):
            by_idx.setdefault(e['index_no'].strip(), e)
    return by_idx


_FAM = {}
for _codes, _f in [(('H200', 'H201', 'H202', 'H203', 'H204', 'H205'), 'expl'), (('H220', 'H221'), 'flamgas'),
                   (('H222', 'H223'), 'aerosol'), (('H224', 'H225', 'H226'), 'flamliq'), (('H228',), 'flamsol'),
                   (('H240', 'H241', 'H242'), 'selfreact'), (('H250',), 'pyr'), (('H251', 'H252'), 'selfheat'),
                   (('H260', 'H261'), 'waterreact'), (('H270',), 'oxgas'), (('H271', 'H272'), 'oxls'),
                   (('H280', 'H281'), 'press'), (('H290',), 'metcorr'), (('H300', 'H301', 'H302'), 'acute_o'),
                   (('H310', 'H311', 'H312'), 'acute_d'), (('H330', 'H331', 'H332'), 'acute_i'), (('H304',), 'asp'),
                   (('H314', 'H315'), 'skin'), (('H317',), 'skinsens'), (('H318', 'H319'), 'eye'),
                   (('H334',), 'respsens'), (('H335', 'H336', 'H370', 'H371'), 'stotse'), (('H372', 'H373'), 'stotre'),
                   (('H340', 'H341'), 'muta'), (('H350', 'H351'), 'carc'), (('H360', 'H361'), 'repr'),
                   (('H362',), 'lact'), (('H400',), 'aqa'), (('H410', 'H411', 'H412', 'H413'), 'aqc'), (('H420',), 'ozone')]:
    for _c in _codes:
        _FAM[_c] = _f

DEFAULT_CLASS = {
    'H200': 'Unst. Expl.', 'H201': 'Expl. 1.1', 'H202': 'Expl. 1.2', 'H203': 'Expl. 1.3', 'H204': 'Expl. 1.4',
    'H205': 'Expl. 1.5', 'H220': 'Flam. Gas 1', 'H221': 'Flam. Gas 2', 'H222': 'Aerosol 1', 'H223': 'Aerosol 2',
    'H224': 'Flam. Liq. 1', 'H225': 'Flam. Liq. 2', 'H226': 'Flam. Liq. 3', 'H228': 'Flam. Sol. 1',
    'H240': 'Self-react. A', 'H241': 'Self-react. B', 'H242': 'Self-react. C', 'H250': 'Pyr. Liq. 1',
    'H251': 'Self-heat. 1', 'H252': 'Self-heat. 2', 'H260': 'Water-react. 1', 'H261': 'Water-react. 2',
    'H270': 'Ox. Gas 1', 'H271': 'Ox. Liq. 1', 'H272': 'Ox. Liq. 2', 'H280': 'Press. Gas', 'H281': 'Press. Gas',
    'H290': 'Met. Corr. 1', 'H300': 'Acute Tox. 2', 'H301': 'Acute Tox. 3', 'H302': 'Acute Tox. 4',
    'H310': 'Acute Tox. 1', 'H311': 'Acute Tox. 3', 'H312': 'Acute Tox. 4', 'H330': 'Acute Tox. 2',
    'H331': 'Acute Tox. 3', 'H332': 'Acute Tox. 4', 'H304': 'Asp. Tox. 1', 'H314': 'Skin Corr. 1',
    'H315': 'Skin Irrit. 2', 'H317': 'Skin Sens. 1', 'H318': 'Eye Dam. 1', 'H319': 'Eye Irrit. 2',
    'H334': 'Resp. Sens. 1', 'H335': 'STOT SE 3', 'H336': 'STOT SE 3', 'H340': 'Muta. 1B', 'H341': 'Muta. 2',
    'H350': 'Carc. 1B', 'H351': 'Carc. 2', 'H360': 'Repr. 1B', 'H361': 'Repr. 2', 'H362': 'Lact.',
    'H370': 'STOT SE 1', 'H371': 'STOT SE 2', 'H372': 'STOT RE 1', 'H373': 'STOT RE 2',
    'H400': 'Aquatic Acute 1', 'H410': 'Aquatic Chronic 1', 'H411': 'Aquatic Chronic 2',
    'H412': 'Aquatic Chronic 3', 'H413': 'Aquatic Chronic 4', 'H420': 'Ozone 1',
}


def build_classification(idx: str, class_lines: list, code_text: str, eu_by_idx: dict, issues: list) -> list:
    """
    Resmî tabloda sınıf sütunu ile H kodu sütunu bazen uyuşmaz (yazım hatası, eksik hücre, sıra kayması).
    1) Sınıf ↔ kod, kategori dahil tam uyum.
    2) Kodu olmayan sınıf:
       a) Basınçlı gaz → H280 (tabloda kod yazılmaz, Not U)
       b) Aynı tehlike ailesinden artan kod var → çelişki: iki kaynağın (sınıf / kod / AB kaydı)
          hemfikir olduğu taraf kazanır; AB kaydı yoksa koda güvenilir
       c) AB kaydında sınıfın kodu var → kaynakta kod eksik, AB'den tamamla
       d) AB kaydı yok, kod tek ve artan kod yok → sınıftan türet
    3) Kalan sınıf/kod çiftleri 1:1 → (2b) kuralı.
    4) Artan kodlar: 2c'de AB'den tamamlanan sınıf varsa ve kod AB'de yoksa → yazım hatası, atılır;
       aksi hâlde resmî metinde yazdığı için tutulur (AB'de yoksa "kontrol edin" notuyla).
    Kaynağa uymayan her satır 'derived' ile işaretlenir ve rapora yazılır.
    """
    classes = []
    for tr in split_classes(class_lines):
        base, cat = classify_name(tr)
        if not base:
            issues.append(f'Tanınmayan sınıf adı: {tr!r}')
        classes.append({'tr': tr, 'base': base, 'cat': cat, 'code': None, 'class_en': None, 'derived': None})
    codes = [re.sub(r'\s+', ' ', c).strip() for c in HCODE.findall(code_text)]

    used = set()
    for i, code in enumerate(codes):                     # 1
        slot = next((c for c in classes if c['code'] is None and c['base'] and fits(c['base'], c['cat'], code)), None)
        if slot:
            slot['code'] = code
            used.add(i)
    left = [code for i, code in enumerate(codes) if i not in used]

    eu_rec = eu_by_idx.get(idx)
    eu_cls = [(x.get('class', ''), x.get('h_code', '')) for x in (eu_rec or {}).get('classification') or []]
    eu4 = {code4(h) for _, h in eu_cls}

    def eu_class_for(code):
        return next((cl for cl, h in eu_cls if code4(h) == code4(code)), None)

    def opts_of(c):
        return allowed_codes(c['base'], c['cat']) if c['base'] else set()

    def resolve(c, code, why):
        left.remove(code)
        eu_code_cls = next((h for _, h in eu_cls if code4(h) in opts_of(c)), None) if eu_rec else None
        if eu_rec and code4(code) not in eu4 and eu_code_cls:
            c['code'] = eu_code_cls
            c['derived'] = (f"H kodu yazım hatası (kaynak: \"{c['tr']}\" / {code}) — sınıf sütunu ve "
                            f"AB Annex VI {eu_code_cls} diyor")
            issues.append(f"\"{c['tr']}\" ↔ {code} çelişkili → {code} yazım hatası, {c['tr']} {eu_code_cls} kullanıldı")
            return
        c['code'] = code
        c['class_en'] = eu_class_for(code) or DEFAULT_CLASS.get(code4(code), c['tr'])
        basis = 'AB Annex VI da aynı kodu veriyor' if code4(code) in eu4 else (
                'AB kaydında yok — kontrol edin' if eu_rec else 'AB kaydı yok, koda güvenildi')
        c['derived'] = f"Sınıf adı H koduyla çelişiyor (kaynak: \"{c['tr']}\" / {code}) — {why}; {basis}"
        issues.append(f"\"{c['tr']}\" ↔ {code} çelişkili → {c['class_en']} {code} ({basis})")

    omitted_from_eu = []
    mismatch = []
    for c in classes:                                    # 2
        if c['code']:
            continue
        opts = opts_of(c)
        if c['base'] == 'Press. Gas':                    # 2a
            c['code'] = 'H280'
            c['derived'] = ('Basınçlı gaz: tabloda kod yok (Not U) — H280 varsayıldı; '
                            'soğutulmuş sıvılaştırılmış gaz ise H281')
            continue
        fams = {_FAM.get(x) for x in opts}
        same_fam = next((k for k in left if _FAM.get(code4(k)) in fams), None)
        if same_fam:                                     # 2b
            resolve(c, same_fam, 'aynı tehlike ailesi')
            continue
        eu_code = next((h for _, h in eu_cls if code4(h) in opts), None) if eu_rec else None
        if eu_code:                                      # 2c
            c['code'], c['derived'] = eu_code, "H kodu kaynakta eksik — AB Annex VI aynı liste no'dan"
            issues.append(f"{c['tr']}: H kodu eksik → {eu_code} (AB Annex VI)")
            omitted_from_eu.append(c)
        elif not eu_rec and len(opts) == 1 and not left:  # 2d
            c['code'], c['derived'] = next(iter(opts)), 'H kodu kaynakta eksik — sınıftan türetildi'
            issues.append(f"{c['tr']}: H kodu eksik → {c['code']} (sınıftan)")
        else:
            mismatch.append(c)

    if mismatch and len(mismatch) == len(left):          # 3
        for c, code in zip(list(mismatch), list(left)):
            resolve(c, code, 'eşleşmeyen tek sınıf/kod çifti')
        mismatch = []

    out = []
    for c in classes:
        if c['code'] is None:
            opts = opts_of(c)
            if len(opts) == 1:
                c['code'], c['derived'] = next(iter(opts)), 'H kodu kaynakta eksik — sınıftan türetildi'
                issues.append(f"{c['tr']}: H kodu eksik → {c['code']} (sınıftan)")
            else:
                issues.append(f"{c['tr']}: H kodu eksik ve türetilemedi — satır ATLANDI")
                continue
        e = {'class': c['tr'],
             'class_en': c['class_en'] or (en_name(c['base'], c['cat']) if c['base'] else c['tr']),
             'h_code': c['code']}
        if c['derived']:
            e['derived'] = c['derived']
        out.append(e)

    for code in left:                                    # 4
        if eu_rec and code4(code) not in eu4 and omitted_from_eu:
            c = omitted_from_eu.pop(0)
            issues.append(f"{code}: sınıf sütununda ve AB'de karşılığı yok; {c['tr']} için AB'den "
                          f"{c['code']} tamamlandı → {code} yazım hatası sayılıp atıldı")
            continue
        cls = eu_class_for(code) or DEFAULT_CLASS.get(code4(code))
        if not cls:
            issues.append(f'{code}: sınıfı belirlenemedi — ATLANDI')
            continue
        basis = 'sınıf AB Annex VI aynı liste no' if code4(code) in eu4 else (
                'sınıf H kodundan; AB kaydında yok — kontrol edin' if eu_rec else 'sınıf H kodundan')
        out.append({'class': cls, 'class_en': cls, 'h_code': code,
                    'derived': f'Sınıf sütununda karşılığı yok — {basis}'})
        issues.append(f'{code}: sınıf eksik → {cls} ({basis})')
    return out


def build(src: Path):
    rows = read_rows(src)
    eu_by_idx = load_eu()
    db, report = {}, []
    prev = None          # (index_no, primary_key)
    dup_cas = []

    for r in rows:
        idx = IDX.match(r[0][0]).group(1)
        issues = []
        name_en = ' '.join(r[1]).strip()
        name_tr = ' '.join(r[2]).strip() or name_en
        notes = [t for t in re.split(r'[,\s]+', ' '.join(r[3])) if t]
        ecs = EC.findall(' '.join(r[4]))
        cas_list = list(dict.fromkeys(CAS.findall(re.sub(r'\[\d+\]', ' ', ' '.join(r[5])))))
        classification = build_classification(idx, r[6], ' '.join(r[7]), eu_by_idx, issues)
        aq_a1 = any(c['class_en'] == 'Aquatic Acute 1' for c in classification)
        aq_c1 = any(c['class_en'] == 'Aquatic Chronic 1' for c in classification)
        scl, m_factors, ate, euh_limits = parse_limits(r[11], aq_a1, aq_c1, issues)
        euh = list(dict.fromkeys(re.findall(r'EUH\d{3}A?', ' '.join(r[10]))))

        entry = {
            'index_no': idx, 'names': [name_tr], 'name_en': name_en,
            'ec_no': ecs[0] if ecs else '', 'cas': cas_list[0] if cas_list else '',
            'synonyms': cas_list[1:], 'lang': 'tr', 'atp': SOURCE_LABEL, 'notes': notes,
            'euh_codes': euh, 'classification': classification,
            'scl_limits': scl, 'm_factors': m_factors, 'ate': ate,
        }
        if len(ecs) > 1:
            entry['ec_list'] = ecs
        if euh_limits:
            entry['euh_limits'] = euh_limits

        # Çözelti varyantı: önceki kaydın aynı liste no kökü (NNN-NNN-01-x) ya da
        # aynı CAS + Not B (örn. 009-002 hidrojen florür → 009-003 hidroflorik asit)
        # Not B şart: aynı kökteki Not B'siz varyantlar (örn. bütan / ≥%0,1 bütadienli bütan)
        # çözelti değildir — onlar aşağıda aynı-CAS kuralıyla liste no anahtarına düşer.
        variant_of = None
        if prev and prev[1] and 'B' in notes:
            main_cas = db[prev[1]].get('cas')
            same_root = idx[:7] == prev[0][:7] and idx != prev[0]
            same_cas  = bool(cas_list) and cas_list[0] == main_cas
            if same_root or same_cas:
                variant_of = prev[1]
        if variant_of and variant_of + '-AQ' in db:
            issues.append(f'{variant_of} için ikinci çözelti varyantı — liste no anahtarıyla saklandı')
            db[idx] = entry
            variant_of, key = None, idx
        elif variant_of:
            key = variant_of + '-AQ'
            entry['form'] = 'solution'
            main = db[variant_of]
            main['note_b_pair'] = True
            if any(c['class_en'].startswith(('Press. Gas', 'Flam. Gas', 'Ox. Gas')) for c in main['classification']):
                main['form'] = 'gas'
            if cas_list and cas_list[0] != main.get('cas') and cas_list[0] not in db:
                db[cas_list[0]] = entry                    # kendi CAS'ı var (örn. amonyak çözeltisi)
                db[key] = {'_alias': cas_list[0]}
            else:
                db[key] = entry
        elif cas_list:
            key = cas_list[0]
            if key in db and '_alias' not in db[key]:
                dup_cas.append((idx, key, db[key]['index_no']))
                key = idx                                   # aynı CAS farklı liste no → liste no ile sakla
            db[key] = entry
            for syn in cas_list[1:]:
                if syn not in db:
                    db[syn] = {'_alias': key}
        else:
            key = idx                                       # CAS'sız grup kaydı
            db[key] = entry

        prev = (idx, key if not key.endswith('-AQ') else prev[1])
        if issues:
            report.append((idx, entry['cas'] or '—', name_en[:60], issues))

    return db, report, dup_cas, len(rows)


def write_report(report, dup_cas, n_rows, db):
    real = [e for e in db.values() if '_alias' not in e]
    lines = [
        '# SEA Ek-6 dönüştürme raporu', '',
        f'Kaynak: {SOURCE_LABEL} — {n_rows} satır', '',
        f'- Kayıt: {len(real)} | alias: {sum(1 for e in db.values() if "_alias" in e)} '
        f'| CAS\'sız grup kaydı: {sum(1 for e in real if not e["cas"])} '
        f'| çözelti varyantı (-AQ): {sum(1 for k in db if k.endswith("-AQ"))}',
        f'- M-faktörü: {sum(1 for e in real if e["m_factors"])} | SCL: {sum(1 for e in real if e["scl_limits"])} '
        f'| ATE: {sum(1 for e in real if e["ate"])} | EUH: {sum(1 for e in real if e["euh_codes"])}',
        f'- Kaynakta eksik olup tamamlanan sınıflandırma satırı: '
        f'{sum(1 for e in real for c in e["classification"] if c.get("derived"))}', '',
        '## Kaynaktaki sorunlu satırlar', '',
    ]
    for idx, cas, name, issues in report:
        lines.append(f'- **{idx}** ({cas}) {name}')
        lines.extend(f'  - {i}' for i in issues)
    if dup_cas:
        lines += ['', '## Aynı CAS birden fazla liste numarasında', '']
        lines += [f'- {idx}: CAS {cas} zaten {first} kaydında — liste no anahtarıyla saklandı' for idx, cas, first in dup_cas]
    REPORT.write_text('\n'.join(lines) + '\n', encoding='utf-8')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else SRC_DEF
    db, report, dup_cas, n = build(src)
    OUT_PATH.write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding='utf-8')
    write_report(report, dup_cas, n, db)
    real = [e for e in db.values() if '_alias' not in e]
    print(f'{n} satır → {len(real)} kayıt, {len(db)} anahtar | sorunlu satır: {len(report)} | çift CAS: {len(dup_cas)}')
    print(f'Yazıldı: {OUT_PATH}\nRapor : {REPORT}')
