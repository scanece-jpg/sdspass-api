"""
SCL Class Alanı Düzeltme Scripti — QA (a1) Fix
================================================
data/cl/ ve data/annex6/ altındaki JSON dosyalarında
scl_limits içindeki boş 'class' alanlarını doldurur.

Kural seti:
  H317 → "Skin Sens. 1"         (tek kategori, CLP §3.4)
  H318 → "Eye Dam. 1"           (tek kategori, CLP §3.3)
  H314 → çıkarım kuralı:
    - Aynı CAS için 2+ H314 bandı varsa:
        c_max=None (üst bant) → hazards listesindeki class (genellikle 1A)
        c_max dolu (alt bant) → "Skin Corr. 1B"
    - Tek H314 bandı:
        hazards listesindeki H314 class'ını kullan
    - Hazards'da da boşsa → SKIP (manuel inceleme gerekir)

Kullanım:
  python scripts/fix_scl_class.py --dry-run          # ne yapacağını göster, değiştirme
  python scripts/fix_scl_class.py                    # data/cl/ düzelt
  python scripts/fix_scl_class.py --dir annex6       # data/annex6/ düzelt
  python scripts/fix_scl_class.py --dir her ikisi    # her ikisini düzelt
  python scripts/fix_scl_class.py --cas 1310-73-2    # tek madde
"""

import io, json, sys, argparse, collections
from pathlib import Path
from typing import Optional

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

_ROOT   = Path(__file__).parent.parent
_CL     = _ROOT / 'data' / 'cl'
_A6     = _ROOT / 'data' / 'annex6'

# ── Sabit kural haritası ─────────────────────────────────────────────────────
SINGLE_CAT = {
    'H317': 'Skin Sens. 1',
    'H318': 'Eye Dam. 1',
    'H315': 'Skin Irrit. 2',
    'H319': 'Eye Irrit. 2',
    'H335': 'STOT SE 3',
    'H336': 'STOT SE 3',
}

def _hazards_class(hazards: list, h_code: str) -> Optional[str]:
    """Hazards listesinden h_code için dolu class döner, yoksa None."""
    for h in hazards:
        if (h.get('h_code') or '') == h_code:
            cls = (h.get('class') or '').strip()
            if cls:
                return cls
    return None

def _infer_h314_class(scl_limits: list, idx: int, hazards: list) -> Optional[str]:
    """
    SCL listesindeki idx'inci H314 girişi için class çıkar.
    Önce konum/bant analizine bakar, sonra hazards listesine.
    """
    h314_bands = [(i, s) for i, s in enumerate(scl_limits) if s.get('h_code') == 'H314']

    if len(h314_bands) == 0:
        return None

    if len(h314_bands) == 1:
        # Tek bant: hazards listesinden al
        return _hazards_class(hazards, 'H314')

    # Birden fazla bant: c_min'e göre büyükten küçüğe sırala
    # En büyük c_min + c_max=None → 1A (üst sınır yok = üst bant)
    # Diğerleri → 1B
    sorted_bands = sorted(h314_bands, key=lambda x: (x[1].get('c_min') or 0), reverse=True)

    for rank, (band_idx, _) in enumerate(sorted_bands):
        if band_idx == idx:
            if rank == 0:
                # Üst bant: hazards'tan al (genellikle 1A), bulamazsa 1A ver
                from_hz = _hazards_class(hazards, 'H314')
                return from_hz if from_hz else 'Skin Corr. 1A'
            else:
                return 'Skin Corr. 1B'
    return None

def fix_file(path: Path, dry_run: bool) -> dict:
    """
    Tek JSON dosyasını düzelt.
    Döner: {'fixed': int, 'skipped': int, 'details': list}
    """
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except json.JSONDecodeError as e:
        return {'fixed': 0, 'skipped': 0, 'details': [f'JSON parse hatası: {e}']}

    scl = data.get('classification', {}).get('scl_limits', [])
    hazards = data.get('classification', {}).get('hazards', [])
    changed = 0
    skipped = 0
    details = []

    for i, entry in enumerate(scl):
        h_code = entry.get('h_code') or ''
        cls    = (entry.get('class') or '').strip()
        if cls:
            continue  # zaten dolu, atla

        new_cls: Optional[str] = None

        if h_code in SINGLE_CAT:
            new_cls = SINGLE_CAT[h_code]
        elif h_code == 'H314':
            new_cls = _infer_h314_class(scl, i, hazards)
        # H372/H373 gibi organ-spesifik kodlar → SKIP (organ bilgisi gerekli)

        if new_cls:
            details.append(f'  scl[{i}] {h_code}: "" → "{new_cls}"')
            if not dry_run:
                entry['class'] = new_cls
            changed += 1
        elif h_code:
            details.append(f'  scl[{i}] {h_code}: SKIP — çıkarım yapılamadı')
            skipped += 1

    if changed > 0 and not dry_run:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

    return {'fixed': changed, 'skipped': skipped, 'details': details}


def main():
    parser = argparse.ArgumentParser(description='SCL class alanı düzeltme')
    parser.add_argument('--dry-run', action='store_true', help='Değişiklik yapma, sadece göster')
    parser.add_argument('--dir',     choices=['cl', 'annex6', 'her ikisi'], default='cl')
    parser.add_argument('--cas',     type=str, help='Tek CAS no')
    parser.add_argument('--verbose', action='store_true', help='Her dosya için detay göster')
    args = parser.parse_args()

    if args.dir == 'cl':
        search_dirs = [_CL]
    elif args.dir == 'annex6':
        search_dirs = [_A6]
    else:
        search_dirs = [_CL, _A6]

    # Dosya listesi
    if args.cas:
        cas = args.cas.strip()
        prefix = cas.split('-')[0]
        targets = []
        for d in search_dirs:
            targets += list(d.glob(f'{prefix}/{cas}.json'))
            if not targets:
                targets += list(d.rglob(f'{cas}.json'))
        if not targets:
            print(f'HATA: {cas}.json bulunamadı')
            sys.exit(1)
    else:
        targets = []
        for d in search_dirs:
            targets.extend(sorted(d.rglob('*.json')))

    mode = 'DRY-RUN' if args.dry_run else 'FIX'
    print(f'\n{"="*65}')
    print(f'  SCL CLASS FIX — {mode} — {len(targets)} dosya')
    print(f'{"="*65}\n')

    total_fixed = 0
    total_skipped = 0
    files_changed = 0

    for path in targets:
        result = fix_file(path, dry_run=args.dry_run)
        if result['fixed'] > 0 or result['skipped'] > 0:
            files_changed += 1
            total_fixed   += result['fixed']
            total_skipped += result['skipped']
            if args.verbose or args.cas or args.dry_run:
                cas_id = path.stem
                status = '(DRY)' if args.dry_run else '(FIXED)'
                print(f'  {cas_id} {status}:')
                for d in result['details']:
                    print(d)
                print()

    print(f'{"="*65}')
    print(f'  Etkilenen dosya  : {files_changed}')
    print(f'  Düzeltilen giriş : {total_fixed}')
    print(f'  Atlanan (SKIP)   : {total_skipped}')
    print(f'{"="*65}\n')

    if total_skipped > 0:
        print(f'  NOT: {total_skipped} giriş çıkarılamadı (H372/H373 gibi organ-spesifik kodlar).')
        print('  Bunları manuel incelemek için: python scripts/scan_annex6_gaps.py --dir cl --csv\n')


if __name__ == '__main__':
    main()
