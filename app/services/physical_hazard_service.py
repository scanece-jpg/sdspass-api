"""
Fiziksel Tehlike Servisi
========================
CLP Annex I — Fiziksel tehlike sınıflandırması

Kapsam (Ana):
  Flam. Liq. 1/2/3  (H224/H225/H226) → CLP Tablo 2.6
  Asp. Tox. 1        (H304)           → CLP Tablo 3.10

Kapsam (Ek — toggle):
  Ox. Liq. 1/2  (H271/H272)  → CLP Tablo 2.13
  Flam. Sol. 2  (H228)        → CLP Tablo 2.7

Veri Kaynakları:
  FP_DB   → Dahili parlama noktası veritabanı (33 madde)
  BP_DB   → Kaynama noktası veritabanı
  ASP_TOX_1_CAS → Asp.Tox.1 hidrokarbon listesi

Öncelik:
  1. Kullanıcı test verisi (mixture_flash_point, kinematic_viscosity)
  2. Bileşen FP_DB değeri
  3. Otomatik hesap

Asp. Tox. Notu:
  H304 uygulanabilmesi için karışım viskozitesi ≤ 20.5 mm²/s @ 40°C
  Viskozite test verisi girilmezse KDU doğrulaması gerekir.
"""
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field

# ─── VERİTABANLARI ───────────────────────────────────────────────────────────

# Parlama noktaları (°C) — sık kullanılan maddeler
# None = yanmaz / uygulanamaz
FLASH_POINT_DB: Dict[str, Optional[float]] = {
    # Alifatik hidrokarbonlar
    '110-54-3': -22,   # n-hexane
    '110-82-7': -18,   # cyclohexane
    '142-82-5': -4,    # n-heptane
    '111-65-9': 13,    # n-octane
    # Aromatikler
    '71-43-2':  -11,   # benzene
    '108-88-3': 4,     # toluene
    '1330-20-7': 27,   # xylene (karışım)
    '95-47-6':  17,    # o-xylene
    '106-42-3': 25,    # p-xylene
    '100-41-4': 21,    # ethylbenzene
    '95-63-6':  44,    # 1,2,4-trimethylbenzene
    # Ketonlar / Esterler
    '67-64-1':  -18,   # acetone
    '78-93-3':  -9,    # MEK (butanone)
    '108-10-1': 14,    # MIBK
    '78-59-1':  84,    # isophorone (>60 → kat yok)
    '141-78-6': -4,    # ethyl acetate
    '123-86-4': 22,    # n-butyl acetate
    # Alkoller
    '64-17-5':  13,    # ethanol
    '67-63-0':  12,    # IPA
    '71-23-8':  23,    # n-propanol
    '71-36-3':  29,    # n-butanol
    '78-83-1':  28,    # isobutanol
    '100-51-6': 93,    # benzyl alcohol (>60)
    # Glikoleterleri
    '111-76-2': 62,    # 2-butoxyethanol (Kat3 sınırı!)
    '112-34-5': 78,    # diethylene glycol monobutyl ether (>60)
    '107-98-2': 32,    # propylene glycol methyl ether
    # Petrol / Nafta
    '64742-47-8': 21,  # naphtha hydrotreated heavy
    '64742-48-9': -20, # naphtha hydrotreated light
    '64742-82-1': 61,  # white spirit / stoddard
    '64742-54-7': 220, # base oil heavy paraffinic (>60 → kat yok)
    '8052-41-3':  38,  # stoddard solvent
    # Yanmaz / Uygulanamaz
    '7732-18-5': None,  # water
    '7664-93-9': None,  # H2SO4
    '1310-73-2': None,  # NaOH
    '7681-52-9': None,  # NaOCl
    '13463-67-7': None, # TiO2 (katı)
    '67-66-3':   None,  # chloroform (yanmaz halojenli)
    '79-01-6':   None,  # trichloroethylene
}

# İlk kaynama noktaları (°C) — Kat1 tespiti için (BP ≤ 35°C)
BOILING_POINT_DB: Dict[str, float] = {
    '110-54-3': 69,    # n-hexane (BP>35 → Kat2 değil Kat1 olmaz)
    '110-82-7': 81,    # cyclohexane
    '67-64-1':  56,    # acetone
    '71-43-2':  80,    # benzene
    '78-93-3':  80,    # MEK
    '67-63-0':  82,    # IPA
    '64-17-5':  78,    # ethanol
    '71-23-8':  97,    # n-propanol
    '64742-48-9': 60,  # light naphtha (BP≈60 → Kat1 sınırı)
    # Gerçek Kat1 maddeler (BP ≤ 35°C):
    # Dietil eter: BP=34.6°C, FP=-45°C → H224
    '60-29-7':  35,    # diethyl ether
    '75-09-2':  40,    # DCM (yanmaz ama referans)
    '74-98-6':  -42,   # propane (gaz)
}

# Asp. Tox. 1 CAS listesi — hidrokarbon bazlı, düşük viskoziteli
# Kriter: kinematik viskozite ≤ 20.5 mm²/s @ 40°C
ASP_TOX_1_CAS: set = {
    '110-54-3', '110-82-7', '142-82-5', '111-65-9',   # alkanes C6-C8
    '71-43-2', '108-88-3', '1330-20-7', '95-47-6',    # aromatics
    '100-41-4', '95-63-6',                              # EB, TMB
    '64742-47-8', '64742-48-9', '64742-82-1',          # naphthas
    '64741-41-9', '64741-42-0', '64741-44-2',          # petroleum distillates
    '64741-45-3', '64741-47-5', '64741-48-6',
    '8052-41-3',                                        # stoddard solvent
    '64742-54-7',                                       # base oil (viskozite > 20.5 → H304 uygulanmaz!)
}

# Oksitleyici sıvılar — bilinen CAS
OXIDIZING_LIQ_CAS: Dict[str, Dict] = {
    '7722-84-1': {  # H2O2 — konsantrasyona göre kategori
        'thresholds': [(60, 'Ox. Liq. 1', 'H271'), (8, 'Ox. Liq. 2', 'H272')],
    },
    '7601-90-3': {'cat': 'Ox. Liq. 1', 'h': 'H271'},  # perchloric acid
    '7778-54-3': {'cat': 'Ox. Liq. 2', 'h': 'H272'},  # Ca hypochlorite solution
    '10049-04-4': {'cat': 'Ox. Liq. 2', 'h': 'H272'}, # ClO2 solution
}

# Oksitleyici katılar
OXIDIZING_SOL_CAS: Dict[str, Dict] = {
    '7778-54-3': {'cat': 'Ox. Sol. 1', 'h': 'H271'},  # Ca hypochlorite (katı)
    '7778-50-9': {'cat': 'Ox. Sol. 2', 'h': 'H272'},  # K dichromate
    '7789-09-5': {'cat': 'Ox. Sol. 2', 'h': 'H272'},  # ammonium dichromate
    '10588-01-9': {'cat': 'Ox. Sol. 2', 'h': 'H272'}, # sodium dichromate
    '7681-52-9': {'cat': None, 'h': None},             # NaOCl — sıvı formda değerlendirme
}


# ─── VERİ MODELLERİ ──────────────────────────────────────────────────────────

@dataclass
class TestData:
    """Kullanıcının girdiği test verileri — her bileşen için opsiyonel"""
    flash_point: Optional[float] = None        # °C
    boiling_point: Optional[float] = None      # °C
    kinematic_viscosity: Optional[float] = None # cSt @ 40°C
    ld50_oral: Optional[float] = None          # mg/kg
    particle_size: Optional[float] = None      # μm (TiO2 / toz için)


@dataclass
class PhysHazardResult:
    """Tek fiziksel tehlike sonucu"""
    h_code: str
    h_class: str
    category: int
    signal_word: str
    pictogram: str
    source: str                        # Hangi bileşenden / nasıl tetiklendi
    note: Optional[str] = None         # KDU notu / uyarı
    is_primary: bool = True            # Ana ekranda göster (True) / toggle'da (False)
    fp_value: Optional[float] = None   # Hesaplamada kullanılan FP
    total_pct: Optional[float] = None  # Asp.Tox. toplam %


@dataclass
class PhysHazardOutput:
    """Fiziksel tehlike hesabı çıktısı"""
    primary: List[PhysHazardResult] = field(default_factory=list)   # Flam.Liq + Asp.Tox
    extra: List[PhysHazardResult] = field(default_factory=list)     # Ox.Liq + Flam.Sol
    warnings: List[str] = field(default_factory=list)

    @property
    def all_results(self) -> List[PhysHazardResult]:
        return self.primary + self.extra

    @property
    def h_codes(self) -> List[str]:
        return [r.h_code for r in self.all_results]


# ─── YARDIMCI FONKSİYONLAR ───────────────────────────────────────────────────

def classify_flam_liq(fp: float, bp: Optional[float] = None) -> Optional[Dict]:
    """
    CLP Tablo 2.6 — Flammable Liquid kategorisi
    Returns: {'cat': int, 'h': str, 'signal': str, 'label': str} or None
    """
    if fp >= 60:
        return None  # Kat yok

    if fp < 23:
        bp_val = bp if bp is not None else 999
        if bp_val <= 35:
            return {'cat': 1, 'h': 'H224', 'signal': 'Danger',  'label': 'Flam. Liq. 1'}
        return     {'cat': 2, 'h': 'H225', 'signal': 'Danger',  'label': 'Flam. Liq. 2'}

    # 23 ≤ fp < 60
    return         {'cat': 3, 'h': 'H226', 'signal': 'Warning', 'label': 'Flam. Liq. 3'}


# ─── ANA HESAP FONKSİYONLARI ─────────────────────────────────────────────────

def calc_flam_liq(
    comps: List[Dict],
    mixture_form: str,
    user_fp_override: Optional[float] = None,
    comp_test_data: Optional[Dict[str, TestData]] = None,
) -> Optional[PhysHazardResult]:
    """
    CLP Tablo 2.6 — Yanıcı Sıvı sınıflandırması
    Kural: Karışımda en düşük FP'li bileşenin kategorisi uygulanır
    Konsantrasyon eşikleri: Kat1/2 → ≥%1, Kat3 → ≥%10
    """
    if mixture_form not in ('liquid', 'paste', 'aerosol'):
        return None

    # Kullanıcı ürün düzeyinde FP override
    if user_fp_override is not None:
        cls = classify_flam_liq(user_fp_override)
        if cls:
            return PhysHazardResult(
                h_code=cls['h'], h_class=cls['label'], category=cls['cat'],
                signal_word=cls['signal'], pictogram='GHS02',
                source=f"Kullanıcı girişi: {user_fp_override}°C",
                fp_value=user_fp_override, is_primary=True
            )
        return None

    # Bileşenlerden otomatik hesap
    best_result = None
    best_cat = 99

    for comp in comps:
        cas = comp.get('cas_no', '').strip()
        conc = comp.get('worst_case_conc', comp.get('concentration', 0)) or 0

        # Test verisi varsa önce onu kullan
        td = (comp_test_data or {}).get(cas)
        if td and td.flash_point is not None:
            fp = td.flash_point
            bp = td.boiling_point
        else:
            fp_raw = FLASH_POINT_DB.get(cas)
            if fp_raw is None:
                continue  # Yanmaz veya bilinmiyor
            fp = fp_raw
            bp = BOILING_POINT_DB.get(cas)

        cls = classify_flam_liq(fp, bp)
        if not cls:
            continue

        # Konsantrasyon eşiği (CLP Annex I Tablo 2.6.4)
        threshold = 1.0 if cls['cat'] <= 2 else 10.0
        if conc < threshold:
            continue

        if cls['cat'] < best_cat:
            best_cat = cls['cat']
            name = comp.get('name') or cas
            best_result = PhysHazardResult(
                h_code=cls['h'], h_class=cls['label'], category=cls['cat'],
                signal_word=cls['signal'], pictogram='GHS02',
                source=f"{name} (%{conc}, FP={fp}°C)",
                fp_value=fp, is_primary=True
            )

    return best_result


def calc_asp_tox(
    comps: List[Dict],
    mixture_form: str,
    comp_test_data: Optional[Dict[str, TestData]] = None,
) -> Optional[PhysHazardResult]:
    """
    CLP Tablo 3.10 — Aspirasyon Toksisitesi
    Kriter: Karışımda Asp.Tox.1 bileşen ≥ %10 VEYA
            Karışım viskozitesi ≤ 20.5 mm²/s @ 40°C
    """
    if mixture_form not in ('liquid', 'paste'):
        return None

    triggers = []
    total_asp_pct = 0.0
    high_viscosity_override = False  # Test verisiyle override

    for comp in comps:
        cas = comp.get('cas_no', '').strip()
        conc = comp.get('worst_case_conc', comp.get('concentration', 0)) or 0

        # Bileşen kendi sınıflandırmasında Asp.Tox.1 var mı?
        hazards = comp.get('hazards', [])
        has_asp_class = any(
            h.get('h_class') == 'Asp. Tox. 1' for h in hazards
        )
        in_asp_list = cas in ASP_TOX_1_CAS

        if not (has_asp_class or in_asp_list):
            continue

        # Viskozite test verisi varsa kontrol et
        td = (comp_test_data or {}).get(cas)
        if td and td.kinematic_viscosity is not None:
            if td.kinematic_viscosity > 20.5:
                high_viscosity_override = True
                continue  # Bu bileşen viskozite nedeniyle H304 uygulanmaz

        if conc > 0:
            triggers.append({'cas': cas, 'name': comp.get('name') or cas, 'conc': conc})
            total_asp_pct += conc

    if high_viscosity_override or total_asp_pct < 10:
        return None

    source = ', '.join(f"{t['name']} (%{t['conc']})" for t in triggers)
    note = (
        f"Toplam Asp.Tox.1 bileşeni: %{total_asp_pct:.1f}. "
        "H304 uygulanabilmesi için karışım viskozitesinin ≤20.5 mm²/s @ 40°C olması gerekir. "
        "KDU viskoziteyi doğrulamalıdır."
    )

    return PhysHazardResult(
        h_code='H304', h_class='Asp. Tox. 1', category=1,
        signal_word='Danger', pictogram='GHS08',
        source=source, note=note,
        total_pct=total_asp_pct, is_primary=True
    )


def calc_oxidizing(
    comps: List[Dict],
    mixture_form: str,
) -> Optional[PhysHazardResult]:
    """
    CLP Tablo 2.13/2.14 — Oksitleyici Sıvı / Katı
    """
    best_h = None
    best_label = None
    best_signal = None
    triggers = []

    for comp in comps:
        cas = comp.get('cas_no', '').strip()
        conc = comp.get('worst_case_conc', comp.get('concentration', 0)) or 0
        if conc < 1:
            continue

        # Sıvı oksitleyiciler
        if mixture_form in ('liquid', 'paste'):
            ox = OXIDIZING_LIQ_CAS.get(cas)
            if ox:
                if 'thresholds' in ox:
                    # H2O2 gibi konsantrasyona bağlı
                    for threshold, label, h in ox['thresholds']:
                        if conc >= threshold:
                            triggers.append({'cas': cas, 'conc': conc, 'h': h, 'label': label})
                            break
                elif ox.get('h'):
                    triggers.append({'cas': cas, 'conc': conc, 'h': ox['h'], 'label': ox['cat']})

        # Katı oksitleyiciler
        elif mixture_form == 'solid':
            ox = OXIDIZING_SOL_CAS.get(cas)
            if ox and ox.get('h'):
                triggers.append({'cas': cas, 'conc': conc, 'h': ox['h'], 'label': ox['cat']})

    if not triggers:
        return None

    # En yüksek kategori (H271 > H272)
    triggers.sort(key=lambda t: t['h'])
    best = triggers[0]

    return PhysHazardResult(
        h_code=best['h'], h_class=best['label'], category=1 if best['h'].endswith('1') else 2,
        signal_word='Danger' if best['h'].endswith('1') else 'Warning',
        pictogram='GHS03',
        source=', '.join(f"{t['cas']} %{t['conc']}" for t in triggers),
        is_primary=False  # Ek tehlike — toggle'da göster
    )


def calc_flam_sol(comps: List[Dict], mixture_form: str) -> Optional[PhysHazardResult]:
    """
    CLP Tablo 2.7 — Yanıcı Katı
    Bileşende Flam. Sol. 1/2 sınıflandırması varsa uygula
    """
    if mixture_form != 'solid':
        return None

    triggers = []
    for comp in comps:
        hazards = comp.get('hazards', [])
        if any(h.get('h_class') in ('Flam. Sol. 1', 'Flam. Sol. 2') for h in hazards):
            triggers.append(comp.get('name') or comp.get('cas_no', '?'))

    if not triggers:
        return None

    return PhysHazardResult(
        h_code='H228', h_class='Flam. Sol. 2', category=2,
        signal_word='Warning', pictogram='GHS02',
        source=', '.join(triggers),
        is_primary=False
    )


# ─── ANA ENTRY POINT ─────────────────────────────────────────────────────────

def calculate_physical_hazards(
    comps: List[Dict],
    mixture_form: str,
    user_fp_override: Optional[float] = None,
    comp_test_data: Optional[Dict[str, TestData]] = None,
) -> PhysHazardOutput:
    """
    Tüm fiziksel tehlikeleri hesapla.

    Args:
        comps: Bileşen listesi — her biri dict:
               {'cas_no', 'name', 'concentration'/'worst_case_conc', 'hazards'}
        mixture_form: 'liquid' | 'paste' | 'solid' | 'aerosol'
        user_fp_override: Kullanıcının girdiği ürün FP değeri (opsiyonel)
        comp_test_data: CAS → TestData eşleşmesi (opsiyonel)

    Returns:
        PhysHazardOutput (primary + extra + warnings)
    """
    output = PhysHazardOutput()

    # ── Flam. Liq. (ANA) ─────────────────────────────────────────
    flam = calc_flam_liq(comps, mixture_form, user_fp_override, comp_test_data)
    if flam:
        output.primary.append(flam)

    # ── Asp. Tox. 1 (ANA) ────────────────────────────────────────
    asp = calc_asp_tox(comps, mixture_form, comp_test_data)
    if asp:
        output.primary.append(asp)
        output.warnings.append(asp.note)

    # ── Ox. Liq./Sol. (EK) ───────────────────────────────────────
    ox = calc_oxidizing(comps, mixture_form)
    if ox:
        output.extra.append(ox)

    # ── Flam. Sol. (EK) ──────────────────────────────────────────
    fsol = calc_flam_sol(comps, mixture_form)
    if fsol:
        output.extra.append(fsol)

    return output
