"""
REACH Kayıt Numarası Önbelleği
Kayıt numarasını şu sırayla arar: statik DB → disk önbelleği → Claude AI + web arama.
Bulunan numara disk önbelleğine ve reach_db.py'e kalıcı olarak kaydedilir.

Kullanım:
  load_cached(cas)              → str (disk önbelleğinden oku)
  save_cached(cas, reg_no)      → None (disk önbelleğine yaz)
  fetch_reach_no_async(cas)     → str (tam arama zinciri)
  extract_reg_no(substance)     → str (eski ECHA API yanıtı için — geriye dönük uyum)
"""
import json, os, re

_BASE    = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'reach_cache')
_DB_PATH = os.path.join(os.path.dirname(__file__), 'reach_db.py')
_REG_PAT = re.compile(r'01-\d{10}-\d{2}-\d{4}')
_EC_PAT  = re.compile(r'\b\d{3}-\d{3}-\d\b')


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
    try:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, 'w', encoding='utf-8') as f:
            json.dump({'cas': cas, 'reg_no': reg_no}, f)
    except Exception as e:
        print(f'[REACH CACHE] {cas} kayıt hatası ({p}): {e}')


# ── reach_db.py'e kalıcı kayıt ───────────────────────────────────────────────

def _append_to_reach_db(cas: str, reg_no: str, ec: str = '', name: str = '') -> bool:
    """Bulunan REACH numarasını reach_db.py'deki REACH_DB sözlüğüne ekler.
    Sunucu yeniden başlatıldığında statik DB'den okunur."""
    try:
        with open(_DB_PATH, 'r', encoding='utf-8') as f:
            content = f.read()

        # Zaten mevcutsa atla
        if f"'{cas}'" in content or f'"{cas}"' in content:
            return False

        ec_s   = (ec   or '').replace("'", '')
        name_s = (name or cas).replace("'", '').replace('"', '')
        new_line = (
            f"    '{cas}':  {{'reg':['{reg_no}'],'ec':'{ec_s}',"
            f"'name':'{name_s}'}},  # AI\n"
        )

        # REACH_DB'yi kapatan ilk tek-'}' satırını bul ve önüne ekle
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if line.strip() == '}':
                lines.insert(i, new_line.rstrip('\n'))
                break
        else:
            return False

        with open(_DB_PATH, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

        print(f'[REACH DB] {cas} → reach_db.py\'e eklendi: {reg_no}')
        return True
    except Exception as e:
        print(f'[REACH DB] reach_db.py güncelleme hatası: {e}')
        return False


# ── ECHA API yanıtından REACH no çıkarımı (geriye dönük uyum) ────────────────

def extract_reg_no(substance: dict) -> str:
    """Eski ECHA API JSON yanıtından REACH kayıt numarası çıkarır."""
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
    for field in ('registrationNumber', 'regNo', 'reach_no', 'reachNo',
                  'firstRegistrationNumber'):
        val = substance.get(field, '')
        if isinstance(val, str):
            m = _REG_PAT.search(val)
            if m:
                return m.group()
    return ''


# ── Claude AI + web arama ─────────────────────────────────────────────────────

async def _fetch_via_ai(cas: str) -> tuple[str, str, str]:
    """Claude AI ve web aramasıyla REACH numarasını resmi kaynaklardan bulur.
    Returns: (reg_no, ec, name) — bulunamazsa ('', '', '')"""
    api_key = os.environ.get('ANTHROPIC_API_KEY', '')
    if not api_key:
        return '', '', ''

    try:
        import anthropic
    except ImportError:
        print('[REACH AI] anthropic paketi kurulu değil — pip install anthropic')
        return '', '', ''

    try:
        client = anthropic.AsyncAnthropic(api_key=api_key)
        prompt = (
            f"CAS numarası {cas} olan kimyasalın REACH kayıt numarasını resmi "
            f"kaynaklardan bul. ECHA web sitesi (echa.europa.eu), üretici GBF/SDS "
            f"belgeleri veya kimyasal veritabanlarında ara. "
            f"Yalnızca 01-XXXXXXXXXX-XX-XXXX formatındaki gerçek kayıt numarasını, "
            f"EC numarasını (XXX-XXX-X) ve kimyasalın İngilizce adını yaz. "
            f"Kaynak URL'sini de belirt. Uydurma."
        )
        response = await client.messages.create(
            model='claude-haiku-4-5-20251001',
            max_tokens=512,
            tools=[{'type': 'web_search_20250305', 'name': 'web_search', 'max_uses': 3}],
            messages=[{'role': 'user', 'content': prompt}],
        )

        # Tüm metin bloklarından bilgileri çıkar
        full_text = ' '.join(
            block.text for block in response.content if hasattr(block, 'text')
        )

        reg_m = _REG_PAT.search(full_text)
        if not reg_m:
            print(f'[REACH AI] {cas}: kayıt no bulunamadı')
            return '', '', ''

        reg_no = reg_m.group()
        ec_m   = _EC_PAT.search(full_text)
        ec     = ec_m.group() if ec_m else ''
        print(f'[REACH AI] {cas} → {reg_no}  EC={ec}')
        return reg_no, ec, ''

    except Exception as e:
        print(f'[REACH AI] {cas} hata: {e}')
        return '', '', ''


# ── Ana arama zinciri ─────────────────────────────────────────────────────────

async def fetch_reach_no_async(cas: str) -> str:
    """REACH kayıt numarasını şu sırayla arar:
      1. Statik reach_db (sunucu başlangıcında yüklenir)
      2. Disk önbelleği (data/reach_cache/{prefix}/{cas}.json)
      3. Claude AI + web arama (ANTHROPIC_API_KEY gerekli)
    Adım 3'te bulunan numara hem disk önbelleğine hem reach_db.py'e yazılır."""
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

    # 3. Claude AI + web arama
    reg_no, ec, name = await _fetch_via_ai(cas)
    if reg_no:
        save_cached(cas, reg_no)
        _append_to_reach_db(cas, reg_no, ec, name)

    return reg_no
