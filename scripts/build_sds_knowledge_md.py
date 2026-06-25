"""
build_sds_knowledge_md.py — sds-knowledge/ MD dosyalarını yeniden üretir.

Çıktılar:
  sds-knowledge/sea-ek6-liste.md   ← sea_ek6_raw.xml (tüm girdiler, CAS'sız dahil)
  sds-knowledge/annex6-liste.md    ← data/substance_db.json (ECHA ATP22 tam)
"""

import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT      = Path(__file__).parent.parent
XML_PATH  = ROOT / "scripts" / "sea_ek6_raw.xml"
DB_PATH   = ROOT / "data" / "substance_db.json"
SEA_OUT   = ROOT / "sds-knowledge" / "sea-ek6-liste.md"
AX6_OUT   = ROOT / "sds-knowledge" / "annex6-liste.md"

NS = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}


def _esc(s: str) -> str:
    """Markdown tablo hücresi için | ve newline escape."""
    return s.replace('|', '\\|').replace('\n', ' / ').strip()


# ---------------------------------------------------------------------------
# 1. sea-ek6-liste.md — XML'den doğrudan üret
# ---------------------------------------------------------------------------

def build_sea_ek6_md():
    xml_str = XML_PATH.read_text(encoding='utf-8')
    root    = ET.fromstring(xml_str)
    tables  = root.findall('.//w:tbl', NS)
    rows    = tables[0].findall('w:tr', NS)

    def cell_text(cell) -> str:
        lines = []
        for p in cell.findall('.//w:p', NS):
            line = ''.join(t.text or '' for t in p.findall('.//w:t', NS)).replace('\xa0', ' ').strip()
            if line:
                lines.append(line)
        return '\n'.join(lines)

    def clean_cas(raw: str) -> str:
        return re.sub(r'\s*\[\d+\]', '', raw).replace('\n', ', ').strip()

    lines = []
    lines.append('# SEA Ek-6 / KKDİK Ek-6 — Türkiye Harmonize Sınıflandırma Listesi')
    lines.append('# Kaynak: sea_ek6_raw.xml (SEA Ek-6 Word belgesi, ATP22 uyumlu)')
    lines.append('')

    # Bölüm 1: CAS'lı maddeler
    lines.append('## CAS Numaralı Maddeler')
    lines.append('')
    lines.append('| Index No | Madde Adı (TR) | Madde Adı (EN) | EC No | CAS No | Tehlike Sınıfı | H Kodu | Notlar |')
    lines.append('|---|---|---|---|---|---|---|---|')

    cas_count = 0
    group_rows = []

    for row in rows[2:]:
        cells = row.findall('w:tc', NS)
        if len(cells) < 8:
            continue

        index_no = _esc(cell_text(cells[0]))
        name_en  = _esc(cell_text(cells[1]))
        name_tr  = _esc(cell_text(cells[2]))
        notes    = _esc(cell_text(cells[3]))
        ec_no    = _esc(cell_text(cells[4]))
        cas_raw  = cell_text(cells[5])
        class_raw = cell_text(cells[6]) if len(cells) > 6 else ''
        hcode_raw = cell_text(cells[7]) if len(cells) > 7 else ''

        # Sınıf + H kodu — her satırı ayrı, araya ' | ' koy
        cls_lines = [l.strip() for l in class_raw.split('\n') if l.strip()]
        hc_lines  = [l.strip() for l in hcode_raw.split('\n') if l.strip()]
        cls_str   = _esc(' / '.join(cls_lines)) or '-'
        hc_str    = _esc(' / '.join(hc_lines)) or '-'

        # CAS'sız → grup bölümüne
        if not cas_raw or cas_raw.strip() in ('-', ''):
            group_rows.append((index_no, name_tr, name_en, ec_no, cls_str, hc_str, notes))
            continue

        cas_clean = _esc(clean_cas(cas_raw))
        lines.append(f'| {index_no} | {name_tr} | {name_en} | {ec_no} | {cas_clean} | {cls_str} | {hc_str} | {notes} |')
        cas_count += 1

    # Bölüm 2: CAS'sız grup girdileri
    lines.append('')
    lines.append('## Grup Girdileri (CAS Numarası Yok)')
    lines.append('')
    lines.append('> Bu maddeler belirli bir CAS numarasına değil, madde grubuna uygulanır.')
    lines.append('')
    lines.append('| Index No | Madde Adı (TR) | Madde Adı (EN) | EC No | Tehlike Sınıfı | H Kodu | Notlar |')
    lines.append('|---|---|---|---|---|---|---|')

    for idx, name_tr, name_en, ec_no, cls_str, hc_str, notes in group_rows:
        lines.append(f'| {idx} | {name_tr} | {name_en} | {ec_no} | {cls_str} | {hc_str} | {notes} |')

    content = '\n'.join(lines)
    SEA_OUT.write_text(content, encoding='utf-8')
    return cas_count, len(group_rows)


# ---------------------------------------------------------------------------
# 2. annex6-liste.md — substance_db.json'dan üret (ECHA ATP22 tam)
# ---------------------------------------------------------------------------

def build_annex6_md():
    db = json.loads(DB_PATH.read_text(encoding='utf-8'))
    real = {k: v for k, v in db.items() if '_alias' not in v}

    lines = []
    lines.append('# CLP Annex VI — Uyumlaştırılmış Sınıflandırma Listesi (ECHA ATP22)')
    lines.append('# Kaynak: data/substance_db.json (ECHA ATP22 tam)')
    lines.append(f'# Madde sayısı: {len(real)}')
    lines.append('')
    lines.append('| Index No | Madde Adı (EN) | EC No | CAS No | Tehlike Sınıfı | H Kodu | Notlar | ATP |')
    lines.append('|---|---|---|---|---|---|---|---|')

    for cas, e in sorted(real.items(), key=lambda x: x[1].get('index_no', '')):
        index_no = _esc(e.get('index_no', '') or '')
        names    = _esc('; '.join(e.get('names', [])))
        ec_no    = _esc(e.get('ec_no', '') or '')
        cls_list = e.get('classification', [])
        cls_str  = _esc(' / '.join(c.get('class', '') for c in cls_list if c.get('class'))) or '-'
        hc_str   = _esc(' / '.join(c.get('h_code', '') for c in cls_list if c.get('h_code'))) or '-'
        notes    = _esc(', '.join(e.get('notes', []))) or '-'
        atp      = _esc(e.get('atp', '') or '')
        lines.append(f'| {index_no} | {names} | {ec_no} | {cas} | {cls_str} | {hc_str} | {notes} | {atp} |')

    content = '\n'.join(lines)
    AX6_OUT.write_text(content, encoding='utf-8')
    return len(real)


# ---------------------------------------------------------------------------
# Ana akış
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')

    print('sea-ek6-liste.md üretiliyor...')
    cas_count, group_count = build_sea_ek6_md()
    size = SEA_OUT.stat().st_size / 1024
    print(f'  CAS\'lı madde : {cas_count}')
    print(f'  Grup girdisi : {group_count}')
    print(f'  Toplam       : {cas_count + group_count}')
    print(f'  Boyut        : {size:.0f} KB')

    print()
    print('annex6-liste.md üretiliyor...')
    ax_count = build_annex6_md()
    size2 = AX6_OUT.stat().st_size / 1024
    print(f'  Madde sayısı : {ax_count}')
    print(f'  Boyut        : {size2:.0f} KB')

    print()
    print('Tamamlandı.')
