"""
ECHA / PubChem Lookup Servisi
==============================
Lokal DB'de bulunamayan maddeleri PubChem üzerinden çeker.
PubChem, ECHA C&L Inventory bildirim verilerini barındırır (GHS Classification).

Seçim mantığı (kullanıcı isteği):
  Birden fazla bildirim grubu varsa → bildirim sayısı EN YÜKSEK olan
  (= "Aggregated GHS information ... from N notifications") veya
  "Joint Notification" ibareli grup seçilir.

Akış:
  1. substances_annex_vi.json + substances_custom.json → hızlı döner
  2. PubChem GHS API → ECHA C&L notification'larını parse et
  3. Sonuç substances_custom.json'a otomatik kaydedilir

NOT: clp_cl_data.json ve annex_vi_lookup.json artık kullanılmıyor.
     substances_annex_vi.json (4155 madde, tam format) ikisini de kapsar.
"""

import re, httpx, asyncio, json, os
from pathlib import Path

# Lokal cache dosyası (oturum boyunca tekrar çekmeyelim)
CACHE_FILE = Path(__file__).parent / 'echa_cache.json'

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
    'H300':'Acute Tox. 1 (oral)','H301':'Acute Tox. 3 (oral)','H302':'Acute Tox. 4 (oral)',
    'H304':'Asp. Tox. 1',
    'H310':'Acute Tox. 1 (derm.)','H311':'Acute Tox. 3 (derm.)','H312':'Acute Tox. 4 (derm.)',
    'H314':'Skin Corr. 1','H315':'Skin Irrit. 2',
    'H317':'Skin Sens. 1','H318':'Eye Dam. 1','H319':'Eye Irrit. 2',
    'H330':'Acute Tox. 1 (inhal.)','H331':'Acute Tox. 3 (inhal.)','H332':'Acute Tox. 4 (inhal.)',
    'H334':'Resp. Sens. 1',
    'H335':'STOT SE 3 (resp.)','H336':'STOT SE 3 (narc.)',
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
    substances_annex_vi.json + substances_custom.json içinde CAS ara.
    clp_cl_data.json ve annex_vi_lookup.json artık kullanılmıyor.
    """
    from app.services.substance_lookup import lookup_substance
    entry = lookup_substance(cas.strip())
    if not entry:
        return None
    return {
        'cas'           : cas,
        'name'          : entry.get('name', ''),
        'source'        : 'Annex VI' if entry.get('annex_vi') else 'Custom DB',
        'h_codes'       : [h['h_code'] for h in entry.get('hazards', []) if h.get('h_code')],
        'hazard_classes': [h['h_class'] for h in entry.get('hazards', []) if h.get('h_class')],
        'signal'        : entry.get('signal', ''),
        'pictograms'    : entry.get('pictograms', []),
    }


# ---------------------------------------------------------------------------
# Cache
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
            # "H225 (> 99.9%): Highly Flammable liquid and vapor [...]"
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

        elif name == 'ECHA C&L Notifications Summary':
            current['summary'] = text
            current['notif_count'] = _extract_notif_count(text)

    if current is not None:
        groups.append(current)

    return groups


def _best_group(groups: list) -> dict | None:
    """
    Bildirim sayısı en yüksek grubu seç.
    Eşitlik durumunda Joint Notification öncelikli.
    """
    if not groups:
        return None
    # Sadece ECHA C&L summary içeren gruplara bak
    echa_groups = [g for g in groups if g['notif_count'] > 0]
    if echa_groups:
        return max(echa_groups, key=lambda g: g['notif_count'])
    # ECHA summary yoksa (örn. sadece tek grup) ilkini al
    return groups[0]


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


async def _get_pubchem_props(cid: int, client: httpx.AsyncClient) -> dict:
    """CID → IUPAC name, molecular weight"""
    try:
        r = await client.get(
            f'https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/property/IUPACName,MolecularWeight,MolecularFormula/JSON',
            timeout=8.0
        )
        if r.status_code == 200:
            props = r.json().get('PropertyTable', {}).get('Properties', [])
            return props[0] if props else {}
    except Exception:
        pass
    return {}


async def lookup_echa_api(cas: str) -> dict | None:
    """
    PubChem GHS endpoint'inden ECHA C&L bildirim verisi çek.
    En yüksek bildirim sayılı grubu seç.
    """
    cas = cas.strip()
    cache = _load_cache()
    if cas in cache:
        return cache[cas]

    try:
        async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:

            # 1. CID bul
            cid = await _get_pubchem_cid(cas, client)
            if not cid:
                return None

            # 2. GHS Classification view
            r = await client.get(
                f'https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/data/compound/{cid}/JSON/?heading=GHS+Classification',
                timeout=12.0
            )
            if r.status_code != 200:
                return None

            data = r.json()

            # 3. GHS Classification node'unu bul
            def find_ghs(obj):
                if isinstance(obj, dict):
                    if obj.get('TOCHeading') == 'GHS Classification':
                        return obj
                    for v in obj.values():
                        res = find_ghs(v)
                        if res: return res
                elif isinstance(obj, list):
                    for item in obj:
                        res = find_ghs(item)
                        if res: return res
                return None

            ghs_node = find_ghs(data)
            if not ghs_node:
                return None

            info_list = ghs_node.get('Information', [])
            groups    = _parse_ghs_groups(info_list)
            best      = _best_group(groups)

            if not best:
                return None

            # 4. Madde ismi
            props = await _get_pubchem_props(cid, client)
            name  = props.get('IUPACName', '') or cas

            result = {
                'cas'          : cas,
                'name'         : name,
                'ec_no'        : '',
                'source'       : f'ECHA C&L / PubChem ({best["notif_count"]} bildirim)',
                'signal'       : best['signal'],
                'pictograms'   : best['pictograms'],
                'h_codes'      : best['h_codes'],
                'hazard_classes': best['hazard_classes'],
                'notif_count'  : best['notif_count'],
                'notif_summary': best['summary'],
            }

            # Cache'e kaydet
            cache[cas] = result
            _save_cache(cache)
            return result

    except Exception as e:
        print(f'[PubChem lookup] {cas}: {e}')
    return None


# ---------------------------------------------------------------------------
# Ana lookup
# ---------------------------------------------------------------------------

async def lookup_substance(cas: str) -> dict:
    """
    Sıra: substances_annex_vi + substances_custom → PubChem/ECHA C&L
           → PubChem/ECHA C&L API → boş sonuç
    Lokal DB'de yoksa PubChem'den çeker ve custom'a kaydeder.
    """
    cas = cas.strip()

    # 1. Lokal DB (annex_vi + custom) — lookup_local içinde birleşik
    local = lookup_local(cas)
    if local:
        from app.services.reach_db import get_ec_no, get_reg_no
        local['ec_no']    = local.get('ec_no') or get_ec_no(cas) or ''
        local['reach_no'] = get_reg_no(cas) or ''
        return local

    # 2. PubChem → ECHA C&L
    echa = await lookup_echa_api(cas)  # cache'den veya canlı çekim
    if echa:
        from app.services.reach_db import get_ec_no, get_reg_no
        echa['ec_no']    = echa.get('ec_no') or get_ec_no(cas) or ''
        echa['reach_no'] = get_reg_no(cas) or ''

        # Annex VI'da yoksa → custom listesine otomatik kaydet
        _auto_save_custom(cas, echa)
        return echa

    # 4. Bulunamadı
    from app.services.reach_db import get_ec_no, get_reg_no
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
