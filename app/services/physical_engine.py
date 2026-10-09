"""
PhysicalEngine — Fiziksel Tehlikeler + Teorik Fiziksel Özellikler
=================================================================
JS physical_engine.js'nin Python karşılığı.

Bölüm 2.1 (Fiziksel tehlike sınıflandırması) + Bölüm 9 (Fiziksel/kimyasal özellikler)

Kapsanan tehlikeler:
  Flam. Liq. 1/2/3   (H224/H225/H226) — CLP Annex I Tablo 2.6
  Flam. Aerosol 1/2  (H222/H223)      — CLP Annex I §2.3
  Aerosol basınç     (H229)           — CLP Annex I §2.3 (tüm aerosoller)
  Asp. Tox. 1        (H304)           — CLP Annex I Tablo 3.10
  Flam. Gas 1 (H220) / 2 (H221)       — SEA Ek-1 2.2 (ISO 10156); TR SEA'da pirofor gaz/H232 yok
  Ox. Gas 1          (H270)           — CLP Annex I §2.4
  Flam. Sol. 2       (H228)           — CLP Annex I Tablo 2.7
  Ox. Liq. 3         (H272)           — CLP Annex I Tablo 2.13
  Ox. Sol. 1/2       (H271/H272)      — CLP Annex I Tablo 2.13

Bölüm 9 değerleri: karışım özellikleri bileşenlerden hesaplanmaz (KKDİK Ek-2 9 — ampirik bilgi). Madde /
bileşen verisi component_phys (ECHA kayıt dosyası → PubChem); gaz karışımında alt alevlenme sınırı ISO 10156.
"""

from app.services import iso10156
from app.services import component_phys as _cp
from typing import List, Dict, Any, Optional


# Parlama / kaynama noktası: kaynaksız elle yazılmış tablolar (FP_DB 817, BP_DB 1075 madde) kaldırıldı
# (2026-10-09) — bileşen değerleri component_phys (ECHA kayıt dosyası → PubChem) üzerinden.


# Oksitleyici bileşen CAS → maddenin kendi kategorisi (1=H271, 2/3=H272). YALNIZ YEDEK: bileşen
# kaydında H271/H272 yoksa kullanılır; önce SEA Ek-6 konsantrasyon aralığı, sonra bileşen kaydı
# (SEA Md.6(1)(c)). Ek-6'da olanlar Ek-6 değerine göre düzeltildi (2026-10-08); sodyum tiyosülfat
# (indirgen, oksitleyici değil) ve sodyum hipoklorit çözeltisi (Ek-6'da oksitleyici sınıfı yok) çıkarıldı.
OXIDIZING_LIQ_CAS: Dict[str, int] = {
    '7722-84-1': 1,   # H₂O₂ — Ek-6: ≥%70 Ox. Liq. 1, %50–70 Ox. Liq. 2 (aralık _ox_cat'te)
    '7790-98-9': 1,   # NH₄ClO₄ amonyum perklorat — Ek-6 Ox. Sol. 1
    '7775-09-9': 1,   # NaClO₃  sodyum klorat     — Ek-6 Ox. Sol. 1
    '7727-54-0': 3,   # (NH₄)₂S₂O₈ amonyum persülfat — Ek-6 Ox. Sol. 3
    '7722-64-7': 2,   # KMnO₄   potasyum permanganat — Ek-6 Ox. Sol. 2
}


def _ox_cat(c, table: Dict[str, int]) -> int:
    """Oksitleyici bileşenin kategorisi — öncelik SEA Md.6(1)(c):
    1) SEA Ek-6 özel konsantrasyon aralığı (örn. H₂O₂ %50–70 → Kategori 2),
    2) bileşen kaydı ("Ox. Sol. 3" / "Ox. Liq. 2"; H272 hem Kat.2 hem Kat.3'ü kapsar —
       SEA Ek-1 Tablo 2.13.2 / 2.14.2 — kategori sınıf adından okunur, okunamazsa daha ağır olan 2),
    3) yedek tablo. 0 → oksitleyici değil."""
    import re as _re
    cas = (c.get('cas') or c.get('cas_no') or '').strip()
    try:
        conc = float(c.get('concMax') or c.get('conc') or 0)
    except (TypeError, ValueError):
        conc = 0.0
    try:
        from app.services.substance_lookup import _load_sea_ek6
        _db = _load_sea_ek6() or {}
        _e = _db.get(cas) or {}
        if '_alias' in _e:
            _e = _db.get(_e['_alias']) or {}
        for _s in (_e.get('scl_limits') or []):
            if _s.get('h_code') not in ('H271', 'H272') or _s.get('min') is None:
                continue
            _lo, _hi = float(_s['min']), _s.get('max')
            if conc >= _lo and (_hi is None or conc < float(_hi)):
                _m = _re.search(r'(\d)\s*$', str(_s.get('class_en') or _s.get('class') or ''))
                if _m:
                    return int(_m.group(1))
    except Exception:
        pass
    best = 0
    for h in (c.get('hazards') or []):
        hc = (h.get('h_code') or '').replace('*', '').strip()[:4]
        if hc not in ('H271', 'H272'):
            continue
        m = _re.search(r'(\d)\s*$', str(h.get('h_class') or h.get('class') or '').strip())
        cat = int(m.group(1)) if m else (1 if hc == 'H271' else 2)
        best = cat if not best else min(best, cat)
    return best or table.get(cas, 0)


def _ox_signal(cat: int) -> str:
    """SEA Ek-1 Tablo 2.13.2 / 2.14.2: Kategori 1 ve 2 → Tehlike, Kategori 3 → Dikkat."""
    return 'Warning' if cat == 3 else 'Danger'


# Oksitleyici katı CAS → kategori. YALNIZ YEDEK (bkz. _ox_cat). Ek-6'dakiler Ek-6'ya göre düzeltildi.
OXIDIZING_SOLID_CAS: Dict[str, int] = {
    '7778-54-3': 2,   # Ca(ClO)₂  kalsiyum hipoklorit     Ek-6 Ox. Sol. 2
    '7722-64-7': 2,   # KMnO₄     potasyum permanganat   Ek-6 Ox. Sol. 2
    '7778-74-7': 1,   # KClO₄     potasyum perklorat      Ek-6 Ox. Sol. 1
    '7789-38-0': 2,   # NaBrO₃    sodyum bromat           Ox. Sol. 2
    '7776-28-5': 3,   # Na₂S₂O₈   sodyum persülfat        Ox. Sol. 3 (K₂S₂O₈ / (NH₄)₂S₂O₈ Ek-6 Kat.3)
    '7727-21-1': 3,   # K₂S₂O₈    potasyum persülfat      Ek-6 Ox. Sol. 3
    '6484-52-2': 3,   # NH₄NO₃    amonyum nitrat          Ox. Sol. 3
    '7757-79-1': 3,   # KNO₃      potasyum nitrat         Ox. Sol. 3
    '7631-99-4': 3,   # NaNO₃     sodyum nitrat           Ox. Sol. 3
    '10124-37-5': 3,  # Ca(NO₃)₂  kalsiyum nitrat         Ox. Sol. 3
}

# ── TEORİK FİZİKSEL ÖZELLİKLER ──────────────────────────────────────────────
# Karışımın fiziksel özellikleri bileşenlerden HESAPLANMAZ (2026-10-09). KKDİK Ek-2 Bölüm 9 ampirik bilgi ister;
# önceki hesaplar (yoğunluk Σwᵢ/Σ(wᵢ/ρᵢ), Raoult buhar basıncı, sıvıda Le Chatelier alt patlama sınırı, buhar
# yoğunluğu, Kendall-Monroe viskozite, çözünürlük ortalaması, Henry sabiti) kaynağı belirtilmemiş iç tablolara
# (MW / DENSITY / VP / LEL / UEL / VISC / SOL_DB) dayanıyordu — tablolarla birlikte kaldırıldı. GBF'ye ve panele
# madde / bileşen verisi component_phys.section9 ile gelir (ECHA kayıt dosyası → PubChem).
# Burada yalnız en düşük bileşen kaynama noktası (kaynaklı bileşen verisi) tahmin olarak tutulur — test ihtiyacı
# listesi ve Kat.1/2 açıklaması için; GBF'ye karışımın değeri olarak yazılmaz.
def calc_theo_props(comps: List[Dict]) -> Optional[Dict]:
    rows = []
    for c in comps:
        cas = (c.get('cas') or c.get('cas_no') or '').strip()
        w = float(c.get('concMax') or c.get('conc') or 0)
        if w > 0 and cas:
            rows.append((c, cas, w))
    if not rows:
        return None
    tot = sum(w for _, _, w in rows)
    covered = sum(w for c, cas, w in rows
                  if (c.get('phys') if c.get('phys') is not None else _cp.get(cas)))
    min_bp = None
    for c, cas, w in rows:
        bp = _cp.value(c, 'boiling_point')
        if bp is not None and w >= 1 and (min_bp is None or bp < min_bp):
            min_bp = bp
    res: Dict = {'coverage': round(covered / tot * 100) if tot else 0,
                 'has_water': any(cas == '7732-18-5' and w >= 20 for _, cas, w in rows)}
    if min_bp is not None:
        res['boiling_point'] = {'value': min_bp, 'error': None,
                                'method': 'En düşük bileşen kaynama noktası (bileşen verisi)', 'standard': ''}
    return res


# ── TEHLİKE SINIFLANDIRMASI ───────────────────────────────────────────────────

def _cls_flam_liq(fp: float, bp: Optional[float]) -> Optional[Dict]:
    if fp < 23 and (bp is None or bp <= 35):
        return {'h': 'H224', 'cat': 1, 'h_class': 'Flam. Liq. 1', 'signal': 'Danger'}
    if fp < 23:
        return {'h': 'H225', 'cat': 2, 'h_class': 'Flam. Liq. 2', 'signal': 'Danger'}
    if 23 <= fp <= 60:
        return {'h': 'H226', 'cat': 3, 'h_class': 'Flam. Liq. 3', 'signal': 'Warning'}
    return None


_LIT_FP = None
_LIT_MARGIN = 3.0   # literatür (interpolasyon) değeri sınıflandırma sınırına (23 / 60 °C) bu kadar yakınsa kullanılmaz


def _lit_fp_data() -> dict:
    global _LIT_FP
    if _LIT_FP is None:
        try:
            import json as _json
            from pathlib import Path as _Path
            _LIT_FP = _json.loads((_Path(__file__).resolve().parents[2] / 'data' / 'literature_fp_aqueous.json')
                                  .read_text(encoding='utf-8'))
        except Exception as _e:
            print(f'[FLAM LIT] veri okunamadı: {_e}')
            _LIT_FP = {'maddeler': {}}
    return _LIT_FP


def _literature_fp(comps: List[Dict]) -> Optional[Dict]:
    """SEA Ek-1 2.6.4.1: parlama noktası literatürden. Yalnız su + tablodaki TEK alevlenir sıvı (+ alevlenir sıvı
    olmayan, uçucu olmayan bileşenler) içeren karışım. Derişim alevlenir sıvı / (alevlenir sıvı + su) oranından
    hacimce % olarak hesaplanır — uçucu olmayan bileşenler hesaba girmez (parlama noktasını az miktarda yükseltirler,
    SEA Ek-1 2.6.4.3 → temkinli). Ölçülmüş noktalar arasında doğrusal interpolasyon; ölçüm aralığı dışına çıkılmaz
    (yalnız en düşük derişim noktası > 60 °C ise daha seyreltik çözelti de > 60 °C sayılır — seyrelme parlama noktasını
    yükseltir). Döner: {fp|None, above60, vol, cas, ad, yontem, kaynak} veya None (uygulanamaz)."""
    data = _lit_fp_data()
    tbl = data.get('maddeler') or {}
    act = [c for c in comps if float(c.get('concMax') or c.get('conc') or 0) > 0]
    water = [c for c in act if (c.get('cas') or c.get('cas_no') or '').strip() == '7732-18-5']
    hits = [c for c in act if (c.get('cas') or c.get('cas_no') or '').strip() in tbl]
    if len(water) != 1 or len(hits) != 1:
        return None
    for c in act:
        if c is water[0] or c is hits[0]:
            continue
        cas = (c.get('cas') or c.get('cas_no') or '').strip()
        hs = {(h.get('h_code') or '').replace('*', '').strip()[:4] for h in (c.get('hazards') or [])}
        _fp = _cp.value(c, 'flash_point')
        if hs & {'H224', 'H225', 'H226'} or (_fp is not None and _fp < 93):
            return None    # başka alevlenir / uçucu alevlenir bileşen var — tablo uygulanamaz
    f = hits[0]
    cas = (f.get('cas') or f.get('cas_no') or '').strip()
    e = tbl[cas]
    m_f = float(f.get('concMax') or f.get('conc') or 0)
    m_w = float(water[0].get('concMax') or water[0].get('conc') or 0)
    v_f, v_w = m_f / float(e['yogunluk']), m_w / 0.998
    vol = 100.0 * v_f / (v_f + v_w)
    pts = sorted(e['noktalar'])
    base = {'vol': round(vol, 1), 'cas': cas, 'ad': e['ad'], 'yontem': e['yontem'],
            'kaynak': data.get('kaynak_kisa') or data.get('kaynak', ''), 'kaynak_tam': data.get('kaynak', '')}
    if vol < pts[0][0]:
        if pts[0][1] > 60 + _LIT_MARGIN:
            return {**base, 'fp': None, 'above60': True}
        return None
    for (c1, t1), (c2, t2) in zip(pts, pts[1:]):
        if c1 <= vol <= c2:
            fp = t1 + (t2 - t1) * (vol - c1) / (c2 - c1) if c2 > c1 else t1
            return {**base, 'fp': round(fp, 1), 'above60': fp > 60}
    if abs(vol - pts[-1][0]) < 1e-6:
        return {**base, 'fp': pts[-1][1], 'above60': pts[-1][1] > 60}
    return None


def _calc_flam_liq(comps: List[Dict], user_fp=None, user_bp=None, form_sub: str = '',
                   fp_status: str = '') -> Dict:
    """Alevlenir sıvı sınıfı (CLP Ek-I §2.6).

    fp_status — kullanıcı parlama noktası girmediğinde kararı:
      ''               karar verilmedi → en kötü durum + karar uyarısı (needs_decision)
      'no_measurement' ölçüm yok → en kötü durum, bilgi uyarısı
      'not_flammable'  test edildi, parlama noktası > 60 °C → sınıf yok (kullanıcı beyanı)
    Yanıcı bileşen varken sınıflandırma sessizce atlanmaz (SEA Md. 8: fiziksel zararda test verisi).
    """
    DECLARED_FALLBACK = {
        'H224': {'fp': -20, 'bp': 25},
        'H225': {'fp':  15, 'bp': 80},
        'H226': {'fp':  40, 'bp': 120},
    }

    if user_fp is not None:
        # Kullanıcı FP girmiş
        theo_bp = None
        _bp_unknown = []   # kaynama noktası bilinmeyen alevlenir sıvı bileşenler
        for c in comps:
            cas = (c.get('cas') or c.get('cas_no') or '').strip()
            w   = float(c.get('concMax') or c.get('conc') or 0)
            if w < 1:
                continue
            bp  = _cp.value(c, 'boiling_point')
            _hs = {(h.get('h_code') or '').replace('*', '').strip()[:4] for h in (c.get('hazards') or [])}
            if 'H224' in _hs:
                bp = min(bp, 35) if bp is not None else 35   # Kat.1 madde: kaynama ≤ 35 °C
            if bp is not None:
                if theo_bp is None or bp < theo_bp:
                    theo_bp = bp
            elif _hs & {'H225', 'H226'}:
                _bp_unknown.append(c.get('name') or cas)
        # SEA Ek-1 Tablo 2.6.1: Kat.1/Kat.2 ayrımı karışımın başlangıç kaynama noktasıyla yapılır — ölçülen değer
        # varsa o kullanılır. Yoksa en düşük bileşen kaynama noktası temkinli tahmindir (karışımınki genellikle ondan düşük
        # olmaz). Alevlenir bir bileşenin kaynama noktası bilinmiyorsa en kötü durum (≤ 35 °C → Kat.1).
        # Önceden hiçbir bileşen kaynama noktası bilinmiyorsa 100 °C varsayılıp Kat.2 veriliyordu (2026-10-09).
        _bp_worst = False
        if user_bp is not None:
            effective_bp, _bp_src = user_bp, f', kaynama başlangıcı {user_bp}°C ölçülen'
        elif user_fp >= 23:
            effective_bp, _bp_src = None, ''
        elif theo_bp is not None and (theo_bp <= 35 or not _bp_unknown):
            effective_bp = theo_bp
            _bp_src = f', kaynama başlangıcı ölçülmedi — en düşük bileşen kaynama noktası {theo_bp:g}°C'
        else:
            effective_bp = None
            _bp_worst = True
            _bp_src = (', kaynama başlangıcı ölçülmedi ve '
                       + (f"bileşen kaynama noktası bilinmiyor ({', '.join(_bp_unknown)})" if _bp_unknown
                          else 'bileşen kaynama noktaları bilinmiyor')
                       + ' — en kötü durum ≤ 35 °C (SEA Ek-1 Tablo 2.6.1)')
        if fp_status == 'l2_negative' and 35 < user_fp <= 60:
            # SEA Ek-1 2.6.4.5: parlama noktası 35–60 °C ve UN L.2 sürekli yanma testi olumsuz → Kat.3 gerekmez
            return {'result': None, 'source': f'Kullanıcı girişi ({user_fp}°C); UN L.2 sürekli yanma testi olumsuz '
                                              '(SEA Ek-1 2.6.4.5)', 'fp': user_fp, 'l2': True}
        return {'result': _cls_flam_liq(user_fp, effective_bp),
                'source': f'Kullanıcı girişi ({user_fp}°C{_bp_src})', 'fp': user_fp, 'bp_worst': _bp_worst}

    # SEA Ek-1 2.6.4.1: "Veriler testlerle elde edilebilir, literatürlerden bulunabilir veya hesaplanabilir." Su +
    # tek alevlenir sıvı karışımında ölçülmüş literatür değeri (data/literature_fp_aqueous.json) — önceden %10 etanollü
    # su bazlı ürüne etanolün kendi parlama noktasıyla (13 °C) H225 veriliyordu; ölçülmüş değer ~48 °C (H226).
    _lit = _literature_fp(comps) if fp_status != 'not_flammable' else None
    _lit_warn = None
    if _lit:
        _lfp = _lit['fp']
        _src = (f"Literatür değeri: hacimce %{_lit['vol']:g} {_lit['ad']} (su içinde) için "
                + (f"~{_lfp:g} °C" if _lfp is not None else '> 60 °C')
                + f" — {_lit['kaynak']}, {_lit['yontem']}; ölçülmüş noktalar arası doğrusal interpolasyon "
                  "(SEA Ek-1 2.6.4.1)")
        if _lfp is not None and (abs(_lfp - 23) < _LIT_MARGIN or abs(_lfp - 60) < _LIT_MARGIN):
            # Interpolasyon / derişim çevrimi belirsizliği sınıf sınırını değiştirebilir — ölçüm gerekir
            _lit_warn = (f"ℹ Literatür değeri (~{_lfp:g} °C, hacimce %{_lit['vol']:g} {_lit['ad']}) sınıflandırma "
                         f"sınırına ±{_LIT_MARGIN:g} °C'den yakın — parlama noktası kapalı kap yöntemiyle ölçülmelidir "
                         "(SEA Ek-1 2.6.4.1).")
        else:
            _l2 = fp_status == 'l2_negative' and _lfp is not None and 35 < _lfp <= 60
            _res = None if (_lfp is None or _l2) else _cls_flam_liq(_lfp, 100)   # su bazlı: kaynama > 35 °C
            return {'result': _res, 'source': _src + ('; UN L.2 sürekli yanma testi olumsuz (SEA Ek-1 2.6.4.5)'
                                                      if _l2 else ''),
                    'fp': _lfp, 'lit': _lit, 'l2': _l2, 'screening': False, 'flam_components': False,
                    'water_dilution_warning': None}

    # CLP §2.6.4.2 — su seyreltme etkisi:
    # Su (CAS 7732-18-5) >= %50 olan karışımlarda yanıcı bileşenin FP'si
    # doğrudan kullanılamaz; karışımın gerçek FP'si çok daha yüksek olur.
    # Bu durumda kullanıcıdan ölçülmüş FP istenir.
    _water_conc = sum(
        float(c.get('concMax') or c.get('conc') or 0)
        for c in comps
        if (c.get('cas') or c.get('cas_no') or '').strip() == '7732-18-5'
    )
    _high_water = _water_conc >= 50.0
    _aqueous    = _high_water or form_sub == 'waterbased'

    cat_sum = {1: 0.0, 2: 0.0, 3: 0.0}
    cat_triggers = {1: [], 2: [], 3: []}
    cat_fp = {1: None, 2: None, 3: None}

    for c in comps:
        cas  = (c.get('cas') or c.get('cas_no') or '').strip()
        conc = float(c.get('concMax') or c.get('conc') or 0)
        fp   = _cp.value(c, 'flash_point')   # ECHA kayıt dosyası / PubChem; yoksa None (bilinmiyor)
        bp   = None
        estimated = False
        decl_h = None

        # SEA Md.6(1)(c): bileşenin kendi kaydındaki sınıf (Ek-6 → ECHA bildirimi) bileşenin ölçülmüş parlama /
        # kaynama noktasından önce gelir (Ek-6'da sınıf yoksa ölçülmüş değerle kendi sınıflandırma). Önceden tablo öndeydi: o-ksilen (Ek-6 Kat.3) tablodaki 17 °C ile
        # Kat.2, n-propanol (Ek-6 Kat.2) Kat.3 sayılıyor; diglyme (Ek-6 H226) tabloda 70 °C diye atlanıyordu.
        if conc > 0:
            hazard_codes = {(h.get('h_code') or '').replace('*','').strip()[:4]
                            for h in (c.get('hazards') or [])}
            decl_h = next((h for h in ('H224', 'H225', 'H226') if h in hazard_codes), None)
        if decl_h:
            _bp_db = _cp.value(c, 'boiling_point')
            _db_cls = (_cls_flam_liq(fp, _bp_db)
                       if fp is not None and fp < 60 else None)
            if _db_cls and _db_cls['h'] == decl_h:
                bp = _bp_db            # ölçülmüş değer kayıtla uyumlu — gösterimde kullanılabilir
            else:
                fp        = DECLARED_FALLBACK[decl_h]['fp']
                bp        = DECLARED_FALLBACK[decl_h]['bp']
                estimated = True

        if fp is None or fp >= 60:
            continue
        if not estimated and not decl_h:
            bp = _cp.value(c, 'boiling_point')

        cls = _cls_flam_liq(fp, bp)
        if not cls:
            continue
        cat = cls['cat']
        cat_sum[cat] += conc
        # Kayıttan gelen sınıf için konan temsilî değer gerçek parlama noktası değildir → tahmine katılmaz
        if not estimated and (cat_fp[cat] is None or fp < cat_fp[cat]):
            cat_fp[cat] = fp
        cat_triggers[cat].append({'cas': cas, 'name': c.get('name') or cas,
                                   'conc': conc, 'fp': fp, 'estimated': estimated, 'h': cls['h']})

    def trig_src(t):
        if t['estimated']:
            return f"{t['name']} (%{t['conc']}, bileşen sınıflandırması {t['h']})"
        return f"{t['name']} (%{t['conc']}, FP={t['fp']}°C)"

    sum1   = cat_sum[1]
    sum12  = cat_sum[1] + cat_sum[2]
    sum123 = cat_sum[1] + cat_sum[2] + cat_sum[3]

    # Kullanıcı FP girmediğinde bileşen-kategori toplamı tarama (en kötü durum) yöntemidir.
    # Karışımın gerçek FP'si ölçümle belirlenir (CLP Ek-I §2.6.4); hesap ancak sonucu
    # kriterin ≥ 5 °C üstündeyse muafiyet için kullanılabilir (§2.6.4.2).
    _screening = True
    if sum1 >= 1:
        trigs, worst = cat_triggers[1], {'h':'H224','cat':1,'h_class':'Flam. Liq. 1','signal':'Danger'}
        fps = [cat_fp[1]]
    elif sum12 >= 1:
        trigs, worst = cat_triggers[1] + cat_triggers[2], {'h':'H225','cat':2,'h_class':'Flam. Liq. 2','signal':'Danger'}
        fps = [cat_fp[k] for k in (1, 2)]
    elif sum123 >= 10:
        trigs, worst = cat_triggers[1] + cat_triggers[2] + cat_triggers[3], {'h':'H226','cat':3,'h_class':'Flam. Liq. 3','signal':'Warning'}
        fps = [cat_fp[k] for k in (1, 2, 3)]
    else:
        # Alevlenir sıvı bileşen var ama toplamı programın tarama eşiğinin (%1 / %10) altında. Bu
        # eşikler SEA Ek-1'de yoktur (karışımın parlama noktası ölçümle belirlenir — Ek-1 2.6.4);
        # sınıf verilmez ama kullanıcı sessiz bırakılmaz.
        _low = cat_triggers[1] + cat_triggers[2] + cat_triggers[3]
        _low_warn = None
        if _low and fp_status != 'not_flammable':
            _low_warn = (
                f'ℹ Parlama noktası girilmedi — ürün az miktarda alevlenir sıvı bileşen içeriyor '
                f'({" + ".join(trig_src(t) for t in _low)}). Toplam miktar programın tarama eşiğinin '
                '(Kat.1–2 için %1, Kat.3 için %10) altında olduğundan alevlenir sıvı sınıfı verilmedi. '
                'Bu eşikler yönetmelikte yer almaz; karışımın parlama noktası ölçümle belirlenir '
                '(SEA Ek-1 2.6.4). Ölçülen değer varsa girin.')
        return {'result': None, 'source': None, 'fp': None, 'screening': _screening,
                'water_dilution_warning': _low_warn, 'flam_components': False}

    fps = [f for f in fps if f is not None]
    src = ' + '.join(trig_src(t) for t in trigs)
    if fp_status == 'not_flammable':
        return {'result': None, 'source': 'Kullanıcı beyanı — test edildi, parlama noktası > 60 °C',
                'fp': None, 'screening': False, 'declared_nonflam': True, 'flam_components': True,
                'worst_h': worst['h'], 'triggers': trigs, 'water_dilution_warning': None}

    _aq_note = (' Su bazlı karışımda gerçek parlama noktası bileşenlerinkinden genellikle çok daha '
                'yüksektir; ölçüm yapılırsa sınıf hafifleyebilir veya kalkabilir.' if _aqueous else
                ' Ölçüm yapılırsa sınıf hafifleyebilir.')
    if fp_status == 'no_measurement':
        _warn = (f'ℹ Parlama noktası ölçülmedi — {worst["h"]} bileşenlere göre en kötü durum '
                 f'varsayımıyla verildi ({src}).' + _aq_note
                 + ' Bu geçici bir ihtiyat uygulamasıdır: SEA Md.10(2) uyarınca yeterli ve güvenilir bilgi yoksa '
                   'parlama noktası testi yapılır (kapalı kap, SEA Ek-1 Tablo 2.6.3); GBF Bölüm 16\'ya not düşülür.')
    else:
        _warn = (f'⚠ Parlama noktası girilmedi — yanıcı sıvı bileşen var ({src}). '
                 f'Şimdilik en kötü durum uygulandı: {worst["h"]}. Ölçülen değeri girin, '
                 '"Test edildi — yanıcı değil" beyanını seçin veya "Ölçüm yok" deyin.' + _aq_note)
    if _lit_warn:
        _warn = _lit_warn + ' ' + _warn
    return {'result': worst, 'source': src, 'fp': min(fps) if fps else None,
            'screening': _screening, 'worst_case': True, 'flam_components': True,
            'needs_decision': fp_status != 'no_measurement', 'worst_h': worst['h'],
            'triggers': trigs, 'water_dilution_warning': _warn}


def _aerosol_flam_components(comps: List[Dict]) -> Dict:
    """SEA Ek-1 2.3 (2.1.4.1) alevlenir bileşenler: alevlenir gazlar, parlama noktası ≤ 93 °C sıvılar (alevlenir
    sıvılar dahil), alevlenir katılar. Piroforik / kendiliğinden ısınan / su ile tepkimeye girenler sayılmaz (Not 1).
    Dönüş: {'pct': toplam % (kütlece), 'items': [...], 'unknown': [verisi olmayan bileşen adları]}"""
    try:
        _iso_flam = iso10156.data()['alevlenir']
    except Exception:
        _iso_flam = {}
    _non_flam = {'7732-18-5', '124-38-9', '7727-37-9', '7440-37-1', '7440-59-7', '10024-97-2', '7782-44-7'}
    items, unknown, pct = [], [], 0.0
    for c in comps:
        cas = (c.get('cas') or c.get('cas_no') or '').strip()
        conc = float(c.get('concMax') or c.get('conc') or 0)
        if conc <= 0:
            continue
        name = c.get('name_tr') or c.get('name') or cas
        hs = {(h.get('h_code') or '').replace('*', '').strip()[:4] for h in (c.get('hazards') or [])}
        fp = _cp.value(c, 'flash_point')
        why = None
        if hs & {'H220', 'H221'} or (_iso_flam.get(cas, {}).get('tablo') == 'Tablo 2'):
            why = 'alevlenir gaz'
        elif fp is not None and fp <= 93:
            why = f'parlama noktası {fp:g} °C ≤ 93 °C'
        elif hs & {'H224', 'H225', 'H226'}:
            why = 'alevlenir sıvı'
        elif 'H228' in hs:
            why = 'alevlenir katı'
        if why:
            pct += conc
            items.append(f'{name} (%{conc:g}, {why})')
        elif fp is None and cas not in _non_flam and not (hs & {'H280', 'H281', 'H270'}):
            unknown.append(name)
    return {'pct': pct, 'items': items, 'unknown': unknown}


def _calc_flam_aerosol(comps: List[Dict], user_fp=None,
                       aerosol_flam_pct=None, aerosol_hoc=None, decision: str = '') -> Dict:
    """
    Aerosol alevlenirliği — SEA Ek-1 2.3 (2.1.4.1–2.1.4.2, Şekil 2.3.1):
      ≤ %1 alevlenir bileşen ve yanma ısısı < 20 kJ/g        → Kategori 3 (yalnız H229)
      ≥ %85 alevlenir bileşen ve yanma ısısı ≥ 30 kJ/g       → Kategori 1 (H222)
      diğerleri: tutuşma mesafesi / kapalı ortam / köpük testi → Kategori 1, 2 veya 3
      Not: bu testlere tâbi tutulmamış, %1'den fazla alevlenir bileşen içeren aerosol → Kategori 1.
    aerosol_flam_pct / aerosol_hoc: kullanıcı beyanı (kütlece %, kJ/g); yoksa bileşenlerden hesaplanır.
    decision (test_data['flammable_aerosol']): test sonucu — 'H222' | 'H223' | 'not_flammable'.
    Dönüş: {'result': {...}|None, 'pending': {...}|None, 'warning': str|None}
    """
    _cat1 = {'h': 'H222', 'h_class': 'Aerosol 1', 'signal': 'Danger'}
    _cat2 = {'h': 'H223', 'h_class': 'Aerosol 2', 'signal': 'Warning'}
    _test_src = 'Aerosol testi sonucu (UN Test ve Kriterler El Kitabı 31.4–31.6) — kullanıcı beyanı'
    if decision == 'H222':
        return {'result': {**_cat1, 'source': _test_src}, 'pending': None, 'warning': None}
    if decision == 'H223':
        return {'result': {**_cat2, 'source': _test_src}, 'pending': None, 'warning': None}
    if decision == 'not_flammable':
        return {'result': None, 'pending': None, 'warning': None}

    fc = _aerosol_flam_components(comps)
    if decision == 'not_tested':
        return {'result': {**_cat1, 'source': ("Aerosol testi yapılmadı — %1'den fazla alevlenir bileşen içerdiğinden "
                                                'Kategori 1 (SEA Ek-1 2.3, 2.1.4.2 Not)')},
                'pending': None, 'warning': None, 'untested_cat1': True}
    declared = aerosol_flam_pct is not None
    pct = float(aerosol_flam_pct) if declared else fc['pct']
    hoc = float(aerosol_hoc) if aerosol_hoc is not None else None
    _src_pct = (f'beyan edilen alevlenir içerik %{pct:g}' if declared else
                f"alevlenir bileşenler %{pct:g}: {', '.join(fc['items']) or 'yok'}")
    _unk = ('' if declared or not fc['unknown'] else
            f" Parlama noktası verisi olmayan bileşen(ler): {', '.join(fc['unknown'])} — parlama noktası ≤ 93 °C ise "
            'alevlenir bileşen sayılır, doğrulayın.')

    if pct <= 1 and (hoc is None or hoc < 20):
        _w = ('Aerosol Kategori 3: alevlenir bileşen ≤ %1'
              + ('' if hoc is not None else ' — yanma ısısının < 20 kJ/g olduğu doğrulanmalı (SEA Ek-1 Şekil 2.3.1(a))')
              + '.' + _unk)
        return {'result': None, 'pending': None, 'warning': _w if (hoc is None or _unk) else None}
    if pct >= 85 and hoc is not None and hoc >= 30:
        return {'result': {**_cat1, 'source': f'{_src_pct}, yanma ısısı {hoc:g} kJ/g (SEA Ek-1 Şekil 2.3.1(a))'},
                'pending': None, 'warning': None}

    pending = {
        'code': 'PHYS_AEROSOL_UNTESTED', 'field': 'flammable_aerosol',
        'question': (f"Aerosol %1'den fazla alevlenir bileşen içeriyor ({_src_pct}). SEA Ek-1 2.3 gereği kategori "
                     'tutuşma mesafesi / kapalı ortam testi (sprey) veya köpük testiyle belirlenir; bu testlere tâbi '
                     'tutulmamış aerosol Kategori 1 sayılır. Test sonucunu seçin.' + _unk),
        'test_guidance': ('UN Test ve Kriterler El Kitabı Kısım III 31.4 (kapalı ortam), 31.5 (tutuşma mesafesi), '
                          '31.6 (köpük); kategori ölçütleri SEA Ek-1 Şekil 2.3.1(b)/(c).'),
        'options': [
            {'value': 'H222', 'label': 'Test sonucu — Kategori 1 (H222)', 'effect': 'H222 + H229, GHS02, Tehlike'},
            {'value': 'H223', 'label': 'Test sonucu — Kategori 2 (H223)', 'effect': 'H223 + H229, GHS02, Dikkat'},
            {'value': 'not_flammable', 'label': 'Test sonucu — Kategori 3 (yalnız H229)',
             'effect': 'H222/H223 atanmaz; H229, Dikkat'},
            {'value': 'not_tested', 'label': 'Test yapılmadı — Kategori 1 (SEA Ek-1 2.3 notu)',
             'effect': "H222 + H229, Tehlike; Bölüm 16'ya \"test yapılmadı\" notu düşülür"},
        ],
        'legal_basis': 'SEA Ek-1 2.3 (2.1.4.2 Not)',
    }
    return {'result': {**_cat1, 'source': (f'{_src_pct} — aerosol testi yapılmadığından Kategori 1 '
                                            '(SEA Ek-1 2.3, 2.1.4.2 Not)')},
            'pending': pending, 'warning': None}


def _calc_asp_tox(comps: List[Dict], test_data: Dict = None) -> Dict:
    kin_visc = None
    if test_data:
        v = test_data.get('viscosity')
        if v is not None:
            try:
                kin_visc = float(v)
            except (ValueError, TypeError):
                pass

    if kin_visc is not None and kin_visc > 20.5:
        return {'result': None,
                'source': f'Kinematik viskozite {kin_visc} mm²/s > 20,5 mm²/s — H304 uygulanmaz',
                'total': 0, 'viscosity_excluded': True}

    total, triggers = 0.0, []
    for c in comps:
        cas  = (c.get('cas') or c.get('cas_no') or '').strip()
        conc = float(c.get('concMax') or c.get('conc') or 0)
        # Yalnız bileşen kaydı (SEA Ek-6 → ECHA bildirimleri). Elle tutulan CAS listesi kaldırıldı: ağır fuel oil,
        # baz yağ ve ksilen için Ek-6'da H304 yokken listeden H304 veriliyordu (2026-10-08 tablo denetimi).
        # Sınıf adı TR ("Asp. Tok. 1") gelebilir — H304 kodu da kabul edilir
        has_class = any((h.get('h_class') or '') == 'Asp. Tox. 1'
                        or (h.get('h_code') or '').replace('*', '').strip()[:4] == 'H304'
                        for h in (c.get('hazards') or []))
        if has_class and conc > 0:
            triggers.append({'cas': cas, 'name': c.get('name') or cas, 'conc': conc})
            total += conc

    if total >= 10:
        visc_note = ('' if kin_visc is not None else
                     ' (40 °C kinematik viskozite ölçülmedi — SEA Ek-1 3.10.3.3.1; ölçüm > 20,5 mm²/s ise H304 kalkar)')
        src = ', '.join(f"{t['name']} (%{t['conc']})" for t in triggers) + visc_note
        return {'result': {'h':'H304','h_class':'Asp. Tox. 1','signal':'Danger'},
                'source': src, 'total': total}
    return {'result': None, 'source': None, 'total': total}


# ── ANA HESAP FONKSİYONU ─────────────────────────────────────────────────────

# Fiziksel H kodları (H220-H272) — oksitleyici katı/sıvı bypass şartı 3 için kontrol seti.
# Modül düzeyinde: önce yalnızca katı dalında tanımlıydı, sıvı oksitleyici dalı (örn. sodyum
# hipoklorit çözeltisi) UnboundLocalError ile çöküyordu.
_PHYS_H_SET = {f'H{n}' for n in range(220, 273)}


def calculate(comps: List[Dict], form: str = 'liquid',
              user_fp=None, user_bp=None, test_data: Dict = None,
              form_sub: str = '', fp_status: str = '', mixture_ph=None,
              mixture_skin_corr: bool = False) -> Dict:
    """
    Fiziksel tehlike sınıflandırması + teorik fiziksel özellikler hesapla.

    Returns:
        {
          'results': [...],    # tüm tehlike sonuçları
          'primary': [...],    # ana tehlikeler
          'extra':   [...],    # ek tehlikeler
          'warnings': [...],
          'theo_props': {...}  # teorik fiziksel özellikler
        }
    """
    if test_data is None:
        test_data = {}

    primary, extra, warnings, pending_decisions = [], [], [], []
    _aer_info = None   # aerosol alevlenir bileşen oranı / yanma ısısı (GBF Bölüm 9.2)
    _iso_gas = None   # ISO 10156 gaz karışımı hesabı sonucu (Bölüm 9 / 16 için)
    _iso_ox = None    # ISO 10156 5.3 oksitleme gücü hesabı sonucu (Bölüm 16 için)
    _aerosol_untested = False   # aerosol testi yapılmadan Kat.1 (Bölüm 16 notu için)

    fl = {'result': None, 'source': None, 'fp': None}
    if form in ('liquid', 'paste'):
        fl = _calc_flam_liq(comps, user_fp, user_bp=user_bp, form_sub=form_sub,
                            fp_status=fp_status)
        if fl.get('water_dilution_warning'):
            warnings.append(fl['water_dilution_warning'])
        if fl['result']:
            # Ölçüm yoksa %1 / %10 bileşen toplamı programın tarama (en kötü durum) kuralıdır —
            # yönetmelikte yer almaz; kriter karışımın parlama noktasıdır (SEA Ek-1 Tablo 2.6.1).
            _flam_cutoff = ('Ölçülen parlama noktası — SEA Ek-1 Tablo 2.6.1' if user_fp is not None else
                            'Literatür parlama noktası — SEA Ek-1 2.6.4.1 / Tablo 2.6.1' if fl.get('lit') else {
                'H224': 'Ölçüm yok — tarama: ≥ %1 Kat.1 alevlenir sıvı bileşen (en kötü durum; SEA Ek-1 Tablo 2.6.1 ölçümle)',
                'H225': 'Ölçüm yok — tarama: ≥ %1 Kat.1+2 alevlenir sıvı bileşen (en kötü durum; SEA Ek-1 Tablo 2.6.1 ölçümle)',
                'H226': 'Ölçüm yok — tarama: ≥ %10 alevlenir sıvı bileşen (en kötü durum; SEA Ek-1 Tablo 2.6.1 ölçümle)',
            }.get(fl['result']['h'], 'Alevlenir sıvı — SEA Ek-1 Tablo 2.6.1'))
            primary.append({'type': 'flam_liq', **fl['result'],
                            'source': fl['source'], 'fp': fl['fp'],
                            'cutoff_used': _flam_cutoff})

    if form == 'aerosol':
        fa = _calc_flam_aerosol(comps, user_fp,
                                aerosol_flam_pct=test_data.get('aerosol_flam_pct'),
                                aerosol_hoc=test_data.get('aerosol_hoc'),
                                decision=(test_data.get('flammable_aerosol') or '').strip())
        if fa.get('warning'):
            warnings.append(fa['warning'])
        if fa.get('pending'):
            pending_decisions.append(fa['pending'])
        if fa.get('result'):
            primary.append({'type': 'flam_aerosol', **fa['result'], 'cutoff_used': fa['result']['source']})
        _aerosol_untested = bool(fa.get('pending') or fa.get('untested_cat1'))
        _declared = test_data.get('aerosol_flam_pct') is not None
        _aer_info = {'pct': (float(test_data['aerosol_flam_pct']) if _declared
                             else _aerosol_flam_components(comps)['pct']),
                     'declared': _declared,
                     'hoc': float(test_data['aerosol_hoc']) if test_data.get('aerosol_hoc') is not None else None}
        extra.append({'type': 'aerosol_press', 'h': 'H229', 'h_class': 'Aerosol 3',
                      'signal': 'Warning', 'source': 'Aerosol ürün — basınçlı kap',
                      'cutoff_used': 'CLP Ek-I §2.3 — tüm aerosollere uygulanır'})

    if form in ('liquid', 'paste'):
        # SEA Ek-1 3.10.3.3.1: karar "40 °C'de ölçülmüş kinematik viskozite"ye göre verilir. Hesaplanmış
        # viskozite ölçüm değildir — H304'ü dışarıda bırakmak için kullanılmaz (2026-10-09; önceden kullanılıyordu).
        asp = _calc_asp_tox(comps, test_data)
        if asp['result']:
            primary.append({'type': 'asp_tox', **asp['result'],
                            'source': asp['source'], 'total': asp['total'],
                            'cutoff_used': '≥ %10 aspirasyon toksik bileşen'})
        if asp.get('viscosity_excluded'):
            warnings.append('H304: ' + asp['source'])

    if form == 'gas':
        # Pirofor gazlar (silan, fosfin, arsin…) ISO 10156 Tablo 2'de — karışım hesabına girer. TR SEA'da
        # pirofor gaz kategorisi / H232 yoktur. Önceden "≥ %1 pirofor gaz → H220" kısa yolu vardı; yönetmelikte
        # böyle bir eşik yok (örn. %1 arsin ISO 10156'ya göre alevlenir değildir) — kaldırıldı.
        # Alevlenir gaz karışımı — SEA Ek-1 2.2 / Tablo 2.2.1 (TR: Kategori 1 ve 2). Karışımın alevlenirliği
        # test (EN 1839) veya ISO 10156 hesabıyla belirlenir; bileşenin varlığı yetmez (örn. azotta %1 CO
        # alevlenmez). Sıra: kullanıcının test sonucu → ISO 10156:2017 hesabı (iso10156.py, parametreler
        # data/iso10156_gas_data.json) → hesap yapılamıyorsa (tabloda olmayan bileşen, oksitleyici gaz,
        # kısmen halojenli hidrokarbon) bütün bileşenler Kat.1 ise Kat.1, değilse karar sorusu.
        def _gas_cat(c):
            hs = {(h.get('h_code') or '').replace('*', '').strip()[:4] for h in (c.get('hazards') or [])}
            return 1 if 'H220' in hs else 2 if 'H221' in hs else 0
        _gas_comps = [c for c in comps if float(c.get('concMax') or c.get('conc') or 0) > 0]
        _flam = [c for c in _gas_comps if _gas_cat(c)]
        _fg_dec = (test_data.get('flammable_gas') or '').strip()
        _iso = iso10156.evaluate(comps) if not _fg_dec else {'status': 'skipped'}
        if _iso['status'] == 'calculated':
            _iso_gas = _iso
            if _iso['flammable']:
                primary.append({'type': 'flam_gas', 'h': _iso['h'], 'h_class': _iso['h_class'],
                                'signal': 'Danger' if _iso['h'] == 'H220' else 'Warning',
                                'source': f"{_iso['text']} — parametreler: {_iso['source']}",
                                'cutoff_used': _iso['text']})
        elif (_flam or _iso['status'] == 'not_applicable') and not _fg_dec:
            _nm = lambda c: (c.get('name_tr') or c.get('name') or c.get('cas') or c.get('cas_no') or '')
            _fsrc = ', '.join(f"{_nm(c)} (%{float(c.get('concMax') or c.get('conc') or 0):g})" for c in _flam)
            _iso_why = _iso.get('reason') or ''
            if _flam and len(_flam) == len(_gas_comps) and all(_gas_cat(c) == 1 for c in _flam):
                primary.append({
                    'type': 'flam_gas', 'h': 'H220', 'h_class': 'Flam. Gas 1', 'signal': 'Danger',
                    'source': _fsrc,
                    'cutoff_used': ('Tüm bileşenler Kategori 1 alevlenir gaz — karışımın alt alevlenme sınırı '
                                    'de ≤ %13 (SEA Ek-1 Tablo 2.2.1(a))'),
                })
            else:
                pending_decisions.append({
                    'code': 'PHYS_FLAM_GAS_UNTESTED',
                    'field': 'flammable_gas',
                    'question': (
                        (f'Gaz karışımında alevlenir gaz bileşeni var: {_fsrc}. ' if _fsrc else
                         'Gaz karışımında alevlenir olabilecek bileşen var. ')
                        + 'SEA Ek-1 2.2 gereği karışımın alevlenirliği test (EN 1839) veya ISO 10156 hesabıyla '
                        'belirlenir — bileşenin varlığı yeterli değildir. Program hesabı yapamadı: '
                        + (_iso_why or 'bileşen verisi eksik') + '. Sonucu seçin.'),
                    'test_guidance': (
                        'Kategori 1: havada hacimce %13 veya daha az bir karışımda tutuşuyor ya da alevlenme '
                        'aralığı en az 12 puan; Kategori 2: diğer alevlenir gazlar (SEA Ek-1 Tablo 2.2.1). '
                        'ISO 10156: alevlenir bileşenlerin oranı ve alevlenme sınırları ile inert gazların '
                        'eşdeğerlik katsayılarından hesaplanır; gaz tedarikçisinin GBF\'sinde veya sertifikasında '
                        'genellikle yer alır.'),
                    'options': [
                        {'value': 'H220', 'label': 'Test / ISO 10156 sonucu — Kategori 1 (H220)',
                         'effect': 'H220 → GHS02, Tehlike'},
                        {'value': 'H221', 'label': 'Test / ISO 10156 sonucu — Kategori 2 (H221)',
                         'effect': 'H221 → piktogram yok, Dikkat'},
                        {'value': 'not_flammable', 'label': 'Test / ISO 10156 sonucu — alevlenir değil',
                         'effect': 'H220/H221 atanmaz; Bölüm 16\'ya gerekçe yazılır'},
                        {'value': 'not_tested_precautionary',
                         'label': 'Test/hesap yapılmadı — geçici ihtiyatlı H220 (revizyon şartıyla)',
                         'effect': 'H220 atanır; Bölüm 16\'ya "test bekliyor" notu düşülür'},
                    ],
                    'legal_basis': 'SEA Ek-1 2.2 (Tablo 2.2.1)',
                    'components': [f"{c.get('cas') or c.get('cas_no') or ''} — {_nm(c)}" for c in _flam],
                })

        # Oksitleyici gaz (H270) — SEA Ek-1 2.4: karışım havadan daha oksitleyiciyse (ISO 10156 5.3 oksitleme gücü
        # > %23,5). Önceki "≥ %1 oksitleyici bileşen" kuralı sentetik havaya (%21 O2) bile H270 veriyordu.
        # Sıra: kullanıcının test/hesap sonucu → ISO 10156 hesabı → hesap yapılamıyorsa karar sorusu.
        if not (test_data.get('oxidizing_gas') or '').strip():
            _ox = iso10156.evaluate_oxidizing(comps)
            if _ox['status'] == 'calculated':
                _iso_ox = _ox
                if _ox['oxidizing']:
                    extra.append({'type': 'ox_gas', 'h': 'H270', 'h_class': 'Ox. Gas 1', 'signal': 'Danger',
                                  'source': f"{_ox['text']} — parametreler: {_ox['source']}",
                                  'cutoff_used': _ox['text']})
            elif _ox['status'] == 'not_applicable':
                pending_decisions.append({
                    'code': 'PHYS_OX_GAS_UNTESTED',
                    'field': 'oxidizing_gas',
                    'question': ('Gaz karışımında oksitleyici gaz bileşeni var. SEA Ek-1 2.4 gereği karışımın '
                                 'havadan daha oksitleyici olup olmadığı test veya ISO 10156 hesabıyla belirlenir — '
                                 f"bileşenin varlığı yeterli değildir. Program hesabı yapamadı: {_ox['reason']}. "
                                 'Sonucu seçin.'),
                    'test_guidance': ('ISO 10156: oksitleme gücü OP = Σ xᵢCᵢ / (Σ xᵢ + Σ KₖBₖ) > %23,5 ise '
                                      'oksitleyici gaz (Kategori 1). Gaz tedarikçisinin GBF\'sinde genellikle yer alır.'),
                    'options': [
                        {'value': 'H270', 'label': 'Test / ISO 10156 sonucu — oksitleyici gaz (H270)',
                         'effect': 'H270 → GHS03, Tehlike'},
                        {'value': 'not_oxidizing', 'label': 'Test / ISO 10156 sonucu — oksitleyici değil',
                         'effect': 'H270 atanmaz; Bölüm 16\'ya gerekçe yazılır'},
                        {'value': 'not_tested_precautionary',
                         'label': 'Test/hesap yapılmadı — geçici ihtiyatlı H270 (revizyon şartıyla)',
                         'effect': 'H270 atanır; Bölüm 16\'ya "test bekliyor" notu düşülür'},
                    ],
                    'legal_basis': 'SEA Ek-1 2.4 (Tablo 2.4.1)',
                })

        # H280/H281 — Basınçlı kap (CLP Ek-I §2.5, Tablo 2.5.1)
        # Gaz formu = ≥200 kPa gauge ambalaj → H280 zorunlu (ambalaj özelliği, içerikten bağımsız)
        # Alt kategori (SEA Ek-1 Tablo 2.5.1): sıkıştırılmış / sıvılaştırılmış / soğutulmuş
        # sıvılaştırılmış / çözünmüş — GBF 2.1'de belirtilir, taşımada B.B.B. girişini belirler.
        gas_type = test_data.get('gas_type') or ('refrigerated' if test_data.get('cryo_gas') else None)
        is_cryo = gas_type == 'refrigerated'
        _pg_cls = {'compressed': 'Press. Gas (Comp.)', 'liquefied': 'Press. Gas (Liq.)',
                   'refrigerated': 'Press. Gas (Ref. Liq.)', 'dissolved': 'Press. Gas (Diss.)'}
        extra.append({
            'type':        'press_gas',
            'h':           'H281' if is_cryo else 'H280',
            'h_class':     _pg_cls.get(gas_type, 'Press. Gas'),
            'signal':      'Warning',
            'source':      'Gaz formu — CLP Ek-I §2.5 Tablo 2.5.1',
            'cutoff_used': ('Gaz formundaki tüm ürünlere uygulanır (≥200 kPa gauge @20°C)'
                            + ('' if gas_type else ' — gaz türü seçilmedi')),
        })

    if form in ('solid', 'powder'):
        # H228 — alevlenir katı. SEA Ek-1 2.7 (Tablo 2.7.1): yalnız yanma hızı testiyle (UN N.1) belirlenir;
        # bileşen oranından hesaplama / köprüleme yöntemi yoktur. Önceden ≥ %1 H228 bileşen → otomatik H228
        # veriliyordu (örn. %2 karbon siyahı → H228 + ADR 4.1). Artık karar sorusu; alevlenir bileşen yoksa
        # sınıflandırma gerekmez (SEA Md.16(2)(a)).
        fs = []
        for c in comps:
            cas  = (c.get('cas') or c.get('cas_no') or '').strip()
            conc = float(c.get('concMax') or c.get('conc') or 0)
            if conc <= 0:
                continue
            _chip_h = {(h.get('h_code') or '').replace('*', '').strip()[:4]
                       for h in (c.get('hazards') or [])}
            # Yalnız bileşen kaydındaki H228. Elle liste kaldırıldı: karbon siyahı Ek-6'da yok, beyaz fosfor
            # Ek-6'da piroforik katı (H250) — alevlenir katı değil (2026-10-08 tablo denetimi).
            if 'H228' in _chip_h:
                fs.append(c)
        if fs and not (test_data.get('flammable_solid') or '').strip():
            _fs_src = ', '.join(
                f"{c.get('name') or c.get('cas','')} (%{float(c.get('concMax') or c.get('conc') or 0):g})"
                for c in fs
            )
            pending_decisions.append({
                'code': 'PHYS_FLAM_SOL_UNTESTED',
                'field': 'flammable_solid',
                'question': (
                    f'Karışımda alevlenir katı bileşen var: {_fs_src}. SEA Ek-1 2.7 gereği alevlenir katı '
                    'sınıflandırması yalnız yanma hızı testi (UN N.1) sonucuna dayanır — bileşen oranından '
                    'hesaplanmaz. Test sonucunu veya kararınızı seçin.'
                    # SEA Ek-1 2.7.1: "kolay yanabilen katılar ... toz halinde, granüler halde veya macun kıvamındaki"
                    + (' Not: SEA Ek-1 2.7.1 tanımındaki kolay yanabilen katılar toz, granül veya macun hâlindeki '
                       'ürünlerdir; ürün tablet / blok hâlinde piyasaya arz ediliyorsa testin uygulanabilirliğini '
                       'değerlendirin (sürtünmeyle yangına neden olma ayrıca değerlendirilir).'
                       if form_sub in ('tablet', 'block') else '')),
                'test_guidance': (
                    'UN Test ve Kriterler El Kitabı 33.2.1 (N.1): yanma süresi < 45 s veya yanma hızı > 2,2 mm/s; '
                    'ıslak bölge alevi söndüremiyorsa Kategori 1, en az 4 dakika durduruyorsa Kategori 2 '
                    '(metal tozları: tüm numuneye yayılma ≤ 5 dk Kat.1, 5–10 dk Kat.2) — SEA Ek-1 Tablo 2.7.1.'),
                'options': [
                    {'value': 'H228_cat1', 'label': 'Test yapıldı — Kategori 1 (Alev. Katı 1)',
                     'effect': 'H228 → GHS02, Tehlike, Bölüm 14: Sınıf 4.1'},
                    {'value': 'H228_cat2', 'label': 'Test yapıldı — Kategori 2 (Alev. Katı 2)',
                     'effect': 'H228 → GHS02, Dikkat, Bölüm 14: Sınıf 4.1'},
                    {'value': 'not_flammable_sol', 'label': 'Test yapıldı — alevlenir katı değil',
                     'effect': 'H228 atanmaz'},
                    {'value': 'not_tested_exclude', 'label': 'Test yapılmadı — uzman kararıyla sınıflandırılmamış',
                     'effect': "H228 atanmaz; Bölüm 16'ya gerekçe yazılır"},
                    {'value': 'not_tested_precautionary',
                     'label': 'Test yapılmadı — geçici ihtiyatlı H228, Kategori 1 (revizyon şartıyla)',
                     'effect': 'H228 atanır; Bölüm 16\'ya "test bekliyor" notu düşülür'},
                ],
                'legal_basis': 'SEA Ek-1 2.7 (Tablo 2.7.1) + SEA Md.10(2), Md.11(3)',
                'components': [f"{c.get('cas') or c.get('cas_no') or ''} — {c.get('name') or ''}" for c in fs],
            })

        # Toz patlaması — SEA'da zararlılık sınıfı değildir; KKDİK Ek-2 2.3 "diğer zararlar": toz patlaması
        # zararlılığı varsa "Eğer yayılırsa, patlayabilen toz-hava karışımı oluşabilir." Yanıcılık (organik / metal
        # toz) bileşimden otomatik bilinemez → KDU "Toz patlaması riski var" kutusuyla karar verir (2.3 ve 7.2).
        # Önceki uyarı AB ATEX direktifine atıf yapıyor ve yanmaz inorganik tozda da 7.2'ye patlama cümlesi
        # yazdırıyordu (2026-10-09).
        if form == 'powder' or form_sub in ('powder_fine', 'powder_nano'):
            warnings.append(
                'ℹ Toz ürün: yanıcı (organik veya metal) toz içeriyorsa havada dağıldığında patlayabilir. Bu durumda '
                'fiziksel özelliklerde "Toz patlaması riski var" kutusunu işaretleyin — GBF Bölüm 2.3\'e KKDİK Ek-2\'deki '
                'ifade ve Bölüm 7\'ye önlem yazılır. Toz patlaması SEA\'da ayrı bir zararlılık sınıfı değildir.')

        # Nano boyutlu toz — TR SEA ve KKDİK Ek-2'de nanoforma özel hüküm (ör. EUH212) yoktur
        if form_sub == 'powder_nano':
            warnings.append(
                'ℹ Nano boyutlu toz (< 1 µm): SEA ve KKDİK Ek-2\'de nanoformlara özel hüküm yoktur; maddenin '
                'sınıflandırması uygulanır. Nano boyuta özgü toksikoloji verisi varsa Bölüm 11\'e eklenmelidir.')

        # Oksitleyici katı — CLP Ek-I §2.14 gereği TEST (O.1) zorunlu; toplama yöntemi yok.
        # Bypass: bileşen ≥%90 + Ek-6 harmonize + diğer bileşenlerde fiziksel H kodu yok
        #         → uzman kararı ve delil ağırlığı (SEA Md.11(3), Ek-1 1.1.1) ile H kodu
        #           bileşenden devralınır. (Md.16(2)(b) içerik değişikliğine ilişkindir — dayanak değildir.)
        # Aksi: pending_decision — test sonucu veya uzman kararı istenir.
        # Test verisi test_data['oxidizing_solid'] üzerinden gelirse aşağıda _MANUAL_H_MAP işler.

        def _ox_sol_cat(c) -> int:
            return _ox_cat(c, OXIDIZING_SOLID_CAS)

        ox_sol_comps: list = []
        for c in comps:
            cat = _ox_sol_cat(c)
            if not cat:
                continue
            conc = float(c.get('concMax') or c.get('conc') or 0)
            if conc > 0:
                ox_sol_comps.append({
                    'cas':      c.get('cas') or c.get('cas_no') or '',
                    'name':     c.get('name') or c.get('cas') or '',
                    'conc':     conc,
                    'cat':      cat,
                    'annex_vi': bool(c.get('annex_vi') or c.get('sea_ek6')),
                    'index_no': c.get('index_no', ''),
                    '_comp':    c,
                })

        if ox_sol_comps and not test_data.get('oxidizing_solid'):
            # ── Bypass değerlendirmesi ────────────────────────────────────────────
            # Tek oksitleyici bileşen için üç koşul birlikte sağlanmalı:
            _bypass = False
            _bypass_comp = None
            if len(ox_sol_comps) == 1:
                _t = ox_sol_comps[0]
                _cond1 = _t['conc'] >= 90.0
                _cond2 = _t['annex_vi']   # Ek-6 harmonize kayıt zorunlu
                # Diğer bileşenlerde fiziksel H kodu (H220-H272) yok mu?
                _other_phys = False
                for _c in comps:
                    _cas_c = (_c.get('cas') or _c.get('cas_no') or '').strip()
                    if _cas_c == _t['cas']:
                        continue
                    _oh = {(h.get('h_code') or '')[:4] for h in (_c.get('hazards') or [])}
                    if _oh & _PHYS_H_SET:
                        _other_phys = True
                        break
                _cond3 = not _other_phys
                if _cond1 and _cond2 and _cond3:
                    _bypass = True
                    _bypass_comp = _t

            if _bypass and _bypass_comp:
                # Bypass: H kodu bileşenden devral, B16 notu üret
                _h_bypass = 'H271' if _bypass_comp['cat'] == 1 else 'H272'
                _cls_bypass = f"Ox. Sol. {_bypass_comp['cat']}"
                _sig_bypass = _ox_signal(_bypass_comp['cat'])
                _idx = _bypass_comp['index_no']
                extra.append({
                    'type':        'oxidizing_solid_bypass',
                    'h':           _h_bypass,
                    'h_class':     _cls_bypass,
                    'signal':      _sig_bypass,
                    'source':      f"{_bypass_comp['name']} %{_bypass_comp['conc']:.1f} (Ek-6 harmonize)",
                    'cutoff_used': (
                        f"Uzman kararı ve delil ağırlığı (SEA Md.11(3), Ek-1 1.1.1): bileşen ≥%90 + Ek-6 harmonize"
                        + (f" (İndeks No: {_idx})" if _idx else '')
                        + " + diğer bileşenler inert → H kodu bileşenden devralındı"
                    ),
                })
                warnings.append(
                    f'Oksitleyici katı ({_h_bypass}, Kategori {_bypass_comp["cat"]}): uzman kararı (SEA Md.11(3)) — '
                    f'{_bypass_comp["name"]} ≥%90, Ek-6 harmonize kayıt'
                    + (f' (İndeks No: {_idx})' if _idx else '')
                    + ', kalan bileşenler inert. '
                    'B16 notu: Karışım test edilmemiştir; bileşen ≥%90 ve Ek-6 uyumlaştırılmış '
                    'sınıflandırması temelinde uzman kararı ve delil ağırlığı (SEA Md.11(3), Ek-1 1.1.1) uygulanmıştır.'
                )
            else:
                # Bypass koşulları sağlanmadı → pending_decision
                _ox_comp_str = '; '.join(
                    f"{t['name']} %{t['conc']:.1f} (Ox.Sol.{t['cat']})" for t in ox_sol_comps
                )
                pending_decisions.append({
                    'code': 'PHYS_OX_SOL_UNTESTED',
                    'field': 'oxidizing_solid',
                    'question': (
                        f'Karışımda oksitleyici katı bileşen var: {_ox_comp_str}. '
                        'CLP Ek-I §2.14 gereği oksitleyici katı sınıflandırması yalnızca '
                        'test O.1 (yakma süresi kıyaslaması) sonucuna dayanır — '
                        'konsantrasyon toplama yöntemi mevzuatta tanımlı değildir. '
                        'Bu karışım için test sonucu girin veya uzman kararı verin.'
                    ),
                    'test_guidance': (
                        'Test O.1 (UN El Kitabı §34.4): karışım referans maddeyle kıyaslanarak '
                        'yakma süresi ölçülür. '
                        'Kategori 1 → alev referans maddeden hızlı yayılıyor; '
                        'Kategori 2 → referans maddeyle benzer; '
                        'Kategori 3 → referans maddeden yavaş ama oksitleyici sayılıyor. '
                        'Test yapılmadıysa uzman kararıyla sınıflandırılmamış veya '
                        'geçici ihtiyatlı H272 seçilebilir '
                        '(CLP Ek-I §1.6.3.2 — fiziksel tehlikeler için köprüleme ilkesi tanımlı değil).'
                    ),
                    'options': [
                        {'value': 'H271',
                         'label': 'Test yapıldı — Kategori 1 (Ox. Sol. 1)',
                         'effect': 'H271 → GHS03, Danger, B14: UN 1479 PG I'},
                        {'value': 'H272_cat2',
                         'label': 'Test yapıldı — Kategori 2 (Ox. Sol. 2)',
                         'effect': 'H272 → GHS03, Danger, B14: UN 1479 PG II'},
                        {'value': 'H272_cat3',
                         'label': 'Test yapıldı — Kategori 3 (Ox. Sol. 3)',
                         'effect': 'H272 → GHS03, Warning, B14: UN 1479 PG III'},
                        {'value': 'not_oxidizing',
                         'label': 'Test yapıldı — Oksitleyici değil',
                         'effect': 'H271/H272 atanmaz; B14 oksitleyici tehlike yok'},
                        {'value': 'not_tested_exclude',
                         'label': 'Test yapılmadı — uzman kararıyla sınıflandırılmamış',
                         'effect': 'H271/H272 atanmaz; B16\'ya gerekçe yazılır (uzman kararı — SEA Md.11(3))'},
                        {'value': 'not_tested_precautionary',
                         'label': 'Test yapılmadı — geçici ihtiyatlı H272, Kategori 2 (revizyon şartıyla)',
                         'effect': 'H272 atanır; B16\'ya "test bekliyor" notu düşülür'},
                    ],
                    'legal_basis': 'SEA Ek-1 2.14 (test O.1) + SEA Md.10(2), Md.11(3)',
                    'b16_note': (
                        'Oksitleyici katı sınıflandırması değerlendirilmemiştir '
                        '(UN O.1 testi mevcut değil; CLP Ek-I §1.6.3.2 gereği fiziksel tehlikeler '
                        'için köprüleme ilkesi tanımlı değildir).'
                    ),
                    'components': [
                        f"{t['cas']} — {t['name']} %{t['conc']:.1f}" for t in ox_sol_comps
                    ],
                })

    if form in ('liquid', 'paste'):
        # Oksitleyici sıvı — CLP Ek-I §2.13 gereği TEST (L.1/L.2) zorunlu; toplama yöntemi yok.
        # Bileşende H271/H272 varsa kullanıcıya test sonucu sorulur (pending_decision).
        # Test verisi test_data['oxidizing_liquid'] üzerinden gelirse aşağıda _MANUAL_H_MAP işler.
        def _ox_liq_cat(c) -> int:
            return _ox_cat(c, OXIDIZING_LIQ_CAS)

        def _ek6_ox_min(cas: str):
            """SEA Ek-6'da maddenin oksitleyici sınıfı için özel konsantrasyon sınırı varsa en düşüğü
            (örn. nitrik asit: Ox. Liq. 3 ≥ %65). Bu sınırın altında madde oksitleyici sayılmaz."""
            try:
                from app.services.substance_lookup import _load_sea_ek6
                _db = _load_sea_ek6() or {}
                _e = _db.get(cas) or {}
                if '_alias' in _e:
                    _e = _db.get(_e['_alias']) or {}
                _mins = [float(s['min']) for s in (_e.get('scl_limits') or [])
                         if s.get('h_code') in ('H271', 'H272') and s.get('min') is not None]
                return min(_mins) if _mins else None
            except Exception:
                return None

        ox_liq_triggers: list = []
        for c in comps:
            cat = _ox_liq_cat(c)
            if not cat:
                continue
            conc = float(c.get('concMax') or c.get('conc') or 0)
            _ox_min = _ek6_ox_min((c.get('cas') or c.get('cas_no') or '').strip())
            if _ox_min is not None and conc < _ox_min:
                continue   # Ek-6 SCL'nin altında — oksitleyici katkısı yok, test kararı sorulmaz
            if conc > 0:
                ox_liq_triggers.append({
                    'cas':      c.get('cas') or c.get('cas_no') or '',
                    'name':     c.get('name') or c.get('cas', ''),
                    'conc':     conc, 'cat': cat,
                    'annex_vi': bool(c.get('annex_vi') or c.get('sea_ek6')),
                    'index_no': c.get('index_no', ''),
                })

        if ox_liq_triggers and not test_data.get('oxidizing_liquid'):
            # ── Bypass değerlendirmesi (sıvı) ────────────────────────────────────
            _bypass_liq = False
            _bypass_liq_comp = None
            if len(ox_liq_triggers) == 1:
                _tl = ox_liq_triggers[0]
                _cl1 = _tl['conc'] >= 90.0
                _cl2 = bool(_tl.get('annex_vi'))
                _other_phys_liq = False
                for _c in comps:
                    _cas_c = (_c.get('cas') or _c.get('cas_no') or '').strip()
                    if _cas_c == _tl['cas']:
                        continue
                    _oh = {(h.get('h_code') or '')[:4] for h in (_c.get('hazards') or [])}
                    if _oh & _PHYS_H_SET:
                        _other_phys_liq = True
                        break
                if _cl1 and _cl2 and not _other_phys_liq:
                    _bypass_liq = True
                    _bypass_liq_comp = _tl

            if _bypass_liq and _bypass_liq_comp:
                _h_bl = 'H271' if _bypass_liq_comp['cat'] == 1 else 'H272'
                _cls_bl = f"Ox. Liq. {_bypass_liq_comp['cat']}"
                _sig_bl = _ox_signal(_bypass_liq_comp['cat'])
                _idx_l = _bypass_liq_comp.get('index_no', '')
                extra.append({
                    'type':        'oxidizing_liquid_bypass',
                    'h':           _h_bl,
                    'h_class':     _cls_bl,
                    'signal':      _sig_bl,
                    'source':      f"{_bypass_liq_comp['name']} %{_bypass_liq_comp['conc']:.1f} (Ek-6 harmonize)",
                    'cutoff_used': (
                        'Uzman kararı ve delil ağırlığı (SEA Md.11(3), Ek-1 1.1.1): bileşen ≥%90 + Ek-6 harmonize'
                        + (f' (İndeks No: {_idx_l})' if _idx_l else '')
                        + ' + diğer bileşenler inert → H kodu bileşenden devralındı'
                    ),
                })
                warnings.append(
                    f'Oksitleyici sıvı ({_h_bl}, Kategori {_bypass_liq_comp["cat"]}): uzman kararı (SEA Md.11(3)) — '
                    f'{_bypass_liq_comp["name"]} ≥%90, Ek-6 harmonize kayıt'
                    + (f' (İndeks No: {_idx_l})' if _idx_l else '')
                    + ', kalan bileşenler inert.'
                )
            else:
                _ox_liq_str = '; '.join(
                    f"{t['name']} %{t['conc']:.1f} (Ox.Liq.{t['cat']})" for t in ox_liq_triggers
                )
                # TODO: Sıvı oksitleyici pending çözüldükten sonra ADR PG ataması
                # ayrıca test sonucuna bağlıdır (UN L.1/L.2 → PG I/II/III).
                pending_decisions.append({
                    'code': 'PHYS_OX_LIQ_UNTESTED',
                    'field': 'oxidizing_liquid',
                    'question': (
                        f'Karışımda oksitleyici sıvı bileşen var: {_ox_liq_str}. '
                        'CLP Ek-I §2.13 gereği oksitleyici sıvı sınıflandırması yalnızca '
                        'test L.1/L.2 sonucuna dayanır — konsantrasyon toplama yöntemi '
                        'mevzuatta tanımlı değildir. '
                        'Bu karışım için test sonucu girin veya uzman kararı verin.'
                    ),
                    'test_guidance': (
                        'Test L.1/L.2 (UN El Kitabı §34.2): sıvı karışımın oksidatif gücü '
                        'referans maddeyle (nitrik asit %65) kıyaslanır. '
                        'Kategori 1 → basınç yükselme süresi referanstan kısa; '
                        'Kategori 2 → referansla benzer; '
                        'Kategori 3 → nitrik asit %40\'tan daha hızlı. '
                        'Test yapılmadıysa uzman kararıyla sınıflandırılmamış veya '
                        'geçici ihtiyatlı H272 seçilebilir (CLP Ek-I §1.6.3.2).'
                    ),
                    'options': [
                        {'value': 'H271',
                         'label': 'Test yapıldı — Kategori 1 (Ox. Liq. 1)',
                         'effect': 'H271 → GHS03, Danger, B14: UN 3139 PG I'},
                        {'value': 'H272_cat2',
                         'label': 'Test yapıldı — Kategori 2 (Ox. Liq. 2)',
                         'effect': 'H272 → GHS03, Danger, B14: UN 3139 PG II'},
                        {'value': 'H272_cat3',
                         'label': 'Test yapıldı — Kategori 3 (Ox. Liq. 3)',
                         'effect': 'H272 → GHS03, Warning, B14: UN 3139 PG III'},
                        {'value': 'not_oxidizing',
                         'label': 'Test yapıldı — Oksitleyici değil',
                         'effect': 'H271/H272 atanmaz; B14 oksitleyici tehlike yok'},
                        {'value': 'not_tested_exclude',
                         'label': 'Test yapılmadı — uzman kararıyla sınıflandırılmamış',
                         'effect': 'H271/H272 atanmaz; B16\'ya gerekçe yazılır (uzman kararı — SEA Md.11(3))'},
                        {'value': 'not_tested_precautionary',
                         'label': 'Test yapılmadı — geçici ihtiyatlı H272, Kategori 2 (revizyon şartıyla)',
                         'effect': 'H272 atanır; B16\'ya "test bekliyor" notu düşülür'},
                    ],
                    'legal_basis': 'SEA Ek-1 2.13 (test O.2) + SEA Md.10(2), Md.11(3)',
                    'b16_note': (
                        'Oksitleyici sıvı sınıflandırması değerlendirilmemiştir '
                        '(UN L.1/L.2 testi mevcut değil; CLP Ek-I §1.6.3.2 gereği fiziksel '
                        'tehlikeler için köprüleme ilkesi tanımlı değildir).'
                    ),
                    'components': [
                        f"{t['cas']} — {t['name']} %{t['conc']:.1f}" for t in ox_liq_triggers
                    ],
                })

    # Metallere aşındırıcılık (H290) — karışımda yalnızca test (UN C.1) ile belirlenir
    # (SEA Ek-1 §2.16); bileşen oranından hesaplanmaz. Karar sorusu: bileşende H290 varsa, ürünün
    # kendisi cilt aşındırıcı (H314) sınıflandırıldıysa ya da ürün pH'ı ≤ 2 / ≥ 11,5 ise. (Örn. sodyum
    # hidroksitin Ek-6 kaydında H290 yoktur; yalnız bileşen H290'ına bakıldığında soru çıkmıyordu.)
    if form != 'gas' and not test_data.get('metal_corrosive'):
        def _mc_h(c):
            return {(h.get('h_code') or '').replace('*', '').strip()[:4] for h in (c.get('hazards') or [])}
        _mc_comps = [
            f"{(c.get('name') or c.get('cas') or '')} %{float(c.get('concMax') or c.get('conc') or 0):g}"
            for c in comps
            if 'H290' in _mc_h(c)
            and float(c.get('concMax') or c.get('conc') or 0) > 0
        ]
        try:
            _mc_ph = float(str(mixture_ph).replace(',', '.')) if mixture_ph not in (None, '') else None
        except (TypeError, ValueError):
            _mc_ph = None
        _mc_ph_ext = _mc_ph is not None and (_mc_ph <= 2 or _mc_ph >= 11.5)
        if _mc_comps or _mc_ph_ext or mixture_skin_corr:
            _mc_why = []
            if _mc_comps:
                _mc_why.append(f"metallere aşındırıcı (H290) bileşen: {'; '.join(_mc_comps)}")
            if mixture_skin_corr:
                _mc_why.append('ürün cilt aşındırıcı (H314) olarak sınıflandırıldı')
            if _mc_ph_ext:
                _mc_why.append(f'ürün pH değeri {_mc_ph:g}')
            pending_decisions.append({
                'code': 'PHYS_MET_CORR_UNTESTED',
                'field': 'metal_corrosive',
                'question': (
                    f"Karışım metallere aşındırıcı olabilir — {' / '.join(_mc_why)}. "
                    'Karışımın H290 sınıfı bileşen oranından hesaplanmaz, yalnızca test '
                    '(UN C.1) sonucuyla belirlenir (SEA Ek-1 §2.16). Test sonucunu veya '
                    'kararınızı seçin.'
                ),
                'test_guidance': (
                    'Test UN C.1 (UN El Kitabı §37.4): çelik ve alüminyum levhada 55 °C\'de '
                    'yıllık aşınma 6,25 mm\'yi aşarsa H290 (Met. Corr. 1). '
                    'İpucu: güçlü baz (NaOH, KOH) veya güçlü asit içeren ürünlerde — özellikle '
                    'alüminyuma karşı — test genellikle pozitif çıkar; pH tek başına ölçüt değildir.'
                ),
                'options': [
                    {'value': 'H290',
                     'label': 'Test yapıldı — metal aşındırıcı (H290)',
                     'effect': 'H290 → GHS05, Warning'},
                    {'value': 'not_corrosive',
                     'label': 'Test yapıldı — metal aşındırıcı değil',
                     'effect': 'H290 atanmaz'},
                    {'value': 'not_tested_precautionary',
                     'label': 'Test yapılmadı — ihtiyatlı H290 (revizyon şartıyla)',
                     'effect': 'H290 atanır; Bölüm 16\'ya "test bekliyor" notu düşülür'},
                    {'value': 'not_tested_exclude',
                     'label': 'Test yapılmadı — uzman kararıyla sınıflandırılmamış',
                     'effect': 'H290 atanmaz; Bölüm 16\'ya gerekçe yazılır'},
                ],
                'legal_basis': 'SEA Ek-1 §2.16 (CLP Ek-I §2.16)',
                'components': _mc_comps,
            })

    # Özel fiziksel tehlike muafiyet/manuel giriş (kullanıcı beyanı)
    # oxidizing_solid/liquid: test sonucu gelirse burada işlenir;
    # 'not_oxidizing' ve 'not_tested_exclude' → H kodu atanmaz (h_map'te yok)
    # Uyarı kelimeleri SEA Ek-1 etiket tablolarından: Tablo 2.12.2 (su ile temas: Kat.1-2 Tehlike, Kat.3 Dikkat),
    # 2.13.2 / 2.14.2 (oksitleyici sıvı/katı: Kat.1-2 Tehlike, Kat.3 Dikkat), 2.15 (org. peroksit: A-D Tehlike,
    # E-F Dikkat), 2.11.2 (kendiliğinden ısınan), 2.2.3 (alevlenir gaz: Kat.1 Tehlike, Kat.2 Dikkat).
    # İhtiyatlı karar, aynı H kodunu veren en ağır kategoriyle verilir (H272 → Kat.2).
    _MANUAL_H_MAP = {
        'water_reactive':    {'H260': ('H260', 'Water React. 1',   'Danger'),
                              'H261_cat2': ('H261', 'Water React. 2', 'Danger'),
                              'H261_cat3': ('H261', 'Water React. 3', 'Warning'),
                              'H261': ('H261', 'Water React. 2',   'Danger')},   # kategorisiz eski değer → ağır olan
        'pyrophoric':        {'H250': ('H250', 'Pyr. Liq./Sol. 1', 'Danger')},
        'self_heating':      {'H251': ('H251', 'Self-heat. 1',     'Danger'),
                              'H252': ('H252', 'Self-heat. 2',     'Warning')},
        'metal_corrosive':   {'H290': ('H290', 'Met. Corr. 1',    'Warning'),
                              'not_tested_precautionary': ('H290', 'Met. Corr. 1 (ihtiyatlı)', 'Warning')},
        'organic_peroxide':  {'H240': ('H240', 'Org. Perox. Type A', 'Danger'),
                              'H241': ('H241', 'Org. Perox. Type B', 'Danger'),
                              'H242_CD': ('H242', 'Org. Perox. Type C/D', 'Danger'),
                              'H242_EF': ('H242', 'Org. Perox. Type E/F', 'Warning'),
                              'H242': ('H242', 'Org. Perox. Type C/D', 'Danger')},   # kategorisiz eski değer
        'oxidizing_solid':   {'H271':                    ('H271', 'Ox. Sol. 1',          'Danger'),
                              'H272_cat2':               ('H272', 'Ox. Sol. 2',          'Danger'),
                              'H272_cat3':               ('H272', 'Ox. Sol. 3',          'Warning'),
                              'not_tested_precautionary':('H272', 'Ox. Sol. 2',          'Danger')},
        'oxidizing_liquid':  {'H271':                    ('H271', 'Ox. Liq. 1',          'Danger'),
                              'H272_cat2':               ('H272', 'Ox. Liq. 2',          'Danger'),
                              'H272_cat3':               ('H272', 'Ox. Liq. 3',          'Warning'),
                              'not_tested_precautionary':('H272', 'Ox. Liq. 2',          'Danger')},
        'flammable_gas':     {'H220':                    ('H220', 'Flam. Gas 1',         'Danger'),
                              'H221':                    ('H221', 'Flam. Gas 2',         'Warning'),
                              'not_tested_precautionary':('H220', 'Flam. Gas 1',         'Danger')},
        'flammable_solid':   {'H228_cat1':               ('H228', 'Flam. Sol. 1',        'Danger'),
                              'H228_cat2':               ('H228', 'Flam. Sol. 2',        'Warning'),
                              'not_tested_precautionary':('H228', 'Flam. Sol. 1',        'Danger')},
        'oxidizing_gas':     {'H270':                    ('H270', 'Ox. Gas 1',           'Danger'),
                              'not_tested_precautionary':('H270', 'Ox. Gas 1',           'Danger')},
    }
    for field, h_map in _MANUAL_H_MAP.items():
        val = (test_data.get(field) or '').strip()
        if val and val != 'na' and val in h_map:
            h, h_class, signal = h_map[val]
            _test_n = {'metal_corrosive': 'UN C.1', 'oxidizing_liquid': 'UN L.1/L.2',
                       'oxidizing_solid': 'UN O.1', 'flammable_gas': 'EN 1839 / ISO 10156',
                       'oxidizing_gas': 'ISO 10156', 'flammable_solid': 'UN N.1'}.get(field, '')
            if val == 'not_tested_precautionary':
                _src = 'Test yapılmadı — ihtiyatlı sınıflandırma (kullanıcı kararı)'
                _cut = 'Test yapılmadı — ihtiyatlı sınıflandırma (bkz. Bölüm 16)'
            else:
                _cut = f'{_test_n} test sonucu (kullanıcı beyanı)' if _test_n else 'Test sonucu (kullanıcı beyanı)'
                _src = _cut
            extra.append({'type': f'manual_{field}', 'h': h, 'h_class': h_class,
                          'signal': signal, 'source': _src, 'cutoff_used': _cut})

    # Bölüm 16 sınıflandırma notları — test yerine verilen kararların gerekçesi
    _NOTE_NAMES = {
        'metal_corrosive':  ('Metallere aşındırıcılık (H290)', 'Corrosive to metals (H290)', 'UN C.1'),
        'oxidizing_liquid': ('Oksitleyici sıvı (H271/H272)', 'Oxidising liquid (H271/H272)', 'UN L.1/L.2'),
        'oxidizing_solid':  ('Oksitleyici katı (H271/H272)', 'Oxidising solid (H271/H272)', 'UN O.1'),
        'flammable_gas':    ('Alevlenir gaz (H220/H221)', 'Flammable gas (H220/H221)', 'EN 1839 / ISO 10156'),
        'oxidizing_gas':    ('Oksitleyici gaz (H270)', 'Oxidising gas (H270)', 'ISO 10156'),
        'flammable_solid':  ('Alevlenir katı (H228)', 'Flammable solid (H228)', 'UN N.1'),
    }
    classification_notes = []
    if fl.get('lit'):
        _lt = fl['lit']
        classification_notes.append({
            'TR': (f"Alevlenir sıvı: parlama noktası ürün için ölçülmemiştir; SEA Ek-1 2.6.4.1 uyarınca literatür "
                   f"değeri kullanılmıştır — {_lt['kaynak_tam']} ({_lt['yontem']}); hacimce %{_lt['vol']:g} "
                   f"{_lt['ad']} için " + (f"~{fl['fp']:g} °C." if fl['fp'] is not None else '> 60 °C.')),
            'EN': (f"Flammable liquid: the flash point was not measured on the product; a literature value was used "
                   f"— {_lt['kaynak_tam']} ({_lt['yontem']})."),
        })
    if fl.get('worst_case') and fl.get('result'):
        classification_notes.append({
            'TR': (f"Alevlenir sıvı ({fl['result']['h']}): ürünün parlama noktası ölçülmemiştir; sınıflandırma "
                   "bileşenlerin sınıflarına göre en kötü durum varsayımıyla (ihtiyatlı) yapılmıştır. SEA Yönetmeliği Md.10(2) uyarınca fiziksel zararlılığın belirlenmesinde yeterli ve güvenilir bilgi yoksa test yapılır; "
                   "parlama noktası kapalı kap yöntemiyle (SEA Ek-1 Tablo 2.6.3) ölçülmeli ve GBF test sonucuna göre "
                   "revize edilmelidir."),
            'EN': (f"Flammable liquid ({fl['result']['h']}): the flash point of the product has not been measured; "
                   "classified on a worst-case basis from the components. The flash point is to be measured "
                   "(closed cup) and the SDS revised accordingly."),
        })
    if fl.get('bp_worst') and fl.get('result'):
        classification_notes.append({
            'TR': ("Alevlenir sıvı: kaynama başlangıç noktası ölçülmemiş ve bileşen verisi yetersiz olduğundan "
                   "Kategori 1 / Kategori 2 ayrımında en kötü durum (≤ 35 °C) varsayılmıştır (SEA Ek-1 Tablo 2.6.1). "
                   "SEA Yönetmeliği Md.10(2) uyarınca fiziksel zararlılığın belirlenmesinde yeterli ve güvenilir bilgi yoksa test yapılır" + "; ölçüm sonucuna göre revize edilecektir."),
            'EN': ("Flammable liquid: the initial boiling point has not been measured; worst case (≤ 35 °C) assumed "
                   "for the Category 1 / 2 distinction. To be revised based on measurement."),
        })
    if fl.get('l2'):
        classification_notes.append({
            'TR': (f"Alevlenir sıvı: parlama noktası {fl['fp']:g} °C (35–60 °C aralığında); UN Test ve Kriterler El "
                   "Kitabı L.2 sürekli yanma testi olumsuz olduğundan SEA Ek-1 2.6.4.5 uyarınca Kategori 3 olarak "
                   "sınıflandırılmamıştır (kullanıcı beyanı)."),
            'EN': (f"Flammable liquid: flash point {fl['fp']:g} °C (35–60 °C); not classified in Category 3 as the "
                   "UN L.2 sustained combustibility test was negative (user declaration)."),
        })
    for field, (tr_n, en_n, test_n) in _NOTE_NAMES.items():
        val = (test_data.get(field) or '').strip()
        if val == 'not_tested_precautionary':
            classification_notes.append({
                'TR': f'{tr_n}: karışım test edilmemiştir ({test_n}); ihtiyatlı olarak sınıflandırılmıştır. '
                      'SEA Yönetmeliği Md.10(2) uyarınca fiziksel zararlılığın belirlenmesinde yeterli ve güvenilir bilgi yoksa test yapılır; test sonucuna göre revize edilecektir.',
                'EN': f'{en_n}: the mixture has not been tested ({test_n}); classified as a precaution. '
                      'To be revised based on test results.'})
        elif val == 'not_tested_exclude':
            classification_notes.append({
                'TR': f'{tr_n}: karışım test edilmemiştir ({test_n}); uzman değerlendirmesiyle '
                      'sınıflandırılmamıştır. SEA Yönetmeliği Md.10(2) uyarınca fiziksel zararlılığın belirlenmesinde yeterli ve güvenilir bilgi yoksa test yapılır.',
                'EN': f'{en_n}: the mixture has not been tested ({test_n}); not classified based on '
                      'expert judgement.'})
        elif val == 'not_flammable':
            classification_notes.append({
                'TR': f'{tr_n}: test (EN 1839) veya ISO 10156 hesabı sonucuna göre karışım alevlenir değildir '
                      '(tedarikçi beyanı).',
                'EN': f'{en_n}: the mixture is not flammable based on a test (EN 1839) or an ISO 10156 calculation '
                      '(supplier declaration).'})
        elif val in ('not_corrosive', 'not_oxidizing', 'not_flammable_sol'):
            classification_notes.append({
                'TR': f'{tr_n}: {test_n} test sonucuna göre sınıflandırılmamıştır (tedarikçi beyanı).',
                'EN': f'{en_n}: not classified based on {test_n} test result (supplier declaration).'})

    if _aerosol_untested:
        classification_notes.append({
            'TR': ('Alevlenir aerosol: aerosol alevlenirlik testleri (tutuşma mesafesi / kapalı ortam / köpük) '
                   "yapılmamıştır; %1'den fazla alevlenir bileşen içerdiğinden SEA Ek-1 2.3 notu gereği Kategori 1 "
                   'olarak sınıflandırılmıştır. Test sonucuna göre revize edilecektir.'),
            'EN': ('Flammable aerosol: aerosol flammability tests have not been performed; classified as Category 1 '
                   'as it contains more than 1 % flammable components. To be revised based on test results.')})

    # Gaz karışımı ISO 10156 hesabıyla değerlendirildiyse yöntem ve sonuç Bölüm 16'ya yazılır (Ek-2 16(ç))
    if _iso_gas:
        _sum_s = f"{_iso_gas['sum']:.2f}".replace('.', ',')
        if _iso_gas['flammable']:
            classification_notes.append({
                'TR': (f"Alevlenir gaz ({_iso_gas['h']}): ISO 10156:2017 hesap yöntemiyle sınıflandırılmıştır "
                       f"(Σ A'ᵢ/Tcᵢ = {_sum_s} > 1; parametreler: {_iso_gas['source']}). "
                       'Test (EN 1839) sonucu varsa test esastır.'),
                'EN': (f"Flammable gas ({_iso_gas['h']}): classified by the ISO 10156:2017 calculation method "
                       f"(Σ A'i/Tci = {_sum_s.replace(',', '.')} > 1). A test result (EN 1839) takes precedence.")})
        else:
            classification_notes.append({
                'TR': (f"Alevlenir gaz: ISO 10156:2017 hesabına göre karışım havada alevlenir değildir "
                       f"(Σ A'ᵢ/Tcᵢ = {_sum_s} ≤ 1; parametreler: {_iso_gas['source']}); sınıflandırılmamıştır. "
                       'Test (EN 1839) sonucu varsa test esastır.'),
                'EN': (f"Flammable gas: according to the ISO 10156:2017 calculation the mixture is not flammable "
                       f"in air (Σ A'i/Tci = {_sum_s.replace(',', '.')} ≤ 1); not classified. "
                       'A test result (EN 1839) takes precedence.')})

    if _iso_ox:
        _op_s = f"{_iso_ox['op']:g}".replace('.', ',')
        classification_notes.append({
            'TR': (f"Oksitleyici gaz: ISO 10156:2017 5.3 hesabına göre oksitleme gücü %{_op_s} "
                   + ('> %23,5 — Oks. Gaz 1 (H270) olarak sınıflandırılmıştır'
                      if _iso_ox['oxidizing'] else '≤ %23,5 — havadan daha oksitleyici değildir, sınıflandırılmamıştır')
                   + f" (parametreler: {_iso_ox['source']}). Test sonucu varsa test esastır."),
            'EN': (f"Oxidising gas: oxidising power per ISO 10156:2017 5.3 = {_iso_ox['op']:g} % "
                   + ('> 23.5 % — classified as Ox. Gas 1 (H270)' if _iso_ox['oxidizing']
                      else '≤ 23.5 % — not more oxidising than air, not classified')
                   + '. A test result takes precedence.')})

    # Teorik özellikler — yalnız en düşük bileşen kaynama noktası tahmini (karışım değerleri hesaplanmaz)
    theo_props = calc_theo_props(comps) or {}

    # Alevlenir gaz karışımının alt alevlenme sınırı — Le Chatelier (ISO 10156:2017 4.5); üst sınır bu yöntemle
    # hesaplanamaz (ISO 10156 4.5.1) → yalnız alt sınır yazılır
    if _iso_gas and _iso_gas.get('lm') is not None:
        theo_props['lel'] = {'value': _iso_gas['lm'], 'error': None, 'measured': False,
                             'method': 'Le Chatelier (ISO 10156:2017 4.5)', 'standard': 'ISO 10156:2017'}
        theo_props.pop('uel', None)

    # Bileşim %100'e tamamlanmamışsa (örn. su girilmemiş) karışım özellikleri yalnız girilen
    # bileşenlerden hesaplanır ve yanıltıcı olur (örn. %15 nitrik asitli sulu üründe 1,9 g/cm³) →
    # ölçüm girilmediyse Bölüm 9'a değer yazılmaz.
    _tot_conc = sum(float(c.get('concMax') or c.get('conc') or 0) for c in comps)
    if 0 < _tot_conc < 95:
        for _k, _v in list(theo_props.items()):
            if isinstance(_v, dict) and _v.get('value') is not None and not _v.get('measured'):
                theo_props[_k] = {
                    'value': None, 'display': 'Belirlenmemiştir', 'estimate': _v.get('value'),
                    'measured': False, 'estimate_only': True, 'method': '—', 'standard': '',
                    'note': (f'Bileşim toplamı %{_tot_conc:.0f} — %100\'e tamamlanmadığı için karışım '
                             'değeri hesaplanmaz (eksik bileşeni, örn. suyu ekleyin veya ölçüm girin).'),
                }
            elif isinstance(_v, dict) and _v.get('text') and not _v.get('measured'):
                theo_props[_k] = {**_v, 'text': None, 'value': None, 'display': 'Belirlenmemiştir',
                                  'estimate_only': True}

    # Aerosolde bileşen hesabı itici gazı (sıvılaştırılmış propan/bütan vb.) içermeyen sıvı karışım
    # formülleridir: buhar basıncı (kap içi basınç bar düzeyindeyken birkaç hPa), alevlenme sınırları (yalnız
    # çözücü), yoğunluk/viskozite/çözünürlük yanıltıcı olur → ölçüm girilmediyse Bölüm 9'a değer yazılmaz.
    if form == 'aerosol':
        for _k, _v in list(theo_props.items()):
            if not isinstance(_v, dict) or _v.get('measured'):
                continue
            if _v.get('value') is not None or _v.get('text'):
                theo_props[_k] = {**_v, 'text': None, 'value': None, 'display': 'Belirlenmemiştir',
                                  'estimate': _v.get('value'), 'measured': False, 'estimate_only': True,
                                  'method': '—', 'standard': '',
                                  'note': 'Aerosol: bileşen hesabı itici gazı kapsamadığından değer yazılmaz — '
                                          'kap içeriği için ölçüm girin.'}

    # Test verisi varsa üzerine yaz
    if test_data:
        _apply_test_data(theo_props, test_data)

    # Parlama noktasını ekle
    if test_data.get('flash_point') is not None:
        theo_props['flash_point'] = {
            'value': test_data['flash_point'], 'measured': True,
            'method': 'Kullanıcı girişi', 'standard': 'ISO 2719 / ASTM D93',
        }
    elif user_fp is not None:
        theo_props['flash_point'] = {
            'value': user_fp, 'measured': True, 'method': 'Kullanıcı beyanı', 'standard': '',
            'note': f"Sınıflandırma: {fl['result']['h_class']} ({fl['result']['h']})" if fl.get('result') else '',
        }
    elif fl.get('lit'):
        _lt = fl['lit']
        theo_props['flash_point'] = {
            'value': fl['fp'], 'display': (f"~{fl['fp']:g} °C" if fl['fp'] is not None else '> 60 °C'),
            'measured': False, 'method': 'Literatür değeri', 'standard': _lt['yontem'],
            'pdf_note': (f"literatür değeri (ürün test edilmemiştir) — {_lt['kaynak']}; {_lt['yontem']}; "
                         f"hacimce %{_lt['vol']:g} {_lt['ad']} için"),
            'note': fl['source'],
        }
    elif fl.get('declared_nonflam'):
        theo_props['flash_point'] = {
            'value': None, 'display': '> 60 °C', 'measured': True,
            'method': 'Kullanıcı beyanı', 'standard': '',
            'note': 'Test edildi — alevlenir sıvı değil (kullanıcı beyanı)',
        }
    elif fl['fp'] is not None:
        # En düşük bileşen FP'si karışımın FP'si değildir → Bölüm 9'a değer yazılmaz,
        # yalnızca bilgi amaçlı tahmin (estimate) taşınır.
        theo_props['flash_point'] = {
            'value': None, 'estimate': fl['fp'], 'display': 'Belirlenmemiştir',
            'measured': False, 'estimate_only': True,
            'method': fl['source'] or '', 'standard': '',
            'pdf_note': 'ölçülmedi — sınıflandırma bileşenlere göre en kötü durum varsayımıyla yapılmıştır',
            'note': (f"Tahmini en düşük (bileşen) değer ~{fl['fp']} °C — karışımın parlama noktası "
                     f"değildir. Sınıflandırma: {fl['result']['h_class']} ({fl['result']['h']}), en kötü durum."
                     if fl['result'] else ''),
        }

    # Kaynama noktası: en düşük bileşen KN'si karışımın başlangıç KN'si değildir → ölçülmediyse
    # Bölüm 9'a değer yazılmaz; tahmin yalnızca bilgi olarak taşınır.
    _bp = theo_props.get('boiling_point')
    if isinstance(_bp, dict) and not _bp.get('measured') and _bp.get('value') is not None:
        theo_props['boiling_point'] = {
            'value': None, 'estimate': _bp['value'], 'display': 'Belirlenmemiştir',
            'measured': False, 'estimate_only': True, 'method': _bp.get('method', ''), 'standard': '',
            'note': f"Tahmini (en düşük bileşen) ~{_bp['value']} °C — karışımın kaynama noktası değildir.",
        }

    fp_decision = {
        'required':    bool(fl.get('flam_components')) and user_fp is None
                       and test_data.get('flash_point') is None,
        'status':      fp_status or '',
        'worst_h':     fl.get('worst_h'),
        'estimate_fp': fl.get('fp'),
        'triggers':    [f"{t['name']} %{t['conc']:g}" for t in (fl.get('triggers') or [])],
        'needs_decision': bool(fl.get('needs_decision')),
        # SEA Ek-1 2.6.4.5: parlama noktası 35–60 °C → "UN L.2 sürekli yanma testi olumsuz" kararı seçilebilir
        'l2_possible': (fl.get('fp') is not None and 35 < float(fl['fp']) <= 60
                        and (bool(fl.get('lit')) or user_fp is not None)),
        'literature': bool(fl.get('lit')),
    }

    return {
        'fp_decision':         fp_decision,
        'classification_notes': classification_notes,
        'results':             primary + extra,
        'primary':             primary,
        'extra':               extra,
        'warnings':            warnings,
        'theo_props':          theo_props,
        'pending_decisions':   pending_decisions,
        'aerosol_flam':        _aer_info,
    }


def _apply_test_data(props: Dict, test_data: Dict) -> None:
    """Test/ölçülen verileri teorik değerlerin üzerine yaz (in-place)."""
    def meas(value, standard, note='Test verisinden alındı.'):
        return {'value': value, 'measured': True,
                'method': 'Kullanıcı girişi (ölçülen/beyan değer)',
                'standard': standard, 'note': note, 'error': None}

    mapping = {
        'density':       ('density',       'ISO 2811 / ASTM D4052'),
        'boiling_point': ('boiling_point', 'ASTM D86 / ISO 3924'),
        'ph':            ('ph',            'ISO 4316 / ASTM E70'),
        'viscosity':     ('viscosity',     'ISO 3219 / ASTM D2196'),
        'solubility':    ('solubility',    'OECD 105'),
        'flash_point':   ('flash_point',   'ISO 2719 / ASTM D93'),
        'vapor_pressure':('vapor_pressure','Raoult Yasası / OECD 104'),
    }
    for key, (prop, std) in mapping.items():
        if test_data.get(key) is not None:
            props[prop] = meas(test_data[key], std)

    # Yalnızca kullanıcı girer; (test_key, prop_key, std)
    for test_key, prop_key, std in [
        ('appearance',  'appearance',        'REACH Ek II §9'),
        ('odor',        'odor',              'Duyusal test'),
        ('melting_point','melting_point',    'ISO 1218 / ASTM D97'),
        ('auto_ignition','auto_ignition',    'EN 14522 / ASTM E659'),
        ('decomp_temp', 'decomposition_temp','ISO 11357 / DSC'),
        ('evap_rate',   'evap_rate',         'ASTM D3539'),
        ('log_kow',     'log_kow',           'OECD 117 / 107'),
    ]:
        if test_data.get(test_key) is not None:
            props[prop_key] = meas(test_data[test_key], std)


