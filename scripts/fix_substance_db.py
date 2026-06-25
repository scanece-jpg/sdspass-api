"""Fix A + B + C for substance_db.json — run once from repo root."""
import json, re, sys
from pathlib import Path

try:
    import pandas as pd
except ImportError:
    sys.exit("pip install pandas openpyxl")

XLSX  = Path("annex_vi_clp_table_atp22_en.xlsx")
DB    = Path("data/substance_db.json")

if not XLSX.exists():
    sys.exit(f"Not found: {XLSX}")
if not DB.exists():
    sys.exit(f"Not found: {DB}")

# ── load xlsx ────────────────────────────────────────────────────────────────
df = pd.read_excel(XLSX, sheet_name="ATP_22", header=4, dtype=str)
df.columns = [
    "index_no", "name", "ec_no", "cas_no",
    "cls_block", "h_codes", "label_block", "signal", "pictograms",
    "scl_m", "notes", "atp"
]
df = df.fillna("")
df = df[df["index_no"].str.strip() != ""]

# ── load db ──────────────────────────────────────────────────────────────────
with open(DB, encoding="utf-8") as f:
    db = json.load(f)

print(f"DB loaded: {len(db)} entries")

# ─────────────────────────────────────────────────────────────────────────────
# helper: parse M-factors from scl_m cell
# cell may contain: "M = 10", "M = 1\nM = 10", "C ≥ 25%: …  M = 10", etc.
# ─────────────────────────────────────────────────────────────────────────────
def parse_m_factors(cell: str) -> dict | None:
    """Return {'acute': int, 'chronic': int} or None if no M found."""
    lines = [l.strip() for l in cell.replace("\r", "\n").split("\n") if l.strip()]
    m_vals = []
    for line in lines:
        m = re.search(r"M\s*=\s*(\d+)", line)
        if m:
            m_vals.append(int(m.group(1)))
    if not m_vals:
        return None
    if len(m_vals) == 1:
        return {"acute": m_vals[0], "chronic": m_vals[0]}
    # xlsx convention: first M-line = acute, second = chronic
    return {"acute": m_vals[0], "chronic": m_vals[1]}

# ─────────────────────────────────────────────────────────────────────────────
# Build index_no → row lookup and CAS → row lookup from xlsx
# ─────────────────────────────────────────────────────────────────────────────
def cas_list(cell: str) -> list[str]:
    return [c.strip() for c in re.split(r"[;,\n]+", cell) if c.strip()]

xlsx_by_index: dict[str, dict] = {}
xlsx_by_cas:   dict[str, dict] = {}
for _, row in df.iterrows():
    idx = row["index_no"].strip()
    row_d = row.to_dict()
    xlsx_by_index[idx] = row_d
    for c in cas_list(row["cas_no"]):
        xlsx_by_cas[c] = row_d

# ─────────────────────────────────────────────────────────────────────────────
# FIX C — update ALL m_factors in db to {'acute': X, 'chronic': Y}
# Sources of truth: xlsx rows matched by CAS or index_no
# ─────────────────────────────────────────────────────────────────────────────
fix_c_updated   = 0
fix_c_no_xlsx   = 0
fix_c_no_m      = 0
fix_c_already   = 0

for cas_key, entry in db.items():
    # find xlsx row
    row = xlsx_by_cas.get(cas_key)
    if row is None:
        row = xlsx_by_index.get(entry.get("index_no", ""))
    if row is None:
        fix_c_no_xlsx += 1
        continue

    mf = parse_m_factors(row["scl_m"])
    if mf is None:
        # no M-factor in xlsx → clear any stale 'default' key
        if entry.get("m_factors"):
            entry["m_factors"] = {}
            fix_c_no_m += 1
        continue

    current = entry.get("m_factors", {})
    if current == mf:
        fix_c_already += 1
        continue

    entry["m_factors"] = mf
    fix_c_updated += 1

print(f"\nFix C: {fix_c_updated} updated, {fix_c_already} already correct, "
      f"{fix_c_no_m} cleared (no M in xlsx), {fix_c_no_xlsx} no xlsx row found")

# ─────────────────────────────────────────────────────────────────────────────
# FIX B — add CAS 135410-20-7 as alias for acetamiprid (160430-64-8)
# ─────────────────────────────────────────────────────────────────────────────
ACETA_PRIMARY = "160430-64-8"
ACETA_ALIAS   = "135410-20-7"

if ACETA_PRIMARY not in db:
    print(f"\nFix B: PRIMARY {ACETA_PRIMARY} NOT FOUND — skipping")
elif ACETA_ALIAS in db:
    print(f"\nFix B: {ACETA_ALIAS} already exists — skipping")
else:
    import copy
    alias_entry = copy.deepcopy(db[ACETA_PRIMARY])
    alias_entry["cas"] = ACETA_ALIAS
    db[ACETA_ALIAS] = alias_entry
    print(f"\nFix B: added {ACETA_ALIAS} -> acetamiprid alias  OK")

# ─────────────────────────────────────────────────────────────────────────────
# FIX A — add entries for 36483-57-5 and 1522-92-5 (Index 603-243-00-6)
# ─────────────────────────────────────────────────────────────────────────────
INDEX_A = "603-243-00-6"
CAS_A   = ["36483-57-5", "1522-92-5"]

row_a = xlsx_by_index.get(INDEX_A)
if row_a is None:
    print(f"\nFix A: index {INDEX_A} not found in xlsx — skipping")
else:
    # Parse h-codes from h_codes column
    raw_h = row_a.get("h_codes", "") or ""
    h_codes_raw = [h.strip() for h in re.split(r"[\s,;]+", raw_h) if re.match(r"H\d", h.strip())]

    # Parse classification block for class names
    raw_cls = row_a.get("cls_block", "") or ""
    # Build classification list from h_codes (simplified — class comes from db pattern)
    # We map known H codes to their CLP class names
    H_TO_CLASS = {
        "H350": "Carc. 1B", "H351": "Carc. 2",
        "H340": "Muta. 1B", "H341": "Muta. 2",
        "H360": "Repr. 1B", "H361": "Repr. 2",
        "H370": "STOT SE 1", "H371": "STOT SE 2", "H372": "STOT RE 1", "H373": "STOT RE 2",
        "H300": "Acute Tox. 1", "H301": "Acute Tox. 2", "H302": "Acute Tox. 4",
        "H310": "Acute Tox. 1", "H311": "Acute Tox. 3", "H312": "Acute Tox. 4",
        "H330": "Acute Tox. 1", "H331": "Acute Tox. 3", "H332": "Acute Tox. 4",
        "H400": "Aquatic Acute 1", "H410": "Aquatic Chronic 1",
        "H411": "Aquatic Chronic 2", "H412": "Aquatic Chronic 3",
        "H314": "Skin Corr. 1", "H315": "Skin Irrit. 2",
        "H317": "Skin Sens. 1", "H334": "Resp. Sens. 1",
        "H318": "Eye Dam. 1", "H319": "Eye Irrit. 2",
        "H290": "Met. Corr. 1",
        "H200": "Expl.", "H201": "Expl. 1.1", "H202": "Expl. 1.2",
        "H220": "Flam. Gas 1", "H225": "Flam. Liq. 2", "H226": "Flam. Liq. 3",
        "H271": "Ox. Sol. 1", "H272": "Ox. Sol. 2",
        "H280": "Press. Gas", "H281": "Press. Gas",
    }
    classification = []
    for h in h_codes_raw:
        base = h[:4]
        cls_name = H_TO_CLASS.get(base, "")
        classification.append({"class": cls_name, "h_code": h, "note_flag": ""})

    notes_raw = row_a.get("notes", "") or ""
    notes = [n.strip() for n in notes_raw.split() if n.strip()]
    atp_raw = row_a.get("atp", "") or "ATP22"
    name_raw = row_a.get("name", "") or ""

    mf = parse_m_factors(row_a.get("scl_m", ""))

    base_entry = {
        "index_no": INDEX_A,
        "names": [name_raw.strip()],
        "ec_no": (row_a.get("ec_no", "") or "").strip(),
        "cas": CAS_A[0],
        "synonyms": CAS_A[1:],
        "atp": atp_raw.strip(),
        "notes": notes,
        "classification": classification,
        "scl_limits": [],
        "m_factors": mf or {},
        "ate": {},
    }

    added = []
    for c in CAS_A:
        if c in db:
            print(f"\nFix A: {c} already exists — skipping")
        else:
            import copy
            e = copy.deepcopy(base_entry)
            e["cas"] = c
            db[c] = e
            added.append(c)

    if added:
        print(f"\nFix A: added {added}  OK")

    # Show what we parsed for verification
    print(f"       index={INDEX_A}, name={name_raw[:60]}")
    print(f"       h_codes={h_codes_raw}, notes={notes}, mf={mf}")

# ─────────────────────────────────────────────────────────────────────────────
# Save
# ─────────────────────────────────────────────────────────────────────────────
with open(DB, "w", encoding="utf-8") as f:
    json.dump(db, f, ensure_ascii=False, indent=2)

print(f"\nDB saved: {len(db)} entries  OK")
