"""
GBF denetimi — Jev katmanı (TypeSafe Jev, "System One" karar modeli).

data/sds_audit_checklist.json'daki yontem == 'jev' sorularını bir GBF metni üzerinde çalıştırır:
  1. Metin 16 bölüme ayrılır (split_sections)
  2. Ürünün koşulları metinden çıkarılır (derive_facts) → yalnız ilgili sorular sorulur
  3. Kişisel veri (ad, telefon, e-posta) dış servise gitmeden maskelenir (mask_personal)
  4. Sorular bölüm gruplarıyla Jev'e gönderilir; karar: uygun / kdu (KDU baksın) / eksik

Jev REST: POST https://api.typesafe.ai/v1/systemone (Authorization: Bearer TYPESAFE_API_KEY).
SDK yerine httpx kullanılır (uygulamanın sabit httpx sürümüyle çakışmasın diye).
Pilot (2026-10-02): 177 doğrulanmış cevapta %97,7 doğruluk.
"""
import asyncio
import json
import os
import re
from typing import Dict, List, Optional

import httpx

_CK_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'sds_audit_checklist.json')
JEV_URL = 'https://api.typesafe.ai/v1/systemone'
JEV_MODEL = 'jev-latest'
MAX_Q_PER_CALL = 12        # bir istekte en fazla soru
MAX_STATE_CHARS = 60000    # Jev sınırı: tek soru + durum ≤ 32k token — güvenli pay
P_OK, P_KDU = 0.65, 0.35   # noul kararı: ≥ 0,65 uygun; 0,35–0,65 KDU baksın; < 0,35 eksik


def load_checklist() -> dict:
    with open(_CK_PATH, encoding='utf-8') as f:
        return json.load(f)


# ── 1. Bölümlere ayırma ─────────────────────────────────────────────────────────
# "BÖLÜM 3:" / "SECTION 3:" ya da numara önde "3. BÖLÜM:" (Habaş gaz GBF'leri, 2026-10-10)
_SEC_RE = re.compile(r'(?im)^\s*(?:(?:B[ÖO]L[ÜU]M|SECTION)\s*(\d{1,2})\s*[:.\-–]|(\d{1,2})\s*\.\s*B[ÖO]L[ÜU]M\s*:)')


# "BÖLÜM n" yazılmayan GBF'ler: "1. MADDENİN/KARIŞIMIN …", "8. MARUZ KALMA …" — numara + büyük harfli başlık
# (alt başlıklar "1.1." ile ayrılır: numaradan sonra boşluk gelir). Önceden bu biçimde bölümler bulunamıyor,
# e-posta / 114 / Bölüm 3 / KDU gibi var olan bilgiler "eksik" sayılıyordu (Hyper Hypo GBF, 2026-10-10).
# Nokta ile başlık arasında boşluk olmayabilir ("1.MADDENİN/KARIŞIMIN…" — Baystar GBF'si, 2026-10-10)
_SEC_RE_NUM = re.compile(r"(?m)^\s*(\d{1,2})\s*[.)]\s*(?=[A-ZÇĞİÖŞÜ][A-ZÇĞİÖŞÜ/,'’ \-]{6,})")


def split_sections(text: str) -> Dict[str, str]:
    """Her bölüm numarasının ilk başlığından bir sonrakine kadar olan metin."""
    first = {}
    for m in _SEC_RE.finditer(text or ''):
        n = int(m.group(1) or m.group(2))
        if 1 <= n <= 16 and n not in first:
            first[n] = m.start()
    if len(first) < 8:
        # Yedek: numaralı büyük harfli başlıklar — sıra korunarak (her bölüm bir öncekinden sonra gelmeli)
        alt, son = {}, -1
        for m in _SEC_RE_NUM.finditer(text or ''):
            n = int(m.group(1))
            if 1 <= n <= 16 and n not in alt and m.start() > son and all(k < n for k in alt):
                alt[n] = m.start()
                son = m.start()
        if len(alt) > len(first):
            first = alt
    order = sorted(first.items(), key=lambda x: x[1])
    return {str(n): text[pos:(order[i + 1][1] if i + 1 < len(order) else len(text))]
            for i, (n, pos) in enumerate(order)}


# ── 2. Koşulları metinden çıkarma ───────────────────────────────────────────────
def derive_facts(secs: Dict[str, str], full_text: str = '') -> set:
    """Checklist 'kosul' sözlüğündeki anahtarlar + H kodları (örn. 'H314')."""
    f = set()
    s2, s3, s8 = secs.get('2', ''), secs.get('3', ''), secs.get('8', '')
    s9, s14, s15 = secs.get('9', ''), secs.get('14', ''), secs.get('15', '')
    hs = set(re.findall(r'\b(H\d{3}[A-Za-z]{0,2}|EUH\d{3})\b', s2))
    f |= {h[:4] if h.startswith('H') and not h.startswith('EUH') else h for h in hs}
    if any(h.startswith('H') and not h.startswith('EUH') for h in hs):
        f.add('siniflandirilmis')
        # SEA Ek-1 Tablo 4.1.4 / 3.7.3: yalnız bu sınıflarda uyarı kelimesi kullanılmaz
        if {h[:4] for h in hs if not h.startswith('EUH')} - {'H411', 'H412', 'H413', 'H362'}:
            f.add('uyari_kelimesi')
    else:
        f.add('siniflandirilmamis')
    low3 = s3.lower()
    if re.search(r'\b3\.1\b', s3) and not re.search(r'\b3\.2\b', s3) or 'madde tipi : madde' in low3:
        f.add('madde')
    else:
        f.add('karisim')
    # Fiziksel hal yalnız 9.1(a) "Görünüm / Fiziksel hal" satırından — "Alevlenirlik (katı, gaz)" gibi
    # özellik adları yanıltmasın
    m9 = re.search(r'(?is)(?:görünüm|fiziksel\s+(?:hal|durum)|physical\s+state|appearance)\s*[:\-]?\s*(.{0,80})', s9)
    look = (m9.group(1) if m9 else '').lower()
    if re.search(r'aerosol', look):
        f.add('form:aerosol')
    elif re.search(r'\bgaz\b|\bgas\b', look):
        f.add('form:gaz')
    elif re.search(r'\btoz\b|\bkatı\b|\bpowder\b|\bsolid\b|granül|tablet|kristal|pul\b', look):
        f.add('form:kati')
    else:
        f.add('form:sivi')
    if re.search(r'\d\s*(mg/m[³3]|ppm)', s8, re.I):
        f.add('oel')
    if re.search(r'\bUN\s*\d{4}\b|UN Numaras[ıi].{0,40}\b\d{4}\b', s14, re.I | re.S):
        f.add('tehlikeli_mal')
        if re.search(r'B\.\s?B\.\s?B\.|N\.\s?O\.\s?S\.', s14):
            f.add('bbb')
    else:
        f.add('tehlikeli_mal_degil')
    if re.search(r'deterjan', s15, re.I):
        f.add('deterjan')
    if re.search(r'toz[- ]hava karışımı|toz patlama', full_text, re.I):
        f.add('toz_patlamasi')
    if _is_revision(full_text):
        f.add('revizyon')
    return f


# "Rev.281", "Revizyon No 2", "Sürüm 1.1", "Kaçıncı düzenleme olduğu : 1.0" — tarih ("02.10.2026") sayılmaz
_REV = re.compile(r'(?i)\b(?:rev(?:izyon)?\.?(?:\s*no)?|sürüm|versiyon|version|düzenleme olduğu)\s*[:.]?\s*'
                  r'(\d+)(?:[.,](\d+))?(?![.,]?\d*[.,]\d{4})(?!\d)')


def _is_revision(text: str) -> bool:
    for m in _REV.finditer(text or ''):
        major, minor = int(m.group(1)), int(m.group(2) or 0)
        if major > 1 or minor > 0:
            return True
    return False


def applies(kosul: str, facts: set) -> bool:
    for part in kosul.split(','):
        if part == 'her':
            continue
        if part.startswith('h:'):
            if not any(h in facts for h in part[2:].split('|')):
                return False
        elif part not in facts:
            return False
    return True


# ── 3. Kişisel veri maskeleme ───────────────────────────────────────────────────
_EMAIL = re.compile(r'[\w.+-]+@[\w-]+\.[\w.-]+')
_PHONE = re.compile(r'(?<!\d)(?:\+?\d[\d ()\-]{8,}\d)(?!\d)')
_NAME_FIELDS = re.compile(
    r'((?:İsim,?\s*Soyisim|Ad[ıi]?,?\s*Soyad[ıi]?|Ad Soyad|Hazırlayan(?: kişi)?|Yetkili kişi|İlgili kişi)\s*[:\-]\s*)'
    r'([^\n:]{2,60}?)(?=\s{2,}|\n|Sertifika|Belge|$)', re.I)


def mask_personal(text: str) -> str:
    """Ad/soyad alanları, e-posta ve telefon numaraları yer tutucuyla değiştirilir. Acil numara 114 korunur."""
    text = _NAME_FIELDS.sub(lambda m: m.group(1) + 'Ad Soyad ', text or '')
    text = _EMAIL.sub('eposta@ornek.com', text)
    return _PHONE.sub('+90 000 000 00 00', text)


# ── 4. Jev çağrısı ve karar ─────────────────────────────────────────────────────
def _verdict(q: dict, ans: dict):
    if q.get('tur') == 'choice':
        c = ans.get('choice')
        p = (ans.get('probabilities') or {}).get(c, 0)
        v = 'uygun' if c in q.get('kabul', []) else 'kdu' if c in q.get('kdu', []) else 'eksik'
        return v, c, round(float(p or 0), 3)
    p = float(ans.get('noul') or 0)
    if q.get('ters'):
        p = 1 - p
    v = 'uygun' if p >= P_OK else 'kdu' if p >= P_KDU else 'eksik'
    return v, None, round(p, 3)


async def _ask(client: httpx.AsyncClient, key: str, state: str, part: List[dict]) -> dict:
    questions = {}
    for q in part:
        qk = q['id'].replace('.', '_').replace('-', '_')
        questions[qk] = ({'type': 'choice', 'instructions': q['soru_en'], 'criteria': q['secenekler']}
                         if q.get('tur') == 'choice' else {'type': 'noul', 'instructions': q['soru_en']})
    r = await client.post(JEV_URL, headers={'Authorization': f'Bearer {key}'},
                          json={'state': state[:MAX_STATE_CHARS], 'model': JEV_MODEL, 'questions': questions})
    r.raise_for_status()
    return r.json()


async def run_jev_audit(text: str, facts: Optional[set] = None, only: Optional[set] = None,
                        concurrency: int = 4) -> dict:
    """GBF metnini Jev sorularıyla denetler.
    Döner: {facts, sonuclar:[{id, bolum, dayanak, onem, soru, karar, secim, p}], token, hatalar}"""
    key = os.environ.get('TYPESAFE_API_KEY', '').strip()
    if not key:
        raise RuntimeError('TYPESAFE_API_KEY tanımlı değil')
    secs = {k: mask_personal(v) for k, v in split_sections(text).items()}
    facts = facts if facts is not None else derive_facts(secs, text)
    ck = load_checklist()
    qs = [q for q in ck['sorular'] if q['yontem'] == 'jev' and applies(q['kosul'], facts)
          and (only is None or q['id'] in only)]
    groups: Dict[tuple, List[dict]] = {}
    for q in qs:
        groups.setdefault(tuple(q.get('bolumler') or []), []).append(q)
    jobs = [(bl, items[i:i + MAX_Q_PER_CALL]) for bl, items in groups.items()
            for i in range(0, len(items), MAX_Q_PER_CALL)]
    sem = asyncio.Semaphore(concurrency)
    results, errors, tokens = [], [], 0

    async with httpx.AsyncClient(timeout=90) as client:
        async def one(bl, part):
            nonlocal tokens
            state = '\n\n'.join(secs.get(b, '') for b in bl)
            async with sem:
                try:
                    data = await _ask(client, key, state, part)
                except Exception as e:   # bir grup hata verirse diğerleri sürer; sorular "KDU baksın" olur
                    errors.append(f'{",".join(bl)}: {e}')
                    for q in part:
                        results.append({'id': q['id'], 'bolum': q['bolum'], 'dayanak': q['dayanak'],
                                        'onem': q['onem'], 'soru': q['soru_tr'], 'karar': 'kdu',
                                        'secim': None, 'p': None, 'hata': True})
                    return
            tokens += int((data.get('usage') or {}).get('input_tokens') or 0)
            ans = data.get('answers') or {}
            for q in part:
                v, c, p = _verdict(q, ans.get(q['id'].replace('.', '_').replace('-', '_'), {}))
                if not state.strip():   # bölüm GBF'de hiç yoksa soru cevaplanamaz → eksik
                    v, p = 'eksik', 0.0
                results.append({'id': q['id'], 'bolum': q['bolum'], 'dayanak': q['dayanak'],
                                'onem': q['onem'], 'soru': q['soru_tr'], 'karar': v, 'secim': c, 'p': p})
        await asyncio.gather(*(one(bl, part) for bl, part in jobs))

    order = {q['id']: n for n, q in enumerate(ck['sorular'])}
    results.sort(key=lambda x: order.get(x['id'], 0))
    return {'facts': sorted(facts), 'sonuclar': results, 'token': tokens, 'hatalar': errors}
