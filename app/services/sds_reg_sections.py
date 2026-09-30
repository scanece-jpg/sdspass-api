"""
GBF Bölüm 4, 6, 7 metinleri — KKDİK Ek-2 yapısına ve SEA Ek-4 resmî önlem ifadelerine göre.

KKDİK Ek-2:
  4.1.1 İlk yardım talimatları maruz kalma yollarına göre verilir (soluma, cilt, göz, yutma).
  4.1.2 a) acil tıbbi yardım gereği, b) temiz havaya çıkarma, c) giysilerin çıkarılması,
        ç) ilk yardım yapanlar için KKE.
  6.1   Kişisel önlemler (KKE — Bölüm 8, tutuşturucu kaynaklar, havalandırma, toz kontrolü,
        acil durum prosedürleri); 6.1.2 acil müdahale ekibi.
  6.2   Çevresel önlemler (kanallardan, yer üstü ve yer altı sularından uzak tutma).
  6.3   6.3.1 kontrol altına alma (set, tahliye deliklerinin kapatılması, kapatma prosedürleri);
        6.3.2 temizleme (nötralizasyon, emici madde, temizlik/vakumlama teknikleri, kıvılcım
        çıkarmayan ekipman); 6.3.3 uygunsuz teknikler.
  7.1.2 Genel mesleki hijyen: yeme/içme/sigara yasağı, el yıkama, kirli giysiyi çıkarma.

Metinler mümkün olduğunda SEA Ek-4 resmî P ifadeleridir (codes_i18n.get_p). Resmî metindeki
"…" tedarikçinin tamamlaması gereken yerdir (SEA Etiketleme Rehberi) — burada tamamlanır.
Bu modül ürünün fiziksel haline göre (katı/toz, gaz, sıvı) farklı metin üretir.
"""
from typing import Dict, List

from app.services.codes_i18n import get_p

FLAMMABLE_H = {'H220', 'H221', 'H222', 'H223', 'H224', 'H225', 'H226', 'H228',
               'H240', 'H241', 'H242', 'H250', 'H251', 'H252', 'H260', 'H261'}
HAZARD_H_FOR_FIRST_AIDER = {'H300', 'H301', 'H310', 'H311', 'H314', 'H317', 'H330', 'H331', 'H334'}


def _kind(form: str) -> str:
    f = (form or '').lower()
    if f in ('solid', 'powder'):
        return 'solid'
    if f == 'gas':
        return 'gas'
    return 'liquid'   # sıvı, pasta, aerosol


def _p(code: str, lang: str) -> str:
    """Resmî P metni; tedarikçinin tamamlayacağı "…" yerleri doldurulur."""
    t = get_p(lang, code) or code
    fills_tr = {
        'P302+P352': ('Bol su/… ile yıkayın', 'Bol su ile yıkayın'),
        'P301+P310': ('doktoru/… arayın', 'doktoru/hekimi arayın'),
        'P301+P312': ('doktoru/… arayın', 'doktoru/hekimi arayın'),
        'P264':      ('Elleçlemeden sonra … iyice yıkayın', 'Elleçlemeden sonra ellerinizi iyice yıkayın'),
    }
    fills_en = {
        'P302+P352': ('water/…', 'water'),
        'P264':      ('Wash … thoroughly', 'Wash hands thoroughly'),
    }
    pair = (fills_tr if lang == 'TR' else fills_en).get(code)
    if pair and pair[0] in t:
        t = t.replace(pair[0], pair[1])
    return t.replace('…', '').replace('  ', ' ').strip()


def _join(*texts: str) -> str:
    return ' '.join(t.strip() for t in texts if t and t.strip())


# ── 4.1 — maruz kalma yoluna göre ilk yardım ───────────────────────────────────
def first_aid(h_codes: List[str], form: str, lang: str = 'TR') -> List[Dict]:
    """[{'route': 'Soluma', 'text': '…'}, …] — her yol için resmî P ifadeleri."""
    h = {str(c)[:4] for c in h_codes}
    L = lang if lang in ('TR', 'EN') else 'EN'
    P = lambda c: _p(c, L)
    kind = _kind(form)
    out = []

    # Soluma
    if h & {'H330', 'H331'} or ('H314' in h and kind != 'solid'):
        inh = _join(P('P304+P340'), P('P310'))
    elif 'H334' in h:
        inh = _join(P('P304+P340'), P('P342+P311'))
    elif h & {'H332', 'H335', 'H336'}:
        inh = _join(P('P304+P340'), P('P312'))
    else:
        inh = _join(P('P304+P340'), P('P312'))
    out.append({'route': 'Soluma' if L == 'TR' else 'Inhalation', 'text': inh})

    # Cilt
    if 'H314' in h:
        skin = _join(P('P303+P361+P353'), P('P363'), P('P310'))
    elif h & {'H310', 'H311'}:
        skin = _join(P('P302+P352'), P('P361+P364'), P('P310') if 'H310' in h else P('P312'))
    elif 'H317' in h:
        skin = _join(P('P302+P352'), P('P333+P313'), P('P362+P364'))
    elif 'H315' in h:
        skin = _join(P('P302+P352'), P('P332+P313'), P('P362+P364'))
    elif 'H312' in h:
        skin = _join(P('P302+P352'), P('P312'), P('P362+P364'))
    else:
        skin = P('P302+P352')
    if kind == 'gas' and 'H281' in h:   # soğutulmuş sıvılaştırılmış gaz — donma yanığı
        skin = _join(P('P336'), P('P315'))
    out.append({'route': 'Cilt' if L == 'TR' else 'Skin', 'text': skin})

    # Göz
    if h & {'H314', 'H318'}:
        eye = _join(P('P305+P351+P338'), P('P310'))
    elif 'H319' in h:
        eye = _join(P('P305+P351+P338'), P('P337+P313'))
    else:
        eye = P('P305+P351+P338')
    out.append({'route': 'Göz' if L == 'TR' else 'Eyes', 'text': eye})

    # Yutma (gazlarda uygulanmaz)
    if kind != 'gas':
        if 'H314' in h:
            ing = P('P301+P330+P331') + ' ' + P('P310')
        elif 'H304' in h:
            ing = _join(P('P301+P310'), P('P331'))
        elif h & {'H300', 'H301'}:
            ing = _join(P('P301+P310'), P('P330'))
        elif 'H302' in h:
            ing = _join(P('P301+P312'), P('P330'))
        else:
            ing = _join('YUTULDUĞUNDA:' if L == 'TR' else 'IF SWALLOWED:', P('P330'), P('P312'))
        out.append({'route': 'Yutma' if L == 'TR' else 'Ingestion', 'text': ing})

    # 4.1.2 ç) ilk yardım yapanlar için KKE
    if h & HAZARD_H_FOR_FIRST_AIDER:
        out.append({'route': 'İlk yardım yapanlar' if L == 'TR' else 'First aiders',
                    'text': ('İlk yardım müdahalesinde bulunan kişi uygun kişisel koruyucu ekipman '
                             'kullanmalıdır (bkz. Bölüm 8).' if L == 'TR' else
                             'Persons giving first aid should wear suitable personal protective '
                             'equipment (see Section 8).')})
    return out


# ── 6 — kaza sonucu yayılmaya karşı önlemler ───────────────────────────────────
_ENV_KEYS = ('kanalizasyon', 'su kaynak', 'su kanal', 'drenaj', 'toprağa', 'zemin suyu',
             'yüzey suyu', 'su ortamına', 'dere', 'göle', 'drains', 'watercourse', 'sewer')


def split_env_and_cleanup(sentences: List[str]):
    """H kodu cümlelerini 6.2 (çevresel) ve 6.3 (temizleme) olarak ayırır.
    Birden çok cümle içeren maddeler önce cümlelere bölünür (her cümle kendi alt başlığına)."""
    import re as _re
    env, clean = [], []
    for s in sentences or []:
        for part in _re.split(r'(?<=\.)\s+', s.strip()):
            part = part.strip()
            if not part:
                continue
            target = env if any(k in part.lower() for k in _ENV_KEYS) else clean
            if part not in target:
                target.append(part)
    return env, clean


def accidental_release(h_codes: List[str], form: str, hazard_sentences: List[str],
                       lang: str = 'TR') -> Dict[str, List[str]]:
    """{'6.1': [...], '6.2': [...], '6.3': [...]} — Ek-2 alt başlıklarına göre."""
    from app.services.sds_sentence_service import adapt_list_for_form
    h = {str(c)[:4] for c in h_codes}
    kind = _kind(form)
    flam = bool(h & FLAMMABLE_H)
    TR = lang == 'TR'
    hz = adapt_list_for_form(hazard_sentences, form)
    env_h, clean_h = split_env_and_cleanup(hz)

    s61 = [('Cilt, göz ve giysi ile teması önlemek için uygun kişisel koruyucu ekipman kullanın '
            '(bkz. Bölüm 8).') if TR else
           'Wear suitable personal protective equipment to prevent contact with skin, eyes and clothing (see Section 8).']
    if kind == 'solid':
        s61.append('Toz oluşumunu kontrol altında tutun; yeterli havalandırma sağlayın.' if TR else
                   'Control dust generation; ensure adequate ventilation.')
    elif kind == 'gas':
        s61.append('Alanı havalandırın; gaz dağılana kadar koruyucu ekipman olmadan girmeyin.' if TR else
                   'Ventilate the area; do not enter without protective equipment until the gas has dispersed.')
    else:
        s61.append('Yeterli havalandırma sağlayın.' if TR else 'Ensure adequate ventilation.')
    if flam:
        s61.append('Tüm tutuşturucu kaynakları uzaklaştırın.' if TR else 'Remove all sources of ignition.')
    s61.append('Büyük dökülme veya sızıntılarda tehlike alanını boşaltın ve acil durum ekibine haber verin.'
               if TR else 'For large spills or leaks, evacuate the danger area and alert emergency responders.')
    s61.append('Acil durum müdahale ekibi Bölüm 8\'de belirtilen koruyucu giysi ve ekipmanı kullanmalıdır'
               + ('; kendinden hava beslemeli solunum cihazı kullanın.' if (kind == 'gas' or h & {'H330', 'H331'}) else '.')
               if TR else
               'Emergency responders should wear the protective clothing and equipment specified in Section 8'
               + ('; use self-contained breathing apparatus.' if (kind == 'gas' or h & {'H330', 'H331'}) else '.'))

    if kind == 'gas':
        _default62 = ('Gazın kanalizasyon, bodrum ve çukur gibi kapalı alanlara girmesini ve birikmesini önleyin.'
                      if TR else 'Prevent gas from entering and accumulating in sewers, basements and pits.')
    else:
        _default62 = ('Ürünün kanalizasyona, yüzey ve yer altı sularına ulaşmasını önleyin.' if TR else
                      'Prevent the product from entering drains, surface water and groundwater.')
    s62 = list(env_h) or [_default62]

    if kind == 'solid':
        base63 = ['Dökülen ürünün yayılmasını önleyin; tahliye deliklerini kapatın.' if TR else
                  'Prevent the spilled product from spreading; cover drains.',
                  'Dökülen ürünü toz kaldırmadan süpürerek veya vakumla toplayın.' if TR else
                  'Sweep or vacuum up spilled product without generating dust.',
                  'Uygun ve etiketli atık kaplarına koyun.' if TR else 'Place in suitable, labelled waste containers.',
                  'Basınçlı hava ile temizlik yapmayın.' if TR else 'Do not use compressed air for cleaning.']
    elif kind == 'gas':
        base63 = ['Güvenli ise sızıntı kaynağını kapatın (vana/valf).' if TR else
                  'Stop the leak at source if safe to do so (close valve).',
                  'Gaz dağılana kadar alanı havalandırın.' if TR else 'Ventilate the area until the gas has dispersed.']
    else:
        base63 = ['Dökülmeyi set veya bariyer ile sınırlayın; tahliye deliklerini ve kanalizasyon girişlerini kapatın.'
                  if TR else 'Contain the spill with dikes or barriers; cover drains and sewer inlets.',
                  'Emici malzeme (kum, vermikülit, diatomit) ile toplayın.' if TR else
                  'Absorb with inert absorbent material (sand, vermiculite, diatomaceous earth).',
                  'Uygun ve etiketli atık kaplarına koyun.' if TR else 'Place in suitable, labelled waste containers.']
    if flam:
        base63.append('Kıvılcım çıkarmayan alet ve ekipman kullanın.' if TR else 'Use non-sparking tools and equipment.')
    # H koduna özgü temizleme cümleleri — genel yöntemi tekrarlayanlar atlanır
    # 6.1'de zaten yer alan (havalandırma, toz, KKE, tutuşturucu kaynak) ve genel temizleme
    # yöntemini tekrarlayan cümleler 6.3'e eklenmez
    _generic = ('absorban', 'süpürerek', 'vakumla', 'sızıntıyı durdurun', 'absorbent', 'sweep',
                'havalandırma', 'havalandırın', 'toz oluşum', 'kke', 'kişisel koruyucu',
                'tutuşma kaynak', 'tutuşturucu', 'ventilat', 'ignition', 'protective equipment')
    extra = [s for s in clean_h if not any(g in s.lower() for g in _generic)]
    s63 = base63 + [s for s in extra if s not in base63]
    return {'6.1': s61, '6.2': s62, '6.3': s63}


# ── 7.1.2 — genel mesleki hijyen ───────────────────────────────────────────────
def hygiene(lang: str = 'TR') -> List[str]:
    L = lang if lang in ('TR', 'EN') else 'EN'
    return [
        _p('P270', L),
        _p('P264', L),
        ('Yemek alanlarına girmeden önce kirlenmiş giysi ve koruyucu ekipmanı çıkarın.' if L == 'TR' else
         'Remove contaminated clothing and protective equipment before entering eating areas.'),
    ]
