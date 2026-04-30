"""
cl/ Sertlik Düzeltme Scripti
=============================
annex6/ verisinde cl/ verisinden daha sıkı sınıf bulunan
maddeleri tespit edip cl/ dosyasını günceller.

Kullanım:
  python scripts/fix_cl_strict.py [--dry-run]
"""

import sys, json, re, argparse
from pathlib import Path

_ROOT    = Path(__file__).parent.parent
_CL_DIR  = _ROOT / 'data' / 'cl'
_AX_DIR  = _ROOT / 'data' / 'annex6'

_H_CLASS_GROUP: dict[str, str] = {
    'H224': 'flam_liq',   'H225': 'flam_liq',   'H226': 'flam_liq',
    'H300': 'acute_oral', 'H301': 'acute_oral',  'H302': 'acute_oral',
    'H310': 'acute_derm', 'H311': 'acute_derm',  'H312': 'acute_derm',
    'H330': 'acute_inh',  'H331': 'acute_inh',   'H332': 'acute_inh',
    'H314': 'skin',       'H315': 'skin',
    'H318': 'eye',        'H319': 'eye',
    'H317': 'skin_sens',  'H334': 'resp_sens',
    'H340': 'muta',       'H341': 'muta',
    'H350': 'carc',       'H351': 'carc',
    'H360': 'repr',       'H361': 'repr',        'H362': 'repr',
    'H370': 'stot_se',    'H371': 'stot_se',
    'H372': 'stot_re',    'H373': 'stot_re',
    'H400': 'aq_acute',   'H401': 'aq_acute',    'H402': 'aq_acute',
    'H410': 'aq_chron',   'H411': 'aq_chron',    'H412': 'aq_chron', 'H413': 'aq_chron',
}

_SEVERITY: dict[str, int] = {
    'H360': 1, 'H361': 2, 'H362': 3,
    'H340': 1, 'H341': 2,
    'H350': 1, 'H351': 2,
    'H300': 1, 'H301': 2, 'H302': 3,
    'H310': 1, 'H311': 2, 'H312': 3,
    'H330': 1, 'H331': 2, 'H332': 3,
    'H314': 1, 'H315': 2,
    'H318': 1, 'H319': 2,
    'H370': 1, 'H371': 2,
    'H372': 1, 'H373': 2,
    'H400': 1, 'H401': 2, 'H402': 3,
    'H410': 1, 'H411': 2, 'H412': 3, 'H413': 4,
}


def _h4(code: str) -> str:
    return re.sub(r'[^A-Z0-9]', '', str(code).upper())[:4]


def _is_stricter(new_code: str, old_code: str) -> bool:
    return _SEVERITY.get(_h4(new_code), 99) < _SEVERITY.get(_h4(old_code), 99)


def _read(path: Path) -> dict | None:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding='utf-8'))
        except Exception:
            return None
    return None


def _write(path: Path, data: dict):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def _cl_path(cas: str) -> Path:
    return _CL_DIR / cas[:2] / f'{cas}.json'


def _ax_path(cas: str) -> Path:
    return _AX_DIR / cas[:2] / f'{cas}.json'


def fix_all(dry_run: bool = False):
    # Tüm cl/ ve annex6/ dosyalarını tara
    fixed_cas  = []
    skip_cas   = []
    changes    = []

    cl_files = list(_CL_DIR.rglob('*.json'))
    print(f"cl/ dosya sayısı: {len(cl_files)}")
    print("Karşılaştırılıyor...\n")

    for cl_file in sorted(cl_files):
        cas = cl_file.stem
        ax  = _read(_ax_path(cas))
        if not ax:
            continue

        cl = _read(cl_file)
        if not cl:
            continue

        # cl/ hazardlarını grup → {h_code, class, index} şeklinde indexle
        cl_hazards = cl.get('classification', {}).get('hazards', [])
        cl_by_group: dict[str, dict] = {}
        for i, h in enumerate(cl_hazards):
            code  = _h4(h.get('h_code', ''))
            group = _H_CLASS_GROUP.get(code)
            if group:
                cl_by_group[group] = {'code': code, 'class': h.get('class', ''), 'idx': i}

        # annex6/ hazardlarıyla karşılaştır
        ax_hazards = ax.get('classification', {}).get('hazards', [])
        updated    = False
        cas_changes = []

        for ax_h in ax_hazards:
            ax_code  = _h4(ax_h.get('h_code', ''))
            ax_class = ax_h.get('class', '')
            group    = _H_CLASS_GROUP.get(ax_code)
            if not group or group not in cl_by_group:
                continue

            cl_info = cl_by_group[group]
            cl_code = cl_info['code']

            if _is_stricter(ax_code, cl_code):
                idx = cl_info['idx']
                old_code  = cl_hazards[idx].get('h_code', '')
                old_class = cl_hazards[idx].get('class', '')

                cas_changes.append(f'  {old_code} ({old_class}) → {ax_h["h_code"]} ({ax_class})')

                if not dry_run:
                    cl_hazards[idx]['h_code'] = ax_h['h_code']
                    cl_hazards[idx]['class']  = ax_class

                updated = True

        if updated:
            if not dry_run:
                # ATP'yi annex6/ ile güncelle
                cl['atp'] = ax.get('atp', cl.get('atp', ''))

                # Not ekle (varsa üzerine yazma)
                notes = cl.get('notes', [])
                note  = (f"ATP22 düzeltmesi: Annex VI verisi ışığında "
                         f"daha sıkı sınıflandırmaya güncellendi.")
                if note not in notes:
                    notes.append(note)
                cl['notes'] = notes

                # Etiket h_codes güncelle
                cl.setdefault('labelling', {})['h_codes'] = [
                    h.get('h_code', '') for h in cl_hazards if h.get('h_code')
                ]

                _write(cl_file, cl)

            fixed_cas.append(cas)
            changes.append(f'\n{cas} ({ax.get("name","")[:50]}):')
            changes += cas_changes
        else:
            skip_cas.append(cas)

    # Rapor
    print(f"Güncellenen  : {len(fixed_cas)}")
    print(f"Değişmeyen   : {len(skip_cas)}")
    if changes:
        out = '\nDegisiklikler:\n' + '\n'.join(changes)
        try:
            print(out)
        except UnicodeEncodeError:
            print(out.encode('ascii', errors='replace').decode('ascii'))
    if dry_run:
        print('\n[DRY-RUN] Hicbir dosya degistirilmedi.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    fix_all(dry_run=args.dry_run)
