"""
Fiziksel Özellik Parser  —  PCN Hazırlık Modülü
=================================================
Kullanıcı girdi string'lerini yapılandırılmış dict'e çevirir.

Çıkış formatı (her özellik için):
    {
        'display'        : str           – Section 9'da gösterilecek metin
        'calc'           : float | None  – Sınıflandırma motoru (worst-case)
        'pcn'            : float | None  – PCN bildirimi için tek değer
        'nd'             : bool          – Belirlenmemiştir
        'na'             : bool          – Uygulanamaz
        'has_range'      : bool          – Aralık girişi mi?
        'range_min'      : float | None
        'range_max'      : float | None
        'calc_direction' : str | None    – 'min' | 'max'
        'calc_note'      : dict | None   – {'TR': '...', 'EN': '...'} — Section 2 notu
    }

PCN bantları (CLP Yönetmeliği Ek VIII):
    Bileşen konsantrasyonu için PCN bildirimine giden sabit bant etiketleri.
"""

from __future__ import annotations
import re
from typing import Optional, Tuple


# ── Worst-case kuralları ─────────────────────────────────────────────────────
# None → sınıflandırmayı etkilemez, sadece display

WORST_CASE_RULE: dict[str, Optional[str]] = {
    # Sınıflandırmayı etkileyen — worst-case zorunlu
    'flash_point':      'min',      # Düşük FP → yüksek yanıcılık kategorisi
    'boiling_point':    'min',      # FP<23 + BP≤35 → Flam. Liq. Cat.1 (H224)
    'ph':               'context',  # Asit → min; baz → max
    'viscosity':        'min',      # H304: ≤ 20.5 mm²/s koşulu
    'vapor_pressure':   'max',      # Yüksek buhar basıncı → daha fazla maruziyet
    'auto_ignition':    'min',      # Düşük otoalev sıcaklığı → daha tehlikeli
    # Sadece bilgi — sınıflandırmayı etkilemez
    'density':          None,
    'rel_density':      None,
    'melting_point':    None,
    'solubility':       None,
    'log_kow':          None,
    'partition_coeff':  None,
    'decomp_temp':      None,
    'decomposition_temp': None,
    'evap_rate':        None,
    'odour_threshold':  None,
    'vapor_density':    None,
    'lel':              None,
    'uel':              None,
}

# Özellik adı → (TR etiketi, EN etiketi)
_PROP_LABELS: dict[str, tuple[str, str]] = {
    'flash_point':    ('Parlama noktası',          'Flash point'),
    'boiling_point':  ('Kaynama noktası',           'Boiling point'),
    'ph':             ('pH',                        'pH'),
    'viscosity':      ('Viskozite',                 'Viscosity'),
    'vapor_pressure': ('Buhar basıncı',             'Vapour pressure'),
    'auto_ignition':  ('Kendiliğinden tutuşma sıc.','Auto-ignition temp.'),
}

# Regex: Belirlenmemiştir / ND
_RE_ND = re.compile(
    r'^(belirlenmemi[sş]|not\s*det(ermined)?|nd|n\.d\.|n/d|'
    r'tespit\s*edilmemi[sş]|bilinmiyor|unknown)$',
    re.IGNORECASE,
)

# Regex: Uygulanamaz / N/A
_RE_NA = re.compile(
    r'^(uygulanamaz|not\s*appl(icable)?|n\.?a\.?|uyg\.$|geçersiz)$',
    re.IGNORECASE,
)

# Regex: aralık  "58-62"  "2–4"  ">60-80"
_RE_RANGE = re.compile(
    r'^([<>≤≥~≈]?\s*\d+\.?\d*)\s*[-–]\s*(\d+\.?\d*)$'
)

# Regex: prefix  ">100"  "<20"  "≥7"  "~55"
_RE_PREFIX = re.compile(
    r'^([<>≤≥~≈])\s*(\d+\.?\d*)$'
)

# Regex: saf sayı
_RE_NUM = re.compile(r'^\d+\.?\d*$')


# ── PCN Bantları (CLP Ek VIII) ────────────────────────────────────────────────
PCN_BANDS: list[tuple[float, float, str]] = [
    (0,     0.1,   '< 0.1%'),
    (0.1,   1,     '≥ 0.1% - < 1%'),
    (1,     5,     '≥ 1% - < 5%'),
    (5,     10,    '≥ 5% - < 10%'),
    (10,    20,    '≥ 10% - < 20%'),
    (20,    30,    '≥ 20% - < 30%'),
    (30,    40,    '≥ 30% - < 40%'),
    (40,    50,    '≥ 40% - < 50%'),
    (50,    60,    '≥ 50% - < 60%'),
    (60,    70,    '≥ 60% - < 70%'),
    (70,    80,    '≥ 70% - < 80%'),
    (80,    90,    '≥ 80% - < 90%'),
    (90,    100,   '≥ 90% - < 100%'),
]


def get_pcn_band(
    conc_min: Optional[float] = None,
    conc_max: Optional[float] = None,
    conc_exact: Optional[float] = None,
) -> Optional[str]:
    """
    Bileşen konsantrasyon değerinden PCN bandı döndür.
    Aralık varsa worst-case = max değer kullanılır.

    Returns
    -------
    str — örn. '≥ 5% - < 10%'   |   None — değer yoksa
    """
    if conc_exact is not None:
        value = float(conc_exact)
    elif conc_max is not None:
        value = float(conc_max)
    elif conc_min is not None:
        value = float(conc_min)
    else:
        return None

    if value >= 100:
        return '100%'
    if value <= 0:
        return PCN_BANDS[0][2]   # < 0.1%

    for lo, hi, label in PCN_BANDS:
        if lo <= value < hi:
            return label
    return None


# ── Ana parse fonksiyonu ──────────────────────────────────────────────────────

def parse_phys_value(raw, prop: str = '') -> dict:
    """
    Tek bir fiziksel özellik ham değerini parse eder.

    Parameters
    ----------
    raw  : str | int | float | None — kullanıcı girdisi
    prop : str — özellik anahtarı (örn. 'flash_point', 'ph')

    Returns
    -------
    Yapılandırılmış dict (yukarıdaki formata göre)
    """
    # Zaten parse edilmişse dokunma
    if isinstance(raw, dict):
        return raw

    if raw is None or str(raw).strip() == '':
        return _empty()

    s = str(raw).strip()

    # Belirlenmemiştir
    if _RE_ND.match(s):
        return {**_empty(), 'display': s, 'nd': True}

    # Uygulanamaz
    if _RE_NA.match(s):
        return {**_empty(), 'display': s, 'na': True}

    # Aralık: "58-62", "2–4", ">60-80"
    m = _RE_RANGE.match(s)
    if m:
        lo_str = m.group(1).strip()
        hi_str = m.group(2).strip()
        try:
            lo = float(re.sub(r'[<>≤≥~≈\s]', '', lo_str))
            hi = float(hi_str)
            rule = WORST_CASE_RULE.get(prop)
            calc, direction = _worst_case(lo, hi, rule)
            note = _make_note(prop, calc, lo, hi, direction) if (rule and lo != hi) else None
            display = f'{lo_str}–{hi_str}'
            return {
                'display':        display,
                'calc':           calc,
                'pcn':            calc,
                'nd':             False,
                'na':             False,
                'has_range':      True,
                'range_min':      lo,
                'range_max':      hi,
                'calc_direction': direction,
                'calc_note':      note,
            }
        except ValueError:
            pass

    # Prefix: ">100", "<20", "≥7", "~55"
    m = _RE_PREFIX.match(s)
    if m:
        try:
            val = float(m.group(2))
            return {**_single(s, val)}
        except ValueError:
            pass

    # Saf sayı
    if _RE_NUM.match(s):
        try:
            val = float(s)
            return _single(s, val)
        except ValueError:
            pass

    # Tanımsız format — display olarak sakla, calc yok
    return {**_empty(), 'display': s}


def parse_all_phys_props(phys_in: dict) -> dict:
    """
    Tüm phys_in dict'ini parse eder.
    String/sayı değerler yapılandırılmış dict'e dönüşür.
    Diğer tipler (bool, list, dict) dokunulmadan aktarılır.
    """
    parsed: dict = {}
    for key, val in phys_in.items():
        if isinstance(val, (str, int, float)) and not isinstance(val, bool):
            parsed[key] = parse_phys_value(val, prop=key)
        else:
            parsed[key] = val
    return parsed


# ── Yardımcı erişimciler ──────────────────────────────────────────────────────

def get_display(phys: dict, key: str) -> Optional[str]:
    """
    phys_props dict'inden display değerini döndür.
    Hem yeni dict formatını hem eski string formatını destekler.
    """
    val = phys.get(key)
    if val is None:
        return None
    if isinstance(val, dict):
        if val.get('nd'):
            return 'Belirlenmemiştir'
        if val.get('na'):
            return 'Uygulanamaz'
        return val.get('display') or None
    return str(val) if str(val).strip() != '' else None


def get_calc(phys: dict, key: str) -> Optional[float]:
    """
    phys_props dict'inden sınıflandırma motoru değerini (worst-case) döndür.
    Hem yeni dict formatını hem eski string/float formatını destekler.
    """
    val = phys.get(key)
    if isinstance(val, dict):
        return val.get('calc')
    if val is not None and str(val).strip() != '':
        try:
            return float(re.sub(r'[<>≤≥~≈\s]', '', str(val).split('-')[0].split('–')[0]))
        except (ValueError, AttributeError):
            return None
    return None


def get_range_notes(phys: dict, lang: str = 'TR') -> list[str]:
    """
    Sınıflandırma kararını etkileyen aralıklar için Section 2 gerekçe notlarını
    döndür. Aralık yoksa veya tek değer girildiyse boş liste döner.

    Parameters
    ----------
    phys : parse_all_phys_props() çıktısı
    lang : 'TR' | 'EN'

    Returns
    -------
    list[str] — her madde bir bullet olarak Section 2'ye eklenir
    """
    notes: list[str] = []
    for val in phys.values():
        if not isinstance(val, dict):
            continue
        if not val.get('has_range'):
            continue
        note_dict = val.get('calc_note')
        if not note_dict:
            continue
        if isinstance(note_dict, dict):
            note = note_dict.get(lang) or note_dict.get('TR', '')
        else:
            note = str(note_dict)
        if note:
            notes.append(note)
    return notes


# ── İç yardımcılar ───────────────────────────────────────────────────────────

def _empty() -> dict:
    return {
        'display':        '',
        'calc':           None,
        'pcn':            None,
        'nd':             False,
        'na':             False,
        'has_range':      False,
        'range_min':      None,
        'range_max':      None,
        'calc_direction': None,
        'calc_note':      None,
    }


def _single(display: str, val: float) -> dict:
    return {
        'display':        display,
        'calc':           val,
        'pcn':            val,
        'nd':             False,
        'na':             False,
        'has_range':      False,
        'range_min':      None,
        'range_max':      None,
        'calc_direction': None,
        'calc_note':      None,
    }


def _worst_case(lo: float, hi: float, rule: Optional[str]) -> Tuple[float, str]:
    if rule == 'min':
        return lo, 'min'
    if rule == 'max':
        return hi, 'max'
    if rule == 'context':
        # pH: her iki uç da nötr bölge dışındaysa en tehlikeliyi seç
        if hi <= 7.0:
            return lo, 'min'   # asit bölge → en düşük pH
        elif lo >= 7.0:
            return hi, 'max'   # baz bölge  → en yüksek pH
        else:
            return lo, 'min'   # nötrü kesiyor → asit tarafı daha tehlikeli (H314 eşiği ≤2)
    return lo, 'min'           # kural yoksa bile min (güvenli taraf)


def _make_note(prop: str, calc: float, lo: float, hi: float, direction: str) -> dict:
    lbl_tr, lbl_en = _PROP_LABELS.get(prop, (prop, prop))
    dir_tr = 'en düşük değer' if direction == 'min' else 'en yüksek değer'
    dir_en = 'lowest value'   if direction == 'min' else 'highest value'
    rng    = f'{lo:g}–{hi:g}'
    c      = f'{calc:g}'
    return {
        'TR': f'{lbl_tr} {rng} aralığından {c} ({dir_tr}) esas alınmıştır.',
        'EN': f'{lbl_en} range {rng}: {c} ({dir_en}) used for classification.',
    }
