"""
SVHC Kontrolü — KKDİK Md.49(1) aday listesi (Ek-14'e alınmaya aday maddeler)
Madde ve karışım bileşenlerini Aday Liste ile karşılaştırır. Türkiye listesi Bakanlıkça
yayımlanana kadar AB (ECHA) Aday Listesi dikkate alınır (ÇŞİDB Çevre Etiketi kılavuzları).

KKDİK Zorunlulukları:
- Ek-2 3.2.1(c) / 3.2.2(b): ≥ %0,1 Aday Liste maddesi Bölüm 3'te listelenir; madde
  sınıflandırılmamışsa listelenme nedeni yazılır (Ek-2 3.2.3)
- Ek-2 15.1: ürünün tabi olduğu mevzuat — Aday Liste maddesi varlığı belirtilir
- Md.27: sınıflandırılmamış karışımda ≥ %0,1 Aday Liste maddesi → talep halinde GBF
"""
import json
import os
from functools import lru_cache

_DATA_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'svhc_candidate_list.json')

# Zorunluluk eşiği (KKDİK Ek-2 3.2.1(c) / 3.2.2(b), Md.27)
SVHC_THRESHOLD_PCT = 0.1


@lru_cache(maxsize=1)
def _load_svhc_list() -> dict:
    """SVHC verisi dosyasını bir kez yükle ve CAS'a göre indeksle."""
    try:
        with open(_DATA_PATH, encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        return {"meta": {}, "by_cas": {}}

    by_cas = {}
    for s in data.get('substances', []):
        # Bazı girişlerde birden çok CAS virgülle yazılı (örn. hidrazin, boraks) — her biri ayrı indekslenir
        for cas in (s.get('cas') or '').split(','):
            cas = cas.strip()
            if cas:
                by_cas.setdefault(cas, s)

    return {
        "meta": {
            "version": data.get('version', ''),
            "date": data.get('date', ''),
            "source": data.get('source', ''),
            "count": len(by_cas),
        },
        "by_cas": by_cas,
    }


def check_svhc_single(cas: str) -> dict | None:
    """
    Tek bir CAS numarasını SVHC listesi ile karşılaştır.
    Döner: SVHC bilgisi dict veya None (listede değil).
    """
    db = _load_svhc_list()
    entry = db['by_cas'].get((cas or '').strip())
    if not entry:
        return None
    return {
        'cas': entry.get('cas', cas),
        'name': entry.get('name', ''),
        'name_tr': entry.get('name_tr', ''),
        'ec_no': entry.get('ec', ''),
        'concern': entry.get('concern', ''),
        'concern_tr': entry.get('concern_tr', ''),
    }


def check_svhc_mixture(components: list) -> dict:
    """
    Karışım bileşenlerini SVHC listesi ile karşılaştır.

    components: [{'cas': str, 'name': str, 'concentration': float, ...}]

    Döner: {
        'found': [...],      # SVHC olan bileşenler (tüm konsantrasyonlar)
        'above_threshold': [...],  # ≥ 0.1% olanlar — bildirim zorunlu
        'meta': {...}
    }
    """
    db = _load_svhc_list()
    found = []
    above_threshold = []

    for comp in components:
        cas  = (comp.get('cas_no') or comp.get('cas') or '').strip()
        name = comp.get('name_tr') or comp.get('name') or cas
        # Aralık girildiyse üst değer (en kötü durum) eşikle karşılaştırılır
        conc = float(comp.get('concMax') or comp.get('conc_max') or comp.get('concentration')
                     or comp.get('conc', 0) or 0)

        entry = db['by_cas'].get(cas)
        if not entry:
            continue

        hit = {
            'cas': cas,
            'name': name,
            'name_svhc': entry.get('name', ''),
            'name_tr': entry.get('name_tr', ''),
            'ec_no': entry.get('ec', ''),
            'concern': entry.get('concern', ''),
            'concern_tr': entry.get('concern_tr', ''),
            'concentration': conc,
            'above_threshold': conc >= SVHC_THRESHOLD_PCT,
        }
        found.append(hit)
        if conc >= SVHC_THRESHOLD_PCT:
            above_threshold.append(hit)

    return {
        'found': found,
        'above_threshold': above_threshold,
        'threshold_pct': SVHC_THRESHOLD_PCT,
        'meta': db['meta'],
    }


def _list_date(meta: dict) -> str:
    """'2026-08-24' → '24.08.2026' (liste sürümü 15.1'de belirtilir)."""
    d = (meta or {}).get('date', '')
    parts = d.split('-')
    return '.'.join(reversed(parts)) if len(parts) == 3 else d


def svhc_section3_reason(cas: str, conc, lang: str = 'TR') -> str:
    """Ek-2 3.2.3: sınıflandırılmamış madde 3.2'de Aday Liste nedeniyle yer alıyorsa nedeni.
    Madde listede değilse veya ≥ %0,1 değilse boş döner."""
    try:
        c = float(conc or 0)
    except (TypeError, ValueError):
        c = 0.0
    if c < SVHC_THRESHOLD_PCT or not check_svhc_single(cas):
        return ''
    return ('Aday Listede yer alan madde (KKDİK Md.49)' if lang == 'TR'
            else 'Substance on the Candidate List (SVHC)')


def svhc_section15_text(svhc_result: dict, lang: str = 'TR') -> list[str]:
    """
    Bölüm 15.1 için Aday Liste (SVHC) metin blokları üret.
    Konsantrasyon yazılmaz — Bölüm 3'teki gizlilik (aralık) tercihini açığa çıkarmamak için.
    Döner: satır listesi (PDF ve frontend için).
    """
    lines = []
    above = svhc_result.get('above_threshold', [])
    dt = _list_date(svhc_result.get('meta', {}))
    if lang == 'TR':
        basis = ('Türkiye aday listesi Bakanlıkça yayımlanana kadar AB (ECHA) Aday Listesi esas alınmıştır'
                 + (f' ({dt} tarihli liste).' if dt else '.'))
    else:
        basis = ('The EU (ECHA) Candidate List has been used until the Turkish candidate list is published'
                 + (f' (list dated {dt}).' if dt else '.'))

    if not above:
        if lang == 'TR':
            lines.append('Aday Liste (SVHC — KKDİK Md.49): Bu karışım, Ek-14\'e alınmaya aday madde listesinde '
                         'yer alan maddeleri ağırlıkça %0,1 veya üzerinde içermemektedir.')
        else:
            lines.append('Candidate List (SVHC): This mixture does not contain substances on the Candidate List '
                         'at or above 0.1 % by weight.')
        lines.append(basis)
        return lines

    if lang == 'TR':
        lines.append('⚠ Aday Liste (SVHC — KKDİK Md.49):')
        lines.append('Aşağıdaki maddeler Ek-14\'e alınmaya aday madde listesinde yer almakta ve karışımda '
                     'ağırlıkça %0,1 veya üzerinde bulunmaktadır:')
    else:
        lines.append('⚠ Candidate List (SVHC):')
        lines.append('The following substances are on the Candidate List and present at or above 0.1 % by weight:')

    for s in above:
        if lang == 'TR':
            lines.append(
                f"  • {s['name_tr'] or s['name'] or s['name_svhc']} (CAS {s['cas']}) — "
                f"Neden: {s['concern_tr'] or s['concern']}"
            )
        else:
            lines.append(
                f"  • {s['name_svhc'] or s['name']} (CAS {s['cas']}) — "
                f"Reason: {s['concern']}"
            )
    lines.append(basis)
    return lines
