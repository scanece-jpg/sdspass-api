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

os.environ.setdefault('SDSPASS_PHYS_OFFLINE', '1')   # bileşen fiziksel verisi yalnız yerel önbellekten
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
            'Nitril veya lateks', 'Görünüm Sıvı b) Koku',
            # 2026-10-08 aralık denetimi: AB atıflı / uydurma Bölüm 3 notları
            'ECHA aralığı', 'CLP Madde 24(2)', 'ÇSGB bildirimi']
URUNLER = [
    {'ad': 'Nitrik asit %15 (aşındırıcı, ADR; metal aşındırıcılık kararı: ihtiyatlı)',
     'bil': [('7697-37-2', 15), ('7732-18-5', 85)],
     'test_data': {'metal_corrosive': 'not_tested_precautionary'}, 'soru': ('PHYS_MET_CORR_UNTESTED', 'metal_corrosive'),
     'h': ['H290', 'H314'], 'signal': 'Danger',
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
             'P5c (Alevlenir sıvılar', 'En düşük parlama noktalı bileşen', 'karışımın parlama noktası değildir',
             'Aspirasyon zararı (H304): kusturmayın', 'Bu karışım için kimyasal güvenlik değerlendirmesi yapılmamıştır',
             'toluen, benzen: sayısal akut toksisite verisi'],
     'yok': _UYDURMA + ['hesaplanmış –', 'Le Chatelier']},
    {'ad': 'Benzil benzoat %20 (yalnız H412)', 'bil': [('120-51-4', 20), ('7732-18-5', 80)],
     'h': ['H412'], 'signal': '',
     'var': ['Uyarı Kelimesi Yok', 'Kirlenmiş giysiler', 'İlk yardım yapanlar', 'Bileşenlerden benzil benzoat (H302)',
             'Nitril kauçuk eldiven ≥0,1 mm', 'Sıvı; renk: belirtilmemiştir', 'Veri kaynağı Karışımın kendisine ait',
             # Ek-2 A 3.2: aralıklı Bölüm 3'te ATEmix ve ATE tablosu kesin değer vermez
             'Oral (Ağız) > 2000 mg/kg', 'benzil benzoat ≥ 20 - < 25% H302'],
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
     'var': ["Hesaplama yöntemi (bileşenlerin Bölüm 3'teki konsantrasyon aralıklarıyla) — eşik %10 (CLP Tablo 3.2.3)",
             'Yıkamaya en az 15 dakika devam edin', '≥ 1 - < 2,5%', 'KKDİK Ek-2 A 3.2(b) uyarınca yüzde aralığı'],
     'yok': _UYDURMA + ['10x2.0'],
     's3_yok': ['7732-18-5']},
    # ── Toz / aerosol / gaz (madde 4, 2026-10-08) — beklenenler SEA Ek-1 tablolarından elle çıkarıldı ──
    {'ad': 'Toz oksijenli deterjan (oksitleyici kararı: ihtiyatlı)', 'form': 'powder',
     'bil': [('15630-89-4', 30), ('497-19-8', 50), ('7757-82-6', 15), ('68439-46-3', 5)],
     'test_data': {'oxidizing_solid': 'not_tested_precautionary'}, 'soru': ('PHYS_OX_SOL_UNTESTED', 'oxidizing_solid'),
     'phys': {'appearance': 'Toz', 'color': 'beyaz', 'odor': 'kokusuz', 'ph': '10.5'},
     'h': ['H272', 'H318', 'H302'], 'signal': 'Danger',
     'var': ['Oks. Kat. 2 H272', 'P220', 'UN 1479', 'Ambalaj grubu II', 'ihtiyatlı olarak sınıflandırılmıştır',
             'Buhar basıncı Uygulanamaz (katı)', 'tane boyutu: belirlenmemiştir (ölçülmemiştir)'],
     'yok': _UYDURMA + ['P221', 'Ox. Sol. (ihtiyatlı)', 'ATEX', 'patlayabilen toz-hava', 'Toz-hava karışımı oluşumunu']},
    {'ad': 'Aerosol sprey (etanol, propan/bütan itici)', 'form': 'aerosol',
     'bil': [('64-17-5', 40), ('74-98-6', 30), ('106-97-8', 20), ('7732-18-5', 10)],
     'test_data': {'flammable_aerosol': 'not_tested'}, 'soru': ('PHYS_AEROSOL_UNTESTED', 'flammable_aerosol'),
     'phys': {'appearance': 'Aerosol', 'color': 'renksiz', 'odor': 'alkol'},
     'h': ['H222', 'H229'], 'signal': 'Danger',
     'var': ['Aerosol 1 H222 + H229', 'P211', 'P251', 'P410+P412', 'UN 1950', 'AEROSOLLER, alevlenebilir',
             'Alevlenir bileşen oranı (kütlece) %90 (ürün bileşiminden; SEA Ek-1 2.3)'],
     'yok': _UYDURMA + ['hPa hesaplanmış', '%Belirlenmemiştir', 'Alevlenir gaz (H220)'], 's3_yok': ['7732-18-5']},
    {'ad': 'LPG (propan/bütan, sıvılaştırılmış)', 'form': 'gas', 'bil': [('74-98-6', 60), ('106-97-8', 40)],
     'test_data': {'gas_type': 'liquefied'}, 'phys': {'appearance': 'Gaz', 'color': 'renksiz', 'odor': 'karakteristik'},
     'h': ['H220', 'H280'], 'signal': 'Danger',
     'var': ['Alev. Gaz 1 H220 ISO 10156:2017 4.3 hesabı', '= 27,33 > 1', 'Basınçlı Gaz (Sıvılaştırılmış gaz)', 'UN 1965',
             'HİDROKARBON GAZ KARIŞIMI, SIVILAŞTIRILMIŞ', 'Bağıl yoğunluk Uygulanamaz (gaz)',
             'En uçucu bileşen: propan'],
     'yok': _UYDURMA + ['Alev. Gaz 1A', 'H232', 'UN 3163', 'bileşen varlığı']},
    # 2026-10-09 klor GBF incelemesi: Ek-6 Akut Tok. 3 (ECHA'daki Kat.2 eklenmez), ADR 2TOC C/D, inorganik gaz
    # metinleri (karbon oksit / organik fragment yok, 16 05 04*, sızıntıya su verilmez), Bölüm 8 çelişkileri
    {'ad': 'Klor %100 (sıvılaştırılmış, oksitleyici + toksik gaz)', 'form': 'gas', 'bil': [('7782-50-5', 100)],
     'test_data': {'gas_type': 'liquefied'}, 'phys': {'appearance': 'Gaz', 'color': 'açık sarı', 'odor': 'keskin'},
     'h': ['H270', 'H280', 'H315', 'H319', 'H331', 'H335', 'H400'], 'signal': 'Danger',
     'var': ['Akut Toks. 3 (solunum) H331', 'Basınçlı Gaz (Sıvılaştırılmış gaz)', '2TOC', 'C/D', 'UN1017',
             '16 05 04*', 'Sızıntı noktasına ve kabın içine doğrudan su', 'Klorür bileşikleri',
             '3.1 Maddeler', 'Madde sınıflandırması - SEA Ek-6', 'Maddenin sınıflandırılması', '-34 °C', 'ECHA kayıt dosyası'],
     'yok': _UYDURMA + ['H330:', 'Akut Toks. 2', 'Acute Tox', 'Karbon oksit', 'organik fragment', 'FFP2',
                        'cilt için sınıflandırılmamıştır', 'uzun süreli olumsuz', 'CO₂ KULLANMAYIN', '16 03 05',
                        'mPa·s',
                        'kontrollü yakma', '3.2 Karışımlar', 'ATE Karışım Hesabı', 'Gaz karışımı',
                        'karışım için test yapılmamıştır', 'Bu karışım', 'kesme %']},
    {'ad': 'Azot içinde %1 karbon monoksit (ISO 10156 hesabı: alevlenir değil)', 'form': 'gas',
     'bil': [('630-08-0', 1), ('7727-37-9', 99)],
     'test_data': {'gas_type': 'compressed'},
     'phys': {'appearance': 'Gaz', 'color': 'renksiz', 'odor': 'kokusuz'},
     'h': ['H280', 'H360D', 'H373'], 'signal': 'Danger',
     'var': ['UN 1956', 'SIKIŞTIRILMIŞ GAZ, B.B.B.', 'Alevlenir gaz olarak sınıflandırılmamıştır',
             'ISO 10156:2017 hesabına göre karışım havada alevlenir değildir', '= 0,07 ≤ 1', 'EIGA Doc 169',
             'hacimce (h/h)'],
     'yok': _UYDURMA + ['Alevlenir gaz (H220)', 'UN 1954', 'P377']},
    {'ad': 'Formlama gazı (%5 hidrojen / azot) — ISO 10156: 5/5,5 = 0,91 ≤ 1', 'form': 'gas',
     'bil': [('1333-74-0', 5), ('7727-37-9', 95)], 'test_data': {'gas_type': 'compressed'},
     'phys': {'appearance': 'Gaz', 'color': 'renksiz', 'odor': 'kokusuz'},
     'h': ['H280'], 'signal': 'Warning',
     'var': ['UN 1956', 'Alevlenir gaz olarak sınıflandırılmamıştır', '= 0,91 ≤ 1'],
     'yok': _UYDURMA + ['Alevlenir gaz (H220)', 'UN 1954', 'P210']},
    {'ad': 'ISO 10156 Örnek 2 (%2 H2, %8 CH4, %25 Ar, %65 He) — alevlenir', 'form': 'gas',
     'bil': [('1333-74-0', 2), ('74-82-8', 8), ('7440-37-1', 25), ('7440-59-7', 65)],
     'test_data': {'gas_type': 'compressed'}, 'phys': {'appearance': 'Gaz', 'color': 'renksiz', 'odor': 'kokusuz'},
     'h': ['H220', 'H280'], 'signal': 'Danger',
     'var': ['Alev. Gaz 1 H220', '= 1,56 > 1', 'Kategori 1 (ISO 10156 4.7)', 'Alt: %39.7; üst: belirlenmemiştir',
             'UN 1954', 'P210'],
     'yok': _UYDURMA + ['%?', 'UN 1956']},
    {'ad': 'Sentetik hava (%21 oksijen / azot) — ISO 10156 OP %21 ≤ %23,5', 'form': 'gas',
     'bil': [('7782-44-7', 21), ('7727-37-9', 79)], 'test_data': {'gas_type': 'compressed'},
     'phys': {'appearance': 'Gaz', 'color': 'renksiz', 'odor': 'kokusuz'},
     'h': ['H280'], 'signal': 'Warning',
     'var': ['oksitleme gücü %21 ≤ %23,5', 'P410+P403', 'Güneş ışığından koruyun'],
     'yok': _UYDURMA + ['Oksitleyici gaz (H270)', 'UN 3156', 'Sınıf 2.2 (5.1)']},
    {'ad': 'Oksijen %30 / azot — ISO 10156 OP %30 > %23,5', 'form': 'gas',
     'bil': [('7782-44-7', 30), ('7727-37-9', 70)], 'test_data': {'gas_type': 'compressed'},
     'phys': {'appearance': 'Gaz', 'color': 'renksiz', 'odor': 'kokusuz'},
     'h': ['H270', 'H280'], 'signal': 'Danger',
     'var': ['Oks. Gaz 1 H270 ISO 10156:2017 5.3 hesabı', 'P220', 'P410+P403', 'UN 3156',
             'etiket: 2.2 + 5.1', 'Sınıf 2.2 (5.1)'],
     'yok': _UYDURMA + ['≥ %1 oksitleyici']},
]


_GCL = [  # (konsantrasyon, bileşen sınıfı, H kodu, aranan karışım kodu, olmalı mı) — SEA Ek-1 Bölüm 3
    (5, 'Skin Corr. 1A', 'H314', 'H314', True), (4.9, 'Skin Corr. 1A', 'H314', 'H314', False),
    (1, 'Skin Corr. 1A', 'H314', 'H315', True), (0.9, 'Skin Corr. 1A', 'H314', 'H315', False),
    (10, 'Skin Irrit. 2', 'H315', 'H315', True), (9.9, 'Skin Irrit. 2', 'H315', 'H315', False),
    (3, 'Eye Dam. 1', 'H318', 'H318', True), (2.9, 'Eye Dam. 1', 'H318', 'H318', False),
    (1, 'Eye Dam. 1', 'H318', 'H319', True), (3, 'Skin Corr. 1B', 'H314', 'H318', True),
    (10, 'Eye Irrit. 2', 'H319', 'H319', True),
    (1, 'Skin Sens. 1', 'H317', 'H317', True), (0.9, 'Skin Sens. 1', 'H317', 'H317', False),
    (0.1, 'Skin Sens. 1A', 'H317', 'H317', True),
    (0.1, 'Muta. 1B', 'H340', 'H340', True), (1, 'Muta. 2', 'H341', 'H341', True),
    (0.9, 'Muta. 2', 'H341', 'H341', False),
    (0.1, 'Carc. 1B', 'H350', 'H350', True), (1, 'Carc. 2', 'H351', 'H351', True),
    (0.3, 'Repr. 1B', 'H360D', 'H360', True), (0.29, 'Repr. 1B', 'H360D', 'H360', False),
    (3, 'Repr. 2', 'H361d', 'H361', True), (0.3, 'Lact.', 'H362', 'H362', True),
    (10, 'STOT SE 1', 'H370', 'H370', True), (1, 'STOT SE 1', 'H370', 'H371', True),
    (0.9, 'STOT SE 1', 'H370', 'H371', False), (10, 'STOT SE 2', 'H371', 'H371', True),
    (20, 'STOT SE 3', 'H335', 'H335', True), (19, 'STOT SE 3', 'H335', 'H335', False),
    (10, 'Asp. Tox. 1', 'H304', 'H304', True),
]
_GCL_RE = [(10, 'STOT RE 1', 'H372', 'H372', True), (1, 'STOT RE 1', 'H372', 'H373', True),
           (0.9, 'STOT RE 1', 'H372', 'H373', False), (10, 'STOT RE 2', 'H373', 'H373', True),
           (9.9, 'STOT RE 2', 'H373', 'H373', False)]


def _gcl_sinirlari(clp, stot, C) -> list:
    """SEA Ek-1 Bölüm 3 genel konsantrasyon sınırlarını eşikte ve hemen altında dener; uymayanları döndürür."""
    hata = []
    for satirlar, f in ((_GCL, lambda cs: clp(cs, mixture_form='liquid')['h_codes']),
                        (_GCL_RE, lambda cs: stot(cs)['h_codes'])):
        for k, sinif, h, aranan, olmali in satirlar:
            hs = f([C('x', k, (sinif, h)), C('7732-18-5', 100 - k)])
            if any(str(x).startswith(aranan) for x in hs) != olmali:
                hata.append((k, sinif, aranan, olmali, hs))
    return hata


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
    from app.services.clp_service import signal_word_for, class_signal
    from app.services.codes_i18n import correct_hclass
    from app.services.sds_pipeline import section3_display
    from app.services.sds_sentence_service import generate_section3
    from app.services import iso10156
    from app.services.physical_engine import calculate as phys_calc
    from app.services.transport_engine import classify as tr_classify
    from app.services.transport_engine import Component as TC, build_transport_components as build_tc
    from app.services.stot_engine import calculate as _stot
    from app.services.clp_service import _ate_core
    import datetime

    def _raises(fn):
        try:
            fn()
        except ValueError:
            return True
        return False

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

    def tn(bil, form='liquid', **kw):
        """Test ihtiyacı listesi (SEA Md.10, KKDİK Ek-2 9.1) — {özellik: satır}"""
        comps = []
        for cas, conc in bil:
            r = c.get('/api/v1/sds/substance/lookup', params={'cas': cas, 'form': form}).json()
            comps.append({'cas': cas, 'name': r.get('name') or cas, 'conc': conc, 'concMax': conc,
                          'hazards': r.get('hazards', []), 'sclRaw': r.get('scl', []), 'm_factors': {}, 'ate': None})
        p = {'components': comps, 'form': form, 'usage': 'industrial', 'lang': 'TR'}
        p.update(kw)
        return {x['ozellik']: x for x in c.post('/api/v1/sds/calculate', json=p).json().get('test_ihtiyaci') or []}

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
        ('3.10.3.3.1 "40 °C\'de ölçülmüş" viskozite: girilmemişse hesaplanmış viskoziteyle H304 kaldırılmaz '
         '(toluen %15 + gliserin)',
         lambda: 'H304' in calc([('108-88-3', 15), ('56-81-5', 85)], user_fp=40)),
        ('Tablo 2.6.1 kaynama başlangıcı ölçülmedi: FP 10 °C + kaynama noktası bilinmeyen alevlenir bileşen → H224 '
         '(en kötü durum; önceden 100 °C varsayılıp H225); bileşen kaynama noktası 56 °C (aseton) → H225',
         lambda: [x['h'] for x in phys_calc([C('999-99-9', 40, ('Flam. Liq. 2', 'H225')), C('7732-18-5', 60)],
                                            form='liquid', user_fp=10)['results']] == ['H224']
         and [x['h'] for x in phys_calc([C('67-64-1', 30, ('Flam. Liq. 2', 'H225')), C('7732-18-5', 70)],
                                        form='liquid', user_fp=10)['results']] == ['H225']),
        ('SEA Md.10(2): "ölçüm yok" (parlama noktası) ve bilinmeyen kaynama başlangıcı en kötü durumu Bölüm 16\'ya '
         '"test yapılır / revize edilecektir" notuyla yazılır; "test yapılmadı — ihtiyatlı" kararlarında da aynı atıf',
         lambda: (lambda n1, n2, n3: any('Md.10(2)' in n and 'en kötü durum' in n for n in n1)
                  and any('Md.10(2)' in n and 'kaynama başlangıç noktası ölçülmemiş' in n for n in n2)
                  and any('Md.10(2)' in n and 'ihtiyatlı' in n for n in n3))(
             [n['TR'] for n in phys_calc([C('64-17-5', 30, ('Flam. Liq. 2', 'H225')), C('67-63-0', 10, ('Flam. Liq. 2', 'H225')),
                                          C('7732-18-5', 60)], form='liquid',
                                         fp_status='no_measurement')['classification_notes']],
             [n['TR'] for n in phys_calc([C('999-99-9', 40, ('Flam. Liq. 2', 'H225'), phys={}),
                                          C('7732-18-5', 60, phys={})], form='liquid',
                                         user_fp=10)['classification_notes']],
             [n['TR'] for n in phys_calc([C('1310-73-2', 5, ('Skin Corr. 1A', 'H314')), C('7732-18-5', 95)],
                                         form='liquid', mixture_ph=13.5,
                                         test_data={'metal_corrosive': 'not_tested_precautionary'})['classification_notes']])),
        ('Form alt türleri: toz patlaması yalnız KDU kararıyla (yanmaz tozda GBF\'ye yazılmaz, AB ATEX atfı yok); '
         'nano tozda EUH212 (TR SEA\'da yok) önerilmez; su bazlı üründe "parlama noktası uygulanamaz — N/A" önerisi '
         'yok (alevlenir bileşenli sulu ürün H226 alabilir); polimerde Ek-2 9.1(d) madde adı korunur',
         lambda: (lambda w, html, pdf: not any('ATEX' in x or 'EUH212' in x for x in w)
                  and any('Toz patlaması riski var' in x for x in w)
                  and 'Su bazlı ürünlerde parlama noktası genellikle uygulanamaz' not in html and 'EUH212' not in html and '2004/42' not in html
                  and "'Erime noktası/donma noktası (polimer" in pdf and 'ATEX 2014/34' not in pdf)(
             phys_calc([C('7631-86-9', 100, phys={})], form='powder', form_sub='powder_nano')['warnings'],
             open('static/index.html', encoding='utf-8').read(),
             open('app/services/pdf_sds_service.py', encoding='utf-8').read())),
        ('KKDİK Ek-2 0.2.5 / 16(a) revizyon: ilk yayında ilk sayfada "Hazırlanma tarihi"; revizyonda "Revizyon", '
         'versiyon / revizyon no ve "Yerine geçtiği versiyon" (önceki GBF\'nin gömülü özetinden); özet PDF\'e gömülür '
         've geri okunur; değişiklikler bölüm bölüm bulunur (Bölüm 3\'te listelenmeyen bileşen özete girmez)',
         lambda: (lambda rv, fitz: (lambda raw: (lambda oz, t1, t2: oz == {'surum': 1, 'x': 'ç'}
                  and 'Hazırlanma tarihi 01.02.2026' in t1 and 'Versiyon / revizyon no 1.1 / Rev.2' in t2
                  and 'Yerine geçtiği versiyon Versiyon 1.0 (Rev.1) — 01.02.2026' in t2
                  and rv.farklar({'b2': {'siniflandirma': ['H226'], 'uyari': 'Warning'}, 'b3': [],
                                  'b14': {'tehlikeli_degil': True}},
                                 {'b2': {'siniflandirma': ['H225'], 'uyari': 'Danger'},
                                  'b3': [{'cas': '67-63-0', 'ad': 'izopropanol; IPA', 'derisim': '≥ 10 - < 20%'}],
                                  'b14': {'un': 'UN 1993'}})[:3] == [
                      'Bölüm 2.1 sınıflandırma — eklendi: H225; çıkarıldı: H226.',
                      'Bölüm 2.2 uyarı kelimesi: Dikkat → Tehlike.', 'Bölüm 3: izopropanol eklendi.'])(
                  rv.oku(rv.gom(raw, {'surum': 1, 'x': 'ç'})),
                  _pdf_text(c, [('64-17-5', 30), ('7732-18-5', 70)],
                            revision={'no': '1', 'version': '1.0', 'date': '01.02.2026', 'notes': 'İlk yayın'}),
                  _pdf_text(c, [('64-17-5', 30), ('7732-18-5', 70)],
                            revision={'no': '2', 'version': '1.1', 'date': '09.10.2026', 'notes': 'Bölüm 9 güncellendi',
                                      'previous_ozet': {'surum': 1, 'revizyon': {'versiyon': '1.0', 'no': '1',
                                                                                 'tarih': '01.02.2026'}}})))(
                  (lambda d: (d.new_page(), d.tobytes())[1])(fitz.open())))(
             __import__('app.services.gbf_revision', fromlist=['x']), __import__('fitz'))),
        ('KKDİK Ek-2 8.1.4 DNEL / PNEC: ECHA kayıt dosyası özetlerinden çözümleme (işçi / genel nüfus, yol, etki, '
         'süre; PNEC ortamları, µg/L); GBF 8.1\'de bileşen tablosu ve kaynak (kayıt numarası); 8.1.2 izleme TS EN 689 '
         '+ TS EN 482; 2.1 gerekçesinde bileşen adı Türkçe',
         lambda: (lambda cp: cp.parse_dnel(
                     '<p>Workers - Hazard via inhalation route Systemic effects Long term exposure Hazard assessment '
                     'conclusion DNEL (Derived No Effect Level) Value 1,210 mg/m³ Most sensitive endpoint x Local '
                     'effects Long term exposure Hazard assessment conclusion low hazard (no threshold derived) '
                     'General Population - Hazard via oral route Systemic effects Long term exposure Hazard assessment '
                     'conclusion DNEL (Derived No Effect Level) Value 2.69 mg/kg bw/day Most sensitive endpoint</p>') == [
                     {'nufus': 'İşçiler', 'yol': 'soluma', 'etki': 'sistemik', 'sure': 'uzun süreli', 'deger': 1210.0,
                      'birim': 'mg/m³'},
                     {'nufus': 'Genel nüfus', 'yol': 'ağız', 'etki': 'sistemik', 'sure': 'uzun süreli', 'deger': 2.69,
                      'birim': 'mg/kg bw/day'}]
                  and cp.parse_pnec('Freshwater Hazard assessment conclusion PNEC aqua (freshwater) PNEC value 74 µg/L '
                                    'Assessment factor 10 Soil Hazard assessment conclusion PNEC soil PNEC value 0.313 '
                                    'mg/kg soil dw Extrapolation') == [
                      {'ortam': 'tatlı su', 'deger': 74.0, 'birim': 'µg/L'},
                      {'ortam': 'toprak', 'deger': 0.313, 'birim': 'mg/kg soil dw'}])(
             __import__('app.services.component_phys', fromlist=['x']))
         and (lambda t: 'DNEL/PNEC (KKDİK Ek-2 8.1.4)' in t and 'toluen İşçiler soluma, sistemik, uzun süreli 75,37 mg/m³' in t
              and 'toluen tatlı su 74 µg/L' in t and 'ECHA kayıt dosyası (01-2119471310-51-0000)' in t
              and 'TS EN 482' in t and 'Alev. Sıv. 2 H225 toluen' in t)(_pdf_text(c, [('108-88-3', 100)]))),
        ('KKDİK Ek-2 8.2.2.2(b)(i) eldiven: malzeme / kalınlık / tipik delinme süresi önce kayıt yaptıranın önerisinden '
         '(ECHA "Guidance on safe use"; "uygun olmayan" malzeme alınmaz); yoksa genel tablo + "doğrulayın" uyarısı; '
         'borik asit (zayıf asit) ve amonyum persülfat (persülfat) EN 374 L / P sınıfına eşlenmez',
         lambda: (lambda cp, gs: cp.parse_glove('Hand protection: - Impervious gloves - Suitable material: PVC, Neoprene '
                                                '- Unsuitable material: Nitrile rubber')['malzemeler'] == ['neopren', 'pvc']
                  and (lambda r: r['kaynak'] == 'kayit' and r['malzeme'] == 'butil' and r['kalinlik_mm'] == 0.5
                       and 'malzeme: kayıt yaptıranın önerisi — ECHA kayıt dosyası' in r['text']
                       and 'Tipik delinme süresi > 480 dk' in r['text'])(
                      gs.select([{'cas': '67-64-1', 'conc': 100, 'name': 'aseton', 'hazards': [{'h_code': 'H319'}]}],
                                ['H319']))
                  and (lambda r: r['kaynak'] == 'genel' and any('resmî dayanağı yok' in w for w in r['uyarilar']))(
                      gs.select([{'cas': '999-99-9', 'conc': 50, 'name': 'x', 'hazards': [{'h_code': 'H315'}]}],
                                ['H315']))
                  and (lambda r: r['kaynak'] == 'secim' and 'kayıt yaptıranın' not in r['text'])(
                      gs.select([{'cas': '67-64-1', 'conc': 100, 'name': 'aseton', 'hazards': [{'h_code': 'H319'}]}],
                                ['H319'], material='nitril'))
                  and '10043-35-3' not in gs.CAS_CLASS and '7727-54-0' not in gs.CAS_CLASS)(
             __import__('app.services.component_phys', fromlist=['x']),
             __import__('app.services.glove_service', fromlist=['x']))),
        ('ADR ÖH 375 (UN 3082): not ambalaj miktarına (≤ 5 L) dayanır, viskozite şartı yok (ADR 2025 3.3.1)',
         lambda: (lambda n: '5 L' in n and 'viskozite' not in n.lower())(
             tr_classify(h_codes=['H411'], form='liquid', viscosity=5000)['road']['note'])),
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
        # ── Bölüm 3 konsantrasyon gösterimi (KKDİK Ek-2 A 3.2, 2026-10-08) ──
        ('Ek-2 A 3.2: %6 + %3 cilt tahriş edici — bant üst uçları (<10, <5) H315 verirdi → aralıklar daraltılır',
         lambda: (lambda d: all(d[k]['kind'] == 'narrowed' for k in ('a', 'b'))
                  and d['a']['upper'] + d['b']['upper'] < 10.0001)(
             section3_display([C('a', 6, ('Skin Irrit. 2', 'H315')), C('b', 3, ('Skin Irrit. 2', 'H315'))]))),
        ('Ek-2 A 3.2: kullanıcı aralığı 10–30 aynen yazılır',
         lambda: section3_display([C('x', 30, ('Skin Irrit. 2', 'H315'), conc_min=10)])['x']['text'] == '≥ 10 - ≤ 30%'),
        ('Ek-2 A 3.2: "tam değer" seçimi → 20%; varsayılan → ≥ 20 - < 25%',
         lambda: section3_display([C('x', 20, ('Aquatic Chronic 2', 'H411'))], mode='exact')['x']['text'] == '20%'
         and section3_display([C('x', 20, ('Aquatic Chronic 2', 'H411'))])['x']['text'] == '≥ 20 - < 25%'),
        ('SEA Md.26: onay bilgisi yoksa alternatif ad kullanılmaz; onay varsa ad ve CAS gizlenir',
         lambda: generate_section3([C('71-43-2', 1, name='benzen', alt_name='aromatik', disclosure='hide')])[0]['name']
         == 'benzen' and generate_section3([C('9-9-9', 1, name='x', alt_name='aromatik', alt_name_approval='01.01.2026/1',
                                               disclosure='hide')])[0]['name'] == 'aromatik'),
        # ── Fiziksel sınıflar (madde 4, 2026-10-08) ──
        ('SEA Ek-1 Tablo 2.14.2: Oks. Kat. 2 (H272) → Tehlike, Kat. 3 → Dikkat',
         lambda: signal_word_for({'H272'}, [{'h_code': 'H272', 'signal': 'Danger'}]) == 'Danger'
         and signal_word_for({'H272'}, [{'h_code': 'H272', 'signal': 'Warning'}]) == 'Warning'
         and class_signal('Ox. Sol. 2') == 'Danger' and class_signal('Ox. Liq. 3') == 'Warning'),
        ('SEA Ek-1 Tablo 2.12.2 / 2.15: Su ile temas Kat.2 Tehlike; Org. peroksit Tip E Dikkat; Alev. Katı 2 Dikkat',
         lambda: class_signal('Water-react. 2') == 'Danger' and class_signal('Org. Perox. Type E') == 'Warning'
         and class_signal('Flam. Sol. 2') == 'Warning'),
        ('SEA Ek-1 Tablo 2.14.2 (2020): H272 → P210, P220, P280; P221 yok',
         lambda: (lambda p: {'P210', 'P220', 'P280'} <= set(p) and 'P221' not in p)(assign_p_codes(['H272'])['p_codes'])),
        ('SEA Ek-1 Tablo 2.2.1 (TR): alevlenir gaz Kategori 1 — "1A" alt kategorisi yok',
         lambda: correct_hclass('H220', 'Flam. Gas 1A') == 'Flam. Gas 1'),
        # ── Gaz karışımı alevlenirliği — ISO 10156:2017 (2026-10-08); beklenenler standardın 4.4 / 4.6 örnekleri ──
        ('ISO 10156 4.4 Örnek 1: %7 H2 + %93 CO2 → Σ = 0,869, alevlenir değil',
         lambda: (lambda r: not r['flammable'] and abs(r['sum'] - 0.869) < 0.001)(
             iso10156.evaluate([C('1333-74-0', 7), C('124-38-9', 93)]))),
        ('ISO 10156 4.4 Örnek 2: %2 H2 + %8 CH4 + %25 Ar + %65 He → Σ = 1,56, alevlenir (Kat.1)',
         lambda: (lambda r: r['flammable'] and abs(r['sum'] - 1.56) < 0.01 and r['h'] == 'H220')(
             iso10156.evaluate([C('1333-74-0', 2), C('74-82-8', 8), C('7440-37-1', 25), C('7440-59-7', 65)]))),
        ('ISO 10156 4.6 Örnek 3 ve 4: alt alevlenme sınırı %11,4 ve %14,3',
         lambda: iso10156.evaluate([C('74-82-8', 40), C('124-38-9', 60)])['lm'] == 11.4
         and iso10156.evaluate([C('1333-74-0', 15), C('74-82-8', 15), C('124-38-9', 30),
                                C('7727-37-9', 40)])['lm'] == 14.3),
        ('EIGA Doc 169 2.2.2.1: yalnız amonyak içeren alevlenir karışım → Kategori 2 (H221)',
         lambda: iso10156.evaluate([C('7664-41-7', 50), C('7727-37-9', 50)])['h'] == 'H221'),
        ('Tabloda olmayan alevlenir gaz veya oksijen → hesap yok, karar sorusu',
         lambda: all('PHYS_FLAM_GAS_UNTESTED' in [d['code'] for d in phys_calc(b, form='gas')['pending_decisions']]
                     for b in ([C('9999-99-9', 5, ('Flam. Gas 1', 'H220')), C('7727-37-9', 95)],
                               [C('74-82-8', 5, ('Flam. Gas 1', 'H220')), C('7782-44-7', 95)]))),
        ('ISO 10156 5.3 Örnek 1 ve 2: OP %13 (oksitleyici değil), %29 (oksitleyici)',
         lambda: (lambda a, b: a['op'] == 13.0 and not a['oxidizing'] and b['oxidizing'] and abs(b['op'] - 29.1) < 0.1)(
             iso10156.evaluate_oxidizing([C('10024-97-2', 5), C('7782-44-7', 10), C('7727-37-9', 85)]),
             iso10156.evaluate_oxidizing([C('10024-97-2', 20), C('7782-44-7', 20), C('7727-37-9', 40),
                                          C('124-38-9', 20)]))),
        ('Oksijen + alevlenir gaz → oksitleyici hesabı yok, karar sorusu (ISO 10156 bölüm 6)',
         lambda: 'PHYS_OX_GAS_UNTESTED' in [d['code'] for d in phys_calc(
             [C('7782-44-7', 30), C('74-82-8', 2, ('Flam. Gas 1', 'H220')), C('7727-37-9', 68)],
             form='gas')['pending_decisions']]),
        ('SEA Ek-1 Tablo 2.5: H280 → etikette P410+P403 (ayrık P410/P403 değil); H220 ile P403 tekrar etmez',
         lambda: p_label('industrial', ['H280']) == ['P410+P403']
         and (lambda p: 'P410+P403' in p and 'P403' not in p)(p_label('industrial', ['H220', 'H280']))),
        # ── Fiziksel / ADR denetimi (2026-10-08) ──
        ('SEA Ek-1 2.3: su + %30 propan aerosol, test yok → Aerosol 1 (H222) + test sorusu',
         lambda: (lambda r: 'H222' in [x['h'] for x in r['results']]
                  and 'PHYS_AEROSOL_UNTESTED' in [d['code'] for d in r['pending_decisions']])(
             phys_calc([C('7732-18-5', 70), C('74-98-6', 30, ('Flam. Gas 1', 'H220'))], form='aerosol'))),
        ('SEA Ek-1 2.3: parlama noktası 78 °C (≤ 93 °C) sıvı alevlenir bileşen sayılır; ≤ %1 → yalnız H229',
         lambda: 'H222' in [x['h'] for x in phys_calc([C('8042-47-5', 60, phys={}),
                                                       C('112-34-5', 30, phys={'flash_point': {'value': 78}}),
                                                       C('124-38-9', 10, phys={})],
                                                     form='aerosol')['results']]
         and [x['h'] for x in phys_calc([C('7732-18-5', 98), C('7727-37-9', 2)], form='aerosol')['results']] == ['H229']),
        ('SEA Ek-1 2.7: H228 kayıtlı bileşen (%2 kükürt) tozda H228 otomatik verilmez, test (N.1) sorusu sorulur; '
         'kaydında H228 olmayan karbon siyahı için elle liste yok — soru da sınıf da çıkmaz',
         lambda: (lambda r: not r['results'] and 'PHYS_FLAM_SOL_UNTESTED' in [d['code'] for d in r['pending_decisions']])(
             phys_calc([C('7704-34-9', 2, ('Flam. Sol. 2', 'H228')), C('471-34-1', 98)], form='powder'))
         and (lambda r: not r['results'] and 'PHYS_FLAM_SOL_UNTESTED' not in [d['code'] for d in r['pending_decisions']])(
             phys_calc([C('1333-86-4', 2), C('471-34-1', 98)], form='powder'))),
        ('Tablo denetimi 2026-10-08: alevlenir sıvı bileşen kategorisi önce bileşen kaydından (SEA Md.6(1)(c)) — '
         'o-ksilen Ek-6 H226 (tablodaki 17 °C ile H225 olmaz); diglyme H226 atlanmaz',
         lambda: [x['h'] for x in phys_calc([C('95-47-6', 20, ('Flam. Liq. 3', 'H226')), C('7732-18-5', 80)],
                                           form='liquid', fp_status='no_measurement')['results']] == ['H226']
         and [x['h'] for x in phys_calc([C('111-96-6', 30, ('Flam. Liq. 3', 'H226')), C('7732-18-5', 70)],
                                       form='liquid', fp_status='no_measurement')['results']] == ['H226']),
        ('Tablo denetimi 2026-10-08: ADR Tablo A adlı girişler — n-heptan UN1206 (1-kloropropan değil), '
         'NaOH katı UN1823, kalsiyum oksit ADR\'ye tabi değil, %10 H2O2 UN2984, %37 formaldehit UN2209',
         lambda: (lambda L: L('142-82-5', 100, 'liquid')['un_no'] == 'UN1206'
                  and L('1310-73-2', 99, 'solid')['un_no'] == 'UN1823'
                  and L('1310-73-2', 30, 'liquid')['un_no'] == 'UN1824'
                  and L('1305-78-8', 95, 'solid') is None
                  and L('7722-84-1', 10, 'liquid')['un_no'] == 'UN2984'
                  and L('50-00-0', 37, 'liquid')['un_no'] == 'UN2209')(
             lambda cas, conc, st: __import__('app.services.transport_adr_service', fromlist=['x'])
             .lookup_by_cas(cas, concentration=conc, physical_state=st))),
        ('ADR 2.2.8.1.5.3 (c)(ii): yalnız H290 → Sınıf 8 PG III (UN 1760)',
         lambda: (lambda d: d['class'] == '8' and d['pg'] == 'III' and d['un'] == 'UN 1760')(
             tr_classify(['H290'], form='liquid')['road'])),
        ('ADR Tablo A: su ile tepkimeye giren katı (alevlenir değil) UN 2813; organik peroksit Tip B UN 3101',
         lambda: tr_classify(['H261'], form='solid')['road']['un'] == 'UN 2813'
         and tr_classify(['H241'], form='liquid')['road']['un'] == 'UN 3101'),
        ('ADR 2025 (TR) 3.1.2.1: 14.2 resmî ad — "ALEVLENEBİLİR SIVI, B.B.B." / "AŞINDIRICI SIVI, B.B.B."; '
         'veritabanında da B.N.O. kalmadı; katı pirofor UN 2846',
         lambda: tr_classify(['H225'], form='liquid')['road']['label'] == 'ALEVLENEBİLİR SIVI, B.B.B.'
         and tr_classify(['H314'], form='liquid')['road']['label'] == 'AŞINDIRICI SIVI, B.B.B.'
         and tr_classify(['H250'], form='solid')['road']['un'] == 'UN 2846'
         and not any('B.N.O' in (v.get('name_tr') or '') for v in __import__('json').load(
             open('data/adr_data.json', encoding='utf-8')).values())),
        ('SEA Ek-1 Tablo 2.14.2: ≥%90 Ek-6 oksitleyici — Kat.2 (Ca hipoklorit) Tehlike, Kat.3 (persülfat) Dikkat; '
         'gerekçe Md.11(3)',
         lambda: (lambda f: f('7778-54-3', 'Ox. Sol. 2') == ('H272', 'Ox. Sol. 2', 'Danger', True)
                  and f('7775-27-1', 'Ox. Sol. 3') == ('H272', 'Ox. Sol. 3', 'Warning', True))(
             lambda cas, cl: next((x['h'], x['h_class'], x['signal'], 'Md.11(3)' in x['cutoff_used'])
                                  for x in phys_calc([C(cas, 95, (cl, 'H272'), annex_vi=True), C('7732-18-5', 5)],
                                                     form='solid')['extra'] if 'oxidiz' in x['type']))),
        ('KKDİK Ek-2 9 (ampirik bilgi): sıvı karışımda patlama sınırı / yoğunluk / buhar basıncı / viskozite / '
         'çözünürlük bileşenlerden hesaplanmaz (kaynaksız iç tablolar kaldırıldı)',
         lambda: (lambda t: not ({'lel', 'uel', 'density', 'vapor_pressure', 'viscosity', 'solubility',
                                  'vapor_density', 'henry_constant'} & set(t)))(
             phys_calc([C('64-17-5', 50, ('Flam. Liq. 2', 'H225')), C('67-64-1', 50, ('Flam. Liq. 2', 'H225'))],
                       form='liquid')['theo_props'])),
        ('SEA Ek-1 2.16: bileşende H290 yok ama pH 13,5 → metal aşındırıcılık sorusu',
         lambda: 'PHYS_MET_CORR_UNTESTED' in [d['code'] for d in phys_calc(
             [C('1310-73-2', 5, ('Skin Corr. 1A', 'H314')), C('7732-18-5', 95)], form='liquid',
             mixture_ph=13.5)['pending_decisions']]),
        ('Alevlenir sıvı bileşen tarama eşiğinin altında (%0,4 etanol + %0,4 izopropanol), parlama noktası yok → '
         'bilgi uyarısı (iki alevlenir bileşen — literatür tablosu uygulanmaz)',
         lambda: any('tarama eşiğinin' in w for w in phys_calc(
             [C('64-17-5', 0.4, ('Flam. Liq. 2', 'H225')), C('67-63-0', 0.4, ('Flam. Liq. 2', 'H225')),
              C('7732-18-5', 99.2)], form='liquid')['warnings'])),
        ('SEA Ek-1 2.6.4.1 literatür parlama noktası (INERIS 2013, Abel kapalı kap): su + etanol %80 → H225, '
         '%10 → H226 (~45 °C; önceden H225), %3 → sınıf yok; %10 + L.2 olumsuz → sınıf yok (2.6.4.5); '
         'ikinci alevlenir bileşen varsa tablo uygulanmaz; sınıra ±3 °C yakınsa uygulanmaz',
         lambda: (lambda F: F(80) == 'H225' and F(10) == 'H226' and F(3) is None and F(10, 'l2_negative') is None
                  and F(40) == 'H225' and 'ölçülmelidir' in ' '.join(phys_calc(
                      [C('64-17-5', 40, ('Flam. Liq. 2', 'H225')), C('7732-18-5', 60)], form='liquid')['warnings'])
                  and [x['h'] for x in phys_calc([C('64-17-5', 10, ('Flam. Liq. 2', 'H225')),
                                                  C('67-63-0', 5, ('Flam. Liq. 2', 'H225')), C('7732-18-5', 85)],
                                                 form='liquid', fp_status='no_measurement')['results']] == ['H225'])(
             lambda p, st='': next((x['h'] for x in phys_calc(
                 [C('64-17-5', p, ('Flam. Liq. 2', 'H225')), C('7732-18-5', 100 - p)], form='liquid',
                 fp_status=st)['results'] if x.get('type') == 'flam_liq'), None))),
        ('GBF uçtan uca: %10 etanol / su → H226, Bölüm 9 parlama noktası "literatür değeri (ürün test '
         'edilmemiştir) — INERIS ...; Abel kapalı kap", Bölüm 16 kaynak notu; H225 / "hesaplanmış" yok',
         lambda: (lambda t: (lambda hdr: 'H226' in hdr and 'H225' not in hdr)(
                      t[t.find('Tehlike Kodları:'):t.find('BÖLÜM 1')])
                  and 'literatür değeri (ürün test edilmemiştir)' in t
                  and 'INERIS' in t and 'Abel kapalı kap' in t and 'SEA Ek-1 2.6.4.1' in t)(
             _pdf_text(c, [('64-17-5', 10), ('7732-18-5', 90)]))),
        ('SEA Ek-1 2.6.4.5: ölçülen parlama noktası 45 °C + L.2 olumsuz → sınıf yok; 30 °C + L.2 seçimi → H226 '
         '(35 °C altı L.2 kapsamı dışı)',
         lambda: [x['h'] for x in phys_calc([C('64-17-5', 20, ('Flam. Liq. 2', 'H225')), C('100-51-6', 80)],
                                            form='liquid', user_fp=45, fp_status='l2_negative')['results']
                  if x.get('type') == 'flam_liq'] == []
         and [x['h'] for x in phys_calc([C('64-17-5', 20, ('Flam. Liq. 2', 'H225')), C('100-51-6', 80)],
                                        form='liquid', user_fp=30, fp_status='l2_negative')['results']
              if x.get('type') == 'flam_liq'] == ['H226']),
        ('Test ihtiyacı listesi: toluen %15 + baz yağ → parlama noktası ve 40 °C kinematik viskozite ölçülmeli '
         '(SEA Md.10(2), Ek-1 3.10.3.3.1); viskozite girilince tamam; %10 etanol/su → parlama noktası literatür, L.2 '
         'isteğe bağlı; NaOH %5 → pH sınıflandırma verisi (Ek-1 3.2.3.1.2) + metal aşındırıcılık testi; N2/O2 gazı → '
         'alevlenirlik testi gerekmez; sağlık/çevre testi gerekmez (Md.10(1))',
         lambda: (lambda a, b, e, n, g: a['Parlama noktası']['durum'] == 'eksik'
                  and a['Viskozite (40 °C, kinematik)']['durum'] == 'eksik'
                  and b['Viskozite (40 °C, kinematik)']['durum'] == 'tamam'
                  and e['Parlama noktası']['durum'] == 'tamam' and 'literatür' in e['Parlama noktası']['durum_metni'].lower()
                  and e['Sürekli yanma testi (UN L.2)']['durum'] == 'istege_bagli'
                  and n['pH']['grup'] == 'siniflandirma' and n['Metallere aşındırıcılık']['durum'] == 'eksik'
                  and g['Alevlenirlik (gaz karışımı)']['grup'] == 'gerekmez'
                  and a['Sağlık ve çevre zararları (Bölüm 11–12)']['grup'] == 'gerekmez')(
             tn([('108-88-3', 15), ('64742-54-7', 85)]),
             tn([('108-88-3', 15), ('64742-54-7', 85)], test_data={'viscosity': 30}),
             tn([('64-17-5', 10), ('7732-18-5', 90)]),
             tn([('1310-73-2', 5), ('7732-18-5', 95)]),
             tn([('7727-37-9', 79), ('7782-44-7', 21)], form='gas'))),
        ('Ek-2 9.1: koku girilmemişse nedenli ifade; karışımda hesaplanmış değer yok (Bölüm 9 "ampirik bilgi"), '
         'bileşen verisi ilgili maddeye atfen (AB 2020/878 yöntemi: en uçucu / en düşük parlama noktalı bileşen), '
         'Bölüm 16 kaynak notu',
         lambda: (lambda t: 'koku değerlendirmesi yapılmamıştır' in t and 'hesaplanmış' not in t
                  and 'En uçucu bileşen: aseton 240 hPa (20 °C)' in t
                  and 'En düşük parlama noktalı bileşen: aseton' in t
                  and 'ilgili bileşene atfen verilmiştir (KKDİK Ek-2 9.1)' in t
                  and 'ECHA kayıt dosyaları (chem.echa.europa.eu)' in t)(
             _pdf_text(c, [('67-64-1', 20), ('64-17-5', 20), ('7732-18-5', 60)]))),
        ('Bileşen fiziksel verisi: ECHA anahtar değeri birimleri (K → °C, Pa → hPa, bilimsel gösterim, "[Empty]" '
         'yoğunluk alınmaz, ICSC biçimi); gazda viskozite / yoğunluk Bölüm 9\'a yazılmaz; parlama noktası Ek-6 sınıfıyla '
         'çelişen bileşen (ksilen 18 °C / H226) Bölüm 9\'a yazılmaz',
         lambda: (lambda cp: cp.parse_temp('286 K at the pressure of 101,325 Pa')['value'] == 12.9
                  and cp.parse_pressure('5,726 Pa at the temperature of 292.8 K')['value'] == 57.26
                  and cp.parse_pressure('5.83X10+3 mm Hg at 25 °C')['value'] == 7773.0
                  and cp.parse_pressure('Vapour pressure, kPa at 20 °C: 24')['value'] == 240
                  and cp.parse_density('Relative density (water = 1): 0.79')['value'] == 0.79
                  and cp.parse_temp('55 °F (13 °C) (Closed cup)')['value'] == 13
                  and 'viscosity' not in cp.section9(
                      [{'cas': 'x', 'conc': 100, 'phys': {'viscosity': {'value': 13.3, 'unit': 'mPa·s', 'ref': 'r'},
                                                          'boiling_point': {'value': -34, 'unit': '°C', 'ref': 'r'}}}],
                      True, 'gas')
                  and 'flash_point' not in cp.section9(
                      [{'cas': '1330-20-7', 'name': 'ksilen', 'conc': 50, 'hazards': [{'h_code': 'H226'}],
                        'phys': {'flash_point': {'value': 18, 'unit': '°C', 'ref': 'ECHA'}}},
                       {'cas': '7732-18-5', 'conc': 50, 'phys': {}}], False, 'liquid'))(
             __import__('app.services.component_phys', fromlist=['x']))),
        ('ISO 10156 / EIGA Doc 169 parametre tablosu 13 aydan eski değil (EIGA her Nisan yeni revizyon; '
         'data/iso10156_gas_data.json — kaynakları kontrol edip dogrulama_tarihi güncellenir)',
         lambda: (datetime.date.today() - datetime.date.fromisoformat(iso10156.data()['dogrulama_tarihi'])).days < 395),
        ("Ek-2 A 3.2 uçtan uca: panelde 'tam değer' → Bölüm 3'te 20%, aralık notu yok",
         lambda: (lambda t: '≥ 20 - < 25%' not in t and ' 20% ' in t and 'yüzde aralığı olarak' not in t)(
             _pdf_text(c, [('120-51-4', 20), ('7732-18-5', 80)], conc_display='exact'))),
        ('SEA Ek-1 Bölüm 3 genel konsantrasyon sınırları — 35 sınır noktası (Tablo 3.2.3, 3.3.3, 3.4.5, 3.5.2, '
         '3.6.2, 3.7.2, 3.8.3, 3.8.3.4.5, 3.9.4, 3.10): eşikte sınıf var, hemen altında yok',
         lambda: _gcl_sinirlari(classify_mixture_clp, _stot, C) == []),
        ('SEA Md.6(1)(c): Ek-6\'daki sınıfın ECHA\'daki farklı kategorisi eklenmez (klor Ek-6 H331 + ECHA H330 → '
         'H330 yalnız bilgi); Ek-6\'da olmayan yol/etki eklenir (soluma yolu H332, BHOT narkotik H336, Repr. F)',
         lambda: (lambda S, H: (lambda r: [h['h_code'] for h in r[0]] == [] and [a['h_code'] for a in r[1]] == ['H330'])(
                     S([H('Acute Tox. 3', 'H331')], [H('Acute Tox. 2', 'H330')]))
                  and [h['h_code'] for h in S([H('Acute Tox. 3', 'H301'), H('STOT SE 3', 'H335'), H('Repr. 1B', 'H360D')],
                                              [H('Acute Tox. 4', 'H332'), H('STOT SE 3', 'H336'), H('Repr. 2', 'H361f'),
                                               H('Acute Tox. 4', 'H302'), H('Repr. 2', 'H361')])[0]]
                  == ['H332', 'H336', 'H361f'])(
             __import__('app.services.ek6_family', fromlist=['x']).split_echa,
             lambda c, h: {'h_class': c, 'h_code': h})),
        ('SEA Md.4 / Ek-1 3.1.2: tek maddeli ürün maddenin kendi sınıfını alır (Kat.2 gaz → Kat.2, ATEmix yok); '
         'karışımda Tablo 3.1.1 harfiyen (iki Kat.2 gaz %50+%50 → ATEmix 100 ppmV → Kat.1)',
         lambda: (lambda sub, mix: [x['cat_num'] for x in sub] == [2] and [x['cat_num'] for x in mix] == [1])(
             __import__('app.services.sds_pipeline', fromlist=['x'])._substance_acute(
                 {'cas': 'x', 'conc': 100, 'sea_ek6': True,
                  'hazards': [{'h_class': 'Acute Tox. 2', 'h_code': 'H330'}]}, 'gas'),
             _ate_core([{'cas': c, 'name': c, 'conc': 50, 'source_priority': 1, 'ate': {},
                         'hazards': [{'h_class': 'Acute Tox. 2', 'h_code': 'H330'}]} for c in ('a', 'b')],
                       form='gas')[0])),
        ('ADR 2025 Tablo A (ECE/TRANS/352 Cilt I): UN1017 2TOC/C/D/265, UN1230 tünel D/E, UN1648 F1/33, '
         'UN2014 OC1, UN1199 Sınıf 6.1',
         lambda: (lambda A: A['UN1017']['classification_code'] == '2TOC'
                  and A['UN1017']['packing_groups']['-']['tunnel'] == 'C/D' and A['UN1017']['kemler'] == '265'
                  and A['UN1230']['packing_groups']['II']['tunnel'] == 'D/E'
                  and A['UN1648']['classification_code'] == 'F1' and A['UN1648']['packing_groups']['II']['kemler'] == '33'
                  and A['UN2014']['classification_code'] == 'OC1' and A['UN1199']['class'] == '6.1')(
             __import__('json').load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                                       'data', 'adr_data.json'), encoding='utf-8')))),
        # ── tests/ klasöründen taşınanlar (2026-10-08; klasör silindi) ──────────────────────────────────
        ('SEA Ek-1 Tablo 3.9.4: STOT RE 2 toplanmaz — %8 + %8 → H373 yok; tek bileşen %10 → H373',
         lambda: _stot([C('110-54-3', 8, ('STOT RE 2', 'H373')), C('71-43-2', 8, ('STOT RE 2', 'H373')),
                        C('7732-18-5', 84)])['h_codes'] == []
         and 'H373' in _stot([C('110-54-3', 10, ('STOT RE 2', 'H373')), C('7732-18-5', 90)])['h_codes']),
        ('SEA Ek-1 4.1 kronik toplama M faktörüyle: Kronik 1 M=10 %3 → H410; %2 → H411',
         lambda: all(calculate_aquatic([C('x', k, ('Aquatic Chronic 1', 'H410'), m_factors={'acute': 1, 'chronic': 10}),
                                        C('7732-18-5', 100 - k)]).h_code == h for k, h in ((3, 'H410'), (2, 'H411')))),
        ('SEA Ek-1 3.2 baskınlık: %5 NaOH (Kat.1A) → H314 var, H315 yok',
         lambda: (lambda h: 'H314' in h and 'H315' not in h)(classify_mixture_clp(
             [C('1310-73-2', 5, ('Skin Corr. 1A', 'H314')), C('7732-18-5', 95)])['h_codes'])),
        ('SEA Ek-1 3.1.3.6.1: su ATEmix\'te bilinmeyen sayılmaz (ate_unknown True/False) — %4 ATE 500 → sınıf yok',
         lambda: all((lambda r: abs(r[2].get('oral', 0)) < 1e-9 and not any(
             x['h_code'] in ('H300', 'H301', 'H302') for x in r[0]))(_ate_core([
                 {'cas': '7732-18-5', 'name': 'Su', 'conc': 96, 'ate_unknown': u, 'hazards': [], 'ate': {}},
                 {'cas': '108-88-3', 'name': 'B', 'conc': 4, 'ate_unknown': False,
                  'hazards': [{'h_code': 'H302', 'h_class': 'Acute Tox. 4'}], 'ate': {'oral': 500}}], form='liquid'))
             for u in (True, False))),
        ('ADR 3.1.3.2 baskın madde: %90 TCCA katı → UN2468 Sınıf 5.1; sıvı üründe "KURU" girişi verilmez',
         lambda: (lambda r: '2468' in r['un'] and r['class'] == '5.1')(tr_classify(
             ['H272', 'H302', 'H410'], form='solid',
             components=[TC(cas='87-90-1', conc=90.0, h_codes=['H272', 'H302', 'H410']),
                         TC(cas='7647-14-5', conc=8.0, h_codes=[])])['road'])
         and '2468' not in (tr_classify(['H272', 'H302', 'H410'], form='liquid',
             components=[TC(cas='87-90-1', conc=95.0, h_codes=['H272', 'H302', 'H410']),
                         TC(cas='7647-14-5', conc=5.0, h_codes=[])])['road'].get('un') or '')),
        ('ADR SP 135: troklosen sodyum dihidrat (DIPOL 306) adlı girişe girmez → çevre için UN3077 Sınıf 9; '
         'yalnız H319 → taşımada tehlikesiz',
         lambda: (lambda r: not r.get('not_regulated') and r['road']['class'] == '9' and '3077' in r['road']['un']
                  and r.get('env_mark') is True)(tr_classify(
             ['H302', 'H319', 'H335', 'H410'], form='solid', components=build_tc([
                 {'cas_no': '51580-86-0', 'conc': 92.0, 'hazards': [
                     {'h_class': 'Acute Tox. 4', 'h_code': 'H302'}, {'h_class': 'Eye Irrit. 2', 'h_code': 'H319'},
                     {'h_class': 'STOT SE 3', 'h_code': 'H335'}, {'h_class': 'Aquatic Acute 1', 'h_code': 'H400'},
                     {'h_class': 'Aquatic Chronic 1', 'h_code': 'H410'}]},
                 {'cas_no': '7647-14-5', 'conc': 8.0, 'hazards': []}])))
         and tr_classify(['H319'], form='liquid', components=[TC(cas='1234-56-7', conc=90.0, h_codes=['H319']),
                                                             TC(cas='7647-14-5', conc=10.0, h_codes=[])])
         .get('not_regulated')),
        ('Taşıma: okunamayan / eksik konsantrasyon sessizce 0 sayılmaz — hata verir',
         lambda: all(_raises(lambda r=r: build_tc(r)) for r in (
             [{'cas_no': '87-90-1', 'conc': 'GIZLI', 'h_codes': ['H272']}],
             [{'cas_no': '87-90-1', 'h_codes': ['H272']}]))),
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


def _pdf_text(c, bil, **extra) -> str:
    """Kısa uçtan uca GBF: bileşen listesiyle PDF üretip metnini (boşluklar tek) döndürür."""
    import fitz
    comps = []
    for cas, conc in bil:
        r = c.get('/api/v1/sds/substance/lookup', params={'cas': cas, 'form': 'liquid'}).json()
        comps.append({'cas': cas, 'name': r.get('name') or cas, 'name_tr': r.get('name_tr', ''), 'conc': conc,
                      'concMax': conc, 'hazards': r.get('hazards', []), 'sclRaw': r.get('scl', []), 'm_factors': {}})
    calc = {'components': comps, 'form': 'liquid', 'usage': 'industrial', 'lang': 'TR'}
    body = {'lang': 'TR', 'product': {'name': 'Kural testi', 'form': 'liquid', 'usage': 'industrial'},
            'supplier': {'name': 'Kontrol Seti A.Ş.', 'address': 'Örnek Mah. No:1 İstanbul', 'phone': '0212 000 00 00',
                         'email': 'kontrol@ornek.com'},
            'components': comps, 'calc_input': calc, 'phys_props': {}, 'phys_methods': {},
            'revision': {'no': '1', 'date': '08.10.2026', 'notes': ''}, **extra}
    j = c.post('/api/v1/sds/pdf', json=body).json()
    b64 = next(v for v in j.values() if isinstance(v, str) and len(v) > 5000)
    return _norm('\n'.join(p.get_text() for p in fitz.open(stream=base64.b64decode(b64), filetype='pdf')))


def _norm(t: str) -> str:
    t = re.sub(r'Sayfa \d+ / \d+\s.*?formatına uygundur\.\s', ' ', t, flags=re.S)
    return re.sub(r'\s+', ' ', t)


def main(run_jev: bool) -> int:
    from fastapi.testclient import TestClient
    from app.main import app
    import fitz
    from app.services.audit_checks import run_code_checks

    c = TestClient(app)

    def comp(cas, conc, form='liquid'):
        r = c.get('/api/v1/sds/substance/lookup', params={'cas': cas, 'form': form}).json()
        return {'cas': cas, 'name': r.get('name') or cas, 'name_tr': r.get('name_tr', ''), 'ec_no': r.get('ec_no', ''),
                'conc': conc, 'concMax': conc, 'hazards': r.get('hazards', []), 'sclRaw': r.get('scl', []),
                'm_factors': {}, 'ate': None}

    hatalar, t0 = 0, time.time()
    dipol_pages = None
    for u in URUNLER:
        sorun = []
        form = u.get('form', 'liquid')
        comps = [comp(a, b, form) for a, b in u['bil']]
        calc = {'components': comps, 'form': form, 'usage': 'industrial', 'lang': 'TR',
                'test_data': dict(u.get('test_data') or {})}
        # Karar sorusu beklenen ürün: karar verilmeden önce soru çıkmalı (bileşen varlığından H kodu verilmemeli)
        if u.get('soru'):
            _td0 = {k: v for k, v in calc['test_data'].items() if k != u['soru'][1]}
            r0 = c.post('/api/v1/sds/calculate', json={**calc, 'test_data': _td0}).json()
            if u['soru'][0] not in [d.get('code') for d in r0.get('pending_decisions') or []]:
                sorun.append(f"karar sorusu çıkmadı: {u['soru'][0]}")
        r = c.post('/api/v1/sds/calculate', json=calc).json()
        h = sorted(str(x).split()[0].upper() for x in (r.get('h_codes') or []))
        if h != sorted(x.upper() for x in u['h']):
            sorun.append(f"H kodları {h} — beklenen {sorted(u['h'])}")
        if (r.get('signal') or '') != u['signal']:
            sorun.append(f"uyarı kelimesi {r.get('signal')!r} — beklenen {u['signal']!r}")
        body = {'lang': 'TR', 'product': {'name': u['ad'][:40], 'form': form, 'usage': 'industrial',
                                          'is_detergent': bool(u.get('det')), 'usage_desc': u.get('kullanim', '')},
                'supplier': {'name': 'Kontrol Seti A.Ş.', 'address': 'Örnek Mah. No:1 İstanbul', 'phone': '0212 000 00 00',
                             'email': 'kontrol@ornek.com'},
                'components': comps, 'calc_input': calc, 'phys_props': dict(u.get('phys') or {}), 'phys_methods': {},
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
