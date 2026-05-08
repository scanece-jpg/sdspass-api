"""
Ekolojik Değerlendirme Servisi
================================
CLP + REACH — SDS Bölüm 12 hesaplamaları

Kapsam:
  12.1 Aquatic Toxicity    → H400/H410/H411/H412/H413 (M-faktör ile)
  12.2 Degradabilty        → Kullanıcı verisi / bilinen hızlı bozunan listesi
  12.3 Bioaccumulation     → log Kow ≥ 4 → biyobirikim potansiyeli
  12.5 PBT/vPvB            → REACH Annex XIII kriterleri
  EUH059                   → Ozon tabakasına zararlı

Aquatic Hesap Kuralları (SEA/CLP Annex I Tablo 4.1.2 — Karışımlar):
  Tüm toplama eşikleri %25'tir. 0.1%/M ve 1%/M dahil etme (inclusion) cut-off'larıdır.
  H400: Σ(Ci × M_acute)                              ≥ %25
  H410: Σ(Ci × M_chr)[Kronik1]                       ≥ %25
  H411: 10×Σ(Ci×M)[K1] + Σ(Ci)[K2]                  ≥ %25
  H412: 100×Σ(Ci×M)[K1] + 10×Σ(Ci)[K2] + Σ(Ci)[K3] ≥ %25
  H413: Σ(Ci)[tüm kronik]                             ≥ %25

Veri Kaynağı:
  Önce Annex VI M-faktörü, yoksa varsayılan M=1
  Kullanıcı EC50/LC50 girerse → M-faktör override hesaplanır
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
import math


# ─── PBT/vPvB BİLİNEN MADDELER ──────────────────────────────────────────────
# ECHA SVHC listesinden seçilmiş PBT maddeler
PBT_CAS = {
    '57-74-9',   # chlordane
    '319-84-6',  # alpha-HCH
    '319-85-7',  # beta-HCH
    '58-89-9',   # lindane (gamma-HCH)
    '72-54-8',   # DDD
    '50-29-3',   # DDT
    '76-44-8',   # heptachlor
    '118-74-1',  # hexachlorobenzene
    '87-68-3',   # hexachlorobutadiene
    '757-58-4',  # hexaethyl tetraphosphate
    '36355-01-8',# hexabromobiphenyl
    '67774-32-7',# polychlorinated biphenyls (PCB)
    # ECHA SVHC PBT — KKDİK Ek-17 uyarınca ek maddeler
    '85535-84-8',# SCCP (kısa zincirli klorlu parafinler) — PBT/vPvB
    '68920-70-7',# MCCP (orta zincirli klorlu parafinler, CAS aralığı)
    '72629-94-8',# decabromodiphenyl ether (deca-BDE)
    '1163-19-5', # decabromodiphenyl oxide
}

VPVB_CAS = {
    '25637-99-4', # hexabromocyclododecane (HBCD)
    '3194-55-6',  # HBCD isomers
    '36483-57-5', # HBCD
}

# Ozon tabakasına zararlı (EUH059 / H420)
OZONE_CAS = {
    '75-69-4',   # CFC-11
    '75-71-8',   # CFC-12
    '76-13-1',   # CFC-113
    '76-14-2',   # CFC-114
    '76-15-3',   # CFC-115
    '75-72-9',   # CFC-13
    '354-23-4',  # CFC-123
    '75-63-8',   # halon-1301
    '353-59-3',  # halon-1211
    '74-83-9',   # methyl bromide
    '74-87-3',   # methyl chloride
    '56-23-5',   # carbon tetrachloride
    '67-66-3',   # chloroform (trichloromethane)
    '79-01-6',   # trichloroethylene
}

# Hızlı biyobozunur (readily biodegradable) — OECD 301 geçen
READILY_BIODEGRADABLE_CAS = {
    '64-17-5',   # ethanol
    '67-63-0',   # IPA
    '71-23-8',   # n-propanol
    '71-36-3',   # n-butanol
    '67-64-1',   # acetone
    '78-93-3',   # MEK
    '141-78-6',  # ethyl acetate
    '7732-18-5', # water
    '57-55-6',   # propylene glycol
    '56-81-5',   # glycerol
    '77-92-9',   # citric acid
    '64-19-7',   # acetic acid
    '79-09-4',   # propionic acid
}

# Zor biyobozunur (persistent)
PERSISTENT_CAS = {
    '1330-20-7', # xylene (moderate)
    '108-88-3',  # toluene (moderate)
    '110-54-3',  # n-hexane (moderate)
    '71-43-2',   # benzene
    '100-41-4',  # ethylbenzene
}

# log Kow veritabanı (tahmini)
LOG_KOW_DB: Dict[str, float] = {
    '110-54-3': 3.29,  # n-hexane
    '110-82-7': 3.44,  # cyclohexane
    '108-88-3': 2.73,  # toluene
    '1330-20-7': 3.12, # xylene
    '71-43-2':  2.13,  # benzene
    '100-41-4': 3.15,  # ethylbenzene
    '64-17-5':  -0.31, # ethanol
    '67-63-0':  0.05,  # IPA
    '71-36-3':  0.88,  # n-butanol
    '67-64-1': -0.24,  # acetone
    '111-76-2': 0.83,  # 2-butoxyethanol
    '50-00-0': 0.35,   # formaldehyde
    '7681-52-9': -3.4, # NaOCl
    '7732-18-5': -1.38,# water
    '64742-54-7': 7.0, # base oil (tahmini)
    '64742-47-8': 4.5, # naphtha (tahmini)
}


# ─── VERİ MODELLERİ ──────────────────────────────────────────────────────────

@dataclass
class EcoTestData:
    """Kullanıcının girdiği ekolojik test verileri"""
    ec50_algae: Optional[float] = None      # mg/L — LC50/EC50 alg
    lc50_fish: Optional[float] = None       # mg/L — LC50 balık 96h
    ec50_daphnia: Optional[float] = None    # mg/L — EC50 daphnia 48h
    noec_chronic: Optional[float] = None    # mg/L — NOEC kronik
    log_kow: Optional[float] = None         # log Kow (ölçülen)
    half_life_water: Optional[float] = None # gün — suda yarı ömür
    half_life_soil: Optional[float] = None  # gün — toprakta yarı ömür
    bcf: Optional[float] = None             # L/kg — biyokonsantrasyon faktörü
    log_koc: Optional[float] = None         # Koc — toprak adsorpsiyon katsayısı


@dataclass
class AquaticResult:
    h_code: str
    h_class: str
    signal: str
    sum_value: float
    formula: str
    note: Optional[str] = None
    component_details: list = None  # Her bileşen için M faktör detayı


@dataclass
class PBTResult:
    is_pbt: bool
    is_vpvb: bool
    p_score: str    # Persistent: Yes/No/Uncertain
    b_score: str    # Bioaccumulative: Yes/No/Uncertain
    t_score: str    # Toxic: Yes/No/Uncertain
    notes: List[str] = field(default_factory=list)


@dataclass
class EcoOutput:
    aquatic: Optional[AquaticResult] = None
    pbt_results: List[Dict] = field(default_factory=list)
    ozone_hazard: List[str] = field(default_factory=list)
    biodegradability: Dict = field(default_factory=dict)
    bioaccumulation: Dict = field(default_factory=dict)
    soil_mobility: Dict = field(default_factory=dict)
    endocrine_disruptors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    sds_section_12: Dict = field(default_factory=dict)


# ─── YARDIMCI FONKSİYONLAR ───────────────────────────────────────────────────

def _ec50_to_m_factor(ec50_mg_l: float) -> int:
    """
    EC50/LC50 değerinden M-faktör hesapla (CLP Tablo 4.1.3 Not 2)
    """
    if ec50_mg_l <= 0.01:   return 1000
    if ec50_mg_l <= 0.1:    return 100
    if ec50_mg_l <= 1.0:    return 10
    return 1


def _classify_log_kow(log_kow: float) -> str:
    """Log Kow'dan biyobirikim sınıfı"""
    if log_kow >= 5.0:   return "Yüksek (BCF ≥ 2000 beklenir, B kriteri)"
    if log_kow >= 4.0:   return "Orta-Yüksek (BCF ≥ 500 olabilir)"
    if log_kow >= 3.0:   return "Orta (izleme önerilir)"
    return "Düşük (biyobirikim potansiyeli sınırlı)"


# ─── ANA HESAPLAR ─────────────────────────────────────────────────────────────

def calculate_aquatic(
    comp_list: List[Dict],
    eco_test_data: Optional[Dict[str, EcoTestData]] = None
) -> Optional[AquaticResult]:
    """
    SEA/CLP Annex I Tablo 4.1.2 — Aquatic toxicity sınıflandırması (Karışımlar)

    Toplama formülü eşikleri (Tablo 4.1.2):
      H400: Σ(Ci × M_acute)               ≥ %25   → Aquatic Acute 1
      H410: Σ(Ci × M_chronic) [Kronik 1]  ≥ %25   → Aquatic Chronic 1
      H411: 10×Σ(Ci×M)[Kronik1] + Σ[K2]  ≥ %25   → Aquatic Chronic 2
      H412: 100×Σ[K1×M]+10×Σ[K2]+Σ[K3]  ≥ %25   → Aquatic Chronic 3

    Not: 0.1%/M = hesaplamaya DAHİL ETME eşiği (inclusion cut-off), sınıflandırma
    tetikleyicisi değildir. Bileşen bu eşiğin üzerindeyse formüle katılır.
    """
    sum_acute_m   = 0.0
    sum_chronic1_m = 0.0   # Σ(Ci × Mi_chronic) — sadece Kronik 1 bileşenler
    sum_chronic2   = 0.0   # Σ(Ci) — Kronik 2 bileşenler (M-faktörsüz)
    sum_chronic3   = 0.0   # Σ(Ci) — Kronik 3 bileşenler
    sum_chronic_plain = 0.0  # H412/H413 için düz toplam (M-faktörsüz)
    detail_parts = []
    comp_m_details = []

    for comp in comp_list:
        cas = comp.get('cas_no', comp.get('cas', '')).strip()
        conc = float(comp.get('worst_case_conc', comp.get('conc', 0)) or 0)
        hazards = comp.get('hazards', [])

        # M-faktörler — önce veritabanı
        m_acute = comp.get('m_factors', {}).get('acute', 1) if comp.get('m_factors') else 1
        m_chronic = comp.get('m_factors', {}).get('chronic', 1) if comp.get('m_factors') else 1

        # Kullanıcı EC50 override
        td = (eco_test_data or {}).get(cas)
        if td:
            if td.ec50_algae:
                m_acute = max(m_acute, _ec50_to_m_factor(td.ec50_algae))
            if td.lc50_fish:
                m_acute = max(m_acute, _ec50_to_m_factor(td.lc50_fish))
            if td.ec50_daphnia:
                m_acute = max(m_acute, _ec50_to_m_factor(td.ec50_daphnia))
            if td.noec_chronic:
                m_chronic = max(m_chronic, _ec50_to_m_factor(td.noec_chronic))

        # H410 (Aquatic Chronic 1) varsa H400 (Aquatic Acute 1) atla:
        # H410 zaten hem akut hem kronik katkıyı kapsar (çift sayım ve çift tablo satırı önleme)
        haz_classes = {h.get('h_class', '').replace('*', '').strip() for h in hazards}
        has_h410 = 'Aquatic Chronic 1' in haz_classes

        for haz in hazards:
            hc = haz.get('h_class', '').replace('*', '').strip()

            if hc == 'Aquatic Acute 1':
                if has_h410:
                    continue  # H410 varsa H400 işleme — H410 bloğu akut+kronik ikisini de karşılar
                # Dahil etme eşiği: ≥ %0.1 / M_akut  (SEA Ek-1 §4.1.3.5.5)
                if conc >= (0.1 / max(m_acute, 1)):
                    sum_acute_m += (conc * m_acute) / 100
                    detail_parts.append(f"{cas} Acute M={m_acute}")
                    comp_m_details.append({
                        'cas': cas, 'name': comp.get('name',''),
                        'name_tr': comp.get('name_tr',''),
                        'conc': conc,
                        'm_acute': m_acute, 'm_chronic': m_chronic,
                        'h_class': 'Aquatic Acute 1',
                    })

            elif hc == 'Aquatic Chronic 1':
                # Dahil etme eşiği: ≥ %0.1 / M_kronik  (SEA Ek-1 §4.1.3.5.5)
                if conc >= (0.1 / max(m_chronic, 1)):
                    # Kronik 1 hem akut hem kronik hesaba girer (H410 = Kronik 1 + Akut 1)
                    sum_acute_m    += (conc * m_acute)   / 100
                    sum_chronic1_m += (conc * m_chronic) / 100
                    sum_chronic_plain += conc / 100
                    detail_parts.append(f"{cas} Chronic1 M_akut={m_acute} M_kronik={m_chronic}")
                    comp_m_details.append({
                        'cas': cas, 'name': comp.get('name',''),
                        'name_tr': comp.get('name_tr',''),
                        'conc': conc,
                        'm_acute': m_acute, 'm_chronic': m_chronic,
                        'h_class': hc,
                    })

            elif hc == 'Aquatic Chronic 2':
                # Dahil etme eşiği: ≥ %1.0 (düz — M-faktörsüz)  (SEA Ek-1 §4.1.3.5.5)
                if conc >= 1.0:
                    sum_chronic2 += conc / 100
                    sum_chronic_plain += conc / 100
                    comp_m_details.append({
                        'cas': cas, 'name': comp.get('name',''),
                        'name_tr': comp.get('name_tr',''),
                        'conc': conc,
                        'm_acute': m_acute, 'm_chronic': m_chronic,
                        'h_class': hc,
                    })

            elif hc in ('Aquatic Chronic 3', 'Aquatic Chronic 4'):
                # Dahil etme eşiği: ≥ %1.0 (düz)  (SEA Ek-1 §4.1.3.5.5)
                if conc >= 1.0:
                    sum_chronic3 += conc / 100
                    sum_chronic_plain += conc / 100
                    comp_m_details.append({
                        'cas': cas, 'name': comp.get('name',''),
                        'name_tr': comp.get('name_tr',''),
                        'conc': conc,
                        'm_acute': 1, 'm_chronic': 1,
                        'h_class': hc,
                    })

    # ── SEA/CLP Tablo 4.1.2: Toplama Formülü Sınıflandırması ─────────────────────
    # Kaynak: CLP Annex I §4.1.3.5.5 — tüm eşikler %25'tir.
    # Algoritma: Kronik sınıflandırma ÖNCE kontrol edilir.
    # H410 (Kronik 1) varsa H400 (Akut 1) etiket'ten elenir — Baskınlık kuralı.
    # H410 yoksa, H400 bağımsız olarak atanır.

    # ── Kronik Sınıflandırma (öncelik sırası: H410 > H411 > H412 > H413) ────────

    # H410: Σ(Ci × M_kronik)[Kronik1] ≥ %25
    if sum_chronic1_m >= 0.25:
        return AquaticResult(
            h_code='H410', h_class='Aquatic Chronic 1', signal='Warning',
            sum_value=sum_chronic1_m,
            formula=f"Σ(Ci×M_kr)[K1]/100 = {sum_chronic1_m:.4f} ≥ 0.25 (Tablo 4.1.2)",
            note="H410 atandı → H400 etiket'ten elendi (baskınlık kuralı)",
            component_details=comp_m_details,
        )

    # H411: 10×Σ(Ci×M)[K1] + Σ(Ci)[K2] ≥ %25
    h411_sum = 10 * sum_chronic1_m + sum_chronic2
    if h411_sum >= 0.25:
        return AquaticResult(
            h_code='H411', h_class='Aquatic Chronic 2', signal='Warning',
            sum_value=h411_sum,
            formula=f"10×Σ[K1×M]+Σ[K2] = {h411_sum:.4f} ≥ 0.25 (Tablo 4.1.2)",
            component_details=comp_m_details,
        )

    # H412: 100×Σ[K1×M] + 10×Σ[K2] + Σ[K3] ≥ %25
    h412_sum = 100 * sum_chronic1_m + 10 * sum_chronic2 + sum_chronic3
    if h412_sum >= 0.25:
        return AquaticResult(
            h_code='H412', h_class='Aquatic Chronic 3', signal='Warning',
            sum_value=h412_sum,
            formula=f"100×Σ[K1×M]+10×Σ[K2]+Σ[K3] = {h412_sum:.4f} ≥ 0.25 (Tablo 4.1.2)",
            component_details=comp_m_details,
        )

    # H413: Σ(Ci tüm kronik)/100 ≥ %25 (M-faktörsüz düz toplam)
    if sum_chronic_plain >= 0.25:
        return AquaticResult(
            h_code='H413', h_class='Aquatic Chronic 4', signal='Warning',
            sum_value=sum_chronic_plain,
            formula=f"Σ(Ci tüm kronik)/100 = {sum_chronic_plain:.4f} ≥ 0.25 (Tablo 4.1.2)",
            component_details=comp_m_details,
        )

    # ── Akut Sınıflandırma — sadece kronik yoksa (H410 baskınlık kuralı) ────────
    # H400: Σ(Ci × M_akut) ≥ %25
    if sum_acute_m >= 0.25:
        return AquaticResult(
            h_code='H400', h_class='Aquatic Acute 1', signal='Warning',
            sum_value=sum_acute_m,
            formula=f"Σ(Ci×M_akut)/100 = {sum_acute_m:.4f} ≥ 0.25 (Tablo 4.1.1)",
            component_details=comp_m_details,
        )

    return None


def assess_pbt(
    comp_list: List[Dict],
    eco_test_data: Optional[Dict[str, EcoTestData]] = None
) -> List[Dict]:
    """
    REACH Annex XIII — PBT/vPvB değerlendirmesi bileşen bazında
    
    P kriteri: t1/2 > 60 gün su, > 180 gün toprak
    B kriteri: BCF > 2000 L/kg veya log Kow > 4.5
    T kriteri: H400/H410/H411 veya CMR
    """
    results = []

    for comp in comp_list:
        cas = comp.get('cas_no', comp.get('cas', '')).strip()
        conc = float(comp.get('worst_case_conc', comp.get('conc', 0)) or 0)
        if conc < 0.1:
            continue  # < %0.1 SDS'de belirtilmez

        name = comp.get('name') or cas
        td = (eco_test_data or {}).get(cas)
        hazards = comp.get('hazards', [])
        h_codes = [h.get('h_code','').replace('*','').strip() for h in hazards]

        notes = []
        p_result = "Belirsiz"
        b_result = "Belirsiz"
        t_result = "Belirsiz"

        # Bilinen PBT/vPvB listesi
        if cas in PBT_CAS:
            p_result = b_result = t_result = "Evet"
            notes.append("ECHA SVHC listesinde PBT olarak tanımlanmış")
        if cas in VPVB_CAS:
            p_result = b_result = "Evet (vPvB)"
            notes.append("ECHA SVHC listesinde vPvB olarak tanımlanmış")

        # P — Kalıcılık
        if cas in READILY_BIODEGRADABLE_CAS:
            p_result = "Hayır (hızlı bozunur)"
        elif cas in PERSISTENT_CAS:
            p_result = "Olası (orta kalıcılık)"
            notes.append("Orta kalıcı madde — yarı ömür testi önerilir")

        if td:
            if td.half_life_water is not None:
                if td.half_life_water > 60:
                    p_result = f"Evet (t½ su={td.half_life_water}g > 60g)"
                else:
                    p_result = f"Hayır (t½ su={td.half_life_water}g ≤ 60g)"
            if td.half_life_soil is not None:
                if td.half_life_soil > 180:
                    p_result = f"Evet (t½ toprak={td.half_life_soil}g > 180g)"

        # B — Biyobirikim
        log_kow = LOG_KOW_DB.get(cas)
        if td and td.log_kow is not None:
            log_kow = td.log_kow  # Kullanıcı verisi öncelikli
        if td and td.bcf is not None:
            if td.bcf > 2000:
                b_result = f"Evet (BCF={td.bcf:.0f} > 2000)"
            else:
                b_result = f"Hayır (BCF={td.bcf:.0f} ≤ 2000)"
        elif log_kow is not None:
            if log_kow >= 4.5:
                b_result = f"Olası (log Kow={log_kow:.2f} ≥ 4.5)"
                notes.append(f"log Kow={log_kow:.2f} — BCF testi önerilir")
            elif log_kow >= 4.0:
                b_result = f"Belirsiz (log Kow={log_kow:.2f})"
            else:
                b_result = f"Hayır (log Kow={log_kow:.2f} < 4.0)"

        # T — Toksisite
        toxic_h = {'H400','H410','H411','H331','H311','H301',
                   'H351','H350','H341','H340','H361','H360'}
        cmr_h = {'H340','H341','H350','H350i','H351','H360','H360D',
                 'H360F','H361','H361d','H361f'}
        if any(h in toxic_h for h in h_codes):
            t_result = "Evet"
        elif any(h in cmr_h for h in h_codes):
            t_result = "Evet (CMR)"

        is_pbt = (p_result.startswith("Evet") and
                  (b_result.startswith("Evet") or b_result.startswith("Olası")) and
                  t_result.startswith("Evet"))
        is_vpvb = cas in VPVB_CAS

        results.append({
            'cas': cas,
            'name': name,
            'conc': conc,
            'P': p_result,
            'B': b_result,
            'T': t_result,
            'is_pbt': is_pbt,
            'is_vpvb': is_vpvb,
            'log_kow': log_kow,
            'notes': notes,
        })

    return results


def check_ozone(comp_list: List[Dict]) -> List[str]:
    """EUH059 / H420 — Ozon tabakasına zararlı CAS listesi"""
    found = []
    for comp in comp_list:
        cas = comp.get('cas_no', comp.get('cas', '')).strip()
        if cas in OZONE_CAS:
            found.append(comp.get('name') or cas)
    return found


def assess_biodegradability(
    comp_list: List[Dict],
    eco_test_data: Optional[Dict[str, EcoTestData]] = None
) -> Dict:
    """
    Karışım biyobozunurluğu değerlendirmesi
    Ağırlıklı ortalama yaklaşımı — SDS Bölüm 12.2 için
    """
    readily_pct = 0.0
    persistent_pct = 0.0
    unknown_pct = 0.0
    total = 0.0

    for comp in comp_list:
        cas = comp.get('cas_no', comp.get('cas', '')).strip()
        conc = float(comp.get('worst_case_conc', comp.get('conc', 0)) or 0)
        if conc <= 0:
            continue
        total += conc

        td = (eco_test_data or {}).get(cas)
        if td and td.half_life_water is not None:
            if td.half_life_water <= 40:
                readily_pct += conc
            else:
                persistent_pct += conc
        elif cas in READILY_BIODEGRADABLE_CAS:
            readily_pct += conc
        elif cas in PERSISTENT_CAS:
            persistent_pct += conc
        else:
            unknown_pct += conc

    if total <= 0:
        return {'assessment': 'Veri yetersiz', 'readily_pct': 0}

    r_ratio = readily_pct / total * 100
    p_ratio = persistent_pct / total * 100

    if r_ratio > 70:
        assessment = 'Büyük ölçüde biyobozunur (>%70 hızlı bozunan bileşen)'
    elif p_ratio > 30:
        assessment = 'Kalıcılık endişesi (>%30 zor bozunan bileşen)'
    else:
        assessment = f'Karışık — hızlı bozunan %{r_ratio:.0f}, kalıcı %{p_ratio:.0f}, bilinmeyen %{unknown_pct/total*100:.0f}'

    return {
        'assessment': assessment,
        'readily_pct': round(r_ratio, 1),
        'persistent_pct': round(p_ratio, 1),
        'unknown_pct': round(unknown_pct / total * 100, 1),
    }



# ─── EK VERİTABANLARI ────────────────────────────────────────────────────────

# H420 — Ozon tabakasına zararlı (CLP Annex VI 2023)
H420_CAS = OZONE_CAS  # Aynı liste, farklı H kodu

# Endokrin bozucu (ECHA ED Assessment 2023)
ENDOCRINE_CAS = {
    '80-05-7',   # bisphenol A (BPA)
    '84-66-2',   # diethyl phthalate (DEP)
    '117-81-7',  # DEHP
    '85-68-7',   # BBP
    '84-74-2',   # DBP
    '57-63-6',   # ethinyl estradiol
    '50-28-2',   # estradiol
    '8007-45-2', # coal tar
    '1336-36-3', # PCB (total)
}

# Toprak/sediment toksisitesi — bilinen EC50 (mg/kg kuru ağırlık)
SOIL_EC50_DB: Dict[str, float] = {
    '71-43-2':  4.3,    # benzene — solucan EC50
    '108-88-3': 200.0,  # toluene
    '1330-20-7':10.0,   # xylene
    '7681-52-9': 1.2,   # NaOCl (soil)
    '7664-93-9': 0.8,   # H2SO4
}

# log Koc veritabanı (ölçülen veya literatür)
LOG_KOC_DB: Dict[str, float] = {
    '110-54-3': 2.80,   # n-hexane
    '71-43-2':  1.77,   # benzene
    '108-88-3': 2.25,   # toluene
    '1330-20-7': 2.54,  # xylene
    '100-41-4': 2.69,   # ethylbenzene
    '67-64-1':  0.20,   # acetone
    '64-17-5':  0.00,   # ethanol
}


def estimate_log_koc(log_kow: float) -> float:
    """
    Karickhoff korelasyonu: log Koc ≈ 0.81 × log Kow + 0.10
    Organik maddelerde geçerli, iyonik bileşikler için güvenilmez
    """
    return round(0.81 * log_kow + 0.10, 2)


def assess_soil_mobility(
    comp_list: List[Dict],
    eco_test_data: Optional[Dict[str, Any]] = None
) -> Dict:
    """
    SDS 12.4 — Toprakta hareketlilik
    log Koc < 2 → yüksek hareketlilik (yıkanma riski)
    log Koc 2-4 → orta
    log Koc > 4 → düşük hareketlilik (toprakta tutunur)
    """
    results = []
    for comp in comp_list:
        cas = comp.get('cas_no', comp.get('cas', '')).strip()
        conc = float(comp.get('worst_case_conc', comp.get('conc', 0)) or 0)
        if conc < 0.1:
            continue
        name    = comp.get('name') or cas
        name_tr = comp.get('name_tr') or name   # TR SDS için Türkçe ad
        td = (eco_test_data or {}).get(cas)

        log_koc = LOG_KOC_DB.get(cas)
        if td and hasattr(td, 'log_koc') and td.log_koc is not None:
            log_koc = td.log_koc
        elif log_koc is None:
            kow = LOG_KOW_DB.get(cas)
            if td and hasattr(td, 'log_kow') and td.log_kow:
                kow = td.log_kow
            if kow is not None:
                log_koc = estimate_log_koc(kow)

        if log_koc is None:
            results.append({'cas': cas, 'name': name, 'name_tr': name_tr,
                            'conc': conc, 'log_koc': None, 'mobility': 'Bilinmiyor'})
            continue

        if log_koc < 2.0:
            mobility = f"Yüksek (log Koc={log_koc:.2f} < 2 — yeraltı suyu riski)"
        elif log_koc < 4.0:
            mobility = f"Orta (log Koc={log_koc:.2f})"
        else:
            mobility = f"Düşük (log Koc={log_koc:.2f} > 4 — toprakta tutunur)"

        # Toprak toksisitesi
        soil_ec50 = SOIL_EC50_DB.get(cas)
        results.append({'cas': cas, 'name': name, 'name_tr': name_tr,
                        'conc': conc, 'log_koc': log_koc, 'mobility': mobility,
                        'soil_ec50': soil_ec50})

    return {'components': results}


def check_endocrine_disruptors(comp_list: List[Dict]) -> List[str]:
    """
    SDS 12.6 — Endokrin bozucu madde tespiti
    ECHA ED Assessment listesi (2023)
    """
    found = []
    for comp in comp_list:
        cas = comp.get('cas_no', comp.get('cas', '')).strip()
        if cas in ENDOCRINE_CAS:
            found.append(comp.get('name') or cas)
    return found


# ─── ANA ENTRY POINT ─────────────────────────────────────────────────────────

def calculate_ecological(
    comp_list: List[Dict],
    eco_test_data: Optional[Dict[str, EcoTestData]] = None
) -> EcoOutput:
    """
    Tam ekolojik değerlendirme — SDS Bölüm 12
    """
    out = EcoOutput()

    # 12.1 Aquatic
    out.aquatic = calculate_aquatic(comp_list, eco_test_data)

    # 12.2 Degradability
    out.biodegradability = assess_biodegradability(comp_list, eco_test_data)

    # 12.3 Bioaccumulation — log Kow özeti
    kow_data = []
    for comp in comp_list:
        cas = comp.get('cas_no', comp.get('cas', '')).strip()
        conc = float(comp.get('worst_case_conc', comp.get('conc', 0)) or 0)
        if conc < 0.1:
            continue
        td = (eco_test_data or {}).get(cas)
        kow = td.log_kow if td and td.log_kow else LOG_KOW_DB.get(cas)
        if kow is not None:
            kow_data.append({
                'cas': cas,
                'name': comp.get('name') or cas,
                'conc': conc,
                'log_kow': kow,
                'classification': _classify_log_kow(kow)
            })
    out.bioaccumulation = {
        'components': kow_data,
        'high_kow': [k for k in kow_data if k['log_kow'] >= 4.0]
    }

    # 12.5 PBT/vPvB
    out.pbt_results = assess_pbt(comp_list, eco_test_data)

    # EUH059 / Ozon
    out.ozone_hazard = check_ozone(comp_list)
    if out.ozone_hazard:
        out.warnings.append(
            f"EUH059 / H420: Ozon tabakasına zararlı bileşen tespit edildi: "
            f"{', '.join(out.ozone_hazard)}"
        )

    # 12.6 Uyarılar
    if out.bioaccumulation['high_kow']:
        names = ', '.join(c['name'] for c in out.bioaccumulation['high_kow'])
        out.warnings.append(
            f"Biyobirikim potansiyeli: {names} — log Kow ≥ 4.0. BCF testi önerilir."
        )

    pbt_flagged = [p for p in out.pbt_results if p['is_pbt'] or p['is_vpvb']]
    if pbt_flagged:
        names = ', '.join(p['name'] for p in pbt_flagged)
        out.warnings.append(f"PBT/vPvB: {names} — SVHC listesinde veya kriterleri karşılıyor.")

    # SDS Bölüm 12 özeti
    out.sds_section_12 = {
        '12.1': out.aquatic.h_code if out.aquatic else 'Sınıflandırma yok',
        '12.2': out.biodegradability.get('assessment', 'Bilinmiyor'),
        '12.3': f"{len(out.bioaccumulation['high_kow'])} bileşende yüksek log Kow" if out.bioaccumulation['high_kow'] else 'Biyobirikim potansiyeli düşük',
        '12.4': 'Manuel değerlendirme gerekli',
        '12.5': f"{len(pbt_flagged)} PBT/vPvB bileşen" if pbt_flagged else 'PBT/vPvB değil',
        '12.6': 'EUH059 — ozon' if out.ozone_hazard else 'Endokrin bozucu: ECHA SVHC listesini kontrol edin',
    }

    # 12.4 Toprak hareketliliği
    out.sds_section_12['12.4_detail'] = assess_soil_mobility(comp_list, eco_test_data)

    # 12.6 Endokrin bozucu
    ed_found = check_endocrine_disruptors(comp_list)
    if ed_found:
        out.warnings.append(
            f"Endokrin bozucu (ECHA ED 2023): {', '.join(ed_found)} — SDS 12.6'da belirtilmeli."
        )
    out.sds_section_12['12.6_ed'] = ed_found

    # H420 — Ozon sınıflandırması (H kodu)
    ozone_h420 = [c.get('name') or c.get('cas_no', c.get('cas',''))
                  for c in comp_list
                  if c.get('cas_no', c.get('cas','')) in H420_CAS]
    if ozone_h420:
        out.sds_section_12['H420'] = ozone_h420

    return out
