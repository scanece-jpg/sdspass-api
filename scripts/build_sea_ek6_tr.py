"""
build_sea_ek6_tr.py — SEA Ek-6 Word belgesini TR substance_db formatına çevirir.

Giriş : sds-knowledge/sea_ek6_l-ste_15062020-20200618142549.docx
Çıktı : data/sea_ek6_tr.json  (CAS anahtarlı, substance_db.json ile aynı şema)
"""

import json
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

DOCX_PATH = Path(__file__).parent.parent / "sds-knowledge" / "tr" / "sea_ek6_l-ste_15062020-20200618142549.docx"
OUT_PATH  = Path(__file__).parent.parent / "data" / "sea_ek6_tr.json"

NS = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}

_VALID_CAS = re.compile(r'\d{2,7}-\d{2}-\d\b')


# ---------------------------------------------------------------------------
# XML okuma
# ---------------------------------------------------------------------------

def _load_xml() -> str:
    with zipfile.ZipFile(DOCX_PATH) as z:
        return z.read("word/document.xml").decode("utf-8")


def _cell_lines(cell) -> list[str]:
    """
    Hücredeki metni satırlara böler.
    <w:p> paragraf sınırları ve <w:br/> yumuşak satır kırılmaları ikisi de
    ayrı satır sayılır — bu olmadan multi-class hücreler tek parçada gelir.
    """
    lines = []
    for p in cell.findall('.//w:p', NS):
        current = []
        for r in p.findall('w:r', NS):
            for child in r:
                local = child.tag.split('}')[-1]
                if local == 'br':
                    text = ''.join(current).strip()
                    if text:
                        lines.append(text)
                    current = []
                elif local == 't':
                    current.append(child.text or '')
        text = ''.join(current).strip()
        if text:
            lines.append(text)
    return lines


def _cell_text(cell) -> str:
    return '\n'.join(_cell_lines(cell))


# ---------------------------------------------------------------------------
# CAS parse
# ---------------------------------------------------------------------------

def _parse_cas_raw(cas_raw: str) -> list[str]:
    """
    Her iki CAS formatını destekler:
      - Satır kırılmalı: '7439-93-2\n1234-56-7'
      - Aynı satırda [N] etiketli: '15120-21-5[1]7632-04-4[2]'
    [N] etiketlerini kaldır, tüm geçerli CAS kalıplarını bul.
    """
    cleaned = re.sub(r'\[\d+\]', ' ', cas_raw)
    return _VALID_CAS.findall(cleaned)


# ---------------------------------------------------------------------------
# SCL parse
# ---------------------------------------------------------------------------

_RE_M   = re.compile(r'M(?:\((\w+)\))?\s*=\s*(\d+)', re.IGNORECASE)
_RE_ATE = re.compile(
    r'(oral|dermal|inhalation|ağızdan|soluma|solunum|cilt|deri)\s*:\s*ATE\s*=\s*([\d,\.]+)\s*(mg/kg|mg/L|ppm)'
    r'(?:\s*(?:bw|body\s*weight|va|v\.a\.|vücut\s*ağırlığı))?'
    r'(?:\s*\((.+?)\))?',
    re.IGNORECASE,
)
_RE_GE    = re.compile(r'C\s*[≥>=]+\s*%?\s*([\d,\.]+)\s*%?')
_RE_RANGE = re.compile(r'([\d,\.]+)\s*[\xa0 ]*%\s*[≤<=]+\s*C\s*[<≤]\s*([\d,\.]+)')
_RE_LT    = re.compile(r'C\s*[<≤]+\s*%?\s*([\d,\.]+)\s*%?')


def _num(s: str) -> float:
    return float(s.replace(',', '.'))


def _split_scl_entries(raw: str) -> list[str]:
    raw = raw.replace('\xa0', ' ').strip()
    split = re.sub(r'(?<=[\d%])\s*(?=[A-ZÇŞĞÜÖİ][a-zçşğüöıA-ZÇŞĞÜÖİ])', '\n', raw)
    return [l.strip() for l in split.split('\n') if l.strip()]


def _parse_scl(raw: str):
    scl_limits  = []
    m_factors   = {}
    ate         = {}
    bare_m_vals = []

    # Ön-işleme: "route:\nATE=..." → "route: ATE=..." (TR ve EN rota adları)
    raw = re.sub(
        r'(oral|dermal|inhalation|ağızdan|soluma|solunum|cilt|deri)\s*:\s*\n\s*ATE',
        r'\1: ATE',
        raw,
        flags=re.IGNORECASE,
    )
    # "ATE ()=..." veya "ATE=..." arası boşluk/parantez varyantlarını normalize et
    raw = re.sub(r'ATE\s*(?:\(\))?\s*=\s*', 'ATE=', raw)
    # Birim ile değer arasındaki boşluğu sağla: "5mg/kg" → "5 mg/kg"
    raw = re.sub(r'(\d)(mg/)', r'\1 \2', raw)

    for line in _split_scl_entries(raw):
        m = _RE_M.search(line)
        if m:
            mtype = m.group(1)
            mval  = int(m.group(2))
            if mtype:
                m_factors[mtype.lower()] = mval
            else:
                bare_m_vals.append(mval)
            continue

        a = _RE_ATE.search(line)
        if a:
            _TR_ROUTE = {
                'ağızdan': 'oral', 'soluma': 'inhalation', 'solunum': 'inhalation',
                'cilt': 'dermal', 'deri': 'dermal',
            }
            route = _TR_ROUTE.get(a.group(1).lower(), a.group(1).lower())
            entry = {'value': _num(a.group(2)), 'unit': a.group(3)}
            if a.group(4):
                entry['form'] = a.group(4)
            ate[route] = entry
            continue

        cm = re.match(r'^(.+?);\s*(H\d+\w*)\s*:\s*(.+)$', line)
        if not cm:
            continue
        cls_name = cm.group(1).strip().rstrip('*').strip()
        h_code   = cm.group(2).strip().rstrip('*').strip()
        conc_str = cm.group(3)

        rm = _RE_RANGE.search(conc_str)
        if rm:
            scl_limits.append({'h_code': h_code, 'class': cls_name,
                                'op': 'range', 'min': _num(rm.group(1)),
                                'max': _num(rm.group(2)), 'unit': '%'})
            continue
        gm = _RE_GE.search(conc_str)
        if gm:
            scl_limits.append({'h_code': h_code, 'class': cls_name,
                                'op': '>=', 'min': _num(gm.group(1)),
                                'max': None, 'unit': '%'})
            continue
        lm = _RE_LT.search(conc_str)
        if lm:
            scl_limits.append({'h_code': h_code, 'class': cls_name,
                                'op': '<', 'min': None,
                                'max': _num(lm.group(1)), 'unit': '%'})

    # Tipisiz M değerleri: tek → acute=chronic; iki → 1.akut 2.kronik
    if bare_m_vals and 'acute' not in m_factors and 'chronic' not in m_factors:
        m_factors['acute']   = bare_m_vals[0]
        m_factors['chronic'] = bare_m_vals[1] if len(bare_m_vals) > 1 else bare_m_vals[0]

    return scl_limits, m_factors, ate


# ---------------------------------------------------------------------------
# Sınıflandırma parse
# ---------------------------------------------------------------------------

_PRESS_GAS_TR = {'Basınç Gaz', 'Press. Gas'}

def _parse_classification(class_raw: str, hcode_raw: str) -> list[dict]:
    classes = [l.strip() for l in class_raw.split('\n') if l.strip()]
    hcodes  = [l.strip() for l in hcode_raw.split('\n') if l.strip()]

    # SEA Ek-6 Word belgesinde "Basınç Gaz" için H kodu sütununda H280
    # yazılmaz (standart sayılır). Press. Gas pozisyonuna H280 enjekte et.
    adjusted = list(hcodes)
    for i, cls in enumerate(classes):
        cls_clean = cls.rstrip('* ').strip()
        if cls_clean in _PRESS_GAS_TR and i <= len(adjusted):
            existing = adjusted[i].rstrip('* ').strip() if i < len(adjusted) else ''
            if existing not in ('H280', 'H281'):
                adjusted.insert(i, 'H280')

    length  = max(len(classes), len(adjusted))
    result  = []
    for i in range(length):
        cls = classes[i] if i < len(classes) else ''
        hc  = adjusted[i] if i < len(adjusted) else ''
        cls_ast = 1 if cls.endswith('*') else 0
        hc_ast  = len(re.search(r'\*+$', hc).group()) if re.search(r'\*+$', hc) else 0
        cls = cls.rstrip('* ').strip()
        hc  = hc.rstrip('* ').strip()
        if cls and hc:
            entry = {'class': cls, 'h_code': hc}
            if cls_ast: entry['class_asterisk'] = cls_ast
            if hc_ast:  entry['h_code_asterisk'] = hc_ast
            result.append(entry)
    return result


# ---------------------------------------------------------------------------
# Notlar parse
# ---------------------------------------------------------------------------

def _parse_notes(notes_raw: str) -> list[str]:
    """
    Virgül veya boşlukla ayrılmış notları ayrı token'lara böler.
    'J M' → ['J', 'M'],  'A, B' → ['A', 'B']
    """
    if not notes_raw:
        return []
    return [t for t in re.split(r'[,\s]+', notes_raw.strip()) if t]


# ---------------------------------------------------------------------------
# Ana parse
# ---------------------------------------------------------------------------

def parse(xml_str: str) -> dict:
    root   = ET.fromstring(xml_str)
    tables = root.findall('.//w:tbl', NS)
    if not tables:
        raise ValueError("Tablo bulunamadı")

    rows = tables[0].findall('w:tr', NS)
    db   = {}
    _last_cas = None  # Not B çözelti kayıtları için bir önceki CAS'ı hatırla

    for row in rows[2:]:
        cells = row.findall('w:tc', NS)
        if len(cells) < 9:
            continue

        index_no  = _cell_text(cells[0]).strip()
        name_en   = _cell_text(cells[1]).strip()
        name_tr   = _cell_text(cells[2]).strip()
        notes_raw = _cell_text(cells[3]).strip()
        ec_no     = _cell_text(cells[4]).strip()
        cas_raw   = _cell_text(cells[5]).strip()

        if len(cells) >= 12:
            class_raw = _cell_text(cells[6])
            hcode_raw = _cell_text(cells[7])
            euh_raw   = _cell_text(cells[10])
            scl_raw   = _cell_text(cells[11])
        elif len(cells) >= 9:
            class_raw = _cell_text(cells[6])
            hcode_raw = _cell_text(cells[7]) if len(cells) > 7 else ''
            euh_raw   = ''
            scl_raw   = _cell_text(cells[8]) if len(cells) > 8 else ''
        else:
            continue

        notes = _parse_notes(notes_raw)

        # Not B çözelti kayıtları: CAS = "-", bir önceki maddenin CAS + "-AQ" kullan
        if not cas_raw or cas_raw == '-':
            if 'B' in notes and _last_cas:
                primary_cas = _last_cas + '-AQ'
                synonyms    = []
            else:
                continue
        else:
            cas_list = _parse_cas_raw(cas_raw)
            if not cas_list:
                continue
            primary_cas = cas_list[0]
            synonyms    = cas_list[1:]
            _last_cas   = primary_cas

        euh_codes      = re.findall(r'EUH\d+\w*', euh_raw)
        classification = _parse_classification(class_raw, hcode_raw)
        scl_limits, m_factors, ate = _parse_scl(scl_raw)

        names_tr = [n.strip() for n in name_tr.split('\n') if n.strip()] or [name_en]

        entry = {
            'index_no'      : index_no,
            'names'         : names_tr,
            'name_en'       : name_en,
            'ec_no'         : ec_no,
            'cas'           : primary_cas,
            'synonyms'      : synonyms,
            'lang'          : 'tr',
            'notes'         : notes,
            'euh_codes'     : euh_codes,
            'classification': classification,
            'scl_limits'    : scl_limits,
            'm_factors'     : m_factors,
            'ate'           : ate,
        }

        if primary_cas not in db:
            db[primary_cas] = entry

        for syn in synonyms:
            if syn and syn not in db:
                db[syn] = {'_alias': primary_cas}

    return db


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    print("Word dosyası okunuyor...")
    xml_str = _load_xml()
    print(f"  {len(xml_str)//1024} KB")

    print("Parse ediliyor...")
    db = parse(xml_str)

    real    = sum(1 for v in db.values() if '_alias' not in v)
    alias   = sum(1 for v in db.values() if '_alias' in v)
    has_scl = sum(1 for v in db.values() if '_alias' not in v and v.get('scl_limits'))
    has_m   = sum(1 for v in db.values() if '_alias' not in v and v.get('m_factors'))
    has_euh = sum(1 for v in db.values() if '_alias' not in v and v.get('euh_codes'))

    print(f"  Gerçek madde : {real}")
    print(f"  Alias        : {alias}")
    print(f"  SCL verisi   : {has_scl}")
    print(f"  M-faktör     : {has_m}")
    print(f"  EUH kodu     : {has_euh}")

    OUT_PATH.write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"\nKaydedildi: {OUT_PATH}")

    print("\n--- Örnek (lityum 7439-93-2) ---")
    if '7439-93-2' in db:
        print(json.dumps(db['7439-93-2'], ensure_ascii=False, indent=2))
