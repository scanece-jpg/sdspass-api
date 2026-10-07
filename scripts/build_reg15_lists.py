"""GBF 15 için mevzuat listeleri: data/tr_reg15_lists.json

Kaynaklar (mevzuat.gov.tr ek dosyaları; sds-knowledge/tr/*-ekler.docx → .md, docx git'e girmez):
- Kalıcı Organik Kirleticiler Hakkında Yönetmelik (RG 14.11.2018/30595; Değişik RG 25.03.2021/31434)
  Ek-1 (yasaklamaya tabi) ve Ek-2 (kısıtlamaya tabi) — kok-30595-ekler.md
- Ozon Tabakasını İncelten Maddelere İlişkin Yönetmelik (RG 07.04.2017/30031; Değişik RG 28.07.2017/30137)
  Ek-5 (kontrol altına alınan maddeler) ve Ek-8 (yeni maddeler) — ozon-30031-ekler.md. Ekte CAS yoktur;
  aşağıdaki CAS eşlemesi ekteki tekil adlandırılmış maddeler içindir, izomer aileleri ad/formülle yakalanır.
- Büyük Endüstriyel Kazaların Önlenmesi ve Etkilerinin Azaltılması Hakkında Yönetmelik (RG 02.03.2019/30702)
  Ek-1 Bölüm 2 (adlandırılmış tehlikeli maddeler) — bekra-2019-ekler.md (CAS'lar ekte "gösterge amaçlı")
Kullanım: python scripts/build_reg15_lists.py
"""
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KD = os.path.join(ROOT, 'sds-knowledge', 'tr')
OUT = os.path.join(ROOT, 'data', 'tr_reg15_lists.json')
CAS_RE = re.compile(r'(?<![\d-])(\d{2,7}-\d{2}-\d)(?![\d-])')


def cas_ok(c):
    d = c.replace('-', '')
    return sum(int(x) * (i + 1) for i, x in enumerate(reversed(d[:-1]))) % 10 == int(d[-1])


def rows(md, start, stop):
    t = open(os.path.join(KD, md), encoding='utf-8').read()
    a = t.find(start)
    b = t.find(stop, a + 1) if stop else len(t)
    for line in t[a:b].splitlines():
        if line.startswith('|'):
            yield [c.strip() for c in line.strip('|').split('|')]


# ── KOK Ek-1 / Ek-2 ──────────────────────────────────────────────────────────
kok = {}
for ek, start, stop in (('Ek-1', 'EK - 1', 'EK - 2'), ('Ek-2', 'EK - 2', 'EK - 3')):
    for r in rows('kok-30595-ekler.md', start, stop):
        if len(r) < 2 or r[0] in ('Madde', ''):
            continue
        name = re.sub(r'\s+', ' ', r[0])[:120]
        for c in CAS_RE.findall(r[1]):
            if cas_ok(c):
                kok.setdefault(c, {'ad': name, 'ek': ek})

# ── BEKRA Ek-1 Bölüm 2 ───────────────────────────────────────────────────────
bekra2 = {}
for r in rows('bekra-2019-ekler.md', 'BÖLÜM 2', 'NOTLAR'):
    if len(r) < 2:
        continue
    for c in CAS_RE.findall(' '.join(r[1:2]) or ''):
        if cas_ok(c):
            bekra2.setdefault(c, re.sub(r'\s+', ' ', r[0])[:120])

# ── Ozon Ek-5 / Ek-8 — ekteki tekil adlandırılmış maddelerin CAS karşılıkları ─────
OZON = {
    # Grup I / IX — HCFC'ler
    '75-45-6': ('HCFC-22 Klorodiflorometan', 'Ek-5 Grup I'),
    '75-43-4': ('HCFC-21 Flordiklormetan', 'Ek-5 Grup IX'),
    '593-70-4': ('HCFC-31 Klorflormetan', 'Ek-5 Grup IX'),
    '306-83-2': ('HCFC-123 Diklortrifloretan', 'Ek-5 Grup IX'),
    '2837-89-0': ('HCFC-124 Klortetrafloretan', 'Ek-5 Grup IX'),
    '1717-00-6': ('HCFC-141b 1,1-Dikloro-1-floretan', 'Ek-5 Grup IX'),
    '75-68-3': ('HCFC-142b 1-Kloro-1,1-difloroetan', 'Ek-5 Grup IX'),
    '422-56-0': ('HCFC-225ca 3,3-Diklor-1,1,1,2,2-pentaflorpropan', 'Ek-5 Grup IX'),
    '507-55-1': ('HCFC-225cb 1,3-Diklor-1,1,2,2,3-pentaflorpropan', 'Ek-5 Grup IX'),
    # Grup II / III — CFC'ler
    '75-69-4': ('CFC-11 Triklorflorometan', 'Ek-5 Grup II'),
    '75-71-8': ('CFC-12 Diklordiflormetan', 'Ek-5 Grup II'),
    '76-13-1': ('CFC-113 Triklortrifloretan', 'Ek-5 Grup II'),
    '76-14-2': ('CFC-114 Diklortetrafloretan', 'Ek-5 Grup II'),
    '76-15-3': ('CFC-115 Klorpentafloretan', 'Ek-5 Grup II'),
    '75-72-9': ('CFC-13 Klortriflorometan', 'Ek-5 Grup III'),
    '354-56-3': ('CFC-111 Pentaklorofloroetan', 'Ek-5 Grup III'),
    '76-12-0': ('CFC-112 Tetraklorodifloroetan', 'Ek-5 Grup III'),
    '76-11-9': ('CFC-112a Tetraklorodifloroetan', 'Ek-5 Grup III'),
    # Grup IV — halonlar
    '353-59-3': ('halon-1211 Bromoklorodiflorometan', 'Ek-5 Grup IV'),
    '75-63-8': ('halon-1301 Bromotriflorometan', 'Ek-5 Grup IV'),
    '124-73-2': ('halon-2402 Dibromotetrafloroetan', 'Ek-5 Grup IV'),
    # Grup V, VI, VII, X
    '56-23-5': ('Karbontetraklorür', 'Ek-5 Grup V'),
    '71-55-6': ('1,1,1-trikloretan (metil kloroform)', 'Ek-5 Grup VI'),
    '74-83-9': ('Metil bromür (bromometan)', 'Ek-5 Grup VII'),
    '1511-62-2': ('HBFC-22 B1 Bromodiflorometan', 'Ek-5 Grup VIII'),
    '74-97-5': ('Bromoklorometan', 'Ek-5 Grup X'),
    # Ek-8 — yeni maddeler
    '75-61-6': ('Dibromodiflorometan (halon-1202)', 'Ek-8'),
    '106-94-5': ('1-Bromopropan (n-propil bromür)', 'Ek-8'),
    '74-96-4': ('Bromoetan (etil bromür)', 'Ek-8'),
    '2314-97-8': ('Trifloroiodometan', 'Ek-8'),
    '74-87-3': ('Klorometan (metil klorür)', 'Ek-8'),
}
ozon = {c: {'ad': a, 'ek': e} for c, (a, e) in OZON.items() if cas_ok(c)}
bad = [c for c in OZON if not cas_ok(c)]

json.dump({
    'kaynak': {
        'kok': 'Kalıcı Organik Kirleticiler Hakkında Yönetmelik (RG 14.11.2018/30595; Değişik RG 25.03.2021/31434) Ek-1, Ek-2',
        'ozon': 'Ozon Tabakasını İncelten Maddelere İlişkin Yönetmelik (RG 07.04.2017/30031) Ek-5, Ek-8',
        'bekra': 'Büyük Endüstriyel Kazaların Önlenmesi ve Etkilerinin Azaltılması Hakkında Yönetmelik (RG 02.03.2019/30702) Ek-1',
    },
    'kok': kok, 'ozon': ozon, 'bekra2': bekra2,
}, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'KOK: {len(kok)} CAS | ozon: {len(ozon)} CAS (geçersiz: {bad}) | BEKRA Bölüm 2: {len(bekra2)} CAS')
