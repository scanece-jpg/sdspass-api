"""KKDİK Ek-17 (kısıtlamalar) — ana tablo ve ekler (Ek-I…Ek-IX) bilgi tabanı md dosyalarından CAS → kısıtlama
girişi eşlemesi üretir: data/kkdik_ek17_cas.json
Kullanım: python scripts/build_ek17_cas.py
Not: KKDİK Ek-14 (izne tabi maddeler) yönetmelik metninde boştur ("Bakanlığın internet sitesinde yayınlanır")."""
import glob
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KD = os.path.join(ROOT, 'sds-knowledge', 'tr', 'kkdik-ekleri')
OUT = os.path.join(ROOT, 'data', 'kkdik_ek17_cas.json')
CAS_RE = re.compile(r'(?<![\d-])(\d{2,7}-\d{2}-\d)(?![\d-])')


def cas_ok(c):
    d = c.replace('-', '')
    return sum(int(x) * (i + 1) for i, x in enumerate(reversed(d[:-1]))) % 10 == int(d[-1])


out = {}


def add(cas, rec):
    if not cas_ok(cas):
        return
    lst = out.setdefault(cas, [])
    if rec not in lst:
        lst.append(rec)


# Ana tablo: "| 5. Benzen  CAS No 71-43-2 ... | koşullar |"
main = open(os.path.join(KD, 'kkdik-ek-17.md'), encoding='utf-8').read()
for line in main.splitlines():
    m = re.match(r'^\|\s*(\d{1,3})\.\s*([^|]+)\|', line)
    if not m:
        continue
    no, cell = m.group(1), m.group(2)
    name = re.split(r'\s+CAS|\s+EC No|\s+Liste', cell)[0].strip()[:120]
    for c in CAS_RE.findall(cell):
        add(c, {'giris': no, 'ad': name, 'kaynak': f'KKDİK Ek-17 madde {no}'})

# Ekler: başlıktaki "Giriş NN" ve tablo satırlarındaki madde adı
for f in sorted(glob.glob(os.path.join(KD, 'kkdik-ek-17-ek-*.md'))):
    txt = open(f, encoding='utf-8').read()
    ek = re.search(r'ek-17-ek-([ivx]+)\.md$', f).group(1).upper()
    g = re.search(r'Giriş\s*(\d+)\s*[-–]?\s*([^*(]*)', txt)
    giris, baslik = (g.group(1), g.group(2).strip(' -–')) if g else ('', '')
    for line in txt.splitlines():
        if not line.startswith('|'):
            continue
        cells = [c.strip() for c in line.strip('|').split('|')]
        cas = [c for cell in cells[1:] for c in CAS_RE.findall(cell)]
        for c in cas:
            add(c, {'giris': giris, 'ad': re.sub(r'\s+', ' ', cells[0])[:120],
                    'kaynak': f'KKDİK Ek-17 Ek-{ek} (Giriş {giris}{" — " + baslik if baslik else ""})'})

# Ek-17 madde 46 — metin nonilfenol için yalnız 25154-52-3 verir, nonilfenol etoksilatlar için CAS vermez (yalnız
# formül). Kapsamdaki diğer CAS'lar, aynı maddeleri tanımlayan Bazı Zararlı Kimyasalların İhracatı ve İthalatı Hakkında
# Yönetmelik (RG 28.01.2023/32087) Ek-1 satırlarından alınır.
_pic = os.path.join(ROOT, 'sds-knowledge', 'tr', 'pic-32087-ekler.md')
if os.path.exists(_pic):
    for line in open(_pic, encoding='utf-8'):
        cells = [c.strip() for c in line.strip().strip('|').split('|')]
        if len(cells) < 3 or not cells[1].lower().startswith('nonilfenol'):
            continue
        is_npe = 'etoksilat' in cells[1].lower()
        for c in CAS_RE.findall(cells[2]):
            if any(r['giris'] == '46' for r in out.get(c, [])):
                continue   # ana tabloda zaten madde 46 (25154-52-3)
            add(c, {'giris': '46', 'ad': 'Nonilfenol etoksilatlar' if is_npe else 'Nonilfenol',
                    'kaynak': 'KKDİK Ek-17 madde 46'})

json.dump({'kaynak': 'KKDİK Ek-17 (RG 23.06.2017/30105 Mükerrer; RG 29.11.2019/30963 ile güncel) — bilgi tabanı md',
           'not': 'Ek-14 (izne tabi maddeler) yönetmelik metninde boş; Bakanlık sitesinde yayımlanır.',
           'cas': out}, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
from collections import Counter
print('CAS:', len(out), '| kaynak dağılımı:', Counter(r['kaynak'].split(' (')[0] for v in out.values() for r in v).most_common())
for c in ['71-43-2', '75-01-4', '1333-82-0', '7439-92-1', '7697-37-2', '84-74-2']:
    print(c, [r['kaynak'] for r in out.get(c, [])])
