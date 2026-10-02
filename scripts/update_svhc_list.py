"""Kullanım: python scripts/update_svhc_list.py <candidate_list_full-YYYY-MM-DD.xlsx>
Excel, echa.europa.eu/candidate-list-table sayfasından elle indirilir (ECHA'dan programla toplu çekim yapılmaz).

data/svhc_candidate_list.json'u ECHA Aday Liste dışa aktarımıyla günceller ve sds-knowledge için md üretir.
Mevcut dosya grup maddelerinin tek tek CAS'larını da içerdiği için korunur; xlsx'teki her CAS'ın mevcut
olduğu doğrulanır, eksikler eklenir, nedenler xlsx'ten yenilenir."""
import json
import os
import re
import sys
import openpyxl

sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
XLSX = sys.argv[1]
_m = re.search(r'(\d{4})-(\d{2})-(\d{2})', os.path.basename(XLSX))   # dosya adındaki dışa aktarım tarihi
EXPORT_DATE = '-'.join(_m.groups()) if _m else ''
EXPORT_DATE_TR = '.'.join(reversed(_m.groups())) if _m else ''
DATA = os.path.join(ROOT, 'data', 'svhc_candidate_list.json')
MD = os.path.join(ROOT, 'sds-knowledge', 'tr', 'svhc-aday-liste-echa.md')

# ECHA "Reason for inclusion" (REACH Md.57) → KKDİK Md.47(1) bendi
REASONS = [
    (r'Carcinogenic', 'Kanserojen (KKDİK Md.47/1-a)'),
    (r'Mutagenic', 'Mutajen (KKDİK Md.47/1-b)'),
    (r'Toxic for reproduction', 'Üreme için toksik (KKDİK Md.47/1-c)'),
    (r'\bPBT\b', 'PBT (KKDİK Md.47/1-ç)'),
    (r'\bvPvB\b', 'vPvB (KKDİK Md.47/1-d)'),
    (r'Endocrine disrupting properties \(Article 57\(f\) - human health\)', 'Endokrin bozucu — insan sağlığı (KKDİK Md.47/1-e)'),
    (r'Endocrine disrupting properties \(Article 57\(f\) - environment\)', 'Endokrin bozucu — çevre (KKDİK Md.47/1-e)'),
    (r'Specific target organ toxicity after repeated exposure', 'Tekrarlı maruziyette belirli hedef organ toksisitesi — eşdeğer endişe (KKDİK Md.47/1-e)'),
    (r'Respiratory sensitising properties', 'Solunum yolu hassaslaştırıcı — eşdeğer endişe (KKDİK Md.47/1-e)'),
    (r'Equivalent level of concern having probable serious effects to human health', 'Eşdeğer endişe — insan sağlığı (KKDİK Md.47/1-e)'),
    (r'Equivalent level of concern having probable serious effects to the environment', 'Eşdeğer endişe — çevre (KKDİK Md.47/1-e)'),
]


def concern_tr(concern: str) -> str:
    out = []
    for pat, tr in REASONS:
        if re.search(pat, concern or '') and tr not in out:
            out.append(tr)
    return '; '.join(out)


def norm_concern(c: str) -> str:
    return '; '.join(p.strip() for p in re.split(r'[\n"]+', c or '') if p.strip())


old = json.load(open(DATA, encoding='utf-8'))
subs = old['substances']
ws = openpyxl.load_workbook(XLSX, read_only=True).worksheets[0]
rows = [r for r in list(ws.iter_rows(values_only=True))[1:] if r and r[0]]


def cas_list(s):
    return [c.strip() for c in re.split(r'[,;]', s or '') if c.strip() and c.strip() != '-']


by_cas = {}
for s in subs:
    for c in cas_list(s['cas']):
        by_cas.setdefault(c, s)

added, updated = [], 0
for r in rows:
    name, desc, ec, cas, date, reason = r[0], r[1], r[2], r[3], r[4], r[5]
    if not cas or cas == '-':
        continue
    s = by_cas.get(cas)
    if s is None:
        s = {'cas': cas, 'ec': ec if ec != '-' else '', 'name': name, 'name_tr': '',
             'concern': '', 'concern_tr': '', 'date': date}
        subs.append(s)
        by_cas[cas] = s
        added.append((cas, name))
    if norm_concern(s['concern']) != norm_concern(reason) or s.get('date') != date:
        updated += 1
    s['concern'] = norm_concern(reason)
    s['date'] = date

# Grup kayıtları (CAS'sız): xlsx'teki ad/tarih ile var mı kontrol et, yoksa ekle
def _nm(n):
    return re.sub(r'\s*\(group\)$', '', (n or '').strip().lower())


old_names = {_nm(s['name']) for s in subs}
groups_added = []
for r in rows:
    if (not r[3] or r[3] == '-') and _nm(r[0]) not in old_names:
        subs.append({'cas': '', 'ec': r[2] if r[2] != '-' else '', 'name': r[0], 'name_tr': '',
                     'concern': norm_concern(r[5]), 'concern_tr': '', 'date': r[4]})
        groups_added.append(r[0])

for s in subs:
    s['concern'] = norm_concern(s['concern'])
    s['concern_tr'] = concern_tr(s['concern'])

missing_tr = [s['concern'] for s in subs if s['concern'] and not s['concern_tr']]
assert not missing_tr, set(missing_tr)

latest = max(rows, key=lambda r: __import__('datetime').datetime.strptime(r[4], '%d-%b-%Y'))[4]
out = {
    'version': f'ECHA Aday Liste — dışa aktarım {EXPORT_DATE_TR} (son ekleme {latest}, {len(rows)} giriş)',
    'date': EXPORT_DATE,
    'source': 'ECHA Candidate List of substances of very high concern for Authorisation (REACH Md.59(10)); '
              'echa.europa.eu/candidate-list-table',
    'note': 'KKDİK Md.49(1) aday listesi Bakanlıkça yayımlanana kadar AB Aday Listesi dikkate alınır '
            '(ÇŞİDB Çevre Etiketi kılavuzları). Grup girişlerinin bilinen bileşen CAS numaraları da ayrı kayıt '
            'olarak tutulur; CAS\'sız grup girişleri yalnız adla izlenir.',
    'substances': subs,
}
json.dump(out, open(DATA, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print('ECHA giriş:', len(rows), '| veri kaydı:', len(subs), '| eklenen CAS:', added,
      '| eklenen grup:', groups_added, '| nedeni/tarihi güncellenen:', updated)

# ── Bilgi tabanı md ──
md = [f'<!-- Kaynak: ECHA Aday Liste dışa aktarımı ({os.path.basename(XLSX)}), SDSPass '
      'data/svhc_candidate_list.json ile birlikte üretildi. -->\n',
      '# Yüksek Önem Arz Eden Maddeler — Aday Liste (SVHC)\n',
      '- **TR dayanağı:** KKDİK Md.49(1) — Ek-14\'e alınmaya aday madde listesi; Bakanlık listeyi internet '
      'sitesinde yayımlar (Md.49(6)).',
      '- **Geçerli liste:** Türkiye listesi Bakanlıkça yayımlanana kadar **AB (ECHA) Aday Listesi** dikkate '
      'alınır (ÇŞİDB Çevre Etiketi başvuru kılavuzları).',
      f'- **Sürüm:** ECHA dışa aktarımı {EXPORT_DATE_TR}; {len(rows)} giriş; son ekleme {latest}. ECHA listeyi '
      'genelde Ocak ve Haziran\'da günceller — yenilenmeli.',
      '- **Kriterler:** KKDİK Md.47(1): (a) kanserojen 1A/1B, (b) mutajen 1A/1B, (c) üreme toksik 1A/1B, '
      '(ç) PBT, (d) vPvB, (e) eşdeğer endişe (endokrin bozucu vb.). ECHA\'daki "Article 57 a–f" bu bentlere karşılık gelir.\n',
      '## SDS yükümlülükleri\n',
      '- **Bölüm 3.2:** Karışımda Aday Listedeki madde ağırlıkça **≥ %0,1** ise listelenir — karışım '
      'sınıflandırılmış (Ek-2 3.2.1(c)) veya sınıflandırılmamış (Ek-2 3.2.2(b)) olsun. Madde sınıflandırma '
      'kriterlerini karşılamıyorsa listelenme nedeni yazılır (Ek-2 3.2.3).',
      '- **SDS verme:** Tehlikeli olarak sınıflandırılmayan karışım, gaz olmayan karışımda tekil '
      'konsantrasyonu ≥ %0,1 olan Aday Liste maddesi içeriyorsa alıcının talebi üzerine SDS verilir (KKDİK Md.27).',
      '- **Eşya:** Eşyada ≥ %0,1 Aday Liste maddesi → alıcıya madde adı ve güvenli kullanım bilgisi; '
      'tüketiciye talep halinde 45 gün içinde (KKDİK Md.29).\n',
      f'## Liste ({len(rows)} giriş)\n',
      '| Madde | EC | CAS | Eklenme | Neden (KKDİK Md.47/1) |', '| --- | --- | --- | --- | --- |']
for r in rows:
    name = (r[0] or '').replace('|', '/').replace('\n', ' ')
    if r[1] and r[1] != '-':
        name += f' — {r[1]}'.replace('|', '/').replace('\n', ' ')
    md.append(f'| {name} | {r[2]} | {r[3]} | {r[4]} | {concern_tr(norm_concern(r[5]))} |')
open(MD, 'w', encoding='utf-8').write('\n'.join(md) + '\n')
print('md yazıldı')
