"""
SDS Denetim Endpoint — /api/v1/sds/review

Akış:
  1. validate_sds()           → V001-V027 kural sonuçları
  2. _build_sds_text()        → PDF motoruyla aynı sds_data'dan 16 bölüm düz metin
  3. build_context_blocks()   → ilgili mevzuat paragrafları
  4. Claude API               → bağımsız denetim raporu (Markdown)
"""

import os
import json as _json
import pathlib
from datetime import date
from fastapi import APIRouter, Body, HTTPException

router = APIRouter()

_SYSTEM_PROMPT = """Sen KKDİK ve SEA yönetmelikleri uzmanı bir GBF/SDS denetçisisin.
CLP Tüzüğü (EC 1272/2008), KKDİK, SEA, ADR ve ilgili ECHA kılavuzlarını tam olarak biliyorsun.

Sana üç kaynak verilecek:
  A) Denetlenecek SDS'in 16 bölüm okunabilir metni — PDF'deki gerçek değerler
  B) İlgili mevzuat paragrafları (SEA, KKDİK, CLP, ADR) — ek bağlam olarak kullan
  C) Otomatik kural kontrolü sonuçları (V001-V027 kodlu bulgular)

A kaynağı bölüm bölüm düz metin formatındadır. Bölümlerin içerdiği alanlar:
  product/supplier   → Bölüm 1 (kimlik ve tedarikçi)
  clp.all_h_codes    → Bölüm 2.1 (tam tehlike sınıflandırması)
  clp.h_codes        → Bölüm 2.2 etiket H kodları (dominance uygulanmış)
  clp.signal_word    → Bölüm 2.2 uyarı kelimesi
  components         → Bölüm 3.2 (bileşenler, CAS, konsantrasyon, H kodları)
  phys_props         → Bölüm 9 (fiziksel ve kimyasal özellikler)
  eco                → Bölüm 12 (ekoloji / sucul tehlike)
  transport          → Bölüm 14 (ADR taşıma)
  p_codes            → Bölüm 2.2 güvenlik önlemleri (P kodları)
  euh                → Bölüm 2.2 EUH kodları
  ate_mix_details    → Bölüm 11 ATEmix hesap detayı
  revision           → Bölüm 16 revizyon bilgisi

Görevin:
1. A kaynağındaki SDS verisini baştan sona oku.
2. Her bölümü KKDİK Ek-2 ve CLP Tüzüğü gerekliliklerine göre bağımsız olarak denetle.
3. Tespit ettiğin her sorunu şu şekilde raporla:
   - Hangi bölüm (B1–B16)
   - Ne eksik veya hatalı
   - Hangi mevzuat maddesine aykırı — madde/ek/tablo numarasıyla birlikte
   - Mevzuat kaynağına doğrudan bağlantı (aşağıdaki URL tablosundan)
   - Somut düzeltme adımı
4. C kaynağındaki otomatik bulgular varsa onları da açıkla ve yorumla.
5. Sorun tespit etmediğin bölümleri "## Uyumlu Bölümler" başlığı altında tek satırla listele:
   örn. "✓ B1 — Kimyasal tanımlama tam ve doğru."
   Bu bölüm ZORUNLUDUR — rapor her zaman hem hataları hem uyumlu bölümleri içermelidir.

Yanıtını şu formatta ver:
## Hatalar (Düzeltilmesi Zorunlu)
## Uyarılar (Kontrol Edilmeli)
## Bilgi Notları
## Uyumlu Bölümler
## Genel Değerlendirme

**Her bulgu (hata/uyarı/not) şu şablona göre yazılmalıdır:**
- **Alan:** [SDS bölümü ve alan adı, ör. B2.1 — H kodları]
- **Okunan değer:** [JSON'dan birebir alınan değer veya "mevcut değil"]
- **Sorun:** [neden yanlış olduğunun kısa açıklaması]
- **Beklenen:** [doğru değer veya format]
> 📋 **[Mevzuat Adı — Madde/Ek No]** — [kısa açıklama]

**Uyumlu bölümlerde her satır şu formatta olmalıdır:**
✅ **[Bölüm adı]** — Okunan: [JSON'daki değer veya "mevcut ve eksiksiz"] → Uygun

Her bulgu için dayanak şu formatta olsun:
> 📋 **[Mevzuat Adı — Madde/Ek No]** — [kısa açıklama]
> 🔗 [bağlantı metni](URL)

Mevzuat URL tablosu (bulguya göre uygun olanı seç):
- KKDİK (ana metin + tüm ekler aynı sayfada): https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=21737&MevzuatTur=7&MevzuatTertip=5
  → Ek-2 (GBF/SDS gereklilikleri), Ek-5 (muafiyetler), Ek-6 (SVHC) bu sayfada yer alır
- SEA Yönetmeliği   : https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=20764&MevzuatTur=7&MevzuatTertip=5
- CLP Tüzüğü (EU)   : https://eur-lex.europa.eu/legal-content/TR/TXT/?uri=CELEX:02008R1272-20231101
- ECHA CLP Kılavuzu : https://echa.europa.eu/tr/guidance-documents/guidance-on-clp
- ADR 2023          : https://unece.org/transport/dangerous-goods/adr-2023

Yanıt dili: Türkçe. Teknik terimler için parantez içinde İngilizce karşılık ekle.

## Bulgu Doğrulama Protokolü — Uygulanması Zorunlu

Bir bulgu yazmadan önce aşağıdaki kontrolleri sırayla yap:

**1. ATEmix kontrolü (H300-H302 oral / H310-H312 dermal / H330-H332 inhalasyon):**
B11'de ATEmix hesabı varsa ve hesap matematiksel olarak tutarlıysa (1/ATEmix = Σ Ci/ATEi formülü),
bileşen H kodu ile karışım H kodunun farklı olması normaldir — gerekçesizlik değildir.
Hesap B11'de yoksa VEYA rakamlar tutmuyorsa, bu bulgu konusudur.

**2. B3.2 ↔ B2.1 H kodu farkı († işareti):**
B3.2'deki bir bileşen H kodunun B2.1'de görünmemesi normaldir (bileşen katkısı eşiğin altında kalabilir).
Ancak B2.1'de yer alan bir H kodunun B3.2'de hiçbir bileşende dayanağı yoksa, bu ayrı bir bulgudur.
"Bileşen H331, karışım H332" gibi ATEmix kaynaklı farklılıklar kural 1 kapsamındadır.

**3. Zorunlu / Opsiyonel ayrımı:**
Mevzuat ifadesinde "verilir / sağlanır / bulunur" → zorunlu gereklilik.
"Sağlanabilir / verilebilir / eklenebilir" → opsiyonel. İkisini aynı ağırlıkta hata sayma.
Opsiyonel öneriler "Hatalar (Düzeltilmesi Zorunlu)" bölümüne yazılamaz; en fazla "Uyarılar" bölümüne gider.
Bir alan mevzuatta zorunlu sayılıyor olsa bile, kullanıcı geçerli bir içerik girmişse ("yok", "—", boşluk yerine açıklayıcı metin)
bu girişi yetersiz bulmak için ayrıca mevzuattan açık bir format şartı gösterilmelidir.

**4. Metin doğrulama (halüsinasyon önleme):**
Bir terimi, kısaltmayı veya alanı "eksik" ya da "çelişkili" olarak raporlamadan önce
o terimin SDS metninde birebir geçip geçmediğini doğrula (Ctrl+F mantığıyla ara).
Metinde bulunmayan bir ifadeye dayanan bulgu yazma.

**5. Başlık / B2.1 tutarsızlığı:**
Belgenin üst bilgi / metadata alanındaki H-kodu özeti ile B2.1 tablosu karşılaştırılmalıdır.
Tutarsızlık varsa bulgu "B2.1 içinde çelişki" değil "başlık ile B2.1 tutarsızlığı" olarak tanımlanmalıdır.

**6. Kaynak sınırlaması (uydurma hüküm önleme):**
Bir bulgunun mevzuat dayanağı, SANA VERİLEN B kaynağı (rule_blocks / sistem bağlamı) içindeki
paragraflardan biriyle birebir eşleşmelidir. B kaynağında açıkça yer almayan bir hükmü
"ima eder", "mantıken gerektirir" veya "ruhuna aykırıdır" gerekçesiyle bulgu olarak yazma.
Kural metnini okumadan bir madde numarası veya kota rakamı türetme.
Verilmeyen bilgi → bulgu yok; verilmeyen bilgi → "kapsam dışı" notu.

**6b. B3.2 ↔ B2.1 kategori farkı (SCL bant kaynaklı):**
Konsantrasyon-bağımlı sınıflandırılan maddelerde (ör. formik asit, asetik asit, H2O2) B3.2 ve B2.1'deki
alt-kategori (1A/1B) farklı olabilir — bu HATA DEĞİLDİR.
Nedeni: B3.2'deki sınıflandırma maddenin kendi CLP Ek-VI/veritabanı sınıfıdır (saf madde olarak ne?).
B2.1'deki sınıflandırma ise karışımın hesaplanmış sınıfıdır — SCL bantlarına göre bileşenin karışımdaki
konsantrasyonuna karşılık gelen alt-kategori seçilir.
Örnek: Formik asit saf madde olarak Skin Corr. 1A (≥%90), ama %15 konsantrasyonlu karışımda
SCL bant kuralı gereği karışım B2.1'de Skin Corr. 1B çıkar. B3.2'de "1A", B2.1'de "1B" → DOĞRU.
Bu tür farklılıkları "tutarsızlık" veya "hata" olarak raporlama. BULGU YOK.

**6a. M-faktör bağlam kısıtlaması:**
M-faktör (çarpım faktörü) YALNIZCA sucul ortam toksisitesi (H400 Akut Kat.1 / H410-H412 Kronik) sınıflandırmasında
karışım hesabına girer. Cilt aşındırıcılık (H314), göz hasarı (H318), akut toksisite (H300/H310/H330),
solunum tahrişi veya başka tehlike sınıflarında M-faktör kavramı geçerli değildir — bu bağlamlarda
M-faktör gerekliliği iddia eden herhangi bir bulgu yazma.

---

## ARAÇ KULLANIM PROTOKOLÜ

Aşağıdaki araçlar gerçek fonksiyon çağrılarıdır — metin üretme değil, gerçek veri sorgulama.
Bir bulgu yazmadan önce ilgili aracı çağır ve dönen sonuca göre karar ver.

**Araçlar:**
- `verify_text_in_sds(phrase)` — SDS metninde bir ifadeyi ara; `found` alanını kontrol et
- `search_regulation(query)` — Mevzuat kural bloklarında ara; sonuç boşsa hükmü uydurma
- `get_substance_scl(cas_no, h_code)` — SEA Ek-6 SCL (özel konsantrasyon sınırı) sorgula; `found=False` ise kayıtlı sınır yok

---

## ÇÖZÜMLÜ ÖRNEKLER — Her Denetimde Bu Mantığı İzle

### Örnek 1: H314 + H318 dominance

SDS: B2.1'de H314+H318 var, B2.2 etikette yalnızca H314 var.

```
[Araç çağrısı] verify_text_in_sds("H318 etiket")
[Sonuç]        found=False → etiket satırında H318 yok

[Araç çağrısı] search_regulation("H314 H318 dominance etiket")
[Sonuç]        "H314 içeren karışım H318 otomatik tetikler (§3.3.3.3).
                H314 baskın (dominant) — H318 etikette ayrıca gösterilmez."

[Karar]        B2.2'de H318 yok → CLP §3.3.3.3 gereği DOĞRU.
               BULGU YOK.
```

### Örnek 2: ATEmix — bileşen H331, karışım H332

SDS: B3.2'de formik asit H331, B2.1'de H332, B11'de ATEmix=14,2 mg/L/4h.

```
[Araç çağrısı] verify_text_in_sds("ATEmix")
[Sonuç]        found=True, context="ATEmix inhalasyon = 14,2 mg/L/4h → H332"

[Karar]        10,0 < 14,2 ≤ 20,0 → H332 eşiği. Hesap tutarlı.
               BULGU YOK. "Bileşen H331 iken karışım H332" hata değildir.
```

### Örnek 3: SCL çok-bantlı seçim — formik asit %15, B2.1'de H314 (1A)

SDS: B3.2'de formik asit (CAS 64-18-6) %15, B2.1'de H314 Cilt Aşınd. 1A yazıyor.

```
[Araç çağrısı] get_substance_scl("64-18-6", "H314")
[Sonuç]        found=True, bands=[
                 {h_class: "Cilt Aşınd. 1A", c_min: 90.0, c_max: null},
                 {h_class: "Cilt Aşınd. 1B", c_min: 10.0, c_max: 90.0},
                 {h_class: "Cilt Tah. 2",    c_min:  2.0, c_max: 10.0}
               ]

[Karar]        Konsantrasyon %15 — hangi banda düşüyor?
               1A bandı: c_min=90 → %15 < 90 → 1A HAYIR
               1B bandı: 10 ≤ 15 < 90 → 1B EVET
               SDS'te "1A" yazıyor → yanlış.
               BULGU VAR — H314 kategorisi 1A değil 1B olmalı.
```

UYARI: bands listesi boş veya tek bantlı dönse bile tek eşik karşılaştırması
yapma. Her zaman tüm bantları kontrol et; konsantrasyon hangi aralığa düşüyorsa
o kategori geçerlidir."""


def _format_ate_b11(sds_data: dict) -> list[str]:
    """ate_mix_details'dan B11 için okunabilir ATEmix satırları üretir."""
    details = sds_data.get("ate_mix_details") or {}
    if not details:
        return []
    _route_tr = {"oral": "Oral", "dermal": "Dermal", "inhal": "İnhalasyon"}
    lines = ["ATEmix hesabı (CLP Ek-I §3.1.3.6 / SEA §3.1.3.6.2):"]
    for route, rd in details.items():
        if not isinstance(rd, dict):
            continue
        ate_val  = rd.get("ateMix") or rd.get("ate_mix")
        code     = rd.get("resultCode") or rd.get("result_code") or "sınıflandırma yok"
        unk_pct  = rd.get("unknownPct", 0)
        route_tr = _route_tr.get(route, route)
        line = f"  {route_tr}: ATEmix = {ate_val} → {code}"
        if unk_pct and float(unk_pct) > 0:
            line += f" (bilinmeyen konsantrasyon: %{unk_pct})"
        lines.append(line)
    return lines


def _format_oel_b8(sds_data: dict, components: list) -> list[str]:
    """B8 — OEL/TWA/STEL değerlerini bileşen bazında listeler."""
    try:
        from app.services.tr_oel_service import get_oel_table
    except Exception:
        return []
    lines = []
    for c in (components or sds_data.get("components", [])):
        cas = c.get("cas_no") or c.get("cas", "")
        if not cas:
            continue
        try:
            oel = get_oel_table(cas)
        except Exception:
            continue
        if not oel:
            continue
        name = c.get("name_tr") or c.get("name") or cas
        for row in oel:
            twa  = row.get("twa")  or row.get("TWA")  or "—"
            stel = row.get("stel") or row.get("STEL") or "—"
            unit = row.get("unit") or "mg/m³"
            lines.append(f"  OEL {name} (CAS {cas}): TWA={twa} {unit} | STEL={stel} {unit}")
    return lines if lines else ["  OEL: Bileşenler için ulusal OEL tablosunda kayıt yok"]


def _format_disposal_b13(sds_data: dict) -> list[str]:
    """B13 — atık kodu ve bertaraf yönetmeliği."""
    try:
        from app.services.tr_mevzuat_service import get_disposal_content
        disposal = get_disposal_content(sds_data.get("clp", {}).get("all_h_codes", []))
    except Exception:
        disposal = None
    waste_code = sds_data.get("waste_code") or sds_data.get("product", {}).get("waste_code") or "—"
    lines = [f"  Atık kodu (EWC/AVY): {waste_code}"]
    if disposal:
        lines.append(f"  Bertaraf: {str(disposal)[:300]}")
    else:
        lines.append("  Bertaraf: Yerel yönetmeliklere uygun bertaraf.")
    return lines


def _format_transport_b14(sds_data: dict) -> list[str]:
    """B14 — IMDG (deniz) ve IATA (hava) taşıma bilgileri + çevre tehlikeli."""
    transport = sds_data.get("transport", {}) or {}
    lines = []
    sea = transport.get("sea", {}) or {}
    if sea.get("un_no") or sea.get("un"):
        un  = sea.get("un_no") or sea.get("un", "—")
        cls = sea.get("class", "—")
        pg  = sea.get("pg", "—")
        mp  = "Evet" if sea.get("marine_pollutant") else "Hayır"
        lines.append(f"  IMDG (Deniz): UN {un} | Sınıf {cls} | PG {pg} | Deniz kirleticisi: {mp}")
    air = transport.get("air", {}) or {}
    if air.get("un_no") or air.get("un"):
        un  = air.get("un_no") or air.get("un", "—")
        cls = air.get("class", "—")
        pg  = air.get("pg", "—")
        lines.append(f"  IATA (Hava): UN {un} | Sınıf {cls} | PG {pg}")
    env = transport.get("env_hazard") or transport.get("road", {}).get("env_hazard")
    if env is not None:
        lines.append(f"  Çevre açısından tehlikeli: {'Evet' if env else 'Hayır'}")
    return lines


def _build_sds_text(sds_data: dict, h_codes: list, phys_props: dict, components: list) -> str:
    """
    PDF motoruyla aynı sds_data yapısından 16 bölüm okunabilir metin üretir.
    PDF endpoint'in döndürdüğü sds_data direkt buraya girer — ham dict/liste yok.
    """
    product  = sds_data.get("product", {})
    supplier = sds_data.get("supplier", {})
    clp      = sds_data.get("clp", {})
    euh_data = sds_data.get("euh", {})
    p_data   = sds_data.get("p_codes", {})
    eco      = sds_data.get("eco", {})
    ppe      = sds_data.get("ppe", {})
    transport= sds_data.get("transport", {})
    revision = sds_data.get("revision", {})
    phys     = sds_data.get("phys_props", {}) or phys_props

    # Türkçe görüntüleme dönüşümleri (PDF ile aynı)
    _SIGNAL_TR = {"danger": "TEHLİKE", "warning": "UYARI", "none": "—"}
    _USAGE_TR  = {
        "industrial":   "Endüstriyel",
        "professional": "Mesleki/Profesyonel",
        "consumer":     "Tüketici",
    }
    signal_raw = clp.get("signal_word", "")
    signal_tr  = _SIGNAL_TR.get(signal_raw.lower(), signal_raw)
    usage_raw  = product.get("usage", "industrial")
    usage_tr   = _USAGE_TR.get(usage_raw.lower(), usage_raw)

    # ── EUH kodları ──────────────────────────────────────────────────────────
    euh_codes = []
    if isinstance(euh_data, dict):
        euh_codes = euh_data.get("codes", []) or []
    elif isinstance(euh_data, list):
        euh_codes = euh_data

    # ── P kodları ─────────────────────────────────────────────────────────────
    label_sel, sds_mand, sds_eval = [], [], []
    if isinstance(p_data, dict):
        lbl = p_data.get("label", {})
        if isinstance(lbl, dict):
            label_sel = lbl.get("selected", []) or []
        sds_cls = p_data.get("sds", {})
        if isinstance(sds_cls, dict):
            sds_mand = sds_cls.get("mandatory", []) or []
            sds_eval = sds_cls.get("evaluate", []) or []

    # ── ADR ──────────────────────────────────────────────────────────────────
    road = {}
    if isinstance(transport, dict):
        road = transport.get("road", {}) or {}
    _un_raw = road.get('un', '-')
    _un_str = _un_raw if str(_un_raw).upper().startswith('UN') else f"UN {_un_raw}"
    if road.get("un"):
        try:
            from app.services.transport_adr_service import get_adr_details as _get_adr
            _adr_det = _get_adr(_un_str, road.get('pg', 'II'))
        except Exception:
            _adr_det = {}
        _kemler  = _adr_det.get('kemler') or road.get('kemler_code') or '—'
        _tunnel  = _adr_det.get('tunnel_code') or road.get('tunnel_code') or '—'
        _clf_code= _adr_det.get('classification_code') or '—'
        adr_line = (
            f"{_un_str} | Sınıf {road.get('class','-')} | "
            f"PG {road.get('pg','-')} | {road.get('shipping_name') or road.get('label','-')} | "
            f"Kemler: {_kemler} | Tünel: {_tunnel} | Sınıf Kodu: {_clf_code}"
        )
    else:
        adr_line = "Tehlikeli madde değil / belirsiz"

    # ── KKE ──────────────────────────────────────────────────────────────────
    ppe_line = "belirtilmemiş"
    if isinstance(ppe, dict):
        parts = []
        for key, label in [("eye","Göz"),("skin","Cilt"),("resp","Solunum"),("hand","El")]:
            val = ppe.get(key)
            if val and isinstance(val, str) and val.strip():
                parts.append(f"{label}: {val.strip()[:80]}")
        ppe_line = " | ".join(parts) if parts else "belirtilmemiş"

    # ── Ekoloji ───────────────────────────────────────────────────────────────
    eco_h = []
    if isinstance(eco, dict):
        eco_h = eco.get("h_codes", []) or []
    eco_line = ", ".join(eco_h) if eco_h else "Sucul tehlike sınıfı yok"

    # ── PBT ──────────────────────────────────────────────────────────────────
    pbt_h = {"H400","H410","H411","H412","H413"}
    has_pbt = bool(set(eco_h) & pbt_h)
    pbt_line = (
        f"Karışım sucul tehlike içeriyor ({', '.join(eco_h)}). PBT/vPvB değerlendirmesi gerekli."
        if has_pbt else "Bu karışım PBT veya vPvB kriterlerini karşılamamaktadır."
    )

    # ── Bileşenler ────────────────────────────────────────────────────────────
    try:
        from app.services.reach_db import get_reg_no, get_ec_no as _get_ec
    except Exception:
        get_reg_no = _get_ec = lambda x: ""
    comp_lines = []
    for c in (components or sds_data.get("components", [])):
        name  = c.get("name_tr") or c.get("name") or c.get("cas_no", "?")
        conc  = c.get("conc") or c.get("concentration", "?")
        cas   = c.get("cas_no") or c.get("cas", "")
        ec    = c.get("ec_no", "") or _get_ec(cas) or "—"
        reach = c.get("reach_no", "") or get_reg_no(cas) or "—"
        h_list= ", ".join(
            h.get("h_code","") for h in (c.get("hazards") or []) if h.get("h_code")
        )
        line = f"  • {name} (CAS: {cas} | EC: {ec} | REACH: {reach}) — %{conc}"
        if h_list: line += f" | H: {h_list}"
        comp_lines.append(line)

    # ── Fiziksel özellikler ───────────────────────────────────────────────────
    def _pv(key, unit=""):
        v = phys.get(key)
        if v is None: return "N/A"
        if isinstance(v, dict):
            v = v.get("display") or v.get("value") or v.get("calc")
        return f"{v} {unit}".strip() if v is not None else "N/A"

    # ── B4-B8 cümleleri ───────────────────────────────────────────────────────
    sec4 = sec5 = sec6 = sec7 = ""
    mixture_form = product.get("form", "liquid")
    try:
        from app.services.sds_sentence_service import generate_section
        for no, var in [(4,"sec4"),(5,"sec5"),(6,"sec6"),(7,"sec7")]:
            res = generate_section(no, h_codes, mixture_form)
            bullets = res.get("bullets", [])
            txt = res.get("text", "") or (" | ".join(bullets) if bullets else "N/A")
            if no == 4: sec4 = txt
            if no == 5: sec5 = txt
            if no == 6: sec6 = txt
            if no == 7: sec7 = txt
        res8 = generate_section(8, h_codes, mixture_form)
        ppe_motor = res8.get("ppe", {})
        ppe_line = " | ".join(
            f"{lbl}: {ppe_motor.get(k,'').strip()[:80]}"
            for k, lbl in [("eye","Göz"),("skin","Cilt"),("resp","Solunum")]
            if ppe_motor.get(k,"").strip()
        ) or ppe_line
    except Exception:
        pass

    lines = [
        "=== GBF/SDS TAM METNİ (16 BÖLÜM) ===",
        "",
        f"BÖLÜM 1 — Madde/Karışım ve Şirket/Üstlenen Tanımlaması",
        f"B1.1 Ürün adı        : {product.get('name') or 'belirtilmemiş'}",
        f"     Ürün kodu       : {product.get('code') or '-'}",
        f"     Kullanım        : {usage_tr}",
        f"B1.3 Tedarikçi       : {supplier.get('name') or 'belirtilmemiş'}",
        f"     Adres           : {supplier.get('address') or 'belirtilmemiş'}",
        f"     Telefon         : {supplier.get('phone') or 'belirtilmemiş'}",
        f"     E-posta         : {supplier.get('email') or 'belirtilmemiş'}",
        f"B1.4 Acil tel (şirket): {supplier.get('emergency_tel') or 'belirtilmemiş'}",
        f"B1.4 Acil tel (UZM)  : UZEM — Ulusal Zehir Danışma Merkezi: 114 (KKDİK Ek-2 B1.4 zorunlu)",
        "",
        f"BÖLÜM 2 — Zararlılık Tanımlaması",
        f"B2.1 Sınıflandırma (tüm H kodları) : {', '.join(clp.get('all_h_codes', h_codes)) or 'yok'}",
        *[
            f"  → {p.get('h_code','')} ({p.get('h_class','')}) | "
            f"Kaynak: {p.get('cutoff_source','?')} | "
            f"Eşik: %{p.get('cutoff_value','?')} | "
            f"Gerekçe: {p.get('reason','')}"
            for p in (clp.get('passed') or [])
            if p.get('h_code')
        ],
        f"B2.1 EUH kodları                   : {', '.join(euh_codes) or 'yok'}",
        f"B2.2 Etiket H kodları (dominant)   : {', '.join(clp.get('h_codes', h_codes)) or 'yok'}",
        f"     NOT: Etiket H kodları B2.1'den az olabilir — CLP dominance kuralı gereği",
        f"     H314 varsa H318 etiketten çıkarılır (H314 zaten H318'i kapsar); bu normaldir.",
        f"B2.2 Sinyal kelimesi : {signal_tr}",
        f"B2.2 Piktogramlar    : {', '.join(clp.get('pictograms', [])) or 'yok'}",
        f"B2.2 Etiket P kodları: {', '.join(label_sel) or 'yok'}",
        f"B2.3 PBT/vPvB        : {pbt_line}",
        "",
        f"BÖLÜM 3 — Bileşim/İçindekiler Hakkında Bilgi",
        *comp_lines,
        "",
        f"BÖLÜM 4 — İlk Yardım Önlemleri",
        sec4[:500] if sec4 else "N/A",
        "",
        f"BÖLÜM 5 — Yangınla Mücadele Önlemleri",
        sec5[:400] if sec5 else "N/A",
        "",
        f"BÖLÜM 6 — Kaza Sonucu Yayılmaya Karşı Önlemler",
        sec6[:400] if sec6 else "N/A",
        "",
        f"BÖLÜM 7 — Elleçleme ve Depolama",
        sec7[:400] if sec7 else "N/A",
        "",
        f"BÖLÜM 8 — Maruziyet Kontrolleri/Kişisel Korunma",
        f"KKE: {ppe_line}",
        *_format_oel_b8(sds_data, components),
        "",
        f"BÖLÜM 9 — Fiziksel ve Kimyasal Özellikler",
        f"Parlama noktası   : {_pv('flash_point','°C')}",
        f"Kaynama noktası   : {_pv('boiling_point','°C')}",
        f"Yoğunluk          : {_pv('density','g/mL')}",
        f"pH                : {_pv('ph')}",
        f"Buhar basıncı     : {_pv('vapor_pressure','hPa')}",
        f"Viskozite         : {_pv('viscosity','mm²/s')}",
        f"Su çözünürlüğü    : {_pv('solubility','mg/L')}",
        f"Tutuşma sıc.      : {_pv('auto_ignition','°C')}",
        f"Log Kow           : {_pv('log_kow')}",
        f"Erime noktası     : {_pv('melting_point','°C')}",
        "",
        f"BÖLÜM 10 — Kararlılık ve Reaktivite",
        f"H kodlarına göre değerlendirme: {', '.join(h_codes)}",
        "",
        f"BÖLÜM 11 — Toksikolojik Bilgi",
        f"Akut toksisite H kodları: {', '.join(h_codes)}",
        *_format_ate_b11(sds_data),
        "",
        f"BÖLÜM 12 — Ekolojik Bilgi",
        f"Ekolojik H kodları: {eco_line}",
        f"PBT/vPvB          : {pbt_line}",
        "",
        f"BÖLÜM 13 — Bertaraf Etme",
        *_format_disposal_b13(sds_data),
        "",
        f"BÖLÜM 14 — Taşımacılık Bilgisi",
        f"ADR (Karayolu): {adr_line}",
        *_format_transport_b14(sds_data),
        "",
        f"BÖLÜM 15 — Mevzuat Bilgisi",
        f"KKDİK kapsamında kayıtlı bileşenler listesi yukarıda (B3.2).",
        "",
        f"BÖLÜM 16 — Diğer Bilgiler",
        f"SDS zorunlu P kodları   : {', '.join(sds_mand) or 'yok'}",
        f"SDS değerl. P kodları   : {', '.join(sds_eval[:12]) or 'yok'}",
        f"Revizyon tarihi         : {revision.get('date', 'belirtilmemiş')}",
        f"Revizyon no             : {revision.get('no', '-')}",
        f"Revizyon notları        : {revision.get('notes', '-')}",
        "",
        "=== SDS METNİ SONU ===",
    ]
    return "\n".join(lines)


@router.post("/api/v1/sds/review")
async def sds_review(data: dict = Body(...)):
    import traceback as _tb
    try:
        import anthropic as _anthropic
    except ImportError:
        raise HTTPException(status_code=500, detail="anthropic paketi kurulu değil")

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY tanımlı değil")

    try:
        h_codes    = list(data.get("h_codes", []))
        phys_props = data.get("phys_props", {})
        components = data.get("components", [])

        sds_xml          = data.get("sds_xml") or None
        full_sds_data    = data.get("full_sds_data") or None
        sds_data_simple  = data.get("sds_data", {})

        # ── Motor düzeltmeleri ────────────────────────────────────────────────
        if full_sds_data:
            sds_for_validator = dict(full_sds_data)
            clp_val = dict(sds_for_validator.get("clp", {}))
            try:
                from app.services.ghs_pictogram import get_ghs_codes
                clp_val["pictograms"] = get_ghs_codes(h_codes)
            except Exception:
                pass
            sds_for_validator["clp"] = clp_val
        else:
            all_h_codes = list(sds_data_simple.get("clp", {}).get("all_h_codes", h_codes))
            if "H314" in h_codes and "H318" not in all_h_codes:
                all_h_codes = all_h_codes + ["H318"]
            try:
                from app.services.ghs_pictogram import get_ghs_codes
                motor_pictograms = get_ghs_codes(h_codes)
            except Exception:
                motor_pictograms = sds_data_simple.get("clp", {}).get("pictograms", [])
            sds_data_simple = dict(sds_data_simple)
            sds_data_simple["clp"] = {
                **sds_data_simple.get("clp", {}),
                "all_h_codes": all_h_codes,
                "pictograms":  motor_pictograms,
            }
            sds_for_validator = sds_data_simple

        # ── 1. Kural kontrolü (V001-V027) ──────────────────────────────────────
        from app.services.sds_validator import validate_sds
        issues = validate_sds(sds_for_validator, h_codes, phys_props, components)
        issues = [i for i in issues if i.get("code") not in ("V013", "V015")]

        summary = {
            "error":   sum(1 for i in issues if i["level"] == "error"),
            "warning": sum(1 for i in issues if i["level"] == "warning"),
            "info":    sum(1 for i in issues if i["level"] == "info"),
        }

        # ── 2. SDS verisi — XML öncelikli, yoksa metin özeti ────────────────────
        if sds_xml:
            sds_text = sds_xml
        else:
            sds_text = _build_sds_text(sds_for_validator, h_codes, phys_props, components)

        # ── 3. Mevzuat bağlamı ─────────────────────────────────────────────────
        kb_blocks = []

        # ── 4. Kural sonuçları metni ───────────────────────────────────────────
        _icon = {"error": "❌", "warning": "⚠️", "info": "ℹ️"}
        issues_text = "=== OTOMATİK KURAL KONTROLÜ (V001-V027) ===\n\n"
        if not issues:
            issues_text += "Hiçbir kural ihlali tespit edilmedi.\n"
        else:
            for iss in issues:
                issues_text += (
                    f"{_icon.get(iss['level'],'•')} [{iss['code']}] "
                    f"Bölüm {iss['section']}: {iss['msg']}"
                )
                if iss.get("rule"):
                    issues_text += f"\n   Dayanak: {iss['rule']}"
                issues_text += "\n\n"
        issues_text += "=== KURAL KONTROLÜ SONU ==="

        # ── 5. Tool tanımları ──────────────────────────────────────────────────
        _tools = [
            {
                "name": "get_substance_scl",
                "description": (
                    "Bir bileşenin CAS numarası ve H kodu için SEA Ek-6 / substance_db'den "
                    "tüm SCL bantlarını döndürür. "
                    "Dönen 'bands' listesindeki her bant {h_class, c_min, c_max} içerir. "
                    "c_min <= konsantrasyon < c_max olan bant geçerlidir; c_max=None üst sınır yok demektir. "
                    "found=False ise bu bileşen için kayıtlı SCL yok — varsayım yapma."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "cas_no": {"type": "string", "description": "CAS numarası (örn: '7664-93-9')"},
                        "h_code": {"type": "string", "description": "H kodu (örn: 'H314')"},
                    },
                    "required": ["cas_no", "h_code"],
                },
            },
            {
                "name": "verify_text_in_sds",
                "description": (
                    "SDS verisinde bir ifadenin geçip geçmediğini kontrol eder. "
                    "Bir alanın 'eksik' veya 'mevcut' olduğunu iddia etmeden önce bu araçla doğrula. "
                    "Türkçe karakter farklılıklarını tolere eder."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "phrase": {"type": "string", "description": "Aranacak ifade veya kelime"},
                    },
                    "required": ["phrase"],
                },
            },
            {
                "name": "search_regulation",
                "description": (
                    "Mevzuat kural bloklarında anahtar kelime araması yapar. "
                    "Bir hükmün gerçekten mevzuatta var olup olmadığını doğrulamak için kullan. "
                    "B kaynağında bulamazsan bulgu yazma."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Arama sorgusu (örn: 'H318 dominance H314')"},
                        "top_k": {"type": "integer", "description": "Kaç sonuç dönsün (varsayılan 4)", "default": 4},
                    },
                    "required": ["query"],
                },
            },
        ]

        # ── 6. Tool-use döngüsü ────────────────────────────────────────────────
        from app.services.substance_lookup import get_substance_scl as _get_scl
        from app.services.regulation_search import (
            verify_text_in_sds as _verify_text,
            search_regulation   as _search_reg,
        )

        def _dispatch_tool(name: str, inputs: dict) -> str:
            try:
                if name == "get_substance_scl":
                    result = _get_scl(inputs["cas_no"], inputs["h_code"])
                elif name == "verify_text_in_sds":
                    result = _verify_text(inputs["phrase"], sds_text)
                elif name == "search_regulation":
                    result = _search_reg(inputs["query"], inputs.get("top_k", 4))
                else:
                    result = {"error": f"Bilinmeyen araç: {name}"}
            except Exception as exc:
                result = {"error": str(exc)}
            return _json.dumps(result, ensure_ascii=False)

        client = _anthropic.Anthropic(api_key=api_key)
        system_prompt = _SYSTEM_PROMPT + _load_extra_rules()

        user_parts: list[dict] = []
        user_parts.extend(kb_blocks)
        user_parts.append({"type": "text", "text": sds_text})
        user_parts.append({"type": "text", "text": issues_text})
        user_parts.append({
            "type": "text",
            "text": (
                "Yukarıdaki SDS verisini (A — JSON formatı) mevzuat paragraflarıyla (B) karşılaştırarak "
                "bağımsız denetim raporu yaz. Otomatik bulgular (C) ek bağlam olarak kullan.\n"
                "Bir bulgu yazmadan önce:\n"
                "  • JSON'da olmayan bir şeyi iddia ediyorsan → verify_text_in_sds ile doğrula\n"
                "  • SCL sınırı ile ilgili bir bulgu varsa → get_substance_scl ile sorgula\n"
                "  • Mevzuat hükmünden emin değilsen → search_regulation ile kontrol et"
            ),
        })

        messages: list[dict] = [{"role": "user", "content": user_parts}]

        total_input  = 0
        total_output = 0
        report       = ""
        MAX_ROUNDS   = 4

        for _round in range(MAX_ROUNDS):
            resp = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=4096,
                system=system_prompt,
                tools=_tools,
                messages=messages,
            )
            total_input  += resp.usage.input_tokens
            total_output += resp.usage.output_tokens

            if resp.stop_reason in ("end_turn", "max_tokens"):
                report = "".join(
                    b.text for b in resp.content if getattr(b, "type", None) == "text"
                )
                break

            if resp.stop_reason == "tool_use":
                messages.append({"role": "assistant", "content": resp.content})
                tool_results = []
                for block in resp.content:
                    if getattr(block, "type", None) != "tool_use":
                        continue
                    tool_output = _dispatch_tool(block.name, block.input)
                    tool_results.append({
                        "type":        "tool_result",
                        "tool_use_id": block.id,
                        "content":     tool_output,
                    })
                messages.append({"role": "user", "content": tool_results})
                continue

            report = "".join(
                b.text for b in resp.content if getattr(b, "type", None) == "text"
            )
            break

        # Döngü bitti ama rapor hâlâ boşsa → araçsız final çağrı
        if not report.strip():
            messages.append({
                "role": "user",
                "content": "Araç çağrıları tamamlandı. Şimdi lütfen denetim raporunu yaz. "
                           "Hem hataları hem de uyumlu bölümleri (## Uyumlu Bölümler başlığıyla) mutlaka ekle.",
            })
            final = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=4096,
                system=system_prompt,
                messages=messages,
            )
            total_input  += final.usage.input_tokens
            total_output += final.usage.output_tokens
            report = "".join(
                b.text for b in final.content if getattr(b, "type", None) == "text"
            )

        return {
            "issues":        issues,
            "summary":       summary,
            "report":        report,
            "docs_used":     len(kb_blocks),
            "input_tokens":  total_input,
            "output_tokens": total_output,
            "tool_rounds":   _round + 1,
            "sds_text":      sds_text,
        }

    except Exception as _exc:
        _detail = f"{type(_exc).__name__}: {_exc}\n\n{_tb.format_exc()}"
        raise HTTPException(status_code=500, detail=_detail)


@router.post("/api/v1/sds/chat")
async def sds_chat(data: dict = Body(...)):
    """
    Denetim sonrası soru-cevap.
    data: { sds_text, report, history: [{role, content}], question }
    """
    try:
        import anthropic as _anthropic
    except ImportError:
        raise HTTPException(status_code=500, detail="anthropic paketi kurulu değil")

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY tanımlı değil")

    sds_text = data.get("sds_text", "")
    report   = data.get("report", "")
    history  = data.get("history", [])   # [{role:"user"|"assistant", content:"..."}]
    question = (data.get("question") or "").strip()

    if not question:
        raise HTTPException(status_code=400, detail="Soru boş olamaz")

    system = (
        "Sen KKDİK ve SEA yönetmelikleri uzmanı bir GBF/SDS denetçisisin. "
        "Sana denetlenen SDS'in tam metni ve denetim raporu verildi. "
        "Kullanıcının sorularını bu bağlam üzerinden Türkçe olarak yanıtla. "
        "Her yanıtta ilgili mevzuat maddesini ve mümkünse resmi URL bağlantısını ver.\n\n"
        f"=== SDS METNİ ===\n{sds_text[:6000]}\n\n"
        f"=== DENETİM RAPORU ===\n{report[:3000]}"
    )

    # Konuşma geçmişi + yeni soru
    messages = []
    for h in history[-10:]:   # son 10 tur
        role = h.get("role")
        if role in ("user", "assistant"):
            messages.append({"role": role, "content": h.get("content", "")})
    messages.append({"role": "user", "content": question})

    client = _anthropic.Anthropic(api_key=api_key)
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=system,
        messages=messages,
    )

    answer = "".join(
        b.text for b in resp.content if getattr(b, "type", None) == "text"
    )
    return {
        "answer":        answer,
        "input_tokens":  resp.usage.input_tokens,
        "output_tokens": resp.usage.output_tokens,
    }


_DOGRULAMA_PATH = pathlib.Path(__file__).parents[2] / "sds-knowledge" / "DOGRULAMA_NOTLARI.md"
_RULES_PATH     = pathlib.Path(__file__).parents[2] / "sds-knowledge" / "review_rules.md"


def _load_extra_rules() -> str:
    """review_rules.md dosyasındaki kullanıcı onaylı kuralları yükler."""
    try:
        text = _RULES_PATH.read_text(encoding="utf-8").strip()
        # Sadece kural satırlarını al (- ile başlayanlar)
        rules = [l for l in text.splitlines() if l.strip().startswith("-")]
        if rules:
            return "\n\nGeçmişte tespit edilen denetim düzeltmeleri (bunlara dikkat et):\n" + "\n".join(rules)
    except FileNotFoundError:
        pass
    return ""

_DRAFT_SYSTEM = """Sen GBF/SDS denetim sisteminin kalite güvence modülüsün.
Sana bir denetim raporu ve kullanıcının bu rapor üzerine yaptığı sohbet verilecek.

ÖNEMLİ: Kullanıcı sohbette hangi bulguların yanlış olduğunu bizzat açıkladı.
Rapordaki tüm bulguları değil, YALNIZCA kullanıcının sohbette işaret ettiği hataları yaz.
Sohbet yoksa raporu genel olarak değerlendir.

İKİ AYRI BÖLÜM üret, başka hiçbir şey yazma:

### DOGRULAMA_NOTU
(Markdown, DOGRULAMA_NOTLARI.md dosyasına eklenecek insan referansı)
Şu format:
---
## [Ürün adı] — [Tarih]
- **Hatalı denetim çıktısı:** sistemin ne söylediği (kullanıcının işaret ettiği bulgu)
- **Neden yanlıştı:** mevzuat/hesap açıklaması
- **Doğru davranış:** olması gereken
- **Durum:** ⏳ Açık

### SISTEM_KURALI
(1-3 cümle, Türkçe, doğrudan system prompt'a eklenecek — gelecekte bu hata tekrarlanmasın)
Başına "- " koy.
"""

@router.post("/api/v1/sds/draft-error-report")
async def draft_error_report(data: dict = Body(...)):
    """
    Denetim raporundan hata taslağı + sistem kuralı üretir.
    data: { report: str, product_name: str, sds_text: str (opsiyonel) }
    """
    try:
        import anthropic as _anthropic
    except ImportError:
        raise HTTPException(status_code=500, detail="anthropic paketi kurulu değil")

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY tanımlı değil")

    report       = (data.get("report") or "").strip()
    product_name = (data.get("product_name") or "Ürün").strip()
    today        = date.today().strftime("%d.%m.%Y")

    if not report:
        raise HTTPException(status_code=400, detail="Denetim raporu boş")

    user_msg = (
        f"Ürün adı: {product_name}\nTarih: {today}\n\n"
        f"=== DENETİM RAPORU ===\n{report[:4000]}"
    )

    client = _anthropic.Anthropic(api_key=api_key)
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=800,
        system=_DRAFT_SYSTEM,
        messages=[{"role": "user", "content": user_msg}],
    )
    raw = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")

    # Bölümleri ayır
    note = rule = ""
    if "### DOGRULAMA_NOTU" in raw and "### SISTEM_KURALI" in raw:
        parts = raw.split("### SISTEM_KURALI")
        note  = parts[0].replace("### DOGRULAMA_NOTU", "").strip()
        rule  = parts[1].strip()
    else:
        note = raw.strip()

    return {"note": note, "rule": rule}


@router.post("/api/v1/sds/add-rule")
async def add_rule(data: dict = Body(...)):
    """
    Onaylanan kuralı review_rules.md dosyasına ekler.
    data: { rule: str }
    """
    rule = (data.get("rule") or "").strip()
    if not rule:
        raise HTTPException(status_code=400, detail="Kural boş olamaz")

    try:
        if not _RULES_PATH.exists():
            _RULES_PATH.write_text(
                "# Denetim Düzeltme Kuralları\n"
                "Bu dosya, tespit edilen denetim hatalarından üretilen kalıcı kurallardır.\n\n",
                encoding="utf-8"
            )
        with open(_RULES_PATH, "a", encoding="utf-8") as f:
            f.write(rule + "\n")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dosya yazma hatası: {e}")

    return {"ok": True}


@router.post("/api/v1/sds/report-error")
async def report_error(data: dict = Body(...)):
    """
    Denetim hatasını DOGRULAMA_NOTLARI.md dosyasına ekler.
    data: { content: str }  — kullanıcının onayladığı / düzenlediği markdown bloğu
    """
    content = (data.get("content") or "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="İçerik boş olamaz")

    try:
        with open(_DOGRULAMA_PATH, "a", encoding="utf-8") as f:
            f.write("\n\n" + content + "\n")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dosya yazma hatası: {e}")

    return {"ok": True}
