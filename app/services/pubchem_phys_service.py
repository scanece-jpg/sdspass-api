"""
PubChem Fiziksel Özellik Servisi
=================================
CAS numarasına göre PubChem'den fiziksel özellik verisi çeker.
Sonuçlar data/phys_cache/ altında önbelleğe alınır.

Döndürülen alanlar (SI/standart birimlerde):
  density        : g/cm³ (20°C)
  boiling_point  : °C
  flash_point    : °C  (None → yanmaz)
  vapor_pressure : hPa (20°C)
  viscosity      : mm²/s — cSt @ 40°C (nadiren PubChem'de bulunur)
  solubility     : mg/L  (None → metin açıklama döner)
  solubility_text: str
  mw             : g/mol (molekül ağırlığı)
  lel            : %v/v  (alt patlama sınırı)
  uel            : %v/v  (üst patlama sınırı)
"""

import re, json, asyncio
from datetime import datetime, timezone
from pathlib import Path

import httpx

_BASE = Path(__file__).parent.parent.parent / 'data' / 'phys_cache'
_BASE.mkdir(exist_ok=True, parents=True)

_PUBCHEM = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
_PUGVIEW = "https://pubchem.ncbi.nlm.nih.gov/rest/pug_view"

# ── Cache TTL (gün) ───────────────────────────────────────────────────────────
# Güvenlik sınıflandırmasını doğrudan etkileyen kritik alanlar daha sık yenilenir.
_TTL_CRITICAL = 90    # gün — flash_point, boiling_point, lel, uel
_TTL_STANDARD = 365   # gün — mw, density, vapor_pressure, solubility
_CRITICAL_FIELDS = frozenset({'flash_point', 'boiling_point', 'lel', 'uel'})
# Önbellekte saklanır ama dışarıya dönmez (iç meta veriler)
_CACHE_META_KEYS = frozenset({'_cached_at', '_classification_h22x'})


def _h22x_category(flash_point, boiling_point=None) -> str | None:
    """
    Flash point + boiling point → CLP H22x kategorisi.
    Değer değişirse önbellekten uyarı tetiklemek için kullanılır.
    """
    if flash_point is None:
        return None
    try:
        fp = float(flash_point)
        bp = float(boiling_point) if boiling_point is not None else None
    except (TypeError, ValueError):
        return None
    if fp < 23:
        return 'H224' if (bp is not None and bp <= 35) else 'H225'
    if fp <= 60:
        return 'H226'
    return None

# ── Yardımcı: Metin içinden ilk sayıyı çek ───────────────────────────────────
_NUM_RE = re.compile(r'[-+]?\d[\d,]*\.?\d*')

def _num(s: str) -> float | None:
    s = s.replace(',', '')
    m = _NUM_RE.search(s)
    return float(m.group()) if m else None


def _to_celsius(val: float, text: str) -> float:
    """°F → °C dönüşümü (metin '°F' içeriyorsa)."""
    if '°f' in text.lower() or ' f' in text.lower():
        return round((val - 32) * 5 / 9, 1)
    return round(val, 1)


def _to_hpa(val: float, text: str) -> float:
    """Farklı basınç birimlerini hPa'ya çevir."""
    tl = text.lower()
    if 'mmhg' in tl or 'mm hg' in tl:
        return round(val * 1.33322, 3)
    if 'torr' in tl:
        return round(val * 1.33322, 3)
    if 'atm' in tl:
        return round(val * 1013.25, 2)
    if 'kpa' in tl:
        return round(val * 10, 3)
    if re.search(r'\bpa\b', tl) and 'kpa' not in tl and 'hpa' not in tl:
        return round(val / 100, 4)
    # mbar veya hPa — olduğu gibi
    return round(val, 3)


def _to_mg_l(val: float, text: str) -> float | None:
    """Çözünürlük birimini mg/L'ye çevir."""
    tl = text.lower()
    if 'g/l' in tl and 'mg' not in tl:
        return round(val * 1000, 1)
    if 'g/ml' in tl or 'g/cm' in tl:
        return round(val * 1e6, 1)
    if '%' in tl:
        # % ağırlık → yaklaşık mg/L (yoğunluk ~1 g/mL varsayımı)
        return round(val * 10000, 1)
    return round(val, 2)  # mg/L olarak varsay


# ── PUG View bölüm ağacında başlık ara ───────────────────────────────────────
def _find_section(sections, heading: str):
    """Özyinelemeli bölüm arama."""
    for s in sections:
        if s.get('TOCHeading', '').lower() == heading.lower():
            yield s
        for sub in _find_section(s.get('Section', []), heading):
            yield sub


def _first_string(section) -> str | None:
    """Bölümdeki ilk metin değerini döndür."""
    for info in section.get('Information', []):
        val = info.get('Value', {})
        for swm in val.get('StringWithMarkup', []):
            s = swm.get('String', '').strip()
            if s:
                return s
        nums = val.get('Number', [])
        if nums:
            unit = val.get('Unit', '')
            return f"{nums[0]} {unit}".strip()
    return None


# ── Ana çekme fonksiyonu ──────────────────────────────────────────────────────
# ── İnorganik/iyonik maddeler — BP verileri PubChem'den güvenilmez ─────────────
# Bu maddeler için boiling_point PubChem çıktısından çıkarılır.
# (PubChem zaman zaman çözelti/ayrışma sıcaklığını BP olarak listeler)
_INORGANIC_NO_BP = {
    '1310-73-2',  # NaOH
    '1310-58-3',  # KOH
    '7681-52-9',  # NaOCl
    '7722-84-1',  # H₂O₂
    '7664-93-9',  # H₂SO₄
    '7664-38-2',  # H₃PO₄
    '7697-37-2',  # HNO₃
    '7647-01-0',  # HCl
    '497-19-8',   # Na₂CO₃
    '10043-52-4', # CaCl₂
    '7647-14-5',  # NaCl
    '1336-21-6',  # NH₃ çözeltisi
    '1305-62-0',  # Ca(OH)₂
    '1305-78-8',  # CaO
    '1313-59-3',  # Na₂O
    '7779-90-0',  # Zn₃(PO₄)₂
}


async def fetch_phys(cas: str) -> dict:
    """
    CAS numarası için fiziksel özellikleri döndür.
    Önce önbellekten bakar; bulamazsa PubChem'den çeker ve önbelleğe alır.
    """
    safe_name = cas.replace('/', '_').replace('\\', '_')
    cache_file = _BASE / f"{safe_name}.json"

    _prev_cached: dict = {}   # önceki önbellek verisi (kategori karşılaştırması için)
    _ttl_expired = False

    if cache_file.exists():
        try:
            _prev_cached = json.loads(cache_file.read_text(encoding='utf-8'))
            _cached_at_str = _prev_cached.get('_cached_at')
            if _cached_at_str:
                age_days = (datetime.now(timezone.utc)
                            - datetime.fromisoformat(_cached_at_str)).days
                has_critical = any(f in _prev_cached for f in _CRITICAL_FIELDS)
                ttl = _TTL_CRITICAL if has_critical else _TTL_STANDARD
                if age_days < ttl:
                    # TTL geçerli → meta anahtarları çıkar ve döndür
                    return {k: v for k, v in _prev_cached.items()
                            if k not in _CACHE_META_KEYS}
                else:
                    _ttl_expired = True   # TTL doldu → PubChem'den yenile
            else:
                # Eski format — _cached_at yok → dokunma, yeni sorguları bekle
                return {k: v for k, v in _prev_cached.items()
                        if k not in _CACHE_META_KEYS}
        except Exception:
            pass

    props = {}

    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            # 1. CAS → CID
            r = await client.get(f"{_PUBCHEM}/compound/name/{cas}/cids/JSON")
            if r.status_code != 200:
                return {}
            cids = r.json().get('IdentifierList', {}).get('CID', [])
            if not cids:
                return {}
            cid = cids[0]

            # 2. Molekül ağırlığı (hızlı, güvenilir)
            r2 = await client.get(
                f"{_PUBCHEM}/compound/cid/{cid}/property/MolecularWeight/JSON"
            )
            if r2.status_code == 200:
                pd = r2.json().get('PropertyTable', {}).get('Properties', [])
                if pd:
                    mw = pd[0].get('MolecularWeight')
                    if mw:
                        props['mw'] = float(mw)

            # 3. Deneysel fiziksel özellikler (PUG View)
            r3 = await client.get(
                f"{_PUGVIEW}/data/compound/{cid}/JSON/",
                params={"heading": "Experimental Properties"}
            )
            if r3.status_code != 200:
                # Daha geniş bir sorgu dene
                r3 = await client.get(
                    f"{_PUGVIEW}/data/compound/{cid}/JSON/",
                    params={"heading": "Physical and Chemical Properties"}
                )

            if r3.status_code == 200:
                sections = r3.json().get('Record', {}).get('Section', [])

                # Kaynama Noktası — inorganik/iyonik maddeler için atla
                if cas.strip() not in _INORGANIC_NO_BP:
                    for sec in _find_section(sections, 'Boiling Point'):
                        s = _first_string(sec)
                        if s:
                            v = _num(s)
                            if v is not None:
                                props['boiling_point'] = _to_celsius(v, s)
                        break

                # Parlama Noktası
                for sec in _find_section(sections, 'Flash Point'):
                    s = _first_string(sec)
                    if s:
                        sl = s.lower()
                        if 'non-flam' in sl or 'not flam' in sl or 'none' in sl:
                            props['flash_point'] = None
                        else:
                            v = _num(s)
                            if v is not None:
                                props['flash_point'] = _to_celsius(v, s)
                    break

                # Yoğunluk
                for sec in _find_section(sections, 'Density'):
                    s = _first_string(sec)
                    if s:
                        v = _num(s)
                        if v is not None and 0.3 < v < 6.0:
                            props['density'] = round(v, 4)
                    break

                # Buhar Basıncı
                for sec in _find_section(sections, 'Vapor Pressure'):
                    s = _first_string(sec)
                    if s:
                        v = _num(s)
                        if v is not None and v >= 0:
                            props['vapor_pressure'] = _to_hpa(v, s)
                    break

                # Çözünürlük
                for sec in _find_section(sections, 'Solubility'):
                    s = _first_string(sec)
                    if s:
                        props['solubility_text'] = s[:150]
                        sl = s.lower()
                        if any(w in sl for w in ('miscible', 'soluble in all', 'completely')):
                            # Tam karışır — SOL_DB güncellemesi ve çapraz kontrol için 1e6 kullan.
                            # physical_engine sol_val >= 900000 kontrolüyle bunu "Karışır" olarak
                            # gösterir; PDF'de "~1.000.000 mg/L" yerine "Karışır" çıkar.
                            # NOT: None kullanılırsa dosya sonundaki çapraz kontrol TypeError verir.
                            props['solubility']      = 1e6
                            props['solubility_text'] = 'Karışır'
                        elif 'insoluble' in sl or 'immiscible' in sl:
                            props['solubility'] = 0.1
                        else:
                            v = _num(s)
                            if v is not None and v >= 0:
                                props['solubility'] = _to_mg_l(v, s)
                    break

                # Alt/Üst Patlama Sınırı
                for sec in _find_section(sections, 'Lower Explosive Limit'):
                    s = _first_string(sec)
                    if s:
                        v = _num(s)
                        if v is not None:
                            props['lel'] = round(v, 2)
                    break
                for sec in _find_section(sections, 'Upper Explosive Limit'):
                    s = _first_string(sec)
                    if s:
                        v = _num(s)
                        if v is not None:
                            props['uel'] = round(v, 2)
                    break

    except Exception as e:
        print(f"[PubChemPhys] CAS {cas} hatası: {e}")
        return {}

    # ── Son işlem: Çözünürlük × Yoğunluk çapraz kontrolü ────────────────────────
    # Fiziksel kural: max çözünürlük (mg/L) = yoğunluk (g/mL) × 1.000.000
    # Yani 1 litre %100 saf madde = yoğunluk × 1L = yoğunluk_mg_L
    # Bu sınırı aşan çözünürlük birim hatasından kaynaklanıyordur (g/mL → mg/L karışıklığı).
    if 'solubility' in props and 'density' in props:
        density_mg_l = props['density'] * 1e6   # g/mL → mg/L
        sol_val      = props['solubility']
        MISCIBLE_PLACEHOLDER = 1e6              # "miscible" için atanan sabit değer
        if sol_val != MISCIBLE_PLACEHOLDER and sol_val > density_mg_l:
            original_sol = sol_val
            # Gerçekçi düzeltme: yoğunluk değerine kırp + metin uyarısı ekle
            props['solubility'] = round(density_mg_l, 1)
            existing_text = props.get('solubility_text', '')
            props['solubility_text'] = (
                f"{existing_text} "
                f"[Ham değer {original_sol:,.0f} mg/L → yoğunluktan "
                f"({density_mg_l:,.0f} mg/L) büyük, birim hatası olası; "
                f"yoğunluk üst sınırına göre düzeltildi]"
            ).strip()

    # ── Kategorisel değişiklik tespiti ───────────────────────────────────────────
    # TTL dolup yenilenen veride H22x kategorisi değişmişse kullanıcı uyarılır.
    if _ttl_expired and _prev_cached:
        _old_h22x = _prev_cached.get('_classification_h22x')
        _new_h22x = _h22x_category(
            props.get('flash_point'), props.get('boiling_point')
        )
        if _old_h22x is not None and _new_h22x != _old_h22x:
            props['_category_changed'] = True
            props['_category_change_detail'] = (
                f"Parlama noktası kategorisi değişti: "
                f"{_old_h22x} → {_new_h22x or 'sınıfsız'}. "
                f"Sınıflandırmayı ve etiket bilgilerini gözden geçirin."
            )

    # ── Önbelleğe kaydet (boş sonuç kaydedilmez) ─────────────────────────────────
    if props:
        try:
            _to_cache = {k: v for k, v in props.items()
                         if not k.startswith('_')}   # uyarı meta'larını kaydetme
            _to_cache['_cached_at'] = datetime.now(timezone.utc).isoformat()
            _to_cache['_classification_h22x'] = _h22x_category(
                props.get('flash_point'), props.get('boiling_point')
            )
            cache_file.write_text(
                json.dumps(_to_cache, ensure_ascii=False), encoding='utf-8'
            )
        except Exception:
            pass

    return props
