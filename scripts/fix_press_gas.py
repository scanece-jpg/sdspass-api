"""
fix_press_gas.py — Press. Gas / Basınç Gaz H kodu kaymasını düzeltir.

Sorun: Excel parse sırasında Press. Gas satırının H kodu bir sonraki
sınıfa kayıyor. Örnek:
  Press. Gas → H330  (yanlış)
  Acute Tox. 2 → H314  (yanlış)
  Skin Corr. 1A → ''   (eksik)

Düzeltme:
  Press. Gas → H280   (basınçlı sıvılaştırılmış gaz)
  Acute Tox. 2 → H330  (bir öncekinden alınan H kodu)
  Skin Corr. 1A → H314 (bir öncekinden alınan H kodu)
"""

import json, sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(__file__).parent.parent

PRESS_GAS_CLASSES = {'Press. Gas', 'Basınç Gaz'}


def fix_classification(cls_list: list) -> tuple[list, bool]:
    """
    classification listesindeki Press. Gas H kodu kaymasını düzeltir.

    İki durum:
      A) Press. Gas H kodu yanlış (H330 vb.) → H280 yap, yanlış kodu
         sonraki boş sınıfa zincirleme taşı
      B) Press. Gas H kodu boş → H280 ekle (toksik olmayan gazlar)

    Döner: (düzeltilmiş_liste, değişti_mi)
    """
    changed = False
    result  = list(cls_list)

    for i, entry in enumerate(result):
        if entry.get('class') not in PRESS_GAS_CLASSES:
            continue

        h = entry.get('h_code', '')

        if h in ('H280', 'H281'):
            continue  # zaten doğru

        if not h:
            # Durum B: boş — sadece H280 ekle
            result[i] = {**entry, 'h_code': 'H280'}
            changed = True
            continue

        # Durum A: yanlış H kodu var — zincirleme taşı
        displaced_h = h
        result[i] = {**entry, 'h_code': 'H280'}
        changed = True

        # Sonraki boş sınıflara zincirleme taşı (sınır yok)
        j = i + 1
        while displaced_h and j < len(result):
            next_entry = result[j]
            current_h  = next_entry.get('h_code', '')
            result[j]  = {**next_entry, 'h_code': displaced_h}
            displaced_h = current_h  # bir sonraki için
            if current_h:
                # Bir sonraki doluysa zincir devam eder;
                # ama son boş sınıfa ulaşmak için devam et
                pass
            j += 1
            # Son entry'yi doldurduktan sonra artık displaced_h boşsa dur
            if not displaced_h:
                break

    return result, changed


def fix_file(path: Path, class_key: str = 'classification') -> int:
    db = json.loads(path.read_text(encoding='utf-8'))
    fixed_count = 0

    for cas, v in db.items():
        if not isinstance(v, dict) or '_alias' in v:
            continue

        # Ana kayıt
        cls = v.get(class_key, [])
        new_cls, changed = fix_classification(cls)
        if changed:
            v[class_key] = new_cls
            fixed_count += 1

        # forms listesi (gümüş nano/kütle gibi)
        for form in v.get('forms', []):
            cls2 = form.get(class_key, [])
            new_cls2, changed2 = fix_classification(cls2)
            if changed2:
                form[class_key] = new_cls2

    path.write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding='utf-8')
    return fixed_count


if __name__ == '__main__':
    print('substance_db.json düzeltiliyor...')
    n1 = fix_file(ROOT / 'data' / 'substance_db.json', class_key='classification')
    print(f'  {n1} kayıt düzeltildi')

    print('sea_ek6_tr.json düzeltiliyor...')
    n2 = fix_file(ROOT / 'data' / 'sea_ek6_tr.json', class_key='classification')
    print(f'  {n2} kayıt düzeltildi')

    print()
    print('Örnek kontrol (BF₃ 7637-07-2):')
    db = json.loads((ROOT / 'data' / 'substance_db.json').read_text(encoding='utf-8'))
    if '7637-07-2' in db:
        for c in db['7637-07-2'].get('classification', []):
            print(f'  {c["class"]:20} → {c.get("h_code","")}')
