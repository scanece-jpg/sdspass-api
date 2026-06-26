"""
check_oel_word.py — tr_oel_limits.json'u Word belgesindeki OEL tablosuyla karşılaştırır.

Word: C:/Users/user/Documents/maruziyet sınır.docx
JSON: data/tr_oel_limits.json
Çıktı: data/oel_conflict_report.md
"""

import json, re, sys, zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

ROOT      = Path(__file__).parent.parent
OEL_PATH  = ROOT / 'data' / 'tr_oel_limits.json'
WORD_PATH = Path('C:/Users/user/Documents/maruziyet sınır.docx')
REPORT    = ROOT / 'data' / 'oel_conflict_report.md'

NS = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}

# ---------------------------------------------------------------------------
# CAS normalize (Word formatı: "131977-3" → "1319-77-3")
# ---------------------------------------------------------------------------

def fix_cas(raw: str) -> str:
    """
    Word'de CAS tüm iç tireler kaldırılmış, sadece son tire korunmuş.
    "88-891"   → "88-89-1"
    "131977-3" → "1319-77-3"
    "744006-4" → "7440-06-4"
    """
    raw = raw.strip()
    m = re.match(r'^(.+)-(\d)$', raw)
    if not m:
        return raw
    prefix, last = m.group(1), m.group(2)
    # prefix zaten tire içeriyorsa (NN-NN formatı) → doğrudan ekle
    if '-' in prefix:
        return f'{prefix}-{last}'
    # Tire yoksa → son 2 rakamı ayır
    if len(prefix) >= 3:
        return f'{prefix[:-2]}-{prefix[-2:]}-{last}'
    return f'{prefix}-{last}'

# ---------------------------------------------------------------------------
# Word metnini oku ve tokenize et
# ---------------------------------------------------------------------------

DASH = r'(?:—|–|-)'
NUM  = r'[\d]+(?:[,\.]\d+)?'

def read_word_text(path: Path) -> str:
    with zipfile.ZipFile(str(path)) as z:
        xml_bytes = z.read('word/document.xml')
    root = ET.fromstring(xml_bytes.decode('utf-8'))
    parts = []
    for t in root.findall('.//w:t', NS):
        parts.append(t.text or '')
    return ' '.join(parts)

def _num(s: str):
    if not s or re.match(r'^[—\-–]+$', s.strip()):
        return None
    try:
        return float(s.strip().replace(',', '.').replace(' ', ''))
    except ValueError:
        return None

# ---------------------------------------------------------------------------
# Word metnini satırlara ayır (her kayıt: EINECS CAS İsim değerler)
# ---------------------------------------------------------------------------

# EINECS formatı: NNN-NNNN veya NNN-NNN-N (tireli veya tiresiz)
EINECS_RE = re.compile(r'\b\d{3}-\d{3,4}-?\d?\b')
# Word CAS (tiresiz iç, son tire var): NN...N-N
WORD_CAS_RE = re.compile(r'\b\d{2,6}-\d{1,2}\b')

def parse_word_oel(text: str) -> dict:
    """
    Metni boşlukla ayrılmış token dizisine çevirir, EINECS+CAS çiftlerini
    anchor olarak kullanarak her kaydın değerlerini çıkarır.
    """
    records = {}

    # Satırları EINECS numarasıyla başlayan bloklara böl
    # Pattern: NNN-NNNN veya NNN-NNN benzeri EINECS, ardından CAS (tiresiz)
    # Kayıtları bulmak için EINECS regex'i anchor olarak kullan
    # EINECS+CAS çifti sonrası: isim (sayı olmayan kelimeler) + sayılar

    token_pattern = re.compile(
        r'(\d{3}-\d{3,5}[-\d]*)'   # EINECS benzeri
        r'\s+'
        r'(\d[\d-]+\d)'             # CAS benzeri (en az 5 karakter)
        r'\s+'
        r'((?:(?!\d[\d,\.]+\s).)+?)'  # İsim (sayı olmayan)
        r'\s+'
        r'([\d,\.]+|' + DASH + r')'   # tw_mgm3
        r'\s+'
        r'([\d,\.]+|' + DASH + r')'   # tw_ppm
        r'(?:\s+([\d,\.]+|' + DASH + r'))?'   # stel_mgm3
        r'(?:\s+([\d,\.]+|' + DASH + r'))?',  # stel_ppm
        re.DOTALL
    )

    # Daha basit yaklaşım: metni JSON'daki bilinen CAS'larla eşleştir
    # Önce tüm Word CAS'larını çıkar, JSON ile karşılaştır
    return records

def parse_by_known_cas(text: str, json_data: dict) -> dict:
    """
    JSON'daki CAS numaralarını Word formatına çevirip metinde ara.
    Her CAS bulunduğunda ardındaki sayısal değerleri çıkar.
    """
    records = {}

    for cas in json_data:
        # CAS'ı Word formatına çevir: "1330-20-7" → "133020-7"
        parts = cas.split('-')
        if len(parts) != 3:
            continue
        word_form1 = parts[0] + parts[1] + '-' + parts[2]       # 133020-7
        word_form2 = parts[0] + '-' + parts[1] + parts[2]       # 1330-207 (nadir)
        word_form3 = cas                                          # orijinal

        found_pos = -1
        for wf in [word_form1, word_form2, word_form3]:
            idx = text.find(wf)
            if idx != -1:
                found_pos = idx + len(wf)
                break

        if found_pos == -1:
            continue

        # Sonraki 120 karakterden sayısal değerleri çıkar
        snippet = text[found_pos:found_pos + 150]
        nums = re.findall(r'[\d]+[,\.]?[\d]*', snippet)

        # Beklenen sıra: tw_mgm3, tw_ppm, stel_mgm3, stel_ppm
        # Dash karakterleri sayı değil, atla
        float_nums = []
        for n in nums[:8]:
            try:
                float_nums.append(float(n.replace(',', '.')))
            except ValueError:
                pass

        skin = 'Deri' in snippet[:100]

        records[cas] = {
            'tw_mgm3':   float_nums[0] if len(float_nums) > 0 else None,
            'tw_ppm':    float_nums[1] if len(float_nums) > 1 else None,
            'stel_mgm3': float_nums[2] if len(float_nums) > 2 else None,
            'stel_ppm':  float_nums[3] if len(float_nums) > 3 else None,
            'skin':      skin,
        }

    return records

# ---------------------------------------------------------------------------
# Karşılaştır
# ---------------------------------------------------------------------------

def compare(word_data: dict, json_data: dict) -> list:
    issues = []
    tol = 0.06  # %6 tolerans (yuvarlama farkları için)

    for cas, wd in word_data.items():
        jd = json_data.get(cas, {})

        for field in ['tw_mgm3', 'tw_ppm', 'stel_mgm3', 'stel_ppm']:
            wval = wd.get(field)
            jval = jd.get(field)

            if wval is None:
                continue
            if jval is None:
                issues.append((cas, jd.get('name_tr', ''), field,
                               '', str(wval), f'JSON boş, belgede {wval}'))
                continue
            if abs(wval - jval) / max(wval, 0.001) > tol:
                issues.append((cas, jd.get('name_tr', ''), field,
                               str(jval), str(wval), 'Değer uyuşmuyor'))

    # JSON'da var, Word'de bulunamayan
    for cas in json_data:
        if cas not in word_data and json_data[cas].get('tw_mgm3') or json_data[cas].get('tw_ppm'):
            issues.append((cas, json_data[cas].get('name_tr', ''), 'belgede_bulunamadi',
                           str(json_data[cas].get('tw_mgm3')), '', 'Word belgesinde bu CAS bulunamadı'))

    return issues

# ---------------------------------------------------------------------------
# Rapor
# ---------------------------------------------------------------------------

def write_report(issues, word_count, json_count):
    lines = [
        '# TR OEL Çelişki Raporu (Word Kaynağı)',
        f'Word kayıt sayısı: {word_count}',
        f'JSON kayıt sayısı: {json_count}',
        f'Bulunan uyumsuzluk: {len(issues)}',
        '',
        '| CAS | İsim | Alan | JSON | Belge | Açıklama |',
        '|-----|------|------|------|-------|----------|',
    ]
    for cas, name, field, jval, bval, desc in issues:
        n = str(name)[:35].replace('|', '/')
        lines.append(f'| {cas} | {n} | {field} | {jval} | {bval} | {desc} |')
    REPORT.write_text('\n'.join(lines), encoding='utf-8')

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    print('Word belgesi okunuyor...')
    text = read_word_text(WORD_PATH)
    print(f'Metin uzunluğu: {len(text)} karakter')

    json_data = json.loads(OEL_PATH.read_text(encoding='utf-8'))
    print(f'JSON kayıt sayısı: {len(json_data)}')

    print('CAS eşleştiriliyor...')
    word_data = parse_by_known_cas(text, json_data)
    print(f'Eşleşen kayıt: {len(word_data)}')

    print('Karşılaştırılıyor...')
    issues = compare(word_data, json_data)

    # Sadece gerçek değer uyuşmazlıklarını göster (belgede_bulunamadi hariç)
    real_issues = [i for i in issues if i[2] != 'belgede_bulunamadi']
    print(f'Değer uyuşmazlığı: {len(real_issues)}')

    write_report(real_issues, len(word_data), len(json_data))
    print(f'Rapor: {REPORT}')

    if real_issues:
        print('\nUyuşmazlıklar:')
        for cas, name, field, jval, bval, desc in real_issues:
            print(f'  {cas} ({name[:30]}) [{field}] JSON={jval} Belge={bval}')
    else:
        print('\nTüm değerler uyuşuyor.')

    print('\nEşleşemeyen JSON kayıtları:')
    not_found = [cas for cas in json_data if cas not in word_data]
    print(f'  {len(not_found)} kayıt Word belgesinde bulunamadı')
    for cas in not_found[:10]:
        print(f'  {cas}: {json_data[cas].get("name_tr","")}')
