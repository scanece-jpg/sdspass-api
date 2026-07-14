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


def generate_sds_xml(sds_data: dict) -> str:
    """
    sds_data dict'inden 16-bölüm SDS XML üretir.
    Dönen değer UTF-8 XML string'idir.
    """
    root = ET.Element("SDS")

    # ── B1 ───────────────────────────────────────────────────────────────────
    b1 = _sub(root, "Bolum1_Kimlik")
    prod = sds_data.get("product", {})
    supp = sds_data.get("supplier", {})
    _sub(b1, "UrunAdi",    _safe(prod.get("name")))
    _sub(b1, "UrunKodu",   _safe(prod.get("code")))
    _sub(b1, "Kullanim",   _safe(prod.get("usage")))
    s = _sub(b1, "Tedarikci")
    _sub(s, "Ad",          _safe(supp.get("name")))
    _sub(s, "Adres",       _safe(supp.get("address")))
    _sub(s, "Telefon",     _safe(supp.get("phone")))
    _sub(s, "Eposta",      _safe(supp.get("email")))
    _sub(s, "AcilTel",     _safe(supp.get("emergency_tel")))
    _sub(b1, "AcilTelUZEM", "114")

    # ── B2 ───────────────────────────────────────────────────────────────────
    b2 = _sub(root, "Bolum2_Zararlılık")
    clp = sds_data.get("clp", {})
    _sub(b2, "TumHKodlari",   " ".join(clp.get("all_h_codes", []) or clp.get("h_codes", [])))
    _sub(b2, "EtiketHKodlari"," ".join(clp.get("h_codes", [])))
    _sub(b2, "SinyalKelimesi", _safe(clp.get("signal_word")))
    _sub(b2, "Piktogramlar",  " ".join(clp.get("pictograms", []) or []))

    euh_data = sds_data.get("euh", {})
    euh_codes = euh_data.get("codes", []) if isinstance(euh_data, dict) else (euh_data or [])
    _sub(b2, "EUHKodlari", " ".join(euh_codes))

    p_data = sds_data.get("p_codes", {})
    if isinstance(p_data, dict):
        lbl = p_data.get("label", {})
        label_sel = (lbl.get("selected", []) if isinstance(lbl, dict) else []) or []
        sds_cls   = p_data.get("sds", {})
        sds_mand  = (sds_cls.get("mandatory", []) if isinstance(sds_cls, dict) else []) or []
    else:
        label_sel = sds_mand = []
    _sub(b2, "EtiketPKodlari", " ".join(label_sel))
    _sub(b2, "SDSZorunluPKodlari", " ".join(sds_mand))

    # Sınıflandırma gerekçeleri
    passed_el = _sub(b2, "SınıflandırmaGerekceleri")
    for p in (clp.get("passed") or []):
        h_code = _safe(p.get("h_code"))
        if not h_code:
            continue
        pe = _sub(passed_el, "Gecekce")
        pe.set("hKodu", h_code)
        pe.set("hSinifi", _safe(p.get("h_class")))
        pe.set("kaynak", _safe(p.get("cutoff_source", "?")))
        pe.set("esik", _safe(p.get("cutoff_value", "")))
        pe.text = _safe(p.get("reason"))

    # ── B3 ───────────────────────────────────────────────────────────────────
    b3 = _sub(root, "Bolum3_Bilesen")
    try:
        from app.services.reach_db import get_reg_no, get_ec_no as _get_ec
    except Exception:
        get_reg_no = _get_ec = lambda x: ""

    for c in (sds_data.get("components", []) or []):
        ce = _sub(b3, "Bilesen")
        cas   = _safe(c.get("cas_no") or c.get("cas"))
        ec    = _safe(c.get("ec_no")  or _get_ec(cas))
        reach = _safe(c.get("reach_no") or get_reg_no(cas))
        ce.set("cas",   cas)
        ce.set("ec",    ec or "—")
        ce.set("reach", reach or "—")
        _sub(ce, "Ad",             _safe(c.get("name_tr") or c.get("name")))
        _sub(ce, "Konsantrasyon",  _safe(c.get("conc") or c.get("concentration")))
        hz = _sub(ce, "Tehlikeler")
        for h in (c.get("hazards") or []):
            he = _sub(hz, "Tehlike")
            he.set("hKodu",  _safe(h.get("h_code")))
            he.set("hSinifi",_safe(h.get("h_class")))

    # ── B9 ───────────────────────────────────────────────────────────────────
    b9 = _sub(root, "Bolum9_FizikselOzellikler")
    phys = sds_data.get("phys_props", {}) or {}

    def _pv(key):
        v = phys.get(key)
        if v is None:
            return "N/A"
        if isinstance(v, dict):
            v = v.get("display") or v.get("value") or v.get("calc")
        return _safe(v) if v is not None else "N/A"

    _sub(b9, "ParlamaNok",      _pv("flash_point"))
    _sub(b9, "KaynamaNok",      _pv("boiling_point"))
    _sub(b9, "Yogunluk",        _pv("density"))
    _sub(b9, "pH",              _pv("ph"))
    _sub(b9, "BuharBasinci",    _pv("vapor_pressure"))
    _sub(b9, "Viskozite",       _pv("viscosity"))
    _sub(b9, "SuCozurlugu",     _pv("solubility"))
    _sub(b9, "OtutusmasSic",    _pv("auto_ignition"))
    _sub(b9, "LogKow",          _pv("log_kow"))
    _sub(b9, "ErimNok",         _pv("melting_point"))

    # ── B8 OEL ───────────────────────────────────────────────────────────────
    b8 = _sub(root, "Bolum8_MaruziyetKontrol")
    try:
        from app.services.tr_oel_service import get_oel_table
        for c in (sds_data.get("components", []) or []):
            cas = _safe(c.get("cas_no") or c.get("cas"))
            if not cas:
                continue
            try:
                rows = get_oel_table(cas) or []
            except Exception:
                rows = []
            for row in rows:
                oe = _sub(b8, "OEL")
                oe.set("cas", cas)
                oe.set("twa",  _safe(row.get("twa")  or row.get("TWA")  or "—"))
                oe.set("stel", _safe(row.get("stel") or row.get("STEL") or "—"))
                oe.set("unit", _safe(row.get("unit") or "mg/m³"))
    except Exception:
        pass

    # ── B11 ATE ──────────────────────────────────────────────────────────────
    b11 = _sub(root, "Bolum11_Toksikoloji")
    ate = sds_data.get("ate_mix_details") or {}
    for route, rd in (ate.items() if isinstance(ate, dict) else []):
        ae = _sub(b11, "ATE")
        ae.set("yol", route)
        ae.set("deger", _safe(rd.get("ateMix") or rd.get("ate_mix")))
        ae.set("hKodu", _safe(rd.get("resultCode") or rd.get("result_code")))

    # ── B12 Ekoloji ───────────────────────────────────────────────────────────
    b12 = _sub(root, "Bolum12_Ekoloji")
    eco = sds_data.get("eco", {}) or {}
    eco_h = eco.get("h_codes", []) if isinstance(eco, dict) else []
    _sub(b12, "EkoHKodlari", " ".join(eco_h))

    # ── B13 Bertaraf ──────────────────────────────────────────────────────────
    b13 = _sub(root, "Bolum13_Bertaraf")
    waste = _safe(sds_data.get("waste_code") or sds_data.get("product", {}).get("waste_code"))
    _sub(b13, "AtikKodu", waste or "—")

    # ── B14 Taşımacılık ───────────────────────────────────────────────────────
    b14 = _sub(root, "Bolum14_Tasima")
    transport = sds_data.get("transport", {}) or {}

    def _transport_mode(parent, tag, data: dict, un_raw: str | None = None):
        if not data:
            return
        un = _safe(data.get("un_no") or data.get("un") or un_raw or "")
        if not un:
            return
        me = _sub(parent, tag)
        me.set("un",    un if un.upper().startswith("UN") else f"UN {un}")
        me.set("sinif", _safe(data.get("class") or data.get("hazard_class")))
        me.set("pg",    _safe(data.get("pg") or data.get("pack_group")))
        me.set("ad",    _safe(data.get("shipping_name") or data.get("label")))
        # ADR'ye özgü alanlar
        un_key = me.get("un", "")
        try:
            from app.services.transport_adr_service import get_adr_details as _get_adr
            det = _get_adr(un_key, me.get("pg", "II"))
            me.set("kemler",     _safe(det.get("kemler") or data.get("kemler_code") or "—"))
            me.set("tunel",      _safe(det.get("tunnel_code") or data.get("tunnel_code") or "—"))
            me.set("sinifKodu",  _safe(det.get("classification_code") or "—"))
        except Exception:
            pass
        env = data.get("env_hazard") or data.get("marine_pollutant")
        if env is not None:
            me.set("cevreTehl", "Evet" if env else "Hayır")

    road = transport.get("road", {}) or {}
    _transport_mode(b14, "ADR_Karayolu", road)
    _transport_mode(b14, "IMDG_Deniz",   transport.get("sea", {}) or {})
    _transport_mode(b14, "IATA_Hava",    transport.get("air", {}) or {})

    # ── B16 Revizyon ──────────────────────────────────────────────────────────
    b16 = _sub(root, "Bolum16_DigerBilgiler")
    rev = sds_data.get("revision", {}) or {}
    _sub(b16, "RevTarihi", _safe(rev.get("date")))
    _sub(b16, "RevNo",     _safe(rev.get("no")))
    _sub(b16, "RevNotu",   _safe(rev.get("notes")))

    # Pretty-print
    raw = ET.tostring(root, encoding="unicode")
    return minidom.parseString(raw).toprettyxml(indent="  ", encoding=None)
