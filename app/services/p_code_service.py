"""
P Kodu Servisi (Güvenlik Önlemleri)
=====================================
CLP Regulation (EC) No 1272/2008 — Annex IV

P ifadeleri H kodlarından otomatik atanır.
CLP Annex IV Tablo 6.2'deki eşleşme kuralları uygulanır.

P Kodu Kategorileri:
  P1xx → Genel (General)
  P2xx → Önleme (Prevention)
  P3xx → Müdahale (Response)
  P4xx → Saklama (Storage)
  P5xx → İmha (Disposal)

Kombinasyon Kuralları:
  - Aynı kategorideki benzer P kodları birleştirilir
  - Kombine kodlar (P301+P310) birlikte yazılır
  - Maksimum 6 P kodu önerilir (SDS için kısıtlama yok)

Veri Kaynağı: CLP Annex IV (2023 güncellemeli)
"""

from app.services.codes_i18n import get_p

from typing import List, Dict, Set, Optional


# ─── P KODU METİNLERİ (Türkçe) ───────────────────────────────────────────────

P_TEXTS: Dict[str, str] = {
    # P1xx — Genel
    'P101': 'Tıbbi tavsiye için, mümkünse ürün kabını veya etiketini hazır bulundurun.',
    'P102': 'Çocukların ulaşamayacağı yerde saklayın.',
    'P103': 'Kullanmadan önce etiketi okuyun.',

    # P2xx — Önleme
    'P201': 'Kullanmadan önce özel talimatları edinin.',
    'P202': 'Tüm güvenlik talimatlarını okuyup anlamadan kullanmayın.',
    'P210': 'Isı, kıvılcım, açık alev ve sıcak yüzeylerden uzak tutun. Sigara içmeyin.',
    'P211': 'Açık alev veya diğer tutuşma kaynaklarına püskürtmeyin.',
    'P220': 'Giysi ve yanıcı maddelerden uzak tutun.',
    'P221': 'Yanıcı maddelerle karışmasını önlemek için her türlü tedbiri alın.',
    'P222': 'Hava ile temasına izin vermeyin.',
    'P223': 'Su ile temasına kesinlikle izin vermeyin.',
    'P230': 'Nemli tutarak saklayın.',
    'P231': 'İnert gaz altında saklayın ve kullanın.',
    'P232': 'Nemi önleyin.',
    'P233': 'Kabı sıkıca kapalı tutun.',
    'P234': 'Yalnızca orijinal kabında saklayın.',
    'P235': 'Serin yerde saklayın.',
    'P240': 'Kabı ve alıcı ekipmanı topraklayın/bağlayın.',
    'P241': 'Patlamaya dayanıklı elektrik/havalandırma/aydınlatma ekipmanı kullanın.',
    'P242': 'Sadece kıvılcım çıkarmayan aletler kullanın.',
    'P243': 'Statik elektrik oluşumunu önleyin.',
    'P244': 'Valfleri yağ ve gresden uzak tutun.',
    'P250': 'Taşlama/şok/sürtünme gibi uygulamalardan kaçının.',
    'P251': 'Basınç altında delinmeyin veya yakılmayın, kullanım sonrasında bile.',
    'P260': 'Toz/duman/gaz/sis/buhar/aerosol solumayın.',
    'P261': 'Toz/duman/gaz/sis/buhar/aerosol solumaktan kaçının.',
    'P262': 'Göz, cilt veya giysiyle temastan kaçının.',
    'P263': 'Hamilelik süresince ve emzirme döneminde temastan kaçının.',
    'P264': 'Kullanımdan sonra elleri ve maruz kalan bölgeleri iyice yıkayın.',
    'P270': 'Bu ürünü kullanırken yemek yemeyin, bir şey içmeyin ve sigara içmeyin.',
    'P271': 'Yalnızca açık havada veya iyi havalandırılan alanlarda kullanın.',
    'P272': 'Kirlenmiş iş kıyafetini işyerinden çıkarmayın.',
    'P273': 'Çevreye salınımından kaçının.',
    'P280': 'Koruyucu eldiven/koruyucu giysi/göz koruyucu/yüz koruyucu kullanın.',
    'P281': 'Gerekli kişisel koruyucu ekipmanı kullanın.',
    'P282': 'Soğuğa karşı koruyucu eldiven ve yüz/göz koruyucu kullanın.',
    'P283': 'Aleve dayanıklı/yanmaz giysi kullanın.',
    'P284': 'İyi havalandırma yoksa solunum koruyucu kullanın.',
    'P285': 'Yetersiz havalandırma durumunda solunum koruyucu kullanın.',

    # P3xx — Müdahale
    'P301': 'YUTULURSA:',
    'P302': 'CİLDE TEMAS DURUMUNDA:',
    'P303': 'CİLDE (veya SAÇA) TEMAS DURUMUNDA:',
    'P304': 'SOLUNURSA:',
    'P305': 'GÖZLE TEMAS DURUMUNDA:',
    'P306': 'GİYSİYE TEMAS DURUMUNDA:',
    'P307': 'MARUZ KALMASI HALİNDE:',
    'P308': 'MARUZ KALINMASI VEYA ENDİŞE DUYULMASI HALİNDE:',
    'P310': 'Derhal ZEHİR MERKEZİ/doktoru/... arayın.',
    'P311': 'ZEHİR MERKEZİ/doktoru/... arayın.',
    'P312': 'Kendinizi iyi hissetmiyorsanız ZEHİR MERKEZİ/doktoru/... arayın.',
    'P313': 'Tıbbi yardım alın.',
    'P314': 'Kendinizi iyi hissetmiyorsanız tıbbi yardım alın.',
    'P315': 'Derhal tıbbi yardım alın.',
    'P320': 'Acil tedavi gereklidir (bkz. bu etiket).',
    'P321': 'Özel tedavi (bkz. bu etiket).',
    'P330': 'Ağzı çalkalayın.',
    'P331': 'KUSMayı UYARMAYIN.',
    'P332': 'Cilt tahrişi oluşursa:',
    'P333': 'Cilt tahrişi veya kızarıklık oluşursa:',
    'P334': 'Soğuk suya batırın/nemli bandaj uygulayın.',
    'P335': 'Ciltteki gevşek partikülleri fırçalayın.',
    'P336': 'Donmuş bölgeleri ılık suyla çözün. Etkilenen bölgeyi ovalamayın.',
    'P337': 'Göz tahrişi devam ederse:',
    'P338': 'Varsa kontakt lensleri çıkarın. Gözleri yıkamaya devam edin.',
    'P340': 'Kişiyi temiz havaya çıkarın ve rahat nefes almasını sağlayın.',
    'P341': 'Nefes almak güçleşirse, kişiyi temiz havaya çıkarın ve rahat nefes almasını sağlayın.',
    'P342': 'Solunum belirtileri varsa:',
    'P350': 'Sabun ve bol su ile yavaşça yıkayın.',
    'P351': 'Birkaç dakika boyunca suyla dikkatlice yıkayın.',
    'P352': 'Bol su ile yıkayın.',
    'P353': 'Cilde su dökün/duş alın.',
    'P360': 'Kirlenmiş giysi ve cildi, giysiyi çıkarmadan önce hemen bol su ile durulayın.',
    'P361': 'Kirlenmiş tüm giysileri hemen çıkarın.',
    'P362': 'Kirlenmiş giysileri çıkarın ve tekrar kullanmadan önce yıkayın.',
    'P363': 'Kirlenmiş giysileri tekrar kullanmadan önce yıkayın.',
    'P370': 'Yangın durumunda:',
    'P371': 'Büyük yangın ve büyük miktarlar söz konusu olduğunda:',
    'P372': 'Patlama riski vardır.',
    'P373': 'Yangın patlayıcılara ulaşırsa yangına MÜDAHALE ETMEYİN.',
    'P374': 'Standart önlemlerle yangına makul bir mesafeden müdahale edin.',
    'P375': 'Patlama riski nedeniyle yangına uzaktan müdahale edin.',
    'P376': 'Güvenli yapılabiliyorsa kaçak durdurulabilir.',
    'P377': 'Gaz kaçağından kaynaklanan yangın: Kaçak güvenli biçimde durdurulamıyorsa yangını söndürmeyin.',
    'P378': 'Söndürmek için ... kullanın.',
    'P380': 'Bölgeyi boşaltın.',
    'P381': 'Güvenli yapılabiliyorsa tüm tutuşma kaynaklarını ortadan kaldırın.',
    'P390': 'Malzeme hasarını önlemek için döküleni emin.',
    'P391': 'Döküntüleri toplayın.',

    # P4xx — Saklama
    'P401': 'Saklayın ...',
    'P402': 'Kuru yerde saklayın.',
    'P403': 'İyi havalandırılan bir yerde saklayın.',
    'P404': 'Kapalı bir kapta saklayın.',
    'P405': 'Kilitli olarak saklayın.',
    'P406': 'Aşındırmaya dayanıklı/... kapta saklayın.',
    'P407': 'Yığınlar/paletler arasında hava boşluğu bırakın.',
    'P410': 'Güneş ışığından koruyun.',
    'P411': '... °C\'yi aşmayan sıcaklıklarda saklayın.',
    'P412': '50 °C\'yi (122 °F) aşan sıcaklıklara maruz bırakmayın.',
    'P413': 'Dökme miktarları ... kg\'ı aşıyorsa, ... °C\'yi aşmayan sıcaklıklarda saklayın.',
    'P420': 'Diğer maddelerden ayrı saklayın.',

    # P5xx — İmha
    'P501': 'İçindekilerini/kabını ... yönetmeliğine uygun olarak imha edin.',
    'P502': 'Geri dönüşüm veya yeniden kazanım hakkında üretici/tedarikçiye danışın.',
}

# Kombine P kodları — birlikte yazılır
P_COMBOS: Dict[str, str] = {
    'P301+P310':     'YUTULURSA: Derhal ZEHİR MERKEZİ/doktoru arayın.',
    'P301+P312':     'YUTULURSA: Kendinizi iyi hissetmiyorsanız ZEHİR MERKEZİ/doktoru arayın.',
    'P301+P330+P331':'YUTULURSA: Ağzı çalkalayın. KUSMayı UYARMAYIN.',
    'P302+P350':     'CİLDE TEMAS DURUMUNDA: Sabun ve bol su ile yavaşça yıkayın.',
    'P302+P352':     'CİLDE TEMAS DURUMUNDA: Bol sabun ve su ile yıkayın.',
    'P303+P361+P353':'CİLDE (veya SAÇA) TEMAS DURUMUNDA: Kirlenmiş giysileri hemen çıkarın. Cilde su dökün.',
    'P304+P340':     'SOLUNURSA: Kişiyi temiz havaya çıkarın ve rahat nefes almasını sağlayın.',
    'P304+P341':     'SOLUNURSA: Nefes almak güçleşirse, kişiyi temiz havaya çıkarın.',
    'P305+P351+P338':'GÖZLE TEMAS DURUMUNDA: Birkaç dakika boyunca suyla dikkatlice yıkayın. Varsa kontakt lensleri çıkarın. Yıkamaya devam edin.',
    'P306+P360':     'GİYSİYE TEMAS DURUMUNDA: Kirlenmiş giysiyi çıkarmadan önce hemen bol su ile durulayın.',
    'P307+P311':     'MARUZ KALINMASI HALİNDE: ZEHİR MERKEZİ/doktoru arayın.',
    'P308+P311':     'MARUZ KALINMASI VEYA ENDİŞE DUYULMASI HALİNDE: ZEHİR MERKEZİ/doktoru arayın.',
    'P308+P313':     'MARUZ KALINMASI VEYA ENDİŞE DUYULMASI HALİNDE: Tıbbi yardım alın.',
    'P332+P313':     'Cilt tahrişi oluşursa: Tıbbi yardım alın.',
    'P333+P313':     'Cilt tahrişi veya kızarıklık oluşursa: Tıbbi yardım alın.',
    'P337+P313':     'Göz tahrişi devam ederse: Tıbbi yardım alın.',
    'P342+P311':     'Solunum belirtileri varsa: ZEHİR MERKEZİ/doktoru arayın.',
    'P370+P376':     'Yangın durumunda: Güvenli yapılabiliyorsa kaçak durdurulabilir.',
    'P370+P378':     'Yangın durumunda: Söndürmek için ... kullanın.',
    'P370+P380':     'Yangın durumunda: Bölgeyi boşaltın.',
    'P370+P380+P375':'Yangın durumunda: Bölgeyi boşaltın. Patlama riski nedeniyle uzaktan müdahale edin.',
    'P371+P380+P375':'Büyük yangın durumunda: Bölgeyi boşaltın. Uzaktan müdahale edin.',
    'P231+P232':     'İnert gaz altında işleyin. Nemi önleyin.',
    'P235+P410':     'Serin yerde saklayın. Güneş ışığından koruyun.',
    'P302+P334':     'CİLDE TEMAS DURUMUNDA: Soğuk suya sokun ya da ıslak pansuman uygulayın.',
    'P335+P334':     'Ciltteki gevşek partikülleri fırçalayın. Soğuk suya batırın/nemli bandaj uygulayın.',
    'P402+P404':     'Kapalı bir kapta kuru yerde saklayın.',
    'P403+P233':     'Kabı sıkıca kapalı tutarak iyi havalandırılan bir yerde saklayın.',
    'P403+P235':     'Serin, iyi havalandırılan bir yerde saklayın.',
    'P410+P403':     'Güneş ışığından koruyun. İyi havalandırılan bir yerde saklayın.',
    'P410+P412':     'Güneş ışığından koruyun. 50 °C\'yi aşan sıcaklıklara maruz bırakmayın.',
}


# ─── H → P ATAMA TABLOSU ─────────────────────────────────────────────────────

# Her H kodu için: zorunlu P kodları listesi
# Formatlar: 'P210' (tek), 'P301+P310' (kombine)
H_TO_P: Dict[str, List[str]] = {
    # ── Yanıcı Gaz ───────────────────────────────────────────────────────────
    # CLP Annex IV Tablo 6.1: H220/H221 → P210, P377, P381, P403
    'H220': ['P210','P377','P381','P403'],
    'H221': ['P210','P377','P381','P403'],

    # ── Aerosol ──────────────────────────────────────────────────────────────
    # CLP Annex IV: H222/H223 → P210, P211, P251, P410+P412
    'H222': ['P210','P211','P251','P410+P412'],
    'H223': ['P210','P211','P251','P410+P412'],

    # ── Yanıcı Sıvı ──────────────────────────────────────────────────────────
    'H224': ['P210','P233','P241','P242','P243','P280',
             'P303+P361+P353','P370+P378','P403+P235','P501'],
    'H225': ['P210','P233','P241','P242','P243','P280',
             'P303+P361+P353','P370+P378','P403+P235','P501'],
    'H226': ['P210','P233','P280','P370+P378','P403+P235','P501'],
    # H227: Yanıcı Sıvı Kat.4 (düşük tehlike) — CLP Annex IV
    'H227': ['P210','P280','P370+P378','P403+P235','P501'],

    # ── Aspirasyon Toksisitesi ────────────────────────────────────────────────
    'H304': ['P260','P264','P270','P301+P310','P331','P405','P501'],

    # ── Cilt/Göz ─────────────────────────────────────────────────────────────
    'H314': ['P260','P264','P280',
             'P301+P330+P331','P303+P361+P353','P304+P340',
             'P305+P351+P338','P310','P321','P363','P405','P501'],
    'H315': ['P264','P280','P302+P352','P321','P332+P313','P362','P501'],
    'H316': ['P264','P272','P280','P302+P352','P333+P313','P321','P363','P501'],
    # H317: P321 kaldırıldı — Cilt duyarlılaştırıcı için maddeye özel antidot yok
    'H317': ['P261','P272','P280','P302+P352','P333+P313','P363','P501'],
    'H318': ['P264','P280','P305+P351+P338','P310','P501'],
    'H319': ['P264','P280','P305+P351+P338','P337+P313','P501'],

    # ── Solunum/Deri Duyarlılaştırıcı ────────────────────────────────────────
    'H334': ['P260','P271','P284','P304+P340','P342+P311','P501'],
    'H335': ['P261','P271','P304+P340','P312','P501'],
    'H336': ['P261','P271','P304+P340','P312','P501'],

    # ── Akut Toksisite ────────────────────────────────────────────────────────
    'H300': ['P264','P270','P301+P310','P321','P330','P405','P501'],
    'H301': ['P264','P270','P301+P310','P321','P330','P405','P501'],
    'H302': ['P264','P270','P301+P312','P330','P501'],
    'H310': ['P262','P264','P270','P280','P302+P350','P310','P321','P361','P405','P501'],
    'H311': ['P280','P302+P352','P312','P321','P361','P405','P501'],
    'H312': ['P280','P302+P352','P312','P321','P501'],
    'H330': ['P260','P271','P284','P304+P340','P310','P320','P403+P233','P405','P501'],
    'H331': ['P261','P271','P304+P340','P311','P321','P403+P233','P405','P501'],
    'H332': ['P261','P271','P304+P340','P312','P501'],

    # ── Mutajenisite/Karsinojenite/Üreme ─────────────────────────────────────
    'H340': ['P201','P202','P280','P308+P313','P405','P501'],
    'H341': ['P201','P202','P280','P308+P313','P405','P501'],
    'H350': ['P201','P202','P280','P308+P313','P405','P501'],
    'H350i':['P201','P202','P280','P308+P313','P405','P501'],
    'H351': ['P201','P202','P280','P308+P313','P405','P501'],
    'H360': ['P201','P202','P263','P280','P308+P313','P405','P501'],
    'H360D':['P201','P202','P263','P280','P308+P313','P405','P501'],
    'H360F':['P201','P202','P263','P280','P308+P313','P405','P501'],
    'H361': ['P201','P202','P263','P280','P308+P313','P405','P501'],
    'H361d':['P201','P202','P263','P280','P308+P313','P405','P501'],
    'H362': ['P263','P264','P270'],

    # ── STOT ─────────────────────────────────────────────────────────────────
    'H370': ['P260','P264','P270','P307+P311','P405','P501'],
    'H371': ['P260','P264','P270','P308+P313','P405','P501'],
    # H372 Tehlike → P405 (kilitli depolama) eklendi — CLP Annex IV best practice
    'H372': ['P260','P264','P270','P314','P405','P501'],
    'H373': ['P260','P314','P501'],

    # ── Aquatic ───────────────────────────────────────────────────────────────
    # CLP Annex IV: P273 H400/H410/H411 için zorunlu; P391 döküntü toplama
    'H400': ['P273','P391','P501'],
    'H410': ['P273','P391','P501'],
    'H411': ['P273','P391','P501'],
    'H412': ['P273','P501'],          # Cat.3: P273 yeterli, P391 zorunlu değil
    'H413': ['P273','P501'],
    # H273: Çevreye zararlı ama kategorilendirilmemiş — minimal P kodu
    'H273': ['P501'],

    # ── Ozon ──────────────────────────────────────────────────────────────────
    'H420': ['P502'],

    # ── Oksitleyici ───────────────────────────────────────────────────────────
    'H271': ['P210','P220','P221','P280','P283',
             'P306+P360','P370+P378','P405','P501'],
    'H272': ['P210','P220','P221','P280','P370+P378','P501'],   # P221 zorunlu (CLP Annex III)

    # ── Yanıcı Katı ───────────────────────────────────────────────────────────
    'H228': ['P210','P240','P241','P280','P370+P378','P501'],

    # ── Basınçlı Gaz ─────────────────────────────────────────────────────────
    'H280': ['P410','P403'],
    'H281': ['P282','P410','P403'],
    'H229': ['P210','P251','P410+P412'],

    # ── Oksitleyici Gaz ──────────────────────────────────────────────────────
    'H270': ['P220','P244','P370+P376','P403'],

    # ── Su Reaktif ───────────────────────────────────────────────────────────
    'H260': ['P223','P231+P232','P370+P378','P402+P404','P501'],
    'H261': ['P231+P232','P370+P378','P402+P404','P501'],

    # ── Pirofor ──────────────────────────────────────────────────────────────
    # H250: Pirofor — CLP Annex IV Tablo 6.2
    # P335+P334: ciltteki gevşek partikülleri fırçala, SONRA soğuk su — pirofor için kritik sıra
    # P302+P334 (genel cilt temas) ile karıştırılmamalı; P335 önce fırçalama adımını ekler
    'H250': ['P210','P222','P235+P410','P280','P335+P334','P370+P378'],
    'H251': ['P235+P410','P407','P413','P420'],
    'H252': ['P235+P410','P407','P413','P420'],

    # ── Kendi Kendine Isınan ─────────────────────────────────────────────────
    'H240': ['P210','P234','P280','P370+P378','P420','P501'],
    'H241': ['P210','P234','P280','P370+P378','P420','P501'],
    'H242': ['P210','P234','P280','P370+P378','P501'],

    # ── Metallere Aşındırıcı ─────────────────────────────────────────────────
    'H290': ['P234','P390','P404'],

    # ── Akut Toksisite Kat.5 ve diğer "Olabilir" ─────────────────────────────
    'H303': ['P312'],
    'H305': ['P301+P312','P330','P331'],
    'H313': ['P302+P352','P312','P321','P362'],
    'H320': ['P264','P305+P351+P338','P337+P313'],
    'H333': ['P304+P340','P312'],

    # ── Sucul Akut Kat.2 ─────────────────────────────────────────────────────
    'H401': ['P273','P391','P501'],
}


# ─── P KODU ÇAKIŞMA KURALLARI ────────────────────────────────────────────────
# Daha güçlü P kodu varsa zayıfı çıkar
P_SUPERSEDES: Dict[str, List[str]] = {
    # P310 (derhal ara) daha güçlü — P311/P312 ve P301+P312 kombine kodunu da ezer
    # H314+H302 kombinasyonunda: P310 gelir (H314'ten), P301+P312 silinir (H302'den)
    # Sonuç: P301+P330+P331 + P310 kalır → korozif yutma için doğru
    'P310':           ['P311', 'P312', 'P301+P312'],
    'P301+P310':      ['P301+P312'],
    'P304+P340':      ['P304+P341'],    # P340 daha kapsamlı
    'P305+P351+P338': [],
    'P260':           ['P261'],         # P260 (solunum) daha güçlü
    'P271':           ['P261'],
    # P403+P233 varsa ayrı P233 gereksiz
    'P403+P233':      ['P233'],
}


# ─── ANA FONKSİYON ───────────────────────────────────────────────────────────

def assign_p_codes(
    h_codes: List[str],
    signal_word: str = 'Warning',
    mixture_form: str = 'liquid',
    usage: str = 'industrial',  # 'consumer' | 'professional' | 'industrial'
) -> Dict:
    """
    H kodları listesinden P kodlarını ata.

    Args:
        h_codes: Karışımın H kodları ['H225', 'H315', ...]
        signal_word: 'Danger' veya 'Warning'
        mixture_form: 'liquid'|'solid'|'aerosol'|'paste'

    Returns:
        {
          'p_codes': ['P210', 'P233', ...],
          'p_details': [{'code', 'text', 'category', 'combined'}],
          'by_category': {'prevention': [...], 'response': [...], ...},
          'mandatory': ['P101', 'P102'],
        }
    """
    assigned: Set[str] = set()

    # Her H kodu için P kodlarını topla
    for h in h_codes:
        h_clean = h.replace('*', '').replace(' ', '').strip()
        p_list = H_TO_P.get(h_clean, [])
        for p in p_list:
            assigned.add(p)

    # Zorunlu P kodları — çakışma sonrası eklenecek
    if usage == 'consumer':
        mandatory = ['P101', 'P102', 'P103']
    elif usage == 'professional':
        mandatory = ['P101']
    else:  # industrial
        mandatory = []

    # Çakışma kontrolü — güçlü kod varsa zayıfı çıkar
    final = set(assigned)
    for strong, weaks in P_SUPERSEDES.items():
        if strong in final:
            for weak in weaks:
                final.discard(weak)

    # P103 consumer/professional için usage mantığında zaten eklendi

    # Zorunlu P kodlarını ekle (çakışma sonrası)
    for p in mandatory:
        final.add(p)

    # Sıralı liste
    all_codes = sorted(
        list(final),
        key=lambda x: (x.split('+')[0])
    )

    # Detay listesi
    details = []
    for code in all_codes:
        text = P_COMBOS.get(code) or P_TEXTS.get(code, code)
        first = code.split('+')[0]
        cat_num = int(first[1]) if len(first) > 1 else 0
        category = {
            1: 'general', 2: 'prevention', 3: 'response',
            4: 'storage', 5: 'disposal'
        }.get(cat_num, 'other')
        details.append({
            'code': code,
            'text': text,
            'category': category,
            'combined': '+' in code,
        })

    # Kategoriye göre grupla
    by_category: Dict[str, List] = {
        'general': [], 'prevention': [], 'response': [],
        'storage': [], 'disposal': []
    }
    for d in details:
        by_category.get(d['category'], by_category['general']).append(d)

    return {
        'p_codes': all_codes,
        'p_details': details,
        'by_category': by_category,
        'mandatory': mandatory,
        'total': len(all_codes),
    }


# ─── ETİKET P KODU SEÇİMİ ────────────────────────────────────────────────────

# Öncelik ağırlıkları — yüksek = önce seçilir
P_LABEL_PRIORITY: Dict[str, int] = {
    # Response — can güvenliği (en yüksek öncelik)
    'P301+P310': 100, 'P301+P330+P331': 95, 'P303+P361+P353': 90,
    'P304+P340': 88,  'P305+P351+P338': 85, 'P308+P313': 82,
    'P308+P311': 80,  'P307+P311': 78,      'P310': 75,
    'P301+P312': 73,  # H302 yutma müdahalesi — response kodu, öncelik yüksek
    'P342+P311': 72,  'P335+P334': 67,      'P302+P352': 65,      'P333+P313': 61,
    'P332+P313': 57,  'P337+P313': 55,
    # Aspirasyon: KUSMayı UYARMAYIN — hayati önem (aspiration tox → kusturma ölümcül)
    'P331': 87,
    # STOT RE tıbbi yardım — kronik hasar riski
    'P314': 60,

    # Prevention + Response — kritik önlemler
    'P370+P378': 56,  # Yangın müdahale → acil yanıt (response > prevention, CLP Annex IV)
    # Su reaktif: inert gaz zorunlu — yangın ve patlama riski
    'P231+P232': 75,
    # Gaz yangın önleme: kaçak yangın söndürme ve tutuşma kaynağı uzaklaştırma
    'P377': 58,
    'P381': 53,
    'P210': 54,       # Yanıcı → tutuşma kaynağı önleme (H224/H225/H226)
    'P211': 46,       # Aerosol → açık aleve püskürtme
    'P273': 52,       # Çevre — H411/H410/H400 için ECHA rehber gereği etikette olmalı
    'P280': 51,       # KKE — H317/H319/H314 için zorunlu (H_BASED_LABEL_FORCED ile zaten giriyor)
    'P260': 48,       # Solunum koruma (H334/H330/H372 için kritik)
    'P220': 47,       # Oksitleyici — yanıcı maddelerden uzak tut (H271/H272)
    'P221': 45,       # Oksitleyici — yanıcılarla karışımı önle (H271/H272)
    'P284': 44,       # Solunum cihazı (H334 Resp.Sens. için)
    'P201': 43,       # CMR — talimat al (H340/H350/H360 için)
    'P263': 42,       # Hamile/emziren (H360 için)
    'P271': 40,       # Açık hava/ventilasyon (H330/H331)
    'P261': 38,       # Buhar/toz solumaktan kaçın

    # Storage
    'P405': 36,       # Kilitli (H_BASED_LABEL_FORCED ile kritik H'lar için zaten giriyor)
    'P403+P235': 33,  # Serin havalandırmalı
    'P403+P233': 32,
    'P410+P412': 30,

    # Disposal
    'P501': 25,
    'P502': 24,

    # Genel — düşük öncelik (etiket için zorunlu ama)
    'P391': 20,       # Döküntü toplama (aquatic önemli)
    'P264': 15,
    'P270': 14,
    'P233': 10,
}

# Bu P kodları zaten zorunlu — etiket 6'ya dahil edilmez (ayrı yazılır)
# P501: CLP Annex IV'te sınıflandırılmış her ürün için listelenir.
# ECHA kılavuzu: P501 her zaman etikette yer almalı, 6-kod limitine dahil edilmez.
P_LABEL_MANDATORY = ['P101', 'P102', 'P501']



# H kodu bazlı etiket zorunlu P kodları — CLP Annex IV zorunluluğu
# Bu P kodları ilgili H kodu varken her zaman etikete yazılmalı (6 limitinden önce eklenir)
H_BASED_LABEL_FORCED: Dict[str, List[str]] = {
    # Alevlenir sıvı — tutuşma kaynağından uzak tutma ZORUNLU (CLP Annex IV)
    # P210 en kritik önleme kodudur; 6-limit yarışına bırakılmamalı
    'H224': ['P210'],
    'H225': ['P210'],
    'H226': ['P210'],
    # Cilt aşınması — 4 kritik müdahale + KKE kodu zorunlu (CLP Annex IV Tablo 6.3)
    # P260 (solunum koruma) önem sırasında daha düşük → öncelik yarışına bırakıldı
    # Bu sayede H272/H410 gibi ek tehlikeler için etiket kontenjanı açık kalır
    # P310 (zehir danışma hattı) CLP Ek-IV: H314 Cilt Aşın. 1A için zorunlu.
    # H225/H400 ile birleşince forced toplam 7'yi aşabilir — CLP Madde 22(4)
    # gereği 6 limiti aşıldığında tüm forced kodlar korunur (trim kaldırıldı).
    'H314': ['P280', 'P301+P330+P331', 'P303+P361+P353', 'P305+P351+P338', 'P310'],
    # Ağır göz hasarı — KKE zorunlu (H318, H314 ile çakışırsa P280 zaten var)
    'H318': ['P280'],
    # Cilt tahrişi / Cilt duyarlılaştırma — KKE zorunlu (CLP Annex IV)
    # H315 ve H317 için P280 etiket üzerinde açıkça yer almalı
    'H315': ['P280'],
    'H317': ['P280'],
    # Göz tahrişi — P280 zorunlu (H319 için CLP Annex IV)
    'H319': ['P280'],
    # Öldürücü / ağır akut toksisite — kilitli depolama zorunlu (CLP Annex IV)
    'H300': ['P405'],
    'H301': ['P405'],
    'H310': ['P405'],
    'H330': ['P405'],
    # STOT SE 1 / Tehlike — kilitli depolama (kronik maruziyeti önlemek için)
    'H370': ['P405'],
    # Kanserojen / mutajen / üreme toksik — KKE + bilgi alma + kilitli (CLP Annex IV)
    'H340': ['P280', 'P405'],
    'H350': ['P280', 'P405'],
    'H360': ['P280', 'P405'],
    # Oksitleyici sıvı — yanıcılardan uzak tut (CLP Annex III Tablo 3.4.3)
    # H271 (Ox. Liq. 1): P220 (uzak tut) zorunlu
    'H271': ['P220', 'P221'],
    # H272 (Ox. Liq. 2/3): hem P220 hem P221 zorunlu (CLP Annex III)
    # P221 = yanıcılarla karışımı kesinlikle önle
    'H272': ['P220', 'P221'],
    # Aspirasyon toksisitesi — P331 (KUSMayı UYARMAYIN) HAYATI ÖNEM
    # Aspiration Tox. 1 için kusturma kesinlikle yasak — CLP Annex IV zorunlu
    'H304': ['P331'],
    # Solunum duyarlılaştırıcı — P284 (solunum koruyucu) zorunlu (CLP Annex IV)
    'H334': ['P284'],
    # Şüpheli CMR (Kat.2) — P201 (özel talimat al) CLP Annex IV zorunlu
    'H341': ['P201'],
    'H351': ['P201'],
    'H361': ['P201'],
    # STOT Tekrarlanan Maruziyet — P314 (tıbbi yardım) CLP Annex IV
    'H372': ['P314'],
    'H373': ['P314'],
    # Su reaktif — P231+P232 (inert gaz) kritik güvenlik önlemi
    'H260': ['P231+P232'],
    'H261': ['P231+P232'],
    # Sucul çevre tehlikesi — P273 (çevreye bırakma) etikette zorunlu (SEA Tablo 4.1.4)
    # H412/H413 de dahil: CLP Annex IV tüm sucul kategoriler P273 gerektirir
    # P273: çevreye bırakma önlemi — tüm sucul kategoriler zorunlu
    # P391: döküntü toplama — H400/H410/H411 için CLP Ek-IV ek önlem
    'H400': ['P273', 'P391'],
    'H410': ['P273', 'P391'],
    'H411': ['P273', 'P391'],
    'H412': ['P273'],   # SEA Tablo 4.1.4: Sucul Kronik 3 → P273 zorunlu
    'H413': ['P273'],   # SEA Tablo 4.1.4: Sucul Kronik 4 → P273 zorunlu
}

def select_label_p_codes(all_p_codes: List[str], max_codes: int = 6,
                         h_codes: List[str] = None) -> Dict:
    """
    CLP Madde 22 — Etiket için maksimum 6 P kodu seçimi.
    Öncelik ağırlıklarına göre en kritik 6 kodu seç.

    h_codes: H kod listesi — H kodu bazlı zorunlu P kodlarını belirlemeye yarar.
    Returns:
        {
          'selected': [...],      # Seçilen P kodları (zorunlular + öncelik sırası)
          'all': [...],           # Tüm P kodları (SDS için)
          'excluded': [...],      # Etiket dışında kalan
          'note': str             # Seçim gerekçesi
        }
    """
    h_codes = h_codes or []

    # H kodu bazlı zorunlu P kodlarını belirle
    forced_by_h = set()
    for h in h_codes:
        for p in H_BASED_LABEL_FORCED.get(h, []):
            if p in all_p_codes:
                forced_by_h.add(p)

    # CLP Madde 22(4): H kodu bazlı zorunlu P kodları (forced_by_h) HİÇBİR ZAMAN kesilemez.
    # Tehlikenin niteliği gerektiriyorsa 6 limitinin üzeri zorunlu olabilir.
    # Opsiyonel (candidate) kodlar remaining_slots ile zaten sınırlı kalır.
    # sds_validator.py V013 uyarısı 6+ durumunu kullanıcıya bildirir — bu yeterli.
    limit_exceeded = len(forced_by_h) > max_codes  # bilgi amaçlı; trim uygulanmaz

    # P_LABEL_MANDATORY (P101/P102/P501) + forced_by_h → aday listesinden çıkar
    excluded_from_candidates = set(P_LABEL_MANDATORY) | forced_by_h
    candidates = [p for p in all_p_codes if p not in excluded_from_candidates]

    # Kalan slotlar: max_codes eksi forced_by_h sayısı
    remaining_slots = max(0, max_codes - len(forced_by_h))

    # Önceliğe göre sırala
    sorted_codes = sorted(
        candidates,
        key=lambda p: P_LABEL_PRIORITY.get(p, 5),
        reverse=True
    )

    # Aynı türdeki zayıf kodları çıkar
    SUPERSEDE_LABEL = {
        'P301+P310':     ['P301+P312', 'P310', 'P311', 'P312'],
        'P303+P361+P353':['P302+P352', 'P361', 'P353'],
        'P305+P351+P338':['P338', 'P351', 'P337+P313'],  # P305 göz müdahalesini kapsıyor
        'P260':          ['P261'],
        'P333+P313':     ['P332+P313'],
        'P308+P311':     ['P308+P313'],
    }

    selected_set = set(forced_by_h)  # Zorla eklenenlerle başla
    excluded_by_supersede = set()

    for code in sorted_codes:
        if code in excluded_by_supersede:
            continue
        if len(selected_set) - len(forced_by_h) < remaining_slots:
            selected_set.add(code)
            # Bu kodu seçince zayıf olanları çıkar
            for weak in SUPERSEDE_LABEL.get(code, []):
                excluded_by_supersede.add(weak)

    # Tehlike şiddetine göre sırala (yüksek öncelik önce) — CLP Annex IV Not 3
    selected = sorted(
        list(selected_set),
        key=lambda p: P_LABEL_PRIORITY.get(p, 5),
        reverse=True
    )
    excluded = [p for p in candidates if p not in selected_set]

    # Mandatory P kodlarını all_codes'tan belirle (usage bilgisi all_codes'a yansımış)
    # P501: sınıflandırılmış her ürün için zorunlu (ECHA kılavuzu / CLP Annex IV)
    mandatory_in_codes = [p for p in ['P101', 'P102', 'P103', 'P501'] if p in all_p_codes]

    forced_note = (f" (H kodu zorunlu: {', '.join(sorted(forced_by_h))})" if forced_by_h else "")
    exceeded_note = (" Birden fazla tehlike sınıfı nedeniyle öncelikli kodlar seçildi." if limit_exceeded else "")
    note = (
        f"CLP Madde 28(3): Etiket için {len(selected)}/{len(candidates)+len(forced_by_h)} "
        f"P kodu seçildi{forced_note}.{exceeded_note} "
        f"Kalan {len(excluded)} kod SDS Bölüm 2'ye yazılmalıdır."
        if excluded else
        f"Toplam {len(selected)} P kodu — etiket limiti içinde{forced_note}."
    )

    return {
        'selected':       selected,
        'all':            all_p_codes,
        'excluded':       excluded,
        'limit_exceeded': limit_exceeded,
        'mandatory': mandatory_in_codes,
        'forced_by_h': sorted(list(forced_by_h)),
        'note': note,
    }

# ─── SDS P KODU ÖNCELİK SINIFLANDIRMASI ─────────────────────────────────────
# CLP Annex IV Not 3 — üretici/KDU seçim yapabilir
# Üç grup:
#   'mandatory' → Mutlaka yaz (acil müdahale, kritik önlem)
#   'evaluate'  → KDU değerlendirmeli (duruma göre)
#   'optional'  → Opsiyonel (aşikar/genel bilgi)

P_SDS_PRIORITY: Dict[str, str] = {
    # ── MUTLAKA YAZ (Response — acil) ────────────────────────
    'P301+P310':      'mandatory',
    'P301+P330+P331': 'mandatory',
    'P301+P312':      'mandatory',
    'P303+P361+P353': 'mandatory',
    'P335+P334':      'mandatory',   # Pirofor (H250) — partikülleri fırçala, soğut
    'P304+P340':      'mandatory',
    'P304+P341':      'mandatory',
    'P305+P351+P338': 'mandatory',
    'P306+P360':      'mandatory',
    'P308+P311':      'mandatory',
    'P308+P313':      'mandatory',
    'P307+P311':      'mandatory',
    'P310':           'mandatory',
    'P311':           'mandatory',
    'P342+P311':      'mandatory',
    'P331':           'mandatory',   # KUSMAyı UYARMA
    'P370+P378':      'mandatory',   # Yangın
    'P370+P380':      'mandatory',
    'P371+P380+P375': 'mandatory',
    # ── MUTLAKA YAZ (Prevention — kritik) ────────────────────
    'P210':           'mandatory',   # Yanıcı — tutuşma kaynağı
    'P220':           'mandatory',   # Oksitleyici — yanıcılardan uzak tut (CLP Annex III H271/H272)
    'P221':           'mandatory',   # Oksitleyici — yanıcılarla karışımı kesinlikle önle (CLP Annex III)
    'P260':           'mandatory',   # Solunum koruma
    'P273':           'mandatory',   # Çevre — salınım
    'P280':           'mandatory',   # KKE
    'P284':           'mandatory',   # Solunum cihazı
    'P201':           'mandatory',   # CMR — talimat al
    'P202':           'mandatory',   # CMR — oku anla
    'P263':           'mandatory',   # Hamile/emziren
    'P391':           'evaluate',    # Döküntü toplama (aquatic) — KDU değerlendirmeli (Cat.1'de de iyi uygulama)
    'P405':           'mandatory',   # Kilitli sakla
    # ── KDU DEĞERLENDİRMELİ ──────────────────────────────────
    'P271':           'evaluate',    # Açık hava — ortama bağlı
    'P261':           'evaluate',    # Solunum — P260 yoksa
    'P270':           'evaluate',    # Yemek/içmek — iş ortamı
    'P272':           'evaluate',    # Kirli iş kıyafeti
    'P233':           'evaluate',    # Kabı kapalı tut
    'P241':           'evaluate',    # Patlamaya dayanıklı ekipman
    'P242':           'evaluate',    # Kıvılcımsız alet
    'P243':           'evaluate',    # Statik elektrik
    'P240':           'evaluate',    # Topraklama
    'P332+P313':      'evaluate',    # Tahriş → doktor
    'P333+P313':      'evaluate',    # Kızarıklık → doktor
    'P337+P313':      'evaluate',    # Göz tahrişi → doktor
    'P302+P352':      'evaluate',    # Cilt temas → yıka
    'P312':           'evaluate',    # Hissetmiyorsan ara
    'P321':           'evaluate',    # Özel tedavi
    'P330':           'evaluate',    # Ağız çalkala
    'P362':           'evaluate',    # Kirli giysi çıkar
    'P363':           'evaluate',    # Kirli giysi yıka
    'P403+P235':      'evaluate',    # Serin/havalandırmalı
    'P403+P233':      'evaluate',    # Havalandırmalı/kapalı
    'P410+P412':      'evaluate',    # Güneş/sıcaklık
    'P410+P403':      'evaluate',
    'P402+P404':      'evaluate',
    # ── OPSİYONEL ────────────────────────────────────────────
    'P264':           'evaluate',    # El yıkama — aşikar değil, korozif/toksik ürünlerde SEA zorunlu
    'P314':           'optional',    # Hissetmiyorsan — genel
    'P501':           'optional',    # İmha — yasal zorunlu ama aşikar
    'P502':           'optional',    # Geri dönüşüm
    'P235':           'optional',    # Serin tut
    'P411':           'optional',
    'P420':           'optional',
}

P_SDS_LABELS = {
    'mandatory': ('✅ Mutlaka Yaz', 'var(--green)'),
    'evaluate':  ('⚠ KDU Değerlendirmeli', 'var(--warn)'),
    'optional':  ('ℹ Opsiyonel', 'var(--text3)'),
}


def classify_sds_p_codes(p_codes: List[str]) -> Dict:
    """
    P kodlarını SDS'e yazılma önceliğine göre sınıflandır.
    CLP Annex IV Not 3 — üretici/KDU seçim yapabilir.
    Her grup içi sıralama: tehlike şiddetine göre (yüksek önce).
    """
    groups = {'mandatory': [], 'evaluate': [], 'optional': []}

    for code in p_codes:
        priority = P_SDS_PRIORITY.get(code, 'evaluate')  # Bilinmeyenler evaluate
        groups[priority].append(code)

    # Her grup içinde şiddet sırası — P_LABEL_PRIORITY kullan
    for grp in groups:
        groups[grp].sort(key=lambda p: P_LABEL_PRIORITY.get(p, 5), reverse=True)

    total_mandatory = len(groups['mandatory'])
    total_evaluate = len(groups['evaluate'])
    total_optional = len(groups['optional'])

    return {
        'groups': groups,
        'total': len(p_codes),
        'mandatory_count': total_mandatory,
        'evaluate_count': total_evaluate,
        'optional_count': total_optional,
        'note': (
            f"SDS Bölüm 2: {total_mandatory} zorunlu · "
            f"{total_evaluate} KDU değerlendirmeli · "
            f"{total_optional} opsiyonel"
        )
    }
