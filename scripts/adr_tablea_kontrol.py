"""ADR Tablo A kontrolü — data/adr_data.json, resmî ADR Tablo A (ECE/TRANS/352 Cilt I PDF) ile karşılaştırılır.
ADR 2027 çıkınca: yeni Cilt I PDF yolunu PDF değişkenine verin ve çalıştırın.
  python scripts/adr_tablea_kontrol.py            → farkları listeler
  python scripts/adr_tablea_kontrol.py --yaz      → sınıf / sınıflandırma kodu / tünel / Kemler düzeltir (PG listesine dokunmaz)
2026-10-09: ADR 2025 ile 97 fark düzeltildi."""
import fitz, io, re, json, sys
PDF = 'sds-knowledge/en/2412006_E_ECE_TRANS_352_Vol.I_WEB_0.pdf'
d = fitz.open(PDF)
CLS = re.compile(r'^(1|2|3|4\.1|4\.2|4\.3|5\.1|5\.2|6\.1|6\.2|7|8|9)$')
CODE = re.compile(r'^[0-9A-Z]{1,6}$')
PG = re.compile(r'^(I|II|III)$')
LAB = re.compile(r'^\+?(1|1\.[1-6]|2\.[123]|3|4\.[123]|5\.[12]|6\.[12]|7[AXE]?|8|9A?|\(\+13\))$')
UNL = re.compile(r'^\d{4}$')
left, right = {}, {}
for pno in range(len(d)):
    lines = [x.strip() for x in d[pno].get_text().split('\n')]
    txt = '\n'.join(lines)
    if '(Tunnel' in txt or 'Tunnel \nrestriction' in d[pno].get_text():
        # sağ sayfa: [veri][UN][ad] — veri UN'dan önce
        buf = []
        i = 0
        while i < len(lines):
            ln = lines[i]
            if UNL.match(ln) and i + 1 < len(lines) and re.search(r'[A-Z]{3}', lines[i + 1] or ''):
                tun = next((t for t in buf if re.match(r'^\((?:[A-E](?:/[A-E])?|—|-)\)$', t)), None)
                kem = next((t for t in reversed(buf) if re.match(r'^X?\d{2,3}X?$', t) and not t.startswith('0')), None)
                right.setdefault(ln, []).append({'tunnel': tun.strip('()') if tun else None, 'kemler': kem})
                buf = []
                i += 1
                while i < len(lines) and not (UNL.match(lines[i]) is None and re.match(r'^[A-Z]\w*\(|^[A-Z]{2}\d|^\(|^P|^L|^S|^C|^T|^\d', lines[i] or '') and not re.search(r'[a-z]', lines[i])) and re.search(r'[A-Za-z]', lines[i] or '') and len(lines[i]) > 6:
                    i += 1
                continue
            buf.append(ln)
            i += 1
    elif '(3a)' in txt or 'Classification' in txt:
        for i, ln in enumerate(lines):
            if not UNL.match(ln):
                continue
            j = i + 1
            while j < len(lines) and j < i + 12 and not CLS.match(lines[j]):
                j += 1
            if j >= len(lines) or j >= i + 12 or j + 1 >= len(lines):
                continue
            cls, code = lines[j], lines[j + 1]
            if not CODE.match(code):
                continue
            k = j + 2
            pg = None
            if k < len(lines) and PG.match(lines[k]):
                pg = lines[k]; k += 1
            labs = []
            while k < len(lines) and LAB.match(lines[k]):
                labs.append(lines[k].lstrip('+')); k += 1
            left.setdefault(ln, []).append({'cls': cls, 'code': code, 'pg': pg, 'labels': '+'.join(labs)})
T = {"left": left, "right": right}
L, R = T['left'], T['right']
p = 'data/adr_data.json'
A = json.load(open(p, encoding='utf-8'))
deg = []
for key, e in A.items():
    un = key.replace('UN', '')
    ls, rs = L.get(un) or [], R.get(un) or []
    clss = {x['cls'] for x in ls}
    codes = {x['code'] for x in ls}
    tuns = {x['tunnel'] for x in rs if x['tunnel']}
    kems = {x['kemler'] for x in rs if x['kemler']}
    if len(clss) == 1:
        c = next(iter(clss))
        if e.get('class') and e['class'] != c:
            deg.append((key, 'class', e['class'], c)); e['class'] = c
    if len(codes) == 1:
        c = next(iter(codes))
        if e.get('classification_code') and e['classification_code'] != c:
            deg.append((key, 'classification_code', e['classification_code'], c)); e['classification_code'] = c
        for pg, v in (e.get('packing_groups') or {}).items():
            if v.get('classification_code') and v['classification_code'] != c:
                deg.append((key, f'PG{pg}.classification_code', v['classification_code'], c)); v['classification_code'] = c
    if len(tuns) == 1:
        t = next(iter(tuns))
        if e.get('tunnel') and e['tunnel'] != t:
            deg.append((key, 'tunnel', e['tunnel'], t)); e['tunnel'] = t
        for pg, v in (e.get('packing_groups') or {}).items():
            if v.get('tunnel') and v['tunnel'] != t:
                deg.append((key, f'PG{pg}.tunnel', v['tunnel'], t)); v['tunnel'] = t
    if len(kems) == 1:
        k = next(iter(kems))
        if e.get('kemler') and e['kemler'] != k:
            deg.append((key, 'kemler', e['kemler'], k)); e['kemler'] = k
        for pg, v in (e.get('packing_groups') or {}).items():
            if v.get('kemler') and v['kemler'] != k:
                deg.append((key, f'PG{pg}.kemler', v['kemler'], k)); v['kemler'] = k
# Ambalaj grubu listeleri (2026-10-09: 301 girişte eksik/fazla PG düzeltildi) — yalnız raporlanır
for key, e in A.items():
    _pdf = {x['pg'] for x in (L.get(key.replace('UN', '')) or []) if x['pg']}
    _biz = set((e.get('packing_groups') or {}).keys()) or ({e['packing_group']} if e.get('packing_group') else set())
    if _pdf and _pdf != _biz:
        deg.append((key, 'PG listesi (elle düzeltin)', sorted(_biz), sorted(_pdf)))
print(len(deg), 'değişiklik')
for d in deg:
    print('  ', d)
if '--yaz' in sys.argv:
    io.open(p, 'w', encoding='utf-8', newline='').write(json.dumps(A, ensure_ascii=False, indent=2))
    print('yazıldı')
