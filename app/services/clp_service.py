
# ─── SDSPASS CLP Hesaplayıcı (dict tabanlı, ORM bağımsız) ───────────────────
# CLP Annex I (KKDİK Ek-2) cut-off ve sınıflandırma kuralları

# Annex I Tablo — h_class → {h_code, cutoff_pct, signal, category}
CLP_CUTOFFS_DICT = {
    # 3.1 Akut Toksisite
    "Acute Tox. 1": {"h":"H300","cutoff":1.0,"signal":"Danger"},
    "Acute Tox. 2": {"h":"H300","cutoff":1.0,"signal":"Danger"},
    "Acute Tox. 3": {"h":"H301","cutoff":1.0,"signal":"Danger"},
    "Acute Tox. 4": {"h":"H302","cutoff":5.0,"signal":"Warning"},
    # inhalasyon
    "Acute Tox. 1 *": {"h":"H330","cutoff":1.0,"signal":"Danger"},
    "Acute Tox. 2 *": {"h":"H330","cutoff":1.0,"signal":"Danger"},
    "Acute Tox. 3 *": {"h":"H331","cutoff":1.0,"signal":"Danger"},
    "Acute Tox. 4 *": {"h":"H332","cutoff":5.0,"signal":"Warning"},
    # 3.2 Cilt
    "Skin Corr. 1":  {"h":"H314","cutoff":1.0, "signal":"Danger"},
    "Skin Corr. 1A": {"h":"H314","cutoff":1.0, "signal":"Danger"},
    "Skin Corr. 1B": {"h":"H314","cutoff":1.0, "signal":"Danger"},
    "Skin Corr. 1C": {"h":"H314","cutoff":1.0, "signal":"Danger"},
    "Skin Irrit. 2": {"h":"H315","cutoff":10.0,"signal":"Warning"},
    # 3.3 Göz
    "Eye Dam. 1":    {"h":"H318","cutoff":1.0, "signal":"Danger"},
    "Eye Irrit. 2":  {"h":"H319","cutoff":10.0,"signal":"Warning"},
    # 3.4 Duyarlılaştırma
    "Skin Sens. 1":  {"h":"H317","cutoff":1.0, "signal":"Warning"},
    "Skin Sens. 1A": {"h":"H317","cutoff":0.1, "signal":"Warning"},
    "Skin Sens. 1B": {"h":"H317","cutoff":1.0, "signal":"Warning"},
    "Resp. Sens. 1": {"h":"H334","cutoff":0.1, "signal":"Danger"},
    "Resp. Sens. 1A":{"h":"H334","cutoff":0.1, "signal":"Danger"},
    "Resp. Sens. 1B":{"h":"H334","cutoff":0.1, "signal":"Danger"},
    # 3.5 Mutajenez
    "Muta. 1A": {"h":"H340","cutoff":0.1,"signal":"Danger"},
    "Muta. 1B": {"h":"H340","cutoff":0.1,"signal":"Danger"},
    "Muta. 2":  {"h":"H341","cutoff":1.0,"signal":"Warning"},
    # 3.6 Karsinojenez
    "Carc. 1A": {"h":"H350","cutoff":0.1,"signal":"Danger"},
    "Carc. 1B": {"h":"H350","cutoff":0.1,"signal":"Danger"},
    "Carc. 2":  {"h":"H351","cutoff":1.0,"signal":"Warning"},
    # 3.7 Üreme
    "Repr. 1A": {"h":"H360","cutoff":0.1,"signal":"Danger"},
    "Repr. 1B": {"h":"H360","cutoff":0.1,"signal":"Danger"},
    "Repr. 2":  {"h":"H361","cutoff":1.0,"signal":"Warning"},
    "Repr. Lact.":{"h":"H362","cutoff":0.1,"signal":"Warning"},
    # 3.8 STOT SE
    "STOT SE 1": {"h":"H370","cutoff":10.0,"signal":"Danger"},
    "STOT SE 2": {"h":"H371","cutoff":10.0,"signal":"Warning"},
    "STOT SE 3": {"h":"H336","cutoff":20.0,"signal":"Warning"},  # narkotik/solunum tahrişi
    # 3.9 STOT RE — hedef organ servisi ayrı (stot_re_service)
    "STOT RE 1": {"h":"H372","cutoff":1.0, "signal":"Danger"},
    "STOT RE 2": {"h":"H373","cutoff":10.0,"signal":"Warning"},
    # 3.10 Aspirasyon
    "Asp. Tox. 1": {"h":"H304","cutoff":10.0,"signal":"Danger"},
    # 4.1 Sucul — M-faktör ecological_service ile
    "Aquatic Acute 1":   {"h":"H400","cutoff":0.1, "signal":"Warning"},
    "Aquatic Chronic 1": {"h":"H410","cutoff":0.1, "signal":"Warning"},
    "Aquatic Chronic 2": {"h":"H411","cutoff":1.0, "signal":"Warning"},
    "Aquatic Chronic 3": {"h":"H412","cutoff":10.0,"signal":"Warning"},
    "Aquatic Chronic 4": {"h":"H413","cutoff":25.0,"signal":"Warning"},
    # 2.x Fiziksel — ayrı engine (physical_hazard_service)
    "Flam. Gas 1":  {"h":"H220","cutoff":0.0,"signal":"Danger"},
    "Flam. Gas 2":  {"h":"H221","cutoff":0.0,"signal":"Warning"},
    "Aerosol 1":    {"h":"H222","cutoff":0.0,"signal":"Danger"},
    "Aerosol 2":    {"h":"H223","cutoff":0.0,"signal":"Warning"},
    "Flam. Liq. 1": {"h":"H224","cutoff":1.0, "signal":"Danger"},
    "Flam. Liq. 2": {"h":"H225","cutoff":10.0,"signal":"Danger"},
    "Flam. Liq. 3": {"h":"H226","cutoff":10.0,"signal":"Warning"},
    "Flam. Sol. 1": {"h":"H228","cutoff":0.0,"signal":"Danger"},
    "Flam. Sol. 2": {"h":"H228","cutoff":0.0,"signal":"Warning"},
    "Ox. Liq. 1":   {"h":"H271","cutoff":0.0,"signal":"Danger"},
    "Ox. Liq. 2":   {"h":"H272","cutoff":0.0,"signal":"Danger"},
    "Ox. Liq. 3":   {"h":"H272","cutoff":0.0,"signal":"Warning"},
    "Ox. Sol. 1":   {"h":"H271","cutoff":0.0,"signal":"Danger"},
    "Ox. Sol. 2":   {"h":"H272","cutoff":0.0,"signal":"Danger"},
    "Ox. Sol. 3":   {"h":"H272","cutoff":0.0,"signal":"Warning"},
    "Ox. Gas 1":    {"h":"H270","cutoff":0.0,"signal":"Danger"},
    "Press. Gas":   {"h":"H280","cutoff":0.0,"signal":"Warning"},
    "Water-react. 1":{"h":"H260","cutoff":0.0,"signal":"Danger"},
    "Water-react. 2":{"h":"H261","cutoff":0.0,"signal":"Warning"},
    "Pyr. Liq. 1":  {"h":"H250","cutoff":0.0,"signal":"Danger"},
    "Pyr. Sol. 1":  {"h":"H250","cutoff":0.0,"signal":"Danger"},
    "Self-react. A": {"h":"H240","cutoff":0.0,"signal":"Danger"},
    "Self-react. B": {"h":"H241","cutoff":0.0,"signal":"Danger"},
    "Org. Perox. A": {"h":"H240","cutoff":0.0,"signal":"Danger"},
    "Org. Perox. B": {"h":"H241","cutoff":0.0,"signal":"Danger"},
    "Met. Corr. 1":  {"h":"H290","cutoff":0.0,"signal":"Warning"},
}

DANGER_H = {
    'H200','H201','H202','H203','H204','H205',
    'H220','H221','H222','H224','H225',
    'H228','H240','H241','H250','H260','H270','H271','H272',
    'H300','H301','H304','H310','H311','H314','H318','H330','H331',
    'H334','H340','H350','H360','H370','H372',
}


def classify_mixture_clp(components: list) -> dict:
    """
    CLP Annex I karışım sınıflandırması.
    Giriş: [{cas_no, name, concentration, hazards:[{h_class, h_code}]}]
    Çıkış: {h_codes, signal_word, passed:[{h_class,h_code,conc,reason}], warnings}
    """
    passed = []
    warnings = []
    seen_h = set()

    # STOT RE — hedef organ bazlı ayrı hesapla
    stot_comps = []
    for comp in components:
        cas = comp.get("cas_no", comp.get("cas", ""))
        conc = float(comp.get("concentration", comp.get("conc", 0)) or 0)
        hazards = comp.get("hazards", [])
        stot_comps.append({"cas": cas, "name": comp.get("name",""), "conc": conc, "hazards": hazards})

    # İkincil Skin/Eye kuralı (CLP Tablo 3.2.3/3.3.3)
    sum_corr1 = sum(
        float(comp.get("concentration", comp.get("conc", 0)) or 0)
        for comp in components
        for h in comp.get("hazards", [])
        if h.get("h_class","") in ("Skin Corr. 1","Skin Corr. 1A","Skin Corr. 1B","Skin Corr. 1C")
    )
    sum_eye_dam1 = sum(
        float(comp.get("concentration", comp.get("conc", 0)) or 0)
        for comp in components
        for h in comp.get("hazards", [])
        if h.get("h_class","") == "Eye Dam. 1"
    )

    # Her bileşen × her tehlike sınıfı
    for comp in components:
        cas = comp.get("cas_no", comp.get("cas", ""))
        conc = float(comp.get("concentration", comp.get("conc", 0)) or 0)
        for haz in comp.get("hazards", []):
            h_class = (haz.get("h_class") or "").replace("*","").strip()
            h_code  = (haz.get("h_code")  or "").replace("*","").replace(" ","")[:4]

            rule = CLP_CUTOFFS_DICT.get(h_class)
            if not rule:
                # h_code'dan fallback
                continue

            cutoff = rule["cutoff"]
            h = rule["h"]

            # SCL override — bileşenin özel konsantrasyon sınırı generic cut-off'tan düşükse kullan
            scl_list = comp.get("scl", [])
            for scl_entry in scl_list:
                if scl_entry.get("h_class") == h_class or scl_entry.get("h_code") == h:
                    c_min = scl_entry.get("c_min")
                    if c_min is not None and float(c_min) < cutoff:
                        cutoff = float(c_min)

            if conc < cutoff:
                warnings.append(
                    f"{comp.get('name',cas)} ({h_class} %{conc:.1f}) → "
                    f"cut-off %{cutoff} altı → dahil edilmedi"
                )
                continue

            if h not in seen_h:
                seen_h.add(h)
                passed.append({
                    "h_class": h_class,
                    "h_code":  h,
                    "conc":    conc,
                    "reason":  f"{comp.get('name',cas)} %{conc:.1f} ≥ kesme %{cutoff}",
                })

    # CLP Tablo 3.2.4: Skin Irrit. 2 toplama kuralı
    # Tek bileşen <%10 olsa da toplam ≥%10 → H315
    sum_skin_irrit2 = sum(
        float(comp.get("concentration", comp.get("conc", 0)) or 0)
        for comp in components
        for h in comp.get("hazards", [])
        if h.get("h_class","") == "Skin Irrit. 2"
    )
    if "H314" not in seen_h and "H315" not in seen_h and sum_skin_irrit2 >= 10.0:
        seen_h.add("H315")
        passed.append({"h_class":"Skin Irrit. 2","h_code":"H315","conc":sum_skin_irrit2,
                       "reason":f"Toplama: Σ Skin Irrit.2=%{sum_skin_irrit2:.1f} ≥ %10 (CLP Tablo 3.2.4)"})

    # İkincil Skin kural (Skin Corr. 1 bileşenin alt-eşik katkısı)
    if "H314" not in seen_h and "H315" not in seen_h and 1.0 <= sum_corr1 < 10.0:
        seen_h.add("H315")
        passed.append({"h_class":"Skin Irrit. 2","h_code":"H315","conc":sum_corr1,
                       "reason":f"İkincil: Σ Skin Corr.1=%{sum_corr1:.1f} ∈ [1%,10%) (Tablo 3.2.3)"})

    # İkincil Eye kural
    if "H318" not in seen_h and "H319" not in seen_h and 1.0 <= sum_eye_dam1 < 3.0:
        seen_h.add("H319")
        passed.append({"h_class":"Eye Irrit. 2","h_code":"H319","conc":sum_eye_dam1,
                       "reason":f"İkincil: Σ Eye Dam.1=%{sum_eye_dam1:.1f} ∈ [1%,3%) (Tablo 3.3.3)"})

    h_codes = sorted(seen_h)
    signal  = "Danger" if any(h in DANGER_H for h in h_codes) else ("Warning" if h_codes else "")
    signal_tr = {"Danger":"Tehlike","Warning":"Uyarı","":""}.get(signal,"")

    return {
        "h_codes":     h_codes,
        "signal_word": signal,
        "signal_word_tr": signal_tr,
        "passed":      passed,
        "warnings":    warnings,
    }


"""
CLP Hesaplama Servisi — v3
==========================
CLP Regulation (EC) No 1272/2008 — Annex I

Modül Akışı:
  calculate_clp()                     → Temel hesap (ATE + Cut-off + Aquatic)
  calculate_clp_full()                → CLP + EUH birleşik
  calculate_clp_with_non_additivity() → Tam hesap (CLP + Non-additivity + STOT RE + Fiziksel + EUH)

Uygulanan Kurallar:
  ├─ ATE Toplamı          → Acute Tox. 1-4 (oral/dermal/inhalation) — Annex I Bölüm 3.1
  ├─ Cut-off / SCL        → Bileşen konsantrasyon eşikleri — Annex I Tablo 3.x.4
  ├─ Aquatic              → H400/H410/H411/H412/H413 — Annex I Tablo 4.1.3
  ├─ NOTE 1               → Form bağımlı Carc/Muta/Repr — sıvıda uygulanmaz
  ├─ Non-additivity       → Fenol/aldehit/asit/baz → Skin/Eye override — Tablo 3.2.4
  ├─ STOT RE              → Hedef organ toplamı — stot_re_service.py
  ├─ Fiziksel Tehlike     → Flam.Liq / Asp.Tox — physical_hazard_service.py
  └─ EUH                  → euh_service.py

Öncelik Kuralları:
  - Worst case konsantrasyon (aralık verildiğinde üst sınır)
  - Kullanıcı ATE/LD50 > Annex VI varsayılan
  - SCL > Generic cut-off
  - pH ≤2 / ≥11.5 → Skin Corr. 1 direkt (Tablo 3.2.3)

Bağımlılıklar:
  app.services.echa_service          → CLP verisi çekme
  app.services.non_additivity_service
  app.services.stot_re_service
  app.services.physical_hazard_service
  app.services.euh_service
"""
from typing import List, Dict, Any, Optional
try:
    from sqlalchemy.ext.asyncio import AsyncSession
except ImportError:
    AsyncSession = None

try:
    from app.services.echa_service import fetch_from_echa
except ImportError:
    fetch_from_echa = None

# ─── CUT-OFF LİMİTLERİ ───────────────────────────────────────────────────────

CUTOFFS = {
    'Skin Corr. 1':    {'cutoff': 1.0,  'pictogram': 'GHS05', 'signal': 'Danger'},
    'Skin Corr. 1A':   {'cutoff': 1.0,  'pictogram': 'GHS05', 'signal': 'Danger'},
    'Skin Corr. 1B':   {'cutoff': 1.0,  'pictogram': 'GHS05', 'signal': 'Danger'},
    'Skin Corr. 1C':   {'cutoff': 1.0,  'pictogram': 'GHS05', 'signal': 'Danger'},
    'Skin Irrit. 2':   {'cutoff': 10.0, 'pictogram': 'GHS07', 'signal': 'Warning'},
    'Eye Dam. 1':      {'cutoff': 3.0,  'pictogram': 'GHS05', 'signal': 'Danger'},
    'Eye Irrit. 2':    {'cutoff': 10.0, 'pictogram': 'GHS07', 'signal': 'Warning'},
    'Resp. Sens. 1':   {'cutoff': 1.0,  'pictogram': 'GHS08', 'signal': 'Danger'},
    'Resp. Sens. 1A':  {'cutoff': 1.0,  'pictogram': 'GHS08', 'signal': 'Danger'},
    'Resp. Sens. 1B':  {'cutoff': 1.0,  'pictogram': 'GHS08', 'signal': 'Danger'},
    'Skin Sens. 1':    {'cutoff': 1.0,  'pictogram': 'GHS07', 'signal': 'Warning'},
    'Skin Sens. 1A':   {'cutoff': 1.0,  'pictogram': 'GHS07', 'signal': 'Warning'},
    'Skin Sens. 1B':   {'cutoff': 1.0,  'pictogram': 'GHS07', 'signal': 'Warning'},
    'Muta. 1A':        {'cutoff': 0.1,  'pictogram': 'GHS08', 'signal': 'Danger'},
    'Muta. 1B':        {'cutoff': 0.1,  'pictogram': 'GHS08', 'signal': 'Danger'},
    'Muta. 2':         {'cutoff': 1.0,  'pictogram': 'GHS08', 'signal': 'Warning'},
    'Carc. 1A':        {'cutoff': 0.1,  'pictogram': 'GHS08', 'signal': 'Danger'},
    'Carc. 1B':        {'cutoff': 0.1,  'pictogram': 'GHS08', 'signal': 'Danger'},
    'Carc. 2':         {'cutoff': 1.0,  'pictogram': 'GHS08', 'signal': 'Warning'},
    'Repr. 1A':        {'cutoff': 0.3,  'pictogram': 'GHS08', 'signal': 'Danger'},
    'Repr. 1B':        {'cutoff': 0.3,  'pictogram': 'GHS08', 'signal': 'Danger'},
    'Repr. 2':         {'cutoff': 3.0,  'pictogram': 'GHS08', 'signal': 'Warning'},
    'Lact.':           {'cutoff': 0.3,  'pictogram': 'GHS08', 'signal': 'Warning'},
    'STOT SE 1':       {'cutoff': 1.0,  'pictogram': 'GHS08', 'signal': 'Danger'},
    'STOT SE 2':       {'cutoff': 10.0, 'pictogram': 'GHS08', 'signal': 'Warning'},
    'STOT SE 3':       {'cutoff': 20.0, 'pictogram': 'GHS07', 'signal': 'Warning'},
    'STOT RE 1':       {'cutoff': 1.0,  'pictogram': 'GHS08', 'signal': 'Danger'},
    'STOT RE 2':       {'cutoff': 10.0, 'pictogram': 'GHS08', 'signal': 'Warning'},
    'Asp. Tox. 1':     {'cutoff': 10.0, 'pictogram': 'GHS08', 'signal': 'Danger'},
}

# ATE kategori varsayılan değerleri (spesifik ATE yoksa kullanılır)
ATE_DEFAULTS = {
    'oral':             {'Acute Tox. 1': 5,    'Acute Tox. 2': 50,   'Acute Tox. 3': 300,  'Acute Tox. 4': 2000},
    'dermal':           {'Acute Tox. 1': 50,   'Acute Tox. 2': 200,  'Acute Tox. 3': 1000, 'Acute Tox. 4': 2000},
    'inhalation_dust':  {'Acute Tox. 1': 0.05, 'Acute Tox. 2': 0.5,  'Acute Tox. 3': 1.0,  'Acute Tox. 4': 5.0},
    'inhalation_vapour':{'Acute Tox. 1': 0.5,  'Acute Tox. 2': 2.0,  'Acute Tox. 3': 10.0, 'Acute Tox. 4': 20.0},
    'inhalation':       {'Acute Tox. 1': 0.05, 'Acute Tox. 2': 0.5,  'Acute Tox. 3': 1.0,  'Acute Tox. 4': 5.0},
}

ATE_HCODES = {
    'oral':             {1: 'H300', 2: 'H300', 3: 'H301', 4: 'H302'},
    'dermal':           {1: 'H310', 2: 'H310', 3: 'H311', 4: 'H312'},
    'inhalation_dust':  {1: 'H330', 2: 'H330', 3: 'H331', 4: 'H332'},
    'inhalation_vapour':{1: 'H330', 2: 'H330', 3: 'H331', 4: 'H332'},
    'inhalation':       {1: 'H330', 2: 'H330', 3: 'H331', 4: 'H332'},
}
ATE_PICS = {1: 'GHS06', 2: 'GHS06', 3: 'GHS06', 4: 'GHS07'}
ATE_SIGS = {1: 'Danger', 2: 'Danger', 3: 'Danger', 4: 'Warning'}

# Fiziksel tehlike sınıfları — hesaplanamaz
PHYSICAL = ['Ox.', 'Flam.', 'Expl.', 'Press. Gas', 'Water-react.',
            'Self-react.', 'Pyr.', 'Self-heat.', 'Org. Perox.', 'Corr. Met.']

# NOTE 1: Sadece toz/çözünebilir toz formunda geçerli sınıflandırmalar
# Sıvı/çözelti formunda bu hazard sınıfları uygulanmaz
NOTE1_HAZARDS = {'Carc. 1B', 'Carc. 1A', 'Muta. 1B', 'Muta. 1A', 'Repr. 1B', 'Repr. 1A'}

# Note 1 uygulanan maddeler (Annex VI)
NOTE1_CAS = {
    '10124-43-3',  # cobalt sulfate
    '10026-24-1',  # cobalt sulfate heptahydrate
    '7791-13-1',   # cobalt chloride
    '513-79-1',    # cobalt carbonate
    '71-48-7',     # cobalt acetate
}


def _get_ate_value(ate_data: dict, route: str, h_class: str) -> Optional[float]:
    """
    ATE değerini önce spesifik veriden, sonra kategori varsayılanından al.
    Spesifik ATE her zaman önceliklidir.
    """
    # Spesifik ATE varsa kullan
    if ate_data.get(route):
        return ate_data[route]
    # İnhalasyon alt türleri birbirinin yerine
    if route in ('inhalation_dust', 'inhalation_vapour') and ate_data.get('inhalation'):
        return ate_data['inhalation']
    # Kategori varsayılanı
    return ATE_DEFAULTS.get(route, {}).get(h_class)


def _is_note1_applicable(cas: str, h_class: str, form: Optional[str]) -> bool:
    """
    NOTE 1 kontrolü: Madde NOTE 1 kapsamındaysa ve sıvı/çözelti formundaysa
    ilgili hazard sınıfı uygulanmaz.
    """
    if cas not in NOTE1_CAS:
        return True  # Note 1 yok, normal uygula
    if h_class not in NOTE1_HAZARDS:
        return True  # Bu hazard için Note 1 yok

    # Form belirtilmişse kontrol et
    if form:
        liquid_forms = {'liquid', 'solution', 'aqueous', 'sıvı', 'çözelti'}
        solid_forms = {'solid', 'powder', 'dust', 'toz', 'katı'}
        form_lower = form.lower()
        if any(f in form_lower for f in liquid_forms):
            return False  # Sıvı form → Note 1 → uygulanmaz
        if any(f in form_lower for f in solid_forms):
            return True   # Toz form → uygula
    # Form belirtilmemişse güvenli tarafta kal — uyarı ver, hesapla
    return True


async def calculate_clp(db: AsyncSession, components: List[Any]) -> Dict:
    """
    Ana CLP hesaplama fonksiyonu — v3
    CLP Regulation (EC) No 1272/2008, Annex I'e göre
    """
    results_passed = []
    results_failed = []
    results_physical = []
    warnings = []
    passed_h_codes = set()
    passed_pictograms = set()
    signal_danger = False
    signal_warning = False

    # Her bileşen için veri hazırla
    enriched = []
    for comp in components:
        cas = str(comp.cas_no).strip()

        # Worst case konsantrasyon (CLP kuralı)
        conc = comp.worst_case_concentration

        # Spesifik ATE verisi
        user_ate = comp.ate_dict if hasattr(comp, 'ate_dict') else {}

        # Madde formu (NOTE 1 için)
        form = getattr(comp, 'form', None)

        # CLP verisi çek
        data = await get_clp_data(db, cas)

        enriched.append({
            'cas': cas,
            'conc': conc,
            'data': data,
            'name': getattr(comp, 'name', None) or (data.get('chemical_name') if data else cas),
            'user_ate': user_ate,
            'form': form,
            'conc_min': getattr(comp, 'concentration_min', None),
            'conc_max': getattr(comp, 'concentration_max', None),
        })

    # ─── ADIM 1: ATE TOPLAMA ────────────────────────────────────────────
    ate_routes = list(ATE_DEFAULTS.keys())
    ate_sum = {r: 0.0 for r in ate_routes}

    for item in enriched:
        if not item['data']:
            continue
        data = item['data']
        conc_frac = item['conc'] / 100
        # Kullanıcı spesifik ATE her zaman öncelikli (test verisi)
        # Önce Annex VI/C&L, üstüne kullanıcı verisi override
        base_ate = data.get('ate', {}) or {}
        combined_ate = {**base_ate, **item['user_ate']}
        # Kullanıcı veri girdiyse log
        if item['user_ate']:
            pass  # API response'a detay eklenebilir

        for haz in data.get('hazards', []):
            hc = haz.get('h_class', '').replace('*', '').strip()
            if not hc.startswith('Acute Tox.'):
                continue
            for route in ate_routes:
                ate_val = _get_ate_value(combined_ate, route, hc)
                if ate_val and ate_val > 0:
                    ate_sum[route] += conc_frac / ate_val

    for route, total in ate_sum.items():
        if total <= 0:
            continue
        mix_ate = 100 / total
        limits = ATE_DEFAULTS.get(route, {})
        cat_num = None
        for n in [1, 2, 3, 4]:
            # <= kullanıyoruz: tam eşit değerler de geçiyor
            if mix_ate <= limits.get(f'Acute Tox. {n}', float('inf')):
                cat_num = n
                break
        if cat_num:
            hcode = ATE_HCODES[route][cat_num]
            pic = ATE_PICS[cat_num]
            sig = ATE_SIGS[cat_num]
            results_passed.append({
                'cas': 'KARIŞIM', 'name': f'ATE ({route})',
                'conc': '-', 'h_class': f'Acute Tox. {cat_num}', 'h_code': hcode,
                'cutoff_used': f'ATE={mix_ate:.1f}',
                'passed': True, 'reason': f'Karışım ATE={mix_ate:.1f} ≤ {limits.get(f"Acute Tox. {cat_num}")}',
            })
            passed_h_codes.add(hcode)
            passed_pictograms.add(pic)
            if sig == 'Danger': signal_danger = True
            else: signal_warning = True

    # ─── ADIM 2: CUT-OFF / SCL ──────────────────────────────────────────
    for item in enriched:
        cas = item['cas']
        conc = item['conc']
        data = item['data']
        form = item['form']

        if not data:
            warnings.append(f"{cas}: Annex VI/C&L'de bulunamadı — manuel kontrol gerekli")
            continue

        # Konsantrasyon aralığı bilgisi uyarıya ekle
        if item['conc_min'] is not None and item['conc_max'] is not None:
            range_note = f" [aralık: %{item['conc_min']}-{item['conc_max']}, worst case: %{conc}]"
        else:
            range_note = ''

        scl_list = data.get('scl', [])

        for haz in data.get('hazards', []):
            hc_raw = haz.get('h_class', '').strip()
            hc = hc_raw.replace('*', '').strip()
            hcode = haz.get('h_code', '').replace('*', '').strip()

            # Fiziksel tehlike
            if any(hc.startswith(p) for p in PHYSICAL):
                if not any(w for w in warnings if hc in w and cas in w):
                    warnings.append(f"{cas} → {hc}: Fiziksel tehlike — karışım için ayrıca test edilmeli")
                results_physical.append({
                    'cas': cas, 'name': data.get('chemical_name', ''),
                    'conc': conc, 'h_class': hc, 'h_code': hcode,
                    'cutoff_used': '—', 'passed': False,
                    'reason': 'Fiziksel tehlike (hesaplanamaz)'
                })
                continue

            # Aquatic — Adım 3'te
            if hc.startswith('Aquatic'):
                continue

            # Acute Tox. — ATE'de hesaplandı
            if hc.startswith('Acute Tox.'):
                continue

            # NOTE 1 kontrolü
            if not _is_note1_applicable(cas, hc, form):
                warnings.append(
                    f"{cas} → {hc}: NOTE 1 — Bu madde sıvı/çözelti formunda bu sınıflandırma uygulanmaz"
                )
                results_failed.append({
                    'cas': cas, 'name': data.get('chemical_name', ''),
                    'conc': conc, 'h_class': hc, 'h_code': hcode,
                    'cutoff_used': 'NOTE 1', 'passed': False,
                    'reason': 'NOTE 1: Sıvı formda uygulanmaz'
                })
                continue

            # NOTE 1 var ama form belirtilmemiş — uyarı ver ama hesapla
            if cas in NOTE1_CAS and hc in NOTE1_HAZARDS and not form:
                warnings.append(
                    f"{cas} → {hc}: NOTE 1 mevcut — madde formunu belirtin (toz/sıvı). "
                    f"Form belirtilmediği için hesaba dahil edildi."
                )

            # SCL kontrolü
            cutoff = None
            scl_note = ''
            for scl in scl_list:
                scl_hc = scl.get('hazard', '').replace('*', '').strip()
                scl_hcode = scl.get('h_code', '').replace('*', '').strip()
                if scl_hc == hc or scl_hcode == hcode:
                    cutoff = scl['c_min']
                    scl_note = f' (SCL≥{cutoff}%)'
                    break

            if cutoff is None:
                info = CUTOFFS.get(hc, {})
                cutoff = info.get('cutoff')

            if cutoff is None:
                continue

            # >= kullanıyoruz: tam eşit değerler de geçiyor (worst case)
            passed = conc >= cutoff
            info = CUTOFFS.get(hc, {})
            entry = {
                'cas': cas, 'name': data.get('chemical_name', ''),
                'conc': conc, 'h_class': hc, 'h_code': hcode,
                'cutoff_used': f'%{cutoff}{scl_note}',
                'passed': passed,
                'reason': f'%{conc} {"≥" if passed else "<"} %{cutoff}{scl_note}{range_note}',
            }
            if passed:
                results_passed.append(entry)
                if hcode: passed_h_codes.add(hcode)
                if info.get('pictogram'): passed_pictograms.add(info['pictogram'])
                if info.get('signal') == 'Danger': signal_danger = True
                elif info.get('signal') == 'Warning': signal_warning = True
            else:
                results_failed.append(entry)

    # ─── ADIM 2b: İKİNCİL CİLT/GÖZ SINIFLANDIRMASI ───────────────────────────
    # CLP Annex I Tablo 3.2.3 / 3.3.3 — Skin Corr./Eye Dam. bileşen ikincil kural
    # Skin Corr. 1 içeren madde SCL altında ama Σ %1-10 → Skin Irrit. 2 (H315)
    # Eye Dam. 1 içeren madde SCL altında ama Σ %1-3   → Eye Irrit. 2 (H319)

    sum_corr1 = 0.0   # Skin Corr. 1 bileşen toplamı
    sum_eye_dam1 = 0.0  # Eye Dam. 1 bileşen toplamı

    for item in enriched:
        if not item['data']:
            continue
        conc = item['conc']
        for haz in item['data'].get('hazards', []):
            hc = haz.get('h_class', '').replace('*', '').strip()
            if hc in ('Skin Corr. 1', 'Skin Corr. 1A', 'Skin Corr. 1B', 'Skin Corr. 1C'):
                sum_corr1 += conc
            if hc in ('Eye Dam. 1',):
                sum_eye_dam1 += conc

    # Skin Irrit. 2 ikincil kural — H314 zaten geçmemişse uygula
    if 'H314' not in passed_h_codes and 1.0 <= sum_corr1 < 10.0:
        passed_h_codes.add('H315')
        passed_pictograms.add('GHS07')
        signal_warning = True
        results_passed.append({
            'cas': 'KARIŞIM', 'name': 'Skin Irrit. 2 (ikincil kural)',
            'conc': '-', 'h_class': 'Skin Irrit. 2', 'h_code': 'H315',
            'cutoff_used': 'Tablo 3.2.3 ikincil',
            'passed': True,
            'reason': f'Σ Skin Corr.1 = %{sum_corr1:.1f} ∈ [1%, 10%) → H315 (ikincil sınıflandırma)',
        })
        warnings.append(
            f"İkincil kural: Σ Skin Corr.1 = %{sum_corr1:.1f} — H314 eşiği aşılmadı "
            f"ancak %1-10 aralığında → H315 Skin Irrit. 2 uygulandı (CLP Tablo 3.2.3)"
        )

    # Eye Irrit. 2 ikincil kural — H318 zaten geçmemişse uygula
    if 'H318' not in passed_h_codes and 1.0 <= sum_eye_dam1 < 3.0:
        passed_h_codes.add('H319')
        passed_pictograms.add('GHS07')
        signal_warning = True
        results_passed.append({
            'cas': 'KARIŞIM', 'name': 'Eye Irrit. 2 (ikincil kural)',
            'conc': '-', 'h_class': 'Eye Irrit. 2', 'h_code': 'H319',
            'cutoff_used': 'Tablo 3.3.3 ikincil',
            'passed': True,
            'reason': f'Σ Eye Dam.1 = %{sum_eye_dam1:.1f} ∈ [1%, 3%) → H319 (ikincil sınıflandırma)',
        })

    # ─── ADIM 3: AQUATIC (CLP Annex I Tablo 4.1.3) ──────────────────────
    sum_acute_m = 0.0
    sum_chronic_m = 0.0
    sum_chronic_plain = 0.0

    for item in enriched:
        if not item['data']:
            continue
        conc = item['conc']
        data = item['data']
        m_acute = data.get('m_factors', {}).get('acute', 1)
        m_chronic = data.get('m_factors', {}).get('chronic', 1)

        for haz in data.get('hazards', []):
            hc = haz.get('h_class', '').replace('*', '').strip()
            if hc == 'Aquatic Acute 1':
                sum_acute_m += (conc * m_acute) / 100
            elif hc in ('Aquatic Chronic 1', 'Aquatic Chronic 2'):
                sum_chronic_m += (conc * m_chronic) / 100
                sum_chronic_plain += conc / 100
            elif hc in ('Aquatic Chronic 3', 'Aquatic Chronic 4'):
                sum_chronic_plain += conc / 100

    # Aquatic Acute 1
    if sum_acute_m >= 0.25:
        passed_h_codes.add('H400')
        passed_pictograms.add('GHS09')
        signal_warning = True
        results_passed.append({
            'cas': 'KARIŞIM', 'name': 'Aquatic Acute',
            'conc': '-', 'h_class': 'Aquatic Acute 1', 'h_code': 'H400',
            'cutoff_used': 'Σ(Ci×Mi)/100≥0.25',
            'passed': True, 'reason': f'Σ(Ci×Mi)/100={sum_acute_m:.4f}≥0.25',
        })

    # Aquatic Chronic
    if sum_chronic_m >= 0.1:
        passed_h_codes.add('H410')
        passed_pictograms.add('GHS09')
        results_passed.append({
            'cas': 'KARIŞIM', 'name': 'Aquatic Chronic 1',
            'conc': '-', 'h_class': 'Aquatic Chronic 1', 'h_code': 'H410',
            'cutoff_used': 'Σ(Ci×Mi)/100≥0.1',
            'passed': True, 'reason': f'Σ(Ci×Mi)/100={sum_chronic_m:.4f}≥0.1',
        })
    elif sum_chronic_m >= 0.01:
        passed_h_codes.add('H411')
        passed_pictograms.add('GHS09')
        results_passed.append({
            'cas': 'KARIŞIM', 'name': 'Aquatic Chronic 2',
            'conc': '-', 'h_class': 'Aquatic Chronic 2', 'h_code': 'H411',
            'cutoff_used': 'Σ(Ci×Mi)/100≥0.01',
            'passed': True, 'reason': f'Σ(Ci×Mi)/100={sum_chronic_m:.4f}≥0.01',
        })
    elif sum_chronic_plain >= 0.25:
        passed_h_codes.add('H412')
        results_passed.append({
            'cas': 'KARIŞIM', 'name': 'Aquatic Chronic 3',
            'conc': '-', 'h_class': 'Aquatic Chronic 3', 'h_code': 'H412',
            'cutoff_used': 'Σ(Ci)/100≥0.25',
            'passed': True, 'reason': f'Σ(Ci)/100={sum_chronic_plain:.4f}≥0.25',
        })
    elif sum_chronic_plain >= 0.025:
        passed_h_codes.add('H413')
        results_passed.append({
            'cas': 'KARIŞIM', 'name': 'Aquatic Chronic 4',
            'conc': '-', 'h_class': 'Aquatic Chronic 4', 'h_code': 'H413',
            'cutoff_used': 'Σ(Ci)/100≥0.025',
            'passed': True, 'reason': f'Σ(Ci)/100={sum_chronic_plain:.4f}≥0.025',
        })

    signal_word = 'Danger' if signal_danger else ('Warning' if signal_warning else 'None')

    return {
        'h_codes': sorted(list(passed_h_codes)),
        'pictograms': sorted(list(passed_pictograms)),
        'signal_word': signal_word,
        'passed': results_passed,
        'failed': results_failed,
        'physical': results_physical,
        'warnings': warnings,
    }


async def get_clp_data(db: AsyncSession, cas_no: str) -> Optional[Dict]:
    """CLP verisini önce cache'den, sonra ECHA'dan çeker"""
    result = await db.execute(select(CLPCache).where(CLPCache.cas_no == cas_no))
    cached = result.scalar_one_or_none()

    if cached:
        return {
            'chemical_name': cached.chemical_name,
            'hazards': cached.hazards or [],
            'pictograms': cached.pictograms or [],
            'signal_word': cached.signal_word,
            'm_factors': cached.m_factors or {},
            'scl': cached.scl or [],
            'ate': cached.ate or {},
            'source': cached.source,
        }

    echa_data = await fetch_from_echa(cas_no)
    if echa_data:
        new_cache = CLPCache(
            cas_no=cas_no,
            chemical_name=echa_data.get('chemical_name'),
            hazards=echa_data.get('hazards', []),
            pictograms=echa_data.get('pictograms', []),
            signal_word=echa_data.get('signal_word'),
            m_factors=echa_data.get('m_factors', {}),
            scl=echa_data.get('scl', []),
            ate=echa_data.get('ate', {}),
            source='echa_cl',
        )
        db.add(new_cache)
        await db.flush()
        return echa_data

    return None


async def calculate_clp_full(db, components: List[Any]) -> Dict:
    """
    Tam CLP hesaplama — H kodları + EUH ifadeleri birlikte
    """
    # CLP hesaplama
    clp_result = await calculate_clp(db, components)

    # EUH hesaplama
    from app.services.euh_service import check_euh
    comp_list = [
        {
            'cas': str(c.cas_no).strip(),
            'name': getattr(c, 'name', None) or '',
            'conc': c.worst_case_concentration,
            'hazards': [],  # Veritabanından gelecek
        }
        for c in components
    ]

    # Hazard verilerini ekle
    for i, comp in enumerate(components):
        data = await get_clp_data(db, str(comp.cas_no).strip())
        if data:
            comp_list[i]['hazards'] = data.get('hazards', [])

    euh_result = check_euh(comp_list)

    # Sonuçları birleştir
    clp_result['euh_codes'] = euh_result['euh_codes']
    clp_result['euh_details'] = euh_result['euh_details']
    clp_result['manual_check_euh'] = euh_result['manual_check']

    return clp_result


async def calculate_clp_with_non_additivity(db, components: List[Any]) -> Dict:
    """
    CLP hesaplama — non-additivity override dahil.
    
    Akış:
    1. Normal CLP hesapla (ATE, cut-off, SCL, Aquatic)
    2. Non-additivity kontrolü yap
    3. Non-additivity varsa Skin/Eye sonuçlarını override et
    4. EUH hesapla
    5. Birleşik sonuç döndür
    """
    from app.services.non_additivity_service import classify_skin_eye_non_additivity
    from app.services.euh_service import check_euh

    # Bileşen verilerini hazırla
    comp_list = []
    for comp in components:
        cas = str(comp.cas_no).strip()
        data = await get_clp_data(db, cas)
        comp_list.append({
            'cas': cas,
            'name': getattr(comp, 'name', None) or (data.get('chemical_name') if data else cas),
            'conc': comp.worst_case_concentration,
            'form': getattr(comp, 'form', None),
            'hazards': data.get('hazards', []) if data else [],
            'user_ate': comp.ate_dict if hasattr(comp, 'ate_dict') else {},
        })

    # ─── 1. Normal CLP ───────────────────────────────────────────────────────
    clp_result = await calculate_clp(db, components)
    passed_h = set(clp_result['h_codes'])
    passed_pic = set(clp_result['pictograms'])
    signal_danger = clp_result['signal_word'] == 'Danger'
    signal_warning = clp_result['signal_word'] == 'Warning'

    # ─── 2. Non-additivity kontrolü ──────────────────────────────────────────
    na_result = classify_skin_eye_non_additivity(comp_list)

    if na_result['override']:
        # Non-additivity maddeler var — Skin/Eye sonuçlarını override et
        # Önce normal hesaptan Skin/Eye H kodlarını temizle
        skin_eye_h = {'H314', 'H315', 'H318', 'H319'}
        skin_eye_pic = set()

        # Hangi H kodları Skin/Eye kaynaklı? passed listesinden çıkar
        old_passed = clp_result.get('passed', [])
        new_passed = []
        for entry in old_passed:
            if entry.get('h_code') not in skin_eye_h:
                new_passed.append(entry)
            else:
                # Non-additivity override edecek
                pass

        # Normal Skin/Eye H kodlarını ve pictogramları temizle
        for h in skin_eye_h:
            passed_h.discard(h)
        passed_pic.discard('GHS05')
        # GHS07 diğer hazarddan da gelebilir, dikkatli çıkar
        # Önce GHS07 kaynaklarını kontrol et
        ghs07_still_needed = any(
            e.get('h_code') not in skin_eye_h
            for e in new_passed
            if CUTOFFS.get(e.get('h_class', ''), {}).get('pictogram') == 'GHS07'
        )
        if not ghs07_still_needed:
            passed_pic.discard('GHS07')

        # Non-additivity sonucunu ekle
        override_entries = []

        skin = na_result['skin_result']
        if skin and skin['class']:
            passed_h.add(skin['h_code'])
            passed_pic.add(skin['pictogram'])
            if skin['signal'] == 'Danger':
                signal_danger = True
            override_entries.append({
                'cas': 'NON-ADDITIVITY', 'name': 'Tablo 3.2.4',
                'conc': '-', 'h_class': skin['class'], 'h_code': skin['h_code'],
                'cutoff_used': 'Tablo 3.2.4', 'passed': True,
                'reason': skin['reason'],
            })

        eye = na_result['eye_result']
        if eye and eye['class']:
            passed_h.add(eye['h_code'])
            passed_pic.add(eye['pictogram'])
            if eye['signal'] == 'Danger':
                signal_danger = True
            override_entries.append({
                'cas': 'NON-ADDITIVITY', 'name': 'Tablo 3.3.4',
                'conc': '-', 'h_class': eye['class'], 'h_code': eye['h_code'],
                'cutoff_used': 'Tablo 3.3.4', 'passed': True,
                'reason': eye['reason'],
            })

        # Uyarı ekle
        na_flags = na_result['non_additivity_flags']
        flag_names = ', '.join(f"{f['name']} ({f['group']})" for f in na_flags)
        clp_result['warnings'].append(
            f"Non-additivity grubu tespit edildi: {flag_names}. "
            f"Skin/Eye sınıflandırması Tablo 3.2.4/3.3.4 ile yapıldı."
        )

        clp_result['passed'] = new_passed + override_entries
        clp_result['non_additivity'] = na_result

    # ─── 3. EUH ──────────────────────────────────────────────────────────────
    euh_result = check_euh(comp_list)
    clp_result['euh_codes'] = euh_result['euh_codes']
    clp_result['euh_details'] = euh_result['euh_details']
    clp_result['manual_check_euh'] = euh_result['manual_check']

    # ─── 4. STOT RE Hedef Organ Toplamı ─────────────────────────────────────
    from app.services.stot_re_service import calculate_stot_re

    stot_result = calculate_stot_re(comp_list)
    if stot_result['h_codes']:
        for res in stot_result['results']:
            passed_h.add(res['h_code'])
            if res['h_code'] == 'H372':
                passed_pic.add('GHS08')
                signal_danger = True
            else:  # H373
                passed_pic.add('GHS08')
                signal_warning = True
            clp_result.setdefault('passed', []).append({
                'cas': 'STOT RE', 'name': res['organ'],
                'conc': '-', 'h_class': res['h_class'], 'h_code': res['h_code'],
                'cutoff_used': 'Tablo 3.9.4', 'passed': True, 'reason': res['reason'],
            })
    clp_result['stot_re'] = stot_result
    for w in stot_result['warnings']:
        clp_result['warnings'].append(w)

    # ─── 5. Fiziksel Tehlike (Flam.Liq + Asp.Tox) ────────────────────────
    from app.services.physical_hazard_service import (
        calculate_physical_hazards, TestData
    )
    form = getattr(components[0], 'form', 'liquid') if components else 'liquid'
    user_fp = getattr(components[0], 'mixture_flash_point', None) if components else None

    # LD50 test verisi — ATE'ye aktarım
    # Kullanıcı LD50 girmişse comp_list'e ekle
    for i, comp in enumerate(components):
        if hasattr(comp, 'ate') and comp.ate:
            comp_list[i]['user_ate'] = {
                k: v for k, v in comp.ate.model_dump().items() if v is not None
            }

    phys = calculate_physical_hazards(comp_list, form, user_fp)
    for r in phys.primary + phys.extra:
        if r.h_code not in passed_h:
            passed_h.add(r.h_code)
            passed_pic.add(r.pictogram)
            if r.signal_word == 'Danger':
                signal_danger = True
            else:
                signal_warning = True
    clp_result['physical_hazards'] = {
        'primary': [vars(r) for r in phys.primary],
        'extra': [vars(r) for r in phys.extra],
        'warnings': phys.warnings,
    }
    for w in phys.warnings:
        clp_result['warnings'].append(w)

    # ─── 6. Birleşik sonuç ───────────────────────────────────────────────────
    clp_result['h_codes'] = sorted(list(passed_h))
    clp_result['pictograms'] = sorted(list(passed_pic))
    clp_result['signal_word'] = (
        'Danger' if signal_danger else ('Warning' if signal_warning else 'None')
    )

    return clp_result


# ─── FİZİKSEL TEHLİKE ENTEGRASYONU ─────────────────────────────────────────

from app.services.physical_hazard_service import (
    calculate_physical_hazards, TestData, PhysHazardOutput
)


def build_comp_test_data(component_test_data: dict) -> dict:
    """Schema ComponentTestData → service TestData dönüşümü"""
    return {
        cas: TestData(
            flash_point=td.get('flash_point'),
            boiling_point=td.get('boiling_point'),
            kinematic_viscosity=td.get('kinematic_viscosity'),
            ld50_oral=td.get('ld50_oral'),
            particle_size=td.get('particle_size'),
        )
        for cas, td in (component_test_data or {}).items()
    }


def add_physical_hazards(clp_result: dict, request: dict) -> dict:
    """
    CLP hesabı sonucuna fiziksel tehlikeleri ekle.
    clp_result: calculate_clp() çıktısı
    request: CLPCalculateRequestV2.model_dump()
    """
    comps = []
    for c in request.get('components', []):
        comps.append({
            'cas_no': c.get('cas_no', ''),
            'name': c.get('name', ''),
            'worst_case_conc': c.get('concentration_max') or c.get('concentration') or 0,
            'hazards': [],  # Fiziksel tehlike için bileşen H sınıfları şimdilik boş
        })

    test_data = build_comp_test_data(request.get('component_test_data') or {})
    phys = calculate_physical_hazards(
        comps=comps,
        mixture_form=request.get('form', 'liquid'),
        user_fp_override=request.get('mixture_flash_point'),
        comp_test_data=test_data,
    )

    clp_result['physical_hazards'] = {
        'primary': [
            {
                'h_code': r.h_code,
                'h_class': r.h_class,
                'category': r.category,
                'signal_word': r.signal_word,
                'pictogram': r.pictogram,
                'source': r.source,
                'note': r.note,
                'fp_value': r.fp_value,
                'total_pct': r.total_pct,
            }
            for r in phys.primary
        ],
        'extra': [
            {
                'h_code': r.h_code,
                'h_class': r.h_class,
                'category': r.category,
                'signal_word': r.signal_word,
                'pictogram': r.pictogram,
                'source': r.source,
            }
            for r in phys.extra
        ],
        'warnings': phys.warnings,
        'all_h_codes': phys.h_codes,
    }

    return clp_result
