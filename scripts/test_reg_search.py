import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.regulation_search import verify_text_in_sds, search_regulation

# --- verify_text_in_sds ---
sds = "B1.4 Acil tel (UZM): UZEM — Ulusal Zehir Danisma Merkezi: 114 (KKDİK Ek-2 B1.4 zorunlu)"
r = verify_text_in_sds("UZEM", sds)
print("UZEM bulundu:", r["found"], "| context:", r["context"])

r2 = verify_text_in_sds("M-faktör hesabı", sds)
print("M-faktör bulundu:", r2["found"])

r3 = verify_text_in_sds("kkdik", sds)
print("kkdik (küçük harf) bulundu:", r3["found"])

# --- search_regulation ---
print()
results = search_regulation("H318 dominance H314 etiket")
for res in results[:3]:
    safe = lambda s: s.encode('ascii', errors='replace').decode('ascii')
    print(f"[{res['score']:.3f}] {safe(res['title'])}")
    print(" ", safe(res["text"][:120]))
    print()

print("---")
results2 = search_regulation("ATEmix karışım formül oral")
for res in results2[:3]:
    safe = lambda s: s.encode('ascii', errors='replace').decode('ascii')
    print(f"[{res['score']:.3f}] {safe(res['title'])}")
    print(" ", safe(res["text"][:120]))
    print()
