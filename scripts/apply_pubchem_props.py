"""
PubChem verilerini physical_engine.py'e uygular.
fetch_pubchem_props.py tamamlandiktan sonra calistirin.
"""
import os, json, sys

PROPS_FILE  = os.path.join(os.path.dirname(__file__), 'pubchem_props.json')
ENGINE_FILE = os.path.join(os.path.dirname(__file__), '..', 'app', 'services', 'physical_engine.py')

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from app.services.physical_engine import FP_DB, BP_DB, MW_DB, DENSITY_DB

def main():
    with open(PROPS_FILE, encoding='utf-8') as f:
        data = json.load(f)

    new_fp = {}; new_bp = {}; new_mw = {}; new_density = {}

    for cas, props in data.items():
        if not props.get('found'):
            continue
        bp  = props.get('bp')
        den = props.get('density')
        fp  = props.get('fp')
        mw  = props.get('mw')
        if bp  is not None and cas not in BP_DB:
            new_bp[cas] = bp
        if den is not None and cas not in DENSITY_DB:
            new_density[cas] = den
        if fp  is not None and cas not in FP_DB:
            new_fp[cas] = fp
        if mw  is not None and cas not in MW_DB:
            new_mw[cas] = round(float(mw), 2)

    print(f'Yeni BP:       {len(new_bp)}')
    print(f'Yeni Yogunluk: {len(new_density)}')
    print(f'Yeni FP:       {len(new_fp)}')
    print(f'Yeni MW:       {len(new_mw)}')

    def build_block(d, label):
        if not d:
            return ''
        lines = ['    # ── PubChem ' + label + ' (' + str(len(d)) + ' kimyasal)']
        row = []
        for cas, val in sorted(d.items()):
            if isinstance(val, float):
                row.append("'" + cas + "': " + str(val))
            else:
                row.append("'" + cas + "': " + str(val))
            if len(row) == 4:
                lines.append('    ' + ',  '.join(row) + ',')
                row = []
        if row:
            lines.append('    ' + ',  '.join(row) + ',')
        return '\n'.join(lines)

    with open(ENGINE_FILE, encoding='utf-8') as f:
        src = f.read()

    def insert_before_close(src, db_name, block):
        """DB'nin kapanma parantezinden once blok ekle"""
        db_def = src.find(db_name + ': Dict[')
        if db_def == -1:
            db_def = src.find(db_name + ':Dict[')
        if db_def == -1:
            print('UYARI: ' + db_name + ' bulunamadi')
            return src
        # Kapanma parantezini bul
        depth = 0; pos = None
        for i in range(db_def, len(src)):
            if src[i] == '{':
                depth += 1
            elif src[i] == '}':
                depth -= 1
                if depth == 0:
                    pos = i
                    break
        if pos is None:
            print('UYARI: ' + db_name + ' kapanis bulunamadi')
            return src
        return src[:pos] + '\n' + block + '\n' + src[pos:]

    changes = [
        ('FP_DB',      new_fp,      'FP'),
        ('BP_DB',      new_bp,      'BP'),
        ('MW_DB',      new_mw,      'MW'),
        ('DENSITY_DB', new_density, 'Density'),
    ]

    for db_name, new_data, label in changes:
        if not new_data:
            continue
        block = build_block(new_data, label)
        src = insert_before_close(src, db_name, block)
        print(db_name + ': ' + str(len(new_data)) + ' giris eklendi')

    with open(ENGINE_FILE, 'w', encoding='utf-8') as f:
        f.write(src)
    print('\nphysical_engine.py guncellendi.')

    # Dogrula
    try:
        import importlib, app.services.physical_engine as eng
        importlib.reload(eng)
        print('Sozdizimi OK')
        print('FP_DB: ' + str(len(eng.FP_DB)) + ' | BP_DB: ' + str(len(eng.BP_DB)) + ' | DENSITY_DB: ' + str(len(eng.DENSITY_DB)) + ' | MW_DB: ' + str(len(eng.MW_DB)))
    except Exception as e:
        print('HATA: ' + str(e))

if __name__ == '__main__':
    main()
