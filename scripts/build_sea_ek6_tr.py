"""
build_sea_ek6_tr.py — SEA Ek-6 Word belgesini TR substance_db formatına çevirir.

Giriş : sea ek6.docx (Word tablosu)
Çıktı : data/sea_ek6_tr.json  (CAS anahtarlı, substance_db.json ile aynı şema)
"""

import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

DOCX_PATH = Path(r"C:\Users\user\Documents\sea ekleri\sea ekleri excel\sea ek6.docx")
XML_PATH  = Path(__file__).parent / "sea_ek6_raw.xml"
OUT_PATH  = Path(__file__).parent.parent / "data" / "sea_ek6_tr.json"

NS = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}


# ---------------------------------------------------------------------------
# XML okuma
# ---------------------------------------------------------------------------

def _extract_xml():
    import zipfile
    with zipfile.ZipFile(DOCX_PATH) as z:
        return z.read("word/document.xml").decode("utf-8")


def _cell_lines(cell) -> list[str]:
    lines = []
    for p in cell.findall('.//w:p', NS):
        line = ''.join(t.text or '' for t in p.findall('.//w:t', NS)).strip()
        if line:
            lines.append(line)
    return lines


def _cell_text(cell) -> str:
    return '\n'.join(_cell_lines(cell))


# ---------------------------------------------------------------------------
# SCL parse (TR formatı — aynı semboller ≥ < –)
# ---------------------------------------------------------------------------

_RE_M   = re.compile(r'M(?:\((\w+)\))?=(\d+)', re.IGNORECASE)
_RE_ATE = re.compile(
    r'(oral|dermal|inhalation|ağızdan|soluma)\s*:\s*ATE\s*=\s*([\d,\.]+)\s*(mg/kg|mg/L|ppm)',
    re.IGNORECASE,
)
# SCL satırı: "ClassName; Hxxx: ..." — satır sınırı olarak kullan
_RE_SCL_ENTRY = re.compile(r'(.+?);\s*(H\d+\w*)\s*:\s*(.+?)(?=\S+;\s*H\d+|$)', re.DOTALL)
# Konsantrasyon değerleri
_RE_GE    = re.compile(r'C\s*[≥>=]+\s*%?\s*([\d,\.]+)\s*%?')
_RE_RANGE = re.compile(r'([\d,\.]+)\s*[\xa0 ]*%\s*[≤<=]+\s*C\s*[<≤]\s*([\d,\.]+)')
_RE_LT    = re.compile(r'C\s*[<≤]+\s*%?\s*([\d,\.]+)\s*%?')


def _num(s: str) -> float:
    return float(s.replace(',', '.'))


def _split_scl_entries(raw: str) -> list[str]:
    """Birleşik SCL metnini noktalı virgül+H-kodu sınırından böler."""
    raw = raw.replace('\xa0', ' ').strip()
    # TR belgede: "...%5Cilt..." veya "...5 %Cilt..." — rakam/% sonrası büyük harf yeni giriş
    split = re.sub(r'(?<=[\d%])\s*(?=[A-ZÇŞĞÜÖİ][a-zçşğüöıA-ZÇŞĞÜÖİ])', '\n', raw)
    return [l.strip() for l in split.split('\n') if l.strip()]


def _parse_scl(raw: str):
    scl_limits, m_factors, ate = [], {}, {}
    raw = raw.replace('\xa0', ' ')

    for line in _split_scl_entries(raw):
        m = _RE_M.search(line)
        if m:
            mtype = (m.group(1) or 'default').lower()
            m_factors[mtype] = int(m.group(2))
            continue
        a = _RE_ATE.search(line)
        if a:
            ate[a.group(1).lower()] = {'value': _num(a.group(2)), 'unit': a.group(3)}
            continue

        # Sınıf adı ve H-kodu bul
        cm = re.match(r'^(.+?);\s*(H\d+\w*)\s*:\s*(.+)$', line)
        if not cm:
            continue
        cls_name = cm.group(1).strip().rstrip('*').strip()
        h_code   = cm.group(2).strip().rstrip('*').strip()
        conc_str = cm.group(3)

        rm = _RE_RANGE.search(conc_str)
        if rm:
            scl_limits.append({'h_code': h_code, 'class': cls_name,
                                'op': 'range', 'min': _num(rm.group(1)), 'max': _num(rm.group(2)), 'unit': '%'})
            continue
        gm = _RE_GE.search(conc_str)
        if gm:
            scl_limits.append({'h_code': h_code, 'class': cls_name,
                                'op': '>=', 'min': _num(gm.group(1)), 'max': None, 'unit': '%'})
            continue
        lm = _RE_LT.search(conc_str)
        if lm:
            scl_limits.append({'h_code': h_code, 'class': cls_name,
                                'op': '<', 'min': None, 'max': _num(lm.group(1)), 'unit': '%'})

    return scl_limits, m_factors, ate


# ---------------------------------------------------------------------------
# Sınıflandırma parse
# ---------------------------------------------------------------------------

def _parse_classification(class_raw: str, hcode_raw: str) -> list[dict]:
    classes = [l.strip() for l in class_raw.split('\n') if l.strip()]
    hcodes  = [l.strip() for l in hcode_raw.split('\n') if l.strip()]
    length  = max(len(classes), len(hcodes))
    result  = []
    for i in range(length):
        cls = classes[i] if i < len(classes) else ''
        hc  = hcodes[i]  if i < len(hcodes)  else ''
        # asterisk
        cls_ast = 1 if cls.endswith('*') else 0
        hc_ast  = len(re.search(r'\*+$', hc).group()) if re.search(r'\*+$', hc) else 0
        cls = cls.rstrip('* ').strip()
        hc  = hc.rstrip('* ').strip()
        if cls or hc:
            entry = {'class': cls, 'h_code': hc}
            if cls_ast: entry['class_asterisk'] = cls_ast
            if hc_ast:  entry['h_code_asterisk'] = hc_ast
            result.append(entry)
    return result


# ---------------------------------------------------------------------------
# Ana parse
# ---------------------------------------------------------------------------

def parse(xml_str: str) -> dict:
    root = ET.fromstring(xml_str)
    tables = root.findall('.//w:tbl', NS)
    if not tables:
        raise ValueError("Tablo bulunamadı")

    rows = tables[0].findall('w:tr', NS)
    db   = {}

    for row in rows[2:]:  # İlk 2 satır başlık
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
            scl_raw   = _cell_text(cells[11])
        else:
            class_raw = _cell_text(cells[6])
            hcode_raw = _cell_text(cells[7]) if len(cells) > 7 else ''
            scl_raw   = _cell_text(cells[8]) if len(cells) > 8 else ''

        if not cas_raw or cas_raw == '-':
            continue

        # Çoklu CAS
        cas_list = [re.sub(r'\s*\[\d+\]', '', c).strip()
                    for c in cas_raw.split('\n') if re.sub(r'\s*\[\d+\]', '', c).strip() not in ('', '-')]
        if not cas_list:
            continue

        primary_cas = cas_list[0]
        synonyms    = cas_list[1:]

        notes = [n.strip() for n in re.split(r'[\s,]+', notes_raw) if n.strip()] if notes_raw else []
        classification          = _parse_classification(class_raw, hcode_raw)
        scl_limits, m_factors, ate = _parse_scl(scl_raw)

        # İsim listesi (TR önce)
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
            'classification': classification,
            'scl_limits'    : scl_limits,
            'm_factors'     : m_factors,
            'ate'           : ate,
        }

        if primary_cas in db:
            pass  # ilk kaydı koru
        else:
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
    print("XML okunuyor...")
    xml_str = _extract_xml()
    print(f"  {len(xml_str)//1024} KB")

    print("Parse ediliyor...")
    db = parse(xml_str)

    real  = sum(1 for v in db.values() if '_alias' not in v)
    alias = sum(1 for v in db.values() if '_alias' in v)
    has_scl = sum(1 for v in db.values() if '_alias' not in v and v.get('scl_limits'))
    has_m   = sum(1 for v in db.values() if '_alias' not in v and v.get('m_factors'))

    print(f"  Gerçek madde : {real}")
    print(f"  Alias        : {alias}")
    print(f"  SCL verisi   : {has_scl}")
    print(f"  M-faktör     : {has_m}")

    OUT_PATH.write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"\nKaydedildi: {OUT_PATH}")

    print("\n--- Örnek (NaOH 1310-73-2) ---")
    if '1310-73-2' in db:
        print(json.dumps(db['1310-73-2'], ensure_ascii=False, indent=2))
