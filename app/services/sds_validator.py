"""
SDS Cross-Validator — Çapraz Bölüm Tutarlılık Kontrol Motoru
=============================================================
CLP Regulation + KKDİK Ek-2 gerekliliklerine göre bölümler arası
tutarlılık denetimi.

Kullanım:
    from app.services.sds_validator import validate_sds
    issues = validate_sds(sds_data, h_codes, phys_props)
    # issues: [{"level": "error/warning", "code": "V001", "msg": "..."}]
"""

from typing import List, Dict, Any


def validate_sds(
    sds_data: Dict,
    h_codes: List[str],
    phys_props: Dict,
    components: List[Dict] = None,
) -> List[Dict]:
    """
    SDS verilerini çapraz bölüm kurallarına göre doğrula.
    
    Returns:
        [{"level": "error"|"warning"|"info", "code": "V0XX", 
          "section": "B9", "msg": "...", "rule": "..."}]
    """
    issues = []

    def error(code, section, msg, rule=""):
        issues.append({"level":"error","code":code,"section":section,"msg":msg,"rule":rule})
    def warn(code, section, msg, rule=""):
        issues.append({"level":"warning","code":code,"section":section,"msg":msg,"rule":rule})
    def info(code, section, msg):
        issues.append({"level":"info","code":code,"section":section,"msg":msg,"rule":""})

    fp = phys_props.get("flash_point")
    bp = phys_props.get("boiling_point")
    vis = phys_props.get("viscosity")
    ph  = phys_props.get("ph")
    sol = phys_props.get("solubility","")
    density = phys_props.get("density")

    # ── B Fiziksel Doğrulama ────────────────────────────────────────────
    
    # V001: H226 → Parlama Noktası zorunlu ve ≤60°C olmalı
    if "H226" in h_codes or "H225" in h_codes or "H224" in h_codes:
        if fp is None:
            error("V001","B9",
                  "H226 (Alevlenir Sıvı) kodunuz var. Bölüm 9'da Parlama Noktası zorunludur.",
                  "CLP Annex I 2.6 + KKDİK EK-2")
        elif fp > 60 and "H226" in h_codes:
            warn("V002","B9",
                 f"Parlama noktası {fp}°C. H226 için ≤60°C beklenir. Sınıflandırmayı kontrol edin.",
                 "CLP Annex I Tablo 2.6.1")

    # V003: H304 (Aspirasyon) → Viskozite zorunlu
    if "H304" in h_codes:
        if vis is None:
            error("V003","B9",
                  "H304 (Aspirasyon tehlikesi) kodunuz var. Bölüm 9'da Viskozite değeri zorunludur.",
                  "CLP Annex I 3.10 — viskozite H304 için belirleyici")
        elif vis > 20:
            warn("V004","B9",
                 f"Viskozite {vis} mm²/s. H304 genellikle <20 mm²/s maddeler için geçerlidir.",
                 "CLP Annex I 3.10.3")

    # V005: H314 (Aşındırıcı) → pH zorunlu
    if "H314" in h_codes or "H290" in h_codes:
        if ph is None:
            warn("V005","B9",
                 "H314 (Aşındırıcı) veya H290 kodunuz var. pH değeri girilmesi önerilir.",
                 "KKDİK EK-2 B9 gereklilikleri")
        elif ph is not None and 4 <= ph <= 10:
            warn("V006","B2+B9",
                 f"pH {ph} — aşındırıcı özellik için pH<2 veya pH>11.5 beklenir. Sınıflandırmayı kontrol edin.",
                 "CLP Annex I 3.2.1")

    # V007: H400/H410 → Sucul bilgi zorunlu (B12)
    if any(h in h_codes for h in ["H400","H410","H411"]):
        ec_comps = components or []
        has_eco_data = any(c.get("hazards") for c in ec_comps 
                          if any("Aquatic" in str(h) for h in c.get("hazards",[])))
        if not has_eco_data:
            info("V008","B12",
                 "Sucul tehlike kodunuz var. B12 için EC50/LC50 test verisi girilmesi tavsiye edilir.")

    # ── Bölümler Arası Tutarlılık ────────────────────────────────────────
    
    # V009: H272 (Oksitleyici) varsa B10'da uyumsuz madde uyarısı olmalı
    if any(h in h_codes for h in ["H270","H271","H272"]):
        info("V009","B10",
             "Oksitleyici madde — B10.5 Bağdaşmayan Maddeler: yanıcı ve organik maddeler belirtilmeli.")

    # V010: H260/H261 (Su reaktif) varsa B7'de nem uyarısı olmalı
    if any(h in h_codes for h in ["H260","H261"]):
        info("V010","B7",
             "Su reaktif madde — B7 Depolama: nem ve su kaynaklarından korunma zorunludur.")

    # V011: CMR maddeler → B8'de özel KKE
    cmr_h = {"H340","H341","H350","H351","H360","H361","H362"}
    if any(h in h_codes for h in cmr_h):
        info("V011","B8",
             "CMR maddesi (kanserojen/mutajen/üreme toksik) — B8'de solunum koruması ve özel KKE gerekebilir.")

    # V012: H334 (Solunum duyarlılaştırıcı) → B8'de solunum koruyucu zorunlu
    if "H334" in h_codes:
        warn("V012","B8",
             "H334 (Solunum duyarlılaştırıcı) — B8.2'de SCBA veya tam yüz maskesi belirtilmeli.",
             "KKDİK Kanserojen/Mutajen Yönetmeliği")

    # V013: Etiket P kodu sayısı kontrolü
    p_codes = sds_data.get("p_codes",{})
    label_p = p_codes.get("label",{})
    label_count = len(label_p) if isinstance(label_p, (list,dict)) else 0
    if label_count > 6:
        warn("V013","B2",
             f"Etikette {label_count} P kodu var. CLP kuralı max 6 P koduna izin verir.",
             "CLP Article 22(4)")

    # V014: Signal word tutarlılığı
    signal = sds_data.get("clp",{}).get("signal_word","")
    danger_h = {"H300","H301","H310","H311","H330","H331","H314","H318","H340",
                "H350","H360","H370","H372","H224","H225"}
    if any(h in h_codes for h in danger_h) and signal != "Danger":
        error("V014","B2",
              f"Bu H kodları için sinyal kelimesi 'Danger' olmalıdır (mevcut: '{signal}').",
              "CLP Annex III")

    # V015: Revizyonsuz GBF uyarısı
    author = sds_data.get("author",{})
    if not author.get("cert_no"):
        warn("V015","B16",
             "GBF Hazırlayıcı sertifika numarası girilmemiş. KKDİK kapsamında zorunludur.",
             "KKDİK EK-2 B16")

    return issues


def format_issues(issues: List[Dict], lang: str = "TR") -> str:
    """Doğrulama sonuçlarını okunabilir formatta döndür."""
    if not issues:
        return "✓ Tüm çapraz bölüm kontrolleri geçti." if lang=="TR" else "✓ All cross-section checks passed."
    
    lines = []
    for iss in issues:
        level_icon = {"error":"❌","warning":"⚠️","info":"ℹ️"}.get(iss["level"],"•")
        lines.append(f"{level_icon} [{iss['code']}] {iss['section']}: {iss['msg']}")
    return "\n".join(lines)


if __name__ == "__main__":
    # Test
    sds = {"clp":{"signal_word":"Warning"},"p_codes":{},"author":{}}
    h = ["H226","H304","H315","H411"]
    phys = {"flash_point":27,"boiling_point":138}
    
    issues = validate_sds(sds, h, phys)
    print(f"Bulunan sorun: {len(issues)}")
    for iss in issues:
        print(f"  {iss['level'].upper()} {iss['code']}: {iss['msg'][:80]}")
