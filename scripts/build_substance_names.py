"""
build_substance_names.py — Çok dilli madde isim veritabanı üretir.

Giriş:
  data/substance_db.json   → EN isimleri (ECHA ATP22)
  data/sea_ek6_tr.json     → TR isimleri (SEA Ek-6)

Çıktı:
  data/substance_names.json  → {cas: {en: "...", tr: "..."}}

Öncelik: substance_db EN önce, sea_ek6_tr TR önce.
Diğer diller eklemek için aynı pattern'i uygula.
"""

import json
import sys
from pathlib import Path

DB_PATH    = Path(__file__).parent.parent / "data" / "substance_db.json"
TR_PATH    = Path(__file__).parent.parent / "data" / "sea_ek6_tr.json"
OUT_PATH   = Path(__file__).parent.parent / "data" / "substance_names.json"


def main():
    sys.stdout.reconfigure(encoding="utf-8")

    db = json.loads(DB_PATH.read_text(encoding="utf-8"))
    tr = json.loads(TR_PATH.read_text(encoding="utf-8"))

    names: dict[str, dict] = {}

    def _clean(s: str) -> str:
        return s.replace("\xa0", " ").strip()

    # 1. substance_db'den EN isimlerini topla (alias dahil → primary CAS'a yönlendir)
    for cas, entry in db.items():
        if "_alias" in entry:
            continue
        en_names = [_clean(n) for n in entry.get("names", []) if n.strip()]
        en_str = "; ".join(en_names)
        if en_str:
            names.setdefault(cas, {})["en"] = en_str

    # 2. sea_ek6_tr'den TR isimlerini ekle
    for cas, entry in tr.items():
        if "_alias" in entry:
            target = entry["_alias"]
            # alias ise primary CAS'a yaz
            if target in names:
                cas = target
            else:
                continue

        tr_names = [_clean(n) for n in entry.get("names", []) if n.strip()]
        tr_str = "; ".join(tr_names)
        if tr_str:
            names.setdefault(cas, {})["tr"] = tr_str

        # sea_ek6_tr'deki name_en alanıyla EN yoksa tamamla
        name_en = _clean(entry.get("name_en", ""))
        if name_en and cas in names and "en" not in names[cas]:
            names[cas]["en"] = name_en

    # Sırala
    names = dict(sorted(names.items()))

    OUT_PATH.write_text(json.dumps(names, ensure_ascii=False, indent=2), encoding="utf-8")

    total   = len(names)
    with_tr = sum(1 for v in names.values() if v.get("tr"))
    with_en = sum(1 for v in names.values() if v.get("en"))
    print(f"Toplam kayıt : {total}")
    print(f"EN adı var   : {with_en}")
    print(f"TR adı var   : {with_tr}")
    print(f"TR adı yok   : {total - with_tr}")
    print(f"\nKaydedildi   : {OUT_PATH}")

    print("\n--- Örnek ---")
    for cas in ["1310-73-2", "7647-01-0", "7664-93-9"]:
        print(f"  {cas}: {names.get(cas)}")


if __name__ == "__main__":
    main()
