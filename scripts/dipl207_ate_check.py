"""DIPL207 ATEmix senaryo analizi"""

components = [
    dict(name='metanol',      conc=6.5,  has_acute_tox=True,  ate_val=100,  annex_vi=False),
    dict(name='bakir_sulfat', conc=2.0,  has_acute_tox=True,  ate_val=500,  annex_vi=False),
    dict(name='formaldehit',  conc=0.18, has_acute_tox=True,  ate_val=500,  annex_vi=False),
    dict(name='H2SO4',        conc=8.0,  has_acute_tox=False, ate_val=None, annex_vi=False),
    dict(name='NaOH',         conc=1.5,  has_acute_tox=False, ate_val=None, annex_vi=False),
]

total_declared = sum(c['conc'] for c in components)
undeclared     = 100 - total_declared

print("=" * 60)
print("DIPL207 Bilesen Analizi")
print(f"  Beyan edilen toplam   : %{total_declared}")
print(f"  Beyan EDILMEYEN bosluk: %{undeclared:.2f}")
print("=" * 60)

def cls_oral(v):
    if v <= 5:    return "H300 (Kat1)"
    if v <= 50:   return "H300 (Kat2)"
    if v <= 300:  return "H301 (Kat3)"
    if v <= 2000: return "H302 (Kat4)"
    return "siniflandirilmamis (>2000)"

# Senaryo A: mevcut kod davranisi
ate_sum_A = 0.0
unknown_A = 0.0
for c in components:
    if c['has_acute_tox']:
        ate_sum_A += (c['conc'] / 100) / c['ate_val']
    else:
        if c['annex_vi']:
            ate_sum_A += (c['conc'] / 100) / 5000.0
        else:
            unknown_A += c['conc']

formula_A = "REVIZE" if unknown_A > 10 else "STANDART"
mix_A = ((100 - unknown_A) / ate_sum_A) if unknown_A > 10 else (100 / ate_sum_A)

print()
print("SENARYO A: Mevcut kod")
print(f"  H2SO4 + NaOH => unknown_conc (annex_vi=False)")
print(f"  unknown_A  = %{unknown_A}  (H2SO4 %8 + NaOH %1.5)")
print(f"  Undeclared = %{undeclared:.2f}  -> KOD GÖRMÜYOR")
print(f"  Sigma      = {ate_sum_A:.5f}")
print(f"  Formül     = {formula_A} (unknown <= %10 koşulu: {unknown_A} <= 10 = {unknown_A <= 10})")
print(f"  ATEmix     = {mix_A:.1f} mg/kg  -> {cls_oral(mix_A)}")
print()

# Senaryo B: kullanicinin tezi (undeclared de unknown sayilir)
unknown_B = unknown_A + undeclared
mix_B = (100 - unknown_B) / ate_sum_A
print("SENARYO B: Kullanicinin tezi — undeclared %81.82 de unknown")
print(f"  unknown_B  = %{unknown_B:.2f}  ({unknown_A} + {undeclared:.2f})")
print(f"  Formül     = REVIZE (unknown > %10)")
print(f"  ATEmix     = (100-{unknown_B:.2f}) / {ate_sum_A:.5f} = {mix_B:.1f} mg/kg  -> {cls_oral(mix_B)}")
print()

# Senaryo C: H2SO4+NaOH Annex VI + undeclared unknown
ate_sum_C = ate_sum_A + (8.0 / 100 / 5000) + (1.5 / 100 / 5000)
unknown_C = undeclared
mix_C = (100 - unknown_C) / ate_sum_C
print("SENARYO C: H2SO4+NaOH Annex VI (ATE=5000) + undeclared unknown")
print(f"  Sigma_C    = {ate_sum_C:.5f}  (+H2SO4 +NaOH via ATE=5000)")
print(f"  unknown_C  = %{unknown_C:.2f}  (sadece beyan edilmeyen kisim)")
print(f"  Formül     = REVIZE (unknown > %10)")
print(f"  ATEmix     = (100-{unknown_C:.2f}) / {ate_sum_C:.5f} = {mix_C:.1f} mg/kg  -> {cls_oral(mix_C)}")
print()

print("=" * 60)
print("ÖZET")
print(f"  Senaryo A (mevcut): {mix_A:.1f} mg/kg -> {cls_oral(mix_A)}")
print(f"  Senaryo B (undecl unknown): {mix_B:.1f} mg/kg -> {cls_oral(mix_B)}")
print(f"  Senaryo C (AnnexVI+undecl): {mix_C:.1f} mg/kg -> {cls_oral(mix_C)}")
print("=" * 60)
