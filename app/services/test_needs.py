"""
Test ihtiyacı listesi — ürün için hangi fiziksel/kimyasal verinin ölçülmesi gerektiği, yönetmelik gerekçesiyle.

İki ayrı yükümlülük karıştırılmaz:
  • GBF yükümlülüğü (KKDİK Ek-2 Bölüm 9.1): her özellik yazılır; "belirli bir özelliğe dair bilgilerin mevcut
    olmadığı belirtilmiş ise, nedenleri belirtilir" — test şartı yoktur.
  • Test yükümlülüğü (SEA Md.10(2)): "fiziksel zararlılık arz edip etmediğinin belirlenmesinde yeterli ve güvenilir
    bilgilerin mevcut olmadığı durumda … ek-1'in ikinci bölümünde belirtilen testleri yapar." Sağlık/çevre için
    Md.10(1) "yeni testler yapabilir" (isteğe bağlı); hayvan deneyi yalnız alternatif yoksa (Md.9(1)).

Gruplar:
  siniflandirma — sınıflandırmayı değiştirir; veri yoksa ölçüm/test gerekir (SEA Md.10(2) veya Ek-1 kriteri)
  rutin         — sınıflandırmayı değiştirmez ama kolay/ucuz ölçülür; GBF Bölüm 9'da yazılır
  gerekmez      — test gerekmez; veri yoksa Bölüm 9'a "veri yok" + nedeni yazılır (KKDİK Ek-2 9.1)

Liste yalnız panelde gösterilir; GBF'ye yazılmaz.
"""
from typing import Dict, List

WATER_CAS = '7732-18-5'

_EK2 = 'KKDİK Ek-2 Bölüm 9.1'
_MD10_2 = 'SEA Md.10(2)'

# Fiziksel tehlike karar soruları (physical_engine pending_decisions 'field') → liste satırı
_DECISION_ROWS = {
    'flammable_gas':     ('Alevlenirlik (gaz karışımı)', 'EN 1839 testi veya ISO 10156 hesabı',
                          'SEA Ek-1 2.2 (ilave sınıflandırma kriterleri)'),
    'oxidizing_gas':     ('Oksitleyicilik (gaz karışımı)', 'ISO 10156 oksitleme gücü hesabı/testi',
                          'SEA Ek-1 2.4 (Tablo 2.4.1)'),
    'flammable_aerosol': ('Aerosol alevlenirliği', 'UN Test ve Kriterler El Kitabı 31.4 / 31.5 / 31.6',
                          'SEA Ek-1 2.3'),
    'flammable_solid':   ('Alevlenir katı', 'UN N.1 yanma hızı testi', 'SEA Ek-1 2.7 (Tablo 2.7.1)'),
    'oxidizing_solid':   ('Oksitleyici katı', 'UN O.1 testi', 'SEA Ek-1 2.14'),
    'oxidizing_liquid':  ('Oksitleyici sıvı', 'UN O.2 testi', 'SEA Ek-1 2.13'),
    'metal_corrosive':   ('Metallere aşındırıcılık', 'UN C.1 testi', 'SEA Ek-1 2.16'),
}


def _hset(c: dict) -> set:
    return {(h.get('h_code') or '').replace('*', '').strip()[:4] for h in (c.get('hazards') or [])}


def _conc(c: dict) -> float:
    try:
        return float(c.get('concMax') or c.get('conc') or 0)
    except (TypeError, ValueError):
        return 0.0


def _row(grup, ozellik, durum, durum_metni, neden, dayanak, yontem='', alan=''):
    return {'grup': grup, 'ozellik': ozellik, 'durum': durum, 'durum_metni': durum_metni,
            'neden': neden, 'dayanak': dayanak, 'yontem': yontem, 'alan': alan}


def build(form: str, comps: List[Dict], phys_res: Dict, test_data: Dict = None,
          user_fp=None, user_bp=None, fp_status: str = '', mixture_ph=None) -> List[Dict]:
    from app.services.physical_engine import _calc_asp_tox

    td = test_data or {}
    form = form or 'liquid'
    comps = [c for c in (comps or []) if _conc(c) > 0]
    liquid = form in ('liquid', 'paste')
    solid = form in ('solid', 'powder')
    gas = form == 'gas'
    has_water = any((c.get('cas') or c.get('cas_no') or '').strip() == WATER_CAS for c in comps)
    all_h = set().union(*[_hset(c) for c in comps]) if comps else set()
    results = phys_res.get('results') or []
    res_h = {r.get('type'): r.get('h') for r in results}
    fd = phys_res.get('fp_decision') or {}
    rows: List[Dict] = []

    # ── 1. Sınıflandırma için gerekli ──────────────────────────────────────────
    if liquid:
        flam_h = res_h.get('flam_liq')
        if user_fp is not None or td.get('flash_point') is not None:
            rows.append(_row('siniflandirma', 'Parlama noktası', 'tamam', 'Ölçülen değer girildi',
                             'Alevlenir sıvı kategorisi parlama noktasına göre belirlenir.',
                             'SEA Ek-1 Tablo 2.6.1', 'Kapalı kap (SEA Ek-1 Tablo 2.6.3)', 'tf_fp'))
        elif fp_status == 'not_flammable':
            rows.append(_row('siniflandirma', 'Parlama noktası', 'tamam', 'Test edildi — alevlenir değil (beyan)',
                             'Test sonucu beyan edildi.', 'SEA Ek-1 Tablo 2.6.1',
                             'Kapalı kap (SEA Ek-1 Tablo 2.6.3)', 'tf_fp'))
        elif fd.get('literature'):
            rows.append(_row('siniflandirma', 'Parlama noktası', 'tamam', 'Literatür değeri — test gerekmez',
                             'Su + tek alevlenir bileşen için ölçülmüş literatür değeri kullanıldı.',
                             'SEA Ek-1 2.6.4.1 ("veriler literatürden bulunabilir")',
                             'Literatür (kapalı kap)', 'tf_fp'))
        elif fd.get('required'):
            _trg = ', '.join(fd.get('triggers') or [])
            rows.append(_row(
                'siniflandirma', 'Parlama noktası', 'eksik', 'ÖLÇÜLMELİ',
                (f"Alevlenir sıvı bileşen var ({_trg}). Ölçüm olmadığı için en kötü durum "
                 f"({fd.get('worst_h') or flam_h or 'alevlenir'}) uygulanıyor; ölçülen değer sınıfı "
                 'hafifletebilir veya kaldırabilir.'),
                f'{_MD10_2}; SEA Ek-1 2.6.4.1, Tablo 2.6.1',
                'Kapalı kap — Abel, Pensky-Martens, Tag vb. (SEA Ek-1 Tablo 2.6.3)', 'tf_fp'))
        else:
            rows.append(_row('gerekmez', 'Parlama noktası', 'bilgi', 'Sınıflandırma için gerekmez',
                             ('Alevlenir sıvı (H224–H226) bileşen yok. Bölüm 9\'a bilinen değer ya da '
                              '"veri yok" ve nedeni yazılır.'),
                             _EK2, '', 'tf_fp'))

        # Kat.1 / Kat.2 ayrımı: parlama noktası < 23 °C iken kaynama başlangıç noktası ≤ 35 °C → Kat.1
        if flam_h in ('H224', 'H225'):
            _bp_ok = user_bp is not None or td.get('boiling_point') is not None
            _bp_est = (phys_res.get('theo_props') or {}).get('boiling_point')
            _bp_est = _bp_est.get('estimate') if isinstance(_bp_est, dict) else None
            _kat12 = ('Parlama noktası < 23 °C olan sıvıda kaynama başlangıç noktası ≤ 35 °C ise Kategori 1 (H224), '
                      '> 35 °C ise Kategori 2 (H225).')
            if _bp_ok:
                rows.append(_row('siniflandirma', 'Kaynama başlangıç noktası', 'tamam', 'Ölçülen değer girildi',
                                 _kat12, 'SEA Ek-1 Tablo 2.6.1', 'SEA Ek-1 Tablo 2.6.4 yöntemleri', 'tf_bp'))
            elif flam_h == 'H225' and _bp_est is not None and float(_bp_est) > 35:
                rows.append(_row('rutin', 'Kaynama başlangıç noktası', 'kontrol', '',
                                 (_kat12 + f' En düşük bileşen kaynama noktası ~{float(_bp_est):g} °C (35 °C üstü) — '
                                  'Kategori 2 bileşen verisiyle destekleniyor; ölçüm Bölüm 9 (e) için önerilir.'),
                                 'SEA Ek-1 Tablo 2.6.1; ' + _EK2, 'SEA Ek-1 Tablo 2.6.4 yöntemleri', 'tf_bp'))
            else:
                rows.append(_row('siniflandirma', 'Kaynama başlangıç noktası', 'eksik', 'ÖLÇÜLMELİ',
                                 _kat12 + ' Bileşenlerin en düşük kaynama noktası karışımınki değildir.',
                                 'SEA Ek-1 Tablo 2.6.1', 'SEA Ek-1 Tablo 2.6.4 yöntemleri', 'tf_bp'))

        # SEA Ek-1 2.6.4.5 — L.2 sürekli yanma testi (isteğe bağlı; olumsuzsa Kat.3 gerekmez)
        if fd.get('l2_possible') and fp_status != 'l2_negative':
            rows.append(_row(
                'siniflandirma', 'Sürekli yanma testi (UN L.2)', 'istege_bagli', 'İsteğe bağlı',
                ('Parlama noktası 35–60 °C aralığında. L.2 testi olumsuz çıkarsa Kategori 3 (H226) '
                 'gerekmez; test yapılmazsa H226 kalır.'),
                'SEA Ek-1 2.6.4.5', 'UN Test ve Kriterler El Kitabı Kısım III, 32 (L.2)'))
        elif fp_status == 'l2_negative':
            rows.append(_row('siniflandirma', 'Sürekli yanma testi (UN L.2)', 'tamam', 'Olumsuz (beyan)',
                             'L.2 olumsuz beyan edildi — Kategori 3 uygulanmadı.', 'SEA Ek-1 2.6.4.5',
                             'UN Test ve Kriterler El Kitabı Kısım III, 32 (L.2)'))

        # Viskozite — H304 (SEA Ek-1 3.10.3.3.1: 40 °C'de ÖLÇÜLMÜŞ kinematik viskozite)
        asp_total = _calc_asp_tox(comps, {}).get('total') or 0
        visc_ok = td.get('viscosity') is not None
        if asp_total >= 10:
            if visc_ok:
                rows.append(_row('siniflandirma', 'Viskozite (40 °C, kinematik)', 'tamam', 'Ölçülen değer girildi',
                                 f'Aspirasyon zararlı (H304) bileşen toplamı %{asp_total:g} ≥ %10.',
                                 'SEA Ek-1 3.10.3.3.1', 'mm²/s, 40 °C (ör. ISO 3104)', 'tf_visc'))
            else:
                _now = ('H304 uygulanıyor' if res_h.get('asp_tox') else
                        'H304 şu an hesaplanmış viskoziteyle dışarıda bırakılıyor — bu bir ölçüm değildir')
                rows.append(_row(
                    'siniflandirma', 'Viskozite (40 °C, kinematik)', 'eksik', 'ÖLÇÜLMELİ',
                    (f'Aspirasyon zararlı (H304) bileşen toplamı %{asp_total:g} ≥ %10 ({_now}). Karar 40 °C\'de '
                     'ölçülmüş kinematik viskoziteye göre verilir: ≤ 20,5 mm²/s → H304. Oda sıcaklığında ölçülen '
                     'dinamik viskozite (mPa·s, Brookfield) bu karar için kullanılamaz.'),
                    'SEA Ek-1 3.10.3.3.1', 'mm²/s, 40 °C (ör. ISO 3104)', 'tf_visc'))
        else:
            rows.append(_row('rutin', 'Viskozite', 'kontrol', '',
                             'Bölüm 9 (o) akışkanlık. Sınıflandırmayı etkilemiyor (H304 bileşen toplamı < %10); '
                             'ürün spesifikasyonu ölçümü yeterli, ölçüm koşulu (sıcaklık, birim) belirtilir.',
                             _EK2, '', 'tf_visc'))

    # pH — SEA Ek-1 3.2.3.1.2 / 3.3.3.1.2: pH ≤ 2 veya ≥ 11,5 → başka bilgi yoksa Cilt Aşındırıcı 1 + Göz Hasarı 1
    if not gas:
        ph_ok = mixture_ph not in (None, '') or td.get('ph') not in (None, '')
        acid_base = bool(all_h & {'H314', 'H290'})
        if solid:
            _ph_neden = 'Bölüm 9 (ç): katı üründe sulu çözeltinin pH\'ı ve çözelti derişimi yazılır.'
        elif liquid and not has_water:
            _ph_neden = ('Bölüm 9 (ç). Su içermeyen üründe pH ölçülemiyorsa "uygulanamaz — sulu olmayan ürün" '
                         'yazılır.')
        else:
            _ph_neden = 'Bölüm 9 (ç): tedarik edildiği hâliyle pH.'
        if acid_base and (has_water or solid):
            rows.append(_row(
                'siniflandirma', 'pH', 'tamam' if ph_ok else 'eksik',
                'Ölçülen değer girildi' if ph_ok else 'ÖLÇÜN',
                ('Asit/baz (H314/H290) bileşen var. Başka bilgi yoksa pH ≤ 2 veya ≥ 11,5 olan karışım Cilt '
                 'Aşındırıcı Kat.1 ve Ciddi Göz Hasarı Kat.1 kabul edilir; pH ayrıca metallere aşındırıcılık '
                 'sorusunu da etkiler. ' + _ph_neden),
                'SEA Ek-1 3.2.3.1.2, 3.3.3.1.2; ' + _EK2, 'pH metre (katıda sulu çözelti, derişim belirtilir)',
                'tf_ph'))
        else:
            rows.append(_row('rutin', 'pH', 'kontrol', '', _ph_neden, _EK2,
                             'pH metre (katıda sulu çözelti, derişim belirtilir)', 'tf_ph'))

    # Fiziksel tehlike karar soruları (bekleyen) ve verilmiş kararlar
    pending = {d.get('field'): d for d in (phys_res.get('pending_decisions') or []) if d.get('field')}
    for field, (ad, yontem, dayanak) in _DECISION_ROWS.items():
        d = pending.get(field)
        if d:
            rows.append(_row('siniflandirma', ad, 'eksik', 'TEST GEREKLİ (veri yoksa)',
                             (d.get('question') or '').strip(),
                             f"{_MD10_2}; {d.get('legal_basis') or dayanak}",
                             d.get('test_guidance') or yontem))
            continue
        val = str(td.get(field) or '').strip()
        if not val:
            continue
        if val.startswith('not_tested'):
            _ihtiyat = 'ihtiyatlı sınıf atandı' if 'precaution' in val else 'uzman kararıyla sınıflandırılmadı'
            rows.append(_row('siniflandirma', ad, 'karar', f'Test yapılmadı — {_ihtiyat}',
                             ('Yeterli ve güvenilir bilgi yoksa test yapılır; mevcut karar geçicidir, '
                              'test sonucuyla GBF revize edilir.'),
                             f'{_MD10_2}; {dayanak}', yontem))
        else:
            rows.append(_row('siniflandirma', ad, 'tamam', 'Test sonucu beyan edildi', '', dayanak, yontem))

    # Gaz: ISO 10156 hesabı yapıldıysa test gerekmez (SEA Ek-1 2.2 ilave kriterler, 2.4 not)
    if gas:
        for field, hk, tur in (('flammable_gas', {'H220', 'H221'}, 'alevlenir'),
                               ('oxidizing_gas', {'H270'}, 'oksitleyici')):
            if field not in pending and not td.get(field):
                ad, _y, dayanak = _DECISION_ROWS[field]
                if all_h & hk:
                    rows.append(_row('siniflandirma', ad, 'tamam', 'ISO 10156 hesabıyla belirlendi — test gerekmez',
                                     'Bileşen verisi yeterli; karışım ISO 10156\'ya göre hesaplandı.', dayanak,
                                     'ISO 10156 hesabı'))
                else:
                    rows.append(_row('gerekmez', ad, 'bilgi', 'Test gerekmez',
                                     f'Karışımda {tur} gaz bileşeni yok.', dayanak))
        _gt = bool(td.get('gas_type'))
        rows.append(_row('siniflandirma', 'Basınç altındaki gaz alt kategorisi', 'tamam' if _gt else 'eksik',
                         'Seçildi' if _gt else 'SEÇİN',
                         ('Sıkıştırılmış / sıvılaştırılmış / soğutulmuş / çözünmüş ayrımı için 50 °C buhar basıncı, '
                          '20 °C fiziksel hal ve kritik sıcaklık gerekir; bunlar literatürden alınabilir.'),
                         'SEA Ek-1 2.5 (ilave sınıflandırma kriterleri)', 'Literatür / test'))

    # ── 2. Rutin (kolay, ölçün) ───────────────────────────────────────────────
    rows.append(_row('rutin', 'Görünüm (fiziksel hal) ve renk', 'kontrol', '',
                     'Bölüm 9 (a): tedarik edildiği fiziksel hal ve renk.', _EK2, 'Gözle', 'tf_appearance'))
    rows.append(_row('rutin', 'Koku', 'kontrol', '',
                     'Bölüm 9 (b): koku algılanabiliyorsa kısa tarifi.', _EK2, 'Duyusal', 'tf_odor'))
    if not gas:
        rows.append(_row('rutin', 'Yoğunluk / bağıl yoğunluk', 'kontrol', '',
                         'Bölüm 9 (j). Taşıma ve dozaj için de kullanılır.', _EK2,
                         'Piknometre / dansimetre', 'tf_density'))
    if liquid and res_h.get('flam_liq') not in ('H224', 'H225'):
        rows.append(_row('rutin', 'Kaynama noktası / aralığı', 'kontrol', '',
                         'Bölüm 9 (e). Sınıflandırmayı etkilemiyor; bilinmiyorsa "veri yok" + neden yazılabilir.',
                         _EK2, '', 'tf_bp'))
    if solid:
        rows.append(_row('rutin', 'Erime noktası', 'kontrol', '',
                         'Bölüm 9 (d).', _EK2, 'Kapiler / DSC', 'tf_mp'))
    rows.append(_row('rutin', 'Suda çözünürlük', 'kontrol', '',
                     'Bölüm 9 (k). Nitel ifade ("suda tamamen karışır" gibi) çoğu ürün için yeterlidir.',
                     _EK2, '', 'tf_sol'))

    # ── 3. Test gerekmez (veri yoksa "veri yok" + neden) ──────────────────────
    _vy = 'Sınıflandırmayı değiştirmez; veri yoksa Bölüm 9\'a "veri yok" ve nedeni yazılır.'
    for ad, alan in [('Buhar basıncı', 'tf_vp'), ('Buhar yoğunluğu', ''), ('Buharlaşma hızı', 'tf_evap'),
                     ('Koku eşiği', 'tf_odor_thresh'), ('Dağılım katsayısı (n-oktanol/su)', 'tf_logkow'),
                     ('Kendiliğinden tutuşma sıcaklığı', 'tf_ait'), ('Bozunma sıcaklığı', 'tf_decomp'),
                     ('Alt/üst patlama (alevlenirlik) sınırları', '')]:
        if gas and ad in ('Buharlaşma hızı', 'Buhar yoğunluğu'):
            continue
        rows.append(_row('gerekmez', ad, 'bilgi', 'Test gerekmez', _vy, _EK2, '', alan))
    if solid:
        rows.append(_row('gerekmez', 'Granülometri / özgül yüzey alanı', 'bilgi', 'Mevcutsa yazılır',
                         'Bölüm 9 (a): "uygun ve mevcut güvenlik bilgileri" — test şartı yok; toz ürünlerde '
                         'toz patlaması değerlendirmesi için yararlıdır.', _EK2, '', 'tf_particle_size'))

    expl_h = {'H200', 'H201', 'H202', 'H203', 'H204', 'H205', 'H240', 'H241', 'H242'}
    if not (all_h & expl_h):
        rows.append(_row('gerekmez', 'Patlayıcı özellikler', 'bilgi', 'Test gerekmez',
                         ('Bileşenlerin hiçbiri patlayıcı / kendiliğinden tepkimeye giren / organik peroksit olarak '
                          'sınıflandırılmamış. Molekülde patlayıcı özellikli kimyasal grup yoksa (UN Test ve '
                          'Kriterler El Kitabı Ek-6 Tablo A6.1) patlayıcı olarak sınıflandırılmaz — bileşen '
                          'yapılarından doğrulayın.'),
                         'SEA Ek-1 2.1', '', 'tf_expl'))
    ox_h = {'H270', 'H271', 'H272'}
    if not (all_h & ox_h) and not any(f in pending for f in ('oxidizing_liquid', 'oxidizing_solid', 'oxidizing_gas')):
        rows.append(_row('gerekmez', 'Oksitleyici özellikler', 'bilgi', 'Test gerekmez',
                         'Oksitleyici (H270–H272) bileşen yok; Bölüm 9 (p)\'ye "uygulanamaz" ve nedeni yazılır.',
                         _EK2, '', 'tf_oxid'))

    rows.append(_row('gerekmez', 'Sağlık ve çevre zararları (Bölüm 11–12)', 'bilgi', 'Test gerekmez',
                     ('Karışımın sağlık ve çevre sınıfları bileşen verisinden hesaplanır (toplama yöntemi, ATE, genel '
                      'derişim sınırları). Yeni test isteğe bağlıdır; hayvan deneyi yalnız güvenilir alternatif yoksa '
                      'yapılır.'),
                     'SEA Md.10(1) ("yapabilir"), Md.9(1)'))
    return rows
