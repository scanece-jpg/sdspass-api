"""ta_cand.json + ta_cas.json → data/adr_cas_map.json (CAS → Tablo A adlı giriş satırları) + inceleme listesi.
Doğrulama: maddenin SEA/CLP sınıflandırmasından türeyen ADR sınıfları Tablo A sınıfını içermiyorsa satır alınmaz."""
import sys, os, re, json, io
HERE = os.path.dirname(os.path.abspath(sys.argv[0]))
os.chdir(r'C:\Users\DİPOL KİMYA\cl\sdspass-api'); sys.path.insert(0, '.'); sys.stdout.reconfigure(encoding='utf-8')
from app.services.transport_engine import H_TO_ADR
from app.services.transport_adr_service import _SEED_ENTRIES
CAND = json.load(open(os.path.join(HERE, 'ta_cand.json'), encoding='utf-8'))
CASM = json.load(open(os.path.join(HERE, 'ta_cas.json'), encoding='utf-8'))
DB = json.load(open('data/substance_db.json', encoding='utf-8'))
NUM = r'(\d+(?:[.,]\d+)?)\s*%'


def cond(name, base):
    """Ad içindeki derişim koşulu → (min, max, min_exclusive) ya da None (ayrıştırılamaz / maddeye ait değil)."""
    t = name.lower()
    if re.search(r'water|alcohol|nitrogen|available chlorine|phlegmatiz|solvent|inert|lactose|plasticiz', t):
        return None
    lo, hi, ex = 0.0, 100.0, False
    m = re.search(r'not less than ' + NUM + r'.*?(?:not more than|less than) ' + NUM, t)
    if m:
        return float(m.group(1).replace(',', '.')), float(m.group(2).replace(',', '.')), False
    m = re.search(r'more than ' + NUM + r'.*?(?:not more than|less than) ' + NUM, t)
    if m and 'not more than ' + m.group(1) not in t.split('but')[0]:
        return float(m.group(1).replace(',', '.')), float(m.group(2).replace(',', '.')), True
    m = re.search(r'not more than ' + NUM, t) or re.search(r'(?<!not )less than ' + NUM, t)
    if m:
        return 0.0, float(m.group(1).replace(',', '.')), False
    m = re.search(r'not less than ' + NUM, t)
    if m:
        return float(m.group(1).replace(',', '.')), 100.0, False
    m = re.search(r'more than ' + NUM, t)
    if m:
        return float(m.group(1).replace(',', '.')), 100.0, True
    return None


def classes_of(cas):
    e = DB.get(cas)
    if not e:
        return None
    try:
        cl = eval(e.get('classification') or '[]') if isinstance(e.get('classification'), str) else e.get('classification')
    except Exception:
        return None
    out = set()
    for x in cl or []:
        h = str(x.get('h_code', ''))[:4]
        if h in H_TO_ADR:
            out.add(H_TO_ADR[h]['class'])
        if h in ('H314', 'H290'):
            out.add('8')
        if h[:3] in ('H30', 'H31', 'H33') and h[:4] in ('H300', 'H301', 'H310', 'H311', 'H330', 'H331'):
            out.add('6.1')
    return out


rows, review = {}, []
for x in CAND:
    m = CASM.get(x['base'])
    if not m:
        review.append((x['un'], 'CAS bulunamadı', x['name'][:80])); continue
    cas = m['cas']
    if cas in _SEED_ENTRIES:
        continue
    r = {'un': x['un'], 'pg': x['pgs'][0] if x['pgs'] else ''}
    if x['state']:
        r['physical_state'] = x['state']
    if x['kosul'] and len(x['pgs']) > 1 and x['un'] not in ('UN1297',):
        review.append((x['un'], 'Tablo A içinde birden çok derişim satırı — veri dosyasındaki ad tek satırı gösteriyor', x['name'][:80]))
        continue
    if x['kosul']:
        c = cond(x['name'], x['base'])
        if not c:
            review.append((x['un'], 'derişim koşulu ayrıştırılamadı', x['name'][:90])); continue
        r['min_conc'], r['max_conc'] = c[0], c[1]
        if c[2]:
            r['min_exclusive'] = True
        r['pg_fixed'] = len(x['pgs']) == 1
    cls = classes_of(cas)                      # None: madde Ek-6'da yok
    t = m.get('tum') or {}
    k = m['kaynak']
    uyum = cls is not None and (x['cls'] in cls or (x['cls'].startswith('2') and any(c.startswith('2') for c in cls)))
    if k == 'substance_db':
        kabul, neden = True, 'Ek-6 tek ad eşleşmesi'
    elif k == 'pubchem':
        kabul, neden = (not t.get('wd') or cas in t['wd']), 'PubChem birebir ad'
    else:   # wikidata / wikidata+substance_db
        kabul = uyum or t.get('pc') == cas
        neden = 'Wikidata + ' + ('Ek-6 sınıfı uyumlu' if uyum else 'PubChem aynı CAS')
    if kabul and cls is not None and not cls and x['cls'] not in ('9',) and k != 'substance_db':
        kabul = False          # Ek-6'da var ama taşımaya ilişkin hiçbir zararı yok (örn. sitrik asit ↔ HCl)
    if not kabul:
        review.append((x['un'], f'kaynak doğrulanamadı ({k}, Ek-6 sınıfları {sorted(cls) if cls is not None else "yok"}, {cas})',
                       x['name'][:70])); continue
    r['_kaynak'] = neden
    rows.setdefault(cas, []).append(r)
# Aynı CAS: koşullu satırlar önce, hal belirtilmiş satırlar önce
for cas, lst in rows.items():
    lst.sort(key=lambda r: ('min_conc' not in r, 'physical_state' not in r))
out = {'kaynak': 'ADR 2025 Tablo A (ECE/TRANS/352) adları; CAS: substance_db (SEA Ek-6) veya PubChem eş anlamlıları. '
                 'scripts dışı üretim 2026-10-10; elle eklenen seed girişleri (transport_adr_service._SEED_ENTRIES) önceliklidir.',
       'harita': rows}
io.open('data/adr_cas_map.json', 'w', encoding='utf-8', newline='').write(json.dumps(out, ensure_ascii=False, indent=1))
io.open(os.path.join(HERE, 'ta_inceleme.txt'), 'w', encoding='utf-8').write('\n'.join(' | '.join(r) for r in review))
nr = sum(len(v) for v in rows.values())
nd = sum(1 for v in rows.values() for r in v if r['_kaynak'] == 'PubChem birebir ad')
print(f'{len(rows)} CAS, {nr} satır yazıldı ({nd} satır yalnız PubChem ad eşleşmesiyle); inceleme listesi: {len(review)}')
from collections import Counter
print(Counter(r[1].split(':')[0] for r in review))
