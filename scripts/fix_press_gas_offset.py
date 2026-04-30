"""
Press. Gas Offset Düzeltme Scripti
====================================
cl/ verisinde 'Press. Gas' sınıfının yanlış H koduyla eşleştiği
(kayma hatası) dosyaları tespit edip annex6/ verisinden düzeltir.

Kullanım:
  python scripts/fix_press_gas_offset.py [--dry-run]
"""

import json, re, argparse
from pathlib import Path

_ROOT   = Path(__file__).parent.parent
_CL_DIR = _ROOT / 'data' / 'cl'
_AX_DIR = _ROOT / 'data' / 'annex6'

# Press. Gas veya Flam. Gas'a ait OLMAYAN H kodları
# (bu kodlar söz konusu sınıfla eşleşirse kayma var demektir)
_GAS_CODES = {'H220', 'H221', 'H222', 'H223', 'H228', 'H229',
               'H280', 'H281', 'H232'}


def _has_offset(hazards: list) -> bool:
    """Hazard listesinde Press./Flam. Gas + yanlış H kodu var mı?"""
    for h in hazards:
        cls  = h.get('class', '')
        code = re.sub(r'[^A-Z0-9]', '', h.get('h_code', '').upper())[:4]
        if ('Press. Gas' in cls or 'Flam. Gas' in cls) and code and code not in _GAS_CODES:
            return True
    return False


def _read(p: Path) -> dict | None:
    if p.exists():
        try:
            return json.loads(p.read_text(encoding='utf-8'))
        except Exception:
            return None
    return None


def _write(p: Path, d: dict):
    p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')


def fix_all(dry_run: bool = False):
    fixed = []
    no_ax = []
    clean = []

    for cl_file in sorted(_CL_DIR.rglob('*.json')):
        cas = cl_file.stem
        cl  = _read(cl_file)
        if not cl:
            continue

        hazards = cl.get('classification', {}).get('hazards', [])
        if not _has_offset(hazards):
            clean.append(cas)
            continue

        # annex6/ verisini al
        ax = _read(_AX_DIR / cas[:2] / f'{cas}.json')
        if not ax:
            no_ax.append(cas)
            continue

        ax_hazards = ax.get('classification', {}).get('hazards', [])

        if not dry_run:
            # Sadece hazardları ve etiket H kodlarını annex6/'dan al,
            # geri kalan alanları (name_tr, scl_limits, m_factors, notes) koru
            cl['classification']['hazards'] = ax_hazards
            cl['labelling']['h_codes'] = [
                h['h_code'] for h in ax_hazards if h.get('h_code')
            ]
            cl['labelling']['signal']     = ax['labelling'].get('signal', cl['labelling'].get('signal', ''))
            cl['labelling']['pictograms'] = ax['labelling'].get('pictograms', cl['labelling'].get('pictograms', []))

            # ATP ve not güncelle
            cl['atp'] = ax.get('atp', cl.get('atp', ''))
            notes = cl.get('notes', [])
            note  = 'Press.Gas kayma hatası düzeltildi: hazardlar Annex VI ATP22 verisinden yeniden oluşturuldu.'
            if note not in notes:
                notes.append(note)
            cl['notes'] = notes

            _write(cl_file, cl)

        fixed.append(f'{cas} ({cl.get("name","")[:40]})')

    print(f'Düzeltilen : {len(fixed)}')
    print(f'annex6 yok : {len(no_ax)}')
    print(f'Temiz      : {len(clean)}')

    if fixed:
        print('\nDüzeltilen dosyalar:')
        for f in fixed:
            try:
                print(f'  ✓ {f}')
            except UnicodeEncodeError:
                print(f'  + {f.encode("ascii", errors="replace").decode()}')

    if no_ax:
        print('\nannex6/ karşılığı olmayan (atlandı):')
        for c in no_ax:
            print(f'  - {c}')

    if dry_run:
        print('\n[DRY-RUN] Hicbir dosya degistirilmedi.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    fix_all(dry_run=args.dry_run)
