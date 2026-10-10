"""
Bileşen (madde) fiziksel verileri — kaynağı belli, ölçüme dayanan değerler.

Kaynak sırası (madde başına, alan alan):
  1. ECHA kayıt dosyası — "Key value for assessment" (KKDİK/REACH kaydında kayıt yaptıranın değerlendirdiği
     anahtar değer; çoğunlukla el kitabı veya deney verisi). chem.echa.europa.eu, tek madde, isteğe bağlı okuma.
  2. PubChem "Experimental Properties" (kaynak adıyla — HSDB, ILO-ICSC vb.) — ECHA'da kaydı / değeri yoksa.
  Hiçbiri yoksa değer bilinmiyor sayılır (sınıflandırmada en kötü durum; Bölüm 9'da "veri yok").

Kullanım yerleri:
  • Sınıflandırma (physical_engine): bileşen parlama noktası (kaydında alevlenir sınıfı olmayan bileşen; aerosolde
    SEA Ek-1 2.3 "parlama noktası ≤ 93 °C" alevlenir bileşen sayımı), bileşen kaynama noktası (Tablo 2.6.1 Kat.1/2).
    Önceden kaynağı belirtilmemiş elle yazılmış tablolar (FP_DB / BP_DB) kullanılıyordu — kaldırıldı (2026-10-09).
  • GBF Bölüm 9 (section9): tek maddede maddenin kendi değeri; karışımda karışım değeri yoksa, KKDİK Ek-2 9.1
    ("verinin karışım içindeki hangi madde için geçerli olduğu açıkça belirtilir") uyarınca bileşen değeri.
    Hangi bileşenin seçileceğine TR Ek-2'de kural yok; AB 2020/878 Ek-II 9.1 yöntemi uygulanır (en düşük parlama
    noktası / kaynama noktası / kendiliğinden tutuşma; buhar basıncında en uçucu bileşen).

ECHA kullanım koşulları: kaynak gösterilerek kullanım; toplu kopyalama yok. Bu modül yalnız kullanıcının girdiği
CAS için, istekler arasında 1 sn bekleyerek okur; sayfanın kendisini değil yalnız anahtar değerleri saklar.
Önbellek: data/echa_phys/<cas>.json (sdspass-data deposunda kalıcı); kullanımda 30 günde bir yenilenir.
"""
import asyncio, html, json, os, re, time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import httpx

ROOT = Path(__file__).resolve().parents[2]
_DIR = ROOT / 'data' / 'echa_phys'
_E = 'https://chem.echa.europa.eu'
_H = {'Accept': 'application/json', 'User-Agent': 'Mozilla/5.0 (SDSPass)'}
_TTL_DAYS = 30          # kullanımda yenileme (ECHA verisi)
_ERR_RETRY_DAYS = 1     # ağ hatasından sonra yeniden deneme
_DELAY = 1.0            # ECHA istekleri arası bekleme (sn)
_REC_V = 4              # v4 (2026-10-10) kayıt yaptıranın GHS öz-sınıflandırması (2.1 GHS); 2026-10-09: v2 DNEL / PNEC (Bölüm 8.1); v3 güvenli kullanım rehberi eldiven önerisi (8.2.2.2)
# Çevrim dışı (kontrol seti): ağa çıkılmaz, önbellek eskimiş olsa da kullanılır
OFFLINE = os.environ.get('SDSPASS_PHYS_OFFLINE', '').strip() not in ('', '0')

FIELDS = ('flash_point', 'boiling_point', 'melting_point', 'vapour_pressure', 'density',
          'water_solubility', 'auto_ignition', 'viscosity')

# IUCLID bölüm numarası → alan (kayıt dosyası içindekiler tablosu)
_SECTIONS = {
    '4.2': 'melting_point', '4.3': 'boiling_point', '4.4': 'density', '4.6': 'vapour_pressure',
    '4.8': 'water_solubility', '4.11': 'flash_point', '4.12': 'auto_ignition', '4.22': 'viscosity',
}
# Anahtar değer metnindeki alan etiketi
_LABELS = {
    'melting_point': 'Melting / freezing point', 'boiling_point': 'Boiling point', 'density': None,
    'vapour_pressure': 'Vapour pressure', 'water_solubility': 'Water solubility', 'flash_point': 'Flash point',
    'auto_ignition': 'Self-ignition temperature', 'viscosity': 'Viscosity',
}

_states: Dict[int, Dict] = {}   # olay döngüsü başına kilit + süren istekler (TestClient her istekte yeni döngü açar)


def _state() -> Dict:
    loop = asyncio.get_running_loop()
    st = _states.get(id(loop))
    if st is None or st['loop'] is not loop:
        st = {'loop': loop, 'lock': asyncio.Lock(), 'inflight': {}}
        _states[id(loop)] = st
    return st


# ── Birim çözümleme ─────────────────────────────────────────────────────────
_NUM = r'(-?\d[\d,]*(?:\.\d+)?)'


def _sci(s: str) -> str:
    """'5.83X10+3', '1.2x10^-4', '3.5E+02' → düz sayı (PubChem bilimsel gösterim)."""
    def plain(v: float) -> str:
        return f'{v:.10f}'.rstrip('0').rstrip('.')

    s = (s or '').replace('−', '-')
    s = re.sub(r'(\d+(?:\.\d+)?)\s*[xX×]\s*10\s*\^?\s*\(?([+-]?\d+)\)?',
               lambda m: plain(float(m.group(1)) * 10 ** int(m.group(2))), s)
    return re.sub(r'\b(\d+(?:\.\d+)?)[eE]([+-]?\d+)\b', lambda m: plain(float(m.group(0))), s)


def _f(s: str) -> float:
    return float(s.replace(',', ''))


def _temp_c(v: float, unit: str) -> float:
    u = unit.upper().replace('°', '').strip()
    if u == 'K':
        return round(v - 273.15, 1)
    if u == 'F':
        return round((v - 32) * 5 / 9, 1)
    return round(v, 1)


def _qual(s: str) -> str:
    m = re.search(r'(ca\.|>=|<=|>|<|≥|≤|~)\s*$', s or '')
    return {'>=': '≥', '<=': '≤', 'ca.': '~'}.get(m.group(1), m.group(1)) if m else ''


def parse_temp(s: str) -> Optional[Dict]:
    """'286 K', '-95 °C', '55 °F (13 °C)' → °C. °C yazılı değer öncelikli."""
    pairs = re.findall(_NUM + r'\s*(°\s*C|°\s*F|K|deg\s*C|deg\s*F)\b', s or '')
    if not pairs:
        return None
    pick = next((p for p in pairs if 'C' in p[1].upper()), pairs[0])
    unit = 'K' if pick[1].strip() == 'K' else ('F' if 'F' in pick[1].upper() else 'C')
    return {'value': _temp_c(_f(pick[0]), unit), 'unit': '°C', 'qual': _qual(s[:s.find(pick[0])][-6:])}


def _at_temp(s: str) -> Optional[float]:
    m = re.search(r'(?:temperature of|at|@)\s*' + _NUM + r'\s*(°\s*C|°\s*F|K|deg\s*C)\b', s or '', re.I)
    if not m:
        return None
    unit = 'K' if m.group(2).strip() == 'K' else ('F' if 'F' in m.group(2).upper() else 'C')
    return _temp_c(_f(m.group(1)), unit)


def parse_pressure(s: str) -> Optional[Dict]:
    s = _sci(s)
    # ICSC biçimi (PubChem): "Vapour pressure, kPa at 20 °C: 24"
    m = re.search(r'(kPa|hPa|Pa)\s+at\s+' + _NUM + r'\s*°\s*C\s*:\s*' + _NUM, s or '')
    if m:
        k = {'kPa': 10, 'hPa': 1, 'Pa': 0.01}[m.group(1)]
        return {'value': round(_f(m.group(3)) * k, 4), 'unit': 'hPa', 'temp_c': _f(m.group(2)), 'qual': ''}
    m = re.search(_NUM + r'\s*(kPa|hPa|mbar|MPa|Pa|bar|mm\s*Hg|mmHg|torr|atm)\b', s or '', re.I)
    if not m:
        return None
    v, u = _f(m.group(1)), m.group(2).lower().replace(' ', '')
    k = {'pa': 0.01, 'kpa': 10, 'hpa': 1, 'mbar': 1, 'mpa': 10000, 'bar': 1000, 'mmhg': 1.33322,
         'torr': 1.33322, 'atm': 1013.25}[u]
    rest = s[m.end():]
    return {'value': float(f'{v * k:.4g}'), 'unit': 'hPa', 'temp_c': _at_temp(rest[:80]),
            'qual': _qual(s[:m.start()][-6:])}


def parse_density(s: str) -> Optional[Dict]:
    s = _sci(s)
    s = re.sub(r'\(\s*(?:water|air)\s*=\s*1\s*\)', '', s, flags=re.I)   # "Relative density (water = 1): 0.79"
    m = re.search(_NUM + r'\s*(g/cm³|g/cm3|g/mL|g/ml|kg/m³|kg/m3)?', s or '')
    if not m:
        return None
    v, u = _f(m.group(1)), (m.group(2) or '').lower()
    if u.startswith('kg'):
        v = v / 1000
    if not 0.05 < v < 25:
        return None
    rel = 'relative' in (s or '').lower()[:60] and not u
    return {'value': round(v, 4), 'unit': '' if rel else 'g/cm³', 'relative': rel,
            'temp_c': _at_temp((s or '')[m.end():m.end() + 80]), 'qual': _qual(s[:m.start()][-6:])}


def parse_solubility(s: str) -> Optional[Dict]:
    s = _sci(s)
    sl = (s or '').lower()
    if 'miscible' in sl and 'immiscible' not in sl and 'not miscible' not in sl:
        return {'value': None, 'text': 'suyla karışır', 'unit': ''}
    m = re.search(_NUM + r'\s*(mg/L|g/L|µg/L|ug/L|g/100\s*mL|g/100\s*g|%)', s or '', re.I)
    if not m:
        return None
    v, u = _f(m.group(1)), m.group(2).lower().replace(' ', '')
    k = {'mg/l': 1, 'g/l': 1000, 'µg/l': 0.001, 'ug/l': 0.001, 'g/100ml': 10000, 'g/100g': 10000, '%': 10000}[u]
    return {'value': round(v * k, 3), 'unit': 'mg/L', 'temp_c': _at_temp(s[m.end():m.end() + 80]),
            'qual': _qual(s[:m.start()][-6:])}


def parse_viscosity(s: str) -> Optional[Dict]:
    m = re.search(_NUM + r'\s*(mPa\s*[·.*]?\s*s|cP|mm²/s|mm2/s|cSt)', s or '', re.I)
    if not m:
        return None
    u = m.group(2).lower()
    kin = u.startswith('mm') or u == 'cst'
    return {'value': _f(m.group(1)), 'unit': 'mm²/s' if kin else 'mPa·s',
            'kind': 'kinematik' if kin else 'dinamik', 'temp_c': _at_temp(s[m.end():m.end() + 80]),
            'qual': _qual(s[:m.start()][-6:])}


_PARSERS = {
    'flash_point': parse_temp, 'boiling_point': parse_temp, 'melting_point': parse_temp,
    'auto_ignition': parse_temp, 'vapour_pressure': parse_pressure, 'density': parse_density,
    'water_solubility': parse_solubility, 'viscosity': parse_viscosity,
}


# ── ECHA kayıt dosyası ──────────────────────────────────────────────────────
def _path(cas: str) -> Path:
    return _DIR / f"{re.sub(r'[^0-9A-Za-z-]', '_', cas)}.json"


def _read(cas: str) -> Optional[Dict]:
    p = _path(cas)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding='utf-8'))
    except Exception:
        return None


def _age_days(rec: Dict) -> float:
    try:
        return (datetime.now(timezone.utc) - datetime.fromisoformat(rec['_fetched'])).total_seconds() / 86400
    except Exception:
        return 1e9


def _fresh(rec: Optional[Dict]) -> bool:
    if not rec:
        return False
    if OFFLINE:
        return True
    if rec.get('status') == 'ok' and rec.get('_v') != _REC_V:
        return False
    return _age_days(rec) < (_ERR_RETRY_DAYS if rec.get('status') == 'error' else _TTL_DAYS)


def _key_value_text(page: str, field: str) -> Optional[str]:
    t = re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', page)))
    i = t.find('Key value for assessment')
    if i < 0:
        return None
    seg = t[i + len('Key value for assessment'): i + 600]
    for stop in (' Additional information', ' Justification for classification', ' Attached background'):
        j = seg.find(stop)
        if j > 0:
            seg = seg[:j]
    lab = _LABELS[field]
    k = seg.find(lab) if lab else -1
    seg = (seg[k + len(lab):] if k >= 0 else seg).strip()
    return seg[:250] or None


def _plain(page: str) -> str:
    t = re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', page)))
    return t


_POP = {'Workers': 'İşçiler', 'General Population': 'Genel nüfus'}
_ROUTE = {'inhalation': 'soluma', 'dermal': 'deri', 'oral': 'ağız', 'eyes': 'göz'}


def parse_dnel(page: str) -> List[Dict]:
    """IUCLID 7 "Toxicological information" özeti — sayısal DNEL'ler (KKDİK Ek-2 8.1.4)."""
    t = _plain(page)
    out = []
    heads = list(re.finditer(r'(Workers|General Population) - Hazard (?:via (inhalation|dermal|oral) route|for the (eyes))', t))
    for k, h in enumerate(heads):
        blk = t[h.end(): heads[k + 1].start() if k + 1 < len(heads) else len(t)]
        for m in re.finditer(r'(Long term exposure|Acute/short term exposure) Hazard assessment conclusion '
                             r'DNEL \(Derived No Effect Level\) Value ([\d.,]+) (.+?) '
                             r'(?=Most sensitive endpoint|DNEL related information|Route of original study)', blk):
            eff = blk.rfind('Local effects', 0, m.start()) > blk.rfind('Systemic effects', 0, m.start())
            out.append({'nufus': _POP[h.group(1)], 'yol': _ROUTE[h.group(2) or h.group(3)],
                        'etki': 'yerel' if eff else 'sistemik',
                        'sure': 'uzun süreli' if m.group(1).startswith('Long') else 'kısa süreli',
                        'deger': _f(m.group(2)), 'birim': m.group(3).strip()})
    return out


_PNEC = {'aqua (freshwater)': 'tatlı su', 'aqua (marine water)': 'deniz suyu', 'STP': 'atık su arıtma tesisi',
         'sediment (freshwater)': 'tatlı su sedimenti', 'sediment (marine water)': 'deniz sedimenti',
         'soil': 'toprak', 'oral': 'ikincil zehirlenme (besin)'}


def parse_pnec(page: str) -> List[Dict]:
    """IUCLID 6 "Ecotoxicological information" özeti — sayısal PNEC'ler (KKDİK Ek-2 8.1.4)."""
    t = _plain(page)
    out = []
    for m in re.finditer(r'PNEC (aqua \(freshwater\)|aqua \(marine water\)|STP|sediment \(freshwater\)|'
                         r'sediment \(marine water\)|soil|oral) PNEC value ([\d.,]+) '
                         r'((?:mg|µg|g|ng)/(?:L|kg(?: sediment dw| soil dw| food)?))', t):
        out.append({'ortam': _PNEC[m.group(1)], 'deger': _f(m.group(2)), 'birim': m.group(3)})
    return out


# Kayıt yaptıranın "11 Guidance on safe use" metninde el koruması (KKDİK Ek-2 8.2.2.2(b)(i)) — serbest metin;
# malzeme / kalınlık / delinme süresi sezgisel ayrıştırılır, ham cümle KDU'nun doğrulaması için saklanır
_GLOVE_MAT = (
    ('butil', r'butyl'), ('nitril', r'nitrile|\bNBR\b'), ('neopren', r'neoprene|chloroprene'),
    ('viton', r'viton|fluor\w*\s*(?:elastomer|rubber|caoutchouc)|\bFKM\b'),
    ('laminat', r'laminate|\bPE/EV|EVOH|silver ?shield|\b4H\b'), ('pva', r'polyvinyl alcohol|\bPVA\b'),
    ('pvc', r'polyvinyl chloride|\bPVC\b'), ('dogal_kaucuk', r'natural rubber|\blatex\b'),
)


_GHS_PAIR = re.compile(r'Hazard category (?!\[Empty\])(.+?) Hazard statement (H\d{3}[A-Za-z]{0,2})')


# IUCLID seçim listesi adları → SEA / Ek-6 kısaltmaları
_IUCLID_CLS = (('Flam. Liquid', 'Flam. Liq.'), ('Flam. Solid', 'Flam. Sol.'), ('Ox. Liquid', 'Ox. Liq.'),
               ('Ox. Solid', 'Ox. Sol.'), ('STOT Single Exp.', 'STOT SE'), ('STOT Rep. Exp.', 'STOT RE'))


def parse_ghs(page: str) -> List[Dict]:
    """IUCLID 2.1 GHS kaydı → [{'h_class','h_code'}] (yalnız dolu "Hazard category … Hazard statement H…" satırları)."""
    t = _plain(page)
    out = []
    for m in _GHS_PAIR.finditer(t):
        cls = re.sub(r'\s+', ' ', m.group(1)).strip()
        for a, b in _IUCLID_CLS:
            cls = cls.replace(a, b)
        if len(cls) <= 40 and (cls, m.group(2)) not in {(o['h_class'], o['h_code']) for o in out}:
            out.append({'h_class': cls, 'h_code': m.group(2)})
    return out


def parse_glove(page: str) -> Optional[Dict]:
    t = _plain(page)
    m = re.search(r'(?i)hand protection|protective gloves|\bgloves?\b', t)
    if not m:
        return None
    seg = t[max(0, m.start() - 40): m.start() + 600]
    end = re.search(r'(?i)eye protection|body protection|skin and body|respiratory protection|hygiene|'
                    r'unsuitable|not suitable|not recommended', seg[60:])
    if end:
        seg = seg[:60 + end.start()]
    mats = [k for k, rx in _GLOVE_MAT if re.search(rx, seg, re.I)]
    th = re.search(r'(\d+(?:[.,]\d+)?)\s*mm', seg)
    bt = re.search(r'(?i)(?:>|≥|>=|more than|at least)\s*(\d+)\s*min', seg) or \
        re.search(r'(?i)breakthrough time[^0-9]{0,20}(\d+)\s*min', seg)
    if not mats and not th:
        return None
    return {'malzemeler': mats, 'kalinlik_mm': float(th.group(1).replace(',', '.')) if th else None,
            'delinme_dk': int(bt.group(1)) if bt else None, 'metin': seg.strip()[:400]}


def _summary_doc(idx: str, num: str) -> Optional[str]:
    m0 = re.search(r'das-nav-header">\s*' + re.escape(num) + r' ', idx)
    if not m0:
        return None
    j = idx.find('das-nav-topsection', m0.start() + 1)
    blk = idx[m0.start(): j if j > 0 else m0.start() + 50000]
    for chunk in blk.split('<a class="das-leaf')[1:]:
        m = re.search(r'href="([^"]+)"', chunk)
        if m and ('Endpoint summary' in chunk or re.search(r'S-\d+ \|[^"<]*Summary', chunk)):
            return m.group(1)
    return None


async def _fetch_echa(cas: str) -> Dict:
    rec: Dict = {'cas': cas, '_fetched': datetime.now(timezone.utc).isoformat(), 'values': {}}
    async with httpx.AsyncClient(headers=_H, timeout=40, follow_redirects=True) as c:
        async def get(url, **kw):
            await asyncio.sleep(_DELAY)
            r = await c.get(url, **kw)
            r.raise_for_status()
            return r
        s = (await get(_E + '/api-substance/v1/substance',
                       params={'pageIndex': 1, 'pageSize': 10, 'searchText': cas})).json()
        # Aynı CAS birden çok kayıtta geçebilir (ör. ksilen 1330-20-7: izomer karışımı 905-215-1 kayıtsız, "Xylene"
        # 215-535-7 kayıtlı) — CAS'ı içeren ilk üç kayıttan aktif kayıt dosyası olan seçilir
        subs = [i['substanceIndex'] for i in s.get('items', [])
                if cas in (i.get('substanceIndex', {}).get('casNumber') or [])][:3]
        if not subs:
            rec['status'] = 'not_found'
            return rec
        sub, items = subs[0], []
        for cand in subs:
            dl = (await get(_E + '/api-dossier-list/v1/dossier',
                            params={'pageIndex': 1, 'pageSize': 100, 'rmlId': cand['rmlId'], 'legislation': 'REACH',
                                    'registrationStatuses': 'Active'})).json()
            if dl.get('items'):
                sub, items = cand, dl['items']
                break
        rec['rml_id'], rec['name'] = sub.get('rmlId'), sub.get('rmlName')

        def _rank(d):
            info = d.get('reachDossierInfo') or {}
            return (0 if 'lead' in (info.get('registrationRole') or '').lower() else 1,
                    0 if 'full' in (info.get('dossierSubtype') or '').lower() else 1)
        items.sort(key=_rank)
        if not items:
            rec['status'] = 'not_registered'
            return rec
        d = items[0]
        info = d.get('reachDossierInfo') or {}
        asset = d['assetExternalId']
        base = f'{_E}/html-pages-prod/{asset}'
        rec['dossier'] = {'asset': asset, 'registration_number': d.get('registrationNumber'),
                          'last_updated': d.get('lastUpdatedDate'), 'role': info.get('registrationRole'),
                          'subtype': info.get('dossierSubtype'), 'url': f'{base}/index.html'}
        idx = (await get(base + '/index.html')).text
        for num, field in _SECTIONS.items():
            doc = _summary_doc(idx, num)
            if not doc:
                continue
            page = (await get(f'{base}/documents/{doc}.html')).text
            raw = _key_value_text(page, field)
            main = (raw or '').split(' at the ')[0]
            if not raw or '[Empty]' in main or not re.search(r'\d', main):
                continue
            val = _PARSERS[field](raw)
            if val:
                rec['values'][field] = {**val, 'text': raw[:160]}
        # DNEL (7 Toxicological information) ve PNEC (6 Ecotoxicological information) özetleri — Bölüm 8.1
        for num, key, parser in (('7', 'dnel', parse_dnel), ('6', 'pnec', parse_pnec)):
            doc = _summary_doc(idx, num)
            if doc:
                try:
                    rec[key] = parser((await get(f'{base}/documents/{doc}.html')).text)
                except Exception as e:
                    print(f'[component_phys] {cas} {key}: {e}')
        # 2.1 GHS — kayıt yaptıranın öz-sınıflandırması ("harmonised" kaydı hariç). Birden çok öz-sınıflandırma kaydı varsa
        # (örn. toluen "high grade" / "commercial grade ≥ %0,1 benzen") yalnız HEPSİNDE ortak sınıflar alınır — safsızlığa
        # bağlı sınıflar (H340/H350) dışarıda kalır. SEA Md.6(1)(c): Ek-6'da olmayan sınıflar için kullanılır (substance_lookup).
        m21 = re.search(r'id="id_21_GHS"', idx)
        if m21:
            j21 = idx.find('das-nav-topsection', m21.end())
            seg = idx[m21.end(): j21 if j21 > 0 else m21.end() + 30000]
            recs = re.findall(r'href="([0-9a-f\-_]+)".*?<span data-dastttxt="([^"]+)"', seg, re.S)
            recs = [(d, html.unescape(t)) for d, t in recs]
            # Başlığında "self" geçen kayıtlar öz-sınıflandırmadır; yoksa "harmonised" olmayanlar alınır
            # (benzen: "001 | Benzene" başlıksız uyumlaştırılmış kayıt, "002 | … (self-classification)")
            selfs = ([r for r in recs if 'self' in r[1].lower()]
                     or [r for r in recs if 'harmonised' not in r[1].lower()])
            sets, titles = [], []
            for d, t in selfs[:4]:
                try:
                    hz = parse_ghs((await get(f'{base}/documents/{d}.html')).text)
                    sets.append({(h['h_class'], h['h_code']) for h in hz}); titles.append(t)
                except Exception as e:
                    print(f'[component_phys] {cas} GHS: {e}')
            if sets:
                common = set.intersection(*sets)
                rec['ghs_self'] = {'kayitlar': titles,
                                   'hazards': [{'h_class': c, 'h_code': h} for c, h in sorted(common)]}
            else:
                rec['ghs_self'] = {'kayitlar': [], 'hazards': []}
        # 11 Guidance on safe use — el koruması önerisi (KKDİK Ek-2 8.2.2.2(b)(i))
        m11 = re.search(r'das-nav-header">\s*11 ', idx)
        if m11:
            j11 = idx.find('das-nav-topsection', m11.start() + 1)
            h11 = re.search(r'href="([^"]+)"', idx[m11.start(): j11 if j11 > 0 else m11.start() + 30000])
            if h11:
                try:
                    g = parse_glove((await get(f'{base}/documents/{h11.group(1)}.html')).text)
                    if g:
                        rec['eldiven'] = g
                except Exception as e:
                    print(f'[component_phys] {cas} eldiven: {e}')
        rec['status'] = 'ok'
        rec['_v'] = _REC_V
    return rec


async def _refresh(cas: str) -> Dict:
    async with _state()['lock']:          # ECHA'ya aynı anda tek madde
        prev = _read(cas)
        if _fresh(prev):
            return prev
        try:
            rec = await _fetch_echa(cas)
        except Exception as e:
            print(f'[component_phys] ECHA {cas}: {type(e).__name__}: {e}')
            if prev and prev.get('status') == 'ok':
                return prev    # ağ hatası — eski geçerli veri korunur, sonraki kullanımda yeniden denenir
            rec = {'cas': cas, 'values': {}, 'status': 'error',
                   '_fetched': datetime.now(timezone.utc).isoformat()}
        _DIR.mkdir(parents=True, exist_ok=True)
        _path(cas).write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding='utf-8')
        try:
            from app.services.data_store import persist
            persist(_path(cas))
        except Exception:
            pass
        return rec


async def ensure(cas: str) -> None:
    """Madde verisini hazırla (ECHA + PubChem). Önbellek tazeyse ağa çıkmaz; aynı CAS için tek istek."""
    cas = (cas or '').strip()
    if not cas or OFFLINE:
        return
    if _fresh(_read(cas)) and _pubchem_cached(cas):
        return
    _inflight = _state()['inflight']
    t = _inflight.get(cas)
    if t is None or t.done():
        async def _job():
            try:
                await _refresh(cas)
                try:
                    from app.services.pubchem_phys_service import fetch_phys
                    await fetch_phys(cas)
                except Exception as e:
                    print(f'[component_phys] PubChem {cas}: {e}')
            finally:
                _inflight.pop(cas, None)
        t = asyncio.ensure_future(_job())
        _inflight[cas] = t
    await asyncio.shield(t)


async def ensure_many(cas_list: List[str], timeout: float = 90.0) -> List[str]:
    """Birden çok maddeyi hazırla; süre aşılırsa kalanlar bilinmiyor sayılır. Döner: süresi aşılan CAS'lar."""
    todo = [c for c in dict.fromkeys((x or '').strip() for x in cas_list) if c]
    if not todo or OFFLINE:
        return []
    tasks = {c: asyncio.ensure_future(ensure(c)) for c in todo}
    done, pending = await asyncio.wait(tasks.values(), timeout=timeout)
    return [c for c, t in tasks.items() if t in pending]


def _pubchem_cached(cas: str) -> bool:
    try:
        from app.services.pubchem_phys_service import cached
        return cached(cas) is not None
    except Exception:
        return True


# ── Okuma (senkron, yalnız önbellek) ─────────────────────────────────────────
_PUBCHEM_MAP = {'flash_point': 'flash_point', 'boiling_point': 'boiling_point', 'melting_point': 'melting_point',
                'vapour_pressure': 'vapor_pressure', 'density': 'density', 'water_solubility': 'solubility',
                'auto_ignition': 'auto_ignition'}


def get(cas: str) -> Dict[str, Dict]:
    """{alan: {value, unit, temp_c?, qual?, text, source: 'ECHA'|'PubChem', ref}} — yalnız önbellekten."""
    cas = (cas or '').strip()
    out: Dict[str, Dict] = {}
    if not cas:
        return out
    rec = _read(cas) or {}
    if rec.get('status') == 'ok':
        dos = rec.get('dossier') or {}
        ref = 'ECHA kayıt dosyası' + (f" ({dos['registration_number']})" if dos.get('registration_number') else '')
        for f, v in (rec.get('values') or {}).items():
            out[f] = {**v, 'source': 'ECHA', 'ref': ref}
    try:
        from app.services.pubchem_phys_service import cached
        pc = cached(cas) or {}
    except Exception:
        pc = {}
    srcs = pc.get('_src') or {}
    if pc.get('_v') == 2:   # yalnız düzeltilmiş (2026-10-09) PubChem çözümlemesi kullanılır
        for f, k in _PUBCHEM_MAP.items():
            if f in out or pc.get(k) is None:
                continue
            ent = {'value': pc[k], 'unit': {'vapour_pressure': 'hPa', 'density': 'g/cm³',
                                            'water_solubility': 'mg/L'}.get(f, '°C'),
                   'temp_c': (pc.get('_temp') or {}).get(k), 'qual': '', 'text': (pc.get('_raw') or {}).get(k, ''),
                   'source': 'PubChem', 'ref': 'PubChem' + (f" — {srcs[k]}" if srcs.get(k) else '')}
            out[f] = ent
    return out


def glove(cas: str) -> Dict:
    """Kayıt yaptıranın el koruması önerisi {malzemeler, kalinlik_mm, delinme_dk, metin, ref} — yalnız önbellek."""
    rec = _read((cas or '').strip()) or {}
    if rec.get('status') != 'ok' or not rec.get('eldiven'):
        return {}
    dos = rec.get('dossier') or {}
    return {**rec['eldiven'],
            'ref': 'ECHA kayıt dosyası' + (f" ({dos['registration_number']})" if dos.get('registration_number') else '')}


def dnel_pnec(cas: str) -> Dict:
    """{'dnel': [...], 'pnec': [...], 'ref': 'ECHA kayıt dosyası (no)'} — yalnız önbellek."""
    rec = _read((cas or '').strip()) or {}
    if rec.get('status') != 'ok':
        return {}
    dos = rec.get('dossier') or {}
    return {'dnel': rec.get('dnel') or [], 'pnec': rec.get('pnec') or [],
            'ref': 'ECHA kayıt dosyası' + (f" ({dos['registration_number']})" if dos.get('registration_number') else '')}


def value(c: Dict, field: str) -> Optional[float]:
    """Bileşen sözlüğünden alan değeri: önce c['phys'] (hat ekler), yoksa önbellek."""
    ph = c.get('phys')
    if ph is None:
        ph = get(c.get('cas') or c.get('cas_no') or '')
    v = (ph.get(field) or {}).get('value')
    return float(v) if isinstance(v, (int, float)) else None


def attach(comps: List[Dict]) -> None:
    for c in comps:
        c['phys'] = get(c.get('cas') or c.get('cas_no') or '')


# ── GBF Bölüm 9 metni ───────────────────────────────────────────────────────
def _fmt_num(v: float) -> str:
    s = f'{v:,.4g}' if abs(v) >= 1000 else (f'{v:.4g}')
    return s.replace(',', ' ').replace('.', ',')


def fmt(ent: Dict, field: str) -> str:
    v = ent.get('value')
    q = ent.get('qual') or ''
    if v is None:
        return ent.get('text') or ''
    unit = ent.get('unit') or ''
    s = f"{q}{_fmt_num(v)} {unit}".strip()
    if field == 'density' and ent.get('relative'):
        s = f"{q}{_fmt_num(v)} (bağıl)"
    if field == 'viscosity' and ent.get('kind'):
        s += f" ({ent['kind']})"
    if ent.get('temp_c') is not None and field in ('vapour_pressure', 'density', 'water_solubility', 'viscosity'):
        s += f" ({_fmt_num(ent['temp_c'])} °C)"
    return s


def _name(c: Dict) -> str:
    return (c.get('name_tr') or c.get('name') or c.get('cas') or '').split(';')[0].strip()


# Fiziksel hale göre uygulanmayan özellikler (AB 2020/878 Ek-II 9.1: parlama noktası gaz/aerosol/katıya, kinematik
# viskozite yalnız sıvılara, yoğunluk sıvı ve katılara uygulanır) — PDF bu satırlara "Uygulanamaz" yazar
_NOT_FOR_FORM = {
    'gas': {'flash_point', 'viscosity', 'density'},
    'aerosol': {'flash_point'},
    'solid': {'flash_point', 'viscosity'},
    'powder': {'flash_point', 'viscosity'},
}


def _decl_flam(c: Dict) -> Optional[str]:
    hs = {(h.get('h_code') or '').replace('*', '').strip()[:4] for h in (c.get('hazards') or [])}
    return next((h for h in ('H224', 'H225', 'H226') if h in hs), None)


def fp_conflict(c: Dict) -> Optional[str]:
    """Bileşenin veri kaynağındaki parlama noktası kendi (bağlayıcı Ek-6 / kayıt) alevlenir sıvı sınıfıyla çelişiyor mu?
    SEA Ek-1 Tablo 2.6.1: Kat.1–2 < 23 °C, Kat.3 23–60 °C. Çelişen değer Bölüm 9'a yazılmaz (Ek-2 9: bölüm
    sınıflandırmayla tutarlı olur). Örn. ksilen: ECHA anahtar değeri 18 °C, Ek-6 H226. Döner: uyarı metni veya None."""
    h = _decl_flam(c)
    fp = value(c, 'flash_point')
    if not h or fp is None:
        return None
    ok = fp < 23 if h in ('H224', 'H225') else 23 <= fp <= 60
    if ok:
        return None
    ph = c.get('phys') if c.get('phys') is not None else get(c.get('cas') or '')
    ref = (ph.get('flash_point') or {}).get('ref') or 'veri kaynağı'
    return (f"ℹ {_name(c)}: {ref} parlama noktası ({_fmt_num(fp)} °C) maddenin sınıfıyla ({h}) uyumlu değil — "
            "sınıflandırmada kayıtlı sınıf kullanıldı (SEA Md.6(1)(c)); bu değer GBF Bölüm 9'a yazılmadı.")


def section9(comps: List[Dict], substance_mode: bool, form: str = 'liquid') -> Dict[str, Dict]:
    """Bölüm 9 satırları: {alan_anahtarı (Bölüm 9 adı): {'display', 'note'}}. Karışımda yalnız AB 2020/878 Ek-II 9.1
    yönteminin bileşen değerini öngördüğü özellikler (parlama, kaynama, kendiliğinden tutuşma, buhar basıncı)."""
    b9_key = {'flash_point': 'flash_point', 'boiling_point': 'boiling_point', 'melting_point': 'melting_point',
              'vapour_pressure': 'vapor_pressure', 'density': 'density', 'water_solubility': 'solubility',
              'auto_ignition': 'auto_ignition', 'viscosity': 'viscosity'}
    act = [c for c in comps if float(c.get('concMax') or c.get('conc') or 0) > 0 and (c.get('cas') or c.get('cas_no'))]
    out: Dict[str, Dict] = {}
    if substance_mode and act:
        ph = act[0].get('phys') if act[0].get('phys') is not None else get(act[0].get('cas') or '')
        for f, ent in ph.items():
            if f in _NOT_FOR_FORM.get(form, ()) or (f == 'flash_point' and fp_conflict(act[0])):
                continue
            out[b9_key[f]] = {'display': fmt(ent, f), 'note': f"{ent['ref']} — madde verisi"}
        return out
    rules = (('flash_point', min, 'En düşük parlama noktalı bileşen', 'karışımın parlama noktası değildir'),
             ('boiling_point', min, 'En düşük kaynama noktalı bileşen', 'karışımın kaynama noktası değildir'),
             ('auto_ignition', min, 'En düşük kendiliğinden tutuşma sıcaklıklı bileşen',
              'karışımın değeri değildir'),
             ('vapour_pressure', max, 'En uçucu bileşen', 'karışımın buhar basıncı değildir'))
    for f, pick, lead, caveat in rules:
        if f in _NOT_FOR_FORM.get(form, ()):
            continue
        cands = []
        for c in act:
            ph = c.get('phys') if c.get('phys') is not None else get(c.get('cas') or '')
            ent = ph.get(f)
            if ent and ent.get('value') is not None and not (f == 'flash_point' and fp_conflict(c)):
                cands.append((ent['value'], c, ent))
        if f == 'boiling_point':
            cands = [x for x in cands if (x[1].get('cas') or '').strip() != '7732-18-5'] or cands
        if not cands:
            continue
        v, c, ent = pick(cands, key=lambda x: x[0])
        out[b9_key[f]] = {
            'display': f"Karışım için ölçülmemiştir. {lead}: {_name(c)} {fmt(ent, f)} ({caveat})",
            'note': f"bileşen verisi — {ent['ref']} (KKDİK Ek-2 9.1)"}
    return out
