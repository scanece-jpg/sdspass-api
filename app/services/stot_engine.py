"""
STOTEngine — CLP (AT) No 1272/2008 Ek I §3.9
STOT RE (Tekrarlı Maruziyet) karışım hesaplama

H372 (STOT RE 1): organ Cat1 toplamı ≥ %10.0 (generic) VEYA madde SCL_H372 ≤ konsantrasyon
H373 (STOT RE 2): Cat1 %1.0–%10.0 VEYA Cat2 ≥ %10.0 (generic) VEYA SCL_H373 ≤ konsantrasyon
SCL generic eşiğin önüne geçer — CLP Madde 10(3) / KKDİK Ek-2 Madde 10
Kaynak: CLP Ek-1 §3.9, Tablo 3.9.4
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


def _get_scl_cmin(comp: dict, h_code4: str) -> float | None:
    """Bileşenin SCL listesinden H kodu için c_min döndürür; yoksa None."""
    scl_raw = comp.get('scl', [])
    if isinstance(scl_raw, list):
        for s in scl_raw:
            if not isinstance(s, dict):
                continue
            sh = (s.get('h_code', '') or '').replace('*', '').strip()[:4]
            if sh == h_code4 and s.get('c_min') is not None:
                return float(s['c_min'])
    elif isinstance(scl_raw, dict):
        val = scl_raw.get(h_code4)
        if val is not None:
            return float(val)
    return None


def _scl_update(scl_organ: Dict, org: str, trig_h: str, reason: str) -> None:
    """SCL organ takibini güncelle — H372 > H373 önceliği."""
    if org not in scl_organ:
        scl_organ[org] = {'h': trig_h, 'reasons': [reason]}
    else:
        if trig_h == 'H372' and scl_organ[org]['h'] == 'H373':
            scl_organ[org]['h'] = 'H372'
        scl_organ[org]['reasons'].append(reason)


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
    scl_organ: Dict[str, Dict] = {}  # org → {h: 'H372'|'H373', reasons: [str]}

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
            name   = c.get('name') or c.get('cas') or ''

            # SCL kontrolü — CLP Art. 10(3): SCL generic eşiğin yerini alır
            scl_h372 = _get_scl_cmin(c, 'H372')
            scl_h373 = _get_scl_cmin(c, 'H373')

            if cat == 1 and (scl_h372 is not None or scl_h373 is not None):
                # SCL tanımlı → bireysel değerlendirme, generic havuza katılmaz
                for org in (organs or ['Genel (organ belirsiz)']):
                    if scl_h372 is not None and conc >= scl_h372:
                        _scl_update(scl_organ, org, 'H372',
                                    f"{name} %{conc:.3g} ≥ SCL_H372=%{scl_h372}")
                    elif scl_h373 is not None and conc >= scl_h373:
                        _scl_update(scl_organ, org, 'H373',
                                    f"{name} %{conc:.3g} ≥ SCL_H373=%{scl_h373}")
                    # SCL eşiği altındaysa katkı yok

            elif cat == 2 and scl_h373 is not None:
                # H373 + SCL → bireysel değerlendirme
                for org in (organs or ['Genel (organ belirsiz)']):
                    if conc >= scl_h373:
                        _scl_update(scl_organ, org, 'H373',
                                    f"{name} %{conc:.3g} ≥ SCL_H373=%{scl_h373}")

            else:
                # Generic additive havuz — mevcut davranış
                if not organs:
                    if cat == 1: general_cat1 += conc
                    else:        general_cat2 += conc
                else:
                    for org in organs:
                        if org not in organ_sums:
                            organ_sums[org] = {'cat1': 0.0, 'cat2': 0.0, 'sources': []}
                        if cat == 1: organ_sums[org]['cat1'] += conc
                        else:        organ_sums[org]['cat2'] += conc
                        organ_sums[org]['sources'].append(
                            {'name': name, 'conc': conc, 'cat': cat})

    # Organ belirsiz maddeler tüm organlara muhafazakâr olarak eklenir
    for org in organ_sums:
        organ_sums[org]['cat1'] += general_cat1
        organ_sums[org]['cat2'] += general_cat2

    # Generic sonuçlar — Tablo 3.9.4
    for org, sums in organ_sums.items():
        if sums['cat1'] >= 10.0:
            results.append({
                'h': 'H372', 'h_class': 'STOT RE 1', 'organ': org, 'signal': 'Danger',
                'reason': f"{org}: STOT RE 1 toplamı %{sums['cat1']:.1f} ≥ %10.0 (KKDİK Ek-2, Tablo 3.9.4)",
            })
        elif sums['cat1'] >= 1.0 or sums['cat2'] >= 10.0:
            parts = []
            if sums['cat1'] >= 1.0:
                parts.append(f"STOT RE 1 toplamı %{sums['cat1']:.1f} (%1.0–%10.0 → H373)")
            if sums['cat2'] >= 10.0:
                parts.append(f"STOT RE 2 toplamı %{sums['cat2']:.1f} ≥ %10.0")
            results.append({
                'h': 'H373', 'h_class': 'STOT RE 2', 'organ': org, 'signal': 'Warning',
                'reason': f"{org}: {'; '.join(parts)} (KKDİK Ek-2, Tablo 3.9.4)",
            })

    # SCL sonuçlarını ekle veya mevcut generic sonuçla birleştir
    generic_by_organ = {r['organ']: r for r in results}
    for org, sd in scl_organ.items():
        trig_h    = sd['h']
        scl_rsn   = f"{org}: {'; '.join(sd['reasons'])} (CLP Art.10(3), Tablo 3.9.4)"
        if org not in generic_by_organ:
            results.append({
                'h': trig_h,
                'h_class': 'STOT RE 1' if trig_h == 'H372' else 'STOT RE 2',
                'organ': org,
                'signal': 'Danger' if trig_h == 'H372' else 'Warning',
                'reason': scl_rsn,
                'scl_based': True,
            })
        elif trig_h == 'H372' and generic_by_organ[org]['h'] == 'H373':
            # SCL H372 generic H373'ü geçersiz kılar
            r = generic_by_organ[org]
            r['h']        = 'H372'
            r['h_class']  = 'STOT RE 1'
            r['signal']   = 'Danger'
            r['reason']  += f'; + SCL: {scl_rsn}'
            r['scl_based'] = True

    # Analitik mod (genel katkı hariç) — generic
    for org, sums in organ_sums.items():
        c1 = sums['cat1'] - general_cat1
        c2 = sums['cat2'] - general_cat2
        if c1 >= 10.0:
            analytic_results.append({
                'h': 'H372', 'h_class': 'STOT RE 1', 'organ': org, 'signal': 'Danger',
                'reason': f"{org}: Eşleşen Cat1=%{c1:.1f} ≥ %10.0",
                'general_excl': general_cat1,
            })
        elif c1 >= 1.0 or c2 >= 10.0:
            parts = []
            if c1 >= 1.0:
                parts.append(f"Eşleşen Cat1=%{c1:.1f} (%1.0–%10.0 → H373)")
            if c2 >= 10.0:
                parts.append(f"Eşleşen Cat2=%{c2:.1f} ≥ %10.0")
            analytic_results.append({
                'h': 'H373', 'h_class': 'STOT RE 2', 'organ': org, 'signal': 'Warning',
                'reason': f"{org}: {'; '.join(parts)}",
                'general_excl': general_cat1,
            })

    # SCL sonuçları analitik listede de yer alır
    for org, sd in scl_organ.items():
        trig_h = sd['h']
        analytic_results.append({
            'h': trig_h,
            'h_class': 'STOT RE 1' if trig_h == 'H372' else 'STOT RE 2',
            'organ': org,
            'signal': 'Danger' if trig_h == 'H372' else 'Warning',
            'reason': f"{org}: {'; '.join(sd['reasons'])} (SCL)",
            'scl_based': True,
        })

    # Organ belirsiz — genel havuz (hiç organ eşleşmesi yoksa)
    if not organ_sums:
        if general_cat1 >= 10.0:
            results.append({
                'h': 'H372', 'h_class': 'STOT RE 1', 'organ': 'Genel (organ belirsiz)',
                'signal': 'Danger',
                'reason': f'Genel: Cat1=%{general_cat1:.1f} ≥ %10.0 (Tablo 3.9.4)',
            })
        elif general_cat1 >= 1.0 or general_cat2 >= 10.0:
            parts = []
            if general_cat1 >= 1.0:
                parts.append(f"Cat1=%{general_cat1:.1f} (%1.0–%10.0 → H373)")
            if general_cat2 >= 10.0:
                parts.append(f"Cat2=%{general_cat2:.1f} ≥ %10.0")
            results.append({
                'h': 'H373', 'h_class': 'STOT RE 2', 'organ': 'Genel (organ belirsiz)',
                'signal': 'Warning',
                'reason': f"Genel: {'; '.join(parts)} (Tablo 3.9.4)",
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
