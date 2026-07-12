"""
sea_ek6_tr.json — op="<", min=null SCL satırlarını düzelt.
substance_db.json'dan doğru min değerlerini alır.

7 kural:
1. substance_db forms[] dizisini de tarar
2. Eşleştirme sadece aynı H-kod ailesinde (H314/H315, H372/H373)
3. H317, H334 zincire girmez (tek eşikli)
4. H272 ayrı işlenir
5. Zincir tepesinde max=None geçerli
6. Eşleşme bulunamazsa "elle_girilecek" listesine düşer
7. Komşu kademelerle çakışma assertion kontrolü
"""
import json, copy

SEA_PATH = "data/sea_ek6_tr.json"
DB_PATH  = "data/substance_db.json"

# H-kod aileleri — sadece bu aileler zincir mantığına girer
FAMILIES = {
    "skin":    {"H314", "H315", "H316"},
    "eye":     {"H318", "H319"},
    "stot_re": {"H372", "H373"},
    "stot_se": {"H370", "H371", "H335"},  # H335 = STOT SE 3, tek eşikli
    "ox_liq":  {"H270", "H271", "H272"},
}

# H335 için min her zaman 0 (tek eşikli, gerçekten sıfırdan başlar)
SINGLE_THRESHOLD_ZERO = {"H335"}

# Zincire hiç girmeyen kodlar
NO_CHAIN = {"H317", "H334"}

def get_family(hcode):
    h4 = hcode[:4]
    for fam, codes in FAMILIES.items():
        if h4 in codes:
            return fam
    return None

def collect_db_scl(db_entry):
    """Ana kayıt + forms[] içindeki tüm scl_limits'i birleştirir."""
    all_scl = list(db_entry.get("scl_limits") or [])
    for form in (db_entry.get("forms") or []):
        all_scl.extend(form.get("scl_limits") or [])
    return all_scl

def find_min_in_db(db_scl, hcode, max_val):
    """
    substance_db'de aynı H kodu + max_val eşleşen range satırını bul,
    min değerini döndür. Bulamazsa None.
    """
    h4 = hcode[:4]
    best = None
    for s in db_scl:
        sh = (s.get("h_code") or "")[:4]
        if sh != h4:
            continue
        op = s.get("op", "")
        if op == "range":
            db_max = s.get("max")
            db_min = s.get("min")
            if db_max is not None and abs(float(db_max) - float(max_val)) < 0.001:
                best = float(db_min) if db_min is not None else None
    return best

with open(SEA_PATH, encoding="utf-8") as f:
    sea = json.load(f)
with open(DB_PATH, encoding="utf-8") as f:
    db = json.load(f)

def resolve_db_entry(cas):
    """substance_db'den CAS ara, alias takip et."""
    e = db.get(cas)
    if e is None:
        return None
    if "_alias" in e:
        e = db.get(e["_alias"])
    return e

fixed   = 0
manual  = []   # elle girilecekler
clashes = []   # assertion hatası

for cas, entry in sea.items():
    if "_alias" in entry:
        continue
    db_entry = resolve_db_entry(cas)
    db_scl   = collect_db_scl(db_entry) if db_entry else []
    name     = (entry.get("names") or ["?"])[0][:40]

    scl_list = entry.get("scl_limits") or []

    for scl in scl_list:
        if not (scl.get("op") == "<" and scl.get("min") is None):
            continue

        hcode = scl.get("h_code", "")
        h4    = hcode[:4]
        max_v = scl.get("max")

        # Kural 3: duyarlılaştırma — atla
        if h4 in NO_CHAIN:
            manual.append((cas, name, hcode, scl.get("class"), max_v, "NO_CHAIN (H317/H334)"))
            continue

        # Kural 4: H272 fiziksel tehlike — ayrı, substance_db'den bak
        fam = get_family(hcode)
        if fam is None:
            manual.append((cas, name, hcode, scl.get("class"), max_v, "Bilinmeyen aile"))
            continue

        min_v = find_min_in_db(db_scl, hcode, max_v)

        if min_v is None:
            # Fallback 1: H335 tek esikli — min=0 (gercekten sifirdan baslar)
            if h4 in SINGLE_THRESHOLD_ZERO:
                min_v = 0.0
            # Fallback 2: H314 1B icin ayni CAS'taki H315 max degerinden turet
            elif h4 == "H314" and "1B" in scl.get("class", ""):
                for s2 in scl_list:
                    if s2.get("h_code", "")[:4] in ("H315", "H316") and s2.get("max") is not None:
                        candidate = float(s2["max"])
                        if candidate < float(max_v):
                            min_v = candidate
                            break
            if min_v is None:
                manual.append((cas, name, hcode, scl.get("class"), max_v, "eslesme yok"))
                continue

        # Kural 7: çakışma kontrolü — min >= max olmamalı
        if min_v >= float(max_v):
            clashes.append((cas, name, hcode, min_v, max_v))
            manual.append((cas, name, hcode, scl.get("class"), max_v, f"ÇAKIŞMA: min={min_v} >= max={max_v}"))
            continue

        # Düzelt
        scl["op"]  = "range"
        scl["min"] = min_v
        fixed += 1

print(f"\n[OK] Duzeltilen satir sayisi : {fixed}")
print(f"[!!] Elle girilecek          : {len(manual)}")
if clashes:
    print(f"[XX] Cakisma hatasi          : {len(clashes)}")

if manual:
    print("\n--- ELLE GİRİLECEKLER ---")
    for row in manual:
        print(f"  CAS={row[0]:12s}  {row[4]:6}  {row[2]:5s}  {row[3]:25s}  Neden: {row[5]}")

# Değiştirilmiş dosyayı kaydet
with open(SEA_PATH, "w", encoding="utf-8") as f:
    json.dump(sea, f, ensure_ascii=False, indent=2)

print(f"\nDosya güncellendi: {SEA_PATH}")
