"""ADR Tablo B (3.2.2, alfabetik dizin; eş anlamlılar dahil) × SEA Ek-6 (substance_db: CAS + adlar) → CAS ↔ UN.
Yalnız resmî kaynaklar. Çıktı: tb_cas.json (bu klasör; git dışı). Kullanım: python scripts/adr_cas_map/5_tablo_b.py"""
import sys, os, re, json, collections
HERE = os.path.dirname(os.path.abspath(sys.argv[0]))
ROOT = os.path.dirname(os.path.dirname(HERE))
os.chdir(ROOT); sys.stdout.reconfigure(encoding='utf-8')
import fitz
PDF = 'sds-knowledge/en/2412006_E_ECE_TRANS_352_Vol.I_WEB_0.pdf'
d = fitz.open(PDF)
start = next(p for p in range(540, len(d)) if 'Table B' in d[p].get_text())
HDR = ('Name and description', 'UN', 'No.', 'No. Class', 'Class', 'Remarks', 'Table B')
rows = []
for p in range(start, len(d)):
    L = [x.strip() for x in d[p].get_text().split('\n')]
    buf, i = [], 0
    while i < len(L):
        ln = L[i]
        if not ln or ln in HDR or re.fullmatch(r'-\s*\d+\s*-', ln):
            if not ln and buf and buf[-1] != '':
                pass
            i += 1; continue
        if re.fullmatch(r'\d{4}', ln) and buf:
            j = i + 1
            while j < len(L) and not L[j]:
                j += 1
            if j < len(L) and re.fullmatch(r'\d(\.\d)?', L[j]):
                ad = re.sub(r',?\s*see$', '', ' '.join(buf)).strip(' ,')
                rows.append((ad, ln, L[j])); buf = []; i = j + 1; continue
        buf.append(ln)
        if len(buf) > 6:
            buf = buf[-6:]
        i += 1
print('Tablo B satırı:', len(rows))


def norm(s):
    s = s.upper().replace('SULPH', 'SULF').replace('ALUMINIUM', 'ALUMINUM').replace('CAESIUM', 'CESIUM')
    s = re.sub(r'\b(SOLUTION|AQUEOUS|SOLID|LIQUID|ANHYDROUS|STABILIZED|INHIBITED|DRY|GLACIAL|MOLTEN)\b', '', s)
    return re.sub(r'[^A-Z0-9]', '', s)


DB = json.load(open('data/substance_db.json', encoding='utf-8'))
local = collections.defaultdict(set)
for cas, e in DB.items():
    for fld in ('names', 'synonyms'):
        try:
            lst = eval(e.get(fld) or '[]') if isinstance(e.get(fld), str) else (e.get(fld) or [])
        except Exception:
            lst = []
        if fld == 'names' and len(lst) > 1:
            continue                     # Ek-6 grup satırı
        for n in lst:
            local[norm(str(n))].add(cas)
by_un = collections.defaultdict(set)
for ad, un, cls in rows:
    if re.search(r'N\.O\.S|MIXTURE|ARTICLES?\b', ad, re.I):
        continue
    L = local.get(norm(re.split(r',\s', ad)[0]))
    if L and len(L) == 1:
        by_un['UN' + un].add(next(iter(L)))
out = {un: sorted(c) for un, c in by_un.items()}
json.dump(out, open(os.path.join(HERE, 'tb_cas.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
print('Tablo B × Ek-6 eşleşmesi:', len(out), 'UN,', sum(len(v) for v in out.values()), 'CAS')
