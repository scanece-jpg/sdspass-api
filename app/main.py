"""
HazardDesk PDF API — Minimal Deploy
DB gerektirmez, sadece PDF üretimi + madde lookup
"""

from fastapi import FastAPI, Body, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import sys, os

# Data yolu — deploy'da /app/data, lokalde /home/claude
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
if not os.path.exists(DATA_DIR):
    DATA_DIR = '/home/claude'

# clp_service bu path'e bakıyor — env ile ilet
os.environ.setdefault('CLP_DATA_DIR', os.path.abspath(DATA_DIR))

app = FastAPI(
    title="HazardDesk API",
    description="KKDİK/CLP SDS PDF üretim servisi",
    version="1.2.0-DANGER_H_FIX",
    docs_url="/docs",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "HazardDesk PDF API"}


@app.get("/")
async def serve_frontend():
    """SDS Hesaplama arayüzü"""
    html_path = os.path.join(os.path.dirname(__file__), '..', 'static', 'index.html')
    return FileResponse(html_path, media_type="text/html")


# ─── STATIC DOSYALAR (js/ klasörü) ────────────────────────────────────────────
_BASE = os.path.join(os.path.dirname(__file__), '..')
_JS_DIR = os.path.abspath(os.path.join(_BASE, 'js'))
if os.path.exists(_JS_DIR):
    app.mount("/js", StaticFiles(directory=_JS_DIR), name="js")


# ─── PDF ENDPOINT ─────────────────────────────────────────────────────────────

from app.services.pdf_sds_service import generate_sds_pdf
from app.services.clp_service import DANGER_H
from app.services.p_code_service import (
    assign_p_codes, select_label_p_codes, classify_sds_p_codes
)
from app.services.sds_sentence_service import generate_all_sections
from app.services.ecological_service import calculate_ecological


@app.post("/api/v1/sds/pdf", response_class=Response)
async def generate_pdf(data: dict = Body(...)):
    """
    SDS PDF üret — auth gerektirmez.
    Frontend'den doğrudan çağrılır.
    """
    try:
        lang        = data.get('lang', 'TR')
        product     = data.get('product', {})
        components  = data.get('components', [])
        # Tüm H kodlarını str'e normalize et — int/None gelirse PDF çökmez
        h_codes     = [str(h) for h in data.get('h_codes', []) if h is not None]
        euh_codes   = [str(h) for h in data.get('euh_codes', []) if h is not None]
        p_codes_in  = data.get('p_codes', [])
        disc_map    = data.get('disclosure_map', {})
        supplier_in = data.get('supplier', {})
        phys_in     = data.get('phys_props', {})
        revision_in = data.get('revision', {})
        usage       = product.get('usage', 'industrial')

        # Signal word — clp_service.DANGER_H kullan (H225 dahil, doğru liste)
        # Frontend'den gelen signal_word öncelikli, fallback hesaplama
        signal = data.get('signal_word', '')
        if signal not in ('Danger', 'Warning'):
            clean = {h.split()[0] for h in h_codes if isinstance(h, str)}
            signal = 'Danger' if clean & DANGER_H else 'Warning'

        # P kodları
        p_result = assign_p_codes(h_codes, signal, usage=usage)
        p_result['label'] = select_label_p_codes(p_result['p_codes'], 6)
        p_result['sds']   = classify_sds_p_codes(p_result['p_codes'])

        # EUH
        euh_details = data.get('euh_details', []) or [{'code':c,'text':''} for c in euh_codes]
        euh_result  = {'euh_codes': euh_codes, 'euh_details': euh_details}

        # Ekoloji
        eco_comps = [{'cas': c.get('cas',''), 'name': c.get('name',''),
                      'conc': float(c.get('conc', c.get('concentration',0)) or 0),
                      'hazards': c.get('hazards',[])} for c in components]
        try:
            eco_result = calculate_ecological(eco_comps)
        except Exception:
            eco_result = {'sds_section_12': {}}

        # ── PDF için Unicode → ASCII güvenli metin dönüşümü ──────────────────────
        # Avrupa kaynaklı DB'lerde (ECHA, CLP Annex VI) "…", "≤", "≥" karakterleri
        # sık geçer. DejaVu font yüklenemezse Helvetica fallback → WinAnsiEncoding
        # bu karakterleri karşılamaz ve UTF-8 byte'ları Latin-1 olarak görünür.
        _UNICODE_SAFE = str.maketrans({
            '\u2026': '...',   # … → ...
            '\u2264': '<=',    # ≤ → <=
            '\u2265': '>=',    # ≥ → >=
            '\u2248': '~',     # ≈ → ~
            '\u00b1': '+/-',   # ± → +/-
            '\u00d7': 'x',     # × → x
            '\u00f7': '/',     # ÷ → /
            '\u2013': '-',     # – → -
            '\u2014': '-',     # — → -
            '\u2018': "'",     # ' → '
            '\u2019': "'",     # ' → '
            '\u201c': '"',     # " → "
            '\u201d': '"',     # " → "
            '\u00b5': 'u',     # µ → u
            '\u00b0': 'C',     # ° → C (derece sembolü için)
            '\u00b2': '2',     # ² → 2
            '\u00b3': '3',     # ³ → 3
        })
        def _safe(text: str) -> str:
            """PDF için güvenli metin — sorunlu Unicode karakterleri ASCII'ye çevir"""
            if not text:
                return text
            return text.translate(_UNICODE_SAFE)

        # Bileşenler
        def _map_comp(c):
            name = _safe(c.get('name', ''))
            # "%100'e tamamla" bileşeni — PDF'de standart metin
            if name and 'mevzuata' in name.lower():
                name = 'Mevzuata göre sınıflandırılmamıştır'
            conc     = float(c.get('conc', c.get('concentration', 0)) or 0)
            conc_min = c.get('conc_min')
            conc_max = c.get('conc_max')
            conc_str = c.get('conc_str', '').strip()
            # conc_str yoksa conc_min/max'tan oluştur
            if not conc_str and conc_min is not None and conc_max is not None:
                lo = float(conc_min or 0)
                hi = float(conc_max or 0)
                if hi > 0 and hi != lo:
                    conc_str = f'{lo}-{hi}'
                elif hi > 0:
                    conc_str = f'{hi}'
                elif lo > 0:
                    conc_str = f'{lo}'
            return {
                'cas_no':        c.get('cas', c.get('cas_no', '')),
                'name':          name,
                'concentration': conc,
                'conc_str':      conc_str,
                'conc_min':      conc_min,
                'conc_max':      conc_max,
                'hazards':       [{'h_class': h.get('h_class', '')} for h in c.get('hazards', [])],
                'ec_no':         c.get('ec_no', ''),
                'reach_no':      c.get('reach_no', ''),
            }
        mapped_comps = [_map_comp(c) for c in components]

        # Revizyon tarihi
        import datetime
        rev_date = revision_in.get('date', datetime.datetime.now().strftime('%d.%m.%Y'))

        sds_data = {
            'product': {
                'name':       _safe(product.get('name', 'Product')),
                'code':       _safe(product.get('code', '')),
                'form':       product.get('form', 'liquid'),
                'usage':      _safe(usage),
                'usage_desc': _safe(product.get('usage_desc') or ''),
            },
            'supplier': {
                'name':          _safe(supplier_in.get('name', '')),
                'address':       _safe(supplier_in.get('address', '')),
                'phone':         supplier_in.get('phone', ''),
                'email':         supplier_in.get('email', ''),
                'emergency_tel': supplier_in.get('emergency_tel', ''),
            },
            'clp': {
                'h_codes':    h_codes,
                'signal_word': signal,
                'passed': [
                    {'h_class': h.get('h_class',''), 'h_code': h.get('h_code',''),
                     'reason': _safe(h.get('reason','')), 'cutoff_used': _safe(h.get('cutoff_used',''))}
                    for h in data.get('clp_passed', [])
                ],
            },
            'euh':          euh_result,
            'p_codes':      p_result,
            'components':   mapped_comps,
            'disclosure_map': disc_map,
            'phys_props':   phys_in,
            'eco':          eco_result,
            'transport':    data.get('transport', {}),
            'revision': {
                'date':    rev_date,
                'no':      revision_in.get('no', '1'),
                'version': revision_in.get('version', '1.0'),
                'notes':   revision_in.get('notes', 'İlk yayın'),
            },
        }

        pdf_bytes = generate_sds_pdf(sds_data, lang=lang)

        _tr_map = str.maketrans('ıİğĞüÜşŞçÇöÖ', 'iIgGuUsScCoO')
        _name_ascii = product.get('name', 'SDS').translate(_tr_map)
        safe = ''.join(x if (x.isalnum() and x.isascii()) or x in '-_' else '_'
                       for x in _name_ascii)[:30]
        rev_no = revision_in.get('no','1')

        return Response(
            content=pdf_bytes,
            media_type='application/pdf',
            headers={'Content-Disposition':
                     f'attachment; filename="{safe}_GBF_{lang}_Rev{rev_no}.pdf"'}
        )

    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e) + '\n\nTRACEBACK:\n' + tb)


@app.post("/api/v1/sds/debug")
async def debug_signal(data: dict = Body(...)):
    """Signal word hesaplama debug endpoint."""
    h_codes = data.get('h_codes', [])
    signal_from_fe = data.get('signal_word', '')
    clean = {h.split()[0] for h in h_codes}
    computed = 'Danger' if clean & DANGER_H else 'Warning'
    final = signal_from_fe if signal_from_fe in ('Danger', 'Warning') else computed
    return {
        "api_version": "1.2.0-DANGER_H_FIX",
        "h_codes_received": h_codes,
        "signal_from_frontend": signal_from_fe,
        "signal_computed": computed,
        "signal_final": final,
        "DANGER_H_has_H225": 'H225' in DANGER_H,
        "h225_in_hcodes": 'H225' in clean,
    }

# ─── SUBSTANCE LOOKUP ─────────────────────────────────────────────────────────

from app.services.echa_service import lookup_substance


@app.get("/api/v1/sds/substance/lookup")
async def substance_lookup(cas: str):
    """CAS numarasına göre madde bilgisi döndür."""
    from app.services.substance_lookup import lookup_substance, get_oel
    from app.services.reach_db import get_ec_no, get_reg_no
    
    result = lookup_substance(cas)
    oel = get_oel(cas)
    
    if result:
        return {
            "found": True,
            "cas": cas,
            "name": result.get("name",""),
            "ec_no": result.get("ec_no","") or get_ec_no(cas),
            "reach_no": get_reg_no(cas),
            "annex_vi": result.get("annex_vi", False),
            "signal": result.get("signal",""),
            "pictograms": result.get("pictograms",[]),
            "hazards": result.get("hazards",[]),
            "m_factors": result.get("m_factors",{}),
            "scl": result.get("scl", []),   # Annex VI özel kesme değerleri (SCL)
            "oel": oel,
        }
    # DB'de yoksa REACH DB'ye bak
    ec = get_ec_no(cas)
    reg = get_reg_no(cas)
    if ec or reg:
        return {"found": True, "cas": cas, "name": "", "ec_no": ec, 
                "reach_no": reg, "annex_vi": False, "hazards": [], "oel": oel}
    return {"found": False, "cas": cas}


@app.get("/api/v1/sds/substance/search")
async def substance_search(q: str, limit: int = 20):
    """İsim veya CAS'a göre madde arama."""
    from app.services.substance_lookup import search_substances
    results = search_substances(q, limit=min(limit, 50))
    return {"count": len(results), "results": results}


@app.get("/api/v1/sds/substance/stats")
async def substance_stats():
    """Veritabanı istatistikleri."""
    from app.services.substance_lookup import get_substance_count, get_oel_count, get_custom_count
    return {
        "substances": get_substance_count(),
        "oel_entries": get_oel_count(),
        "custom_substances": get_custom_count(),
    }


@app.post("/api/v1/sds/substance/save-custom")
async def save_custom_substance_endpoint(body: dict):
    """
    Annex VI dışı maddeyi custom listeye kaydet.
    Body: { "cas": "7732-18-5", "name": "water", "ec_no": "231-791-2",
            "signal": "", "pictograms": [], "hazards": [], "m_factors": {} }
    """
    from app.services.substance_lookup import save_custom_substance, is_annex_vi
    cas = (body.get("cas") or "").strip()
    if not cas:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="CAS numarası gerekli")
    if is_annex_vi(cas):
        return {"status": "skipped", "reason": "Bu madde zaten Annex VI listesinde", "cas": cas}
    entry = {
        "name":       body.get("name", ""),
        "ec_no":      body.get("ec_no", ""),
        "annex_vi":   False,
        "signal":     body.get("signal", ""),
        "pictograms": body.get("pictograms", []),
        "hazards":    body.get("hazards", []),
        "m_factors":  body.get("m_factors", {}),
        "index_no":   body.get("index_no", ""),
        "atp":        "custom",
    }
    is_new = save_custom_substance(cas, entry)
    return {
        "status": "created" if is_new else "updated",
        "cas": cas,
        "name": entry["name"],
    }


# ══════════════════════════════════════════════════════════════════════════════
# KÜTÜPHANe API'LERİ
# ══════════════════════════════════════════════════════════════════════════════

# ── GİRİŞ: Hesaplama Endpoint'leri ───────────────────────────────────────────

@app.post("/api/v1/clp/calculate")
async def clp_calculate(body: dict):
    """
    Karışım bileşenlerinden CLP sınıflandırması hesapla.
    CLP Annex I (KKDİK Ek-2) cut-off kuralları uygulanır.
    Input: {components: [{cas_no, concentration, hazards:[{h_class,h_code}]}], lang:"TR"}
    Output: {h_codes, signal_word, signal_word_tr, passed, warnings}
    """
    from app.services.clp_service import classify_mixture_clp
    from app.services.stot_re_service import calculate_stot_re
    from app.services.ecological_service import calculate_ecological
    import dataclasses

    components = body.get("components", [])
    lang = body.get("lang", "TR")

    try:
        # 1. Ana CLP (cut-off tablosu)
        result = classify_mixture_clp(components)

        # 2. STOT RE (hedef organ bazlı)
        stot = calculate_stot_re(components)
        for h in stot["h_codes"]:
            if h not in result["h_codes"]:
                result["h_codes"].append(h)
                result["passed"].append({
                    "h_class": "STOT RE",
                    "h_code": h,
                    "conc": 0,
                    "reason": next((r["reason"] for r in stot["results"] if r["h_code"] == h), "STOT RE toplamsal"),
                })

        # 3. Ekoloji (M-faktör ile sucul)
        def to_dict(obj):
            if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
                return {k: to_dict(v) for k, v in dataclasses.asdict(obj).items()}
            elif isinstance(obj, list):
                return [to_dict(i) for i in obj]
            return obj

        eco = calculate_ecological(components)
        if eco.aquatic:
            aq_h = eco.aquatic.h_code
            if aq_h and aq_h not in result["h_codes"]:
                result["h_codes"].append(aq_h)
                result["passed"].append({
                    "h_class": eco.aquatic.h_class,
                    "h_code": aq_h,
                    "conc": 0,
                    "reason": eco.aquatic.formula or "M-faktör toplamsal",
                })

        # 4. Sinyal kelimesi güncelle
        DANGER_H = {
            'H200','H201','H202','H203','H204','H205',
            'H220','H221','H222','H224','H225','H228','H240','H241',
            'H250','H260','H270','H271','H272',
            'H300','H301','H304','H310','H311','H314','H318','H330','H331',
            'H334','H340','H350','H360','H370','H372',
        }
        signal = "Danger" if any(h in DANGER_H for h in result["h_codes"]) else (
                  "Warning" if result["h_codes"] else "")
        result["signal_word"] = signal
        result["signal_word_tr"] = {"Danger":"Tehlike","Warning":"Uyarı","":""}.get(signal,"")
        result["h_codes"] = sorted(result["h_codes"])

        return {"success": True, "result": result, "lang": lang}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/clp/classify")
async def clp_classify_single(body: dict):
    """
    Tek madde için CLP sınıflandırması.
    Input: {cas_no, concentration, h_codes:[...], lang:"TR"}
    Output: {h_codes, signal_word, ghs_pictograms}
    """
    from app.services.codes_i18n import get_h, CLP_CLASS_TR, translate_hclass
    from app.services.ghs_pictogram import get_ghs_codes
    h_codes = body.get("h_codes", [])
    lang = body.get("lang", "TR")
    ghs = get_ghs_codes(h_codes)
    signal = "Danger" if any(h in h_codes for h in [
        "H200","H201","H202","H203","H204","H220","H222","H224","H225",
        "H260","H270","H271","H300","H301","H310","H311","H314","H318",
        "H330","H331","H340","H350","H360","H370","H372"
    ]) else "Warning" if h_codes else ""
    return {
        "success": True,
        "h_codes": h_codes,
        "signal_word": ("Tehlike" if lang=="TR" else "Danger") if signal=="Danger" else (
                        "Uyarı" if lang=="TR" else "Warning") if signal=="Warning" else "",
        "signal_word_en": signal,
        "ghs_pictograms": ghs,
        "h_texts": {h: get_h(lang, h) for h in h_codes},
    }


@app.post("/api/v1/euh/check")
async def euh_check(body: dict):
    """
    Bileşenlerden EUH kodlarını tespit et.
    Input: {components: [{cas_no, conc, hazards:[...]}]}
    Output: {euh_codes, euh_details}
    """
    from app.services.euh_service import check_euh
    components = body.get("components", [])
    try:
        result = check_euh(components)
        return {"success": True, **result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/p-codes/assign")
async def p_codes_assign(body: dict):
    """
    H kodlarından P kodlarını ata.
    Input: {h_codes:[...], signal_word:"Warning", usage:"industrial", lang:"TR"}
    Output: {p_codes, by_category, label_p_codes, mandatory}
    """
    from app.services.p_code_service import assign_p_codes, select_label_p_codes, classify_sds_p_codes
    from app.services.codes_i18n import get_p
    h_codes    = body.get("h_codes", [])
    signal     = body.get("signal_word", "Warning")
    usage      = body.get("usage", "industrial")
    lang       = body.get("lang", "TR")
    max_label  = body.get("max_label", 6)
    try:
        result = assign_p_codes(h_codes, signal, usage=usage)
        result["label"]    = select_label_p_codes(result["p_codes"], max_label, usage)
        result["sds"]      = classify_sds_p_codes(result["p_codes"])
        result["p_texts"]  = {p: get_p(lang, p) for p in result["p_codes"]}
        return {"success": True, **result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/physical/hazards")
async def physical_hazards(body: dict):
    """
    Fiziksel tehlike hesapla (parlama noktası, patlayıcılık...).
    Input: {components:[...], form:"liquid", flash_point:27}
    Output: {h_codes, results, warnings}
    """
    from app.services.physical_hazard_service import calc_physical_hazards
    components  = body.get("components", [])
    form        = body.get("form", "liquid")
    flash_point = body.get("flash_point")
    show_extra  = body.get("show_extra", False)
    try:
        result = calc_physical_hazards(components, form, flash_point, show_extra)
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/ecological/assess")
async def ecological_assess(body: dict):
    """
    Ekolojik değerlendirme (sucul toksisite, PBT, biyobirikim).
    Input: {components:[{cas_no,conc,hazards:[...]}]}
    Output: {aquatic, pbt_results, biodegradability, bioaccumulation, sds_section_12}
    """
    from app.services.ecological_service import calculate_ecological
    import dataclasses
    components = body.get("components", [])
    try:
        result = calculate_ecological(components)
        def to_dict(obj):
            if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
                return {k: to_dict(v) for k, v in dataclasses.asdict(obj).items()}
            elif isinstance(obj, list):
                return [to_dict(i) for i in obj]
            return obj
        d = to_dict(result)
        return {
            "success": True,
            "result": d,
            "has_aquatic_hazard": result.aquatic is not None,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/sds/validate")
async def sds_validate(body: dict):
    """
    SDS çapraz bölüm doğrulaması.
    Input: {sds_data:{...}, h_codes:[...], phys_props:{...}, components:[...]}
    Output: {issues:[{level,code,section,msg}], error_count, warning_count}
    """
    from app.services.sds_validator import validate_sds
    h_codes    = body.get("h_codes", [])
    phys_props = body.get("phys_props", {})
    sds_data   = body.get("sds_data", {})
    components = body.get("components", [])
    issues = validate_sds(sds_data, h_codes, phys_props, components)
    return {
        "success": True,
        "issues": issues,
        "error_count":   sum(1 for i in issues if i["level"] == "error"),
        "warning_count": sum(1 for i in issues if i["level"] == "warning"),
        "info_count":    sum(1 for i in issues if i["level"] == "info"),
        "passed": len(issues) == 0,
    }


# ── ÇIKTI: Veri Endpoint'leri ─────────────────────────────────────────────────

@app.get("/api/v1/oel/{cas}")
async def oel_lookup(cas: str, lang: str = "TR"):
    """
    CAS numarasına göre TR OEL (TWA/STEL) değerleri.
    """
    from app.services.tr_oel_service import get_oel
    result = get_oel(cas)
    if result:
        return {"found": True, "cas": cas, **result}
    return {"found": False, "cas": cas,
            "message": "Bu madde için TR OEL limiti tanımlanmamış." if lang=="TR"
                       else "No TR OEL limit defined for this substance."}


@app.get("/api/v1/adr/lookup")
async def adr_lookup(un_no: str, packing_group: str = "II", lang: str = "TR"):
    """
    UN numarasına göre ADR bilgisi (kemler, tünel kodu, ambalaj grubu).
    """
    from app.services.transport_adr_service import get_adr_details
    result = get_adr_details(un_no, packing_group)
    if result:
        return {"found": True, "un_no": un_no, "packing_group": packing_group, **result}
    return {"found": False, "un_no": un_no,
            "message": "UN numarası bulunamadı." if lang=="TR" else "UN number not found."}


@app.post("/api/v1/adr/auto-detect")
async def adr_auto_detect(body: dict):
    """
    H kodlarından UN numarası otomatik tespit.
    Input: {h_codes:[...], flash_point:27, lang:"TR"}
    Output: {un_no, shipping_name, hazard_class, packing_group, kemler, tunnel_code}
    """
    h_codes     = body.get("h_codes", [])
    flash_point = body.get("flash_point")
    lang        = body.get("lang", "TR")

    # pdf_sds_service'deki _auto_un kullan
    import sys
    sys.path.insert(0, ".")
    from app.services.pdf_sds_service import _auto_un
    from app.services.transport_adr_service import get_adr_details

    result = _auto_un(h_codes)
    if result:
        un = result.get("un_no", "")
        pg = result.get("packing_group", "II")
        adr_det = get_adr_details(un, pg) if un and un != "UN0000" else {}
        return {
            "found": True,
            "auto": True,
            **result,
            "kemler":      adr_det.get("kemler", "—"),
            "tunnel_code": adr_det.get("tunnel_code", "—"),
            "classification_code": adr_det.get("classification_code", "—"),
            "note": ("Otomatik tespit — sevkiyat öncesi uzman onayı alın." if lang=="TR"
                     else "Auto-detected — verify with transport expert before shipment."),
        }
    return {"found": False, "h_codes": h_codes,
            "message": "Bu H kodları için ADR sınıflandırması tespit edilemedi." if lang=="TR"
                       else "No ADR classification detected for these H codes."}


@app.get("/api/v1/codes/h/{code}")
async def h_code_text(code: str, lang: str = "TR"):
    """H kodu metnini döndür (TR/EN/DE)."""
    from app.services.codes_i18n import get_h
    text = get_h(lang.upper(), code.upper())
    if text:
        return {"code": code.upper(), "lang": lang, "text": text}
    raise HTTPException(status_code=404, detail=f"{code} bulunamadı.")


@app.get("/api/v1/codes/p/{code}")
async def p_code_text(code: str, lang: str = "TR"):
    """P kodu metnini döndür (TR/EN/DE)."""
    from app.services.codes_i18n import get_p
    text = get_p(lang.upper(), code.upper())
    if text:
        return {"code": code.upper(), "lang": lang, "text": text}
    raise HTTPException(status_code=404, detail=f"{code} bulunamadı.")


@app.get("/api/v1/codes/ghs/{h_code}")
async def ghs_for_h_code(h_code: str, lang: str = "TR"):
    """H koduna karşılık gelen GHS piktogramlarını döndür."""
    from app.services.ghs_pictogram import get_ghs_codes, H_TO_GHS
    h = h_code.upper()
    ghs_list = get_ghs_codes([h])
    return {
        "h_code": h,
        "ghs_codes": ghs_list,
        "count": len(ghs_list),
    }


@app.get("/api/v1/codes/all")
async def all_codes(lang: str = "TR"):
    """Tüm H ve P kodlarını döndür."""
    from app.services.codes_i18n import H_STMTS, P_STMTS, EUH_STMTS
    l = lang.upper()
    return {
        "lang": l,
        "h_codes": H_STMTS.get(l, {}),
        "p_codes": P_STMTS.get(l, {}),
        "euh_codes": EUH_STMTS.get(l, {}),
    }



# ── Konsantrasyon Aralığı Dropdown ────────────────────────────────────────────

@app.get("/api/v1/sds/concentration-ranges/{cas}")
async def concentration_ranges(
    cas: str,
    lang: str = "TR",
    scl: str = "",          # örn. "0.5,2.0,5.0" — virgülle ayrılmış SCL değerleri
    m_acute: int = 1,
    m_chronic: int = 1,
):
    """
    CAS numarası için konsantrasyon aralığı dropdown listesi.
    Her aralık için aktif karışım sınıflandırması, sinyal sözcüğü ve piktogramlar döner.

    Parametreler:
      cas       : CAS numarası
      lang      : TR | EN | DE
      scl       : Virgülle ayrılmış özel eşik değerleri (%) — Annex VI SCL
      m_acute   : Akut M-faktörü (su ortamı için)
      m_chronic : Kronik M-faktörü
    """
    from app.services.concentration_ranges import build_concentration_ranges

    scl_list = []
    if scl:
        try:
            scl_list = [float(v.strip()) for v in scl.split(",") if v.strip()]
        except ValueError:
            pass

    ranges = build_concentration_ranges(
        cas=cas,
        scl_thresholds=scl_list or None,
        m_factor_acute=m_acute,
        m_factor_chronic=m_chronic,
        lang=lang.upper(),
    )

    return {
        "cas"   : cas,
        "lang"  : lang.upper(),
        "count" : len(ranges),
        "ranges": ranges,
    }


@app.get("/api/v1/sds/concentration-ranges/{cas}/standard")
async def concentration_standard_ranges(
    cas: str,
    lang: str = "TR",
    scl: str = "",
    m_acute: int = 1,
    m_chronic: int = 1,
):
    """
    Aşama 1 — Standart 7-seçenekli dropdown.
    needs_refinement=True olan aralıklar için /refine endpoint'i çağırılmalı.
    """
    from app.services.concentration_ranges import build_standard_ranges
    scl_list = [float(v.strip()) for v in scl.split(",") if v.strip()] if scl else []
    ranges = build_standard_ranges(
        cas=cas, scl_thresholds=scl_list or None,
        m_factor_acute=m_acute, m_factor_chronic=m_chronic, lang=lang.upper(),
    )
    return {"cas": cas, "lang": lang.upper(), "count": len(ranges), "ranges": ranges}


@app.get("/api/v1/sds/concentration-ranges/{cas}/refine")
async def concentration_refine(
    cas: str,
    lower: float,
    upper: float,
    lang: str = "TR",
    scl: str = "",
    m_acute: int = 1,
    m_chronic: int = 1,
):
    """
    Aşama 2 — Seçilen aralık içindeki kritik eşikler ve alt/üst seçenekler.

    Her eşik için döner:
      threshold, question (kullanıcıya sorulacak), below{}, above{},
      classification_changes (True → eşiğin iki tarafı farklı sınıf)

    classification_changes=False ise → iki taraf aynı sınıf,
    kullanıcıya soruda sadece ticari sır koruması için göster.
    """
    from app.services.concentration_ranges import get_refinements
    scl_list = [float(v.strip()) for v in scl.split(",") if v.strip()] if scl else []
    refs = get_refinements(
        lower=lower, upper=upper, cas=cas,
        scl_thresholds=scl_list or None,
        m_factor_acute=m_acute, m_factor_chronic=m_chronic, lang=lang.upper(),
    )
    return {
        "cas": cas, "lower": lower, "upper": upper,
        "lang": lang.upper(),
        "refinement_count": len(refs),
        "refinements": refs,
    }
