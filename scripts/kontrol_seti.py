"""Kontrol seti — referans ürünlerle GBF regresyon kontrolü (her push öncesi).

Her referans ürün için sağ panel hesabı (/api/v1/sds/calculate) ve GBF PDF'i (/api/v1/sds/pdf) üretilir, denetimin
kod kontrolleri (audit_checks) çalıştırılır ve sonuçlar aşağıdaki beklenenlerle karşılaştırılır:
  - H kodları ve uyarı kelimesi (yönetmelik kurallarıyla elle doğrulanmış değerler, 2026-10-07)
  - GBF metninde bulunması / bulunmaması gereken ifadeler (uydurma varsayılan cümleler dahil)
  - Denetimde "eksik" çıkmaması (beklenen istisnalar hariç)
Beklenenden farklı bir sonuç çıkarsa çıkış kodu 1 olur (pre-push kancası push'u durdurur).

Kullanım:  python scripts/kontrol_seti.py          (yalnız kod kontrolleri — ücretsiz)
           python scripts/kontrol_seti.py --jev    (DIPOL 369 için Jev de çalışır — TYPESAFE_API_KEY, ücretli)
Not: test sırasında data/substances_custom.json'a eklenen kayıtlar çalışma sonunda geri alınır.
"""
import asyncio
import base64
import os
import re
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
sys.stdout.reconfigure(encoding='utf-8')

CUSTOM = os.path.join(ROOT, 'data', 'substances_custom.json')

# ── Referans ürünler ─────────────────────────────────────────────────────────
# h: beklenen H kodları (sıra önemsiz); signal: 'Danger' / 'Warning' / '' (uyarı kelimesi yok)
# var / yok: GBF metninde (boşluklar tek boşluğa indirgenmiş) bulunması / bulunmaması gereken ifadeler
# s3_yok: Bölüm 3'te listelenmemesi gereken CAS'lar; kdu_ok: "eksik" yerine beklenen KDU maddeleri
# Not: bileşen H kodları Bölüm 3/16'da geçtiği için karışımın H kodları metinle değil 'h' ile kontrol edilir.
_UYDURMA = ['Uygun yangın söndürücü kullanın.', 'Sınıflandırma ve etiketleme bilgileri güncellenmiştir',
            '(Tavsiye: İyi havalandırma sağlayın)', 'beyan edilecek bileşen sınıfı bulunmamaktadır',
            # 2026-10-08 Ek-2 denetimi (madde 3): içi boş 4.2 cümlesi, yanlış KGD hükmü, nedensiz 12.4, kalınlıksız eldiven
            'Başlıca semptomlar maruziyet tipine göre değişir', 'KKDİK Madde 14', 'Toprakta hareketlilik Bilgi yok',
            'Nitril veya lateks', 'Görünüm Sıvı b) Koku']
URUNLER = [
    {'ad': 'Nitrik asit %15 (aşındırıcı, ADR)', 'bil': [('7697-37-2', 15), ('7732-18-5', 85)],
     'h': ['H314'], 'signal': 'Danger',
     'var': ['UN2031', '14.1 UN Numarası', 'Uygun olmayan söndürücüler', 'Doğrudan su jeti',
             "nitrik asit: sayısal akut toksisite verisi (LD50, LC50 veya ATE) bu GBF'de bulunmamaktadır"],
     'yok': _UYDURMA, 's3_yok': ['7732-18-5']},
    {'ad': 'DIPOL 369 (su bazlı deterjan, H318)', 'det': True, 'kullanim': 'mutfak temizleme ürünü',
     'bil': [('68439-50-9', 2.9), ('141-43-5', 0.2), ('7732-18-5', 96.9)],
     'h': ['H318'], 'signal': 'Danger',
     'var': ["%5'ten az: noniyonik yüzey aktif maddeler", 'Uygulanamaz — tehlikeli madde değildir',
             'Uygulanamaz — sulu, alevlenir olarak sınıflandırılmamış ürün',
             'Bölüm 1 zararlılık kategorilerinin hiçbirinde', 'Kirlenmiş giysiler', 'İlk yardım yapanlar',
             'Tip C (delinme süresi ≥ 10 dk', 'ABEK-P2', 'Atık işlemeyi etkileyen özellikler'],
     'yok': _UYDURMA + ['Tavsiye: İyi havalandırma'], 's3_yok': ['7732-18-5']},
    {'ad': 'Toluen + %0,5 benzen (alevlenir, CMR)', 'bil': [('108-88-3', 99.5), ('71-43-2', 0.5)],
     'h': ['H225', 'H304', 'H315', 'H336', 'H340', 'H350', 'H361D', 'H373'], 'signal': 'Danger',
     'var': ['28730 sayılı Kanserojen', 'Ek-17 madde 48', 'Ek-17 madde 5', 'Alkole dayanıklı köpük',
             'P5c (Alevlenir sıvılar', '%1.1 – %', 'hesaplanmış – ISO 10156',
             'Aspirasyon zararı (H304): kusturmayın', 'Bu karışım için kimyasal güvenlik değerlendirmesi yapılmamıştır',
             'toluen, benzen: sayısal akut toksisite verisi'],
     'yok': _UYDURMA},
    {'ad': 'Benzil benzoat %20 (yalnız H412)', 'bil': [('120-51-4', 20), ('7732-18-5', 80)],
     'h': ['H412'], 'signal': '',
     'var': ['Uyarı Kelimesi Yok', 'Kirlenmiş giysiler', 'İlk yardım yapanlar', 'Bileşenlerden benzil benzoat (H302)',
             'Nitril kauçuk eldiven ≥0,1 mm', 'Sıvı; renk: belirtilmemiştir', 'Veri kaynağı Karışımın kendisine ait'],
     'yok': _UYDURMA + ['Uyarı Kelimesi Dikkat'], 's3_yok': ['7732-18-5']},
    {'ad': 'Gliserin %5 (tehlikesiz)', 'bil': [('56-81-5', 5), ('7732-18-5', 95)],
     'h': [], 'signal': '', 'var': ['belirtilmesi gereken madde bulunmamaktadır', 'İlk yayın.',
                                    'Toprakta hareketlilik verisi mevcut değil', 'Küçük dökülmeler',
                                    'hiçbir zararlılık sınıfı için sınıflandırma kriterlerini karşılamamıştır',
                                    'bilinen önemli akut veya gecikmiş belirti ve etki yoktur'],
     'yok': _UYDURMA, 's3_yok': ['7732-18-5', '56-81-5']},
    {'ad': 'Metanol %60 (akut toksik, BEKRA Bölüm 2)', 'bil': [('67-56-1', 60), ('7732-18-5', 40)],
     'h': ['H225', 'H301', 'H311', 'H331', 'H370'], 'signal': 'Danger',
     'var': ['Bölüm 2 adlandırılmış madde: Metanol', '28733 sayılı Kimyasal Maddelerle'],
     'yok': _UYDURMA, 's3_yok': ['7732-18-5']},
    {'ad': 'NPE %5 deterjan (Ek-17 madde 46, ÖBK)', 'det': True, 'kullanim': 'endüstriyel temizleme ürünü',
     'bil': [('9016-45-9', 5), ('7732-18-5', 95)], 'h': ['H410'], 'signal': 'Warning',
     'var': ['Ek-17 madde 46', 'İhracatta Md.8'], 'yok': _UYDURMA, 's3_yok': ['7732-18-5'],
     'kdu_ok': ['15.1-izin-kisit']},
    {'ad': 'Etanolamin %2 (SEA Tablo 3.2.3 eşiği)', 'bil': [('141-43-5', 2), ('7732-18-5', 98)],
     'h': ['H315', 'H319'], 'signal': 'Warning',
     'var': ['Ağırlıklı: 10x2.0', '(CLP Tablo 3.2.3)', 'Yıkamaya en az 15 dakika devam edin'], 'yok': _UYDURMA,
     's3_yok': ['7732-18-5']},
]


def kural_testleri(c) -> int:
    """SEA Ek-1 / Ek-2 kural testleri (2026-10-08 kural denetimi): her satır, resmî metinle satır satır
    karşılaştırılarak bulunan bir hatanın düzeltilmiş hâlini korur. Döner: hatalı test sayısı."""
    from app.services.clp_service import classify_mixture_clp
    from app.services.ecological_service import calculate_aquatic, _compute_sum_acute_m
    from app.services.euh_service import check_euh, euh210_triggers
    from app.services.ghs_pictogram import get_ghs_codes
    from app.services.codes_i18n import get_h, _official_tr
    from app.services.p_code_service import assign_p_codes, select_label_p_codes
    from app.services.sds_pipeline import label_components
    from app.services.audit_jev import derive_facts

    def p_label(usage, h):
        allp = assign_p_codes(h, usage=usage)['p_codes']
        return select_label_p_codes(allp, 6, h_codes=h, usage=usage)['selected']

    def C(cas, conc, *hz, **kw):
        d = {'cas': cas, 'conc': conc, 'concMax': conc, 'name': cas,
             'hazards': [{'h_class': a, 'h_code': b} for a, b in hz]}
        d.update(kw)
        return d

    def calc(bil, **kw):
        comps = []
        for cas, conc in bil:
            r = c.get('/api/v1/sds/substance/lookup', params={'cas': cas, 'form': 'liquid'}).json()
            comps.append({'cas': cas, 'name': r.get('name') or cas, 'conc': conc, 'concMax': conc,
                          'hazards': r.get('hazards', []), 'sclRaw': r.get('scl', []), 'm_factors': {}, 'ate': None})
        p = {'components': comps, 'form': 'liquid', 'usage': 'industrial', 'lang': 'TR'}
        p.update(kw)
        return set(c.post('/api/v1/sds/calculate', json=p).json().get('h_codes') or [])

    sens_scl = C('f', 0.5, ('Skin Sens. 1', 'H317'), sclRaw=[{'h_code': 'H317', 'c_min': 0.1}])
    aq4 = calculate_aquatic([C('c', 30, ('Aquatic Chronic 4', 'H413'))])
    testler = [
        ('Tablo 3.4.5 solunum hassaslaştırıcı Kat.1 %0,5 → sınıf yok',
         lambda: 'H334' not in classify_mixture_clp([C('x', 0.5, ('Resp. Sens. 1', 'H334'))], mixture_form='liquid')['h_codes']),
        ('3.8.3.4.5 STOT SE 3 toplamı %12+%12 → H336',
         lambda: 'H336' in classify_mixture_clp([C('a', 12, ('STOT SE 3', 'H336')), C('b', 12, ('STOT SE 3', 'H336'))])['h_codes']),
        ('3.8.3.4.5 aseton %12 + etil asetat %12 (uçtan uca) → H336',
         lambda: 'H336' in calc([('67-64-1', 12), ('141-78-6', 12), ('7732-18-5', 76)], user_fp=40)),
        ('Tablo 4.1.2 Kronik 4 %30 → H413 (H412 değil)', lambda: aq4 is not None and aq4.h_code == 'H413'),
        ('Tablo 4.1.1 yalnız Kronik 1 bileşen akut toplama girmez',
         lambda: _compute_sum_acute_m([C('d', 30, ('Aquatic Chronic 1', 'H410'))]) == 0),
        ('3.10.3.3.1 viskozite 50 mm²/s → H304 yok (toluen %15)',
         lambda: 'H304' not in calc([('108-88-3', 15), ('56-81-5', 85)], test_data={'viscosity': 50}, user_fp=40)),
        ('Tablo 2.6.1 ölçülen kaynama başlangıcı 60 °C, FP 0 °C → H225 (H224 değil)',
         lambda: (lambda h: 'H225' in h and 'H224' not in h)(
             calc([('60-29-7', 5), ('108-88-3', 95)], user_fp=0, test_data={'boiling_point': 60}))),
        ('Tablo 3.4.6 cilt hassaslaştırıcı 1A %0,05 → EUH208',
         lambda: 'EUH208' in check_euh([C('e', 0.05, ('Skin Sens. 1A', 'H317'))])['euh_codes']),
        ('EUH208: özel sınırla H317 veren madde EUH208\'e yazılmaz',
         lambda: 'H317' in classify_mixture_clp([sens_scl])['h_codes'] and 'EUH208' not in check_euh([sens_scl])['euh_codes']),
        ('Ek-2 2.6 hipoklorit %0,5 (aktif klor < %1) → EUH206 yok',
         lambda: 'EUH206' not in check_euh([C('7681-52-9', 0.5, ('Skin Corr. 1B', 'H314'))], usage='consumer')['euh_codes']),
        ('Ek-2 2.6 hipoklorit %5 tüketici → EUH206',
         lambda: 'EUH206' in check_euh([C('7681-52-9', 5, ('Skin Corr. 1B', 'H314'))], usage='consumer')['euh_codes']),
        ('Ek-2 1.2.5 EUH070 madde %0,05 → EUH070 yok',
         lambda: 'EUH070' not in check_euh([C('g', 0.05, suppl_hazards=['EUH070'])])['euh_codes']),
        ('Ek-2 2.1 kurşunlu boya %0,1 (≤ %0,15) → EUH201 yok',
         lambda: 'EUH201' not in check_euh([C('1317-36-8', 0.1)], form_sub='paint')['euh_codes']),
        ('Ek-2 2.3 krom(VI) çimento dışı → EUH203 yok',
         lambda: 'EUH203' not in check_euh([C('7789-00-6', 0.01)])['euh_codes']),
        ('Ek-2 2.10 cilt hassaslaştırıcı %0,2 → EUH210 tetikleyicisi',
         lambda: bool(euh210_triggers([C('h', 0.2, ('Skin Sens. 1', 'H317'))]))),
        # ── Etiket / 2.2 (SEA Md.19–30) ──
        ('Tablo 2.8.1 H241 (Tip B) → GHS01 + GHS02', lambda: get_ghs_codes(['H241']) == ['GHS01', 'GHS02']),
        ('Tablo 5.2 H420 → GHS07', lambda: get_ghs_codes(['H420']) == ['GHS07']),
        ('H360Df alt kodu → GHS08', lambda: get_ghs_codes(['H360Df']) == ['GHS08']),
        ('Ek-3 resmî alt kod: Repr.1B H360Df %5 → H360Df (H360FD değil)',
         lambda: classify_mixture_clp([C('r', 5, ('Repr. 1B', 'H360Df'))])['h_codes'] == ['H360Df']),
        ('Ek-3 resmî alt kod: H360Df %1 (f için < %3) → H360D',
         lambda: classify_mixture_clp([C('r', 1, ('Repr. 1B', 'H360Df'))])['h_codes'] == ['H360D']),
        ('Md.29 / 3.8: H370 varken başka bileşenin H336\'sı silinmez',
         lambda: 'H336' in classify_mixture_clp([C('a', 50, ('STOT SE 1', 'H370')), C('b', 30, ('STOT SE 3', 'H336'))])['h_codes']),
        ('Rehber 7.3.1 tüketici, H314 → etikette P101 ve P102',
         lambda: {'P101', 'P102'} <= set(p_label('consumer', ['H314']))),
        ('Rehber 7.3.1 tüketici, yalnız H412 → P101/P102 yok',
         lambda: not {'P101', 'P102'} & set(p_label('consumer', ['H412']))),
        ('Md.19 tehlikesiz tüketici ürünü → P ifadesi yok', lambda: assign_p_codes([], usage='consumer')['p_codes'] == []),
        ('Md.20(3)(b) %0,5 linalool (H317 eşiği altı) etiket bileşeni değil, %2 limonen öyle',
         lambda: label_components([C('l', 0.5, ('Skin Sens. 1', 'H317'), name='linalool'),
                                   C('d', 2, ('Skin Sens. 1', 'H317'), name='limonen')], ['H317']) == ['limonen']),
        ('Md.23(4) tüm Türkçe H metinleri SEA Ek-3 / Ek-6 Tablo 1.2 resmî metniyle aynı',
         lambda: (lambda off: len(off) >= 70 and all(get_h('TR', k) == v for k, v in off.items())
                  and get_h('TR', 'H361D') == off['H361d'])(_official_tr()['h'])),
        ('Md.23(4) H304 resmî: "…öldürücü olabilir." / H317 "…yol açabilir."',
         lambda: get_h('TR', 'H304').endswith('öldürücü olabilir.') and get_h('TR', 'H317').endswith('yol açabilir.')),
        ('Md.20(2)(a) Ek-6 grup üyesi adı: 5989-27-5 → d-limonen (grubun tüm adları değil)',
         lambda: c.get('/api/v1/sds/substance/lookup', params={'cas': '5989-27-5'}).json().get('name_tr')
         == '(R)-p-menta-1,8-dien; d-limonen'),
        # ── Denetim aracı (2026-10-08 Ek-2 denetimi) ──
        ('Denetim: yalnız H412 → uyarı kelimesi sorusu sorulmaz; H318 → sorulur (SEA Ek-1 Tablo 4.1.4)',
         lambda: 'uyari_kelimesi' not in derive_facts({'2': '2.1 H412 2.2 Uyarı Kelimesi Yok'})
         and 'uyari_kelimesi' in derive_facts({'2': '2.1 H318 2.2 Tehlike'})),
    ]
    hata = 0
    for ad, f in testler:
        try:
            ok = bool(f())
        except Exception as e:
            ok, ad = False, f'{ad} — HATA: {e}'
        if not ok:
            hata += 1
            print(f'✗ Kural: {ad}')
    if not hata:
        print(f'✓ {len(testler)} SEA kural testi')
    return hata


def _norm(t: str) -> str:
    t = re.sub(r'Sayfa \d+ / \d+\s.*?formatına uygundur\.\s', ' ', t, flags=re.S)
    return re.sub(r'\s+', ' ', t)


def main(run_jev: bool) -> int:
    from fastapi.testclient import TestClient
    from app.main import app
    import fitz
    from app.services.audit_checks import run_code_checks

    c = TestClient(app)

    def comp(cas, conc):
        r = c.get('/api/v1/sds/substance/lookup', params={'cas': cas, 'form': 'liquid'}).json()
        return {'cas': cas, 'name': r.get('name') or cas, 'name_tr': r.get('name_tr', ''), 'ec_no': r.get('ec_no', ''),
                'conc': conc, 'concMax': conc, 'hazards': r.get('hazards', []), 'sclRaw': r.get('scl', []),
                'm_factors': {}, 'ate': None}

    hatalar, t0 = 0, time.time()
    dipol_pages = None
    for u in URUNLER:
        sorun = []
        comps = [comp(a, b) for a, b in u['bil']]
        calc = {'components': comps, 'form': 'liquid', 'usage': 'industrial', 'lang': 'TR'}
        r = c.post('/api/v1/sds/calculate', json=calc).json()
        h = sorted(str(x).split()[0].upper() for x in (r.get('h_codes') or []))
        if h != sorted(x.upper() for x in u['h']):
            sorun.append(f"H kodları {h} — beklenen {sorted(u['h'])}")
        if (r.get('signal') or '') != u['signal']:
            sorun.append(f"uyarı kelimesi {r.get('signal')!r} — beklenen {u['signal']!r}")
        body = {'lang': 'TR', 'product': {'name': u['ad'][:40], 'form': 'liquid', 'usage': 'industrial',
                                          'is_detergent': bool(u.get('det')), 'usage_desc': u.get('kullanim', '')},
                'supplier': {'name': 'Kontrol Seti A.Ş.', 'address': 'Örnek Mah. No:1 İstanbul', 'phone': '0212 000 00 00',
                             'email': 'kontrol@ornek.com'},
                'components': comps, 'calc_input': calc, 'phys_props': {}, 'phys_methods': {},
                'revision': {'no': '1', 'date': '07.10.2026', 'notes': ''}}
        j = c.post('/api/v1/sds/pdf', json=body).json()
        b64 = next((v for v in j.values() if isinstance(v, str) and len(v) > 5000), None)
        if not b64:
            print(f"✗ {u['ad']}: PDF üretilemedi — {str(j)[:200]}")
            hatalar += 1
            continue
        pages = [p.get_text() for p in fitz.open(stream=base64.b64decode(b64), filetype='pdf')]
        if u.get('det'):
            dipol_pages = dipol_pages or pages
        t = _norm('\n'.join(pages))
        for s in u['var']:
            if s not in t:
                sorun.append(f'GBF\'de yok: "{s}"')
        for s in u['yok']:
            if s in t:
                sorun.append(f'GBF\'de olmamalı: "{s}"')
        a, b = t.find('3.2 Karışımlar'), t.find('BÖLÜM 4')
        s3 = t[a:b] if a >= 0 else ''
        for cas in u.get('s3_yok', []):
            if cas in s3:
                sorun.append(f'Bölüm 3\'te listelenmemeli: {cas}')
        au = run_code_checks(pages)['sonuclar']
        eksik = [x['id'] for x in au if x['karar'] == 'eksik']
        if eksik:
            sorun.append('denetimde eksik: ' + ', '.join(eksik))
        kdu_beklenen = set(u.get('kdu_ok', []))
        for x in au:
            if x['id'] in ('15.1-izin-kisit', '15.1-deterjan', '2.2-tutarlilik') and x['karar'] == 'kdu' \
                    and x['id'] not in kdu_beklenen:
                sorun.append(f"beklenmeyen KDU: {x['id']} — {x['aciklama'][:90]}")
        # Denetimin kendi yanlış alarmları (2026-10-08 düzeltildi): bu kontroller artık KDU'ya düşmemeli
        for x in au:
            if x['id'] in ('T-hesap', 'T-3-2', '3.2-ec', '3.2-kayit', 'T-14-2') and x['karar'] == 'kdu' \
                    and x['id'] not in kdu_beklenen:
                sorun.append(f"beklenmeyen KDU: {x['id']} — {x['aciklama'][:90]}")
        for k in kdu_beklenen:
            if not any(x['id'] == k and x['karar'] == 'kdu' for x in au):
                sorun.append(f'beklenen KDU uyarısı çıkmadı: {k}')
        if sorun:
            hatalar += 1
            print(f"✗ {u['ad']}")
            for s in sorun:
                print(f'    - {s}')
        else:
            print(f"✓ {u['ad']}")

    hatalar += kural_testleri(c)

    if run_jev and dipol_pages:
        from app.services.audit_jev import run_jev_audit
        jr = asyncio.run(run_jev_audit('\n'.join(dipol_pages)))
        jeksik = sorted(x.get('id') for x in jr.get('sonuclar', []) if x.get('karar') == 'eksik')
        beklenen = ['16-kdu']    # Bölüm 16 KDU bilgisi henüz eklenmedi (bilinçli)
        if jeksik != beklenen:
            hatalar += 1
            print(f'✗ Jev (DIPOL 369): eksik {jeksik} — beklenen {beklenen}')
        else:
            print(f"✓ Jev (DIPOL 369): yalnız beklenen eksik {beklenen} ({jr.get('token')} token)")

    print(f"\n{len(URUNLER)} ürün, {round(time.time() - t0)} sn — "
          + ('HATA YOK' if not hatalar else f'{hatalar} üründe HATA — push yapılmamalı'))
    return 1 if hatalar else 0


if __name__ == '__main__':
    _yedek = open(CUSTOM, 'rb').read() if os.path.exists(CUSTOM) else None
    try:
        kod = main('--jev' in sys.argv)
    finally:
        if _yedek is not None:
            open(CUSTOM, 'wb').write(_yedek)   # testin eklediği madde kayıtlarını geri al
    sys.exit(kod)
