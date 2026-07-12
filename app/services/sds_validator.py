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

import re
from typing import List, Dict, Any
from app.services.clp_service import _parse_ph_range, normalize_ph_display

# H kodu → zorunlu piktogramlar (CLP Annex V)
_H_TO_PIC: Dict[str, str] = {
    'H200':'GHS01','H201':'GHS01','H202':'GHS01','H203':'GHS01','H204':'GHS01','H205':'GHS01','H241':'GHS01',
    'H220':'GHS02','H221':'GHS02','H222':'GHS02','H223':'GHS02','H224':'GHS02','H225':'GHS02',
    'H226':'GHS02','H228':'GHS02','H229':'GHS02','H230':'GHS02','H231':'GHS02','H232':'GHS02',
    'H270':'GHS03','H271':'GHS03','H272':'GHS03',
    'H280':'GHS04','H281':'GHS04',
    'H290':'GHS05','H314':'GHS05','H318':'GHS05',
    'H300':'GHS06','H301':'GHS06','H304':'GHS06','H310':'GHS06','H311':'GHS06','H330':'GHS06','H331':'GHS06',
    'H334':'GHS08','H340':'GHS08','H341':'GHS08','H350':'GHS08','H351':'GHS08',
    'H360':'GHS08','H361':'GHS08','H362':'GHS08',
    'H370':'GHS08','H371':'GHS08','H372':'GHS08','H373':'GHS08',
    'H302':'GHS07','H303':'GHS07','H312':'GHS07','H315':'GHS07','H317':'GHS07',
    'H319':'GHS07','H320':'GHS07','H332':'GHS07','H333':'GHS07','H335':'GHS07','H336':'GHS07','H420':'GHS07',
    'H400':'GHS09','H410':'GHS09','H411':'GHS09','H412':'GHS09','H413':'GHS09',
}

# GHS09 gerektiren H kodları varken GHS07 de varsa GHS09 baskın olur (CLP kural: çevre + irritant)
_DANGER_PICS = {'GHS01','GHS02','GHS03','GHS05','GHS06','GHS08'}  # GHS07'yi baskılar

# H kodu → ADR sınıfı eşleşmesi (temel kontrol)
_H_TO_ADR_CLASS: Dict[str, str] = {
    'H200':'1','H201':'1','H202':'1','H203':'1','H204':'1','H205':'1',
    'H220':'2','H221':'2','H222':'2','H223':'2','H224':'3','H225':'3','H226':'3','H228':'4.1',
    'H250':'4.2','H251':'4.2','H252':'4.2','H260':'4.3','H261':'4.3',
    'H270':'2','H271':'5.1','H272':'5.1',
    'H280':'2','H281':'2',
    'H290':'8',
    'H300':'6.1','H301':'6.1','H302':'6.1','H310':'6.1','H311':'6.1','H330':'6.1','H331':'6.1',
    'H314':'8','H290':'8',
    'H400':'9','H410':'9','H411':'9',
}


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
        if v is None: return None
        # _parsed_phys dict formatı: {'display':..., 'calc':..., 'value':...}
        if isinstance(v, dict):
            v = v.get('calc') if v.get('calc') is not None else v.get('value')
            if v is None: return None
        s = str(v).strip()
        # Önek sembollerini temizle: ~, >, <, ≈, ≤, ≥  (ör. "~1.000.000 mg/L")
        s = re.sub(r'^[~><≈≤≥]+\s*', '', s)
        # Birim ve açıklama kısmını at — ilk boşluğa kadar al (ör. "27 °C" → "27")
        s = s.split()[0] if s else ''
        # Türkçe/Avrupa binlik ayracı: "1.000.000" → "1000000"
        # Kalıp: rakam + nokta + tam olarak 3 rakam (en az 1 kez)
        if re.search(r'\d\.\d{3}', s):
            s = s.replace('.', '')
        # Aralık değerleri için alt sınırı döndür (ör. "23-60" → "23")
        if '-' in s and not s.startswith('-'):
            s = s.split('-')[0].strip()
        try: return float(s)
        except: return None

    def _ph_range(v):
        """pH için (alt, üst) tuple döndür. Aralık yoksa her ikisi de aynı değer."""
        if v is None: return None, None
        # _parsed_phys dict formatı: {'display':..., 'calc':...}
        if isinstance(v, dict):
            v = v.get('display') or v.get('calc')
            if v is None: return None, None
        try:
            return _parse_ph_range(v)
        except (ValueError, TypeError):
            return None, None

    fp      = _f(phys_props.get("flash_point"))
    bp      = _f(phys_props.get("boiling_point"))
    vis     = _f(phys_props.get("viscosity"))
    ph_low, ph_high = _ph_range(phys_props.get("ph"))
    ph = ph_low   # geriye dönük uyumluluk (ph is None kontrolü için)
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

    # H314 bileşen bazlı toplamsal yoldan mı geliyor?
    # Herhangi bir bileşenin hazards listesinde H314 varsa → additivity yolu → V006 tetiklemez.
    # CLP Annex I §3.2.3.1.2 (pH yolu) ile §3.2.3.3 (toplamsal yol) bağımsız alternatif yöntemlerdir.
    _h314_from_additivity = (
        "H314" in h_codes and
        any(
            any((h.get('h_code') or '').replace('*', '').strip().startswith('H314')
                for h in (c.get('hazards') or []))
            for c in (components or [])
        )
    )

    # V005: H314 (Aşındırıcı) → pH zorunlu
    if "H314" in h_codes or "H290" in h_codes:
        if ph is None:
            warn("V005","B9",
                 "H314 (Aşındırıcı) veya H290 kodunuz var. pH değeri girilmesi önerilir.",
                 "KKDİK EK-2 B9 gereklilikleri")
        elif ph_low is not None and ph_high is not None and ph_low > 2.0 and ph_high < 11.5:
            if _neutralization_likely:
                # Asit + baz bir arada → nötralizasyon → H314 geçersiz olabilir
                _base_names = [c.get('name_tr') or c.get('name','')
                               for c in (components or [])
                               if str(c.get('cas_no') or c.get('cas','')).strip() in _CORROSIVE_BASES]
                _acid_names = [c.get('name_tr') or c.get('name','')
                               for c in (components or [])
                               if str(c.get('cas_no') or c.get('cas','')).strip() in _CORROSIVE_ACIDS]
                _ph_disp = f"{ph_low}–{ph_high}" if ph_low != ph_high else str(ph_low)
                warn("V006","B2+B9",
                     f"pH {_ph_disp} ile H314 çelişiyor — Karışımda asit ({', '.join(_acid_names)}) "
                     f"ve baz ({', '.join(_base_names)}) birlikte mevcut. "
                     f"KKDİK Ek-1 §3.2.3.3: nötralizasyon gerçekleşmişse H314 geçersiz olabilir. "
                     f"Karışımı test ettirin veya serbest bileşen konsantrasyonlarını gözden geçirin.",
                     "KKDİK Ek-1 §3.2.3.3.3 / CLP Annex I §3.2.3.3")
            elif not _h314_from_additivity:
                # H314 bileşen bazlı toplamsal yoldan gelmiyorsa → pH çelişkisi uyarısı
                _ph_disp = f"{ph_low}–{ph_high}" if ph_low != ph_high else str(ph_low)
                warn("V006","B2+B9",
                     f"pH {_ph_disp} — aşındırıcı özellik için pH<2 veya pH>11.5 beklenir. Sınıflandırmayı kontrol edin.",
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
    cmr_h = {"H340","H341","H350","H351",
             "H360","H360D","H360F","H360FD",
             "H361","H361D","H361F","H361FD",
             "H362"}
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
             f"Etikette {label_count} adet P kodu seçildi (P501/P101/P102 hariç). "
             f"CLP Madde 22(4): tehlikenin niteliği gerektiriyorsa 6 limit aşılabilir — "
             f"H kodu bazlı zorunlu P kodları bu sistemde kesilmez. "
             f"Etiket tasarımında yer kısıtlıysa manuel gözden geçirebilirsiniz.",
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

    # V017: STOT kodları mevcut ancak hedef organ bilgisi girilmemiş
    # CLP Ek-VI dipnotu (**): hedef organ / maruziyet yolu Bölüm 11'de zorunlu.
    import re as _re
    stot_codes_present = [h for h in h_codes if h in ('H370', 'H371', 'H372', 'H373')]
    if stot_codes_present:
        _stot_comps = (components or []) or sds_data.get('components', [])
        has_organ_info = any(
            _re.search(r'\(([^)]+)\)', (haz.get('h_code') or ''))
            for c in _stot_comps
            for haz in (c.get('hazards') or [])
            if (haz.get('h_code') or '').replace('*', '').strip()[:4]
            in ('H370', 'H371', 'H372', 'H373')
        )
        if not has_organ_info:
            warn("V017", "B11",
                 f"STOT kodu/ları mevcut ({', '.join(stot_codes_present)}). "
                 f"CLP Ek-VI dipnotu (**): hedef organ Bölüm 11'de zorunlu olarak belirtilmelidir. "
                 f"Bileşen tehlike kodu formatında organ bilgisi ekleyin; "
                 f"örn. 'H372 (nervous system)' veya 'H370 (liver)'.",
                 "CLP Ek-VI (**) dipnotu — hedef organ zorunlu")

    # V018: ECHA C&L / PubChem kaynaklı bileşende REACH numarası eksik
    # source_priority ≥ 4 → ECHA C&L (4) veya PubChem (5) — daha az güvenilir kaynak.
    # Bu bileşenlerde REACH kayıt numarası bulunamadıysa B15 eksik kalır.
    # Not: bu uyarı PDF'e değil, yalnızca API yanıtına / uygulama içi uyarıya eklenir.
    _v018_comps = (components or []) or sds_data.get('components', [])
    _echa_no_reach = [
        c for c in _v018_comps
        if int(c.get('source_priority') or 1) >= 4
        and not (c.get('reach_no') or '').strip()
        and not c.get('ate_unknown', False)   # "mevzuata göre sınıflandırılmamış" bileşeni atla
    ]
    if _echa_no_reach:
        _v018_names = ', '.join(
            (c.get('name_tr') or c.get('name') or c.get('cas_no') or '?')
            for c in _echa_no_reach[:3]
        )
        _v018_suffix = f' (+{len(_echa_no_reach) - 3} daha)' if len(_echa_no_reach) > 3 else ''
        warn("V018", "B15",
             f"ECHA C&L / PubChem kaynaklı {len(_echa_no_reach)} bileşende REACH numarası "
             f"bulunamadı: {_v018_names}{_v018_suffix}. "
             f"B15 için REACH kayıt numarasını doğrulayın veya 'muaf — [gerekçe]' belirtin. "
             f"(Madde tescilsizse REACH Art. 2 kapsamında muafiyet gerekçesi zorunludur.)",
             "REACH (AT) 1907/2006 Madde 31(6)(a) + KKDİK B15")

    # V019: GHS09 / env_mark tutarlılık kontrolü
    # SEA Ek-5 §3.1: H400, H410, H411 → GHS09 zorunlu
    #                H412, H413 (kronik 3-4) → GHS09 piktogramı ALMAZ
    _GHS09_TRIGGER = {'H400', 'H410', 'H411'}
    _ECO_ALL       = {'H400', 'H410', 'H411', 'H412', 'H413'}
    _h_set          = set(h_codes)
    _ghs09_required = bool(_h_set & _GHS09_TRIGGER)
    _eco_present    = bool(_h_set & _ECO_ALL)
    _clp_pics       = set(sds_data.get('clp', {}).get('pictograms', []))
    _ghs09_on_label = 'GHS09' in _clp_pics

    if _ghs09_required and not _ghs09_on_label:
        warn("V019", "B2",
             f"H kodu ({', '.join(_h_set & _GHS09_TRIGGER)}) var ama GHS09 (çevre tehlikesi) "
             f"piktogramı etikette eksik. "
             f"SEA Ek-5 §3.1: H400/H410/H411 → GHS09 zorunludur.",
             "SEA Ek-5 §3.1 / CLP Annex V Tablo 1.4")
    elif _ghs09_on_label and not _eco_present:
        warn("V019", "B2",
             "GHS09 piktogramı etikette var ancak H400/H410/H411/H412/H413 yok. "
             "Sucul tehlike sınıflandırmasını ekleyin veya GHS09'u kaldırın.",
             "SEA Ek-5 §3.1 / CLP Annex V")
    elif _eco_present and not _ghs09_required and _ghs09_on_label:
        # Yalnızca H412/H413 var; piktogram yanlışlıkla eklenmiş
        info("V019", "B2",
             f"Yalnızca H412/H413 için GHS09 piktogramı gerekmez (SEA Ek-5 §3.1). "
             f"Etiket tasarımında GHS09'u kaldırabilirsiniz.")

    # V020: H314 → H318 otomatik tetikleme kontrolü
    # SEA Ek-1, Tablo 3.3.1: H314 (Cilt Aş. 1) mevcut olduğunda H318 (Göz Hasarı 1)
    # sınıflandırmaya otomatik eklenir.
    # Etikette H318 gizlenmesi normaldir — SEA Md. 28 dominance: H314 baskın gelir.
    if 'H314' in h_codes:
        _all_h = set(sds_data.get('clp', {}).get('all_h_codes', []))
        # all_h_codes yoksa h_codes ile aynı kabul et (fallback)
        if not _all_h:
            _all_h = set(h_codes)

        if 'H318' not in _all_h:
            warn("V020", "B2",
                 "H314 (Cilt Aşındırıcı 1) mevcut — SEA Ek-1 Tablo 3.3.1 uyarınca "
                 "H318 (Göz Hasarı 1) sınıflandırma tablosuna (B2.1) otomatik eklenmeli. "
                 "B2.1'de H318 satırı eksik.",
                 "SEA Ek-1 Tablo 3.3.1 / CLP Annex I §3.3.2.1")

        # H318 etiket h_codes'unda görünüyorsa uyar (dominance uygulanmamış)
        if 'H318' in set(h_codes):
            info("V020", "B2",
                 "H318 etiket H kodları arasında görünüyor. H314 varken H318 etiketten "
                 "gizlenmelidir (SEA Madde 28 öncelik kuralı). "
                 "Etiket tasarımında H318 ifadesini kaldırın.",
                 "SEA Madde 28(3) / CLP Article 27 — label dominance")

    # ── V021: H kodu substance_db / sea_ek6 doğrulaması ─────────────────────
    # Her bileşenin CAS'ı için resmi sınıflandırmayı çek, bildirilen H kodlarını karşılaştır
    if components:
        try:
            from app.services.substance_lookup import lookup_substance
            for comp in components:
                cas = (comp.get('cas') or '').strip()
                if not cas:
                    continue
                comp_h = {h.get('h_code','')[:4] for h in comp.get('hazards', []) if h.get('h_code')}
                if not comp_h:
                    continue
                ref = lookup_substance(cas)
                if not ref:
                    continue
                ref_h = {h.get('h_code','')[:4] for h in ref.get('hazards', []) if h.get('h_code')}
                if not ref_h:
                    continue
                # Resmi listede olan ama bileşende eksik H kodları
                missing = ref_h - comp_h - {'H318'}  # H318 dominance ile gizlenebilir
                # Bileşende olan ama resmi listede olmayan H kodları
                extra = comp_h - ref_h
                name = comp.get('name') or cas
                if missing:
                    warn("V021", "B2+B3",
                         f"{name} ({cas}): Resmi sınıflandırmada olan H kodları eksik: "
                         f"{', '.join(sorted(missing))}. Kaynak: {ref.get('source','')}",
                         "CLP Annex VI / SEA Ek-6 / KKDİK")
                if extra:
                    warn("V021", "B2+B3",
                         f"{name} ({cas}): Resmi sınıflandırmada olmayan H kodları mevcut: "
                         f"{', '.join(sorted(extra))}. Kaynak: {ref.get('source','')}",
                         "CLP Annex VI / SEA Ek-6 / KKDİK")
        except Exception:
            pass

    # ── V022: H kodundan piktogram doğruluğu ─────────────────────────────────
    _label_pics = set(sds_data.get('clp', {}).get('pictograms', []))
    _h_set_base = {h[:4] for h in h_codes}
    _required_pics: set = set()
    for h in _h_set_base:
        p = _H_TO_PIC.get(h)
        if p:
            _required_pics.add(p)
    # GHS07 baskınlık — CLP Madde 26 / SEA Madde 28, ghs_pictogram.py ile tutarlı:
    #
    # Kural A — CLP Art.26(3): GHS06 (kafatası) varsa GHS07 tamamen kaldırılır.
    if 'GHS06' in _required_pics:
        _required_pics.discard('GHS07')

    # Kural B — CLP Art.26(4): GHS05 (aşındırıcı) varsa GHS07 yalnızca H315/H319
    #   kaynaklıysa gizlenir; H317/H302/H312/H332/H335/H336 varsa KALIR.
    _GHS07_KEEPS_GHS05 = {'H302', 'H312', 'H332', 'H317', 'H335', 'H336'}
    if 'GHS05' in _required_pics and 'GHS06' not in _required_pics:
        if not (_h_set_base & _GHS07_KEEPS_GHS05):
            _required_pics.discard('GHS07')

    # Kural C — CLP Art.26(5): GHS08 YALNIZCA solunum hassasiyeti (H334) nedeniyle
    #   varsa GHS07 cilt duyar.(H317) + cilt/göz tahrişi(H315/H319) için gizlenir;
    #   H302/H312/H332/H335/H336 varsa GHS07 KALIR.
    #   GHS08 kanserojen(H350)/mutajen(H340)/repro(H360) nedeniyle varsa kural
    #   devreye GİRMEZ — GHS07 etkilenmez.
    _GHS07_KEEPS_H334 = {'H302', 'H312', 'H332', 'H335', 'H336'}
    if ('GHS08' in _required_pics
            and 'H334' in _h_set_base
            and not (_h_set_base & _GHS07_KEEPS_H334)):
        _required_pics.discard('GHS07')
    _missing_pics = _required_pics - _label_pics
    _extra_pics   = _label_pics - _required_pics - {'GHS09'}  # GHS09 ayrıca V019'da
    if _missing_pics:
        error("V022", "B2",
              f"H kodlarından zorunlu piktogram(lar) etikette eksik: {', '.join(sorted(_missing_pics))}. "
              f"İlgili H kodları: {', '.join(h for h in sorted(_h_set_base) if _H_TO_PIC.get(h) in _missing_pics)}",
              "CLP Annex V / SEA Ek-5")
    if _extra_pics:
        warn("V022", "B2",
             f"Etikette H kodlarıyla desteklenmeyen piktogram(lar) var: {', '.join(sorted(_extra_pics))}",
             "CLP Annex V / SEA Ek-5")

    # ── V023: P kodu uyumu ────────────────────────────────────────────────────
    # p_code_service'in önerdiği zorunlu P kodlarını hesapla, etikettekilerle karşılaştır
    try:
        _p_raw = sds_data.get('p_codes', {})
        if isinstance(_p_raw, list):
            _label_p = set(_p_raw)
        elif isinstance(_p_raw, dict):
            _selected  = _p_raw.get('label', {}).get('selected', []) or []
            _mandatory = _p_raw.get('label', {}).get('mandatory', []) or []
            _label_p   = set(_selected) | set(_mandatory)
        else:
            _label_p = set()
        from app.services.p_code_service import H_BASED_LABEL_FORCED
        _forced_p = set()
        for _hc in _h_set_base:
            for _p in H_BASED_LABEL_FORCED.get(_hc.replace('*','').strip(), []):
                _forced_p.add(_p)
        _missing_p = _forced_p - _label_p
        # P303+P361+P353 etikette varsa P302+P352'yi bastırır (aşındırıcı temas acil
        # yanıtı daha kapsamlı; p_code_service suppress kuralıyla tutarlı).
        if 'P303+P361+P353' in _label_p:
            _missing_p.discard('P302+P352')
        if _missing_p:
            warn("V023", "B2",
                 f"Etikette zorunlu P kodu(ları) eksik: {', '.join(sorted(_missing_p))}",
                 "CLP Annex IV §1.2 / KKDİK Madde 22(4) — H koduna bağlı zorunlu kodlar")
    except Exception:
        pass

    # ── V024: ADR sınıfı H koduna uygun mu ───────────────────────────────────
    _adr = sds_data.get('adr', {})
    _adr_class = str(_adr.get('class', '') or _adr.get('adr_class', '')).strip()
    if _adr_class and _adr_class not in ('-', ''):
        _expected_adr = set()
        for h in _h_set_base:
            ac = _H_TO_ADR_CLASS.get(h)
            if ac:
                _expected_adr.add(ac)
        if _expected_adr and _adr_class not in _expected_adr:
            warn("V024", "B14",
                 f"ADR sınıfı '{_adr_class}' H kodlarından beklenen sınıf(lar) ile uyuşmuyor: "
                 f"{', '.join(sorted(_expected_adr))}. ADR 2025 tablosunu kontrol edin.",
                 "ADR 2025 Bölüm 3.2 Tablo A / TMKTBY")

    # ── V025: SVHC bileşen bildirimi B15 ─────────────────────────────────────
    if components:
        try:
            from app.services.svhc_service import check_svhc_mixture
            _svhc_result = check_svhc_mixture(components)
            _svhc_above  = _svhc_result.get('above_threshold', [])
            _b15_text    = str(sds_data.get('section15', '') or sds_data.get('regulatory', '') or '')
            for sv in _svhc_above:
                sv_cas  = sv.get('cas', '')
                sv_name = sv.get('name', sv_cas)
                sv_conc = sv.get('concentration', 0)
                if sv_cas and sv_cas not in _b15_text and sv_name not in _b15_text:
                    error("V025", "B15",
                          f"SVHC madde '{sv_name}' ({sv_cas}) karışımda ≥{sv_conc}% konsantrasyonda "
                          f"ama B15'te bildirilmemiş. KKDİK Madde 33 / REACH Art.33 uyarınca "
                          f"zorunlu bildirim gereklidir.",
                          "KKDİK Madde 33 / REACH Art.33 / SEA Ek-2 §15")
        except Exception:
            pass

    # ── V026: OEL değerleri B8 doğruluğu ─────────────────────────────────────
    if components:
        try:
            import json, os
            _oel_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'tr_oel_limits.json')
            with open(_oel_path, encoding='utf-8') as _f:
                _oel_db = json.load(_f)
            _b8_text = str(sds_data.get('section8', '') or sds_data.get('exposure', '') or '')
            for comp in components:
                cas = (comp.get('cas') or '').strip()
                if not cas or cas not in _oel_db:
                    continue
                oel = _oel_db[cas]
                tw  = oel.get('tw_mgm3')
                name = comp.get('name') or cas
                if tw and _b8_text:
                    # B8 metninde bu CAS'ın TWA değeri var mı kontrol et
                    if cas not in _b8_text and name[:10] not in _b8_text:
                        warn("V026", "B8",
                             f"{name} ({cas}) için TR OEL limiti mevcut "
                             f"(TWA: {tw} mg/m³) ancak B8'de belirtilmemiş. "
                             f"KKDİK Ek-2 §8.1 uyarınca zorunludur.",
                             "KKDİK Ek-2 §8.1 / Mesleki Maruziyet Sınır Değerleri Yönetmeliği")
        except Exception:
            pass

    # ── V027: B16 ↔ B2.2 P-kodu tutarlılık kontrolü ─────────────────────────
    # classify_sds_p_codes 'mandatory' dediği + H_BASED_LABEL_FORCED'da olan
    # her P kodu B2.2 etiketinde de bulunmalı.
    try:
        _p_raw27 = sds_data.get('p_codes', {})
        if isinstance(_p_raw27, dict):
            _sds_classif = _p_raw27.get('sds', {})
            _sds_mandatory = set(
                _sds_classif.get('mandatory', []) if isinstance(_sds_classif, dict) else []
            )
            _label_sel27 = set(_p_raw27.get('label', {}).get('selected', []))
            _LABEL_EXCL  = {'P501', 'P101', 'P102'}

            from app.services.p_code_service import H_BASED_LABEL_FORCED as _HBLF
            _label_forced27 = set()
            for _hc27 in _h_set_base:
                for _p27 in _HBLF.get(_hc27.replace('*', '').strip(), []):
                    _label_forced27.add(_p27)

            # Mandatory (B16) + label-forced kesişimi → etikette OLMAK ZORUNDA
            _v027_missing = (_sds_mandatory & _label_forced27) - _label_sel27 - _LABEL_EXCL
            if _v027_missing:
                error("V027", "B2+B16",
                      f"B16'da 'Zorunlu' sınıflandırılan P kodu/ları B2.2 etiketinde eksik: "
                      f"{', '.join(sorted(_v027_missing))}. "
                      f"Sınıflandırma motoru (B16) ile etiket render'ı (B2.2) uyumsuz.",
                      "SEA Madde 24 / CLP Annex IV — zorunlu önlem ifadeleri")
    except Exception:
        pass

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
