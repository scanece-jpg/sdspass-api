"""
STOTEngine — CLP (AT) No 1272/2008 Ek I §3.9
STOT RE (Tekrarlı Maruziyet) karışım hesaplama

H372 (STOT RE 1): organ Cat1 toplamı ≥ %10.0 (generic) VEYA madde SCL_H372 ≤ konsantrasyon
H373 (STOT RE 2): Cat1 %1.0–%10.0 VEYA Cat2 ≥ %10.0 (generic) VEYA SCL_H373 ≤ konsantrasyon
SCL generic eşiğin önüne geçer — CLP Madde 10(3) / KKDİK Ek-2 Madde 10
Kaynak: CLP Ek-1 §3.9, Tablo 3.9.4
"""

from typing import List, Dict

# ─── SABİTLER (stot_re_service'den taşındı) ──────────────────────────────────

GENERAL_ORGAN = 'Genel (organ belirsiz)'  # Organ belirtilmemiş sentinel

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
    'respiratory tract': 'respiratory tract',
    'respiratory system': 'respiratory system',
    'eye': 'eyes',
    'gi tract': 'gastro-intestinal tract',
    'gastrointestinal tract': 'gastro-intestinal tract',
    'gi': 'gastro-intestinal tract',
    'bone marrow': 'bone',
    'thymus': 'immune system',
    'spleen': 'immune system',
}

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
        scl_organ[org] = {'h_code': trig_h, 'reasons': [reason]}
    else:
        if trig_h == 'H372' and scl_organ[org]['h_code'] == 'H373':
            scl_organ[org]['h_code'] = 'H372'
        scl_organ[org]['reasons'].append(reason)


def _h_worse(current: 'str | None', new: str) -> str:
    """H372 > H373 önceliği."""
    return 'H372' if (current == 'H372' or new == 'H372') else new


def calculate(comps: List[Dict]) -> Dict:
    """
    STOT RE hesapla — CLP §3.9.5.4: toplamsallık yok.
    Her bileşen kendi konsantrasyonuyla tek başına Tablo 3.9.4 eşiklerine bakılır;
    farklı bileşenler toplanmaz. En ağır tekil sonuç (H372 > H373) seçilir.

    Returns:
        {
          'results': [...],
          'analytic_results': [...],
          'h_codes': [...],
          'has_general': bool,
          'general_cat1': float,  # backward compat — her zaman 0.0
          'general_cat2': float,  # backward compat — her zaman 0.0
          'warnings': []
        }
    """
    # organ → {'h_code': 'H372'|'H373'|None, 'sources': [...]}
    organ_best: Dict[str, Dict] = {}
    general_best_h: 'str | None' = None  # organ belirsiz bileşenler — en kötü tekil
    general_sources: list = []
    results: list = []
    scl_organ: Dict[str, Dict] = {}

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

            scl_h372 = _get_scl_cmin(c, 'H372')
            scl_h373 = _get_scl_cmin(c, 'H373')

            if cat == 1 and (scl_h372 is not None or scl_h373 is not None):
                # SCL → bireysel değerlendirme, generic havuza katılmaz
                for org in (organs or [GENERAL_ORGAN]):
                    if scl_h372 is not None and conc >= scl_h372:
                        _scl_update(scl_organ, org, 'H372',
                                    f"{name} %{conc:.3g} ≥ SCL_H372=%{scl_h372}")
                    elif scl_h373 is not None and conc >= scl_h373:
                        _scl_update(scl_organ, org, 'H373',
                                    f"{name} %{conc:.3g} ≥ SCL_H373=%{scl_h373}")

            elif cat == 2 and scl_h373 is not None:
                for org in (organs or [GENERAL_ORGAN]):
                    if conc >= scl_h373:
                        _scl_update(scl_organ, org, 'H373',
                                    f"{name} %{conc:.3g} ≥ SCL_H373=%{scl_h373}")

            else:
                # Generic — Tablo 3.9.4, bireysel değerlendirme (toplama yok)
                this_h: 'str | None' = None
                if cat == 1:
                    if   conc >= 10.0: this_h = 'H372'
                    elif conc >=  1.0: this_h = 'H373'
                else:  # cat == 2
                    if conc >= 10.0:   this_h = 'H373'

                if this_h is None:
                    continue  # eşik altı — katkı yok

                src = {'name': name, 'conc': conc, 'cat': cat, 'h': this_h}

                if not organs:
                    general_best_h = _h_worse(general_best_h, this_h)
                    general_sources.append(src)
                else:
                    for org in organs:
                        if org not in organ_best:
                            organ_best[org] = {'h_code': None, 'sources': []}
                        organ_best[org]['h_code'] = _h_worse(organ_best[org]['h_code'], this_h)
                        organ_best[org]['sources'].append(src)

    # Organ belirsiz bileşenler: eşiği tek başına aşıyorsa muhafazakâr uygulanır
    if general_best_h is not None:
        if not organ_best:
            organ_best[GENERAL_ORGAN] = {'h_code': general_best_h, 'sources': general_sources}
        else:
            for org in organ_best:
                organ_best[org]['h_code'] = _h_worse(organ_best[org]['h_code'], general_best_h)
                organ_best[org]['sources'].extend(general_sources)

    # Generic sonuçlar — Tablo 3.9.4
    for org, data in organ_best.items():
        h = data['h_code']
        if h is None:
            continue
        srcs = data['sources']
        if h == 'H372':
            parts = [f"{s['name']} %{s['conc']:.3g} (Cat1≥%10.0→H372)"
                     for s in srcs if s['h'] == 'H372']
        else:
            parts = []
            for s in srcs:
                if s.get('cat') == 1:
                    parts.append(f"{s['name']} %{s['conc']:.3g} (Cat1 %1–%10→H373)")
                else:
                    parts.append(f"{s['name']} %{s['conc']:.3g} (Cat2≥%10.0→H373)")
        results.append({
            'h_code':  h,
            'h_class': 'STOT RE 1' if h == 'H372' else 'STOT RE 2',
            'organ':   org,
            'signal':  'Danger' if h == 'H372' else 'Warning',
            'reason':  f"{org}: {'; '.join(parts)} (CLP §3.9, Tablo 3.9.4)",
        })

    # SCL sonuçlarını ekle veya mevcut generic sonuçla birleştir
    generic_by_organ = {r['organ']: r for r in results}
    for org, sd in scl_organ.items():
        trig_h  = sd['h_code']
        scl_rsn = f"{org}: {'; '.join(sd['reasons'])} (CLP Art.10(3), Tablo 3.9.4)"
        if org not in generic_by_organ:
            results.append({
                'h_code':  trig_h,
                'h_class': 'STOT RE 1' if trig_h == 'H372' else 'STOT RE 2',
                'organ':   org,
                'signal':  'Danger' if trig_h == 'H372' else 'Warning',
                'reason':  scl_rsn,
                'scl_based': True,
            })
        elif trig_h == 'H372' and generic_by_organ[org]['h_code'] == 'H373':
            r = generic_by_organ[org]
            r['h_code']    = 'H372'
            r['h_class']   = 'STOT RE 1'
            r['signal']    = 'Danger'
            r['reason']   += f'; + SCL: {scl_rsn}'
            r['scl_based'] = True

    h_codes = list({r['h_code'] for r in results})

    return {
        'results':          results,
        'analytic_results': list(results),  # backward compat — bireysel modda aynı liste
        'h_codes':          h_codes,
        'has_general':      general_best_h is not None,
        'general_cat1':     0.0,  # toplama kaldırıldı; backward compat için 0.0
        'general_cat2':     0.0,
        'warnings':         [],
    }
