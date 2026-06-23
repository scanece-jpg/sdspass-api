"""
sds-knowledge/ Markdown Liste Üretici
=======================================
data/cl/ ve data/annex6/ JSON verilerinden annex6-liste.md ve
sea-ek6-liste.md dosyalarını yeniden oluşturur.

Düzeltilen sorunlar:
  - Boş h_code girişlerinden kaynaklanan trailing comma (H314, )
  - Çok uzun isimlerin tablo hücresinde satır kırması
  - SCL class alanları doldurulduktan sonra güncel veri

Kullanım:
  python scripts/generate_knowledge_lists.py
  python scripts/generate_knowledge_lists.py --dry-run   # sadece sayıları göster
"""

import io, json, sys, argparse
from pathlib import Path
from datetime import date

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

_ROOT      = Path(__file__).parent.parent
_CL        = _ROOT / 'data' / 'cl'
_A6        = _ROOT / 'data' / 'annex6'
_KNW       = _ROOT / 'sds-knowledge'
_OUT_CL    = _KNW  / 'sea-ek6-liste.md'
_OUT_A6    = _KNW  / 'annex6-liste.md'

NAME_MAX   = 65   # isim sütunu max karakter
SCL_MAX    = 50   # SCL sütunu max karakter


def _trunc(s: str, max_len: int) -> str:
    s = s.replace('\n', ' ').replace('\r', '').strip()
    if len(s) <= max_len:
        return s
    return s[:max_len - 3] + '...'


def _h_codes(hazards: list) -> str:
    """Hazards listesinden H kodlarını üret, boş ve duplicate'leri atla."""
    seen = set()
    parts = []
    for h in hazards:
        code = (h.get('h_code') or '').strip()
        if not code:
            continue  # Press.Gas gibi kasıtlı boş h_code — atla
        # Normalizasyon: H373(hearing_organs) gibi parantezli kodları koru
        base = code.split('(')[0][:4]
        # Not işareti
        marker = ' **' if h.get('note_flag') else ''
        full   = code + marker
        if full not in seen:
            seen.add(full)
            parts.append(full)
    return ', '.join(parts) if parts else '—'


def _m_factors(m_factors: dict) -> str:
    if not m_factors:
        return '—'
    parts = []
    acute   = m_factors.get('acute')   or m_factors.get('Acute')
    chronic = m_factors.get('chronic') or m_factors.get('Chronic')
    if acute:
        parts.append(f'Akut={acute}')
    if chronic:
        parts.append(f'Kr={chronic}')
    return ' / '.join(parts) if parts else '—'


def _scl(scl_limits: list) -> str:
    if not scl_limits:
        return '—'
    parts = []
    for s in scl_limits:
        hc    = (s.get('h_code') or '').strip()
        c_min = s.get('c_min')
        if hc and c_min is not None:
            parts.append(f'{hc}:{c_min}%')
    if not parts:
        return '—'
    joined = '; '.join(parts)
    return _trunc(joined, SCL_MAX)


def load_dir(directory: Path) -> list:
    """Dizindeki tüm JSON'ları oku, CAS'a göre sırala."""
    entries = []
    for path in sorted(directory.rglob('*.json')):
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
            entries.append(data)
        except json.JSONDecodeError:
            pass
    entries.sort(key=lambda x: x.get('cas', ''))
    return entries


def build_row(data: dict, use_tr_name: bool) -> str:
    cas     = data.get('cas', '—')
    name    = data.get('name_tr', '') if use_tr_name else ''
    if not name:
        name = data.get('name', '')
    name    = _trunc(name, NAME_MAX)
    clf     = data.get('classification', {})
    hazards = clf.get('hazards', [])
    h_col   = _h_codes(hazards)
    m_col   = _m_factors(clf.get('m_factors', {}))
    scl_col = _scl(clf.get('scl_limits', []))
    atp     = data.get('atp', '—') or '—'
    return f'| {cas} | {name} | {h_col} | {m_col} | {scl_col} | {atp} |'


def generate(directory: Path, out_path: Path, use_tr_name: bool,
             title: str, source_note: str, dry_run: bool):
    entries = load_dir(directory)
    today   = date.today().strftime('%Y-%m-%d')
    count   = len(entries)

    if dry_run:
        print(f'  {out_path.name}: {count} madde — (dry-run, yazılmadı)')
        return

    name_col = 'Ad (TR)' if use_tr_name else 'Ad'
    lines = [
        f'# {title}',
        f'# Kaynak: {source_note}',
        f'# Tarih: {today} | Madde sayısı: {count}',
        f'# Kullanım: CAS numarasıyla arama yapın',
        '',
        f'| CAS | {name_col} | H Kodları | M-Faktör (Akut/Kronik) | SCL | ATP |',
        f'|-----|{"-"*(len(name_col)+2)}|-----------|------------------------|-----|-----|',
    ]

    for data in entries:
        lines.append(build_row(data, use_tr_name))

    out_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f'  {out_path.name}: {count} madde yazıldı → {out_path}')


def main():
    parser = argparse.ArgumentParser(description='sds-knowledge liste üretici')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    print(f'\n{"="*60}')
    print('  SDS-KNOWLEDGE LİSTE ÜRETİCİ')
    print(f'{"="*60}\n')

    generate(
        directory  = _CL,
        out_path   = _OUT_CL,
        use_tr_name= True,
        title      = 'SEA Ek-6 / KKDİK Ek-6 — Türkiye Harmonize Sınıflandırma Listesi',
        source_note= 'SDSPass data/cl (KKDİK Ek-6 tabanlı)',
        dry_run    = args.dry_run,
    )

    generate(
        directory  = _A6,
        out_path   = _OUT_A6,
        use_tr_name= False,
        title      = 'CLP Annex VI — Uyumlaştırılmış Sınıflandırma Listesi',
        source_note= 'SDSPass data/annex6 (ATP21 + ATP22 kısmi)',
        dry_run    = args.dry_run,
    )

    print()


if __name__ == '__main__':
    main()
