"""data/tr_oel_limits.json'u resmî TR metinlerine göre düzeltir / tamamlar.

Kaynaklar:
- Kimyasal Maddelerle Çalışmalarda Sağlık ve Güvenlik Önlemleri Hakkında Yönetmelik (RG 12.08.2013/28733) Ek-1
  (Değişik: RG 20.10.2023/32345) — sds-knowledge/tr/mesleki mar sınır değeri.pdf
  Sütunlar: EINECS | CAS | Madde | TWA mg/m³ | TWA ppm | STEL mg/m³ | STEL ppm | Tavan mg/m³ | Tavan ppm | Özel işaret
- Kanserojen veya Mutajen Maddelerle Çalışmalarda Sağlık ve Güvenlik Önlemleri Hakkında Yönetmelik
  (RG 06.08.2013/28730) Ek-2 — sds-knowledge/tr/kanserojen-mutajen-yonetmeligi-ek2.md

Kurallar:
- Değerler, deri işareti ve tavan (ceiling) değeri resmî tablodan alınır. Aynı CAS iki satırda farklıysa daha sıkı
  (küçük) değer ve "Deri" işareti (herhangi bir satırda varsa) alınır.
- Resmî tabloda olup listede olmayan maddeler eklenir; iki yönetmelikte de bulunmayan kayıtlar
  data/oel_tr_disi.json'a taşınır (GBF'de TR sınır değeri olarak basılmaz).
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
FIELDS = ('tw_mgm3', 'tw_ppm', 'stel_mgm3', 'stel_ppm', 'ceil_mgm3', 'ceil_ppm')

# 28730 Ek-2 (sert ağaç tozlarının CAS'ı yok)
KANS = {
    '71-43-2': {'name_tr': 'Benzen', 'tw_ppm': 1, 'tw_mgm3': 3.25, 'stel_ppm': None, 'stel_mgm3': None,
                'ceil_mgm3': None, 'ceil_ppm': None, 'skin': True, 'carcinogen': True, 'regulation': '28730 Ek-2'},
    '75-01-4': {'name_tr': 'Vinilklorür monomeri', 'tw_ppm': 3, 'tw_mgm3': 7.77, 'stel_ppm': None,
                'stel_mgm3': None, 'ceil_mgm3': None, 'ceil_ppm': None, 'skin': False, 'carcinogen': True,
                'regulation': '28730 Ek-2'},
}

# Resmî tablodaki satır hataları: bu CAS'a bu adla yazılmış satır yok sayılır
# (34590-94-8 dipropilen glikol metil eterdir; "Florür, inorganik" satırına yanlışlıkla aynı CAS yazılmış).
SKIP_ROWS = {('34590-94-8', 'Florür')}

# Tablo okuyucunun (find_tables) satırını ayıramadığı, resmî Ek-1'de elle doğrulanmış kayıtlar:
# mevcut değerler korunur. tert-amilasetat 270/50/540/100; MTBE 183,5/50/367/100; klorlu difenil oksit 0,5;
# e-kaprolaktam 10/—/40; viniliden klorür 8/2/20/5; klorometan 42/20.
MANUAL = {'625-16-1', '1634-04-4', '55720-99-5', '105-60-2', '75-35-4', '74-87-3'}


def cas_ok(c):
    d = c.replace('-', '')
    return sum(int(x) * (i + 1) for i, x in enumerate(reversed(d[:-1]))) % 10 == int(d[-1])


def num(s):
    try:
        return float(re.sub(r'\s', '', s or '').replace(',', '.'))
    except ValueError:
        return None


def official():
    """CAS → {name, değerler, skin}. Yinelenen satırlar daha sıkı değerle birleştirilir."""
    out = {}
    for page in fitz.open(PDF):
        for tab in page.find_tables().tables:
            for r in tab.extract():
                r = [c for c in r if c is not None]
                if len(r) != 10:
                    continue
                cas_cell = re.sub(r'-\s*\n\s*', '-', r[1] or '').replace('\n', ' ')
                name = re.sub(r'\s+', ' ', r[2] or '').strip()
                for c in re.findall(r'\d{2,7}-\d{2}-\d', cas_cell):
                    if not cas_ok(c) or any(c == s and name.startswith(n) for s, n in SKIP_ROWS):
                        continue
                    rec = dict(zip(FIELDS, (num(x) for x in r[3:9])), name=name, skin='Deri' in (r[9] or ''))
                    if c in out:
                        old = out[c]
                        for f in FIELDS:
                            vals = [v for v in (old[f], rec[f]) if v is not None]
                            old[f] = min(vals) if vals else None
                        old['skin'] = old['skin'] or rec['skin']
                        old['dup'] = True
                    else:
                        out[c] = rec
    return out


def clean_name(n):
    n = re.sub(r'\s*\(maruziyet tespit.*?alınmalıdır\)', '', n)
    return n.strip()


def main(write):
    off = official()
    data = json.load(open(OEL, encoding='utf-8'))
    disi_path = json.load(open(DISI, encoding='utf-8')) if os.path.exists(DISI) else {'kayitlar': {}}
    out, disi, log = {}, dict(disi_path.get('kayitlar', {})), []
    for k, v in data.items():
        if k in KANS:
            continue
        if k in MANUAL:
            out[k] = dict(v, ceil_mgm3=v.get('ceil_mgm3'), ceil_ppm=v.get('ceil_ppm'))
            continue
        if k not in off:
            disi[k] = v
            log.append(f'TR dışı: {k} {v.get("name_tr")}')
            continue
        f, nv = off[k], dict(v)
        if k == '34590-94-8':
            nv['name_tr'] = 'Dipropilen glikol metil eter; (2-Metoksimetiletoksi)propanol'
        for x in FIELDS + ('skin',):
            if (nv.get(x) or None) != (f[x] or None):
                log.append(f'{k} {nv.get("name_tr")}: {x} {nv.get(x)} → {f[x]}' + (' (iki satır; sıkı değer)'
                                                                                   if f.get('dup') else ''))
            nv[x] = f[x]
        nv['carcinogen'], nv['regulation'] = False, '28733 Ek-1'
        out[k] = nv
    for k, f in off.items():
        if k not in out and k not in KANS:
            out[k] = {'name_tr': clean_name(f['name']), **{x: f[x] for x in FIELDS}, 'skin': f['skin'],
                      'carcinogen': False, 'regulation': '28733 Ek-1'}
            log.append(f'EKLENDİ: {k} {out[k]["name_tr"]} {[f[x] for x in FIELDS]} deri={f["skin"]}')
    out.update(KANS)
    print(f'Resmî tablo: {len(off)} CAS | liste: {len(out)} | TR dışı: {len(disi)}')
    print('\n'.join(log))
    if write:
        json.dump(out, open(OEL, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
        json.dump({'not': 'Bu değerler Türkiye mevzuatında (28733 Ek-1, 28730 Ek-2) yer almaz; GBF\'de TR sınır '
                          'değeri olarak kullanılmaz. Yalnız başvuru amaçlı saklanır.', 'kayitlar': disi},
                  open(DISI, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
        print('yazıldı')


if __name__ == '__main__':
    main('--yaz' in sys.argv)
