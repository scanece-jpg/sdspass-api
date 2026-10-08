"""
Gaz karışımı alevlenirliği — ISO 10156:2017 hesap yöntemi (SEA Ek-1 2.2: test veya ISO 10156 hesabı).

  4.3  Alevlenirlik : A'ᵢ = Aᵢ / (ΣAᵢ + ΣKₖBₖ) · 100 ;  Σ A'ᵢ / Tcᵢ ≤ 1 → havada alevlenir değil
  4.5  Alt alevlenme sınırı (Le Chatelier, inert düzeltmeli Formül 6)
  4.7  Üst sınır hesaplanamaz → test yoksa alevlenir karışım Kategori 1
  EIGA Doc 169/26 2.2.2.1 Not 4: yalnız Kategori 2 gazları (amonyak, bromometan) içeren karışım Kategori 2

Parametreler data/iso10156_gas_data.json'da (kaynak revizyonu ve doğrulama tarihiyle). Tabloda olmayan bileşen,
oksitleyici gaz (ISO 10156 bölüm 6 ayrı yöntem) veya kısmen halojenli hidrokarbon sınırı aşılırsa hesap yapılmaz
→ çağıran taraf kullanıcıya karar sorusu sorar.
"""
import json
import os
from typing import Dict, List, Optional

_DATA: Optional[Dict] = None

# ISO 10156 Tablo 4 + oksijen (bölüm 6: oksijen/oksitleyici içeren karışım bu hesapla değerlendirilmez)
_OXIDIZER_CAS = {'7782-44-7', '10028-15-6', '7782-50-5', '7782-41-4', '10024-97-2', '10102-44-0',
                 '10102-43-9', '7783-54-2', '7790-91-2', '13637-63-3', '7789-30-2', '7783-41-7'}


def data() -> Dict:
    global _DATA
    if _DATA is None:
        path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'iso10156_gas_data.json')
        with open(path, encoding='utf-8') as f:
            _DATA = json.load(f)
    return _DATA


def source_label() -> str:
    """Örn. 'ISO 10156:2017 (Edition 4 (2017-07)); EIGA Doc 169 (169/26 (Nisan 2026))'"""
    return '; '.join(f"{k['ad']} ({k['revizyon']})" for k in data()['kaynaklar'])


def _f(x) -> str:
    return f'{x:.2f}'.rstrip('0').rstrip('.').replace('.', ',')


def evaluate(comps: List[Dict]) -> Dict:
    """
    Dönüş:
      {'status': 'no_flammable'}                         — alevlenir bileşen yok (hesap gerekmez)
      {'status': 'not_applicable', 'reason': str}         — hesap yapılamaz (karar sorusu sorulmalı)
      {'status': 'calculated', 'flammable': bool, 'sum': float, 'lm': float|None, 'h': 'H220'|'H221'|None,
       'h_class': str|None, 'text': str, 'source': str}
    """
    d = data()
    flam_tab, kk_tab = d['alevlenir'], d['kk_inert']
    halo_tab, cat2 = d['kismen_halojenli'], d['kategori2_gazlar']

    flam, inert, halo, unknown, oxid = [], [], [], [], []
    total = 0.0
    for c in comps:
        cas = (c.get('cas') or c.get('cas_no') or '').strip()
        c_max = float(c.get('concMax') or c.get('conc') or 0)
        if c_max <= 0:
            continue
        c_min = float(c.get('conc_min') or c.get('concMin') or c_max)
        total += c_max
        name = c.get('name_tr') or c.get('name') or cas
        hs = {(h.get('h_code') or '').replace('*', '').strip()[:4] for h in (c.get('hazards') or [])}
        if cas in flam_tab:
            flam.append({'cas': cas, 'name': name, 'a': c_max, **flam_tab[cas]})
        elif cas in _OXIDIZER_CAS or 'H270' in hs:
            oxid.append(name)
        elif cas in kk_tab:
            inert.append({'cas': cas, 'name': name, 'b': c_min, 'kk': kk_tab[cas]['kk']})
        elif cas in halo_tab:
            halo.append({'cas': cas, 'name': name, 'b': c_min, 'kk': 1.5})
        else:
            unknown.append({'name': name, 'cas': cas, 'flam_h': bool(hs & {'H220', 'H221', 'H222', 'H223'})})

    if not flam and not any(u['flam_h'] for u in unknown):
        return {'status': 'no_flammable'}
    if oxid:
        return {'status': 'not_applicable',
                'reason': (f"karışımda oksitleyici gaz var ({', '.join(oxid)}) — ISO 10156 4.3 hesabı uygulanmaz "
                           '(oksijen/oksitleyici içeren karışımlar için ISO 10156 bölüm 6)')}
    if unknown:
        return {'status': 'not_applicable',
                'reason': ('ISO 10156 / EIGA Doc 169 tablolarında parametresi olmayan bileşen: '
                           + ', '.join(f"{u['name']} ({u['cas'] or 'CAS yok'})" for u in unknown))}
    if not 95 <= total <= 105:
        return {'status': 'not_applicable',
                'reason': f'bileşim toplamı %{_f(total)} — hesap için gaz bileşimi %100\'e tamamlanmalı'}
    _halo_sum = sum(h['b'] for h in halo)
    _flam_sum = sum(f['a'] for f in flam)
    if halo and _halo_sum > 0.5 and _flam_sum > 0.25:
        return {'status': 'not_applicable',
                'reason': (f"kısmen halojenli hidrokarbon ({', '.join(h['name'] for h in halo)}) > %0,5 ve "
                           'alevlenir bileşen > %0,25 — ISO 10156 Tablo 1 notu gereği hesap yöntemi uygulanmaz')}
    inert = inert + halo     # sınır altında: ≥3 atomlu alevlenmez gaz → Kk 1,5 (ISO 10156 Tablo 1 notu)

    # 4.3 — eşdeğer içerik ve alevlenirlik toplamı (kötü durum: alevlenir üst, inert alt konsantrasyon)
    sum_a = _flam_sum
    sum_kb = sum(i['kk'] * i['b'] for i in inert)
    denom = sum_a + sum_kb
    s = sum((f['a'] / denom * 100) / f['tci'] for f in flam) if denom > 0 else 0.0
    flammable = s > 1.0

    parts = ' + '.join(f"{_f(f['a'] / denom * 100)}/{_f(f['tci'])}" for f in flam)
    inert_txt = ', '.join(f"{i['name']} Kk={_f(i['kk'])}" for i in inert) or 'yok'
    text = (f"ISO 10156:2017 4.3 hesabı: Σ A'ᵢ/Tcᵢ = {parts} = {_f(s)} "
            f"{'> 1 → havada alevlenir' if flammable else '≤ 1 → havada alevlenir değil'} "
            f"(inert eşdeğerlik: {inert_txt})")

    res = {'status': 'calculated', 'flammable': flammable, 'sum': round(s, 3), 'lm': None,
           'h': None, 'h_class': None, 'text': text, 'source': source_label()}
    if not flammable:
        return res

    # 4.5 — alt alevlenme sınırı: yalnız alevlenir kısmın LM'si (Formül 4) → inert düzeltmesi (Formül 6)
    lm0 = 100.0 / sum((f['a'] / sum_a * 100) / f['li'] for f in flam)
    sum_b = sum(i['b'] for i in inert)
    k_bar = (sum_kb / sum_b) if sum_b > 0 else 1.0
    corr = (100 - lm0 - (1 - k_bar) * (sum_b / sum_a) * lm0) / (100 - lm0)
    lm = 100.0 / sum(f['a'] / (f['li'] * corr) for f in flam)
    res['lm'] = round(lm, 1)

    if all(f['cas'] in cat2 for f in flam):
        res.update(h='H221', h_class='Flam. Gas 2')
        res['text'] += ('; yalnız Kategori 2 alevlenir gaz içerdiğinden Kategori 2 (EIGA Doc 169 2.2.2.1)')
    else:
        res.update(h='H220', h_class='Flam. Gas 1')
        res['text'] += (f"; alt alevlenme sınırı ≈ %{_f(round(lm, 1))} (Le Chatelier, ISO 10156 4.5); üst sınır "
                        'hesaplanamadığından Kategori 1 (ISO 10156 4.7)')
    return res


def evaluate_oxidizing(comps: List[Dict]) -> Dict:
    """
    Oksitleyici gaz (SEA Ek-1 2.4, H270) — ISO 10156:2017 5.3 Formül 7:
      OP = Σ xᵢCᵢ / (Σ xᵢ + Σ KₖBₖ) ;  OP > %23,5 → havadan daha oksitleyici → Ox. Gas 1 (H270)
    Dönüş: {'status': 'no_oxidizer'} | {'status': 'not_applicable', 'reason'} |
           {'status': 'calculated', 'oxidizing': bool, 'op': float (%), 'text', 'source'}
    """
    d = data()
    ci_tab, kk_tab, flam_tab = d['ci_oksitleyici'], d['kk_inert'], d['alevlenir']
    limit = float(d.get('oksitleyici_esik_yuzde', 23.5))

    ox, inert, unknown, flam = [], [], [], []
    total = 0.0
    for c in comps:
        cas = (c.get('cas') or c.get('cas_no') or '').strip()
        c_max = float(c.get('concMax') or c.get('conc') or 0)
        if c_max <= 0:
            continue
        c_min = float(c.get('conc_min') or c.get('concMin') or c_max)
        total += c_max
        name = c.get('name_tr') or c.get('name') or cas
        hs = {(h.get('h_code') or '').replace('*', '').strip()[:4] for h in (c.get('hazards') or [])}
        if cas in ci_tab:
            ox.append({'name': name, 'x': c_max, 'ci': ci_tab[cas]['ci']})
        elif 'H270' in hs or cas in _OXIDIZER_CAS:
            unknown.append(f'{name} ({cas or "CAS yok"}) — Ci değeri tabloda yok')
        elif cas in flam_tab or hs & {'H220', 'H221', 'H222', 'H223'}:
            flam.append(name)
        elif cas in kk_tab:
            inert.append({'name': name, 'b': c_min, 'kk': kk_tab[cas]['kk']})
        else:
            unknown.append(f'{name} ({cas or "CAS yok"})')

    if not ox and not any('Ci değeri' in u for u in unknown):
        return {'status': 'no_oxidizer'}
    if flam:
        return {'status': 'not_applicable',
                'reason': (f"karışımda oksitleyici ve alevlenir gaz birlikte var ({', '.join(flam)}) — "
                           'ISO 10156 bölüm 6 (oksijen + alevlenir gaz) test/uzman değerlendirmesi gerektirir')}
    if unknown:
        return {'status': 'not_applicable',
                'reason': 'ISO 10156 / EIGA Doc 169 tablolarında parametresi olmayan bileşen: ' + ', '.join(unknown)}
    if not 95 <= total <= 105:
        return {'status': 'not_applicable',
                'reason': f'bileşim toplamı %{_f(total)} — hesap için gaz bileşimi %100\'e tamamlanmalı'}

    sum_x = sum(o['x'] for o in ox)
    denom = sum_x + sum(i['kk'] * i['b'] for i in inert)
    op = sum(o['x'] * o['ci'] for o in ox) / denom * 100 if denom > 0 else 0.0
    oxidizing = op > limit
    parts = ' + '.join(f"{_f(o['x'])}×{_f(o['ci'])}" for o in ox)
    inert_txt = ', '.join(f"{i['name']} Kk={_f(i['kk'])}" for i in inert) or 'yok'
    text = (f"ISO 10156:2017 5.3 hesabı: oksitleme gücü OP = ({parts}) / {_f(denom)} = %{_f(round(op, 1))} "
            f"{'>' if oxidizing else '≤'} %{_f(limit)} → "
            f"{'havadan daha oksitleyici (Oks. Gaz 1)' if oxidizing else 'havadan daha oksitleyici değil'} "
            f"(inert eşdeğerlik: {inert_txt})")
    return {'status': 'calculated', 'oxidizing': oxidizing, 'op': round(op, 1), 'text': text,
            'source': source_label()}
