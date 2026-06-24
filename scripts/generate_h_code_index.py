"""
generate_h_code_index.py — substance_db.json'dan H-kod indeksi türetir.

Giriş : data/substance_db.json
Çıktı : data/h_code_index.json

Her H-kodu için:
  - kaç maddede geçtiği (count)
  - hangi CAS'larda geçtiği (occurrences)
  - o H-kodu için SCL verisi olan CAS'lar (scl_cas)
  - M-faktör olan CAS'lar (m_cas)
"""

import json
import sys
from pathlib import Path
from collections import defaultdict

DB_PATH  = Path(__file__).parent.parent / "data" / "substance_db.json"
OUT_PATH = Path(__file__).parent.parent / "data" / "h_code_index.json"


def build(db: dict) -> dict:
    index = defaultdict(lambda: {
        "count": 0,
        "occurrences": [],
        "scl_cas": [],
        "m_cas": [],
    })

    for cas, entry in db.items():
        if "_alias" in entry:
            continue

        # Classification'dan H-kodları
        seen_hcodes = set()
        for cl in entry.get("classification", []):
            hc = cl.get("h_code", "").strip()
            if not hc:
                continue
            if hc not in seen_hcodes:
                index[hc]["count"] += 1
                index[hc]["occurrences"].append(cas)
                seen_hcodes.add(hc)

        # SCL'deki H-kodları
        scl_hcodes = {s["h_code"] for s in entry.get("scl_limits", [])}
        for hc in scl_hcodes:
            if cas not in index[hc]["scl_cas"]:
                index[hc]["scl_cas"].append(cas)

        # M-faktör olan H-kodları (H400/H410/H411 grubuna işaret eder)
        if entry.get("m_factors"):
            for hc in seen_hcodes:
                if hc in ("H400", "H410", "H411"):
                    if cas not in index[hc]["m_cas"]:
                        index[hc]["m_cas"].append(cas)

    # Sırala: count büyükten küçüğe
    return dict(sorted(index.items(), key=lambda x: -x[1]["count"]))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")

    db = json.loads(DB_PATH.read_text(encoding="utf-8"))
    print(f"substance_db: {sum(1 for v in db.values() if '_alias' not in v)} madde")

    idx = build(db)

    OUT_PATH.write_text(json.dumps(idx, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"H-kod sayısı : {len(idx)}")
    print(f"Kaydedildi   : {OUT_PATH}")
    print()
    print("En sık 10 H-kodu:")
    for hc, data in list(idx.items())[:10]:
        print(f"  {hc:8s}  {data['count']:4d} madde  SCL:{len(data['scl_cas'])}  M:{len(data['m_cas'])}")
