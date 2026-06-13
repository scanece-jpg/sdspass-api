"""
STOT RE Toplamı Servisi
=======================
CLP Annex I Tablo 3.9.4 — Specific Target Organ Toxicity (Repeated Exposure)

Temel Kural:
  Aynı hedef organ → konsantrasyonlar toplanır → cut-off kontrolü
  Farklı hedef organ → toplanmaz, ayrı değerlendirilir
  Organ belirtilmemiş → muhafazakâr (tüm organlara eklenir)

Cut-off'lar:
  STOT RE 1 (H372): Kat1 bileşen toplamı ≥ %1.0
  STOT RE 2 (H373): Kat2 bileşen toplamı ≥ %10.0

Organ Tespiti:
  H kod içinden parse edilir: 'H373 (nervous system)' → nervous system
  521 maddede organ belirtilmemiş (H372 **) → genel grup
  126 maddede organ bilgisi mevcut

Organ Normalizasyonu:
  'blood system' → 'blood'
  'central nervous system' → 'nervous system'
  'kidney' → 'kidneys'
  (ORGAN_ALIASES sözlüğüne bakın)
"""
import re
from typing import List, Dict, Optional, Any


# ─── ORGAN NORMALIZASYON ─────────────────────────────────────────────────────

# Eş anlamlı organ isimlerini birleştir
ORGAN_ALIASES = {
    'blood system': 'blood',
    'haematopoietic system': 'blood',
    'haematopoietic': 'blood',
    'cns': 'nervous system',
    'central nervous system': 'nervous system',
    'peripheral nervous system': 'nervous system',
    'kidney': 'kidneys',
    'renal': 'kidneys',
    'hepatic': 'liver',
    'lung': 'lungs',
    'respiratory tract': 'respiratory tract',   # ayrı organ — akciğerlerle birleştirilmez
    'respiratory system': 'respiratory system', # CLP H372/H373 ayrı hedef organ
    'eye': 'eyes',
    'gi tract': 'gastro-intestinal tract',
    'gastrointestinal tract': 'gastro-intestinal tract',
    'gi': 'gastro-intestinal tract',
    'bone marrow': 'bone',
    'thymus': 'immune system',
    'spleen': 'immune system',
}

GENERAL_ORGAN = '__general__'  # Organ belirtilmemiş

# Organ adı Türkçe çevirisi
ORGAN_TR = {
    'blood':                    'kan',
    'nervous system':           'sinir sistemi',
    'kidneys':                  'böbrekler',
    'liver':                    'karaciğer',
    'lungs':                    'akciğerler',
    'respiratory tract':        'solunum yolu',
    'respiratory system':       'solunum sistemi',
    'eyes':                     'gözler',
    'gastro-intestinal tract':  'gastrointestinal sistem',
    'skin':                     'cilt',
    'thyroid':                  'tiroid bezi',
    'bone':                     'kemik iliği',
    'immune system':            'bağışıklık sistemi',
    'cardiovascular system':    'kardiyovasküler sistem',
    'heart':                    'kalp',
    'teeth':                    'diş',
    'upper respiratory tract':  'üst solunum yolu',
    'nervous system, eyes':     'sinir sistemi ve gözler',
}


def normalize_organ(raw: str) -> str:
    """Organ adını normalize et — virgülle ayrılmış çoklu organları ayır"""
    raw = raw.lower().strip().replace('_', ' ')
    return ORGAN_ALIASES.get(raw, raw)


def extract_organs(h_code: str) -> List[str]:
    """
    H372/H373 h_code'undan organ listesi çıkar.
    'H373 (liver, nervous system)' → ['liver', 'nervous system']
    'H372 **' → ['__general__']
    """
    m = re.search(r'\(([^)]+)\)', h_code)
    if not m:
        return [GENERAL_ORGAN]
    
    raw_organs = m.group(1)
    organs = []
    for part in raw_organs.split(','):
        part = part.strip()
        if part:
            organs.append(normalize_organ(part))
    return organs if organs else [GENERAL_ORGAN]


# ─── ANA HESAP ───────────────────────────────────────────────────────────────

def calculate_stot_re(comp_list: List[Dict]) -> Dict:
    """
    STOT RE hedef organ toplamı.
    
    Args:
        comp_list: [{'cas', 'name', 'conc', 'hazards': [{'h_class', 'h_code'}]}]
    
    Returns:
        {
          'results': [{'organ', 'sum_cat1', 'sum_cat2', 'h_code', 'h_class', 'reason'}],
          'h_codes': ['H372', 'H373'],
          'warnings': [...],
          'organ_details': {organ: {'cat1_sum': %, 'cat2_sum': %, ...}}
        }
    """
    # Organ bazında toplama: {organ: {'cat1': sum%, 'cat2': sum%}}
    organ_sums: Dict[str, Dict] = {}
    warnings = []

    for comp in comp_list:
        cas = comp.get('cas', '')
        conc = float(comp.get('conc', 0) or 0)
        name = comp.get('name') or cas

        for haz in comp.get('hazards', []):
            h_class = haz.get('h_class', '').replace('*', '').strip()
            h_code = haz.get('h_code', '').strip()

            if 'STOT RE 1' in h_class:
                cat = 1
            elif 'STOT RE 2' in h_class:
                cat = 2
            else:
                continue

            organs = extract_organs(h_code)

            for organ in organs:
                if organ not in organ_sums:
                    organ_sums[organ] = {'cat1': 0.0, 'cat2': 0.0, 'sources': []}

                if cat == 1:
                    organ_sums[organ]['cat1'] += conc
                else:
                    organ_sums[organ]['cat2'] += conc

                organ_sums[organ]['sources'].append({
                    'cas': cas, 'name': name, 'conc': conc, 'cat': cat,
                    'h_code': h_code, 'organ': organ
                })

    # General organ grubunu tüm organ toplamlarına ekle (muhafazakâr)
    general = organ_sums.get(GENERAL_ORGAN, {})
    gen_cat1 = general.get('cat1', 0.0)
    gen_cat2 = general.get('cat2', 0.0)

    results = []
    passed_h_codes = set()

    # Her organ için değerlendir
    all_organs = set(organ_sums.keys())

    for organ in all_organs:
        if organ == GENERAL_ORGAN:
            cat1_sum = organ_sums[organ]['cat1']
            cat2_sum = organ_sums[organ]['cat2']
            organ_label = 'Genel (organ belirtilmemiş)'
        else:
            # Organ'ın kendi toplamı + general
            cat1_sum = organ_sums[organ]['cat1'] + gen_cat1
            cat2_sum = organ_sums[organ]['cat2'] + gen_cat2
            organ_label = organ.title()

        sources = organ_sums[organ]['sources']
        if organ != GENERAL_ORGAN and gen_cat1 + gen_cat2 > 0:
            sources = sources + general.get('sources', [])

        # CLP Tablo 3.9.4 cut-off'lar
        # STOT RE 1 (H372): Cat1 bileşen toplamı ≥ %10
        # STOT RE 2 (H373): Cat1 toplamı %1-10 VEYA Cat2 bileşen toplamı ≥ %10
        if cat1_sum >= 10.0:
            h = 'H372'
            h_class = 'STOT RE 1'
            reason = (f"{organ_label}: STOT RE 1 bileşen toplamı %{cat1_sum:.2f} ≥ %10.0"
                     + (f" (genel dahil)" if organ != GENERAL_ORGAN and gen_cat1 > 0 else ""))
            passed_h_codes.add(h)
            results.append({
                'organ': organ_label, 'h_code': h, 'h_class': h_class,
                'cat1_sum': cat1_sum, 'cat2_sum': cat2_sum,
                'reason': reason, 'sources': sources
            })
        elif cat1_sum >= 1.0 or cat2_sum >= 10.0:
            h = 'H373'
            h_class = 'STOT RE 2'
            if cat1_sum >= 1.0:
                reason = (f"{organ_label}: STOT RE 1 bileşen toplamı %{cat1_sum:.2f} — "
                         f"1% ≤ toplam < 10% → karışım STOT RE 2"
                         + (f" (genel dahil)" if organ != GENERAL_ORGAN and gen_cat1 > 0 else ""))
            else:
                reason = (f"{organ_label}: STOT RE 2 bileşen toplamı %{cat2_sum:.2f} ≥ %10.0"
                         + (f" (genel dahil)" if organ != GENERAL_ORGAN and gen_cat2 > 0 else ""))
            passed_h_codes.add(h)
            results.append({
                'organ': organ_label, 'h_code': h, 'h_class': h_class,
                'cat1_sum': cat1_sum, 'cat2_sum': cat2_sum,
                'reason': reason, 'sources': sources
            })
        elif cat1_sum >= 0.1 or cat2_sum >= 1.0:
            # Eşiğin altında ama yakın — uyarı
            warnings.append(
                f"STOT RE uyarı — {organ_label}: Cat1=%{cat1_sum:.2f}, Cat2=%{cat2_sum:.2f} "
                f"(eşik: Cat1≥1% veya Cat2≥10%)"
            )

    # Organ bilgisi olmayanlara uyarı
    if gen_cat1 > 0 or gen_cat2 > 0:
        warnings.append(
            f"STOT RE: {len(general.get('sources', []))} bileşen için hedef organ belirtilmemiş "
            f"(H372/H373 genel). Bu bileşenler tüm organ toplamlarına eklendi (muhafazakâr)."
        )

    # ─── Analitik mod: sadece eşleşen organlar (genel grup hariç) ───────────
    analytic_results = []
    analytic_h_codes = set()

    for organ in all_organs:
        if organ == GENERAL_ORGAN:
            continue  # Genel grubu analitik'e dahil etme
        cat1_only = organ_sums[organ]['cat1']  # Sadece eşleşen
        cat2_only = organ_sums[organ]['cat2']
        organ_label = organ.title()

        if cat1_only >= 10.0:
            analytic_h_codes.add('H372')
            analytic_results.append({
                'organ': organ_label, 'h_code': 'H372', 'h_class': 'STOT RE 1',
                'cat1_sum': cat1_only, 'cat2_sum': cat2_only,
                'reason': f"{organ_label}: Sadece eşleşen Cat1=%{cat1_only:.2f} ≥ %10.0",
                'general_excluded': gen_cat1
            })
        elif cat1_only >= 1.0 or cat2_only >= 10.0:
            analytic_h_codes.add('H373')
            if cat1_only >= 1.0:
                reason = f"{organ_label}: Sadece eşleşen Cat1=%{cat1_only:.2f} — 1% ≤ toplam < 10% → STOT RE 2"
            else:
                reason = f"{organ_label}: Sadece eşleşen Cat2=%{cat2_only:.2f} ≥ %10.0"
            analytic_results.append({
                'organ': organ_label, 'h_code': 'H373', 'h_class': 'STOT RE 2',
                'cat1_sum': cat1_only, 'cat2_sum': cat2_only,
                'reason': reason,
                'general_excluded': gen_cat2
            })

    # Genel grup kendi başına değerlendir
    if gen_cat1 >= 10.0:
        analytic_h_codes.add('H372')
        analytic_results.append({
            'organ': 'Genel (organ belirtilmemiş)',
            'h_code': 'H372', 'h_class': 'STOT RE 1',
            'cat1_sum': gen_cat1, 'cat2_sum': gen_cat2,
            'reason': f"Genel: Cat1=%{gen_cat1:.2f} ≥ %10.0 (organ bilinmiyor)",
            'general_excluded': 0
        })
    elif gen_cat1 >= 1.0 or gen_cat2 >= 10.0:
        analytic_h_codes.add('H373')
        if gen_cat1 >= 1.0:
            gen_reason = f"Genel: Cat1=%{gen_cat1:.2f} — 1% ≤ toplam < 10% → STOT RE 2 (organ bilinmiyor)"
        else:
            gen_reason = f"Genel: Cat2=%{gen_cat2:.2f} ≥ %10.0 (organ bilinmiyor)"
        analytic_results.append({
            'organ': 'Genel (organ belirtilmemiş)',
            'h_code': 'H373', 'h_class': 'STOT RE 2',
            'cat1_sum': gen_cat1, 'cat2_sum': gen_cat2,
            'reason': gen_reason,
            'general_excluded': 0
        })

    return {
        # Muhafazakâr (CLP yasal zorunluluk)
        'results': results,
        'h_codes': sorted(list(passed_h_codes)),
        'warnings': warnings,
        # Analitik (KDU bilgi notu)
        'analytic_results': analytic_results,
        'analytic_h_codes': sorted(list(analytic_h_codes)),
        'has_general': (gen_cat1 + gen_cat2) > 0,
        'general_cat1': gen_cat1,
        'general_cat2': gen_cat2,
        # Detay
        'organ_details': {
            organ: {
                'cat1_sum': data['cat1'],
                'cat2_sum': data['cat2'],
                'sources': data['sources']
            }
            for organ, data in organ_sums.items()
        }
    }
