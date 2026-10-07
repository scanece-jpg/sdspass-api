"""data/tr_oel_limits.json'u resmî TR metinlerine göre düzeltir.

Kaynaklar:
- Kimyasal Maddelerle Çalışmalarda Sağlık ve Güvenlik Önlemleri Hakkında Yönetmelik (RG 12.08.2013/28733) Ek-1
  (Değişik: RG 20.10.2023/32345) — sds-knowledge/tr/mesleki mar sınır değeri.pdf
- Kanserojen veya Mutajen Maddelerle Çalışmalarda Sağlık ve Güvenlik Önlemleri Hakkında Yönetmelik
  (RG 06.08.2013/28730) Ek-2 — sds-knowledge/tr/kanserojen-mutajen-yonetmeligi-ek2.md

Yapılanlar:
- Her kayda 'regulation' = '28733 Ek-1' veya '28730 Ek-2'; 'skin' resmî "Deri" sütunundan.
- İki yönetmelikte de bulunmayan kayıtlar data/oel_tr_disi.json'a taşınır (GBF'de TR sınır değeri olarak basılmaz).
Kullanım: python scripts/verify_tr_oel.py [--yaz]
"""
import json
import os
import re
import sys

import fitz

sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF = os.path.join(ROOT, 'sds-knowledge', 'tr', 'mesleki mar sınır değeri.pdf')
OEL = os.path.join(ROOT, 'data', 'tr_oel_limits.json')
DISI = os.path.join(ROOT, 'data', 'oel_tr_disi.json')

# 28730 Ek-2 (sert ağaç tozlarının CAS'ı yok)
KANS = {
    '71-43-2': {'name_tr': 'Benzen', 'tw_ppm': 1, 'tw_mgm3': 3.25, 'stel_ppm': None, 'stel_mgm3': None,
                'skin': True, 'carcinogen': True, 'regulation': '28730 Ek-2'},
    '75-01-4': {'name_tr': 'Vinilklorür monomeri', 'tw_ppm': 3, 'tw_mgm3': 7.77, 'stel_ppm': None,
                'stel_mgm3': None, 'skin': False, 'carcinogen': True, 'regulation': '28730 Ek-2'},
}


# PDF'te EC ve CAS sütunları iç içe bölündüğü için otomatik okunamayan, resmî Ek-1'de elle doğrulanmış satırlar
# (CAS → "Deri" var mı). Değerler: tert-amilasetat 270/50/540/100; MTBE 183,5/50/367/100; klorlu difenil oksit 0,5.
MANUAL = {'625-16-1': False, '1634-04-4': False, '55720-99-5': False}


def cas_ok(c):
    d = c.replace('-', '')
    return sum(int(x) * (i + 1) for i, x in enumerate(reversed(d[:-1]))) % 10 == int(d[-1])


def official_rows():
    """CAS → satır belirteçleri (ad, değerler, açıklama). Satır sonu tireyle bölünmüş numaralar birleştirilir."""
    lines = [l.strip() for p in fitz.open(PDF) for l in p.get_text().split('\n')]
    toks, buf = [], ''
    for l in lines:
        if buf:
            l, buf = buf + l, ''
        if re.fullmatch(r'[\d-]+-', l):
            buf = l
            continue
        toks.append(l)
    idx = [i for i, t in enumerate(toks) if re.fullmatch(r'\d{2,7}-\d{2}-\d', t) and cas_ok(t)]
    rows = {toks[a]: toks[a + 1:b] for a, b in zip(idx, idx[1:] + [len(toks)])}
    for c, deri in MANUAL.items():
        rows.setdefault(c, ['Deri'] if deri else [])
    return rows


def main(write):
    off = official_rows()
    data = json.load(open(OEL, encoding='utf-8'))
    out, disi, skin_fix = {}, {}, []
    for k, v in data.items():
        if k in KANS:
            continue
        if k not in off:
            disi[k] = v
            continue
        v = dict(v)
        deri = 'Deri' in off[k]
        if deri != bool(v.get('skin')):
            skin_fix.append(f'{k} {v.get("name_tr")}: {v.get("skin")} → {deri}')
        v['skin'], v['carcinogen'], v['regulation'] = deri, False, '28733 Ek-1'
        out[k] = v
    out.update(KANS)
    print(f'28733 Ek-1: {len(out) - len(KANS)} | 28730 Ek-2: {len(KANS)} | TR dışı: {len(disi)} | '
          f'deri düzeltmesi: {len(skin_fix)}')
    print('TR dışı:', ', '.join(f'{k} {v.get("name_tr")}' for k, v in disi.items()))
    print('Resmî Ek-1\'de olup listede olmayan CAS:', sorted(set(off) - set(out)))
    if write:
        json.dump(out, open(OEL, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
        json.dump({'not': 'Bu değerler Türkiye mevzuatında (28733 Ek-1, 28730 Ek-2) yer almaz; GBF\'de TR sınır '
                          'değeri olarak kullanılmaz. Yalnız başvuru amaçlı saklanır.', 'kayitlar': disi},
                  open(DISI, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
        print('yazıldı')


if __name__ == '__main__':
    main('--yaz' in sys.argv)
