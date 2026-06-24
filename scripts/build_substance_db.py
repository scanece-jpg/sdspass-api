"""
build_substance_db.py — Ham Excel satırlarını 6b şemasına dönüştürür.

Giriş : echa_excel_loader.load() çıktısı
Çıktı : data/substance_db.json  (CAS anahtarlı)
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from echa_excel_loader import load

OUT_PATH = Path(__file__).parent.parent / "data" / "substance_db.json"


# ---------------------------------------------------------------------------
# Yardımcılar
# ---------------------------------------------------------------------------

def _num(s: str) -> float:
    """'0,75' veya '0.75' → float"""
    return float(s.replace(",", "."))


def _strip_asterisk(s: str) -> tuple[str, int]:
    """
    'Acute Tox. 3 *'  → ('Acute Tox. 3', 1)
    'H373 **'          → ('H373', 2)
    CLP'de * ve ** farklı anlam taşır; count olarak sakla.
    """
    s = s.strip()
    m = re.search(r'(\*+)\s*$', s)
    if m:
        count = len(m.group(1))
        return s[:m.start()].strip(), count
    return s, 0


# ---------------------------------------------------------------------------
# SCL / M-faktör / ATE parse
# ---------------------------------------------------------------------------

# Örn: "Eye Dam. 1; H318: C ≥ 22 %"
_RE_SCL_GE    = re.compile(r"^(.+?);\s*(H\d+\w*)\s*:\s*C\s*[≥>=]+\s*([\d,\.]+)\s*%")
# Örn: "Eye Irrit. 2; H319: 14 % ≤ C < 22 %"
_RE_SCL_RANGE = re.compile(r"^(.+?);\s*(H\d+\w*)\s*:\s*([\d,\.]+)\s*%\s*[≤<=]+\s*C\s*[<≤]\s*([\d,\.]+)\s*%")
# Örn: "Skin Corr. 1A; H314: C < 5 %"  (sadece üst sınır)
_RE_SCL_LT    = re.compile(r"^(.+?);\s*(H\d+\w*)\s*:\s*C\s*[<≤]+\s*([\d,\.]+)\s*%")

# M-faktör: "M=100" veya "M(acute)=10" veya "M(chronic)=1"
_RE_M         = re.compile(r"M(?:\((\w+)\))?=(\d+)", re.IGNORECASE)

# ATE: "oral: ATE = 300 mg/kg bw"  |  "inhalation: ATE = 0,75 mg/L (dusts or mists)"
_RE_ATE       = re.compile(
    r"(oral|dermal|inhalation)\s*:\s*ATE\s*=\s*([\d,\.]+)\s*(mg/kg|mg/L|ppm)"
    r"(?:\s*(?:bw|body weight))?"
    r"(?:\s*\((.+?)\))?",
    re.IGNORECASE,
)


def _parse_scl(raw: str) -> tuple[list[dict], dict, dict]:
    """
    Ham SCL hücresini parse eder.
    Döner: (scl_limits, m_factors, ate)
      scl_limits : [{h_code, class, op, min, max, unit}]
      m_factors  : {"acute": int, "chronic": int}  (veya {"default": int})
      ate        : {"oral": float, "dermal": float, "inhalation": {...}}
    """
    scl_limits = []
    m_factors  = {}
    ate        = {}

    for line in raw.split("\n"):
        line = line.strip()
        if not line:
            continue

        # M-faktör
        m_match = _RE_M.search(line)
        if m_match:
            mtype = (m_match.group(1) or "default").lower()
            m_factors[mtype] = int(m_match.group(2))
            continue

        # ATE
        a_match = _RE_ATE.search(line)
        if a_match:
            route  = a_match.group(1).lower()
            value  = _num(a_match.group(2))
            unit   = a_match.group(3)
            form   = a_match.group(4) or ""
            entry  = {"value": value, "unit": unit}
            if form:
                entry["form"] = form
            ate[route] = entry
            continue

        # SCL aralık  (önce range, sonra >= çünkü >= daha genel)
        m = _RE_SCL_RANGE.match(line)
        if m:
            cls, hc = _strip_asterisk(m.group(1))[0], m.group(2)
            scl_limits.append({
                "h_code": hc, "class": cls,
                "op": "range",
                "min": _num(m.group(3)), "max": _num(m.group(4)),
                "unit": "%",
            })
            continue

        m = _RE_SCL_GE.match(line)
        if m:
            cls = _strip_asterisk(m.group(1))[0]
            scl_limits.append({
                "h_code": m.group(2), "class": cls,
                "op": ">=",
                "min": _num(m.group(3)), "max": None,
                "unit": "%",
            })
            continue

        m = _RE_SCL_LT.match(line)
        if m:
            cls = _strip_asterisk(m.group(1))[0]
            scl_limits.append({
                "h_code": m.group(2), "class": cls,
                "op": "<",
                "min": None, "max": _num(m.group(3)),
                "unit": "%",
            })
            continue

    return scl_limits, m_factors, ate


# ---------------------------------------------------------------------------
# Classification parse
# ---------------------------------------------------------------------------

def _parse_classification(pairs: list[dict]) -> list[dict]:
    """
    [{class, h_code}] listesini şemaya dönüştürür.
    class_asterisk  : sınıflandırma tarafındaki * sayısı (0/1)
    h_code_asterisk : H-kodu tarafındaki * sayısı (0/1/2)
    """
    result = []
    for p in pairs:
        cls_raw = p["class"].strip()
        hc_raw  = p["h_code"].strip()
        if not cls_raw and not hc_raw:
            continue
        cls, cls_ast = _strip_asterisk(cls_raw)
        hc,  hc_ast  = _strip_asterisk(hc_raw)
        entry = {"class": cls, "h_code": hc}
        if cls_ast:
            entry["class_asterisk"] = cls_ast
        if hc_ast:
            entry["h_code_asterisk"] = hc_ast
        result.append(entry)
    return result


# ---------------------------------------------------------------------------
# Ana dönüştürücü
# ---------------------------------------------------------------------------

def build(rows: list[dict]) -> dict:
    """
    Ham satır listesini substance_db dict'ine dönüştürür.
    Anahtar: birincil CAS (ilk CAS). Çoklu CAS → synonyms.
    """
    db = {}

    for row in rows:
        cas_list = row["cas_list"]
        if not cas_list:
            continue

        primary_cas = cas_list[0]
        synonyms    = cas_list[1:] if len(cas_list) > 1 else []

        classification          = _parse_classification(row["class_h_pairs"])
        scl_limits, m_factors, ate = _parse_scl(row["scl_raw"])

        notes_raw = row["notes_raw"].strip()
        notes = [n.strip() for n in re.split(r"[\s,]+", notes_raw) if n.strip()] if notes_raw else []

        entry = {
            "index_no":       row["index_no"],
            "names":          row["names"],
            "ec_no":          row["ec_no"],
            "cas":            primary_cas,
            "synonyms":       synonyms,
            "atp":            row["atp"],
            "notes":          notes,
            "classification": classification,
            "scl_limits":     scl_limits,
            "m_factors":      m_factors,
            "ate":            ate,
        }

        # Çakışma: aynı CAS farklı Index No ile iki kez geliyor (nadiren)
        if primary_cas in db:
            existing = db[primary_cas]
            # ATP numarası yüksek olanı tut
            if row["atp"] > existing["atp"]:
                db[primary_cas] = entry
        else:
            db[primary_cas] = entry

        # Synonym CAS'ları da birincil CAS'a işaret etsin
        for syn in synonyms:
            if syn not in db:
                db[syn] = {"_alias": primary_cas}

    return db


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    print("Excel okunuyor...")
    rows = load()
    print(f"  {len(rows)} satır yüklendi")

    print("Dönüştürülüyor...")
    db = build(rows)

    real   = sum(1 for v in db.values() if "_alias" not in v)
    alias  = sum(1 for v in db.values() if "_alias" in v)
    has_scl = sum(1 for v in db.values() if "_alias" not in v and v.get("scl_limits"))
    has_m   = sum(1 for v in db.values() if "_alias" not in v and v.get("m_factors"))
    has_ate = sum(1 for v in db.values() if "_alias" not in v and v.get("ate"))

    print(f"  Gerçek madde : {real}")
    print(f"  Alias kayıt  : {alias}")
    print(f"  SCL verisi   : {has_scl}")
    print(f"  M-faktör     : {has_m}")
    print(f"  ATE verisi   : {has_ate}")

    OUT_PATH.parent.mkdir(exist_ok=True)
    OUT_PATH.write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nKaydedildi: {OUT_PATH}")

    # Örnek çıktı
    print("\n--- Örnek (NaOH 1310-73-2) ---")
    if "1310-73-2" in db:
        print(json.dumps(db["1310-73-2"], ensure_ascii=False, indent=2))
