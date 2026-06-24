"""
validate_refs.py — Build kapısı: veri bütünlüğü 4 katman kontrolü.

Hata varsa exit(1) — CI/deploy durur.
Uyarı varsa raporlanır ama build devam eder.
"""

import json
import sys
from pathlib import Path

DB_PATH    = Path(__file__).parent.parent / "data" / "substance_db.json"
IDX_PATH   = Path(__file__).parent.parent / "data" / "h_code_index.json"

ERRORS   = []
WARNINGS = []


def err(msg: str):
    ERRORS.append(msg)


def warn(msg: str):
    WARNINGS.append(msg)


# ---------------------------------------------------------------------------
# Katman 1 — Alias bütünlüğü
# ---------------------------------------------------------------------------

def check_aliases(db: dict):
    """Her _alias kaydı gerçek bir CAS'a işaret etmeli."""
    for cas, entry in db.items():
        if "_alias" not in entry:
            continue
        target = entry["_alias"]
        if target not in db:
            err(f"[K1] Alias hedefi bulunamadı: {cas} → {target}")
        elif "_alias" in db[target]:
            err(f"[K1] Alias zinciri (alias→alias): {cas} → {target}")


# ---------------------------------------------------------------------------
# Katman 2 — SCL / classification tutarlılığı
# ---------------------------------------------------------------------------

def check_scl_vs_classification(db: dict):
    """
    scl_limits içindeki H-kodları classification'da da bulunmalı
    VEYA scl_limits'te 'H319' gibi bant genişletme olabilir
    (ana madde H318 ama SCL bantında H319 → kabul edilir, sadece uyarı).
    """
    for cas, entry in db.items():
        if "_alias" in entry:
            continue
        cl_hcodes = {c["h_code"] for c in entry.get("classification", [])}
        for scl in entry.get("scl_limits", []):
            hc = scl.get("h_code", "")
            if hc and hc not in cl_hcodes:
                # Bant genişletme vakası: uyarı yeterli, hata değil
                warn(f"[K2] SCL H-kodu classification'da yok (bant genişletme?): "
                     f"{cas} scl={hc} classification={sorted(cl_hcodes)}")


# ---------------------------------------------------------------------------
# Katman 3 — h_code_index tutarlılığı
# ---------------------------------------------------------------------------

def check_index_vs_db(db: dict, idx: dict):
    """
    h_code_index'teki occurrence'lar substance_db'de gerçekten o H-kodu
    taşıyan maddeler olmalı.
    """
    for hc, data in idx.items():
        for cas in data.get("occurrences", []):
            if cas not in db:
                err(f"[K3] Index'te CAS yok: h_code={hc} cas={cas}")
                continue
            entry = db[cas]
            if "_alias" in entry:
                err(f"[K3] Index'te alias CAS: h_code={hc} cas={cas}")
                continue
            cl_hcodes = {c["h_code"] for c in entry.get("classification", [])}
            if hc not in cl_hcodes:
                err(f"[K3] Index ↔ DB çelişkisi: h_code={hc} cas={cas} "
                    f"ama classification={sorted(cl_hcodes)}")


# ---------------------------------------------------------------------------
# Katman 4 — Yetim kayıt tespiti
# ---------------------------------------------------------------------------

def check_orphans(db: dict):
    """
    classification veya scl_limits olan ama hiç H-kodu taşımayan
    kayıtları işaretle (veri girişi hatası riski).
    """
    for cas, entry in db.items():
        if "_alias" in entry:
            continue
        cl = entry.get("classification", [])
        if cl and all(not c.get("h_code") for c in cl):
            warn(f"[K4] H-kodu olmayan classification: {cas}")

        for scl in entry.get("scl_limits", []):
            if not scl.get("h_code"):
                warn(f"[K4] H-kodu olmayan scl_limits girişi: {cas}")
                break


# ---------------------------------------------------------------------------
# Ana akış
# ---------------------------------------------------------------------------

def main():
    sys.stdout.reconfigure(encoding="utf-8")

    if not DB_PATH.exists():
        print(f"HATA: {DB_PATH} bulunamadı — önce build_substance_db.py çalıştırın")
        sys.exit(1)
    if not IDX_PATH.exists():
        print(f"HATA: {IDX_PATH} bulunamadı — önce generate_h_code_index.py çalıştırın")
        sys.exit(1)

    db  = json.loads(DB_PATH.read_text(encoding="utf-8"))
    idx = json.loads(IDX_PATH.read_text(encoding="utf-8"))

    print("Kontrol ediliyor...")
    check_aliases(db)
    check_scl_vs_classification(db)
    check_index_vs_db(db, idx)
    check_orphans(db)

    print(f"  Hata   : {len(ERRORS)}")
    print(f"  Uyarı  : {len(WARNINGS)}")

    if WARNINGS:
        print("\n--- UYARILAR ---")
        for w in WARNINGS[:20]:
            print(" ", w)
        if len(WARNINGS) > 20:
            print(f"  ... ve {len(WARNINGS)-20} uyarı daha")

    if ERRORS:
        print("\n--- HATALAR ---")
        for e in ERRORS:
            print(" ", e)
        print("\nBuild DURDU.")
        sys.exit(1)

    print("\nTüm kontroller geçti. Build devam edebilir.")


if __name__ == "__main__":
    main()
