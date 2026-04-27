"""
SVHC Kontrolü — REACH Madde 59(10) / KKDİK Ek-14
Madde ve karışım bileşenlerini ECHA SVHC Aday Listesi ile karşılaştırır.

KKDİK Zorunlulukları:
- SDS Bölüm 15.1: SVHC varlığı bildirilmeli
- Karışımda ≥ 0.1 % konsantrasyonda SVHC varsa alıcılara bildirme yükümlülüğü
"""
import json
import os
from functools import lru_cache

_DATA_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'svhc_candidate_list.json')

# Zorunluluk eşiği (KKDİK Madde 33 / REACH Art. 33)
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
        cas = (s.get('cas') or '').strip()
        if cas:
            by_cas[cas] = s

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
        name = comp.get('name', cas)
        conc = float(comp.get('concentration', comp.get('conc', 0)) or 0)

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


def svhc_section15_text(svhc_result: dict, lang: str = 'TR') -> list[str]:
    """
    Bölüm 15.1 için SVHC metin blokları üret.
    Döner: satır listesi (PDF ve frontend için).
    """
    lines = []
    above = svhc_result.get('above_threshold', [])

    if not above:
        if lang == 'TR':
            lines.append('SVHC (Çok Yüksek Endişe Veren Madde): Bu karışım ECHA SVHC Aday Listesi\'nde '
                         'yer alan madde içermemektedir (≥ %0,1 eşiği).')
        else:
            lines.append('SVHC (Substances of Very High Concern): This mixture does not contain substances '
                         'listed on the ECHA SVHC Candidate List at or above 0.1 %.')
        return lines

    if lang == 'TR':
        lines.append('⚠ SVHC (Çok Yüksek Endişe Veren Madde) — REACH Madde 33 / KKDİK Madde 35:')
        lines.append('Aşağıdaki SVHC aday listesi maddeleri ≥ %0,1 konsantrasyonda bulunmaktadır:')
    else:
        lines.append('⚠ SVHC (Substances of Very High Concern) — REACH Article 33 / KKDİK Article 35:')
        lines.append('The following SVHC candidate list substances are present at ≥ 0.1 %:')

    for s in above:
        conc_str = f"%{s['concentration']:.1f}" if s['concentration'] else '—'
        if lang == 'TR':
            lines.append(
                f"  • {s['name_tr'] or s['name_svhc']} (CAS {s['cas']}) — "
                f"{conc_str} — Endişe: {s['concern_tr']}"
            )
        else:
            lines.append(
                f"  • {s['name_svhc']} (CAS {s['cas']}) — "
                f"{conc_str} — Concern: {s['concern']}"
            )

    if lang == 'TR':
        lines.append(
            'REACH Madde 33 / KKDİK Madde 35 uyarınca alıcılara bildirim yükümlülüğü doğmaktadır.'
        )
    else:
        lines.append(
            'Notification obligations apply to recipients under REACH Article 33 / KKDİK Article 35.'
        )

    return lines
