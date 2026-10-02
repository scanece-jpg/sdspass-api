"""G-basliklar: GBF metnindeki başlık ve alt başlıkları KKDİK Ek-2 Bölüm B ile karşılaştırır.
Kullanım: python scripts/check_headings.py <gbf.pdf>"""
import os
import re
import sys
import unicodedata

sys.stdout.reconfigure(encoding='utf-8')
import fitz

EK2 = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sds-knowledge", "tr", "kkdik-ekleri", "kkdik-ek-02.md")


def norm(s):
    # Büyük harf I/İ karışıklığı (örn. "ÖNLEMLERI") başlık farkı sayılmaz
    s = unicodedata.normalize('NFC', s).replace('İ', 'i').replace('I', 'i').lower().replace('ı', 'i')
    s = re.sub(r'[^\wçğıöşü/ ]', ' ', s)
    s = re.sub(r'\s*/\s*', '/', s)            # "Bileşimi /içindekiler" = "Bileşimi/içindekiler"
    return re.sub(r'\s+', ' ', s).strip()


# Bölüm B listesi: "BÖLÜM n: başlık" ve "n.m başlık" satırları
txt = open(EK2, encoding='utf-8').read()
part_b = txt[txt.index('**BÖLÜM B**'):]
heads = []
sec = None
for line in part_b.splitlines():
    line = line.strip().lstrip('- ').strip()
    m = re.match(r'^BÖLÜM\s+(\d+)\s*[:.]\s*(.+)$', line)
    if m:
        sec = int(m.group(1)); heads.append((f'{sec}', m.group(2).strip()))
        continue
    m = re.match(r'^(\d+)\.(\d+)\.?\s+(.+)$', line)
    if m and sec is not None:
        heads.append((f'{sec}.{m.group(2)}', m.group(3).strip()))   # docling numara kaymasına karşı bölümden

pdf = fitz.open(sys.argv[1])
body = norm(' '.join(p.get_text() for p in pdf))
pos, rows = 0, []
for num, title in heads:
    t = norm(title)
    key = (f'bölüm {num} ' if '.' not in num else f'{num} ') + t
    i = body.find(norm(key), pos)
    if i >= 0:
        rows.append((num, title, 'tam', '')); pos = i
        continue
    # numara var, başlık metni farklı mı?
    # norm() noktaları boşluğa çevirir: "2.1" metinde "2 1" olarak aranır
    pat = (rf'bölüm {num} (.{{0,90}})' if '.' not in num else rf'(?<!\d ){num.replace(".", " ")} (.{{0,90}})')
    m = re.search(pat, body[pos:])
    rows.append((num, title, 'farklı' if m else 'yok', m.group(1)[:90] if m else ''))
# Ek-2 B: 3. bölümde "uygun görülürse yalnızca 3.1 veya 3.2" — biri varsa diğeri eksik sayılmaz
st = {r[0]: r[2] for r in rows}
if 'tam' in (st.get('3.1'), st.get('3.2')):
    rows = [(n, t, 'tam' if n in ('3.1', '3.2') else s, x) for n, t, s, x in rows]
ok = sum(r[2] == 'tam' for r in rows)
print(f'Ek-2 Bölüm B başlık: {len(rows)} | birebir: {ok} | farklı: {sum(r[2]=="farklı" for r in rows)} | '
      f'bulunamadı: {sum(r[2]=="yok" for r in rows)}')
for num, title, st, seen in rows:
    if st != 'tam':
        print(f'  {st:7} {num:5} Ek-2: "{title}"' + (f'\n                GBF:  "{seen}"' if seen else ''))
