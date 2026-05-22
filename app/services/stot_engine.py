"""
STOTEngine — CLP (AT) No 1272/2008 Ek I §3.9
STOT RE (Tekrarlı Maruziyet) karışım hesaplama

JS stot_engine.js'nin Python karşılığı.

H372 (STOT RE 1): organ bazlı Cat1 toplamı ≥ %1.0
H373 (STOT RE 2): organ bazlı Cat2 toplamı ≥ %10.0
"""

from typing import List, Dict

_ORGAN_MAP = {
    'upper respiratory': 'üst solunum yolu',
    'respiratory':       'solunum sistemi',
    'nervous system':    'sinir sistemi',
    'liver':             'karaciğer',
    'kidney':            'böbrek',
    'blood':             'kan',
    'heart':             'kalp',
    'eyes':              'gözler',
    'skin':              'deri',
    'bone marrow':       'kemik iliği',
    'thyroid':           'tiroid',
}


def _normalize_organ(raw: str) -> str:
    if not raw:
        return ''
    r = raw.lower().strip()
    for en, tr in _ORGAN_MAP.items():
        if en in r:
            return tr
    return raw


def _extract_organs(h_code: str) -> List[str]:
    import re
    m = re.search(r'\(([^)]+)\)', h_code)
    if not m:
        return []
    parts = re.split(r'[,;]', m.group(1))
    return [_normalize_organ(p.strip()) for p in parts if p.strip()]


def calculate(comps: List[Dict]) -> Dict:
    """
    STOT RE hesapla.

    Returns:
        {
          'results': [...],
          'analytic_results': [...],
          'h_codes': [...],
          'has_general': bool,
          'general_cat1': float,
          'general_cat2': float,
          'warnings': []
        }
    """
    organ_sums: Dict[str, Dict] = {}
    general_cat1 = 0.0
    general_cat2 = 0.0
    results, analytic_results = [], []

    for c in comps:
        conc = float(c.get('concMax') or c.get('conc') or 0)
        if conc <= 0:
            continue

        for h in (c.get('hazards') or []):
            code = (h.get('h_code') or '').replace('*', '').strip()[:4]
            cat  = 1 if code == 'H372' else (2 if code == 'H373' else None)
            if cat is None:
                continue

            organs = _extract_organs(h.get('h_code') or '')

            if not organs:
                if cat == 1:
                    general_cat1 += conc
                else:
                    general_cat2 += conc
            else:
                for org in organs:
                    if org not in organ_sums:
                        organ_sums[org] = {'cat1': 0.0, 'cat2': 0.0, 'sources': []}
                    if cat == 1:
                        organ_sums[org]['cat1'] += conc
                    else:
                        organ_sums[org]['cat2'] += conc
                    organ_sums[org]['sources'].append({
                        'name': c.get('name') or c.get('cas') or '', 'conc': conc, 'cat': cat
                    })

    # Organ belirsiz maddeler tüm organlara muhafazakâr olarak eklenir
    for org in organ_sums:
        organ_sums[org]['cat1'] += general_cat1
        organ_sums[org]['cat2'] += general_cat2

    # Sonuç değerlendirme
    for org, sums in organ_sums.items():
        if sums['cat1'] >= 1.0:
            results.append({
                'h': 'H372', 'h_class': 'STOT RE 1', 'organ': org, 'signal': 'Danger',
                'reason': f"{org}: STOT RE 1 toplamı %{sums['cat1']:.1f} ≥ %1.0 (KKDİK Ek-2, Tablo 3.9.4)",
            })
        elif sums['cat2'] >= 10.0:
            results.append({
                'h': 'H373', 'h_class': 'STOT RE 2', 'organ': org, 'signal': 'Warning',
                'reason': f"{org}: STOT RE 2 toplamı %{sums['cat2']:.1f} ≥ %10.0 (KKDİK Ek-2, Tablo 3.9.4)",
            })

    # Analitik mod (genel katkı hariç)
    for org, sums in organ_sums.items():
        c1 = sums['cat1'] - general_cat1
        c2 = sums['cat2'] - general_cat2
        if c1 >= 1.0:
            analytic_results.append({
                'h': 'H372', 'h_class': 'STOT RE 1', 'organ': org, 'signal': 'Danger',
                'reason': f"{org}: Eşleşen Cat1=%{c1:.1f} ≥ %1.0",
                'general_excl': general_cat1,
            })
        elif c2 >= 10.0:
            analytic_results.append({
                'h': 'H373', 'h_class': 'STOT RE 2', 'organ': org, 'signal': 'Warning',
                'reason': f"{org}: Eşleşen Cat2=%{c2:.1f} ≥ %10.0",
                'general_excl': general_cat2,
            })

    # Organ belirsiz — genel havuz (hiç organ eşleşmesi yoksa)
    if not organ_sums:
        if general_cat1 >= 1.0:
            results.append({
                'h': 'H372', 'h_class': 'STOT RE 1', 'organ': 'Genel (organ belirsiz)',
                'signal': 'Danger',
                'reason': f'Genel: Cat1=%{general_cat1:.1f} ≥ %1.0',
            })
        elif general_cat2 >= 10.0:
            results.append({
                'h': 'H373', 'h_class': 'STOT RE 2', 'organ': 'Genel (organ belirsiz)',
                'signal': 'Warning',
                'reason': f'Genel: Cat2=%{general_cat2:.1f} ≥ %10.0',
            })

    h_codes = list({r['h'] for r in results})

    return {
        'results':          results,
        'analytic_results': analytic_results,
        'h_codes':          h_codes,
        'has_general':      general_cat1 > 0 or general_cat2 > 0,
        'general_cat1':     general_cat1,
        'general_cat2':     general_cat2,
        'warnings':         [],
    }
