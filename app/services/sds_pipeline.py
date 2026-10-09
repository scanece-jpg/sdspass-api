"""
Tek sınıflandırma hattı — sağ panel (/api/v1/sds/calculate) ve PDF (/api/v1/sds/pdf)
ikisi de bu modülü çağırır. Önceden iki uç nokta ayrı ayrı yazılmış birleştirme
kuralları kullanıyordu; panel ile PDF farklı H kodu / P kodu / taşıma gösterebiliyordu.

Girdi (normalize):
    components, form, form_sub, usage, lang, user_fp, user_bp, fp_status,
    mixture_ph, additivity_na, test_data, h314_removed

Çıktı: h_codes (etiket), all_h_codes (Bölüm 2.1), signal, pictograms, clp_passed,
       euh, p_codes, transport, ppe, phys_res, stot_res, eco_obj, eco_panel,
       components (tazelenmiş), ate_details, warnings, pending_decisions
"""
import asyncio

from app.services.clp_service import signal_word_for
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
    'H220', 'H221',                  # Alevlenir gaz — karışımda test/ISO 10156 (SEA Ek-1 2.2); bileşen varlığı yetmez
    'H232',                          # Pirofor gaz — TR SEA'da yok (Tablo 2.2.1 yalnız Kat.1/2); hiçbir yoldan verilmez
}
DOMINANCE_MAP = {
    'H225': ['H226'], 'H224': ['H225', 'H226'], 'H220': ['H221'],
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
    """H360x/H361x alt kodlarını SEA Ek-3 resmî yazımına çevirir (H361D → H361d; H360Df korunur).
    Önceden büyük harfe çevriliyordu — H360Df → H360FD anlam değiştiriyordu."""
    from app.services.clp_service import canon_repro
    return canon_repro(h)


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
    from app.services.reach_db import is_registered as _registered
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
        try:
            if _registered(cas):
                c['_kayitli'] = True   # yalnız "veri var" işareti — numara GBF'ye basılmaz
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
            # GBF 12. bölüm M tablosunun kaynak notu: resmî liste mi, ECHA bildirimleri mi
            _echa = 'ECHA C&L' in str(src.get('source') or '') or src.get('atp') == 'ECHA C&L API'
            c['m_source'] = ('sea_ek6' if src.get('sea_ek6') else 'annex_vi' if src.get('annex_vi')
                             else 'echa_cl' if _echa else 'db') if c['m_factors'] else ''
        else:
            c['m_source'] = 'user'
        user_ate = comp.get('ate') or {}
        if any(_f(v) > 0 for v in user_ate.values()):
            c['ate_source'] = 'user'   # GBF 11.1.2 tablosunda kaynak olarak gösterilir
        else:
            c['ate'] = src.get('ate') or {}
            c['ate_source'] = (src.get('source') or '') if c['ate'] else ''

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
                if fresh.get('ek6_daha_agir'):
                    c['ek6_daha_agir'] = fresh['ek6_daha_agir']
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
                   'H340': 0.1, 'H350': 0.1, 'H360': 0.3, 'H362': 0.3, 'H361': 3.0}   # Tablo 3.7.2 %0,3; H317/H334: _label_min
# Önem sırası — 4'ten fazla bileşen varsa en önemlileri seçilir
_LABEL_RANK = {'H340': 10, 'H350': 10, 'H360': 10, 'H300': 9, 'H310': 9, 'H330': 9, 'H334': 8,
               'H301': 7, 'H311': 7, 'H331': 7, 'H370': 7, 'H372': 7, 'H314': 6, 'H318': 6,
               'H341': 5, 'H351': 5, 'H361': 5, 'H362': 5, 'H317': 5, 'H304': 4, 'H371': 4,
               'H373': 4, 'H302': 3, 'H312': 3, 'H332': 3, 'H335': 2, 'H336': 2}


def _label_min(c: dict, h: str) -> float:
    """Bileşenin karışım sınıflandırmasına katkı eşiği. Hassaslaştırıcılar toplanmaz (SEA Ek-1 3.4.3.3.1):
    katkı = kendi sınıflandırma eşiğini aşması (Tablo 3.4.5 — Kat.1/1B %1, 1A %0,1, özel sınır varsa o).
    Eşiğin altındaki hassaslaştırıcı EUH208 satırında adlandırılır (Ek-2 2.8) — Md.20(3)(b) listesine girmez."""
    if h in ('H317', 'H334'):
        from app.services.clp_service import _normalize_scl_list
        for e in _normalize_scl_list(c.get('sclRaw') or c.get('scl') or []):
            if _h4(e.get('h_code')) == h and e.get('c_min') is not None:
                return float(e['c_min'])
        if any('1A' in str(x.get('h_class') or '') and _h4(x.get('h_code')) == h for x in (c.get('hazards') or [])):
            return 0.1
        return 1.0
    return _LABEL_MIN_CONC.get(h, 1.0)


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
        codes = {h for h in codes if conc >= _label_min(c, h)}
        if codes:
            found.append((max(_LABEL_RANK.get(h, 1) for h in codes), conc, name))
    found.sort(key=lambda x: (-x[0], -x[1]))
    out = [n for i, (rank, _, n) in enumerate(found) if i < 4 or rank >= 9]
    return list(dict.fromkeys(out))


# ── Bölüm 3 konsantrasyon gösterimi (KKDİK Ek-2 A 3.2) ───────────────────────────
# Ek-2 A 3.2: konsantrasyon (a) tam yüzde veya (b) yüzde aralığı olarak verilir; aralık kullanılırsa
# "sağlık ve çevresel zararlar, bileşenlerin en yüksek konsantrasyonunun etkilerini tanımlar".
# TR'de zorunlu bir aralık tablosu yoktur (AB 2020/878 tablosu KKDİK Ek-2'ye alınmamıştır); aşağıdaki
# bantlar programın seçimidir ve her GBF'de üst uçta sınıflandırma değişmiyorsa kullanılır.
_SEC3_BANDS = [(0.0, 0.1), (0.1, 1.0), (1.0, 2.5), (2.5, 5.0), (5.0, 10.0), (10.0, 20.0), (20.0, 25.0),
               (25.0, 50.0), (50.0, 75.0), (75.0, 100.0)]
# Bölüm 3'te her zaman kesin değer (gizlenecek bir şey yok)
_SEC3_ALWAYS_EXACT = {'7732-18-5', '7664-41-7', '124-38-9', '7727-37-9', '7782-44-7'}


def _with_conc(c: dict, v: float) -> dict:
    c = dict(c)
    for k in ('conc', 'concentration', 'concMax', 'conc_max', 'worst_case_conc'):
        c[k] = v
    return c


def health_env_codes(comps: list, form: str = 'liquid', mixture_ph=None, additivity_na: bool = False) -> set:
    """Karışımın sağlık/çevre sınıflandırması (H3xx/H4xx, baskınlık uygulanmış) — classify() ile aynı
    motorlar. Bölüm 3 aralıklarının üst ucunda sınıflandırmanın değişip değişmediğini sınamak için."""
    from app.services.clp_service import classify_mixture_clp, calculate_ate_health_h_codes
    from app.services.stot_engine import calculate as stot_calc
    from app.services.ecological_service import calculate_ecological
    out = set()
    res = classify_mixture_clp(comps, mixture_ph=mixture_ph, mixture_form=form, additivity_na=additivity_na)
    out |= {norm_sub(h) for h in res.get('h_codes', []) if str(h)[:2] == 'H3'}
    try:
        out |= {norm_sub(e['h_code']) for e in calculate_ate_health_h_codes(comps, form=form)[0]}
    except Exception:
        pass
    try:
        out |= {norm_sub(r.get('h_code') or r.get('h')) for r in stot_calc(comps).get('results', [])}
    except Exception:
        pass
    try:
        eco = calculate_ecological([{
            'cas': c.get('cas') or c.get('cas_no') or '', 'name': c.get('name', ''),
            'conc': float(c.get('conc') or 0), 'worst_case_conc': float(c.get('conc') or 0),
            'hazards': c.get('hazards', []), 'm_factors': c.get('m_factors', {}),
            'ec50_algae': c.get('ec50_algae'), 'ec50_fish': c.get('ec50_fish'),
            'ec50_daphnia': c.get('ec50_daphnia'), 'ec50_noec': c.get('ec50_noec'),
        } for c in comps])
        for a in (getattr(eco, 'aquatic', None), getattr(eco, 'aquatic_acute', None)):
            if a is not None and getattr(a, 'h_code', None):
                out.add(a.h_code)
    except Exception:
        pass
    out.discard('')
    for dom, subs in DOMINANCE_MAP.items():
        if dom in out:
            out -= set(subs)
    return out


def _pct(v: float) -> str:
    return f'{round(v, 4):g}'.replace('.', ',')


def _band_text(lo: float, hi: float) -> str:
    return f'< {_pct(hi)}%' if lo <= 0 else f'≥ {_pct(lo)} - < {_pct(hi)}%'


def _narrow_levels(v: float, lo: float, hi: float) -> list:
    """Bandın daraltma basamakları (geniş → dar); her biri lo ≤ v < hi. Son çare tam değer (None)."""
    import math
    out, prev = [(lo, hi)], hi - lo
    for step in (5.0, 1.0, 0.5, 0.1, 0.01):
        a = round(math.floor(v / step + 1e-9) * step, 4)
        b = round(a + step, 4)
        if a < lo or b > hi or b - a >= prev or not (a <= v < b):
            continue
        out.append((a, b))
        prev = b - a
    out.append(None)
    return out


def section3_display(comps: list, mode: str = 'range', form: str = 'liquid', mixture_ph=None,
                     additivity_na: bool = False) -> dict:
    """Bölüm 3 konsantrasyon metinleri. Döner: {anahtar (CAS veya ad): {'text', 'kind', 'upper'}}.
    kind: 'exact' (tam yüzde) | 'user_range' (kullanıcının girdiği aralık; sınıflandırma üst değerle) |
          'band' (program aralığı) | 'narrowed' (üst uçta sınıflandırma değiştiği için daraltılmış aralık).
    mode: 'range' (varsayılan) | 'exact' — kullanıcının panel seçimi."""
    rows, test = {}, []
    for c in comps:
        key = str(c.get('cas') or c.get('cas_no') or '').strip() or str(c.get('name') or '').strip()
        try:
            v = float(c.get('concMax') or c.get('conc_max') or c.get('conc') or c.get('concentration') or 0)
        except (TypeError, ValueError):
            v = 0.0
        try:
            lo_u = float(c.get('conc_min') or c.get('concMin') or 0)
        except (TypeError, ValueError):
            lo_u = 0.0
        if 0 < lo_u < v:
            # Kullanıcının girdiği aralık aynen yazılır; sınıflandırma zaten üst değerle yapılır
            rows[key] = {'text': f'≥ {_pct(lo_u)} - ≤ {_pct(v)}%', 'kind': 'user_range', 'upper': v}
        elif v >= 100 or key in _SEC3_ALWAYS_EXACT or v <= 0 or (
                mode == 'exact' and c.get('comp_type') != 'fragrance'):
            rows[key] = {'text': f'{_pct(v)}%' if v > 0 else '—', 'kind': 'exact', 'upper': v}
        else:
            lo, hi = next(b for b in _SEC3_BANDS if b[0] <= v < b[1])
            rows[key] = {'text': _band_text(lo, hi), 'kind': 'band', 'upper': hi,
                         '_v': v, '_levels': _narrow_levels(v, lo, hi), '_i': 0}
        test.append((key, c, v))

    banded = [k for k, r in rows.items() if r['kind'] == 'band']
    if banded:
        def _codes(at_upper: bool) -> set:
            cs = []
            for key, c, v in test:
                r = rows[key]
                if at_upper and r['kind'] in ('band', 'narrowed'):
                    cs.append(_with_conc(c, r['upper'] * (1 - 1e-6)))   # "< üst" → eşiğin hemen altı
                else:
                    cs.append(_with_conc(c, v))
            return health_env_codes(cs, form=form, mixture_ph=mixture_ph, additivity_na=additivity_na)

        base = _codes(False)

        def _apply(k, i):
            r = rows[k]
            lvl = r['_levels'][i]
            r['_i'] = i
            if lvl is None:
                r.update(text=f"{_pct(r['_v'])}%", kind='exact', upper=r['_v'])
            else:
                r.update(text=_band_text(*lvl), upper=lvl[1], kind='band' if i == 0 else 'narrowed')

        guard = 0
        while _codes(True) != base and guard < 60:
            guard += 1
            open_ = [k for k in banded if rows[k]['kind'] != 'exact']
            if not open_:
                break
            # Tek bileşeni bir basamak daraltmak yetiyorsa onu seç; yoksa üst ucu en uzak olanı daralt
            pick = None
            for k in sorted(open_, key=lambda k: -(rows[k]['upper'] - rows[k]['_v'])):
                saved = {kk: dict(rows[kk]) for kk in open_}
                _apply(k, rows[k]['_i'] + 1)
                ok = _codes(True) == base
                rows.update({kk: saved[kk] for kk in open_})
                if ok:
                    pick = k
                    break
            if pick is None:
                pick = max(open_, key=lambda k: rows[k]['upper'] - rows[k]['_v'])
            _apply(pick, rows[pick]['_i'] + 1)
    for r in rows.values():
        for k in ('_v', '_levels', '_i'):
            r.pop(k, None)
    return rows


def _normalize_conc(comps: list) -> None:
    for c in comps:
        if 'conc' not in c and 'concentration' in c:
            c['conc'] = c['concentration']
        if 'concMax' not in c:
            c['concMax'] = c.get('conc_max') or c.get('conc') or c.get('concentration') or 0


# ── Ana hat ───────────────────────────────────────────────────────────────────
def _conc_of(c: dict) -> float:
    try:
        return float(c.get('concMax') or c.get('conc') or c.get('concentration') or 0)
    except (TypeError, ValueError):
        return 0.0


def _substance_source(c: dict, h: dict) -> str:
    """Madde sınıflandırmasının kaynağı (GBF 2.1 gerekçesi)."""
    if h.get('echa_supplement') or h.get('_echa_supplement'):
        return 'ECHA C&L bildirimleri (Ek-6\'da yer almayan sınıf, SEA Md.6(1)(c))'
    if c.get('sea_ek6') or int(c.get('source_priority') or 9) == 1:
        return 'SEA Ek-6 uyumlaştırılmış sınıflandırma (SEA Md.6(1)(c))'
    if c.get('annex_vi') or int(c.get('source_priority') or 9) == 2:
        return 'AB CLP Ek-VI uyumlaştırılmış sınıflandırma'
    return 'madde verisi / tedarikçi sınıflandırması'


def _substance_acute(c: dict, form: str) -> list:
    """Tek maddeli ürün: akut toksisite maddenin kendi sınıfından (SEA Ek-1 3.1.2) — ATEmix (3.1.3, karışımlar
    için) uygulanmaz. Taşıma (6.1 PG / 2.3) için yol ve kategori de döner."""
    import re as _r
    out, seen = [], set()
    _inh = ('inhalation_gas' if form == 'gas' else
            'inhalation_dust' if form in ('solid', 'powder') else 'inhalation_vapour')
    _lbl = {'oral': 'oral', 'dermal': 'dermal', 'inhalation_gas': 'inhalasyon (gaz)',
            'inhalation_dust': 'inhalasyon (toz)', 'inhalation_vapour': 'inhalasyon (buhar)'}
    for h in c.get('hazards') or []:
        code = _h4(h.get('h_code'))
        if code not in ACUTE_TOX_H or code in seen:
            continue
        seen.add(code)
        route = 'oral' if code < 'H310' else ('dermal' if code < 'H330' else _inh)
        m = _r.search(r'(?:Tox|Tok|Toks)\.?\s*(\d)', h.get('h_class') or '')
        n = int(m.group(1)) if m else {'H300': 1, 'H310': 1, 'H330': 1, 'H301': 3, 'H311': 3, 'H331': 3,
                                       'H302': 4, 'H312': 4, 'H332': 4}[code]
        out.append({'h_code': code, 'h_class': f'Acute Tox. {n} ({_lbl[route]})', 'route': route, 'cat_num': n,
                    'reason': f'Madde sınıflandırması — {_substance_source(c, h)} (SEA Ek-1 3.1.2)',
                    'cutoff_used': '—'})
    return out


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
    additivity_na = bool(inp.get('additivity_na'))   # SEA Ek-1 Tablo 3.2.4 / 3.3.4 (KDU kararı)

    comps = [dict(c) for c in (inp.get('components') or [])]
    _normalize_conc(comps)
    comps = await refresh_components(comps, form)

    # Bileşen fiziksel verileri (ECHA kayıt dosyası → PubChem) — sınıflandırmada bileşen parlama / kaynama noktası,
    # Bölüm 9'da madde / bileşen verisi. Önbellekte yoksa okunur; süre aşılırsa bilinmiyor sayılır (en kötü durum).
    from app.services import component_phys as _cp
    _phys_late = await _cp.ensure_many([c.get('cas') or c.get('cas_no') for c in comps if _conc_of(c) > 0])
    _cp.attach(comps)

    # Tek maddeli ürün (SEA Md.4: madde — katkı ve safsızlıkları dahil; karışım = iki veya daha fazla madde).
    # Madde kendi sınıflandırmasıyla (Ek-6 / veri) sınıflandırılır; karışım hesap yöntemleri (ATEmix 3.1.3,
    # toplama, kesme değerleri) uygulanmaz. Önceden %100 klor karışım gibi hesaplanıp Kat.1 alıyordu (2026-10-09).
    _active = [c for c in comps if _conc_of(c) > 0]
    substance_mode = len(_active) == 1

    # ATE sağlık tehlikeleri (classify_mixture_clp Acute Tox. atlar)
    try:
        if substance_mode:
            ate_h, ate_details = _substance_acute(_active[0], form), {}
        else:
            ate_h, ate_details = calculate_ate_health_h_codes(comps, form=form)
    except Exception as e:
        print(f'[ATE ERROR] {e}')
        ate_h, ate_details = [], {}

    tr_components = build_transport_components(comps)

    clp_res  = classify_mixture_clp(comps, mixture_ph=mixture_ph, mixture_form=form,
                                    additivity_na=additivity_na)
    # "Bileşen geçişkenliğine dayanır — test önerilir" uyarısı yalnızca-test sınıfları için
    # geçersiz: bu sınıflar artık kullanıcının test kararıyla verilir (Bölüm 16 notu ayrı).
    clp_res['warnings'] = [
        w for w in (clp_res.get('warnings') or [])
        if not (isinstance(w, dict) and str(w.get('code', '')).startswith('PHYS_NO_TEST_BASIS_')
                and _h4(w.get('h_code')) in MANUAL_PHYS_H)
    ]
    # Ölçülen kaynama başlangıç noktası: panel bunu test_data.boiling_point olarak gönderir
    _user_bp = inp.get('user_bp')
    if _user_bp is None and test_data.get('boiling_point') not in (None, ''):
        try:
            _user_bp = float(str(test_data.get('boiling_point')).replace(',', '.'))
        except (TypeError, ValueError):
            _user_bp = None
    phys_res = phys_calc(comps, form=form, user_fp=inp.get('user_fp'), user_bp=_user_bp,
                         test_data=test_data, form_sub=form_sub, fp_status=inp.get('fp_status') or '',
                         mixture_ph=mixture_ph,
                         mixture_skin_corr='H314' in {_h4(h) for h in (clp_res.get('h_codes') or [])})
    if _phys_late:
        phys_res.setdefault('warnings', []).append(
            'ℹ Bileşen fiziksel verisi zamanında alınamadı (' + ', '.join(_phys_late) + ') — bu bileşenlerin parlama / '
            'kaynama noktası bilinmiyor sayıldı. Birkaç dakika sonra yeniden hesaplayın.')
    for _c in comps:
        _w = _cp.fp_conflict(_c) if _conc_of(_c) > 0 else None
        if _w:
            phys_res.setdefault('warnings', []).append(_w)
    # GBF Bölüm 9: tek maddede maddenin kendi değerleri, karışımda bileşen verisi (KKDİK Ek-2 9.1)
    b9 = _cp.section9(comps, substance_mode, form)
    stot_res = stot_calc(comps)
    if substance_mode:
        # Madde: bileşen değeri maddenin kendi değeridir — "karışım için belirlenmemiştir" yazılmaz
        _bp = (phys_res.get('theo_props') or {}).get('boiling_point')
        if isinstance(_bp, dict) and _bp.get('estimate_only') and _bp.get('estimate') is not None:
            phys_res['theo_props']['boiling_point'] = {
                'value': _bp['estimate'], 'display': f"{_bp['estimate']:g} °C", 'measured': False,
                'method': 'Madde verisi (literatür)', 'standard': ''}

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
    if substance_mode:
        # Sağlık/çevre satırlarında kesme değeri / toplama formülü yerine madde sınıflandırmasının kaynağı
        _src = {}
        for _h in _active[0].get('hazards') or []:
            _src.setdefault(_h4(_h.get('h_code')), _substance_source(_active[0], _h))
        for e in cp:
            if e['h_code'] in _src and e['h_code'] not in MANUAL_PHYS_H and e['h_code'][:3] not in ('H22', 'H28'):
                e['reason'], e['cutoff_used'] = f"Madde sınıflandırması — {_src[e['h_code']]}", '—'
    present = {e['h_code'] for e in cp}
    dominated = set()
    for dom, subs in DOMINANCE_MAP.items():
        if dom in present:
            dominated.update(subs)
    cp = [e for e in cp if e['h_code'] not in dominated]

    # ── Taşıma ────────────────────────────────────────────────────────────────
    phys_h = [(r.get('h') or r.get('h_code') or '') for r in phys_res.get('results', [])]
    visc = test_data.get('viscosity')   # yalnız ölçülen değer (hesaplanmış viskozite taşımaya verilmez)
    try:
        visc = float(visc) if visc not in (None, '') else None
    except (TypeError, ValueError):
        visc = None
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

    # 6. H304 — yalnızca sıvı/pasta; sıvı/pastada fiziksel motor yetkili (SEA Ek-1 3.10.3.3.1: toplam ≥ %10
    #    VE 40 °C kinematik viskozite ≤ 20,5 mm²/s). Viskozite koşulu sağlanmıyorsa bileşen toplamından
    #    gelen H304 silinir — önceden viskozite girilse de H304 kalıyordu.
    _asp_ok = any((r.get('type') == 'asp_tox') for r in phys_res.get('results', []) + phys_res.get('primary', []))
    if form not in ('liquid', 'paste') or not _asp_ok:
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
    # Kategoriye bağlı kodlar (H228, H272, H261, H242) için fiziksel motor/karar sonucunun uyarı kelimesi de verilir
    _sig_src = list(clp_res.get('passed', [])) + [
        {'h_code': _h4(r.get('h') or r.get('h_code')), 'signal': r.get('signal')} for r in phys_res.get('results', [])]
    signal = signal_word_for(clean, _sig_src)   # H411/H412/H413/H362 tek başına → ''

    euh = check_euh(comps, mixture_form=form, form_sub=form_sub, usage=usage)

    def _drop_euh(code):
        euh['euh_codes']   = [c for c in euh.get('euh_codes', []) if c != code]
        euh['euh_details'] = [d for d in euh.get('euh_details', []) if d.get('code') != code]
    if set(all_h) & {'H314', 'H315'}:   # SEA Ek-2 1.2.4: EUH066 cilt tahrişi yoksa
        _drop_euh('EUH066')
    if 'H317' in {_h4(h) for h in all_h}:   # SEA Ek-2 2.3: EUH203 yalnız H317 taşımayan çimentoda
        _drop_euh('EUH203')
    # SEA Ek-2 2.10 — EUH210: zararlı olarak sınıflandırılmayan, halkın kullanımı için tasarlanmamış karışım
    if not all_h and usage != 'consumer':
        from app.services.euh_service import euh210_triggers
        from app.services.codes_i18n import get_euh as _get_euh
        _t210 = euh210_triggers(comps, mixture_form=form)
        if _t210 and 'EUH210' not in euh.get('euh_codes', []):
            euh.setdefault('euh_codes', []).append('EUH210')
            euh.setdefault('euh_details', []).append({
                'code': 'EUH210', 'text': _get_euh('TR', 'EUH210'),
                'source_cas': '; '.join(t['cas'] for t in _t210),
                'source_name': '; '.join(t['name'] for t in _t210),
                'note': 'SEA Ek-2 2.10 — ' + '; '.join(f"{t['name']}: {t['reason']}" for t in _t210),
            })
            euh['euh_codes'] = sorted(euh['euh_codes'])
            euh['euh_details'] = sorted(euh['euh_details'], key=lambda x: x['code'])
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
                              material=inp.get('glove_material'), thickness=inp.get('glove_thickness'),
                              breakthrough=inp.get('glove_breakthrough'))
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
    # Ek-6 sınıfı uygulandı, ECHA bildirimlerinde daha ağır kategori var — yalnız panelde KDU bilgisi (GBF'ye basılmaz)
    ek6_agir = [{'cas': c.get('cas') or c.get('cas_no') or '', 'name': c.get('name_tr') or c.get('name') or '', **e}
                for c in comps for e in (c.get('ek6_daha_agir') or [])]
    cls_notes = list(phys_res.get('classification_notes', []))
    if b9:
        _srcs = [k for k in ('ECHA', 'PubChem') if any(k in (v.get('note') or '') for v in b9.values())]
        _src_tr = ' ve '.join(s for s in (('ECHA kayıt dosyaları (chem.echa.europa.eu)' if 'ECHA' in _srcs else ''),
                                          ('PubChem (NIH)' if 'PubChem' in _srcs else '')) if s)
        cls_notes.append({
            'TR': (f'Bölüm 9: madde verilerinin kaynağı: {_src_tr}.' if substance_mode else
                   'Bölüm 9: karışım için ölçülmemiş özelliklerde verilen değerler ilgili bileşene atfen verilmiştir '
                   f'(KKDİK Ek-2 9.1); kaynak: {_src_tr}.'),
            'EN': 'Section 9: ' + ('component data are attributed to the relevant substance; ' if not substance_mode
                                   else 'substance data; ') + 'source: '
                  + ' and '.join(s for s in (('ECHA registration dossiers' if 'ECHA' in _srcs else ''),
                                             ('PubChem' if 'PubChem' in _srcs else '')) if s) + '.'})
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

    # KKDİK Ek-17 kısıtlamaları — panelde KDU uyarısı için (örn. madde 46: nonilfenol/etoksilatlar temizlik
    # ürünlerinde ≥%0,1 piyasaya arz edilemez). GBF 15.1 satırları ek17_service ile ayrıca basılır.
    ek17_hits = []
    try:
        from app.services.ek17_service import lookup as _ek17_lookup
        for _c in comps:
            _cas = str(_c.get('cas_no') or _c.get('cas') or '').strip()
            for _r in _ek17_lookup(_cas):
                ek17_hits.append({'cas': _cas, 'name': _c.get('name_tr') or _c.get('name') or _cas,
                                  'conc': float(_c.get('concMax') or _c.get('conc') or _c.get('concentration') or 0),
                                  'giris': _r.get('giris'), 'kaynak': _r.get('kaynak')})
    except Exception as _e:
        print(f'[EK17] {_e}')

    # SEA Ek-1 4.1.3.6.1 — sucul zararı bilinmeyen bileşen ifadesi (etiket + GBF 2.2)
    try:
        from app.services.ecological_service import aquatic_unknown as _aq_unk
        aq_unknown = _aq_unk(comps)
    except Exception as _e:
        print(f'[AQ UNKNOWN] {_e}')
        aq_unknown = {'needed': False, 'pct': 0.0, 'components': []}

    return {
        'components':  comps,
        'ek17':        ek17_hits,
        'aquatic_unknown': aq_unknown,
        'ek6_supplements': ek6_supp,
        'ek6_daha_agir': ek6_agir,
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
        'ate_details': ({} if substance_mode else
                        {**(clp_res.get('ate_mix_details') or {}), **(ate_details or {})}),
        'substance_mode': substance_mode,
        'warnings':    (phys_res.get('warnings', []) + stot_res.get('warnings', [])
                        + clp_res.get('warnings', [])),
        'pending_decisions': phys_res.get('pending_decisions', []),
        'classification_notes': cls_notes,
        'b9': b9,
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
