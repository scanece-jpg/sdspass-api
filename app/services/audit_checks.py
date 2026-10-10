"""
GBF denetimi — kod kontrolleri (kesin kurallar).

data/sds_audit_checklist.json'daki yontem == 'kod' sorularını GBF PDF metni üzerinde çalıştırır.
Her kontrol: ctx → (karar, açıklama). Karar: 'uygun' | 'eksik' | 'kdu' (KDU baksın) | 'kontrol_yok'.
Metinden kesin karar verilemeyen durumlar 'kdu' döner; henüz yazılmamış kontroller 'kontrol_yok'.

ctx: {'pages': [sayfa metinleri], 'text': tüm metin, 'secs': {bölüm: metin}, 'facts': set}
"""
import os
import re
import unicodedata
from typing import Callable, Dict, List, Tuple

from app.services.audit_jev import split_sections, derive_facts

_EK2 = os.path.join(os.path.dirname(__file__), '..', '..', 'sds-knowledge', 'tr', 'kkdik-ekleri', 'kkdik-ek-02.md')

H_RE = re.compile(r'\b(H\d{3})(?:[A-Za-z]{1,2})?\b')
EUH_RE = re.compile(r'\bEUH\d{3}\b')
P_RE = re.compile(r'\bP\d{3}(?:\s*\+\s*P\d{3})*')
CAS_RE = re.compile(r'(?<![\d-])(\d{2,7}-\d{2}-\d)(?![\d-])')
EC_RE = re.compile(r'(?<![\d-])(\d{3}-\d{3}-\d)(?![\d-])')
CONC_RE = re.compile(r'(?:[<>≤≥]=?\s*)?\d+(?:[.,]\d+)?\s*(?:-|–)?\s*(?:[<>≤≥]=?\s*)?\d*(?:[.,]\d+)?\s*%|%\s*[<>≤≥]?\s*\d')

# "Tehlike" gerektiren H kodları (SEA Ek-1 etiket tabloları); diğerleri "Dikkat"
DANGER_H = {'H200', 'H201', 'H202', 'H203', 'H205', 'H220', 'H222', 'H224', 'H225', 'H228', 'H230',
            'H240', 'H241', 'H242', 'H250', 'H251', 'H260', 'H261', 'H270', 'H271', 'H272', 'H300', 'H301',
            'H304', 'H310', 'H311', 'H314', 'H318', 'H330', 'H331', 'H334', 'H340', 'H350', 'H360', 'H370',
            'H372'}
WARNING_H = {'H204', 'H221', 'H223', 'H226', 'H252', 'H280', 'H281', 'H290', 'H302', 'H312', 'H315', 'H317',
             'H319', 'H332', 'H335', 'H336', 'H341', 'H351', 'H361', 'H371', 'H373', 'H400', 'H410'}
# Not: H225/H228/H242/H272 kategoriye göre Dikkat da olabilir — yalnız "Tehlike hiç yoksa" kontrol edilir
# SEA Ek-1 Tablo 4.1.4 / 3.7.3: uyarı kelimesi kullanılmayan sınıflar
NO_SIGNAL_H = {'H411', 'H412', 'H413', 'H362'}
# SEA Md.20(3)(b) (CLP 18(3)(b)): etikette adı yazılacak bileşen gerektiren karışım sınıfları (sağlık tehlikeleri)
LABEL_COMP_H = {'H300', 'H301', 'H302', 'H310', 'H311', 'H312', 'H330', 'H331', 'H332', 'H314', 'H318',
                'H340', 'H341', 'H350', 'H351', 'H360', 'H361', 'H362', 'H334', 'H317', 'H370', 'H371',
                'H372', 'H373', 'H335', 'H336', 'H304'}
# "Tehlike İfadeleri", "Tehlike Kodları" gibi başlıklar uyarı kelimesi sayılmaz
_SIG_HEAD = re.compile(r'(?i)tehlike\s+(?:ifade|İfade|i̇fade)\w*|tehlike\s+kod\w*|tehlike\s+sınıf\w*|'
                       r'tehlike\s+işaret\w*|tehlike\s+bilgi\w*|tehlike\s+beyan\w*|tehlike\s+belirten\w*')


def _signal_text(s22: str) -> str:
    return _SIG_HEAD.sub(' ', s22 or '')


def _cas_ok(cas: str) -> bool:
    d = cas.replace('-', '')
    return sum(int(x) * (i + 1) for i, x in enumerate(reversed(d[:-1]))) % 10 == int(d[-1])


def _norm(s: str) -> str:
    s = unicodedata.normalize('NFC', s).replace('İ', 'i').replace('I', 'i').lower().replace('ı', 'i')
    s = re.sub(r'[^\wçğöşü/ ]', ' ', s)
    s = re.sub(r'\s*/\s*', '/', s)
    return re.sub(r'\s+', ' ', s).strip()


def _sub(sec_text: str, num: str, nxt: str) -> str:
    """Bölüm metninde 'num' alt başlığından 'nxt'e kadar (örn. 2.2 → 2.3)."""
    a = re.search(rf'(?<![\d.]){re.escape(num)}\b', sec_text or '')
    if not a:
        return ''
    b = re.search(rf'(?<![\d.]){re.escape(nxt)}\b', sec_text[a.end():]) if nxt else None
    return sec_text[a.start():a.end() + b.start()] if b else sec_text[a.start():]


def _h(text: str) -> set:
    return set(H_RE.findall(text or ''))


# ── Başlıklar (Ek-2 Bölüm B) ────────────────────────────────────────────────────
def ek2_headings() -> List[Tuple[str, str]]:
    txt = open(_EK2, encoding='utf-8').read()
    part_b = txt[txt.index('**BÖLÜM B**'):]
    heads, sec = [], None
    for line in part_b.splitlines():
        line = line.strip().lstrip('- ').strip()
        m = re.match(r'^BÖLÜM\s+(\d+)\s*[:.]\s*(.+)$', line)
        if m:
            sec = int(m.group(1)); heads.append((f'{sec}', m.group(2).strip())); continue
        m = re.match(r'^(\d+)\.(\d+)\.?\s+(.+)$', line)
        if m and sec is not None:
            heads.append((f'{sec}.{m.group(2)}', m.group(3).strip()))
    return heads


def check_headings(text: str) -> List[Tuple[str, str, str, str]]:
    """[(numara, Ek-2 başlığı, 'tam'|'farklı'|'yok', GBF'de görülen)]"""
    body = _norm(text)
    pos, rows = 0, []
    for num, title in ek2_headings():
        key = (f'bölüm {num} ' if '.' not in num else f'{num.replace(".", " ")} ') + _norm(title)
        i = body.find(_norm(key), pos)
        if i >= 0:
            rows.append((num, title, 'tam', '')); pos = i; continue
        pat = rf'bölüm {num} (.{{0,90}})' if '.' not in num else rf'(?<!\d ){num.replace(".", " ")} (.{{0,90}})'
        m = re.search(pat, body[pos:])
        rows.append((num, title, 'farklı' if m else 'yok', m.group(1)[:90] if m else ''))
    st = {r[0]: r[2] for r in rows}
    if 'tam' in (st.get('3.1'), st.get('3.2')):   # Ek-2 B: yalnızca 3.1 veya 3.2
        rows = [(n, t, 'tam' if n in ('3.1', '3.2') else s, x) for n, t, s, x in rows]
    return rows


# ── Kontroller ──────────────────────────────────────────────────────────────────
def c_basliklar(ctx):
    rows = check_headings(ctx['text'])
    bad = [r for r in rows if r[2] != 'tam']
    if not bad:
        return 'uygun', f'Ek-2 Bölüm B\'deki {len(rows)} başlığın hepsi birebir.'
    det = '; '.join(f'{n} "{t}" ' + ('yok' if s == 'yok' else f'farklı yazılmış ("{x[:50]}…")') for n, t, s, x in bad)
    return ('eksik' if any(r[2] == 'yok' for r in bad) else 'kdu'), det


def c_tarih(ctx):
    p1 = ctx['pages'][0] if ctx['pages'] else ''
    return ('uygun', 'İlk sayfada tarih var.') if re.search(r'\b\d{1,2}[./]\d{1,2}[./]\d{4}\b', p1) else \
           ('eksik', 'İlk sayfada tarih bulunamadı.')


def c_surum(ctx):
    """KKDİK Ek-2 0.2.5: revizyonda ilk sayfada sürüm / revizyon numarası VE hangi versiyonun değiştirildiği
    (değiştirme tarihi veya yerine geçtiği versiyon)."""
    p1 = ctx['pages'][0] if ctx['pages'] else ''
    if not re.search(r'(?i)\b(rev(?:izyon)?\.?(?:\s*no)?|sürüm|versiyon|version|düzenleme(?:\s+olduğu)?)\s*[:.]?\s*\d', p1):
        return 'eksik', 'İlk sayfada sürüm/revizyon numarası bulunamadı.'
    sup = re.search(r'(?i)yerine geçtiği|yerine geçer|değiştirdiği|değiştirme tarihi|önceki (?:versiyon|sürüm)|'
                    r'supersed|replaces|previous version', p1)
    if sup or len(set(re.findall(r'\b\d{1,2}[./]\d{1,2}[./]\d{4}\b', p1))) >= 2:
        return 'uygun', 'İlk sayfada sürüm/revizyon numarası ve değiştirilen versiyon bilgisi var.'
    return 'eksik', ('İlk sayfada sürüm numarası var ama hangi versiyonun değiştirildiği (değiştirme tarihi / '
                     'yerine geçtiği versiyon) yok (KKDİK Ek-2 0.2.5).')


def c_sayfa(ctx):
    n = len(ctx['pages'])
    miss = []
    for i, p in enumerate(ctx['pages'], 1):
        ok = re.search(rf'(?<!\d){i}\s*/\s*{n}(?!\d)', p) or re.search(rf'(?i)\b{i}\s*(?:of|/)\s*{n}\b', p) \
            or re.search(r'(?i)devam[ıi] (?:bir )?sonraki sayfada|güvenlik bilgi formunun sonu', p)
        if not ok:
            miss.append(i)
    return ('uygun', f'{n} sayfanın hepsinde "sayfa x/{n}" var.') if not miss else \
           ('eksik', f'Toplam sayfa sayısı veya devam göstergesi olmayan sayfalar: {miss[:10]}')


def c_bos_alt(ctx):
    """Bölüm B alt başlıklarından sonra gelen metin boş mu (bir sonraki başlığa kadar < 3 harf)."""
    body = ctx['text']
    heads = [h for h in ek2_headings() if '.' in h[0]]
    empty = []
    for i, (num, _t) in enumerate(heads):
        nxt = heads[i + 1][0] if i + 1 < len(heads) and heads[i + 1][0].split('.')[0] == num.split('.')[0] else None
        sec = ctx['secs'].get(num.split('.')[0], '')
        part = _sub(sec, num, nxt)
        if not part:
            continue
        content = re.sub(rf'^{re.escape(num)}\s*', '', part)
        content = re.sub(re.escape(_t), '', content, flags=re.I)
        if len(re.findall(r'[A-Za-zÇĞİÖŞÜçğıöşü0-9]', content)) < 1:   # "Ambalaj grubu: I" boş değildir
            empty.append(num)
    return ('uygun', 'Boş alt bölüm bulunmadı.') if not empty else ('eksik', f'Boş görünen alt bölümler: {empty}')


def c_dil(ctx):
    t = ctx['text']
    tr = len(re.findall(r'[çğışöüÇĞİŞÖÜ]', t))
    return ('uygun', 'Metin Türkçe.') if tr > 50 else ('eksik', 'Metin Türkçe görünmüyor.')


_YASAK = [r'zararlı olabilir', r'sağlığa etkisi yok', r'çoğu kullanım koşullarında güvenli', r'\bzararsızdır\b',
          r'toksik değildir', r'kirletici değildir', r'\bekolojiktir\b']


def c_yasak(ctx):
    hits = []
    for pat in _YASAK:
        for m in re.finditer(pat, ctx['text'], re.I):
            hits.append(ctx['text'][max(0, m.start() - 40):m.end() + 20].replace('\n', ' '))
    return ('uygun', 'Yasak ifade bulunmadı.') if not hits else \
           ('eksik', 'Ek-2 0.2.4 / SEA Md.27(4) ifadeleri: ' + ' | '.join(hits[:3]))


def c_eposta(ctx):
    return ('uygun', 'Bölüm 1\'de e-posta var.') if re.search(r'[\w.+-]+@[\w-]+\.[\w.-]+', ctx['secs'].get('1', '')) \
        else ('eksik', 'Bölüm 1\'de e-posta adresi bulunamadı.')


def c_zehir(ctx):
    s1 = ctx['secs'].get('1', '')
    return ('uygun', 'UZEM 114 var.') if re.search(r'(?<!\d)114(?!\d)', s1) else \
           ('eksik', 'Bölüm 1.4\'te Ulusal Zehir Danışma Merkezi (114) numarası yok.')


def c_h_atif(ctx):
    s2 = ctx['secs'].get('2', '')
    s16 = ctx['secs'].get('16', '')
    codes = _h(s2)
    missing = sorted(c for c in codes if c not in s16 and not re.search(rf'{c}\s*[:\-–]?\s*[A-Za-zÇĞİÖŞÜçğıöşü]{{4}}', s2))
    return ('uygun', 'H ifadeleri tam metinli veya 16. bölümde.') if not missing else \
           ('eksik', f'Tam metni ne 2. ne 16. bölümde olan H kodları: {missing}')


def c_uyari_tek(ctx):
    s22 = _signal_text(_sub(ctx['secs'].get('2', ''), '2.2', '2.3'))
    both = re.search(r'\bTehlike\b', s22) and re.search(r'\bDikkat\b', s22)
    return ('eksik', '2.2\'de hem "Tehlike" hem "Dikkat" geçiyor.') if both else ('uygun', 'Tek uyarı kelimesi.')


def c_22_h(ctx):
    s22 = _sub(ctx['secs'].get('2', ''), '2.2', '2.3')
    return ('uygun', f'2.2\'de H ifadeleri: {sorted(_h(s22))}') if _h(s22) else ('eksik', '2.2\'de H ifadesi yok.')


def c_22_p(ctx):
    s22 = _sub(ctx['secs'].get('2', ''), '2.2', '2.3')
    return ('uygun', '2.2\'de P ifadeleri var.') if P_RE.search(s22) else ('eksik', '2.2\'de P ifadesi yok.')


def c_p_sayi(ctx):
    s22 = _sub(ctx['secs'].get('2', ''), '2.2', '2.3')
    ps = list(dict.fromkeys(re.sub(r'\s+', '', p) for p in P_RE.findall(s22)))
    return ('uygun', f'{len(ps)} önlem ifadesi.') if len(ps) <= 6 else \
           ('kdu', f'2.2\'de {len(ps)} önlem ifadesi (SEA Md.30(3): zarar gerektirmedikçe en fazla 6).')


def c_bilesen(ctx):
    s2 = ctx['secs'].get('2', '')
    if not ({h[:4] for h in _h(s2)} & LABEL_COMP_H):
        return 'uygun', ('Etikette bileşen adı gerektiren sağlık sınıflandırması yok (SEA Md.20(3)(b): akut '
                         'toksisite, aşındırıcılık/ciddi göz hasarı, CMR, hassaslaştırma, BHOT, aspirasyon).')
    return ('uygun', 'Etikette belirtilecek zararlı bileşenler yazılmış.') if re.search(
        r'(?i)zararlı bileşen|içerir\s*:|tehlikeli bileşen', s2) else \
           ('eksik', '2.2\'de "etikette belirtilmesi zorunlu zararlı bileşenler" bulunamadı (SEA Md.20(3)(b)).')


def c_22_tutarlilik(ctx):
    s2 = ctx['secs'].get('2', '')
    s21, s22 = _sub(s2, '2.1', '2.2'), _sub(s2, '2.2', '2.3')
    notes = []
    h21, h22 = _h(s21), _h(s22)
    s22 = _signal_text(s22)
    if h22 - h21 and h21:
        notes.append(f'2.2\'de olup 2.1\'de olmayan H kodları: {sorted(h22 - h21)}')
    # SEA Md.29: H410 varken H400 tekrar sayılır; H411/H412/H413 ile H400 ayrı sınıflar → etikette ikisi de olur
    if 'H400' in h21 and h22 and 'H400' not in h22 and 'H410' not in h22:
        notes.append('2.1\'de Sucul Akut 1 (H400) var ama etikette (2.2) H400 yok — yalnız H410 varken çıkarılabilir '
                     '(SEA Md.29)')
    if (h21 | h22) & DANGER_H and not re.search(r'\bTehlike\b', s22):
        notes.append('"Tehlike" gerektiren sınıflandırma var ama 2.2\'de "Tehlike" yok')
    if not ((h21 | h22) & DANGER_H) and (h21 | h22) & WARNING_H and not re.search(r'\bDikkat\b', s22):
        notes.append('"Dikkat" gerektiren sınıflandırma var ama 2.2\'de "Dikkat" yok')
    _all = {h[:4] for h in (h21 | h22)}
    if _all and _all <= NO_SIGNAL_H and re.search(r'\b(?:Dikkat|Tehlike)\b', s22):
        notes.append(f'Yalnız {sorted(_all)} var — uyarı kelimesi kullanılmaz (SEA Ek-1 Tablo 4.1.4 / 3.7.3) '
                     f'ama 2.2\'de uyarı kelimesi basılmış')
    return ('uygun', 'Etiket unsurları 2.1 ile tutarlı.') if not notes else ('eksik', '; '.join(notes))


def _rows3(ctx):
    """Bölüm 3'teki geçerli CAS numaraları (sıra korunur)."""
    s3 = ctx['secs'].get('3', '')
    return [c for c in dict.fromkeys(CAS_RE.findall(s3)) if _cas_ok(c)], s3


_NOTHING_TO_LIST = re.compile(r'(?i)(belirtilmesi|listelenmesi) gereken (bir )?madde bulunmamaktad|'
                              r'no substances that need to be listed')


def c_32_liste(ctx):
    cas, s3 = _rows3(ctx)
    if not cas and _NOTHING_TO_LIST.search(s3):
        return 'uygun', 'Bölüm 3: Ek-2 3.2.1/3.2.2 uyarınca listelenmesi gereken madde olmadığı belirtilmiş.'
    return ('uygun', f'Bölüm 3\'te {len(cas)} madde CAS ile listelenmiş.') if cas else \
           ('eksik', 'Bölüm 3\'te CAS numaralı madde bulunamadı.')


def c_32_konsantrasyon(ctx):
    cas, s3 = _rows3(ctx)
    if not cas and _NOTHING_TO_LIST.search(s3):
        return 'uygun', 'Listelenmesi gereken madde yok.'
    n = len(CONC_RE.findall(s3))
    return ('uygun', f'{n} konsantrasyon değeri / {len(cas)} madde.') if cas and n >= len(cas) else \
           ('kdu', f'Konsantrasyon değeri sayısı ({n}) madde sayısından ({len(cas)}) az görünüyor.')


def c_32_sinif(ctx):
    cas, s3 = _rows3(ctx)
    if not cas and _NOTHING_TO_LIST.search(s3):
        return 'uygun', 'Listelenmesi gereken madde yok.'
    n = len(re.findall(r'\bH\d{3}|sınıflandırılmamış|sınıflandırma kriterlerini karşılamamaktadır|not classified',
                       s3, re.I))
    return ('uygun', 'Maddelerin sınıflandırması verilmiş.') if cas and n >= 1 else \
           ('eksik', 'Bölüm 3\'te madde sınıflandırması (H kodu) bulunamadı.')


def c_32_ec(ctx):
    cas, s3 = _rows3(ctx)
    if not cas and _NOTHING_TO_LIST.search(s3):
        return 'uygun', 'Listelenmesi gereken madde yok.'
    ecs = set(EC_RE.findall(s3))
    return ('uygun', f'{len(ecs)} EC numarası.') if len(ecs) >= max(1, len(cas) - 1) else \
           ('kdu', f'EC numarası sayısı ({len(ecs)}) madde sayısından ({len(cas)}) az — mevcutsa verilmeli.')


def c_32_svhc(ctx):
    from app.services.svhc_service import check_svhc_single
    cas, _ = _rows3(ctx)
    hits = [c for c in cas if check_svhc_single(c)]
    return ('uygun', 'Bölüm 3\'te Aday Liste maddesi yok.' if not hits else f'Aday Liste maddesi listelenmiş: {hits}')


def c_oel(ctx):
    from app.services.substance_lookup import get_oel
    cas, _ = _rows3(ctx)
    s8 = ctx['secs'].get('8', '')
    need = [c for c in cas if get_oel(c)]
    miss = [c for c in need if c not in s8]
    if not need:
        return 'uygun', 'TR sınır değeri olan bileşen yok.'
    return ('uygun', f'TR sınır değerli bileşenler 8.1\'de: {need}') if not miss else \
           ('eksik', f'TR sınır değeri olduğu halde 8.1\'de bulunamayan bileşenler (CAS): {miss}')


_PROPS = [('a) görünüm', r'görünüm|fiziksel (?:hal|durum)|görünüş'), ('b) koku', r'\bkoku\b(?!\s*eşi)|kokusuz'),
          ('c) koku eşiği', r'koku eşi'), ('ç) pH', r'\bph\b'), ('d) erime/donma', r'erime|donma'),
          ('e) kaynama', r'kaynama'), ('f) parlama noktası', r'parlama'), ('g) buharlaşma hızı', r'buharlaşma'),
          ('ğ) alevlenirlik', r'alevlenirlik|tutuşabilirlik'),
          ('h) patlama limitleri', r'patlay[ıi]c[ıi] limit|patlama limit|alevlenirlik limit|üst/alt|alt patlay|üst patlay|infilak sınır'),
          ('ı) buhar basıncı', r'buhar bas'), ('i) buhar yoğunluğu', r'buhar yoğ|bağıl buhar|nispi buhar'),
          ('j) bağıl yoğunluk', r'bağıl yoğ|yoğunluk'), ('k) çözünürlük', r'çözünür'),
          ('l) dağılım katsayısı', r'dağılım katsay|oktanol'),
          ('m) kendiliğinden tutuşma', r'kendiliğinden tutuş|oto.?tutuş'),
          ('n) bozunma sıcaklığı', r'bozunma|dekompozisyon'), ('o) akışkanlık', r'akışkanlık|viskozite'),
          ('ö) patlayıcı özellikler', r'patlayıcı özellik'), ('p) oksitleyici özellikler', r'oksitleyici özellik|oksitleyici olarak')]


def c_91(ctx):
    s9 = ctx['secs'].get('9', '').lower()
    miss = [n for n, pat in _PROPS if not re.search(pat, s9, re.I)]
    return ('uygun', '9.1\'deki 20 özelliğin hepsi var.') if not miss else ('eksik', f'9.1\'de bulunamayan özellikler: {miss}')


_CLASSES = [('a) akut toksisite', r'akut toksisite|akut toksik'), ('b) cilt aşınması/tahrişi', r'cilt aşın|deri korozyon|cilt tahriş|deri tahriş|ciltte aşın'),
            ('c) göz hasarı/tahrişi', r'göz hasar|göz tahriş'), ('ç) hassaslaşma', r'hassaslaş|duyarlılaş|hassasiyet'),
            ('d) mutajenite', r'mutajen|mütajen|mütagen|mutagen|eşey hücre|germ hücre'), ('e) kanserojenite', r'kanserojen'),
            ('f) üreme toksisitesi', r'üreme|reprodüktif'), ('g) BHOT tek', r'tek maruz|tek bir maruz'),
            ('ğ) BHOT tekrarlı', r'tekrarl[ıi] maruz|tekrarlanan maruz'), ('h) aspirasyon', r'aspirasyon')]


def c_111_siniflar(ctx):
    s11 = ctx['secs'].get('11', '').lower()
    miss = [n for n, pat in _CLASSES if not re.search(pat, s11, re.I)]
    return ('uygun', '11.1\'de 10 zararlılık sınıfının hepsi var.') if not miss else \
           ('eksik', f'11. bölümde bulunamayan sınıflar: {miss}')


def c_111_ifade(ctx):
    s11 = ctx['secs'].get('11', '')
    ok = re.search(r'(?i)sınıflandırma kriterlerini karşılamamaktadır|bilgi bulunmamaktadır|veri (?:yok|mevcut değil)|'
                   r'belirlenmemiştir|test edilmemiştir', s11)
    return ('uygun', 'Sınıflandırılmayan sınıflar için gerekçe var.') if ok else \
           ('eksik', 'Sınıflandırılmayan sınıflar için gerekçe/standart ifade bulunamadı (Ek-2 A 11.1.1).')


def c_un(ctx):
    s14 = ctx['secs'].get('14', '')
    if re.search(r'(?i)belirlenmemiştir|not determined', s14):
        return 'kdu', ('14.1\'de UN numarası "belirlenmemiştir" — KKDİK Ek-2 Bölüm 14 buna izin verir; gönderen '
                       'sınıflandırmayı belirlemeli (ADR 1.4.2.1). KDU kontrol etmeli.')
    m = re.search(r'\bUN\s*(\d{4})\b|UN Numaras[ıi][^\d]{0,30}(\d{4})', s14, re.I)
    return ('uygun', f'UN {m.group(1) or m.group(2)}') if m else ('eksik', '14.1\'de UN numarası bulunamadı.')


# Taşıma sınıfı Romen rakamıyla yazılmış olabilir ("ADR Sınıfı: VIII") — karşılaştırmadan önce Arap rakamına çevrilir
_ROMA_SINIF = {'IX': '9', 'VIII': '8', 'VII': '7', 'VI': '6', 'V': '5', 'IV': '4', 'III': '3', 'II': '2', 'I': '1'}


def _s14_rakam(s14: str) -> str:
    return re.sub(r'(?i)((?:sınıf\w*|class)\s*[:\-]?\s*)(IX|VIII|VII|VI|IV|V|III|II|I)\b',
                  lambda m: m.group(1) + _ROMA_SINIF[m.group(2).upper()], s14 or '')


def c_sinif14(ctx):
    if re.search(r'(?i)belirlenmemiştir|not determined', ctx['secs'].get('14', '')):
        return 'kdu', '14. bölümde taşımacılık sınıflandırması "belirlenmemiştir" — KDU kontrol etmeli (KKDİK Ek-2 Bölüm 14).'
    s14 = _s14_rakam(ctx['secs'].get('14', ''))
    return ('uygun', 'Taşımacılık sınıfı var.') if re.search(r'(?i)(?:sınıf[\w()]*|class|zararlar[ıi])\s*[:\-]?\s*\d(?:\.\d)?', s14) \
        else ('eksik', '14.3\'te taşımacılık sınıfı bulunamadı.')


def c_pg(ctx):
    if re.search(r'(?i)belirlenmemiştir|not determined', ctx['secs'].get('14', '')):
        return 'kdu', '14. bölümde taşımacılık sınıflandırması "belirlenmemiştir" — KDU kontrol etmeli (KKDİK Ek-2 Bölüm 14).'
    s14 = ctx['secs'].get('14', '')
    return ('uygun', 'Ambalaj grubu var.') if re.search(r'(?i)ambalaj(?:lama)? grubu\s*[:\-]?\s*(?:I{1,3}\b|uygulanamaz|'
                                                        r'uygulanabilir değil|yok|[-–](?=\s|$))', s14) \
        else ('eksik', '14.4\'te ambalaj grubu bulunamadı.')


def c_15_svhc(ctx):
    from app.services.svhc_service import check_svhc_single
    cas, _ = _rows3(ctx)
    s15 = ctx['secs'].get('15', '')
    stated = re.search(r'(?i)aday liste|svhc|yüksek önem arz eden', s15)
    hits = [c for c in cas if check_svhc_single(c)]
    if hits and not stated:
        return 'eksik', f'Bölüm 3\'te Aday Liste maddesi ({hits}) var ama 15.1\'de belirtilmemiş.'
    return ('uygun', 'Aday Liste durumu belirtilmiş.') if stated else ('kdu', 'Aday Liste beyanı yok (madde yoksa iyi uygulama).')


def c_deterjan(ctx):
    s15 = ctx['secs'].get('15', '')
    # Ek-7 A son paragraf: endüstriyel üründe bilgi teknik veri belgesi / GBF / benzer belgeyle; tüketici ürününde
    # etikette. GBF bilginin etikette / teknik veri belgesinde verildiğini belirtiyorsa KDU o belgeyi doğrular.
    if re.search(r'(?i)ek-7\s*a içerik bilgisi[^.]{0,60}(etiket|teknik veri belgesi)', s15):
        return 'kdu', ('15.1: Ek-7 A içerik bilgisinin etikette / teknik veri belgesinde verildiği belirtilmiş — '
                       'KDU etiket veya belgede listenin eksiksiz olduğunu doğrulamalı (Deterjanlar Yön. Ek-7 A).')
    if re.search(r'(?i)sınıfı belirlenmemiş|class to be determined', s15):
        return 'eksik', 'Ek-7 A beyanında sınıfı belirlenmemiş (yüzey aktif madde olabilecek) bileşen var.'
    if re.search(r'(?i)beyan edilecek bileşen sınıfı bulunmamaktadır|no ingredient classes subject', s15):
        return 'kdu', ('15.1\'de "Ek-7 A kapsamında beyan edilecek bileşen sınıfı bulunmamaktadır" yazıyor — ürün yüzey '
                       'aktif madde vb. içeriyorsa beyan gerekir; KDU doğrulasın.')
    return ('uygun', 'Deterjan içerik beyanı var.') if re.search(r'(?i)%\s*5.?ten az|yüzey aktif|surfaktan|parfüm', s15) \
        else ('eksik', 'Deterjan Ek-7 A içerik beyanı bulunamadı.')


def c_tam_metin(ctx):
    s3, s16 = ctx['secs'].get('3', ''), ctx['secs'].get('16', '')
    codes = _h(s3) | set(EUH_RE.findall(s3))
    miss = sorted(c for c in codes if c not in s16)
    return ('uygun', '3. bölümdeki H/EUH kodlarının tam metni 16. bölümde.') if not miss else \
           ('eksik', f'16. bölümde tam metni olmayan kodlar: {miss}')


def c_t14(ctx):
    if re.search(r'(?i)belirlenmemiştir|not determined', ctx['secs'].get('14', '')):
        return 'kdu', '14. bölümde taşımacılık sınıflandırması "belirlenmemiştir" — KDU kontrol etmeli (KKDİK Ek-2 Bölüm 14).'
    h = _h(ctx['secs'].get('2', ''))
    s14 = _s14_rakam(ctx['secs'].get('14', ''))
    exp = []
    if h & {'H314', 'H290'}:
        exp.append('8')                           # H290 → ADR 2.2.8.1.5.3 (c)(ii) Sınıf 8 PG III
    if h & {'H224', 'H225', 'H226'}:
        exp.append('3')
    # Aerosol → UN 1950 (Sınıf 2); gaz: alevlenir → 2.1, yalnız basınçlı gaz → 2.2 (ADR 2.2.2.1.5);
    # oksitleyici katı/sıvı → 5.1 (ADR 2.2.51)
    if h & {'H222', 'H223', 'H229'}:
        return (('uygun', 'Aerosol: UN 1950 14\'te var.') if re.search(r'(?i)\bUN\s*1950\b', s14) else
                ('eksik', '2. bölümde aerosol sınıflandırması var; 14\'te UN 1950 bulunamadı.'))
    # Zehirli gaz (ADR 2.2.2.1.3 T grubu) → etiket 2.3; oksitleyici ise + 5.1 (örn. klor 2TOC: 2.3+5.1+8).
    # Önceden tanımsızdı; klor GBF'sinde Sınıf 9 aranıp yanlış KDU uyarısı çıkıyordu (2026-10-09).
    if h & {'H280', 'H281'} and h & {'H330', 'H331'}:
        exp.append('2.3')
        if 'H270' in h:
            exp.append('5.1')
    if h & {'H220', 'H221'}:
        exp.append('2.1')
    elif 'H270' in h and h & {'H280', 'H281'} and not h & {'H330', 'H331', 'H314'}:
        exp += ['2.2', '5.1']                     # oksitleyici gaz: ADR 1O/2O/3O → etiket 2.2 + 5.1
    elif h & {'H280', 'H281'} and not h & {'H330', 'H331', 'H314', 'H270'}:
        exp.append('2.2')
    if h & {'H271', 'H272'} and not exp:
        exp.append('5.1')
    # ADR 2.2.9.1.10: Sucul Akut 1 / Kronik 1 / Kronik 2 → başka sınıf yoksa Sınıf 9 (UN 3082 sıvı, UN 3077 katı)
    if not exp and h & {'H400', 'H410', 'H411'}:
        un9 = re.search(r'(?i)\bUN\s*(3082|3077)\b', s14)
        return ('uygun', f'Çevre için tehlikeli madde: Sınıf 9, UN {un9.group(1)} 14\'te var.') if un9 else \
               ('kdu', '2. bölümde H400/H410/H411 var; 14\'te Sınıf 9 (UN 3082 / UN 3077) bulunamadı '
                       '(ADR 2.2.9.1.10) — KDU doğrulasın.')
    miss = [e for e in exp if not re.search(rf'(?<![\d.]){e}(?![\d])', s14)]
    if not exp:
        return 'kdu', 'Bu sınıflandırma için basit eşleme yok; KDU doğrulasın.'
    return ('uygun', f'Beklenen taşıma sınıf(lar)ı {exp} 14\'te var.') if not miss else \
           ('eksik', f'2. bölüm sınıflandırmasına göre beklenen taşıma sınıfı 14\'te yok: {miss}')


def c_t32(ctx):
    s2, s3 = ctx['secs'].get('2', ''), ctx['secs'].get('3', '').lower()
    if not ({h[:4] for h in _h(s2)} & LABEL_COMP_H):
        return 'uygun', '2.2\'de etikette adı yazılacak bileşen gerektiren sınıflandırma yok (SEA Md.20(3)(b)).'
    # "içerir" yalnız iki noktayla ("… içerir:") — H280 metnindeki "Basınçlı gaz içerir;" bileşen listesi değildir
    m = re.search(r'(?is)(?:zararlı bileşen\w*\s*:?|tehlikeli bileşen\w*\s*:?|içerir\s*:)\s*(.{0,250})', s2)
    if not m:
        return 'kdu', '2.2\'de zararlı bileşen adı bulunamadı.'
    # Yalnız ilk dolu satır: sonrası 2.3 veya başka bir cümle
    first = next((ln for ln in m.group(1).splitlines() if ln.strip()), '')
    first = re.split(r'(?<![\d.])2\.3\b|Karışımın|\bH\d{3}', first)[0]
    names = [re.sub(r'\.\.\..*$|\s*%.*$', '', n).strip(' .') for n in re.split(r'[,;]', first)]
    names = [n for n in names if len(n) > 3][:6]
    if not names:
        return 'kdu', '2.2\'de zararlı bileşen adı okunamadı.'
    miss = [n for n in names if n.lower()[:8] not in s3]
    return ('uygun', f'2.2\'deki bileşenler 3\'te: {names}') if not miss else \
           ('kdu', f'2.2\'deki adlar 3. bölümde birebir bulunamadı (farklı adlandırma olabilir): {miss}')


_CONC_NEAR = re.compile(r'(?:[<>≤≥]=?\s*)?(\d+(?:[.,]\d+)?)\s*(?:%)?\s*(?:-|–)\s*(?:[<>≤≥]=?\s*)?(\d+(?:[.,]\d+)?)\s*%'
                        r'|(?:[<>≤≥]=?\s*)?(\d+(?:[.,]\d+)?)\s*%|%\s*[<>≤≥]?\s*(\d+(?:[.,]\d+)?)')


_RANGE_GE = re.compile(r'(?:[>≥]=?|&gt;=?|(?<=Alan\s)|(?<=Alan:\s))\s*(\d+(?:[.,]\d+)?)\s*%?\s*[-–]\s*([<≤]=?|&lt;=?)\s*(\d+(?:[.,]\d+)?)')
# Yalnız üst sınır: "< 0,1%" (alt sınırsız aralık)
_RANGE_LT = re.compile(r'(?<![\d.,])(?:<|&lt;)\s*(\d+(?:[.,]\d+)?)\s*%')


def _segments3(ctx):
    """Bölüm 3 satırları: her CAS'tan bir sonraki CAS'a kadar olan metin (tablo satırı yaklaşımı)."""
    cas, s3 = _rows3(ctx)
    pos = [(c, s3.find(c)) for c in cas]
    pos = sorted([p for p in pos if p[1] >= 0], key=lambda x: x[1])
    return [(c, s3[i:(pos[k + 1][1] if k + 1 < len(pos) else len(s3))]) for k, (c, i) in enumerate(pos)], s3


def _ek6_not_suz(lk: dict, seg: str) -> list:
    """Bileşenin veritabanı tehlikeleri; Ek-6 notlu (J/K/L/M/N/P) maddede GBF Bölüm 3 satırı kanserojen / mutajen kodu
    içermiyorsa (firma notu uygulamış) o kodlar yeniden hesaba katılmaz."""
    hz = list(lk.get('hazards') or [])
    notlar = set(lk.get('notes') or []) & set('JKLMNP')
    if not notlar or not lk.get('sea_ek6'):
        return hz
    kodlar = {'H350', 'H351'} | ({'H340', 'H341'} if notlar & set('JKP') else set())
    yazili = {h[:4] for h in re.findall(r'H3[45]\d\w?', seg or '')}
    return [h for h in hz if str(h.get('h_code') or '')[:4] not in kodlar or str(h.get('h_code') or '')[:4] in yazili]


def _comps3(ctx):
    """Bölüm 3'ten bileşenler: CAS, konsantrasyon üst değeri, veritabanı tehlikeleri. (comps, okunamayanlar)"""
    if '_comps3' in ctx:
        return ctx['_comps3']
    from app.services.substance_lookup import lookup_substance
    segs, s3 = _segments3(ctx)
    comps, unknown = [], []
    for c, seg in segs:
        i = s3.find(c)
        # Ek-6 UVCB adlarındaki köşeli parantezli tanım ("[... C3 ila C7 ... -40°C ila 80°C ...]") atlanır — uzun tanım
        # konsantrasyon sütununu okuma penceresinin dışına itiyordu (LPG 68476-85-7)
        seg = re.sub(r'\[[^\]]*\]', ' ', seg)
        # Önce "≥ x - < y" aralığı (konsantrasyon sütunu; % işareti olmayabilir). Bazı GBF'ler satırda önce
        # özel konsantrasyon sınırlarını "20 - 100 %" biçiminde yazar — onlar konsantrasyon değildir.
        # KKDİK Ek-2 A 3.2: aralıkta zararlar en yüksek konsantrasyona göre tanımlanır → hesap üst uçta;
        # "< y" üst sınırı dahil değildir → eşiğin hemen altı (y × (1 − 10⁻⁶)); "≤ y" → y.
        r = _RANGE_GE.search(seg)
        lt = _RANGE_LT.search(seg[:260]) if not r else None
        if r:
            conc = float(r.group(3).replace(',', '.'))
            if r.group(2) in ('<', '&lt;'):
                conc *= (1 - 1e-6)
        elif lt:
            conc = float(lt.group(1).replace(',', '.')) * (1 - 1e-6)
        else:
            m = _CONC_NEAR.search(seg[:260]) or _CONC_NEAR.search(s3[max(0, i - 120):i])
            if not m:
                unknown.append(c); continue
            conc = max(float(v.replace(',', '.')) for v in m.groups() if v)
        lk = lookup_substance(c, form='liquid' if 'form:sivi' in ctx['facts'] else '') or {}
        if not lk.get('hazards') and not lk.get('found') and c != '7732-18-5':
            unknown.append(c)
        comps.append({'cas_no': c, 'cas': c, 'name': lk.get('name') or c, 'name_tr': lk.get('name_tr') or '',
                      'concentration': conc, 'conc': conc,
                      # SEA Ek-6 Not J/K/L/M/N/P: koşul tedarikçi belgesiyle gösterilmişse kanserojen / mutajen sınıf
                      # uygulanmaz — GBF Bölüm 3'te bileşene bu sınıf yazılmamışsa not uygulanmış sayılır
                      'hazards': _ek6_not_suz(lk, seg),
                      'sclRaw': lk.get('scl') or [], 'euh_limits': lk.get('euh_limits') or [],
                      'm_factors': lk.get('m_factors') or {},
                      'suppl_hazards': lk.get('suppl_hazards') or [], 'segment': seg})
    ctx['_comps3'] = (comps, unknown)
    return comps, unknown


def c_hesap(ctx):
    """Bölüm 3'teki CAS + konsantrasyon üst değeriyle karışım sınıflandırmasını yeniden hesaplar."""
    from app.services.clp_service import classify_mixture_clp
    cas, s3 = _rows3(ctx)
    given0 = {h for h in _h(_sub(ctx['secs'].get('2', ''), '2.1', '2.2')) if h[:2] in ('H3', 'H4')}
    if not cas and _NOTHING_TO_LIST.search(s3):
        return (('uygun', 'Bölüm 3\'te listelenecek madde yok ve 2.1\'de sağlık/çevre sınıflandırması yok — tutarlı.')
                if not given0 else
                ('eksik', f'2.1\'de {sorted(given0)} var ama Bölüm 3\'te listelenen madde yok (Ek-2 A 3.2.1).'))
    if not cas:
        return 'kdu', 'Bölüm 3 okunamadı.'
    comps, unknown = _comps3(ctx)
    # GBF 2.1 gerekçesinde Tablo 3.2.4 / 3.3.4 (toplama yöntemi uygulanamaz) yazıyorsa aynı kural kullanılır
    _na = bool(re.search(r'Tablo\s*3\.[23]\.4', ctx['secs'].get('2', '')))
    _liq = 'form:sivi' in ctx['facts']

    def _calc(cs):
        res = classify_mixture_clp(cs, mixture_form='liquid' if _liq else '', additivity_na=_na)
        # Sucul sınıf programın hattındaki gibi yalnız ecological_service'ten (SEA Ek-1 4.1.3.5 toplama)
        out = {p['h_code'][:4] for p in res.get('passed', []) if p.get('h_code') and p['h_code'][:2] != 'H4'}
        try:
            from app.services.ecological_service import calculate_ecological
            eco = calculate_ecological([{'cas': c['cas'], 'name': c['name'], 'conc': c['conc'],
                                         'worst_case_conc': c['conc'], 'hazards': c['hazards'],
                                         'm_factors': c.get('m_factors') or {}} for c in cs])
            for _a in (getattr(eco, 'aquatic', None), getattr(eco, 'aquatic_acute', None)):
                if _a is not None and getattr(_a, 'h_code', None):
                    out.add(_a.h_code[:4])
        except Exception:
            pass
        # Programın hattındaki gibi: STOT RE toplamsal (H372/H373) ve ATE ile akut toksisite ayrı motorlardan
        try:
            from app.services.stot_engine import calculate as stot_calc
            out |= {str(h)[:4] for h in stot_calc(cs).get('h_codes', [])}
        except Exception:
            pass
        try:
            from app.services.clp_service import calculate_ate_health_h_codes
            out |= {e['h_code'][:4] for e in calculate_ate_health_h_codes(
                cs, form='liquid' if _liq else 'solid')[0]}
        except Exception:
            pass
        if 'H372' in out:
            out.discard('H373')
        out = {h for h in out if h[:2] in ('H3', 'H4')}
        if 'H314' in out:
            out.discard('H318')
        return out

    given = set(given0)
    if 'H314' in given:
        given.discard('H318')
    note = f' (verisi/konsantrasyonu okunamayan: {unknown})' if unknown else ''
    try:
        calc = _calc(comps)
        if calc == given:
            return 'uygun', (f'Bölüm 3 konsantrasyonlarının üst değeriyle yeniden hesaplanan sağlık/çevre '
                             f'sınıflandırması 2.1 ile aynı: {sorted(calc)}{note}')
    except Exception as e:
        return 'kdu', f'Yeniden hesap yapılamadı: {e}'
    return 'kdu', (f'Bölüm 3 üst değerleriyle yeniden hesap {sorted(calc)} — 2.1 {sorted(given)}. KKDİK Ek-2 A 3.2: '
                   f'aralık kullanılırsa zararlar en yüksek konsantrasyona göre tanımlanır — aralık çok geniş olabilir '
                   f'ya da fark kaynak verisinden/okumadan kaynaklanabilir; KDU doğrulasın.{note}')


def c_32_sira(ctx):
    """Ek-2 A 3.2 (a)/(b): azalan sırada — konsantrasyon üst değerleri artmamalı."""
    comps, unknown = _comps3(ctx)
    if len(comps) < 2:
        return 'uygun', 'Sıralanacak birden fazla madde yok.'
    seq = [(c['cas_no'], c['conc']) for c in comps]
    bad = [(seq[i][0], seq[i][1], seq[i + 1][0], seq[i + 1][1]) for i in range(len(seq) - 1)
           if seq[i + 1][1] > seq[i][1]]
    if not bad:
        return 'uygun', 'Maddeler konsantrasyona göre azalan sırada: ' + ', '.join(f'{c} %{v:g}' for c, v in seq)
    det = '; '.join(f'{a} (%{x:g}) → {b} (%{y:g})' for a, x, b, y in bad[:4])
    return ('eksik' if not unknown else 'kdu'), f'Azalan sıraya uymayan geçişler: {det}'


_REASON = re.compile(r'(?i)maruz kalma|sınır değer|\bOEL\b|PBT|vPvB|Aday Liste|SVHC|gönüllü|bilgi amaçlı|'
                     r'listelenme nedeni|nedeni\s*:')


def c_32_neden(ctx):
    """Ek-2 A 3.2.3: sınıflandırılmamış listelenen maddenin listelenme nedeni."""
    segs, _ = _segments3(ctx)
    miss = []
    for c, seg in segs:
        if c == '7732-18-5':   # su — yaygın olarak gönüllü listelenir
            continue
        if not H_RE.search(seg) and not _REASON.search(seg):
            miss.append(c)
    return ('uygun', 'Sınıflandırılmamış listelenen maddeler için neden belirtilmiş (veya yok).') if not miss else \
           ('kdu', f'Sınıflandırması görünmeyen ve listelenme nedeni yazılmamış maddeler (CAS): {miss} '
                   f'— Ek-2 A 3.2.3 "işyeri maruz kalma limiti", "sınıflandırılmamış vPvB" gibi nedeni ister.')


def c_32_kayit(ctx):
    """Ek-2 A 3.2.4: varsa kayıt numarası."""
    s3 = ctx['secs'].get('3', '')
    if not _rows3(ctx)[0] and _NOTHING_TO_LIST.search(s3):
        return 'uygun', 'Listelenmesi gereken madde yok.'
    if re.search(r'\b01-\d{10}-\d{2}', s3):
        return 'uygun', 'Kayıt numaraları verilmiş.'
    if re.search(r'(?i)tedarikçiden|muaf|kayıt numarası|registration', s3):
        return 'uygun', 'Kayıt numarası durumu belirtilmiş (muaf / tedarikçiden temin).'
    return 'kdu', 'Bölüm 3\'te kayıt numarası veya durumu bulunamadı — varsa verilmeli.'


# Kimyasal Maddelerle Çalışmalarda Sağlık ve Güvenlik Önlemleri Hakkında Yönetmelik (RG 12.08.2013/28733)
# Ek-2: zorunlu biyolojik sınır değer — kurşun ve iyonik bileşikleri (70 µg Pb/100 ml kan)
_LEAD_CAS = {'7439-92-1', '1317-36-8', '1314-41-6', '7446-14-2', '598-63-0', '301-04-2', '10099-74-8',
             '7758-97-6', '1344-37-2', '12656-85-8', '1335-32-6', '7758-95-4', '13424-46-9', '1309-60-0'}


def c_bld(ctx):
    cas, _ = _rows3(ctx)
    lead = [c for c in cas if c in _LEAD_CAS]
    if not lead:
        return 'uygun', 'Biyolojik sınır değeri olan bileşen (kurşun ve iyonik bileşikleri) yok.'
    return ('uygun', 'Kurşun bileşeni için biyolojik sınır değer verilmiş.') if re.search(
        r'(?i)biyolojik', ctx['secs'].get('8', '')) else \
           ('eksik', f'Kurşun bileşeni {lead} var; 8.1\'de biyolojik sınır değer (70 µg Pb/100 ml kan, '
                     f'28733 sayılı Yönetmelik Ek-2) yok.')


# Kanserojen veya Mutajen Maddelerle Çalışmalarda Sağlık ve Güvenlik Önlemleri Hakkında Yönetmelik
# (RG 06.08.2013/28730) Ek-2 "Mesleki maruziyet sınır değerleri" — mevzuat.gov.tr MevzuatNo=18695,
# değişiklik işlenmemiş (2026-10-07 kontrol). Sert ağaç tozları (5,0 mg/m³) CAS'sız olduğundan ada göre aranır.
_KANS_OEL = {
    '71-43-2': ('Benzen', ('3,25', '3.25'), ('1',)),
    '75-01-4': ('Vinilklorür monomeri', ('7,77', '7.77'), ('3',)),
}


def c_oel_kanserojen(ctx):
    """Ek-2 A 8.1.1.2: kanserojen/mutajen bileşen için Kanserojen Yönetmeliği Ek-2 sınır değeri."""
    cas, _ = _rows3(ctx)
    s8 = _sub(ctx['secs'].get('8', ''), '8.1', '8.2') or ctx['secs'].get('8', '')
    hits = [c for c in cas if c in _KANS_OEL]
    wood = re.search(r'(?i)(sert\s+)?ağaç\s+toz|hardwood\s+dust', ctx['secs'].get('3', ''))
    if not hits and not wood:
        return 'uygun', ('Kanserojen Yönetmeliği Ek-2\'de sınır değeri olan bileşen yok (Ek-2 yalnız benzen, '
                         'vinil klorür monomeri ve sert ağaç tozlarını içerir).')
    miss = []
    for c in hits:
        name, mg, ppm = _KANS_OEL[c]
        if c not in s8 or not any(re.search(rf'(?<![\d.,]){re.escape(v)}(?![\d.,])\s*mg', s8) for v in mg):
            miss.append(f'{name} ({c}): {mg[0]} mg/m³ / {ppm[0]} ppm')
    if wood and not re.search(r'(?<![\d.,])5([.,]0)?\s*mg', s8):
        miss.append('Sert ağaç tozları: 5,0 mg/m³')
    if not miss:
        if not re.search(r'(?i)28730|kanserojen\s+veya\s+mutajen', s8):
            return 'kdu', ('Kanserojen Yönetmeliği Ek-2 sınır değeri 8.1\'de var ama dayanağı bu yönetmelik olarak '
                           'gösterilmemiş (RG 06.08.2013/28730, Ek-2); KDU kaynak satırını kontrol etmeli.')
        return 'uygun', 'Kanserojen Yönetmeliği Ek-2 sınır değerleri 8.1\'de dayanağıyla verilmiş.'
    return 'eksik', ('8.1\'de Kanserojen veya Mutajen Maddelerle Çalışmalarda Sağlık ve Güvenlik Önlemleri '
                     'Hakkında Yönetmelik (RG 06.08.2013/28730) Ek-2 sınır değeri bulunamadı: ' + '; '.join(miss))




def _ek17():
    from app.services.ek17_service import db
    return db()


def c_izin_kisit(ctx):
    """Ek-2 A 15.1: izne tabi / kısıtlanmış madde durumu. TR Ek-14 listesi boştur (Bakanlık sitesinde yayımlanır);
    kontrol Ek-17 kısıtlamalarına göre yapılır."""
    cas, _ = _rows3(ctx)
    db = _ek17()
    hits = {c: db[c] for c in cas if c in db}
    # Ek-17 madde 28/29/30 (CMR listeleri) yalnız sınıf GBF'de varsa — Ek-6 Not K/P ile kalkan sınıfta uygulanmaz
    _h23 = {h[:4] for h in _h(ctx['secs'].get('2', '') + ' ' + ctx['secs'].get('3', ''))}
    _cmr = {'Giriş 28': 'H350', 'Giriş 29': 'H340', 'Giriş 30': 'H360'}
    hits = {c: [r for r in v if all(g not in str(r.get('kaynak') or '') or h in _h23 for g, h in _cmr.items())]
            for c, v in hits.items()}
    hits = {c: v for c, v in hits.items() if v}
    if not hits:
        return 'uygun', 'Bölüm 3\'te KKDİK Ek-17 kapsamında madde yok (TR Ek-14 listesi henüz yayımlanmadı).'
    det = '; '.join(f'{c}: ' + ', '.join(r['kaynak'] for r in v[:2]) for c, v in hits.items())
    # Yönetmelik adındaki "İzni ve Kısıtlanması Hakkında" ifadesi kısıtlama beyanı sayılmaz
    s15 = re.sub(r'(?i)izni\s+ve\s+kısıtlanması|authorisation\s+and\s+restriction', '', ctx['secs'].get('15', ''))
    stated = re.search(r'(?i)ek[- ]?17\b|ek[- ]?xvii|annex\s+xvii|kısıtlama(?:ya|lar|sı)?\b|kısıtlanmış', s15)
    # Ek-17 madde 46: nonilfenol / nonilfenol etoksilatlar temizlik ürünlerinde ≥%0,1 piyasaya arz edilemez
    np46 = [c for c, v in hits.items() if any(str(r.get('giris')) == '46' for r in v)]
    s1 = ctx['secs'].get('1', '')
    cleaning = 'deterjan' in ctx['facts'] or re.search(
        r'(?i)temizl|deterjan|yıkama|bulaşık|çamaşır|cleaner|cleaning|detergent|dishwash|laundry', s1)
    if np46 and cleaning:
        return 'kdu', (f'Temizlik ürünü ve nonilfenol/nonilfenol etoksilat içeriyor ({", ".join(np46)}): KKDİK Ek-17 '
                       f'madde 46 gereği endüstriyel/kurumsal ve evsel temizlikte ağırlıkça %0,1 ve üzerinde piyasaya '
                       f'arz edilemez — konsantrasyonu KDU doğrulamalı.')
    return ('uygun', f'Ek-17 durumu 15.1\'de belirtilmiş ({det}).') if stated else \
           ('eksik', f'Ek-17 kapsamındaki maddeler 15.1\'de belirtilmemiş: {det}')


def c_ek_unsur(ctx):
    """SEA Md.25/27: bileşenlere göre gereken EUH ifadeleri 2. bölümde var mı (programın EUH motoruyla)."""
    from app.services.euh_service import check_euh
    comps, unknown = _comps3(ctx)
    if not comps:
        return 'kdu', 'Bölüm 3 okunamadı.'
    form = 'liquid' if 'form:sivi' in ctx['facts'] else 'solid' if 'form:kati' in ctx['facts'] else ''
    try:
        exp = set(check_euh(comps, mixture_form=form).get('euh_codes', []))
    except Exception as e:
        return 'kdu', f'EUH hesaplanamadı: {e}'
    found = set(EUH_RE.findall(ctx['secs'].get('2', '')))
    miss = sorted(exp - found)
    if not exp:
        return 'uygun', 'Bileşenlere göre gereken ek etiket unsuru (EUH) yok.' + (
            f' Not: 2. bölümde {sorted(found)} var.' if found else '')
    return ('uygun', f'Gereken EUH ifadeleri 2. bölümde: {sorted(exp)}') if not miss else \
           ('kdu', f'Programın hesabına göre gereken ama 2. bölümde bulunamayan EUH ifadeleri: {miss} '
                   f'(kaynak verisi farklı olabilir; KDU doğrulasın).')



# ── 2026-10-09: üretimdeki kural değişikliklerinin denetimi ──────────────────────────────────────────────
def _line(sec: str, label_rx: str, n: int = 160) -> str:
    m = re.search(label_rx, sec or '', re.I)
    return (sec[m.end(): m.end() + n] if m else '')


def c_16_revizyon(ctx):
    """KKDİK Ek-2 16(a): revizyonda önceki versiyona göre değişiklikler."""
    s16 = ctx['secs'].get('16', '')
    if re.search(r'(?i)değişiklik(?:ler)?\s+belirtilmemiştir|changes[^.]{0,40}not (?:been )?specified', s16):
        return 'eksik', 'Bölüm 16\'da önceki versiyona göre değişikliklerin "belirtilmediği" yazıyor (KKDİK Ek-2 16(a)).'
    if re.search(r'(?i)değişiklik|güncellen|revize edil|eklendi|çıkarıldı|düzeltilmiş bölüm|changes|revised|amended', s16):
        return 'uygun', 'Bölüm 16\'da önceki versiyona göre değişiklikler belirtilmiş.'
    return 'eksik', 'Revizyon olduğu halde Bölüm 16\'da değişiklik açıklaması bulunamadı (KKDİK Ek-2 16(a)).'


def c_dnel(ctx):
    """KKDİK Ek-2 8.1.4: DNEL/PNEC mevcutsa verilir; yoksa belirlenmediği / mevcut olmadığı belirtilir."""
    s8 = ctx['secs'].get('8', '')
    if not re.search(r'DNEL|PNEC|DMEL', s8):
        return 'kdu', 'Bölüm 8\'de DNEL/PNEC bilgisi yok — madde için mevcutsa verilmeli (KKDİK Ek-2 8.1.4).'
    if re.search(r'(?i)(?:DNEL|PNEC)[^.]{0,200}?\d[\d.,]*\s*(?:mg|µg|ug|g)/', s8):
        return 'uygun', 'Bölüm 8\'de sayısal DNEL/PNEC değerleri var.'
    if re.search(r'(?i)(?:DNEL|PNEC)[^.]{0,160}(belirlenmemiş|mevcut değil|bulunmamakta|bakınız|not (?:established|available))', s8):
        return 'uygun', 'DNEL/PNEC\'in belirlenmediği / mevcut olmadığı belirtilmiş.'
    return 'kdu', 'DNEL/PNEC geçiyor ama değer ya da "belirlenmemiştir" ifadesi bulunamadı.'


_GLOVE_SEG = r'(?i)ellerin korunması|el koruma|eldiven|hand protection|gloves?'
_GLOVE_MAT = (r'(?i)nitril|bütil|butil|butyl|neopren|polikloropren|chloroprene|viton|florokauçuk|fluoro|FKM|laminat|'
              r'laminate|PVC|polivinil|PVA|lateks|latex|doğal kauçuk|natural rubber')


def _glove_seg(ctx):
    s8 = ctx['secs'].get('8', '')
    m = re.search(_GLOVE_SEG, s8)
    return s8[m.start(): m.start() + 700] if m else None


def _glove_not_needed(seg):
    return bool(re.search(r'(?i)eldiven gerekmez|gerekli değildir|özel (?:el )?koruma gerekmez|not required', seg or ''))


def c_eldiven_malzeme(ctx):
    seg = _glove_seg(ctx)
    if seg is None:
        return 'eksik', 'Bölüm 8\'de el koruması (eldiven) bilgisi bulunamadı.'
    if _glove_not_needed(seg) or re.search(_GLOVE_MAT, seg):
        return 'uygun', 'Eldiven malzemesi belirtilmiş.'
    return 'eksik', 'Eldiven var ama malzemesi (nitril, bütil vb.) belirtilmemiş (KKDİK Ek-2 8.2.2.2(b)(i)).'


def c_eldiven_kalinlik(ctx):
    seg = _glove_seg(ctx)
    if seg is None:
        return 'eksik', 'Bölüm 8\'de el koruması (eldiven) bilgisi bulunamadı.'
    if _glove_not_needed(seg) or re.search(r'\d+(?:[.,]\d+)?\s*mm\b', seg):
        return 'uygun', 'Eldiven kalınlığı belirtilmiş.'
    return 'eksik', 'Eldiven malzeme kalınlığı (mm) belirtilmemiş (KKDİK Ek-2 8.2.2.2(b)(i)).'


def c_eldiven_sure(ctx):
    seg = _glove_seg(ctx)
    if seg is None:
        return 'eksik', 'Bölüm 8\'de el koruması (eldiven) bilgisi bulunamadı.'
    if _glove_not_needed(seg) or re.search(r'(?i)\d+\s*(?:dk|dak|dakika|min|saat)\b', seg):
        return 'uygun', 'Eldivenin delinme (aşınma) süresi belirtilmiş.'
    if re.search(r'(?i)delinme süresi|breakthrough', seg) and re.search(r'(?i)üretici|manufacturer', seg):
        return 'kdu', ('Delinme süresi sayı olarak yok; üretici verisine göre seçim yazılmış — KDU eldiven üreticisinin '
                       'süresini girmeli (KKDİK Ek-2 8.2.2.2(b)(i)).')
    return 'eksik', 'Eldivenin tipik veya en az delinme süresi belirtilmemiş (KKDİK Ek-2 8.2.2.2(b)(i)).'


def c_9_ampirik(ctx):
    """KKDİK Ek-2 9: bölüm ampirik bilgi açıklar — hesaplanmış / tahmini değer (gaz karışımında ISO 10156 hariç)."""
    s9 = ctx['secs'].get('9', '')
    bad = []
    for m in re.finditer(r'(?i)hesaplan\w*|tahmin\w*|teorik|calculated|estimated', s9):
        ctx_s = s9[max(0, m.start() - 80): m.end() + 80]
        if re.search(r'(?i)ISO 10156|hesapla belirlenemez|hesaplanmaz|not calculated|cannot be calculated', ctx_s):
            continue
        bad.append(re.sub(r'\s+', ' ', ctx_s).strip()[:120])
    return ('uygun', 'Bölüm 9\'da hesaplanmış / tahmini değer yok.') if not bad else \
           ('eksik', f'Bölüm 9\'da hesaplanmış / tahmini değer: "{bad[0]}" — KKDİK Ek-2 9 ampirik (ölçülmüş) bilgi '
                     'ister; karışım değeri yoksa nedeni veya ilgili maddeye ait veri yazılır.')


def c_9_neden(ctx):
    """KKDİK Ek-2 9.1: bilgi mevcut değil / uygulanamaz denmişse nedeni belirtilir."""
    s9 = ctx['secs'].get('9', '')
    bare = re.findall(r'(?i)\b(belirlenmemiştir|veri (?:yok|mevcut değil)|bilgi (?:yok|mevcut değil)|mevcut değil|'
                      r'uygulanamaz|not available|no data|not applicable|not determined)\b(?!\s*[(\-—:;,]|\s+\()', s9)
    return ('uygun', 'Bölüm 9\'da "veri yok / uygulanamaz" ifadelerinin nedeni belirtilmiş.') if not bare else \
           ('eksik', f'Bölüm 9\'da nedeni yazılmamış {len(bare)} "veri yok / uygulanamaz" ifadesi var '
                     f'(ör. "{bare[0]}") — KKDİK Ek-2 9.1 nedenin belirtilmesini ister.')


def c_9_fp_sinif(ctx):
    """Ek-2 9: bölüm sınıflandırmayla tutarlıdır — parlama noktası ↔ alevlenir sıvı sınıfı (SEA Ek-1 Tablo 2.6.1)."""
    s9, f = ctx['secs'].get('9', ''), ctx['facts']
    line = _line(s9, r'parlama noktas[ıi]|flash point', 200)
    if not line or re.search(r'(?i)bileşen|component|uygulanamaz|belirlenmemiş|not applicable|not determined', line[:120]):
        return 'uygun', 'Karışım için ölçülmüş / literatür parlama noktası yok (karşılaştırma yapılmadı).'
    m = re.search(r'(>|≥|<)?\s*~?\s*(-?\d+(?:[.,]\d+)?)\s*°\s*C', line)
    if not m:
        return 'uygun', 'Parlama noktası sayısal değil (karşılaştırma yapılmadı).'
    fp = float(m.group(2).replace(',', '.'))
    gt = m.group(1) in ('>', '≥')
    cls = {h for h in ('H224', 'H225', 'H226') if h in f}
    l2 = re.search(r'(?i)L\.2|sürekli yanma', ctx['text'])
    if gt and fp >= 60:
        exp = set()
    elif fp < 23:
        exp = {'H224', 'H225'}
    elif fp <= 60:
        exp = {'H226'}
    else:
        exp = set()
    if (cls & exp) or (not exp and not cls) or (exp == {'H226'} and not cls and l2):
        return 'uygun', f'Parlama noktası ({m.group(0).strip()}) ile alevlenir sıvı sınıfı tutarlı.'
    if not exp and cls == {'H226'} and 55 <= fp <= 75:
        return 'kdu', ('Parlama noktası 55–75 °C ve H226: gaz yağı / dizel / hafif ısıtma yağı özel hükmü olabilir '
                       '(SEA Ek-1 Tablo 2.6.1 notu) — KDU doğrulasın.')
    return 'eksik', (f'Bölüm 9 parlama noktası ({m.group(0).strip()}) ile Bölüm 2 sınıfı '
                     f'({", ".join(sorted(cls)) or "alevlenir sıvı sınıfı yok"}) tutarsız (SEA Ek-1 Tablo 2.6.1; '
                     'KKDİK Ek-2 9: bölüm sınıflandırmayla tutarlıdır).')


def c_9_h304(ctx):
    """SEA Ek-1 3.10.3.3.1: H304 kararı 40 °C'de ölçülmüş kinematik viskoziteye (≤ 20,5 mm²/s) göre."""
    s9 = ctx['secs'].get('9', '')
    line = _line(s9, r'akışkanlık|viskozite|viscosity', 160)
    m = re.search(r'(-?\d+(?:[.,]\d+)?)\s*(mm²/s|mm2/s|cSt|mPa\s*[·.]?\s*s|cP)', line)
    if not m:
        return 'uygun', 'Bölüm 9\'da sayısal viskozite yok (karşılaştırma yapılmadı).'
    v, unit = float(m.group(1).replace(',', '.')), m.group(2).lower()
    if not (unit.startswith('mm') or unit == 'cst') or not re.search(r'40\s*°?\s*C', line):
        return 'kdu', (f'H304 var; Bölüm 9 viskozitesi ({m.group(0)}) 40 °C kinematik değil — SEA Ek-1 3.10.3.3.1 '
                       'kararı 40 °C\'de ölçülmüş kinematik viskoziteye göredir.')
    if v > 20.5:
        return 'eksik', (f'H304 var ama Bölüm 9 kinematik viskozitesi {v:g} mm²/s (40 °C) > 20,5 — SEA Ek-1 3.10.3.3.1 '
                         'ile tutarsız.')
    return 'uygun', f'H304 ve 40 °C kinematik viskozite ({v:g} mm²/s ≤ 20,5) tutarlı.'


def c_toz_tutarlilik(ctx):
    """KKDİK Ek-2 2.3 (toz patlaması ifadesi) ↔ Bölüm 7 (patlayıcı atmosfer önlemleri) tutarlılığı."""
    s2, s7 = ctx['secs'].get('2', ''), ctx['secs'].get('7', '')
    in2 = re.search(r'(?i)toz[- ]hava karışımı|toz patlama|dust[- ]air|dust explosion', s2)
    in7 = re.search(r'(?i)toz[- ]hava|toz patlama|dust[- ]air|dust explosion', s7)
    if bool(in2) == bool(in7):
        return 'uygun', 'Toz patlaması bilgisi Bölüm 2.3 ve 7\'de tutarlı.'
    return 'kdu', ('Toz patlaması ' + ('Bölüm 7\'de var ama 2.3\'te yok' if in7 else '2.3\'te var ama Bölüm 7\'de önlem yok')
                   + ' — KKDİK Ek-2 2.3 / 7.1.')


def c_oh375(ctx):
    """ADR 3.3.1 ÖH 375: muafiyet ≤ 5 L / 5 kg ambalaja bağlıdır; viskozite şartı yoktur."""
    s14 = ctx['secs'].get('14', '')
    for m in re.finditer(r'(?:ÖH|SP|özel hüküm|special provision)\s*375', s14, re.I):
        near = s14[max(0, m.start() - 150): m.end() + 250]
        if re.search(r'(?i)viskozite|viscosity|mm²/s|mm2/s|2\s?500', near):
            return 'eksik', 'Bölüm 14: ÖH 375 viskoziteye bağlanmış — ADR 3.3.1 ÖH 375 viskozite şartı içermez (≤ 5 L / 5 kg).'
    return 'uygun', 'Bölüm 14\'te ÖH 375 için hatalı viskozite şartı yok.'


def c_md10(ctx):
    """SEA Md.10(2): ölçülmeden en kötü durum / ihtiyatlı sınıflandırma → test yapılır; Bölüm 16'da revizyon notu."""
    t, s16 = ctx['text'], ctx['secs'].get('16', '')
    if not re.search(r'(?i)en kötü durum|ihtiyatlı olarak sınıflandır|worst[- ]case|as a precaution', t):
        return 'uygun', 'Ölçülmeden ihtiyatlı / en kötü durum sınıflandırması yok.'
    if re.search(r'(?i)revize edil|test sonucuna göre|ölçülmeli|to be revised|test result', s16):
        return 'uygun', 'İhtiyatlı sınıflandırma için Bölüm 16\'da test / revizyon notu var.'
    return 'eksik', ('Ölçülmeden en kötü durum / ihtiyatlı sınıflandırma yapılmış ama Bölüm 16\'da test ve revizyon notu '
                     'yok (SEA Md.10(2): yeterli bilgi yoksa test yapılır).')


def c_t_un(ctx):
    """ADR 3.1.2.8.1 / 2.1.3: Bölüm 3 bileşimi ve 2.1 sınıflandırmasıyla UN numarası yeniden belirlenir (Tablo A adlı
    girişler — örn. UN 1791 hipoklorit, UN 3149 H2O2 + PAA, UN 1796 nitrasyon asidi — ve B.B.B. seçimi), 14.1 ile karşılaştırılır."""
    s14 = ctx['secs'].get('14', '')
    uns = {a or b for a, b in re.findall(r'(?i)\bUN\s*(\d{4})\b|(?:UN|BM)[^\n\d]{0,12}numaras[ıi][^\d]{0,40}(\d{4})\b', s14)}
    if not uns:
        return 'uygun', '14\'te UN numarası yok — karşılaştırılacak taşıma girişi yok.'
    facts = ctx['facts']
    form = ('liquid' if 'form:sivi' in facts else 'solid' if 'form:kati' in facts else None)
    if not form:
        return 'kdu', 'Ürünün fiziksel hali (sıvı/katı) belirlenemedi — UN karşılaştırması yapılmadı.'
    comps, unknown = _comps3(ctx)
    if not comps:
        return 'kdu', 'Bölüm 3 okunamadı — UN karşılaştırması yapılmadı.'
    try:
        from app.services.transport_engine import classify, build_transport_components
        h = sorted(_h(_sub(ctx['secs'].get('2', ''), '2.1', '2.2')))
        r = classify(h, form=form, components=build_transport_components(comps))
    except Exception as e:
        return 'kdu', f'UN yeniden hesaplanamadı: {e}'
    exp = re.sub(r'\D', '', ((r or {}).get('road') or {}).get('un') or '')
    if not exp or r.get('not_regulated'):
        return 'kdu', f'Bölüm 3 ve 2.1\'den taşıma sınıfı çıkmadı; 14.1\'de UN {sorted(uns)} var — KDU kontrol etmeli.'
    if exp in uns:
        return 'uygun', f'UN {exp} Bölüm 3 bileşimi ve 2.1 sınıflandırmasıyla uyumlu (ADR Tablo A).'
    note = f' (verisi okunamayan: {unknown})' if unknown else ''
    return 'kdu', (f'Bölüm 3 bileşimi ve 2.1 sınıflandırmasıyla UN {exp} bekleniyor; 14.1\'de UN {sorted(uns)} var '
                   f'(ADR 3.1.2.8.1: Tablo A\'da adlı giriş varsa B.B.B. yerine o kullanılır){note} — KDU kontrol etmeli.')


def c_md6c(ctx):
    """SEA Md.6(1)(c): Ek-6'da olan maddede Ek-6'da bulunmayan sınıflar da değerlendirilir. Kayıt yaptıranın
    sınıflandırmasında (ECHA kayıt dosyası 2.1 GHS) olup Ek-6'da olmayan sınıf 2.1'de yoksa KDU'ya bildirilir."""
    from app.services.substance_lookup import lookup_substance
    comps, _u = _comps3(ctx)
    if not comps:
        return 'kdu', 'Bölüm 3 okunamadı.'
    ana = max(comps, key=lambda c: c['conc'])
    try:
        lk = lookup_substance(ana['cas'], 'liquid' if 'form:sivi' in ctx['facts'] else '')
    except Exception:
        lk = {}
    src = lk.get('classification_sources') or {}
    reg = sorted({h for h, v in src.items() if 'kayıt yaptıranın' in str(v)})
    if not reg:
        return 'uygun', f"{ana['cas']}: kayıt yaptıranın Ek-6 dışı sınıfı yok (veya kayıt dosyası verisi önbellekte yok)."
    given = _h(_sub(ctx['secs'].get('2', ''), '2.1', '2.2'))
    yok = [h for h in reg if h not in given and h[:4] not in {g[:4] for g in given}]
    if not yok:
        return 'uygun', f"{ana['cas']}: kayıt yaptıranın Ek-6 dışı sınıfları ({', '.join(reg)}) 2.1'de var."
    return 'kdu', (f"{ana['cas']}: kayıt yaptıranın sınıflandırmasında Ek-6'da olmayan {', '.join(yok)} var "
                   f"({src[yok[0]]}); 2.1'de yok — SEA Md.6(1)(c) gereği değerlendirilmeli.")


def c_16_kdu(ctx):
    """KKDİK Usul ve Esaslar (05.08.2025) Md.16(2): 16. bölümde KDU iletişim bilgisi + yeterlilik belgesi tarihi ve no."""
    s16 = ctx['secs'].get('16', '')
    # Usul ve Esaslar Md.16(2) "KDU" kelimesini zorunlu tutmaz; hazırlayanın iletişim bilgisi ve yeterlilik belgesinin
    # tarih / numarası yeterlidir ("Düzenleyen … Sertifika Numarası … Sertifika Tarihi" biçimi de kabul)
    _hazirlayan = re.search(r'(?i)(düzenleyen|hazırlayan|hazırlayan kişi|prepared by)[\s\S]{0,200}?(sertifika|belge)', s16)
    if not re.search(r'(?i)kimyasal\s+de[ğg]erlendirme\s+uzman|\bKDU\b', s16) and not _hazirlayan:
        return 'eksik', '16. bölümde GBF\'yi hazırlayan KDU belirtilmemiş (KKDİK Usul ve Esaslar Md.16(2)).'
    eksik = []
    if not re.search(r'[^@\s]+@[^@\s]+\.\w+|\+?\d[\d\s()-]{8,}\d', s16):
        eksik.append('iletişim bilgisi (e-posta/telefon)')
    if not re.search(r'(?i)(belge|sertifika|yeterlilik)[^\n]{0,40}(no|numaras)', s16):
        eksik.append('yeterlilik belgesi numarası')
    if not re.search(r'(?i)(belge|sertifika|yeterlilik)[\s\S]{0,80}?\d{1,2}[./-]\d{1,2}[./-]\d{4}|tarih[\s\S]{0,30}?\d{1,2}[./-]\d{1,2}[./-]\d{4}', s16):
        eksik.append('yeterlilik belgesi tarihi')
    # Yeterlilik belgesi tarihi ileri bir tarih olamaz
    from datetime import date as _date
    # GBF'nin tarihi (başlık / hazırlanma / revizyon tarihi) — belge bu tarihte geçerli olmalı (Ek-18: beş yıl)
    _gm = re.search(r'(?i)(?:hazırlanma\s+tarihi|revizyon\s+tarihi|Rev\.\s*\d+\s*\|)\s*[:|]?\s*(\d{1,2})[./-](\d{1,2})[./-](\d{4})', ctx['text'])
    try:
        _gbf_t = _date(int(_gm.group(3)), int(_gm.group(2)), int(_gm.group(1))) if _gm else _date.today()
    except ValueError:
        _gbf_t = _date.today()
    for _m in re.finditer(r'(?i)(?:belge|sertifika|yeterlilik)[^\n]{0,40}tarih[^\d]{0,30}(\d{1,2})[./-](\d{1,2})[./-](\d{4})', s16):
        try:
            _bt = _date(int(_m.group(3)), int(_m.group(2)), int(_m.group(1)))
        except ValueError:
            eksik.append('yeterlilik belgesi tarihi geçersiz')
            continue
        if _bt > _gbf_t:
            eksik.append(f'yeterlilik belgesi tarihi GBF tarihinden ileri ({_m.group(0)[-10:]}) — belgenin veriliş tarihi yazılmalı')
        else:
            try:
                _son = _bt.replace(year=_bt.year + 5)
            except ValueError:
                _son = _bt.replace(year=_bt.year + 5, day=28)
            if _son < _gbf_t:
                eksik.append(f"yeterlilik belgesinin süresi GBF tarihinde dolmuş ({_son.strftime('%d.%m.%Y')}; KKDİK Ek-18: beş yıl)")
    return (('uygun', 'KDU iletişim bilgisi ile yeterlilik belgesi numarası ve tarihi 16. bölümde var.') if not eksik else
            ('eksik', '16. bölümde KDU var ama eksik: ' + ', '.join(eksik) + ' (KKDİK Usul ve Esaslar Md.16(2)).'))


def c_16_celiski(ctx):
    """16. bölüm kendi içinde ve 2.1 ile çelişmemeli: KDU bilgisi verilmişken "onaylanmamıştır / yasal geçerliliği
    yoktur" uyarısı; 2.1'de "test yapılmadı / ihtiyatlı" denen sınıf için 16'da "test verisi" yöntemi."""
    s16 = ctx['secs'].get('16', '')
    s2 = ctx['secs'].get('2', '')
    sorun = []
    if re.search(r'(?i)kimyasal\s+de[ğg]erlendirme\s+uzman|\bKDU\b', s16) and \
            re.search(r'(?i)yasal\s+geçerliliği\s+bulunmamaktadır|onaylanmamıştır', s16):
        sorun.append('KDU bilgisi verilmişken "onaylanmamıştır / yasal geçerliliği bulunmamaktadır" uyarısı var')
    if re.search(r'(?i)test\s+yapılmadı|ihtiyatlı', s2) and re.search(r'(?i)test\s+verisi\s*/\s*üretici\s+beyanı', s16):
        sorun.append("2.1'de test yapılmadan (ihtiyatlı) sınıflandırılan sınıf için 16'da \"test verisi / üretici beyanı\" yazıyor")
    return ('eksik', '; '.join(sorun) + '.') if sorun else ('uygun', '16. bölümde çelişki bulunmadı.')


def c_15_bekra_hal(ctx):
    """BEKRA Ek-1 Bölüm 2 kaydı maddenin belirli hâlini adlandırıyorsa ("Hidrojen klorür (Sıvılaştırılmış gaz)",
    "Susuz amonyak") yalnız o hâldeki ürüne uygulanır; sulu çözelti / sıvı ürün kapsam dışıdır."""
    s15 = ctx['secs'].get('15', '')
    m = re.search(r'(?i)[^.;\n]*(?:\(sıvılaştırılmış gaz\)|susuz amonyak)[^.;\n]*', s15)
    if not m:
        return 'uygun', 'BEKRA hâl nitelikli adlandırılmış madde yok.'
    if 'form:gaz' in ctx['facts']:
        return 'uygun', f'Gaz ürün — {m.group(0).strip()[:80]}'
    return 'eksik', (f"Bölüm 15 BEKRA: \"{m.group(0).strip()[:90]}\" — kayıt maddenin gaz / susuz hâlini adlandırır; "
                     'ürün gaz değil (sulu çözelti / sıvı), Ek-1 Bölüm 2 bu kayıtla uygulanmaz.')


def c_9_gaz_bilesen(ctx):
    """Sıvı karışımın Bölüm 9'unda "en düşük kaynama noktalı / en uçucu bileşen" olarak çözünmüş gazın (kaynama
    noktası < 20 °C) değeri verilmemeli — ürünün yanında yanıltıcıdır (örn. %32 HCl'de −85 °C, 46 200 hPa)."""
    if 'form:sivi' not in ctx['facts']:
        return 'uygun', 'Sıvı ürün değil.'
    s9 = ctx['secs'].get('9', '')
    m = re.search(r'(?i)en\s+düşük\s+kaynama\s+noktalı\s+bileşen:\s*([^\n(]*?)\s(-\d+(?:[.,]\d+)?|\d+(?:[.,]\d+)?)\s*°\s*C', s9)
    if m:
        try:
            v = float(m.group(2).replace(',', '.'))
        except ValueError:
            v = None
        if v is not None and v < 20:
            return 'eksik', (f'Bölüm 9: sıvı karışımda "{m.group(1).strip()} {m.group(2)} °C" (oda sıcaklığında gaz) '
                             'en düşük kaynama noktalı bileşen olarak verilmiş — çözünmüş gazın değeri ürünü yansıtmaz.')
    return 'uygun', 'Bölüm 9\'da gaz hâlindeki bileşen değeri yok.'


def c_t_madde(ctx):
    """GBF "tek madde" diyorsa Bölüm 3'teki bileşen derişimi ≥ %80 olmalı (ECHA Madde Tanımlama Rehberi —
    tek bileşenli madde). %32 HCl'yi "madde" sayan GBF bunu karşılamaz."""
    t = '\n'.join(ctx['secs'].values())
    if not re.search(r'(?i)ürün\s+tek\s+bir\s+maddedir', t):
        return 'uygun', 'GBF ürünü tek madde olarak tanımlamıyor.'
    comps, _u = _comps3(ctx)
    if not comps:
        return 'eksik', "GBF ürünü tek madde olarak tanımlıyor ama Bölüm 3'te madde kimliği yok (KKDİK Ek-2 3.1)."
    ust = max(c['conc'] for c in comps)
    if ust < 80:
        return 'eksik', (f"GBF ürünü tek madde olarak tanımlıyor ama Bölüm 3'teki derişim üst sınırı %{ust:g} — "
                         'ürün karışımdır (3.2 Karışımlar; karışım sınıflandırma yöntemleri uygulanmalı).')
    return 'uygun', f'Tek madde; Bölüm 3 derişimi %{ust:g}.'


def c_euh071(ctx):
    """SEA Ek-2 madde 105: EUH071 yalnız soluma toksisitesi (aşındırma mekanizması) ya da H314 + soluma testi yok +
    solunabilir ürün için. H314 olup EUH071 yoksa KDU solunabilirliği değerlendirir; dayanaksız EUH071 eksiktir."""
    s2 = ctx['secs'].get('2', '')
    if not s2.strip():
        return 'kdu', '2. bölüm okunamadı — EUH071 kontrolü yapılamadı.'
    h21 = {h[:4] for h in _h(_sub(s2, '2.1', '2.2'))}
    has71 = bool(re.search(r'EUH\s*071', s2))
    if has71 and not (h21 & {'H314', 'H330', 'H331', 'H332'}):
        return 'eksik', ('2. bölümde EUH071 var ama karışım ne cilt aşındırıcı (H314) ne de soluma toksisitesiyle '
                         'sınıflandırılmış (SEA Ek-2 madde 105).')
    if 'H314' in h21 and not has71:
        return 'kdu', ('Karışım H314; akut soluma test verisi yoksa ve ürün solunabiliyorsa (sprey/buhar/toz) EUH071 '
                       'gerekir (SEA Ek-2 madde 105) — KDU ürünün solunabilirliğini değerlendirmeli.')
    return 'uygun', 'EUH071 kullanımı SEA Ek-2 madde 105 ile tutarlı.'

# ADR Tablo A — sıkıştırılmış / sıvılaştırılmış hâlin adlı girişi → soğutulmuş sıvı hâlinin girişi
_GAZ_SOGUTULMUS = {'1072': '1073', '1066': '1977', '1006': '1951', '1046': '1963', '1049': '1966', '1971': '1972',
                   '1065': '1913', '1056': '1970', '2036': '2591', '1013': '2187', '1070': '2201', '1962': '1038',
                   '1035': '1961', '1002': '1003'}


def c_gaz_grup(ctx):
    """SEA Ek-1 2.5 / Ek-6 Not U: basınç altındaki gaz tek gruptadır — H280 ile H281 birlikte olmaz. Soğutulmuş
    sıvılaştırılmış gazda (H281) taşıma, maddenin soğutulmuş sıvı adlı girişiyle yapılır (örn. oksijen UN1073, UN1072
    değil; ADR 2.2.2.1.2)."""
    s2 = ctx['secs'].get('2', '')
    h = {x[:4] for x in _h(s2)}
    if not h & {'H280', 'H281'}:
        return 'uygun', 'Basınç altındaki gaz sınıfı yok.'
    if {'H280', 'H281'} <= h:
        return 'eksik', ('2. bölümde H280 ve H281 birlikte — basınç altındaki gaz tek gruptadır (sıkıştırılmış / '
                         'sıvılaştırılmış / soğutulmuş sıvılaştırılmış / çözünmüş; SEA Ek-1 2.5, Ek-6 Not U).')
    m = re.search(r'UN\s*(\d{4})', ctx['secs'].get('14', ''))
    if 'H281' in h and m and m.group(1) in _GAZ_SOGUTULMUS:
        return 'eksik', (f"Ürün soğutulmuş sıvılaştırılmış gaz (H281) ama 14.1 UN{m.group(1)} sıkıştırılmış / "
                         f"sıvılaştırılmış hâlin girişi — soğutulmuş sıvı girişi UN{_GAZ_SOGUTULMUS[m.group(1)]} "
                         '(ADR Tablo A, 2.2.2.1.2).')
    return 'uygun', 'Basınç altındaki gaz grubu ve taşıma girişi tutarlı.'


def c_p_bilesik(ctx):
    """Birleşik önlem ifadesi tek ifadeyi kapsar — aynı listede hem P410+P403 hem P403 yazılmaz."""
    s2 = _sub(ctx['secs'].get('2', ''), '2.2', '2.3')
    ps = set(re.findall(r'P\d{3}(?:\s*\+\s*P\d{3})*', s2))
    ps = {re.sub(r'\s+', '', p) for p in ps}
    tek = {p for p in ps if '+' not in p}
    ic = {x for p in ps if '+' in p for x in p.split('+')}
    cift = sorted(tek & ic)
    if cift:
        return 'eksik', f"2.2'de {', '.join(cift)} hem tek başına hem birleşik ifade içinde yazılmış."
    return 'uygun', 'Önlem ifadelerinde tekrar yok.'


def c_euh066(ctx):
    """SEA Ek-2 madde 103: EUH066 yalnız cilt tahrişi (Ek-1 3.2) kriterlerini karşılamayan ürün için — 2.1'de H315 / H314
    varken EUH066 kullanılmaz."""
    s2 = ctx['secs'].get('2', '')
    if not s2.strip():
        return 'kdu', '2. bölüm okunamadı — EUH066 kontrolü yapılamadı.'
    h21 = {h[:4] for h in _h(_sub(s2, '2.1', '2.2'))}
    if re.search(r'EUH\s*066', s2) and h21 & {'H314', 'H315'}:
        return 'eksik', ('2. bölümde EUH066 var ama ürün cilt tahrişi / aşınması (H315 / H314) ile sınıflandırılmış — '
                         'EUH066 yalnız bu kriterleri karşılamayan ürün içindir (SEA Ek-2 madde 103).')
    return 'uygun', 'EUH066 kullanımı SEA Ek-2 madde 103 ile tutarlı.'


CHECKS: Dict[str, Callable] = {
    '3.2-sira': c_32_sira, '3.2-neden': c_32_neden, '3.2-kayit': c_32_kayit, '8.1-bld': c_bld,
    '15.1-izin-kisit': c_izin_kisit, '2.2-ek-unsur': c_ek_unsur, '8.1-oel-kanserojen': c_oel_kanserojen,
    'G-basliklar': c_basliklar, 'G-tarih': c_tarih, 'G-surum': c_surum, 'G-sayfa': c_sayfa,
    'G-bos-alt': c_bos_alt, 'G-dil': c_dil, 'G-yasak-ifade': c_yasak, '1.3-eposta': c_eposta,
    '1.4-zehir': c_zehir, '2.1-h-atif': c_h_atif, '2.2-uyari-tek': c_uyari_tek, '2.2-h': c_22_h,
    '2.2-p': c_22_p, '2.2-p-sayi': c_p_sayi, '2.2-bilesen': c_bilesen, '2.2-tutarlilik': c_22_tutarlilik,
    '3.2-liste': c_32_liste, '3.2-konsantrasyon': c_32_konsantrasyon, '3.2-sinif': c_32_sinif, '3.2-ec': c_32_ec,
    '3.2-svhc': c_32_svhc, '8.1-oel': c_oel, '9.1-ozellikler': c_91, '11.1-siniflar': c_111_siniflar,
    '11.1-ifade': c_111_ifade, '14.1-un': c_un, '14.3-sinif': c_sinif14, '14.4-pg': c_pg,
    '15.1-svhc': c_15_svhc, '15.1-deterjan': c_deterjan, '16-tam-metin': c_tam_metin, 'T-14-2': c_t14,
    'T-3-2': c_t32, 'T-hesap': c_hesap, 'T-un': c_t_un, 'T-md6c': c_md6c, '16-kdu': c_16_kdu, '16-celiski': c_16_celiski, 'T-madde': c_t_madde, '15-bekra-hal': c_15_bekra_hal, '9-gaz-bilesen': c_9_gaz_bilesen, '2.2-euh071': c_euh071, '2.2-euh066': c_euh066, '2.1-gaz-grup': c_gaz_grup, '2.2-p-bilesik': c_p_bilesik,
    '16-revizyon': c_16_revizyon, '8.1-dnel': c_dnel, '8.2.2-eldiven-malzeme': c_eldiven_malzeme,
    '8.2.2-eldiven-kalinlik': c_eldiven_kalinlik, '8.2.2-eldiven-sure': c_eldiven_sure,
    '9-ampirik': c_9_ampirik, '9.1-neden': c_9_neden, '9-fp-sinif': c_9_fp_sinif, '9-h304-visk': c_9_h304,
    '2.3-toz-tutarlilik': c_toz_tutarlilik, '14-oh375': c_oh375, '16-md10': c_md10,
}


def run_code_checks(pages: List[str], facts: set = None) -> dict:
    """Kod kontrolleri. Döner: {facts, sonuclar:[{id, bolum, dayanak, onem, soru, karar, aciklama}]}"""
    from app.services.audit_jev import load_checklist, applies
    text = '\n'.join(pages)
    secs = split_sections(text)
    facts = facts if facts is not None else derive_facts(secs, text)
    ctx = {'pages': pages, 'text': text, 'secs': secs, 'facts': facts}
    out = []
    for q in load_checklist()['sorular']:
        if q['yontem'] not in ('kod', 'gorsel', 'kdu') or not applies(q['kosul'], facts):
            continue
        base = {'id': q['id'], 'bolum': q['bolum'], 'dayanak': q['dayanak'], 'onem': q['onem'], 'soru': q['soru_tr']}
        if q['yontem'] == 'kdu':
            out.append({**base, 'karar': 'kdu', 'aciklama': q.get('not') or 'Metinden doğrulanamaz; KDU kontrol etmeli.'})
            continue
        if q['yontem'] == 'gorsel':
            out.append({**base, 'karar': 'kdu', 'aciklama': 'Piktogramlar resim olarak basılı; KDU görsel olarak kontrol etmeli.'})
            continue
        fn = CHECKS.get(q['id'])
        if not fn:
            out.append({**base, 'karar': 'kontrol_yok', 'aciklama': 'Bu madde için otomatik kontrol henüz yok.'})
            continue
        try:
            k, a = fn(ctx)
        except Exception as e:
            k, a = 'kdu', f'Kontrol çalıştırılamadı: {e}'
        out.append({**base, 'karar': k, 'aciklama': a})
    return {'facts': sorted(facts), 'sonuclar': out}
