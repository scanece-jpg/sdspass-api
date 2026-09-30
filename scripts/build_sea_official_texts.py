"""
build_sea_official_texts.py — SEA Yönetmeliği eklerinden resmî Türkçe P ve EUH metinlerini çıkarır.

Kaynak : sds-knowledge/tr/7.5.19108-Ek.docx (RG 10.12.2020/31330, mevzuat.gov.tr ekleri)
Çıktı  : data/sea_official_texts.json  {"p": {kod: metin}, "euh": {kod: metin}}

P metinleri: Ek-4 İkinci Bölüm ("Önlem ifadeleri") — SEA Md. 24(4) gereği etikette bu metin
kullanılır; orada olmayanlar Birinci Bölüm tablolarından alınır. Sayfa sonunda bölünmüş satırlar
için kod başına en uzun hücre alınır; kaynaktaki kelime içi boşluklar ("gazı nı") temiz metinlerle
kurulan sözlüğe göre birleştirilir.
EUH metinleri: Ek-2 tabloları ve "EUHxxx — “…”" biçimindeki paragraflar.
"""
import collections
import json
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

ROOT = Path(__file__).parent.parent
SRC = ROOT / 'sds-knowledge' / 'tr' / '7.5.19108-Ek.docx'
OUT = ROOT / 'data' / 'sea_official_texts.json'
W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
PCODE = re.compile(r'P\d{3}(?:\+P\d{3})*')


def _cell(tc):
    return re.sub(r'\s+', ' ', ' '.join(''.join(t.text or '' for t in p.iter(W + 't'))
                                        for p in tc.iter(W + 'p'))).strip()


def _tok(s):
    return re.findall(r"[A-Za-zÇĞİÖŞÜçğıöşü']+", s.lower())


def _tidy(s):
    s = re.sub(r'\](?=[A-Za-zÇĞİÖŞÜçğıöşü])', '] ', s)
    s = re.sub(r'\s+([.,;:])', r'\1', s)
    return re.sub(r'\s+', ' ', s).strip()


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    root = ET.fromstring(zipfile.ZipFile(SRC).read('word/document.xml'))
    body = list(root.find(W + 'body'))

    # Ek-4 İkinci Bölüm başlangıcı: "İKİNCİ BÖLÜM ÖNLEM İFADELERİ" paragrafından sonraki tablolar
    part2_from, ti = None, -1
    for el in body:
        if el.tag == W + 'tbl':
            ti += 1
        elif el.tag == W + 'p' and part2_from is None:
            t = ''.join(x.text or '' for x in el.iter(W + 't'))
            if re.search(r'İKİNCİ BÖLÜM\s*ÖNLEM İFADELERİ', re.sub(r'\s+', ' ', t)):
                part2_from = ti + 1
    tables = [el for el in body if el.tag == W + 'tbl']

    part1, part2, euh = collections.defaultdict(list), collections.defaultdict(list), {}
    for i, tbl in enumerate(tables):
        for tr in tbl.iter(W + 'tr'):
            tcs = tr.findall(W + 'tc')
            if len(tcs) < 2:
                continue
            c0, c1 = _cell(tcs[0]).replace(' ', ''), _cell(tcs[1])
            if not c1:
                continue
            if PCODE.fullmatch(c0):
                (part2 if part2_from is not None and i >= part2_from else part1)[c0].append(c1)
            elif re.fullmatch(r'EUH\d{3}A?', c0):
                euh.setdefault(c0, c1)
    for el in root.iter(W + 'p'):
        t = re.sub(r'\s+', ' ', ''.join(x.text or '' for x in el.iter(W + 't')))
        for m in re.finditer(r'(EUH\d{3}A?)\s*[—–\-:]?\s*[“"]([^”"]{8,220})[”"]', t):
            euh.setdefault(m.group(1), m.group(2).strip())

    vocab = set()
    for v in list(part2.values()) + list(part1.values()):
        for s in v:
            vocab |= {w for w in _tok(s) if len(w) > 3}

    def repair(s):
        out = []
        for w in s.split(' '):
            if out and out[-1][-1:].isalpha() and w[:1].isalpha():
                a, b = _tok(out[-1])[-1], _tok(w)[0]
                if a + b in vocab and (a not in vocab or b not in vocab):
                    out[-1] += w
                    continue
            out.append(w)
        return ' '.join(out)

    p = {}
    for code in set(part1) | set(part2):
        src = part2.get(code) or part1.get(code)
        p[code] = _tidy(repair(max(src, key=len)))
    euh = {k: _tidy(v) for k, v in euh.items()}
    OUT.write_text(json.dumps({'source': 'SEA Yönetmeliği ekleri, RG 10.12.2020/31330',
                               'p': dict(sorted(p.items())), 'euh': dict(sorted(euh.items()))},
                              ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'P: {len(p)} (İkinci Bölüm: {len(part2)}) | EUH: {len(euh)} → {OUT}')


if __name__ == '__main__':
    main()
