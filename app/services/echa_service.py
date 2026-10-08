"""
ECHA / PubChem Lookup Servisi
==============================
Lokal DB'de bulunamayan maddeleri PubChem üzerinden çeker.
PubChem, ECHA C&L Inventory bildirim verilerini barındırır (GHS Classification).

Seçim mantığı: Birden fazla bildirim grubu varsa → bildirim sayısı EN YÜKSEK olan
  (= "Aggregated GHS information ... from N notifications") veya
  "Joint Notification" ibareli grup seçilir.

Arama Hiyerarşisi (SDS TR):
  1. substances_annex_vi.json  — Annex VI / SEA Ek-6 (mutlak, yerel)
  2. data/echa_cl_archive.json — Kalıcı ECHA C&L arşivi (önceki çekimler)
  3. PubChem/ECHA C&L API     — Canlı çekim, sonuç arşive kaydedilir
  4. substances_custom.json    — Kullanıcı girişleri (API'de de bulunamazsa)
"""

import re, httpx, asyncio, json, os
from datetime import datetime, timezone
from pathlib import Path

# Oturum içi hızlı önbellek (bellek bazlı)
CACHE_FILE = Path(__file__).parent / 'echa_cache.json'

# Kalıcı ECHA C&L arşivi — proje kökü/data/
_DATA_DIR    = Path(__file__).parent.parent.parent / 'data'
ARCHIVE_FILE = _DATA_DIR / 'echa_cl_archive.json'

# ECHA yasal uyarısı: yeniden kullanımda kaynak gösterilmesi zorunlu
ECHA_ATTRIBUTION = 'Kaynak: European Chemicals Agency, https://echa.europa.eu/'
CHANGES_FILE     = _DATA_DIR / 'echa_changes.jsonl'

# H kodu → hazard class mapping (CLP Annex VI / GHS)
_H_TO_CLASS = {
    'H200':'Expl. Unst.','H201':'Expl. 1.1','H202':'Expl. 1.2','H203':'Expl. 1.3',
    'H204':'Expl. 1.4','H205':'Expl. 1.5','H206':'Expl. 1.6',
    'H220':'Flam. Gas 1','H221':'Flam. Gas 2',
    'H222':'Flam. Aerosol 1','H223':'Flam. Aerosol 2',
    'H224':'Flam. Liq. 1','H225':'Flam. Liq. 2','H226':'Flam. Liq. 3',
    'H228':'Flam. Sol. 1','H229':'Flam. Sol. 2',
    'H240':'Self-react. A','H241':'Self-react. B',
    'H250':'Pyr. Liq. 1','H251':'Self-heat. 1','H252':'Self-heat. 2',
    'H260':'Water-react. 1','H261':'Water-react. 2','H270':'Ox. Gas 1',
    'H271':'Ox. Liq. 1','H272':'Ox. Liq. 2','H290':'Met. Corr. 1',
    'H300':'Acute Tox. 1','H301':'Acute Tox. 3','H302':'Acute Tox. 4',
    'H304':'Asp. Tox. 1',
    'H310':'Acute Tox. 1','H311':'Acute Tox. 3','H312':'Acute Tox. 4',
    'H314':'Skin Corr. 1','H315':'Skin Irrit. 2',
    'H317':'Skin Sens. 1','H318':'Eye Dam. 1','H319':'Eye Irrit. 2',
    'H330':'Acute Tox. 1','H331':'Acute Tox. 3','H332':'Acute Tox. 4',
    'H334':'Resp. Sens. 1',
    'H335':'STOT SE 3','H336':'STOT SE 3',
    'H340':'Muta. 1B','H341':'Muta. 2',
    'H350':'Carc. 1B','H351':'Carc. 2',
    'H360':'Repr. 1B','H361':'Repr. 2','H362':'Repr. Lact.',
    'H370':'STOT SE 1','H371':'STOT SE 2','H372':'STOT RE 1','H373':'STOT RE 2',
    'H400':'Aquatic Acute 1','H401':'Aquatic Acute 2','H402':'Aquatic Acute 3',
    'H410':'Aquatic Chronic 1','H411':'Aquatic Chronic 2',
    'H412':'Aquatic Chronic 3','H413':'Aquatic Chronic 4',
    'H420':'Ozone','EUH001':'EUH001','EUH006':'EUH006','EUH014':'EUH014',
    'EUH018':'EUH018','EUH019':'EUH019','EUH029':'EUH029','EUH031':'EUH031',
    'EUH032':'EUH032','EUH044':'EUH044','EUH059':'EUH059','EUH066':'EUH066',
    'EUH070':'EUH070','EUH071':'EUH071',
}

# GHS piktogram kodu → resim dosya adı
_PICT_MAP = {
    'GHS01':'GHS01','GHS02':'GHS02','GHS03':'GHS03','GHS04':'GHS04',
    'GHS05':'GHS05','GHS06':'GHS06','GHS07':'GHS07','GHS08':'GHS08','GHS09':'GHS09',
    'exploding bomb':'GHS01','flame':'GHS02','flame over circle':'GHS03',
    'gas cylinder':'GHS04','corrosion':'GHS05','skull and crossbones':'GHS06',
    'exclamation mark':'GHS07','health hazard':'GHS08','environment':'GHS09',
}


# ---------------------------------------------------------------------------
# Lokal DB — substance_lookup üzerinden (annex_vi + custom)
# ---------------------------------------------------------------------------

def lookup_local(cas: str) -> dict | None:
    """
    Öncelik sırası:
      1 — SEA Ek-6            (sea_ek6=True)          MUTLAK
      2 — AB CLP Annex VI     (annex_vi=True, sea_ek6=False)
      4 — Tedarikçi/Kullanıcı (annex_vi=False, sea_ek6=False)
    """
    from app.services.substance_lookup import lookup_substance
    entry = lookup_substance(cas.strip())
    if not entry:
        return None

    sea_ek6   = entry.get('sea_ek6', False)
    annex_vi  = entry.get('annex_vi', False)

    if sea_ek6:
        priority = 1
        source   = f'SEA Ek-6 ({entry.get("atp","?")})'
    elif annex_vi:
        priority = 2
        source   = f'AB CLP Annex VI ({entry.get("atp","?")})'
    else:
        priority = 4
        source   = 'Tedarikçi/Kullanıcı Girişi'

    return {
        'cas'           : cas,
        'name'          : entry.get('name', ''),
        'name_tr'       : entry.get('name_tr', ''),
        'source'        : source,
        'source_priority': priority,
        'h_codes'       : [h['h_code'] for h in entry.get('hazards', []) if h.get('h_code')],
        'hazard_classes': [h['h_class'] for h in entry.get('hazards', []) if h.get('h_class')],
        'signal'        : entry.get('signal', ''),
        'pictograms'    : entry.get('pictograms', []),
        'm_factors'     : entry.get('m_factors', {}),
        'ate'           : entry.get('ate', {}),
        'scl'           : entry.get('scl', []),
        'suppl_hazards' : entry.get('suppl_hazards', []),
        'index_no'      : entry.get('index_no', ''),
        'atp'           : entry.get('atp', ''),
    }


# ---------------------------------------------------------------------------
# Oturum önbelleği (bellek + dosya)
# ---------------------------------------------------------------------------

def _load_cache() -> dict:
    try:
        if CACHE_FILE.exists():
            with open(CACHE_FILE, encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _save_cache(cache: dict):
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
        from app.services.data_store import persist
        persist(CACHE_FILE)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Kalıcı ECHA C&L Arşivi — data/echa_cl_archive.json
# ---------------------------------------------------------------------------

_archive_mem: dict | None = None  # bellek önbelleği (sunucu yeniden başlayana kadar)


def _load_archive() -> dict:
    global _archive_mem
    if _archive_mem is not None:
        return _archive_mem
    try:
        if ARCHIVE_FILE.exists():
            with open(ARCHIVE_FILE, encoding='utf-8') as f:
                _archive_mem = json.load(f)
                return _archive_mem
    except Exception:
        pass
    _archive_mem = {}
    return _archive_mem


def _save_to_archive(cas: str, result: dict):
    """ECHA C&L API sonucunu kalıcı arşive kaydet."""
    global _archive_mem
    archive = _load_archive()
    archive[cas] = {
        **result,
        'fetched_at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'source': result.get('source', 'ECHA C&L Archive'),
    }
    _archive_mem = archive
    try:
        with open(ARCHIVE_FILE, 'w', encoding='utf-8') as f:
            json.dump(archive, f, ensure_ascii=False, indent=2)
        from app.services.data_store import persist
        persist(ARCHIVE_FILE)
        print(f'[archive] Kaydedildi: {cas} ({result.get("name","")}) '
              f'— {result.get("notif_count", 0)} bildirim')
    except Exception as ex:
        print(f'[archive] Kayıt hatası {cas}: {ex}')


def lookup_archive(cas: str) -> dict | None:
    """Kalıcı arşivde CAS ara. Bulunursa döndür, yoksa None."""
    archive = _load_archive()
    entry = archive.get(cas.strip())
    if entry and isinstance(entry, dict) and entry.get('h_codes'):
        entry = dict(entry)
        entry['source'] = f'ECHA C&L Arşiv ({entry.get("notif_count", "?")} bildirim)'
        return entry
    return None


# ---------------------------------------------------------------------------
# PubChem → ECHA C&L parser
# ---------------------------------------------------------------------------

def _extract_notif_count(summary_text: str) -> int:
    """
    'Aggregated GHS information provided per 13886 reports by companies
     from 79 notifications ...'
    → 79
    'The GHS information provided by 1 company from 1 notification ...'
    → 1
    'Joint Notification' → 9999 (en yüksek öncelik)
    """
    if not summary_text:
        return 0
    t = summary_text.lower()
    if 'joint notification' in t:
        return 9999
    # "from N notifications"
    m = re.search(r'from\s+(\d+)\s+notification', t)
    if m:
        return int(m.group(1))
    # "N notification"
    m = re.search(r'(\d+)\s+notification', t)
    if m:
        return int(m.group(1))
    return 1


def _parse_ghs_groups(info_list: list) -> list:
    """
    Information[] dizisini Pictogram(s) başlangıç noktalarına göre
    bloklara böl. Her blok bir bildirim grubunu temsil eder.
    Returns: list of dicts:
      { 'notif_count': int, 'signal': str,
        'h_codes': [...], 'pictograms': [...], 'summary': str }
    """
    groups = []
    current = None

    for item in info_list:
        name = item.get('Name', '')
        val  = item.get('Value', {})
        strings = [s.get('String', '') for s in val.get('StringWithMarkup', [])]
        text = ' '.join(strings).strip()

        if name == 'Pictogram(s)':
            if current is not None:
                groups.append(current)
            current = {
                'notif_count': 0,
                'signal': '',
                'h_codes': [],
                'hazard_classes': [],
                'pictograms': [],
                'summary': '',
                'm_factors': {},
            }
            # Pictogram'ları markup'tan çıkar
            for s in val.get('StringWithMarkup', []):
                for mk in s.get('Markup', []):
                    extra = mk.get('Extra', '').lower()
                    for key, code in _PICT_MAP.items():
                        if key in extra or key == extra:
                            if code not in current['pictograms']:
                                current['pictograms'].append(code)

        elif current is None:
            continue

        elif name == 'Signal':
            current['signal'] = text

        elif name == 'GHS Hazard Statements':
            # "H225 (> 99.9%): Highly Flammable liquid and vapor [M-factor: 10]"
            for s in val.get('StringWithMarkup', []):
                raw = s.get('String', '')
                m = re.match(r'(H\d+|EUH\d+)', raw)
                if m:
                    hcode = m.group(1)
                    if hcode not in current['h_codes']:
                        current['h_codes'].append(hcode)
                    hcls = _H_TO_CLASS.get(hcode, '')
                    if hcls and hcls not in current['hazard_classes']:
                        current['hazard_classes'].append(hcls)
                # M-faktör: "... [M-factor: 10]" veya "M factor: 10"
                m_match = re.search(r'[Mm][- ]?[Ff]actor[:\s]+(\d+)', raw)
                if m_match:
                    try:
                        mval = int(m_match.group(1))
                        hbase = m.group(1) if m else ''
                        if hbase in ('H400', 'H401', 'H402'):
                            current.setdefault('m_factors', {})['acute'] = mval
                        elif hbase in ('H410', 'H411'):
                            current.setdefault('m_factors', {})['chronic'] = mval
                        else:
                            current.setdefault('m_factors', {})['acute'] = mval
                    except (ValueError, AttributeError):
                        pass

    if current is not None:
        groups.append(current)

    # Fiziksel hal çakışması tespiti: aynı grupta hem gaz hem sıvı H-kodu varsa
    GAS_H   = {'H220', 'H221', 'H280', 'H281'}
    LIQ_H   = {'H224', 'H225', 'H226'}
    SOL_H   = {'H228', 'H229'}
    for g in groups:
        h_set = set(g['h_codes'])
        states = []
        if h_set & GAS_H:   states.append('gas')
        if h_set & LIQ_H:   states.append('liquid')
        if h_set & SOL_H:   states.append('solid')
        if len(states) > 1:
            g['physical_state_conflict'] = states

    return groups


def _best_group(groups: list) -> dict | None:
    """
    Sınıflandırma grubu seçimi — "tedbirli olma" ilkesi (CLP Madde 10).

    Öncelik sırası:
      1. Joint Notification (resmi birleşik bildirim)
      2. CMR (Carc./Repr./Muta./Resp.Sens.) H-kodu içeren herhangi bir grup
         → bu H-kodları çoğunluk grubuna eklenir (birleştirme)
      3. En çok bildirim alan grup (baseline)

    Gerekçe: Mevzuatta "tedbirli olma" ilkesi gereği 1000 bildirim "tehlikesiz"
    dese bile 10 bildirim kanıtlı karsinojen diyorsa bu dikkate alınmalıdır.
    """
    if not groups:
        return None

    # Öncelik 1: Joint Notification
    for g in groups:
        if g['notif_count'] == 9999:
            return g

    # Sadece ECHA C&L summary içeren gruplara bak
    echa_groups = [g for g in groups if g['notif_count'] > 0]
    if not echa_groups:
        return groups[0]

    # Öncelik 3: En çok bildirim → baseline grup
    majority = max(echa_groups, key=lambda g: g['notif_count'])

    # CMR H-kodları: her koşulda eklenmesi gereken tehlikeler
    CMR_HCODES = {
        'H340', 'H341',                          # Mutajenite
        'H350', 'H350i', 'H351',                 # Kanserojenite
        'H360', 'H360D', 'H360F', 'H360FD',      # Üreme
        'H361', 'H361d', 'H361f', 'H361fd',
        'H362',                                  # Emzirme
        'H334',                                  # Solunum hassaslaştırıcı
        'H372', 'H373',                          # STOT RE (hedef organ)
        'H400', 'H410',                          # Yüksek akut/kronik sucul (M-faktörlü)
    }

    # Öncelik 2: Diğer gruplardan CMR H-kodlarını topla
    extra_h = []
    extra_cls = []
    extra_pict = []

    for g in echa_groups:
        if g is majority:
            continue
        for hcode in g['h_codes']:
            base = re.match(r'(H\d+[A-Za-z]*)', hcode)
            if base and base.group(1) in CMR_HCODES:
                if hcode not in majority['h_codes'] and hcode not in extra_h:
                    extra_h.append(hcode)
                    cls = _H_TO_CLASS.get(base.group(1), '')
                    if cls and cls not in majority['hazard_classes'] and cls not in extra_cls:
                        extra_cls.append(cls)
        for pic in g['pictograms']:
            if pic not in majority['pictograms'] and pic not in extra_pict:
                extra_pict.append(pic)

    if not extra_h:
        return majority

    # Birleştirilmiş grup oluştur
    merged = dict(majority)
    merged['h_codes']        = majority['h_codes'] + extra_h
    merged['hazard_classes'] = majority['hazard_classes'] + extra_cls
    merged['pictograms']     = list(dict.fromkeys(majority['pictograms'] + extra_pict))
    # CMR eklendiyse sinyal Danger'a çekilebilir
    if any(p in ('GHS08',) for p in extra_pict) and merged['signal'] == 'Warning':
        merged['signal'] = 'Danger'
    merged['_cmr_merged']    = True   # bilgi amaçlı flag
    return merged


# ---------------------------------------------------------------------------
# ECHA C&L Inventory — ECHA CHEM (chem.echa.europa.eu)
# ---------------------------------------------------------------------------
# Belgelenmemiş iç API (ECHA CHEM sitesinin kendi kullandığı); ECHA değiştirirse burası kırılır.
_ECHA_CHEM          = 'https://chem.echa.europa.eu'
_CL_CLASS_THRESHOLD = 50.0   # tehlike sınıfı bildirimlerin bu yüzdesini AŞARSA eklenir
_CL_TIE_MARGIN      = 2.0    # en yüksek paya bu kadar yakın kategoriler eşit sayılır → daha ağır olan seçilir
_CL_MAX_PARALLEL    = 5
# M/ATE seçim yönteminin sürümü. 2: M yazmayan bildirimler M=1 sayılır; M ve ATE yalnız ilgili tehlikeyi
# bildiren gruplardan. 3: bildirim ATE'si yalnız SEA Ek-1 Tablo 3.1.2 dönüşüm değerinden düşükse kullanılır. Daha düşük sürümle kaydedilmiş ECHA kayıtları yeniden çekilir (substance_lookup._is_stale).
ECHA_EXTRAS_VER     = 3

_CAT_RE   = re.compile(r'^(?P<base>.+?)\s+(?P<cat>\d[A-C]?)\.?$')
_ROUTE_RE = re.compile(r'^(.*?)\s*(\([^)]*\))?\s*$')


def _split_hazard_class(code: str) -> tuple:
    """'Acute Tox. 4 (Oral)' → ('Acute Tox. (Oral)', '4', 'Acute Tox. 4')"""
    m = _ROUTE_RE.match(code.strip())
    main, route = m.group(1), m.group(2) or ''
    cm = _CAT_RE.match(main)
    base, cat = (cm.group('base'), cm.group('cat')) if cm else (main, '')
    return f'{base} {route}'.strip(), cat, main


def _severity_key(cat: str, h_code: str) -> tuple:
    # Küçük = daha ağır: kategori 1 < 2, 1A < 1B; aynı kategoride H361fd > H361f > H361
    m = re.match(r'(\d)([A-C]?)', cat or '')
    num    = int(m.group(1)) if m else 9
    letter = (m.group(2) if m else '') or 'Z'
    return (num, letter, -(len(h_code) - 4))


async def _fetch_echa_cl_direct(cas: str, client: httpx.AsyncClient) -> dict | None:
    """
    ECHA C&L Inventory öz-sınıflandırmalarından konsensüs H-kodları.

    Kural (tehlike sınıfı bazlı):
      1. Her sınıfın (örn. Flam. Liq.) bildirim payı, kategorileri toplanarak hesaplanır.
      2. Pay %50'yi aşmıyorsa sınıf eklenmez.
      3. Aşıyorsa en çok bildirilen kategori seçilir; ona 2 puandan yakın olanlar
         eşit sayılır ve aralarından daha ağır olan alınır.
    Akut toksisite maruziyet yoluna göre, STOT SE 3 ise H335/H336'ya göre ayrı sınıf sayılır.
    """
    headers = {'Accept': 'application/json', 'User-Agent': 'Mozilla/5.0 (SDSPass)'}

    async def _get(path: str, params: dict | None = None):
        r = await client.get(_ECHA_CHEM + path, params=params, headers=headers, timeout=15.0)
        r.raise_for_status()
        return r.json()

    try:
        search = await _get('/api-substance/v1/substance',
                            {'pageIndex': 1, 'pageSize': 10, 'searchText': cas})
        subst = next((i['substanceIndex'] for i in search.get('items', [])
                      if cas in (i.get('substanceIndex', {}).get('casNumber') or [])), None)
        if not subst:
            print(f'[ECHA CHEM] {cas}: madde bulunamadı')
            return None

        groups = (await _get(f"/api-cnl-inventory/industry/{subst['rmlId']}/classifications")).get('items', [])
        if not groups:
            print(f'[ECHA CHEM] {cas}: C&L bildirimi yok')
            return None

        sem = asyncio.Semaphore(_CL_MAX_PARALLEL)

        async def _detail(g):
            async with sem:
                d = await _get(f"/api-cnl-inventory/industry/classification/{g['classificationId']}")
                return g['classificationId'], float(g.get('substanceNotificationPercentage') or 0), d.get('items', [])

        family_share: dict = {}
        variant_share: dict = {}
        group_pairs: dict = {}    # classificationId → {(ana sınıf, H kodu)} — M/ATE için ilgili grup seçimi
        for gid, pct, items in await asyncio.gather(*[_detail(g) for g in groups]):
            seen_fam, seen_var = set(), set()
            for it in items:
                codes = tuple(h['hazardStatementCode'].strip() for h in it.get('hazardStatements', [])
                              if h.get('hazardStatementCode'))
                if not codes:
                    continue
                family, cat, main = _split_hazard_class(it.get('hazardClassAndCategoryCode', ''))
                group_pairs.setdefault(gid, set()).update((main, c.upper()) for c in codes)
                if family == 'STOT SE' and cat == '3':
                    family = f'{family} {codes[0]}'
                if family not in seen_fam:
                    seen_fam.add(family)
                    family_share[family] = family_share.get(family, 0.0) + pct
                var = (main, cat, codes)
                if (family, var) not in seen_var:
                    seen_var.add((family, var))
                    fv = variant_share.setdefault(family, {})
                    fv[var] = fv.get(var, 0.0) + pct

        h_codes, hazard_classes, chosen = [], [], []
        for family, share in sorted(family_share.items(), key=lambda t: -t[1]):
            if share <= _CL_CLASS_THRESHOLD:
                continue
            variants = variant_share[family]
            top = max(variants.values())
            near = [v for v, s in variants.items() if top - s < _CL_TIE_MARGIN]
            main, cat, codes = min(near, key=lambda v: _severity_key(v[1], v[2][0]))
            chosen.append(f'{family} %{share:.0f} → {main} {"/".join(codes)}')
            for code in codes:
                if code not in h_codes:
                    h_codes.append(code)
                    hazard_classes.append(main)

        from app.services.ghs_pictogram import get_ghs_codes
        from app.services.clp_service import signal_word_for, class_signal
        up = {h.upper() for h in h_codes} | {h[:4].upper() for h in h_codes}
        # H411/H412/H413/H362 tek başına → uyarı kelimesi yok; H228/H261/H272/H242 kategoriye göre
        signal = signal_word_for(h_codes, [{'h_code': c[:4].upper(), 'signal': class_signal(k)}
                                           for k, c in zip(hazard_classes, h_codes)])

        # M faktörü ve ATE — bildirimlerden (yalnız Ek-6/Annex VI dışı maddeler bu yola gelir)
        m_factors, ate = {}, {}
        try:
            m_factors, ate = await _fetch_echa_m_ate(groups, up, _get, sem, group_pairs,
                                                     dict(zip((h.upper() for h in h_codes), hazard_classes)))
        except Exception as ex:
            print(f'[ECHA CHEM] {cas}: M/ATE alınamadı ({type(ex).__name__}: {ex})')

        print(f'[ECHA CHEM] {cas}: {len(groups)} bildirim grubu → {chosen}')
        return {
            'cas'           : cas,
            'name'          : subst.get('rmlName') or cas,
            'ec_no'         : subst.get('rmlEc') or '',
            'source'        : (f'ECHA C&L öz-sınıflandırma bildirimlerinden derlendi ({len(groups)} bildirim grubu, '
                               f'sınıf payı >%{_CL_CLASS_THRESHOLD:g}) — {ECHA_ATTRIBUTION}'),
            'signal'        : signal,
            'pictograms'    : get_ghs_codes(sorted(up)),
            'h_codes'       : h_codes,
            'hazard_classes': hazard_classes,
            'm_factors'     : m_factors,
            'ate'           : ate,
            'echa_extras'   : ECHA_EXTRAS_VER,   # M/ATE yöntem sürümü (eski kayıtlar yeniden çekilir)
            'notif_count'   : len(groups),
        }

    except Exception as e:
        print(f'[ECHA CHEM] {cas}: {type(e).__name__}: {e}')
    return None


# ── Bildirimlerden M faktörü ve ATE ────────────────────────────────────────────
# ECHA CHEM C&L: /industry/m-factors/{id}, /industry/acute-toxicity-estimates/{id}
_CL_EXTRA_GROUPS = 8   # ilgili tehlikeyi bildiren en yüksek paylı gruplar (sorgu sayısını sınırlar)

# Seçilen kategoriye uyan ATE aralıkları (SEA Ek-1 Tablo 3.1.1) — (alt, üst]
_ATE_RANGE = {
    'oral':              {'H300': (0, 50), 'H301': (50, 300), 'H302': (300, 2000)},
    'dermal':            {'H310': (0, 200), 'H311': (200, 1000), 'H312': (1000, 2000)},
    'inhalation_vapour': {'H330': (0, 2), 'H331': (2, 10), 'H332': (10, 20)},
    'inhalation_dust':   {'H330': (0, 0.5), 'H331': (0.5, 1), 'H332': (1, 5)},
    'inhalation':        {'H330': (0, 500), 'H331': (500, 2500), 'H332': (2500, 20000)},   # gaz, ppmV
}


def _ate_route(route_text: str, unit: str) -> str | None:
    r, u = (route_text or '').lower(), (unit or '').lower()
    if 'oral' in r:
        return 'oral'
    if 'dermal' in r:
        return 'dermal'
    if 'inhal' in r:
        if 'dust' in r or 'mist' in r:
            return 'inhalation_dust'
        if 'vapour' in r or 'vapor' in r:
            return 'inhalation_vapour'
        if 'gas' in r or 'ppm' in u:
            return 'inhalation'
        return None   # alt tür belirsiz — birim yorumlanamaz
    return None


async def _fetch_echa_m_ate(groups: list, h_up: set, _get, sem, group_pairs: dict | None = None,
                            chosen: dict | None = None) -> tuple:
    """Seçilen sınıflandırmaya göre M faktörü (H400/H410 varsa) ve ATE (akut toksisite varsa).

    Yalnız ilgili tehlikeyi bildiren gruplar sayılır (M: H400/H410; ATE: seçilen kategori ve yol).
    M: M yazmayan bildirimler M=1 sayılır (Akut/Kronik 1 için SEA Ek-1 4.1.3.5.5.5 Tablo 4.1.3'ün en düşük M'si; M>1
       yalnız daha yüksek toksisitede verilir). Önceden yalnız M yazanlar
       sayılıyordu; azınlıktaki yüksek M seçilebiliyordu. Ağırlığı en yüksek değer; 2 puandan yakınlar → yüksek M.
    ATE: yalnız sayısal değer bildirenler arasında (seçilen kategorinin aralığında) ağırlığı en yüksek değer; yakınlar
       → düşük ATE (ihtiyatlı). ATE bir deney verisidir (SEA Ek-1 3.1.3.6: veri varsa kullanılır); bildirimde
       yazılmaması dönüşüm değerinin seçildiği anlamına gelmez — değer yoksa hesap Tablo 3.1.2 dönüşüm değerini kullanır.
       ATE'yi çoğu zaman bildirimlerin binde birkaçı yazdığından, bildirimden gelen değer yalnız Tablo 3.1.2 dönüşüm
       değerinden DÜŞÜKSE (daha ihtiyatlıysa) kullanılır; değilse yazılmaz ve hesap dönüşüm değerini kullanır."""
    from app.services.clp_service import ATE_DEFAULTS
    group_pairs, chosen = group_pairs or {}, chosen or {}
    need_m = bool(h_up & {'H400', 'H410'})
    ate_codes = {'oral': ('H300', 'H301', 'H302'), 'dermal': ('H310', 'H311', 'H312'),
                 'inhal': ('H330', 'H331', 'H332')}
    # yol → (seçilen H kodu, ana sınıf "Acute Tox. N")
    ate_need = {r: (c, chosen.get(c, '')) for r, cs in ate_codes.items() for c in cs if c in h_up}
    if not (need_m or ate_need):
        return {}, {}

    def _has(gid, code, main=''):
        return any(c == code and (not main or m == main) for m, c in group_pairs.get(gid, ()))

    def _relevant(g):
        gid = g['classificationId']
        if not group_pairs:      # eski çağrı biçimi: grup ayrıntısı yok → tüm gruplar
            return True
        return (need_m and (_has(gid, 'H400') or _has(gid, 'H410'))) or                any(_has(gid, c, m) for c, m in ate_need.values())

    top = sorted([g for g in groups if _relevant(g)],
                 key=lambda g: -float(g.get('substanceNotificationPercentage') or 0))[:_CL_EXTRA_GROUPS]

    async def _one(g):
        async with sem:
            cid = g['classificationId']
            m = (await _get(f'/api-cnl-inventory/industry/m-factors/{cid}')).get('items', []) if need_m else []
            a = (await _get(f'/api-cnl-inventory/industry/acute-toxicity-estimates/{cid}')).get('items', [])                 if ate_need else []
            return cid, float(g.get('substanceNotificationPercentage') or 0), m, a

    m_w = {'acute': {}, 'chronic': {}}
    ate_w: dict = {}            # alt yol → {değer: ağırlık}
    for cid, gpct, m_items, a_items in await asyncio.gather(*[_one(g) for g in top]):
        for k, key, code in (('acute', 'mfactorAcute', 'H400'), ('chronic', 'mfactorChronic', 'H410')):
            if code not in h_up or (group_pairs and not _has(cid, code)):
                continue
            given = 0.0
            for it in m_items:
                v, p = it.get(key), float(it.get('percentage') or 0)
                if v:
                    m_w[k][int(v)] = m_w[k].get(int(v), 0.0) + gpct * p / 100.0
                    given += p
            m_w[k][1] = m_w[k].get(1, 0.0) + gpct * max(0.0, 100.0 - given) / 100.0
        for it in a_items:
            route_text = (it.get('routeExposure') or {}).get('routeOfExposure', '')
            for est in it.get('acuteToxicities') or []:
                val = est.get('estimation')
                route = _ate_route(route_text, est.get('unit', ''))
                if val is None or not route:
                    continue
                fam = 'inhal' if route.startswith('inhal') else route
                if group_pairs and fam in ate_need and not _has(cid, *ate_need[fam]):
                    continue     # bu grup o yolda seçilen kategoriyi bildirmemiş
                ate_w.setdefault(route, {})
                ate_w[route][float(val)] = ate_w[route].get(float(val), 0.0) +                     gpct * float(est.get('percentage') or 0) / 100.0

    m_factors = {}
    for k, need_h in (('acute', 'H400'), ('chronic', 'H410')):
        if need_h in h_up and m_w[k]:
            topw = max(m_w[k].values())
            m_factors[k] = max(v for v, w in m_w[k].items() if topw - w < _CL_TIE_MARGIN)

    ate = {}
    for route, vals in ate_w.items():
        ranges = _ATE_RANGE.get(route, {})
        cat = next((h for h in ranges if h in h_up), None)
        if not cat:
            continue
        lo, hi = ranges[cat]
        fit = {v: w for v, w in vals.items() if lo < v <= hi}
        if fit:
            topw = max(fit.values())
            best = min(v for v, w in fit.items() if topw - w < _CL_TIE_MARGIN)   # yakınsa ihtiyatlı (düşük)
            fam = 'inhal' if route.startswith('inhal') else route
            main = ate_need.get(fam, ('', ''))[1]
            conv = ATE_DEFAULTS.get('inhalation_gas' if route == 'inhalation' else route, {}).get(main)
            if conv is not None and best >= float(conv):
                continue     # dönüşüm değerinden yüksek/eşit → yazılmaz, hesap dönüşüm değerini kullanır
            ate[route] = best
    return m_factors, ate


# ---------------------------------------------------------------------------
# PubChem — Fiziksel/Kimyasal Özellikler + LD50 (H-kodu için DEĞİL)
# ---------------------------------------------------------------------------

async def _get_pubchem_cid(cas: str, client: httpx.AsyncClient) -> int | None:
    """CAS → PubChem CID"""
    try:
        r = await client.get(
            f'https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{cas}/cids/JSON',
            timeout=8.0
        )
        if r.status_code == 200:
            ids = r.json().get('IdentifierList', {}).get('CID', [])
            return ids[0] if ids else None
    except Exception:
        pass
    return None


async def fetch_pubchem_properties(cas: str) -> dict:
    """
    PubChem'den fiziksel/kimyasal özellikler çek.
    SDS Bölüm 9 (fiziksel/kimyasal özellikler) ve Bölüm 11 (toksikoloji) için.

    Döndürülen alanlar:
      iupac_name, molecular_formula, molecular_weight,
      boiling_point, melting_point, flash_point, vapor_pressure,
      water_solubility, log_kow (XLogP), ld50
    """
    cas = cas.strip()
    try:
        async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
            cid = await _get_pubchem_cid(cas, client)
            if not cid:
                return {}

            # Temel özellikler
            props_r = await client.get(
                f'https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/property/'
                'IUPACName,MolecularFormula,MolecularWeight,XLogP,'
                'HBondDonorCount,HBondAcceptorCount/JSON',
                timeout=8.0
            )
            props = {}
            if props_r.status_code == 200:
                p = props_r.json().get('PropertyTable', {}).get('Properties', [])
                props = p[0] if p else {}

            # GHS view'dan fiziksel veriler (BP, MP, FP, buhar basıncı, çözünürlük, LD50)
            view_r = await client.get(
                f'https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/data/compound/{cid}/JSON/'
                '?heading=Physical+and+Chemical+Properties',
                timeout=12.0
            )
            physical = {}
            if view_r.status_code == 200:
                physical = _parse_pubchem_physical(view_r.json())

            # LD50 verisi
            tox_r = await client.get(
                f'https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/data/compound/{cid}/JSON/'
                '?heading=Acute+Effects',
                timeout=12.0
            )
            ld50 = {}
            if tox_r.status_code == 200:
                ld50 = _parse_pubchem_ld50(tox_r.json())

            return {
                'cid'               : cid,
                'iupac_name'        : props.get('IUPACName', ''),
                'molecular_formula' : props.get('MolecularFormula', ''),
                'molecular_weight'  : props.get('MolecularWeight'),
                'log_kow'           : props.get('XLogP'),
                'hbond_donors'      : props.get('HBondDonorCount'),
                'hbond_acceptors'   : props.get('HBondAcceptorCount'),
                **physical,
                **ld50,
                'source'            : 'PubChem',
            }

    except Exception as e:
        print(f'[PubChem properties] {cas}: {e}')
    return {}


def _parse_pubchem_physical(data: dict) -> dict:
    """PubChem pug_view JSON'dan fiziksel özellikleri çıkar."""
    result = {}
    FIELD_MAP = {
        'Boiling Point'       : 'boiling_point',
        'Melting Point'       : 'melting_point',
        'Flash Point'         : 'flash_point',
        'Vapor Pressure'      : 'vapor_pressure',
        'Water Solubility'    : 'water_solubility',
        'Density'             : 'density',
        'Auto-Ignition'       : 'autoignition_temp',
        'Viscosity'           : 'viscosity',
        'Refractive Index'    : 'refractive_index',
        'pH'                  : 'ph',
        'Decomposition'       : 'decomposition_temp',
    }
    try:
        def walk(obj):
            if isinstance(obj, dict):
                name = obj.get('TOCHeading', '') or obj.get('Name', '')
                key  = FIELD_MAP.get(name)
                if key:
                    strings = obj.get('Value', {}).get('StringWithMarkup', [])
                    if strings:
                        result[key] = strings[0].get('String', '')
                for v in obj.values():
                    walk(v)
            elif isinstance(obj, list):
                for item in obj:
                    walk(item)
        walk(data)
    except Exception:
        pass
    return result


def _parse_pubchem_ld50(data: dict) -> dict:
    """PubChem Acute Effects bölümünden LD50 değerlerini çıkar."""
    ld50_values = []
    try:
        def walk(obj):
            if isinstance(obj, dict):
                name = obj.get('Name', '') or obj.get('TOCHeading', '')
                if 'LD50' in name or 'LD 50' in name:
                    strings = obj.get('Value', {}).get('StringWithMarkup', [])
                    for s in strings:
                        text = s.get('String', '')
                        if text:
                            ld50_values.append(text)
                for v in obj.values():
                    walk(v)
            elif isinstance(obj, list):
                for item in obj:
                    walk(item)
        walk(data)
    except Exception:
        pass
    return {'ld50': ld50_values[:5]} if ld50_values else {}


# ---------------------------------------------------------------------------
# PubChem GHS fallback — ECHA C&L bulunamazsa H-kodları için
# ---------------------------------------------------------------------------

async def _get_pubchem_ec_no(cid: int, client: httpx.AsyncClient) -> str:
    """
    PubChem synonym listesinden EC numarasını çıkar.
    EC numarası formatı: ddd-ddd-d (EINECS/ELINCS/NLP, 9 karakter).
    Örnek: 203-928-6 (HDTMAC), 200-578-6 (Etanol).
    """
    try:
        r = await client.get(
            f'https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/synonyms/JSON',
            timeout=8.0,
        )
        if r.status_code == 200:
            info_list = r.json().get('InformationList', {}).get('Information', [])
            for info in info_list:
                for syn in info.get('Synonym', []):
                    if re.match(r'^\d{3}-\d{3}-\d$', syn.strip()):
                        return syn.strip()
    except Exception:
        pass
    return ''


async def _fetch_pubchem_ghs_fallback(cas: str, client: httpx.AsyncClient) -> dict | None:
    """
    ECHA C&L doğrudan API'si başarısız olursa PubChem GHS Classification'ı dene.
    PubChem, ECHA C&L bildirimlerini kısmen barındırır — eksik kalabilir.
    """
    try:
        cid = await _get_pubchem_cid(cas, client)
        if not cid:
            return None

        r = await client.get(
            f'https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/data/compound/{cid}/JSON/'
            '?heading=GHS+Classification',
            timeout=12.0
        )
        if r.status_code != 200:
            return None

        data = r.json()

        def find_ghs(obj):
            if isinstance(obj, dict):
                if obj.get('TOCHeading') == 'GHS Classification':
                    return obj
                for v in obj.values():
                    res = find_ghs(v)
                    if res:
                        return res
            elif isinstance(obj, list):
                for item in obj:
                    res = find_ghs(item)
                    if res:
                        return res
            return None

        ghs_node = find_ghs(data)
        groups   = _parse_ghs_groups(ghs_node.get('Information', [])) if ghs_node else []
        best     = _best_group(groups) if groups else None

        # Madde ismi ve EC numarası — H kodu olmasa da çek (sınıflandırılmamış madde)
        props_r, ec_no = await asyncio.gather(
            client.get(
                f'https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/property/'
                'IUPACName,MolecularFormula/JSON',
                timeout=8.0,
            ),
            _get_pubchem_ec_no(cid, client),
        )
        name = cas
        if props_r.status_code == 200:
            p = props_r.json().get('PropertyTable', {}).get('Properties', [])
            name = (p[0].get('IUPACName') if p else '') or cas

        # H kodu yok → sınıflandırılmamış madde olarak döndür (isim + boş hazards)
        if not best or not best['h_codes']:
            return {
                'cas'           : cas,
                'name'          : name,
                'ec_no'         : ec_no,
                'source'        : 'PubChem (sınıflandırılmamış)',
                'source_note'   : '',
                'signal'        : '',
                'pictograms'    : [],
                'h_codes'       : [],
                'hazard_classes': [],
                'm_factors'     : {},
                'notif_count'   : 0,
                'notif_summary' : '',
            }

        src_note = 'CMR birleştirme aktif' if best.get('_cmr_merged') else ''
        result = {
            'cas'           : cas,
            'name'          : name,
            'ec_no'         : ec_no,
            'source'        : f'PubChem/ECHA C&L ({best["notif_count"]} bildirim)',
            'source_note'   : src_note,
            'signal'        : best['signal'],
            'pictograms'    : best['pictograms'],
            'h_codes'       : best['h_codes'],
            'hazard_classes': best['hazard_classes'],
            'm_factors'     : best.get('m_factors', {}),
            'notif_count'   : best['notif_count'],
            'notif_summary' : best['summary'],
        }
        if best.get('physical_state_conflict'):
            result['physical_state_conflict'] = best['physical_state_conflict']
        return result

    except Exception as e:
        print(f'[PubChem GHS fallback] {cas}: {e}')
    return None


def _dedupe_h_codes(result: dict) -> dict:
    """
    CLP dominans kurallarını API yanıtına uygula — çakışan H kodlarını temizle.
    Örn: H318 varsa H319 düşer; H314 varsa H315+H319 düşer.
    ECHA C&L çoklu bildirim birleştirmesinden kaynaklanan çakışmaları önler.
    Kural seti: clp_service.DOMINANCE (tek kaynak — import ile).
    """
    from app.services.clp_service import DOMINANCE as _DOM
    h_codes = result.get('h_codes', [])
    hazard_classes = result.get('hazard_classes', [])
    h_set = set(h_codes)
    dominated = set()
    for dominant, subs in _DOM.items():
        if dominant in h_set:
            dominated.update(subs)
    if not dominated:
        return result
    kept = [i for i, h in enumerate(h_codes) if h not in dominated]
    result['h_codes'] = [h_codes[i] for i in kept]
    if hazard_classes:
        result['hazard_classes'] = [hazard_classes[i] for i in kept if i < len(hazard_classes)]
    removed = dominated & h_set
    if removed:
        print(f'[dedupe_h_codes] Cakisan kodlar kaldirildi: {sorted(removed)}')
    return result


def _record_change(cas: str, new: dict) -> None:
    """Önceki ECHA kaydıyla H-kodları farklıysa data/echa_changes.jsonl'e satır ekle (SDS revizyon takibi)."""
    from app.services.substance_lookup import _read_cl_file, _ECHA_CL_DIR
    old = _read_cl_file(_ECHA_CL_DIR, cas)
    if not old:
        return
    old_h = old.get('labelling', {}).get('h_codes', [])
    new_h = new.get('h_codes', [])
    added   = [h for h in new_h if h not in old_h]
    removed = [h for h in old_h if h not in new_h]
    if not added and not removed:
        return
    rec = {
        'tarih'       : datetime.now(timezone.utc).strftime('%Y-%m-%d'),
        'cas'         : cas,
        'ad'          : new.get('name', ''),
        'eklenen'     : added,
        'cikan'       : removed,
        'onceki'      : old_h,
        'yeni'        : new_h,
        'onceki_tarih': old.get('fetched_at', ''),
    }
    try:
        with open(CHANGES_FILE, 'a', encoding='utf-8') as f:
            f.write(json.dumps(rec, ensure_ascii=False) + '\n')
        from app.services.data_store import persist
        persist(CHANGES_FILE)
        print(f'[ECHA değişiklik] {cas}: eklenen {added}, çıkan {removed}')
    except Exception as e:
        print(f'[ECHA değişiklik] {cas}: kayıt hatası — {e}')


async def lookup_echa_api(cas: str, refresh: bool = False) -> dict | None:
    """
    Canlı API hiyerarşisi (lokal önbellekte bulunamazsa çağrılır):
      1. ECHA C&L Inventory (chem.echa.europa.eu) → data/echa_cl/'a kaydet
      2. PubChem GHS fallback → data/pubchem_cl/'a kaydet

    refresh=True: eskimiş kaydı yenile — oturum önbelleği atlanır, sadece ECHA denenir;
    başarısızsa mevcut kayıt olduğu gibi kalır.
    Sonuç ilgili önbelleğe yazılır; bir sonraki sorgu lokal dosyadan gelir.
    """
    from app.services.substance_lookup import save_echa_cl_substance, save_pubchem_substance, _is_stale

    cas = cas.strip()
    cache = _load_cache()
    if not refresh and cas in cache and not _is_stale(cache[cas]):
        before = list(cache[cas].get('h_codes', []))
        result = _dedupe_h_codes(cache[cas])
        if list(result.get('h_codes', [])) != before:
            cache[cas] = result
            _save_cache(cache)
        return result

    try:
        async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:

            # Sıra 1: ECHA C&L → data/echa_cl/
            result = await _fetch_echa_cl_direct(cas, client)
            if result:
                result = _dedupe_h_codes(result)
                result['_cache_source'] = 'echa_cl'
                result['fetched_at']    = datetime.now(timezone.utc).isoformat(timespec='seconds')
                _record_change(cas, result)
                save_echa_cl_substance(cas, result)
                cache[cas] = result
                _save_cache(cache)
                return result

            if refresh:
                return None

            # Sıra 2: PubChem GHS fallback → data/pubchem_cl/
            print(f'[ECHA C&L] {cas}: ECHA sonucu yok, PubChem fallback deneniyor')
            result = await _fetch_pubchem_ghs_fallback(cas, client)
            if result:
                result = _dedupe_h_codes(result)
                result['_cache_source'] = 'pubchem'
                result['fetched_at']    = datetime.now(timezone.utc).isoformat(timespec='seconds')
                save_pubchem_substance(cas, result)
                cache[cas] = result
                _save_cache(cache)
                return result

    except Exception as e:
        print(f'[lookup_echa_api] {cas}: {e}')
    return None


# ---------------------------------------------------------------------------
# Ana lookup
# ---------------------------------------------------------------------------

async def _supplement_sea_with_echa(cas: str, sea_result: dict) -> dict:
    """
    SEA Ek-6 / Annex VI kaydını ECHA C&L öz-sınıflandırması ile tamamla.
    Harmonize olmayan tehlike sınıfları için ECHA konsensüs H-kodlarını ekler.
    SEA Ek-6 kayıtlarına dokunulmaz — sadece fazladan kodlar eklenir.
    Dönen sonuçta 'classification_sources' ve 'echa_supplement' alanları bulunur
    (arayüz bilgilendirmesi için).
    """
    echa = lookup_archive(cas)
    if not echa:
        echa = await lookup_echa_api(cas)

    if not echa or not echa.get('h_codes'):
        return sea_result

    sea_h_set = set(sea_result.get('h_codes', []))
    extra_h = [h for h in echa.get('h_codes', []) if h not in sea_h_set]

    if not extra_h:
        return sea_result

    classification_sources = {h: 'SEA Ek-6' for h in sea_result.get('h_codes', [])}
    for h in extra_h:
        classification_sources[h] = 'ECHA C&L öz-sınıflandırma'

    sea_cls = sea_result.get('hazard_classes', [])
    extra_cls = []
    for h in extra_h:
        cls = _H_TO_CLASS.get(h, '')
        if cls and cls not in sea_cls and cls not in extra_cls:
            extra_cls.append(cls)

    sea_pict = sea_result.get('pictograms', [])
    extra_pict = [p for p in echa.get('pictograms', []) if p not in sea_pict]

    result = dict(sea_result)
    result['h_codes']                = sea_result['h_codes'] + extra_h
    result['hazard_classes']         = sea_cls + extra_cls
    result['pictograms']             = sea_pict + extra_pict
    result['classification_sources'] = classification_sources
    result['echa_supplement']        = extra_h
    result['echa_supplement_source'] = echa.get('source', 'ECHA C&L')

    print(f'[sea_supplement] {cas}: ECHA\'dan {len(extra_h)} ek H-kodu: {extra_h}')
    return result


async def lookup_substance(cas: str) -> dict:
    """
    TR SDS Arama Hiyerarşisi:
      Sıra 1 — SEA Ek-6                MUTLAK (uyumlaştırılmış — KKDİK)
      Sıra 2 — AB CLP Annex VI         (SEA güncellenmemişse en güncel bilimsel veri)
      Sıra 3 — Tedarikçi/Kullanıcı     (manuel onaylı, substances_custom.json)
      Sıra 4 — ECHA C&L Arşivi         (önceki canlı çekimler, kalıcı)
      Sıra 5 — ECHA C&L Canlı API      (PubChem → arşive kaydet)
    """
    cas = cas.strip()
    from app.services.reach_db import get_ec_no, get_reg_no

    def _enrich(d: dict) -> dict:
        d['ec_no']    = d.get('ec_no')    or get_ec_no(cas)    or ''
        d['reach_no'] = d.get('reach_no') or get_reg_no(cas)   or ''
        return d

    local = lookup_local(cas)

    # ── Sıra 1: SEA Ek-6 — MUTLAK, harmonize H-kodlar; ECHA ile supplement edilir ──
    if local and local.get('source_priority') == 1:
        return await _supplement_sea_with_echa(cas, _enrich(local))

    # ── Sıra 2: AB CLP Annex VI — aynı şekilde ECHA ile supplement edilir ──────────
    if local and local.get('source_priority') == 2:
        return await _supplement_sea_with_echa(cas, _enrich(local))

    # ── Sıra 3: Tedarikçi/Kullanıcı girişi (manuel onaylı) ──────────────────
    if local and local.get('source_priority') == 4:
        return _enrich(local)

    # ── Sıra 4: Kalıcı ECHA C&L arşivi ──────────────────────────────────────
    archived = lookup_archive(cas)
    if archived:
        return _enrich(archived)

    # ── Sıra 5: PubChem / ECHA C&L canlı çekim ───────────────────────────────
    echa = await lookup_echa_api(cas)
    if echa:
        _enrich(echa)
        _save_to_archive(cas, echa)
        _auto_save_custom(cas, echa)
        return echa

    # ── Bulunamadı ────────────────────────────────────────────────────────────
    return {
        'cas': cas, 'name': '', 'ec_no': get_ec_no(cas) or '',
        'reach_no': get_reg_no(cas) or '', 'source': 'not_found',
        'h_codes': [], 'hazard_classes': [],
    }


def _auto_save_custom(cas: str, echa_result: dict):
    """PubChem'den gelen veriyi substances_custom.json'a kaydet."""
    try:
        from app.services.substance_lookup import save_custom_substance, is_annex_vi
        if is_annex_vi(cas):
            return  # Annex VI'da varsa custom'a yazma
        entry = {
            'name'      : echa_result.get('name', ''),
            'ec_no'     : echa_result.get('ec_no', ''),
            'annex_vi'  : False,
            'signal'    : echa_result.get('signal', ''),
            'pictograms': echa_result.get('pictograms', []),
            'hazards'   : [
                {'h_class': cls, 'h_code': code}
                for cls, code in zip(
                    echa_result.get('hazard_classes', []),
                    echa_result.get('h_codes', [])
                )
            ],
            'm_factors' : {},
            'index_no'  : '',
            'atp'       : f'PubChem/{echa_result.get("notif_count", 0)} notif',
        }
        is_new = save_custom_substance(cas, entry)
        if is_new:
            print(f'[custom] Yeni madde kaydedildi: {cas} ({echa_result.get("name","")}) '
                  f'— {echa_result.get("notif_count", 0)} bildirim')
        else:
            print(f'[custom] Güncellendi: {cas}')
    except Exception as ex:
        print(f'[auto_save_custom] {ex}')


# Sync wrapper (non-async ortamlar için)
def lookup_substance_sync(cas: str) -> dict:
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            return lookup_local(cas) or {
                'cas': cas, 'name': '', 'ec_no': '', 'reach_no': '',
                'source': 'not_found', 'h_codes': [], 'hazard_classes': []
            }
        return loop.run_until_complete(lookup_substance(cas))
    except Exception:
        return lookup_local(cas) or {
            'cas': cas, 'name': '', 'ec_no': '', 'reach_no': '',
            'source': 'not_found', 'h_codes': [], 'hazard_classes': []
        }
