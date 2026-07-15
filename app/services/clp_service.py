
# ─── SDSPASS CLP Hesaplayıcı (dict tabanlı, ORM bağımsız) ───────────────────
# CLP Annex I (KKDİK Ek-2) cut-off ve sınıflandırma kuralları
import re as _re
import logging as _logging

_log = _logging.getLogger(__name__)


def _parse_ph_range(ph_raw):
    """
    pH aralığını parse eder. Her türlü ayracı kabul eder:
      "2-4"   "2/4"   "2 4"   "2–4"   "2 to 4"   "2.5"
    Çıkış: (low, high) float tuple.
    Raises ValueError ayırt edilemezse.
    """
    if ph_raw is None:
        raise ValueError("pH None")
    s = str(ph_raw).strip()
    if not s:
        raise ValueError("pH boş")

    # "to" kelimesiyle (Ör: "2 to 4")
    m = _re.split(r'\s+to\s+', s, maxsplit=1, flags=_re.IGNORECASE)
    if len(m) == 2:
        return float(m[0].strip()), float(m[1].strip())

    # "/" ile
    if '/' in s:
        parts = s.split('/', 1)
        return float(parts[0].strip()), float(parts[1].strip())

    # em-dash veya en-dash (–, —)
    for dash in ('–', '—'):
        if dash in s:
            parts = s.split(dash, 1)
            return float(parts[0].strip()), float(parts[1].strip())

    # "-" ile (ama başta negatif işaret değilse)
    if '-' in s and not s.startswith('-'):
        parts = s.split('-', 1)
        return float(parts[0].strip()), float(parts[1].strip())

    # Boşlukla iki sayı (Ör: "2 4")
    parts = s.split()
    if len(parts) == 2:
        return float(parts[0]), float(parts[1])

    # Tek sayı
    val = float(s)
    return val, val


def normalize_ph_display(ph_raw) -> str:
    """
    pH değerini standart gösterim formatına çevirir.
    Çıkış örnekleri: "7.0"  →  "7"  |  "2-4"  →  "2 - 4"
    """
    try:
        low, high = _parse_ph_range(ph_raw)
        if low == high:
            return f"{low:g}"
        return f"{low:g} - {high:g}"
    except (ValueError, TypeError):
        return str(ph_raw) if ph_raw else ''

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
    # 3.2 Cilt — CLP Tablo 3.2.3 bireysel GCL
    # H314 için tek bileşen eşiği = %5 (toplamsal kural da %5'i kullanır)
    # %1-5 arası SC1 → 10×[SC1]+[SI2] ≥ %10 formülüyle H315 yakalanır
    "Skin Corr. 1":  {"h":"H314","cutoff":5.0, "signal":"Danger"},
    "Skin Corr. 1A": {"h":"H314","cutoff":5.0, "signal":"Danger"},
    "Skin Corr. 1B": {"h":"H314","cutoff":5.0, "signal":"Danger"},
    "Skin Corr. 1C": {"h":"H314","cutoff":5.0, "signal":"Danger"},
    "Skin Irrit. 2": {"h":"H315","cutoff":10.0,"signal":"Warning"},
    # 3.3 Göz — CLP Tablo 3.3.3 bireysel GCL
    # H318 için tek bileşen eşiği = %3 (toplamsal kural da %3'ü kullanır)
    # %1-3 arası ED1 → 10×[ED1]+[EI2] ≥ %10 formülüyle H319 yakalanır
    "Eye Dam. 1":    {"h":"H318","cutoff":3.0, "signal":"Danger"},
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
    "Repr. 1A": {"h":"H360","cutoff":0.3,"signal":"Danger"},   # SEA Tablo 3.7.2: GCL=%0,3
    "Repr. 1B": {"h":"H360","cutoff":0.3,"signal":"Danger"},   # SEA Tablo 3.7.2: GCL=%0,3
    "Repr. 2":  {"h":"H361","cutoff":3.0,"signal":"Warning"},  # SEA Tablo 3.7.2: GCL=%3
    "Repr. Lact.":{"h":"H362","cutoff":0.1,"signal":"Warning"},
    # 3.8 STOT SE
    "STOT SE 1": {"h":"H370","cutoff":10.0,"signal":"Danger"},
    "STOT SE 2": {"h":"H371","cutoff":10.0,"signal":"Warning"},
    "STOT SE 3": {"h":"H336","cutoff":20.0,"signal":"Warning"},  # varsayılan narkotik; H335 ayrıca _H_CODE_FALLBACK'te
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
    'H220','H222','H224','H225',
    'H228','H232',                   # H232: pirofor gaz → Danger (CLP Annex III)
    'H240','H241','H250','H251',     # H251: kendiliğinden ısınan Kat.1 → Danger
    'H260','H270','H271',
    # H272 — Ox. Liq. 2 (Danger) veya Ox. Liq. 3 (Warning) için aynı kod kullanılır.
    # Kategori bilinmeden Danger/Warning ayrımı yapılamaz → JS motoru ile tutarlı: Warning.
    'H300','H301','H304','H310','H311','H314','H318','H330','H331',
    'H334','H340','H350','H360','H360D','H360F','H360FD','H370','H372',
}

# CLP Annex I üstünlük (dominance) kuralları — alt kategori H kodlarını sil
DOMINANCE: dict = {
    'H314': ['H318', 'H315', 'H319'],
    'H318': ['H319'],
    'H300': ['H301', 'H302'], 'H301': ['H302'],
    'H310': ['H311', 'H312'], 'H311': ['H312'],
    'H330': ['H331', 'H332'], 'H331': ['H332'],
    'H370': ['H371', 'H335', 'H336'], 'H371': ['H335', 'H336'],
    # H372 → H373 kuralı KALDIRILDI: stot_re_service organ başına öncelik uygular;
    # farklı hedef organlar (örn. H372 sinir + H373 işitme) her ikisi de etikette görünmeli.
    'H340': ['H341'], 'H350': ['H351'], 'H360': ['H361'],
    'H410': ['H400', 'H411', 'H412', 'H413'],
    'H411': ['H412', 'H413'],
    'H412': ['H413'],
    'H224': ['H225', 'H226'], 'H225': ['H226'],
    'H271': ['H272'],
    'H260': ['H261'],                          # su reaktif Kat.1 > Kat.2/3 (CLP Tablo 2.12.1)
    'H240': ['H241', 'H242'], 'H241': ['H242'],
    'H251': ['H252'],
}


# h_code bazlı fallback — TR class name'leri (Cilt Hassas. 1A vb.) CLP_CUTOFFS_DICT'te
# eşleşmediğinde kullanılır. Acute tox, fiziksel tehlike ve özel döngüyle işlenen
# H314/H315/H318/H319 buraya dahil edilmez.
_H_CODE_FALLBACK: dict = {
    'H317': {"h": "H317", "cutoff": 1.0,  "signal": "Warning"},
    'H334': {"h": "H334", "cutoff": 0.1,  "signal": "Danger"},
    'H340': {"h": "H340", "cutoff": 0.1,  "signal": "Danger"},
    'H341': {"h": "H341", "cutoff": 1.0,  "signal": "Warning"},
    'H350': {"h": "H350", "cutoff": 0.1,  "signal": "Danger"},
    'H351': {"h": "H351", "cutoff": 1.0,  "signal": "Warning"},
    'H360': {"h": "H360", "cutoff": 0.3,  "signal": "Danger"},
    'H361': {"h": "H361", "cutoff": 3.0,  "signal": "Warning"},
    'H362': {"h": "H362", "cutoff": 0.1,  "signal": "Warning"},
    'H304': {"h": "H304", "cutoff": 10.0, "signal": "Danger"},
    'H370': {"h": "H370", "cutoff": 10.0, "signal": "Danger"},
    'H371': {"h": "H371", "cutoff": 10.0, "signal": "Warning"},
    # STOT SE 3 etki ayrımı: H335=solunum tahrişi, H336=narkotik — CLP §3.8.3.4.5
    'H335': {"h": "H335", "cutoff": 20.0, "signal": "Warning"},
    'H336': {"h": "H336", "cutoff": 20.0, "signal": "Warning"},
}


def _normalize_scl_list(scl_raw) -> list:
    """
    SCL verisini her zaman liste formatına normalize et.
    Frontend dict gönderebilir: {"H314": 2.0, "H315": 0.5}
    Backend liste bekler:        [{"h_code":"H314","c_min":2.0}, ...]
    """
    if isinstance(scl_raw, list):
        return scl_raw
    if isinstance(scl_raw, dict):
        return [{"h_code": k, "c_min": v} for k, v in scl_raw.items() if v is not None]
    return []


def _get_scl_cutoff(comp: dict, h_class: str, h_code4: str) -> float | None:
    """Bileşenin SCL listesinden ilgili H kodu/sınıfı için minimum c_min döndürür; yoksa None."""
    raw = _normalize_scl_list(comp.get("sclRaw") or comp.get("scl", []))
    matched_mins = []
    for scl in raw:
        sc = scl.get("h_class", scl.get("hazard", "")).replace("*", "").strip()
        sh = scl.get("h_code", "").replace("*", "").strip()[:4]
        if sc == h_class or (h_code4 and sh == h_code4):
            c_min = scl.get("c_min")
            if c_min is not None:
                matched_mins.append(float(c_min))
    return min(matched_mins) if matched_mins else None


_TR_HCLASS = {
    "Skin Corr. 1":  "Deri Korozyon 1",
    "Skin Corr. 1A": "Deri Korozyon 1A",
    "Skin Corr. 1B": "Deri Korozyon 1B",
    "Skin Corr. 1C": "Deri Korozyon 1C",
    "Skin Irrit. 2": "Deri Tahriş 2",
    "Eye Dam. 1":    "Göz Hasarı 1",
    "Eye Irrit. 2":  "Göz Tahriş 2",
}


def _cascade_reason(cas: str, conc: float, scl_list: list,
                    parent_h4: str, triggered_code: str, triggered_c_min: float,
                    triggered_cutoff: float, gcl_fallback: bool = False) -> str:
    """
    H314→H315/H319 ve H318→H319 cascade için tam denetim izi metni.
    Tüm üst sınıf eşiklerini (1A/1B/1C) sırayla listeler, her birinin
    sonucunu (elendi / TETİKLENDİ) gösterir.
    """
    steps = []
    # Üst sınıf (H314 veya H318) alt-eşiklerini yüksekten düşüğe sırala
    parent_bands = sorted(
        [s for s in scl_list
         if s.get("h_code", "").replace("*", "").strip()[:4] == parent_h4
         and s.get("c_min") is not None],
        key=lambda s: float(s["c_min"]),
        reverse=True,
    )
    for band in parent_bands:
        tr = _TR_HCLASS.get(band.get("h_class", ""), band.get("h_class", ""))
        cmin = float(band["c_min"])
        steps.append(f"{tr} (C≥%{cmin:.0f}): %{conc:.1f} < %{cmin:.0f} → elendi")

    tr_out = "Deri Tahriş 2" if triggered_code == "H315" else "Göz Tahriş 2"
    if gcl_fallback:
        steps.append(
            f"SKS bandı yok; {tr_out} GCL (C≥%{triggered_c_min:.0f}): "
            f"%{conc:.1f} ≥ %{triggered_c_min:.0f} → TETİKLENDİ"
        )
    else:
        steps.append(
            f"{tr_out} ({triggered_code}) SKS bandı "
            f"(%{triggered_c_min:.0f}≤C<%{triggered_cutoff:.0f}): "
            f"%{conc:.1f} bu aralıkta → TETİKLENDİ"
        )
    return f"{cas} %{conc:.1f} — CLP Ek-VI SKS: " + " | ".join(steps)


def _get_scl_entry_for_conc(scl_list: list, h_code4: str, conc: float) -> dict | None:
    """
    Konsantrasyona göre uygun SCL entry'sini bul — h_class override için.
    Örn: NaOH %3 → c_min=2, c_max=5 entry → "Skin Corr. 1B"
         NaOH %6 → c_min=5, c_max=null entry → "Skin Corr. 1A"
    """
    matches = []
    for s in scl_list:
        sh = (s.get("h_code", "") or "").replace("*", "").strip()[:4]
        if sh != h_code4:
            continue
        c_min = s.get("c_min")
        c_max = s.get("c_max")
        if c_min is None:
            continue
        if conc < float(c_min):
            continue
        if c_max is not None and conc >= float(c_max):
            continue
        matches.append(s)
    if not matches:
        return None
    # En yüksek c_min olan entry en spesifik aralık
    return max(matches, key=lambda s: float(s.get("c_min", 0)))


def classify_mixture_clp(components: list, mixture_ph: float = None,
                         mixture_form: str = '') -> dict:
    """
    CLP Annex I karışım sınıflandırması.
    Giriş: [{cas_no, name, concentration, hazards:[{h_class, h_code}]}]
           mixture_ph:   ölçülen karışım pH değeri (opsiyonel)
           mixture_form: ürün fiziksel formu ('liquid','sıvı','solid' vb.)
                         Not B maddeleri için sıvı formda sulu SCL verisi kullanılır.
    Çıkış: {h_codes, signal_word, passed:[{h_class,h_code,conc,reason}], warnings}
    """
    from app.services.substance_lookup import lookup_substance as _lu, _NOTE_B_CAS, _is_liquid

    passed = []
    warnings = []
    seen_h = set()

    # Not B override: sıvı ürünlerde gaz formu SCL'si yerine sulu form SCL'si kullan.
    # Bileşen hazards listesini AQ kaydındakiyle değiştir (gaz-özgü H280/H331 kalkar).
    _use_liquid = _is_liquid(mixture_form)
    def _maybe_override_comp(comp: dict) -> dict:
        cas = comp.get("cas_no", comp.get("cas", "")).strip()
        if _use_liquid and cas in _NOTE_B_CAS:
            aq = _lu(cas, form=mixture_form)
            if aq and aq.get('hazards'):
                comp = dict(comp)
                comp['hazards'] = aq['hazards']
                # sclRaw da AQ kaydından gelsin
                comp['sclRaw'] = aq.get('scl', [])
        return comp

    components = [_maybe_override_comp(c) for c in components]

    # STOT RE — hedef organ bazlı ayrı hesapla
    stot_comps = []
    for comp in components:
        cas = comp.get("cas_no", comp.get("cas", ""))
        conc = float(comp.get("concentration", comp.get("conc", 0)) or 0)
        hazards = comp.get("hazards", [])
        stot_comps.append({"cas": cas, "name": comp.get("name",""), "conc": conc, "hazards": hazards})

    # İkincil Skin/Eye kuralı — SCL dikkate alarak toplam (CLP Tablo 3.2.3/3.3.3)
    # SCL tanımlı bileşenler sadece SCL eşiğini aşarsa toplamına katkı yapar
    sum_corr1 = 0.0
    for comp in components:
        conc = float(comp.get("concentration", comp.get("conc", 0)) or 0)
        for h in comp.get("hazards", []):
            if h.get("h_class","") not in ("Skin Corr. 1","Skin Corr. 1A","Skin Corr. 1B","Skin Corr. 1C"):
                continue
            scl = _get_scl_cutoff(comp, h.get("h_class",""), "H314")
            effective = scl if scl is not None else 5.0  # SCL yoksa GCL (Skin Corr.1 = %5)
            if conc >= effective:
                sum_corr1 += conc
                break  # bileşen başına bir kez say

    # CLP §3.3.1.4: Skin Corr. 1 (H314) maddeler Eye Dam. 1 anlamına gelir.
    # Bileşen listesinde yalnızca H314 olsa bile göz toplamına dahil edilmeli.
    _EYE_DAM1_CLASSES = {"Eye Dam. 1", "Skin Corr. 1", "Skin Corr. 1A", "Skin Corr. 1B", "Skin Corr. 1C"}
    sum_eye_dam1 = 0.0
    for comp in components:
        conc = float(comp.get("concentration", comp.get("conc", 0)) or 0)
        for h in comp.get("hazards", []):
            if h.get("h_class","") not in _EYE_DAM1_CLASSES:
                continue
            # SCL: Eye Dam. 1 için H318, Skin Corr. için H314 SCL'sini kontrol et
            h_code_ref = "H318" if h.get("h_class","") == "Eye Dam. 1" else "H314"
            scl = _get_scl_cutoff(comp, h.get("h_class",""), h_code_ref)
            effective = scl if scl is not None else 3.0  # SCL yoksa GCL (Eye Dam.1 = %3)
            if conc >= effective:
                sum_eye_dam1 += conc
                break  # bileşen başına bir kez say

    # Eye Irrit. 2 toplamı: Eye Dam. 1 veya Skin Corr. 1 içeren bileşenler hariç.
    # Aynı bileşende H318/H314 + H319 birlikte bulunuyorsa sum_eye_dam1'e zaten katkı yaptı;
    # H319'a da eklemek çift sayıma yol açar (ECHA C&L çakışan bildirimlerde olabilir).
    sum_eye_irrit2 = 0.0
    for _comp_ei in components:
        if any(_hh.get("h_class", "") in _EYE_DAM1_CLASSES
               for _hh in _comp_ei.get("hazards", [])):
            continue
        for _hh in _comp_ei.get("hazards", []):
            if _hh.get("h_class", "") == "Eye Irrit. 2":
                sum_eye_irrit2 += float(_comp_ei.get("concentration", _comp_ei.get("conc", 0)) or 0)
                break

    # Her bileşen × her tehlike sınıfı
    for comp in components:
        cas = comp.get("cas_no", comp.get("cas", ""))
        conc = float(comp.get("concentration", comp.get("conc", 0)) or 0)
        for haz in comp.get("hazards", []):
            h_class = (haz.get("h_class") or "").replace("*","").strip()
            h_code  = (haz.get("h_code")  or "").replace("*","").replace(" ","")[:4]

            # Acute Tox. — karışım için ATE yöntemi (CLP Annex I 3.1.3.6) birincil yöntemdir.
            # Cutoff/konvansiyonel yöntem (Tablo 3.1.3) Acute Tox. için kullanılmaz;
            # ATE hesabı aşağıdaki calculate_clp() async fonksiyonunda yapılır.
            if h_class.startswith('Acute Tox.') or h_class.startswith('Akut Tok.'):
                continue

            rule = CLP_CUTOFFS_DICT.get(h_class)
            if not rule:
                # h_code bazlı fallback: TR class name'leri (örn. "Cilt Hassas. 1A")
                # CLP_CUTOFFS_DICT'te İngilizce key olduğundan eşleşmez; h_code ile ara.
                rule = _H_CODE_FALLBACK.get(h_code)
            if not rule:
                continue

            cutoff = rule["cutoff"]
            h = rule["h"]

            # STOT SE 3 etki ayrımı — CLP §3.8.3.4.5:
            # H335 (solunum tahrişi) ve H336 (narkotik) aynı kategoride farklı etkilerdir.
            # CLP_CUTOFFS_DICT varsayılanı H336; bileşen H335 veriyorsa karışıma H335 yazılır.
            if h_class == "STOT SE 3" and h_code == "H335":
                h = "H335"

            # SCL override — SEA Ek-6 / CLP Annex VI maddeye özel sınır GCL'nin YERİNE GEÇİCEKTİR.
            # Mevzuat: SEA Ek-I §1.2.1.3 / CLP 1272/2008 Art.10(3):
            # SCL büyük de olsa küçük de olsa GCL'yi tamamen devre dışı bırakır.
            # ÖNEMLİ: SCL h_code suffix içerebilir (H361f, H361fd, H314 *) — 4 karaktere normalize et
            # sclRaw: tam bant bilgisi (h_class + c_max) — 1A/1B override için zorunlu
            # scl: sadece dict fallback {"H314":2.0} — c_max ve h_class yok, yalnızca eşik kesimi
            scl_list = _normalize_scl_list(comp.get("sclRaw") or comp.get("scl", []))
            # Çok-bantlı SCL (1A/1B): tüm eşleşen bantların minimum c_min'i geçerli eşiktir.
            # İlk eşleşmeyi almak yanlış: 1A c_min=90 alınırsa %15 katkı atlanır.
            _h4 = h[:4]
            _scl_matched_mins = [
                float(s.get("c_min", 0))
                for s in scl_list
                if (s.get("h_class","") == h_class or
                    s.get("h_code","").replace("*","").strip()[:4] == _h4)
                and s.get("c_min") is not None
            ]
            if _scl_matched_mins:
                cutoff = min(_scl_matched_mins)

            # Fiziksel tehlikeler (cutoff=0.0) — fiziksel tehlike motoru tarafından da
            # hesaplanır; burada sadece B2.1 tablosu için ek kayıt tutulur.
            # Konsantrasyon eşiği 0.0 → görsel olarak anlamlı bir minimum (%1) kullan.
            _orig_cutoff = rule["cutoff"]   # SCL öncesi orijinal kesme değeri

            if conc < cutoff:
                # ── STOT SE 1→2 geçiş kuralı — CLP Tablo 3.8.3 ──────────────────
                # STOT SE 1 bileşen H370 eşiğinin altında ama H371 eşiğinin üstündeyse
                # karışım STOT SE 2 (H371) olarak sınıflandırılır.
                # H371 SCL varsa (ör. metanol %3) generic %1'in YERİNE geçer.
                if h == 'H370' and 'H371' not in seen_h:
                    # H371 SCL kontrolü
                    h371_cutoff = 1.0  # generic alt sınır
                    for scl_e in scl_list:
                        sc4 = scl_e.get("h_code", "").replace("*", "").strip()[:4]
                        if sc4 == "H371":
                            cm = scl_e.get("c_min")
                            if cm is not None:
                                h371_cutoff = float(cm)
                            break
                    if conc >= h371_cutoff:
                        seen_h.add('H371')
                        passed.append({
                            "h_class": "STOT SE 2",
                            "h_code":  "H371",
                            "conc":    conc,
                            "reason":  (
                                f"{cas} %{conc:.1f} — STOT SE 1 bileşen "
                                f"%{h371_cutoff} ≤ C < {cutoff}% → CLP Tablo 3.8.3 geçiş: STOT SE 2"
                            ),
                        })
                elif h == 'H314':
                    # ── Skin Corr. 1 → Skin Irrit. 2 / Eye Irrit. 2 cascade ─────────
                    # CLP Annex VI çok-bantlı SCL: bileşenin H314 eşiği aşılmadıysa
                    # sclRaw'daki H315/H319 bantlarına bak — asetik asit %10-25 bandı gibi.
                    # SCL bandı yoksa GCL (Skin Irrit. 2 = %10) kullan.
                    _H315_GCL = 10.0
                    _H319_GCL = 10.0
                    # H315
                    if 'H315' not in seen_h:
                        _h315_entry = _get_scl_entry_for_conc(scl_list, "H315", conc)
                        if _h315_entry is not None:
                            _c315 = float(_h315_entry.get("c_min", _H315_GCL))
                            seen_h.add('H315')
                            passed.append({
                                "h_class":       "Skin Irrit. 2",
                                "h_code":        "H315",
                                "conc":          conc,
                                "reason":        _cascade_reason(
                                    cas, conc, scl_list, "H314", "H315", _c315, cutoff
                                ),
                                "cutoff_source": "SKS",
                                "cutoff_value":  _c315,
                            })
                        elif conc >= _H315_GCL:
                            seen_h.add('H315')
                            passed.append({
                                "h_class":       "Skin Irrit. 2",
                                "h_code":        "H315",
                                "conc":          conc,
                                "reason":        _cascade_reason(
                                    cas, conc, scl_list, "H314", "H315", _H315_GCL, cutoff,
                                    gcl_fallback=True
                                ),
                                "cutoff_source": "GKS",
                                "cutoff_value":  _H315_GCL,
                            })
                    # H319
                    if 'H319' not in seen_h:
                        _h319_entry = _get_scl_entry_for_conc(scl_list, "H319", conc)
                        if _h319_entry is not None:
                            _c319 = float(_h319_entry.get("c_min", _H319_GCL))
                            seen_h.add('H319')
                            passed.append({
                                "h_class":       "Eye Irrit. 2",
                                "h_code":        "H319",
                                "conc":          conc,
                                "reason":        _cascade_reason(
                                    cas, conc, scl_list, "H314", "H319", _c319, cutoff
                                ),
                                "cutoff_source": "SKS",
                                "cutoff_value":  _c319,
                            })
                    if 'H315' not in seen_h and 'H319' not in seen_h:
                        warnings.append(
                            f"{cas} ({h_class} %{conc:.1f}) → "
                            f"cut-off %{cutoff} altı, H315/H319 cascade yok → dahil edilmedi"
                        )
                elif h == 'H318' and 'H319' not in seen_h:
                    # ── Eye Dam. 1 → Eye Irrit. 2 cascade — CLP Tablo 3.3.3 ──────────
                    _H319_GCL = 10.0
                    _h319_entry = _get_scl_entry_for_conc(scl_list, "H319", conc)
                    if _h319_entry is not None:
                        _c319 = float(_h319_entry.get("c_min", _H319_GCL))
                        seen_h.add('H319')
                        passed.append({
                            "h_class":       "Göz Tahriş 2",
                            "h_code":        "H319",
                            "conc":          conc,
                            "reason":        _cascade_reason(
                                cas, conc, scl_list, "H318", "H319", _c319, cutoff
                            ),
                            "cutoff_source": "SKS",
                            "cutoff_value":  _c319,
                        })
                    elif conc >= _H319_GCL:
                        seen_h.add('H319')
                        passed.append({
                            "h_class":       "Eye Irrit. 2",
                            "h_code":        "H319",
                            "conc":          conc,
                            "reason":        _cascade_reason(
                                cas, conc, scl_list, "H318", "H319", _H319_GCL, cutoff,
                                gcl_fallback=True
                            ),
                            "cutoff_source": "GKS",
                            "cutoff_value":  _H319_GCL,
                        })
                    else:
                        warnings.append(
                            f"{cas} ({h_class} %{conc:.1f}) → "
                            f"cut-off %{cutoff} altı, H319 cascade yok → dahil edilmedi"
                        )
                else:
                    warnings.append(
                        f"{cas} ({h_class} %{conc:.1f}) → "
                        f"cut-off %{cutoff} altı → dahil edilmedi"
                    )
                continue

            if h not in seen_h:
                seen_h.add(h)
                # Konsantrasyona göre uygun SCL entry'sinden h_class override (1A/1B ayrımı)
                # Örn: NaOH %3 → SCL entry class="Skin Corr. 1B" → h_class override
                scl_entry_conc = _get_scl_entry_for_conc(scl_list, h[:4], conc)
                effective_hclass = (scl_entry_conc or {}).get("h_class") or h_class
                # Kesme değeri gösterimi: 0.0 → "bileşen varlığı" (fiziksel tehlike)
                if _orig_cutoff == 0.0:
                    _cutoff_str = f'%{conc:.1f} (fiziksel tehlike, bileşen varlığı)'
                else:
                    _cutoff_str = f'%{conc:.1f} ≥ kesme %{cutoff}'
                _scl_used = bool(_scl_matched_mins)
                _cutoff_display = float(scl_entry_conc["c_min"]) if scl_entry_conc and scl_entry_conc.get("c_min") is not None else cutoff
                passed.append({
                    "h_class":       effective_hclass,
                    "h_code":        h,
                    "conc":          conc,
                    "reason":        f"{cas} {_cutoff_str}",
                    "cutoff_source": "SCL" if _scl_used else "GCL",
                    "cutoff_value":  _cutoff_display,
                })

    # ── pH Uç Değer Kontrolü — SEA/CLP Annex I Tablo 3.2.3 notu ─────────────────
    # Ölçülen karışım pH ≤ 2 VEYA ≥ 11.5 ise H314+H318 atanır.
    # ANCAK: CLP Rehberi Part 3 — korozif/tahrişçi bileşen için Annex VI SCL tanımlıysa
    # pH uygulanmaz; SCL türetilirken pH davranışı zaten hesaba katılmıştır (double counting).
    # pH yalnızca SCL'si olmayan güçlü asit/baz içeren karışımlar için geçerlidir.
    _CORR_CLASSES = {"Skin Corr. 1", "Skin Corr. 1A", "Skin Corr. 1B", "Skin Corr. 1C"}
    _has_scl_corrosive = any(
        _get_scl_cutoff(comp, h.get("h_class", ""), "H314") is not None
        for comp in components
        for h in comp.get("hazards", [])
        if h.get("h_class", "") in _CORR_CLASSES
    )
    if mixture_ph is not None and not _has_scl_corrosive:
        try:
            # _parse_ph_range: her türlü ayracı kabul eder (-, /, –, boşluk, "to")
            ph_low, ph_high = _parse_ph_range(mixture_ph)
            # Uç değer tetikleyici: alt ≤ 2 VEYA üst ≥ 11.5
            triggers_low  = ph_low  <= 2.0
            triggers_high = ph_high >= 11.5
            ph = ph_low if triggers_low else ph_high   # gerekçe metninde gösterilecek değer
            if triggers_low or triggers_high:
                direction = "≤ 2" if triggers_low else "≥ 11.5"
                _ph_display = normalize_ph_display(mixture_ph)
                # Aralık girilmişse hangi ucun kullanıldığını göster
                _ph_used = ph_low if triggers_low else ph_high
                _ph_used_str = f'{_ph_used:g}'
                if str(_ph_used_str) != str(_ph_display).replace(' ', ''):
                    _ph_basis = f'{_ph_display} → esas alınan: pH {_ph_used_str}'
                else:
                    _ph_basis = _ph_display
                ph_reason = (
                    f"Karışım pH = {_ph_basis} ({direction}) → "
                    f"SEA Tablo 3.2.3 notu: pH uç değeri → doğrudan sınıflandırma"
                )
                if "H314" not in seen_h:
                    seen_h.add("H314")
                    passed.append({
                        "h_class": "Skin Corr. 1",
                        "h_code":  "H314",
                        "conc":    100.0,
                        "reason":  ph_reason,
                    })
                if "H318" not in seen_h:
                    seen_h.add("H318")
                    passed.append({
                        "h_class": "Eye Dam. 1",
                        "h_code":  "H318",
                        "conc":    100.0,
                        "reason":  ph_reason,
                    })
        except (TypeError, ValueError):
            warnings.append(f"pH değeri okunamadı: {mixture_ph!r} — pH kontrolü atlandı")

    # ── Skin Toplamsal Sınıflandırma — CLP Tablo 3.2.3 ──────────────────────────
    sum_skin_irrit2 = sum(
        float(comp.get("concentration", comp.get("conc", 0)) or 0)
        for comp in components
        for h in comp.get("hazards", [])
        if h.get("h_class","") == "Skin Irrit. 2"
    )

    # Kural 1: ΣSkin Corr.1 ≥ %5 → H314 (toplamsal — birden fazla bileşen)
    # Tek bileşen <%1 cutoff altında kalsa bile Σ≥%5 → karışım Skin Corr. 1
    if "H314" not in seen_h and sum_corr1 >= 5.0:
        seen_h.add("H314")
        passed.append({"h_class":"Skin Corr. 1","h_code":"H314","conc":sum_corr1,
                       "reason":f"Toplama: Σ Cilt Aş.1=%{sum_corr1:.1f} ≥ %5 (CLP Tablo 3.2.3 toplamsal kural)"})

    # Kural 2: 10×ΣSkin Corr.1 + ΣSkin Irrit.2 ≥ %10 → H315 (H314 yoksa)
    # Bu ağırlıklı formül hem ΣKat2≥%10 hem de %1≤ΣKat1<%5 geçiş durumunu kapsar
    if "H314" not in seen_h and "H315" not in seen_h:
        weighted_skin = 10.0 * sum_corr1 + sum_skin_irrit2
        if weighted_skin >= 10.0:
            seen_h.add("H315")
            passed.append({"h_class":"Skin Irrit. 2","h_code":"H315","conc":weighted_skin,
                           "reason":(
                               f"Ağırlıklı: 10×{sum_corr1:.1f}+{sum_skin_irrit2:.1f}"
                               f"={weighted_skin:.1f} ≥ %10 (CLP Tablo 3.2.3)"
                           )})

    # ── Göz Toplamsal Sınıflandırma — CLP Tablo 3.3.3 ──────────────────────────
    # Kural 1: ΣEye Dam.1 ≥ %3 → H318 (toplamsal — birden fazla bileşen)
    if "H318" not in seen_h and sum_eye_dam1 >= 3.0:
        seen_h.add("H318")
        passed.append({"h_class":"Eye Dam. 1","h_code":"H318","conc":sum_eye_dam1,
                       "reason":f"Toplama: Σ Göz Hasar.1=%{sum_eye_dam1:.1f} ≥ %3 (CLP Tablo 3.3.3 toplamsal kural)"})

    # Kural 2: 10×ΣEye Dam.1 + ΣEye Irrit.2 ≥ %10 → H319 (H318 yoksa)
    if "H318" not in seen_h and "H319" not in seen_h:
        weighted_eye = 10.0 * sum_eye_dam1 + sum_eye_irrit2
        if weighted_eye >= 10.0:
            seen_h.add("H319")
            passed.append({"h_class":"Eye Irrit. 2","h_code":"H319","conc":weighted_eye,
                           "reason":(
                               f"Ağırlıklı: 10×{sum_eye_dam1:.1f}+{sum_eye_irrit2:.1f}"
                               f"={weighted_eye:.1f} ≥ %10 (CLP Tablo 3.3.3)"
                           )})

    # ── Dominance: üst kategori varsa alt kategorileri çıkar (CLP Annex I) ────────
    for dominant, subordinates in DOMINANCE.items():
        if dominant in seen_h:
            for sub in subordinates:
                if sub in seen_h:
                    seen_h.discard(sub)
                    passed = [p for p in passed if p.get("h_code") != sub]

    # Prefix dominance: herhangi bir H360x varsa tüm H361x kaldırılır
    if any(h.startswith('H360') for h in seen_h):
        for _h in list(seen_h):
            if _h.startswith('H361'):
                seen_h.discard(_h)
                passed = [p for p in passed if not p.get('h_code','').startswith('H361')]

    # Sub-kod çözümleme: H360/H361 → H360D/H361D vb. (bileşen h_code'larından)
    for _base, _classes in (('H360', ('Repr. 1A', 'Repr. 1B')), ('H361', ('Repr. 2',))):
        if _base not in seen_h:
            continue
        _cutoff = CLP_CUTOFFS_DICT[_classes[0]]['cutoff']
        _has_d = _has_f = False
        for _comp in components:
            _conc = float(_comp.get('concentration', _comp.get('conc', 0)) or 0)
            if _conc < _cutoff:
                continue
            for _haz in _comp.get('hazards', []):
                _hc   = (_haz.get('h_code')  or '').replace('*', '').strip()
                _hcls = (_haz.get('h_class') or '').replace('*', '').strip()
                if any(c in _hcls for c in _classes) and _hc.upper().startswith(_base) and len(_hc) > 4:
                    _sfx = _hc[4:].upper()
                    if 'D' in _sfx: _has_d = True
                    if 'F' in _sfx: _has_f = True
        if not (_has_d or _has_f):
            continue
        _resolved = _base + ('FD' if _has_d and _has_f else ('D' if _has_d else 'F'))
        seen_h.discard(_base)
        seen_h.add(_resolved)
        for _p in passed:
            if _p.get('h_code') == _base:
                _p['h_code'] = _resolved

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
# Tek kaynak: CLP_CUTOFFS_DICT'ten türetilir. Pictogram bilgisi eklenerek genişletilir.
# İkinci bir dict tutmak yerine CLP_CUTOFFS_DICT'i doğrudan kullanın.

_PICTOGRAM_MAP = {
    'H314':'GHS05','H315':'GHS07','H318':'GHS05','H319':'GHS07',
    'H317':'GHS07','H334':'GHS08',
    'H340':'GHS08','H341':'GHS08',
    'H350':'GHS08','H351':'GHS08',
    'H360':'GHS08','H361':'GHS08','H362':'GHS08',
    'H370':'GHS08','H371':'GHS08','H372':'GHS08','H373':'GHS08',
    'H335':'GHS07','H336':'GHS07',
    'H304':'GHS08',
    'H220':'GHS02','H221':'GHS02','H222':'GHS02','H223':'GHS02',
    'H224':'GHS02','H225':'GHS02','H226':'GHS02','H228':'GHS02',
    'H240':'GHS01','H241':'GHS01',
    'H250':'GHS02','H260':'GHS02','H261':'GHS02',
    'H270':'GHS03','H271':'GHS03','H272':'GHS03',
    'H280':'GHS04','H290':'GHS05',
    'H400':'GHS09','H410':'GHS09','H411':'GHS09','H412':'GHS09','H413':'GHS09',
}

CUTOFFS = {
    cls: {
        'cutoff':    rule['cutoff'],
        'pictogram': _PICTOGRAM_MAP.get(rule['h'], ''),
        'signal':    rule['signal'],
    }
    for cls, rule in CLP_CUTOFFS_DICT.items()
}

# ATE nokta tahminleri — SEA Tablo 3.1.2 / CLP Annex I Table 3.1.2
# UYARI: Bu değerler kategori SINIR değerleri değil, ATE formülünde kullanılan
# NOKTA TAHMİNLERİDİR. Örn: Oral Kat.4 üst sınırı 2000 mg/kg, nokta tahmini 500 mg/kg.
ATE_DEFAULTS = {
    'oral':             {'Acute Tox. 1': 0.5,   'Acute Tox. 2': 5,    'Acute Tox. 3': 100,  'Acute Tox. 4': 500},
    'dermal':           {'Acute Tox. 1': 5,     'Acute Tox. 2': 50,   'Acute Tox. 3': 300,  'Acute Tox. 4': 1100},
    'inhalation_dust':  {'Acute Tox. 1': 0.005, 'Acute Tox. 2': 0.05, 'Acute Tox. 3': 0.5,  'Acute Tox. 4': 1.5},
    'inhalation_vapour':{'Acute Tox. 1': 0.05,  'Acute Tox. 2': 0.5,  'Acute Tox. 3': 3.0,  'Acute Tox. 4': 11.0},
    'inhalation':       {'Acute Tox. 1': 0.05,  'Acute Tox. 2': 0.5,  'Acute Tox. 3': 3.0,  'Acute Tox. 4': 11.0},
}

# ATE sınıflandırma eşikleri — CLP Annex I Tablo 3.1.1 (kategori üst sınırları)
# ATE_DEFAULTS ile KARIŞTIRILMAMALI: ATE_DEFAULTS formül için nokta tahmini,
# ATE_THRESHOLDS ise hesaplanan karışım ATE'sini kategoriye çevirmek için kullanılır.
ATE_THRESHOLDS = {
    'oral':             {1: 5,     2: 50,    3: 300,   4: 2000},
    'dermal':           {1: 50,    2: 200,   3: 1000,  4: 2000},
    'inhalation_dust':  {1: 0.05,  2: 0.5,   3: 1.0,   4: 5.0},
    'inhalation_vapour':{1: 0.5,   2: 2.0,   3: 10.0,  4: 20.0},
    'inhalation':       {1: 0.5,   2: 2.0,   3: 10.0,  4: 20.0},
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


# H kodu → maruziyet rotası eşleştirmesi (CLP Annex I Bölüm 3.1)
# H300/H301/H302 = oral, H310/H311/H312 = dermal, H330/H331/H332 = inhalasyon
_H_CODE_TO_ROUTE: dict = {
    'H300': 'oral',   'H301': 'oral',   'H302': 'oral',
    'H310': 'dermal', 'H311': 'dermal', 'H312': 'dermal',
    'H330': 'inhalation', 'H331': 'inhalation', 'H332': 'inhalation',
}


def _get_ate_value(ate_data: dict, route: str, h_class: str) -> Optional[float]:
    """
    ATE değerini önce spesifik veriden, sonra kategori varsayılanından al.
    Spesifik ATE her zaman önceliklidir.
    """
    def _to_float(raw) -> Optional[float]:
        """Ham değeri güvenle float'a çevirir; dict ise 'value' anahtarını dener."""
        if raw is None:
            return None
        if isinstance(raw, dict):
            raw = raw.get('value') or raw.get('ate') or raw.get('val')
        try:
            val = float(raw)
            return val if val > 0 else None
        except (TypeError, ValueError):
            return None

    # Spesifik ATE varsa kullan
    val = _to_float(ate_data.get(route))
    if val is not None:
        return val
    # İnhalasyon alt türleri birbirinin yerine
    # inhalation_mgl = mg/L/4h ölçümü — buhar ve jenerik rota için kullan (toz değil)
    if route in ('inhalation_dust', 'inhalation_vapour', 'inhalation'):
        val = _to_float(ate_data.get('inhalation'))
        if val is not None:
            return val
        if route != 'inhalation_dust':
            val = _to_float(ate_data.get('inhalation_mgl'))
            if val is not None:
                return val
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


_LIQUID_FORMS = frozenset({
    'liquid', 'solution', 'sıvı', 'çözelti', 'aqueous', 'slurry', 'emulsion',
    'concentrate', 'konsantre', 'suspension', 'süspansiyon',
})

def _is_liquid_form(form: str) -> bool:
    """Ürün formu sıvı/çözelti ise True döner — inhalasyon toz rotasını atlamak için."""
    return bool(form) and form.lower() in _LIQUID_FORMS


# CLP §3.1.3.6.1(b): "akut toksik olmadığı varsayılan" maddeler
# ATEmix formülünden tamamen dışlanır — "bilinmiyor" sayılmaz.
_PRESUME_NOT_ACUTELY_TOXIC_CAS: frozenset = frozenset({
    '7732-18-5',  # su / water
    '57-50-1',    # sakkaroz / sucrose
    '50-99-7',    # glikoz / glucose
    '7647-14-5',  # NaCl
    '10043-52-4', # CaCl₂
    '497-19-8',   # Na₂CO₃
})


def _ate_core(items: list, form: str = '') -> tuple:
    """
    ATE karışım hesabının paylaşılan çekirdeği — sync ve async her ikisi de buraya çağırır.
    items: [{cas, conc (%), hazards, ate, source_priority, ate_unknown, name}]
    form:  ürün fiziksel formu — sıvı ise inhalasyon toz rotası atlanır.

    Döner: (ate_h_results, ate_b11, unknown_conc_per_route, ate_annex_vi_5000, stmt_needed)
      ate_h_results:         [{h_code, h_class, reason, cutoff_used, route, cat_num, mix_ate, _unk}]
      ate_b11:               {oral/dermal/inhal: {ateMix, resultCode, ...}}
      unknown_conc_per_route:{route: float (bilinmeyen konsantrasyon %)}
      ate_annex_vi_5000:     [name, ...] — Annex VI ATE=5000 alınan bileşenler
      stmt_needed:           True ise ≥%1 bilinmiyor bileşen var → B11 ifadesi ekle
    """
    ate_routes = list(ATE_DEFAULTS.keys())
    ate_sum: dict = {r: 0.0 for r in ate_routes}
    ate_comps: dict = {r: [] for r in ate_routes}
    unknown_conc: dict = {r: 0.0 for r in ate_routes}
    stmt_needed = False
    ate_annex_vi_5000: list = []

    for item in items:
        conc = float(item.get('conc') or 0)
        if conc <= 0:
            continue
        conc_frac = conc / 100.0
        cas = str(item.get('cas') or '').strip()

        # CLP §3.1.3.6.1(b): dışlama listesi en önce — ate_unknown'dan bağımsız
        # (DB lookup başarısız olsa bile su/glikoz/sakkaroz bilinmiyor sayılmaz)
        if cas in _PRESUME_NOT_ACUTELY_TOXIC_CAS:
            continue

        if item.get('ate_unknown', False):
            for _r in ate_routes:
                unknown_conc[_r] += conc
            if conc >= 1.0:
                stmt_needed = True
            continue

        hazards = item.get('hazards') or []
        _ACUTE_TOKS = {'H300','H301','H302','H310','H311','H312','H330','H331','H332'}
        has_acute_tox = any(
            (h.get('h_code') or '').replace('*','').strip()[:4] in _ACUTE_TOKS
            for h in hazards
        )

        if not has_acute_tox:
            if cas in _PRESUME_NOT_ACUTELY_TOXIC_CAS:
                continue  # bu dala artık ulaşılmaz — üstte yakalanır (savunma kopyası)
            source_priority = int(item.get('source_priority') or 4)
            if source_priority <= 2:
                for route in ate_routes:
                    ate_sum[route] += conc_frac / 5000.0
                ate_annex_vi_5000.append(item.get('name') or cas)
            else:
                for _r in ate_routes:
                    unknown_conc[_r] += conc
                if conc >= 1.0:
                    stmt_needed = True
            continue

        combined_ate = item.get('ate') or {}
        contributed_routes: set = set()
        source_priority = int(item.get('source_priority') or 4)

        for haz in hazards:
            h_code_raw = (haz.get('h_code') or '').replace('*','').strip()[:4]
            if h_code_raw not in _ACUTE_TOKS:
                continue
            hc = (haz.get('h_class') or '').replace('*','').strip()
            if hc.startswith('Akut Tok.'):
                hc = hc.replace('Akut Tok.', 'Acute Tox.')
            base_route = _H_CODE_TO_ROUTE.get(h_code_raw)
            if not base_route:
                routes_to_process = ate_routes
            elif base_route == 'inhalation':
                if combined_ate.get('inhalation_vapour'):
                    routes_to_process = ['inhalation_vapour', 'inhalation']
                elif combined_ate.get('inhalation_dust'):
                    routes_to_process = ['inhalation_dust', 'inhalation']
                elif combined_ate.get('inhalation_mgl') or _is_liquid_form(form):
                    routes_to_process = ['inhalation_vapour', 'inhalation']
                else:
                    routes_to_process = ['inhalation_vapour', 'inhalation_dust', 'inhalation']
            else:
                routes_to_process = [base_route]

            for route in routes_to_process:
                ate_val = _get_ate_value(combined_ate, route, hc)
                if ate_val and ate_val > 0:
                    ate_sum[route] += conc_frac / ate_val
                    contributed_routes.add(route)
                    _cn = item.get('name') or cas
                    if not any(x.get('name') == _cn for x in ate_comps[route]):
                        ate_comps[route].append({'name': _cn, 'conc': conc, 'code': h_code_raw, 'ate': ate_val})

        # Gayri-resmi kaynaklar için: katkı vermediği rotalar = bilinmiyor
        # Resmi kaynak (≤2) → katkısız rota = test edilmiş-negatif (bilinmiyor değil)
        if source_priority > 2:
            for _r in ate_routes:
                if _r not in contributed_routes:
                    unknown_conc[_r] += conc
                    if conc >= 1.0:
                        stmt_needed = True

    # ── Sınıflandırma ──────────────────────────────────────────────────────
    _route_labels = {
        'oral': 'oral', 'dermal': 'dermal',
        'inhalation': 'inhalasyon', 'inhalation_vapour': 'inhalasyon (buhar)',
        'inhalation_dust': 'inhalasyon (toz)',
    }
    _ROUTE_TO_B11 = {
        'oral': 'oral', 'dermal': 'dermal',
        'inhalation': 'inhal', 'inhalation_vapour': 'inhal', 'inhalation_dust': 'inhal',
    }
    _CLASSIFY_B11 = {
        'oral':   [(5,'H300'),(50,'H300'),(300,'H301'),(2000,'H302')],
        'dermal': [(50,'H310'),(200,'H310'),(1000,'H311'),(2000,'H312')],
        'inhal':  [(0.5,'H330'),(2.0,'H330'),(10,'H331'),(20,'H332')],
    }
    ate_h_results: list = []
    seen_h: set = set()
    ate_b11: dict = {}

    for route, total in ate_sum.items():
        if total <= 0:
            continue
        _unk = unknown_conc[route]
        mix_ate = ((100.0 - _unk) / 100.0 / total
                   if _unk > 10.0 else 1.0 / total)
        mix_ate_cmp = round(mix_ate, 6)  # FP gürültüsünü gider
        thresholds = ATE_THRESHOLDS.get(route, {})
        for n in [1, 2, 3, 4]:
            if mix_ate_cmp <= thresholds.get(n, float('inf')):
                hcode = ATE_HCODES[route][n]
                if hcode not in seen_h:
                    seen_h.add(hcode)
                    ate_h_results.append({
                        'h_code':      hcode,
                        'h_class':     f'Acute Tox. {n} ({_route_labels.get(route, route)})',
                        'reason':      (
                            f'Karışım ATE={mix_ate_cmp} ≤ {thresholds[n]} (CLP Tablo 3.1.1 Kat{n})'
                            + (f' [Revize: %{_unk:.1f} bilinmiyor]' if _unk > 10.0 else '')
                        ),
                        'cutoff_used': f'ATEmix={mix_ate_cmp}',
                        'route':       route,
                        'cat_num':     n,
                        'mix_ate':     mix_ate_cmp,
                        '_unk':        _unk,
                    })
                break
        try:
            b11_key = _ROUTE_TO_B11.get(route, 'inhal')
            mix_ate_r = round(mix_ate, 2)
            if b11_key not in ate_b11 or mix_ate_r < ate_b11[b11_key]['ateMix']:
                result_code_b11 = None
                for threshold_b11, hcode_b11 in _CLASSIFY_B11.get(b11_key, []):
                    if mix_ate_r <= threshold_b11:
                        result_code_b11 = hcode_b11
                        break
                ate_b11[b11_key] = {
                    'ateMix':          mix_ate_r,
                    'resultCode':      result_code_b11,
                    'unknownPct':      round(_unk, 1),
                    'revisedFormula':  _unk > 10.0,
                    'statementNeeded': stmt_needed,
                    'components':      ate_comps.get(route, []),
                }
        except Exception as _e:
            _log.warning("ate_b11 hesaplanamadı (rota=%s, mix_ate=%s): %s", route, mix_ate, _e)

    return ate_h_results, ate_b11, unknown_conc, ate_annex_vi_5000, stmt_needed


def calculate_ate_health_h_codes(components: list, form: str = '') -> tuple:
    """
    Sync ATE sağlık tehlike hesabı — PDF endpoint için (DB gerekmez).
    classify_mixture_clp Acute Tox. sınıfını atladığı için bu fonksiyon ayrı çağrılır.
    form: ürün fiziksel formu ('liquid','solution',...) — sıvı ise toz/sis rotası atlanır.
    Döndürür: ([{'h_code','h_class','reason','cutoff_used'}], ate_b11_dict) — baskınlık uygulanmış
    """
    items = []
    for c in components:
        conc = float(c.get('concMax') or c.get('conc') or c.get('concentration') or 0)
        if conc <= 0:
            continue

        # Frontend ate alanı: {oral, dermal, inhal} — inhal → inhalation normalize et
        _fe_ate = dict(c.get('ate') or {})
        if _fe_ate.get('inhal') is not None:
            _fe_ate['inhalation'] = _fe_ate['inhal']
        combined_ate = {**_fe_ate, **(c.get('user_ate') or {})}

        # DB fallback: inhalasyon ATE yoksa substance DB'den çek
        _ATE_KEYS = ('inhalation', 'inhalation_vapour', 'inhalation_dust', 'inhalation_mgl')
        if not any(combined_ate.get(k) for k in _ATE_KEYS):
            _cas = str(c.get('cas') or '').strip()
            if _cas:
                try:
                    from app.services.substance_lookup import lookup_substance as _sl
                    _sub = _sl(_cas)
                    if _sub and _sub.get('ate'):
                        combined_ate = {**_sub['ate'], **combined_ate}
                except Exception as _e:
                    _log.warning("substance_lookup ATE alınamadı (cas=%s): %s", _cas, _e)

        items.append({
            'cas':             str(c.get('cas') or c.get('cas_no') or '').strip(),
            'conc':            conc,
            'hazards':         c.get('hazards') or [],
            'ate':             combined_ate,
            'source_priority': c.get('source_priority', 4),
            'ate_unknown':     bool(c.get('ate_unknown', False)),
            'name':            c.get('name_tr', '') or c.get('name', '') or str(c.get('cas', '')),
        })

    ate_h_results, ate_b11, _unk_r, _ann5000, _stmt = _ate_core(items, form)

    # Baskınlık: H300>H301>H302, H310>H311>H312, H330>H331>H332
    _h_set = {e['h_code'] for e in ate_h_results}
    _dominated: set = set()
    for _dom, _subs in [('H300', ['H301', 'H302']), ('H301', ['H302']),
                         ('H310', ['H311', 'H312']), ('H311', ['H312']),
                         ('H330', ['H331', 'H332']), ('H331', ['H332'])]:
        if _dom in _h_set:
            _dominated.update(_subs)
    return [e for e in ate_h_results if e['h_code'] not in _dominated], ate_b11


async def calculate_clp(db: AsyncSession, components: List[Any], form: str = '') -> Dict:
    """
    Ana CLP hesaplama fonksiyonu — v3
    CLP Regulation (EC) No 1272/2008, Annex I'e göre
    form: ürün fiziksel formu — sıvı ise inhalasyon toz rotası atlanır.
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

        # Spesifik ATE verisi (ate_dict: kullanıcı girişi; ate_unknown: bilinmiyor beyanı)
        user_ate    = comp.ate_dict if hasattr(comp, 'ate_dict') else {}
        ate_unknown = getattr(comp, 'ate_unknown', False) or False

        # Madde formu (NOTE 1 için)
        form = getattr(comp, 'form', None)

        # CLP verisi çek
        data = await get_clp_data(db, cas)

        enriched.append({
            'cas':         cas,
            'conc':        conc,
            'data':        data,
            'name':        getattr(comp, 'name', None) or (data.get('chemical_name') if data else cas),
            'user_ate':    user_ate,
            'ate_unknown': ate_unknown,
            'form':        form,
            'conc_min':    getattr(comp, 'concentration_min', None),
            'conc_max':    getattr(comp, 'concentration_max', None),
        })

    # ─── ADIM 1: ATE TOPLAMA ────────────────────────────────────────────
    # _ate_core: sync ve async her ikisinin de paylaştığı hesaplama çekirdeği
    _ate_items = []
    for item in enriched:
        data = item['data']
        base_ate = (data.get('ate') or {}) if data else {}
        _ate_items.append({
            'cas':             item['cas'],
            'conc':            item['conc'],
            'hazards':         (data.get('hazards') or []) if data else [],
            'ate':             {**base_ate, **(item['user_ate'] or {})},
            'source_priority': (data.get('source_priority', 4) if data else 4),
            # "veri yok" durumu ate_unknown=True'ya katla — _ate_core tek yol bilir
            'ate_unknown':     (
                bool(item.get('ate_unknown', False))
                or not data
                or data.get('source') == 'not_found'
            ),
            'name':            item['name'] or item['cas'],
        })

    _ate_h, _ate_b11_ignored, _unk_r, _ate_ann5000, _stmt = _ate_core(_ate_items, form)

    # Sonuçları results_passed'a aktar
    for _r in _ate_h:
        _hcode = _r['h_code']
        _cat   = _r['cat_num']
        _route = _r['route']
        _mxate = _r['mix_ate']
        _unk   = _r['_unk']
        results_passed.append({
            'cas':         'KARIŞIM',
            'name':        f'ATE ({_route})',
            'conc':        '-',
            'h_class':     f'Acute Tox. {_cat}',
            'h_code':      _hcode,
            'cutoff_used': f'ATE={_mxate}',
            'passed':      True,
            'reason':      (
                f'Karışım ATE={_mxate} ≤ {ATE_THRESHOLDS.get(_route, {}).get(_cat)} '
                f'(Tablo 3.1.1 Kat{_cat})'
                + (f' [Revize formül: %{_unk:.1f} bilinmiyor — CLP 3.1.3.6.2.3]'
                   if _unk > 10.0 else '')
            ),
        })
        passed_h_codes.add(_hcode)
        passed_pictograms.add(ATE_PICS[_cat])
        if ATE_SIGS[_cat] == 'Danger':
            signal_danger = True
        else:
            signal_warning = True

    # Bilinmeyen bileşen uyarıları (per-route maksimum kullan)
    _unk_max = max(_unk_r.values(), default=0.0)
    if _unk_max > 0:
        warnings.append(
            f"ATEmix: Karışımın %{_unk_max:.1f}'i için akut toksisite verisi "
            f"güvenilir kaynakta bulunamamıştır "
            f"({'Revize formül uygulandı — CLP 3.1.3.6.2.3' if _unk_max > 10 else 'Standart formül kullanıldı'})."
        )
    if _ate_ann5000:
        warnings.append(
            f"ATEmix: {len(_ate_ann5000)} bileşen ({', '.join(_ate_ann5000[:3])}"
            f"{'...' if len(_ate_ann5000) > 3 else ''}) Annex VI'da akut toksik "
            f"sınıflandırılmamış → ATE=5000 alındı (muhafazakâr)."
        )

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

            # SCL kontrolü — SEA Ek-I §1.2.1.3 / CLP Art.10(3)
            # SCL h_code suffix içerebilir (H361f, H361fd, H314 *) → 4 karaktere normalize et
            # h_class ile de eşleştir (h_code yoksa veya farklı suffix varsa)
            cutoff = None
            scl_note = ''
            hcode4 = hcode[:4] if hcode else ''
            for scl in scl_list:
                scl_hclass = scl.get('h_class', scl.get('hazard', '')).replace('*', '').strip()
                scl_hcode4 = scl.get('h_code', '').replace('*', '').strip()[:4]
                if scl_hclass == hc or (hcode4 and scl_hcode4 == hcode4):
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

    # ─── ADIM 2b: SKIN/GÖZ TOPLAMSAL SINIFLANDIRMA — CLP Tablo 3.2.3 / 3.3.3 ──────
    sum_corr1         = 0.0  # Skin Corr. 1/1A/1B/1C bileşen toplamı
    sum_skin_irrit2_b = 0.0  # Skin Irrit. 2 bileşen toplamı
    sum_eye_dam1      = 0.0  # Eye Dam. 1 bileşen toplamı
    sum_eye_irrit2_b  = 0.0  # Eye Irrit. 2 bileşen toplamı

    _EYE_DAM1_HCS = {'Eye Dam. 1', 'Skin Corr. 1', 'Skin Corr. 1A', 'Skin Corr. 1B', 'Skin Corr. 1C'}
    for item in enriched:
        if not item['data']:
            continue
        conc = item['conc']
        _item_hcs = {haz.get('h_class', '').replace('*', '').strip()
                     for haz in item['data'].get('hazards', [])}
        _has_eye_dam1 = bool(_item_hcs & _EYE_DAM1_HCS)
        for haz in item['data'].get('hazards', []):
            hc = haz.get('h_class', '').replace('*', '').strip()
            if hc in ('Skin Corr. 1', 'Skin Corr. 1A', 'Skin Corr. 1B', 'Skin Corr. 1C'):
                sum_corr1 += conc
            if hc == 'Skin Irrit. 2':
                sum_skin_irrit2_b += conc
            if hc == 'Eye Dam. 1':
                sum_eye_dam1 += conc
            if hc == 'Eye Irrit. 2' and not _has_eye_dam1:
                # Eye Dam. 1 / Skin Corr. 1 taşıyan bileşen zaten sum_eye_dam1'e dahil;
                # H319'a da eklemek çift sayıma yol açar (ECHA C&L çakışan bildirimlerde olabilir).
                sum_eye_irrit2_b += conc

    # Kural 1: ΣSkin Corr.1 ≥ %5 → H314 (toplamsal — Tablo 3.2.3 additivity)
    if 'H314' not in passed_h_codes and sum_corr1 >= 5.0:
        passed_h_codes.add('H314')
        passed_pictograms.add('GHS05')
        signal_danger = True
        results_passed.append({
            'cas': 'KARIŞIM', 'name': 'Skin Corr. 1 (toplamsal kural)',
            'conc': sum_corr1, 'h_class': 'Skin Corr. 1', 'h_code': 'H314',
            'cutoff_used': 'Tablo 3.2.3 Σ≥%5',
            'passed': True,
            'reason': f'Toplama: Σ Cilt Aş.1 = %{sum_corr1:.1f} ≥ %5 → H314 (CLP Tablo 3.2.3 toplamsal kural)',
        })
        warnings.append(
            f"Toplamsal kural: Σ Cilt Aş.1 = %{sum_corr1:.1f} ≥ %5 → H314 Cilt Aş. 1 atandı (CLP Tablo 3.2.3)"
        )

    # Kural 2: 10×ΣSkin Corr.1 + ΣSkin Irrit.2 ≥ %10 → H315 (H314 yoksa — Tablo 3.2.3)
    if 'H314' not in passed_h_codes and 'H315' not in passed_h_codes:
        weighted_skin_b = 10.0 * sum_corr1 + sum_skin_irrit2_b
        if weighted_skin_b >= 10.0:
            passed_h_codes.add('H315')
            passed_pictograms.add('GHS07')
            signal_warning = True
            results_passed.append({
                'cas': 'KARIŞIM', 'name': 'Skin Irrit. 2 (ağırlıklı formül)',
                'conc': weighted_skin_b, 'h_class': 'Skin Irrit. 2', 'h_code': 'H315',
                'cutoff_used': 'Tablo 3.2.3 10×Kat1+Kat2',
                'passed': True,
                'reason': (
                    f'Ağırlıklı: 10×{sum_corr1:.1f}+{sum_skin_irrit2_b:.1f}'
                    f'={weighted_skin_b:.1f} ≥ %10 → H315 (CLP Tablo 3.2.3)'
                ),
            })
            warnings.append(
                f"Ağırlıklı skin formülü: 10×{sum_corr1:.1f}+{sum_skin_irrit2_b:.1f}"
                f"={weighted_skin_b:.1f} ≥ %10 → H315 Cilt Tahriş. 2 uygulandı (CLP Tablo 3.2.3)"
            )

    # Kural 1: ΣEye Dam.1 ≥ %3 → H318 (toplamsal — Tablo 3.3.3 additivity)
    if 'H318' not in passed_h_codes and sum_eye_dam1 >= 3.0:
        passed_h_codes.add('H318')
        passed_pictograms.add('GHS05')
        signal_danger = True
        results_passed.append({
            'cas': 'KARIŞIM', 'name': 'Eye Dam. 1 (toplamsal kural)',
            'conc': sum_eye_dam1, 'h_class': 'Eye Dam. 1', 'h_code': 'H318',
            'cutoff_used': 'Tablo 3.3.3 Σ≥%3',
            'passed': True,
            'reason': f'Toplama: Σ Göz Hasar.1 = %{sum_eye_dam1:.1f} ≥ %3 → H318 (CLP Tablo 3.3.3 toplamsal kural)',
        })
        warnings.append(
            f"Toplamsal kural: Σ Göz Hasar.1 = %{sum_eye_dam1:.1f} ≥ %3 → H318 Göz Hasar. 1 atandı (CLP Tablo 3.3.3)"
        )

    # Kural 2: 10×ΣEye Dam.1 + ΣEye Irrit.2 ≥ %10 → H319 (H318 yoksa — Tablo 3.3.3)
    if 'H318' not in passed_h_codes and 'H319' not in passed_h_codes:
        weighted_eye_b = 10.0 * sum_eye_dam1 + sum_eye_irrit2_b
        if weighted_eye_b >= 10.0:
            passed_h_codes.add('H319')
            passed_pictograms.add('GHS07')
            signal_warning = True
            results_passed.append({
                'cas': 'KARIŞIM', 'name': 'Eye Irrit. 2 (ağırlıklı formül)',
                'conc': weighted_eye_b, 'h_class': 'Eye Irrit. 2', 'h_code': 'H319',
                'cutoff_used': 'Tablo 3.3.3 10×Kat1+Kat2',
                'passed': True,
                'reason': (
                    f'Ağırlıklı: 10×{sum_eye_dam1:.1f}+{sum_eye_irrit2_b:.1f}'
                    f'={weighted_eye_b:.1f} ≥ %10 → H319 (CLP Tablo 3.3.3)'
                ),
            })
            warnings.append(
                f"Ağırlıklı göz formülü: 10×{sum_eye_dam1:.1f}+{sum_eye_irrit2_b:.1f}"
                f"={weighted_eye_b:.1f} ≥ %10 → H319 Göz Tahriş. 2 uygulandı (CLP Tablo 3.3.3)"
            )

    # ─── ADIM 3: AQUATIC (CLP Annex I Tablo 4.1.3) ──────────────────────
    # SEA Tablo 4.1.1/4.1.2 — JS eco_engine.js ile aynı formül
    # K1 = Σ(Ci × M_kronik)/100  için Kronik Kat.1 (H410 bileşenleri) — M-faktörlü
    # K2 = Σ(Ci)/100             için Kronik Kat.2 (H411 bileşenleri) — düz
    # K3 = Σ(Ci)/100             için Kronik Kat.3/4 (H412/H413 bileşenleri) — düz
    # CLP eşiği %0.25; K değerleri /100 kesir → eşik 0.0025 kullanılır
    # H410: K1 ≥ 0.0025  (= %0.25)
    # H411: 10×K1 + K2 ≥ 0.0025
    # H412: 100×K1 + 10×K2 + K3 ≥ 0.0025
    # H413: K1+K2+K3 ≥ 0.0025 (düz toplam)
    sum_acute_m    = 0.0
    sum_chronic_k1 = 0.0   # Kronik Kat.1 — M-faktörlü
    sum_chronic_k2 = 0.0   # Kronik Kat.2 — düz (M=1 efektif)
    sum_chronic_k3 = 0.0   # Kronik Kat.3 ve 4 — düz

    _AQUATIC_CLASS_MAP = {
        'Aquatic Acute 1':   'H400', 'Aquatic Chronic 1': 'H410',
        'Aquatic Chronic 2': 'H411', 'Aquatic Chronic 3': 'H412',
        'Aquatic Chronic 4': 'H413',
    }

    for item in enriched:
        if not item['data']:
            continue
        conc = item['conc']
        data = item['data']
        m_acute   = data.get('m_factors', {}).get('acute',   1)
        m_chronic = data.get('m_factors', {}).get('chronic', 1)

        # Bileşenin tüm sucul tehlike kodlarını bir kez topla (Set).
        # Spinosad gibi maddeler hazard listesinde hem H400 hem H410 taşıyabilir;
        # satır bazlı döngü çift sayıma yol açar — bileşen bazlı Set ile önlenir.
        haz_set = set()
        for haz in data.get('hazards', []):
            hc   = haz.get('h_class',  '').replace('*', '').strip()
            hcod = haz.get('h_code',   '').replace('*', '').strip()[:4]
            if hcod in ('H400', 'H410', 'H411', 'H412', 'H413'):
                haz_set.add(hcod)
            if hc in _AQUATIC_CLASS_MAP:
                haz_set.add(_AQUATIC_CLASS_MAP[hc])

        # H410 (Kronik Kat.1) → akut+kronik katkı; H400 varsa atla (çift sayım önleme)
        if 'H410' in haz_set:
            inc_thr = 0.1 / max(m_chronic, 1)
            if conc >= inc_thr:
                sum_acute_m    += (conc * m_acute)   / 100
                sum_chronic_k1 += (conc * m_chronic) / 100
        elif 'H400' in haz_set:
            # H400 (Akut Kat.1) → yalnızca H410 yoksa; dahil etme eşiği ≥ 0.1%/M_akut
            if conc >= (0.1 / max(m_acute, 1)):
                sum_acute_m += (conc * m_acute) / 100

        # H411 (Kronik Kat.2) → eşik ≥ 1.0%
        if 'H411' in haz_set and conc >= 1.0:
            sum_chronic_k2 += conc / 100

        # H412/H413 (Kronik Kat.3/4) → eşik ≥ 1.0%
        if ('H412' in haz_set or 'H413' in haz_set) and conc >= 1.0:
            sum_chronic_k3 += conc / 100

    h411_sum = 10 * sum_chronic_k1 + sum_chronic_k2
    h412_sum = 100 * sum_chronic_k1 + 10 * sum_chronic_k2 + sum_chronic_k3
    h413_sum = sum_chronic_k1 + sum_chronic_k2 + sum_chronic_k3

    # Aquatic Acute 1 — H410 yoksa bağımsız H400 kontrolü
    has_h410_chronic = False
    # CLP Ek-I Tablo 4.1.0 — eşik %0.25; K değerleri /100 kesir olarak saklandığından
    # karşılaştırma 0.0025 (= 0.25/100) ile yapılır. Eski kod 0.25 kullanıyordu → 100× hata.
    if sum_chronic_k1 >= 0.0025:
        has_h410_chronic = True
        passed_h_codes.add('H410')
        passed_pictograms.add('GHS09')
        signal_warning = True
        results_passed.append({
            'cas': 'KARIŞIM', 'name': 'Aquatic Chronic 1',
            'conc': '-', 'h_class': 'Aquatic Chronic 1', 'h_code': 'H410',
            'cutoff_used': 'Σ(Ci×M_kr)≥%0.25 → K1=Σ/100≥0.0025 (SEA Tablo 4.1.2)',
            'passed': True,
            'reason': f'K1=Σ(Ci×M_kr)/100={sum_chronic_k1:.4f}≥0.0025 [=%{sum_chronic_k1*100:.2f}≥%0.25]',
        })
    elif h411_sum >= 0.0025:
        passed_h_codes.add('H411')
        passed_pictograms.add('GHS09')
        results_passed.append({
            'cas': 'KARIŞIM', 'name': 'Aquatic Chronic 2',
            'conc': '-', 'h_class': 'Aquatic Chronic 2', 'h_code': 'H411',
            'cutoff_used': '10×Σ(Ci×M)+Σ(Ci_K2)≥%0.25 → toplam/100≥0.0025 (SEA Tablo 4.1.2)',
            'passed': True,
            'reason': f'10×K1+K2=10×{sum_chronic_k1:.4f}+{sum_chronic_k2:.4f}={h411_sum:.4f}≥0.0025',
        })
    elif h412_sum >= 0.0025:
        passed_h_codes.add('H412')
        results_passed.append({
            'cas': 'KARIŞIM', 'name': 'Aquatic Chronic 3',
            'conc': '-', 'h_class': 'Aquatic Chronic 3', 'h_code': 'H412',
            'cutoff_used': '100×K1+10×K2+K3≥0.0025 (SEA Tablo 4.1.2)',
            'passed': True,
            'reason': f'100×{sum_chronic_k1:.4f}+10×{sum_chronic_k2:.4f}+{sum_chronic_k3:.4f}={h412_sum:.4f}≥0.0025',
        })
    elif h413_sum >= 0.0025:
        passed_h_codes.add('H413')
        results_passed.append({
            'cas': 'KARIŞIM', 'name': 'Aquatic Chronic 4',
            'conc': '-', 'h_class': 'Aquatic Chronic 4', 'h_code': 'H413',
            'cutoff_used': 'Σ(Ci tüm kronik)/100≥0.0025 (SEA Tablo 4.1.2)',
            'passed': True,
            'reason': f'K1+K2+K3={h413_sum:.4f}≥0.0025',
        })

    # H400: H410 yoksa ve akut eşik aşılmışsa (SEA Tablo 4.1.1)
    if sum_acute_m >= 0.0025 and not has_h410_chronic:
        passed_h_codes.add('H400')
        passed_pictograms.add('GHS09')
        signal_warning = True
        results_passed.append({
            'cas': 'KARIŞIM', 'name': 'Aquatic Acute 1',
            'conc': '-', 'h_class': 'Aquatic Acute 1', 'h_code': 'H400',
            'cutoff_used': 'Σ(Ci×M_ak)/100≥0.0025 [=%0.25] (SEA Tablo 4.1.1)',
            'passed': True,
            'reason': f'Σ(Ci×M_ak)/100={sum_acute_m:.4f}≥0.0025 [=%{sum_acute_m*100:.2f}≥%0.25]',
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
    from app.services.stot_engine import calculate as calculate_stot_re

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
    user_visc = getattr(components[0], 'mixture_kinematic_viscosity', None) if components else None

    # LD50 test verisi — ATE'ye aktarım
    # Kullanıcı LD50 girmişse comp_list'e ekle
    for i, comp in enumerate(components):
        if hasattr(comp, 'ate') and comp.ate:
            comp_list[i]['user_ate'] = {
                k: v for k, v in comp.ate.model_dump().items() if v is not None
            }

    phys = calculate_physical_hazards(comp_list, form, user_fp, mixture_kinematic_viscosity=user_visc)
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
    mixture_visc = (
        request.get('mixture_kinematic_viscosity')
        or request.get('phys_props', {}).get('viscosity')
    )
    phys = calculate_physical_hazards(
        comps=comps,
        mixture_form=request.get('form', 'liquid'),
        user_fp_override=request.get('mixture_flash_point'),
        comp_test_data=test_data,
        mixture_kinematic_viscosity=mixture_visc,
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
