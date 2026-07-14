"""
SDS XML Üreticisi — sds_data dict'inden standart XML üretir.
Denetim AI'ı bu XML'i okur; _build_sds_text'in yerini alır.
"""
import xml.etree.ElementTree as ET
from xml.dom import minidom


def _sub(parent: ET.Element, tag: str, text: str | None = None) -> ET.Element:
    el = ET.SubElement(parent, tag)
    if text is not None:
        el.text = str(text) if text != "" else None
    return el


def _safe(v) -> str:
    if v is None:
        return ""
    return str(v).strip()


def _bullets_to_xml(parent: ET.Element, bullets: list, tag: str = "Madde"):
    for b in (bullets or []):
        if isinstance(b, dict):
            el = _sub(parent, tag, _safe(b.get("text") or b.get("sentence")))
            hk = b.get("h_code")
            if hk:
                el.set("hKodu", _safe(hk))
        else:
            _sub(parent, tag, _safe(b))


def generate_sds_xml(sds_data: dict) -> str:
    """
    sds_data dict'inden 16-bölüm SDS XML üretir.
    Dönen değer UTF-8 XML string'idir.
    """
    root = ET.Element("SDS")

    prod       = sds_data.get("product", {})
    clp        = sds_data.get("clp", {})
    components = sds_data.get("components", []) or []
    h_codes    = clp.get("h_codes", []) or []
    all_h      = clp.get("all_h_codes", []) or h_codes
    mixture_form = prod.get("form", "liquid") or "liquid"

    # ── Sentence generator import ─────────────────────────────────────────────
    try:
        from app.services.sds_sentence_service import (
            generate_section, generate_section_42,
        )
        _gen_ok = True
    except Exception:
        _gen_ok = False

    # ── B1 ───────────────────────────────────────────────────────────────────
    b1   = _sub(root, "Bolum1_Kimlik")
    supp = sds_data.get("supplier", {})
    _sub(b1, "UrunAdi",          _safe(prod.get("name")))
    _sub(b1, "UrunKodu",         _safe(prod.get("code")))
    _sub(b1, "UrunFormu",        _safe(mixture_form))
    _sub(b1, "Kullanim",         _safe(prod.get("usage")))
    _sub(b1, "KullanimAciklama", _safe(prod.get("usage_desc")))
    s = _sub(b1, "Tedarikci")
    _sub(s, "Ad",      _safe(supp.get("name")))
    _sub(s, "Adres",   _safe(supp.get("address")))
    _sub(s, "Telefon", _safe(supp.get("phone")))
    _sub(s, "Eposta",  _safe(supp.get("email")))
    _sub(s, "AcilTel", _safe(supp.get("emergency_tel")))
    _sub(b1, "AcilTelUZEM", "114")

    # ── B2 ───────────────────────────────────────────────────────────────────
    b2 = _sub(root, "Bolum2_Zararlılık")
    _sub(b2, "TumHKodlari",    " ".join(all_h))
    _sub(b2, "EtiketHKodlari", " ".join(h_codes))
    _sub(b2, "SinyalKelimesi", _safe(clp.get("signal_word")))
    _sub(b2, "Piktogramlar",   " ".join(clp.get("pictograms", []) or []))

    if sds_data.get("h314_neutralization_removed"):
        _sub(b2, "H314NötralizasyonKaldirildi", "Evet")

    # B2.1 Sınıflandırma gerekçeleri
    passed_el = _sub(b2, "SiniflandirmaGerekceleri")
    for p in (clp.get("passed") or []):
        h_code = _safe(p.get("h_code"))
        if not h_code:
            continue
        pe = _sub(passed_el, "Gerekcesi")
        pe.set("hKodu",   h_code)
        pe.set("hSinifi", _safe(p.get("h_class")))
        pe.set("kaynak",  _safe(p.get("cutoff_source", "?")))
        pe.set("esik",    _safe(p.get("cutoff_value", "")))
        if p.get("note_flag"):
            pe.set("notFlag", _safe(p["note_flag"]))
        if p.get("note"):
            pe.set("not", _safe(p["note"]))
        if p.get("repro_sub"):
            pe.set("reproAlt", _safe(p["repro_sub"]))
        pe.text = _safe(p.get("reason"))

    # Not geçersiz kılmalar
    note_ovr = sds_data.get("clp_note_overrides") or {}
    if note_ovr:
        no_el = _sub(b2, "NotGecersizKilmalar")
        for hkod, val in note_ovr.items():
            ne = _sub(no_el, "Not")
            ne.set("hKodu", _safe(hkod))
            ne.text = _safe(val)

    # EUH ifadeleri
    euh_data = sds_data.get("euh", {})
    if isinstance(euh_data, dict):
        euh_codes   = euh_data.get("euh_codes") or euh_data.get("codes") or []
        euh_details = euh_data.get("euh_details") or euh_data.get("details") or []
        manual_euh  = euh_data.get("manual_check") or []
    else:
        euh_codes = list(euh_data) if euh_data else []
        euh_details = []
        manual_euh  = []

    _sub(b2, "EUHKodlari", " ".join(euh_codes))
    if euh_details:
        euh_el = _sub(b2, "EUHDetaylari")
        for d in euh_details:
            de = _sub(euh_el, "EUH")
            de.set("kod",      _safe(d.get("code")))
            de.set("kaynasCas",_safe(d.get("source_cas") or d.get("cas")))
            de.set("kaynasMad",_safe(d.get("source_name") or d.get("name")))
            de.text = _safe(d.get("text") or d.get("phrase"))
    if manual_euh:
        _sub(b2, "EUHManuelKontrol", " ".join(manual_euh))

    # P kodları
    p_data = sds_data.get("p_codes", {})
    if isinstance(p_data, dict):
        lbl      = p_data.get("label", {})
        label_sel = (lbl.get("selected", []) if isinstance(lbl, dict) else []) or []
        sds_cls   = p_data.get("sds", {})
        sds_mand  = (sds_cls.get("mandatory", []) if isinstance(sds_cls, dict) else []) or []
        sds_eval  = (sds_cls.get("evaluate", []) if isinstance(sds_cls, dict) else []) or []
    else:
        label_sel = sds_mand = sds_eval = []

    _sub(b2, "EtiketPKodlari",    " ".join(label_sel))
    _sub(b2, "SDSZorunluPKodlari"," ".join(sds_mand))
    if sds_eval:
        _sub(b2, "SDSDegerlendirmePKodlari", " ".join(sds_eval))

    # ── B3 ───────────────────────────────────────────────────────────────────
    b3 = _sub(root, "Bolum3_Bilesen")
    try:
        from app.services.reach_db import get_reg_no, get_ec_no as _get_ec
    except Exception:
        get_reg_no = _get_ec = lambda x: ""

    for c in components:
        ce  = _sub(b3, "Bilesen")
        cas   = _safe(c.get("cas_no") or c.get("cas"))
        ec    = _safe(c.get("ec_no")  or _get_ec(cas))
        reach = _safe(c.get("reach_no") or get_reg_no(cas))
        ce.set("cas",   cas)
        ce.set("ec",    ec or "—")
        ce.set("reach", reach or "—")
        _sub(ce, "Ad",            _safe(c.get("name_tr") or c.get("name")))
        _sub(ce, "Konsantrasyon", _safe(c.get("conc") or c.get("concentration")))
        scl_raw = c.get("sclRaw") or c.get("scl_raw")
        if scl_raw:
            _sub(ce, "SCLHam", _safe(scl_raw))
        hz = _sub(ce, "Tehlikeler")
        for h in (c.get("hazards") or []):
            he = _sub(hz, "Tehlike")
            he.set("hKodu",  _safe(h.get("h_code")))
            he.set("hSinifi",_safe(h.get("h_class")))
            scl = h.get("scl") or h.get("specific_conc_limit")
            if scl:
                he.set("scl", _safe(scl))

    # ── B4 İlk Yardım ────────────────────────────────────────────────────────
    b4 = _sub(root, "Bolum4_IlkYardim")
    if _gen_ok:
        try:
            sec4    = generate_section(4, h_codes, mixture_form)
            sec4_42 = generate_section_42(h_codes)
            maruziyet = _sub(b4, "MaruziyetYollari")
            _bullets_to_xml(maruziyet, sec4.get("bullets", []))
            semptomlar = _sub(b4, "Semptomlar")
            for s42 in (sec4_42 or []):
                _sub(semptomlar, "Madde", _safe(s42))
            _sub(b4, "ZehirMerkezi", "114 (Türkiye Zehir Danışma Merkezi — UZEM)")
        except Exception:
            pass

    # ── B5 Yangın ────────────────────────────────────────────────────────────
    b5 = _sub(root, "Bolum5_Yangin")
    if _gen_ok:
        try:
            sec5 = generate_section(5, h_codes, mixture_form)
            _sub(b5, "SondurucuMadde", _safe(sec5.get("extinguisher")))
            tehlikeler5 = _sub(b5, "OzelTehlikeler")
            _bullets_to_xml(tehlikeler5, sec5.get("bullets", []))
            _sub(b5, "ItfaiyeKKD",
                 "Tam bağımsız hava beslemeli solunum cihazı (SCBA) ve tam koruyucu elbise kullanın.")
        except Exception:
            pass

    # ── B6 Kaza Önlemleri ────────────────────────────────────────────────────
    b6 = _sub(root, "Bolum6_KazaOnlemleri")
    _sub(b6, "KisiselOnlemler",
         "Gereksiz personeli uzaklaştırın. KKD kullanın (Bölüm 8). "
         "İyi havalandırma sağlayın. Tutuşturma kaynaklarını ortadan kaldırın.")
    if _gen_ok:
        try:
            sec6 = generate_section(6, h_codes, mixture_form)
            cevre = _sub(b6, "CevreselOnlemler")
            _bullets_to_xml(cevre, sec6.get("bullets", []))
        except Exception:
            pass
    _sub(b6, "TemizlemeYontemi",
         "Döküntüyü uygun emici madde (kum, kil, ticari emici) ile toplayın. "
         "Onaylı atık konteynerine koyun. Bertaraf için Bölüm 13'e bakın.")

    # ── B7 Elleçleme ve Depolama ──────────────────────────────────────────────
    b7 = _sub(root, "Bolum7_ElleçlemeDepolama")
    if _gen_ok:
        try:
            sec7  = generate_section(7,  h_codes, mixture_form)
            sec72 = generate_section(72, h_codes, mixture_form)
            ellecleme = _sub(b7, "Ellecleme")
            _bullets_to_xml(ellecleme, sec7.get("bullets", []))
            depolama = _sub(b7, "Depolama")
            _bullets_to_xml(depolama, sec72.get("bullets", []))
            if not sec72.get("bullets"):
                _sub(depolama, "Madde",
                     "Serin, kuru ve iyi havalandırılmış yerde, orijinal ambalajında saklayın.")
        except Exception:
            pass
    _sub(b7, "OzelSonKullanim",
         "Belirli bir son kullanım önerilmemektedir. "
         "Genişletilmiş maruziyet senaryosu için tedarikçiye başvurunuz.")

    # ── B8 Maruziyet Kontrolü ─────────────────────────────────────────────────
    b8 = _sub(root, "Bolum8_MaruziyetKontrol")

    try:
        from app.services.tr_oel_service import get_oel_table
        for c in components:
            cas = _safe(c.get("cas_no") or c.get("cas"))
            if not cas:
                continue
            try:
                rows = get_oel_table(cas) or []
            except Exception:
                rows = []
            for row in rows:
                oe = _sub(b8, "OEL")
                oe.set("cas",  cas)
                oe.set("twa",  _safe(row.get("twa")  or row.get("TWA")  or "—"))
                oe.set("stel", _safe(row.get("stel") or row.get("STEL") or "—"))
                oe.set("unit", _safe(row.get("unit") or "mg/m³"))
    except Exception:
        pass

    ppe = sds_data.get("ppe") or {}
    if isinstance(ppe, dict) and ppe:
        ppe_el = _sub(b8, "KKD")
        for kategori, anahtar in [
            ("Solunum", "respiratory"),
            ("El",      "hands"),
            ("Goz",     "eyes"),
            ("Vucut",   "body"),
        ]:
            items = ppe.get(anahtar) or []
            if items:
                kat_el = _sub(ppe_el, kategori)
                for item in items:
                    if isinstance(item, dict):
                        ie = _sub(kat_el, "Ekipman")
                        ie.set("seviye", _safe(item.get("level", "")))
                        ie.text = _safe(item.get("ppe") or item.get("text"))
                    else:
                        _sub(kat_el, "Ekipman", _safe(item))
        general = ppe.get("general") or []
        if general:
            gen_el = _sub(ppe_el, "GenelHijyen")
            for g in general:
                _sub(gen_el, "Kural", _safe(g))

    # ── B9 Fiziksel Özellikler ────────────────────────────────────────────────
    b9      = _sub(root, "Bolum9_FizikselOzellikler")
    phys    = sds_data.get("phys_props", {}) or {}
    methods = sds_data.get("phys_methods", {}) or {}

    _PHYS_FIELDS = [
        ("flash_point",    "ParlamaNok"),
        ("boiling_point",  "KaynamaNok"),
        ("density",        "Yogunluk"),
        ("ph",             "pH"),
        ("vapor_pressure", "BuharBasinci"),
        ("viscosity",      "Viskozite"),
        ("solubility",     "SuCozurlugu"),
        ("auto_ignition",  "OtutusmasSic"),
        ("log_kow",        "LogKow"),
        ("melting_point",  "ErimNok"),
    ]
    for key, tag in _PHYS_FIELDS:
        v = phys.get(key)
        if v is None:
            val = "N/A"
        elif isinstance(v, dict):
            val = _safe(v.get("display") or v.get("value") or v.get("calc")) or "N/A"
        else:
            val = _safe(v) or "N/A"
        el = _sub(b9, tag, val)
        method = methods.get(key)
        if method:
            el.set("yontem", _safe(method))

    # ── B10 Kararlılık ve Reaktivite ──────────────────────────────────────────
    b10 = _sub(root, "Bolum10_Kararlılık")

    comp_cas_set = {c.get("cas_no", c.get("cas", "")) for c in components}
    ALCOHOL_CAS = {
        "64-17-5","67-63-0","71-36-3","71-23-8","78-83-1",
        "67-56-1","71-41-0","75-65-0","100-51-6",
    }
    CHLORINATED_CAS = {
        "75-09-2","67-66-3","71-55-6","79-01-6","127-18-4",
        "7647-01-0","75-00-3","79-00-5","106-93-4",
    }
    h_set           = set(h_codes)
    has_alcohol     = bool(comp_cas_set & ALCOHOL_CAS)
    has_chlorinated = bool(comp_cas_set & CHLORINATED_CAS)
    is_flammable    = bool(h_set & {"H224","H225","H226","H228"})
    acid_cas        = {"7664-93-9","7647-01-0","7697-37-2","7664-38-2","64-19-7"}
    base_cas        = {"1310-73-2","1310-58-3","1336-21-6","7664-41-7"}
    is_acid = ("H314" in h_set or "H290" in h_set) and bool(comp_cas_set & acid_cas)
    is_base = "H314" in h_set and bool(comp_cas_set & base_cas)

    _sub(b10, "Reaktivite", _safe(phys.get("reactivity")) or "Standart koşullarda reaktif değil.")
    _sub(b10, "KimyasalKararlılık", "Normal kullanım ve depolama koşullarında kararlıdır.")
    _sub(b10, "TehlikeliReaksiyonlar", "Bölüm 7'ye bakınız.")

    avoid_parts = []
    if is_flammable:
        avoid_parts += ["Açık alev, ısı kaynakları, kıvılcım ve statik elektrik",
                        "Yüksek sıcaklıklar ve doğrudan güneş ışığı"]
    if h_set & {"H270","H271","H272"}:
        avoid_parts.append("Yanıcı maddeler")
    if h_set & {"H260","H261"}:
        avoid_parts.append("Su ve nem")
    if h_set & {"H240","H241","H242"}:
        avoid_parts.append("Isıtma ve sürtünme")
    avoid_parts.append("Oksitleyici maddeler ve kuvvetli asitler")
    _sub(b10, "KaçınılmasıGerekenKoşullar", "; ".join(avoid_parts) + ".")

    comp_incompat_db = {
        "1330-20-7": ["güçlü oksitleyiciler","kuvvetli asitler"],
        "64-17-5":   ["güçlü oksitleyiciler","kuvvetli asitler","alkali metaller"],
        "67-56-1":   ["güçlü oksitleyiciler","klorin bileşikleri"],
        "67-64-1":   ["güçlü oksitleyiciler","kloroform"],
        "1310-73-2": ["asitler","su (ekzotermik)"],
        "7647-01-0": ["bazlar","oksitleyiciler"],
        "71-43-2":   ["güçlü oksitleyiciler","kuvvetli asitler"],
        "108-88-3":  ["güçlü oksitleyiciler","kuvvetli asitler"],
    }
    incompat_set = set()
    for comp in components:
        cas = comp.get("cas_no", comp.get("cas",""))
        for item in comp_incompat_db.get(cas, []):
            incompat_set.add(item)
    if is_flammable:
        incompat_set.add("güçlü oksitleyiciler")
    if has_alcohol:
        incompat_set.update(["alkali metaller","alüminyum (yüksek sıcaklıkta)"])
    if is_acid:
        incompat_set.add("bazlar ve aktif metaller")
    if is_base:
        incompat_set.add("asitler")
    if "H314" in h_set and not is_acid and not is_base:
        incompat_set.add("asitler ve bazlar")
    if not incompat_set:
        incompat_set.add("güçlü oksitleyiciler, kuvvetli asitler ve bazlar")
    _sub(b10, "Bağdaşmayanlar", ", ".join(sorted(incompat_set)).capitalize() + ".")

    decomp_parts = []
    if is_flammable or h_set & {"H228","H242"}:
        decomp_parts.append("Karbon oksitler (CO, CO₂)")
    if has_chlorinated:
        decomp_parts.append("Klorür bileşikleri (HCl, Cl₂)")
    if comp_cas_set & {"1336-21-6","7664-41-7"}:
        decomp_parts.append("NH₃ (amonyak)")
    if h_set & {"H400","H411"}:
        decomp_parts.append("Sucul ortama zararlı organik fragmentler")
    _sub(b10, "BozunmaÜrünleri",
         ("; ".join(decomp_parts) + ".") if decomp_parts
         else "Tehlikeli bozunma ürünü bilinmemektedir.")

    # ── B11 Toksikoloji / ATE ─────────────────────────────────────────────────
    b11 = _sub(root, "Bolum11_Toksikoloji")
    ate = sds_data.get("ate_mix_details") or {}
    for route, rd in (ate.items() if isinstance(ate, dict) else []):
        ae = _sub(b11, "ATE")
        ae.set("yol",   route)
        ae.set("deger", _safe(rd.get("ateMix") or rd.get("ate_mix")))
        ae.set("hKodu", _safe(rd.get("resultCode") or rd.get("result_code")))

    # ── B12 Ekoloji ───────────────────────────────────────────────────────────
    b12   = _sub(root, "Bolum12_Ekoloji")
    eco   = sds_data.get("eco", {}) or {}
    eco_h = eco.get("h_codes", []) if isinstance(eco, dict) else []
    _sub(b12, "EkoHKodlari", " ".join(eco_h))

    aquatic = eco.get("aquatic") if isinstance(eco, dict) else None
    if aquatic is not None:
        aq_el = _sub(b12, "Sucul")
        if hasattr(aquatic, "component_details"):
            comp_details = aquatic.component_details or []
        elif isinstance(aquatic, dict):
            comp_details = aquatic.get("component_details") or []
        else:
            comp_details = []
        for cd in comp_details:
            cde = _sub(aq_el, "BilesenDetay")
            cde.set("cas",     _safe(cd.get("cas") or cd.get("cas_no")))
            cde.set("konc",    _safe(cd.get("conc")))
            cde.set("mFaktor", _safe(cd.get("m_factor") or cd.get("m_acute")))
            cde.text = _safe(cd.get("name") or cd.get("name_tr"))

    pbt_list = eco.get("pbt", []) if isinstance(eco, dict) else []
    if pbt_list:
        pbt_el = _sub(b12, "PBT_vPvB")
        for p in pbt_list:
            pe = _sub(pbt_el, "Madde")
            pe.set("cas",  _safe(p.get("cas")))
            pe.set("turu", _safe(p.get("type") or p.get("flag")))
            pe.text = _safe(p.get("name"))

    # ── B13 Bertaraf ──────────────────────────────────────────────────────────
    b13   = _sub(root, "Bolum13_Bertaraf")
    waste = _safe(sds_data.get("waste_code") or prod.get("waste_code"))
    _sub(b13, "AtikKodu", waste or "—")
    _sub(b13, "BertarafYontemi",
         "Yetkili bertaraf kuruluşlarına teslim edin. "
         "Kanalizasyona veya doğal ortama dökmeyin. "
         "Türk Atık Mevzuatı ve yerel yönetmelikler uygulanır.")

    # ── B14 Taşımacılık ───────────────────────────────────────────────────────
    b14       = _sub(root, "Bolum14_Tasima")
    transport = sds_data.get("transport", {}) or {}

    def _transport_mode(parent, tag, data: dict):
        if not data:
            return
        un = _safe(data.get("un_no") or data.get("un") or "")
        if not un or un == "-":
            return
        me = _sub(parent, tag)
        me.set("un",    un if un.upper().startswith("UN") else f"UN {un}")
        me.set("sinif", _safe(data.get("class") or data.get("hazard_class")))
        me.set("pg",    _safe(data.get("pg") or data.get("packing_group")))
        me.set("ad",    _safe(data.get("shipping_name") or data.get("label")))
        me.set("kemler",    _safe(data.get("kemler_code") or data.get("kemler") or "—"))
        me.set("tunel",     _safe(data.get("tunnel_code") or data.get("tunnel") or "—"))
        me.set("sinifKodu", _safe(data.get("classification_code") or "—"))
        env = data.get("env_hazard") or data.get("marine_pollutant") or data.get("env_mark")
        if env is not None:
            me.set("cevreTehl", "Evet" if env else "Hayır")

    road = transport.get("road", {}) or {}
    if road:
        un_key = _safe(road.get("un_no") or road.get("un") or "")
        pg_key = _safe(road.get("packing_group") or road.get("pg") or "II")
        if un_key and not road.get("kemler_code"):
            try:
                from app.services.transport_adr_service import get_adr_details as _get_adr
                det = _get_adr(un_key if un_key.upper().startswith("UN") else f"UN {un_key}", pg_key)
                road = {**road,
                        "kemler_code": det.get("kemler") or "—",
                        "tunnel_code": det.get("tunnel_code") or "—",
                        "classification_code": det.get("classification_code") or "—"}
            except Exception:
                pass

    _transport_mode(b14, "ADR_Karayolu", road)
    _transport_mode(b14, "IMDG_Deniz",   transport.get("sea", {}) or {})
    _transport_mode(b14, "IATA_Hava",    transport.get("air", {}) or {})

    if transport.get("not_regulated"):
        _sub(b14, "DuzenlenmemisEmtia", "Evet")

    # ── B15 Mevzuat ───────────────────────────────────────────────────────────
    b15 = _sub(root, "Bolum15_Mevzuat")
    try:
        from app.services.tr_mevzuat_service import get_section15_text
        reg_text = get_section15_text(h_codes, has_biocide=False, lang="TR")
        _sub(b15, "MevzuatMetni", _safe(reg_text))
    except Exception:
        _sub(b15, "MevzuatMetni",
             "KKDİK (29.05.2015 tarihli ve 29729 sayılı Resmî Gazete), "
             "Kimyasal Maddelerle Çalışmalarda Sağlık ve Güvenlik Önlemleri Hakkında Yönetmelik "
             "(12.08.2013 tarihli ve 28733 sayılı Resmî Gazete), "
             "Tehlikeli Maddelerin Karayoluyla Taşınması Hakkında Yönetmelik.")

    try:
        from app.services.svhc_service import check_svhc_mixture, svhc_section15_text
        svhc_res = check_svhc_mixture(components)
        svhc_lines = svhc_section15_text(svhc_res, lang="TR")
        if svhc_lines:
            _sub(b15, "SVHCBilgisi", "\n".join(svhc_lines))
    except Exception:
        pass

    # ── B16 Revizyon ──────────────────────────────────────────────────────────
    b16 = _sub(root, "Bolum16_DigerBilgiler")
    rev = sds_data.get("revision", {}) or {}
    _sub(b16, "RevTarihi", _safe(rev.get("date")))
    _sub(b16, "RevNo",     _safe(rev.get("no")))
    _sub(b16, "RevNotu",   _safe(rev.get("notes")))

    # Pretty-print
    raw = ET.tostring(root, encoding="unicode")
    return minidom.parseString(raw).toprettyxml(indent="  ", encoding=None)
