"""
SDS Asistan Endpoint — /api/v1/sds/assistant

Faz tabanlı sohbet mimarisi:
  COLLECTION  — kullanıcıdan veri topla (PDF parse + klavye girişi)
  CALCULATION — mevcut hesaplama motorunu çağır (Claude yok, deterministik)
  REVIEW      — hesap sonuçlarını kullanıcıya göster, onay al
  AUDIT       — mevcut denetim motorunu çağır (Claude yok, arka planda)
  QA          — soru-cevap (kaynaksız iddia yok)

Faz geçişi deterministik: Claude'un kararına değil, somut sinyallere bağlı.
  COLLECTION  → CALCULATION : submit_for_calculation aracı çağrıldığında
  CALCULATION → REVIEW      : hesaplama başarılı döndüğünde (otomatik)
  REVIEW      → AUDIT       : kullanıcı onayladığında
  AUDIT       → QA          : denetim raporu üretildiğinde (otomatik)

Chat = Form ekranı:
  Ekran 1 — Üretici/tedarikçi bilgileri
  Ekran 2 — Bileşenler (CAS → lookup → H kodları/ATE/M faktörü göster → düzenle)
  Ekran 3 — Fiziksel & kimyasal özellikler (zorunlu: görünüm, renk, koku)
  Ekran 4 — Özet & onay → hesaplama
"""

import os
import json as _json
import base64
import io
from fastapi import APIRouter, Body, HTTPException

router = APIRouter()

# ─────────────────────────────────────────────────────────────────────────────
# Faz sabitleri
# ─────────────────────────────────────────────────────────────────────────────
PHASE_COLLECTION  = "collection"
PHASE_CALCULATION = "calculation"
PHASE_REVIEW      = "review"
PHASE_AUDIT       = "audit"
PHASE_QA          = "qa"

# ─────────────────────────────────────────────────────────────────────────────
# Faz 1 — Veri Toplama System Prompt
# ─────────────────────────────────────────────────────────────────────────────
_COLLECTION_SYSTEM = """Sen SDSPass kimyasal güvenlik bilgi formu sisteminin veri toplama asistanısın.
Görevin: formu 4 ekran olarak chat'e taşımak. Kullanıcı formu görmez — sadece seninle konuşur.
Her ekranı sırayla tamamla, formun uyarılarını mesaj olarak ilet, lookup sonuçlarını göster.

═══════════════════════════════════════
EKRAN 1 — ÜRETİCİ / TEDARİKÇİ BİLGİLERİ
═══════════════════════════════════════
Zorunlu alanlar — bunlar olmadan geçme:
  • Ürün adı
  • Fiziksel form: sıvı / katı / toz / gaz / aerosol
  • Kullanım amacı: endüstriyel / profesyonel / tüketici
  • Firma adı
  • Adres (cadde, ilçe, il, posta kodu)
  • Telefon
  • Acil durum telefonu

Opsiyonel:
  • E-posta, iletişim kişisi, web sitesi

Tüm bu alanları tek mesajda sor. Zorunlu alan boş kalırsa uyar ve tamamlatmadan geçme:
  ⚠ "Firma adı zorunludur, lütfen girin."
  ⚠ "Acil durum telefonu KKDİK Ek-2 Bölüm 1 gereği zorunludur."

═══════════════════════════════════════
EKRAN 2 — BİLEŞENLER
═══════════════════════════════════════
Her bileşen için şu sırayı izle:

1. CAS numarası sor (format: rakamlar-rakamlar-rakam, örn: 67-64-1)
2. lookup_substance ile veritabanında ara
3. Bulununca tool sonucundaki `SHOW_TO_USER` alanını HARF HARF AYNEN kopyala, değiştirme:
   ─────────────────────────────
   [results[0].SHOW_TO_USER tam metni]
   ─────────────────────────────
   "Bu madde mi? Değiştirmek istediğiniz var mı?"

   YASAK: H kodları "yok" değilse (yani liste doluysa) asla "bulunamadı / kayıtlı değil / mevcut değil" yazma.
   YASAK: ATE boş olsa bile H kodlarını gizleme veya "eksik kayıt" yorumu yapma.
   YASAK: kendi bilginden ek yorum, kaynak açıklaması veya öneri ekleme.
4. Kullanıcı düzenleme yapabilir: "H335'i kaldır" / "ATE oral 500 yap" / "M faktörü 10 yap"
   → Değişiklikleri kabul et, güncellenmiş listeyi göster
5. Konsantrasyon sor: tek değer veya min-maks aralığı (örn: %30 veya %20-40)
6. "Başka bileşen var mı?" — varsa 1'den tekrarla

Uyarılar (bunları mutlaka ilet):
  ⚠ Konsantrasyon girilmezse: "Konsantrasyon zorunludur."
  ⚠ Toplam %100'ü geçerse: "Toplam konsantrasyon %[X], kontrol edin."
  ⚠ Tüm bileşenler tamamlanıp "başka bileşen yok" denince toplam <100 ise: "Toplam konsantrasyon %[X] — 100'e tamamlamak ister misiniz?"
  ⚠ Madde DB'de bulunamazsa: "Veritabanımızda bulunamadı. Siz onaylarsanız H kodu olmadan eklerim."

KESINLIKLE YAZMA:
  ✗ "forma bu şekilde görünecek"
  ✗ "formda şöyle görünecek"
  ✗ "sisteme şu şekilde kaydedilecek"
  ✗ Formla ilgili herhangi bir meta-yorum — sen sadece kullanıcıyla konuşursun, arka planda ne olduğunu açıklamazsın.

Lookup kuralları:
  • Kullanıcı CAS verirse direkt CAS ile ara
  • İsim verirse isimle ara; bulunamazsa o maddenin CAS'ını biliyorsan CAS ile tekrar ara
  • CAS'taki "-AQ", "-GAS" eklerini temizle (7647-01-0-AQ → 7647-01-0)
  • Sonuçları kullanıcıya göster, "Bu madde mi?" diye onaylat

═══════════════════════════════════════
EKRAN 3 — FİZİKSEL & KİMYASAL ÖZELLİKLER
═══════════════════════════════════════
Bileşenler tamamlanınca bu ekrana geç.

ZORUNLU (KKDİK Ek-2 Bölüm 9 — bunlar olmadan SDS geçersiz):
  • Görünüm (sıvı / toz / katı / jel / pasta vb.)
  • Renk (renksiz / sarı / beyaz vb.)
  • Koku (keskin / karakteristik / kokusuz vb.)

Bunları önce sor. Boş geçilirse uyar:
  ⚠ "Görünüm zorunludur (KKDİK Ek-2 Bölüm 9)."

Ardından diğer özellikleri grup halinde sor:
  • Parlama noktası (°C) — sıvı/aerosol için öncelikli
  • pH
  • Yoğunluk (g/mL)
  • Kaynama noktası (°C)
  • Buhar basıncı (hPa)
  • Viskozite (mPa·s)
  • Erime noktası (°C)
  • Çözünürlük (mg/L)
  • Koku eşiği (ppm)

Kullanıcı değer bilmiyorsa: "Bu değerleri ürün test raporunuzdan veya tedarikçi SDS'inden alabilirsiniz; bilmiyorsanız boş bırakabilirsiniz."
Parlama noktası uyuşmazlığı gibi uyarıları motordan gelince ilet.

═══════════════════════════════════════
EKRAN 4 — ÖZET & ONAY
═══════════════════════════════════════
Tüm veriler toplandıktan sonra özet göster:

📋 Özet — onaylamadan önce kontrol edin:
─────────────────────────────
🏭 Üretici: [firma] | [tel] | Acil: [acil tel]
📍 Adres: [adres]
🧴 Ürün: [ad] | [form] | [kullanım]
🧪 Bileşenler:
  • [CAS] [ad] — %[konsentrasyon] | H: [kodlar]
🔬 Görünüm: [görünüm] · Renk: [renk] · Koku: [koku]
⚗️ [Fiziksel özellikler varsa]
─────────────────────────────
"Değiştirmek istediğiniz var mı? Yoksa hesaplamayı başlatalım mı?"

Onaydan sonra submit_for_calculation çağır — sohbet boyunca toplanan TÜM verileri ekle:
  • product_name, product_meta (form, usage, supplier)
  • components: her bileşen için cas, name, name_tr, conc_min, conc_max,
    hazards (lookup'tan gelen + kullanıcının düzenlediği H kodları),
    ate (oral/dermal/inhalation), m_factors (acute/chronic)
  • phys_props: appearance, color, odor + tüm sayısal değerler

═══════════════════════════════════════
KESİNLİKLE YASAK
═══════════════════════════════════════
- Zorunlu alanı boş geçmek
- H kodu veya tehlike sınıfı tahmin etmek (sadece lookup sonucunu kullan)
- CAS doğrulamadan bileşeni kabul etmek
- Aynı soruyu iki kez sormak
- Fiziksel özellik değeri önermek (ölçüm verisidir)
- "-AQ", "-GAS" eklerini kullanıcıya göstermek

Yanıt dili: Türkçe. Kısa ve net mesajlar."""

# ─────────────────────────────────────────────────────────────────────────────
# Faz 4 — Soru-Cevap System Prompt
# ─────────────────────────────────────────────────────────────────────────────
_QA_SYSTEM_BASE = """Sen KKDİK ve SEA yönetmelikleri uzmanı bir GBF/SDS denetçisisin.
Sana hesaplama sonuçları, üretilen SDS metni ve denetim raporu verildi.
Kullanıcının sorularını bu bağlam üzerinden yanıtla.

## Temel Kurallar

- Belge içeriği hakkında HER iddiadan önce `verify_text_in_sds` çağır.
- Mevzuat hükmünden emin değilsen `search_regulation` çağır.
- Araç boş veya found=false dönerse o konuda yorum yapma: "Bu bilgi elimdeki kaynakta yer almıyor."
- Her cevapta ilgili mevzuat maddesini ve varsa URL'sini belirt.
- Kaynaksız teknik iddia kesinlikle yasak.

## Mevzuat URL Tablosu
- KKDİK Ek-2: https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=21737&MevzuatTur=7&MevzuatTertip=5
- SEA: https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=20764&MevzuatTur=7&MevzuatTertip=5
- CLP: https://eur-lex.europa.eu/legal-content/TR/TXT/?uri=CELEX:02008R1272-20231101
- ADR 2023: https://unece.org/transport/dangerous-goods/adr-2023

Yanıt dili: Türkçe."""

# ─────────────────────────────────────────────────────────────────────────────
# Araç tanımları — faz bazlı
# ─────────────────────────────────────────────────────────────────────────────
_COLLECTION_TOOLS = [
    {
        "name": "parse_supplier_pdf",
        "description": (
            "Yüklenen tedarikçi SDS PDF'inden bileşen bilgilerini çıkarır. "
            "Her alan için 0.0-1.0 arası güven skoru döner. "
            "0.7 altındaki alanları kullanıcıya onaylatmadan kullanma."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "file_index": {
                    "type": "integer",
                    "description": "Yüklenen PDF'lerin 0 tabanlı sıra numarası",
                },
            },
            "required": ["file_index"],
        },
    },
    {
        "name": "lookup_substance",
        "description": (
            "İsim veya CAS numarasıyla veri tabanında madde arar. "
            "Kullanıcı madde adı verdiğinde (örn. 'HCl', 'aseton', 'etanol') çağır; "
            "CAS numarası, Türkçe/İngilizce ad, H kodları ve tehlike sınıfı döner. "
            "Sonucu kullanıcıya göster ve 'Bu madde mi?' diye onaylat."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Madde adı veya CAS numarası (örn: 'HCl', '67-64-1', 'aseton')",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "validate_input",
        "description": (
            "Toplanan bileşen verilerini doğrular: CAS format, yüzde toplamı (≤100), "
            "zorunlu alan kontrolü. Hata listesi döner, boşsa geçerlidir."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "components": {
                    "type": "array",
                    "description": "Doğrulanacak bileşen listesi",
                    "items": {
                        "type": "object",
                        "properties": {
                            "cas":      {"type": "string"},
                            "name":     {"type": "string"},
                            "conc_min": {"type": "number"},
                            "conc_max": {"type": "number"},
                        },
                    },
                },
            },
            "required": ["components"],
        },
    },
    {
        "name": "submit_for_calculation",
        "description": (
            "Kullanıcı veri özetini onayladıktan sonra hesaplama fazına geçişi tetikler. "
            "Kullanıcının açık onayı olmadan çağırma. "
            "ÖNEMLI: Sohbet boyunca toplanan TÜM verileri eksiksiz doldur — "
            "phys_props, product_meta.supplier, product_meta.form ve product_meta.usage dahil."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "product_name": {"type": "string", "description": "Ürün ticari adı"},
                "components": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "cas":      {"type": "string"},
                            "name":     {"type": "string"},
                            "name_tr":  {"type": "string"},
                            "conc_min": {"type": "number"},
                            "conc_max": {"type": "number"},
                            "hazards":  {
                                "type": "array",
                                "description": "lookup + kullanıcı düzenlemesinden gelen H kodları (örn: ['H314','H335'])",
                                "items": {"type": "string"},
                            },
                            "ate": {
                                "type": "object",
                                "description": "ATE değerleri — lookup'tan veya kullanıcı düzenlemesinden",
                                "properties": {
                                    "oral":        {"type": "number", "description": "mg/kg"},
                                    "dermal":      {"type": "number", "description": "mg/kg"},
                                    "inhalation":  {"type": "number", "description": "mg/L/4h"},
                                },
                            },
                            "m_factors": {
                                "type": "object",
                                "description": "M faktörleri — lookup'tan veya kullanıcı düzenlemesinden",
                                "properties": {
                                    "acute":   {"type": "number"},
                                    "chronic": {"type": "number"},
                                },
                            },
                        },
                    },
                },
                "phys_props": {
                    "type": "object",
                    "description": "Fiziksel & kimyasal özellikler — bilinmeyenler göndermeyebilirsin",
                    "properties": {
                        "appearance":     {"type": "string", "description": "Görünüm — ZORUNLU (sıvı/katı/toz vb.)"},
                        "color":          {"type": "string", "description": "Renk — ZORUNLU (renksiz/sarı vb.)"},
                        "odor":           {"type": "string", "description": "Koku — ZORUNLU (keskin/kokusuz vb.)"},
                        "flash_point":    {"type": "number", "description": "Parlama noktası °C"},
                        "ph":             {"type": "number", "description": "pH değeri"},
                        "density":        {"type": "number", "description": "Yoğunluk g/mL"},
                        "boiling_point":  {"type": "number", "description": "Kaynama noktası °C"},
                        "melting_point":  {"type": "number", "description": "Erime noktası °C"},
                        "vapor_pressure": {"type": "number", "description": "Buhar basıncı hPa"},
                        "viscosity":      {"type": "number", "description": "Viskozite mPa·s"},
                        "solubility":     {"type": "number", "description": "Çözünürlük mg/L"},
                        "odour_threshold":{"type": "number", "description": "Koku eşiği ppm"},
                        "rel_density":    {"type": "number", "description": "Bağıl yoğunluk"},
                        "log_kow":        {"type": "number", "description": "log Kow"},
                        "auto_ignition":  {"type": "number", "description": "Kendiliğinden tutuşma °C"},
                    },
                },
                "product_meta": {
                    "type": "object",
                    "description": "Ürün meta verisi",
                    "properties": {
                        "form":  {"type": "string", "enum": ["liquid","solid","powder","gas","aerosol"]},
                        "usage": {"type": "string", "enum": ["industrial","professional","consumer"]},
                        "supplier": {
                            "type": "object",
                            "properties": {
                                "name":    {"type": "string"},
                                "address": {"type": "string"},
                                "phone":   {"type": "string"},
                                "email":   {"type": "string"},
                                "contact": {"type": "string"},
                            },
                        },
                    },
                },
            },
            "required": ["product_name", "components"],
        },
    },
]

_QA_TOOLS = [
    {
        "name": "verify_text_in_sds",
        "description": "SDS metninde bir ifadenin geçip geçmediğini kontrol eder.",
        "input_schema": {
            "type": "object",
            "properties": {
                "phrase": {"type": "string", "description": "Aranacak ifade"},
            },
            "required": ["phrase"],
        },
    },
    {
        "name": "search_regulation",
        "description": "Mevzuat kural bloklarında anahtar kelime araması yapar.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "top_k": {"type": "integer", "default": 4},
            },
            "required": ["query"],
        },
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# Deterministik araç dispatch'leri
# ─────────────────────────────────────────────────────────────────────────────

def _dispatch_collection_tool(name: str, inputs: dict, session: dict) -> tuple[str, dict]:
    """
    Toplama fazı araçlarını çalıştırır.
    (tool_result_json, updated_session) döner.
    submit_for_calculation çağrıldığında session["_submit"] set edilir.
    """
    if name == "parse_supplier_pdf":
        result = _run_parse_supplier_pdf(inputs, session)
    elif name == "lookup_substance":
        raw = _run_lookup_substance(inputs)
        if raw.get("found") and raw.get("results"):
            hits = raw["results"]
            # Structured data session'a sakla — submit'te kullanılacak
            session = dict(session)
            session["_last_lookups"] = session.get("_last_lookups", []) + hits

            # AI'a sadece düz metin döndür — JSON yorumlaması yok
            lines = []
            for r in hits:
                lines.append(r.get("SHOW_TO_USER", ""))
            plain = "\n\n---\n\n".join(lines)
            return plain, session
        else:
            msg = raw.get("message", f"'{inputs.get('query')}' bulunamadı.")
            return msg, session
    elif name == "validate_input":
        result = _run_validate_input(inputs)
    elif name == "submit_for_calculation":
        # Faz geçiş sinyali — session'a işaretle, döngü yakalar
        session = dict(session)
        session["_submit"] = inputs   # product_name, components, phys_props, product_meta
        result = {"ok": True, "message": "Hesaplama başlatılıyor..."}
    else:
        result = {"error": f"Bilinmeyen araç: {name}"}

    return _json.dumps(result, ensure_ascii=False), session


def _dispatch_qa_tool(name: str, inputs: dict, sds_text: str) -> str:
    """Soru-cevap fazı araçlarını çalıştırır."""
    try:
        if name == "verify_text_in_sds":
            from app.services.regulation_search import verify_text_in_sds as _vt
            result = _vt(inputs["phrase"], sds_text)
        elif name == "search_regulation":
            from app.services.regulation_search import search_regulation as _sr
            result = _sr(inputs["query"], inputs.get("top_k", 4))
        else:
            result = {"error": f"Bilinmeyen araç: {name}"}
    except Exception as exc:
        result = {"error": str(exc)}
    return _json.dumps(result, ensure_ascii=False)


# ─────────────────────────────────────────────────────────────────────────────
# PDF parse yardımcısı (mevcut parse-supplier mantığını sarar)
# ─────────────────────────────────────────────────────────────────────────────

def _run_parse_supplier_pdf(inputs: dict, session: dict) -> dict:
    """
    session["files"] listesindeki file_index numaralı PDF'i parse eder.
    Mevcut parse-supplier mantığını (main.py) doğrudan çağırır.
    Her alana güven skoru atar.
    """
    files = session.get("files", [])
    idx   = inputs.get("file_index", 0)
    if idx >= len(files):
        return {"error": f"PDF bulunamadı: index {idx}, yüklü dosya sayısı {len(files)}"}

    try:
        pdf_b64  = files[idx]
        pdf_bytes = base64.b64decode(pdf_b64)
    except Exception as e:
        return {"error": f"PDF decode hatası: {e}"}

    try:
        import pdfplumber
        pages = []
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                t = page.extract_text(x_tolerance=2, y_tolerance=2)
                if t:
                    pages.append(t)
        sds_text = "\n\n".join(pages)[:30000]
    except Exception as e:
        return {"error": f"PDF metin çıkarma hatası: {e}"}

    # Claude ile parse — mevcut parse-supplier prompt'u kullan
    try:
        import anthropic as _anthropic
        api_key = os.getenv("ANTHROPIC_API_KEY")
        client  = _anthropic.Anthropic(api_key=api_key)

        parse_prompt = """Bu tedarikçi GBF/SDS metninden bileşen bilgilerini çıkar.
Her bileşen için şu alanları doldur:
- cas: CAS numarası (string)
- name: kimyasal adı (İngilizce veya Türkçe)
- name_tr: Türkçe adı (varsa)
- conc_min: minimum konsantrasyon (sayı, % ağırlık)
- conc_max: maksimum konsantrasyon (sayı, % ağırlık)
- ld50_oral: oral LD50 (mg/kg, Bölüm 11'den)
- ld50_dermal: dermal LD50 (mg/kg, Bölüm 11'den)
- lc50_inhal: inhalasyon LC50 (mg/L/4h, Bölüm 11'den)
- confidence: bu bileşen için genel güven skoru (0.0-1.0)
  1.0 = net değer, 0.5 = tahmini, 0.0 = belirsiz

Ayrıca ürün seviyesinde:
- product_name: ürün adı
- product_name_confidence: güven (0.0-1.0)

JSON formatında döndür: {"product_name": "...", "product_name_confidence": 0.9, "components": [...]}
Bulunamazsa boş liste ver. Yalnızca JSON döndür, başka metin ekleme."""

        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=4096,
            messages=[{
                "role": "user",
                "content": f"{parse_prompt}\n\n=== SDS METNİ ===\n{sds_text}"
            }],
        )
        raw = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")

        # JSON temizle
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        parsed = _json.loads(raw.strip())

    except Exception as e:
        return {"error": f"Claude parse hatası: {e}"}

    # CAS DB lookup — tehlike sınıfları ekle
    components = parsed.get("components", [])
    enriched   = []
    for comp in components:
        cas = comp.get("cas", "")
        if cas:
            try:
                from app.services.substance_lookup import lookup_substance
                sub = lookup_substance(cas)
                if sub:
                    comp["hazards"]   = sub.get("hazards", [])
                    comp["m_factors"] = sub.get("m_factors", {})
            except Exception:
                pass
        enriched.append(comp)

    return {
        "product_name":             parsed.get("product_name", ""),
        "product_name_confidence":  parsed.get("product_name_confidence", 0.5),
        "components":               enriched,
        "file_index":               idx,
        "pages_read":               len(pages),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Girdi doğrulama
# ─────────────────────────────────────────────────────────────────────────────

async def _run_lookup_substance_api(cas: str) -> dict | None:
    """Formun kullandığı /api/v1/sds/substance/lookup endpoint'ini çağırır (ECHA fallback dahil)."""
    try:
        from app.main import substance_lookup as _sl_endpoint
        result = await _sl_endpoint(cas)
        if hasattr(result, "body"):
            import json as _j
            result = _j.loads(result.body)
        if isinstance(result, dict) and result.get("found"):
            return result
    except Exception:
        pass
    return None


def _run_lookup_substance(inputs: dict) -> dict:
    """İsim, kısaltma veya CAS ile veri tabanında madde arar, ilk 5 sonucu döner."""
    import os as _os, json as _json2, asyncio as _asyncio
    try:
        from app.services.substance_lookup import search_substances, lookup_substance
        query = (inputs.get("query") or "").strip()
        if not query:
            return {"error": "Arama terimi boş"}

        q = query.lower()

        def _api_lookup(cas_key: str) -> dict | None:
            """Formun endpoint'ini async context içinde çağırır."""
            try:
                loop = _asyncio.get_event_loop()
                if loop.is_running():
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as pool:
                        future = pool.submit(_asyncio.run, _run_lookup_substance_api(cas_key))
                        return future.result(timeout=5)
                else:
                    return loop.run_until_complete(_run_lookup_substance_api(cas_key))
            except Exception:
                return lookup_substance(cas_key)

        # 1. Standart arama — her CAS için formun endpoint'iyle (ECHA dahil) zenginleştir
        raw_results = search_substances(query, limit=5)
        results = []
        seen_enrich = set()
        for sr in raw_results:
            cas_key = (sr.get("cas") or "").split("-AQ")[0].split("-GAS")[0].strip()
            if cas_key and cas_key not in seen_enrich:
                seen_enrich.add(cas_key)
                full = _api_lookup(cas_key)
                results.append(full if full else sr)

        # 2. Bulunamadıysa — CAS lookup dene (kullanıcı CAS girmiş olabilir)
        if not results:
            full = _api_lookup(query) or lookup_substance(query)
            if full:
                results = [full]

        # 3. Hâlâ bulunamadıysa — name_en ve synonyms dahil geniş tarama
        if not results:
            try:
                _data_dir = _os.path.join(_os.path.dirname(__file__), '..', '..', 'data')
                hits = []
                for fname in ('sea_ek6_tr.json', 'substance_db.json'):
                    fpath = _os.path.join(_data_dir, fname)
                    if not _os.path.exists(fpath):
                        continue
                    with open(fpath, encoding='utf-8') as _f:
                        db = _json2.load(_f)
                    for cas_key, entry in db.items():
                        if isinstance(entry, dict) and '_alias' not in entry:
                            all_text = ' '.join(filter(None, [
                                entry.get('name_en', ''),
                                ' '.join(entry.get('names', [])),
                                ' '.join(entry.get('synonyms', [])),
                                entry.get('formula', ''),
                            ])).lower()
                            if q in all_text:
                                sub = _api_lookup(cas_key) or lookup_substance(cas_key)
                                if sub:
                                    hits.append(sub)
                                if len(hits) >= 5:
                                    break
                    if hits:
                        break
                results = hits
            except Exception:
                pass

        if not results:
            return {
                "found": False,
                "message": f"'{query}' veri tabanında bulunamadı. CAS numarasını doğrudan girebilirsiniz.",
            }

        # CAS'a göre tekilleştir (-AQ/-GAS gibi iç ekleri temizle)
        seen_cas = set()
        hits_out = []
        for r in results:
            raw_cas = r.get("cas", "")
            cas = raw_cas.split("-AQ")[0].split("-GAS")[0].strip()
            if cas in seen_cas:
                continue
            seen_cas.add(cas)
            names = r.get("names") or []
            raw_hazards = r.get("hazards", []) or []
            # hazards list of dicts ({"h_code": "H314", "h_class": "..."}) → sadece kodları çıkar
            if raw_hazards and isinstance(raw_hazards[0], dict):
                h_codes_simple = [h["h_code"] for h in raw_hazards if h.get("h_code")]
            else:
                h_codes_simple = [h for h in raw_hazards if isinstance(h, str)]

            raw_ate = r.get("ate", {}) or {}
            ate_display = {k: v for k, v in raw_ate.items() if v} if raw_ate else {}

            raw_mf = r.get("m_factors", {}) or {}
            mf_display = {k: v for k, v in raw_mf.items() if v is not None} if raw_mf else {}

            hits_out.append({
                "cas":       cas,
                "name":      r.get("name") or (names[0] if names else ""),
                "name_tr":   r.get("name_tr", ""),
                "h_codes":   h_codes_simple,
                "hazards":   raw_hazards,   # tam nesneler — submit'te kullanılacak
                "ate":       ate_display,
                "m_factors": mf_display,
            })
            if len(hits_out) >= 5:
                break
        # Her sonuç için kullanıcıya gösterilecek hazır özet — AI bu metni AYNEN kopyalar
        for hit in hits_out:
            h_list = hit.get("h_codes", [])
            ate    = hit.get("ate", {}) or {}
            mf     = hit.get("m_factors", {}) or {}

            h_str  = ", ".join(h_list) if h_list else "yok"
            ate_parts = []
            if ate.get("oral"):        ate_parts.append(f"Oral {ate['oral']} mg/kg")
            if ate.get("dermal"):      ate_parts.append(f"Dermal {ate['dermal']} mg/kg")
            if ate.get("inhalation"):  ate_parts.append(f"İnhalasyon {ate['inhalation']} mg/L/4h")
            ate_str = " · ".join(ate_parts) if ate_parts else "yok"
            mf_parts = []
            if mf.get("acute")   is not None: mf_parts.append(f"Akut: {mf['acute']}")
            if mf.get("chronic") is not None: mf_parts.append(f"Kronik: {mf['chronic']}")
            mf_str = " · ".join(mf_parts) if mf_parts else "yok"

            hit["SHOW_TO_USER"] = (
                f"CAS: {hit['cas']}\n"
                f"Ad: {hit['name']} / {hit['name_tr']}\n"
                f"H kodları: {h_str}\n"
                f"ATE: {ate_str}\n"
                f"M faktörü: {mf_str}"
            )

        return {"found": True, "results": hits_out}
    except Exception as exc:
        return {"error": str(exc)}


def _run_validate_input(inputs: dict) -> dict:
    """
    Deterministik doğrulama:
    - CAS format kontrolü
    - Konsantrasyon toplamı ≤ 100
    - Zorunlu alan kontrolü
    """
    import re
    cas_pattern = re.compile(r"^\d{2,7}-\d{2}-\d$")
    components = inputs.get("components", [])
    errors = []

    total_max = 0.0
    for i, c in enumerate(components, 1):
        cas  = c.get("cas", "")
        name = c.get("name", "")
        cmin = c.get("conc_min")
        cmax = c.get("conc_max")

        if not cas:
            errors.append(f"Bileşen {i}: CAS numarası eksik")
        elif not cas_pattern.match(cas):
            errors.append(f"Bileşen {i} ({cas}): CAS formatı hatalı (örn: 67-64-1)")

        if not name:
            errors.append(f"Bileşen {i}: kimyasal adı eksik")

        if cmin is None and cmax is None:
            errors.append(f"Bileşen {i} ({name or cas}): konsantrasyon eksik")
        else:
            val = cmax if cmax is not None else cmin
            total_max += float(val or 0)

    if total_max > 100.1:
        errors.append(f"Konsantrasyon toplamı %{total_max:.1f} — 100'ü geçemez")

    return {"valid": len(errors) == 0, "errors": errors}


# ─────────────────────────────────────────────────────────────────────────────
# Faz 2 — Hesaplama (Claude yok, doğrudan motor)
# ─────────────────────────────────────────────────────────────────────────────

async def _run_calculation(submit_data: dict) -> dict:
    """
    1. sds_calculate ile h_codes/clp/transport/ppe/p_codes hesaplar.
    2. Sonuçları generate_pdf payload formatına dönüştürüp generate_pdf çağırır.
    3. PDF bytes + sds_data döner — formun tam yaptığı akışın aynısı.
    """
    try:
        import json as _j
        from app.main import sds_calculate, generate_pdf

        product_name = submit_data.get("product_name", "") or "Ürün"
        components   = submit_data.get("components", [])
        phys_props   = submit_data.get("phys_props", {}) or {}
        product_meta = submit_data.get("product_meta", {}) or {}
        supplier     = product_meta.get("supplier", {}) or {}
        form         = product_meta.get("form", "liquid")
        usage        = product_meta.get("usage", "industrial")

        # ── 1. Hesapla ────────────────────────────────────────────────────────
        def _norm_hazards(raw):
            """String listesini [{h_code, h_class}] formatına çevir."""
            out = []
            for h in (raw or []):
                if isinstance(h, dict):
                    out.append(h)
                elif isinstance(h, str) and h.strip():
                    out.append({"h_code": h.strip(), "h_class": ""})
            return out

        calc_comps = [
            {
                "cas":        c.get("cas", ""),
                "name":       c.get("name", ""),
                "name_tr":    c.get("name_tr", ""),
                "conc":       c.get("conc_max") or c.get("conc_min") or 0,
                "concMax":    c.get("conc_max"),
                "concMin":    c.get("conc_min"),
                "hazards":    _norm_hazards(c.get("hazards", [])),
                "m_factors":  c.get("m_factors", {}),
                "ate":        c.get("ate"),
                "ec50_algae":   c.get("ec50_algae"),
                "ec50_fish":    c.get("ec50_fish"),
                "ec50_daphnia": c.get("ec50_daphnia"),
                "ec50_noec":    c.get("ec50_noec"),
            }
            for c in components
        ]
        calc_payload = {
            "form":      form,
            "usage":     usage,
            "lang":      "TR",
            "test_data": phys_props,
            "components": calc_comps,
        }
        if phys_props.get("flash_point"):
            calc_payload["user_fp"] = phys_props["flash_point"]
        if phys_props.get("ph"):
            calc_payload["mixture_ph"] = str(phys_props["ph"])

        calc_raw = await sds_calculate(calc_payload)
        if hasattr(calc_raw, "body"):
            calc_raw = _j.loads(calc_raw.body)

        # ── 2. generate_pdf payload'ı oluştur (form formatı) ──────────────────
        # generate_pdf içindeki clp_service conc alanının sayı olmasını bekler.
        # _fmt_comp_for_sds sadece audit/review için kullanılır (sds_data içinde).
        # generate_pdf'e calc_comps gönder — _refresh_comp zaten H kodlarını tazeler.

        euh_data   = calc_raw.get("euh") or {}
        p_data     = calc_raw.get("p_codes") or {}

        pdf_payload = {
            "lang":       "TR",
            "form":       form,
            "product":    {"name": product_name, "form": form, "usage": usage},
            "supplier":   supplier,
            "components": calc_comps,
            "phys_props": phys_props,
            # Hesaplama motorlarından gelen sınıflandırma
            "h_codes":     calc_raw.get("h_codes", []),
            "all_h_codes": calc_raw.get("all_h_codes", []),
            "signal_word": calc_raw.get("signal", ""),
            "clp_passed":  calc_raw.get("clp_passed", []),
            "euh_codes":   euh_data.get("euh_codes") or calc_raw.get("euh_codes", []),
            "euh_details": euh_data.get("euh_details") or calc_raw.get("euh_details", []),
            "p_codes":     p_data,
            "transport":   calc_raw.get("transport", {}),
            "eco":         calc_raw.get("eco", {}),
            "ppe":         calc_raw.get("ppe", {}),
            "ate_mix_details": calc_raw.get("ate_details", {}),
            "revision":    {},
            "h314_neutralization_removed": False,
        }

        # ── 3. PDF üret ───────────────────────────────────────────────────────
        pdf_raw = await generate_pdf(pdf_payload)
        if hasattr(pdf_raw, "body"):
            pdf_raw = _j.loads(pdf_raw.body)

        return {
            "ok":       True,
            "pdf":      pdf_raw.get("pdf"),
            "filename": pdf_raw.get("filename"),
            "sds_data": pdf_raw.get("sds_data"),
            # Hesaplama özeti (audit fazı ve QA için)
            **{k: v for k, v in calc_raw.items() if k not in ("ok",)},
        }

    except Exception as exc:
        import traceback
        return {"ok": False, "error": f"{exc}\n{traceback.format_exc()}"}


# ─────────────────────────────────────────────────────────────────────────────
# Faz 3 — Denetim (mevcut review motoru, aynen)
# ─────────────────────────────────────────────────────────────────────────────

def _fmt_comp_for_sds(c: dict) -> dict:
    """AI'dan gelen conc_min/conc_max alanlarını generate_sds_pdf'in beklediği
    sayısal conc/concMax ve gösterim için conc_str alanlarına dönüştürür.
    concentration alanı eklenmez — pdf_sds_service conc_str'den üretir."""
    conc_min = c.get("conc_min") or c.get("concMin") or 0
    conc_max = c.get("conc_max") or c.get("concMax") or conc_min
    conc_val = float(conc_max or conc_min or c.get("conc") or 0)
    if conc_min and conc_max and float(conc_min) != float(conc_max):
        conc_str = f"{conc_min}–{conc_max}"
    elif conc_val:
        conc_str = f"{conc_val:.4g}"
    else:
        conc_str = c.get("conc_str", "")
    return {
        **c,
        "conc":     conc_val,
        "concMax":  float(conc_max) if conc_max else conc_val,
        "concMin":  float(conc_min) if conc_min else conc_val,
        "conc_str": conc_str,
    }


async def _run_audit(calc_result: dict, submit_data: dict | None = None) -> dict:
    """
    Mevcut /api/v1/sds/review endpoint mantığını doğrudan çağırır.
    _run_calculation'ın ürettiği sds_data'yı full_sds_data olarak kullanır.
    """
    try:
        from app.services.review_endpoint import sds_review as _review_fn

        # _run_calculation artık generate_pdf'ten gelen tam sds_data'yı döndürüyor.
        # Bunu doğrudan full_sds_data olarak geç — format uyumsuzluğu yok.
        full_sds_data = calc_result.get("sds_data")

        if full_sds_data:
            payload = {
                "h_codes":      calc_result.get("h_codes", []),
                "phys_props":   (full_sds_data.get("phys_props") or
                                 calc_result.get("phys_props", {})),
                "components":   full_sds_data.get("components", []),
                "full_sds_data": full_sds_data,
            }
        else:
            # Fallback: sds_data yoksa eski yöntemle oluştur
            sd = submit_data or {}
            product_meta = sd.get("product_meta") or {}
            supplier     = product_meta.get("supplier") or {}
            product_name = sd.get("product_name") or "Ürün"
            raw_components = sd.get("components") or calc_result.get("components", [])
            components = [_fmt_comp_for_sds(c) for c in raw_components]
            product_dict = {
                "name":  product_name,
                "form":  product_meta.get("form", "liquid"),
                "usage": product_meta.get("usage", "industrial"),
            }
            payload = {
                "h_codes":    calc_result.get("h_codes", []),
                "phys_props": calc_result.get("phys_props", {}),
                "components": components,
                "full_sds_data": {
                    **calc_result,
                    "product":    product_dict,
                    "supplier":   supplier,
                    "components": components,
                    "clp":        calc_result.get("clp", {}),
                    "eco":        calc_result.get("eco", {}),
                    "transport":  calc_result.get("transport", {}),
                    "revision":   {},
                    "p_codes":    calc_result.get("p_codes", {}),
                    "euh":        calc_result.get("euh", {}),
                    "ppe":        calc_result.get("ppe", {}),
                },
            }

        result = await _review_fn(payload)
        return {"ok": True, "report": result.get("report", ""), "sds_text": result.get("sds_text", "")}

    except Exception as exc:
        import traceback
        return {"ok": False, "error": f"{exc}\n{traceback.format_exc()}", "report": "", "sds_text": ""}


# ─────────────────────────────────────────────────────────────────────────────
# Claude sohbet döngüsü — toplama ve soru-cevap fazları
# ─────────────────────────────────────────────────────────────────────────────

def _claude_turn(
    system:    str,
    messages:  list,
    tools:     list,
    session:   dict,
    sds_text:  str = "",
    phase:     str = PHASE_COLLECTION,
    max_rounds: int = 6,
) -> tuple[str, dict]:
    """
    Claude ile bir tur konuşma yapar, araçları dispatch eder.
    (reply_text, updated_session) döner.
    COLLECTION fazında submit_for_calculation çağrıldıysa
    session["_submit"] set edilmiş olur.
    """
    import anthropic as _anthropic

    api_key = os.getenv("ANTHROPIC_API_KEY")
    client  = _anthropic.Anthropic(api_key=api_key)
    reply   = ""

    for _ in range(max_rounds):
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            temperature=0,
            system=system,
            tools=tools or _anthropic.NOT_GIVEN,
            messages=messages,
        )

        if resp.stop_reason in ("end_turn", "max_tokens"):
            reply = "".join(
                b.text for b in resp.content if getattr(b, "type", None) == "text"
            )
            break

        if resp.stop_reason == "tool_use":
            messages = messages + [{"role": "assistant", "content": resp.content}]
            tool_results = []

            for block in resp.content:
                if getattr(block, "type", None) != "tool_use":
                    continue

                if phase == PHASE_COLLECTION:
                    tool_out, session = _dispatch_collection_tool(block.name, block.input, session)
                else:
                    tool_out = _dispatch_qa_tool(block.name, block.input, sds_text)

                tool_results.append({
                    "type":        "tool_result",
                    "tool_use_id": block.id,
                    "content":     tool_out,
                })

            messages = messages + [{"role": "user", "content": tool_results}]

            # Faz geçiş sinyali yakalandıysa döngüyü kes
            if phase == PHASE_COLLECTION and session.get("_submit"):
                reply = "".join(
                    b.text for b in resp.content if getattr(b, "type", None) == "text"
                ) or "Veriler alındı, hesaplama başlatılıyor..."
                break
            continue

        reply = "".join(
            b.text for b in resp.content if getattr(b, "type", None) == "text"
        )
        break

    return reply, session


# ─────────────────────────────────────────────────────────────────────────────
# Ana endpoint
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/api/v1/sds/assistant")
async def sds_assistant(data: dict = Body(...)):
    """
    Birleşik SDS asistan endpoint'i.

    İstek gövdesi:
    {
      "phase":        "collection" | "calculation" | "audit" | "qa",
      "session":      { ... },        // birikimli oturum verisi
      "messages":     [{role, content}],  // konuşma geçmişi
      "user_message": "...",          // yeni kullanıcı mesajı
      "files":        ["base64..."]   // yüklenen PDF'ler (opsiyonel)
    }

    Yanıt:
    {
      "reply":          "...",        // Claude'un yanıtı (toplama/soru-cevap)
      "phase":          "...",        // güncel ya da yeni faz
      "phase_changed":  false,
      "session":        { ... },      // güncel oturum verisi
      "calc_result":    { ... },      // yalnızca CALCULATION fazında
      "audit_report":   "...",        // yalnızca AUDIT fazında
      "sds_text":       "..."         // AUDIT tamamlanınca
    }
    """
    try:
        import anthropic as _anthropic
    except ImportError:
        raise HTTPException(status_code=500, detail="anthropic paketi kurulu değil")

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY tanımlı değil")

    phase        = data.get("phase", PHASE_COLLECTION)
    session      = dict(data.get("session", {}))
    messages     = list(data.get("messages", []))
    user_message = (data.get("user_message") or "").strip()
    files        = data.get("files", [])

    # Yüklenen dosyaları session'a ekle
    if files:
        existing = session.get("files", [])
        session["files"] = existing + [f for f in files if f not in existing]

    # ── PHASE: COLLECTION ────────────────────────────────────────────────────
    if phase == PHASE_COLLECTION:
        if not user_message and not files:
            # İlk açılış — karşılama mesajı
            return {
                "reply": (
                    "Merhaba! SDSPass veri toplama asistanıyım.\n\n"
                    "Başlamak için:\n"
                    "• Tedarikçi SDS PDF'lerini yükleyebilirsiniz (birden fazla olabilir)\n"
                    "• Ya da ürün adı ve bileşen bilgilerini yazarak girebilirsiniz\n\n"
                    "Nasıl devam etmek istersiniz?"
                ),
                "phase":         PHASE_COLLECTION,
                "phase_changed": False,
                "session":       session,
            }

        # Konuşma geçmişine kullanıcı mesajını ekle
        if user_message:
            messages = messages + [{"role": "user", "content": user_message}]
        elif files and not messages:
            # Dosya var ama mesaj yok — parse için yönlendirme
            file_count = len(session.get("files", []))
            messages = messages + [{
                "role": "user",
                "content": f"{file_count} adet PDF yüklendi. Lütfen parse et.",
            }]

        reply, session = _claude_turn(
            system   = _COLLECTION_SYSTEM,
            messages = messages,
            tools    = _COLLECTION_TOOLS,
            session  = session,
            phase    = PHASE_COLLECTION,
        )

        # submit_for_calculation çağrıldı mı?
        if session.get("_submit"):
            submit_data = session.pop("_submit")
            session["submit_data"] = submit_data
            return {
                "reply":         reply,
                "phase":         PHASE_CALCULATION,
                "phase_changed": True,
                "session":       session,
            }

        messages = messages + [{"role": "assistant", "content": reply}]
        return {
            "reply":         reply,
            "phase":         PHASE_COLLECTION,
            "phase_changed": False,
            "session":       session,
            "messages":      messages,
        }

    # ── PHASE: CALCULATION (otomatik, Claude yok) ────────────────────────────
    if phase == PHASE_CALCULATION:
        submit_data = session.get("submit_data", {})
        if not submit_data:
            raise HTTPException(status_code=400, detail="submit_data session'da bulunamadı")

        calc_result = await _run_calculation(submit_data)

        if not calc_result.get("ok"):
            return {
                "reply":         f"Hesaplama hatası: {calc_result.get('error', 'bilinmeyen hata')}",
                "phase":         PHASE_COLLECTION,
                "phase_changed": True,
                "session":       session,
            }

        # PDF'i session'dan çıkar — büyük veri, her istekte gidip gelmemeli
        session["calc_result"] = {k: v for k, v in calc_result.items() if k != "pdf"}
        # PDF'i ayrıca sakla — AUDIT sonrası frontend alacak
        session["_pdf"]      = calc_result.get("pdf", "")
        session["_filename"] = calc_result.get("filename", "SDS.pdf")

        # Hesap özeti oluştur — kullanıcıya REVIEW fazında gösterilecek
        h_codes   = calc_result.get("h_codes", [])
        signal    = calc_result.get("signal", "")
        transport = calc_result.get("transport", {})
        adr_un    = transport.get("un_number", "") if transport else ""
        adr_class = transport.get("class", "") if transport else ""
        adr_pg    = transport.get("packing_group", "") if transport else ""
        adr_str   = f"UN {adr_un}, Sınıf {adr_class}, PG {adr_pg}" if adr_un else "ADR kapsamı dışı"

        review_summary = (
            f"**Hesaplama tamamlandı. Sonuçları kontrol edin:**\n\n"
            f"⚠ Sinyal kelimesi: **{signal or '—'}**\n"
            f"🏷 H kodları: {', '.join(h_codes) if h_codes else '—'}\n"
            f"🚛 Taşımacılık (ADR): {adr_str}\n\n"
            f"Bu sonuçlarla SDS oluşturulsun mu? (Evet / Hayır)"
        )

        return {
            "reply":         review_summary,
            "phase":         PHASE_REVIEW,
            "phase_changed": True,
            "session":       session,
            "calc_result":   session["calc_result"],
            "pdf":           calc_result.get("pdf", ""),
            "filename":      calc_result.get("filename", "SDS.pdf"),
        }

    # ── PHASE: REVIEW (kullanıcı onayı) ─────────────────────────────────────
    if phase == PHASE_REVIEW:
        calc_result = session.get("calc_result", {})
        if not calc_result:
            raise HTTPException(status_code=400, detail="calc_result session'da bulunamadı")

        msg_lower = (user_message or "").strip().lower()
        # Kullanıcı onayladıysa audit'e geç
        if any(w in msg_lower for w in ("evet", "oluştur", "devam", "tamam", "başlat", "sds", "yes", "ok")):
            return {
                "reply":         "",
                "phase":         PHASE_AUDIT,
                "phase_changed": True,
                "session":       session,
                "calc_result":   calc_result,
            }
        # Kullanıcı değişiklik istedi — collection'a geri dön
        return {
            "reply":         "Hangi bilgiyi değiştirmek istiyorsunuz?",
            "phase":         PHASE_COLLECTION,
            "phase_changed": True,
            "session":       session,
        }

    # ── PHASE: AUDIT (otomatik, mevcut review motoru) ────────────────────────
    if phase == PHASE_AUDIT:
        calc_result = session.get("calc_result", {})
        if not calc_result:
            raise HTTPException(status_code=400, detail="calc_result session'da bulunamadı")

        submit_data  = session.get("_submit", {})
        audit_result = await _run_audit(calc_result, submit_data=submit_data)
        session["audit_report"] = audit_result.get("report", "")
        session["sds_text"]     = audit_result.get("sds_text", "")

        return {
            "reply":         "",
            "phase":         PHASE_QA,
            "phase_changed": True,
            "session":       session,
            "audit_report":  audit_result.get("report", ""),
            "sds_text":      audit_result.get("sds_text", ""),
            "pdf":           session.get("_pdf", ""),
            "filename":      session.get("_filename", "SDS.pdf"),
        }

    # ── PHASE: QA ────────────────────────────────────────────────────────────
    if phase == PHASE_QA:
        if not user_message:
            raise HTTPException(status_code=400, detail="user_message boş olamaz")

        sds_text     = session.get("sds_text", "")
        audit_report = session.get("audit_report", "")
        calc_result  = session.get("calc_result", {})

        # System prompt'a bağlam enjekte et
        context = (
            f"\n\n=== HESAPLAMA SONUÇLARI ===\n"
            f"H kodları: {', '.join(calc_result.get('h_codes', []))}\n"
            f"Ürün: {calc_result.get('product', {}).get('name', '')}\n\n"
            f"=== DENETİM RAPORU ===\n{audit_report[:5000]}\n\n"
            f"=== SDS METNİ ===\n{sds_text[:10000]}"
        )
        system = _QA_SYSTEM_BASE + context

        messages = messages + [{"role": "user", "content": user_message}]

        reply, _ = _claude_turn(
            system   = system,
            messages = messages,
            tools    = _QA_TOOLS,
            session  = session,
            sds_text = sds_text,
            phase    = PHASE_QA,
        )

        messages = messages + [{"role": "assistant", "content": reply}]
        return {
            "reply":         reply,
            "phase":         PHASE_QA,
            "phase_changed": False,
            "session":       session,
            "messages":      messages,
        }

    raise HTTPException(status_code=400, detail=f"Geçersiz faz: {phase}")
