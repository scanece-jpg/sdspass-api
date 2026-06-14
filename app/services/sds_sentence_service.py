"""
SDS Otomatik Cümle Servisi
===========================
KKDİK Ek-2 — SDS Bölüm 1-16 için otomatik metin üretimi

Bölüm 3: Konsantrasyon gizleme (ECHA aralıkları)
Bölüm 4-8: H kodu → otomatik cümle veritabanı
Bölüm 11-12: CLP/Ekoloji sonuçlarından metin
Bölüm 14: ADR/IMDG/IATA UN numarası veritabanı

Gizleme Seviyeleri (Bölüm 3):
  'show'   → Tam konsantrasyon göster (%20.0)
  'range'  → ECHA aralığı ver (10-<25%)
  'hide'   → CAS gizle, kimyasal grup adı + aralık

Kaynak: CLP Madde 24(2), REACH Madde 119, KKDİK Madde 15
"""

from typing import List, Dict, Optional, Any
from app.services.codes_i18n import correct_hclass


# ─── BÖLÜM 3: ECHA KONSANTRASYON ARALIĞI ─────────────────────────────────────

# ECHA SDS Kılavuzu Rev.4 (2022) Tablo 3.1 — Madde 3.2 CLP Annex I 1.1.3
# Ticari sır durumunda kesin konsantrasyon yerine kullanılır.
# Semboller: ≥ (büyük eşit), < (küçük)
ECHA_RANGES = [
    (25.0, 100.01, '≥ 25%'),
    (10.0,  25.0,  '≥ 10 - < 25%'),
    ( 5.0,  10.0,  '≥ 5 - < 10%'),
    ( 2.5,   5.0,  '≥ 2,5 - < 5%'),
    ( 1.0,   2.5,  '≥ 1 - < 2,5%'),
    ( 0.1,   1.0,  '≥ 0,1 - < 1%'),
    ( 0.0,   0.1,  '< 0,1%'),
]

# Kimyasal grup adları (CAS gizlendiğinde kullanılır)
CHEM_GROUP_NAMES: Dict[str, str] = {
    'aromatic':      'Aromatik Hidrokarbon',
    'aliphatic':     'Alifatik Hidrokarbon',
    'ketone':        'Keton',
    'ester':         'Ester',
    'alcohol':       'Alkol',
    'glycol':        'Glikol Eter',
    'acid':          'Organik Asit',
    'base':          'İnorganik Baz',
    'inorganic_acid':'İnorganik Asit',
    'surfactant':    'Yüzey Aktif Madde',
    'biocide':       'Biyosit',
    'pigment':       'Pigment / Dolgu',
    'solvent':       'Organik Çözücü',
    'water':         'Su',
    'unknown':       'Kimyasal Madde',
}

# CAS → kimyasal grup (yaygın maddeler)
CAS_TO_GROUP: Dict[str, str] = {
    '71-43-2':   'aromatic',   # benzene
    '108-88-3':  'aromatic',   # toluene
    '1330-20-7': 'aromatic',   # xylene
    '100-41-4':  'aromatic',   # ethylbenzene
    '95-63-6':   'aromatic',   # TMB
    '110-54-3':  'aliphatic',  # n-hexane
    '110-82-7':  'aliphatic',  # cyclohexane
    '142-82-5':  'aliphatic',  # n-heptane
    '67-64-1':   'ketone',     # acetone
    '78-93-3':   'ketone',     # MEK
    '108-10-1':  'ketone',     # MIBK
    '141-78-6':  'ester',      # ethyl acetate
    '123-86-4':  'ester',      # n-butyl acetate
    '64-17-5':   'alcohol',    # ethanol
    '67-63-0':   'alcohol',    # IPA
    '71-36-3':   'alcohol',    # n-butanol
    '111-76-2':  'glycol',     # 2-butoxyethanol
    '107-98-2':  'glycol',     # PGME
    '7732-18-5': 'water',      # water
    '7664-93-9': 'inorganic_acid',  # H2SO4
    '7697-37-2': 'inorganic_acid',  # nitric acid
    '7647-01-0': 'inorganic_acid',  # HCl
    '1310-73-2': 'base',       # NaOH
    '1310-58-3': 'base',       # KOH
}


def get_echa_range(concentration: float) -> str:
    """
    Konsantrasyonu ECHA SDS Kılavuzu (Rev.4, 2022) aralığına çevir.
    CLP Annex I Bölüm 1.1.3 — Ticari sır / konsantrasyon gizleme.
    """
    if concentration >= 100:
        return '100%'
    for lo, hi, label in ECHA_RANGES:
        if lo <= concentration < hi:
            return label
    return f'%{concentration:.1f}'


# Akut toksisite maruziyet yolları — CLP Tablo 3.1.1 (oral / dermal / inhal)
_ACUTE_TOX_ROUTE: Dict[str, str] = {}
for _c in ('H300', 'H301', 'H302', 'H303'):
    _ACUTE_TOX_ROUTE[_c] = '(oral)'
for _c in ('H310', 'H311', 'H312', 'H313'):
    _ACUTE_TOX_ROUTE[_c] = '(dermal)'
for _c in ('H330', 'H331', 'H332', 'H333'):
    _ACUTE_TOX_ROUTE[_c] = '(inhal.)'


def format_section3_component(
    comp: Dict,
    disclosure_level: str = 'show',  # 'show' | 'range' | 'hide'
    lang: str = 'TR',
) -> Dict:
    """
    Bölüm 3 bileşen satırı formatla.

    Returns:
        {
          'cas': str,           # CAS no veya 'Gizli'
          'name': str,          # İsim veya kimyasal grup
          'concentration': str, # '%20.0' veya '10-<25%' veya '10-<25%'
          'hazards': str,       # 'Flam. Liq. 3; STOT RE 2'
          'is_hidden': bool,
          'note': str,          # Gizleme notu
        }
    """
    import re as _re
    cas = comp.get('cas_no', comp.get('cas', '')).strip()
    # Türkçe SDS → name_tr öncelikli, yoksa name
    if lang == 'TR':
        name = comp.get('name_tr', '') or comp.get('name', '') or cas
    else:
        name = comp.get('name', '') or cas
    # CLP Ek-VI notasyonu temizliği: "sülfürik asit ... %" → "sülfürik asit"
    # (Bazı maddelerde konsantrasyon-bağımlı sınıflandırma için "... %" eklenir)
    name = _re.sub(r'\s*[ \s]*\.\.\.[ \s]*%\s*$', '', name).strip()
    # Bileşen tipi notasyonu (Polimer / UVCB / Esans) — B3.2 adı sütununa eklenir
    comp_type = comp.get('comp_type', 'normal')
    _TYPE_LABELS = {
        'polymer':   '(Polimer)',
        'uvcb':      '(UVCB)',
        'fragrance': '(Tedar. Kar.)',
    }
    if comp_type in _TYPE_LABELS:
        name = f"{name} {_TYPE_LABELS[comp_type]}"
    conc = float(comp.get('worst_case_conc', comp.get('conc', comp.get('concentration', 0))) or 0)
    hazards = comp.get('hazards', [])
    # Tekrar eden h_class değerleri gider; h_code'dan yetkili h_class türet (DB bozukluğuna karşı)
    # Akut toksisite kodları (H300-H333) için maruziyet yolu (oral/dermal/inhal.) de eklenir.
    _seen_cls = set()
    _haz_parts = []
    _has_annex_supplement = False
    for h in hazards:
        raw_cls  = h.get('h_class', '').replace('*', '').strip()
        raw_code = h.get('h_code', '').replace('*', '').strip()
        code4    = raw_code[:4] if len(raw_code) >= 4 else raw_code
        cls = correct_hclass(raw_code, raw_cls) or raw_cls  # düzelt; düzeltemezse orijinali kullan
        # Akut toksisite için yol son eki ekle — CLP SDS Kılavuzu Rev.4 §3.2
        route = _ACUTE_TOX_ROUTE.get(code4, '')
        cls_key = f'{cls} {route}'.strip() if route else cls  # dedup anahtarı
        if cls_key and cls_key not in _seen_cls:
            _seen_cls.add(cls_key)
            # H-kodunu sınıf adının yanına ekle — KKDİK Ek-2 B3.2 / CLP Annex II §3.2
            h_code_sfx = f' {raw_code}' if raw_code else ''
            if h.get('_annex_supplement'):
                _haz_parts.append(f'{cls_key}{h_code_sfx}†')
                _has_annex_supplement = True
            else:
                _haz_parts.append(f'{cls_key}{h_code_sfx}')
    haz_str = '; '.join(_haz_parts)
    if _has_annex_supplement:
        haz_str += '  († CLP Ek VI tamamlayıcı sınıflandırma)'

    # Kullanıcının girdiği orijinal konsantrasyon metni (ör: "25-50")
    conc_str = comp.get('conc_str', '').strip()
    conc_min = comp.get('conc_min')
    conc_max = comp.get('conc_max')
    if conc_str:
        # Tire ile ayrılmış aralık girilmişse (ör: "1-3" ya da "1–3") → standart formata çevir
        import re as _rc
        _m = _rc.match(r'^(\d[\d,.]*)[\-–](\d[\d,.]*)$', conc_str)
        if _m:
            _lo, _hi = _m.group(1).replace(',', '.'), _m.group(2).replace(',', '.')
            conc_display = f'%{_lo}–<%{_hi}'
        else:
            conc_display = f'%{conc_str}'
    elif conc_min is not None and conc_max is not None and conc_min != conc_max:
        # CLP Annex I §3 notasyonu: üst sınır önünde '<' zorunlu — örn. %1–<%5
        conc_display = f'%{conc_min}–<%{conc_max}'
    else:
        # Seçenek B: girilen tam değer worst-case, B3'te ≥%X formatı (CLP Annex II §3.2.3.1)
        conc_display = f'≥%{conc:g}'

    if disclosure_level == 'show':
        return {
            'cas': cas, 'name': name,
            'concentration': conc_display,
            'hazards': haz_str, 'is_hidden': False, 'note': '',
        }

    elif disclosure_level == 'range':
        return {
            'cas': cas, 'name': name,
            'concentration': get_echa_range(conc),
            'hazards': haz_str, 'is_hidden': False,
            'note': 'Konsantrasyon ticari sır — ECHA aralığı verilmiştir (CLP Madde 24(2))',
        }

    else:  # hide
        group = CAS_TO_GROUP.get(cas, 'unknown')
        group_name = CHEM_GROUP_NAMES.get(group, 'Kimyasal Madde')
        return {
            'cas': 'Gizli*', 'name': group_name,
            'concentration': get_echa_range(conc),
            'hazards': haz_str, 'is_hidden': True,
            'note': '* CAS numarası gizlidir — ÇSGB bildirimi yapılmıştır (KKDİK Madde 15)',
        }


# ─── BÖLÜM 4-8 OTOMATIK CÜMLE VERİTABANI ────────────────────────────────────

# Format: H_KODU → {bölüm_no: cümle}
# Bölümler: 4=İlk yardım, 5=Yangın, 6=Kaza, 7=Depolama, 8=KKE
H_SENTENCES: Dict[str, Dict[int, str]] = {

    # ── YANICILIK ──────────────────────────────────────────────────────────
    'H224': {
        4: 'Buhar solunursa kişiyi derhal temiz havaya çıkarın. Solunumu yoksa suni solunum uygulayın.',
        5: 'Son derece yanıcı sıvı ve buhar. Kuru kimyasal toz, CO₂ veya alkolle uyumlu köpük kullanın. Su spreyi ile söndürülebilir ancak su jeti kullanmayın.',
        6: 'Tüm tutuşma kaynaklarını derhal ortadan kaldırın. Dökülmüş maddenin kanalizasyon veya su kaynaklarına ulaşmasını önleyin. Kuru kum veya inert absorban malzemeyle toplayın.',
        7: 'Ekipman ve alıcı kabı topraklayın/bağlayın (P240). Kıvılcım çıkarmayan aletler kullanın (P242). '
           'Statik elektrik oluşumunu kesinlikle önleyin (P243). Yalnızca iyi havalandırılan alanlarda kullanın. '
           'Buhar ve sis solumaktan kaçının; sprey oluşturmayın. Isı, kıvılcım ve açık alevden uzak tutun.',
        72: 'Serin (≤20°C), kuru ve iyi havalandırılan yerde orijinal kabında saklayın. '
            'Isı, kıvılcım ve açık alevden uzakta, güçlü oksitleyicilerden ayrı depolayın. Kabı sıkıca kapalı tutun.',
    },
    'H225': {
        4: 'Buhar solunursa kişiyi temiz havaya çıkarın. Ciltle temas halinde bol su ile yıkayın.',
        5: 'Yanıcı sıvı ve buhar. Kuru kimyasal, CO₂ veya köpükle söndürün. Büyük yangınlarda su sisi kullanılabilir.',
        6: 'Tutuşma kaynaklarını ortadan kaldırın. Döküntüyü absorban malzeme ile toplayın. Buhar birikimini önlemek için havalandırın.',
        7: 'Ekipman ve alıcı kabı topraklayın/bağlayın (P240). Kıvılcım çıkarmayan aletler kullanın (P242). '
           'Statik elektrik oluşumunu önleyin (P243). İyi havalandırılan alanlarda kullanın. '
           'Tutuşma kaynaklarından (kıvılcım, alev, sıcak yüzey) uzak tutun; sigara içmeyin.',
        72: 'Serin (≤25°C), iyi havalandırılan yerde, orijinal kabında saklayın. '
            'Isı, kıvılcım ve açık alevden uzakta, güçlü oksitleyicilerden ayrı depolayın. Kabı sıkıca kapalı tutun.',
    },
    'H226': {
        4: 'SOLUNMA: Kişiyi temiz havaya çıkarın. Nefes almakta güçlük çekiyorsa oksijen verin. '
           'CİLT: Kirlenmiş giysileri çıkarın, bol su ve sabunla yıkayın. '
           'GÖZ: En az 15 dakika bol suyla yıkayın. Tahriş devam ederse doktora başvurun.',
        5: 'Söndürme maddesi: Kuru kimyasal toz, CO₂ veya alkole dayanıklı köpük. '
           'Yangını kesinlikle su ile söndürmeyin (yayılmaya neden olabilir). '
           'Özel tehlike: Yanma sırasında CO₂ ve CO oluşur. Isınan konteynerler patlayabilir.',
        6: 'Tüm tutuşturma kaynaklarını ortadan kaldırın. Yeterli havalandırma sağlayın. '
           'Kuru absorban malzeme (kum, vermikülit) ile toplayın. '
           'Döküntünün kanalizasyon ve su kaynaklarına ulaşmasını önleyin.',
        7: 'Kullanım sırasında statik elektriğe karşı topraklama yapın (P240). '
           'Kıvılcım çıkarmayan aletler kullanın (P242). Statik elektrik oluşumunu önleyin (P243). '
           'İyi havalandırın; buhar ve sis oluşumundan kaçının. Tutuşma kaynaklarından uzak tutun.',
        72: 'Serin (≤25°C), iyi havalandırılmış yerde, orijinal kabında saklayın. '
            'Isı, kıvılcım ve açık alevden uzak tutun. Güçlü oksitleyicilerden ayrı saklayın.',
    },

    # ── CİLT / GÖZ ────────────────────────────────────────────────────────
    'H314': {
        4: [
            'CİLDE TEMAS: Kirlenmiş giysileri hemen çıkarın. Cildi en az 15-20 dakika bol suyla yıkayın. Derhal tıbbi yardım alın.',
            'GÖZLE TEMAS: Kontak lens varsa hemen çıkarın. Gözü açık tutarak en az 15-20 dakika bol akan suyla yıkayın. Derhal tıbbi yardım alın.',
        ],
        5: 'Korozif madde. Yangın söndürücü olarak CO₂, kuru kimyasal veya su sisi kullanın. Su jeti kullanmayın.',
        6: 'KKE giymeden yaklaşmayın. Asit/baz nötralizasyonu yapmayın. Döküntüyü kuru absorban malzeme ile toplayın.',
        7: 'Kullanmadan önce tam KKE (eldiven, gözlük, yüz siperi) giyin. '
           'Göz yıkama istasyonunun erişilebilir ve çalışır durumda olduğunu kontrol edin. '
           'Nötralizasyon maddesi (kireç veya sodyum karbonat) yakında hazır bulundurun. '
           'Buhar/aerosol oluşumundan kaçının; yetersiz havalandırmada solunum koruyucu kullanın.',
        72: 'Korozif metallere ve aside/baza duyarlı malzemelere zarar verir. '
            'Ayrı, iyi havalandırılan, serin yerde sızdırmaz kapta saklayın.',
        8: 'Yüz siperi, kimyasala dayanıklı eldiven (nitril veya neopren ≥0.5mm), koruyucu giysi ve çizme. Göz yıkama istasyonu bulundurulmalıdır.',
    },
    'H315': {
        4: 'Ciltle temastan sonra bol su ve sabunla yıkayın. Tahriş devam ederse tıbbi yardım alın.',
        5: 'Su spreyi kullanın. Kuru kimyasal veya CO₂ de uygulanabilir.',
        6: 'Kirlenmiş alanı havalandırın. KKE kullanın. Absorban malzeme ile toplayın.',
        7: 'Cilt temasından kaçının; koruyucu eldiven ve giysi kullanın. '
           'Kullanım sonrası maruz kalan bölgeleri bol su ve sabunla yıkayın.',
        72: 'Serin, kuru yerde saklayın. Gıda maddelerinden uzak tutun.',
        8: 'Nitril veya lateks eldiven kullanın.',
    },
    'H317': {
        4: 'Deri duyarlılaştırıcı. Temas halinde bol su ve sabunla yıkayın. Kızarıklık veya döküntü olursa tıbbi yardım alın.',
        6: 'Cilt temasından kaçının. Uygun KKE giyin. Absorban malzeme ile toplayın.',
        7: 'Deri duyarlılaştırıcı — cilt temasından kesinlikle kaçının; uygun eldiven zorunludur. '
           'Daha önce bu maddeye duyarlılaşmış kişiler çalışmamalıdır.',
        72: 'Serin, kuru yerde orijinal ambalajında saklayın.',
        8: 'Kimyasala dayanıklı eldiven kullanın. Daha önce duyarlılaşmış kişiler bu ürünle çalışmamalıdır.',
    },
    'H318': {
        4: 'GÖZLE TEMAS: Kontakt lensleri çıkarın. En az 15-20 dakika bol suyla yıkayın. Derhal göz doktoruna gidin.',
        8: 'Kimyasal gözlük veya yüz siperi zorunludur.',
    },
    'H319': {
        4: 'Gözle temas halinde birkaç dakika suyla yıkayın. Tahriş devam ederse tıbbi yardım alın.',
        8: 'Göz koruyucu kullanın.',
    },

    # ── AKüT TOKSİSİTE ────────────────────────────────────────────────────
    'H300': {
        4: 'YUTULURSA: Derhal Zehir Merkezi (0800 314 6120) veya doktoru arayın. Kusturmayın.',
        8: 'Tam yüz maskesi veya solunum koruyucu, kimyasala dayanıklı eldiven ve giysi.',
    },
    'H301': {
        4: 'YUTULURSA: Derhal Zehir Merkezi (0800 314 6120) veya acile gidin. Kusturmayın.',
        8: 'Kimyasala dayanıklı eldiven, gözlük.',
    },
    'H302': {
        4: 'YUTULURSA: Ağzı çalkalayın. Kusturmayın. Tıbbi yardım alın.',
    },
    'H310': {
        4: [
            'CİLDE TEMAS: Acil servis arayın. Kirlenmiş giysileri çıkarın. Cildi bol su ile yıkayın.',
            'GÖZLE TEMAS: Kontak lens varsa çıkarın. En az 15 dakika bol suyla yıkayın. Derhal tıbbi yardım alın.',
        ],
        8: 'Tam beden kimyasal koruyucu giysi, eldiven ve yüz koruyucu.',
    },
    'H311': {
        4: 'Ciltle temas halinde kirlenmiş giysileri çıkarın, bol suyla yıkayın. Tıbbi yardım alın.',
        8: 'Kimyasala dayanıklı eldiven ve giysi.',
    },
    'H330': {
        4: 'SOLUNURSA: Derhal temiz havaya çıkarın. Solunumu yoksa suni solunum. Derhal acile gidin.',
        6: 'Buhar solunmasından kaçının. Uygun solunum koruması olmadan dökülme bölgesine girmeyin.',
        7: 'Kapalı sistem veya iyi havalandırılan alanda kullanın.',
        8: 'Kimyasal madde için uygun solunum koruyucu (ABEK filtre veya SCBA).',
    },
    'H331': {
        4: 'Solunursa temiz havaya çıkarın. Belirtiler devam ederse tıbbi yardım alın.',
        7: 'Yalnızca iyi havalandırılan alanlarda veya kapalı sistemde kullanın. '
           'Buhar/sis oluşumundan kaçının; OEL aşılma riskinde solunum koruyucu takın.',
        72: 'İyi havalandırılan, serin yerde sıkıca kapalı kapta saklayın.',
        8: 'Organik gaz filtreli solunum maskesi veya SCBA.',
    },

    # ── STOT ──────────────────────────────────────────────────────────────
    'H370': {
        4: 'Organ hasarına neden olabilir. Maruz kalındığında veya kendinizi iyi hissetmediğinizde derhal tıbbi yardım alın.',
        8: 'Solunum koruması, deri ve göz koruması gereklidir.',
    },
    'H371': {
        4: 'Organ hasarına yol açabilir. Semptom durumunda tıbbi yardım alın.',
        8: 'Uygun KKE kullanın.',
    },
    'H372': {
        4: 'Uzun süreli veya tekrarlanan maruziyet halinde organ hasarına neden olur. Periyodik sağlık kontrolü yapılmalıdır.',
        7: 'Maruziyet sınırını (OEL/DNEL) aşmamak için uygun KKE ve havalandırma sağlayın. '
           'Periyodik biyolojik izleme programına dahil olun; çalışırken yemeyin/içmeyin.',
        72: 'Yetkisiz kişilerin erişimini önleyin. Kilitli yerde saklayın.',
        8: 'Maruziyet sınırı aşılma riski varsa solunum koruyucu kullanın.',
    },
    'H373': {
        4: 'Uzun süreli maruziyet organ hasarına yol açabilir. Periyodik kontrol önerilir.',
        8: 'Sürekli maruziyetten kaçının.',
    },

    # ── ASPİRASYON TOKSİSİTESİ ────────────────────────────────────────────
    'H304': {
        4: 'YUTULURSA VE SOLUK BORUSUNA KAÇARSA: Hayati tehlike yaratabilir. KESİNLİKLE KUSTURMAYINIZ. Derhal acile gidin.',
        5: 'Su ile söndürmeyiniz (yanıcı sıvının yayılmasına yol açabilir). CO₂ veya kuru toz kullanın.',
    },

    # ── MUTAJENEZ / KARSİNOJENEZ / ÜREME ─────────────────────────────────
    'H340': {
        4: 'Mutajenik madde. Maruz kalındığında tıbbi yardım alın. Periyodik biyolojik izleme yapılmalıdır.',
        8: 'Deri ve solunum temasından kesinlikle kaçının.',
    },
    'H350': {
        4: 'Kanserojen. Maruziyet sonrası tıbbi değerlendirme yapılmalıdır.',
        8: 'Maruziyet sınırı ne olursa olsun en düşük düzeyde tutulmalıdır (ALARA ilkesi).',
    },
    'H360': {
        4: 'Üreme sistemine zarar verir. Hamile veya emziren kadınlar bu maddeyle çalışmamalıdır.',
        8: 'Sıkı maruziyet kontrolü zorunludur. Üreme çağındaki kişiler özel dikkat göstermelidir.',
    },

    # ── AQUATIC / ÇEVRE ────────────────────────────────────────────────────
    'H400': {
        6: 'Su ortamına karışmasını kesinlikle önleyin. Döküntüyü hemen absorban malzeme ile toplayın. Çevre müdahale ekibini haberdar edin.',
        7: 'Taşıma ve dolum sırasında ikincil güvenlik kabı (driptrays) kullanın. '
           'Su ortamına dökülmesini önleyin; huni/pompa kullanırken taşmaya dikkat edin.',
        72: 'Su kaynaklarından, kanalizasyondan ve zemin suyundan uzak, sızdırmaz kapta saklayın.',
    },
    'H410': {
        6: 'Döküntünün kanalizasyon, dere veya göle ulaşmasını önleyin. Yetkili makamları (ÇSGB/Çevre Bakanlığı) bilgilendirin.',
        7: 'Taşıma ve dolum sırasında ikincil güvenlik kabı kullanın. '
           'Su ortamına dökülmesini kesinlikle önleyin.',
        72: 'Sızdırmaz kapta, su kaynaklarından uzakta saklayın.',
    },
    'H411': {
        4: 'Su ile temasa geçmesini önleyin. Deri veya gözle temas halinde suyla yıkayın. '
           'Tıbbi semptom halinde doktora başvurun. Ürünü çevreye dökmeyiniz.',
        5: 'Yangın söndürme suyunun çevreye yayılmasını önleyin. '
           'Su kaynaklarına, kanalizasyona karışmasını engelleyin.',
        6: 'ÇEVRESEL TEHLİKE: Döküntünün su kaynaklarına ve kanalizasyona ulaşmasını kesinlikle önleyin. '
           'Gerekirse yerel çevre müdahale ekibini haberdar edin.',
        7: 'Döküntüyü önlemek için ikincil güvenlik kabı kullanın. '
           'Su, kanalizasyon veya drenaj hatlarına yakın alanda kullanmaktan kaçının.',
        72: 'Çevre açısından tehlikeli ürün. Kanalizasyona veya açık suya dökmeyin. '
            'Sıkıca kapalı, çevreyle uyumlu kapta saklayın.',
    },
    'H412': {
        6: 'Döküntünün su kanallarına ulaşmasını önleyin.',
    },

    # ── OKSİTLEYİCİ ───────────────────────────────────────────────────────
    'H271': {
        4: 'Yangın veya patlama riski. Derhal acil servisleri arayın. Bölgeyi tahliye edin.',
        5: 'Su kullanmayın. CO₂ veya kum kullanın. Yangın söndürücüleri yakıt ile temastan koruyun.',
        6: 'Bölgeyi tahliye edin. Tüm tutuşma kaynaklarını ortadan kaldırın. Uzmanlaşmış ekip olmadan müdahale etmeyin.',
        7: 'Yanıcı, organik ve indirgen maddelerle kesinlikle temas ettirmeyin. '
           'Uygun KKE (aleve dayanıklı giysi, yüz siperi) giyin. Kontaminasyonu önleyin.',
        72: 'Yanıcı ve organik maddelerden uzakta, serin ve kuru yerde ayrı saklayın.',
    },
    'H272': {
        5: 'Yangını besleyebilir. Isı ve tutuşma kaynaklarından uzak tutun.',
        6: 'Yanıcı maddelerle temasını önleyin.',
        7: 'Yanıcı maddelerle temasından kaçının; oksitleyici — yangını şiddetlendirebilir. '
           'Kontaminasyonu önlemek için temiz ekipman kullanın.',
        72: 'Yanıcı maddelerden ayrı, serin ve kuru yerde saklayın.',
    },

    'H228': {
        4: 'Temas eden giysileri çıkarın. Yanık bölgeyi soğuk suyla yıkayın.',
        5: 'Kuru kimyasal toz veya kum kullanın. Su yayılmayı artırabilir.',
        6: 'Tutuşturma kaynaklarını kaldırın. Tozu süpürmeden ıslak bezle toplayın.',
        7: 'Toz oluşumundan kaçının; antistatik ekipman kullanın. '
           'Tutuşma ve kıvılcım kaynaklarından uzak ortamda çalışın.',
        72: 'Serin, kuru yerde ısı ve kıvılcımdan uzakta saklayın.',
        8: 'Antistatik giysi, eldiven ve göz koruyucu kullanın.',
    },
    'H229': {
        4: 'Gözle temas halinde bol suyla yıkayın. Tahriş devam ederse doktora gidin.',
        5: 'Aerosol kaplara ısı uygulamayın. CO₂ veya kuru kimyasal kullanın.',
        6: 'Tutuşturma kaynaklarını kaldırın. İyi havalandırma sağlayın.',
        7: 'Basınçlı kap — delmeyin ve ısı kaynağına tutmayın. '
           'Açık alev ve kıvılcımdan uzak tutun.',
        72: '50°C üzerinde ısıya maruz bırakmayın. Güneş ışığından koruyun.',
        8: 'Göz koruyucu ve eldiven kullanın.',
    },
    'H240': {
        4: 'Isı veya darbeden kaynaklanan yaralanmalar için doktora başvurun.',
        5: 'PATLAMA RİSKİ. Uzaktan müdahale edin. Su spreyi.',
        6: 'PATLAMA RİSKİ. Bölgeden uzaklaşın. Uzman ekip çağırın.',
        7: 'Darbe, sürtünme ve ısıdan kesinlikle koruyun. '
           'Yalnızca uygun ekipmanla ve eğitimli personel tarafından kullanılmalıdır.',
        72: 'Serin yerde saklayın. Isı, darbe ve sürtünmeden kesinlikle koruyun.',
        8: 'Tam koruyucu ekipman, yüz siperi ve alev geciktirici giysi.',
    },
    'H241': {
        4: 'Yanık veya patlama yaralanması için acil tıbbi yardım alın.',
        5: 'Yangın veya patlama riski. Su spreyi veya CO₂ kullanın.',
        6: 'Tutuşturma kaynaklarını uzaklaştırın. İhtiyatla yaklaşın.',
        7: 'Isı kaynaklarından ve tutuşma noktalarından uzak tutun. '
           'Kontrollü koşullarda, eğitimli personelle kullanın.',
        72: 'Serin yerde, ısı kaynaklarından uzakta saklayın.',
        8: 'Alev geciktirici giysi ve yüz koruyucu kullanın.',
    },
    'H250': {
        4: 'Yanıklar için soğuk su uygulayın. Acil tıbbi yardım alın.',
        5: 'Havadan izole edin. Kuru kum veya inert gaz kullanın.',
        6: 'Hava ile temasından kesinlikle kaçının. Uzman ekip çağırın.',
        7: 'İnert gaz atmosferinde çalışın; hava ile temasını kesinlikle önleyin. '
           'Kuru ekipman kullanın.',
        72: 'İnert atmosfer altında hava geçirmez kapta saklayın.',
        8: 'Tam yüz siperi, alev geciktirici giysi ve kuru eldiven.',
    },
    'H251': {
        4: 'Isıya bağlı yanık veya yangın sonrası tıbbi yardım alın.',
        5: 'Büyük miktarlarda yangın riski. CO₂ veya kuru toz kullanın.',
        6: 'Küçük miktarlarda toplayın. Isı kaynaklarından uzak tutun.',
        7: 'Büyük miktarlarda kendiliğinden ısınabilir; yığın halinde depolamamak koşuluyla kullanın.',
        72: 'Serin yerde, 35°C altında saklayın.',
    },
    'H252': {
        4: 'Ciltle temas halinde bol soğuk suyla yıkayın. Doktora gidin.',
        5: 'Büyük miktarlarda yangın riski. Su veya CO₂ kullanın.',
        6: 'Serin tutun. Sıcak yüzeylerden uzaklaştırın.',
        7: 'Küçük miktarlarda kullanın; büyük yığınlardan kaçının. İyi havalandırın.',
        72: 'Küçük miktarlarda, serin ve iyi havalandırılmış yerde saklayın.',
        8: 'Isıya dayanıklı eldiven, yüz siperi.',
    },
    'H260': {
        4: 'SU KULLANMAYIN. Kuru kum veya D tipi yangın söndürücü. Acil tıbbi yardım.',
        5: 'SU KULLANMAYIN — patlama tehlikesi. Kuru kum veya D tipi söndürücü.',
        6: 'Su ile temasından kesinlikle kaçının. Kuru absorban kullanın.',
        7: 'Su, nem ve yağmurdan kesinlikle uzak tutun. Kuru ekipman kullanın; '
           'ıslak zemin veya nemli ortamda çalışmayın.',
        72: 'Tamamen kuru yerde, nem ve yağmurdan korunarak inert atmosferde saklayın.',
        8: 'Su geçirmez eldiven, yüz siperi, alev geciktirici giysi.',
    },
    'H261': {
        4: 'Nemli cilt veya gözle temas halinde kuru bezle silin. Doktora gidin.',
        5: 'SU KULLANMAYIN. Kuru kimyasal veya kum kullanın.',
        6: 'Su ile temasından kaçının. Kuru absorban ile toplayın.',
        7: 'Nem ve su kaynaklarından uzak ortamda kullanın. Kuru ekipman kullanın.',
        72: 'Kuru yerde nem ve su kaynaklarından uzakta saklayın.',
        8: 'Su geçirmez eldiven ve yüz koruyucu.',
    },
    'H280': {
        4: 'Donma yaralanması için ilık su uygulayın (en fazla 40°C). Ovmayın.',
        5: 'Isınan konteyner patlayabilir. Suyla soğutun. Alevden uzaklaştırın.',
        6: 'Sızdıran konteyneri dışarı çıkarın. İyi havalandırma sağlayın.',
        7: 'Tüp/kabı darbeden koruyun; uygun basınç regülatörü kullanın. '
           'Aşırı ısı kaynaklarından uzak tutun.',
        72: '50°C altında, havalandırılmış depoda dik pozisyonda saklayın.',
        8: 'Kişisel koruyucu ekipman ve uygun basınç regülatörü kullanın.',
    },
    'H281': {
        4: 'KRİYOJENİK YANMA: Etkilenen bölgeyi ilık suyla yıkayın. Hemen doktora gidin.',
        5: 'Soğutulmuş gaz — uzaklaşın. Isıyla birlikte patlama riski.',
        6: 'Sızdırma halinde bölgeyi tahliye edin. Uzman ekip çağırın.',
        7: 'Kriyojenik sıcaklıklarda çalışın; cilt ve göz temasını önleyin. '
           'Onaylı kriyojenik ekipman kullanın.',
        72: 'Onaylı kriyojenik kapta, ısı kaynaklarından uzakta saklayın.',
        8: 'Kriyojenik eldiven, yüz siperi ve tam koruyucu giysi.',
    },
    'H290': {
        4: 'Metalik temas bölgesini bol suyla yıkayın. Tahriş devam ederse doktora gidin.',
        5: 'Standart yangın söndürücü kullanın. Metal ekipmanlara dikkat.',
        6: 'Metal zemin ve ekipmanlardan uzak tutun. Absorban ile toplayın.',
        7: 'Metal kap, alet ve ekipmanlarla temas ettirmeyin; '
           'plastik veya cam kaplarda ve korozyona dayanıklı ekipmanla kullanın.',
        72: 'Metal olmayan veya kaplanmış, korozyona dayanıklı kapta saklayın.',
        8: 'Korozyona dayanıklı eldiven ve ekipman kullanın.',
    },
    'H303': {
        4: 'YUTULMA: Ağzı çalkalayın. Kusturmayın. İyi hissetmiyorsanız doktora gidin.',
        5: 'Uygun söndürücü kullanın.',
        6: 'KKE ile toplayın. Yiyeceklerden uzak tutun.',
        7: 'Çalışırken yemeyin, içmeyin ve sigara içmeyin. '
           'Kullanım sonrası elleri yıkayın.',
        72: 'Gıdadan ayrı, kilitli yerde saklayın.',
        8: 'Eldiven ve göz koruyucu kullanın.',
    },
    'H305': {
        4: 'YUTULMA ve SOLUNUM YOLU: Kusturmayın. Derhal doktora gidin.',
        5: 'Uygun söndürücü kullanın.',
        6: 'Solvent gazlarının birikmesini önleyin. İyi havalandırma.',
        7: 'Aspirasyon riski — yutmaktan kesinlikle kaçının. '
           'Solvent buharlarını solumaktan kaçının; iyi havalandırma sağlayın.',
        72: 'Serin, kuru yerde gıdadan ayrı, orijinal kabında saklayın.',
        8: 'Eldiven, göz koruyucu ve solunum maskesi.',
    },
    'H312': {
        4: 'CİLT: Kirlenmiş giysileri çıkarın. Bol su ve sabunla yıkayın. Doktora gidin.',
        5: 'Uygun söndürücü kullanın.',
        6: 'Cilt temasından kaçının. Uygun KKE giyin.',
        7: 'Cilt temasından kaçının; koruyucu eldiven ve giysi kullanın. '
           'Çalışırken yemeyin ve içmeyin.',
        72: 'Serin, kuru yerde gıdadan ayrı saklayın.',
        8: 'Kimyasala dayanıklı eldiven ve koruyucu giysi.',
    },
    'H313': {
        4: 'CİLT: Bol su ile yıkayın. İyi hissetmiyorsanız doktora gidin.',
        5: 'Standart söndürücü kullanın.',
        6: 'KKE ile toplayın.',
        7: 'Gereksiz cilt temasından kaçının; kullanım sonrası elleri yıkayın.',
        8: 'Koruyucu eldiven kullanın.',
    },
    'H316': {
        4: 'Cildi bol suyla yıkayın. Tahriş devam ederse doktora gidin.',
        5: 'Standart söndürücü kullanın.',
        6: 'KKE ile toplayın.',
        7: 'Uzun süreli cilt temasından kaçının; koruyucu eldiven kullanın.',
        8: 'Koruyucu eldiven kullanın.',
    },
    'H320': {
        4: 'GÖZ: Birkaç dakika suyla yıkayın. Tahriş devam ederse göz doktoruna gidin.',
        5: 'Standart söndürücü kullanın.',
        6: 'KKE ile toplayın.',
        7: 'Göz temasından kaçının; kullanım sırasında göz koruyucu takın.',
        8: 'Göz koruyucu kullanın.',
    },
    'H332': {
        4: 'SOLUNUM: Kişiyi temiz havaya çıkarın. Semptom devam ederse doktora gidin.',
        5: 'Yangın gazlarından solunum koruması kullanın.',
        6: 'İyi havalandırma sağlayın. Buhar/sis oluşmasını önleyin.',
        7: 'İyi havalandırılan alanlarda kullanın; buhar birikiminden kaçının. '
           'OEL aşılma riskinde solunum koruyucu kullanın.',
        72: 'İyi havalandırılmış yerde, kabı kapalı tutarak saklayın.',
        8: 'Yarım yüz maskesi (A tipi filtre) veya tüm yüz maskesi.',
    },
    'H333': {
        4: 'SOLUNUM: Temiz havaya çıkarın. İyi hissetmiyorsanız doktora gidin.',
        5: 'Standart söndürücü kullanın.',
        6: 'Havalandırma sağlayın.',
        7: 'İyi havalandırılan alanlarda kullanın; buhar solumaktan kaçının.',
        72: 'İyi havalandırılmış yerde kapalı kapta saklayın.',
        8: 'Uygun solunum maskesi kullanın.',
    },
    'H334': {
        4: 'SOLUNUM: Temiz havaya çıkarın. Astım semptomu varsa bronkodilatör verin. Acil tıbbi yardım.',
        5: 'Solunum koruyucu kullanın. CO₂ veya kuru kimyasal.',
        6: 'Buhar/aerosol — solunum koruması olmadan girilmeyin.',
        7: 'Solunum duyarlılaştırıcı — bir kez duyarlılaşan kişiler çok düşük '
           'konsantrasyonlarda bile etkilenebilir. SCBA veya tam yüz maskesi zorunlu. '
           'Astım hastaları bu maddeyle çalışmamalıdır.',
        72: 'İyi havalandırılmış yerde, sıkıca kapalı kapta saklayın.',
        8: 'Solunum duyarlılaştırıcı — SCBA veya tam yüz maskesi (ABEK filtre).',
    },
    'H335': {
        4: 'SOLUNUM: Temiz havaya çıkarın. Tahriş devam ederse doktora gidin.',
        5: 'Yangın gazlarından kaçının. Uygun solunum koruması.',
        6: 'İyi havalandırma sağlayın. Buhar birikimini önleyin.',
        7: 'Yalnızca iyi havalandırılan alanlarda kullanın. '
           'Buhar/sis oluşumundan kaçının; solunum tahriş edicidir.',
        72: 'İyi havalandırılmış yerde, sıkıca kapalı kapta saklayın.',
        8: 'Organik buhar filtreli (A tipi) yarım yüz maskesi.',
    },
    'H336': {
        4: 'SOLUNUM/NARKOTİK: Temiz havaya çıkarın. Bilinç kaybı varsa kurtarma pozisyonu. Doktora gidin.',
        5: 'Buhar-hava karışımı patlayıcı olabilir. CO₂ veya kuru kimyasal.',
        6: 'Havalandırın. Kapalı alanda birikim tehlikeli. Narkotik etki riski.',
        7: 'Yalnızca iyi havalandırılan alanlarda kullanın; narkotik etki riski. '
           'Çalışma alanında yemeyin, içmeyin, sigara içmeyin.',
        72: 'Serin, iyi havalandırılmış yerde, sıkıca kapalı kapta saklayın.',
        8: 'Organik buhar filtreli solunum maskesi. Yeterli havalandırma şart.',
    },
    'H341': {
        4: 'Maruziyet kayıt altına alınmalıdır. Doktora başvurun.',
        5: 'Yangın gazları mutajenik olabilir. Solunum koruması zorunlu.',
        6: 'Deri ve solunum temasından kaçının. Tam KKE.',
        7: 'Şüpheli mutajen — maruziyeti minimize edin (ALARA ilkesi). '
           'Kullanmadan önce özel talimatları edinin; tam KKE zorunlu.',
        72: 'Kilitli yerde, yetkisiz erişime kapalı olarak saklayın.',
        8: 'Nitril eldiven (min 0.5mm), ABEK filtreli tam yüz maskesi.',
    },
    'H351': {
        4: 'KANSEROJENİK ŞÜPHELİ: Her türlü maruziyet minimize edilmeli. Doktora başvurun.',
        5: 'Yangın gazları toksik olabilir. Solunum koruması kullanın.',
        6: 'Deri ve solunum temasından kaçının. Tam KKE kullanın.',
        7: 'Şüpheli kanserojen — maruziyeti mümkün olan en düşük düzeyde tutun (ALARA). '
           'Kullanmadan önce özel talimatları edinin; tam KKE zorunlu.',
        72: 'Kilitli yerde yetkili kişiler dışında erişimi kısıtlayın.',
        8: 'Nitril eldiven, ABEK filtreli tam yüz maskesi, koruyucu giysi.',
    },
    'H361': {
        4: 'Maruziyet kayıt altına alınmalı. Üreme sağlığı uzmanına başvurun.',
        5: 'Uygun söndürücü kullanın. Solunum koruması.',
        6: 'Tam KKE kullanın. Deri ve solunum temasından kaçının.',
        7: 'Şüpheli üreme toksini — hamile ve emziren kadınlar çalışmamalıdır. '
           'Kullanmadan önce özel talimatları edinin; maruziyeti minimize edin.',
        72: 'Kilitli yerde saklayın. Hamile ve emziren kadınların erişimini kısıtlayın.',
        8: 'Nitril eldiven, göz koruyucu, ABEK filtreli maske.',
    },
    'H362': {
        4: 'Emziren anneler maruziyetten derhal uzaklaşmalı. Pediatriste başvurun.',
        5: 'Uygun söndürücü kullanın.',
        6: 'KKE ile toplayın.',
        7: 'Emziren anneler bu maddeyle çalışmamalıdır; '
           'maruziyetin süt yoluyla bebeğe geçme riski vardır.',
        72: 'Emziren kadınların erişimini kısıtlayan, kilitli yerde saklayın.',
        8: 'Koruyucu eldiven ve giysi.',
    },
    'H401': {
        4: 'Su ile temasa geçmesini önleyin. Doktora gidin.',
        5: 'Yangın suyu çevreye yayılmasın.',
        6: 'Kanalizasyona girmesini önleyin. Absorban ile toplayın.',
        7: 'Su ortamına dökülmesini önleyin; taşıma sırasında ikincil güvenlik kabı kullanın.',
        72: 'Su kaynaklarından uzak, sıkıca kapalı kapta saklayın.',
        8: 'Çevreye yayılmayı önleyen KKE kullanın.',
    },
    'H413': {
        4: 'Çevresel temas halinde yerel makamları haberdar edin.',
        5: 'Yangın suyu çevreye yayılmasın. Su kaynaklarını koruyun.',
        6: 'Kanalizasyona girmesini önleyin. Absorban ile toplayın.',
        7: 'Su ortamına dökülmesini önleyin; taşıma sırasında ikincil güvenlik kabı kullanın.',
        72: 'Çevre tehlikeli — sıkıca kapalı kapta, su kaynaklarından uzakta saklayın.',
        8: 'Çevreye yayılmayı önleyen KKE kullanın.',
    },
    'H420': {
        4: 'Ozon bozucu madde — yoğun maruziyet halinde doktora gidin.',
        5: 'CO₂ veya kuru kimyasal kullanın.',
        6: 'Açık alanlarda kullanın. Buharlanmayı önleyin.',
        7: 'Ozon tabakasına zarar verir — atmosfere salınımı kesinlikle önleyin; '
           'sızdırmaz ekipman ve boru bağlantıları kullanın.',
        72: 'Sızdırmaz kapta, serin yerde, UV ışığından korunarak saklayın.',
        8: 'Uygun solunum maskesi ve göz koruyucu.',
    },

    'H242': {
        4: 'Isı kaynaklı yangın yaralanması için soğuk su uygulayın. Doktora gidin.',
        5: 'Uygun söndürücü kullanın. Isınan konteynerler patlayabilir.',
        6: 'Isı kaynaklarından uzaklaştırın. KKE ile toplayın.',
        7: 'Isı ve tutuşma kaynaklarından uzak ortamda kullanın; ısınmayı önleyecek şekilde havalandırın.',
        72: 'Serin yerde, ısı ve tutuşturma kaynaklarından uzakta, oksitleyicilerden ayrı saklayın.',
        8: 'Koruyucu eldiven ve yüz siperi kullanın.',
    },
    'H270': {
        4: 'OKSİTLEYİCİ GAZ: Gözle temas halinde bol suyla yıkayın. Doktora gidin.',
        5: 'OKSİTLEYİCİ: Yangını şiddetlendirebilir. CO₂ KULLANMAYIN. Su spreyi.',
        6: 'Bölgeden uzaklaşın. Sızdıran tüpü dışarı çıkarın. Uzman ekip.',
        7: 'Yanıcı maddelerden uzakta, kilitli, havalandırılmış depoda saklayın.',
        8: 'Alev geciktirici giysi, SCBA ve yüz siperi zorunlu.',
    },
    # Not: Tüm H kodları yukarıda detaylı olarak tanımlanmıştır.

}

# Bölüm 8 — KKE: H kodundan ekipman listesi
H_TO_PPE: Dict[str, Dict] = {
    # ── Solunum Toksisitesi ───────────────────────────────────────────────────
    'H330': {   # Kat.1-2 — ÖLÜMCÜL solunursa
        'resp':   'ABEK filtreli tam yüz maskesi veya SCBA (bağımsız solunum cihazı)',
        'gloves': 'Kimyasala dayanıklı eldiven',
        'eyes':   'Kimyasal gözlük veya tam yüz koruyucu',
    },
    'H331': {   # Kat.3 — TOKSİK solunursa
        'resp':   'Organik/inorganik gaz filtreli yarım veya tam yüz maskesi',
        'gloves': 'Kimyasala dayanıklı eldiven',
        'eyes':   'Kimyasal gözlük',
    },
    'H332': {   # Kat.4 — zararlı solunursa
        'resp':   'OEL aşılma riskinde P2/P3 filtreli toz maskesi veya gaz filtreli maske',
        'gloves': 'Nitril eldiven',
        'eyes':   'Güvenlik gözlüğü',
    },
    'H334': {   # Solunum duyarlılaştırıcı — SCBA veya tam yüz maskesi zorunlu
        'resp':   'Solunum duyarlılaştırıcı — SCBA veya tam yüz maskesi (ABEK filtre)',
        'gloves': 'Kimyasala dayanıklı eldiven',
    },
    # ── Cilt Korozif / Aşındırıcı ────────────────────────────────────────────
    'H314': {   # Kat.1A/1B/2 — cilt yanığı/göz hasarı
        'resp':   'Buhar/aerosol oluşursa: ABEK filtreli maske veya ortama uygun solunum koruyucu',
        'gloves': 'Kimyasala dayanıklı eldiven (nitril ≥0.4mm veya neopren/butil)',
        'eyes':   'Kimyasal gözlük ve yüz siperi',
        'body':   'Kimyasala dayanıklı koruyucu giysi ve çizme',
    },
    # ── Akut Toksisite — Deri ────────────────────────────────────────────────
    'H310': {   # Kat.1-2 — ÖLÜMCÜL deri temasında
        'resp':   'Buhar oluşursa SCBA veya ABEK filtreli tam yüz maskesi',
        'gloves': 'Çift eldiven — kimyasala dayanıklı dış eldiven',
        'eyes':   'Tam yüz koruyucu',
        'body':   'Kimyasala dayanıklı tulum',
    },
    'H311': {   # Kat.3 — toksik deri temasında
        'resp':   'Buhar/aerosol oluşursa uygun solunum koruyucu',
        'gloves': 'Kimyasala dayanıklı eldiven',
        'eyes':   'Kimyasal gözlük',
    },
    # ── Oksitleyici ──────────────────────────────────────────────────────────
    'H271': {   # Kat.1 — yangın veya patlama yapabilir
        'resp':   'SCBA veya ABEK-P3 filtreli tam yüz maskesi',
        'gloves': 'Oksidana dayanıklı eldiven (butil veya neopren)',
        'eyes':   'Kimyasal gözlük ve yüz siperi',
        'body':   'Yanmaz/kimyasala dayanıklı koruyucu giysi',
    },
    'H272': {   # Kat.2-3 — yangını şiddetlendirebilir
        'resp':   'OEL aşılma riskinde inorganik gaz filtreli yarım maske',
        'gloves': 'Kimyasala dayanıklı eldiven (nitril veya neopren)',
        'eyes':   'Kimyasal gözlük',
    },
    # ── Yanıcı Sıvı ──────────────────────────────────────────────────────────
    'H225': {
        'resp':   'Organik buhar filtreli maske (konsantrasyona bağlı)',
        'gloves': 'Çözücüye dayanıklı eldiven',
        'eyes':   'Kimyasal gözlük',
        'body':   'Antistatik giysiler',
    },
    'H224': {
        'resp':   'Organik buhar filtreli tam yüz maskesi',
        'gloves': 'Çözücüye dayanıklı eldiven',
        'eyes':   'Kimyasal gözlük',
        'body':   'Antistatik ve kimyasala dayanıklı giysi',
    },
    # ── Karsinojen / Mutajen / Üreme Toksik ─────────────────────────────────
    'H350': {
        'resp':   'HEPA + gaz filtreli solunum koruyucu (ALARA ilkesi)',
        'gloves': 'Kimyasala dayanıklı eldiven',
        'body':   'Koruyucu giysi',
    },
    'H340': {
        'resp':   'P3 filtreli toz maskesi veya gaz filtreli solunum koruyucu',
        'gloves': 'Kimyasala dayanıklı eldiven',
        'body':   'Koruyucu giysi',
    },
    # ── Su Reaktif ───────────────────────────────────────────────────────────
    'H260': {
        'resp':   'Su geçirmez tam yüz maskesi — H2 gazı oluşabilir',
        'gloves': 'Su geçirmez kimyasal koruyucu eldiven',
        'eyes':   'Tam yüz koruyucu',
        'body':   'Su geçirmez koruyucu giysi',
    },
}

# Bölüm 5 — H kodundan yangın söndürücü önerisi
H_TO_EXTINGUISHER: Dict[str, str] = {
    'H224': 'Kuru kimyasal toz, CO₂, alkolle uyumlu köpük. Su spreyi soğutmak için kullanılabilir.',
    'H225': 'Kuru kimyasal, CO₂ veya köpük. Büyük yangın: su sisi.',
    'H226': 'Kuru kimyasal toz, CO₂ veya alkole dayanıklı köpük. Su kullanmayın.',
    'H228': 'Kuru kimyasal veya su spreyi. Toz halindeyse patlama riski — uzaktan müdahale.',
    'H271': 'CO₂ veya kum. Su KULLANILMAZ.',
    'H272': 'Bol su (oksitleyici). Yanıcı maddelerle temastan uzak tutun.',
    'H304': 'CO₂ veya kuru toz. Su yayılmaya neden olabilir.',
    'H314': 'CO₂, kuru kimyasal veya su sisi. Su jeti kullanmayın.',
    # ── Yanıcı Katı / Aerosol / Basınçlı ────────────────────────────────────
    'H229': {
        5: 'Basınçlı kap. Isınırsa patlayabilir. Açık alev veya ısı kaynağından uzak tutun.',
        6: 'Isı kaynaklarından uzak tutun. Serin yerde bekletin.',
        7: 'Doğrudan güneş ışığından ve 50°C üzerindeki sıcaklıklardan koruyun.',
    },
    'H240': {
        4: 'Isı veya şok sonucu patlama olabilir. Tıbbi yardım alın.',
        5: 'Patlama riski! Uzaktan söndürün. Ateş ekibini haberdar edin.',
        6: 'Uzak durun. Uzman ekip çağırın. Isı kaynaklarını uzaklaştırın.',
        7: 'Serin, kuru yerde saklayın. 15°C altında tutun.',
    },
    'H241': {
        4: 'Isı sonucu yangın veya patlama. Tıbbi yardım alın.',
        5: 'Kuru kimyasal veya CO₂ kullanın. Büyük yangınlarda uzak durun.',
        6: 'Isı kaynaklarını ortadan kaldırın. KKE giyin.',
        7: 'Serin, havalandırılmış yerde saklayın.',
    },
    'H242': {
        4: 'Isı ile temas sonrası ilk yardım gerekliyse doktora gidin.',
        5: 'Kuru kimyasal veya CO₂ ile söndürün.',
        6: 'Sıcak yüzeylerden uzaklaştırın. Absorban malzeme ile toplayın.',
        7: 'Serin yerde saklayın. Oksitleyicilerden uzak tutun.',
    },

    # ── Pirofor ──────────────────────────────────────────────────────────────
    'H250': {
        4: 'Havaya maruz kalan alanları suyla soğutun. Ciddi yanık riski — acil tıbbi yardım.',
        5: 'HAVA İLE TEMAS ETMEYİN. Kuru kum veya özel söndürücü kullanın. Su kullanmayın.',
        6: 'Oksijen kaynaklarını uzaklaştırın. İnert atmosfer altında toplayın.',
        7: 'İnert gaz altında, hava ve nemden korumalı kapalı kapta saklayın.',
        8: 'Tam koruyucu giysi, inert atmosfer. Cilt teması önleyin.',
    },
    'H251': {
        4: 'Isıya bağlı yanık veya yangın sonrası tıbbi yardım alın.',
        5: 'Büyük miktarlarda yangın riski. CO₂ veya kuru toz kullanın.',
        6: 'Küçük miktarlarda toplayın. Isı kaynaklarından uzak tutun.',
        7: 'Serin yerde, 35°C altında saklayın.',
    },
    'H252': {
        4: 'Isıya bağlı yanık veya yangın sonrası tıbbi yardım alın.',
        5: 'Büyük miktarlarda depolama yangın riski. Dikkatli yaklaşın.',
        6: 'Büyük yığınlardan uzak durun. Uzman yardımı isteyin.',
        7: 'Büyük miktarlar halinde saklamayın. Serin, havalandırılmış ortam.',
    },

    # ── Su Reaktif ───────────────────────────────────────────────────────────
    'H260': {
        4: 'SU İLE TEMAS ETMEYİN. Yanıcı gaz oluşur. Tutuşma riski — acil tahliye.',
        5: 'SUYLA SÖNDÜRMEYIN. Kuru toz veya kum kullanın.',
        6: 'Su ve yağmurdan koruyun. KKE giyin. İnert gaz ile koru.',
        7: 'Kuru, nem içermeyen ortamda saklayın. Su kaynaklarından uzak tutun.',
        8: 'Su geçirmez eldiven ve kıyafet. Nem ile teması kesinlikle önle.',
    },
    'H261': {
        4: 'Su ile temas sonrası yanıcı gaz oluşabilir. Tıbbi yardım alın.',
        5: 'SUYLA SÖNDÜRMEYIN. Kuru kimyasal kullanın.',
        6: 'Su kaynaklarından uzak toplayın. KKE giyin.',
        7: 'Nemden koruyun. Orijinal kapalı ambalajında saklayın.',
        8: 'Su geçirmez eldiven. Nem ile teması önle.',
    },

    # ── Oksitleyici Gaz ──────────────────────────────────────────────────────
    'H270': {
        4: 'Yangın veya patlama sonrası acil tıbbi yardım alın.',
        5: 'Oksitleyici gaz yangını — yanıcı maddeleri uzaklaştırın. Suyla soğutun.',
        6: 'Tüm tutuşturma kaynaklarını uzaklaştırın. Bölgeyi boşaltın.',
        7: 'Yanıcı ve organik maddelerden uzakta saklayın.',
        8: 'SCBA ve tam koruyucu kıyafet. Oksijen zenginleşmesine dikkat.',
    },

    # ── Basınçlı Gaz ─────────────────────────────────────────────────────────
    'H280': {
        4: 'Donma veya basınç kaynaklı yaralanmada tıbbi yardım alın.',
        5: 'Tüpleri serin tutun. Patlama riski. Su spreyi ile soğutun.',
        6: 'Tüp düşmesin — bölgeden uzaklaştırın.',
        7: 'Dik konumda, serin, havalandırılmış yerde saklayın. Güneşten koruyun.',
        8: 'Gaz kaçağına karşı solunum koruması. İyi havalandırma.',
    },
    'H281': {
        4: 'Kriyojenik yanık — suyla ısıtmayın. Acil tıbbi yardım.',
        5: 'Sıvılaşmış gaz yangını: soğuk tüp — uzaktan müdahale.',
        6: 'Kriyojenik temas riski. Uygun KKE ile toplayın.',
        7: 'Kriyojenik kaplarda saklayın. Isıya maruz bırakmayın.',
        8: 'Kriyojenik eldiven, gözlük. Ciltten uzak tutun.',
    },

    # ── Metallere Aşındırıcı ─────────────────────────────────────────────────
    'H290': {
        4: 'Metal kap veya araç hasarı sonrası yara oluşursa tıbbi yardım.',
        5: 'Metal ekipmanla temas — kimyasal reaksiyon riski. CO₂ veya kuru toz.',
        6: 'Metal yüzeylerle temasını önleyin. Absorban toplayın.',
        7: 'Plastik veya cam kaplarda saklayın. Metalden uzak tutun.',
        8: 'Paslanmaz çelik veya plastik ekipman kullanın.',
    },

    # ── Akut Toksisite "Olabilir" Sınıfları ──────────────────────────────────
    'H303': {
        4: 'Yutulursa ağzı çalkalayın. Rahatsızlık hissedilirse doktora gidin.',
        6: 'Döküntüyü toplayın. Gıda maddelerinden uzak tutun.',
        7: 'Gıda ve içeceklerden uzakta saklayın.',
    },
    'H305': {
        4: 'Yutulursa KUSTURMAYINIZ. Soluk yoluna girme riski. Acil tıbbi yardım.',
        5: 'Aspirasyon riski — yangın söndürme suyunun yayılmasını önleyin.',
        6: 'Döküntüyü dikkatlice toplayın. Soluma riskini minimize edin.',
        7: 'Aspirasyon riskli ürün. Orijinal kapakta saklayın.',
    },
    'H313': {
        4: 'Cilt temasında bol su ile yıkayın. Rahatsızlık devam ederse doktora gidin.',
        6: 'KKE ile toplayın. Cilt temasından kaçının.',
        7: 'Serin, kuru yerde saklayın.',
        8: 'Nitril eldiven. Cilt temasını önle.',
    },
    'H316': {
        4: 'Cilt temasında su ile yıkayın. Tahriş devam ederse tıbbi yardım.',
        6: 'KKE giyin. Cilt temas riskini azaltın.',
        7: 'Serin, kuru yerde saklayın.',
        8: 'Koruyucu eldiven kullanın.',
    },
    'H320': {
        4: 'Gözle temasta bol su ile yıkayın. Rahatsızlık devam ederse göz doktoruna gidin.',
        6: 'Göz koruması ile toplayın.',
        7: 'Serin yerde saklayın.',
        8: 'Kimyasal gözlük. Göz temasından kaçının.',
    },
    'H333': {
        4: 'Solunursa temiz havaya çıkarın. Rahatsızlık devam ederse doktora gidin.',
        6: 'Yeterli havalandırma sağlayın. KKE kullanın.',
        7: 'İyi havalandırılmış yerde saklayın.',
        8: 'Gerekirse organik buhar filtreli maske.',
    },

    # ── Sucul Akut / Kronik Kat.4 ────────────────────────────────────────────
    'H401': {
        6: 'Sucul ortama dökülmesini önleyin. Acil çevre müdahalesini bilgilendirin.',
        7: 'Su kaynaklarından uzakta saklayın.',
    },
    'H413': {
        6: 'Su kaynaklarına ulaşmasını önleyin. Absorban malzeme ile toplayın.',
        7: 'Sıkıca kapalı kapta saklayın. Su kaynaklarından uzak.',
        8: 'Çevre koruyucu önlem alın.',
    },

    # ── Üreme/Emzirme ────────────────────────────────────────────────────────
    'H362': {
        4: 'Emziren anneler bu ürünle çalışmamalıdır. Tıbbi yardım alın.',
        7: 'Çocukların erişemeyeceği yerde saklayın.',
        8: 'Hamile ve emziren kadınlar bu ürünle çalışmamalıdır.',
    },

    # ── Ozon ─────────────────────────────────────────────────────────────────
    'H420': {
        6: 'Atmosfere salınımı önleyin. Yetkili bertaraf noktasına iletin.',
        7: 'Hava geçirmez kapalı kapta saklayın.',
    },

}


# ─── ANA BÖLÜM ÜRETME FONKSİYONLARI ─────────────────────────────────────────

def generate_section3(
    components: List[Dict],
    disclosure_map: Optional[Dict[str, str]] = None,
    lang: str = 'TR',
) -> List[Dict]:
    """
    SDS Bölüm 3 — Bileşenler tablosu
    disclosure_map: {cas: 'show'|'range'|'hide'} — varsayılan 'show'
    lang: 'TR' | 'EN' — Türkçe SDS için name_tr kullanılır
    """
    disclosure_map = disclosure_map or {}
    rows = []
    for comp in components:
        cas = comp.get('cas_no', comp.get('cas', '')).strip()
        # Varsayılan 'range': ticari sır koruması (CLP Madde 24(2) / KKDİK Ek-2 B3.2).
        # Frontend disclosure_map'te explicit 'show' göndermezse ECHA aralığı kullanılır.
        level = disclosure_map.get(cas, 'range')
        # Esans/gizli karışım → disclosure_map'te 'show' bırakılmışsa min. 'range'e zorla
        if comp.get('comp_type') == 'fragrance' and level == 'show':
            level = 'range'
        row = format_section3_component(comp, level, lang=lang)
        rows.append(row)
    return rows


def generate_section(
    section_num: int,
    h_codes: List[str],
    mixture_form: str = 'liquid',
) -> Dict:
    """
    SDS Bölüm 4-8 için otomatik metin üret.

    Args:
        section_num: 4, 5, 6, 7 veya 8
        h_codes: Karışımın H kodu listesi
        mixture_form: 'liquid'|'solid'|'aerosol'

    Returns:
        {'text': str, 'bullets': [...], 'ppe': dict (sadece bölüm 8)}
    """
    sentences = []
    seen = set()

    # Önce en tehlikeli H kodlarını işle
    priority_order = [
        'H330','H331','H334','H310','H311','H300','H301','H314','H318',
        'H271','H272','H304','H340','H350','H360','H370','H371',
        'H372','H373','H400','H410','H225','H226','H317','H319',
        'H315','H302','H312','H332','H411','H412',
    ]
    ordered = [h for h in priority_order if h in h_codes]
    rest = [h for h in h_codes if h not in ordered]

    for h in ordered + rest:
        entry = H_SENTENCES.get(h, {})
        sentence = entry.get(section_num)
        if not sentence:
            continue
        # Liste değeri: birden fazla bullet (ör. H314 cilt + göz ayrımı)
        items = sentence if isinstance(sentence, list) else [sentence]
        for item in items:
            if item and item not in seen:
                sentences.append({'h_code': h, 'text': item})
                seen.add(item)

    # Bölüm 5 için yangın söndürücü ekle
    extinguisher = None
    if section_num == 5:
        for h in priority_order:
            if h in h_codes and h in H_TO_EXTINGUISHER:
                extinguisher = H_TO_EXTINGUISHER[h]
                break
        if not extinguisher:
            extinguisher = 'Uygun yangın söndürücü kullanın. Büyük yangınlarda uzmanlaşmış ekip çağırın.'

    # Bölüm 8 için KKE
    ppe = {}
    if section_num == 8:
        for h in priority_order:
            if h in h_codes and h in H_TO_PPE:
                for eq, desc in H_TO_PPE[h].items():
                    if eq not in ppe:  # İlk (en yüksek öncelikli) KKE kazanır
                        ppe[eq] = desc

        # Varsayılan KKE (yoksa)
        if not ppe.get('gloves'):
            ppe['gloves'] = 'Nitril veya lateks eldiven'
        if not ppe.get('eyes'):
            ppe['eyes'] = 'Güvenlik gözlüğü veya koruyucu yüz siperi'
        # Body KKE — alevlenir sıvı veya cilt tahriş ediciler için
        if not ppe.get('body'):
            flam_h = [h for h in h_codes if h in ('H224','H225','H226','H228')]
            skin_h = [h for h in h_codes if h in ('H314','H315','H317','H310','H311','H312')]
            if flam_h or skin_h:
                ppe['body'] = 'Antistatik ve kimyasala dayanıklı koruyucu giysi'
            else:
                ppe['body'] = 'Uygun iş giysisi'

    # Bölüm 6 için genel çevre notu
    env_note = None
    if section_num == 6 and any(h in h_codes for h in ['H400','H410','H411','H412']):
        env_note = 'Döküntünün kanalizasyon veya su kaynaklarına ulaşmasını önleyin. Çevre müdahale ekibini haberdar edin.'

    return {
        'section': section_num,
        'sentences': sentences,
        'combined_text': ' '.join(s['text'] for s in sentences),
        'bullets': [s['text'] for s in sentences],
        'extinguisher': extinguisher,
        'ppe': ppe,
        'env_note': env_note,
    }


def generate_all_sections(
    h_codes: List[str],
    components: List[Dict],
    mixture_form: str = 'liquid',
    disclosure_map: Optional[Dict[str, str]] = None,
    lang: str = 'TR',
) -> Dict:
    """
    Tüm SDS bölümlerini tek seferde üret.
    """
    return {
        'section3':  generate_section3(components, disclosure_map, lang=lang),
        'section4':  generate_section(4, h_codes, mixture_form),
        'section5':  generate_section(5, h_codes, mixture_form),
        'section6':  generate_section(6, h_codes, mixture_form),
        'section7':  generate_section(7, h_codes, mixture_form),
        'section8':  generate_section(8, h_codes, mixture_form),
    }


# ─── BÖLÜM 4.2 — Semptomlar ve Etkiler (EU CLP 2020/878 §4.2) ───────────────
# Format: H_KODU → semptom metni (Türkçe)
# Amaç: Madde/karışıma özgü belirti/etkileri tanımla (ilk yardım DEĞİL).

SYMPTOM_SENTENCES_42: Dict[str, str] = {

    # ── AKUT TOKSİSİTE — ORAL ────────────────────────────────────────────
    'H300': (
        'YUTULMA (Akut Oral — Kat. 1/2): Yutulması halinde ciddi zehirlenme belirtileri; bulantı, '
        'kusma, karın krampları, bilinç bozukluğu, organ hasarı veya ölüm riski.'
    ),
    'H301': (
        'YUTULMA (Akut Oral — Kat. 3): Yutulması halinde zehirlenme; bulantı, kusma, karın ağrısı, '
        'baş dönmesi ve sistemik etki riski.'
    ),
    'H302': (
        'YUTULMA (Akut Oral — Kat. 4): Yutulması halinde hafif-orta bulantı, kusma ve karın ağrısı.'
    ),

    # ── AKUT TOKSİSİTE — DERİ ────────────────────────────────────────────
    'H310': (
        'DERİ EMILIMI (Akut Dermal — Kat. 1/2): Cilt yoluyla hızlı sistemik emilim; halsizlik, '
        'titreme, solunum güçlüğü, bilinç kaybı ve ölüm riski.'
    ),
    'H311': (
        'DERİ EMILIMI (Akut Dermal — Kat. 3): Cilt yoluyla emilimde baş ağrısı, baş dönmesi, '
        'bulantı ve sistemik etki.'
    ),
    'H312': (
        'DERİ EMILIMI (Akut Dermal — Kat. 4): Cilt yoluyla emilimde hafif sistemik belirtiler; '
        'baş ağrısı, halsizlik.'
    ),

    # ── AKUT TOKSİSİTE — SOLUNUM ─────────────────────────────────────────
    'H330': (
        'SOLUNUM (Akut İnhalasyon — Kat. 1/2): Buhar/gaz solunması halinde solunum yolu ve akciğer '
        'hasarı; ciddi öksürük, akciğer ödemi, siyanoz (morarma), bilinç kaybı ve ölüm riski. '
        'Semptomlar maruziyetten saatler sonra ortaya çıkabilir.'
    ),
    'H331': (
        'SOLUNUM (Akut İnhalasyon — Kat. 3): Buhar solunması halinde solunum yolu tahrişi; '
        'öksürük, nefes darlığı, göğüs ağrısı ve solunum güçlüğü.'
    ),
    'H332': (
        'SOLUNUM (Akut İnhalasyon — Kat. 4): Buhar solunmasında hafif boğaz/solunum yolu tahrişi; '
        'öksürük, burun akıntısı.'
    ),

    # ── ASPİRASYON TOKSİSİTESİ ────────────────────────────────────────────
    'H304': (
        'ASPİRASYON: Yutulup soluk borusuna kaçarsa kimyasal pnömoni (akciğer yangısı) riski; '
        'öksürük, nefes darlığı, göğüs ağrısı, ateş. Semptomlar 24–48 saat gecikebilir.'
    ),

    # ── CİLT / GÖZ TAHRİŞİ / KOROZYON ───────────────────────────────────
    'H314': (
        'CİLT VE GÖZ KOROZYONU (Kat. 1): Cilt ve mukozada anlık kimyasal yanık; şiddetli ağrı, '
        'kızarıklık, kabarcık, doku nekrozu. Gözlerde kalıcı hasar riski. '
        'Yutulması halinde ağız, boğaz ve mide yanığı.'
    ),
    'H315': (
        'CİLT TAHRİŞİ (Kat. 2): Temas bölgesinde kızarıklık, kaşıntı, yanma hissi ve hafif şişme. '
        'Uzun süreli temaslarda deri soyulması.'
    ),
    'H316': (
        'HAFİF CİLT TAHRİŞİ: Temas bölgesinde geçici kızarıklık ve hafif rahatsızlık hissi.'
    ),
    'H317': (
        'CİLT DUYARLILASTIRMASI (Kat. 1): İlk temaslarda belirgin belirti olmayabilir. '
        'Tekrarlayan temaslarda alerjik kontakt dermatit gelişir: kaşıntı, kızarıklık, kabarcık ve egzama. '
        'Bir kez duyarlılaşan kişilerde çok düşük konsantrasyon dahi semptom tetikleyebilir.'
    ),
    'H318': (
        'CİDDİ GÖZ HASARI (Kat. 1): Temas halinde şiddetli göz ağrısı, fotofobi (ışığa duyarlılık), '
        'ağlama, görme bulanıklığı; tedavi edilmezse kalıcı görme kaybı.'
    ),
    'H319': (
        'GÖZ TAHRİŞİ (Kat. 2): Temas halinde yanma hissi, kızarıklık, gözyaşı artışı. '
        'Genellikle geçici; 24–72 saat içinde düzelir.'
    ),
    'H320': (
        'HAFİF GÖZ TAHRİŞİ: Geçici kızarıklık ve rahatsızlık hissi.'
    ),

    # ── SOLUNUM DUYARLILASTIRMA ───────────────────────────────────────────
    'H334': (
        'SOLUNUM DUYARLILASTIRMASI (Kat. 1): Tekrarlayan maruziyette mesleki astım gelişimi; '
        'hırıltılı nefes, nefes darlığı, göğüste sıkışma, öksürük. '
        'Duyarlılaşma sonrası çok düşük konsantrasyonlar ciddi astım krizi tetikleyebilir. '
        'Uzun dönemde kalıcı solunum yolu hasarı riski.'
    ),

    # ── STOT — TEK MARUZIYET ─────────────────────────────────────────────
    'H335': (
        'SOLUNUM YOLU TAHRİŞİ: Buhar/sis solunmasında boğaz ve burun tahrişi, '
        'öksürük, nefes darlığı.'
    ),
    'H336': (
        'UYUŞTURUCU ETKİ: Yüksek konsantrasyonda buhar solunması baş dönmesi, '
        'baş ağrısı, uyuşukluk, koordinasyon bozukluğu ve bilinç değişikliğine yol açar.'
    ),
    'H370': (
        'SPESIFIK ORGAN TOKSISITESI — Tek Maruziyet (Kat. 1): Maruziyetten kısa süre sonra '
        'hedef organa özgü belirtiler; fonksiyon bozukluğu. Acil tıbbi değerlendirme gerektirir.'
    ),
    'H371': (
        'SPESIFIK ORGAN TOKSISITESI — Tek Maruziyet (Kat. 2): Maruziyette olası organ '
        'fonksiyon bozukluğu; organ tipine bağlı belirtiler.'
    ),

    # ── STOT — TEKRARLAYAN MARUZIYET ─────────────────────────────────────
    'H372': (
        'KRONİK ORGAN HASARI (Kat. 1): Uzun süreli veya tekrarlayan maruziyet hedef organda '
        'kalıcı hasar; organ yetmezliğine ilerleyebilir. '
        'Periyodik sağlık takibi zorunludur.'
    ),
    'H373': (
        'KRONİK ORGAN HASARI (Kat. 2): Uzun süreli maruziyette olası organ hasarı; '
        'belirsiz yorgunluk, fonksiyon gerileme riski.'
    ),

    # ── YANICILIK ─────────────────────────────────────────────────────────
    'H224': (
        'YANICILIK/BUHAR SOLUNUM: Yüksek buhar yoğunluğunda baş dönmesi, baş ağrısı, bulantı, '
        'koordinasyon bozukluğu, bilinç değişikliği. Deri ve göz tahrişi.'
    ),
    'H225': (
        'YANICILIK/BUHAR SOLUNUM: Buhar solunması; baş ağrısı, baş dönmesi, uyuşukluk. '
        'Cilt ve göz tahrişi.'
    ),
    'H226': (
        'YANICILIK/BUHAR SOLUNUM: Yoğun buhar solunması; baş ağrısı, baş dönmesi, bulantı. '
        'Deriye ve göze temas halinde tahriş.'
    ),

    # ── KARSİNOJENİTE / MUTAJENİTE / ÜREMEYİ ETKİLEME ────────────────────
    'H340': (
        'GENETİK HASAR (Mutajenite — Kat. 1): Akut belirti yoktur. '
        'Uzun dönemde kalıtsal genetik hasar ve kanser riski.'
    ),
    'H341': (
        'GENETİK HASAR (Mutajenite — Kat. 2): Genetik hasar şüphesi; uzun dönem risk.'
    ),
    'H350': (
        'KARSİNOJENİTE (Kat. 1): Akut belirti yoktur. Uzun dönemde malign tümör gelişim riski. '
        'Maruziyet ALARA (mümkün olan en düşük düzey) ilkesiyle sınırlandırılmalıdır.'
    ),
    'H351': (
        'KARSİNOJENİTE (Kat. 2): Muhtemel kanserojen; uzun dönemde tümör riski şüphesi.'
    ),
    'H360': (
        'ÜREMEYİ ETKİLEME (Kat. 1): Erkek/kadın fertilitesine ve fetüse zarar verir. '
        'Hamile ve emziren kadınlar ile üreme çağındaki bireyler için ciddi risk.'
    ),
    'H361': (
        'ÜREMEYİ ETKİLEME (Kat. 2): Fertilite ve fetüs üzerine muhtemel olumsuz etki.'
    ),
    'H362': (
        'ÜREMEYİ ETKİLEME — Emzirme (Kat. Ek): Anne sütüne geçerek emzirilen bebekte '
        'olumsuz etki riski.'
    ),
}


def generate_section_42(h_codes: List[str]) -> List[str]:
    """
    Bölüm 4.2 — Semptomlar ve etkiler (EU CLP 2020/878 §4.2).
    H kodlarına göre madde/karışıma özgü belirti listesi döndürür.

    Returns:
        Bullet nokta olarak girilecek semptom cümlelerinin listesi.
        Hiçbir H kodu eşleşmezse boş liste döner (fallback PDF'de uygulanır).
    """
    bullets: List[str] = []
    seen: set = set()

    # Öncelik sırası: en kritik etkilerden başla
    priority = [
        'H330', 'H331', 'H332',   # solunum toksisitesi (ölümcül → tahriş)
        'H310', 'H311', 'H312',   # deri absorbsiyon toksisitesi
        'H300', 'H301', 'H302',   # oral toksisite
        'H304',                   # aspirasyon
        'H314', 'H318',           # ciddi korozyon / göz hasarı
        'H334',                   # solunum duyarlılaştırma
        'H317',                   # cilt duyarlılaştırma
        'H370', 'H371',           # STOT tek
        'H372', 'H373',           # STOT tekrarlayan
        'H340', 'H350', 'H360',   # CMR kat. 1
        'H341', 'H351', 'H361', 'H362',  # CMR kat. 2
        'H315', 'H316', 'H319', 'H320',  # tahriş
        'H335', 'H336',           # STOT-SE solunum/narkotik
        'H224', 'H225', 'H226',  # yanıcılık / buhar solunumu
    ]

    ordered = [h for h in priority if h in h_codes]
    rest    = [h for h in h_codes if h not in ordered]

    for h in ordered + rest:
        text = SYMPTOM_SENTENCES_42.get(h)
        if text and text not in seen:
            bullets.append(text)
            seen.add(text)

    return bullets
