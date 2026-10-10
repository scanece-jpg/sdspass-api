"""Kaynak birleştirme → ta_cas.json (temel ad → CAS). Öncelik: substance_db ad eşleşmesi > Wikidata (UN→tek CAS) > PubChem önbelleği.
Wikidata eşleşmesi UN numarasıyla yapılır (ad ayrıştırması gerekmez); bir UN'a birden çok CAS düşüyorsa, substance_db'de
bulunan tek CAS seçilir, yoksa belirsiz sayılır."""
import sys, os, re, json, collections
HERE = os.path.dirname(os.path.abspath(sys.argv[0]))
os.chdir(r'C:\Users\DİPOL KİMYA\cl\sdspass-api'); sys.stdout.reconfigure(encoding='utf-8')
CAND = json.load(open(os.path.join(HERE, 'ta_cand.json'), encoding='utf-8'))
DB = json.load(open('data/substance_db.json', encoding='utf-8'))
_wdp = os.path.join(HERE, 'wd_un_cas.json')
if not os.path.exists(_wdp):   # Wikidata: UN numarası (P695) + CAS (P231) çiftleri — tek sorgu
    import httpx
    _r = httpx.get('https://query.wikidata.org/sparql', params={'format': 'json', 'query':
                   'SELECT ?item ?un ?cas WHERE { ?item wdt:P695 ?un . ?item wdt:P231 ?cas . }'},
                   headers={'User-Agent': 'SDSPass-ADR-mapping/1.0'}, timeout=120)
    json.dump([{'un': b['un']['value'], 'cas': b['cas']['value']} for b in _r.json()['results']['bindings']],
              open(_wdp, 'w', encoding='utf-8'))
WD = json.load(open(_wdp, encoding='utf-8'))
PC = json.load(open(os.path.join(HERE, 'ta_pubchem.json'), encoding='utf-8')) if os.path.exists(os.path.join(HERE, 'ta_pubchem.json')) else {}


def norm(s):
    s = s.upper().replace('SULPH', 'SULF').replace('ALUMINIUM', 'ALUMINUM').replace('CAESIUM', 'CESIUM')
    return re.sub(r'[^A-Z0-9]', '', s)


local = {}
for cas, e in DB.items():
    for fld in ('names', 'synonyms'):
        try:
            lst = eval(e.get(fld) or '[]') if isinstance(e.get(fld), str) else (e.get(fld) or [])
        except Exception:
            lst = []
        if fld == 'names' and len(lst) > 1:
            lst = []          # Ek-6 grup satırı (örn. "metilamin; dimetilamin; …") — tek CAS'a eşlenmez
        for n in lst:
            local.setdefault(norm(str(n)), set()).add(cas)
wd = collections.defaultdict(set)
for x in WD:
    wd['UN' + x['un'].strip().zfill(4)].add(x['cas'].strip())

res, src = {}, collections.Counter()
for x in CAND:
    b = x['base']
    if b in res:
        continue
    L = local.get(norm(b)) or local.get(norm(x.get('full') or b))
    if L and len(L) == 1:
        res[b] = {'cas': next(iter(L)), 'kaynak': 'substance_db'}; src['substance_db'] += 1; continue
    W = wd.get(x['un'])
    if W:
        if len(W) == 1:
            res[b] = {'cas': next(iter(W)), 'kaynak': 'wikidata'}; src['wikidata'] += 1; continue
        inDB = [c for c in W if c in DB]
        if len(inDB) == 1:
            res[b] = {'cas': inDB[0], 'kaynak': 'wikidata+substance_db'}; src['wikidata+db'] += 1; continue
        src['wikidata belirsiz'] += 1
    for q in (b, x.get('full') or b):
        if q in PC and PC[q]['cas']:
            res[b] = {'cas': PC[q]['cas'][0], 'kaynak': 'pubchem'}; src['pubchem'] += 1; break
# Çapraz kontrol: Wikidata ile diğer kaynak çelişiyor mu
conf = []
for x in CAND:
    r = res.get(x['base'])
    W = wd.get(x['un'])
    if r and W and r['kaynak'] != 'wikidata' and r['cas'] not in W:
        conf.append((x['un'], x['base'], r['cas'], r['kaynak'], sorted(W)))
for un, b, c, k, W in conf:
    res.pop(b, None)       # kaynaklar çelişiyor → haritaya girmez, inceleme listesine
json.dump(conf, open(os.path.join(HERE, 'ta_celiski.json'), 'w', encoding='utf-8'), ensure_ascii=False)
allsrc = {}
for x in CAND:
    b = x['base']
    L = local.get(norm(b)) or local.get(norm(x.get('full') or b))
    pc = next((PC[q]['cas'][0] for q in (b, x.get('full') or b) if q in PC and PC[q]['cas']), None)
    allsrc.setdefault(b, {'db': sorted(L) if L and len(L) == 1 else [], 'wd': sorted(wd.get(x['un']) or []), 'pc': pc})
for b, r in res.items():
    r['tum'] = allsrc.get(b)
json.dump(res, open(os.path.join(HERE, 'ta_cas.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
nb = len({x['base'] for x in CAND})
print(f'{nb} temel ad → {len(res)} CAS', dict(src), f'| bulunamayan {nb - len(res)} | kaynak çelişkisi {len(conf)}')
for c in conf[:15]:
    print('  çelişki', c)
