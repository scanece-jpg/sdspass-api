"""
Konsantrasyon Aralığı Servisi
================================
CAS numarası + tehlike sınıfları → dinamik konsantrasyon dropdown listesi

Kaynak: CLP Yönetmeliği Annex I, Part 3, Tablo 3.1 (sağlık) + Tablo 3.2 (çevre)
        KKDİK Ek-1 (TR karşılığı)

Çalışma mantığı:
  1. Maddenin tehlike sınıfları alınır
  2. Her sınıf için CLP GCL (Generic Concentration Limit) tablosuna bakılır
  3. GCL eşikleri + kullanıcı SCL + standart kırılım noktaları birleştirilir
  4. Birbirini izleyen aralıklar oluşturulur
  5. Her aralık için aktif karışım sınıflandırması belirlenir
  6. Select-option formatında döndürülür
"""

from __future__ import annotations
import re
from typing import Optional

# ---------------------------------------------------------------------------
# Sabitler
# ---------------------------------------------------------------------------

# Standart kırılım noktaları (CLP Annex I + endüstriyel kullanım)
STANDARD_BREAKPOINTS = [0.1, 1.0, 5.0, 10.0, 25.0, 50.0, 100.0]

# Sinyal sözcüğü → renk kodu
SIGNAL_COLORS = {
    'Danger' : '#d32f2f',   # kırmızı
    'Warning': '#f57c00',   # turuncu
    ''       : '#757575',   # gri (sınıflandırılmamış)
}

# Türkçe / İngilizce etiketler
LABELS = {
    # sınıflandırılmamış
    'unclassified': {
        'TR': 'Sınıflandırılmamış', 'EN': 'Not classified',
        'DE': 'Nicht eingestuft',
    },
    # hazard class kısa etiketleri
    'Skin Corr. 1A' : {'TR': 'Deri Aşındırıcı (kat.1A)', 'EN': 'Skin Corrosion Cat.1A'},
    'Skin Corr. 1B' : {'TR': 'Deri Aşındırıcı (kat.1B)', 'EN': 'Skin Corrosion Cat.1B'},
    'Skin Corr. 1'  : {'TR': 'Deri Aşındırıcı (kat.1)',  'EN': 'Skin Corrosion Cat.1'},
    'Skin Irrit. 2' : {'TR': 'Deri Tahrişi (kat.2)',     'EN': 'Skin Irritation Cat.2'},
    'Eye Dam. 1'    : {'TR': 'Göz Hasarı (kat.1)',       'EN': 'Eye Damage Cat.1'},
    'Eye Irrit. 2'  : {'TR': 'Göz Tahrişi (kat.2)',      'EN': 'Eye Irritation Cat.2'},
    'Acute Tox. 1'  : {'TR': 'Akut Toksisite (kat.1)',   'EN': 'Acute Toxicity Cat.1'},
    'Acute Tox. 2'  : {'TR': 'Akut Toksisite (kat.2)',   'EN': 'Acute Toxicity Cat.2'},
    'Acute Tox. 3'  : {'TR': 'Akut Toksisite (kat.3)',   'EN': 'Acute Toxicity Cat.3'},
    'Acute Tox. 4'  : {'TR': 'Akut Toksisite (kat.4)',   'EN': 'Acute Toxicity Cat.4'},
    'Resp. Sens. 1' : {'TR': 'Solunum Hassaslaştırıcı',  'EN': 'Respiratory Sensitisation'},
    'Resp. Sens. 1A': {'TR': 'Solunum Hassaslaştırıcı 1A','EN': 'Respiratory Sensitisation 1A'},
    'Resp. Sens. 1B': {'TR': 'Solunum Hassaslaştırıcı 1B','EN': 'Respiratory Sensitisation 1B'},
    'Skin Sens. 1'  : {'TR': 'Deri Hassaslaştırıcı',     'EN': 'Skin Sensitisation'},
    'Skin Sens. 1A' : {'TR': 'Deri Hassaslaştırıcı 1A',  'EN': 'Skin Sensitisation 1A'},
    'Skin Sens. 1B' : {'TR': 'Deri Hassaslaştırıcı 1B',  'EN': 'Skin Sensitisation 1B'},
    'Muta. 1A'      : {'TR': 'Mutajenik (kat.1A)',       'EN': 'Mutagenic Cat.1A'},
    'Muta. 1B'      : {'TR': 'Mutajenik (kat.1B)',       'EN': 'Mutagenic Cat.1B'},
    'Muta. 2'       : {'TR': 'Mutajenik (kat.2)',        'EN': 'Mutagenic Cat.2'},
    'Carc. 1A'      : {'TR': 'Kanserojen (kat.1A)',      'EN': 'Carcinogenic Cat.1A'},
    'Carc. 1B'      : {'TR': 'Kanserojen (kat.1B)',      'EN': 'Carcinogenic Cat.1B'},
    'Carc. 2'       : {'TR': 'Kanserojen (kat.2)',       'EN': 'Carcinogenic Cat.2'},
    'Repr. 1A'      : {'TR': 'Üreme Toksik (kat.1A)',    'EN': 'Repr. Toxic Cat.1A'},
    'Repr. 1B'      : {'TR': 'Üreme Toksik (kat.1B)',    'EN': 'Repr. Toxic Cat.1B'},
    'Repr. 2'       : {'TR': 'Üreme Toksik (kat.2)',     'EN': 'Repr. Toxic Cat.2'},
    'STOT SE 1'     : {'TR': 'Tek Maruziyet STOT (kat.1)','EN': 'STOT-SE Cat.1'},
    'STOT SE 2'     : {'TR': 'Tek Maruziyet STOT (kat.2)','EN': 'STOT-SE Cat.2'},
    'STOT SE 3'     : {'TR': 'Uyarıcı Etki (STOT SE3)',  'EN': 'STOT-SE Cat.3'},
    'STOT RE 1'     : {'TR': 'Tekrarlı Maruziyet (kat.1)','EN': 'STOT-RE Cat.1'},
    'STOT RE 2'     : {'TR': 'Tekrarlı Maruziyet (kat.2)','EN': 'STOT-RE Cat.2'},
    'Asp. Tox. 1'   : {'TR': 'Aspirasyon Toksik',        'EN': 'Aspiration Hazard'},
    'Aquatic Acute 1'   : {'TR': 'Su Ortamı – Akut (kat.1)',  'EN': 'Aquatic Acute Cat.1'},
    'Aquatic Chronic 1' : {'TR': 'Su Ortamı – Kronik (kat.1)','EN': 'Aquatic Chronic Cat.1'},
    'Aquatic Chronic 2' : {'TR': 'Su Ortamı – Kronik (kat.2)','EN': 'Aquatic Chronic Cat.2'},
    'Aquatic Chronic 3' : {'TR': 'Su Ortamı – Kronik (kat.3)','EN': 'Aquatic Chronic Cat.3'},
    'Flam. Liq. 1'  : {'TR': 'Alevlenir Sıvı (kat.1)',  'EN': 'Flammable Liquid Cat.1'},
    'Flam. Liq. 2'  : {'TR': 'Alevlenir Sıvı (kat.2)',  'EN': 'Flammable Liquid Cat.2'},
    'Flam. Liq. 3'  : {'TR': 'Alevlenir Sıvı (kat.3)',  'EN': 'Flammable Liquid Cat.3'},
}

# hazard class → piktogram(lar)
CLASS_PICTOGRAMS = {
    'Skin Corr. 1A': ['GHS05'], 'Skin Corr. 1B': ['GHS05'], 'Skin Corr. 1': ['GHS05'],
    'Skin Irrit. 2': ['GHS07'], 'Eye Dam. 1': ['GHS05'],    'Eye Irrit. 2': ['GHS07'],
    'Acute Tox. 1' : ['GHS06'], 'Acute Tox. 2': ['GHS06'],  'Acute Tox. 3': ['GHS06'],
    'Acute Tox. 4' : ['GHS07'],
    'Resp. Sens. 1': ['GHS08'], 'Resp. Sens. 1A': ['GHS08'],'Resp. Sens. 1B': ['GHS08'],
    'Skin Sens. 1' : ['GHS07'], 'Skin Sens. 1A': ['GHS07'], 'Skin Sens. 1B': ['GHS07'],
    'Muta. 1A': ['GHS08'],  'Muta. 1B': ['GHS08'],  'Muta. 2': ['GHS08'],
    'Carc. 1A': ['GHS08'],  'Carc. 1B': ['GHS08'],  'Carc. 2': ['GHS08'],
    'Repr. 1A': ['GHS08'],  'Repr. 1B': ['GHS08'],  'Repr. 2': ['GHS08'],
    'STOT SE 1': ['GHS08'], 'STOT SE 2': ['GHS08'],
    'STOT SE 3': ['GHS07'], 'STOT RE 1': ['GHS08'], 'STOT RE 2': ['GHS08'],
    'Asp. Tox. 1': ['GHS08'],
    'Aquatic Acute 1': ['GHS09'], 'Aquatic Chronic 1': ['GHS09'],
    'Aquatic Chronic 2': ['GHS09'], 'Aquatic Chronic 3': ['GHS09'],
    'Flam. Liq. 1': ['GHS02'], 'Flam. Liq. 2': ['GHS02'], 'Flam. Liq. 3': ['GHS02'],
}

# Üst kategori → geçersiz kıldığı alt kategoriler
# (Skin Corr. 1A aktifse Skin Corr. 1B listeden çıkar vb.)
SUPERSEDES: dict[str, list[str]] = {
    'Skin Corr. 1A' : ['Skin Corr. 1B', 'Skin Corr. 1'],
    'Skin Corr. 1B' : ['Skin Corr. 1'],
    'Acute Tox. 1'  : ['Acute Tox. 2', 'Acute Tox. 3', 'Acute Tox. 4'],
    'Acute Tox. 2'  : ['Acute Tox. 3', 'Acute Tox. 4'],
    'Acute Tox. 3'  : ['Acute Tox. 4'],
    'STOT SE 1'     : ['STOT SE 2', 'STOT SE 3'],
    'STOT SE 2'     : ['STOT SE 3'],
    'STOT RE 1'     : ['STOT RE 2'],
    'Muta. 1A'      : ['Muta. 1B', 'Muta. 2'],
    'Muta. 1B'      : ['Muta. 2'],
    'Carc. 1A'      : ['Carc. 1B', 'Carc. 2'],
    'Carc. 1B'      : ['Carc. 2'],
    'Repr. 1A'      : ['Repr. 1B', 'Repr. 2'],
    'Repr. 1B'      : ['Repr. 2'],
    'Resp. Sens. 1A': ['Resp. Sens. 1B', 'Resp. Sens. 1'],
    'Resp. Sens. 1B': ['Resp. Sens. 1'],
    'Skin Sens. 1A' : ['Skin Sens. 1B', 'Skin Sens. 1'],
    'Skin Sens. 1B' : ['Skin Sens. 1'],
    'Aquatic Chronic 1': ['Aquatic Chronic 2','Aquatic Chronic 3','Aquatic Chronic 4'],
    'Aquatic Chronic 2': ['Aquatic Chronic 3','Aquatic Chronic 4'],
    'Aquatic Chronic 3': ['Aquatic Chronic 4'],
}


def _apply_dominance(classes: list[str]) -> list[str]:
    """Üst kategori aktifse alt kategoriyi listeden çıkar."""
    remove: set[str] = set()
    for c in classes:
        for sub in SUPERSEDES.get(c, []):
            remove.add(sub)
    return [c for c in classes if c not in remove]


# hazard class → sinyal sözcüğü
CLASS_SIGNAL = {
    'Skin Corr. 1A': 'Danger',  'Skin Corr. 1B': 'Danger',  'Skin Corr. 1': 'Danger',
    'Skin Irrit. 2': 'Warning', 'Eye Dam. 1': 'Danger',     'Eye Irrit. 2': 'Warning',
    'Acute Tox. 1' : 'Danger',  'Acute Tox. 2': 'Danger',
    'Acute Tox. 3' : 'Danger',  'Acute Tox. 4': 'Warning',
    'Resp. Sens. 1': 'Danger',  'Resp. Sens. 1A': 'Danger', 'Resp. Sens. 1B': 'Danger',
    'Skin Sens. 1' : 'Warning', 'Skin Sens. 1A': 'Warning', 'Skin Sens. 1B': 'Warning',
    'Muta. 1A': 'Danger', 'Muta. 1B': 'Danger', 'Muta. 2': 'Warning',
    'Carc. 1A': 'Danger', 'Carc. 1B': 'Danger', 'Carc. 2': 'Warning',
    'Repr. 1A': 'Danger', 'Repr. 1B': 'Danger', 'Repr. 2': 'Warning',
    'STOT SE 1': 'Danger',  'STOT SE 2': 'Warning',
    'STOT SE 3': 'Warning', 'STOT RE 1': 'Danger', 'STOT RE 2': 'Warning',
    'Asp. Tox. 1': 'Danger',
    'Aquatic Acute 1': 'Warning', 'Aquatic Chronic 1': 'Warning',
    'Aquatic Chronic 2': 'Warning', 'Aquatic Chronic 3': 'Warning',
    'Flam. Liq. 1': 'Danger', 'Flam. Liq. 2': 'Danger', 'Flam. Liq. 3': 'Warning',
}

# ---------------------------------------------------------------------------
# CLP Annex I Tablo 3.1 & 3.2 — Generic Concentration Limits
# ---------------------------------------------------------------------------
# Yapı: { normalize_edilmiş_h_class: [
#     (eşik_%, karışım_sınıflandırması, H_kodu),   # küçükten büyüğe
#     ...
# ]}
# Anlam: madde konsantrasyonu ≥ eşik_% ise → karışım bu sınıfa girer
#
# GCL tek kaynaktan besleniyor: basit (tek eşikli) satırlar clp_service.CLP_CUTOFFS_DICT'ten
# türetilir; cascade (çok seviyeli / çapraz sınıf) satırlar hardcode kalır.
# Artık elle senkronizasyon gerekmez — clp_service.py'deki cutoff değişince burası da güncellenir.
from app.services.clp_service import CLP_CUTOFFS_DICT as _CLP


def _s(h_class: str) -> list[tuple]:
    """CLP_CUTOFFS_DICT'ten tek-eşikli GCL satırı üret. cutoff=0.0 → boş liste."""
    e = _CLP.get(h_class)
    if not e or e['cutoff'] == 0.0:
        return []
    return [(e['cutoff'], h_class, e['h'])]


GCL: dict[str, list[tuple]] = {

    # ── CASCADE — çok seviyeli veya çapraz sınıf geçişleri ──────────────────
    # (CLP_CUTOFFS_DICT'te karşılığı yok; burada hardcode kalır)

    # Akut Toksisite — bileşen kat. → farklı karışım kategorileri (CLP Tablo 3.1.3)
    'acute tox. 1':   [(0.1,'Acute Tox. 1','H300/H310/H330'),
                       (1.0,'Acute Tox. 2','H300/H310/H330'),
                       (10.,'Acute Tox. 3','H301/H311/H331'),
                       (25.,'Acute Tox. 4','H302/H312/H332')],
    'acute tox. 2':   [(0.1,'Acute Tox. 1','H300/H310/H330'),
                       (1.0,'Acute Tox. 2','H300/H310/H330'),
                       (10.,'Acute Tox. 3','H301/H311/H331'),
                       (25.,'Acute Tox. 4','H302/H312/H332')],
    'acute tox. 3':   [(1.0,'Acute Tox. 3','H301/H311/H331'),
                       (10.,'Acute Tox. 4','H302/H312/H332')],
    'acute tox. 4':   [(1.0,'Acute Tox. 4','H302/H312/H332')],

    # Deri — çapraz sınıf: Skin Corr. bileşeni aynı zamanda Eye Dam. tetikler (CLP Tablo 3.2.3)
    'skin corr. 1a':  [(1.0,'Skin Corr. 1B','H314'),
                       (3.0,'Eye Dam. 1',   'H318'),
                       (5.0,'Skin Corr. 1A','H314')],
    'skin corr. 1b':  [(1.0,'Skin Corr. 1B','H314'),
                       (3.0,'Eye Dam. 1',   'H318')],
    'skin corr. 1':   [(1.0,'Skin Corr. 1B','H314'),
                       (5.0,'Skin Corr. 1A','H314')],

    # STOT SE — geçiş kuralı: SE1 bileşen düşük konsantrasyonda SE2 tetikler (CLP Tablo 3.8.3)
    'stot se 1':  [(1.0,'STOT SE 2','H371'),
                   (10.,'STOT SE 1','H370')],
    'stot se 2':  [(10.,'STOT SE 2','H371')],
    'stot se 3':  [(20.,'STOT SE 3','H335/H336')],

    # STOT RE — iki kademe (CLP Tablo 3.9.4)
    'stot re 1':  [(1.0,'STOT RE 1','H372'),
                   (10.,'STOT RE 2','H373')],

    # ── SIMPLE — CLP_CUTOFFS_DICT tek kaynak (_s() fonksiyonu ile) ──────────
    # Buradaki değerleri elle değiştirme — clp_service.py'de değiştir.

    'skin irrit. 2':  _s('Skin Irrit. 2'),
    'eye dam. 1':     _s('Eye Dam. 1'),
    'eye irrit. 2':   _s('Eye Irrit. 2'),

    'resp. sens. 1':  _s('Resp. Sens. 1'),
    'resp. sens. 1a': _s('Resp. Sens. 1A'),
    'resp. sens. 1b': _s('Resp. Sens. 1B'),
    'skin sens. 1':   _s('Skin Sens. 1'),
    'skin sens. 1a':  _s('Skin Sens. 1A'),
    'skin sens. 1b':  _s('Skin Sens. 1B'),

    'muta. 1a': _s('Muta. 1A'),
    'muta. 1b': _s('Muta. 1B'),
    'muta. 2':  _s('Muta. 2'),

    'carc. 1a': _s('Carc. 1A'),
    'carc. 1b': _s('Carc. 1B'),
    'carc. 2':  _s('Carc. 2'),

    'repr. 1a':    _s('Repr. 1A'),
    'repr. 1b':    _s('Repr. 1B'),
    'repr. 2':     _s('Repr. 2'),
    'repr. lact.': _s('Repr. Lact.'),

    'stot re 2':   _s('STOT RE 2'),
    'asp. tox. 1': _s('Asp. Tox. 1'),

    # ── AQUATIC — UI için basit eşikler; motor ecological_service kullanır ──
    # (M-faktörlü toplamsal formül motordan farklı — hardcode kalır)

    # --- Su Ortamı — CLP Tablo 4.1.0: taban eşik %25, _build_comp_gcl ÷M_faktör uygular ---
    'aquatic acute 1':   [(25.,'Aquatic Acute 1',  'H400')],
    'aquatic chronic 1': [(25.,'Aquatic Chronic 1','H410')],
    'aquatic chronic 2': [(25.,'Aquatic Chronic 2','H411')],
    'aquatic chronic 3': [(25.,'Aquatic Chronic 3','H412')],
    'aquatic chronic 4': [(25.,'Aquatic Chronic 4','H413')],

    # --- Alevlenirlik (karışım için parlama noktası bazlı değil, yaklaşım) ---
    'flam. liq. 1': [(1.0,'Flam. Liq. 1','H224')],
    'flam. liq. 2': [(1.0,'Flam. Liq. 2','H225')],
    'flam. liq. 3': [(10.,'Flam. Liq. 3','H226')],
}


# ---------------------------------------------------------------------------
# Yardımcı Fonksiyonlar
# ---------------------------------------------------------------------------

def _normalize_class(hclass: str) -> str:
    """'Acute Tox. 3 *' → 'acute tox. 3'  (asterisk ve boşlukları temizle)"""
    return re.sub(r'\s*\*+\s*$', '', hclass or '').strip().lower()


def _fmt(v: float) -> str:
    """0.1 → '0,1'  |  5.0 → '5'  (TR ondalık)"""
    return f'{v:g}'.replace('.', ',')


def _label(cls: str, lang: str) -> str:
    d = LABELS.get(cls)
    if d:
        return d.get(lang) or d.get('TR', cls)
    return cls


def _dominant_signal(classes: list[str]) -> str:
    """Birden fazla sınıf varsa en yüksek öncelikli sinyal sözcüğünü seç."""
    if any(CLASS_SIGNAL.get(c) == 'Danger' for c in classes):
        return 'Danger'
    if any(CLASS_SIGNAL.get(c) == 'Warning' for c in classes):
        return 'Warning'
    return ''


def _pictograms(classes: list[str]) -> list[str]:
    picts: set[str] = set()
    for c in classes:
        picts.update(CLASS_PICTOGRAMS.get(c, []))
    return sorted(picts)


# ---------------------------------------------------------------------------
# Ana Fonksiyon
# ---------------------------------------------------------------------------

def build_concentration_ranges(
    cas: str,
    hazard_classes: Optional[list[str]] = None,
    scl_thresholds: Optional[list[float]] = None,
    m_factor_acute: int = 1,
    m_factor_chronic: int = 1,
    lang: str = 'TR',
) -> list[dict]:
    """
    CAS numarası için konsantrasyon dropdown listesi oluştur.

    Parameters
    ----------
    cas            : CAS numarası (DB'den otomatik yükleme için)
    hazard_classes : ['Skin Corr. 1A', ...] (None → DB'den alınır)
    scl_thresholds : Annex VI özel eşik değerleri [%], örn. [0.5, 2.0, 5.0]
    m_factor_acute : M-faktörü akut (su ortamı eşiğini böler), default 1
    m_factor_chronic: M-faktörü kronik, default 1
    lang           : 'TR' | 'EN' | 'DE'

    Returns
    -------
    list of dict — her biri bir dropdown seçeneği:
      {
        'lower'          : float,   # alt sınır %
        'upper'          : float,   # üst sınır % (100 = saf madde/sonsuz)
        'range_label'    : str,     # '% 1 – % 5'
        'mixture_classes': list,    # aktif karışım sınıflandırmaları
        'h_codes'        : list,    # tetiklenen H kodları
        'hazard_label'   : str,     # kullanıcıya gösterilen kısa açıklama
        'signal'         : str,     # 'Danger' | 'Warning' | ''
        'pictograms'     : list,    # ['GHS05', ...]
        'color'          : str,     # hex renk
        'select_option'  : str,     # <option> içeriği
        'is_pure'        : bool,    # True → saf madde seçeneği
      }
    """

    # --- 1. Tehlike sınıflarını yükle ---
    if hazard_classes is None:
        hazard_classes = _fetch_hazard_classes(cas)

    # --- 2. GCL eşiklerini topla ---
    comp_gcl, gcl_thresholds = _build_comp_gcl(
        hazard_classes, scl_thresholds or [], m_factor_acute, m_factor_chronic
    )

    # --- 3. Tüm kırılım noktalarını birleştir ---
    all_points = sorted({0.0, 100.0} | set(STANDARD_BREAKPOINTS) | gcl_thresholds)

    # --- 4. Her aralığı sınıflandır ---
    ranges = [
        _classify_range(all_points[i], all_points[i+1], comp_gcl, hazard_classes, lang, gcl_thresholds)
        for i in range(len(all_points) - 1)
    ]

    # --- 5. Saf madde ---
    ranges.append(_pure_option(hazard_classes, lang))
    return ranges


def _fetch_hazard_classes(cas: str) -> list[str]:
    """DB'den tehlike sınıflarını çek."""
    try:
        from app.services.substance_lookup import lookup_substance
        entry = lookup_substance(cas)
        if entry:
            return [h['h_class'] for h in entry.get('hazards', []) if h.get('h_class')]
    except Exception:
        pass
    return []


# ---------------------------------------------------------------------------
# Standart Dropdown + Refinement (İki Aşamalı Akış)
# ---------------------------------------------------------------------------

def build_standard_ranges(
    cas: str,
    hazard_classes: Optional[list[str]] = None,
    scl_thresholds: Optional[list[float]] = None,
    m_factor_acute: int = 1,
    m_factor_chronic: int = 1,
    lang: str = 'TR',
) -> list[dict]:
    """
    AŞAMA 1 — Sadece standart kırılım noktalarını kullanarak kaba dropdown.

    Her seçeneğe 'split_points' eklenir:
      [] → aralık içinde eşik yok, doğrudan kullanılabilir
      [20.0] → aralık içinde 20% eşiği var → refinement sorusu gösterilmeli

    Bu sayede kullanıcıya 7-8 temiz seçenek sunulur; eğer seçilen
    aralıkta kritik bir sınır varsa yazılım 'Aşama 2'yi tetikler.
    """
    if hazard_classes is None:
        hazard_classes = _fetch_hazard_classes(cas)

    # Tüm GCL eşiklerini topla (standart dropdown için referans)
    comp_gcl, gcl_thresholds = _build_comp_gcl(
        hazard_classes, scl_thresholds or [], m_factor_acute, m_factor_chronic
    )

    # Sadece standart noktaları kullan
    std_points = sorted({0.0} | set(STANDARD_BREAKPOINTS))

    ranges = []
    for i in range(len(std_points) - 1):
        lo, hi = std_points[i], std_points[i + 1]

        # Bu standart aralığın içinde kalan GCL eşikleri
        internal = sorted(
            t for t in gcl_thresholds
            if lo < t < hi  # sınırlar hariç, içeride olanlar
        )

        # En kötü durum sınıflandırması (üst sınırı baz al)
        r = _classify_range(lo, hi, comp_gcl, hazard_classes, lang, gcl_thresholds)
        r['split_points'] = internal
        r['needs_refinement'] = len(internal) > 0
        ranges.append(r)

    # Saf madde seçeneği
    ranges.append(_pure_option(hazard_classes, lang))
    return ranges


def get_refinements(
    lower: float,
    upper: float,
    cas: str,
    hazard_classes: Optional[list[str]] = None,
    scl_thresholds: Optional[list[float]] = None,
    m_factor_acute: int = 1,
    m_factor_chronic: int = 1,
    lang: str = 'TR',
) -> list[dict]:
    """
    AŞAMA 2 — Seçilen aralıktaki her eşik için 'altında mı / üstünde mi?' seçenekleri.

    Dönüş: [
      {
        'threshold'   : 20.0,
        'question'    : 'Seçtiğiniz aralıkta kritik bir yasal sınır (%20) var...',
        'below'       : { range dict — üst sınır = eşik },
        'above'       : { range dict — alt sınır = eşik },
        'classification_changes': True/False,  # eşik gerçekten sınıfı değiştiriyor mu
      }
    ]

    Eğer liste boşsa → aralık zaten net, refinement gerekmez.
    """
    if hazard_classes is None:
        hazard_classes = _fetch_hazard_classes(cas)

    comp_gcl, gcl_thresholds = _build_comp_gcl(
        hazard_classes, scl_thresholds or [], m_factor_acute, m_factor_chronic
    )

    # Seçilen aralığın içindeki eşikler
    internal = sorted(t for t in gcl_thresholds if lower < t < upper)

    refinements = []
    for thr in internal:
        # "altında" → thr dahil değil (exclusive_upper=True)
        # "üstünde" → thr dahil (normal üst sınır mantığı)
        below = _classify_range(lower, thr,  comp_gcl, hazard_classes, lang,
                                gcl_thresholds, exclusive_upper=True)
        above = _classify_range(thr,   upper, comp_gcl, hazard_classes, lang,
                                gcl_thresholds, exclusive_upper=False)

        # Eşik gerçekten sınıfı değiştiriyor mu?
        changes = (
            set(below['mixture_classes']) != set(above['mixture_classes']) or
            below['signal'] != above['signal']
        )

        # Soru metni (çok dilli)
        q_texts = {
            'TR': (f'Seçtiğiniz aralıkta kritik bir yasal sınır '
                   f'(%{_fmt(thr)}) bulunmaktadır.\n'
                   f'Gerçek konsantrasyonunuz bu sınırın altında mı, üstünde mi?'),
            'EN': (f'Your selected range contains a critical legal limit '
                   f'({_fmt(thr)}%).\n'
                   f'Is your actual concentration below or above this limit?'),
            'DE': (f'Ihr gewählter Bereich enthält einen kritischen Grenzwert '
                   f'({_fmt(thr)} %).\n'
                   f'Liegt Ihre tatsächliche Konzentration darunter oder darüber?'),
        }

        refinements.append({
            'threshold'              : thr,
            'threshold_label'        : f'%{_fmt(thr)}',
            'question'               : q_texts.get(lang, q_texts['TR']),
            'below'                  : below,
            'above'                  : above,
            'classification_changes' : changes,
            'below_label'            : _btn_label(lower, thr, lang, 'below'),
            'above_label'            : _btn_label(thr, upper, lang, 'above'),
        })

    return refinements


# ---------------------------------------------------------------------------
# Dahili yardımcılar
# ---------------------------------------------------------------------------

def _build_comp_gcl(
    hazard_classes: list[str],
    scl_thresholds: list[float],
    m_acute: int,
    m_chronic: int,
) -> tuple[list[tuple], set[float]]:
    """GCL giriş listesini ve eşik kümesini oluştur."""
    comp_gcl: list[tuple] = []
    gcl_thresholds: set[float] = set()
    for hc in hazard_classes:
        nkey = _normalize_class(hc)
        entries = list(GCL.get(nkey, []))
        if 'aquatic' in nkey:
            mf = m_acute if 'acute' in nkey else m_chronic
            entries = [(t / mf, cls, h) for t, cls, h in entries]
        comp_gcl.extend(entries)
        for t, _, _ in entries:
            gcl_thresholds.add(round(t, 4))
    for t in scl_thresholds:
        gcl_thresholds.add(round(t, 4))
    return comp_gcl, gcl_thresholds


def _classify_range(
    lo: float,
    hi: float,
    comp_gcl: list[tuple],
    hazard_classes: list[str],
    lang: str,
    gcl_thresholds: set[float],
    exclusive_upper: bool = False,
) -> dict:
    """
    Tek bir [lo, hi] aralığını sınıflandır ve dict döndür.

    exclusive_upper=True → üst sınır eşiğin tam altı anlamına gelir
      (kullanıcı '%10-%20 aralığındayım' seçtiğinde %20 dahil değil)
    """
    # En kötü durum = üst sınır.
    # exclusive_upper → eşiğin hemen altı (< threshold mantığı için)
    rep_conc = hi - 1e-9 if exclusive_upper and hi > 0 else hi

    raw_active: list[str] = []
    active_h:   list[str] = []
    for threshold, mix_class, h_code in comp_gcl:
        if rep_conc >= threshold and mix_class not in raw_active:
            raw_active.append(mix_class)
            for h in h_code.split('/'):
                if h and h not in active_h:
                    active_h.append(h)

    active_classes = _apply_dominance(raw_active)
    signal  = _dominant_signal(active_classes)
    picts   = _pictograms(active_classes)
    color   = SIGNAL_COLORS.get(signal, SIGNAL_COLORS[''])

    if active_classes:
        hazard_label = ' + '.join(_label(c, lang) for c in active_classes[:3])
        if len(active_classes) > 3:
            hazard_label += f' (+{len(active_classes)-3})'
    else:
        hazard_label = LABELS['unclassified'].get(lang, 'Sınıflandırılmamış')

    if lo == 0.0:
        range_label = f'≤ %{_fmt(hi)}'
    elif hi == 100.0:
        range_label = f'%{_fmt(lo)} – %100'
    else:
        range_label = f'%{_fmt(lo)} – %{_fmt(hi)}'

    return {
        'lower'          : lo,
        'upper'          : hi,
        'range_label'    : range_label,
        'mixture_classes': active_classes,
        'h_codes'        : active_h,
        'hazard_label'   : hazard_label,
        'signal'         : signal,
        'pictograms'     : picts,
        'color'          : color,
        'select_option'  : f'{range_label}   [{hazard_label}]',
        'is_pure'        : False,
        'split_points'   : [],
        'needs_refinement': False,
    }


def _pure_option(hazard_classes: list[str], lang: str) -> dict:
    """Saf madde (%100) seçeneği."""
    raw_classes = [hc for hc in hazard_classes if hc]
    raw_signal  = _dominant_signal(raw_classes)
    raw_picts   = _pictograms(raw_classes)
    pure_label  = ' + '.join(_label(hc, lang) for hc in raw_classes[:3])
    if len(raw_classes) > 3:
        pure_label += f' (+{len(raw_classes)-3})'
    if not pure_label:
        pure_label = LABELS['unclassified'].get(lang, 'Sınıflandırılmamış')
    return {
        'lower': 100.0, 'upper': 100.0,
        'range_label': '%100 (Saf Madde)',
        'mixture_classes': raw_classes, 'h_codes': [],
        'hazard_label': pure_label,
        'signal': raw_signal, 'pictograms': raw_picts,
        'color': SIGNAL_COLORS.get(raw_signal, SIGNAL_COLORS['']),
        'select_option': f'%100 (Saf Madde)   [{pure_label}]',
        'is_pure': True, 'split_points': [], 'needs_refinement': False,
    }


def _btn_label(lo: float, hi: float, lang: str, side: str) -> str:
    """Refinement butonu etiketi: '%10 – %20 aralığındayım' """
    rng = f'%{_fmt(lo)} – %{_fmt(hi)}'
    tmpl = {
        'TR': f'{rng} aralığındayım',
        'EN': f'I am in the {rng} range',
        'DE': f'Ich bin im Bereich {rng}',
    }
    return tmpl.get(lang, tmpl['TR'])


# ---------------------------------------------------------------------------
# HTML <select> Oluşturucu
# ---------------------------------------------------------------------------

def build_select_html(ranges: list[dict], selected_value: str = '') -> str:
    """
    Dropdown için hazır <option> HTML listesi döndür.
    Her option'a renk ve data-signal attribute'u eklenir.
    """
    parts = ['<option value="">-- Konsantrasyon Aralığı Seçin --</option>']
    for r in ranges:
        val  = f"{r['lower']}-{r['upper']}"
        sel  = ' selected' if val == selected_value else ''
        pict = ','.join(r['pictograms'])
        parts.append(
            f'<option value="{val}" '
            f'data-signal="{r["signal"]}" '
            f'data-pictograms="{pict}" '
            f'data-color="{r["color"]}" '
            f'data-h-codes="{",".join(r["h_codes"])}"{sel}>'
            f'{r["select_option"]}'
            f'</option>'
        )
    return '\n'.join(parts)
