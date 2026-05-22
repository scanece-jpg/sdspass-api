"""
EcoEngine — CLP (AT) No 1272/2008 Ek I §4.1
Sucul ekoloji + ozon + PBT sınıflandırması

JS eco_engine.js'nin Python karşılığı.

SEA Tablo 4.1.1 / 4.1.2 formülleri:
  sumAcuteM    = Σ(Ci × M_akut)   / 100  → H400: ≥ 0.25
  sumChronicK1 = Σ(Ci × M_kronik) / 100  → H410: ≥ 0.25
  h411Sum      = 10×K1 + K2              → H411: ≥ 0.25
  h412Sum      = 100×K1 + 10×K2 + K3    → H412: ≥ 0.25
  h413Sum      = K1 + K2 + K3            → H413: ≥ 0.25
"""

from typing import List, Dict, Optional

LOG_KOW_DB: Dict[str, float] = {
    '110-54-3': 3.29, '110-82-7': 3.44, '108-88-3': 2.73, '1330-20-7': 3.12,
    '71-43-2':  2.13, '100-41-4': 3.15, '64-17-5': -0.31, '67-63-0':   0.05,
    '71-36-3':  0.88, '67-64-1': -0.24, '111-76-2': 0.83, '50-00-0':   0.35,
    '7681-52-9':-3.4, '7732-18-5':-1.38,'64742-54-7':7.0, '64742-47-8':4.5,
}

READILY_BIO = {
    '64-17-5','67-63-0','71-23-8','71-36-3','67-64-1',
    '78-93-3','141-78-6','7732-18-5','57-55-6','56-81-5','77-92-9','64-19-7',
}

PERSISTENT = {'1330-20-7','108-88-3','110-54-3','71-43-2','100-41-4'}

OZONE_CAS = {
    '75-69-4','75-71-8','76-13-1','76-14-2','76-15-3',
    '75-72-9','75-63-8',
    '74-83-9','74-87-3',
    '56-23-5','67-66-3','79-01-6',
    '353-59-3','354-23-4',
}

PBT_CAS = {
    '57-74-9','319-84-6','319-85-7','58-89-9',
    '72-54-8','50-29-3','76-44-8',
    '118-74-1','87-68-3',
    '757-58-4','36355-01-8','67774-32-7',
    '72629-94-8','1163-19-5',
    '68920-70-7','85535-84-8',
}


def calculate(comps: List[Dict], eco_test_data: Dict = None) -> Dict:
    """
    Sucul ekoloji + ozon + PBT sınıflandırması hesapla.

    Returns:
        {
          'aquatic':        {...} veya None,
          'aquatic_acute':  {...} veya None,
          'ozone':          [...],
          'pbt':            [...],
          'h_codes':        [...]
        }
    """
    if eco_test_data is None:
        eco_test_data = {}

    h_codes: list = []
    sum_acute_m     = 0.0
    sum_chronic_k1  = 0.0
    sum_chronic_k2  = 0.0
    sum_chronic_k3  = 0.0
    ozone: list = []
    pbt:   list = []

    for c in comps:
        cas  = (c.get('cas') or c.get('cas_no') or '').strip()
        conc = float(c.get('concMax') or c.get('conc') or 0)
        if conc <= 0:
            continue

        m_acute   = float((c.get('m_factors') or {}).get('acute',   1) or 1)
        m_chronic = float((c.get('m_factors') or {}).get('chronic', 1) or 1)

        # Bileşen sucul H kodları — çift sayımı önlemek için Set
        haz_set = set()
        for h in (c.get('hazards') or []):
            code = (h.get('h_code') or '').replace('*','').strip()[:4]
            if code in ('H400','H410','H411','H412','H413'):
                haz_set.add(code)

        # H410: hem akut hem kronik hesaba girer; H400 da varsa H400 atlanır
        if 'H410' in haz_set:
            if conc >= (0.1 / max(m_chronic, 1)):
                sum_acute_m    += (conc * m_acute)   / 100
                sum_chronic_k1 += (conc * m_chronic) / 100
        elif 'H400' in haz_set:
            if conc >= (0.1 / max(m_acute, 1)):
                sum_acute_m += (conc * m_acute) / 100

        if 'H411' in haz_set and conc >= 1.0:
            sum_chronic_k2 += conc / 100

        if ('H412' in haz_set or 'H413' in haz_set) and conc >= 1.0:
            sum_chronic_k3 += conc / 100

        if cas in OZONE_CAS and conc >= 0.1:
            ozone.append({'name': c.get('name') or cas, 'cas': cas, 'conc': conc})
        if cas in PBT_CAS and conc >= 0.1:
            pbt.append({'name': c.get('name') or cas, 'cas': cas, 'conc': conc})

    # ── SEA Tablo 4.1.2 — kronik eşik kararı ────────────────────────────────
    h411_sum = 10  * sum_chronic_k1 + sum_chronic_k2
    h412_sum = 100 * sum_chronic_k1 + 10 * sum_chronic_k2 + sum_chronic_k3
    h413_sum = sum_chronic_k1 + sum_chronic_k2 + sum_chronic_k3

    aquatic: Optional[Dict] = None
    if sum_chronic_k1 >= 0.25:
        aquatic = {
            'h': 'H410', 'h_class': 'Aquatic Chronic 1',
            'formula': f'Σ(Ci×M_kr)/100={sum_chronic_k1:.4f} ≥ 0.25 [=%{sum_chronic_k1*100:.2f}≥%25]',
        }
    elif h411_sum >= 0.25:
        aquatic = {
            'h': 'H411', 'h_class': 'Aquatic Chronic 2',
            'formula': f'10×K1+K2={h411_sum:.4f} ≥ 0.25',
        }
    elif h412_sum >= 0.25:
        aquatic = {
            'h': 'H412', 'h_class': 'Aquatic Chronic 3',
            'formula': f'100×K1+10×K2+K3={h412_sum:.4f} ≥ 0.25',
        }
    elif h413_sum >= 0.25:
        aquatic = {
            'h': 'H413', 'h_class': 'Aquatic Chronic 4',
            'formula': f'Σ(Ci tüm kronik)/100={h413_sum:.4f} ≥ 0.25',
        }

    if aquatic:
        h_codes.append(aquatic['h'])

    # H400: H410 atanmamışsa ve akut eşik aşılmışsa
    has_h410 = 'H410' in h_codes
    aquatic_acute: Optional[Dict] = None
    if sum_acute_m >= 0.25 and not has_h410:
        h_codes.append('H400')
        aquatic_acute = {
            'h': 'H400', 'h_class': 'Aquatic Acute 1',
            'formula': (f'Σ(Ci×M_ak)/100={sum_acute_m:.4f} ≥ 0.25 '
                        f'[=%{sum_acute_m*100:.2f}≥%25] (SEA Tablo 4.1.1)'),
        }

    if ozone:
        h_codes.append('H420')

    return {
        'aquatic':       aquatic,
        'aquatic_acute': aquatic_acute,
        'ozone':         ozone,
        'pbt':           pbt,
        'h_codes':       h_codes,
    }
