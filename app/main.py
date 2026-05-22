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

# ─── Cache engelleme — tüm JS/HTML yanıtları tarayıcı tarafından cache'lenmez ──
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest

class NoCacheMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: StarletteRequest, call_next):
        response = await call_next(request)
        path = request.url.path
        if path == "/" or path.endswith(".js") or path.endswith(".html"):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"]  = "no-cache"
            response.headers["Expires"] = "0"
        return response

app.add_middleware(NoCacheMiddleware)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "HazardDesk PDF API"}


@app.get("/")
async def serve_frontend():
    """SDS Hesaplama arayüzü — cache'lenmez, her zaman taze yüklenir"""
    html_path = os.path.join(os.path.dirname(__file__), '..', 'static', 'index.html')
    return FileResponse(
        html_path,
        media_type="text/html",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        }
    )


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
        # all_h_codes: dominance öncesi tam sınıflandırma (SDS Bölüm 2.1 için)
        all_h_codes = [str(h) for h in data.get('all_h_codes', []) if h is not None] or h_codes
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

        # P kodları — eko H kodu eklendikten SONRA hesaplanacak (aşağıda)

        # EUH
        euh_details = data.get('euh_details', []) or [{'code':c,'text':''} for c in euh_codes]
        euh_result  = {'euh_codes': euh_codes, 'euh_details': euh_details}

        # Ekoloji
        eco_comps = [{'cas': c.get('cas',''), 'name': c.get('name',''),
                      'name_tr': c.get('name_tr',''),
                      'conc': float(c.get('conc', c.get('concentration',0)) or 0),
                      'hazards': c.get('hazards',[]),
                      'm_factors': c.get('m_factors', {})} for c in components]
        try:
            eco_result = calculate_ecological(eco_comps)
        except Exception:
            eco_result = None

        # Backend eko sonucunu h_codes/all_h_codes'a ekle (REPLACE — frontend sonucunu geçersiz kıl)
        # Frontend JS eco_engine farklı eşik kullanabilir; Python sonucu yetkilidir.
        # Frontend'den gelen tüm H400/H410/H411/H412/H413 önce temizlenir, sonra Python sonucu eklenir.
        ECO_H_CODES = {'H400', 'H410', 'H411', 'H412', 'H413'}
        _eco_h = None
        if eco_result and hasattr(eco_result, 'aquatic') and eco_result.aquatic:
            _eco_h = eco_result.aquatic.h_code
        if _eco_h:
            h_codes     = [h for h in h_codes     if h not in ECO_H_CODES] + [_eco_h]
            all_h_codes = [h for h in all_h_codes if h not in ECO_H_CODES] + [_eco_h]
        elif eco_result is not None:
            # Eko sonucu yok → frontend'den gelen eko H kodlarını da temizle
            h_codes     = [h for h in h_codes     if h not in ECO_H_CODES]
            all_h_codes = [h for h in all_h_codes if h not in ECO_H_CODES]

        # H420 — Ozon tabakasına zararlı (CLP Annex VI)
        # ecological_service sds_section_12['H420'] listesine yazar ama h_codes'a eklemez
        _sds12 = getattr(eco_result, 'sds_section_12', None) or (eco_result.get('sds_section_12', {}) if isinstance(eco_result, dict) else {})
        if _sds12.get('H420') and 'H420' not in h_codes:
            h_codes = list(h_codes) + ['H420']
        if _sds12.get('H420') and 'H420' not in all_h_codes:
            all_h_codes = list(all_h_codes) + ['H420']

        # H314 nötralizasyon kararı — P kodu hesabından ÖNCE h_codes filtrelenir
        _H314_COVERED = {'H314', 'H318', 'H315', 'H319'}
        _h314_removed_flag = bool(data.get('h314_neutralization_removed', False))
        if _h314_removed_flag:
            h_codes     = [h for h in h_codes     if h not in _H314_COVERED]
            all_h_codes = [h for h in all_h_codes if h not in _H314_COVERED]
            # Signal word yeniden hesapla (H314 kalkınca Danger→Warning olabilir)
            _danger_h_set = {'H200','H201','H202','H203','H204','H205',
                             'H220','H222','H224','H225','H240','H241',
                             'H250','H260','H270','H271','H272',
                             'H300','H301','H310','H311','H330','H331',
                             'H334','H340','H350','H360','H370','H372'}
            signal = 'Danger' if any(h in _danger_h_set for h in h_codes) else 'Warning'

        # P kodlarını güncel h_codes ile yeniden hesapla (eko H kodu + H314 filtresi dahil)
        p_result = assign_p_codes(h_codes, signal, usage=usage)
        p_result['label'] = select_label_p_codes(p_result['p_codes'], 6, h_codes=h_codes)
        p_result['sds']   = classify_sds_p_codes(p_result['p_codes'])

        if eco_result is None:
            eco_result = {'sds_section_12': {}}  # boş fallback — dict olarak

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
            # NOT: µ (U+00B5), ² (U+00B2), ³ (U+00B3) DejaVu'da desteklenir —
            # dönüştürme yapılmaz (25 µg/mL → 25 ug/mL hatası engellendi)
        })
        def _safe(text: str) -> str:
            """PDF için güvenli metin — sorunlu Unicode karakterleri ASCII'ye çevir"""
            if not text:
                return text
            return text.translate(_UNICODE_SAFE)

        # Transport verisi dönüştürme: frontend {road,sea,air} → backend {un_no, ...}
        def _map_transport(t: dict) -> dict:
            """Frontend TransportEngine çıktısını PDF servisinin beklediği formata çevirir.
            Frontend: { road:{un, class, pg, label, ...}, sea:{...}, air:{...} }
            Backend:  { un_no, shipping_name, hazard_class, packing_group, ... }
            """
            road = t.get('road') or {}
            un_raw = road.get('un', '')
            if not un_raw or t.get('not_regulated'):
                return t  # PDF servisi kendi _auto_un'ını çalıştırsın
            return {
                'un_no':         un_raw,
                'shipping_name': road.get('label', ''),
                'hazard_class':  road.get('class', ''),
                'packing_group': road.get('pg', '') or '',
                'sub_class':     road.get('sub_class', '') or '',
                'note':          road.get('note', '') or '',
                'env_hazard':    road.get('env_mark', False),
                # orijinal yapıyı da sakla (sea/air için)
                'road': road,
                'sea':  t.get('sea') or {},
                'air':  t.get('air') or {},
                'not_regulated': False,
            }

        # Bileşenler
        def _map_comp(c):
            name    = _safe(c.get('name', ''))
            name_tr = _safe(c.get('name_tr', ''))
            # "%100'e tamamla" bileşeni — PDF'de standart metin
            if name and 'mevzuata' in name.lower():
                name = 'Mevzuata göre sınıflandırılmamıştır'
            if name_tr and 'mevzuata' in name_tr.lower():
                name_tr = 'Mevzuata göre sınıflandırılmamıştır'
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
                'name_tr':       name_tr,   # Türkçe SDS için
                'concentration': conc,      # standart alan (servisler bu adı kullanır)
                'conc':          conc,      # eski servisler için alias (comp.get('conc',...))
                'conc_str':      conc_str,
                'conc_min':      conc_min,
                'conc_max':      conc_max,
                'hazards':       [
                    {k: v for k, v in {
                        'h_class':   h.get('h_class', ''),
                        'h_code':    h.get('h_code', ''),
                        'note_flag': h.get('note_flag'),
                        'note':      h.get('note'),
                        'repro_sub': h.get('repro_sub'),
                    }.items() if v is not None and v != ''}
                    for h in c.get('hazards', [])
                ],
                'scl':           c.get('scl', []),
                'ec_no':         c.get('ec_no', ''),
                'reach_no':      c.get('reach_no', ''),
                'annex_vi':      c.get('annex_vi', False),
                'source_priority': c.get('source_priority', 4),
                # ATE kullanıcı beyanı — SEA §3.1.3.6.2.2
                'ate_unknown':   bool(c.get('ate_unknown', False)),
                'ate_dict':      c.get('ate') or {},
                # Bileşen tipi: 'normal' | 'polymer' | 'uvcb' | 'fragrance'
                'comp_type':     c.get('comp_type', 'normal'),
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
                'h_codes':     h_codes,      # etiket için (dominance uygulanmış)
                'all_h_codes': all_h_codes,  # SDS Bölüm 2.1 için (tam sınıflandırma)
                'signal_word': signal,
                'passed': [
                    {k: v for k, v in {
                        'h_class':    h.get('h_class',''),
                        'h_code':     h.get('h_code',''),
                        'reason':     _safe(h.get('reason','')),
                        'cutoff_used':_safe(h.get('cutoff_used','')),
                        'note_flag':  h.get('note_flag'),
                        'note':       h.get('note'),
                        'repro_sub':  h.get('repro_sub'),
                    }.items() if v is not None and v != ''}
                    for h in data.get('clp_passed', [])
                ],
            },
            'euh':          euh_result,
            'p_codes':      p_result,
            'components':   mapped_comps,
            'disclosure_map': disc_map,
            'phys_props':   phys_in,
            'eco':          eco_result,
            # Frontend TransportEngine sonucunu her zaman kullan.
            # JS motoru (transport_engine.js) tek kaynak — H314/pH durumu orada zaten işlendi.
            'transport':    _map_transport(data.get('transport', {})),
            'revision': {
                'date':    rev_date,
                'no':      revision_in.get('no', '1'),
                'version': revision_in.get('version', '1.0'),
                'notes':   revision_in.get('notes', 'İlk yayın'),
            },
            'ate_mix_details': data.get('ate_mix_details', {}),
            'h314_neutralization_removed': bool(data.get('h314_neutralization_removed', False)),
            'clp_note_overrides': data.get('clp_note_overrides', {}),
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

@app.get("/api/v1/sds/substance/phys")
async def substance_phys_lookup(cas: str):
    """
    CAS numarasına göre fiziksel özellik verisi döndür.
    Önce yerel önbellekten bakar (data/phys_cache/),
    bulamazsa PubChem Experimental Properties API'sından çeker.
    """
    try:
        from app.services.pubchem_phys_service import fetch_phys
        props = await fetch_phys(cas.strip())
        return {"cas": cas, "found": bool(props), "props": props}
    except Exception as e:
        return {"cas": cas, "found": False, "props": {}, "error": str(e)}


@app.get("/api/v1/sds/substance/lookup")
async def substance_lookup(cas: str):
    """
    CAS numarasına göre madde bilgisi döndür.
    Hiyerarşi:
      1. data/cl/   — SEA Ek-6 (mutlak)
      2. data/annex6/ — CLP Annex VI
      3. substances_custom.json
      4. ECHA C&L Inventory API (canlı, arşive kaydedilir)
    """
    from app.services.substance_lookup import lookup_substance, get_oel
    from app.services.reach_db import get_ec_no, get_reg_no

    oel = get_oel(cas)

    # Sıra 1-2-3: Lokal dosyalar
    result = lookup_substance(cas)

    # Sıra 5-6: ECHA C&L API → data/echa_cl/ | PubChem → data/pubchem_cl/
    # (kaydetme echa_service.lookup_echa_api içinde yapılır)
    if result is None:
        try:
            from app.services.echa_service import lookup_echa_api
            echa = await lookup_echa_api(cas)
            if echa and echa.get('h_codes'):
                cache_src  = echa.get('_cache_source', 'echa_cl')
                is_pubchem = cache_src == 'pubchem'
                return {
                    "found"     : True,
                    "cas"       : cas,
                    "name"      : echa.get("name", ""),
                    "ec_no"     : echa.get("ec_no", "") or get_ec_no(cas),
                    "reach_no"       : get_reg_no(cas),
                    "sea_ek6"        : False,
                    "annex_vi"       : False,
                    "source_priority": 5,   # ECHA C&L API / PubChem — güvenilirlik düşük
                    "signal"         : echa.get("signal", ""),
                    "pictograms": echa.get("pictograms", []),
                    "hazards"   : [
                        {"h_class": cls, "h_code": code}
                        for cls, code in zip(
                            echa.get("hazard_classes", []),
                            echa.get("h_codes", [])
                        )
                    ],
                    "m_factors" : echa.get("m_factors", {}),
                    "scl"       : [],
                    "oel"       : oel,
                    "source"    : echa.get("source", "PubChem" if is_pubchem else "ECHA C&L API"),
                }
        except Exception:
            pass

    if result:
        return {
            "found"     : True,
            "cas"       : cas,
            "name"      : result.get("name", ""),
            "name_tr"   : result.get("name_tr", ""),   # Türkçe SDS Bölüm 3 için
            "ec_no"     : result.get("ec_no", "") or get_ec_no(cas),
            "reach_no"  : get_reg_no(cas),
            "sea_ek6"   : result.get("sea_ek6", False),
            "annex_vi"  : result.get("annex_vi", False),
            "signal"    : result.get("signal", ""),
            "pictograms": result.get("pictograms", []),
            "hazards"   : result.get("hazards", []),   # _annex_supplement:True olanlar ek tehlikeler
            "m_factors" : result.get("m_factors", {}),
            "scl"       : result.get("scl", []),
            "oel"       : oel,
            "source"    : result.get("source", ""),
        }

    # REACH DB'de EC/REACH no var mı?
    ec  = get_ec_no(cas)
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

    components  = body.get("components", [])
    lang        = body.get("lang", "TR")
    mixture_ph  = body.get("mixture_ph", None)   # Karışım pH değeri (opsiyonel)

    try:
        # 1. Ana CLP (cut-off tablosu) — pH uç değer varsa doğrudan H314+H318 atanır
        result = classify_mixture_clp(components, mixture_ph=mixture_ph)

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
        result["label"]    = select_label_p_codes(result["p_codes"], max_label, h_codes=h_codes)
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


# ── ANA HESAP ENDPOİNT'İ — tek motor, tek kaynak ────────────────────────────
@app.post("/api/v1/sds/calculate")
async def sds_calculate(body: dict = Body(...)):
    """
    Tüm motorları Python'da çalıştır, birleşik sonuç döndür.
    JS frontend bu endpoint'i çağırır; JS engine'ler çalışmaz.

    Input:
        components   : [{cas, name, conc, concMax, hazards, m_factors, scl, ...}]
        form         : 'liquid' | 'solid' | 'gas' | 'paste' | 'aerosol'
        user_fp      : parlama noktası (kullanıcı girişi, opsiyonel)
        mixture_ph   : pH (string, ör: "7.0" veya "2-4", opsiyonel)
        test_data    : {density, boiling_point, viscosity, ...}
        usage        : 'industrial' | 'consumer' | 'professional'
        lang         : 'TR' | 'EN'

    Output:
        h_codes, all_h_codes, signal, clp_passed, euh, p_codes,
        physical, stot, eco, theo_props, warnings
    """
    import dataclasses
    from app.services.clp_service         import classify_mixture_clp, DANGER_H as _DANGER_H
    from app.services.physical_engine     import calculate as phys_calculate
    from app.services.stot_engine         import calculate as stot_calculate
    from app.services.euh_engine          import calculate as euh_calculate
    from app.services.eco_engine          import calculate as eco_calculate
    from app.services.transport_engine    import classify as transport_classify
    from app.services.p_code_service      import assign_p_codes, select_label_p_codes, classify_sds_p_codes
    from app.services.ghs_pictogram       import get_ghs_codes
    from app.services.codes_i18n          import correct_hclass, translate_hclass

    comps       = body.get('components', [])
    form        = body.get('form', 'liquid')
    user_fp_raw = body.get('user_fp') or body.get('flash_point')
    mixture_ph  = body.get('mixture_ph')
    test_data   = body.get('test_data') or {}
    usage       = body.get('usage', 'industrial')
    lang        = body.get('lang', 'TR')

    user_fp = None
    if user_fp_raw is not None:
        try: user_fp = float(user_fp_raw)
        except: pass

    try:
        # ── 1. Fiziksel tehlikeler + teorik özellikler ────────────────────────
        phys_result = phys_calculate(comps, form=form, user_fp=user_fp, test_data=test_data)

        # ── 2. CLP karışım hesabı (cut-off tablosu + ATE) ────────────────────
        clp_result = classify_mixture_clp(comps, mixture_ph=mixture_ph)

        # ── 3. STOT RE ────────────────────────────────────────────────────────
        stot_result = stot_calculate(comps)

        # ── 4. EUH kodları ────────────────────────────────────────────────────
        euh_result = euh_calculate(comps)

        # ── 5. Ekoloji ────────────────────────────────────────────────────────
        eco_result = eco_calculate(comps)

        # ── 6. Taşımacılık — ADR 2023 / IMDG / IATA ──────────────────────────
        # Fiziksel motordaki H22x/H228 kodlarını CLP'ye ilave et
        _phys_h_transport = [
            (r.get('h') or r.get('h_code') or '')
            for r in phys_result.get('results', [])
        ]
        transport_result = transport_classify(
            h_codes=list(clp_result.get('h_codes', [])),
            form=form,
            phys_h_codes=_phys_h_transport,
        )

        # ── H kodlarını birleştir ─────────────────────────────────────────────
        all_h = set(clp_result.get('h_codes', []))

        # Fiziksel tehlikeler
        for r in phys_result.get('results', []):
            h = r.get('h') or r.get('h_code')
            if h: all_h.add(h)

        # STOT RE
        for h in stot_result.get('h_codes', []):
            all_h.add(h)

        # Ekoloji
        for h in eco_result.get('h_codes', []):
            all_h.add(h)

        all_h_list = sorted(all_h)

        # ── Sinyal kelimesi ───────────────────────────────────────────────────
        signal = 'Danger' if (all_h & _DANGER_H) else ('Warning' if all_h else '')

        # ── clp_passed listesi (PDF Bölüm 2.1 için) ──────────────────────────
        clp_passed = []
        seen = set()

        # CLP cut-off sonuçları
        for p in clp_result.get('passed', []):
            hc = (p.get('h_code') or '').replace('*','').strip()[:4]
            if hc and hc not in seen:
                seen.add(hc)
                fixed = correct_hclass(hc, p.get('h_class',''))
                clp_passed.append({
                    'h_code':     hc,
                    'h_class':    fixed or p.get('h_class',''),
                    'reason':     p.get('reason',''),
                    'cutoff_used':p.get('cutoff_used',''),
                })

        # Fiziksel tehlikeler
        for r in phys_result.get('results', []):
            hc = (r.get('h') or r.get('h_code') or '').replace('*','').strip()[:4]
            if hc and hc not in seen:
                seen.add(hc)
                _reason = r.get('source') or r.get('reason') or 'Fiziksel tehlike motoru'
                _cutoff = r.get('cutoff_used') or '—'
                clp_passed.append({
                    'h_code':     hc,
                    'h_class':    r.get('h_class',''),
                    'reason':     _reason,
                    'cutoff_used':_cutoff,
                })

        # STOT RE
        for r in stot_result.get('results', []):
            hc = (r.get('h') or '').replace('*','').strip()[:4]
            if hc and hc not in seen:
                seen.add(hc)
                clp_passed.append({
                    'h_code':     hc,
                    'h_class':    r.get('h_class',''),
                    'reason':     r.get('reason','STOT RE toplamsal'),
                    'cutoff_used':'—',
                })

        # Ekoloji
        if eco_result.get('aquatic'):
            aq = eco_result['aquatic']
            hc = aq.get('h','')
            if hc and hc not in seen:
                seen.add(hc)
                clp_passed.append({
                    'h_code':     hc,
                    'h_class':    aq.get('h_class',''),
                    'reason':     aq.get('formula','Sucul ekoloji'),
                    'cutoff_used':'—',
                })
        if eco_result.get('aquatic_acute'):
            aq = eco_result['aquatic_acute']
            hc = aq.get('h','')
            if hc and hc not in seen:
                seen.add(hc)
                clp_passed.append({
                    'h_code':     hc,
                    'h_class':    aq.get('h_class',''),
                    'reason':     aq.get('formula','Sucul akut'),
                    'cutoff_used':'—',
                })

        # ── P kodları ─────────────────────────────────────────────────────────
        p_result = assign_p_codes(all_h_list, signal, usage=usage)
        p_result['label'] = select_label_p_codes(p_result['p_codes'], 6, h_codes=all_h_list)
        p_result['sds']   = classify_sds_p_codes(p_result['p_codes'])

        # ── Teorik özellikler ─────────────────────────────────────────────────
        theo_props = phys_result.get('theo_props', {})

        return {
            'success':    True,
            'h_codes':    all_h_list,
            'all_h_codes':all_h_list,
            'signal':     signal,
            'clp_passed': clp_passed,
            'euh':        euh_result,
            'euh_codes':  euh_result.get('euh_codes', []),
            'euh_details':euh_result.get('euh_details', []),
            'p_codes':    p_result,
            'physical':   {
                'results':  phys_result.get('results', []),
                'primary':  phys_result.get('primary', []),
                'extra':    phys_result.get('extra', []),
                'warnings': phys_result.get('warnings', []),
            },
            'stot':       stot_result,
            'eco':        eco_result,
            'transport':  transport_result,
            'theo_props': theo_props,
            'warnings':   (phys_result.get('warnings', []) +
                           stot_result.get('warnings', []) +
                           clp_result.get('warnings', [])),
            'pictograms': get_ghs_codes(all_h_list),
            'ate_details':clp_result.get('ate_mix_details', {}),
        }

    except Exception as e:
        import traceback
        raise HTTPException(status_code=500,
                            detail=str(e) + '\n' + traceback.format_exc())


# ── ÇIKTI: Veri Endpoint'leri ─────────────────────────────────────────────────

@app.get("/api/v1/svhc/{cas}")
async def svhc_check_single(cas: str):
    """Tek CAS numarası için SVHC aday listesi kontrolü."""
    from app.services.svhc_service import check_svhc_single
    result = check_svhc_single(cas)
    if result:
        return {"found": True, **result}
    return {"found": False, "cas": cas}


@app.post("/api/v1/svhc/check")
async def svhc_check_mixture(body: dict):
    """Karışım bileşenleri için SVHC kontrolü. Input: {components: [...]}"""
    from app.services.svhc_service import check_svhc_mixture
    components = body.get("components", [])
    return check_svhc_mixture(components)


@app.get("/api/v1/annex6/meta")
async def annex6_meta():
    """CLP Annex VI veri seti meta bilgisi — ATP kapsama, madde sayısı, güncelleme tarihi."""
    import json as _json
    meta_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'annex6_meta.json')
    try:
        with open(meta_path, encoding='utf-8') as f:
            return _json.load(f)
    except FileNotFoundError:
        return {"error": "meta dosyası bulunamadı"}


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
    H kodlarından UN numarası + ADR/IMDG/IATA sınıflandırması.
    ADR 2023 Tablo 2.1.3.10 çoklu tehlike öncelik matrisi uygulanır.

    Input:
        h_codes       : ['H226', 'H302', ...]
        phys_h_codes  : ['H224', 'H228', ...] (opsiyonel, fiziksel motordan)
        form          : 'liquid' | 'solid' | 'gas' | 'aerosol'
        lang          : 'TR' | 'EN'
    """
    from app.services.transport_engine import classify as transport_classify
    h_codes      = body.get('h_codes', [])
    phys_h_codes = body.get('phys_h_codes', [])
    form         = body.get('form', 'liquid')
    result = transport_classify(h_codes=h_codes, form=form, phys_h_codes=phys_h_codes)
    return {'found': not result.get('not_regulated', True), **result}


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
