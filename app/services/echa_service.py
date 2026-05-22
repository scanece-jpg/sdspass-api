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
# ECHA C&L Inventory — Doğrudan ECHA API
# ---------------------------------------------------------------------------

async def _fetch_echa_cl_direct(cas: str, client: httpx.AsyncClient) -> dict | None:
    """
    ECHA C&L Inventory API'sinden H-kodu ve sınıflandırma verisi çek.

    Endpoint: api.echa.europa.eu — önce CAS ile madde ara, sonra C&L bildirimlerini al.
    ECHA C&L'de ~220.000 madde var (Annex VI'da olmayan şirket bildirimleri dahil).
    """
    try:
        # 1. CAS ile madde ara → ECHA substance ID bul
        r = await client.get(
            'https://api.echa.europa.eu/api/substances/search',
            params={'q': cas, 'number_type': 'cas'},
            timeout=10.0,
            headers={'Accept': 'application/json'},
        )
        if r.status_code != 200:
            return None
        results = r.json()
        substances = results if isinstance(results, list) else results.get('results', [])
        if not substances:
            return None
        substance = substances[0]
        echa_id  = substance.get('id') or substance.get('substanceId') or substance.get('ecNumber')
        name     = substance.get('iupacName') or substance.get('name') or cas
        ec_no    = substance.get('ecNumber', '')

        # 2. C&L bildirimlerini çek
        cl_r = await client.get(
            f'https://api.echa.europa.eu/api/substances/{echa_id}/classifications',
            timeout=10.0,
            headers={'Accept': 'application/json'},
        )
        if cl_r.status_code != 200:
            return None
        cl_data = cl_r.json()

        # 3. H-kodları ve sinyali çıkar
        h_codes        = []
        hazard_classes = []
        pictograms     = []
        signal         = ''
        notif_count    = 0

        notifications = cl_data if isinstance(cl_data, list) else cl_data.get('notifications', [])
        notif_count = len(notifications)

        # En kapsamlı bildirimi seç (en çok H-kodu içeren)
        best_notif = None
        for notif in notifications:
            h_list = notif.get('hazardStatements', notif.get('hStatements', []))
            if len(h_list) > len(best_notif.get('hazardStatements', []) if best_notif else []):
                best_notif = notif

        if best_notif:
            for hs in best_notif.get('hazardStatements', best_notif.get('hStatements', [])):
                code = hs.get('code') or hs.get('hazardStatementCode') or ''
                if code and code not in h_codes:
                    h_codes.append(code)
                    cls = _H_TO_CLASS.get(code.split(' ')[0], '')
                    if cls and cls not in hazard_classes:
                        hazard_classes.append(cls)
            for ps in best_notif.get('pictograms', []):
                p = ps.get('code') or ps.get('pictogramCode') or ''
                p_mapped = _PICT_MAP.get(p.lower(), '')
                if p_mapped and p_mapped not in pictograms:
                    pictograms.append(p_mapped)
            signal = best_notif.get('signalWord', best_notif.get('signal', ''))

        if not h_codes:
            return None

        return {
            'cas'           : cas,
            'name'          : name,
            'ec_no'         : ec_no,
            'source'        : f'ECHA C&L Inventory ({notif_count} bildirim)',
            'signal'        : signal,
            'pictograms'    : pictograms,
            'h_codes'       : h_codes,
            'hazard_classes': hazard_classes,
            'm_factors'     : {},
            'notif_count'   : notif_count,
        }

    except Exception as e:
        print(f'[ECHA C&L direct] {cas}: {e}')
    return None


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

        ghs_node  = find_ghs(data)
        if not ghs_node:
            return None
        groups = _parse_ghs_groups(ghs_node.get('Information', []))
        best   = _best_group(groups)
        if not best or not best['h_codes']:
            return None

        # Madde ismi için temel PubChem sorgusu
        props_r = await client.get(
            f'https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/property/'
            'IUPACName,MolecularFormula/JSON',
            timeout=8.0
        )
        name = cas
        if props_r.status_code == 200:
            p = props_r.json().get('PropertyTable', {}).get('Properties', [])
            name = (p[0].get('IUPACName') if p else '') or cas

        src_note = 'CMR birleştirme aktif' if best.get('_cmr_merged') else ''
        result = {
            'cas'           : cas,
            'name'          : name,
            'ec_no'         : '',
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


async def lookup_echa_api(cas: str) -> dict | None:
    """
    Canlı API hiyerarşisi (lokal önbellekte bulunamazsa çağrılır):
      1. ECHA C&L Inventory API (api.echa.europa.eu) → data/echa_cl/'a kaydet
      2. PubChem GHS fallback → data/pubchem_cl/'a kaydet

    Sonuç ilgili önbelleğe yazılır; bir sonraki sorgu lokal dosyadan gelir.
    """
    from app.services.substance_lookup import save_echa_cl_substance, save_pubchem_substance

    cas = cas.strip()
    cache = _load_cache()
    if cas in cache:
        return cache[cas]

    try:
        async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:

            # Sıra 1: ECHA C&L API → data/echa_cl/
            result = await _fetch_echa_cl_direct(cas, client)
            if result:
                result['_cache_source'] = 'echa_cl'
                save_echa_cl_substance(cas, result)
                cache[cas] = result
                _save_cache(cache)
                return result

            # Sıra 2: PubChem GHS fallback → data/pubchem_cl/
            print(f'[ECHA C&L] {cas}: doğrudan API boş, PubChem fallback deneniyor')
            result = await _fetch_pubchem_ghs_fallback(cas, client)
            if result:
                result['_cache_source'] = 'pubchem'
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

    # ── Sıra 1: SEA Ek-6 — MUTLAK, tartışma biter ───────────────────────────
    if local and local.get('source_priority') == 1:
        return _enrich(local)

    # ── Sıra 2: AB CLP Annex VI ───────────────────────────────────────────────
    if local and local.get('source_priority') == 2:
        return _enrich(local)

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
