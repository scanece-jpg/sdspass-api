"""
HazardDesk PDF API — Minimal Deploy
DB gerektirmez, sadece PDF üretimi + madde lookup
"""

from fastapi import FastAPI, Body, Response, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import sys, os, json
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

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


# ─── SDS DENETIM ENDPOINT ─────────────────────────────────────────────────────
from app.services.review_endpoint import router as review_router
app.include_router(review_router)


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
from app.services.clp_service import DANGER_H, is_danger
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

        # Bileşen H kodlarını tazele + CLP dominans uygula.
        # Render'da lokal cache yok → lookup_echa_api ile önbellek/canlı çekim kullan.
        import asyncio as _aio
        from app.services.substance_lookup import (
            lookup_substance as _lu_sub,
            save_custom_substance as _save_custom,
            _load_custom as _custom_db,
        )
        from app.services.echa_service import _dedupe_h_codes as _dedup, lookup_echa_api as _lu_echa

        async def _refresh_comp(comp: dict, _prod_form: str = '') -> dict:
            cas = (comp.get('cas_no') or comp.get('cas') or '').strip()
            if not cas:
                return comp
            try:
                # 1. Yerel DB (SEA Ek-6, CLP Annex VI, substances_custom — git'te mevcut)
                fresh = _lu_sub(cas, form=_prod_form)
                if fresh is not None:
                    # DB'de kayıt var — hazards boş olsa bile (sınıflandırılmamış madde: su, glikoz vb.)
                    # ECHA API'ye düşme; boş hazards kasıtlı "sınıflandırılmamış" anlamına gelir.
                    if fresh.get('hazards'):
                        raw = {
                            'h_codes':        [h['h_code'] for h in fresh['hazards']],
                            'hazard_classes':  [h['h_class'] for h in fresh['hazards']],
                        }
                        _dedup(raw)
                        c = dict(comp)
                        c['hazards'] = [
                            {'h_class': cls, 'h_code': code}
                            for cls, code in zip(raw['hazard_classes'], raw['h_codes'])
                        ]
                        return c
                    else:
                        # Sınıflandırılmamış — hazards listesini temizle, ECHA'ya gitme
                        c = dict(comp)
                        c['hazards'] = []
                        return c
                # 2. ECHA/PubChem API — önbellekten veya canlı çekim, deduplikasyon dahil
                echa = await _lu_echa(cas)
                if echa and echa.get('h_codes'):
                    # substances_custom.json'a kaydet — kalıcı, git'te commit'li
                    if cas not in _custom_db():
                        try:
                            _save_custom(cas, {
                                'name':       echa.get('name', ''),
                                'ec_no':      echa.get('ec_no', ''),
                                'signal':     echa.get('signal', ''),
                                'pictograms': echa.get('pictograms', []),
                                'hazards': [
                                    {'h_class': c2, 'h_code': h2}
                                    for c2, h2 in zip(
                                        echa.get('hazard_classes', []),
                                        echa.get('h_codes', [])
                                    )
                                ],
                                'm_factors': echa.get('m_factors', {}),
                                'index_no':  '',
                                'atp':       'pubchem-auto',
                            })
                        except Exception:
                            pass
                    c = dict(comp)
                    c['hazards'] = [
                        {'h_class': cls, 'h_code': code}
                        for cls, code in zip(
                            echa.get('hazard_classes', []),
                            echa.get('h_codes', [])
                        )
                    ]
                    return c
            except Exception:
                pass
            return comp

        _prod_form_for_refresh = data.get('form') or product.get('form') or 'liquid'
        components = list(await _aio.gather(*[_refresh_comp(c, _prod_form=_prod_form_for_refresh) for c in components]))
        # H360x/H361x sub-kodlarını kanonik büyük harfe normalize et (H361d→H361D, H360Df→H360FD)
        def _norm_sub(h: str) -> str:
            s = str(h).replace('*', '').strip()
            if len(s) <= 4:
                return s
            base, sfx = s[:4], s[4:].upper()
            if base in ('H360', 'H361'):
                if 'D' in sfx and 'F' in sfx:
                    sfx = 'FD'
                elif 'D' in sfx:
                    sfx = 'D'
                elif 'F' in sfx:
                    sfx = 'F'
                else:
                    sfx = ''
                return base + sfx
            return s

        # Tüm H kodlarını str'e normalize et — int/None gelirse PDF çökmez
        h_codes     = [_norm_sub(h) for h in data.get('h_codes', []) if h is not None]
        # all_h_codes: dominance öncesi tam sınıflandırma (SDS Bölüm 2.1 için)
        all_h_codes = [_norm_sub(h) for h in data.get('all_h_codes', []) if h is not None] or h_codes
        euh_codes   = [str(h) for h in data.get('euh_codes', []) if h is not None]
        p_codes_in  = data.get('p_codes', [])
        disc_map    = data.get('disclosure_map', {})
        supplier_in = data.get('supplier', {})
        phys_in     = data.get('phys_props', {})
        revision_in = data.get('revision', {})
        usage       = product.get('usage', 'industrial')
        form        = data.get('form', product.get('form', 'liquid'))

        # Signal word — clp_service.DANGER_H kullan (H225 dahil, doğru liste)
        # Frontend'den gelen signal_word öncelikli, fallback hesaplama
        signal = data.get('signal_word', '')
        if signal not in ('Danger', 'Warning'):
            clean = {h.split()[0] for h in h_codes if isinstance(h, str)}
            signal = 'Danger' if is_danger(clean) else 'Warning'

        # P kodları — eko H kodu eklendikten SONRA hesaplanacak (aşağıda)

        # EUH
        euh_details = data.get('euh_details', []) or [{'code':c,'text':''} for c in euh_codes]
        euh_result  = {'euh_codes': euh_codes, 'euh_details': euh_details}

        # Ekoloji — eco_comps hazırla
        eco_comps = [{'cas': c.get('cas',''), 'name': c.get('name',''),
                      'name_tr': c.get('name_tr',''),
                      'conc': float(c.get('conc', c.get('concentration',0)) or 0),
                      # worst_case_conc: ecological_service.calculate_aquatic() bunu okur.
                      # concMax varsa aralığın üst sınırını kullan.
                      'worst_case_conc': float(c.get('concMax') or c.get('conc', c.get('concentration',0)) or 0),
                      'hazards': c.get('hazards',[]),
                      'm_factors': c.get('m_factors', {})} for c in components]
        eco_result = None  # try bloğunda güncellenir; hata varsa reconciliation fallback devreye girer

        # Sabitler ve yetkili motor çıktıları — reconciliation bloğunda uygulanır
        ECO_H_CODES  = {'H400', 'H410', 'H411', 'H412', 'H413'}
        _FLAM_LIQ_H  = {'H224', 'H225', 'H226'}
        _auth_flam_h = None   # physical_engine: ölçülen FP → flam_liq H kodu
        _clp_res     = {}     # classify_mixture_clp sonucu — try bloğunda doldurulur
        # NOT: h_codes/all_h_codes güncellemeleri TEK reconciliation bloğunda yapılır

        # H314 nötralizasyon kararı — P kodu hesabından ÖNCE h_codes filtrelenir
        _H314_COVERED = {'H314', 'H318', 'H315', 'H319'}
        _h314_removed_flag = bool(data.get('h314_neutralization_removed', False))
        if _h314_removed_flag:
            h_codes     = [h for h in h_codes     if h not in _H314_COVERED]
            all_h_codes = [h for h in all_h_codes if h not in _H314_COVERED]
            # Signal word yeniden hesapla (H314 kalkınca Danger→Warning olabilir)
            signal = 'Danger' if is_danger({h.split()[0] for h in h_codes if isinstance(h, str)}) else 'Warning'

        # ── Python motorlarıyla clp_passed, transport ve ppe'yi yeniden hesapla ──
        # Frontend'den gelen değerler YERINE Python sonuçları kullanılır.
        # ISO 27001: tüm sınıflandırma hesapları sunucu tarafında yapılır.
        py_ppe = data.get('ppe', {})   # fallback değeri (hata durumu için)

        # ATE sağlık tehlikeleri — motor try'ından ÖNCE hesapla, böylece
        # motor hatası _be_ate_h'ı sıfırlayamaz (eski satır 434 sorunu giderildi)
        try:
            from app.services.clp_service import calculate_ate_health_h_codes as _ate_h_calc_pre
            _be_ate_h, _be_ate_details = _ate_h_calc_pre(
                components, form=product.get('form', 'liquid')
            )
        except Exception as _ate_pre_err:
            print(f'[ATE PRE ERROR] {_ate_pre_err}')
            _be_ate_h, _be_ate_details = [], {}

        try:
            from app.services.clp_service       import classify_mixture_clp as _clp_calc
            from app.services.physical_engine   import calculate as _phys_calc
            from app.services.stot_engine       import calculate as _stot_calc
            from app.services.transport_engine  import classify as _transport_calc
            from app.services.ppe_engine        import select as _ppe_calc
            from app.services.codes_i18n        import correct_hclass as _correct_hclass
            from app.services.phys_props_parser import (
                parse_all_phys_props as _parse_phys,
                get_calc             as _phys_calc_val,
                get_pcn_band         as _get_pcn_band,
            )

            # Fiziksel özellikleri parse et → display/calc/pcn/range_notes
            _parsed_phys = _parse_phys(phys_in)

            _form_val = product.get('form') or 'liquid'
            # Flash point — aralık girilmişse worst-case (min) alınır
            # JS auto-fill sonucu ise measured=False gelir → _user_fp=None bırak,
            # engine bileşenlerden hesaplamalı (B2 ile B9 tutarlı olsun).
            _req_methods: dict = data.get('phys_methods', {})
            _fp_req_m = _req_methods.get('flash_point', {}) if isinstance(_req_methods, dict) else {}
            _fp_is_user = _fp_req_m.get('measured', True) if isinstance(_fp_req_m, dict) else True
            _user_fp = _phys_calc_val(_parsed_phys, 'flash_point') if _fp_is_user else None
            if _user_fp is None:
                # Eski format fallback
                _fp_raw = phys_in.get('user_fp')
                if _fp_raw is not None:
                    try: _user_fp = float(_fp_raw)
                    except: pass

            # pH — clp_service kendi parse'ını yapıyor (aralık desteği mevcut)
            # ham string geçirilir; clp_service _parse_ph_range ile lo/hi ayırır
            _ph_raw = phys_in.get('ph') or None
            _clp_res  = _clp_calc(components, mixture_ph=_ph_raw, mixture_form=_form_val)
            _phys_res = _phys_calc(components, form=_form_val, user_fp=_user_fp)
            _stot_res = _stot_calc(components)

            try:
                eco_result = calculate_ecological(eco_comps)
            except Exception:
                eco_result = None

            # ── B9 theo_props backfill ───────────────────────────────────────────
            # physical_engine'in hesapladığı teorik değerleri kullanıcı boş
            # bıraktığı alanlar için _parsed_phys'e aktar.
            # measured: True  → kullanıcı girdi (ölçülen/beyan değer)
            # measured: False → motor hesapladı (teorik, KKDİK Ek-2 §9 dipnotu)
            _theo = _phys_res.get('theo_props') or {}
            _phys_methods: dict = {}
            # _req_methods yukarıda (_user_fp öncesinde) tanımlandı
            _BACKFILL_FIELDS = (
                'flash_point', 'boiling_point', 'density', 'vapor_density',
                'vapor_pressure', 'lel', 'uel', 'viscosity', 'solubility',
                'melting_point', 'auto_ignition', 'decomposition_temp', 'evap_rate',
            )
            for _bk in _BACKFILL_FIELDS:
                _tp = _theo.get(_bk)
                if not _tp:
                    continue
                _tp_val  = _tp.get('value')
                _tp_disp = _tp.get('display') or (str(_tp_val) if _tp_val is not None else None)
                _tp_std  = _tp.get('standard', '')
                _tp_mth  = _tp.get('method', '')
                _tp_err  = (_tp.get('error') or {}).get('pct')

                _existing = _parsed_phys.get(_bk)
                _has_user_val = (
                    isinstance(_existing, dict) and _existing.get('calc') is not None
                ) or (
                    _existing and not isinstance(_existing, dict)
                    and str(_existing).strip() not in ('', '0')
                )

                if _has_user_val:
                    # Kullanıcı değer girmiş — JS'den gelen measured bayrağına güven
                    # (motor auto-fill ise JS dataset.source='theo' → measured=False gönderir)
                    _req_m = _req_methods.get(_bk)
                    _is_measured = bool(_req_m.get('measured', True)) if isinstance(_req_m, dict) else True
                    # Kullanıcı girişinde standart = kullanıcının girdiği yöntem bilgisi;
                    # teorik engine standardı (_tp_std) buraya taşınmaz — Bölüm 9'da
                    # "hesaplanmış – CLP Annex VI" yerine doğru kaynak gösterilsin.
                    _user_std = (_req_m.get('standard', '') or '') if isinstance(_req_m, dict) else ''
                    _phys_methods[_bk] = {
                        'measured': _is_measured, 'standard': _user_std,
                        'error_pct': None if _is_measured else _tp_err,
                    }
                elif _tp_val is not None:
                    # Kullanıcı boş bırakmış, teorik değer var → backfill
                    # _tp.get('measured') True ise kullanıcı test verisi girmiş (theo değil)
                    _tp_measured = _tp.get('measured', False)
                    _parsed_phys[_bk] = {
                        'display': _tp_disp,
                        'calc':    _tp_val,
                        'pcn':     _tp_val,
                        'nd':      False,
                        'na':      False,
                        'theo':    not _tp_measured,
                    }
                    _phys_methods[_bk] = {
                        'measured':  _tp_measured,
                        'standard':  _tp_std,
                        'method':    _tp_mth,
                        'error_pct': _tp_err,
                    }
                elif _tp_disp:
                    # Sayısal değer yok ama metin açıklama var
                    # (örn. çözünürlük: "Su ile tam karışır", buharlaşma hızı: "Yavaş")
                    _tp_measured = _tp.get('measured', False)
                    _parsed_phys[_bk] = {
                        'display': _tp_disp,
                        'calc':    None,
                        'nd':      False,
                        'na':      False,
                        'theo':    not _tp_measured,
                    }
                    _phys_methods[_bk] = {
                        'measured':  _tp_measured,
                        'standard':  _tp_std,
                        'method':    _tp_mth,
                        'error_pct': None,
                    }
            # ────────────────────────────────────────────────────────────────────

            _cp   = []
            _seen = set()

            for p in _clp_res.get('passed', []):
                _hcf = (p.get('h_code') or '').replace('*','').strip()
                hc   = _norm_sub(_hcf)
                if hc[:4] not in ('H360', 'H361'):
                    hc = hc[:4]
                # ECO_H_CODES burada filtreleniyor: aquatik sınıflandırma yalnızca
                # ecological_service'den gelir (SEA Tablo 4.1.2 toplamsal formül).
                # clp_service'in 0.1% kesme değeri raporlama eşiğidir, sınıflandırma eşiği değil.
                if hc and hc not in _seen and hc not in ECO_H_CODES:
                    _seen.add(hc)
                    _fixed = _correct_hclass(hc, p.get('h_class',''))
                    _cp.append({
                        'h_code':      hc,
                        'h_class':     _fixed or p.get('h_class',''),
                        'reason':      p.get('reason',''),
                        'cutoff_used': p.get('cutoff_used',''),
                    })

            # CLP Ek-I §2.6.4.2: ölçülen FP varsa physical_engine kazanır
            # py_clp_passed temizle; h_codes/all_h_codes reconciliation bloğunda güncellenir
            if _user_fp is not None:
                _cp   = [e for e in _cp if e['h_code'] not in _FLAM_LIQ_H]
                _seen -= _FLAM_LIQ_H
                _auth_flam_h = next(
                    (r.get('h') for r in _phys_res.get('results', [])
                     if r.get('type') == 'flam_liq'),
                    None
                )

            for r in _phys_res.get('results', []):
                hc = (r.get('h') or r.get('h_code') or '').replace('*','').strip()[:4]
                if hc and hc not in _seen:
                    _seen.add(hc)
                    _cp.append({
                        'h_code':      hc,
                        'h_class':     r.get('h_class',''),
                        'reason':      r.get('source') or 'Fiziksel tehlike motoru',
                        'cutoff_used': r.get('cutoff_used') or '—',
                    })

            for r in _stot_res.get('results', []):
                hc = (r.get('h_code') or '').replace('*','').strip()[:4]
                if hc and hc not in _seen:
                    _seen.add(hc)
                    _cp.append({
                        'h_code':      hc,
                        'h_class':     r.get('h_class',''),
                        'reason':      r.get('reason','STOT RE toplamsal'),
                        'cutoff_used': '—',
                    })

            if eco_result and hasattr(eco_result, 'aquatic') and eco_result.aquatic:
                _aq = eco_result.aquatic
                hc = _aq.h_code
                if hc and hc not in _seen:
                    _seen.add(hc)
                    _cp.append({
                        'h_code':      hc,
                        'h_class':     _aq.h_class,
                        'reason':      _aq.formula or 'Sucul ekoloji',
                        'cutoff_used': '—',
                    })

            # ── CLP Baskınlık kuralı — Bölüm 2.1 tablosuna uygula ───────────────
            # Fiziksel motor sonuçları CLP dominance'dan sonra eklendi;
            # py_clp_passed kombinasyonuna da uygula.
            # Örnek: H225 varsa H226 Bölüm 2.1'den kaldırılır.
            _DOMINANCE_MAP = {
                'H225': ['H226'], 'H224': ['H225', 'H226'],
                'H271': ['H272'], 'H270': ['H271', 'H272'],
                'H314': ['H315', 'H319'],
                'H318': ['H319'],
                'H300': ['H301', 'H302'], 'H310': ['H311', 'H312'],
                'H330': ['H331', 'H332'],
                'H340': ['H341'], 'H350': ['H351'],
                'H360': ['H361'], 'H370': ['H371'],
                'H372': ['H373'],
                'H400': ['H401', 'H402'],
                'H410': ['H411', 'H412', 'H413'],
                'H411': ['H412', 'H413'],
                'H412': ['H413'],
            }
            _present = {e['h_code'] for e in _cp}
            _dominated = set()
            for _dom, _subs in _DOMINANCE_MAP.items():
                if _dom in _present:
                    _dominated.update(_subs)
            if _dominated:
                _cp = [e for e in _cp if e['h_code'] not in _dominated]

            py_clp_passed = _cp

            # Transport — fiziksel H kodlarını da ilet
            _phys_h_tr = [(r.get('h') or r.get('h_code') or '')
                          for r in _phys_res.get('results', [])]
            py_transport = _transport_calc(
                h_codes=list(_clp_res.get('h_codes', [])),
                form=_form_val,
                phys_h_codes=_phys_h_tr,
            )

            pass  # PPE reconciliation sonrası hesaplanır (ATE H kodları dahil olsun)

        except Exception as _eng_err:
            import traceback as _tb
            print(f'[PDF] Python motor hatası, frontend verisi kullanılıyor: {_eng_err}\n'
                  + _tb.format_exc())
            py_clp_passed = data.get('clp_passed', [])
            py_transport  = data.get('transport', {})
            py_ppe        = data.get('ppe', {})
            # _be_ate_h sıfırlanmıyor — motor try'ından önce hesaplandı, korunuyor
            # eco_result try bloğu içinde atanamamışsa bağımsız hesapla
            if eco_result is None:
                try:
                    eco_result = calculate_ecological(eco_comps)
                except Exception:
                    eco_result = None

        # ════════════════════════════════════════════════════════════════════════════
        # TEK UZLAŞTIRMA BLOĞU — backend motorlarının kesin sonuçları atomik olarak
        # h_codes, all_h_codes, py_clp_passed ve sds_section_12'ye yansıtılır.
        # Dağınık senkronizasyon kodunun TEK merkezi — buraya bakın, başka yerde yok.
        #
        # Politika:
        #   • Backend KESİN sonuç bulursa  → frontend verisini ez
        #   • Backend hiçbir şey bulamazsa → frontend verisine dokunma
        # ════════════════════════════════════════════════════════════════════════════

        # ── 1. Yanıcı Sıvı — ölçülen FP varsa physical_engine kazanır ────────────
        # CLP Ek-I §2.6.4.2 — py_clp_passed try bloğunda zaten temizlendi
        if _auth_flam_h is not None:
            h_codes     = [h for h in h_codes     if h not in _FLAM_LIQ_H] + [_auth_flam_h]
            all_h_codes = [h for h in all_h_codes if h not in _FLAM_LIQ_H] + [_auth_flam_h]

        # ── 2. Sucul Eko — ecological_service tek yetkili kaynak ───────────────────
        _final_eco_h = None
        try:
            if eco_result and hasattr(eco_result, 'aquatic') and eco_result.aquatic:
                _final_eco_h = eco_result.aquatic.h_code
        except Exception:
            pass

        # _final_eco_h hâlâ None ise → frontend eco koduna dokunma
        if _final_eco_h:
            # CLP §4.1.3.5.5: H410 bileşeni aynı zamanda H400 üretir → B2.1'de iki ayrı satır
            # Ama etikette (h_codes) H410 varken H400 fazlalık sayılır (SEA Md.29(1))
            # → all_h_codes (B2.1 sınıflandırma) her ikisini alır
            # → h_codes (B2.2 etiket) sadece baskın kodu alır
            _eco_add_label = [_final_eco_h]
            _eco_add_class = [_final_eco_h]
            # H410 → CLP §4.1.3.5.5: aynı zamanda H400 (B2.1 sınıflandırma)
            # ecological_service baskınlık kuralıyla tek sonuç döndürüyor;
            # H400 satırını eco_result.aquatic_acute üzerinden kontrol et
            _h400_also = False
            if _final_eco_h not in (None, 'H400') and eco_result is not None:
                _aq_acute = getattr(eco_result, 'aquatic_acute', None)
                if _aq_acute and getattr(_aq_acute, 'h_code', None) == 'H400':
                    _h400_also = True
            if _h400_also:
                _eco_add_class.append('H400')  # B2.1'e H400 da gider
                # h_codes'a H400 eklenmez — H410 zaten H400'ü kapsıyor (SEA Md.29(1))
            h_codes     = [h for h in h_codes     if h not in ECO_H_CODES] + _eco_add_label
            all_h_codes = [h for h in all_h_codes if h not in ECO_H_CODES] + _eco_add_class
            # py_clp_passed'da eko yoksa ekle
            _passed_eco_set = {e.get('h_code', '') for e in py_clp_passed}
            if _final_eco_h not in _passed_eco_set:
                py_clp_passed = list(py_clp_passed) + [{
                    'h_code':      _final_eco_h,
                    'h_class':     '',
                    'reason':      'Sucul ekoloji (ecological_service)',
                    'cutoff_used': '—',
                }]
            # H400 ayrı passed satırı — "Baskın tehlike sınıfı" notu yerine doğru gerekçe
            if _h400_also and 'H400' not in _passed_eco_set:
                py_clp_passed = list(py_clp_passed) + [{
                    'h_code':      'H400',
                    'h_class':     'Aquatic Acute 1',
                    'reason':      'CLP §4.1.3.5.5: H410 bileşeni Sucul Akut 1 (H400) de üretir',
                    'cutoff_used': '—',
                }]
            # sds_section_12['12.1'] güncelle:
            # - high confidence → her zaman güncelle (ecological_service'i ez)
            # - low confidence  → yalnızca boşsa güncelle
            try:
                _s12 = (getattr(eco_result, 'sds_section_12', None) or
                        (eco_result.get('sds_section_12', {}) if isinstance(eco_result, dict) else {}))
                if isinstance(_s12, dict):
                    _s12_cur = _s12.get('12.1', '')
                    if _s12_cur in ('Sınıflandırma yok', '', None):
                        _s12['12.1'] = _final_eco_h
            except Exception:
                pass

        # ── 2b. B12.1 garantisi — motor bulamasa bile h_codes'taki eco kodu yansıt ─
        # Bu adım h_codes'u yetkili kaynak olarak kullanarak tutarlılığı sağlar.
        _eco_h_in_hcodes = next((h for h in h_codes if h in ECO_H_CODES), None)
        if _eco_h_in_hcodes:
            try:
                _s12b = (getattr(eco_result, 'sds_section_12', None) or
                         (eco_result.get('sds_section_12', {}) if isinstance(eco_result, dict) else {}))
                if isinstance(_s12b, dict) and _s12b.get('12.1', '') in ('Sınıflandırma yok', '', None):
                    _s12b['12.1'] = _eco_h_in_hcodes
            except Exception:
                pass

        # ── 3. H420 — Ozon tabakasına zararlı ────────────────────────────────────
        _sds12_ref = (getattr(eco_result, 'sds_section_12', None) or
                      (eco_result.get('sds_section_12', {}) if isinstance(eco_result, dict) else {}))
        if _sds12_ref.get('H420'):
            if 'H420' not in h_codes:     h_codes     = list(h_codes)     + ['H420']
            if 'H420' not in all_h_codes: all_h_codes = list(all_h_codes) + ['H420']

        # ── 4. Signal word — h_codes güncellenince yeniden hesapla ───────────────
        _clean_h = {h.split()[0] for h in h_codes if isinstance(h, str)}
        signal = 'Danger' if is_danger(_clean_h, _clp_res.get('passed', [])) else 'Warning'

        # ── 4b. Skin/Eye kodları — classify_mixture_clp override ─────────────────
        # Reconciliation sadece flam/eco/ozone h_codes'u güncelliyor; H314/H315/H318/H319
        # frontend'den ne geldiyse kalıyordu. pH-tabanlı H314 B2.1'e yazılıyor ama
        # h_codes (etiket/P-kodu/B11 kaynağı) güncellenmiyordu → H315/H318 etikette kalıyordu.
        _SKIN_EYE_H = {'H314', 'H315', 'H318', 'H319'}
        _clp_skin_new = {h for h in _clp_res.get('h_codes', []) if h in _SKIN_EYE_H}
        if _clp_skin_new:
            # Backend CLP motor sonucu var → frontend skin/eye kodlarını ez
            h_codes = [h for h in h_codes if h not in _SKIN_EYE_H] + sorted(_clp_skin_new)
            # all_h_codes: B2.1 için dominated kodları da ekle (H318 "Baskın kapsamında" notu)
            _clp_all_skin = set(_clp_skin_new)
            for _pe in _clp_res.get('passed', []):
                if _pe.get('h_code', '') in _SKIN_EYE_H:
                    _clp_all_skin.add(_pe['h_code'])
            _exist_all = set(all_h_codes)
            all_h_codes = list(all_h_codes) + [h for h in sorted(_clp_all_skin) if h not in _exist_all]
            # H314 Danger getirir — signal word yeniden hesapla
            _clean_h = {h.split()[0] for h in h_codes if isinstance(h, str)}
            signal = 'Danger' if is_danger(_clean_h, _clp_res.get('passed', [])) else 'Warning'

        # ── 5. H314 → H318 birlikteliği (CLP §3.3.1.4 / SEA Tablo 3.3.1) ────────
        # Skin Corr. 1 (H314) varlığında Eye Dam. 1 (H318) sınıflandırma tablosuna
        # zorunlu eklenir. Etiket (h_codes): H318 gizlenir — SEA Madde 28 dominance.
        if 'H314' in set(h_codes):
            if 'H318' not in set(all_h_codes):
                all_h_codes = list(all_h_codes) + ['H318']
            if not any(e.get('h_code') == 'H318' for e in py_clp_passed):
                py_clp_passed = list(py_clp_passed) + [{
                    'h_code':      'H318',
                    'h_class':     'Eye Dam. 1',
                    'reason':      'H314 varlığında otomatik (CLP §3.3.1.4)',
                    'cutoff_used': '—',
                }]
            if 'H318' in set(h_codes):
                h_codes = [h for h in h_codes if h != 'H318']

        # ── 6. H304 — sadece sıvı/pasta formda geçerli ──────────────────────────
        # CLP §3.10.1: aspirasyon tehlikesi katı, toz, gaz ve aerosol formda uygulanmaz
        if form not in ('liquid', 'paste'):
            h_codes       = [h for h in h_codes       if h != 'H304']
            all_h_codes   = [h for h in all_h_codes   if h != 'H304']
            py_clp_passed = [p for p in py_clp_passed if p.get('h_code') != 'H304']

        # ── 7. Sağlık tehlikeleri (ATE) — classify_mixture_clp Acute Tox. atlar ─────
        # Tam ATE async DB fonksiyonunda yapılır; bu sync sonuç h_codes'ta eksikleri tamamlar.
        _ACUTE_TOX_H = {'H300','H301','H302','H310','H311','H312','H330','H331','H332'}
        if _be_ate_h:
            _be_ate_hcodes = [e['h_code'] for e in _be_ate_h]
            _ate_hset = {e['h_code'] for e in _be_ate_h}
            # h_codes (etiket/sinyal kelimesi): sunucu ATE sonucu kesin
            h_codes = [h for h in h_codes if h not in _ACUTE_TOX_H] + _be_ate_hcodes
            # all_h_codes (B2.1 tam tablo): frontend kodlarını SİLME — sunucu kodlarını EKLE
            # Sunucu ATEmix eşiği aşarsa (örn. H331 yok ama bileşen bireysel H331 taşıyor)
            # frontend kodları B2.1'de "Baskın tehlike sınıfı kapsamında" ile görünmeye devam eder
            _existing_h = set(all_h_codes)
            all_h_codes = list(all_h_codes) + [h for h in _be_ate_hcodes if h not in _existing_h]
            # Server ATE entry'lerini py_clp_passed'a yaz — önceki boş/yanlış entry'leri ez
            py_clp_passed = [e for e in py_clp_passed if e.get('h_code') not in _ate_hset]
            for _ate_e in _be_ate_h:
                py_clp_passed.append({
                    'h_code':      _ate_e['h_code'],
                    'h_class':     _ate_e['h_class'],
                    'reason':      _ate_e['reason'],
                    'cutoff_used': _ate_e['cutoff_used'],
                })

        # ── 8. Transport env_mark — ADR §2.2.9.1.10.5 / IMDG §2.10.3 ──────────────
        # ADR §2.2.9.1.10.5(a): karışım CLP'ye göre Aquatic Acute 1 (H400),
        # Aquatic Chronic 1 (H410) veya Aquatic Chronic 2 (H411) ise → deniz kirletici.
        # Kronik 3/4 (H412/H413) kapsam dışı. Ayrı Σ(C×M) hesabı gerekmez;
        # ecological_service.py zaten %25 M-faktörlü toplamsal formülü uyguluyor.
        if py_transport and not py_transport.get('not_regulated'):
            _eco_aq_h = (getattr(eco_result, 'aquatic', None) or {})
            _eco_aq_hcode = (_eco_aq_h.h_code if hasattr(_eco_aq_h, 'h_code') else '')
            _correct_env = _eco_aq_hcode in {'H400', 'H410', 'H411'}
            for _mode in ('road', 'sea', 'air'):
                if isinstance(py_transport.get(_mode), dict):
                    py_transport[_mode]['env_mark'] = _correct_env

        # ── eco_result fallback ───────────────────────────────────────────────────
        if eco_result is None:
            eco_result = {'sds_section_12': {}}

        # PPE — reconciliation sonrası final h_codes ile hesapla
        # ATE H kodları (H330/H331/H302 vb.) artık h_codes'ta → doğru KKD profili
        try:
            py_ppe = _ppe_calc([h for h in h_codes if h], lang=lang)
        except Exception:
            pass  # _ppe_calc tanımsızsa (try bloğu erken exception) fallback korunur

        # P kodlarını son h_codes + signal ile hesapla
        p_result = assign_p_codes(h_codes, signal, usage=usage)
        p_result['label'] = select_label_p_codes(p_result['p_codes'], 6, h_codes=h_codes)
        p_result['sds']   = classify_sds_p_codes(p_result['p_codes'], usage=usage)

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
            # Önce tüm alanları kopyala — bilinmeyen alanlar downstream servislere geçer,
            # elle listeleme hatası yüzünden veri düşmez.
            result = dict(c)

            # ── Metin normalizasyonu ──────────────────────────────────────────
            name    = _safe(c.get('name', ''))
            name_tr = _safe(c.get('name_tr', ''))
            # "%100'e tamamla" bileşeni — PDF'de standart metin
            if name and 'mevzuata' in name.lower():
                name = 'Mevzuata göre sınıflandırılmamıştır'
            if name_tr and 'mevzuata' in name_tr.lower():
                name_tr = 'Mevzuata göre sınıflandırılmamıştır'
            result['name']    = name
            result['name_tr'] = name_tr

            # ── CAS no normalizasyonu ─────────────────────────────────────────
            result['cas_no'] = c.get('cas', c.get('cas_no', ''))

            # ── Konsantrasyon normalizasyonu ──────────────────────────────────
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
            result['concentration'] = conc   # standart alan
            result['conc']          = conc   # eski servisler için alias
            result['conc_str']      = conc_str
            result['conc_min']      = conc_min
            result['conc_max']      = conc_max
            # PCN bandı — hesaplanan alan, orijinalde bulunmaz
            result['conc_pcn_band'] = _get_pcn_band(
                conc_min=float(conc_min) if conc_min is not None else None,
                conc_max=float(conc_max) if conc_max is not None else None,
                conc_exact=conc if conc and not (conc_min or conc_max) else None,
            )

            # ── Tehlike listesi normalizasyonu ────────────────────────────────
            result['hazards'] = [
                {k: v for k, v in {
                    'h_class':   h.get('h_class', ''),
                    'h_code':    h.get('h_code', ''),
                    'note_flag': h.get('note_flag'),
                    'note':      h.get('note'),
                    'repro_sub': h.get('repro_sub'),
                }.items() if v is not None and v != ''}
                for h in c.get('hazards', [])
            ]

            # ── Tip dönüşümleri ───────────────────────────────────────────────
            result['annex_vi']        = c.get('annex_vi', False)
            result['source_priority'] = c.get('source_priority', 4)
            result['ate_unknown']     = bool(c.get('ate_unknown', False))
            result['ate_dict']        = c.get('ate') or {}   # frontend 'ate' → 'ate_dict'
            result['comp_type']       = c.get('comp_type', 'normal')

            return result
        mapped_comps = [_map_comp(c) for c in components]

        # ── Bileşen tehlike kodlarını doğrula (Bölüm 3 kalite kontrolü) ──────────
        # SEA Ek-6'da bulunan maddeler için frontend'den gelen hatalı/fazla tehlike
        # kodlarını yetkili DB verisiyle değiştir.
        # Gerekçe: Kullanıcı manuel ekleme, tarayıcı önbelleği veya CAS sorgulama
        # hatası nedeniyle yanlış H kodları ekleyebilir.
        # Yalnızca sea_ek6=True maddeler için geçerlidir; bilinmeyen maddeler
        # (custom / ECHA-only) için frontend verisi korunur.
        try:
            from app.services.substance_lookup import lookup_substance as _lu_check
            for _mc in mapped_comps:
                _cas = _mc.get('cas_no', '').strip()
                if not _cas:
                    continue
                _sub = _lu_check(_cas, form=_prod_form_for_refresh)
                if _sub and _sub.get('sea_ek6', False):
                    # SEA Ek-6 yetkili veri — frontend'den gelen kodları geçersiz kıl
                    _mc['hazards'] = _sub.get('hazards', [])
                if _sub and _sub.get('suppl_hazards'):
                    _mc['suppl_hazards'] = _sub['suppl_hazards']
        except Exception:
            pass  # Hata durumunda frontend verisi korunur

        # ── h_codes + all_h_codes temizle — eski/geçersiz fiziksel H kodlarını çıkar ───
        # Senaryo 3 "manuel" fiziksel tehlike kodları yalnızca physical_engine veya
        # test_data üretebilir. py_clp_passed'da yoklarsa h_codes (B2.2 etiketi) ve
        # all_h_codes (B2.1 sınıflandırma tablosu) listelerinden silinir.
        # Temizlenmezse: eski JS motor kalıntısı H241 → GHS01 (patlayıcı) üretir ve
        # ghs_pictogram dominance kuralı GHS02 (alev) piktogramını siler (B2.2 BULGU 2).
        _MANUAL_PHYS_H = {
            'H240','H241','H242',           # Organik peroksit / öz-reaktif
            'H250','H251','H252',           # Pirofor / kendiliğinden ısınan
            'H260','H261',                  # Su-reaktif
            'H270','H271','H272',           # Oksitleyici gaz/katı/sıvı
            'H290',                         # Metal aşındırıcı
        }
        # Geçerli fiziksel H kodları: Python motorundan VEYA Senaryo 3 test_data'dan gelenler
        # PDF uç noktası _phys_calc'ı test_data olmadan çağırdığından Senaryo 3 kodları
        # py_clp_passed'a girmiyor; ancak calculate API'si onları physical.results'ta saklar.
        # Eski JS motor kalıntıları ise physical.results'ta yer almaz — bu farkı kullanıyoruz.
        _engine_h_set = {e['h_code'] for e in py_clp_passed}
        _stored_phys_h = {
            (r.get('h') or r.get('h_code') or '').replace('*','').strip()[:4]
            for r in (data.get('physical') or {}).get('results', [])
            if r.get('h') or r.get('h_code')
        }
        _valid_phys_h = _engine_h_set | _stored_phys_h
        h_codes = [
            h for h in h_codes
            if h not in _MANUAL_PHYS_H or h in _valid_phys_h
        ]
        all_h_codes = [
            h for h in all_h_codes
            if h not in _MANUAL_PHYS_H or h in _valid_phys_h
        ]
        # h_codes temizlendikten sonra sinyal kelimesini yeniden hesapla
        # (ör. H241 kalkınca Danger devam edip etmediğini doğrula)
        _clean_after_filter = {h.split()[0] for h in h_codes if isinstance(h, str)}
        signal = 'Danger' if is_danger(_clean_after_filter, _clp_res.get('passed', [])) else ('Warning' if _clean_after_filter else '')
        # P kodlarını temizlenmiş h_codes ile yeniden hesapla
        # (filtreden önce H260/H261 vb. varsa P231+P232 gibi yanlış P kodları atanmış olabilir)
        p_result = assign_p_codes(h_codes, signal, usage=usage)
        p_result['label'] = select_label_p_codes(p_result['p_codes'], 6, h_codes=h_codes)
        p_result['sds']   = classify_sds_p_codes(p_result['p_codes'], usage=usage)

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
                        'h_class':       h.get('h_class',''),
                        'h_code':        h.get('h_code',''),
                        'reason':        _safe(h.get('reason','')),
                        'cutoff_used':   _safe(h.get('cutoff_used','')),
                        'cutoff_source': h.get('cutoff_source'),
                        'cutoff_value':  h.get('cutoff_value'),
                        'note_flag':     h.get('note_flag'),
                        'note':          h.get('note'),
                        'repro_sub':     h.get('repro_sub'),
                    }.items() if v is not None and v != ''}
                    for h in py_clp_passed
                ],
                'warnings': _clp_res.get('warnings', []) + _phys_res.get('warnings', []),
            },
            'euh':          euh_result,
            'p_codes':      p_result,
            'components':   mapped_comps,
            'disclosure_map': disc_map,
            'phys_props':   _parsed_phys,
            'phys_methods': _phys_methods,   # ölçülen/hesaplanmış etiket (KKDİK Ek-2 §9)
            'eco':          eco_result,
            # Python transport_engine sonucunu kullan (ISO 27001 uyumu).
            'transport':    _map_transport(py_transport),
            'revision': {
                'date':    rev_date,
                'no':      revision_in.get('no', '1'),
                'version': revision_in.get('version', '1.0'),
                'notes':   revision_in.get('notes', 'İlk yayın'),
            },
            'ate_mix_details': {**data.get('ate_mix_details', {}), **_be_ate_details},
            'h314_neutralization_removed': bool(data.get('h314_neutralization_removed', False)),
            'clp_note_overrides': data.get('clp_note_overrides', {}),
            # Python PPE motoru sonucu (ISO 27001 uyumu — sunucu tarafı)
            'ppe': py_ppe,
        }

        # sds_data['clp']['pictograms'] h_codes'tan türet — V019 için gerekli
        # (eco_engine GHS09'u PDF'e ekler ama clp dict'ine yazmaz → false-positive)
        try:
            from app.services.ghs_pictogram import get_ghs_codes as _get_ghs
            sds_data['clp']['pictograms'] = _get_ghs(h_codes)
        except Exception:
            pass

        # Validator devre dışı
        _val_issues: list = []

        pdf_bytes = generate_sds_pdf(sds_data, lang=lang)

        _tr_map = str.maketrans('ıİğĞüÜşŞçÇöÖ', 'iIgGuUsScCoO')
        _name_ascii = product.get('name', 'SDS').translate(_tr_map)
        safe = ''.join(x if (x.isalnum() and x.isascii()) or x in '-_' else '_'
                       for x in _name_ascii)[:30]
        rev_no = revision_in.get('no','1')

        # Validator sonuçlarını response header'a ekle (frontend toast için)
        _val_errors   = sum(1 for i in _val_issues if i['level'] == 'error')
        _val_warnings = sum(1 for i in _val_issues if i['level'] == 'warning')
        _val_infos    = sum(1 for i in _val_issues if i['level'] == 'info')
        _val_summary  = json.dumps(
            {'error': _val_errors, 'warning': _val_warnings, 'info': _val_infos},
        )
        # İlk 5 issue'yu header'a sığdır — ensure_ascii=True zorunlu (HTTP/1.1 latin-1)
        _val_top = json.dumps(
            _val_issues[:5], separators=(',', ':')
        )

        # sds_data'nın JSON-serileştirilebilir temiz kopyası (review için)
        import base64 as _b64
        def _jsonable(obj, depth=0):
            if depth > 6: return str(obj)
            if obj is None or isinstance(obj, (bool, int, float, str)): return obj
            if isinstance(obj, dict):
                return {str(k): _jsonable(v, depth+1) for k, v in obj.items()}
            if isinstance(obj, (list, tuple)):
                return [_jsonable(i, depth+1) for i in obj]
            return str(obj)

        _sds_for_review = _jsonable(sds_data)
        _filename = f'{safe}_GBF_{lang}_Rev{rev_no}.pdf'

        try:
            from app.services.sds_xml_service import generate_sds_xml as _gen_xml
            _sds_xml = _gen_xml(_sds_for_review)
        except Exception:
            _sds_xml = None

        from fastapi.responses import JSONResponse as _JR
        return _JR({
            'pdf':      _b64.b64encode(pdf_bytes).decode(),
            'filename': _filename,
            'sds_data': _sds_for_review,
            'sds_xml':  _sds_xml,
            'validation': {
                'error':   _val_errors,
                'warning': _val_warnings,
                'info':    _val_infos,
                'issues':  _val_issues[:5],
            },
        })

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
    computed = 'Danger' if is_danger(clean) else 'Warning'
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
            if echa and (echa.get('h_codes') or echa.get('name')):
                cache_src  = echa.get('_cache_source', 'echa_cl')
                is_pubchem = cache_src == 'pubchem'
                try:
                    from app.services.substance_lookup import (
                        save_echa_cl_substance, save_pubchem_substance,
                        save_custom_substance, _load_custom,
                    )
                    if is_pubchem:
                        save_pubchem_substance(cas, echa)
                    else:
                        save_echa_cl_substance(cas, echa)
                    # substances_custom.json'a da yaz — git'te commit'li, Render'da kalıcı.
                    # Manuel kurasyon varsa üzerine yazma.
                    if cas not in _load_custom():
                        _h_codes = echa.get('h_codes', [])
                        _h_cls   = echa.get('hazard_classes', [])
                        save_custom_substance(cas, {
                            'name':       echa.get('name', ''),
                            'ec_no':      echa.get('ec_no', '') or get_ec_no(cas),
                            'signal':     echa.get('signal', ''),
                            'pictograms': echa.get('pictograms', []),
                            'hazards': [
                                {'h_class': c, 'h_code': h}
                                for c, h in zip(_h_cls, _h_codes)
                            ],
                            'm_factors':  echa.get('m_factors', {}),
                            'index_no':   '',
                            'atp':        'pubchem-auto',
                        })
                except Exception:
                    pass
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
        _reach = get_reg_no(cas)
        if not _reach:
            try:
                from app.services.reach_cache import fetch_reach_no_async
                _reach = await fetch_reach_no_async(cas)
            except Exception:
                pass
        return {
            "found"     : True,
            "cas"       : cas,
            "name"      : result.get("name", ""),
            "name_tr"   : result.get("name_tr", ""),   # Türkçe SDS Bölüm 3 için
            "ec_no"     : result.get("ec_no", "") or get_ec_no(cas),
            "reach_no"  : _reach,
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
    if not reg:
        try:
            from app.services.reach_cache import fetch_reach_no_async
            reg = await fetch_reach_no_async(cas)
        except Exception:
            pass
    if ec or reg:
        return {"found": True, "cas": cas, "name": "", "ec_no": ec,
                "reach_no": reg, "annex_vi": False, "hazards": [], "oel": oel}

    # Geçerli CAS formatı (##-##-#) → bilinmeyen madde olarak döndür; kullanıcı elle sınıflandırabilir
    import re as _re
    if _re.match(r'^\d{2,7}-\d{2}-\d$', cas.strip()):
        return {"found": True, "cas": cas, "name": "", "ec_no": "",
                "reach_no": None, "annex_vi": False, "hazards": [], "oel": oel,
                "source": "Bilinmeyen madde — sınıflandırma manuel girilmeli"}

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
    from app.services.stot_engine import calculate as calculate_stot_re
    from app.services.ecological_service import calculate_ecological
    import dataclasses

    components  = body.get("components", [])
    lang        = body.get("lang", "TR")
    mixture_ph  = body.get("mixture_ph", None)   # Karışım pH değeri (opsiyonel)
    mixture_form = body.get("form") or "liquid"

    try:
        # 1. Ana CLP (cut-off tablosu) — pH uç değer varsa doğrudan H314+H318 atanır
        result = classify_mixture_clp(components, mixture_ph=mixture_ph, mixture_form=mixture_form)

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
        signal = "Danger" if is_danger(set(result["h_codes"]), result.get("passed", [])) else (
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
    signal = "Danger" if is_danger(set(h_codes)) else ("Warning" if h_codes else "")
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
        result["sds"]      = classify_sds_p_codes(result["p_codes"], usage=usage)
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
    from app.services.physical_engine import calculate as phys_calculate
    components  = body.get("components", [])
    form        = body.get("form", "liquid")
    flash_point = body.get("flash_point")
    show_extra  = body.get("show_extra", False)
    try:
        result = phys_calculate(components, form=form, user_fp=flash_point, test_data=None)
        if not show_extra:
            result.pop('extra', None)
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
    from app.services.clp_service         import classify_mixture_clp, is_danger as _is_danger
    from app.services.physical_engine     import calculate as phys_calculate
    from app.services.stot_engine         import calculate as stot_calculate
    from app.services.euh_service         import check_euh as euh_calculate
    from app.services.ecological_service  import calculate_aquatic as eco_calculate_aquatic
    from app.services.transport_engine    import classify as transport_classify
    from app.services.ppe_engine          import select as ppe_select
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
        clp_result = classify_mixture_clp(comps, mixture_ph=mixture_ph, mixture_form=form)

        # ── 3. STOT RE ────────────────────────────────────────────────────────
        stot_result = stot_calculate(comps)

        # ── 4. EUH kodları ────────────────────────────────────────────────────
        # suppl_hazards injection: ATP22 / substance_db → comps (EUH071 vb.)
        try:
            from app.services.substance_lookup import lookup_substance as _lu_euh
            for _c in comps:
                _cas = (_c.get('cas') or _c.get('cas_no') or '').strip()
                if _cas and not _c.get('suppl_hazards'):
                    _sub = _lu_euh(_cas)
                    if _sub and _sub.get('suppl_hazards'):
                        _c['suppl_hazards'] = _sub['suppl_hazards']
        except Exception:
            pass
        euh_result = euh_calculate(comps)

        # ── 5. Ekoloji ────────────────────────────────────────────────────────
        _aq = eco_calculate_aquatic(comps)
        eco_result = {'h_codes': [_aq.h_code] if _aq else []}

        # ── 5b. ATE sağlık tehlikeleri — classify_mixture_clp Acute Tox. atlar ─
        from app.services.clp_service import calculate_ate_health_h_codes as _calc_ate
        try:
            _ate_h_list, _ate_b11 = _calc_ate(comps, form=form)
        except Exception:
            _ate_h_list, _ate_b11 = [], {}

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

        # ── KKD (Bölüm 8) ────────────────────────────────────────────────────
        # all_h_list henüz hesaplanmamış, transport sonrasında yapılıyor;
        # şimdi mevcut h kodlarıyla PPE seç — ekoloji H'ları sonra eklenir.
        # PPE fonksiyonu küçük set farkına toleranslı, eksik H=false negative.
        _ppe_h_now = (
            list(clp_result.get('h_codes', []))
            + [r.get('h') or r.get('h_code') or '' for r in phys_result.get('results', [])]
            + stot_result.get('h_codes', [])
            + eco_result.get('h_codes', [])
        )
        ppe_result = ppe_select([h for h in _ppe_h_now if h], lang=lang)

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

        # ATE sağlık tehlikeleri (Acute Tox.) — baskınlık uygulanmış
        _ACUTE_TOX_H_CALC = {'H300','H301','H302','H310','H311','H312','H330','H331','H332'}
        all_h = {h for h in all_h if h not in _ACUTE_TOX_H_CALC}
        for _ae in _ate_h_list:
            all_h.add(_ae['h_code'])

        all_h_list = sorted(all_h)

        # ── Sinyal kelimesi ───────────────────────────────────────────────────
        signal = 'Danger' if _is_danger(all_h, clp_result.get('passed', [])) else ('Warning' if all_h else '')

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
                    'h_code':        hc,
                    'h_class':       fixed or p.get('h_class',''),
                    'reason':        p.get('reason',''),
                    'cutoff_used':   p.get('cutoff_used',''),
                    'cutoff_source': p.get('cutoff_source','GCL'),
                    'cutoff_value':  p.get('cutoff_value'),
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

        # ── ATE sağlık tehlikeleri — clp_passed'a ekle ───────────────────────
        _ate_hset_calc = {e['h_code'] for e in _ate_h_list}
        clp_passed = [e for e in clp_passed if e.get('h_code') not in _ate_hset_calc]
        for _ae in _ate_h_list:
            seen.add(_ae['h_code'])
            clp_passed.append({
                'h_code':     _ae['h_code'],
                'h_class':    _ae['h_class'],
                'reason':     _ae['reason'],
                'cutoff_used':_ae['cutoff_used'],
            })

        # ── H314 → H318 birlikteliği (CLP §3.3.1.4) ──────────────────────────
        if 'H314' in all_h:
            all_h.add('H318')
            all_h_list = sorted(all_h)
            if not any(p.get('h_code') == 'H318' for p in clp_passed):
                clp_passed.append({
                    'h_code':      'H318',
                    'h_class':     'Eye Dam. 1',
                    'reason':      'H314 varlığında otomatik (CLP §3.3.1.4)',
                    'cutoff_used': '—',
                })

        # ── P kodları ─────────────────────────────────────────────────────────
        p_result = assign_p_codes(all_h_list, signal, usage=usage)
        p_result['label'] = select_label_p_codes(p_result['p_codes'], 6, h_codes=all_h_list)
        p_result['sds']   = classify_sds_p_codes(p_result['p_codes'], usage=usage)

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
            'ppe':        ppe_result,
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


# ---------------------------------------------------------------------------
# AI Chat — Anthropic API ile veri doğrulama ve SDS uyumluluk asistanı
# ---------------------------------------------------------------------------

@app.post("/api/v1/ai/chat")
async def ai_chat(body: dict = Body(...)):
    """
    İki mod:
      mode=data   — SEA Ek-6 / Annex VI verisi doğrulama
      mode=sds    — Hazırlanmış SDS metninin yönetmelik uygunluğu kontrolü
    Gelen alanlar:
      message   : str   (kullanıcı sorusu)
      mode      : str   "data" | "sds"  (varsayılan: "data")
      cas       : str   (isteğe bağlı, veri modunda bağlam zenginleştirme)
      sds_text  : str   (isteğe bağlı, sds modunda yüklenen SDS içeriği)
    """
    import os
    try:
        import anthropic as _anthropic
    except ImportError:
        raise HTTPException(status_code=500, detail="anthropic paketi kurulu değil")

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY tanımlı değil")

    message  = (body.get("message") or "").strip()
    mode     = (body.get("mode") or "data").lower()
    cas      = (body.get("cas") or "").strip()
    sds_text = (body.get("sds_text") or "").strip()

    if not message:
        raise HTTPException(status_code=400, detail="message alanı boş olamaz")

    # ── Sistem mesajı ────────────────────────────────────────────────────────
    _kural = (
        "\n\nKESİN KURAL: Yanıtlarında YALNIZCA sana sağlanan veriler ve aşağıdaki resmi "
        "mevzuatı kullan:\n"
        "  - SEA Ek-6 / KKDİK Ek-6 (Türkiye harmonize sınıflandırma listesi)\n"
        "  - CLP Annex VI (ECHA ATP22, AB harmonize sınıflandırma)\n"
        "  - KKDİK Yönetmeliği (REACH TR karşılığı)\n"
        "  - SEA Yönetmeliği (CLP TR karşılığı)\n"
        "  - ADR 2025 (tehlikeli madde taşımacılığı)\n"
        "Eğer sana verilen veride veya yukarıdaki mevzuatta bilgi yoksa, "
        "'Bu madde/konu için veritabanında veya ilgili yönetmelikte bilgi bulunamadı.' "
        "de. Genel kimya bilgine veya tahmine dayanma. "
        "Herhangi bir araç (tool) boş veya bulunamadı sonucu döndürürse, "
        "kendi bilginden H/EUH/P kodu veya sınıflandırma üretme — "
        "'Veritabanında bulunamadı.' de.\n\n"
        "H/EUH/P KODU METİNLERİ: Sana 'Resmi Türkçe tehlike ifadeleri' başlığıyla "
        "kod → metin eşleştirmesi verildiğinde, bu metinleri AYNEN kullan. "
        "Hiçbir şekilde parafraz yapma, çevirme veya değiştirme. "
        "Örneğin H225 için 'Kolay alevlenir sıvı ve buhar.' yazıyorsa yanıtta da "
        "tam bu metin geçmeli."
    )
    if mode == "sds":
        system_prompt = (
            "Sen bir Türk kimyasal güvenlik veri formu (GBF/SDS) uyumluluk denetçisisin. "
            "Sana sunulan SDS metnini ve madde verilerini, yalnızca KKDİK ve SEA yönetmelikleri "
            "ile eklerindeki (Ek-1, Ek-2, Ek-6) zorunlu gerekliliklere göre değerlendirirsin. "
            "Her bulguyu hangi yönetmelik maddesine aykırı olduğunu belirterek Türkçe raporlarsın. "
            "Yanıtların net, madde madde ve eylem odaklı olsun."
        ) + _kural
    else:
        system_prompt = (
            "Sen SDSPass sisteminin resmi veri doğrulama asistanısın. "
            "Sana madde kaydı (JSON) veya soru geldiğinde, yalnızca o kayıttaki verilerden "
            "ve aşağıdaki resmi mevzuattan hareketle yanıt verirsin. "
            "Her yanıtta bilginin kaynağını mutlaka belirt: "
            "'SEA Ek-6 kaydına göre…' veya 'CLP Annex VI kaydına göre…' gibi."
        ) + _kural

    # ── Kullanıcı içeriği ────────────────────────────────────────────────────
    from app.services.knowledge_service import build_context_blocks

    user_parts: list[dict] = []

    # sds-knowledge/ dosyalarından ilgili belgeler (sorguya göre seçilir)
    kb_blocks = build_context_blocks(message)
    user_parts.extend(kb_blocks)

    if sds_text and mode == "sds":
        user_parts.append({
            "type": "text",
            "text": f"İncelenecek SDS metni:\n---\n{sds_text[:8000]}\n---\n\n"
        })

    user_parts.append({"type": "text", "text": message})

    kb_count = len(kb_blocks)

    # ── Tool tanımı (sadece data modunda) ────────────────────────────────────
    _lookup_tool = {
        "name": "lookup_substance",
        "description": (
            "Madde adı veya CAS numarasıyla SEA Ek-6 / KKDİK harmonize "
            "sınıflandırma veritabanından resmi H/EUH kodu bilgisi çeker. "
            "Kullanıcı herhangi bir kimyasal madde sorduğunda bu aracı çağır."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Madde adı (örn: 'aseton') veya CAS numarası (örn: '67-64-1')"
                }
            },
            "required": ["query"]
        }
    }

    # ── API çağrısı ──────────────────────────────────────────────────────────
    import re as _re
    client   = _anthropic.Anthropic(api_key=api_key)
    _msgs    = [{"role": "user", "content": user_parts}]
    _official_table = ""

    _create_kw: dict = dict(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system=system_prompt,
        messages=_msgs,
    )
    if mode != "sds":
        _create_kw["tools"] = [_lookup_tool]

    resp = client.messages.create(**_create_kw)

    # ── Tool Use döngüsü ─────────────────────────────────────────────────────
    while resp.stop_reason == "tool_use":
        from app.services.substance_lookup import lookup_substance, search_substances
        from app.services.codes_i18n import H_STMTS, EUH_STMTS

        _tool_results = []
        for _blk in resp.content:
            if getattr(_blk, "type", None) != "tool_use":
                continue
            _query = _blk.input.get("query", "")

            # CAS regex veya isim araması
            _cm = _re.search(r'\b\d{2,7}-\d{2}-\d\b', _query)
            _rcas = _cm.group() if _cm else None
            if not _rcas:
                _sr = search_substances(_query, limit=1)
                if not _sr:
                    for _w in _query.split():
                        if len(_w) >= 4:
                            _sr = search_substances(_w, limit=1)
                            if _sr:
                                break
                if _sr:
                    _rcas = _sr[0].get("cas")

            _entry = lookup_substance(_rcas) if _rcas else None
            if _entry:
                _hmap  = H_STMTS.get("TR", {})
                _emap  = EUH_STMTS.get("TR", {})
                _seen2: set = set()
                _rows2: list[str] = []
                _hres: list = []
                _eres: list = []

                for _c in _entry.get("hazards", []):
                    _cd = _c.get("h_code", "")
                    if _cd and _cd not in _seen2:
                        _seen2.add(_cd)
                        _tx = _hmap.get(_cd, "")
                        _hres.append({"code": _cd, "class": _c.get("h_class", ""), "text_tr": _tx})
                        if _tx:
                            _rows2.append(f"| **{_cd}** | {_tx} |")

                for _cd in _entry.get("euh_codes", []):
                    if _cd not in _seen2:
                        _seen2.add(_cd)
                        _tx = _emap.get(_cd, "")
                        _eres.append({"code": _cd, "text_tr": _tx})
                        if _tx:
                            _rows2.append(f"| **{_cd}** | {_tx} |")

                _rname = (_entry.get("name_tr") or _entry.get("name") or _rcas)
                _rname = _rname.split(";")[0].strip().capitalize()

                if _rows2:
                    _official_table = (
                        f"**{_rname} (CAS {_rcas})** — SEA Ek-6 / KKDİK Ek-6\n\n"
                        f"| H/EUH Kodu | Resmi Türkçe Tehlike İfadesi |\n"
                        f"|------------|------------------------------|\n"
                        + "\n".join(_rows2)
                        + "\n\n*Kaynak: SEA Ek-6 harmonize sınıflandırma listesi*\n\n"
                    )

                _tdata: dict = {
                    "cas": _rcas, "name": _rname,
                    "source": _entry.get("source", "SEA Ek-6 (TR)"),
                    "h_codes": _hres, "euh_codes": _eres,
                    "m_factors": _entry.get("m_factors", {}),
                    "notes": _entry.get("notes", []),
                }
            else:
                _tdata = {"error": f"'{_query}' veritabanında bulunamadı."}

            _tool_results.append({
                "type": "tool_result",
                "tool_use_id": _blk.id,
                "content": json.dumps(_tdata, ensure_ascii=False),
            })

        _msgs.append({"role": "assistant", "content": resp.content})
        _msgs.append({"role": "user",      "content": _tool_results})
        resp = client.messages.create(**{**_create_kw, "messages": _msgs})

    reply = "".join(
        b.text for b in resp.content if getattr(b, "type", None) == "text"
    )
    if _official_table:
        reply = _official_table + reply
    return {
        "reply": reply,
        "mode":  mode,
        "model": resp.model,
        "docs_used":     kb_count,
        "input_tokens":  resp.usage.input_tokens,
        "output_tokens": resp.usage.output_tokens,
    }


# ─── ETIKET ENDPOINT ──────────────────────────────────────────────────────────

@app.post("/api/v1/label/pdf", response_class=Response)
async def generate_label(data: dict = Body(...)):
    """
    CLP uyumlu etiket PDF üret.

    Beklenen veri:
      product    : {name, form, usage}
      components : [{name, cas, concMin, concMax, hCodes}]
      clp        : {h_codes, signal_word, p_codes}
      supplier   : {name, address, phone}
      volume_l   : float  — ambalaj hacmi (litre)
      lang       : 'TR' | 'EN'
      ufi        : str (isteğe bağlı)
    """
    from app.services.label_service import generate_label_pdf
    try:
        pdf_bytes = generate_label_pdf(data)
        product_name = data.get('product', {}).get('name', 'etiket')
        safe_name = ''.join(c for c in product_name if c.isalnum() or c in (' ', '-', '_'))[:40]
        filename = f"{safe_name}_etiket.pdf"
        return Response(
            content=pdf_bytes,
            media_type='application/pdf',
            headers={'Content-Disposition': f'attachment; filename="{filename}"'},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Etiket üretim hatası: {e}')


# ─────────────────────────────────────────────────────────────────────────────
# Tedarikçi SDS Parse — PDF'den bileşen verisi çıkar
# ─────────────────────────────────────────────────────────────────────────────
@app.post("/api/v1/sds/parse-supplier")
async def parse_supplier_sds(request: Request):
    """
    Tedarikçi SDS PDF'inden bileşen verisi çıkar.
    Multipart form: file=<pdf>
    Döner: {components:[{name,cas,ec_no,index_no,concMin,concMax,hCodes}], warnings:[]}
    """
    import io, json as _json

    try:
        form = await request.form()
        file = form.get("file")
        if not file:
            raise HTTPException(status_code=400, detail="PDF dosyası gerekli (file alanı)")

        pdf_bytes = await file.read()

        # 1. pdfplumber ile metin çıkar
        try:
            import pdfplumber
            pages = []
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                for page in pdf.pages:
                    t = page.extract_text(x_tolerance=2, y_tolerance=2)
                    if t:
                        pages.append(t)
            sds_text = "\n\n--- SAYFA SONU ---\n\n".join(pages)
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"PDF metin çıkarma hatası: {e}")

        if not sds_text.strip():
            raise HTTPException(status_code=422, detail="PDF'den metin çıkarılamadı (taranmış görsel olabilir)")

        # 2. Claude ile parse
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY tanımlı değil")

        import anthropic as _anthropic
        client = _anthropic.Anthropic(api_key=api_key)

        schema_example = _json.dumps({
            "supplier": {
                "company": "Firma Adı",
                "product_name": "Ürün Adı",
                "rev_no": "3",
                "rev_date": "2024-05-01"
            },
            "components": [
                {
                    "name": "Madde adı",
                    "cas": "7647-01-0",
                    "ec_no": "231-595-7",
                    "index_no": "017-002-00-2",
                    "concMin": 15,
                    "concMax": 20,
                    "hCodes": ["H314", "H335"]
                }
            ]
        }, ensure_ascii=False)

        prompt = f"""Aşağıdaki SDS (Güvenlik Bilgi Formu) metninden bilgileri çıkar.

ÇIKTI KURALLARI:
- Sadece JSON objesi döndür, başka hiçbir şey yazma
- Bu şemayı kullan: {schema_example}
- supplier.company: Bölüm 1'deki üretici/tedarikçi firma adı (yoksa null)
- supplier.product_name: Bölüm 1'deki ürün/karışım adı (yoksa null)
- supplier.rev_no: Revizyon numarası (yoksa null)
- supplier.rev_date: Revizyon tarihi YYYY-MM-DD formatında (yoksa null)
- CAS No formatı: xxx-xx-x (belgede yoksa null)
- EC No formatı: xxx-xxx-x (belgede yoksa null)
- Index No / KKDIK No: xxx-xxx-xx-x (belgede yoksa null)
- concMin / concMax: sayısal yüzde değeri (örn. 15.0), belgede tek değer varsa ikisine de yaz, yoksa null
- hCodes: belgede bu bileşen için listelenen H kodları (örn. ["H314","H335"])
- Belgede yazan değerleri birebir al, tahmin etme

SDS METNİ:
{sds_text[:12000]}

Sadece JSON:"""

        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            temperature=0,
            messages=[{"role": "user", "content": prompt}]
        )

        raw = resp.content[0].text.strip()
        # JSON bloğunu temizle
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip().rstrip("```").strip()

        try:
            parsed = _json.loads(raw)
        except Exception:
            raise HTTPException(status_code=422, detail=f"AI parse hatası — ham çıktı: {raw[:300]}")

        # Eski format (liste) veya yeni format (obje) destekle
        if isinstance(parsed, list):
            components = parsed
            supplier = {}
        elif isinstance(parsed, dict):
            components = parsed.get("components") or []
            supplier = parsed.get("supplier") or {}
        else:
            raise HTTPException(status_code=422, detail="AI geçersiz format döndürdü")

        # 3. CAS doğrulama + H kodu Ek-6/Annex VI karşılaştırması
        from app.services.substance_lookup import lookup_substance
        warnings = []
        validated = []
        for comp in components:
            cas = (comp.get("cas") or "").strip()
            pdf_hcodes = [h.strip().upper() for h in (comp.get("hCodes") or []) if h]
            comp["hCodes"] = pdf_hcodes

            if not cas:
                warnings.append(f"{comp.get('name','?')}: CAS numarası yok — H kodları doğrulanamadı, PDF değerleri kullanıldı")
            if cas:
                sub = lookup_substance(cas)
                if not sub:
                    warnings.append(f"{comp.get('name','?')} (CAS {cas}): veritabanında bulunamadı — H kodları doğrulanamadı, PDF değerleri kullanıldı")
                else:
                    # EC no eksikse doldur
                    if not comp.get("ec_no") and sub.get("ec_no"):
                        comp["ec_no"] = sub["ec_no"]
                    # H kodlarını Ek-6/Annex VI ile karşılaştır
                    db_hcodes = [h.get("h_code","").upper() for h in (sub.get("hazards") or []) if h.get("h_code")]
                    if db_hcodes:
                        pdf_set = set(pdf_hcodes)
                        db_set  = set(db_hcodes)
                        if pdf_set != db_set:
                            added   = db_set - pdf_set
                            removed = pdf_set - db_set
                            parts = []
                            if added:   parts.append(f"eklendi: {', '.join(sorted(added))}")
                            if removed: parts.append(f"kaldırıldı: {', '.join(sorted(removed))}")
                            warnings.append(
                                f"⚠️ {comp.get('name','?')} (CAS {cas}): PDF'de {'+'.join(sorted(pdf_set)) or '—'} "
                                f"→ SEA Ek-6/Annex VI: {'+'.join(sorted(db_set))} ({', '.join(parts)}) — güncel değer kullanıldı"
                            )
                        else:
                            warnings.append(
                                f"✅ {comp.get('name','?')} (CAS {cas}): H kodları tam uyuşuyor — {'+'.join(sorted(db_set))}"
                            )
                        comp["hCodes"] = db_hcodes  # her zaman güncel DB değerini kullan

            validated.append(comp)

        return {"components": validated, "warnings": warnings, "supplier": supplier}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
