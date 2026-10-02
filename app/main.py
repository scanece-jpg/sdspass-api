"""
HazardDesk PDF API — Minimal Deploy
DB gerektirmez, sadece PDF üretimi + madde lookup
"""

from fastapi import FastAPI, Body, Response, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
import asyncio
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


@app.on_event("startup")
async def _startup_tasks():
    """Sunucu başlarken arka plan hazırlık işleri."""
    import asyncio as _aio
    from app.services import data_store, substance_lookup, cameo_service
    await _aio.to_thread(data_store.sync_down)
    # İndirilen dosyalar import sırasında belleğe alınmış önbelleklerin üzerine yazıldı → yeniden yükle
    # _load_custom kilitsiz çağrılmalı: save_custom_substance aynı (reentrant olmayan) kilidi tutarken çağırıyor
    substance_lookup._CUSTOM_DB = None
    substance_lookup._load_custom()
    cameo_service._disk_cache = cameo_service._load_disk_cache()
    from app.services import echa_service
    echa_service._archive_mem = None

    from app.services.transport_adr_service import init_cas_map
    init_cas_map()  # substance_db × adr_data isim eşleşmesi → bellek-içi CAS→UN haritası


@app.on_event("shutdown")
async def _shutdown_tasks():
    import asyncio as _aio
    from app.services import data_store
    await _aio.to_thread(data_store.flush)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "HazardDesk PDF API"}


# ─── SDS DENETIM ENDPOINT ─────────────────────────────────────────────────────
from app.services.review_endpoint import router as review_router
app.include_router(review_router)

# ─── SDS ASİSTAN ENDPOINT ─────────────────────────────────────────────────────
from app.services.assistant_endpoint import router as assistant_router
app.include_router(assistant_router)


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

        # ── Tek sınıflandırma hattı — sağ panelle (/sds/calculate) aynı fonksiyon ──
        # Ön yüz, panelin kullandığı hesap girdisini (calc_input) aynen gönderir; böylece
        # panel ile PDF birebir aynı girdiden, aynı kurallarla hesaplanır.
        # calc_input yoksa (eski istemciler) girdi phys_props'tan türetilir.
        from app.services import sds_pipeline as _pipe
        from app.services.phys_props_parser import (
            parse_all_phys_props as _parse_phys,
            get_calc             as _phys_calc_val,
            get_pcn_band         as _get_pcn_band,
        )
        disc_map    = data.get('disclosure_map', {})
        supplier_in = data.get('supplier', {})
        phys_in     = data.get('phys_props', {})
        revision_in = data.get('revision', {})
        usage       = product.get('usage', 'industrial')
        form        = data.get('form', product.get('form', 'liquid'))
        _form_val   = product.get('form') or 'liquid'
        _prod_form_for_refresh = data.get('form') or product.get('form') or 'liquid'
        _parsed_phys = _parse_phys(phys_in)
        _req_methods: dict = data.get('phys_methods', {}) or {}
        _h314_removed_flag = bool(data.get('h314_neutralization_removed', False))

        # KKDİK Ek-2 1.1 ve 1.3 — ürün tanımlayıcısı ve tedarikçi kimliği olmadan GBF üretilmez
        _id_missing = [lbl for lbl, val in (
            ('Ürün adı',   (product.get('name') or '').strip() not in ('', 'Ürün', 'Product')),
            ('Firma adı',  bool((supplier_in.get('name') or '').strip())),
            ('Adres',      bool((supplier_in.get('address') or '').strip())),
            ('Telefon',    bool((supplier_in.get('phone') or '').strip())),
        ) if not val]
        if _id_missing:
            raise HTTPException(status_code=422, detail={
                'error': 'missing_identity',
                'message': 'GBF üretilemiyor — zorunlu alanlar eksik (KKDİK Ek-2 Bölüm 1): ' + ', '.join(_id_missing),
                'missing': _id_missing,
            })

        def _num(v):
            try:
                return float(v) if v not in (None, '') else None
            except (TypeError, ValueError):
                return None

        _ci = data.get('calc_input') or None
        if _ci:
            _inp = {
                'components': _ci.get('components') or components,
                'form':       _ci.get('form') or _form_val,
                'form_sub':   _ci.get('form_sub') or '',
                'usage':      _ci.get('usage') or usage,
                'lang':       lang,
                'user_fp':    _num(_ci.get('user_fp')),
                'user_bp':    _num(_ci.get('user_bp')),
                'fp_status':  _ci.get('fp_status') or '',
                'mixture_ph': _ci.get('mixture_ph'),
                'test_data':  _ci.get('test_data') or {},
                'h314_removed': _h314_removed_flag,
            }
            # Eldiven malzeme/kalınlık seçimi (KKDİK Ek-2 8.2.2.2(b)) — ürün kartından
            _inp['glove_material']  = product.get('glove_material') or _ci.get('glove_material')
            _inp['glove_thickness'] = product.get('glove_thickness') or _ci.get('glove_thickness')
        else:
            _fp_req_m = _req_methods.get('flash_point', {}) if isinstance(_req_methods, dict) else {}
            _fp_is_user = _fp_req_m.get('measured', True) if isinstance(_fp_req_m, dict) else True
            _user_fp = _phys_calc_val(_parsed_phys, 'flash_point') if _fp_is_user else None
            if _user_fp is None:
                _user_fp = _num(phys_in.get('user_fp'))
            _inp = {
                'components': components,
                'form':       _form_val,
                'form_sub':   product.get('form_sub') or data.get('form_sub') or '',
                'usage':      usage,
                'lang':       lang,
                'user_fp':    _user_fp,
                'user_bp':    _phys_calc_val(_parsed_phys, 'boiling_point'),
                'fp_status':  data.get('fp_status') or '',
                'mixture_ph': phys_in.get('ph') or None,
                'test_data':  {},
                'h314_removed': _h314_removed_flag,
                'glove_material':  product.get('glove_material'),
                'glove_thickness': product.get('glove_thickness'),
            }

        # Motor başarısız olursa PDF üretilmez (fail-closed)
        try:
            core = await _pipe.classify(_inp)
        except Exception as _eng_err:
            import traceback as _tb
            print(f'[PDF] Motor hatası — PDF üretilmedi: {_eng_err}\n{_tb.format_exc()}')
            raise HTTPException(status_code=500, detail=f'SDS motor hatası: {_eng_err}')

        if core['pending_decisions']:
            raise HTTPException(
                status_code=409,
                detail={
                    'error': 'pending_decisions',
                    'message': 'PDF üretilemiyor — aşağıdaki kararlar çözümlenmeden sınıflandırma tamamlanamaz.',
                    'pending_decisions': core['pending_decisions'],
                },
            )

        # Bölüm 3 bileşenleri: ön yüz alanları (konsantrasyon metni, EC no…) + tazelenmiş tehlike verisi
        _fresh_by_cas = {(c.get('cas') or c.get('cas_no') or '').strip(): c for c in core['components']}
        def _overlay(c: dict) -> dict:
            f = _fresh_by_cas.get((c.get('cas') or c.get('cas_no') or '').strip())
            if not f:
                return c
            c = dict(c)
            for k in ('hazards', 'm_factors', 'ate', 'ate_source', 'suppl_hazards', 'euh_limits',
                      'source_priority', 'sea_ek6', 'annex_vi'):
                if k in f:
                    c[k] = f[k]
            return c
        components = [_overlay(c) for c in components]

        h_codes         = core['h_codes']
        all_h_codes     = core['all_h_codes']
        signal          = core['signal']
        py_clp_passed   = core['clp_passed']
        euh_result      = core['euh']
        euh_codes       = euh_result.get('euh_codes', [])
        p_result        = core['p_codes']
        py_transport    = core['transport']
        py_ppe          = core['ppe']
        eco_result      = core['eco_obj']
        _phys_res       = core['phys_res']
        _clp_res        = core['clp_res']
        _be_ate_details = core['ate_details']

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
                    'method': (_req_m.get('method', '') or '') if isinstance(_req_m, dict) else '',
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
                if _tp.get('estimate_only'):
                    # Ölçülmemiş FP/KN: "Belirlenmemiştir" — "hesaplanmış" notu basılmaz
                    _phys_methods[_bk] = ({'note_text': _tp['pdf_note']}
                                          if _tp.get('pdf_note') else {})
                else:
                    _phys_methods[_bk] = {
                        'measured':  _tp_measured,
                        'standard':  _tp_std,
                        'method':    _tp_mth,
                        'error_pct': None,
                    }
        # ────────────────────────────────────────────────────────────────────

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
            from app.services.substance_lookup import COMMON_NAMES_TR as _CN_TR, clean_tr_name as _clean_tr
            if not name_tr:   # Ek-6 dışı yaygın maddeler — Türkçe ad (eski kayıtlarda boş kalmasın)
                name_tr = _CN_TR.get(str(c.get('cas_no') or c.get('cas') or '').strip(), '')
            name_tr = _clean_tr(name_tr)   # Ek-6 Not B "nitrik asit ... %" → "nitrik asit"
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
                    'echa_supplement': h.get('echa_supplement') or None,   # Ek-6 dışı sınıf (Bölüm 3 †)
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

        # Bölüm 3 tehlike kodları yukarıda _overlay ile sınıflandırma hattının tazelediği veriden
        # gelir (SEA Ek-6 yetkili; Ek-6 dışı ECHA sınıfları işaretli, kullanıcının kaldırdıkları hariç).
        # Önceden burada DB'den ham kodlar yeniden yazılıyordu — kullanıcının kaldırdığı Ek-6 dışı
        # sınıf Bölüm 3'e geri geliyordu.

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
                'is_detergent': bool(product.get('is_detergent')),   # Deterjanlar Hakkında Yönetmelik
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
            # ATEmix ve "bilinmeyen akut toksisite" ifadesi yalnız sınıflandırma hattından (tek kaynak);
            # önceden arayüzün eski hesabı birleştiriliyordu — verisi olan bileşenler "bilinmeyen" sayılıyordu
            'ate_mix_details': dict(_be_ate_details or {}),
            'ate_from_pipeline': True,   # boş ATE ayrıntısı = bilinmeyen bileşen yok (yedek kontrol yapılmaz)
            'h314_neutralization_removed': bool(data.get('h314_neutralization_removed', False)),
            'clp_note_overrides': data.get('clp_note_overrides', {}),
            'ppe': py_ppe,
            'glove': core.get('glove') or {},
            'form_sub':    data.get('form_sub'),
            'voc_content': data.get('voc_content'),
            # Test yerine verilen fiziksel tehlike kararlarının gerekçesi (Bölüm 16)
            'classification_notes': core.get('classification_notes', []),
            # Etikette adı yazılması zorunlu bileşenler (SEA/CLP Md. 18(3)(b)) — Bölüm 2.2
            'label_components': core.get('label_components', []),
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

        # CAMEO async pre-fetch — event loop bloke olmadan, timeout ile
        try:
            import asyncio as _asyncio
            from app.services.cameo_service import get_mixture_incompatibilities as _get_mi
            _loop = _asyncio.get_event_loop()
            sds_data['_cameo_incompat'] = await _asyncio.wait_for(
                _loop.run_in_executor(None, _get_mi, components),
                timeout=4.0,
            )
        except Exception:
            sds_data['_cameo_incompat'] = None  # None → pdf_sds_service senkron fallback dener

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

        from fastapi.responses import JSONResponse as _JR
        return _JR({
            'pdf':      _b64.b64encode(pdf_bytes).decode(),
            'filename': _filename,
            'sds_data': _sds_for_review,
            'validation': {
                'error':   _val_errors,
                'warning': _val_warnings,
                'info':    _val_infos,
                'issues':  _val_issues[:5],
            },
            # PDF'in kullandığı nihai sınıflandırma — ön yüz sağ panelle karşılaştırır
            'classification': _pipe.summary(core),
        })

    except HTTPException:
        raise   # 409 (bekleyen karar) / 500 (motor hatası) olduğu gibi dönsün
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
async def substance_lookup(cas: str, form: str = None):
    """
    CAS numarasına göre madde bilgisi döndür.
    form parametresi Not B maddeleri için (HCl gibi) sıvı/gaz ayrımı yapar.
    Hiyerarşi:
      1. data/cl/   — SEA Ek-6 (mutlak)
      2. data/annex6/ — CLP Annex VI
      3. substances_custom.json
      4. ECHA C&L Inventory API (canlı, arşive kaydedilir)
    """
    from app.services.substance_lookup import lookup_substance, get_oel
    from app.services.reach_db import get_ec_no, get_reg_no

    oel = get_oel(cas)

    # SEA Ek-6 maddesinde Ek-6 dışı sınıfların ECHA takviyesi önce tamamlanır (ilk sorguda eksik kalmasın)
    try:
        from app.services.substance_lookup import ensure_echa_supplement
        await ensure_echa_supplement(cas)
    except Exception:
        pass
    # Sıra 1-2-3: Lokal dosyalar
    result = lookup_substance(cas, form=form)

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
                    # substances_custom.json'a da yaz — kalıcılığı data_store (sdspass-data deposu) sağlar.
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
                    "name_tr"   : __import__('app.services.substance_lookup', fromlist=['x'])
                                  .COMMON_NAMES_TR.get(cas.strip(), ""),
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
            "name_tr"   : __import__('app.services.substance_lookup', fromlist=['x']).clean_tr_name(
                              result.get("name_tr") or __import__('app.services.substance_lookup', fromlist=['x'])
                              .COMMON_NAMES_TR.get(cas.strip(), "")),   # Türkçe SDS Bölüm 3 için
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

        # 2. STOT RE (hedef organ bazlı) — stot_engine doğru iki kademeli eşik uygular
        stot = calculate_stot_re(components)
        for r_stot in stot["results"]:
            h = r_stot["h_code"]
            if h not in result["h_codes"]:
                result["h_codes"].append(h)
            result["passed"] = [p for p in result["passed"] if p.get("h_code") != h]
            result["passed"].append({
                "h_class": r_stot.get("h_class", "STOT RE"),
                "h_code":  h,
                "conc":    0,
                "reason":  r_stot.get("reason", "STOT RE"),
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
        result["signal_word_tr"] = {"Danger":"Tehlike","Warning":"Dikkat","":""}.get(signal,"")   # SEA Md.4(1)(ff)
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
                        "Dikkat" if lang=="TR" else "Warning") if signal=="Warning" else "",
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
        result = check_euh(components,
                           mixture_form=body.get('form', 'liquid'),
                           form_sub=body.get('form_sub', ''))
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
    euh_codes  = body.get("euh_codes", [])
    signal     = body.get("signal_word", "Warning")
    usage      = body.get("usage", "industrial")
    lang       = body.get("lang", "TR")
    max_label  = body.get("max_label", 6)
    try:
        _pform = body.get("form", "liquid")
        result = assign_p_codes(h_codes, signal, mixture_form=_pform, usage=usage)
        result["label"]    = select_label_p_codes(result["p_codes"], max_label, h_codes=h_codes, euh_codes=euh_codes,
                                                  usage=usage, form=_pform)
        result["sds"]      = classify_sds_p_codes(result["p_codes"], usage=usage, h_codes=h_codes, form=_pform,
                                                  label=result["label"]["selected"])
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
    from app.services import sds_pipeline as _pipe

    def _num(v):
        try:
            return float(v) if v not in (None, '') else None
        except (TypeError, ValueError):
            return None

    form     = body.get('form', 'liquid')
    form_sub = body.get('form_sub') or ''

    try:
        # Tek sınıflandırma hattı — PDF uç noktası da aynı fonksiyonu çağırır
        core = await _pipe.classify({
            'components': body.get('components', []),
            'form':       form,
            'form_sub':   form_sub,
            'usage':      body.get('usage', 'industrial'),
            'lang':       body.get('lang', 'TR'),
            'user_fp':    _num(body.get('user_fp') if body.get('user_fp') is not None else body.get('flash_point')),
            'user_bp':    _num(body.get('user_bp') if body.get('user_bp') is not None else body.get('boiling_point')),
            'fp_status':  body.get('fp_status') or '',
            'mixture_ph': body.get('mixture_ph'),
            'test_data':  body.get('test_data') or {},
            'h314_removed': bool(body.get('h314_neutralization_removed', False)),
            'glove_material':  body.get('glove_material'),
            'glove_thickness': body.get('glove_thickness'),
        })
        phys_result = core['phys_res']
        return {
            'success':     True,
            'h_codes':     core['h_codes'],       # etiket
            'all_h_codes': core['all_h_codes'],   # Bölüm 2.1 sınıflandırma tablosu
            'signal':      core['signal'],
            'clp_passed':  core['clp_passed'],
            'euh':         core['euh'],
            'euh_codes':   core['euh'].get('euh_codes', []),
            'euh_details': core['euh'].get('euh_details', []),
            'p_codes':     core['p_codes'],
            'physical': {
                'results':     phys_result.get('results', []),
                'primary':     phys_result.get('primary', []),
                'extra':       phys_result.get('extra', []),
                'warnings':    phys_result.get('warnings', []),
                'fp_decision': phys_result.get('fp_decision', {}),
                'pending_decisions': phys_result.get('pending_decisions', []),
            },
            'stot':        core['stot_res'],
            'eco':         core['eco_panel'],
            'transport':   core['transport'],
            'ppe':         core['ppe'],
            'glove':       core.get('glove') or {},
            'theo_props':  phys_result.get('theo_props', {}),
            'warnings':    core['warnings'],
            'pictograms':  core['pictograms'],
            'ate_details': core['ate_details'],
            'pending_decisions': core['pending_decisions'],
            'label_components':  core['label_components'],   # etikette adı zorunlu bileşenler
            'ek6_supplements':   core.get('ek6_supplements', []),   # Ek-6 dışı (ECHA) sınıflar
            'summary':     _pipe.summary(core),   # PDF ile karşılaştırma (güvenlik ağı)
            'form_sub':    form_sub or None,
            'voc_content': body.get('voc_content'),
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
        components    : [{'cas': '7647-01-0', 'conc': 18.0, 'h_codes': ['H314', ...]}, ...]
        lang          : 'TR' | 'EN'
    """
    from app.services.transport_engine import classify as transport_classify, build_transport_components
    h_codes      = body.get('h_codes', [])
    phys_h_codes = body.get('phys_h_codes', [])
    form         = body.get('form', 'liquid')
    raw_comps    = body.get('components', [])
    comps        = build_transport_components(raw_comps) if raw_comps else None
    result = transport_classify(h_codes=h_codes, form=form, phys_h_codes=phys_h_codes,
                                components=comps)
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


@app.post("/api/v1/label/guide", response_class=Response)
async def generate_label_guide(data: dict = Body(...)):
    """Etiket Teknik Rehber Kartı PDF üret."""
    from app.services.label_guide_service import generate_label_guide_pdf
    try:
        pdf_bytes = generate_label_guide_pdf(data)
        product_name = data.get('product', {}).get('name', 'etiket')
        safe_name = ''.join(c for c in product_name if c.isalnum() or c in (' ', '-', '_'))[:40]
        filename = f"{safe_name}_etiket_rehber.pdf"
        return Response(
            content=pdf_bytes,
            media_type='application/pdf',
            headers={'Content-Disposition': f'attachment; filename="{filename}"'},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Rehber kartı üretim hatası: {e}')


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
                    "hCodes": ["H314", "H335"],
                    "ld50_oral": 300.0,
                    "ld50_dermal": None,
                    "lc50_inhal": None
                }
            ],
            "phys_props": {
                "appearance": "beyaz katı toz",
                "color": "beyaz",
                "odor": "kokusuz",
                "ph": "7.0",
                "melting_point": "801",
                "boiling_point": "1413",
                "flash_point": None,
                "vapor_pressure": "< 0.1 hPa (20°C)",
                "density": "2.16",
                "solubility": "360 g/L (20°C)",
                "viscosity": None,
                "auto_ignition": None,
                "decomp_temp": None,
                "log_kow": None
            }
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
- ld50_oral: Bölüm 11'deki oral LD50 değeri mg/kg cinsinden sayısal (yoksa null)
- ld50_dermal: Bölüm 11'deki dermal LD50 değeri mg/kg cinsinden sayısal (yoksa null)
- lc50_inhal: Bölüm 11'deki inhalasyon LC50 değeri mg/L/4h cinsinden sayısal (yoksa null)
- phys_props: Bölüm 9'daki fiziksel ve kimyasal özellikler (yoksa null):
  - appearance: görünüm/form (renk + fiziksel hal, örn. "beyaz katı toz")
  - color: renk
  - odor: koku
  - ph: pH değeri (metin olarak, örn. "7.0" veya "6.5-7.5")
  - melting_point: erime/donma noktası °C (sadece sayı veya aralık, örn. "801" veya "58-62")
  - boiling_point: kaynama noktası °C
  - flash_point: parlama noktası °C (yoksa null)
  - vapor_pressure: buhar basıncı (birimi ile, örn. "< 0.1 hPa (20°C)")
  - density: yoğunluk g/cm³ veya g/mL (sadece sayı, örn. "1.84")
  - solubility: suda çözünürlük (birimi ile, örn. "360 g/L (20°C)" veya "tamamen karışır")
  - viscosity: viskozite (birimi ile, örn. "50 mPa·s (20°C)")
  - auto_ignition: kendiliğinden tutuşma sıcaklığı °C
  - decomp_temp: ayrışma sıcaklığı °C
  - log_kow: n-oktanol/su dağılım katsayısı (logP)
- Belgede yazan değerleri birebir al, tahmin etme; birim dönüşümü yapma
- Belirlenmemiş/uygulanamaz değerler için null yaz

SDS METNİ:
{sds_text[:30000]}

Sadece JSON:"""

        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=4096,
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

            if not cas:
                warnings.append(f"{comp.get('name','?')}: CAS numarası yok — H kodları doğrulanamadı, PDF değerleri kullanıldı")
                # PDF değerlerinden hazards üret (h_class bilinmiyor)
                comp["hazards"] = [{"h_class": c, "h_code": c} for c in pdf_hcodes]
            else:
                sub = lookup_substance(cas)
                if not sub:
                    warnings.append(f"{comp.get('name','?')} (CAS {cas}): veritabanında bulunamadı — H kodları doğrulanamadı, PDF değerleri kullanıldı")
                    comp["hazards"] = [{"h_class": c, "h_code": c} for c in pdf_hcodes]
                else:
                    # EC no eksikse doldur
                    if not comp.get("ec_no") and sub.get("ec_no"):
                        comp["ec_no"] = sub["ec_no"]
                    # M faktörleri
                    if sub.get("m_factors"):
                        comp["m_factors"] = sub["m_factors"]
                    # DB'deki hazards listesi — h_class doğru formatta (örn. "Skin Corr. 1A")
                    db_hazards = [h for h in (sub.get("hazards") or []) if h.get("h_code")]
                    db_hcodes  = [h["h_code"].upper() for h in db_hazards]
                    if db_hazards:
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
                        comp["hazards"] = db_hazards  # h_class + h_code doğru formatta
                    else:
                        comp["hazards"] = [{"h_class": c, "h_code": c} for c in pdf_hcodes]

            # ATE değerleri — Bölüm 11'den çekilen, veritabanında yoksa ATEmix hesabına girer
            ate_oral   = comp.get("ld50_oral")
            ate_dermal = comp.get("ld50_dermal")
            ate_inhal  = comp.get("lc50_inhal")
            if ate_oral or ate_dermal or ate_inhal:
                comp["ate"] = {
                    "oral":   float(ate_oral)   if ate_oral   else None,
                    "dermal": float(ate_dermal) if ate_dermal else None,
                    "inhal":  float(ate_inhal)  if ate_inhal  else None,
                }

            validated.append(comp)

        # B9 fiziksel özellikler — yalnızca tek bileşen + konsantrasyon ≥ 95% ise geçerli
        phys_props = parsed.get("phys_props") if isinstance(parsed, dict) else None
        _single = len(validated) == 1
        _conc = validated[0].get("concMax") or validated[0].get("concMin") if _single else None
        try:
            _conc_val = float(_conc) if _conc is not None else 0.0
        except (TypeError, ValueError):
            _conc_val = 0.0
        phys_props_applicable = bool(_single and _conc_val >= 95.0 and phys_props)

        return {
            "components": validated,
            "warnings": warnings,
            "supplier": supplier,
            "phys_props": phys_props,
            "phys_props_applicable": phys_props_applicable,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────────────────────
# AGENT ENDPOINTLERİ
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/api/v1/sds/section-texts")
async def sds_section_texts(body: dict = Body(...)):
    """
    H kodları listesinden B4-8 standart SDS cümlelerini döndür.
    Agent bu endpoint ile standart metinleri çeker — kendisi uydurmaz.

    Gelen: { "h_codes": [...], "lang": "TR", "sections": [4,5,6,7,8] }
    Döner: { "4": [{h_code, text}, ...], "5": [...], ... }
    """
    from app.services.sds_sentence_service import generate_section
    from app.services.codes_i18n import get_h, get_p

    h_codes = body.get("h_codes") or []
    lang    = (body.get("lang") or "TR").upper()
    sections = body.get("sections") or [4, 5, 6, 7, 8]

    result = {}
    for sec in sections:
        sentences = generate_section(sec, h_codes)
        result[str(sec)] = sentences

    # H ve P kod metinleri — etiket için
    h_texts = {h: get_h(lang, h) for h in h_codes}
    return {"sections": result, "h_texts": h_texts}


# ── Agent tool tanımları ──────────────────────────────────────────────────────
_AGENT_TOOLS = [
    {
        "name": "lookup_substance",
        "description": "CAS numarasına göre madde bilgisi çek (ad, tehlike sınıfları, M-faktörleri, SCL, ATE).",
        "input_schema": {
            "type": "object",
            "properties": {
                "cas": {"type": "string", "description": "CAS numarası (örn. 7647-01-0)"},
                "form": {"type": "string", "description": "Fiziksel hal: liquid | solid | gas (opsiyonel)"}
            },
            "required": ["cas"]
        }
    },
    {
        "name": "get_phys_props",
        "description": "CAS numarasına göre PubChem'den fiziksel özellikler çek: yoğunluk, kaynama noktası, parlama noktası, buhar basıncı, viskozite, çözünürlük. Kullanıcıya sormadan önce bu tool'u çağır.",
        "input_schema": {
            "type": "object",
            "properties": {
                "cas": {"type": "string", "description": "CAS numarası (örn. 7647-01-0)"}
            },
            "required": ["cas"]
        }
    },
    {
        "name": "calculate_clp",
        "description": "Karışım bileşenlerinden CLP sınıflandırması hesapla. H kodları, sinyal, piktogram, P kodları, EUH, ekoloji, STOT, fiziksel tehlike döner.",
        "input_schema": {
            "type": "object",
            "properties": {
                "components": {
                    "type": "array",
                    "description": "Bileşen listesi",
                    "items": {
                        "type": "object",
                        "properties": {
                            "cas":       {"type": "string"},
                            "name":      {"type": "string"},
                            "conc":      {"type": "number", "description": "Worst-case konsantrasyon (üst sınır)"},
                            "concMax":   {"type": "number"},
                            "hazards":   {"type": "array"},
                            "m_factors": {"type": "object"},
                            "scl":       {"type": "array"},
                            "ate":       {"type": "object"}
                        }
                    }
                },
                "form":        {"type": "string", "description": "liquid | solid | gas | aerosol"},
                "user_fp":     {"type": "number", "description": "Parlama noktası °C (ölçülmüşse)"},
                "mixture_ph":  {"type": "number", "description": "Karışım pH değeri"},
                "usage":       {"type": "string", "description": "industrial | professional | consumer"},
                "lang":        {"type": "string", "description": "TR | EN"}
            },
            "required": ["components", "form"]
        }
    },
    {
        "name": "detect_adr",
        "description": (
            "H kodlarına göre ADR/IMDG/IATA taşımacılık sınıflandırması yap. "
            "Doğru UN numarası için 'components' listesini MUTLAKA gönder — "
            "aksi hâlde Sınıf 8 karışımlar için UN1760 (B.N.O.) döner."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "h_codes":     {"type": "array", "items": {"type": "string"}},
                "form":        {"type": "string"},
                "flash_point": {"type": "number"},
                "lang":        {"type": "string"},
                "components": {
                    "type": "array",
                    "description": "Bileşen listesi — CAS bazlı spesifik UN araması için gerekli",
                    "items": {
                        "type": "object",
                        "properties": {
                            "cas":     {"type": "string"},
                            "conc":    {"type": "number", "description": "Worst-case konsantrasyon %"},
                            "h_codes": {"type": "array", "items": {"type": "string"}}
                        }
                    }
                }
            },
            "required": ["h_codes", "form"]
        }
    },
    {
        "name": "check_svhc",
        "description": "Bileşenlerin SVHC (çok yüksek endişe verici madde) listesinde olup olmadığını kontrol et.",
        "input_schema": {
            "type": "object",
            "properties": {
                "components": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "cas":           {"type": "string"},
                            "name":          {"type": "string"},
                            "concentration": {"type": "number"}
                        }
                    }
                }
            },
            "required": ["components"]
        }
    },
    {
        "name": "get_oel",
        "description": "Bir maddenin KKDİK Ek-14 mesleki maruziyet limitini (OEL) döndür.",
        "input_schema": {
            "type": "object",
            "properties": {
                "cas": {"type": "string"}
            },
            "required": ["cas"]
        }
    },
    {
        "name": "get_section_texts",
        "description": "H kodlarına göre B4-8 standart SDS cümlelerini döndür. Bu tool olmadan B4-8 metinleri yazma.",
        "input_schema": {
            "type": "object",
            "properties": {
                "h_codes":  {"type": "array", "items": {"type": "string"}},
                "lang":     {"type": "string", "description": "TR | EN"},
                "sections": {"type": "array",  "items": {"type": "integer"}, "description": "Örn. [4,5,6,7,8]"}
            },
            "required": ["h_codes"]
        }
    },
    {
        "name": "read_knowledge",
        "description": (
            "KKDİK/CLP/ADR mevzuat kurallarını ve hesap yöntemlerini okur. "
            "SDS bölümü yazmadan önce ilgili konuyu sorgula. "
            "Özellikle B2, B3, B14, B15 yazmadan ÖNCE zorunlu çağır."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "enum": [
                        "workflow", "mixture_health", "mixture_eco",
                        "labeling", "b3", "physical", "adr",
                        "oel", "self_check", "validation", "kkdik_references"
                    ],
                    "description": (
                        "workflow=genel iş akışı, "
                        "mixture_health=sağlık karışım sınıflandırma hesabı, "
                        "mixture_eco=çevre/sucul karışım hesabı, "
                        "labeling=B2 etiket dominance/P-kodu kuralları, "
                        "b3=B3 bileşim bildirimi eşikleri, "
                        "physical=fiziksel tehlike kuralları, "
                        "adr=B14 taşımacılık/UN numarası kuralları, "
                        "oel=B8 OEL kaynakları, "
                        "self_check=SDS hazırlama öz-denetim listesi, "
                        "validation=doğrulama ve ADR notları, "
                        "kkdik_references=KKDİK/SEA/UN sabit referanslar ve sık hata listesi"
                    )
                }
            },
            "required": ["topic"]
        }
    }
]

# Konu → (dosya, bölüm başlığı) eşlemesi
_KNOWLEDGE_TOPIC_MAP = {
    "workflow":          ("GBF_KURAL_VE_HESAP_LISTESI.md", "## 0."),
    "mixture_health":    ("GBF_KURAL_VE_HESAP_LISTESI.md", "## 2."),
    "mixture_eco":       ("GBF_KURAL_VE_HESAP_LISTESI.md", "## 3."),
    "labeling":          ("GBF_KURAL_VE_HESAP_LISTESI.md", "## 4."),
    "b3":                ("GBF_KURAL_VE_HESAP_LISTESI.md", "## 5."),
    "physical":          ("GBF_KURAL_VE_HESAP_LISTESI.md", "## 6."),
    "adr":               ("GBF_KURAL_VE_HESAP_LISTESI.md", "## 7."),
    "oel":               ("GBF_KURAL_VE_HESAP_LISTESI.md", "## 8."),
    "self_check":        ("GBF_KURAL_VE_HESAP_LISTESI.md", "## 10."),
    "kkdik_references":  ("GBF_KURAL_VE_HESAP_LISTESI.md", "## 11."),
    "validation":        ("DOGRULAMA_NOTLARI.md",           None),
}

_KNOWLEDGE_DIR = Path(__file__).parent.parent / "sds-knowledge"


def _read_knowledge_section(topic: str) -> dict:
    """Konuya göre bilgi tabanından ilgili bölümü döndür."""
    if topic not in _KNOWLEDGE_TOPIC_MAP:
        valid = list(_KNOWLEDGE_TOPIC_MAP.keys())
        return {"error": f"Bilinmeyen konu: '{topic}'. Geçerliler: {valid}"}

    filename, section_prefix = _KNOWLEDGE_TOPIC_MAP[topic]
    filepath = _KNOWLEDGE_DIR / filename

    if not filepath.exists():
        return {"error": f"Dosya bulunamadı: {filename}"}

    content = filepath.read_text(encoding="utf-8")

    # Tüm dosya isteniyorsa
    if section_prefix is None:
        return {"topic": topic, "source": filename, "content": content}

    # Bölüm başlığını bul, bir sonraki ## başlığına kadar al
    lines = content.splitlines()
    start_idx = None
    for i, line in enumerate(lines):
        if line.startswith(section_prefix):
            start_idx = i
            break

    if start_idx is None:
        return {"error": f"'{section_prefix}' bölümü {filename} içinde bulunamadı"}

    end_idx = len(lines)
    for i in range(start_idx + 1, len(lines)):
        if lines[i].startswith("## ") and i > start_idx:
            end_idx = i
            break

    section_text = "\n".join(lines[start_idx:end_idx]).strip()
    return {"topic": topic, "source": f"{filename} {section_prefix}", "content": section_text}


def _load_mevzuat() -> list:
    """data/mevzuat.json dosyasını yükle, hata olursa boş liste döndür."""
    import json
    path = Path(__file__).parent.parent / "data" / "mevzuat.json"
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("mevzuat", [])
    except Exception:
        return []


def _build_sabit_block() -> str:
    """
    data/mevzuat.json'dan _SABIT sistem prompt bloğunu oluştur.
    Yönetmelik değişince sadece JSON güncellenir, kod değişmez.
    """
    mevzuat = _load_mevzuat()
    if not mevzuat:
        return ""

    rows = "\n".join(
        f"| {m['kod']} | **{m['rg_no']}** | {m['rg_tarih']} |"
        for m in mevzuat
    )

    yasak_satirlar = []
    for m in mevzuat:
        for yasak in m.get("yasak_karismalar", []):
            yasak_satirlar.append(
                f"**YASAK:** `{yasak}` bu belgede geçemez — {m['kod']} için her zaman `{m['rg_no']}` kullan."
            )

    yasak_blok = "\n".join(yasak_satirlar)

    # B1 atıf cümlesi
    b1_atif = _build_b1_atif(mevzuat)

    return (
        "\n\n## ⚠️ SABİT MEVZUAT NUMARALARI — EZBERDEN YAZMA, BURADAN AL\n\n"
        "| Mevzuat | Resmi Gazete No | Tarih |\n"
        "|---|---|---|\n"
        f"{rows}\n\n"
        f"{yasak_blok}\n\n"
        f"**B1 ATIF CÜMLESİ** (B1 bölümünün sonuna aynen ekle, değiştirme):\n"
        f"> {b1_atif}\n\n"
    )


def _build_b1_atif(mevzuat: list | None = None) -> str:
    """B1 bölümü için mevzuat atıf cümlesini JSON'dan üret."""
    if mevzuat is None:
        mevzuat = _load_mevzuat()
    b1_list = [m for m in mevzuat if "B1_atif" in m.get("kullanim", [])]
    if not b1_list:
        return ""
    parcalar = "; ".join(
        f"{m['tam_ad']} ({m['kod']}, {m['rg_tarih']} tarihli {m['rg_no']} sayılı Resmî Gazete)"
        for m in b1_list
    )
    return (
        f"Bu Güvenlik Bilgi Formu; {parcalar} hükümlerine uygun olarak hazırlanmıştır."
    )


def _load_knowledge_into_prompt() -> str:
    """
    Bilgi tabanının değişmeyen bölümlerini sistem promptuna göm.
    Her SDS üretiminde read_knowledge tool çağrısı yerine prompt'ta hazır olur:
    - 5-6 tool call tasarrufu (hız)
    - Mevzuat referansları hallüsinasyon riski sıfır
    - B15/B16 sabit metinler her seferinde aynı
    """
    # Her SDS'de çağrılan sabit konular
    ALWAYS_LOAD = [
        "kkdik_references",  # B15: KKDİK/SEA/OEL no, sık hata listesi
        "labeling",          # B2: dominance/P-kodu kuralları
        "b3",                # B3: bileşim eşikleri
        "adr",               # B14: UN numarası kuralları
        "self_check",        # Genel: öz-denetim listesi
    ]
    parts = ["\n\n---\n## 📚 GÖMÜLÜ MEVZUAT BİLGİSİ (read_knowledge yerine kullan)\n"]
    for topic in ALWAYS_LOAD:
        result = _read_knowledge_section(topic)
        if "error" not in result:
            parts.append(f"\n### [{topic.upper()}] — {result['source']}\n{result['content']}\n")
    parts.append("\n> NOT: Yukarıdaki bilgiler read_knowledge tool'u ile aynı kaynaktan gelir.\n"
                 "> Bu konular için ayrıca read_knowledge çağırma — zaman kaybı olur.\n"
                 "> physical / mixture_health / mixture_eco / validation için gerekirse çağır.\n---\n")
    return "".join(parts)


async def _run_agent_tool(tool_name: str, tool_input: dict, base_url: str = "") -> dict:
    """Agent tool call'ını HTTP yerine doğrudan Python fonksiyonları ile çalıştır."""
    try:
        if tool_name == "get_phys_props":
            cas = tool_input["cas"]
            try:
                from app.services.pubchem_phys_service import fetch_phys
                props = await fetch_phys(cas.strip())
                if not props:
                    return {"found": False, "cas": cas, "props": {}}
                # Agent'a anlamlı birimlerle göster
                result_props = {}
                if props.get("density") is not None:
                    result_props["density"] = f"{props['density']} g/cm³"
                if props.get("boiling_point") is not None:
                    result_props["boiling_point"] = f"{props['boiling_point']} °C"
                if props.get("flash_point") is not None:
                    result_props["flash_point"] = f"{props['flash_point']} °C"
                elif "flash_point" in props:
                    result_props["flash_point"] = "Uygulanamaz (yanmaz)"
                if props.get("vapor_pressure") is not None:
                    result_props["vapor_pressure"] = f"{props['vapor_pressure']} hPa"
                if props.get("viscosity") is not None:
                    result_props["viscosity"] = f"{props['viscosity']} cSt"
                if props.get("solubility") is not None:
                    result_props["solubility"] = f"{props['solubility']} mg/L"
                elif props.get("solubility_text"):
                    result_props["solubility"] = props["solubility_text"]
                if props.get("mw") is not None:
                    result_props["mw"] = f"{props['mw']} g/mol"
                if props.get("melting_point") is not None:
                    result_props["melting_point"] = f"{props['melting_point']} °C"
                    result_props["melting_point_note"] = "⚠️ Bu değer saf madde içindir — karışım/çözelti için farklı olabilir. Kullanıcıya sorun."
                return {"found": True, "cas": cas, "props": result_props, "raw": props}
            except Exception as e:
                return {"found": False, "cas": cas, "props": {}, "error": str(e)}

        elif tool_name == "lookup_substance":
            cas  = tool_input["cas"]
            form = tool_input.get("form") or ""
            full = await substance_lookup(cas=cas, form=form or None)
            # SCL verisini agent'a gönderme — konsantrasyon analizi motorun işi
            # scl görünce agent kendi SCL hesabı yapıyor (yasak)
            if isinstance(full, dict):
                full.pop("scl", None)
            return full

        elif tool_name == "calculate_clp":
            return await sds_calculate(body=tool_input)

        elif tool_name == "detect_adr":
            return await adr_auto_detect(body=tool_input)

        elif tool_name == "check_svhc":
            return await svhc_check_mixture(body=tool_input)

        elif tool_name == "get_oel":
            cas = tool_input["cas"]
            return await oel_lookup(cas=cas)

        elif tool_name == "get_section_texts":
            return await sds_section_texts(body=tool_input)

        elif tool_name == "read_knowledge":
            topic = tool_input.get("topic", "")
            return _read_knowledge_section(topic)

        else:
            return {"error": f"Bilinmeyen tool: {tool_name}"}

    except Exception as e:
        return {"error": f"{tool_name} hatası: {str(e)}"}


_TOOL_PROGRESS = {
    "get_phys_props":   "🧪 Fiziksel özellikler alınıyor ({cas})…",
    "lookup_substance": "🔍 Madde verisi alınıyor ({cas})…",
    "calculate_clp":    "⚗️ CLP sınıflandırması hesaplanıyor…",
    "detect_adr":       "🚛 ADR taşımacılık sınıfı belirleniyor…",
    "check_svhc":       "📋 SVHC / REACH kontrolü yapılıyor…",
    "get_oel":          "🏭 OEL maruz kalma sınırları alınıyor…",
    "get_section_texts":"📝 Standart güvenlik metinleri alınıyor…",
}

def _tool_progress_text(tu) -> str:
    tpl = _TOOL_PROGRESS.get(tu.name, f"🔧 {tu.name} çalışıyor…")
    cas = tu.input.get("cas", "")
    return tpl.format(cas=cas) if cas else tpl.format(cas="")


async def _agent_stream(messages: list, lang: str, system_prompt: str):
    """SSE generator — tool_use döngüsü + paralel çağrılar."""
    import anthropic as _anthropic
    import json as _json

    def sse(data: dict) -> str:
        return f"data: {_json.dumps(data, ensure_ascii=False)}\n\n"

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        yield sse({"type": "error", "text": "ANTHROPIC_API_KEY tanımlı değil"})
        return

    client = _anthropic.AsyncAnthropic(api_key=api_key)
    current_messages = list(messages)
    _collected_sds: list[str] = []  # tüm asistan mesajlarını biriktir

    for _turn in range(10):
        yield sse({"type": "progress", "text": "💭 Agent yanıt üretiyor…"})

        resp = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=16384,
            system=system_prompt,
            tools=_AGENT_TOOLS,
            messages=current_messages,
        )

        tool_uses = [b for b in resp.content if b.type == "tool_use"]

        if not tool_uses:
            text = "".join(b.text for b in resp.content if hasattr(b, "text"))

            # FILL_FORM bloğunu yakala ve SSE event olarak yayınla
            import re as _re
            _ff_match = _re.search(r"<FILL_FORM>(.*?)</FILL_FORM>", text, _re.DOTALL)
            if _ff_match:
                try:
                    _ff_payload = _json.loads(_ff_match.group(1).strip())
                    yield f"event: fill_form\ndata: {_json.dumps(_ff_payload, ensure_ascii=False)}\n\n"
                except Exception:
                    pass
                # Bloğu görünen metinden çıkar
                text = _re.sub(r"\n?<FILL_FORM>.*?</FILL_FORM>\n?", "", text, flags=_re.DOTALL).strip()

            _collected_sds.append(text)
            _tl = text.lower()
            # B14+B16 birlikte varsa tam SDS; veya onay sorusu
            done = (
                ("b14" in _tl and "b16" in _tl) or
                any(kw in _tl for kw in [
                    "sds taslağı hazır", "gbf taslağı hazır",
                    "onaylıyor musunuz", "onayladıktan sonra",
                    "sds is ready", "word belgesi",
                ])
            )
            full_sds = "\n\n".join(_collected_sds) if done else ""
            yield sse({"type": "message", "text": text, "done": done,
                       "sds_text": full_sds})
            return

        # İlerleme mesajı
        if len(tool_uses) == 1:
            yield sse({"type": "progress", "text": _tool_progress_text(tool_uses[0])})
        else:
            names = " · ".join(_TOOL_PROGRESS.get(t.name, t.name).split(" ", 1)[-1].rstrip("…")
                               for t in tool_uses)
            yield sse({"type": "progress", "text": f"⚡ Paralel hesaplama: {names}…"})

        current_messages.append({"role": "assistant", "content": resp.content})

        # Tüm tool çağrılarını paralel çalıştır
        results = await asyncio.gather(
            *[_run_agent_tool(tu.name, tu.input) for tu in tool_uses]
        )

        tool_results = [
            {
                "type": "tool_result",
                "tool_use_id": tu.id,
                "content": _json.dumps(result, ensure_ascii=False),
            }
            for tu, result in zip(tool_uses, results)
        ]
        current_messages.append({"role": "user", "content": tool_results})

    yield sse({"type": "error", "text": "Agent döngüsü 10 turda tamamlanamadı"})


@app.post("/api/v1/agent/chat")
async def agent_chat(body: dict = Body(...)):
    """
    SDS oluşturma agent'ı — SSE stream + paralel tool çağrıları.

    Gelen:  messages:[{role,content}], lang:"TR"|"EN"
    Döner:  text/event-stream — progress / message / error olayları
    """
    messages = body.get("messages") or []
    lang     = (body.get("lang") or "TR").upper()

    if not messages:
        raise HTTPException(status_code=400, detail="messages boş olamaz")

    agent_md = Path(__file__).parent.parent / ".claude" / "agents" / "sds-olustur.md"
    if agent_md.exists():
        system_prompt = agent_md.read_text(encoding="utf-8")
        if system_prompt.startswith("---"):
            parts = system_prompt.split("---", 2)
            system_prompt = parts[2].strip() if len(parts) >= 3 else system_prompt
    else:
        system_prompt = "KKDİK/SEA uyumlu 16 bölümlü SDS hazırlayan uzmansın."

    # Mevzuat verilerini JSON'dan yükle ve sistem promptuna ekle
    system_prompt = _build_sabit_block() + system_prompt

    # Bilgi tabanını doğrudan sistem promptuna göm
    system_prompt += _load_knowledge_into_prompt()
    system_prompt += f"\n\nÇalışma dili: {lang}"

    return StreamingResponse(
        _agent_stream(messages, lang, system_prompt),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/v1/agent/export")
async def agent_export(body: dict = Body(...)):
    """
    Agent SDS metnini (Markdown) Word veya PDF olarak dışa aktar.

    Gelen:  { sds_text: "...", format: "docx"|"pdf", filename: "SDS" (opsiyonel) }
    Döner:  application/vnd.openxmlformats-officedocument.wordprocessingml.document
            veya application/pdf
    """
    sds_text = (body.get("sds_text") or "").strip()
    fmt      = (body.get("format") or "docx").lower()
    fname    = (body.get("filename") or "SDS").strip() or "SDS"

    if not sds_text:
        raise HTTPException(status_code=400, detail="sds_text boş olamaz")

    if fmt == "docx":
        content = _markdown_to_docx(sds_text)
        media   = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        dl_name = f"{fname}.docx"
    elif fmt == "pdf":
        content = _markdown_to_pdf(sds_text)
        media   = "application/pdf"
        dl_name = f"{fname}.pdf"
    else:
        raise HTTPException(status_code=400, detail="format 'docx' veya 'pdf' olmalı")

    return Response(
        content=content,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{dl_name}"'},
    )


def _markdown_to_docx(md_text: str) -> bytes:
    """Markdown metnini python-docx Word belgesine dönüştür."""
    from docx import Document
    from docx.shared import Pt, RGBColor, Cm, Inches
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
    import io, re, os

    doc = Document()

    # Sayfa kenar boşlukları
    for section in doc.sections:
        section.top_margin    = Cm(2)
        section.bottom_margin = Cm(2)
        section.left_margin   = Cm(2.5)
        section.right_margin  = Cm(2.5)

    _GHS_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "ghs_icons")

    def _set_cell_bg(cell, hex_color: str):
        """Tablo hücresine arka plan rengi ver (OOXML shading)."""
        tc = cell._tc
        tcPr = tc.get_or_add_tcPr()
        shd = OxmlElement("w:shd")
        shd.set(qn("w:val"), "clear")
        shd.set(qn("w:color"), "auto")
        shd.set(qn("w:fill"), hex_color.lstrip("#"))
        tcPr.append(shd)

    def _add_section_heading(text: str):
        """## başlıkları için koyu mavi kutulu stil."""
        # Tek hücreli tablo — arka plan efekti için
        tbl = doc.add_table(rows=1, cols=1)
        tbl.style = "Table Grid"
        cell = tbl.rows[0].cells[0]
        _set_cell_bg(cell, "1a3a5c")
        p = cell.paragraphs[0]
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after  = Pt(2)
        run = p.add_run(text)
        run.bold = True
        run.font.size = Pt(11)
        run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        # Tablodan sonra boşluk
        doc.add_paragraph("")

    def _extract_ghs_codes(text: str) -> list:
        return re.findall(r"GHS0[1-9]", text.upper())

    def _add_ghs_images(codes: list):
        """GHS piktogramlarını yan yana tablo ile ekle."""
        imgs = [os.path.join(_GHS_DIR, f"{c}.png") for c in codes if os.path.exists(os.path.join(_GHS_DIR, f"{c}.png"))]
        if not imgs:
            return
        tbl = doc.add_table(rows=1, cols=len(imgs))
        for j, img_path in enumerate(imgs):
            cell = tbl.rows[0].cells[j]
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run()
            run.add_picture(img_path, width=Cm(1.2), height=Cm(1.2))

    lines = md_text.splitlines()
    i = 0
    current_table = None

    while i < len(lines):
        line = lines[i]

        # Başlık satırları
        if line.startswith("### "):
            current_table = None
            p = doc.add_heading(line[4:].strip(), level=3)
            i += 1; continue
        if line.startswith("## "):
            current_table = None
            _add_section_heading(line[3:].strip())
            i += 1; continue
        if line.startswith("# "):
            current_table = None
            p = doc.add_heading(line[2:].strip(), level=1)
            for run in p.runs:
                run.font.color.rgb = RGBColor(0x1a, 0x3a, 0x5c)
            i += 1; continue

        # Tablo satırları (|...|...|)
        if line.startswith("|"):
            cols = [c.strip() for c in line.strip("|").split("|")]
            if all(re.match(r"^[-:]+$", c) for c in cols if c):
                i += 1; continue
            if current_table is None:
                ncols = len(cols)
                current_table = doc.add_table(rows=0, cols=ncols)
                current_table.style = "Table Grid"
                hrow = current_table.add_row()
                for j, h in enumerate(cols):
                    if j < len(hrow.cells):
                        hrow.cells[j].text = h
                        _set_cell_bg(hrow.cells[j], "dce6f0")
                        for run in hrow.cells[j].paragraphs[0].runs:
                            run.bold = True
            else:
                drow = current_table.add_row()
                for j, val in enumerate(cols):
                    if j < len(drow.cells):
                        drow.cells[j].text = val
            i += 1; continue
        else:
            current_table = None

        # Madde işareti
        if re.match(r"^[-*]\s+", line):
            text = re.sub(r"^\s*[-*]\s+", "", line)
            text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
            ghs_codes = _extract_ghs_codes(text)
            p = doc.add_paragraph(text, style="List Bullet")
            if ghs_codes:
                _add_ghs_images(ghs_codes)
            i += 1; continue

        # Numaralı liste
        if re.match(r"^\d+\.\s+", line):
            text = re.sub(r"^\d+\.\s+", "", line)
            text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
            p = doc.add_paragraph(text, style="List Number")
            i += 1; continue

        # Yatay çizgi
        if re.match(r"^---+$", line.strip()):
            doc.add_paragraph("")
            i += 1; continue

        # Boş satır
        if not line.strip():
            i += 1; continue

        # Normal paragraf — **bold** destekli + GHS görseli
        ghs_codes = _extract_ghs_codes(line)
        p = doc.add_paragraph()
        parts = re.split(r"(\*\*[^*]+\*\*)", line)
        for part in parts:
            if part.startswith("**") and part.endswith("**"):
                run = p.add_run(part[2:-2])
                run.bold = True
            else:
                p.add_run(part)
        if ghs_codes:
            _add_ghs_images(ghs_codes)
        i += 1

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _markdown_to_pdf(md_text: str) -> bytes:
    """Markdown metnini ReportLab ile PDF'e dönüştür."""
    import io, re, os
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, HRFlowable
    )

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=2.5*cm, rightMargin=2.5*cm,
        topMargin=2*cm, bottomMargin=2*cm,
    )

    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("H1", parent=styles["Heading1"], fontSize=13, textColor=colors.HexColor("#1a3a5c"), spaceAfter=6)
    # B1..B16 bölüm başlıkları — beyaz yazı, koyu mavi kutu
    h2 = ParagraphStyle(
        "H2", parent=styles["Heading2"], fontSize=11, spaceAfter=0, spaceBefore=8,
        textColor=colors.white, backColor=colors.HexColor("#1a3a5c"),
        leftPadding=6, rightPadding=6, topPadding=4, bottomPadding=4,
    )
    h3 = ParagraphStyle("H3", parent=styles["Heading3"], fontSize=10, spaceAfter=3, textColor=colors.HexColor("#1a3a5c"))
    body = ParagraphStyle("Body", parent=styles["Normal"], fontSize=9, leading=13, spaceAfter=3)
    bullet_st = ParagraphStyle("Bullet", parent=body, leftIndent=12, bulletIndent=0)

    # GHS pictogram klasörü
    _GHS_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "ghs_icons")

    def _sanitize(text: str) -> str:
        """Unicode karakterleri Helvetica'nın anlayacağı biçime dönüştür."""
        # Subscript rakamlar → ReportLab <sub> etiketi
        subs = str.maketrans("₀₁₂₃₄₅₆₇₈₉", "0123456789")
        # Önce subscript harfleri yakala, sonra normal rakama çevir
        text = re.sub(r"([A-Za-z])([₀-₉]+)", lambda m: m.group(1) + "<sub>" + m.group(2).translate(subs) + "</sub>", text)
        text = text.translate(subs)  # kalan tek rakam subscript'ler
        # Superscript rakamlar → <super> etiketi
        supers = {"⁰":"0","¹":"1","²":"2","³":"3","⁴":"4","⁵":"5","⁶":"6","⁷":"7","⁸":"8","⁹":"9"}
        for u, a in supers.items():
            text = text.replace(u, f"<super>{a}</super>")
        # Ok ve matematik sembolleri
        text = text.replace("→", "-&gt;").replace("←", "&lt;-").replace("↔", "&lt;-&gt;")
        text = text.replace("≥", "&gt;=").replace("≤", "&lt;=")
        text = text.replace("≠", "!=").replace("±", "+/-")
        # Bullet ve özel semboller
        text = text.replace("•", "-").replace("·", "-")
        text = text.replace("✓", "OK").replace("✗", "X").replace("✔", "OK")
        text = text.replace("™", "(TM)").replace("®", "(R)").replace("©", "(C)")
        # Tırnak işaretleri
        text = text.replace("“", '"').replace("”", '"')
        text = text.replace("‘", "'").replace("’", "'")
        # Tire türleri
        text = text.replace("–", "-").replace("—", "--")
        # Kalan 127+ ASCII dışı karakterleri kaldır (ama Türkçe harfleri koru — WinAnsi içinde)
        result = []
        for ch in text:
            cp = ord(ch)
            # WinAnsi (cp1252) kapsamı veya temel ASCII
            if cp < 128 or (160 <= cp <= 255):
                result.append(ch)
            elif ch in "ğüşıöçĞÜŞİÖÇ":  # Türkçe harfler — cp1252 içinde
                result.append(ch)
            else:
                result.append("?")
        return "".join(result)

    def _strip_bold(text: str) -> str:
        text = _sanitize(text)
        return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)

    def _extract_ghs_codes(text: str) -> list:
        """Metinden GHS01..GHS09 kodlarını çıkar."""
        return re.findall(r"GHS0[1-9]", text.upper())

    story = []
    lines = md_text.splitlines()
    i = 0

    while i < len(lines):
        line = lines[i]

        if line.startswith("### "):
            story.append(Paragraph(_strip_bold(line[4:].strip()), h3))
            i += 1; continue
        if line.startswith("## "):
            story.append(Spacer(1, 8))
            story.append(Paragraph(_strip_bold(line[3:].strip()), h2))
            story.append(Spacer(1, 4))
            i += 1; continue
        if line.startswith("# "):
            story.append(Spacer(1, 6))
            story.append(Paragraph(_strip_bold(line[2:].strip()), h1))
            i += 1; continue

        # Tablo
        if line.startswith("|"):
            tbl_rows = []
            while i < len(lines) and lines[i].startswith("|"):
                cols = [c.strip() for c in lines[i].strip("|").split("|")]
                if not all(re.match(r"^[-:]+$", c) for c in cols if c):
                    tbl_rows.append(cols)
                i += 1
            if tbl_rows:
                page_w = A4[0] - 5*cm
                ncols  = max(len(r) for r in tbl_rows)
                col_w  = [page_w / ncols] * ncols
                pdf_rows = [[Paragraph(_strip_bold(c), body) for c in r] for r in tbl_rows]
                t = Table(pdf_rows, colWidths=col_w, repeatRows=1)
                t.setStyle(TableStyle([
                    ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#dce6f0")),
                    ("FONTNAME",   (0,0), (-1,0), "Helvetica-Bold"),
                    ("FONTSIZE",   (0,0), (-1,-1), 8),
                    ("GRID",       (0,0), (-1,-1), 0.4, colors.grey),
                    ("VALIGN",     (0,0), (-1,-1), "TOP"),
                    ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#f5f8fb")]),
                ]))
                story.append(t)
                story.append(Spacer(1, 4))
            continue

        # Bullet satır
        if re.match(r"^[-*]\s+", line):
            text = re.sub(r"^\s*[-*]\s+", "", line)
            # GHS piktogram satırı mı?
            ghs_codes = _extract_ghs_codes(text)
            if ghs_codes:
                imgs = []
                for code in ghs_codes:
                    img_path = os.path.join(_GHS_DIR, f"{code}.png")
                    if os.path.exists(img_path):
                        imgs.append(Image(img_path, width=1.2*cm, height=1.2*cm))
                if imgs:
                    row = [[img] for img in imgs]
                    # Yan yana diz
                    tbl_data = [imgs]
                    pic_tbl = Table(tbl_data, colWidths=[1.4*cm]*len(imgs))
                    pic_tbl.setStyle(TableStyle([
                        ("ALIGN", (0,0), (-1,-1), "CENTER"),
                        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
                        ("LEFTPADDING", (0,0), (-1,-1), 2),
                        ("RIGHTPADDING", (0,0), (-1,-1), 2),
                    ]))
                    story.append(pic_tbl)
                    story.append(Spacer(1, 2))
                else:
                    story.append(Paragraph(f"- {_strip_bold(text)}", bullet_st))
            else:
                story.append(Paragraph(f"- {_strip_bold(text)}", bullet_st))
            i += 1; continue

        if re.match(r"^---+$", line.strip()):
            story.append(Spacer(1, 6))
            i += 1; continue

        if not line.strip():
            i += 1; continue

        # Normal satır — GHS kodu geçiyorsa piktogram ekle
        ghs_codes = _extract_ghs_codes(line)
        if ghs_codes:
            story.append(Paragraph(_strip_bold(line), body))
            imgs = []
            for code in ghs_codes:
                img_path = os.path.join(_GHS_DIR, f"{code}.png")
                if os.path.exists(img_path):
                    imgs.append(Image(img_path, width=1.2*cm, height=1.2*cm))
            if imgs:
                tbl_data = [imgs]
                pic_tbl = Table(tbl_data, colWidths=[1.4*cm]*len(imgs))
                pic_tbl.setStyle(TableStyle([
                    ("ALIGN", (0,0), (-1,-1), "CENTER"),
                    ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
                    ("LEFTPADDING", (0,0), (-1,-1), 2),
                    ("RIGHTPADDING", (0,0), (-1,-1), 2),
                ]))
                story.append(pic_tbl)
                story.append(Spacer(1, 2))
        else:
            story.append(Paragraph(_strip_bold(line), body))
        i += 1

    doc.build(story)
    return buf.getvalue()
