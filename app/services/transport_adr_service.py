"""
ADR Taşımacılık Servisi
=======================
UN numarasından ADR detaylarını döndürür:
  - Kemler kodu (tehlike tanımlama numarası)
  - Tünel kısıtlama kodu
  - Sınıflandırma kodu
  - Etiket
  - Sınırlı miktar

Kaynak: ADR 2025 Tablo A
CAS→UN eşleşmesi bellekte tutulur (dosya yok):
  substance_db.json isimleri × adr_data.json isimleri → normalize eşleştirme
  Konsantrasyona göre farklı UN gereken maddeler _SEED_ENTRIES'de liste olarak tanımlı.
"""

import json
import re
import logging
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

_ADR_DATA = None
_CAS_TO_UN = None  # {CAS: {'un':..,'pg':..} veya [{'min_conc':..,'max_conc':..,'un':..,'pg':..}]}

_DATA_DIR = Path(__file__).parent.parent.parent / 'data'


def _load():
    global _ADR_DATA
    if _ADR_DATA is None:
        p = _DATA_DIR / 'adr_data.json'
        if p.exists():
            with open(p, encoding='utf-8') as f:
                _ADR_DATA = json.load(f)
        else:
            _ADR_DATA = {}
    return _ADR_DATA


def _normalize(name: str) -> str:
    """İsim eşleştirme için normalize et."""
    name = name.lower()
    name = re.sub(r'[,\.\-\(\)/]', ' ', name)
    name = re.sub(r'\b(n\.?o\.?s\.?|b\.?n\.?o\.?|nos|bno)\b', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name


# Konsantrasyona göre UN değişen maddeler liste olarak tanımlı.
# min_conc/max_conc: % ağırlık (dahil alt sınır, hariç üst sınır).
# Konsantrasyon bilinmiyorsa ilk giriş (en yüksek tehlike) kullanılır.
# Tek UN'lu maddeler dict olarak tanımlı.
_SEED_ENTRIES: dict = {
    # ── Asitler ───────────────────────────────────────────────────────────────
    '7664-93-9': [  # Sülfürik asit — ADR Tablo A
        {'min_conc': 51,  'max_conc': 100, 'un': 'UN1830', 'pg': 'II'},
        {'min_conc': 0,   'max_conc': 51,  'un': 'UN2796', 'pg': 'III'},
    ],
    '7697-37-2': [  # Nitrik asit — ADR Tablo A
        {'min_conc': 65,  'max_conc': 100, 'un': 'UN2031', 'pg': 'I'},
        {'min_conc': 0,   'max_conc': 65,  'un': 'UN2031', 'pg': 'II'},
    ],
    '7647-01-0': [  # Hidroklorik asit — ADR Tablo A
        {'min_conc': 25,  'max_conc': 100, 'un': 'UN1789', 'pg': 'II'},
        {'min_conc': 0,   'max_conc': 25,  'un': 'UN1789', 'pg': 'III'},
    ],
    '7664-38-2': {'un': 'UN1805', 'pg': 'III'},  # Fosforik asit
    '10035-10-6':{'un': 'UN1788', 'pg': 'II'},   # Hidrobromik asit
    '7789-21-1': {'un': 'UN1777', 'pg': 'II'},   # Florosülfürik asit

    # ── Bazlar ────────────────────────────────────────────────────────────────
    '1310-73-2': [  # Sodyum hidroksit çözelti — ADR Tablo A
        {'min_conc': 0,   'max_conc': 100, 'un': 'UN1824', 'pg': 'II'},
    ],
    '1310-58-3': {'un': 'UN1814', 'pg': 'II'},   # Potasyum hidroksit çözelti
    '1305-78-8': {'un': 'UN1910', 'pg': 'III'},  # Kalsiyum oksit
    '7664-41-7': [  # Amonyak — gaz veya çözelti
        {'min_conc': 50,  'max_conc': 100, 'un': 'UN1005', 'pg': 'I'},   # Anhidröz gaz
        {'min_conc': 35,  'max_conc': 50,  'un': 'UN2073', 'pg': 'II'},  # Çözelti >35%
        {'min_conc': 0,   'max_conc': 35,  'un': 'UN2672', 'pg': 'III'}, # Çözelti ≤35%
    ],

    # ── Oksitleyiciler ────────────────────────────────────────────────────────
    '7722-84-1': [  # Hidrojen peroksit — ADR Tablo A
        {'min_conc': 60,  'max_conc': 100, 'un': 'UN2015', 'pg': 'I'},
        {'min_conc': 8,   'max_conc': 60,  'un': 'UN2014', 'pg': 'II'},
        # <8% taşıma yönetmeliği kapsamı dışı
    ],
    '7681-52-9': {'un': 'UN1791', 'pg': 'II', 'physical_state': 'liquid'},  # Sodyum hipoklorit çözelti
    '7778-54-3': {'un': 'UN2208', 'pg': 'II', 'physical_state': 'solid'},  # Kalsiyum hipoklorit karışım
    '87-90-1':   {'un': 'UN2468', 'pg': 'II', 'physical_state': 'solid'},  # TCCA (ADR: "TRİKLOROİZOSİYANÜRİK ASİT, KURU")
    '2893-78-9': {'un': 'UN2468', 'pg': 'II', 'physical_state': 'solid'},  # Sodyum dikloroizosiyanurik asit, kuru
    '10049-04-4':{'un': 'UN2548', 'pg': 'I',  'physical_state': 'gas'},    # Klor dioksit

    # ── Halojenler / Gazlar ───────────────────────────────────────────────────
    '7726-95-6': {'un': 'UN1744', 'pg': 'I'},    # Brom
    '7782-50-5': {'un': 'UN1017', 'pg': None},   # Klor gazı
    '7803-51-2': {'un': 'UN2199', 'pg': 'I'},    # Fosfin
    '74-90-8':   {'un': 'UN1051', 'pg': 'I'},    # Hidrojen siyanür
    '7783-06-4': {'un': 'UN1053', 'pg': 'I'},    # Hidrojen sülfür
    '75-44-5':   {'un': 'UN1076', 'pg': 'I'},    # Fosgen
    '7782-79-8': {'un': 'UN3123', 'pg': 'I'},    # Hidrazoik asit
    '7647-19-0': {'un': 'UN1826', 'pg': 'I'},    # Fosfor pentaflorür
    '10025-87-3':{'un': 'UN1810', 'pg': 'I'},    # Fosfor oksikorür

    # ── Ağır metaller / Toksikler ─────────────────────────────────────────────
    '7784-34-1': {'un': 'UN1556', 'pg': 'I'},    # Arsenik triklorür
    '26628-22-8':{'un': 'UN1687', 'pg': 'II'},   # Sodyum azit

    # ── Yanıcı organikler ─────────────────────────────────────────────────────
    '67-56-1':   {'un': 'UN1230', 'pg': 'II'},   # Metanol
    '64-17-5':   {'un': 'UN1170', 'pg': 'II'},   # Etanol
    '67-63-0':   {'un': 'UN1219', 'pg': 'II'},   # İzopropanol
    '67-64-1':   {'un': 'UN1090', 'pg': 'II'},   # Aseton
    '78-93-3':   {'un': 'UN1193', 'pg': 'II'},   # Metil etil keton
    '108-88-3':  {'un': 'UN1294', 'pg': 'II'},   # Toluen
    '71-43-2':   {'un': 'UN1114', 'pg': 'II'},   # Benzen
    '110-54-3':  {'un': 'UN1208', 'pg': 'II'},   # n-Hekzan
    '142-82-5':  {'un': 'UN1278', 'pg': 'II'},   # n-Heptan
    '108-05-4':  {'un': 'UN1301', 'pg': 'II'},   # Vinil asetat
    '75-05-8':   {'un': 'UN1648', 'pg': 'II'},   # Asetonitril
    '79-01-6':   {'un': 'UN1710', 'pg': 'III'},  # Trikloretilen
    '127-19-5':  {'un': 'UN2810', 'pg': 'III'},  # DMAc
    '50-00-0': [  # Formaldehit çözelti
        {'min_conc': 25,  'max_conc': 100, 'un': 'UN1198', 'pg': 'III'},
        {'min_conc': 0,   'max_conc': 25,  'un': 'UN2209', 'pg': 'III'},
    ],
}


def _build_cas_map() -> dict:
    """
    substance_db.json × adr_data.json isim eşleşmesi → bellek-içi CAS→UN haritası.
    Seed girişleri her zaman dahil, isim eşleşmesi üstüne eklenir.
    Dosyaya yazılmaz.
    """
    mapping: dict = dict(_SEED_ENTRIES)

    sub_path = _DATA_DIR / 'substance_db.json'
    if not sub_path.exists():
        return mapping

    with open(sub_path, encoding='utf-8') as f:
        substances = json.load(f)
    adr_db = _load()

    # ADR isimlerini normalize et → {norm_isim: (UN, PG)}
    adr_index: dict[str, tuple] = {}
    for un_key, entry in adr_db.items():
        raw = entry.get('name', '')
        if not raw:
            continue
        norm = _normalize(raw)
        if not norm:
            continue
        pgs = entry.get('packing_groups', {})
        pg = list(pgs.keys())[0] if pgs else (entry.get('packing_group') or 'II')
        adr_index[norm] = (un_key, pg)

    matched = 0
    for sub in (substances if isinstance(substances, list) else substances.values()):
        cas = str(sub.get('cas') or '').strip()
        if not cas or cas in mapping:
            continue
        names = []
        raw_names = sub.get('names', [])
        if isinstance(raw_names, list):
            names.extend(raw_names)
        elif isinstance(raw_names, str):
            names.append(raw_names)
        syns = sub.get('synonyms', [])
        if isinstance(syns, list):
            names.extend(syns)
        elif isinstance(syns, str):
            names.append(syns)

        for name in names:
            norm = _normalize(str(name))
            if norm and norm in adr_index:
                un_key, pg = adr_index[norm]
                mapping[cas] = {'un': un_key, 'pg': pg}
                matched += 1
                break

    log.info('CAS→UN haritası hazır: %d seed + %d isim eşleşmesi = %d toplam',
             len(_SEED_ENTRIES), matched, len(mapping))
    return mapping


def init_cas_map():
    """Sunucu başlangıcında çağrılır — bellek-içi haritayı oluşturur."""
    global _CAS_TO_UN
    _CAS_TO_UN = _build_cas_map()


def _get_cas_map() -> dict:
    global _CAS_TO_UN
    if _CAS_TO_UN is None:
        _CAS_TO_UN = _build_cas_map()
    return _CAS_TO_UN


def lookup_by_cas(cas: str, concentration: Optional[float] = None) -> 'dict | None':
    """
    CAS + konsantrasyon → ADR Tablo A girişi.

    concentration: % ağırlık (0-100). None ise en yüksek tehlikeli giriş döner.
    Eşleşme yoksa None döner → çağıran jenerik H-kodu mantığına düşer.
    Dönen dict'e 'physical_state' eklenir (seed'de tanımlıysa) — çağıran hal uyum kontrolü yapabilir.
    """
    mapping = _get_cas_map()
    entry = mapping.get(str(cas).strip())
    if not entry:
        return None

    # Konsantrasyon listesi varsa uygun aralığı seç
    if isinstance(entry, list):
        matched = None
        if concentration is not None:
            for rng in entry:
                lo = rng.get('min_conc', 0)
                hi = rng.get('max_conc', 100)
                if lo <= concentration <= hi:
                    matched = rng
                    break
        if matched is None:
            matched = entry[0]  # konsantrasyon bilinmiyor → en tehlikelisi
        un_no = matched.get('un')
        pg    = matched.get('pg') or 'II'
        seed_physical_state: 'str | None' = matched.get('physical_state')
    else:
        un_no = entry.get('un')
        pg    = entry.get('pg') or 'II'
        seed_physical_state = entry.get('physical_state')

    if not un_no:
        return None
    details = get_adr_details(un_no, pg)
    if not details.get('found'):
        return None
    if seed_physical_state:
        details['physical_state'] = seed_physical_state
    return details


def get_adr_details(un_no: str, packing_group: str = 'II') -> dict:
    """
    UN numarası ve ambalaj grubundan ADR detaylarını getir.
    """
    db = _load()

    un_key = un_no.upper().replace(' ', '').strip()
    if not un_key.startswith('UN'):
        un_key = 'UN' + un_key

    entry = db.get(un_key)
    if not entry:
        return {
            'un_no': un_key, 'name': 'NOT FOUND', 'name_tr': 'Bulunamadı',
            'class': '—', 'classification_code': '—', 'kemler': '—',
            'tunnel_code': '—', 'label': '—', 'found': False,
        }

    pg = (packing_group or 'II').upper().replace('PG', '').strip()
    pg_data = entry.get('packing_groups', {}).get(pg, {})

    _pg_used = pg
    if not pg_data and entry.get('packing_groups'):
        _first_key = list(entry['packing_groups'].keys())[0]
        pg_data = entry['packing_groups'][_first_key]
        _pg_used = _first_key

    _has_nested  = bool(entry.get('packing_groups'))
    _pg_final    = _pg_used if _has_nested else (entry.get('packing_group') or _pg_used)
    _kemler      = pg_data.get('kemler') if _has_nested else entry.get('kemler', '')
    _tunnel      = pg_data.get('tunnel') if _has_nested else entry.get('tunnel', '—')
    if _kemler is None: _kemler = entry.get('kemler', '')
    if _tunnel is None: _tunnel = entry.get('tunnel', '—')

    return {
        'un_no':               un_key,
        'name':                entry.get('name', ''),
        'name_tr':             entry.get('name_tr', ''),
        'class':               entry.get('class', '—'),
        'classification_code': pg_data.get('classification_code') or entry.get('classification_code', '—'),
        'kemler':              _kemler or '—',
        'tunnel_code':         _tunnel or '—',
        'label':               pg_data.get('label', entry.get('class', '—')),
        'packing_group':       _pg_final,
        'special_provisions':  entry.get('special_provisions', []),
        'limited_qty':         (lambda lq: lq.get(_pg_final, '—') if isinstance(lq, dict) else (lq or '—'))(entry.get('limited_qty', '—')),
        'imdg_class':          entry.get('class', '—'),
        'iata_class':          entry.get('class', '—'),
        'found': True,
    }


if __name__ == '__main__':
    print(get_adr_details('UN1993', 'II'))
