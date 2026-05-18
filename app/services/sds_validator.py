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

    def _f(v):
        try: return float(v)
        except: return None

    fp      = _f(phys_props.get("flash_point"))
    bp      = _f(phys_props.get("boiling_point"))
    vis     = _f(phys_props.get("viscosity"))
    ph      = _f(phys_props.get("ph"))
    sol     = phys_props.get("solubility","")
    density = _f(phys_props.get("density"))

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

    # ── Asit-Baz nötralizasyon tespiti (V006 için) ──────────────────────────
    # Bilinen korozif bazlar (CAS)
    _CORROSIVE_BASES = {
        '1310-73-2',  # NaOH
        '1310-58-3',  # KOH
        '1305-62-0',  # Ca(OH)2
        '1336-21-6',  # NH3 çözeltisi
        '7664-41-7',  # NH3 gaz
        '497-19-8',   # Na2CO3
        '584-08-7',   # K2CO3
        '7681-52-9',  # NaOCl
        '10124-56-8', # Na hexametafosfat
        '1313-82-2',  # Na2S
        '16721-80-5', # NaHS
    }
    # Bilinen korozif asitler (CAS)
    _CORROSIVE_ACIDS = {
        '7647-01-0',  # HCl
        '7664-93-9',  # H2SO4
        '7697-37-2',  # HNO3
        '7664-38-2',  # H3PO4
        '7783-06-4',  # H2S
        '79-10-7',    # Akrilik asit
        '64-18-6',    # Formik asit
        '79-11-8',    # Kloroasetik asit
        '107-92-6',   # Bütirik asit
        '79-09-4',    # Propiyonik asit
        '50-21-5',    # Laktik asit
        '77-92-9',    # Sitrik asit
    }
    _comp_cas_list = [str(c.get('cas_no') or c.get('cas','')).strip()
                      for c in (components or [])]
    _has_corr_base = any(cas in _CORROSIVE_BASES for cas in _comp_cas_list)
    _has_corr_acid = any(cas in _CORROSIVE_ACIDS for cas in _comp_cas_list)
    _neutralization_likely = _has_corr_base and _has_corr_acid

    # V005: H314 (Aşındırıcı) → pH zorunlu
    if "H314" in h_codes or "H290" in h_codes:
        if ph is None:
            warn("V005","B9",
                 "H314 (Aşındırıcı) veya H290 kodunuz var. pH değeri girilmesi önerilir.",
                 "KKDİK EK-2 B9 gereklilikleri")
        elif ph is not None and 2.0 < ph < 11.5:
            if _neutralization_likely:
                # Asit + baz bir arada → nötralizasyon → H314 geçersiz olabilir
                _base_names = [c.get('name_tr') or c.get('name','')
                               for c in (components or [])
                               if str(c.get('cas_no') or c.get('cas','')).strip() in _CORROSIVE_BASES]
                _acid_names = [c.get('name_tr') or c.get('name','')
                               for c in (components or [])
                               if str(c.get('cas_no') or c.get('cas','')).strip() in _CORROSIVE_ACIDS]
                warn("V006","B2+B9",
                     f"pH {ph} ile H314 çelişiyor — Karışımda asit ({', '.join(_acid_names)}) "
                     f"ve baz ({', '.join(_base_names)}) birlikte mevcut. "
                     f"KKDİK Ek-1 §3.2.3.3: nötralizasyon gerçekleşmişse H314 geçersiz olabilir. "
                     f"Karışımı test ettirin veya serbest bileşen konsantrasyonlarını gözden geçirin.",
                     "KKDİK Ek-1 §3.2.3.3.3 / CLP Annex I §3.2.3.3")
            else:
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
    # Sadece B8.2'de yeterli koruma YOKSA uyar (false positive'i önle)
    if "H334" in h_codes:
        try:
            from app.services.sds_sentence_service import generate_section as _gen8
            _resp = _gen8(8, h_codes).get('ppe', {}).get('resp', '').lower()
            _adequate = any(kw in _resp for kw in ['scba', 'tam yüz', 'full face', 'yarım yüz', 'half face'])
        except Exception:
            _adequate = False
        if not _adequate:
            warn("V012","B8",
                 "H334 (Solunum duyarlılaştırıcı) — B8.2'de SCBA veya tam yüz maskesi belirtilmeli.",
                 "KKDİK Kanserojen/Mutajen Yönetmeliği")

    # V013: Etiket P kodu sayısı kontrolü
    # label yapısı: {'selected':[...], 'all':[...], ...} veya düz liste
    p_codes = sds_data.get("p_codes",{})
    label_p = p_codes.get("label",{})
    if isinstance(label_p, dict):
        # select_label_p_codes sonucu — 'selected' listesini say (P501 hariç)
        _sel = label_p.get("selected", label_p.get("selected_codes", []))
        label_count = len([p for p in _sel if p not in ('P501','P101','P102')])
    elif isinstance(label_p, list):
        label_count = len([p for p in label_p if p not in ('P501','P101','P102')])
    else:
        label_count = 0
    if label_count > 6:
        warn("V013","B2",
             f"Etikette {label_count} P kodu var (P501 hariç). CLP kuralı max 6 P koduna izin verir.",
             "CLP Article 22(4)")

    # V014: Signal word tutarlılığı
    signal = sds_data.get("clp",{}).get("signal_word","")
    danger_h = {"H300","H301","H310","H311","H330","H331","H314","H318","H340",
                "H350","H360","H370","H372","H224","H225"}
    if any(h in h_codes for h in danger_h) and signal != "Danger":
        error("V014","B2",
              f"Bu H kodları için sinyal kelimesi 'Danger' olmalıdır (mevcut: '{signal}').",
              "CLP Annex III")

    # V015: GBF Hazırlayıcı sertifika numarası eksik — info seviyesinde (PDF'de gösterilmez)
    author = sds_data.get("author",{})
    if not author.get("cert_no"):
        info("V015","B16",
             "GBF Hazırlayıcı sertifika numarası girilmemiş. KKDİK kapsamında zorunludur. (V015)")

    # V016: Çözünürlük > Yoğunluk → fiziksel imkânsız
    # Max çözünürlük (mg/L) = yoğunluk (g/mL) × 1.000.000 (= %100 saf maddenin yoğunluğu)
    sol_num = _f(phys_props.get("solubility"))
    if sol_num is not None and density is not None and sol_num > (density * 1e6):
        warn("V016","B9",
             f"Çözünürlük {sol_num:,.0f} mg/L, yoğunluktan "
             f"({density * 1e6:,.0f} mg/L = {density} g/mL) büyük — fiziksel olarak imkânsız. "
             f"Muhtemelen birim dönüşüm hatası (g/mL ↔ mg/L karışıklığı) veya yanlış veri. "
             f"Değeri kontrol edin.",
             "Fizik: max çözünürlük ≤ yoğunluk × 1.000.000 mg/L")

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
