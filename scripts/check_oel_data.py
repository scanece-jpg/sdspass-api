"""
check_oel_data.py — tr_oel_limits.json'u resmi PDF tablosuyla karşılaştırır.

PDF: C:/Users/user/Downloads/mesleki mar sınır değeri.pdf (Ek-1, sayfa 7-18)
JSON: data/tr_oel_limits.json

Çıktı: data/oel_conflict_report.md
"""

import json, re, sys
from pathlib import Path
import pdfplumber

sys.stdout.reconfigure(encoding='utf-8')

ROOT     = Path(__file__).parent.parent
OEL_PATH = ROOT / 'data' / 'tr_oel_limits.json'
PDF_PATH = Path('C:/Users/user/Downloads/mesleki mar sınır değeri.pdf')
REPORT   = ROOT / 'data' / 'oel_conflict_report.md'

CAS_RE  = re.compile(r'\d{2,7}-\d{2}-\d')
DASH_RE = re.compile(r'^[—\-–]+$')

# Koordinat bazlı sütun sınırları (x ekseni)
COL_CAS_MIN   = 95   # CAS sütunu başlangıcı
COL_CAS_MAX   = 143  # CAS sütunu sonu
COL_NAME_MIN  = 143
COL_NAME_MAX  = 255
COL_TW_MG     = (255, 315)
COL_TW_PPM    = (315, 365)
COL_STEL_MG   = (365, 415)
COL_STEL_PPM  = (415, 470)
COL_SKIN_MIN  = 470

def _num(s):
    if not s or DASH_RE.match(s.strip()):
        return None
    s = s.strip().replace(' ', '').replace(',', '.')
    try:
        return float(s)
    except ValueError:
        return None

def _in_col(word, col):
    """Kelimenin x koordinatı sütun aralığında mı?"""
    return col[0] <= word['x0'] < col[1]

def extract_pdf_oel(pdf_path):
    """
    Koordinat bazlı tablo parse — her satırdaki kelimeleri x pozisyonuna göre sütuna atar.
    Döner: dict[cas] = {tw_mgm3, tw_ppm, stel_mgm3, stel_ppm, skin, name}
    """
    records = {}
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page in pdf.pages[6:19]:
            words = page.extract_words(keep_blank_chars=False)

            # Kelimeleri y koordinatına göre satırlara grupla (±4px tolerans)
            rows_by_y = {}
            for w in words:
                y = round(w['top'] / 4) * 4  # 4px hassasiyete yuvarla
                rows_by_y.setdefault(y, []).append(w)

            # Satırları y sırasına göre işle
            sorted_ys = sorted(rows_by_y.keys())
            cas_buffer = ''   # Satır kırılmalı CAS için

            for y in sorted_ys:
                row_words = rows_by_y[y]

                # CAS sütunundaki kelimeleri topla
                cas_words  = [w['text'] for w in row_words if COL_CAS_MIN <= w['x0'] < COL_CAS_MAX]
                name_words = [w['text'] for w in row_words if COL_NAME_MIN <= w['x0'] < COL_NAME_MAX]
                tw_mg_w    = [w['text'] for w in row_words if _in_col(w, COL_TW_MG)]
                tw_ppm_w   = [w['text'] for w in row_words if _in_col(w, COL_TW_PPM)]
                stel_mg_w  = [w['text'] for w in row_words if _in_col(w, COL_STEL_MG)]
                stel_ppm_w = [w['text'] for w in row_words if _in_col(w, COL_STEL_PPM)]
                skin_words = [w['text'] for w in row_words if w['x0'] >= COL_SKIN_MIN]

                cas_text = ''.join(cas_words)

                # CAS satır kırılması: "106-" sonra "35-4" → birleştir
                if cas_text:
                    cas_buffer += cas_text
                    full_cas = CAS_RE.search(cas_buffer.replace(' ', ''))
                    if full_cas:
                        cas_str = full_cas.group()
                        cas_buffer = ''
                    else:
                        continue  # CAS henüz tamamlanmadı
                else:
                    if not cas_buffer:
                        continue
                    # CAS yoksa ama buffer doluysa geç
                    full_cas = CAS_RE.search(cas_buffer.replace(' ', ''))
                    if full_cas:
                        cas_str = full_cas.group()
                        cas_buffer = ''
                    else:
                        continue

                name = ' '.join(name_words)
                skin = any('eri' in w.lower() for w in skin_words)

                tw_mgm3   = _num(' '.join(tw_mg_w))
                tw_ppm    = _num(' '.join(tw_ppm_w))
                stel_mgm3 = _num(' '.join(stel_mg_w))
                stel_ppm  = _num(' '.join(stel_ppm_w))

                if cas_str not in records:
                    records[cas_str] = {
                        'name': name,
                        'tw_mgm3': tw_mgm3,
                        'tw_ppm': tw_ppm,
                        'stel_mgm3': stel_mgm3,
                        'stel_ppm': stel_ppm,
                        'skin': skin,
                    }

    return records

def compare(pdf_data, json_data):
    issues = []
    tolerance = 0.05  # %5 tolerans

    for cas, pdf_rec in pdf_data.items():
        if cas not in json_data:
            issues.append((cas, pdf_rec.get('name',''), 'kayit_bulunamadi',
                           '', str(pdf_rec), 'JSON\'da bu CAS yok'))
            continue

        j = json_data[cas]

        for field in ['tw_mgm3', 'tw_ppm', 'stel_mgm3', 'stel_ppm']:
            pdf_val = pdf_rec.get(field)
            json_val = j.get(field)

            if pdf_val is None:
                continue  # PDF'de yok, atlıyoruz
            if json_val is None:
                issues.append((cas, pdf_rec.get('name',''), field,
                               str(json_val), str(pdf_val),
                               f'JSON\'da {field} boş, belgede {pdf_val}'))
                continue

            if abs(pdf_val - json_val) / max(pdf_val, 0.001) > tolerance:
                issues.append((cas, pdf_rec.get('name',''), field,
                               str(json_val), str(pdf_val),
                               f'Değer uyuşmuyor'))

    return issues

def write_report(issues, pdf_count, json_count):
    lines = [
        '# TR OEL Çelişki Raporu',
        f'PDF kayıt sayısı: {pdf_count}',
        f'JSON kayıt sayısı: {json_count}',
        f'Bulunan uyumsuzluk: {len(issues)}',
        '',
        '| CAS | İsim | Alan | JSON | PDF | Açıklama |',
        '|-----|------|------|------|-----|----------|',
    ]
    for cas, name, field, jval, pval, desc in issues:
        n = name[:35].replace('|', '/')
        lines.append(f'| {cas} | {n} | {field} | {jval} | {pval} | {desc} |')
    REPORT.write_text('\n'.join(lines), encoding='utf-8')

if __name__ == '__main__':
    print('PDF okunuyor...')
    pdf_data = extract_pdf_oel(PDF_PATH)
    print(f'PDF\'den {len(pdf_data)} kayıt çıkarıldı')

    json_data = json.loads(OEL_PATH.read_text(encoding='utf-8'))
    print(f'JSON\'da {len(json_data)} kayıt var')

    print('Karşılaştırılıyor...')
    issues = compare(pdf_data, json_data)
    print(f'Bulunan uyumsuzluk: {len(issues)}')

    write_report(issues, len(pdf_data), len(json_data))
    print(f'Rapor: {REPORT}')

    if issues:
        print('\nİlk 10:')
        for cas, name, field, jval, pval, desc in issues[:10]:
            print(f'  {cas} [{field}] JSON={jval} PDF={pval} → {desc}')

    # PDF'den çıkarılan örnek kayıtları göster
    print('\nPDF\'den çıkarılan örnek (ilk 5):')
    for cas, rec in list(pdf_data.items())[:5]:
        print(f'  {cas}: {rec}')
