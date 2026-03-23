"""
Non-Additivity Servisi
======================
CLP Annex I Tablo 3.2.4 / 3.3.4 — Skin/Eye non-additivity

Neden Gerekli:
  Fenol, aldehit, güçlü asit/baz gibi maddeler deri/göz için
  standart toplama kuralıyla değil, özel eşiklerle sınıflandırılır.

Non-Additivity Grupları:
  Fenollar     → Skin Corr. eşiği ≥%1 (generic %3 yerine)
  Aldehitler   → Skin Corr. eşiği ≥%1
  Güçlü asitler (pH<2) → Skin Corr. ≥%1
  Güçlü bazlar (pH>11.5) → Skin Corr. ≥%1
  Surfaktanlar → Skin Irrit. ≥%3

Çıktı:
  override: bool    → Non-additivity var mı
  skin_result       → Skin Corr./Irrit. sonucu
  eye_result        → Eye Dam./Irrit. sonucu
  non_additivity_flags → Hangi maddeler tetikledi
"""
from typing import List, Dict, Optional, Tuple

# ─── NON-ADDITIVITY GRUPLARI ─────────────────────────────────────────────────

# CAS listesi — bilinen non-additivity maddeleri
NON_ADDITIVITY_CAS = {
    # Fenoller
    '108-95-2',   # phenol
    '59-50-7',    # 4-chloro-3-methylphenol (chlorocresol)
    '1319-77-3',  # cresol (mixed isomers)
    '95-48-7',    # o-cresol
    '108-39-4',   # m-cresol
    '106-44-5',   # p-cresol
    '95-95-4',    # 2,4,5-trichlorophenol
    '88-06-2',    # 2,4,6-trichlorophenol
    '120-83-2',   # 2,4-dichlorophenol
    '51-28-5',    # 2,4-dinitrophenol
    '100-02-7',   # 4-nitrophenol
    '106-48-9',   # 4-chlorophenol
    '95-57-8',    # 2-chlorophenol
    '90-43-7',    # 2-phenylphenol
    # Aldehitler
    '50-00-0',    # formaldehyde
    '111-30-8',   # glutaraldehyde
    '107-22-2',   # glyoxal
    '98-01-1',    # furfural
    '123-38-6',   # propionaldehyde
    '66-25-1',    # hexanal
    # Güçlü asitler
    '7664-93-9',  # sulfuric acid
    '7697-37-2',  # nitric acid
    '7647-01-0',  # hydrochloric acid
    '7664-38-2',  # phosphoric acid
    '75-31-0',    # isopropylamine (pKa ~10.6, güçlü baz ama asit de)
    '79-10-7',    # acrylic acid
    '64-19-7',    # acetic acid (>10%)
    '144-55-8',   # sodium bicarbonate (hafif baz — düşük öncelik)
    '75-75-2',    # methanesulfonic acid
    # Güçlü bazlar
    '1310-73-2',  # sodium hydroxide
    '1310-58-3',  # potassium hydroxide
    '1305-62-0',  # calcium hydroxide
    '7664-41-7',  # ammonia
    '141-43-5',   # ethanolamine (MEA)
    '111-42-2',   # diethanolamine (DEA)
    '102-71-6',   # triethanolamine (TEA)
    '107-15-3',   # ethylenediamine
    '110-85-0',   # piperazine
    '121-44-8',   # triethylamine
    # Hipoklorit / aşındırıcı inorganik tuzlar
    '7681-52-9',  # sodium hypochlorite
    '7778-54-3',  # calcium hypochlorite
    '10588-01-9', # sodium dichromate
    '7775-09-9',  # sodium chlorate
    '7722-64-7',  # potassium permanganate
}

# İsim bazlı anahtar kelimeler
NON_ADDITIVITY_KEYWORDS = {
    'phenol': ['phenol', 'cresol', 'xylenol', 'naphthol', 'chlorophenol',
               'nitrophenol', 'bisphenol', 'resorcinol', 'catechol', 'hydroquinone'],
    'aldehyde': ['aldehyde', 'aldehyd', 'furfural', 'glyoxal', 'acrolein'],
    'strong_acid': ['sulfuric acid', 'sulphuric acid', 'nitric acid', 'hydrochloric acid',
                    'phosphoric acid', 'hydrobromic acid', 'hydroiodic acid',
                    'sulfonic acid', 'sulphonic acid', 'methanesulfonic', 'trifluoroacetic',
                    'acrylic acid', 'methacrylic acid'],
    'strong_base': ['sodium hydroxide', 'potassium hydroxide', 'calcium hydroxide',
                    'lithium hydroxide', 'barium hydroxide', 'ammonium hydroxide',
                    'ethanolamine', 'diethanolamine', 'triethanolamine', 'morpholine',
                    'piperazine', 'triethylamine', 'ethylenediamine', 'isopropylamine'],
    'surfactant': ['sodium lauryl sulfate', 'sodium laureth sulfate', 'sles', 'sds',
                   'dodecylbenzene sulfonate', 'alkyl sulfate', 'alkyl sulphate',
                   'alkyl ether sulfate', 'betaine', 'cocoamidopropyl'],
    'hypochlorite': ['hypochlorite', 'bleach'],
}

# Skin Corr. ve Eye Dam. sınıfları
SKIN_CORR_CLASSES = {'Skin Corr. 1', 'Skin Corr. 1A', 'Skin Corr. 1B', 'Skin Corr. 1C'}
SKIN_IRRIT_CLASSES = {'Skin Irrit. 2'}
EYE_DAM_CLASSES = {'Eye Dam. 1'}
EYE_IRRIT_CLASSES = {'Eye Irrit. 2'}

# Tablo 3.2.4 eşikleri
TABLE_3_2_4 = {
    'skin_corr':  1.0,   # ≥%1 → Skin Corr. 1
    'skin_irrit': 3.0,   # ≥%3 → Skin Irrit. 2
    'eye_dam':    1.0,   # ≥%1 → Eye Dam. 1
    'eye_irrit':  3.0,   # ≥%3 → Eye Irrit. 2
}

# Göz için ağırlıklı toplam eşikleri (Tablo 3.3.4)
# 10 × [Skin Corr.] + [Eye Irrit.] ≥ 10 → Eye Irrit. 2
EYE_WEIGHTED_THRESHOLD = 10.0


def is_non_additivity(cas: str, name: str) -> Tuple[bool, str]:
    """
    Maddenin non-additivity grubuna girip girmediğini kontrol eder.
    Döner: (bool, grup_adı)
    """
    cas = str(cas).strip()
    name_lower = (name or '').lower()

    # CAS listesi kontrolü
    if cas in NON_ADDITIVITY_CAS:
        return True, 'cas_list'

    # İsim bazlı kontrol
    for group, keywords in NON_ADDITIVITY_KEYWORDS.items():
        if any(kw in name_lower for kw in keywords):
            return True, group

    return False, ''


def classify_skin_eye_non_additivity(components: List[Dict]) -> Dict:
    """
    CLP Annex I Tablo 3.2.4'e göre Skin Corr./Irrit. ve Eye Dam./Irrit.
    sınıflandırması yapar.

    Sadece non-additivity grubundaki maddeler için uygulanır.
    Normal cut-off yaklaşımının YERINI ALIR (override eder).

    components: [{'cas', 'name', 'conc', 'hazards': [...]}]

    Döner: {
        'skin_result': None | {'class': 'Skin Corr. 1', 'h_code': 'H314', ...},
        'eye_result':  None | {'class': 'Eye Dam. 1',   'h_code': 'H318', ...},
        'non_additivity_flags': [...],
        'override': bool,  # True ise normal cut-off hesabını override et
        'details': [...],
    }
    """
    details = []
    non_additivity_flags = []
    skin_corr_sum = 0.0
    skin_irrit_sum = 0.0
    eye_dam_sum = 0.0
    eye_irrit_sum = 0.0

    # Ayrıca normal toplamada kullanılan ağırlıklı göz hesabı için
    skin_corr_for_eye = 0.0  # 10× çarpanla göze katkı

    has_non_additivity = False

    for comp in components:
        cas = str(comp.get('cas', '')).strip()
        name = comp.get('name', '') or ''
        conc = float(comp.get('conc', 0) or 0)
        hazards = comp.get('hazards', [])
        hazard_classes = {h.get('h_class', '').replace('*', '').strip() for h in hazards}

        is_na, na_group = is_non_additivity(cas, name)

        if is_na:
            has_non_additivity = True
            non_additivity_flags.append({
                'cas': cas, 'name': name, 'conc': conc, 'group': na_group
            })

            # Skin Corr. katkısı
            if hazard_classes & SKIN_CORR_CLASSES:
                skin_corr_sum += conc
                skin_corr_for_eye += conc  # göz hesabına da katkı
                details.append({
                    'cas': cas, 'name': name, 'conc': conc,
                    'hazard': next(h for h in hazard_classes if h in SKIN_CORR_CLASSES),
                    'contribution_to': 'skin_corr'
                })

            # Skin Irrit. katkısı (Corr. yoksa)
            if hazard_classes & SKIN_IRRIT_CLASSES and not (hazard_classes & SKIN_CORR_CLASSES):
                skin_irrit_sum += conc
                details.append({
                    'cas': cas, 'name': name, 'conc': conc,
                    'hazard': 'Skin Irrit. 2',
                    'contribution_to': 'skin_irrit'
                })

            # Eye Dam. katkısı
            if hazard_classes & EYE_DAM_CLASSES:
                eye_dam_sum += conc
                details.append({
                    'cas': cas, 'name': name, 'conc': conc,
                    'hazard': 'Eye Dam. 1',
                    'contribution_to': 'eye_dam'
                })

            # Eye Irrit. katkısı
            if hazard_classes & EYE_IRRIT_CLASSES and not (hazard_classes & EYE_DAM_CLASSES):
                eye_irrit_sum += conc
                details.append({
                    'cas': cas, 'name': name, 'conc': conc,
                    'hazard': 'Eye Irrit. 2',
                    'contribution_to': 'eye_irrit'
                })

    if not has_non_additivity:
        return {
            'skin_result': None, 'eye_result': None,
            'non_additivity_flags': [], 'override': False, 'details': []
        }

    # ─── Skin sınıflandırması (Tablo 3.2.4) ──────────────────────────────────
    skin_result = None

    if skin_corr_sum >= TABLE_3_2_4['skin_corr']:
        skin_result = {
            'class': 'Skin Corr. 1', 'h_code': 'H314',
            'pictogram': 'GHS05', 'signal': 'Danger',
            'reason': f'Tablo 3.2.4: Σ Skin Corr. = %{skin_corr_sum:.3f} ≥ %{TABLE_3_2_4["skin_corr"]}',
            'sum': skin_corr_sum,
        }
    elif skin_irrit_sum >= TABLE_3_2_4['skin_irrit']:
        skin_result = {
            'class': 'Skin Irrit. 2', 'h_code': 'H315',
            'pictogram': 'GHS07', 'signal': 'Warning',
            'reason': f'Tablo 3.2.4: Σ Skin Irrit. = %{skin_irrit_sum:.3f} ≥ %{TABLE_3_2_4["skin_irrit"]}',
            'sum': skin_irrit_sum,
        }
    else:
        # Eşiğin altında — karışım sınıflandırılmaz
        skin_result = {
            'class': None, 'h_code': None,
            'reason': (
                f'Tablo 3.2.4: Σ Skin Corr. = %{skin_corr_sum:.3f} < %{TABLE_3_2_4["skin_corr"]} '
                f've Σ Skin Irrit. = %{skin_irrit_sum:.3f} < %{TABLE_3_2_4["skin_irrit"]} '
                f'→ Non-additivity grubu, sınıflandırma ÇIKMAZ'
            ),
            'sum': max(skin_corr_sum, skin_irrit_sum),
        }

    # ─── Eye sınıflandırması (Tablo 3.3.4) ───────────────────────────────────
    # Eye Dam. 1: Σ Eye Dam. ≥ %1
    # Eye Irrit. 2: 10×Σ Skin Corr. + Σ Eye Irrit. ≥ %10
    eye_result = None
    weighted_eye = (10 * skin_corr_for_eye) + eye_irrit_sum

    if eye_dam_sum >= TABLE_3_2_4['eye_dam']:
        eye_result = {
            'class': 'Eye Dam. 1', 'h_code': 'H318',
            'pictogram': 'GHS05', 'signal': 'Danger',
            'reason': f'Tablo 3.3.4: Σ Eye Dam. = %{eye_dam_sum:.3f} ≥ %{TABLE_3_2_4["eye_dam"]}',
            'sum': eye_dam_sum,
        }
    elif weighted_eye >= EYE_WEIGHTED_THRESHOLD:
        eye_result = {
            'class': 'Eye Irrit. 2', 'h_code': 'H319',
            'pictogram': 'GHS07', 'signal': 'Warning',
            'reason': f'Tablo 3.3.4: 10×Σ Skin Corr. + Σ Eye Irrit. = {weighted_eye:.2f} ≥ {EYE_WEIGHTED_THRESHOLD}',
            'sum': weighted_eye,
        }
    else:
        eye_result = {
            'class': None, 'h_code': None,
            'reason': (
                f'Tablo 3.3.4: Eye Dam. %{eye_dam_sum:.3f} < %1, '
                f'10×Skin Corr. + Eye Irrit. = {weighted_eye:.2f} < {EYE_WEIGHTED_THRESHOLD} '
                f'→ Sınıflandırma ÇIKMAZ'
            ),
            'sum': max(eye_dam_sum, weighted_eye),
        }

    return {
        'skin_result': skin_result,
        'eye_result': eye_result,
        'non_additivity_flags': non_additivity_flags,
        'override': True,  # Normal cut-off yerine bu sonucu kullan
        'details': details,
    }
