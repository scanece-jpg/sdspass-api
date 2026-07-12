"""
SDS Denetim Endpoint — /api/v1/sds/review

Akış:
  1. validate_sds()  → V001-V026 kural sonuçları
  2. build_context_blocks() → ilgili mevzuat paragrafları
  3. Claude API → bulgu raporu (Markdown)
"""

import os
import json
from fastapi import APIRouter, Body, HTTPException

router = APIRouter()

_SYSTEM_PROMPT = """Sen KKDİK ve SEA yönetmelikleri uzmanı bir GBF/SDS denetçisisin.
Sana iki kaynak verilecek:
  A) Otomatik kural kontrolü sonuçları (V001-V026 kodlu bulgular)
  B) İlgili mevzuat paragrafları (SEA, KKDİK, CLP, ADR)

Görevin:
1. Her hata/uyarıyı hangi yönetmelik maddesine aykırı olduğunu belirterek açıkla.
2. Operatöre somut düzeltme adımı öner (ne yapması gerektiğini yaz).
3. "Bilgi" seviyesindeki bulgular varsa kısaca listele.
4. Mevzuat paragraflarında ilgili madde varsa doğrudan alıntıla.

Yanıtını şu formatta ver:
## Hatalar (Düzeltilmesi Zorunlu)
## Uyarılar (Kontrol Edilmeli)
## Bilgi Notları
## Genel Değerlendirme

Yanıt dili: Türkçe. Teknik terimler için parantez içinde İngilizce karşılık ekle.

KESİN KURAL: Yanıtlarında YALNIZCA sana verilen mevzuat paragraflarını (B kaynağı) ve \
kural kontrolü sonuçlarını (A kaynağı) kullan. \
Bu kaynaklarda bulunmayan bir bilgiyi kendi genel bilginden üretme, tahmin etme veya tamamlama. \
İlgili mevzuat paragrafı sağlanmamışsa "İlgili mevzuat paragrafı bu denetimde sağlanmadı." yaz \
ve o konuda yorum yapma."""


@router.post("/api/v1/sds/review")
async def sds_review(data: dict = Body(...)):
    """
    SDS verilerini doğrular ve Claude ile mevzuat analizi yapar.

    Input:
      h_codes     : list[str]   — etiket H kodları (dominance uygulanmış)
      phys_props  : dict        — fiziksel özellikler (flash_point, ph, vb.)
      components  : list[dict]  — bileşen listesi (cas, hazards, conc, vb.)
      sds_data    : dict        — kısmi SDS verisi (clp, p_codes, adr, author)

    Output:
      issues  : list[dict]  — V001-V026 kural bulgular
      report  : str         — Claude'un Markdown raporu
      summary : dict        — {error, warning, info} sayıları
      docs_used    : int
      input_tokens : int
      output_tokens: int
    """
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

    # ── PDF endpoint ile aynı düzeltmeler ────────────────────────────────────
    # H314 varsa H318 all_h_codes'a ekle (CLP §3.3.1.4 / SEA Tablo 3.3.1)
    all_h_codes = list(sds_data.get("clp", {}).get("all_h_codes", h_codes))
    if "H314" in h_codes and "H318" not in all_h_codes:
        all_h_codes = all_h_codes + ["H318"]

    # Piktogramları motordan üret (frontend ham verisini kullanma)
    try:
        from app.services.ghs_pictogram import get_ghs_codes
        motor_pictograms = get_ghs_codes(h_codes)
    except Exception:
        motor_pictograms = sds_data.get("clp", {}).get("pictograms", [])

    # sds_data'yı düzeltilmiş verilerle güncelle
    sds_data = dict(sds_data)
    sds_data["clp"] = {
        **sds_data.get("clp", {}),
        "all_h_codes": all_h_codes,
        "pictograms":  motor_pictograms,
    }

    # ── 1. Kural kontrolü ────────────────────────────────────────────────────
    from app.services.sds_validator import validate_sds
    issues = validate_sds(sds_data, h_codes, phys_props, components)

    # V013 ve V015 kaldır — algoritmanın beklenen davranışı, hata değil
    issues = [i for i in issues if i.get("code") not in ("V013", "V015")]

    summary = {
        "error":   sum(1 for i in issues if i["level"] == "error"),
        "warning": sum(1 for i in issues if i["level"] == "warning"),
        "info":    sum(1 for i in issues if i["level"] == "info"),
    }

    # ── 2. Mevzuat bağlamı ───────────────────────────────────────────────────
    from app.services.knowledge_service import build_context_blocks
    _query = "sds gbf bölüm " + " ".join(h_codes[:8])
    kb_blocks = build_context_blocks(_query)

    # ── 3. Claude'a gönderilecek içerik ─────────────────────────────────────
    _level_icon = {"error": "❌", "warning": "⚠️", "info": "ℹ️"}

    issues_text = "### Otomatik Kural Kontrolü Sonuçları\n\n"
    if not issues:
        issues_text += "Hiçbir kural ihlali tespit edilmedi.\n"
    else:
        for iss in issues:
            icon = _level_icon.get(iss["level"], "•")
            issues_text += (
                f"{icon} **[{iss['code']}] Bölüm {iss['section']}**: "
                f"{iss['msg']}"
            )
            if iss.get("rule"):
                issues_text += f"\n   *Dayanak: {iss['rule']}*"
            issues_text += "\n\n"

    user_parts: list[dict] = []

    # Mevzuat paragrafları
    user_parts.extend(kb_blocks)

    # Kural sonuçları
    user_parts.append({"type": "text", "text": issues_text})

    # H kodları ve bileşen özeti
    comp_summary = ", ".join(
        f"{c.get('name') or c.get('cas_no', '?')} (%{c.get('conc', c.get('concentration', '?'))})"
        for c in components[:6]
    )
    context_text = (
        f"H kodları: {', '.join(h_codes)}\n"
        f"Bileşenler: {comp_summary or 'belirtilmemiş'}\n"
        f"Sinyal kelimesi: {sds_data.get('clp', {}).get('signal_word', 'belirtilmemiş')}\n"
    )
    user_parts.append({"type": "text", "text": context_text})
    user_parts.append({
        "type": "text",
        "text": "Yukarıdaki kural sonuçlarını ve H kodlarını mevzuat paragraflarıyla karşılaştırarak denetim raporu yaz.",
    })

    # ── 4. Claude çağrısı ────────────────────────────────────────────────────
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
