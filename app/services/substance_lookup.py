"""
Substance Lookup Service
========================
Üç Katmanlı Arama Hiyerarşisi — listeler birbirine GIRMEZ:

  Katman 1 — data/sea_ek6_tr.json      SEA Ek-6 TR (yasal zemin, mutlak öncelik)
               kaynak: 'SEA_EK6_TR'
  Katman 2 — data/substance_db.json    CLP Annex VI / ECHA ATP22
               kaynak: 'CLP_ANNEX_VI_ATP22'  |  tr_yasal_onay_durumu: 'doğrulanmadı'
  Katman 3 — data/echa_cl/ / pubchem_cl/   ECHA C&L API / PubChem önbelleği
               kaynak: 'ECHA_API'           |  tr_yasal_onay_durumu: 'doğrulanmadı'
  +Custom  — substances_custom.json    Tedarikçi/kullanıcı girişi

Her katman içinde arama sırası: CAS → EC No → Index No
Not B maddeleri (CAS boş): EC No ile yakalanır.

Yardımcı veriler:
  data/substance_names.json          CAS → {en, tr} çok dilli isimler
"""
import json, os, threading, re, time
from datetime import datetime, timezone
from typing import Optional, Dict

_BASE          = os.path.join(os.path.dirname(__file__), '..', '..', 'data')
_ECHA_CL_DIR   = os.path.join(_BASE, 'echa_cl')       # ECHA C&L API önbelleği
_PUBCHEM_DIR   = os.path.join(_BASE, 'pubchem_cl')    # PubChem önbelleği
_CUSTOM_PATH   = os.path.join(_BASE, 'substances_custom.json')
_OEL_PATH      = os.path.join(_BASE, 'tr_oel_limits.json')
_DB_PATH       = os.path.join(_BASE, 'substance_db.json')    # ECHA ATP22 (EN)
_NAMES_PATH    = os.path.join(_BASE, 'substance_names.json')  # CAS → {en, tr, ...}
_SEA_EK6_PATH  = os.path.join(_BASE, 'sea_ek6_tr.json')      # SEA Ek-6 (TR, Sıra 1)

_CUSTOM_DB:       Optional[Dict] = None
_OEL_DB:          Optional[Dict] = None
_SUBSTANCE_DB:    Optional[Dict] = None
_NAMES_DB:        Optional[Dict] = None
_SEA_EK6_DB:      Optional[Dict] = None
_SEA_EK6_BY_EC:   Optional[Dict] = None  # EC No → CAS ters indeksi
_SEA_EK6_BY_IDX:  Optional[Dict] = None  # Index No → CAS ters indeksi
_TR_NAME_BY_EC:   Optional[Dict] = None  # EC No → Türkçe ad (Katman 2/3 tamamlama)
_TR_NAME_BY_IDX:  Optional[Dict] = None  # Index No → Türkçe ad (Katman 2/3 tamamlama)
_DB_BY_EC:        Optional[Dict] = None  # EC No → CAS ters indeksi (substance_db)
_DB_BY_IDX:       Optional[Dict] = None  # Index No → CAS ters indeksi (substance_db)
_lock = threading.Lock()

# ---------------------------------------------------------------------------
# Türkçe → İngilizce h_class normalizer
# sea_ek6_tr.json'daki Türkçe sınıf adlarını CLP/clp_service'in beklediği
# İngilizce kanonik isimlere çevirir. Regex tabanlı — yazım varyasyonlarını
# (nokta, boşluk farkları, kısaltma değişimleri) hepsini yakalar.
# ---------------------------------------------------------------------------
def _normalize_hclass(raw: str) -> str:
    """
    Türkçe veya tutarsız CLP sınıf adını kanonik İngilizce forma çevirir.
    Bilinmeyenler olduğu gibi döner.
    """
    s = raw.strip().replace(' ', ' ')
    # Boşluk/nokta normalizasyonu: "Akut Tok.2" → "Akut Tok. 2"
    s = re.sub(r'\.\s*(\d)', r'. \1', s)
    s = re.sub(r'\s+', ' ', s).strip()

    # Kategori numarasını sona al
    _cat = re.search(r'(\d+\w*)$', s)
    cat = ' ' + _cat.group(1) if _cat else ''
    base = s[:_cat.start()].strip() if _cat else s

    b = base.upper()

    # Akut toksisite
    if re.match(r'AKUT\s*TOK', b):
        return f'Acute Tox.{cat}'

    # Cilt aşındırıcı
    if re.match(r'CILT\s*A[ŞS]', b):
        return f'Skin Corr.{cat}'

    # Cilt tahrişi
    if re.match(r'CILT\s*(TAH|THR)', b):
        return f'Skin Irrit.{cat}'

    # Cilt hassasiyeti
    if re.match(r'CILT\s*HASSAS', b):
        return f'Skin Sens.{cat}'

    # Göz hasarı
    if re.match(r'G[ÖO]Z\s*(HASAR|HSR)', b):
        return f'Eye Dam.{cat}'

    # Göz tahrişi
    if re.match(r'G[ÖO]Z\s*(TAH|THR)', b):
        return f'Eye Irrit.{cat}'

    # Solunum hassasiyeti
    if re.match(r'SOLNM\s*HASSAS', b):
        return f'Resp. Sens.{cat}'

    # BHOT Tekrarlanan Maruziyet (STOT RE) — önce kontrol et (TEKR, TEKRAr, TEKRarlı)
    if re.match(r'BHOT\s*TEKR', b):
        return f'STOT RE{cat}'

    # BHOT Tek Maruziyet (STOT SE)
    if re.match(r'BHOT\s*TEK', b):
        return f'STOT SE{cat}'

    # Kanserojen
    if re.match(r'KANS', b):
        return f'Carc.{cat}'

    # Mutajen
    if re.match(r'MUTA', b):
        return f'Muta.{cat}'

    # Üreme toksisitesi — "Örm. Sis. Tok." / "Üreme"
    if re.match(r'([ÜU]REM|[ÖO]RM)', b):
        return f'Repr.{cat}'

    # Sucul akut
    if re.match(r'SUCUL\s*AKUT', b):
        return f'Aquatic Acute{cat}'

    # Sucul kronik
    if re.match(r'SUCUL\s*KRON', b):
        return f'Aquatic Chronic{cat}'

    # Alevlenir sıvı
    if re.match(r'ALEV[^G]*(SIV|SÜV|SIV)', b) or re.match(r'ALEV\.\s*SIV', b) or 'SIV' in b and 'ALEV' in b:
        return f'Flam. Liq.{cat}'

    # Alevlenir katı
    if re.match(r'ALEV.*KAT', b):
        return f'Flam. Sol.{cat}'

    # Alevlenir gaz
    if re.match(r'ALEV.*GAZ', b):
        return f'Flam. Gas{cat}'

    # Aspirasyon toksisitesi
    if re.match(r'ASP', b):
        return f'Asp. Tox.{cat}'

    # Metal aşındırıcı
    if re.match(r'MET', b):
        return f'Met. Corr.{cat}'

    # Basınçlı gaz
    if re.match(r'BAS[Iİ]N', b):
        return 'Press. Gas'

    # Oksitleyici gaz/sıvı/katı
    if re.match(r'OKSIT.*GAZ', b):
        return f'Ox. Gas{cat}'
    if re.match(r'OKSIT.*SIV', b):
        return f'Ox. Liq.{cat}'
    if re.match(r'OKSIT.*KAT', b):
        return f'Ox. Sol.{cat}'

    # Organik peroksit
    if re.match(r'ORG.*PEROKS', b):
        return f'Org. Perox.{cat}'

    # Patlayıcı
    if re.match(r'PAT', b) and 'KARS' not in b:
        return f'Explos.{cat}'

    # Pirofori
    if re.match(r'PIRO', b):
        return f'Pyr.{cat}'

    # Kendiliğinden ısınan
    if re.match(r'KEND.*ISIN', b):
        return f'Self-heat.{cat}'

    # Su ile tepkimeye giren
    if re.match(r'SU[-\s]*TEPK', b):
        return f'Water-react.{cat}'

    # Ozon
    if re.match(r'OZON', b):
        return f'Ozone{cat}'

    # Karsiyojenik patlamaz
    if re.match(r'KAR.*PAT', b):
        return 'Explos. (unstable)'

    return raw  # bilinmeyen — değiştirme


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
        d = {'h_class': _normalize_hclass(h.get('class', '')), 'h_code': h.get('h_code', '')}
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
                'h_class': _normalize_hclass(s.get('class', '')),
                'c_min'  : s.get('c_min'),
                'c_max'  : s.get('c_max'),
            }
            for s in cl.get('scl_limits', [])
        ],
        'sea_ek6'              : priority == 1,
        'annex_vi'             : priority <= 2,
        'source'               : source_label,
        'source_priority'      : priority,
        'kaynak'               : 'ECHA_API',
        'tr_yasal_onay_durumu' : 'doğrulanmadı',
    }


# ---------------------------------------------------------------------------
# Custom (tedarikçi) DB — küçük, JSON yüklemek sorun değil
# ---------------------------------------------------------------------------

def _load_sea_ek6() -> Dict:
    global _SEA_EK6_DB, _SEA_EK6_BY_EC, _SEA_EK6_BY_IDX, _TR_NAME_BY_EC, _TR_NAME_BY_IDX
    if _SEA_EK6_DB is None:
        with _lock:
            if _SEA_EK6_DB is None:
                try:
                    with open(_SEA_EK6_PATH, encoding='utf-8') as f:
                        _SEA_EK6_DB = json.load(f)
                except Exception:
                    _SEA_EK6_DB = {}
                by_ec: Dict = {}
                by_idx: Dict = {}
                tr_by_ec: Dict = {}
                tr_by_idx: Dict = {}
                for cas_key, entry in _SEA_EK6_DB.items():
                    if '_alias' in entry:
                        continue
                    ec  = entry.get('ec_no', '').strip()
                    idx = entry.get('index_no', '').strip()
                    tr_name = (entry.get('names') or [''])[0]
                    if ec:
                        if ec not in by_ec:
                            by_ec[ec] = cas_key
                        if ec not in tr_by_ec and tr_name:
                            tr_by_ec[ec] = tr_name
                    if idx:
                        if idx not in by_idx:
                            by_idx[idx] = cas_key
                        if idx not in tr_by_idx and tr_name:
                            tr_by_idx[idx] = tr_name
                _SEA_EK6_BY_EC  = by_ec
                _SEA_EK6_BY_IDX = by_idx
                _TR_NAME_BY_EC  = tr_by_ec
                _TR_NAME_BY_IDX = tr_by_idx
    return _SEA_EK6_DB


# SEA Ek-6'da yer almayan (Türkçe adı resmî listede bulunmayan) yaygın maddeler — GBF Türkçe
# yazılır; Ek-6 adı varsa her zaman o kullanılır, bu liste yalnızca boşluğu doldurur.
import re as _re_clean


def clean_tr_name(name: str) -> str:
    """SEA Ek-6 Not B adlarındaki doldurulacak konsantrasyon kalıbını temizler:
    "nitrik asit ... %" → "nitrik asit"; "fosforik asit ... %, ortofosforik asit ... %" → "fosforik asit"
    (eşanlamlı tekrar atılır); "…, aktif Cl % ..... çözeltisi" → "…, aktif Cl çözeltisi"."""
    if not name:
        return name
    s = str(name)
    if _re_clean.search(r'(\.{3}|…)\s*%', s):
        parts = [p.strip(' ,;') for p in _re_clean.split(r'(?:\.{3}|…)\s*%', s)]
        parts = [p for p in parts if p]
        return parts[0] if parts else s.strip()
    s = _re_clean.sub(r'\s*%\s*(?:\.{2,}|…)\s*', ' ', s)
    return _re_clean.sub(r'\s{2,}', ' ', s).strip()


COMMON_NAMES_TR = {
    '7732-18-5':  'su',
    '77-92-9':    'sitrik asit',
    '5949-29-1':  'sitrik asit monohidrat',
    '6915-15-7':  'malik asit',
    '87-69-4':    'tartarik asit',
    '124-04-9':   'adipik asit',
    '110-17-8':   'fumarik asit',
    '144-55-8':   'sodyum hidrojen karbonat',
    '7757-82-6':  'sodyum sülfat',
    '56-81-5':    'gliserol',
    '57-55-6':    'propilen glikol',
    '68213-23-0': 'alkoller, C12-18, etoksillenmiş',
    '68439-46-3': 'alkoller, C9-11, etoksillenmiş',
    '68131-39-5': 'alkoller, C12-15, etoksillenmiş',
    '68439-50-9': 'alkoller, C12-14, etoksillenmiş',
    # gazlar
    '7727-37-9':  'azot',
    '124-38-9':   'karbondioksit',
    '7440-37-1':  'argon',
    '7440-59-7':  'helyum',
    '7440-01-9':  'neon',
    '7439-90-9':  'kripton',
    '7440-63-3':  'ksenon',
    '2551-62-4':  'kükürt hekzaflorür',
    '10024-97-2': 'diazot monoksit',
}


def _fill_tr_name(result: dict) -> dict:
    """Katman 2/3 sonucunda name_tr boşsa SEA Ek-6 sözlüğünden, o da yoksa yaygın adlar
    listesinden tamamla."""
    if result.get('name_tr'):
        return result
    _common = COMMON_NAMES_TR.get(str(result.get('cas') or result.get('cas_no') or '').strip())
    _load_sea_ek6()  # indeksler yüklü olsun
    ec  = result.get('ec_no', '').strip()
    idx = result.get('index_no', '').strip()
    tr  = ''
    if ec and _TR_NAME_BY_EC:
        tr = _TR_NAME_BY_EC.get(ec, '')
    if not tr and idx and _TR_NAME_BY_IDX:
        tr = _TR_NAME_BY_IDX.get(idx, '')
    if tr or _common:
        result['name_tr'] = tr or _common
    return result


def _sea_ek6_lookup(cas: str = '', ec_no: str = '', index_no: str = '') -> Optional[dict]:
    """SEA Ek-6'da CAS, EC No veya Index No ile ara (öncelik sırası: CAS > EC No > Index No)."""
    db = _load_sea_ek6()
    # CAS ile ara
    if cas:
        entry = db.get(cas)
        if entry is not None:
            if '_alias' in entry:
                entry = db.get(entry['_alias'])
            if entry and '_alias' not in entry:
                return entry
    # EC No ile ara
    if ec_no and _SEA_EK6_BY_EC:
        cas_key = _SEA_EK6_BY_EC.get(ec_no.strip())
        if cas_key:
            entry = db.get(cas_key)
            if entry and '_alias' not in entry:
                return entry
    # Index No ile ara
    if index_no and _SEA_EK6_BY_IDX:
        cas_key = _SEA_EK6_BY_IDX.get(index_no.strip())
        if cas_key:
            entry = db.get(cas_key)
            if entry and '_alias' not in entry:
                return entry
    return None


def _ek6_split_members(name: str) -> dict:
    """Ek-6 grup girişi adını üyelerine ayırır: "a; b; [1] c; d; [2]" → {1: "a; b", 2: "c; d"}."""
    parts = _re_clean.split(r'\[(\d+)\]', str(name or ''))
    out = {}
    for i in range(1, len(parts), 2):
        txt = parts[i - 1].strip(' ;,')
        if txt:
            out[int(parts[i])] = txt
    return out


def _ek6_member(result: dict, entry: dict, cas: str) -> None:
    """SEA Md.20(2)(a): Ek-6'da birden çok maddeyi kapsayan grup girişlerinde ([1], [2] … işaretli) etikette ve
    GBF'de o maddenin kendi adı kullanılır — önceden grubun tüm adları basılıyordu (örn. d-limonen için 5 ad).
    Üye sırası: girişteki CAS listesi (cas + synonyms) Ek-6'daki [n] sırasıyla aynıdır; sayılar tutmazsa
    hiçbir şey değiştirilmez."""
    try:
        cas_list = [entry.get('cas', '')] + [x for x in (entry.get('synonyms') or [])
                                             if _re_clean.fullmatch(r'\d{2,7}-\d{2}-\d', str(x))]
        if cas not in cas_list:
            return
        n = cas_list.index(cas) + 1
        tr = _ek6_split_members((entry.get('names') or [''])[0])
        en = _ek6_split_members(entry.get('name_en', ''))
        if len(tr) != len(cas_list) or n not in tr:
            return
        result['name_tr'] = tr[n]
        if len(en) == len(cas_list) and n in en:
            result['name'] = en[n]
        ecs = entry.get('ec_list') or []
        if len(ecs) == len(cas_list):
            result['ec_no'] = ecs[n - 1]
        result['ek6_group_member'] = n
    except Exception:
        pass


def _sea_ek6_to_legacy(entry: dict) -> dict:
    """sea_ek6_tr.json formatını API formatına çevirir (Sıra 1 — TR yasal zemin)."""
    cas   = entry.get('cas', '')
    names = _load_names().get(cas, {})
    hazards = []
    for c in entry.get('classification', []):
        raw_class = c.get('class', '')
        h = {
            'h_class':    c.get('class_en') or _normalize_hclass(raw_class),  # İngilizce kanonik ad
            'h_class_tr': raw_class,                      # Türkçe orijinal (görüntü için)
            'h_code':     c.get('h_code', ''),
        }
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
        'euh_limits'     : entry.get('euh_limits', []),
        'sea_ek6'        : True,
        'annex_vi'       : False,
        'source'         : 'SEA Ek-6 (TR)',
        'source_priority': 1,
        'kaynak'         : 'SEA_EK6_TR',
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




def _load_substance_db() -> Dict:
    global _SUBSTANCE_DB, _DB_BY_EC, _DB_BY_IDX
    if _SUBSTANCE_DB is None:
        with _lock:
            if _SUBSTANCE_DB is None:
                try:
                    with open(_DB_PATH, encoding='utf-8') as f:
                        _SUBSTANCE_DB = json.load(f)
                except Exception:
                    _SUBSTANCE_DB = {}
                by_ec: Dict = {}
                by_idx: Dict = {}
                for cas_key, entry in _SUBSTANCE_DB.items():
                    if '_alias' in entry:
                        continue
                    # ec_no_list varsa tüm EC No'ları indeksle
                    ec_list = entry.get('ec_no_list') or ([entry['ec_no']] if entry.get('ec_no') else [])
                    for ec in ec_list:
                        ec = ec.strip()
                        if ec and ec not in by_ec:
                            by_ec[ec] = cas_key
                    idx = entry.get('index_no', '').strip()
                    if idx and idx not in by_idx:
                        by_idx[idx] = cas_key
                _DB_BY_EC  = by_ec
                _DB_BY_IDX = by_idx
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
        'h_class': scl.get('class_en') or _normalize_hclass(scl.get('class', '')),
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
        h = {'h_class': _normalize_hclass(c.get('class', '')), 'h_code': c.get('h_code', '')}
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
        'sea_ek6'              : False,
        'annex_vi'             : True,
        'source'               : f'ECHA ATP22 ({entry.get("atp","?")})',
        'source_priority'      : 2,
        'kaynak'               : 'CLP_ANNEX_VI_ATP22',
        'tr_yasal_onay_durumu' : 'doğrulanmadı',
    }


def _db_lookup(cas: str = '', ec_no: str = '', index_no: str = '') -> Optional[dict]:
    """substance_db.json'dan CAS, EC No veya Index No ile ara."""
    db = _load_substance_db()
    # CAS ile ara
    if cas:
        entry = db.get(cas)
        if entry is not None:
            if '_alias' in entry:
                entry = db.get(entry['_alias'])
            if entry and '_alias' not in entry:
                return entry
    # EC No ile ara
    if ec_no and _DB_BY_EC:
        cas_key = _DB_BY_EC.get(ec_no.strip())
        if cas_key:
            entry = db.get(cas_key)
            if entry and '_alias' not in entry:
                return entry
    # Index No ile ara
    if index_no and _DB_BY_IDX:
        cas_key = _DB_BY_IDX.get(index_no.strip())
        if cas_key:
            entry = db.get(cas_key)
            if entry and '_alias' not in entry:
                return entry
    return None


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

# Not B maddeleri: sea_ek6_tr.json'da form='gas' olan entry'lerden dinamik oluşur.
# Sıvı formda CAS+'-AQ' kaydına yönlendirir; JSON'a yeni çift eklenmesi yeterli.
def _build_note_b_cas() -> set:
    try:
        with open(_SEA_EK6_PATH, encoding='utf-8') as _f:
            _db = json.load(_f)
        return {
            entry['cas']
            for key, entry in _db.items()
            if (entry.get('note_b_pair') or entry.get('form') == 'gas') and entry.get('cas')
        }
    except Exception:
        return {'7647-01-0'}  # fallback

_NOTE_B_CAS: set = _build_note_b_cas()

_LIQUID_FORM_KEYWORDS = frozenset({
    'liquid', 'solution', 'aqueous', 'sıvı', 'çözelti',
    'concentrate', 'konsantre', 'emulsion', 'suspension',
})

def _is_liquid(form: str) -> bool:
    if not form:
        return False
    f = form.lower().strip()
    return any(kw in f for kw in _LIQUID_FORM_KEYWORDS)


def lookup_substance(cas: str, form: str = '',
                     ec_no: str = '', index_no: str = '') -> Optional[Dict]:
    """
    Madde bilgisi döndür. Üç katmanlı arama — listeler birbirine GIRMEZ.

    Katman 1 — SEA Ek-6 TR (yasal zemin, mutlak öncelik)
    Katman 2 — CLP Annex VI / substance_db (ECHA ATP22)
    Katman 3 — ECHA C&L API önbelleği / PubChem önbelleği

    Her katman içinde arama sırası: CAS → EC No → Index No
    Not B maddeleri: sıvı formda CAS+'-AQ' kaydı tercih edilir.
    """
    cas = cas.strip()

    # Not B: sıvı form + bilinen çift-giriş CAS → AQ kaydına yönlendir
    if cas in _NOTE_B_CAS and _is_liquid(form):
        aq_result = _sea_ek6_lookup(cas=cas + '-AQ')
        if aq_result:
            return _sea_ek6_to_legacy(aq_result)

    # ── Katman 1: SEA Ek-6 TR ────────────────────────────────────────────────
    tr_entry = _sea_ek6_lookup(cas=cas, ec_no=ec_no, index_no=index_no)
    if tr_entry:
        result = _sea_ek6_to_legacy(tr_entry)
        _ek6_member(result, tr_entry, cas)
        # Sınıflandırma karışmaz; sadece boş ATE Katman 2'den (AB Ek-VI ATP) tamamlanır — yalnız TR Ek-6
        # kategorisiyle uyumlu değerler (kullanıcı kararı 2026-10-10: "yalnız TR Ek-6")
        if not result.get('ate'):
            db_entry = _db_lookup(cas=result.get('cas',''), ec_no=result.get('ec_no',''),
                                  index_no=result.get('index_no',''))
            if db_entry and db_entry.get('ate'):
                _ate = _ate_ek6_uyumlu(db_entry['ate'], result.get('hazards') or [])
                if _ate:
                    result['ate'] = _ate
        # ECHA C&L öz-sınıflandırmasından ek H-kodları (harmonize edilmemiş tehlikeler)
        try:
            _ek6_kod = {str(h.get('h_code') or '').replace('*', '').strip()[:4].upper() for h in result.get('hazards') or []}
            result = _supplement_from_echa_cl(cas, result)
            # Ek-6 maddesi: kayıt yaptıranın özel sınırı yalnız Ek-6'da olmayan (takviye) sınıflar için (SEA Md.12(3))
            result = _registrant_scl(cas, result, _ek6_kod)
        except Exception as _e:
            print(f'[sea_supplement] {cas}: hata (atlandı) — {_e}')
        return result

    # ── Katman 2: CLP Annex VI / substance_db (ECHA ATP22) ──────────────────
    db_entry = _db_lookup(cas=cas, ec_no=ec_no, index_no=index_no)
    if db_entry and db_entry.get('classification'):
        return _fill_tr_name(_db_to_legacy(db_entry))

    # ── Katman 3: ECHA C&L API önbelleği ────────────────────────────────────
    echa_entry = _read_cl_file(_ECHA_CL_DIR, cas)
    if echa_entry:
        if _is_stale(echa_entry):
            _fetch_echa_background(cas, refresh=True)
        from app.services.echa_service import ECHA_ATTRIBUTION
        return _registrant_scl(cas, _fill_tr_name(_cl_to_legacy(echa_entry, 3, f'ECHA C&L — {ECHA_ATTRIBUTION}')))

    # ── Katman 3b: PubChem önbelleği ─────────────────────────────────────────
    # PubChem tehlike verisi harmonize değil (C&L bildirimi). Sadece fiziksel
    # özellikler alınır; hazards/signal temizlenir.
    pub_entry = _read_cl_file(_PUBCHEM_DIR, cas)
    if pub_entry:
        _fetch_echa_background(cas)   # ECHA verisi henüz yok → arka planda dene
        result = _fill_tr_name(_cl_to_legacy(pub_entry, 4, f'PubChem ({pub_entry.get("atp","?")})')  )
        result['hazards'] = []
        result['signal'] = None
        result['pictograms'] = []
        return result

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
    def _n(t: str) -> str:
        # Türkçe büyük/küçük harf: "İ".lower() → "i̇" (birleşik nokta) — nokta atılır; "I" → "ı"
        return re.sub(r'\s+', ' ', (t or '').replace('I', 'ı').replace('İ', 'i').lower().replace('\u0307', '')).strip()

    def _score(q: str, cas: str, names: list) -> int:
        """Düşük = iyi. 0 CAS ya da ana ad tam; 1 eş anlamlı tam / ana ad bununla başlıyor; 2 eş anlamlı bununla
        başlıyor; 3 tam kelime; 4 alt dize; 9 eşleşme yok. Ana ad: ilk adın ';' öncesi (Ek-6 adları eş anlamlıları
        ';' ile verir — "sodyum hidroksit; kostik soda"); tepkime kütlelerinin içinde geçen ad ana ad sayılmaz."""
        segs = [_n(x) for n in names for x in str(n).split(';') if _n(x)]
        if not segs:
            return 0 if q == cas.lower() else 9
        ana, diger = segs[0], segs[1:]
        if q == cas.lower() or q == ana:
            return 0
        if q in diger or ana.startswith(q) or cas.lower().startswith(q):
            return 1
        if any(x.startswith(q) for x in diger):
            return 2
        if any(re.search(r'(^|[\s,(\-])' + re.escape(q) + r'($|[\s,)\-])', x) for x in segs):
            return 3
        if q in cas.lower() or any(q in x for x in segs):
            return 4
        # Boşluk farkı (Ek-6: "hidrojenperoksit çözeltisi" ↔ "hidrojen peroksit")
        qs = q.replace(' ', '')
        if ana.replace(' ', '').startswith(qs):
            return 1
        if any(qs in x.replace(' ', '') for x in segs):
            return 4
        return 9

    q = _n(query)
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
            names = list(entry.get('names', [])) + [entry.get('name_en', '')] + list(entry.get('synonyms') or [])
            sc = _score(q, cas, [n for n in names if n])
            if sc < 9:
                r = _build_search_result(cas, entry, priority, src)
                r['_mscore'] = sc
                results.append(r)

    # Custom'a da bak
    for cas, data in _load_custom().items():
        name = (data.get('name') or '').lower()
        sc = _score(q, cas, [data.get('name') or '', data.get('name_tr') or ''])
        if sc < 9:
            r = {
                'cas': cas, 'name': data.get('name', ''),
                'ec_no': data.get('ec_no', ''),
                'sea_ek6': False, 'annex_vi': False,
                'source': 'Tedarikçi/Kullanıcı Girişi',
                'source_priority': 4,
                'hazard_count': len(data.get('hazards', [])),
                'h_codes': [h['h_code'] for h in data.get('hazards', []) if h.get('h_code')],
            }
            r['_mscore'] = sc
            results.append(r)

    # Çok dilli ad sözlüğü (TR / EN) — Ek-6 / veritabanı kaydında olmayan adlar için
    try:
        _names = json.load(open(_NAMES_PATH, encoding='utf-8'))
    except Exception:
        _names = {}
    _have = {r['cas'] for r in results}
    for cas, nm in _names.items():
        if cas in _have or not isinstance(nm, dict):
            continue
        sc = _score(q, cas, [nm.get('tr') or '', nm.get('en') or ''])
        if sc < 9:
            results.append({'cas': cas, 'name': nm.get('tr') or nm.get('en') or '', 'ec_no': '',
                            'sea_ek6': False, 'annex_vi': False, 'source': 'Ad sözlüğü', 'source_priority': 3,
                            'hazard_count': None, 'h_codes': [], '_mscore': sc})

    # Aynı CAS bir kez (öncelikli kaynak); kısa ad (genel madde) uzun addan (türev / karışım) önce
    results.sort(key=lambda x: (x.get('_mscore', 9), x['source_priority'], len(x.get('name') or ''), (x.get('name') or '').lower()))
    _seen, _out = set(), []
    for r in results:
        if r['cas'] in _seen:
            continue
        _seen.add(r['cas'])
        _out.append(r)
    results = _out
    return results[:limit]


_ECHA_NAME_CACHE: Dict[str, list] = {}


def echa_name_search(query: str, limit: int = 6) -> list:
    """Yerel veritabanında bulunamayan ad için ECHA madde araması (tek istek, kullanıcının yazdığı ad — toplu çekim
    değil). Yalnız tek CAS numarası taşıyan kayıtlar döner (çok CAS'lı genel kayıtta hangi CAS'ın doğru olduğu belli
    değildir). İngilizce / IUPAC adlarıyla çalışır. Sonuç bellekte tutulur."""
    q = (query or '').strip()
    if len(q) < 4 or not re.search(r'[A-Za-zÇĞİÖŞÜçğıöşü]', q):
        return []
    key = q.lower()
    if key in _ECHA_NAME_CACHE:
        return _ECHA_NAME_CACHE[key]
    out = []
    try:
        import httpx
        r = httpx.get('https://chem.echa.europa.eu/api-substance/v1/substance',
                      params={'pageIndex': 1, 'pageSize': 15, 'searchText': q},
                      headers={'Accept': 'application/json', 'User-Agent': 'Mozilla/5.0 (SDSPass)'}, timeout=8)
        seen = set()
        for it in (r.json().get('items') or []):
            si = it.get('substanceIndex') or {}
            cas = [c for c in (si.get('casNumber') or []) if re.fullmatch(r'\d{2,7}-\d{2}-\d', c or '')]
            if len(cas) != 1 or cas[0] in seen:
                continue
            seen.add(cas[0])
            name = si.get('rmlName') or ''
            out.append({'cas': cas[0], 'name': name, 'ec_no': (si.get('ecNumber') or [''])[0] if isinstance(si.get('ecNumber'), list) else (si.get('ecNumber') or ''),
                        'sea_ek6': False, 'annex_vi': False, 'source': 'ECHA (ad araması)', 'source_priority': 5,
                        'hazard_count': None, 'h_codes': [],
                        '_mscore': 0 if name.lower() == key else 1 if name.lower().startswith(key) else 3})
        out.sort(key=lambda x: (x['_mscore'], len(x['name'])))
        out = out[:limit]
    except Exception as e:
        print(f'[ECHA ad araması] {q}: {e}')
        return []
    _ECHA_NAME_CACHE[key] = out
    return out


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
        'fetched_at': api_result.get('fetched_at') or datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'notes'    : [],
        'ate'      : api_result.get('ate', {}),          # ECHA bildirimlerinden (kategori aralığında)
        'echa_extras': api_result.get('echa_extras', 0),
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
        from app.services.data_store import persist
        persist(file_path)
        return True
    except Exception as e:
        print(f'[CL CACHE] {cas} kayıt hatası ({file_path}): {e}')
        return False


# SEA Ek-1 Tablo 3.1.1 kategori aralıkları (alt sınır hariç, üst sınır dahil) — ATE'nin Ek-6 kategorisine uyumu için
_ATE_ARALIK = {
    'oral':   {1: (0, 5), 2: (5, 50), 3: (50, 300), 4: (300, 2000)},
    'dermal': {1: (0, 50), 2: (50, 200), 3: (200, 1000), 4: (1000, 2000)},
    'vapour': {1: (0, 0.5), 2: (0.5, 2), 3: (2, 10), 4: (10, 20)},
    'dust':   {1: (0, 0.05), 2: (0.05, 0.5), 3: (0.5, 1), 4: (1, 5)},
    'gas':    {1: (0, 100), 2: (100, 500), 3: (500, 2500), 4: (2500, 20000)},
}
_ATE_YOL = {'H300': 'oral', 'H301': 'oral', 'H302': 'oral', 'H310': 'dermal', 'H311': 'dermal', 'H312': 'dermal',
            'H330': 'inhalation', 'H331': 'inhalation', 'H332': 'inhalation'}


def _ate_ek6_uyumlu(ate: dict, hazards: list) -> dict:
    """TR Ek-6'daki maddeye AB Ek-VI (ATP) kaynaklı sayısal ATE: yalnız Ek-6'daki akut toksisite kategorisinin
    aralığına düşen yol değerleri tutulur. Aralık dışı (Ek-6 sınıfından daha ağır) değer atılır — ATEmix'te Ek-6
    kategorisinin dönüşüm değeri (SEA Ek-1 Tablo 3.1.2) kullanılır. SEA Md.6(1)(c): Türkiye'de bağlayıcı olan TR Ek-6;
    yıldızlı (*) asgari sınıf yerine AB'nin daha ağır ATE'si uygulanmaz (örn. perasetik asit TR Ek-6 Akut Tox. 4*,
    AB ATP deri 60 mg/kg → %5'te H312 veriliyordu; Ecolab P3-Oxonia GBF). Kullanıcı kararı 2026-10-10."""
    if not isinstance(ate, dict):
        return {}
    kat = {}
    for h in hazards or []:
        code = str(h.get('h_code') or '').replace('*', '').strip()[:4]
        m = re.search(r'(\d)', str(h.get('h_class') or ''))
        yol = _ATE_YOL.get(code)
        if yol and m and 'Acute' in str(h.get('h_class') or '') or (yol and m and 'Akut' in str(h.get('h_class') or '')):
            kat[yol] = int(m.group(1))
    out = {}
    for k, v in ate.items():
        val = v.get('value') if isinstance(v, dict) else v
        try:
            val = float(val)
        except (TypeError, ValueError):
            continue
        yol = 'inhalation' if k.startswith('inhal') else k
        if yol not in kat:
            continue
        if yol == 'inhalation':
            f = str((v.get('form') if isinstance(v, dict) else '') or '').lower()
            unit = str((v.get('unit') if isinstance(v, dict) else '') or '').lower()
            alt = 'gas' if ('gas' in f or 'ppm' in unit) else 'dust' if any(x in f for x in ('dust', 'mist')) else 'vapour'
        else:
            alt = yol
        lo, hi = _ATE_ARALIK[alt][kat[yol]]
        if lo < val <= hi:
            out[k] = v
    return out


_SCL_AILE = {'H314': 'deri', 'H315': 'deri', 'H318': 'goz', 'H319': 'goz'}


def _aile_ust(codes: set, aile: str):
    """Zararlılık ailesindeki en ağır kod (deri: H314 > H315; göz: H318 > H319, H314 göz hasarını da kapsar)."""
    if aile == 'deri':
        return 'H314' if 'H314' in codes else 'H315' if 'H315' in codes else None
    if aile == 'goz':
        return 'H318' if codes & {'H318', 'H314'} else 'H319' if 'H319' in codes else None
    return aile if aile in codes else None


def _registrant_scl(cas: str, result: dict, ek6_kodlar: set = frozenset()) -> dict:
    """Kayıt yaptıranın ECHA kayıt dosyasındaki (2.1 GHS) özel konsantrasyon sınırları — SEA Md.12(1), 12(5).
    Yalnız: (a) ürünün sınıfıyla aynı ailede ve aynı en ağır kategoride sınıflandırılmışsa (kayıt yaptıran H318 deyip
    sonuç H319 ise sınır alınmaz), (b) o ailede Ek-6 / Ek-VI özel sınırı yoksa, (c) Ek-6'da uyumlaştırılmış sınıf için
    değilse (SEA Md.12(3): uyumlaştırılmış sınıflar için özel sınır belirlenmez). Kullanıcı kararı 2026-10-10."""
    try:
        from app.services import component_phys as _cpx
        gs = (_cpx._read(cas) or {}).get('ghs_self') or {}
    except Exception:
        return result
    scl = gs.get('scl') or []
    if not scl:
        return result
    _c4 = lambda x: str(x or '').replace('*', '').strip()[:4].upper()
    res_kod = {_c4(h.get('h_code')) for h in result.get('hazards') or []}
    reg_kod = {_c4(h.get('h_code')) for h in gs.get('hazards') or []}
    mevcut = {_SCL_AILE.get(_c4(e.get('h_code')), _c4(e.get('h_code'))) for e in result.get('scl') or []}
    ek6_aile = {_SCL_AILE.get(k, k) for k in ek6_kodlar} | ({'goz'} if 'H314' in ek6_kodlar else set())
    ekle = []
    for e in scl:
        kod = _c4(e.get('h_code'))
        aile = _SCL_AILE.get(kod, kod)
        if aile in mevcut or aile in ek6_aile:
            continue
        ust = _aile_ust(res_kod, aile)
        if not ust or ust != _aile_ust(reg_kod, aile):
            continue
        ekle.append({'h_code': kod, 'h_class': e.get('h_class'), 'c_min': e.get('c_min'), 'c_max': e.get('c_max'),
                     'kaynak': 'kayit'})
    if not ekle:
        return result
    out = dict(result)
    out['scl'] = list(result.get('scl') or []) + ekle
    out['registrant_scl'] = ekle
    return out


def _supplement_from_echa_cl(cas: str, sea_result: dict) -> dict:
    """
    SEA Ek-6 sonucunu ECHA C&L dosya önbelleğinden supplement et.
    Harmonize edilmemiş tehlike sınıfları için ekstra H-kodları merge eder.
    SEA Ek-6 H-kodlarına dokunmaz.
    ECHA dosyası yoksa PubChem önbelleğine de bakılır; o da yoksa arka planda çekim tetiklenir.
    """
    echa_entry = _read_cl_file(_ECHA_CL_DIR, cas)
    if echa_entry:
        if _is_stale(echa_entry):
            _fetch_echa_background(cas, refresh=True)
    else:
        _fetch_echa_background(cas)
        # ECHA verisi gelene kadar PubChem'in kaydettiği GHS verisini fallback olarak kullan
        echa_entry = _read_cl_file(_PUBCHEM_DIR, cas)
    # Kayıt yaptıranın GHS öz-sınıflandırması (ECHA kayıt dosyası 2.1 GHS; component_phys) — C&L API yalnız
    # uyumlaştırılmış sınıflandırmayı verdiği için Ek-6'da olmayan sınıflar (örn. toluen H412) buradan gelir.
    _reg = []
    try:
        from app.services import component_phys as _cpx
        _rec = _cpx._read(cas) or {}
        _reg = [dict(h, _registrant=True) for h in ((_rec.get('ghs_self') or {}).get('hazards') or [])]
        _reg_no = ((_rec.get('dossier') or {}).get('registration_number') or '')
    except Exception:
        _reg_no = ''
    if not echa_entry and not _reg:
        return sea_result

    echa_legacy = _cl_to_legacy(echa_entry, 3, 'ECHA C&L') if echa_entry else {'hazards': [], 'pictograms': []}
    _seen = {(h.get('h_class'), h.get('h_code')) for h in echa_legacy.get('hazards', [])}
    echa_legacy = {**echa_legacy, 'hazards': list(echa_legacy.get('hazards', []))
                   + [h for h in _reg if (h['h_class'], h['h_code']) not in _seen]}
    # SEA Md.6(1)(c): yalnız Ek-6 girişinde bulunmayan sınıf/farklılaştırmalar eklenir (H kodu değil sınıf
    # karşılaştırılır — ek6_family). İşaretlenir ki kullanıcı görsün/kaldırabilsin. Aynı sınıfta ECHA'daki
    # daha ağır kategori eklenmez, KDU bilgisi olarak 'ek6_daha_agir'da döner.
    from app.services.ek6_family import split_echa
    _extra, _agir = split_echa(sea_result.get('hazards', []), echa_legacy.get('hazards', []))
    extra_hazards = [{**h, '_echa_supplement': True} for h in _extra]

    if not extra_hazards and not _agir:
        return sea_result
    if not extra_hazards:
        return {**sea_result, 'ek6_daha_agir': _agir}

    result = dict(sea_result)
    if _agir:
        result['ek6_daha_agir'] = _agir
    result['hazards'] = sea_result.get('hazards', []) + extra_hazards

    sea_pict = set(sea_result.get('pictograms', []))
    extra_pict = [p for p in echa_legacy.get('pictograms', []) if p not in sea_pict]
    if extra_pict:
        result['pictograms'] = list(sea_result.get('pictograms', [])) + extra_pict

    result['echa_supplement']        = [h['h_code'] for h in extra_hazards]
    from app.services.echa_service import ECHA_ATTRIBUTION
    result['echa_supplement_source'] = f'ECHA C&L öz-sınıflandırma bildirimlerinden derlendi — {ECHA_ATTRIBUTION}'
    result['classification_sources'] = {
        h['h_code']: 'SEA Ek-6'
        for h in sea_result.get('hazards', []) if h.get('h_code')
    }
    for h in extra_hazards:
        result['classification_sources'][h['h_code']] = (
            f"ECHA kayıt dosyası — kayıt yaptıranın sınıflandırması{(' (' + _reg_no + ')') if _reg_no else ''}"
            if h.get('_registrant') else 'ECHA C&L öz-sınıflandırma')

    print(f'[sea_supplement] {cas}: ECHA dosyasından {len(extra_hazards)} ek H-kodu: '
          f'{[h["h_code"] for h in extra_hazards]}')
    return result


_ECHA_TTL_DAYS  = 30          # ECHA kaydı bundan eskiyse kullanımda arka planda yenilenir
_ECHA_RETRY_SEC = 6 * 3600    # başarısız çekimden sonra aynı CAS için bekleme
_echa_bg_lock   = threading.Lock()
_echa_inflight: set  = set()
_echa_last_try: dict = {}


def _is_stale(entry: dict) -> bool:
    ts = entry.get('fetched_at')
    if not ts:
        return True
    # M faktörü/ATE yöntemi değişmeden önce kaydedilmiş ECHA kayıtları yeniden çekilir
    # (arşiv kaydında 'atp', ham önbellek kaydında yalnız 'echa_extras' bulunur)
    if entry.get('atp') == 'ECHA C&L API' or 'echa_extras' in entry:
        from app.services.echa_service import ECHA_EXTRAS_VER
        if (entry.get('echa_extras') or 0) < ECHA_EXTRAS_VER:
            return True
    try:
        fetched = datetime.fromisoformat(ts)
    except (TypeError, ValueError):
        return True
    if fetched.tzinfo is None:
        fetched = fetched.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - fetched).days >= _ECHA_TTL_DAYS


_ECHA_SYNC_TIMEOUT = 20   # sn — eşzamanlı ECHA çekiminde en fazla bu kadar beklenir


async def ensure_echa_supplement(cas: str) -> None:
    """SEA Ek-6'daki madde için ECHA C&L önbelleği yoksa/eskiyse ÖNCE çek, sonra dön.

    Ek-6 dışı sınıfların (SEA Md.6(1)(c)) takviyesi önceden yalnız arka planda çekiliyordu;
    ilk sorguda eksik (örn. NaOH H290 yok), sonrakinde tam sonuç çıkıyordu. Artık hesaplama ve
    CAS sorgusu bu çekimi bekler. Başarısızlıkta _ECHA_RETRY_SEC boyunca yeniden denenmez;
    ECHA'ya ulaşılamazsa mevcut (varsa eski) kayıtla devam edilir.
    """
    cas = (cas or '').strip()
    if not cas or not _sea_ek6_lookup(cas=cas):
        return
    entry = _read_cl_file(_ECHA_CL_DIR, cas)
    if entry and not _is_stale(entry):
        return
    now = time.time()
    with _echa_bg_lock:
        if cas in _echa_inflight or now - _echa_last_try.get(cas, 0) < _ECHA_RETRY_SEC:
            return
        _echa_inflight.add(cas)
        _echa_last_try[cas] = now
    try:
        import asyncio as _asyncio
        from app.services.echa_service import lookup_echa_api as _lei
        res = await _asyncio.wait_for(_lei(cas, refresh=bool(entry)), timeout=_ECHA_SYNC_TIMEOUT)
        if res:
            _echa_last_try.pop(cas, None)
            # Oturum önbelleğinden dönen sonuç dosyaya yazılmamış olabilir — takviye dosyadan okunur
            if res.get('_cache_source') == 'echa_cl' and not _read_cl_file(_ECHA_CL_DIR, cas):
                save_echa_cl_substance(cas, res)
    except Exception as e:
        print(f'[echa_sync] {cas}: çekilemedi ({type(e).__name__}) — mevcut kayıtla devam')
    finally:
        with _echa_bg_lock:
            _echa_inflight.discard(cas)


def _fetch_echa_background(cas: str, refresh: bool = False):
    """
    Maddeyi arka planda ECHA C&L'den çek (kullanıcı beklemez).
    refresh=True: mevcut ama eski kaydı yenile — sadece ECHA denenir, başarısızsa eski kayıt kalır.
    Aynı CAS için aynı anda tek çekim; başarısız denemeden sonra _ECHA_RETRY_SEC beklenir.
    """
    now = time.time()
    with _echa_bg_lock:
        if cas in _echa_inflight or now - _echa_last_try.get(cas, 0) < _ECHA_RETRY_SEC:
            return
        _echa_inflight.add(cas)
        _echa_last_try[cas] = now

    def _run():
        import asyncio as _asyncio
        from app.services.echa_service import lookup_echa_api as _lei
        loop = _asyncio.new_event_loop()
        try:
            _asyncio.set_event_loop(loop)
            result = loop.run_until_complete(_lei(cas, refresh=refresh))
            if result:
                print(f'[echa_bg] {cas}: ECHA C&L verisi {"yenilendi" if refresh else "çekildi"} ve önbelleğe kaydedildi.')
            else:
                print(f'[echa_bg] {cas}: veri alınamadı — {_ECHA_RETRY_SEC // 3600} saat sonra tekrar denenecek.')
        except Exception as e:
            print(f'[echa_bg] {cas}: çekim hatası — {e}')
        finally:
            loop.close()
            with _echa_bg_lock:
                _echa_inflight.discard(cas)

    threading.Thread(target=_run, daemon=True).start()


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
    from app.services.data_store import persist
    persist(_CUSTOM_PATH)
    return is_new


def is_annex_vi(cas: str, ec_no: str = '', index_no: str = '') -> bool:
    """Madde SEA Ek-6 veya ECHA ATP22'de mi?"""
    cas = cas.strip()
    if _sea_ek6_lookup(cas=cas, ec_no=ec_no, index_no=index_no):
        return True
    return _db_lookup(cas=cas, ec_no=ec_no, index_no=index_no) is not None




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


def get_substance_scl(cas_no: str, h_code: str, form: str = '') -> dict:
    """
    Bir CAS numarası + H kodu için TÜM özel konsantrasyon bantlarını (SCL) döndürür.

    H314 gibi kodlar birden fazla alt kategoriye (1A, 1B) sahip olabilir; model
    doğru bandı seçebilmek için tüm bantları görmek zorundadır.

    form: ürün fiziksel formu ('liquid','solution',...) — Note B maddelerinde
          sıvı formda AQ kaydına yönlendirmek için kullanılır.

    Dönüş şeması:
      {
        "found":   bool,
        "cas_no":  str,
        "h_code":  str,           # sorgulanan H kodu
        "bands": [                # eşleşen tüm bantlar (boşsa found=False)
          {
            "h_class": str,       # örn. "Cilt Aşınd. 1A"
            "c_min":   float|None,# alt sınır (dahil) — None = üst sınır yok
            "c_max":   float|None,# üst sınır (hariç) — None = alt sınır yok
          }, ...
        ],
        "source":  str,           # "sea_ek6" | "substance_db" | "not_found"
      }

    KULLANIM: bands listesini al, konsantrasyonu her banda karşılaştır:
      c_min <= konsantrasyon < c_max → o bant geçerli.
      c_max=None → üst sınır yok (örn. 1A: ≥90).
      c_min=None → alt sınır yok (genellikle olmaz).
    found=False ise bu bileşen için kayıtlı SCL yok — sessizce 0 veya sınırsız alma.
    """
    cas_no  = (cas_no or '').strip()
    h_code  = (h_code or '').strip().upper()

    not_found = {
        'found': False, 'cas_no': cas_no, 'h_code': h_code,
        'bands': [], 'source': 'not_found',
    }

    if not cas_no or not h_code:
        return not_found

    sub = lookup_substance(cas_no, form=form)
    if not sub:
        return not_found

    scl_list = sub.get('scl') or []
    source   = 'sea_ek6' if sub.get('sea_ek6') else 'substance_db'

    # Tam eşleşme VEYA aynı H-kodu ailesindeki tüm bantlar (H314 → 1A ve 1B)
    bands = [
        {'h_class': s.get('h_class', ''), 'c_min': s.get('c_min'), 'c_max': s.get('c_max')}
        for s in scl_list
        if s.get('h_code', '').upper() == h_code
        or s.get('h_code', '').upper().startswith(h_code)
    ]

    if not bands:
        return not_found

    return {
        'found':  True,
        'cas_no': cas_no,
        'h_code': h_code,
        'bands':  bands,
        'source': source,
    }
