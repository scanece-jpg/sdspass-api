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
                       r'tehlike\s+işaret\w*|tehlike\s+bilgi\w*')


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
    p1 = ctx['pages'][0] if ctx['pages'] else ''
    return ('uygun', 'İlk sayfada sürüm/revizyon numarası var.') if re.search(
        r'(?i)\b(rev(?:izyon)?\.?(?:\s*no)?|sürüm|versiyon|version|düzenleme)\s*[:.]?\s*\d', p1) else \
           ('eksik', 'İlk sayfada sürüm/revizyon numarası bulunamadı.')


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
          ('h) patlama limitleri', r'patlay[ıi]c[ıi] limit|patlama limit|alevlenirlik limit|üst/alt|alt patlay|üst patlay'),
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


_CLASSES = [('a) akut toksisite', r'akut toksisite'), ('b) cilt aşınması/tahrişi', r'cilt aşın|deri korozyon|cilt tahriş|deri tahriş|ciltte aşın'),
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
    m = re.search(r'\bUN\s*(\d{4})\b|UN Numaras[ıi][^\d]{0,30}(\d{4})', s14, re.I)
    return ('uygun', f'UN {m.group(1) or m.group(2)}') if m else ('eksik', '14.1\'de UN numarası bulunamadı.')


def c_sinif14(ctx):
    s14 = ctx['secs'].get('14', '')
    return ('uygun', 'Taşımacılık sınıfı var.') if re.search(r'(?i)(?:sınıf|class|zararlar[ıi])\s*[:\-]?\s*\d(?:\.\d)?', s14) \
        else ('eksik', '14.3\'te taşımacılık sınıfı bulunamadı.')


def c_pg(ctx):
    s14 = ctx['secs'].get('14', '')
    return ('uygun', 'Ambalaj grubu var.') if re.search(r'(?i)ambalaj(?:lama)? grubu\s*[:\-]?\s*(?:I{1,3}\b|uygulanamaz|yok)', s14) \
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
    h = _h(ctx['secs'].get('2', ''))
    s14 = ctx['secs'].get('14', '')
    exp = []
    if 'H314' in h:
        exp.append('8')
    if h & {'H224', 'H225', 'H226'}:
        exp.append('3')
    # Aerosol → UN 1950 (Sınıf 2); gaz: alevlenir → 2.1, yalnız basınçlı gaz → 2.2 (ADR 2.2.2.1.5);
    # oksitleyici katı/sıvı → 5.1 (ADR 2.2.51)
    if h & {'H222', 'H223', 'H229'}:
        return (('uygun', 'Aerosol: UN 1950 14\'te var.') if re.search(r'(?i)\bUN\s*1950\b', s14) else
                ('eksik', '2. bölümde aerosol sınıflandırması var; 14\'te UN 1950 bulunamadı.'))
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


_RANGE_GE = re.compile(r'(?:[>≥]=?|&gt;=?)\s*(\d+(?:[.,]\d+)?)\s*%?\s*[-–]\s*([<≤]=?|&lt;=?)\s*(\d+(?:[.,]\d+)?)')
# Yalnız üst sınır: "< 0,1%" (alt sınırsız aralık)
_RANGE_LT = re.compile(r'(?<![\d.,])(?:<|&lt;)\s*(\d+(?:[.,]\d+)?)\s*%')


def _segments3(ctx):
    """Bölüm 3 satırları: her CAS'tan bir sonraki CAS'a kadar olan metin (tablo satırı yaklaşımı)."""
    cas, s3 = _rows3(ctx)
    pos = [(c, s3.find(c)) for c in cas]
    pos = sorted([p for p in pos if p[1] >= 0], key=lambda x: x[1])
    return [(c, s3[i:(pos[k + 1][1] if k + 1 < len(pos) else len(s3))]) for k, (c, i) in enumerate(pos)], s3


def _comps3(ctx):
    """Bölüm 3'ten bileşenler: CAS, konsantrasyon üst değeri, veritabanı tehlikeleri. (comps, okunamayanlar)"""
    if '_comps3' in ctx:
        return ctx['_comps3']
    from app.services.substance_lookup import lookup_substance
    segs, s3 = _segments3(ctx)
    comps, unknown = [], []
    for c, seg in segs:
        i = s3.find(c)
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
                      'hazards': lk.get('hazards') or [],
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
    'T-3-2': c_t32, 'T-hesap': c_hesap,
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
