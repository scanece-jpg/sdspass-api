"""Tablo A temel adı → CAS: önce yerel substance_db (Ek-6 adları/eş anlamlılar), yoksa PubChem (ad → eş anlamlılar → CAS).
Önbellek: ta_pubchem.json (yeniden çalıştırmada kaldığı yerden devam). PubChem: ~3 istek/sn."""
import sys, os, re, json, time
import httpx
HERE = os.path.dirname(os.path.abspath(sys.argv[0]))
os.chdir(r'C:\Users\DİPOL KİMYA\cl\sdspass-api'); sys.stdout.reconfigure(encoding='utf-8')
CAND = json.load(open(os.path.join(HERE, 'ta_cand.json'), encoding='utf-8'))
DB = json.load(open('data/substance_db.json', encoding='utf-8'))
CASRX = re.compile(r'^(\d{2,7})-(\d{2})-(\d)$')


def cas_ok(c):
    m = CASRX.match(c)
    if not m:
        return False
    d = (m.group(1) + m.group(2))[::-1]
    return sum((i + 1) * int(x) for i, x in enumerate(d)) % 10 == int(m.group(3))


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
        for n in lst:
            local.setdefault(norm(str(n)), set()).add(cas)

cache_p = os.path.join(HERE, 'ta_pubchem.json')
cache = json.load(open(cache_p, encoding='utf-8')) if os.path.exists(cache_p) else {}
bases = sorted({x['base'] for x in CAND})
FULL = {}
for x in CAND:
    FULL.setdefault(x['base'], set()).add(x.get('full') or x['base'])


def variants(b):
    out = []
    for q in sorted(FULL.get(b, {b})) + [b]:
        q2 = re.sub(r'(?<=[A-Za-z])-(?=[A-Za-z]{3})', '', q)   # PDF satır bölünmesinden kalan tire
        for v in (q, q2, re.sub(r'SULPH', 'SULF', q, flags=re.I), re.sub(r'SULPH', 'SULF', q2, flags=re.I),
                  re.sub(r'ALUMINIUM', 'ALUMINUM', q, flags=re.I)):
            if v not in out:
                out.append(v)
    return out
res, t0, n_pc = {}, time.time(), 0
with httpx.Client(timeout=30, headers={'User-Agent': 'SDSPass ADR TableA mapping'}) as cl:
    for b in bases:
        L = local.get(norm(b))
        if L and len(L) == 1:
            res[b] = {'cas': next(iter(L)), 'kaynak': 'substance_db'}
            continue
        for q in variants(b):
            if q in cache and cache[q]['cas']:
                break
            if q in cache and cache[q]['durum'] != 'hata':
                continue
            try:
                for _try in range(6):
                    r = cl.post('https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/synonyms/JSON', data={'name': q})
                    if r.status_code in (429, 503, 500, 502, 504):
                        time.sleep(30 * (_try + 1)); continue
                    break
                if r.status_code == 200:
                    syn = r.json()['InformationList']['Information'][0].get('Synonym', [])
                elif r.status_code == 404:
                    syn = []
                else:
                    syn = None   # sınırlama/hata — 'yok' sayılmaz, sonraki çalıştırmada yeniden denenir
            except Exception:
                syn = None
            cas = [x for x in (syn or []) if cas_ok(x)]
            cache[q] = {'cas': cas[:3], 'durum': 'hata' if syn is None else ('yok' if not cas else 'ok')}
            n_pc += 1
            if n_pc % 50 == 0:
                json.dump(cache, open(cache_p, 'w', encoding='utf-8'), ensure_ascii=False)
                print(f'  {n_pc} PubChem sorgusu, {time.time() - t0:.0f} sn', flush=True)
            time.sleep(0.6)
            if cas:
                break
        hit = next((cache[q] for q in variants(b) if q in cache and cache[q]['cas']), None)
        if hit:
            res[b] = {'cas': hit['cas'][0], 'alt': hit['cas'][1:], 'kaynak': 'pubchem'}
        continue
        if b not in cache:
            try:
                r = cl.get(f'https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{httpx.URL(b).raw_path.decode() if False else b}/synonyms/JSON')
                syn = r.json()['InformationList']['Information'][0].get('Synonym', []) if r.status_code == 200 else []
            except Exception as e:
                syn = None
            cas = [s for s in (syn or []) if cas_ok(s)]
            cache[b] = {'cas': cas[:3], 'durum': 'hata' if syn is None else ('yok' if not cas else 'ok')}
            n_pc += 1
            if n_pc % 50 == 0:
                json.dump(cache, open(cache_p, 'w', encoding='utf-8'), ensure_ascii=False)
                print(f'  {n_pc} PubChem sorgusu, {time.time() - t0:.0f} sn', flush=True)
            time.sleep(0.34)
        c = cache[b]
        if c['cas']:
            res[b] = {'cas': c['cas'][0], 'alt': c['cas'][1:], 'kaynak': 'pubchem'}
json.dump(cache, open(cache_p, 'w', encoding='utf-8'), ensure_ascii=False)
json.dump(res, open(os.path.join(HERE, 'ta_cas.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
src = {}
for v in res.values():
    src[v['kaynak']] = src.get(v['kaynak'], 0) + 1
print(len(bases), 'temel ad →', len(res), 'CAS bulundu', src, '| bulunamayan', len(bases) - len(res))
