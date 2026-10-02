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
        'P501':      ('İçeriği/kabı … bertaraf edin',
                      'İçeriği/kabı Atık Yönetimi Yönetmeliği ve yerel mevzuata uygun olarak bertaraf edin'),
    }
    fills_en = {
        'P302+P352': ('water/…', 'water'),
        'P264':      ('Wash … thoroughly', 'Wash hands thoroughly'),
        'P501':      ('Dispose of contents/container to …',
                      'Dispose of contents/container in accordance with local/national regulations'),
    }
    pair = (fills_tr if lang == 'TR' else fills_en).get(code)
    if pair and pair[0] in t:
        t = t.replace(pair[0], pair[1])
    return t.replace('…', '').replace('  ', ' ').strip()


# P280 — SEA Ek-4: "İmalatçı/tedarikçi uygun ekipman türünü belirtecektir." Ekipman, SEA Etiketleme
# Rehberi 7.3'teki her tehlike sınıfı notuna göre seçilir:
#   H315/H317: eldiven · H310–H312: eldiven/giysi · H314: eldiven/giysi/göz/yüz · H318/H319: göz/yüz ·
#   fiziksel tehlikeler (alevlenir, oksitleyici, kendiliğinden tepkimeye giren…): eldiven ve göz/yüz.
# CMR vb. rehberin ekipman belirtmediği sınıflarda resmî metnin tamamı kullanılır.
_P280_PHYS = {'H224', 'H225', 'H226', 'H228', 'H240', 'H241', 'H242', 'H250', 'H251', 'H252',
              'H260', 'H261', 'H270', 'H271', 'H272'}
_P280_GLOVES = {'H315', 'H317', 'H310', 'H311', 'H312', 'H314'} | _P280_PHYS
_P280_CLOTH = {'H310', 'H311', 'H312', 'H314'}
_P280_EYE = {'H314', 'H318', 'H319'} | _P280_PHYS
_P280_FULL = {'H200', 'H201', 'H202', 'H203', 'H204', 'H205', 'H340', 'H341', 'H350', 'H351',
              'H360', 'H361', 'H362'}


def p280_text(h_codes, lang: str = 'TR') -> str:
    """P280 metni — ürünün tehlike sınıflarına göre belirtilmiş ekipman (SEA Ek-4 / Etiketleme Rehberi 7.3)."""
    full = _p('P280', lang)
    h = {str(x).replace('*', '').strip()[:4] for x in (h_codes or [])}
    if h & _P280_FULL or not (h & (_P280_GLOVES | _P280_EYE)):
        return full
    TR = lang == 'TR'
    parts = []
    if h & _P280_GLOVES:
        parts.append('koruyucu eldiven' if TR else 'protective gloves')
    if h & _P280_CLOTH:
        parts.append('koruyucu kıyafet' if TR else 'protective clothing')
    if h & _P280_EYE:
        parts += (['göz koruyucu', 'yüz koruyucu'] if TR else ['eye protection', 'face protection'])
    if TR:
        s = '/'.join(parts)
        return s[0].upper() + s[1:] + ' kullanın.'
    return 'Wear ' + '/'.join(parts) + '.'


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
                    'text': ('İlk yardım müdahalesini yapanlar için kişisel koruyucu ekipman: '
                             'Bölüm 8\'e bakınız.' if L == 'TR' else
                             'Personal protective equipment for first-aid responders: see Section 8.')})
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
    h = {str(c)[:4] for c in h_codes}
    kind = _kind(form)
    flam = bool(h & FLAMMABLE_H)
    TR = lang == 'TR'

    # Metinler KKDİK Ek-2'nin (EN: 2020/878 Ek-II) kendi ifadeleridir — 6.1.1 a/b/c, 6.1.2,
    # 6.2, 6.3.1, 6.3.2, 6.3.3. Ek-2'de karşılığı olmayan cümle eklenmez.
    sfx_tr = ' (Güvenlik Bilgi Formunun 8 inci bölümünde belirtilen kişisel koruyucu ekipman dâhil).'
    s61 = [('Cilt, göz ve kişisel giysideki bulaşmaları önlemek için uygun koruyucu ekipman giyin' + sfx_tr)
           if TR else
           ('Wear suitable protective equipment (including personal protective equipment referred to under '
            'Section 8) to prevent any contamination of skin, eyes and personal clothing.')]
    if flam:
        s61.append('Tutuşturucu kaynakları uzaklaştırın.' if TR else 'Remove ignition sources.')
    s61.append('Yeterli havalandırmayı sağlayın.' if TR else 'Provide sufficient ventilation.')
    if kind == 'solid':
        s61.append('Tozu kontrol altında tutun.' if TR else 'Control dust.')
    s61.append('Gerektiğinde tehlike alanını boşaltın veya uzmana danışın.' if TR else
               'Where necessary, evacuate the danger area or consult an expert.')
    s61.append('Acil durumda müdahale eden kişiler için kişisel koruyucu giysi ve uygun kumaş: '
               'Bölüm 8\'e bakınız.' if TR else
               'For emergency responders — personal protective clothing and suitable fabric: see Section 8.')
    if kind == 'gas' or h & {'H330', 'H331'}:
        s61.append('Kendiliğinden depolu solunum cihazı kullanın.' if TR else 'Use self-contained breathing apparatus.')

    # 6.2 — Ek-2 örneği; sucul tehlikede resmî P273
    s62 = ['Kanallardan, yer üstü ve yer altı sularından uzak tutun.' if TR else
           'Keep away from drains, surface and ground water.']
    if h & {'H400', 'H410', 'H411', 'H412', 'H413'}:
        s62.append(_p('P273', 'TR' if TR else 'EN'))

    # 6.3.1 kontrol altına alma / 6.3.2 temizleme / 6.3.3 uygunsuz teknikler
    if kind == 'solid':
        base63 = ['Tahliye deliklerini kapatın.' if TR else 'Cover drains.',
                  'Vakumlama veya toz oluşturmayan temizlik teknikleriyle toplayın.' if TR else
                  'Collect using vacuuming or cleaning techniques that do not generate dust.',
                  'Asla basınçlı hava kullanmayın.' if TR else 'Never use compressed air.']
    elif kind == 'gas':
        base63 = ['Kapatma prosedürlerini uygulayın.' if TR else 'Apply capping procedures.']
    else:
        base63 = ['Set oluşturun, tahliye deliklerini kapatın.' if TR else 'Use bunding; cover drains.',
                  'Emici maddeler ile toplayın.' if TR else 'Collect with absorbent materials.']
    if flam:
        base63.append('Kıvılcım çıkarmayan aletler ve ekipman kullanın.' if TR else
                      'Use non-sparking tools and equipment.')
    # Yalnızca Ek-2 ifadeleri — H koduna özgü serbest cümleler (sistemin kendi metinleri)
    # eklenmez (kullanıcı talimatı: "yönetmelikte ne yazıyorsa o"). hazard_sentences parametresi
    # geriye dönük uyum için korunur.
    return {'6.1': s61, '6.2': s62, '6.3': base63}


# ── 7.1 / 7.2 — ürünün kendi önlem ifadelerinden (SEA Ek-4 resmî metin) ──────────
# KKE ifadeleri (P280–P285) Bölüm 8'de; bertaraf (P501–P503) Bölüm 13'te yer alır.
_PPE_P = {'P280', 'P281', 'P282', 'P283', 'P284', 'P285'}
_INHAL_SELECT_TR = 'Tozunu/dumanını/gazını/sisini/buharını/spreyini'
_INHAL_SELECT_EN = 'dust/fume/gas/mist/vapours/spray'


def _select_inhal(text: str, form: str, lang: str) -> str:
    """P260/P261 vb.: tedarikçinin seçmesi gereken kısmı fiziksel hale göre seç (SEA Etiketleme Rehberi)."""
    f = (form or '').lower()
    if lang == 'TR':
        sel = {'solid': 'Tozunu', 'powder': 'Tozunu', 'gas': 'Gazını', 'aerosol': 'Spreyini'}.get(f, 'Buharını/sisini')
        return text.replace(_INHAL_SELECT_TR, sel)
    sel = {'solid': 'dust', 'powder': 'dust', 'gas': 'gas', 'aerosol': 'spray'}.get(f, 'vapours/mist')
    return text.replace(_INHAL_SELECT_EN, sel)


def _p_list(codes: List[str], pred, form: str, lang: str) -> List[str]:
    L = lang if lang in ('TR', 'EN') else 'EN'
    out = []
    for c in sorted({str(x).strip() for x in codes if x}, key=lambda s: s.split('+')[0]):
        if pred(c):
            t = _select_inhal(_p(c, L), form, L)
            if t and t not in out:
                out.append(t)
    return out


def handling_p(p_codes: List[str], form: str, lang: str = 'TR') -> List[str]:
    """7.1 — önleme ifadeleri (P2xx), KKE ifadeleri hariç."""
    return _p_list(p_codes, lambda c: c.startswith('P2') and c.split('+')[0] not in _PPE_P, form, lang)


def storage_p(p_codes: List[str], form: str, lang: str = 'TR') -> List[str]:
    """7.2 — depolama ifadeleri (P4xx)."""
    return _p_list(p_codes, lambda c: c.startswith('P4'), form, lang)


# ── 7.1.2 — genel mesleki hijyen ───────────────────────────────────────────────
def hygiene(lang: str = 'TR') -> List[str]:
    """KKDİK Ek-2 7.1.2 a/b/c (EN: 2020/878 Ek-II 7.1) ifadeleri."""
    if lang == 'TR':
        return ['Çalışma alanlarında yiyip içmeyin ve sigara içmeyin.',
                'Kullanımdan sonra ellerinizi yıkayın.',
                'Yemek alanlarına girmeden önce kontamine olmuş giysi ve koruyucu ekipmanı çıkarın.']
    return ['Do not eat, drink and smoke in work areas.',
            'Wash hands after use.',
            'Remove contaminated clothing and protective equipment before entering eating areas.']
