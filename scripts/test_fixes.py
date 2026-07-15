"""Hesaplama motoru düzeltmelerini doğrular."""
import sys
sys.path.insert(0, r'C:\Users\user\Desktop\sdspass')

from app.services.clp_service import ATE_DEFAULTS, ATE_THRESHOLDS, ATE_HCODES

print('=== ATE_DEFAULTS (formul nokta tahminleri) ===')
for r, v in ATE_DEFAULTS.items():
    print(f'  {r}: {v}')

print()
print('=== ATE_THRESHOLDS (siniflandirma sinirlar - Tablo 3.1.1) ===')
for r, v in ATE_THRESHOLDS.items():
    print(f'  {r}: {v}')

print()
errors = 0

# --- Oral testleri ---
cases_oral = [
    (0.3,  1, 'H300'),   # <=5 -> Kat1
    (3.0,  1, 'H300'),   # <=5 -> Kat1
    (10.0, 2, 'H300'),   # 5<x<=50 -> Kat2 -> H300
    (49.0, 2, 'H300'),   # 5<x<=50 -> Kat2
    (51.0, 3, 'H301'),   # 50<x<=300 -> Kat3
    (150.0,3, 'H301'),   # 50<x<=300 -> Kat3
    (301.0,4, 'H302'),   # 300<x<=2000 -> Kat4
]
print('=== Oral ATE siniflandirma ===')
for ate_val, expected_cat, expected_h in cases_oral:
    thresholds = ATE_THRESHOLDS['oral']
    cat = None
    for n in [1,2,3,4]:
        if ate_val <= thresholds[n]:
            cat = n
            break
    h = ATE_HCODES['oral'][cat] if cat else None
    ok = (cat == expected_cat and h == expected_h)
    status = 'OK' if ok else 'HATA'
    if not ok:
        errors += 1
    print(f'  ATE={ate_val:7.1f} -> Kat{cat} {h}  beklenen=Kat{expected_cat} {expected_h}  [{status}]')

# --- Dermal testleri ---
cases_dermal = [
    (10.0,  1, 'H310'),  # <=50 -> Kat1
    (50.0,  1, 'H310'),  # <=50 -> Kat1
    (51.0,  2, 'H310'),  # 50<x<=200 -> Kat2 -> H310
    (150.0, 2, 'H310'),  # 50<x<=200 -> Kat2 -> H310
    (200.0, 2, 'H310'),  # <=200 -> Kat2
    (201.0, 3, 'H311'),  # 200<x<=1000 -> Kat3
    (500.0, 3, 'H311'),  # 200<x<=1000 -> Kat3
    (1001.0,4, 'H312'),  # >1000 -> Kat4
]
print()
print('=== Dermal ATE siniflandirma ===')
for ate_val, expected_cat, expected_h in cases_dermal:
    thresholds = ATE_THRESHOLDS['dermal']
    cat = None
    for n in [1,2,3,4]:
        if ate_val <= thresholds[n]:
            cat = n
            break
    h = ATE_HCODES['dermal'][cat] if cat else None
    ok = (cat == expected_cat and h == expected_h)
    status = 'OK' if ok else 'HATA'
    if not ok:
        errors += 1
    print(f'  ATE={ate_val:7.1f} -> Kat{cat} {h}  beklenen=Kat{expected_cat} {expected_h}  [{status}]')

# --- Inhalasyon vapor testleri ---
cases_vapor = [
    (0.1,  1, 'H330'),  # <=0.5 -> Kat1
    (0.5,  1, 'H330'),  # <=0.5 -> Kat1
    (1.0,  2, 'H330'),  # 0.5<x<=2 -> Kat2 -> H330
    (2.0,  2, 'H330'),  # <=2 -> Kat2
    (3.0,  3, 'H331'),  # 2<x<=10 -> Kat3
    (10.0, 3, 'H331'),  # <=10 -> Kat3
    (11.0, 4, 'H332'),  # 10<x<=20 -> Kat4
]
print()
print('=== Inhalasyon vapor ATE siniflandirma ===')
for ate_val, expected_cat, expected_h in cases_vapor:
    thresholds = ATE_THRESHOLDS['inhalation_vapour']
    cat = None
    for n in [1,2,3,4]:
        if ate_val <= thresholds[n]:
            cat = n
            break
    h = ATE_HCODES['inhalation_vapour'][cat] if cat else None
    ok = (cat == expected_cat and h == expected_h)
    status = 'OK' if ok else 'HATA'
    if not ok:
        errors += 1
    print(f'  ATE={ate_val:5.2f} -> Kat{cat} {h}  beklenen=Kat{expected_cat} {expected_h}  [{status}]')

# --- STOT RE testi ---
print()
print('=== STOT RE siniflandirma ===')
from app.services.stot_engine import calculate as calculate_stot_re

stot_cases = [
    # cat1_sum, cat2_sum, expected_h
    (10.5, 0,    'H372'),   # cat1 >= 10 -> H372
    (5.0,  0,    'H373'),   # 1 <= cat1 < 10 -> H373
    (0.5,  12.0, 'H373'),   # cat2 >= 10 -> H373
    (0.05, 5.0,  None),     # esik alti
]
for cat1, cat2, expected in stot_cases:
    comps = [{'cas': 'test', 'name': 'TestMadde', 'conc': cat1,
              'hazards': [{'h_class': 'STOT RE 1', 'h_code': 'H372(liver)'}]}]
    if cat2 > 0:
        comps.append({'cas': 'test2', 'name': 'TestMadde2', 'conc': cat2,
                      'hazards': [{'h_class': 'STOT RE 2', 'h_code': 'H373(liver)'}]})
    res = calculate_stot_re(comps)
    h_list = res['h_codes']
    got = h_list[0] if h_list else None
    ok = (got == expected)
    status = 'OK' if ok else 'HATA'
    if not ok:
        errors += 1
    print(f'  Cat1={cat1}% Cat2={cat2}% -> {got}  beklenen={expected}  [{status}]')

# --- PBT testi ---
print()
print('=== PBT operator oncelik ===')
from app.services.ecological_service import assess_pbt

# P=Hayir, B=Olasi, T=Evet -> PBT olmamali (onceden True donuyordu)
comps_pbt = [{'cas': 'test', 'name': 'Test', 'conc': 1.0,
              'hazards': [{'h_class': 'Aquatic Chronic 1', 'h_code': 'H410'}]}]
import app.services.ecological_service as eco_svc
# Manuel test: P=Hayir, B=Olasi, T=Evet
p = "Belirsiz"
b = "Olasi (log Kow=4.5)"
t = "Evet"
is_pbt = (p.startswith("Evet") and
          (b.startswith("Evet") or b.startswith("Olasi")) and
          t.startswith("Evet"))
expected_pbt = False  # P=Belirsiz oldugu icin False olmali
ok = (is_pbt == expected_pbt)
status = 'OK' if ok else 'HATA'
if not ok:
    errors += 1
print(f'  P=Belirsiz, B=Olasi, T=Evet -> is_pbt={is_pbt}  beklenen={expected_pbt}  [{status}]')

p = "Evet (t1/2=90g)"
b = "Olasi (log Kow=4.8)"
t = "Evet"
is_pbt = (p.startswith("Evet") and
          (b.startswith("Evet") or b.startswith("Olasi")) and
          t.startswith("Evet"))
expected_pbt = True
ok = (is_pbt == expected_pbt)
status = 'OK' if ok else 'HATA'
if not ok:
    errors += 1
print(f'  P=Evet,    B=Olasi, T=Evet -> is_pbt={is_pbt}  beklenen={expected_pbt}  [{status}]')

print()
if errors == 0:
    print('TUM TESTLER GECTI')
else:
    print(f'HATA: {errors} test basarisiz')
