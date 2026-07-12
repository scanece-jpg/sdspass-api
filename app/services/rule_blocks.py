"""
rule_blocks.py — H koduna göre tetiklenen mevzuat kural blokları.

PDF/DOCX okumak yerine önceden derlenmiş, özlü mevzuat özetleri döner.
Her blok ~300-500 karakter. Toplam yük çok daha düşük.
"""

from __future__ import annotations

# ── H-kod ailesi → kural metni ─────────────────────────────────────────────────
# Her giriş: H kodu prefix (4 kar) → (başlık, mevzuat metni)

_H_RULES: dict[str, tuple[str, str]] = {

    # ── Akut Toksisite ──────────────────────────────────────────────────────────
    "H300": ("Akut Toks. 1 Oral", (
        "CLP Ek-I §3.1.2 — ATE oral: Kat.1 ≤5 mg/kg, Kat.2 ≤50 mg/kg, Kat.3 ≤300 mg/kg, Kat.4 ≤2000 mg/kg. "
        "Karışım ATE: formül 1/ATEmix = Σ(Ci/ATEi). B3.2'deki her bileşen için ATE kullanılır. "
        "† işareti: bileşen kendi sınıflandırmasında H300 taşıyabilir; karışım H301/H302 çıkabilir — normaldir."
    )),
    "H301": ("Akut Toks. 2-3 Oral", (
        "CLP Ek-I §3.1.2 — ATE oral: Kat.2 ≤50 mg/kg, Kat.3 ≤300 mg/kg. "
        "Karışım: B11'deki ATEmix hesabı belirleyicidir. Bileşen H300 olsa bile karışım H301/H302 çıkabilir."
    )),
    "H302": ("Akut Toks. 4 Oral", (
        "CLP Ek-I §3.1.2 — ATE oral Kat.4 ≤2000 mg/kg. "
        "Karışım sınıfında B11 ATE hesabına bak. %1 üzeri Kat.1-3 bileşen → karışım en az Kat.4."
    )),
    "H310": ("Akut Toks. 1-2 Dermal", (
        "CLP Ek-I §3.1.2 — ATE dermal: Kat.1 ≤50 mg/kg, Kat.2 ≤200 mg/kg, Kat.3 ≤1000 mg/kg, Kat.4 ≤2000 mg/kg."
    )),
    "H311": ("Akut Toks. 3 Dermal", "CLP Ek-I §3.1.2 — ATE dermal Kat.3 ≤1000 mg/kg."),
    "H312": ("Akut Toks. 4 Dermal", "CLP Ek-I §3.1.2 — ATE dermal Kat.4 ≤2000 mg/kg."),
    "H330": ("Akut Toks. 1-2 İnhalasyon", (
        "CLP Ek-I §3.1.2 — ATE inhalasyon (4h, buhar): Kat.1 ≤0,5 mg/L, Kat.2 ≤2,0 mg/L. "
        "B11'deki ATEmix inhalasyon hesabına bak."
    )),
    "H331": ("Akut Toks. 3 İnhalasyon", (
        "CLP Ek-I §3.1.2 — ATE inhalasyon (4h, buhar): Kat.3 ≤10,0 mg/L. "
        "Karışımda: B11 ATEmix inhalasyon ≤10,0 → H331; >10,0 → H332. "
        "KURAL: B11'de 'İnhalasyon: X mg/L/4h → H332' gibi bir hesap varsa bu gerekçedir — gerekçesizlik değildir."
    )),
    "H332": ("Akut Toks. 4 İnhalasyon", (
        "CLP Ek-I §3.1.2 — ATE inhalasyon (4h, buhar): Kat.4 ≤20,0 mg/L. "
        "B11 ATEmix >10,0 ve ≤20,0 → H332. Bileşen H331 olsa bile karışım H332 çıkabilir — normaldir."
    )),

    # ── Cilt Korozyon/Tahriş ────────────────────────────────────────────────────
    "H314": ("Cilt Aş. 1A/1B", (
        "CLP Ek-I §3.2.2 — Cilt Aş. 1: tam kalınlık cilt hasarı. "
        "1A: 3 dk içinde, 1B: >3 dk ≤1 saat içinde. "
        "SEA Ek-6 SCL: H314 varsa eşiğin üstünde bileşen → karışım H314. "
        "H314 içeren bileşen aynı zamanda H318 tetikler (CLP §3.3.3.3)."
    )),
    "H315": ("Cilt Tahriş. 2", (
        "CLP Ek-I §3.2.2 — Cilt Tahriş. 2: geri döndürülebilir hasar. "
        "SCL: SEA Ek-6'daki eşiğin altında H314 bileşen → H315. "
        "H314 ve H315 aynı anda verilemez (H314 baskındır)."
    )),

    # ── Göz Hasarı/Tahrişi ─────────────────────────────────────────────────────
    "H318": ("Göz Hasar. 1", (
        "CLP Ek-I §3.3.2 — Göz Hasar. 1: geri döndürülemez hasar. "
        "H314 içeren karışım → H318 otomatik tetiklenir (§3.3.3.3). "
        "H318 varken H319 yazılmaz (H318 baskındır)."
    )),
    "H319": ("Göz Tahriş. 2", (
        "CLP Ek-I §3.3.2 — Göz Tahriş. 2: geri döndürülebilir, ≤21 gün. "
        "H318 veya H314 varsa H319 çıkmaz. SCL eşiğine göre belirlenir."
    )),

    # ── Solunum/Cilt Duyarlılaştırma ───────────────────────────────────────────
    "H334": ("Solunum Duyar. 1", (
        "CLP Ek-I §3.4.2 — Solunum duyarlılaştırıcı Kat.1. "
        "Eşik yok — tek seferlik maruziyette duyarlılaştırma olabilir. "
        "KKDİK Ek-2 B8: uygun PPE zorunlu (N95/P3 filtreli solunum cihazı)."
    )),
    "H317": ("Cilt Duyar. 1", (
        "CLP Ek-I §3.4.2 — Cilt duyarlılaştırıcı Kat.1. "
        "Karışımda: SCL eşiği tanımlı değildir, genel konsantrasyon sınırları uygulanır."
    )),

    # ── STOT Tek Maruziyet ──────────────────────────────────────────────────────
    "H370": ("STOT SE 1", (
        "CLP Ek-I §3.8.2 — Spesifik organ toksisitesi, tek maruziyet Kat.1. "
        "Etkilenen organ belirtilmeli. Karışım: bileşen %1 üzeri → Kat.1 tetiklenir."
    )),
    "H371": ("STOT SE 2", "CLP Ek-I §3.8.2 — STOT SE Kat.2. Bileşen %10+ → karışım Kat.2."),
    "H335": ("STOT SE 3 Solunum", (
        "CLP Ek-I §3.8.2 — STOT SE 3: solunum yolu tahrişi. "
        "Karışım: SEA Ek-6'da tek eşikli (eşiğin altında H335 çıkmaz). "
        "KKDİK Ek-2 B8: yeterli havalandırma veya solunum koruyucu gerekli."
    )),

    # ── STOT Tekrarlı Maruziyet ─────────────────────────────────────────────────
    "H372": ("STOT RE 1", (
        "CLP Ek-I §3.9.2 — STOT RE Kat.1: süregelen/tekrarlı maruziyette organ hasarı. "
        "B8: uzun süreli maruziyet limiti (OEL/TWA) belirtilmeli (KKDİK Ek-2 §8.1)."
    )),
    "H373": ("STOT RE 2", (
        "CLP Ek-I §3.9.2 — STOT RE Kat.2. "
        "SCL: SEA Ek-6'da H372↔H373 zinciri olabilir; konsantrasyona göre kategori değişir."
    )),

    # ── Mutajen/Kanserojen/Üreme ────────────────────────────────────────────────
    "H340": ("Mutaj. 1A/1B", (
        "CLP Ek-I §3.5.2 — Germ hücre mutajenisitesi Kat.1A/1B. "
        "Karışım: bileşen %0,1 üzeri → bildirim zorunlu (H340/H341)."
    )),
    "H350": ("Kans. 1A/1B", (
        "CLP Ek-I §3.6.2 — Kanserojen Kat.1A/1B. "
        "Karışım: %0,1 üzeri → H350 tetiklenir. B15: sınırlı maruziyet gereksinimi."
    )),
    "H360": ("Üreme Toks. 1A/1B", (
        "CLP Ek-I §3.7.2 — Üreme toksisitesi Kat.1A/1B. "
        "Karışım: %0,3 üzeri → H360. KKDİK Ek-2: üreme çağındaki çalışanlar için özel uyarı."
    )),
    "H361": ("Üreme Toks. 2", "CLP Ek-I §3.7.2 — Üreme toks. Kat.2. Karışım %3+ → H361."),
    "H362": ("Emzirme Etkisi", "CLP Ek-I §3.7.2 — Emzirilen çocuklara etki. Ayrı etiket unsuru."),

    # ── Aspirasyon ─────────────────────────────────────────────────────────────
    "H304": ("Aspirasyon Toks. 1", (
        "CLP Ek-I §3.10.2 — Aspirasyon toksisitesi Kat.1: viskozite <20,5 mm²/s @40°C. "
        "Sıvı karışım: hidrokarbon bileşeni %10+ ve viskozite şartı → H304. "
        "KKDİK Ek-2 B8: kusturmayın uyarısı zorunlu."
    )),

    # ── Alevlenirlik ────────────────────────────────────────────────────────────
    "H224": ("Alev. Sıvı 1", "CLP Ek-I §2.6.2 — Parlama noktası <23°C, başlangıç kaynama <35°C. ADR Sınıf 3 PG I."),
    "H225": ("Alev. Sıvı 2", "CLP Ek-I §2.6.2 — Parlama noktası <23°C, başlangıç kaynama ≥35°C. ADR Sınıf 3 PG II."),
    "H226": ("Alev. Sıvı 3", "CLP Ek-I §2.6.2 — Parlama noktası ≥23°C ≤60°C. ADR Sınıf 3 PG III."),
    "H228": ("Alev. Katı 1-2", "CLP Ek-I §2.7.2 — Alevlenebilir katı. ADR Sınıf 4.1."),
    "H242": ("Isınan Kup.", "CLP Ek-I §2.15 — Isınarak infilak. ADR 5.2."),

    # ── Oksitleyici ─────────────────────────────────────────────────────────────
    "H270": ("Oks. Gaz 1", "CLP Ek-I §2.4.2 — Oksitleyici gaz Kat.1. ADR Sınıf 2."),
    "H271": ("Oks. Sıvı/Katı 1", "CLP Ek-I §2.13/2.14 — Patlama/yangın riski. ADR Sınıf 5.1 PG I."),
    "H272": ("Oks. Sıvı/Katı 2-3", "CLP Ek-I §2.13/2.14 — Oksitleyici sıvı/katı Kat.2/3. ADR Sınıf 5.1 PG II-III."),

    # ── Çevre ──────────────────────────────────────────────────────────────────
    "H400": ("Akuat. Akut 1", (
        "CLP Ek-I §4.1.2 — Akuatik akut Kat.1: LC50/EC50 ≤1 mg/L. M-faktörü uygulanır. "
        "Karışım: M×konsantrasyon toplamı ≥0,0001% → H400."
    )),
    "H410": ("Akuat. Kronik 1", "CLP Ek-I §4.1.2 — Kronik Kat.1: LC50/EC50 ≤1 mg/L + kalıcı. M-faktörü uygulanır."),
    "H411": ("Akuat. Kronik 2", "CLP Ek-I §4.1.2 — Kronik Kat.2: LC50/EC50 ≤10 mg/L."),
    "H412": ("Akuat. Kronik 3", "CLP Ek-I §4.1.2 — Kronik Kat.3: ≤1 mg/L BCF/kalıcılık yok ya da ≤100 mg/L."),

    # ── Basınçlı Gaz ────────────────────────────────────────────────────────────
    "H280": ("Basınçlı Gaz", "CLP Ek-I §2.5 — Basınçlı gaz. ADR Sınıf 2. B14: boşaltma talimatı."),
    "H281": ("Soğutulmuş Gaz", "CLP Ek-I §2.5 — Soğutulmuş sıvılaştırılmış gaz. Kriyojenik tehlike."),

    # ── Metal korozif ───────────────────────────────────────────────────────────
    "H290": ("Met. Aş.", (
        "CLP Ek-I §2.16 — Metallere aşındırıcı. "
        "B14: demir/çelik kapla depolamayın. B7: metalle temas → H2 gazı oluşabilir."
    )),
}

# ── Her denetimde her zaman dahil edilecek SDS bölüm gereklilikleri ─────────────
_ALWAYS_BLOCKS: list[tuple[str, str]] = [
    ("KKDİK Ek-2 — Temel SDS Gereklilikleri", (
        "B1.1: Ürün tanımlayıcı (ticari ad, kod). Karışımlar için 'karışım' ibaresi. "
        "B1.2: Kullanım (endüstriyel/mesleki/tüketici). "
        "B1.3: Tedarikçi (adres, telefon). "
        "B1.4: Acil telefon (UZEM: 114, 7/24). "
        "B2.1: Madde/karışım sınıflandırması — CLP uyumlu tüm tehlike sınıfları. "
        "B2.2: Etiket unsurları — piktogram, sinyal kelime, H/EUH/P kodları. "
        "B3.1/3.2: Bileşimde CAS, konsantrasyon, H kodları listesi."
    )),
    ("KKDİK Ek-2 — B8 Maruziyet Önlemleri", (
        "B8.1: Kontrol parametreleri — OEL (TWA/STEL), DNEL, PNEC. "
        "B8.2: PPE — göz (gözlük/siperlik), cilt (eldiven, önlük), solunum, genel. "
        "KKDİK §13: biyolojik limit değerleri uygunsa belirtilir."
    )),
    ("KKDİK Ek-2 — B11 Toksikolojik Bilgi", (
        "Akut toks.: oral/dermal/inhalasyon ATE veya LD50/LC50. "
        "Cilt/göz: korozyon/tahriş testi sonuçları. "
        "STOT: etkilenen organ ve yol. "
        "Kanserojen/mutajen/üreme: kategori ve kanıt düzeyi. "
        "ATEmix hesabı varsa buraya yazılır — bileşen H kodundan farklı karışım H kodu normaldir."
    )),
    ("KKDİK Ek-2 — B14 Taşımacılık (ADR)", (
        "UN numarası, taşıma adı, ADR sınıfı, ambalaj grubu (PG), tünel kodu. "
        "PG I en yüksek tehlike. ADR §2.1.3.5.5: test verisi yoksa en kötü senaryo (PG I). "
        "Deniz/hava: IMDG/IATA doldurulacaksa ayrı bilgi şartı."
    )),
]


def get_blocks_for_hcodes(h_codes: list[str]) -> list[dict]:
    """
    H kodlarına göre ilgili kural bloklarını döner.
    Her zaman dahil edilen SDS gereklilikleri + H koduna özgü kurallar.
    """
    blocks: list[dict] = []

    # 1. Her zaman dahil (SDS bölüm gereklilikleri)
    for title, text in _ALWAYS_BLOCKS:
        blocks.append({
            "type": "text",
            "text": f"[{title}]\n{text}",
        })

    # 2. H koduna özgü kurallar
    seen: set[str] = set()
    for hcode in h_codes:
        key = hcode[:4]  # H314 1A → H314
        if key in seen or key not in _H_RULES:
            continue
        seen.add(key)
        title, text = _H_RULES[key]
        blocks.append({
            "type": "text",
            "text": f"[{key} — {title}]\n{text}",
        })

    return blocks
