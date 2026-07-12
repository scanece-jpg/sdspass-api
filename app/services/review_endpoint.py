"""
SDS Denetim Endpoint — /api/v1/sds/review

Akış:
  1. validate_sds()           → V001-V027 kural sonuçları
  2. _build_sds_text()        → PDF motoruyla aynı sds_data'dan 16 bölüm düz metin
  3. build_context_blocks()   → ilgili mevzuat paragrafları
  4. Claude API               → bağımsız denetim raporu (Markdown)
"""

import os
import pathlib
from datetime import date
from fastapi import APIRouter, Body, HTTPException

router = APIRouter()

_SYSTEM_PROMPT = """Sen KKDİK ve SEA yönetmelikleri uzmanı bir GBF/SDS denetçisisin.
CLP Tüzüğü (EC 1272/2008), KKDİK, SEA, ADR ve ilgili ECHA kılavuzlarını tam olarak biliyorsun.

Sana üç kaynak verilecek:
  A) Denetlenecek SDS'in 16 bölümü (tam metin)
  B) İlgili mevzuat paragrafları (SEA, KKDİK, CLP, ADR) — ek bağlam olarak kullan
  C) Otomatik kural kontrolü sonuçları (V001-V027 kodlu bulgular)

Görevin:
1. SDS metnini (A kaynağı) baştan sona oku.
2. Her bölümü KKDİK Ek-2 ve CLP Tüzüğü gerekliliklerine göre bağımsız olarak denetle.
3. Tespit ettiğin her sorunu şu şekilde raporla:
   - Hangi bölüm (B1–B16)
   - Ne eksik veya hatalı
   - Hangi mevzuat maddesine aykırı — madde/ek/tablo numarasıyla birlikte
   - Mevzuat kaynağına doğrudan bağlantı (aşağıdaki URL tablosundan)
   - Somut düzeltme adımı
4. C kaynağındaki otomatik bulgular varsa onları da açıkla ve yorumla.
5. Bir bölümde sorun görmüyorsan onu raporlama.

Yanıtını şu formatta ver:
## Hatalar (Düzeltilmesi Zorunlu)
## Uyarılar (Kontrol Edilmeli)
## Bilgi Notları
## Genel Değerlendirme

Her bulgu için dayanak şu formatta olsun:
> 📋 **[Mevzuat Adı — Madde/Ek No]** — [kısa açıklama]
> 🔗 [bağlantı metni](URL)

Mevzuat URL tablosu (bulguya göre uygun olanı seç):
- KKDİK Ana Metin    : https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=21737&MevzuatTur=7&MevzuatTertip=5
- KKDİK Ek-2 (GBF)  : https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=21737&MevzuatTur=7&MevzuatTertip=5
- SEA Yönetmeliği   : https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=20764&MevzuatTur=7&MevzuatTertip=5
- CLP Tüzüğü (EU)   : https://eur-lex.europa.eu/legal-content/TR/TXT/?uri=CELEX:02008R1272-20231101
- ECHA CLP Kılavuzu : https://echa.europa.eu/tr/guidance-documents/guidance-on-clp
- ADR 2023          : https://unece.org/transport/dangerous-goods/adr-2023

Yanıt dili: Türkçe. Teknik terimler için parantez içinde İngilizce karşılık ekle."""


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
    adr_line = (
        f"UN {road.get('un','-')} | Sınıf {road.get('class','-')} | "
        f"PG {road.get('pg','-')} | {road.get('shipping_name') or road.get('label','-')}"
        if road.get("un") else "Tehlikeli madde değil / belirsiz"
    )

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
    comp_lines = []
    for c in (components or sds_data.get("components", [])):
        name  = c.get("name_tr") or c.get("name") or c.get("cas_no", "?")
        conc  = c.get("conc") or c.get("concentration", "?")
        cas   = c.get("cas_no") or c.get("cas", "")
        reach = c.get("reach_no", "")
        h_list= ", ".join(
            h.get("h_code","") for h in (c.get("hazards") or []) if h.get("h_code")
        )
        line = f"  • {name} (CAS: {cas}) — %{conc}"
        if reach: line += f" | REACH: {reach}"
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
        f"B2.1 Etiket H kodları: {', '.join(clp.get('h_codes', h_codes)) or 'yok'}",
        f"B2.1 Tüm H kodları   : {', '.join(clp.get('all_h_codes', h_codes)) or 'yok'}",
        f"B2.1 EUH kodları     : {', '.join(euh_codes) or 'yok'}",
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
        f"H kodlarına göre: {', '.join(h_codes)}",
        "",
        f"BÖLÜM 12 — Ekolojik Bilgi",
        f"Ekolojik H kodları: {eco_line}",
        f"PBT/vPvB          : {pbt_line}",
        "",
        f"BÖLÜM 13 — Bertaraf Etme",
        "Yerel yönetmeliklere uygun bertaraf.",
        "",
        f"BÖLÜM 14 — Taşımacılık Bilgisi",
        f"ADR (Karayolu): {adr_line}",
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
    try:
        import anthropic as _anthropic
    except ImportError:
        raise HTTPException(status_code=500, detail="anthropic paketi kurulu değil")

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY tanımlı değil")

    h_codes    = list(data.get("h_codes", []))
    phys_props = data.get("phys_props", {})
    components = data.get("components", [])

    # PDF endpoint'ten gelen tam sds_data var mı? (öncelikli)
    # Yoksa eski review payload'undan basit sds_data kullan
    full_sds_data = data.get("full_sds_data") or None
    sds_data_simple = data.get("sds_data", {})

    # ── Motor düzeltmeleri ────────────────────────────────────────────────────
    if full_sds_data:
        # PDF motorundan gelen veri — direkt kullan, sadece piktogramı güncelle
        sds_for_validator = dict(full_sds_data)
        clp_val = dict(sds_for_validator.get("clp", {}))
        try:
            from app.services.ghs_pictogram import get_ghs_codes
            clp_val["pictograms"] = get_ghs_codes(h_codes)
        except Exception:
            pass
        sds_for_validator["clp"] = clp_val
    else:
        # Eski yol: basit sds_data_simple kullan
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

    # ── 1. Kural kontrolü (V001-V027) ────────────────────────────────────────
    from app.services.sds_validator import validate_sds
    issues = validate_sds(sds_for_validator, h_codes, phys_props, components)
    issues = [i for i in issues if i.get("code") not in ("V013", "V015")]

    summary = {
        "error":   sum(1 for i in issues if i["level"] == "error"),
        "warning": sum(1 for i in issues if i["level"] == "warning"),
        "info":    sum(1 for i in issues if i["level"] == "info"),
    }

    # ── 2. SDS tam metin ─────────────────────────────────────────────────────
    sds_text = _build_sds_text(
        sds_data   = full_sds_data if full_sds_data else sds_for_validator,
        h_codes    = h_codes,
        phys_props = phys_props,
        components = components,
    )

    # ── 3. Mevzuat bağlamı ───────────────────────────────────────────────────
    from app.services.knowledge_service import build_context_blocks
    kb_blocks = build_context_blocks("sds gbf bölüm " + " ".join(h_codes[:8]))

    # ── 4. Kural sonuçları metni ─────────────────────────────────────────────
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

    # ── 5. Claude çağrısı ────────────────────────────────────────────────────
    user_parts: list[dict] = []
    user_parts.extend(kb_blocks)
    user_parts.append({"type": "text", "text": sds_text})
    user_parts.append({"type": "text", "text": issues_text})
    user_parts.append({
        "type": "text",
        "text": "Yukarıdaki SDS metnini (A) mevzuat paragraflarıyla (B) karşılaştırarak "
                "bağımsız denetim raporu yaz. Otomatik bulgular (C) ek bağlam olarak kullan.",
    })

    client = _anthropic.Anthropic(api_key=api_key)
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_parts}],
    )

    report = "".join(
        b.text for b in resp.content if getattr(b, "type", None) == "text"
    )

    return {
        "issues":        issues,
        "summary":       summary,
        "report":        report,
        "docs_used":     len(kb_blocks),
        "input_tokens":  resp.usage.input_tokens,
        "output_tokens": resp.usage.output_tokens,
        "sds_text":      sds_text,   # chat için sakla
    }


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
