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
_HCL_PG_NOTE = ('ADR Tablo A UN 1789 için PG II ve PG III öngörür; ayrım konsantrasyona göre değil '
                'ADR 2.2.8.1.5 aşındırıcılık ölçütlerine (deri tahribat süresi / metal korozyon hızı) '
                'göre yapılır. %25 sınırı varsayımdır — tedarikçi SDS’i veya test verisiyle doğrulayın.')

_SEED_ENTRIES: dict = {
    # ── Asitler ───────────────────────────────────────────────────────────────
    '7664-93-9': [  # Sülfürik asit — ADR Tablo A
        {'min_conc': 51,  'max_conc': 100, 'un': 'UN1830', 'pg': 'II'},
        {'min_conc': 0,   'max_conc': 51,  'un': 'UN2796', 'pg': 'II'},   # Tablo A: yalnız PG II
    ],
    '7697-37-2': [  # Nitrik asit — ADR Tablo A
        {'min_conc': 65,  'max_conc': 100, 'un': 'UN2031', 'pg': 'I', 'pg_fixed': True},
        {'min_conc': 0,   'max_conc': 65,  'un': 'UN2031', 'pg': 'II', 'pg_fixed': True},
    ],
    '7647-01-0': [  # Hidrojen klorür: gaz (susuz) / hidroklorik asit çözeltisi — ADR Tablo A
        {'min_conc': 0,   'max_conc': 100, 'un': 'UN1050', 'pg': '', 'physical_state': 'gas'},
        # Tablo A UN1789 için PG II ve PG III öngörür ama ayrımı konsantrasyonla değil
        # 2.2.8.1.5 aşındırıcılık ölçütleriyle yapar — %25 sınırı bir varsayımdır.
        {'min_conc': 25,  'max_conc': 100, 'un': 'UN1789', 'pg': 'II', 'physical_state': 'liquid',
         'note': _HCL_PG_NOTE},
        {'min_conc': 0,   'max_conc': 25,  'un': 'UN1789', 'pg': 'III', 'physical_state': 'liquid',
         'note': _HCL_PG_NOTE},
    ],
    '7664-38-2': {'un': 'UN1805', 'pg': 'III'},  # Fosforik asit
    '10035-10-6':{'un': 'UN1788', 'pg': 'II'},   # Hidrobromik asit
    '7789-21-1': {'un': 'UN1777', 'pg': 'I'},    # Florosülfürik asit (Tablo A: yalnız PG I)

    # ── Bazlar ────────────────────────────────────────────────────────────────
    '1310-73-2': [  # Sodyum hidroksit — ADR Tablo A: katı UN1823, çözelti UN1824
        {'min_conc': 0,   'max_conc': 100, 'un': 'UN1824', 'pg': 'II', 'physical_state': 'liquid'},
        {'min_conc': 0,   'max_conc': 100, 'un': 'UN1823', 'pg': 'II', 'physical_state': 'solid'},
    ],
    '1310-58-3': [  # Potasyum hidroksit — ADR Tablo A: katı UN1813, çözelti UN1814
        {'min_conc': 0,   'max_conc': 100, 'un': 'UN1814', 'pg': 'II', 'physical_state': 'liquid'},
        {'min_conc': 0,   'max_conc': 100, 'un': 'UN1813', 'pg': 'II', 'physical_state': 'solid'},
    ],
    # ── Adlı çözelti girişleri (ADR 2025 Tablo A; ADR 2.1.3.3) — 2026-10-09 eklendi ───────────────
    # PG: Tablo A derişimle sabitlediyse pg_fixed; birden çok PG varsa ADR 2.2.x hesabından gelir.
    '64-19-7': [  # Asetik asit — UN2789 (>%80, 8+3), UN2790 (%50–80 PG II; >%10–<%50 PG III)
        {'min_conc': 80, 'max_conc': 100, 'un': 'UN2789', 'pg': 'II',  'physical_state': 'liquid', 'min_exclusive': True, 'pg_fixed': True},
        {'min_conc': 50, 'max_conc': 80,  'un': 'UN2790', 'pg': 'II',  'physical_state': 'liquid', 'pg_fixed': True},
        {'min_conc': 10, 'max_conc': 50,  'un': 'UN2790', 'pg': 'III', 'physical_state': 'liquid', 'min_exclusive': True, 'pg_fixed': True},
    ],
    '64-18-6': [  # Formik asit — Tablo A: UN1779 >%85 (8+3); UN3412 %10–85 PG II, %5–<10 PG III
        {'min_conc': 85, 'max_conc': 100, 'un': 'UN1779', 'pg': 'II',  'physical_state': 'liquid', 'min_exclusive': True, 'pg_fixed': True},
        {'min_conc': 10, 'max_conc': 85,  'un': 'UN3412', 'pg': 'II',  'physical_state': 'liquid', 'pg_fixed': True},
        {'min_conc': 5,  'max_conc': 10,  'un': 'UN3412', 'pg': 'III', 'physical_state': 'liquid', 'pg_fixed': True},
    ],
    '7664-39-3': [  # Hidrojen florür — susuz UN1052 (gaz); hidroflorik asit UN1790: >%60 PG I, ≤%60 PG II (8+6.1)
        {'min_conc': 0,  'max_conc': 100, 'un': 'UN1052', 'pg': '',    'physical_state': 'gas'},
        {'min_conc': 60, 'max_conc': 100, 'un': 'UN1790', 'pg': 'I',   'physical_state': 'liquid', 'min_exclusive': True, 'pg_fixed': True},
        {'min_conc': 0,  'max_conc': 60,  'un': 'UN1790', 'pg': 'II',  'physical_state': 'liquid', 'pg_fixed': True},
    ],
    '141-43-5':  {'un': 'UN2491', 'pg': 'III', 'physical_state': 'liquid'},   # Etanolamin / çözeltisi
    '7646-85-7': [{'min_conc': 0, 'max_conc': 100, 'un': 'UN1840', 'pg': 'III', 'physical_state': 'liquid'},   # Çinko klorür çözeltisi
                  {'min_conc': 0, 'max_conc': 100, 'un': 'UN2331', 'pg': 'III', 'physical_state': 'solid'}],   # susuz
    '7705-08-0': [{'min_conc': 0, 'max_conc': 100, 'un': 'UN2582', 'pg': 'III', 'physical_state': 'liquid'},   # Ferrik klorür çözeltisi
                  {'min_conc': 0, 'max_conc': 100, 'un': 'UN1773', 'pg': 'III', 'physical_state': 'solid'}],
    '7446-70-0': [{'min_conc': 0, 'max_conc': 100, 'un': 'UN2581', 'pg': 'III', 'physical_state': 'liquid'},   # Alüminyum klorür çözeltisi
                  {'min_conc': 0, 'max_conc': 100, 'un': 'UN1726', 'pg': 'II',  'physical_state': 'solid'}],
    '7758-19-2': [{'min_conc': 0, 'max_conc': 100, 'un': 'UN1908', 'pg': 'II',  'physical_state': 'liquid'},   # Klorit çözeltisi
                  {'min_conc': 0, 'max_conc': 100, 'un': 'UN1496', 'pg': 'II',  'physical_state': 'solid'}],
    '7775-09-9': [{'min_conc': 0, 'max_conc': 100, 'un': 'UN2428', 'pg': 'II',  'physical_state': 'liquid'},   # Sodyum klorat
                  {'min_conc': 0, 'max_conc': 100, 'un': 'UN1495', 'pg': 'II',  'physical_state': 'solid'}],
    '1302-42-7': {'un': 'UN1819', 'pg': 'II', 'physical_state': 'liquid'},    # Sodyum alüminat çözeltisi
    '1310-65-2': [{'min_conc': 0, 'max_conc': 100, 'un': 'UN2679', 'pg': 'II',  'physical_state': 'liquid'},   # Lityum hidroksit
                  {'min_conc': 0, 'max_conc': 100, 'un': 'UN2680', 'pg': 'II',  'physical_state': 'solid'}],
    '124-09-4':  [{'min_conc': 0, 'max_conc': 100, 'un': 'UN1783', 'pg': 'II',  'physical_state': 'liquid'},   # Heksametilendiamin
                  {'min_conc': 0, 'max_conc': 100, 'un': 'UN2280', 'pg': 'III', 'physical_state': 'solid'}],
    '7681-38-1': {'un': 'UN2837', 'pg': 'II', 'physical_state': 'liquid'},    # Bisülfatlar, sulu çözelti
    '76-03-9':   [{'min_conc': 0, 'max_conc': 100, 'un': 'UN2564', 'pg': 'II',  'physical_state': 'liquid'},   # Trikloroasetik asit
                  {'min_conc': 0, 'max_conc': 100, 'un': 'UN1839', 'pg': 'II',  'physical_state': 'solid'}],
    '79-11-8':   [{'min_conc': 0, 'max_conc': 100, 'un': 'UN1750', 'pg': 'II',  'physical_state': 'liquid'},   # Kloroasetik asit
                  {'min_conc': 0, 'max_conc': 100, 'un': 'UN1751', 'pg': 'II',  'physical_state': 'solid'}],
    '108-95-2':  [{'min_conc': 0, 'max_conc': 100, 'un': 'UN2821', 'pg': 'II',  'physical_state': 'liquid'},   # Fenol çözeltisi
                  {'min_conc': 0, 'max_conc': 100, 'un': 'UN1671', 'pg': 'II',  'physical_state': 'solid'}],
    '143-33-9':  [{'min_conc': 0, 'max_conc': 100, 'un': 'UN3414', 'pg': 'I',   'physical_state': 'liquid'},   # Sodyum siyanür
                  {'min_conc': 0, 'max_conc': 100, 'un': 'UN1689', 'pg': 'I',   'physical_state': 'solid'}],
    '151-50-8':  [{'min_conc': 0, 'max_conc': 100, 'un': 'UN3413', 'pg': 'I',   'physical_state': 'liquid'},   # Potasyum siyanür
                  {'min_conc': 0, 'max_conc': 100, 'un': 'UN1680', 'pg': 'I',   'physical_state': 'solid'}],
    '7681-49-4': [{'min_conc': 0, 'max_conc': 100, 'un': 'UN3415', 'pg': 'III', 'physical_state': 'liquid'},   # Sodyum florür
                  {'min_conc': 0, 'max_conc': 100, 'un': 'UN1690', 'pg': 'III', 'physical_state': 'solid'}],
    '7789-23-3': [{'min_conc': 0, 'max_conc': 100, 'un': 'UN3422', 'pg': 'III', 'physical_state': 'liquid'},   # Potasyum florür
                  {'min_conc': 0, 'max_conc': 100, 'un': 'UN1812', 'pg': 'III', 'physical_state': 'solid'}],
    '79-06-1':   [{'min_conc': 0, 'max_conc': 100, 'un': 'UN3426', 'pg': 'III', 'physical_state': 'liquid'},   # Akrilamid
                  {'min_conc': 0, 'max_conc': 100, 'un': 'UN2074', 'pg': 'III', 'physical_state': 'solid'}],
    '1341-49-7': [{'min_conc': 0, 'max_conc': 100, 'un': 'UN2817', 'pg': 'II',  'physical_state': 'liquid'},   # Amonyum bifl.
                  {'min_conc': 0, 'max_conc': 100, 'un': 'UN1727', 'pg': 'II',  'physical_state': 'solid'}],
    '7789-29-9': [{'min_conc': 0, 'max_conc': 100, 'un': 'UN3421', 'pg': 'II',  'physical_state': 'liquid'},   # Potasyum bifl.
                  {'min_conc': 0, 'max_conc': 100, 'un': 'UN1811', 'pg': 'II',  'physical_state': 'solid'}],
    '1333-82-0': {'un': 'UN1755', 'pg': 'II', 'physical_state': 'liquid'},    # Kromik asit çözeltisi
    # Kalsiyum oksit: Tablo A UN1910 "ADR'ye tabi değildir" — önceden Sınıf 8 PG III veriliyordu.
    '1305-78-8': {'un': None, 'pg': None, 'sp_note': "UN1910 — ADR'ye tabi değildir (Tablo A)"},
    '7664-41-7': [  # Amonyak — gaz veya çözelti
        {'min_conc': 0,   'max_conc': 100, 'un': 'UN1005', 'pg': '', 'physical_state': 'gas'},      # Susuz (gaz)
        # Tablo A: UN3318 "%50'den fazla"; UN2073 "%35'ten fazla ama %50'den az";
        # UN2672 "%10'dan fazla ama %35'ten az". %10 ve altı bu adlı girişlere girmez.
        {'min_conc': 50,  'max_conc': 100, 'un': 'UN3318', 'pg': '', 'physical_state': 'liquid', 'min_exclusive': True},  # 4TC
        {'min_conc': 35,  'max_conc': 50,  'un': 'UN2073', 'pg': '', 'physical_state': 'liquid', 'min_exclusive': True},  # 4A
        {'min_conc': 10,  'max_conc': 35,  'un': 'UN2672', 'pg': 'III', 'physical_state': 'liquid', 'min_exclusive': True},  # C5
    ],

    # ── Oksitleyiciler ────────────────────────────────────────────────────────
    '7722-84-1': [  # Hidrojen peroksit — ADR Tablo A
        {'min_conc': 60,  'max_conc': 100, 'un': 'UN2015', 'pg': 'I', 'pg_fixed': True},
        {'min_conc': 20,  'max_conc': 60,  'un': 'UN2014', 'pg': 'II', 'pg_fixed': True},
        {'min_conc': 8,   'max_conc': 20,  'un': 'UN2984', 'pg': 'III', 'pg_fixed': True},   # Tablo A: %8–20 ayrı giriş
        # <8% taşıma yönetmeliği kapsamı dışı
    ],
    '7681-52-9': {'un': 'UN1791', 'pg': 'II', 'physical_state': 'liquid'},  # Sodyum hipoklorit çözelti
    '7778-54-3': [  # Kalsiyum hipoklorit — Tablo A: >%39 hazır klor UN1748 PG II; %10–39 karışım UN2208 PG III
        # (saf Ca(OCl)2'nin hazır kloru ≈ %99 → hazır klor ≈ madde yüzdesi)
        {'min_conc': 39,  'max_conc': 100, 'un': 'UN1748', 'pg': 'II',  'physical_state': 'solid', 'min_exclusive': True,
         'un_corr': 'UN3485', 'pg_fixed': True},
        {'min_conc': 10,  'max_conc': 39,  'un': 'UN2208', 'pg': 'III', 'physical_state': 'solid', 'min_exclusive': True,
         'un_corr': 'UN3486', 'pg_fixed': True},
    ],
    '87-90-1':   {'un': 'UN2468', 'pg': 'II', 'physical_state': 'solid'},  # TCCA (ADR: "TRİKLOROİZOSİYANÜRİK ASİT, KURU")
    '2893-78-9': {'un': 'UN2465', 'pg': 'II', 'physical_state': 'solid'},  # Sodyum dikloroizosiyanürat, kuru (önceden yanlışlıkla UN2468)
    # ADR SP 135 (Tablo A Satır 836): troklosen sodyum dihidrat Sınıf 5.1 kriterini KARŞILAMAZ.
    # un=None sentinel: kayıt var ama adlı girdi yok → lookup_by_cas None döner → B.N.O. yolu.
    # İsim-eşleştirmesinin yanlış giriş bulmasını engeller.
    '51580-86-0': {'un': None, 'pg': None, 'sp_note': 'SP 135 — Sınıf 5.1 kriterleri karşılanmaz'},

    # ── Halojenler / Gazlar ───────────────────────────────────────────────────
    '7726-95-6': {'un': 'UN1744', 'pg': 'I'},    # Brom
    # Gazlarda (Sınıf 2) ambalaj grubu yoktur → pg ''.
    '7782-50-5': {'un': 'UN1017', 'pg': ''},     # Klor gazı
    '7803-51-2': {'un': 'UN2199', 'pg': ''},     # Fosfin
    '74-90-8':   {'un': 'UN1051', 'pg': 'I'},    # Hidrojen siyanür
    '7783-06-4': {'un': 'UN1053', 'pg': ''},     # Hidrojen sülfür
    '75-44-5':   {'un': 'UN1076', 'pg': ''},     # Fosgen
    '7647-19-0': {'un': 'UN2198', 'pg': ''},     # Fosfor pentaflorür (önceden yanlışlıkla UN1826)
    '10025-87-3':{'un': 'UN1810', 'pg': 'I'},    # Fosfor oksiklorür

    # ── Ağır metaller / Toksikler ─────────────────────────────────────────────
    '7784-34-1': {'un': 'UN1560', 'pg': 'I'},    # Arsenik triklorür (önceden B.B.B. UN1556)
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
    '142-82-5':  {'un': 'UN1206', 'pg': 'II'},   # n-Heptan — HEPTANLAR (önceden yanlışlıkla UN1278 1-kloropropan)
    '108-05-4':  {'un': 'UN1301', 'pg': 'II'},   # Vinil asetat
    '75-05-8':   {'un': 'UN1648', 'pg': 'II'},   # Asetonitril
    '79-01-6':   {'un': 'UN1710', 'pg': 'III'},  # Trikloretilen
    # Formaldehit: Tablo A UN2209 "en az %25 formaldehit içeren" (Sınıf 8). UN1198 alevlenir çözelti içindir
    # (parlama noktasına göre) — önceden ≥%25 → UN1198, <%25 → UN2209 diye ters yazılmıştı.
    '50-00-0': [
        {'min_conc': 25,  'max_conc': 100, 'un': 'UN2209', 'pg': 'III', 'physical_state': 'liquid'},
    ],

    # ── Petrol ürünleri ───────────────────────────────────────────────────────
    '86290-81-5': {'un': 'UN1203', 'pg': 'II'},   # Benzin (Naphtha petroleum hydrotreated light)
}


def _build_cas_map() -> dict:
    """
    substance_db.json × adr_data.json isim eşleşmesi → bellek-içi CAS→UN haritası.
    Seed girişleri her zaman dahil, isim eşleşmesi üstüne eklenir.
    Dosyaya yazılmaz.
    """
    mapping: dict = dict(_SEED_ENTRIES)

    # Tablo A tek madde girişlerinin CAS eşlemesi (data/adr_cas_map.json, 2026-10-10) — seed'ler önceliklidir
    _gen = _DATA_DIR / 'adr_cas_map.json'
    if _gen.exists():
        with open(_gen, encoding='utf-8') as f:
            for cas, rows in (json.load(f).get('harita') or {}).items():
                if cas not in mapping:
                    rows = [{k: v for k, v in r.items() if not k.startswith('_')} for r in rows]
                    mapping[cas] = rows if len(rows) > 1 or 'min_conc' in rows[0] else rows[0]

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


def lookup_by_cas(cas: str, concentration: Optional[float] = None,
                  physical_state: Optional[str] = None, corrosive: bool = False) -> 'dict | None':
    """
    CAS + konsantrasyon (+ fiziksel hal) → ADR Tablo A girişi.

    concentration: % ağırlık (0-100). None ise en yüksek tehlikeli giriş döner.
    physical_state: 'gas' | 'liquid' | 'solid' — aynı CAS'ın hale göre farklı girişi varsa
      (örn. HCl gaz UN1050 / çözelti UN1789) uygun olan seçilir.
    Eşleşme yoksa None döner → çağıran jenerik H-kodu mantığına düşer.
    Dönen dict'e 'physical_state' eklenir (seed'de tanımlıysa) — çağıran hal uyum kontrolü yapabilir.
    """
    mapping = _get_cas_map()
    entry = mapping.get(str(cas).strip())
    if not entry:
        return None

    # Konsantrasyon listesi varsa uygun aralığı seç
    if isinstance(entry, list):
        cands = entry
        if physical_state and any(r.get('physical_state') for r in entry):
            cands = [r for r in entry if r.get('physical_state') in (None, physical_state)]
            if not cands:
                return None   # bu hal için adlı giriş yok → B.N.O.
        matched = None
        if concentration is not None:
            for rng in cands:
                lo = rng.get('min_conc', 0)
                hi = rng.get('max_conc', 100)
                lo_ok = concentration > lo if rng.get('min_exclusive') else concentration >= lo
                if lo_ok and concentration <= hi:
                    matched = rng
                    break
            if matched is None:
                return None   # bu konsantrasyon için adlı giriş yok (örn. amonyak ≤ %10) → B.N.O.
        if matched is None:
            matched = cands[0]  # konsantrasyon bilinmiyor → en tehlikelisi
        un_no = (matched.get('un_corr') if corrosive and matched.get('un_corr') else matched.get('un'))
        pg    = matched['pg'] if 'pg' in matched else 'II'   # gazlarda ambalaj grubu yok ('')
        pg_fixed = bool(matched.get('pg_fixed'))
        seed_physical_state: 'str | None' = matched.get('physical_state')
        seed_note = matched.get('note')
    else:
        seed_note = entry.get('note')
        un_no = entry.get('un')
        pg    = entry['pg'] if 'pg' in entry and entry['pg'] is not None else 'II'
        pg_fixed = bool(entry.get('pg_fixed'))
        seed_physical_state = entry.get('physical_state')

    if not un_no:
        return None
    details = get_adr_details(un_no, pg)
    if not details.get('found'):
        return None
    if pg == '':   # gazlar — ambalaj grubu yoktur
        details['packing_group'] = ''
    if seed_physical_state:
        details['physical_state'] = seed_physical_state
    if seed_note:
        details['seed_note'] = seed_note
    details['pg_fixed'] = pg_fixed
    return details


def class8_pg_for_cas(cas: str) -> Optional[str]:
    """Tablo A'da adıyla yer alan maddenin Sınıf 8 ambalaj grubu (birden çok giriş varsa en ağırı).
    ADR 2.2.8.1.6.3 hesabında bileşenin "atanmış" PG'si olarak kullanılır. Yoksa None."""
    entry = _get_cas_map().get(str(cas).strip())   # seed + Tablo A CAS eşlemesi
    if not entry:
        return None
    best = None
    for rng in (entry if isinstance(entry, list) else [entry]):
        un, pg = rng.get('un'), rng.get('pg')
        if not un or pg not in ('I', 'II', 'III'):
            continue
        if get_adr_details(un, pg).get('class') != '8':
            continue
        if best is None or ['I', 'II', 'III'].index(pg) < ['I', 'II', 'III'].index(best):
            best = pg
    return best


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
        # Etiket listesi (örn. ['2.3', '8']) — gazlarda ADR sınıfı "2", IMDG/IATA bölümü labels[0]
        'labels':              entry.get('labels') or [x for x in str(pg_data.get('label') or '').split('+') if x],
        'packing_group':       _pg_final,
        'special_provisions':  entry.get('special_provisions', []),
        'limited_qty':         (lambda lq: lq.get(_pg_final, '—') if isinstance(lq, dict) else (lq or '—'))(entry.get('limited_qty', '—')),
        'imdg_class':          entry.get('class', '—'),
        'iata_class':          entry.get('class', '—'),
        'found': True,
    }


if __name__ == '__main__':
    print(get_adr_details('UN1993', 'II'))
