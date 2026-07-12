"""
SDS Denetim Endpoint — /api/v1/sds/review

Akış:
  1. validate_sds()           → V001-V027 kural sonuçları
  2. _build_sds_text()        → tüm 16 bölüm düz metin
  3. build_context_blocks()   → ilgili mevzuat paragrafları
  4. Claude API               → bağımsız denetim raporu (Markdown)
"""

import os
from fastapi import APIRouter, Body, HTTPException

router = APIRouter()

_SYSTEM_PROMPT = """Sen KKDİK ve SEA yönetmelikleri uzmanı bir GBF/SDS denetçisisin.

Sana üç kaynak verilecek:
  A) Denetlenecek SDS'in 16 bölümü (tam metin)
  B) İlgili mevzuat paragrafları (SEA, KKDİK, CLP, ADR)
  C) Otomatik kural kontrolü sonuçları (V001-V027 kodlu bulgular)

Görevin:
1. SDS metnini (A kaynağı) baştan sona oku.
2. Her bölümü KKDİK Ek-2 ve CLP Tüzüğü gerekliliklerine göre bağımsız olarak denetle.
3. Tespit ettiğin her sorunu şu şekilde raporla:
   - Hangi bölüm (B1–B16)
   - Ne eksik veya hatalı
   - Hangi mevzuat maddesine aykırı (B kaynağından alıntıla)
   - Somut düzeltme adımı
4. C kaynağındaki otomatik bulgular varsa onları da açıkla — ama bunlara sınırlı kalma,
   kendi bağımsız incelemeni de yap.
5. Bir bölümde sorun görmüyorsan onu raporlama.

Yanıtını şu formatta ver:
## Hatalar (Düzeltilmesi Zorunlu)
## Uyarılar (Kontrol Edilmeli)
## Bilgi Notları
## Genel Değerlendirme

Yanıt dili: Türkçe. Teknik terimler için parantez içinde İngilizce karşılık ekle.

KESİN KURAL: Yanıtlarında YALNIZCA sana verilen mevzuat paragraflarını (B kaynağı) \
ve SDS metnini (A kaynağı) kullan. Bu kaynaklarda bulunmayan bir bilgiyi kendi genel \
bilginden üretme veya tahmin etme. İlgili mevzuat paragrafı sağlanmamışsa \
"İlgili mevzuat paragrafı bu denetimde sağlanmadı." yaz ve o konuda yorum yapma."""


def _build_sds_text(h_codes, phys_props, components, sds_data) -> str:
    """Tüm 16 SDS bölümünü denetim için düz metin olarak oluştur."""

    clp  = sds_data.get("clp", {})
    prod = sds_data.get("product_info", {})
    adr  = sds_data.get("adr", {})
    ppe  = sds_data.get("ppe", {})
    eco  = sds_data.get("eco", {})

    # Seçili P kodları
    p_raw = sds_data.get("p_codes", {})
    if isinstance(p_raw, dict):
        label_sel  = p_raw.get("label", {}).get("selected", [])
        sds_mand   = p_raw.get("sds", {}).get("mandatory", []) if isinstance(p_raw.get("sds"), dict) else []
        sds_eval   = p_raw.get("sds", {}).get("evaluate", []) if isinstance(p_raw.get("sds"), dict) else []
    else:
        label_sel = sds_mand = sds_eval = []

    # ADR özet
    road = adr.get("road", {}) if isinstance(adr, dict) else {}
    adr_line = (
        f"UN {road.get('un','-')} | Sınıf {road.get('class','-')} | "
        f"PG {road.get('pg','-')} | {road.get('shipping_name','-')}"
        if road.get("un") else "Tehlikeli madde değil"
    )

    # Bileşenler
    comp_lines = []
    for c in components:
        name = c.get("name_tr") or c.get("name") or c.get("cas_no", "?")
        conc = c.get("conc") or c.get("concentration", "?")
        cas  = c.get("cas_no") or c.get("cas", "")
        reach = c.get("reach_no", "")
        h_list = ", ".join(
            h.get("h_code", "") for h in c.get("hazards", []) if h.get("h_code")
        )
        comp_lines.append(
            f"  • {name} (CAS: {cas}) — %{conc}"
            + (f" | REACH: {reach}" if reach else "")
            + (f" | H: {h_list}" if h_list else "")
        )

    # Fiziksel özellikler
    def _pv(key, unit=""):
        v = phys_props.get(key)
        if v is None:
            return "N/A"
        if isinstance(v, dict):
            v = v.get("display") or v.get("value") or v.get("calc")
        return f"{v} {unit}".strip() if v is not None else "N/A"

    # Bölüm 4-8 cümleleri — sds_sentence_service'ten üret
    sec4 = sec5 = sec6 = sec7 = sec8_text = ""
    try:
        from app.services.sds_sentence_service import generate_section
        mixture_form = prod.get("form", "liquid")
        for sec_no, var in [(4, "sec4"), (5, "sec5"), (6, "sec6"), (7, "sec7")]:
            res = generate_section(sec_no, h_codes, mixture_form)
            bullets = res.get("bullets", [])
            text    = res.get("text", "")
            val     = text or (" | ".join(bullets) if bullets else "Motor çıktısı yok")
            if sec_no == 4: sec4 = val
            if sec_no == 5: sec5 = val
            if sec_no == 6: sec6 = val
            if sec_no == 7: sec7 = val
        res8 = generate_section(8, h_codes, mixture_form)
        ppe_dict = res8.get("ppe", {})
        sec8_text = (
            f"Göz: {ppe_dict.get('eye','-')} | "
            f"Cilt: {ppe_dict.get('skin','-')} | "
            f"Solunum: {ppe_dict.get('resp','-')}"
        )
    except Exception:
        sec8_text = str(ppe)[:300] if ppe else "Motor çıktısı yok"

    # Ekoloji özeti
    eco_h = eco.get("h_codes", []) if isinstance(eco, dict) else []
    eco_line = ", ".join(eco_h) if eco_h else "Sucul tehlike sınıfı yok"

    lines = [
        "=== GBF/SDS TAM METNİ (16 BÖLÜM) ===",
        "",
        f"B1.1 Ürün adı       : {prod.get('product_name') or 'belirtilmemiş'}",
        f"B1.1 Form / Kullanım: {prod.get('form') or '-'} / {prod.get('usage') or 'industrial'}",
        f"B1.3 Tedarikçi      : {prod.get('supplier_name') or 'belirtilmemiş'}",
        f"      Adres          : {prod.get('supplier_address') or 'belirtilmemiş'}",
        f"      Telefon        : {prod.get('supplier_phone') or 'belirtilmemiş'}",
        f"      E-posta        : {prod.get('supplier_email') or 'belirtilmemiş'}",
        f"B1.4 Acil tel       : {prod.get('emergency_tel') or 'belirtilmemiş'}",
        "",
        f"B2.1 H kodları (sınıf.): {', '.join(clp.get('all_h_codes', h_codes)) or 'yok'}",
        f"B2.1 EUH kodları       : {', '.join(clp.get('euh_codes', [])) or 'yok'}",
        f"B2.2 Sinyal kelimesi   : {clp.get('signal_word') or 'belirtilmemiş'}",
        f"B2.2 Piktogramlar      : {', '.join(clp.get('pictograms', [])) or 'yok'}",
        f"B2.2 Etiket P kodları  : {', '.join(label_sel) or 'yok'}",
        f"B2.3 PBT/vPvB          : {sds_data.get('pbt_statement') or 'belirtilmemiş'}",
        "",
        "B3.2 Bileşenler:",
        *comp_lines,
        "",
        f"B4  İlk yardım         : {sec4[:400] if sec4 else 'N/A'}",
        f"B5  Yangınla mücadele  : {sec5[:300] if sec5 else 'N/A'}",
        f"B6  Kaza döküntüsü     : {sec6[:300] if sec6 else 'N/A'}",
        f"B7  Elleçleme/depolama : {sec7[:300] if sec7 else 'N/A'}",
        f"B8  KKE                : {sec8_text[:300]}",
        "",
        f"B9  Parlama noktası    : {_pv('flash_point','°C')}",
        f"    Kaynama noktası    : {_pv('boiling_point','°C')}",
        f"    Yoğunluk           : {_pv('density','g/mL')}",
        f"    pH                 : {_pv('ph')}",
        f"    Buhar basıncı      : {_pv('vapor_pressure','hPa')}",
        f"    Viskozite          : {_pv('viscosity','mm²/s')}",
        f"    Su çözünürlüğü     : {_pv('solubility','mg/L')}",
        f"    Tutuşma sıcaklığı  : {_pv('auto_ignition','°C')}",
        f"    Log Kow            : {_pv('log_kow')}",
        "",
        f"B10 Kararlılık/reaktivite: H kodlarına göre — {', '.join(h_codes)}",
        f"B11 Toksikoloji          : H kodlarına göre — {', '.join(h_codes)}",
        f"B12 Ekoloji              : {eco_line}",
        f"B12.5 PBT/vPvB           : {sds_data.get('pbt_statement') or 'belirtilmemiş'}",
        f"B14 ADR taşımacılık      : {adr_line}",
        "",
        f"B16 SDS P kodları (zorunlu): {', '.join(sds_mand) or 'yok'}",
        f"B16 SDS P kodları (değerl.): {', '.join(sds_eval[:10]) or 'yok'}",
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
    sds_data   = data.get("sds_data", {})

    # ── Motor düzeltmeleri (PDF endpoint ile aynı) ────────────────────────────
    all_h_codes = list(sds_data.get("clp", {}).get("all_h_codes", h_codes))
    if "H314" in h_codes and "H318" not in all_h_codes:
        all_h_codes = all_h_codes + ["H318"]

    try:
        from app.services.ghs_pictogram import get_ghs_codes
        motor_pictograms = get_ghs_codes(h_codes)
    except Exception:
        motor_pictograms = sds_data.get("clp", {}).get("pictograms", [])

    sds_data = dict(sds_data)
    sds_data["clp"] = {
        **sds_data.get("clp", {}),
        "all_h_codes": all_h_codes,
        "pictograms":  motor_pictograms,
    }

    # ── 1. Kural kontrolü (V001-V027) ────────────────────────────────────────
    from app.services.sds_validator import validate_sds
    issues = validate_sds(sds_data, h_codes, phys_props, components)
    issues = [i for i in issues if i.get("code") not in ("V013", "V015")]

    summary = {
        "error":   sum(1 for i in issues if i["level"] == "error"),
        "warning": sum(1 for i in issues if i["level"] == "warning"),
        "info":    sum(1 for i in issues if i["level"] == "info"),
    }

    # ── 2. Tüm 16 bölüm SDS metni ────────────────────────────────────────────
    sds_text = _build_sds_text(h_codes, phys_props, components, sds_data)

    # ── 3. Mevzuat bağlamı ───────────────────────────────────────────────────
    from app.services.knowledge_service import build_context_blocks
    kb_blocks = build_context_blocks("sds gbf bölüm " + " ".join(h_codes[:8]))

    # ── 4. Otomatik kural sonuçları metni ────────────────────────────────────
    _icon = {"error": "❌", "warning": "⚠️", "info": "ℹ️"}
    issues_text = "=== OTOMATİK KURAL KONTROLÜ (V001-V027) ===\n\n"
    if not issues:
        issues_text += "Hiçbir kural ihlali tespit edilmedi.\n"
    else:
        for iss in issues:
            issues_text += (
                f"{_icon.get(iss['level'], '•')} [{iss['code']}] "
                f"Bölüm {iss['section']}: {iss['msg']}"
            )
            if iss.get("rule"):
                issues_text += f"\n   Dayanak: {iss['rule']}"
            issues_text += "\n\n"
    issues_text += "=== KURAL KONTROLÜ SONU ==="

    # ── 5. Claude'a gönder ───────────────────────────────────────────────────
    user_parts: list[dict] = []
    user_parts.extend(kb_blocks)                                         # B kaynağı
    user_parts.append({"type": "text", "text": sds_text})               # A kaynağı
    user_parts.append({"type": "text", "text": issues_text})            # C kaynağı
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
    }
