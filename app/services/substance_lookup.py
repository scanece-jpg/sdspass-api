"""
Substance Lookup Service
========================
Arama Hiyerarşisi:
  Sıra 1 — data/sea_ek6_tr.json      SEA Ek-6 (TR kanunu, mutlak öncelik)
            + ECHA ATP22'den eksik tehlike sınıfları merge edilir
  Sıra 2 — data/substance_db.json    ECHA ATP22 (EN, harmonize sınıflandırma)
  Sıra 3 — data/echa_cl/             ECHA C&L API önbelleği
  Sıra 4 — data/pubchem_cl/          PubChem önbelleği
  Sıra 5 — substances_custom.json    Tedarikçi/kullanıcı girişi

Yardımcı veriler:
  data/substance_names.json          CAS → {en, tr} çok dilli isimler
"""
import json, os, threading, re
from typing import Optional, Dict

_BASE          = os.path.join(os.path.dirname(__file__), '..', '..', 'data')
_ECHA_CL_DIR   = os.path.join(_BASE, 'echa_cl')       # ECHA C&L API önbelleği
_PUBCHEM_DIR   = os.path.join(_BASE, 'pubchem_cl')    # PubChem önbelleği
_CUSTOM_PATH   = os.path.join(_BASE, 'substances_custom.json')
_OEL_PATH      = os.path.join(_BASE, 'tr_oel_limits.json')
_DB_PATH       = os.path.join(_BASE, 'substance_db.json')    # ECHA ATP22 (EN)
_NAMES_PATH    = os.path.join(_BASE, 'substance_names.json')  # CAS → {en, tr, ...}
_SEA_EK6_PATH  = os.path.join(_BASE, 'sea_ek6_tr.json')      # SEA Ek-6 (TR, Sıra 1)

_CUSTOM_DB:    Optional[Dict] = None
_OEL_DB:       Optional[Dict] = None
_SUBSTANCE_DB: Optional[Dict] = None
_NAMES_DB:     Optional[Dict] = None
_SEA_EK6_DB:   Optional[Dict] = None
_lock = threading.Lock()

# ---------------------------------------------------------------------------
# Tehlike sınıfı grupları — merge için aynı sınıfın farklı H kodlarını eşleştirir
# CLP/KKDİK Ek-2 sınıf yapısına göre: aynı gruptaki kodlar birbirini kapsar
# (örn. H314 ve H315 aynı sınıf — cilt korozif/tahriş edici)
# ---------------------------------------------------------------------------
_H_CLASS_GROUP: dict[str, str] = {
    # Alevlenebilir gazlar
    'H220': 'flam_gas',  'H221': 'flam_gas',  'H232': 'flam_gas',
    # Alevlenebilir aerosoller
    'H222': 'flam_aero', 'H223': 'flam_aero',
    # Alevlenebilir sıvılar
    'H224': 'flam_liq',  'H225': 'flam_liq',  'H226': 'flam_liq',
    # Alevlenebilir katılar
    'H228': 'flam_sol',
    # Kendiliğinden tepkimeye girenler / Organik peroksitler
    'H240': 'self_react', 'H241': 'self_react', 'H242': 'self_react',
    # Piroforik
    'H250': 'pyro_liq',  'H252': 'pyro_sol',
    # Kendiliğinden ısınan
    'H251': 'self_heat', 'H252': 'self_heat',
    # Su ile tepkimeye girenler
    'H260': 'water_react', 'H261': 'water_react',
    # Oksitleyiciler
    'H270': 'ox_gas', 'H271': 'ox_liq', 'H272': 'ox_liq',
    # Basınç altında gazlar
    'H229': 'press_gas', 'H280': 'press_gas', 'H281': 'press_gas',
    # Metal korozyonu
    'H290': 'metal_corr',
    # Akut toksisite — ağızdan / dermal / soluma (ayrı sınıflar)
    'H300': 'acute_oral',  'H301': 'acute_oral',  'H302': 'acute_oral',
    'H310': 'acute_derm',  'H311': 'acute_derm',  'H312': 'acute_derm',
    'H330': 'acute_inh',   'H331': 'acute_inh',   'H332': 'acute_inh',
    # Aspirasyon tehlikesi
    'H304': 'asp_haz',
    # Cilt korozif / tahriş edici (aynı sınıf — H314 daha şiddetli)
    'H314': 'skin_corr_irrit', 'H315': 'skin_corr_irrit',
    # Göz hasarı / tahriş (aynı sınıf)
    'H318': 'eye_dam_irrit',   'H319': 'eye_dam_irrit',
    # Cilt hassaslaştırıcı
    'H317': 'skin_sens',
    # Solunum hassaslaştırıcı
    'H334': 'resp_sens',
    # Mutajenite
    'H340': 'muta', 'H341': 'muta',
    # Kanserojenite
    'H350': 'carc', 'H351': 'carc',
    # Üreme toksisitesi
    'H360': 'repr', 'H361': 'repr', 'H362': 'repr',
    # STOT — tek maruziyet
    'H335': 'stot_se', 'H336': 'stot_se', 'H370': 'stot_se', 'H371': 'stot_se',
    # STOT — tekrarlanan maruziyet
    'H372': 'stot_re', 'H373': 'stot_re',
    # Sucul — akut
    'H400': 'aquatic_acute', 'H401': 'aquatic_acute', 'H402': 'aquatic_acute',
    # Sucul — kronik
    'H410': 'aquatic_chron', 'H411': 'aquatic_chron',
    'H412': 'aquatic_chron', 'H413': 'aquatic_chron',
    # Ozon katmanı için tehlikeli
    'H420': 'ozone',
}


def _merge_annex_supplements(tr_hazards: list, annex_hazards: list) -> list:
    """
    TR Ek-6 tehlike listesine Annex VI'dan eksik tehlike SINIFLARINI ekle.
    Aynı sınıftan (örn. cilt korozif/tahriş) TR Ek-6'da zaten varsa Annex VI'dakini ekleme.
    Döndürür: ek tehlikeler listesi (her biri '_annex_supplement': True ile işaretli)
    """
    # TR'deki mevcut tehlike sınıf grupları
    tr_groups: set[str] = set()
    for h in tr_hazards:
        code = (h.get('h_code') or '').replace('*', '').replace(' ', '')[:4]
        g = _H_CLASS_GROUP.get(code)
        if g:
            tr_groups.add(g)

    supplements = []
    seen_groups: set[str] = set()
    for h in annex_hazards:
        code = (h.get('h_code') or '').replace('*', '').replace(' ', '')[:4]
        g = _H_CLASS_GROUP.get(code)
        if not g:
            continue  # tanınmayan kod — atla
        if g in tr_groups or g in seen_groups:
            continue  # bu sınıf zaten var
        supplements.append({**h, '_annex_supplement': True})
        seen_groups.add(g)

    return supplements


# ---------------------------------------------------------------------------
# Per-dosya okuyucu
# ---------------------------------------------------------------------------

def _read_cl_file(directory: str, cas: str) -> Optional[Dict]:
    """data/cl/{xx}/{cas}.json veya data/annex6/{xx}/{cas}.json oku."""
    path = os.path.join(directory, cas[:2], f'{cas}.json')
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except Exception:
        return None


def _cl_to_legacy(entry: dict, priority: int, source_label: str) -> dict:
    """
    Per-dosya formatını (classification/labelling) eski API formatına çevir.
    main.py endpoint'i 'hazards', 'signal', 'pictograms' bekliyor.
    """
    cl = entry.get('classification', {})
    lb = entry.get('labelling', {})

    # classification.hazards → [{h_class, h_code, note_flag?, note?, repro_sub?}] formatına çevir
    def _build_hazard(h: dict) -> dict:
        d = {'h_class': h.get('class', ''), 'h_code': h.get('h_code', '')}
        if h.get('note_flag'):
            d['note_flag'] = h['note_flag']
        if h.get('note'):
            d['note'] = h['note']
        if h.get('repro_sub'):
            d['repro_sub'] = h['repro_sub']
        return d

    hazards = [_build_hazard(h) for h in cl.get('hazards', [])]

    return {
        'cas'            : entry.get('cas', ''),
        'name'           : entry.get('name', ''),
        'name_tr'        : entry.get('name_tr', ''),
        'ec_no'          : entry.get('ec_no', ''),
        'index_no'       : entry.get('index_no', ''),
        'atp'            : entry.get('atp', ''),
        'notes'          : entry.get('notes', []),
        'ate'            : entry.get('ate', {}),
        'signal'         : lb.get('signal', ''),
        'pictograms'     : lb.get('pictograms', []),
        'hazards'        : hazards,
        'suppl_hazards'  : lb.get('suppl_h', []),
        'm_factors'      : cl.get('m_factors', {}),
        'scl'            : [
            {
                'h_code' : s.get('h_code', ''),
                'h_class': s.get('class', ''),
                'c_min'  : s.get('c_min'),
                'c_max'  : s.get('c_max'),
            }
            for s in cl.get('scl_limits', [])
        ],
        'sea_ek6'        : priority == 1,
        'annex_vi'       : priority <= 2,
        'source'         : source_label,
        'source_priority': priority,
    }


# ---------------------------------------------------------------------------
# Custom (tedarikçi) DB — küçük, JSON yüklemek sorun değil
# ---------------------------------------------------------------------------

def _load_sea_ek6() -> Dict:
    global _SEA_EK6_DB
    if _SEA_EK6_DB is None:
        with _lock:
            if _SEA_EK6_DB is None:
                try:
                    with open(_SEA_EK6_PATH, encoding='utf-8') as f:
                        _SEA_EK6_DB = json.load(f)
                except Exception:
                    _SEA_EK6_DB = {}
    return _SEA_EK6_DB


def _sea_ek6_lookup(cas: str) -> Optional[dict]:
    db = _load_sea_ek6()
    entry = db.get(cas)
    if entry is None:
        return None
    if '_alias' in entry:
        entry = db.get(entry['_alias'])
    if entry is None or '_alias' in entry:
        return None
    return entry


def _sea_ek6_to_legacy(entry: dict) -> dict:
    """sea_ek6_tr.json formatını API formatına çevirir (Sıra 1 — TR yasal zemin)."""
    cas   = entry.get('cas', '')
    names = _load_names().get(cas, {})
    hazards = []
    for c in entry.get('classification', []):
        h = {'h_class': c.get('class', ''), 'h_code': c.get('h_code', '')}
        if c.get('class_asterisk'):
            h['note_flag'] = '*'
        hazards.append(h)
    return {
        'cas'            : cas,
        'name'           : names.get('en') or entry.get('name_en', ''),
        'name_tr'        : names.get('tr') or (entry.get('names') or [''])[0],
        'ec_no'          : entry.get('ec_no', ''),
        'index_no'       : entry.get('index_no', ''),
        'atp'            : entry.get('atp', 'SEA'),
        'notes'          : entry.get('notes', []),
        'ate'            : entry.get('ate', {}),
        'signal'         : '',
        'pictograms'     : [],
        'hazards'        : hazards,
        'suppl_hazards'  : entry.get('euh_codes', []),
        'm_factors'      : entry.get('m_factors', {}),
        'scl'            : [_scl_op_to_cmin_cmax(s) for s in entry.get('scl_limits', [])],
        'euh_codes'      : entry.get('euh_codes', []),
        'sea_ek6'        : True,
        'annex_vi'       : False,
        'source'         : 'SEA Ek-6 (TR)',
        'source_priority': 1,
    }


def _load_names() -> Dict:
    global _NAMES_DB
    if _NAMES_DB is None:
        with _lock:
            if _NAMES_DB is None:
                try:
                    with open(_NAMES_PATH, encoding='utf-8') as f:
                        _NAMES_DB = json.load(f)
                except Exception:
                    _NAMES_DB = {}
    return _NAMES_DB


def get_name(cas: str, lang: str = 'en') -> Optional[str]:
    """CAS için istenen dilde isim döndür. Bulamazsa None."""
    return _load_names().get(cas.strip(), {}).get(lang)


def _load_substance_db() -> Dict:
    global _SUBSTANCE_DB
    if _SUBSTANCE_DB is None:
        with _lock:
            if _SUBSTANCE_DB is None:
                try:
                    with open(_DB_PATH, encoding='utf-8') as f:
                        _SUBSTANCE_DB = json.load(f)
                except Exception:
                    _SUBSTANCE_DB = {}
    return _SUBSTANCE_DB



def _scl_op_to_cmin_cmax(scl: dict) -> dict:
    """op/min/max formatını eski c_min/c_max formatına çevirir (motor uyumu)."""
    op   = scl.get('op', '')
    vmin = scl.get('min')
    vmax = scl.get('max')
    if op == 'range':
        c_min, c_max = vmin, vmax
    elif op == '>=':
        c_min, c_max = vmin, None
    elif op == '<':
        c_min, c_max = None, vmax
    else:
        c_min, c_max = vmin, vmax
    return {
        'h_code' : scl.get('h_code', ''),
        'h_class': scl.get('class', ''),
        'c_min'  : c_min,
        'c_max'  : c_max,
    }


def _db_to_legacy(entry: dict) -> dict:
    """
    substance_db.json formatını eski API formatına çevirir.
    classification listesi → hazards; scl_limits op/min/max → c_min/c_max.
    """
    hazards = []
    for c in entry.get('classification', []):
        h = {'h_class': c.get('class', ''), 'h_code': c.get('h_code', '')}
        if c.get('class_asterisk'):
            h['note_flag'] = '*'
        hazards.append(h)

    cas = entry.get('cas', '')
    names = _load_names().get(cas, {})
    return {
        'cas'            : cas,
        'name'           : names.get('en') or (entry.get('names') or [''])[0],
        'name_tr'        : names.get('tr', ''),
        'ec_no'          : entry.get('ec_no', ''),
        'index_no'       : entry.get('index_no', ''),
        'atp'            : entry.get('atp', ''),
        'notes'          : entry.get('notes', []),
        'ate'            : entry.get('ate', {}),
        'signal'         : '',
        'pictograms'     : [],
        'hazards'        : hazards,
        'suppl_hazards'  : entry.get('euh_codes', []),
        'm_factors'      : entry.get('m_factors', {}),
        'scl'            : [_scl_op_to_cmin_cmax(s) for s in entry.get('scl_limits', [])],
        'sea_ek6'        : False,
        'annex_vi'       : True,
        'source'         : f'ECHA ATP22 ({entry.get("atp","?")})',
        'source_priority': 2,
    }


def _db_lookup(cas: str) -> Optional[dict]:
    """substance_db.json'dan CAS veya alias ile ara."""
    db = _load_substance_db()
    entry = db.get(cas)
    if entry is None:
        return None
    if '_alias' in entry:
        entry = db.get(entry['_alias'])
    if entry is None or '_alias' in entry:
        return None
    return entry


def _load_custom() -> Dict:
    global _CUSTOM_DB
    if _CUSTOM_DB is None:
        with _lock:
            if _CUSTOM_DB is None:
                try:
                    with open(_CUSTOM_PATH, encoding='utf-8') as f:
                        _CUSTOM_DB = json.load(f)
                except Exception:
                    _CUSTOM_DB = {}
    return _CUSTOM_DB


def _load_oel() -> Dict:
    global _OEL_DB
    if _OEL_DB is None:
        with _lock:
            if _OEL_DB is None:
                try:
                    with open(_OEL_PATH, encoding='utf-8') as f:
                        _OEL_DB = json.load(f)
                except Exception:
                    _OEL_DB = {}
    return _OEL_DB


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def lookup_substance(cas: str) -> Optional[Dict]:
    """
    CAS numarasına göre madde bilgisi döndür.

    Hiyerarşi:
      1. data/cl/       — TR SEA Ek-6 (yasal zemin, mutlak)
      2. data/annex6/   — CLP Annex VI statik arşiv (bilimsel rehber)
         → Merge: TR Ek-6 + Annex VI varsa, TR Ek-6 temel; Annex VI eksik sınıfları ek
      3. data/echa_cl/  — ECHA C&L API önbelleği (önceki canlı çekimler)
      4. data/pubchem_cl/ — PubChem önbelleği (önceki canlı çekimler)
      [5-7: canlı API çekimleri main.py'de yapılır ve buraya kaydedilir]
    """
    cas = cas.strip()

    # ── Sıra 1: SEA Ek-6 TR (yasal zemin, mutlak öncelik) ───────────────────
    tr_entry = _sea_ek6_lookup(cas)
    if tr_entry:
        result   = _sea_ek6_to_legacy(tr_entry)
        # EN/EU veritabanından eksik tehlike sınıflarını ekle
        db_entry = _db_lookup(cas)
        if db_entry:
            db_result   = _db_to_legacy(db_entry)
            supplements = _merge_annex_supplements(result['hazards'], db_result['hazards'])
            if supplements:
                result['hazards'] = result['hazards'] + supplements
                result['source']  = f'SEA Ek-6 (TR) + ECHA ATP22 ek ({len(supplements)} tehlike sınıfı)'
            # suppl_hazards (EUH kodları) — SEA boşsa ATP22'den tamamla
            if not result.get('suppl_hazards') and db_result.get('suppl_hazards'):
                result['suppl_hazards'] = db_result['suppl_hazards']
            # M faktörü — daha yüksek (daha zararlı) olanı kullan
            db_mf = db_result.get('m_factors') or {}
            if db_mf:
                tr_mf = result.get('m_factors') or {}
                merged_mf = dict(tr_mf)
                for key, val in db_mf.items():
                    if val and (not merged_mf.get(key) or val > merged_mf[key]):
                        merged_mf[key] = val
                result['m_factors'] = merged_mf
        return result

    # ── Sıra 2 (tek başına): substance_db (ECHA ATP22 yeni format) ──────────
    db_entry = _db_lookup(cas)
    if db_entry and db_entry.get('classification'):
        return _db_to_legacy(db_entry)

    # ── Sıra 3: ECHA C&L API önbelleği ──────────────────────────────────────
    echa_entry = _read_cl_file(_ECHA_CL_DIR, cas)
    if echa_entry:
        return _cl_to_legacy(echa_entry, 3, f'ECHA C&L ({echa_entry.get("atp","?")})')

    # ── Sıra 4: PubChem önbelleği ────────────────────────────────────────────
    pub_entry = _read_cl_file(_PUBCHEM_DIR, cas)
    if pub_entry:
        return _cl_to_legacy(pub_entry, 4, f'PubChem ({pub_entry.get("atp","?")})')

    # ── Sıra 5: Custom (tedarikçi/kullanıcı) ─────────────────────────────────
    custom = _load_custom()
    c = custom.get(cas)
    if c:
        e = dict(c)
        e.setdefault('sea_ek6', False)
        e.setdefault('annex_vi', False)
        e.setdefault('source', 'Tedarikçi/Kullanıcı Girişi')
        e['source_priority'] = 5
        return e

    return None


def search_substances(query: str, limit: int = 20) -> list:
    """
    İsim veya CAS'a göre madde arama.
    cl/ klasöründeki dosyaları tarar — sadece dosya adları (CAS) kontrol edilir,
    isim araması için CAS eşleşmesi + açık dosya okuma yapılır.
    """
    q = query.strip().lower()
    if len(q) < 2:
        return []

    results = []

    # sea_ek6_tr ve substance_db'yi tara
    sea_db = _load_sea_ek6()
    sub_db = _load_substance_db()
    for db_dict, priority, src in [
        (sea_db, 1, 'SEA Ek-6'),
        (sub_db, 2, 'ECHA ATP22'),
    ]:
        for cas, entry in db_dict.items():
            if '_alias' in entry:
                continue
            names = entry.get('names', [])
            names_clean = [n.lower().rstrip('; ').strip() for n in names]
            cas_l = cas.lower()
            if q in cas_l or q in ' '.join(names).lower():
                r = _build_search_result(cas, entry, priority, src)
                # Tam eşleşme = 0, CAS eşleşmesi = 0, alt dize = 1
                exact = (q == cas_l) or any(q == nc for nc in names_clean)
                r['_mscore'] = 0 if exact else 1
                results.append(r)

    # Custom'a da bak
    for cas, data in _load_custom().items():
        name = (data.get('name') or '').lower()
        if q in cas.lower() or q in name:
            r = {
                'cas': cas, 'name': data.get('name', ''),
                'ec_no': data.get('ec_no', ''),
                'sea_ek6': False, 'annex_vi': False,
                'source': 'Tedarikçi/Kullanıcı Girişi',
                'source_priority': 4,
                'hazard_count': len(data.get('hazards', [])),
                'h_codes': [h['h_code'] for h in data.get('hazards', []) if h.get('h_code')],
            }
            r['_mscore'] = 0 if q == name.rstrip('; ').strip() else 1
            results.append(r)

    results.sort(key=lambda x: (x.get('_mscore', 1), x['source_priority'], x['name'].lower()))
    return results[:limit]


def _build_search_result(cas: str, entry: dict, priority: int, src: str) -> dict:
    cl = entry.get('classification', {})
    lb = entry.get('labelling', {})
    # sea_ek6_tr: classification list içinde {h_code, class} dict'leri
    # substance_db/ECHA: classification dict içinde 'hazards' listesi
    if isinstance(cl, list):
        h_codes = [c.get('h_code', '') for c in cl if isinstance(c, dict) and c.get('h_code')]
    else:
        h_codes = lb.get('h_codes', [cl_h.get('h_code', '') for cl_h in cl.get('hazards', [])])
    # sea_ek6_tr 'names' listesi kullanır, substance_db 'name' string kullanır
    name = (entry.get('names') or [entry.get('name', '')])[0]
    return {
        'cas'            : cas,
        'name'           : name,
        'ec_no'          : entry.get('ec_no', ''),
        'sea_ek6'        : priority == 1,
        'annex_vi'       : priority <= 2,
        'source'         : src,
        'source_priority': priority,
        'hazard_count'   : len(h_codes),
        'h_codes'        : [c for c in h_codes if c],
    }


def _save_api_result(directory: str, cas: str, api_result: dict, source_label: str) -> bool:
    """
    API sonucunu per-dosya formatında belirtilen dizine kaydet.
    api_result: {name, ec_no, hazard_classes, h_codes, signal, pictograms, m_factors, ...}
    """
    prefix    = cas[:2]
    dir_path  = os.path.join(directory, prefix)
    os.makedirs(dir_path, exist_ok=True)
    file_path = os.path.join(dir_path, f'{cas}.json')

    hazard_classes = api_result.get('hazard_classes', [])
    h_codes        = api_result.get('h_codes', [])

    entry = {
        'cas'      : cas,
        'name'     : api_result.get('name', ''),
        'name_tr'  : '',
        'ec_no'    : api_result.get('ec_no', ''),
        'index_no' : '',
        'atp'      : source_label,
        'notes'    : [],
        'classification': {
            'hazards': [
                {'class': cls, 'h_code': code}
                for cls, code in zip(hazard_classes, h_codes)
            ],
            'm_factors' : api_result.get('m_factors', {}),
            'scl_limits': [],
        },
        'labelling': {
            'signal'    : api_result.get('signal', ''),
            'pictograms': api_result.get('pictograms', []),
            'h_codes'   : h_codes,
            'suppl_h'   : [],
        },
    }
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(entry, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def save_echa_cl_substance(cas: str, echa_result: dict) -> bool:
    """ECHA C&L API sonucunu data/echa_cl/'a kaydet (sıra 3 önbelleği)."""
    return _save_api_result(_ECHA_CL_DIR, cas, echa_result, 'ECHA C&L API')


def save_pubchem_substance(cas: str, pubchem_result: dict) -> bool:
    """PubChem sonucunu data/pubchem_cl/'a kaydet (sıra 4 önbelleği)."""
    return _save_api_result(_PUBCHEM_DIR, cas, pubchem_result, 'PubChem')


def save_custom_substance(cas: str, entry: Dict) -> bool:
    """Tedarikçi/kullanıcı maddesini substances_custom.json'a kaydet."""
    global _CUSTOM_DB
    with _lock:
        custom = _load_custom()
        is_new = cas not in custom
        entry['annex_vi']        = False
        entry['sea_ek6']         = False
        entry['source_priority'] = 4
        entry.setdefault('atp', 'custom')
        custom[cas] = entry
        with open(_CUSTOM_PATH, 'w', encoding='utf-8') as f:
            json.dump(custom, f, ensure_ascii=False, indent=2)
        _CUSTOM_DB = custom
    return is_new


def is_annex_vi(cas: str) -> bool:
    """Madde SEA Ek-6 veya ECHA ATP22'de mi?"""
    cas = cas.strip()
    return cas in _load_sea_ek6() or cas in _load_substance_db()


def is_sea_ek6(cas: str) -> bool:
    """Madde SEA Ek-6'da mı?"""
    cas = cas.strip()
    return cas in _load_sea_ek6()


def get_oel(cas: str) -> Optional[Dict]:
    """TR OEL limitlerini döndür."""
    return _load_oel().get(cas.strip())


def get_substance_count() -> int:
    """Tüm kaynaklardaki toplam madde sayısı."""
    sea = sum(1 for v in _load_sea_ek6().values() if '_alias' not in v)
    sub = sum(1 for v in _load_substance_db().values() if '_alias' not in v)
    api_count = 0
    for d in [_ECHA_CL_DIR, _PUBCHEM_DIR]:
        if os.path.isdir(d):
            for sub_dir in os.listdir(d):
                sub_path = os.path.join(d, sub_dir)
                if os.path.isdir(sub_path):
                    api_count += sum(1 for f in os.listdir(sub_path) if f.endswith('.json'))
    return sea + sub + api_count + len(_load_custom())


def get_custom_count() -> int:
    return len(_load_custom())


def get_oel_count() -> int:
    return len(_load_oel())


# ---------------------------------------------------------------------------
# Yeni API — motorlar doğrudan bu fonksiyonları çağırır
# ---------------------------------------------------------------------------

def scl_category(cas: str, h_code: str, conc: float) -> Optional[str]:
    """
    Verilen CAS + H-kodu + konsantrasyon için SCL kategorisini döndür.
    Örn: scl_category('1310-73-2', 'H314', 3.0) → 'Skin Corr. 1B'
    Eşleşme yoksa None.
    """
    entry = _db_lookup(cas)
    if not entry:
        return None
    for scl in entry.get('scl_limits', []):
        if scl.get('h_code') != h_code:
            continue
        op   = scl.get('op', '')
        vmin = scl.get('min')
        vmax = scl.get('max')
        if op == '>=' and vmin is not None and conc >= vmin:
            return scl.get('class')
        if op == 'range' and vmin is not None and vmax is not None:
            if vmin <= conc < vmax:
                return scl.get('class')
        if op == '<' and vmax is not None and conc < vmax:
            return scl.get('class')
    return None


