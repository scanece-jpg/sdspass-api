"""
REACH Kayıt Numarası Önbelleği
ECHA substances API'sinden çekilen kayıt numaralarını diske kaydeder.
Format: data/reach_cache/{prefix}/{cas}.json

Kullanım:
  load_cached(cas)              → str (önbellekten oku)
  save_cached(cas, reg_no)      → None (diske yaz)
  fetch_reach_no_async(cas)     → str (statik DB → önbellek → canlı API)
  extract_reg_no(substance)     → str (ECHA API yanıtından çıkar)
"""
import json, os, re
import httpx

_BASE    = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'reach_cache')
_REG_PAT = re.compile(r'01-\d{10}-\d{2}-\d{4}')

# ── Disk I/O ──────────────────────────────────────────────────────────────────

def _path(cas: str) -> str:
    return os.path.join(_BASE, cas[:2], f'{cas}.json')


def load_cached(cas: str) -> str:
    """Disk önbelleğinden REACH kayıt numarasını oku; bulunamazsa '' döner."""
    try:
        with open(_path(cas.strip()), encoding='utf-8') as f:
            return json.load(f).get('reg_no', '')
    except Exception:
        return ''


def save_cached(cas: str, reg_no: str) -> None:
    """REACH kayıt numarasını disk önbelleğine yaz."""
    p = _path(cas.strip())
    os.makedirs(os.path.dirname(p), exist_ok=True)
    try:
        with open(p, 'w', encoding='utf-8') as f:
            json.dump({'cas': cas, 'reg_no': reg_no}, f)
    except Exception:
        pass


# ── ECHA API yanıtından REACH no çıkarımı ────────────────────────────────────

def extract_reg_no(substance: dict) -> str:
    """ECHA API substance dict'inden REACH kayıt numarasını çıkar.
    Birden fazla olası alan adı denenir; regex ile 01-XXXXXXXXXX-XX-XXXX aranır."""
    # Liste tipli alanlar (birden fazla kayıt olabilir)
    for field in ('registrationNumbers', 'registrationDossiers', 'registrations',
                  'regNos', 'dossierNumbers', 'reachRegNumbers'):
        val = substance.get(field)
        if not val:
            continue
        if isinstance(val, list) and val:
            first = val[0]
            if isinstance(first, str):
                m = _REG_PAT.search(first)
                if m:
                    return m.group()
            elif isinstance(first, dict):
                for k in ('number', 'registrationNumber', 'regNo', 'id',
                          'dossierNumber', 'dossier_number', 'value'):
                    v = str(first.get(k, ''))
                    m = _REG_PAT.search(v)
                    if m:
                        return m.group()
        elif isinstance(val, str):
            m = _REG_PAT.search(val)
            if m:
                return m.group()
    # String değerli tekil alanlar
    for field in ('registrationNumber', 'regNo', 'reach_no', 'reachNo',
                  'firstRegistrationNumber'):
        val = substance.get(field, '')
        if isinstance(val, str):
            m = _REG_PAT.search(val)
            if m:
                return m.group()
    return ''


# ── Canlı ECHA API çekimi ─────────────────────────────────────────────────────

async def fetch_reach_no_async(cas: str) -> str:
    """REACH kayıt numarasını şu sırayla arar:
      1. Statik reach_db (import ederek)
      2. Disk önbelleği (data/reach_cache/)
      3. ECHA substances API (canlı)
    Sonuç disk önbelleğine kaydedilir."""
    cas = cas.strip()
    if not cas:
        return ''

    # 1. Statik DB
    try:
        from app.services.reach_db import get_reg_no
        val = get_reg_no(cas)
        if val and val not in ('exempt', 'polymer'):
            return val
    except Exception:
        pass

    # 2. Disk önbelleği
    cached = load_cached(cas)
    if cached:
        return cached

    # 3. ECHA substances API
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                'https://api.echa.europa.eu/api/substances/search',
                params={'q': cas, 'number_type': 'cas'},
                timeout=10.0,
                headers={'Accept': 'application/json'},
            )
            if r.status_code != 200:
                print(f'[REACH API] {cas}: HTTP {r.status_code}')
                return ''
            raw = r.json()
            substances = raw if isinstance(raw, list) else raw.get('results', [])
            if not substances:
                print(f'[REACH API] {cas}: sonuç yok')
                return ''
            substance = substances[0]
            print(f'[REACH API] {cas} alan adları: {list(substance.keys())}')
            reg_no = extract_reg_no(substance)
            if reg_no:
                save_cached(cas, reg_no)
                print(f'[REACH API] {cas} → {reg_no} (önbelleğe alındı)')
            else:
                # İlk birkaç çağrıda yanıtı görmek için tam substance logla
                print(f'[REACH API] {cas}: kayıt no bulunamadı — yanıt: {substance}')
            return reg_no
    except Exception as e:
        print(f'[REACH API] {cas} hata: {e}')
    return ''
