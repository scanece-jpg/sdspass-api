"""
ADR Taşımacılık Servisi
=======================
UN numarasından ADR detaylarını döndürür:
  - Kemler kodu (tehlike tanımlama numarası)
  - Tünel kısıtlama kodu
  - Sınıflandırma kodu
  - Etiket
  - Sınırlı miktar

Kaynak: ADR 2023 Tablo A
"""

import json
import re
import logging
from pathlib import Path

log = logging.getLogger(__name__)

_ADR_DATA = None
_CAS_TO_UN = None

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
    """İsim eşleştirme için normalize et: küçük harf, noktalama temizle."""
    name = name.lower()
    name = re.sub(r'[,\.\-\(\)/]', ' ', name)
    # B.N.O. / N.O.S. ve benzeri jenerik ifadeleri at
    name = re.sub(r'\b(n\.?o\.?s\.?|b\.?n\.?o\.?|nos|bno)\b', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name


# İsim eşleşmesiyle bulunamayan yaygın maddeler — her zaman dahil edilir
_SEED_ENTRIES: dict[str, dict] = {
    '7664-93-9': {'un': 'UN1830', 'pg': 'II'},   # Sülfürik asit
    '7697-37-2': {'un': 'UN2031', 'pg': 'II'},   # Nitrik asit
    '7647-01-0': {'un': 'UN1789', 'pg': 'II'},   # Hidroklorik asit
    '7664-38-2': {'un': 'UN1805', 'pg': 'III'},  # Fosforik asit
    '1310-73-2': {'un': 'UN1824', 'pg': 'II'},   # Sodyum hidroksit çözelti
    '1310-58-3': {'un': 'UN1814', 'pg': 'II'},   # Potasyum hidroksit çözelti
    '7681-52-9': {'un': 'UN1791', 'pg': 'II'},   # Sodyum hipoklorit çözelti
    '87-90-1':   {'un': 'UN2468', 'pg': 'II'},   # TCCA (Trikloroizosiyanurik asit)
    '2893-78-9': {'un': 'UN2468', 'pg': 'II'},   # Sodyum dikloroizosiyanurik asit
    '10049-04-4':{'un': 'UN2548', 'pg': 'I'},    # Klor dioksit
    '7726-95-6': {'un': 'UN1744', 'pg': 'I'},    # Brom
    '7782-79-8': {'un': 'UN3123', 'pg': 'I'},    # Hidrazoik asit
    '7803-51-2': {'un': 'UN2199', 'pg': 'I'},    # Fosfin
    '74-90-8':   {'un': 'UN1051', 'pg': 'I'},    # Hidrojen siyanür
    '7783-06-4': {'un': 'UN1053', 'pg': 'I'},    # Hidrojen sülfür
    '7647-19-0': {'un': 'UN1826', 'pg': 'I'},    # Fosfor pentaflorür
    '10025-87-3':{'un': 'UN1810', 'pg': 'I'},    # Fosfor oksikorür
    '75-44-5':   {'un': 'UN1076', 'pg': 'I'},    # Fosgen
    '7784-34-1': {'un': 'UN1556', 'pg': 'I'},    # Arsenik triklorür
    '108-88-3':  {'un': 'UN1294', 'pg': 'II'},   # Toluen
    '71-43-2':   {'un': 'UN1114', 'pg': 'II'},   # Benzen
    '110-54-3':  {'un': 'UN1208', 'pg': 'II'},   # n-Hekzan
    '142-82-5':  {'un': 'UN1278', 'pg': 'II'},   # n-Heptan
    '64-17-5':   {'un': 'UN1170', 'pg': 'II'},   # Etanol
    '67-63-0':   {'un': 'UN1219', 'pg': 'II'},   # İzopropanol
    '78-93-3':   {'un': 'UN1193', 'pg': 'II'},   # Metil etil keton
    '67-64-1':   {'un': 'UN1090', 'pg': 'II'},   # Aseton
    '127-19-5':  {'un': 'UN2810', 'pg': 'III'},  # DMAc
    '108-05-4':  {'un': 'UN1301', 'pg': 'II'},   # Vinil asetat
    '75-05-8':   {'un': 'UN1648', 'pg': 'II'},   # Asetonitril
    '79-01-6':   {'un': 'UN1710', 'pg': 'III'},  # Trikloretilen
    '7778-54-3': {'un': 'UN2208', 'pg': 'II'},   # Kalsiyum hipoklorit
}


def _build_cas_map() -> dict:
    """
    substance_db.json (CAS + isimler) × adr_data.json (isim + UN) →
    CAS→UN eşleme tablosu. İsim normalleştirmesi + sabit seed girişleri.
    """
    sub_path = _DATA_DIR / 'substance_db.json'
    adr_path = _DATA_DIR / 'adr_data.json'
    if not sub_path.exists() or not adr_path.exists():
        return {}

    with open(sub_path, encoding='utf-8') as f:
        substances = json.load(f)
    adr_db = _load()

    # ADR tablosunu normalize isim → (un_key, pg) olarak indeksle
    adr_index: dict[str, tuple[str, str]] = {}
    for un_key, entry in adr_db.items():
        raw = entry.get('name', '')
        if not raw:
            continue
        norm = _normalize(raw)
        if not norm:
            continue
        # Ambalaj grubu: nested packing_groups varsa ilk anahtarı al
        pgs = entry.get('packing_groups', {})
        pg = list(pgs.keys())[0] if pgs else (entry.get('packing_group') or 'II')
        adr_index[norm] = (un_key, pg)

    # Seed girişleriyle başla, üstüne mevcut dosyayı ve isim eşleşmelerini ekle
    mapping: dict[str, dict] = dict(_SEED_ENTRIES)
    cas_path = _DATA_DIR / 'cas_to_un.json'
    if cas_path.exists():
        with open(cas_path, encoding='utf-8') as f:
            existing = json.load(f)
        mapping.update(existing)  # Mevcut dosya seed'in üstüne yazılır

    matched = 0

    # Her madde için CAS al, isimleri normalize edip adr_index'te ara
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
            if not norm:
                continue
            if norm in adr_index:
                un_key, pg = adr_index[norm]
                mapping[cas] = {'un': un_key, 'pg': pg}
                matched += 1
                break

    log.info('cas_to_un: %d CAS eşleşti, toplam %d giriş', matched, len(mapping))
    return mapping


def _load_cas_map() -> dict:
    """
    cas_to_un.json yükler. substance_db.json daha yeniyse otomatik yeniden oluşturur.
    """
    global _CAS_TO_UN
    cas_path = _DATA_DIR / 'cas_to_un.json'
    sub_path = _DATA_DIR / 'substance_db.json'

    # substance_db güncellenmiş mi kontrol et → yeniden oluştur
    needs_rebuild = False
    if not cas_path.exists():
        needs_rebuild = True
    elif sub_path.exists() and sub_path.stat().st_mtime > cas_path.stat().st_mtime:
        needs_rebuild = True

    if needs_rebuild:
        log.info('cas_to_un.json yeniden oluşturuluyor...')
        _CAS_TO_UN = None  # cache'i sıfırla
        new_map = _build_cas_map()
        if new_map:
            with open(cas_path, 'w', encoding='utf-8') as f:
                json.dump(new_map, f, ensure_ascii=False, indent=2)
            _CAS_TO_UN = new_map
            log.info('cas_to_un.json yazıldı: %d giriş', len(new_map))
        else:
            _CAS_TO_UN = {}
    elif _CAS_TO_UN is None:
        if cas_path.exists():
            with open(cas_path, encoding='utf-8') as f:
                _CAS_TO_UN = json.load(f)
        else:
            _CAS_TO_UN = {}

    return _CAS_TO_UN


def lookup_by_cas(cas: str) -> dict | None:
    """
    CAS numarasından ADR Tablo A girişini döndürür.
    cas_to_un.json → adr_data.json zinciri.
    Eşleşme yoksa None döner (çağıran jenerik H-kodu mantığına düşer).
    """
    mapping = _load_cas_map()
    entry = mapping.get(str(cas).strip())
    if not entry:
        return None
    un_no = entry.get('un')
    pg    = entry.get('pg') or 'II'
    if not un_no:
        return None
    details = get_adr_details(un_no, pg)
    if not details.get('found'):
        return None
    return details


def get_adr_details(un_no: str, packing_group: str = 'II') -> dict:
    """
    UN numarası ve ambalaj grubundan ADR detaylarını getir.

    Returns:
        {
          un_no, name, name_tr, class, classification_code,
          kemler, tunnel_code, label,
          imdg_class, iata_class  (aynı sınıf, farklı isim)
        }
    """
    db = _load()

    # UN no formatını normalize et — "UN 3093", "un3093", "3093" hepsini kabul et
    un_key = un_no.upper().replace(' ', '').strip()
    if not un_key.startswith('UN'):
        un_key = 'UN' + un_key

    entry = db.get(un_key)
    if not entry:
        return {
            'un_no': un_key,
            'name': 'NOT FOUND',
            'name_tr': 'Bulunamadı',
            'class': '—',
            'classification_code': '—',
            'kemler': '—',
            'tunnel_code': '—',
            'label': '—',
            'found': False,
        }

    # Ambalaj grubuna göre detay
    pg = packing_group.upper().replace('PG', '').strip()
    pg_data = entry.get('packing_groups', {}).get(pg, {})

    # İç içe yapıda PG bulunamazsa ilk olanı al
    _pg_used = pg
    if not pg_data and entry.get('packing_groups'):
        _first_key = list(entry['packing_groups'].keys())[0]
        pg_data = entry['packing_groups'][_first_key]
        _pg_used = _first_key

    # Düz (flat) yapı desteği: packing_groups yoksa üst seviyeden oku.
    # Bazı kayıtlar (örn. UN3098) packing_groups dict'i taşımaz;
    # packing_group / kemler / tunnel alanları doğrudan giriş seviyesindedir.
    _has_nested = bool(entry.get('packing_groups'))
    _pg_final      = _pg_used if _has_nested else (entry.get('packing_group') or _pg_used)
    _kemler_final  = pg_data.get('kemler') if _has_nested else entry.get('kemler', '')
    _tunnel_final  = pg_data.get('tunnel') if _has_nested else entry.get('tunnel', '—')
    # Her iki yapıda da pg_data boşsa üst seviyeye düş (ek güvence)
    if _kemler_final is None:
        _kemler_final = entry.get('kemler', '')
    if _tunnel_final is None:
        _tunnel_final = entry.get('tunnel', '—')

    return {
        'un_no':               un_key,
        'name':                entry.get('name', ''),
        'name_tr':             entry.get('name_tr', ''),
        'class':               entry.get('class', '—'),
        'classification_code': pg_data.get('classification_code') or entry.get('classification_code', '—'),
        'kemler':              _kemler_final if _kemler_final else '—',
        'tunnel_code':         _tunnel_final if _tunnel_final else '—',
        'label':               pg_data.get('label', entry.get('class', '—')),
        'packing_group':       _pg_final,
        'special_provisions':  entry.get('special_provisions', []),
        'limited_qty':         (lambda lq: lq.get(_pg_final, '—') if isinstance(lq, dict) else (lq or '—'))(entry.get('limited_qty', '—')),
        # IMDG ve IATA için sınıf aynı, isim farklı olabilir
        'imdg_class':          entry.get('class', '—'),
        'iata_class':          entry.get('class', '—'),
        'found': True,
    }


# auto_detect_un() KALDIRILDI.
# Transport sınıflandırması tek kaynaktan yapılır: js/engines/transport_engine.js
# Bu fonksiyonu çağıran herhangi bir kod varsa transport_engine.js çıktısını kullanacak şekilde güncelleyin.


if __name__ == '__main__':
    # Test
    print(get_adr_details('UN1993', 'II'))
    print()
    print(auto_detect_un(['H225', 'H315']))
