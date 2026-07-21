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
from collections import defaultdict
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

    # İsim bazlı kontrol önce — grup bilgisi daha kesin (CAS'ı gruba atar)
    for group, keywords in NON_ADDITIVITY_KEYWORDS.items():
        if any(kw in name_lower for kw in keywords):
            return True, group

    # CAS listesi: grup bilinmiyor → 'cas_list' (her CAS kendi grubu sayılır)
    if cas in NON_ADDITIVITY_CAS:
        return True, 'cas_list'

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

    # Annex I Tablo 3.2.4/3.3.4: her kimyasal grup BAĞIMSIZ değerlendirilir.
    # Farklı gruplar (fenol + güçlü asit) toplanmaz — her grup kendi eşiğini ayrı karşılar.
    # Aynı grup içindeki bileşenler (ör. 2 farklı fenol) toplanır.
    skin_corr_by_group:   defaultdict = defaultdict(float)
    skin_irrit_by_group:  defaultdict = defaultdict(float)
    eye_dam_by_group:     defaultdict = defaultdict(float)
    eye_irrit_by_group:   defaultdict = defaultdict(float)
    skin_corr_eye_by_group: defaultdict = defaultdict(float)  # 10× çarpan için

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
            # CAS-eşleşmeli ama isimsiz grup → her CAS kendi ayrı grubu (karıştırmama)
            grp_key = na_group if na_group != 'cas_list' else f'cas_{cas}'
            non_additivity_flags.append({
                'cas': cas, 'name': name, 'conc': conc, 'group': na_group
            })

            if hazard_classes & SKIN_CORR_CLASSES:
                skin_corr_by_group[grp_key] += conc
                skin_corr_eye_by_group[grp_key] += conc
                details.append({
                    'cas': cas, 'name': name, 'conc': conc,
                    'hazard': next(h for h in hazard_classes if h in SKIN_CORR_CLASSES),
                    'contribution_to': 'skin_corr', 'group': grp_key,
                })

            if hazard_classes & SKIN_IRRIT_CLASSES and not (hazard_classes & SKIN_CORR_CLASSES):
                skin_irrit_by_group[grp_key] += conc
                details.append({
                    'cas': cas, 'name': name, 'conc': conc,
                    'hazard': 'Skin Irrit. 2',
                    'contribution_to': 'skin_irrit', 'group': grp_key,
                })

            if hazard_classes & EYE_DAM_CLASSES:
                eye_dam_by_group[grp_key] += conc
                details.append({
                    'cas': cas, 'name': name, 'conc': conc,
                    'hazard': 'Eye Dam. 1',
                    'contribution_to': 'eye_dam', 'group': grp_key,
                })

            if hazard_classes & EYE_IRRIT_CLASSES and not (hazard_classes & EYE_DAM_CLASSES):
                eye_irrit_by_group[grp_key] += conc
                details.append({
                    'cas': cas, 'name': name, 'conc': conc,
                    'hazard': 'Eye Irrit. 2',
                    'contribution_to': 'eye_irrit', 'group': grp_key,
                })

    if not has_non_additivity:
        return {
            'skin_result': None, 'eye_result': None,
            'non_additivity_flags': [], 'override': False, 'details': []
        }

    # Tanı için toplam değerler (tüm gruplar birleşik)
    skin_corr_sum  = sum(skin_corr_by_group.values())
    skin_irrit_sum = sum(skin_irrit_by_group.values())
    eye_dam_sum    = sum(eye_dam_by_group.values())
    eye_irrit_sum  = sum(eye_irrit_by_group.values())

    # ─── Skin sınıflandırması (Tablo 3.2.4) — her grup bağımsız ─────────────
    skin_result = None
    all_skin_groups = set(skin_corr_by_group) | set(skin_irrit_by_group)
    for grp in sorted(all_skin_groups):
        g_corr  = skin_corr_by_group.get(grp, 0.0)
        g_irrit = skin_irrit_by_group.get(grp, 0.0)
        if g_corr >= TABLE_3_2_4['skin_corr']:
            skin_result = {
                'class': 'Skin Corr. 1', 'h_code': 'H314',
                'pictogram': 'GHS05', 'signal': 'Danger',
                'reason': f'Tablo 3.2.4 [{grp}]: Σ Skin Corr. = %{g_corr:.3f} ≥ %{TABLE_3_2_4["skin_corr"]}',
                'sum': g_corr,
            }
            break  # en kötü kategori bulundu
        if g_irrit >= TABLE_3_2_4['skin_irrit'] and skin_result is None:
            skin_result = {
                'class': 'Skin Irrit. 2', 'h_code': 'H315',
                'pictogram': 'GHS07', 'signal': 'Warning',
                'reason': f'Tablo 3.2.4 [{grp}]: Σ Skin Irrit. = %{g_irrit:.3f} ≥ %{TABLE_3_2_4["skin_irrit"]}',
                'sum': g_irrit,
            }
    if skin_result is None:
        skin_result = {
            'class': None, 'h_code': None,
            'reason': (
                f'Tablo 3.2.4: Hiçbir grup eşiği aşmadı '
                f'(Σ Skin Corr. = %{skin_corr_sum:.3f} < %{TABLE_3_2_4["skin_corr"]}, '
                f'Σ Skin Irrit. = %{skin_irrit_sum:.3f} < %{TABLE_3_2_4["skin_irrit"]}) '
                f'→ Non-additivity grubu, sınıflandırma ÇIKMAZ'
            ),
            'sum': max(skin_corr_sum, skin_irrit_sum),
        }

    # ─── Eye sınıflandırması (Tablo 3.3.4) — her grup bağımsız ──────────────
    eye_result = None
    all_eye_groups = set(eye_dam_by_group) | set(eye_irrit_by_group) | set(skin_corr_eye_by_group)
    for grp in sorted(all_eye_groups):
        g_dam      = eye_dam_by_group.get(grp, 0.0)
        g_weighted = (10 * skin_corr_eye_by_group.get(grp, 0.0)) + eye_irrit_by_group.get(grp, 0.0)
        if g_dam >= TABLE_3_2_4['eye_dam']:
            eye_result = {
                'class': 'Eye Dam. 1', 'h_code': 'H318',
                'pictogram': 'GHS05', 'signal': 'Danger',
                'reason': f'Tablo 3.3.4 [{grp}]: Σ Eye Dam. = %{g_dam:.3f} ≥ %{TABLE_3_2_4["eye_dam"]}',
                'sum': g_dam,
            }
            break
        if g_weighted >= EYE_WEIGHTED_THRESHOLD and eye_result is None:
            eye_result = {
                'class': 'Eye Irrit. 2', 'h_code': 'H319',
                'pictogram': 'GHS07', 'signal': 'Warning',
                'reason': f'Tablo 3.3.4 [{grp}]: 10×Skin Corr. + Eye Irrit. = {g_weighted:.2f} ≥ {EYE_WEIGHTED_THRESHOLD}',
                'sum': g_weighted,
            }
    if eye_result is None:
        weighted_total = sum(
            10 * skin_corr_eye_by_group.get(g, 0.0) + eye_irrit_by_group.get(g, 0.0)
            for g in all_eye_groups
        ) if all_eye_groups else 0.0
        eye_result = {
            'class': None, 'h_code': None,
            'reason': (
                f'Tablo 3.3.4: Hiçbir grup eşiği aşmadı '
                f'(Eye Dam. %{eye_dam_sum:.3f} < %1, '
                f'ağırlıklı göz toplamı = {weighted_total:.2f} < {EYE_WEIGHTED_THRESHOLD}) '
                f'→ Sınıflandırma ÇIKMAZ'
            ),
            'sum': max(eye_dam_sum, weighted_total),
        }

    return {
        'skin_result': skin_result,
        'eye_result': eye_result,
        'non_additivity_flags': non_additivity_flags,
        'override': True,  # Normal cut-off yerine bu sonucu kullan
        'details': details,
    }
