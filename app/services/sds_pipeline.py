"""
Tek sınıflandırma hattı — sağ panel (/api/v1/sds/calculate) ve PDF (/api/v1/sds/pdf)
ikisi de bu modülü çağırır. Önceden iki uç nokta ayrı ayrı yazılmış birleştirme
kuralları kullanıyordu; panel ile PDF farklı H kodu / P kodu / taşıma gösterebiliyordu.

Girdi (normalize):
    components, form, form_sub, usage, lang, user_fp, user_bp, fp_status,
    mixture_ph, test_data, h314_removed

Çıktı: h_codes (etiket), all_h_codes (Bölüm 2.1), signal, pictograms, clp_passed,
       euh, p_codes, transport, ppe, phys_res, stot_res, eco_obj, eco_panel,
       components (tazelenmiş), ate_details, warnings, pending_decisions
"""
import asyncio

from app.services.clp_service import is_danger
from app.services.p_code_service import (
    assign_p_codes, select_label_p_codes, classify_sds_p_codes,
)

ECO_H_CODES   = {'H400', 'H410', 'H411', 'H412', 'H413'}
FLAM_LIQ_H    = {'H224', 'H225', 'H226'}
ACUTE_TOX_H   = {'H300', 'H301', 'H302', 'H310', 'H311', 'H312', 'H330', 'H331', 'H332'}
SKIN_EYE_H    = {'H314', 'H315', 'H318', 'H319'}
H314_COVERED  = {'H314', 'H318', 'H315', 'H319'}
# Yalnızca fiziksel motor / test verisi üretebilir (bileşen kesimiyle verilmez)
MANUAL_PHYS_H = {
    'H240', 'H241', 'H242',          # Organik peroksit / öz-reaktif
    'H250', 'H251', 'H252',          # Pirofor / kendiliğinden ısınan
    'H260', 'H261',                  # Su-reaktif
    'H270', 'H271', 'H272',          # Oksitleyici gaz/katı/sıvı
    'H290',                          # Metal aşındırıcı
}
DOMINANCE_MAP = {
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


def norm_sub(h) -> str:
    """H360x/H361x alt kodlarını kanonik büyük harfe normalize et (H361d→H361D, H360Df→H360FD)."""
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


def _h4(h) -> str:
    return str(h or '').replace('*', '').strip()[:4]


# ── Bileşen verisini yetkili kaynaktan tazele ────────────────────────────────
async def refresh_components(components: list, form: str) -> list:
    """Bileşen tehlike verisini yerel DB'den (SEA Ek-6 / Annex VI / custom) yeniden al;
    DB'de yoksa ECHA. Ön yüzde kalmış eski/elle değiştirilmiş kodlar sınıflandırmaya girmez."""
    from app.services.substance_lookup import (
        lookup_substance as _lu_sub,
        save_custom_substance as _save_custom,
        _load_custom as _custom_db,
    )
    from app.services.echa_service import _dedupe_h_codes as _dedup, lookup_echa_api as _lu_echa
    from app.services.reach_db import get_reg_no as _reg_no
    from app.services.substance_lookup import ensure_echa_supplement as _ensure_echa

    def _mark(c: dict, cas: str, priority, sea_ek6=False, annex_vi=False) -> None:
        """Kaynak önceliği (1 SEA Ek-6, 2 Annex VI, ≥3 resmî olmayan) ve REACH kayıt no'su —
        akut toksisite hesabı bunlara bakarak bileşeni "veri var" ya da "bilinmeyen" sayar.
        Önceden bu alanlar hesaplamaya taşınmıyordu; resmî kaynaklı maddeler (örn. sitrik asit)
        "bilinmeyen akut toksisite" sayılıyordu."""
        if priority is not None:
            c['source_priority'] = priority
        c['sea_ek6'] = bool(sea_ek6)
        c['annex_vi'] = bool(annex_vi)
        if not (c.get('reach_no') or c.get('reach')):
            try:
                c['reach_no'] = _reg_no(cas) or ''
            except Exception:
                pass

    def _apply_m_ate(c: dict, comp: dict, src: dict) -> None:
        """M faktörü ve ATE: kullanıcının formda girdiği değer önce gelir (M > 1 veya ATE girilmiş);
        yoksa kaynak değeri (SEA Ek-6 / Annex VI resmî; liste dışı maddelerde ECHA bildirimleri).
        Önceden veritabanı değeri kullanıcının girdiğini her durumda eziyordu."""
        def _f(v):
            try:
                return float(v)
            except (TypeError, ValueError):
                return 0.0
        user_m = comp.get('m_factors') or {}
        if not any(_f(v) > 1 for v in user_m.values()):
            c['m_factors'] = src.get('m_factors') or {}
        user_ate = comp.get('ate') or {}
        if not any(_f(v) > 0 for v in user_ate.values()):
            c['ate'] = src.get('ate') or {}

    async def _one(comp: dict) -> dict:
        cas = (comp.get('cas_no') or comp.get('cas') or '').strip()
        if not cas:
            return comp
        try:
            # Ek-6 maddesinde Ek-6 dışı sınıfların ECHA takviyesi hesaptan önce tamamlanır —
            # önceden arka planda çekildiği için ilk hesapta eksik, sonrakinde tam çıkıyordu
            await _ensure_echa(cas)
            fresh = _lu_sub(cas, form=form)
            if fresh is not None:
                # DB'de kayıt var — hazards boşsa "sınıflandırılmamış" (su, glikoz vb.)
                c = dict(comp)
                _mark(c, cas, fresh.get('source_priority'), fresh.get('sea_ek6'), fresh.get('annex_vi'))
                if fresh.get('hazards'):
                    raw = {'h_codes':        [h['h_code'] for h in fresh['hazards']],
                           'hazard_classes': [h['h_class'] for h in fresh['hazards']]}
                    _dedup(raw)
                    # SEA Md.6(1)(c): Ek-6'da listelenmeyen, ECHA bildirimlerinden eklenen sınıflar
                    # işaretlenir; kullanıcının kaldırdıkları (echa_removed) hesaba katılmaz.
                    # Ek-6'nın kendi sınıfları bağlayıcıdır — kaldırma listesi onlara uygulanmaz.
                    supp = {_h4(h['h_code']) for h in fresh['hazards'] if h.get('_echa_supplement')}
                    removed = {_h4(x) for x in (comp.get('echa_removed') or [])} & supp
                    c['hazards'] = []
                    c['ek6_supplements'] = []
                    for cls, code in zip(raw['hazard_classes'], raw['h_codes']):
                        if _h4(code) in supp:
                            c['ek6_supplements'].append({'h_code': _h4(code), 'h_class': cls,
                                                         'removed': _h4(code) in removed})
                            if _h4(code) in removed:
                                continue
                            c['hazards'].append({'h_class': cls, 'h_code': code, 'echa_supplement': True})
                        else:
                            c['hazards'].append({'h_class': cls, 'h_code': code})
                    _apply_m_ate(c, comp, fresh)
                else:
                    c['hazards'] = []
                if fresh.get('suppl_hazards'):
                    c['suppl_hazards'] = fresh['suppl_hazards']
                    c['euh_limits'] = fresh.get('euh_limits', [])
                return c
            echa = await _lu_echa(cas)
            if echa and echa.get('h_codes'):
                if cas not in _custom_db():
                    try:
                        _save_custom(cas, {
                            'name': echa.get('name', ''), 'ec_no': echa.get('ec_no', ''),
                            'signal': echa.get('signal', ''), 'pictograms': echa.get('pictograms', []),
                            'hazards': [{'h_class': c2, 'h_code': h2} for c2, h2 in
                                        zip(echa.get('hazard_classes', []), echa.get('h_codes', []))],
                            'm_factors': echa.get('m_factors', {}), 'index_no': '', 'atp': 'pubchem-auto',
                        })
                    except Exception:
                        pass
                c = dict(comp)
                c['hazards'] = [{'h_class': cls, 'h_code': code} for cls, code in
                                zip(echa.get('hazard_classes', []), echa.get('h_codes', []))]
                _mark(c, cas, 5)
                _apply_m_ate(c, comp, echa)
                return c
        except Exception:
            pass
        return comp

    return list(await asyncio.gather(*[_one(c) for c in components]))


# ── Etikette adı yazılması zorunlu bileşenler (SEA/CLP Md. 18(3)(b)) ───────────
# Karışımın şu sınıflandırmalarına katkı yapan maddeler: akut toksisite, cilt aşındırma /
# ciddi göz hasarı, CMR, solunum/cilt hassaslaştırma, STOT, aspirasyon.
# Karışım kodu → katkı sayılan bileşen kodları
_LABEL_CONTRIB = {
    'H300': {'H300', 'H301', 'H302'}, 'H301': {'H300', 'H301', 'H302'}, 'H302': {'H300', 'H301', 'H302'},
    'H310': {'H310', 'H311', 'H312'}, 'H311': {'H310', 'H311', 'H312'}, 'H312': {'H310', 'H311', 'H312'},
    'H330': {'H330', 'H331', 'H332'}, 'H331': {'H330', 'H331', 'H332'}, 'H332': {'H330', 'H331', 'H332'},
    'H314': {'H314'}, 'H318': {'H314', 'H318'},
    'H340': {'H340', 'H341'}, 'H341': {'H340', 'H341'},
    'H350': {'H350', 'H351'}, 'H351': {'H350', 'H351'},
    'H360': {'H360', 'H361', 'H362'}, 'H361': {'H360', 'H361', 'H362'}, 'H362': {'H360', 'H361', 'H362'},
    'H334': {'H334'}, 'H317': {'H317'},
    'H370': {'H370', 'H371'}, 'H371': {'H370', 'H371'},
    'H372': {'H372', 'H373'}, 'H373': {'H372', 'H373'},
    'H335': {'H335'}, 'H336': {'H336'}, 'H304': {'H304'},
}
# Bileşenin dikkate alınma eşiği (%) — SEA Ek-1 Tablo 1.1 genel eşikleri (yüksek önem → 0,1)
_LABEL_MIN_CONC = {'H300': 0.1, 'H301': 0.1, 'H310': 0.1, 'H311': 0.1, 'H330': 0.1, 'H331': 0.1,
                   'H340': 0.1, 'H350': 0.1, 'H360': 0.1, 'H362': 0.1, 'H334': 0.1, 'H317': 0.1}
# Önem sırası — 4'ten fazla bileşen varsa en önemlileri seçilir
_LABEL_RANK = {'H340': 10, 'H350': 10, 'H360': 10, 'H300': 9, 'H310': 9, 'H330': 9, 'H334': 8,
               'H301': 7, 'H311': 7, 'H331': 7, 'H370': 7, 'H372': 7, 'H314': 6, 'H318': 6,
               'H341': 5, 'H351': 5, 'H361': 5, 'H362': 5, 'H317': 5, 'H304': 4, 'H371': 4,
               'H373': 4, 'H302': 3, 'H312': 3, 'H332': 3, 'H335': 2, 'H336': 2}


def label_components(comps: list, mixture_h: list) -> list:
    """Etikette adı yazılması zorunlu bileşenler (ad listesi, önem sırasıyla, en fazla 4 —
    ölümcül/CMR 1 gibi en ağır olanlar sınırı aşsa da yazılır)."""
    mix = {_h4(h) for h in mixture_h}
    wanted = set()
    for h in mix:
        wanted |= _LABEL_CONTRIB.get(h, set())
    if not wanted:
        return []
    found = []
    for c in comps:
        from app.services.substance_lookup import clean_tr_name as _clean_tr
        name = _clean_tr((c.get('name_tr') or c.get('name') or c.get('cas') or '').strip())
        if not name or 'mevzuata' in name.lower():
            continue
        conc = float(c.get('concMax') or c.get('conc') or 0)
        codes = {_h4(h.get('h_code')) for h in (c.get('hazards') or [])} & wanted
        codes = {h for h in codes if conc >= _LABEL_MIN_CONC.get(h, 1.0)}
        if codes:
            found.append((max(_LABEL_RANK.get(h, 1) for h in codes), conc, name))
    found.sort(key=lambda x: (-x[0], -x[1]))
    out = [n for i, (rank, _, n) in enumerate(found) if i < 4 or rank >= 9]
    return list(dict.fromkeys(out))


def _normalize_conc(comps: list) -> None:
    for c in comps:
        if 'conc' not in c and 'concentration' in c:
            c['conc'] = c['concentration']
        if 'concMax' not in c:
            c['concMax'] = c.get('conc_max') or c.get('conc') or c.get('concentration') or 0


# ── Ana hat ───────────────────────────────────────────────────────────────────
async def classify(inp: dict) -> dict:
    from app.services.clp_service import (
        classify_mixture_clp, calculate_ate_health_h_codes,
    )
    from app.services.physical_engine import calculate as phys_calc
    from app.services.stot_engine import calculate as stot_calc
    from app.services.transport_engine import (
        classify as transport_calc, build_transport_components,
    )
    from app.services.ppe_engine import select as ppe_calc
    from app.services.codes_i18n import correct_hclass
    from app.services.euh_service import check_euh
    from app.services.ecological_service import calculate_ecological
    from app.services.ghs_pictogram import get_ghs_codes

    form      = inp.get('form') or 'liquid'
    form_sub  = inp.get('form_sub') or ''
    usage     = inp.get('usage') or 'industrial'
    lang      = inp.get('lang') or 'TR'
    test_data = dict(inp.get('test_data') or {})
    mixture_ph = inp.get('mixture_ph') or None

    comps = [dict(c) for c in (inp.get('components') or [])]
    _normalize_conc(comps)
    comps = await refresh_components(comps, form)

    # ATE sağlık tehlikeleri (classify_mixture_clp Acute Tox. atlar)
    try:
        ate_h, ate_details = calculate_ate_health_h_codes(comps, form=form)
    except Exception as e:
        print(f'[ATE ERROR] {e}')
        ate_h, ate_details = [], {}

    tr_components = build_transport_components(comps)

    clp_res  = classify_mixture_clp(comps, mixture_ph=mixture_ph, mixture_form=form)
    # "Bileşen geçişkenliğine dayanır — test önerilir" uyarısı yalnızca-test sınıfları için
    # geçersiz: bu sınıflar artık kullanıcının test kararıyla verilir (Bölüm 16 notu ayrı).
    clp_res['warnings'] = [
        w for w in (clp_res.get('warnings') or [])
        if not (isinstance(w, dict) and str(w.get('code', '')).startswith('PHYS_NO_TEST_BASIS_')
                and _h4(w.get('h_code')) in MANUAL_PHYS_H)
    ]
    phys_res = phys_calc(comps, form=form, user_fp=inp.get('user_fp'), user_bp=inp.get('user_bp'),
                         test_data=test_data, form_sub=form_sub, fp_status=inp.get('fp_status') or '')
    stot_res = stot_calc(comps)

    eco_comps = [{
        'cas': c.get('cas') or c.get('cas_no') or '', 'name': c.get('name', ''),
        'name_tr': c.get('name_tr', ''),
        'conc': float(c.get('conc', c.get('concentration', 0)) or 0),
        'worst_case_conc': float(c.get('concMax') or c.get('conc', c.get('concentration', 0)) or 0),
        'hazards': c.get('hazards', []), 'm_factors': c.get('m_factors', {}),
        'ec50_algae': c.get('ec50_algae'), 'ec50_fish': c.get('ec50_fish'),
        'ec50_daphnia': c.get('ec50_daphnia'), 'ec50_noec': c.get('ec50_noec'),
    } for c in comps]
    try:
        eco_obj = calculate_ecological(eco_comps)
    except Exception as e:
        print(f'[ECO ERROR] {e}')
        eco_obj = None

    # ── Bölüm 2.1 satırları (clp_passed) ─────────────────────────────────────
    cp, seen = [], set()
    for p in clp_res.get('passed', []):
        hc = norm_sub(p.get('h_code') or '')
        if hc[:4] not in ('H360', 'H361'):
            hc = hc[:4]
        # Sucul sınıf yalnızca ecological_service'ten; alevlenir sıvı ve yalnızca-test sınıfları
        # (H290, H27x…) yalnızca physical_engine'den — CLP kesim satırı ("bileşen varlığı")
        # kullanıcının test kararının gerekçesini ezmesin
        # Gaz ürününde basınçlı gaz satırı (H280/H281) yalnızca fiziksel motordan gelir — alt
        # kategori (sıkıştırılmış/sıvılaştırılmış…) SEA Ek-1 Tablo 2.5.1 gereği orada belirlenir
        if (hc and hc not in seen and hc not in ECO_H_CODES and hc not in FLAM_LIQ_H
                and hc not in MANUAL_PHYS_H
                and not (form == 'gas' and hc in ('H280', 'H281'))):
            seen.add(hc)
            cp.append({
                'h_code': hc,
                'h_class': correct_hclass(hc, p.get('h_class', '')) or p.get('h_class', ''),
                'reason': p.get('reason', ''),
                'cutoff_used': p.get('cutoff_used', ''),
                'cutoff_source': p.get('cutoff_source'),
                'cutoff_value': p.get('cutoff_value'),
                'note_flag': p.get('note_flag'), 'note': p.get('note'), 'repro_sub': p.get('repro_sub'),
            })
    auth_flam_h = next((r.get('h') for r in phys_res.get('results', []) if r.get('type') == 'flam_liq'), None)
    for r in phys_res.get('results', []):
        hc = _h4(r.get('h') or r.get('h_code'))
        if hc and hc not in seen:
            seen.add(hc)
            cp.append({'h_code': hc, 'h_class': r.get('h_class', ''),
                       'reason': r.get('source') or 'Fiziksel tehlike motoru',
                       'cutoff_used': r.get('cutoff_used') or '—'})
    for r in stot_res.get('results', []):
        hc = _h4(r.get('h_code') or r.get('h'))
        if hc and hc not in seen:
            seen.add(hc)
            cp.append({'h_code': hc, 'h_class': r.get('h_class', ''),
                       'reason': r.get('reason', 'STOT RE toplamsal'), 'cutoff_used': '—'})
    aq = getattr(eco_obj, 'aquatic', None) if eco_obj else None
    if aq and aq.h_code and aq.h_code not in seen:
        seen.add(aq.h_code)
        cp.append({'h_code': aq.h_code, 'h_class': aq.h_class,
                   'reason': aq.formula or 'Sucul ekoloji', 'cutoff_used': '—'})
    present = {e['h_code'] for e in cp}
    dominated = set()
    for dom, subs in DOMINANCE_MAP.items():
        if dom in present:
            dominated.update(subs)
    cp = [e for e in cp if e['h_code'] not in dominated]

    # ── Taşıma ────────────────────────────────────────────────────────────────
    phys_h = [(r.get('h') or r.get('h_code') or '') for r in phys_res.get('results', [])]
    visc = test_data.get('viscosity')
    try:
        visc = float(visc) if visc not in (None, '') else None
    except (TypeError, ValueError):
        visc = None
    if visc is None:
        visc = ((phys_res.get('theo_props') or {}).get('viscosity') or {}).get('value')
    eco_h_merge = []
    if aq and aq.h_code:
        eco_h_merge.append(aq.h_code)
    aqa = getattr(eco_obj, 'aquatic_acute', None) if eco_obj else None
    if aqa and getattr(aqa, 'h_code', None) == 'H400' and 'H400' not in eco_h_merge:
        eco_h_merge.append('H400')
    final_cls_h = list(dict.fromkeys(
        [h for h in clp_res.get('h_codes', [])
         if h not in FLAM_LIQ_H and h not in MANUAL_PHYS_H]      # bu sınıflar yalnızca fiziksel motordan
        + eco_h_merge + phys_h
        # Akut toksisite (ATEmix) — classify_mixture_clp akut toksisiteyi atladığından taşıma
        # motoru zehirli karışımları görmüyordu (Sınıf 6.1 / gazda 2.3 verilemiyordu)
        + [e['h_code'] for e in (ate_h or [])]))
    transport = transport_calc(h_codes=final_cls_h, form=form, phys_h_codes=phys_h,
                               viscosity=float(visc) if visc is not None else None,
                               components=tr_components,
                               acute_tox=ate_h or [],
                               mixture_ph=mixture_ph,
                               gas_type=(test_data.get('gas_type')
                                         or ('refrigerated' if test_data.get('cryo_gas') else None)))

    # ── Etiket (h_codes) ve Bölüm 2.1 (all_h_codes) ─────────────────────────
    h_codes = list(dict.fromkeys(norm_sub(h) for h in clp_res.get('h_codes', [])))
    all_h = list(h_codes)
    if inp.get('h314_removed'):
        h_codes = [h for h in h_codes if h not in H314_COVERED]
        all_h   = [h for h in all_h if h not in H314_COVERED]

    # 1. Alevlenir sıvı — physical_engine yetkili; H224/H225/H226 yalnızca sıvı/pasta ürüne
    #    verilir. Katı/toz/gaz/aerosolde bileşen kesiminden gelen alevlenir SIVI kodu silinir
    #    (bu hallerin yanıcılığı H228 / H220-H221 / H222-H223 ile değerlendirilir).
    add = [auth_flam_h] if (auth_flam_h and form in ('liquid', 'paste')) else []
    h_codes = [h for h in h_codes if h not in FLAM_LIQ_H] + add
    all_h   = [h for h in all_h if h not in FLAM_LIQ_H] + add

    # 1b. Diğer fiziksel motor sonuçları (aerosol, oksitleyici, test verisi…)
    for r in phys_res.get('results', []):
        hc = _h4(r.get('h') or r.get('h_code'))
        if hc and hc not in FLAM_LIQ_H:
            if hc not in h_codes: h_codes.append(hc)
            if hc not in all_h:   all_h.append(hc)

    # 2. Sucul — ecological_service tek yetkili kaynak
    if aq and aq.h_code:
        h400_also = aq.h_code != 'H400' and aqa is not None and getattr(aqa, 'h_code', None) == 'H400'
        h_codes = [h for h in h_codes if h not in ECO_H_CODES] + [aq.h_code]
        all_h   = [h for h in all_h if h not in ECO_H_CODES] + [aq.h_code] + (['H400'] if h400_also else [])
        if h400_also and not any(e['h_code'] == 'H400' for e in cp):
            cp.append({'h_code': 'H400', 'h_class': 'Aquatic Acute 1',
                       'reason': 'CLP §4.1.3.5.5: H410 bileşeni Sucul Akut 1 (H400) de üretir',
                       'cutoff_used': '—'})
    else:
        h_codes = [h for h in h_codes if h not in ECO_H_CODES]
        all_h   = [h for h in all_h if h not in ECO_H_CODES]

    # 3. H420 — ozon tabakası
    s12 = getattr(eco_obj, 'sds_section_12', None) or {} if eco_obj else {}
    if s12.get('H420'):
        if 'H420' not in h_codes: h_codes.append('H420')
        if 'H420' not in all_h:   all_h.append('H420')

    # 4. Cilt/göz — classify_mixture_clp sonucu (pH kuralı dahil)
    clp_skin = {h for h in clp_res.get('h_codes', []) if h in SKIN_EYE_H}
    if clp_skin and not inp.get('h314_removed'):
        h_codes = [h for h in h_codes if h not in SKIN_EYE_H] + sorted(clp_skin)
        extra_skin = set(clp_skin) | {p.get('h_code') for p in clp_res.get('passed', [])
                                      if p.get('h_code') in SKIN_EYE_H}
        all_h = list(all_h) + [h for h in sorted(extra_skin) if h not in set(all_h)]

    # 5. H314 → H318 (sınıflandırmada göster, etikette gizle)
    if 'H314' in h_codes:
        if 'H318' not in all_h:
            all_h.append('H318')
        if not any(e.get('h_code') == 'H318' for e in cp):
            cp.append({'h_code': 'H318', 'h_class': 'Eye Dam. 1',
                       'reason': 'H314 varlığında otomatik (CLP §3.3.1.4)', 'cutoff_used': '—'})
        h_codes = [h for h in h_codes if h != 'H318']

    # 6. H304 — yalnızca sıvı/pasta
    if form not in ('liquid', 'paste'):
        h_codes = [h for h in h_codes if h != 'H304']
        all_h   = [h for h in all_h if h != 'H304']
        cp      = [p for p in cp if p.get('h_code') != 'H304']

    # 7. Akut toksisite — ATEmix sonucu kesin
    if ate_h:
        ate_codes = [e['h_code'] for e in ate_h]
        h_codes = [h for h in h_codes if h not in ACUTE_TOX_H] + ate_codes
        all_h = list(all_h) + [h for h in ate_codes if h not in set(all_h)]
        ate_set = set(ate_codes)
        cp = [e for e in cp if e.get('h_code') not in ate_set]
        for e in ate_h:
            cp.append({'h_code': e['h_code'], 'h_class': e['h_class'],
                       'reason': e['reason'], 'cutoff_used': e['cutoff_used']})

    # 8. STOT RE toplamsal (H372/H373) — önce PDF etiketine girmiyordu
    for hc in stot_res.get('h_codes', []):
        hc = _h4(hc)
        if not hc:
            continue
        if hc == 'H373' and 'H372' in h_codes:
            continue
        if hc not in h_codes: h_codes.append(hc)
        if hc not in all_h:   all_h.append(hc)

    # 9. Yalnızca fiziksel motorun / test sonucunun üretebileceği kodlar (H290, H27x, H24x…).
    #    Karışımda bu sınıflar bileşen oranından hesaplanmaz (SEA Ek-1 §2.x — test gerekir);
    #    CLP kesim tablosundan gelenler silinir.
    valid_phys = {_h4(h) for h in phys_h if h}
    h_codes = [h for h in h_codes if h not in MANUAL_PHYS_H or h in valid_phys]
    all_h   = [h for h in all_h if h not in MANUAL_PHYS_H or h in valid_phys]
    cp      = [e for e in cp if e['h_code'] not in MANUAL_PHYS_H or e['h_code'] in valid_phys]
    # (H290 bileşeni varsa physical_engine "Karar gerekli" sorusu üretir)

    h_codes = list(dict.fromkeys(h for h in h_codes if h))
    all_h   = list(dict.fromkeys(h for h in all_h if h))

    # Taşıma / eko tutarlılığı
    inv_eco = {h for h in all_h if h in {'H400', 'H410', 'H411'}}
    if inv_eco and transport and transport.get('not_regulated'):
        raise RuntimeError(f'Transport/eco pipeline tutarsızlığı: {inv_eco} sınıflandırmada '
                           'var ama taşıma not_regulated=True döndürdü.')

    # ── Uyarı kelimesi, EUH, P kodları, piktogram, KKD ───────────────────────
    clean = {h.split()[0] for h in h_codes}
    signal = ('Danger' if is_danger(clean, clp_res.get('passed', [])) else 'Warning') if clean else ''

    euh = check_euh(comps, mixture_form=form, form_sub=form_sub)
    if set(all_h) & {'H314', 'H315'}:   # SEA Ek-2 1.2.4: EUH066 cilt tahrişi yoksa
        euh['euh_codes']   = [c for c in euh.get('euh_codes', []) if c != 'EUH066']
        euh['euh_details'] = [d for d in euh.get('euh_details', []) if d.get('code') != 'EUH066']
    euh_codes = euh.get('euh_codes', [])

    p_result = assign_p_codes(h_codes, signal, mixture_form=form, usage=usage)
    # P260/P261: "Tozunu/…/spreyini" — tedarikçinin seçeceği kısım fiziksel hale göre (panel ve PDF aynı)
    from app.services.sds_reg_sections import _select_inhal
    from app.services.sds_reg_sections import p280_text as _p280
    for _d in p_result.get('p_details') or []:
        if _d.get('code') == 'P280':
            _d['text'] = _p280(list(all_h) + list(h_codes), 'TR' if lang == 'TR' else 'EN')
        elif _d.get('text'):
            _d['text'] = _select_inhal(_d['text'], form, 'TR' if lang == 'TR' else 'EN')
    p_result['label'] = select_label_p_codes(p_result['p_codes'], 6, h_codes=h_codes, euh_codes=euh_codes,
                                             usage=usage, form=form)
    p_result['sds'] = classify_sds_p_codes(p_result['p_codes'], usage=usage, h_codes=h_codes, form=form,
                                           label=p_result['label']['selected'])
    try:
        ppe = ppe_calc([h for h in h_codes if h], lang=lang, form=form)
    except Exception as e:
        print(f'[PPE ERROR] {e}')
        ppe = {}
    # Eldiven — EN ISO 374-1 sınıf harfi/tip/minimum süre + malzeme önerisi (kullanıcı seçimi varsa o)
    glove = {'applies': False}
    try:
        from app.services.glove_service import select as _glove_select
        glove = _glove_select(comps, list(all_h) + list(h_codes), lang=lang,
                              material=inp.get('glove_material'), thickness=inp.get('glove_thickness'))
        if glove.get('applies') and isinstance(ppe, dict):
            ppe['hands'] = [{'ppe': glove['text'], 'level': glove['level']}]
    except Exception as e:
        print(f'[GLOVE ERROR] {e}')

    eco_panel = {
        'h_codes': [h for h in h_codes if h in ECO_H_CODES or h == 'H420'],
        'aquatic': ({'h': aq.h_code, 'cls': aq.h_class, 'formula': aq.formula,
                     'note': getattr(aq, 'note', ''),
                     'm_factor_warnings': getattr(aq, 'm_factor_warnings', None) or []}
                    if aq else None),
    }

    # ── Ek-6 dışı sınıflar (SEA Md.6(1)(c)) — panel kutusu ve Bölüm 16 notu ─────
    ek6_supp = [{'cas': c.get('cas') or c.get('cas_no') or '',
                 'name': c.get('name_tr') or c.get('name') or '', **e}
                for c in comps for e in (c.get('ek6_supplements') or [])]
    cls_notes = list(phys_res.get('classification_notes', []))
    if ek6_supp:
        _used = [e for e in ek6_supp if not e['removed']]
        _rem = [e for e in ek6_supp if e['removed']]
        _fmt = lambda lst: '; '.join(dict.fromkeys(f"{e['name'] or e['cas']} — {e['h_code']}" for e in lst))
        tr_txt = ('Ek-6 dışı sınıflar: SEA Ek-6’da yer alan maddelerin listede bulunmayan tehlike '
                  'sınıfları SEA Md.6(1)(c) gereği ECHA C&L bildirimlerine göre değerlendirilmiştir'
                  + (f' ({_fmt(_used)})' if _used else '') + '.'
                  + (f' Kullanıcı kararıyla dikkate alınmayanlar: {_fmt(_rem)}.' if _rem else ''))
        en_txt = ('Classes not listed in Annex VI: hazard classes not covered by the harmonised entry were '
                  'assessed from ECHA C&L notifications (CLP Art. 4(3))'
                  + (f' ({_fmt(_used)})' if _used else '') + '.'
                  + (f' Not applied by user decision: {_fmt(_rem)}.' if _rem else ''))
        cls_notes.append({'TR': tr_txt, 'EN': en_txt})

    return {
        'components':  comps,
        'ek6_supplements': ek6_supp,
        'h_codes':     h_codes,
        'all_h_codes': all_h,
        'signal':      signal,
        'pictograms':  get_ghs_codes(h_codes),
        'clp_passed':  cp,
        'euh':         euh,
        'p_codes':     p_result,
        'transport':   transport,
        'ppe':         ppe,
        'glove':       glove,
        'phys_res':    phys_res,
        'stot_res':    stot_res,
        'clp_res':     clp_res,
        'eco_obj':     eco_obj if eco_obj is not None else {'sds_section_12': {}},
        'eco_panel':   eco_panel,
        'ate_details': {**(clp_res.get('ate_mix_details') or {}), **(ate_details or {})},
        'warnings':    (phys_res.get('warnings', []) + stot_res.get('warnings', [])
                        + clp_res.get('warnings', [])),
        'pending_decisions': phys_res.get('pending_decisions', []),
        'classification_notes': cls_notes,
        'label_components': label_components(comps, all_h),
    }


def summary(core: dict) -> dict:
    """Panel ile PDF'i karşılaştırmak için kısa özet (güvenlik ağı)."""
    tr = core.get('transport') or {}
    road = tr.get('road') or {}
    return {
        'h_codes':    sorted(core.get('h_codes', [])),
        'signal':     core.get('signal', ''),
        'pictograms': sorted(core.get('pictograms', [])),
        'euh':        sorted((core.get('euh') or {}).get('euh_codes', [])),
        'p_label':    list(((core.get('p_codes') or {}).get('label') or {}).get('selected', [])),
        'label_components': list(core.get('label_components', [])),
        'un':         None if tr.get('not_regulated') else road.get('un'),
        'pg':         None if tr.get('not_regulated') else road.get('pg'),
    }
