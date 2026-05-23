"""
PhysicalEngine — Fiziksel Tehlikeler + Teorik Fiziksel Özellikler
=================================================================
JS physical_engine.js'nin Python karşılığı.

Bölüm 2.1 (Fiziksel tehlike sınıflandırması) + Bölüm 9 (Fiziksel/kimyasal özellikler)

Kapsanan tehlikeler:
  Flam. Liq. 1/2/3  (H224/H225/H226) — CLP Annex I Tablo 2.6
  Asp. Tox. 1        (H304)           — CLP Annex I Tablo 3.10
  Flam. Gas 1A+H232  (H220/H232)      — CLP Annex I §2.2.3
  Flam. Sol. 2       (H228)           — CLP Annex I Tablo 2.7
  Ox. Liq. 3         (H272)           — CLP Annex I Tablo 2.13

Teorik özellikler:
  Yoğunluk        : ρ_mix = Σwᵢ / Σ(wᵢ/ρᵢ)        ISO 2811
  Buhar Basıncı   : Raoult Yasası
  LEL / UEL       : Raoult + Le Chatelier            ISO 10156 / EN 1839
  Buhar Yoğunluğu : MW_mix / 29
  Kaynama Noktası : min(BPᵢ)
  Viskozite       : Kendall-Monroe log-lineer         ASTM D341
  Çözünürlük      : Ağırlıklı geometrik ortalama      OECD 105
"""

import math
from typing import List, Dict, Any, Optional

# ── PARLAMA NOKTASI VERİTABANI (°C) ─────────────────────────────────────────
FP_DB: Dict[str, Optional[float]] = {
    '110-54-3': -22, '110-82-7': -18, '142-82-5': -4,  '111-65-9': 13,
    '108-88-3':  4,  '71-43-2':  -11, '1330-20-7': 27, '95-47-6':  17,
    '106-42-3': 25,  '100-41-4': 21,  '95-63-6':  44,
    '67-64-1': -18,  '78-93-3':  -9,  '108-10-1': 14,  '108-94-1': 43,
    '141-78-6': -4,  '123-86-4': 22,
    '67-56-1':  11,  '64-17-5':  13,  '67-63-0':  12,  '71-23-8':  23,
    '71-36-3':  29,  '78-83-1':  28,  '78-92-2':  27,  '75-65-0':  11,
    '123-51-3': 43,
    '57-55-6':  99,  '107-21-1':111,  '111-46-6':124,  '25265-71-8':138,
    '111-76-2': 62,  '112-34-5': 78,  '107-98-2': 32,
    '34590-94-8':47, '110-80-5': 43,  '111-15-9': 56,  '109-86-4': 39,
    '56-81-5':  160,
    '64-19-7':  40,  '64-18-6':  50,  '79-09-4':  52,  '107-92-6': 72,
    '7664-93-9':None,'7664-38-2':None,'7697-37-2':None,'7647-01-0':None,
    '79-11-8':  None,
    '141-43-5': 85,  '111-42-2':169,  '102-71-6':179,
    '109-89-7': -26, '75-04-7':  -17, '124-40-3':None, '7664-41-7':None,
    '872-50-4': 91,  '68-12-2':  58,  '67-68-5':  95,
    '75-09-2':  None,'67-66-3':  None,
    '64742-47-8':21, '64742-48-9':-20,'64742-82-1':61, '64742-54-7':220,
    '8052-41-3': 38,
    '7732-18-5':None,'1310-73-2':None,'1310-58-3':None,'7681-52-9':None,
    '7722-84-1':None,'497-19-8': None,'10043-52-4':None,'7647-14-5':None,
    '50-21-5':  74,  '77-92-9':  None,'50-00-0':  None,'1336-21-6':None,
    '7783-06-4':None,
}

# ── KAYNAMA NOKTASI VERİTABANI (°C) ─────────────────────────────────────────
BP_DB: Dict[str, Optional[float]] = {
    '110-54-3': 69,  '110-82-7': 81,  '67-64-1':  56,  '71-43-2':  80,
    '78-93-3':  80,  '67-63-0':  82,  '64-17-5':  78,  '71-23-8':  97,
    '64742-48-9':60, '71-36-3': 118,  '78-83-1': 108,  '111-76-2':171,
    '141-78-6': 77,  '123-86-4':126,  '56-81-5': 290,  '7732-18-5':100,
    '108-88-3':111,  '1330-20-7':138, '95-47-6': 144,  '100-41-4': 136,
    '107-98-2':120,  '108-10-1':117,  '64742-47-8':175,'8052-41-3':195,
    '108-94-1':155,  '67-56-1':  65,  '78-92-2':  99,  '75-65-0':  82,
    '123-51-3':131,  '109-89-7': 55,  '75-09-2':  40,  '67-66-3':  61,
    '57-55-6': 188,  '107-21-1':197,  '111-46-6':244,  '25265-71-8':232,
    '112-34-5':230,  '34590-94-8':190,'110-80-5':136,  '111-15-9': 156,
    '109-86-4':124,
    '64-19-7': 118,  '64-18-6': 101,  '79-09-4': 141,  '50-21-5': 122,
    '141-43-5':171,  '111-42-2':268,  '102-71-6':335,  '109-89-7': 55,
    '75-04-7':  17,
    '872-50-4':202,  '68-12-2': 153,  '67-68-5': 189,
    '1310-73-2':None,'1310-58-3':None,'7681-52-9':None,'7722-84-1':None,
    '7664-93-9':None,'7664-38-2':None,'7697-37-2':None,'7647-01-0':None,
    '50-00-0':  None,'497-19-8': None,'10043-52-4':None,'7647-14-5':None,
    '1336-21-6':None,'1305-62-0':None,'1305-78-8':None,
}

# ── MOLEKÜLER AĞIRLIK VERİTABANI (g/mol) ────────────────────────────────────
MW_DB: Dict[str, float] = {
    '110-54-3': 86.18, '142-82-5':100.20, '110-82-7': 84.16, '111-65-9':114.23,
    '108-88-3': 92.14, '1330-20-7':106.16,'71-43-2':  78.11, '100-41-4':106.17,
    '95-47-6': 106.16, '95-63-6': 120.19, '67-64-1':  58.08, '78-93-3':  72.11,
    '108-10-1':100.16, '141-78-6': 88.11, '123-86-4':116.16, '64-17-5':  46.07,
    '67-63-0':  60.10, '71-36-3':  74.12, '78-83-1':  74.12, '111-76-2':118.17,
    '7732-18-5':18.02, '64742-47-8':120.0,'64742-48-9':100.0,'8052-41-3':145.0,
    '56-81-5':  92.09, '107-98-2': 90.12, '108-94-1': 98.14,
    '67-56-1':  32.04, '78-92-2':  74.12, '75-65-0':  74.12, '123-51-3': 88.15,
    '75-09-2':  84.93, '67-66-3': 119.38,
    '57-55-6':  76.09, '107-21-1': 62.07, '111-46-6':106.12, '25265-71-8':134.17,
    '34590-94-8':148.20,'110-80-5': 90.12,'111-15-9':132.16, '109-86-4': 76.09,
    '64-19-7':  60.05, '64-18-6':  46.03, '79-09-4':  74.08, '50-21-5':  90.08,
    '141-43-5': 61.08, '111-42-2':105.14, '102-71-6':149.19,
    '109-89-7': 73.14, '75-04-7':  45.08,
    '872-50-4': 99.13, '68-12-2':  73.09, '67-68-5':  78.13,
}

# ── YOĞUNLUK VERİTABANI (g/cm³, 20°C) ───────────────────────────────────────
DENSITY_DB: Dict[str, float] = {
    '64-17-5':  0.789, '67-64-1':  0.791, '108-88-3': 0.867, '110-54-3': 0.659,
    '110-82-7': 0.684, '71-43-2':  0.879, '1330-20-7':0.860, '67-63-0':  0.786,
    '71-36-3':  0.810, '78-93-3':  0.805, '111-76-2': 0.902, '78-83-1':  0.802,
    '64742-47-8':0.780,'8052-41-3':0.780, '141-78-6': 0.902, '123-86-4': 0.882,
    '7732-18-5':1.000, '100-41-4': 0.867, '108-10-1': 0.801, '95-47-6':  0.879,
    '95-63-6':  0.900, '56-81-5':  1.261, '107-98-2': 0.922, '64742-48-9':0.685,
    '142-82-5': 0.684, '71-23-8':  0.803, '111-65-9': 0.703,
    '108-94-1': 0.948, '67-56-1':  0.792, '78-92-2':  0.808, '75-65-0':  0.786,
    '123-51-3': 0.813, '75-09-2':  1.325, '67-66-3':  1.490,
    '57-55-6':  1.036, '107-21-1': 1.113, '111-46-6': 1.118, '25265-71-8':1.023,
    '34590-94-8':0.951,'110-80-5': 0.930, '111-15-9': 0.975, '109-86-4': 0.965,
    '64-19-7':  1.049, '64-18-6':  1.220, '79-09-4':  0.993, '50-21-5':  1.206,
    '141-43-5': 1.012, '111-42-2': 1.097, '102-71-6': 1.124,
    '109-89-7': 0.707, '75-04-7':  0.689,
    '872-50-4': 1.028, '68-12-2':  0.944, '67-68-5':  1.100,
}

# ── LEL / UEL VERİTABANI (%v/v) ─────────────────────────────────────────────
LEL_DB: Dict[str, float] = {
    '110-54-3':1.1, '142-82-5':1.05,'110-82-7':1.3, '111-65-9':1.0,
    '108-88-3':1.1, '1330-20-7':1.0,'71-43-2': 1.2, '100-41-4':1.0,
    '95-47-6': 1.0, '67-64-1': 2.5, '78-93-3': 1.4, '108-10-1':1.2,
    '141-78-6':2.0, '123-86-4':1.4, '64-17-5': 3.1, '67-63-0': 2.0,
    '71-36-3': 1.4, '78-83-1': 1.7, '111-76-2':1.1, '64742-47-8':1.1,
    '64742-48-9':1.2,'8052-41-3':0.6,'107-98-2':1.8,
    '67-56-1': 6.0, '64-19-7': 5.4, '64-18-6':14.0, '57-55-6': 2.6,
    '107-21-1':3.2, '141-43-5':3.0, '34590-94-8':1.4,'108-94-1':1.1,
    '109-89-7':1.8, '75-04-7': 3.5, '68-12-2': 2.2, '110-80-5':1.8,
    '109-86-4':2.5, '78-92-2': 1.7,
}
UEL_DB: Dict[str, float] = {
    '110-54-3':7.5, '142-82-5':6.7, '110-82-7':8.4, '111-65-9':6.5,
    '108-88-3':7.1, '1330-20-7':7.0,'71-43-2': 8.0, '100-41-4':7.8,
    '95-47-6': 7.6, '67-64-1':12.8, '78-93-3':11.4, '108-10-1':8.0,
    '141-78-6':11.5,'123-86-4':7.6, '64-17-5':19.0, '67-63-0':12.7,
    '71-36-3':11.2, '78-83-1':10.9, '111-76-2':12.7, '64742-47-8':7.0,
    '64742-48-9':7.7,'8052-41-3':6.5,'107-98-2':13.1,
    '67-56-1':36.5, '64-19-7':16.0, '64-18-6':57.0, '57-55-6':12.6,
    '107-21-1':15.3,'141-43-5':23.5,'34590-94-8':14.0,'108-94-1':9.4,
    '109-89-7':14.0,'75-04-7':14.0, '68-12-2':15.2, '110-80-5':15.7,
    '109-86-4':19.8,'78-92-2': 9.8,
}

# ── KİNEMATİK VİSKOZİTE VERİTABANI (mm²/s = cSt @ 40°C) ────────────────────
VISC_DB: Dict[str, float] = {
    '110-54-3': 0.35, '142-82-5': 0.48, '111-65-9': 0.60, '110-82-7': 0.62,
    '71-43-2':  0.50, '108-88-3': 0.53, '1330-20-7':0.65, '95-47-6':  0.64,
    '100-41-4': 0.62, '95-63-6':  0.82, '67-64-1':  0.32, '78-93-3':  0.45,
    '108-10-1': 0.55, '141-78-6': 0.48, '123-86-4': 0.70, '64-17-5':  0.90,
    '67-63-0':  0.80, '71-23-8':  1.40, '71-36-3':  2.00, '78-83-1':  1.80,
    '111-76-2': 2.50, '112-34-5': 5.00, '107-98-2': 1.20, '56-81-5':  150.0,
    '64742-47-8':1.50,'64742-48-9':0.60,'64742-82-1':2.00,
    '64742-54-7':95.0,'8052-41-3': 2.00,'7732-18-5': 0.65,
    '67-56-1':  0.45, '108-94-1': 0.90, '78-92-2':  1.40, '75-09-2':  0.28,
    '57-55-6':  11.0, '107-21-1': 7.50, '111-46-6': 11.0, '25265-71-8':20.0,
    '34590-94-8':1.20,'110-80-5': 1.50, '109-86-4': 1.50,
    '64-19-7':  0.73, '64-18-6':  0.85, '79-09-4':  0.80,
    '141-43-5': 4.50, '111-42-2': 30.0, '102-71-6': 30.0,
    '872-50-4': 1.50, '68-12-2':  0.60, '67-68-5':  2.00,
}

# ── SUDA ÇÖZÜNÜRLÜK VERİTABANI (mg/L @ 20°C) ────────────────────────────────
SOL_DB: Dict[str, float] = {
    '110-54-3':    13, '142-82-5':     3, '111-65-9':   0.7, '110-82-7':   66,
    '108-88-3':   156, '71-43-2':   1780, '1330-20-7':  156, '95-47-6':   175,
    '100-41-4':   152, '95-63-6':    57,  '67-64-1':  1e6,   '78-93-3':  1e6,
    '108-10-1': 19000, '141-78-6': 80000, '123-86-4':  7000, '64-17-5':  1e6,
    '67-63-0':   1e6,  '71-23-8':   1e6,  '71-36-3':  77000, '78-83-1': 85000,
    '111-76-2':  1e6,  '112-34-5':  1e6,  '107-98-2':  1e6,  '56-81-5':  1e6,
    '7732-18-5': 1e6,  '64742-47-8':  1,  '64742-48-9':  1,
    '64742-82-1':  1,  '64742-54-7':0.1,  '8052-41-3':   1,
    '67-56-1':   1e6,  '108-94-1':23000,  '78-92-2':  1e6,  '75-09-2': 20000,
    '57-55-6':   1e6,  '107-21-1': 1e6,   '111-46-6': 1e6,  '25265-71-8':1e6,
    '34590-94-8':1e6,  '110-80-5': 1e6,   '109-86-4': 1e6,
    '64-19-7':   1e6,  '64-18-6':  1e6,   '79-09-4':  1e6,  '50-21-5':  1e6,
    '141-43-5':  1e6,  '111-42-2': 1e6,   '102-71-6': 1e6,
    '872-50-4':  1e6,  '68-12-2':  1e6,   '67-68-5':  1e6,
    '7664-41-7': 1e6,  '7664-93-9':1e6,
}

# ── BUHAR BASINCI VERİTABANI (hPa, 20°C) ────────────────────────────────────
VP_DB: Dict[str, float] = {
    '110-54-3':160,  '142-82-5': 48,  '110-82-7':103,  '111-65-9': 14,
    '108-88-3': 29,  '1330-20-7': 8,  '71-43-2': 100,  '100-41-4':  9.5,
    '95-47-6':   9,  '67-64-1': 240,  '78-93-3':  96,  '108-10-1': 21,
    '141-78-6': 97,  '123-86-4': 12.5,'64-17-5':  59,  '67-63-0':  43,
    '71-36-3':   6,  '78-83-1':  12,  '111-76-2':  1,  '7732-18-5':23,
    '64742-47-8':50, '64742-48-9':160,'8052-41-3':  1,  '56-81-5': 0.003,
    '107-98-2':  14,
    '67-56-1': 128,  '108-94-1':  5.0,'78-92-2':  17,  '75-09-2': 470,
    '57-55-6':  0.17,'107-21-1': 0.08,'111-46-6': 0.01,'25265-71-8':0.03,
    '34590-94-8':0.34,'110-80-5':3.8, '109-86-4':12.3,
    '64-19-7':  15.7,'64-18-6':  45,  '79-09-4':  3.7, '50-21-5':  0.08,
    '141-43-5': 0.5, '111-42-2': 0.01,'102-71-6': 0.001,
    '872-50-4': 0.04,'68-12-2':  3.8, '67-68-5':  0.08,
}

# ── ASPİRASYON TOKSİSİTESİ VE DİĞER CAS LİSTELERİ ──────────────────────────
ASP_CAS = {
    '110-54-3','110-82-7','142-82-5','111-65-9','71-43-2',
    '1330-20-7','64742-47-8','64742-48-9','64742-82-1',
    '64741-41-9','64741-42-0','64741-44-2','64741-45-3',
    '64741-47-5','64741-48-6','64742-54-7','8052-41-3',
}
OXIDIZING_CAS = {'7722-84-1','7790-98-9','7775-09-9','7727-54-0'}
FLAM_SOL_CAS  = {'7704-34-9','1333-86-4','12185-10-3'}
PYRO_GAS_CAS  = {
    '7803-62-5','19287-45-7','7782-65-2','7803-52-3',
    '13765-25-8','992-94-9','7784-42-1',
}

# ── HATA PAYI METAVERİSİ ─────────────────────────────────────────────────────
ERROR_META = {
    'density':        {'base':0.03, 'polar':0.06,  'method':'ρ_mix = Σwᵢ / Σ(wᵢ/ρᵢ)', 'standard':'ISO 2811'},
    'vapor_pressure': {'base':0.20,               'method':'Raoult Yasası',             'standard':'—'},
    'lel':            {'base':0.15,               'method':'Le Chatelier (ISO 10156)',   'standard':'ISO 10156 / EN 1839'},
    'uel':            {'base':0.20,               'method':'Le Chatelier',               'standard':'ISO 10156 / EN 1839'},
    'vapor_density':  {'base':0.02,               'method':'VD = MW_mix / 29',           'standard':'İdeal gaz'},
    'boiling_point':  {'base':None,               'method':'IBP = min(KNᵢ)',             'standard':'ASTM D86 / ISO 3924'},
}


def _calc_error(prop: str, value: float, coverage: int, has_water: bool = False) -> Optional[Dict]:
    meta = ERROR_META.get(prop, {})
    base = meta.get('base')
    if base is None:
        return None
    if prop == 'density' and has_water:
        base = meta.get('polar', base)
    mult = 1.8 if coverage < 50 else (1.4 if coverage < 70 else (1.15 if coverage < 85 else 1.0))
    rate = base * mult
    pct  = round(rate * 100)
    decimals = 3 if prop == 'density' else (2 if prop == 'vapor_density' else 1)
    return {'abs': round(value * rate, decimals), 'pct': pct, 'rate': rate}


# ── TEORİK FİZİKSEL ÖZELLİKLER ──────────────────────────────────────────────
def calc_theo_props(comps: List[Dict]) -> Optional[Dict]:
    rows = []
    for c in comps:
        cas = (c.get('cas') or c.get('cas_no') or '').strip()
        w   = (float(c.get('concMax') or c.get('conc') or 0)) / 100
        if w > 0 and cas:
            rows.append({'cas': cas, 'w': w})

    if not rows:
        return None

    dens_num = dens_den = 0.0
    mw_den = total_w = 0.0
    vp_data, flam_rows = [], []
    min_bp = None
    has_water = False
    covered_w = 0.0

    for r in rows:
        cas, w = r['cas'], r['w']
        rho = DENSITY_DB.get(cas)
        mw  = MW_DB.get(cas)
        lel = LEL_DB.get(cas)
        uel = UEL_DB.get(cas)
        vp  = VP_DB.get(cas)
        bp  = BP_DB.get(cas, 'MISSING')

        if cas == '7732-18-5' and w * 100 >= 20:
            has_water = True

        if rho is not None:
            dens_num += w; dens_den += w / rho; covered_w += w

        if mw is not None:
            mw_den += w / mw; total_w += w
            if vp is not None:
                vp_data.append({'n': w / mw, 'vp': vp})

        # BP: BP_DB'de key yoksa atla (MISSING), key var ama None ise de atla
        if bp != 'MISSING' and bp is not None and w * 100 >= 1:
            if min_bp is None or bp < min_bp:
                min_bp = bp

        if mw is not None and vp is not None and lel is not None and uel is not None and w > 0:
            flam_rows.append({'n': w / mw, 'vp': vp, 'lel': lel, 'uel': uel})

    total_w_all = sum(r['w'] for r in rows)
    coverage = round((covered_w / total_w_all) * 100) if total_w_all > 0 else 0

    res: Dict = {'coverage': coverage, 'has_water': has_water}

    # Yoğunluk
    if dens_den > 0:
        val = round(dens_num / dens_den, 3)
        res['density'] = {'value': val, 'error': _calc_error('density', val, coverage, has_water),
                          **{k: ERROR_META['density'][k] for k in ('method','standard')}}

    # MW + buhar yoğunluğu + buhar basıncı
    if mw_den > 0 and total_w > 0:
        mw_mix = total_w / mw_den
        vd_val = round(mw_mix / 29, 2)
        res['vapor_density'] = {'value': vd_val, 'error': _calc_error('vapor_density', vd_val, coverage),
                                 **{k: ERROR_META['vapor_density'][k] for k in ('method','standard')}}
        if vp_data:
            tot_n  = sum(e['n'] for e in vp_data)
            vp_val = round(sum((e['n'] / tot_n) * e['vp'] for e in vp_data), 1)
            res['vapor_pressure'] = {'value': vp_val, 'error': _calc_error('vapor_pressure', vp_val, coverage),
                                      **{k: ERROR_META['vapor_pressure'][k] for k in ('method','standard')}}

    # LEL / UEL — Raoult + Le Chatelier (ISO 10156)
    if flam_rows:
        tot_n = sum(e['n'] for e in flam_rows)
        with_p = [{'lel': e['lel'], 'uel': e['uel'], 'p': (e['n'] / tot_n) * e['vp']} for e in flam_rows]
        p_tot = sum(e['p'] for e in with_p)
        if p_tot > 0:
            vy     = [{'lel': e['lel'], 'uel': e['uel'], 'y': e['p'] / p_tot} for e in with_p]
            lel_inv = sum(e['y'] / e['lel'] for e in vy)
            uel_inv = sum(e['y'] / e['uel'] for e in vy)
            if lel_inv > 0:
                lel_val = round(1 / lel_inv, 1)
                uel_val = round(1 / uel_inv, 1)
                res['lel'] = {'value': lel_val, 'error': _calc_error('lel', lel_val, coverage),
                               **{k: ERROR_META['lel'][k] for k in ('method','standard')}}
                res['uel'] = {'value': uel_val, 'error': _calc_error('uel', uel_val, coverage),
                               **{k: ERROR_META['uel'][k] for k in ('method','standard')}}

    # Kaynama noktası
    if min_bp is not None:
        res['boiling_point'] = {'value': min_bp, 'error': None,
                                 **{k: ERROR_META['boiling_point'][k] for k in ('method','standard')}}

    # Kinematik viskozite — Kendall-Monroe (ASTM D341)
    visc_pairs, visc_vol_tot, visc_cov_w = [], 0.0, 0.0
    for r in rows:
        visc = VISC_DB.get(r['cas'])
        rho  = DENSITY_DB.get(r['cas'])
        if visc is not None and rho is not None and r['w'] > 0:
            vol = r['w'] / rho
            visc_pairs.append({'vol': vol, 'visc': visc})
            visc_vol_tot += vol
            visc_cov_w   += r['w']
    if visc_pairs and visc_vol_tot > 0:
        log_sum  = sum((e['vol'] / visc_vol_tot) * math.log(e['visc']) for e in visc_pairs)
        visc_val = round(math.exp(log_sum), 2)
        visc_cov = round((visc_cov_w / total_w_all) * 100) if total_w_all > 0 else 0
        h304_note = (f'H304 eşiği altında ({visc_val} ≤ 20,5 mm²/s) — kimyasal yapı kontrolü gerekir'
                     if visc_val <= 20.5 else
                     f'H304 eşiği üstünde ({visc_val} > 20,5 mm²/s) — H304 bu kriterde hariç')
        res['viscosity'] = {
            'value': visc_val,
            'error': {'abs': round(visc_val * 0.30, 2), 'pct': 30, 'rate': 0.30},
            'method': 'log(ν_mix) = Σ(φᵢ·log(νᵢ)) — Kendall-Monroe (ASTM D341)',
            'standard': 'ISO 3219 / ISO 3104 — Kinematik viskozite @ 40°C',
            'note': f'{h304_note}. DB kapsama: %{visc_cov}',
        }

    # Suda çözünürlük
    sol_log_sum, sol_cov_w = 0.0, 0.0
    water_row = next((r for r in rows if r['cas'] == '7732-18-5'), None)
    water_frac = water_row['w'] if water_row else 0.0
    for r in rows:
        sol = SOL_DB.get(r['cas'])
        if sol is not None and r['w'] > 0:
            sol_log_sum += r['w'] * math.log10(max(sol, 0.01))
            sol_cov_w   += r['w']
    if sol_cov_w > 0:
        sol_cov = round((sol_cov_w / total_w_all) * 100) if total_w_all > 0 else 0
        if water_frac >= 0.5:
            sol_val  = None
            sol_desc = 'Tam karışır — su bazlı ürün (su > %50)'
        else:
            sol_raw  = 10 ** (sol_log_sum / sol_cov_w)
            sol_val  = round(sol_raw, 1)
            sol_desc = (f'Çözünür (>10 g/L), tahmini ~{sol_val} mg/L' if sol_val >= 10000 else
                        f'Kısmen çözünür (0,1–10 g/L), tahmini ~{sol_val} mg/L' if sol_val >= 100 else
                        f'Pratik olarak çözünmez (<100 mg/L), tahmini ~{sol_val} mg/L')
        res['solubility'] = {
            'value': sol_val,
            'text':  sol_desc,
            'error': {'abs': None, 'pct': 50, 'rate': 0.50},
            'method': 'log(S_mix) = Σ(wᵢ·log(Sᵢ))/Σwᵢ — ağırlıklı geometrik ortalama',
            'standard': 'OECD 105 (referans)',
        }

    return res


# ── TEHLİKE SINIFLANDIRMASI ───────────────────────────────────────────────────

def _cls_flam_liq(fp: float, bp: Optional[float]) -> Optional[Dict]:
    if fp < 23 and (bp is None or bp <= 35):
        return {'h': 'H224', 'cat': 1, 'h_class': 'Flam. Liq. 1', 'signal': 'Danger'}
    if fp < 23:
        return {'h': 'H225', 'cat': 2, 'h_class': 'Flam. Liq. 2', 'signal': 'Danger'}
    if 23 <= fp <= 60:
        return {'h': 'H226', 'cat': 3, 'h_class': 'Flam. Liq. 3', 'signal': 'Warning'}
    return None


def _calc_flam_liq(comps: List[Dict], user_fp=None) -> Dict:
    DECLARED_FALLBACK = {
        'H224': {'fp': -20, 'bp': 25},
        'H225': {'fp':  15, 'bp': 80},
        'H226': {'fp':  40, 'bp': 120},
    }

    if user_fp is not None:
        # Kullanıcı FP girmiş
        theo_bp = None
        for c in comps:
            cas = (c.get('cas') or c.get('cas_no') or '').strip()
            w   = float(c.get('concMax') or c.get('conc') or 0)
            bp  = BP_DB.get(cas, 'MISSING')
            if bp != 'MISSING' and bp is not None and w >= 1:
                if theo_bp is None or bp < theo_bp:
                    theo_bp = bp
        effective_bp = theo_bp if theo_bp is not None else (100 if user_fp < 23 else None)
        return {'result': _cls_flam_liq(user_fp, effective_bp),
                'source': f'Kullanıcı girişi ({user_fp}°C)', 'fp': user_fp}

    cat_sum = {1: 0.0, 2: 0.0, 3: 0.0}
    cat_triggers = {1: [], 2: [], 3: []}
    cat_fp = {1: None, 2: None, 3: None}

    for c in comps:
        cas  = (c.get('cas') or c.get('cas_no') or '').strip()
        conc = float(c.get('concMax') or c.get('conc') or 0)
        fp   = FP_DB.get(cas, 'MISSING')
        bp   = None
        estimated = False

        if fp == 'MISSING' and conc > 0:
            hazard_codes = [(h.get('h_code') or '').replace('*','').strip()[:4]
                            for h in (c.get('hazards') or [])]
            decl_h = next((h for h in hazard_codes if h in DECLARED_FALLBACK), None)
            if decl_h:
                fp        = DECLARED_FALLBACK[decl_h]['fp']
                bp        = DECLARED_FALLBACK[decl_h]['bp']
                estimated = True

        if fp is None or fp == 'MISSING' or fp >= 60:
            continue
        if not estimated:
            bp_val = BP_DB.get(cas, 'MISSING')
            bp = None if bp_val == 'MISSING' else bp_val

        cls = _cls_flam_liq(fp, bp)
        if not cls:
            continue
        cat = cls['cat']
        cat_sum[cat] += conc
        if cat_fp[cat] is None or fp < cat_fp[cat]:
            cat_fp[cat] = fp
        cat_triggers[cat].append({'cas': cas, 'name': c.get('name') or cas,
                                   'conc': conc, 'fp': fp, 'estimated': estimated})

    def trig_src(t):
        return f"{t['name']} (%{t['conc']}, FP={t['fp']}°C{'  tahmini' if t['estimated'] else ''})"

    sum1   = cat_sum[1]
    sum12  = cat_sum[1] + cat_sum[2]
    sum123 = cat_sum[1] + cat_sum[2] + cat_sum[3]

    if sum1 >= 1:
        src = ' + '.join(trig_src(t) for t in cat_triggers[1])
        return {'result': {'h':'H224','cat':1,'h_class':'Flam. Liq. 1','signal':'Danger'},
                'source': src, 'fp': cat_fp[1]}
    if sum12 >= 1:
        trigs = cat_triggers[1] + cat_triggers[2]
        fps   = [cat_fp[k] for k in (1,2) if cat_fp[k] is not None]
        src   = ' + '.join(trig_src(t) for t in trigs)
        return {'result': {'h':'H225','cat':2,'h_class':'Flam. Liq. 2','signal':'Danger'},
                'source': src, 'fp': min(fps) if fps else None}
    if sum123 >= 10:
        all_trigs = cat_triggers[1] + cat_triggers[2] + cat_triggers[3]
        all_fps   = [cat_fp[k] for k in (1,2,3) if cat_fp[k] is not None]
        src       = ' + '.join(trig_src(t) for t in all_trigs)
        return {'result': {'h':'H226','cat':3,'h_class':'Flam. Liq. 3','signal':'Warning'},
                'source': src, 'fp': min(all_fps) if all_fps else None}
    return {'result': None, 'source': None, 'fp': None}


def _calc_asp_tox(comps: List[Dict], test_data: Dict = None) -> Dict:
    kin_visc = None
    if test_data:
        v = test_data.get('viscosity')
        if v is not None:
            try:
                kin_visc = float(v)
            except (ValueError, TypeError):
                pass

    if kin_visc is not None and kin_visc > 20.5:
        return {'result': None,
                'source': f'Kinematik viskozite {kin_visc} mm²/s > 20,5 mm²/s — H304 uygulanmaz',
                'total': 0, 'viscosity_excluded': True}

    total, triggers = 0.0, []
    for c in comps:
        cas  = (c.get('cas') or c.get('cas_no') or '').strip()
        conc = float(c.get('concMax') or c.get('conc') or 0)
        in_list   = cas in ASP_CAS
        has_class = any((h.get('h_class') or '') == 'Asp. Tox. 1'
                        for h in (c.get('hazards') or []))
        if (in_list or has_class) and conc > 0:
            triggers.append({'cas': cas, 'name': c.get('name') or cas, 'conc': conc})
            total += conc

    if total >= 10:
        visc_note = '' if kin_visc is not None else ' (viskozite girilmedi — doğrulayın)'
        src = ', '.join(f"{t['name']} (%{t['conc']})" for t in triggers) + visc_note
        return {'result': {'h':'H304','h_class':'Asp. Tox. 1','signal':'Danger'},
                'source': src, 'total': total}
    return {'result': None, 'source': None, 'total': total}


def _calc_flam_gas(comps: List[Dict]) -> Dict:
    triggers = []
    for c in comps:
        cas  = (c.get('cas') or c.get('cas_no') or '').strip()
        conc = float(c.get('concMax') or c.get('conc') or 0)
        if conc < 1.0:
            continue
        has_h232 = any((h.get('h_code') or '').replace('*','').strip()[:4] == 'H232'
                       for h in (c.get('hazards') or []))
        if has_h232 or cas in PYRO_GAS_CAS:
            triggers.append({'cas': cas, 'name': c.get('name') or cas, 'conc': conc})

    if triggers:
        src = ', '.join(f"{t['name']} (%{t['conc']})" for t in triggers)
        return {'result_h220': {'h':'H220','h_class':'Flam. Gas 1A','signal':'Danger'},
                'result_h232': {'h':'H232','h_class':'Flam. Gas 1A — Pirofor','signal':'Danger'},
                'source': src}
    return {'result_h220': None, 'result_h232': None, 'source': None}


# ── ANA HESAP FONKSİYONU ─────────────────────────────────────────────────────

def calculate(comps: List[Dict], form: str = 'liquid',
              user_fp=None, test_data: Dict = None) -> Dict:
    """
    Fiziksel tehlike sınıflandırması + teorik fiziksel özellikler hesapla.

    Returns:
        {
          'results': [...],    # tüm tehlike sonuçları
          'primary': [...],    # ana tehlikeler
          'extra':   [...],    # ek tehlikeler
          'warnings': [...],
          'theo_props': {...}  # teorik fiziksel özellikler
        }
    """
    if test_data is None:
        test_data = {}

    primary, extra, warnings = [], [], []

    fl = {'result': None, 'source': None, 'fp': None}
    if form in ('liquid', 'paste', 'aerosol'):
        fl = _calc_flam_liq(comps, user_fp)
        if fl['result']:
            _flam_cutoff = {
                'H224': '≥ %1 Cat.1 yanıcı sıvı bileşen (CLP Ek-I Tablo 2.6)',
                'H225': '≥ %1 Cat.1+2 yanıcı sıvı bileşen (CLP Ek-I Tablo 2.6)',
                'H226': '≥ %10 yanıcı sıvı bileşen (CLP Ek-I Tablo 2.6)',
            }.get(fl['result']['h'], 'Yanıcı sıvı — CLP Ek-I Tablo 2.6')
            primary.append({'type': 'flam_liq', **fl['result'],
                            'source': fl['source'], 'fp': fl['fp'],
                            'cutoff_used': _flam_cutoff})

    if form in ('liquid', 'paste'):
        asp = _calc_asp_tox(comps, test_data)
        if asp['result']:
            primary.append({'type': 'asp_tox', **asp['result'],
                            'source': asp['source'], 'total': asp['total'],
                            'cutoff_used': '≥ %10 aspirasyon toksik bileşen'})
        if asp.get('viscosity_excluded'):
            warnings.append('H304: ' + asp['source'])

    if form == 'gas':
        fg = _calc_flam_gas(comps)
        if fg['result_h232']:
            _pyro_cutoff = '≥ %1 pirofor gaz bileşen'
            primary.append({'type': 'flam_gas',      **fg['result_h220'], 'source': fg['source'], 'cutoff_used': _pyro_cutoff})
            primary.append({'type': 'flam_gas_pyro', **fg['result_h232'], 'source': fg['source'], 'cutoff_used': _pyro_cutoff})

    if form in ('solid', 'powder'):
        fs = [c for c in comps
              if (c.get('cas') or c.get('cas_no') or '').strip() in FLAM_SOL_CAS
              and float(c.get('concMax') or c.get('conc') or 0) >= 1]
        if fs:
            _fs_src = ', '.join(f"{c.get('name') or c.get('cas','')} (%{float(c.get('concMax') or c.get('conc') or 0):.0f})" for c in fs)
            extra.append({'type': 'flam_sol', 'h': 'H228', 'h_class': 'Flam. Sol. 2',
                          'signal': 'Warning', 'source': _fs_src,
                          'cutoff_used': '≥ %1 yanıcı katı bileşen (CLP Ek-I Tablo 2.7)'})

    if form in ('liquid', 'paste'):
        ox = [c for c in comps
              if (c.get('cas') or c.get('cas_no') or '').strip() in OXIDIZING_CAS
              and float(c.get('concMax') or c.get('conc') or 0) >= 1]
        if ox:
            _ox_src = ', '.join(f"{c.get('name') or c.get('cas','')} (%{float(c.get('concMax') or c.get('conc') or 0):.0f})" for c in ox)
            extra.append({'type': 'oxidizing', 'h': 'H272', 'h_class': 'Ox. Liq. 3',
                          'signal': 'Warning', 'source': _ox_src,
                          'cutoff_used': '≥ %1 oksitleyici bileşen (CLP Ek-I Tablo 2.13)'})

    # Teorik fiziksel özellikler
    theo_props = calc_theo_props(comps) if form in ('liquid', 'paste', 'aerosol') else {}
    if theo_props is None:
        theo_props = {}   # calc_theo_props bileşen yoksa None döner — sonraki adımlar için {}

    # Test verisi varsa üzerine yaz
    if test_data:
        _apply_test_data(theo_props, test_data)

    # Parlama noktasını ekle
    if test_data.get('flash_point') is not None:
        theo_props['flash_point'] = {
            'value': test_data['flash_point'], 'measured': True,
            'method': 'Kullanıcı girişi', 'standard': 'ISO 2719 / ASTM D93',
        }
    elif fl['fp'] is not None:
        theo_props['flash_point'] = {
            'value': fl['fp'], 'measured': False,
            'method': fl['source'] or 'DB sorgusu', 'standard': 'CLP Annex VI / NIST',
            'note': f"Sınıflandırma: {fl['result']['h_class']} ({fl['result']['h']})" if fl['result'] else '',
        }

    return {
        'results':    primary + extra,
        'primary':    primary,
        'extra':      extra,
        'warnings':   warnings,
        'theo_props': theo_props,
    }


def _apply_test_data(props: Dict, test_data: Dict) -> None:
    """Test/ölçülen verileri teorik değerlerin üzerine yaz (in-place)."""
    def meas(value, standard, note='Test verisinden alındı.'):
        return {'value': value, 'measured': True,
                'method': 'Kullanıcı girişi (ölçülen/beyan değer)',
                'standard': standard, 'note': note, 'error': None}

    mapping = {
        'density':       ('density',       'ISO 2811 / ASTM D4052'),
        'boiling_point': ('boiling_point', 'ASTM D86 / ISO 3924'),
        'ph':            ('ph',            'ISO 4316 / ASTM E70'),
        'viscosity':     ('viscosity',     'ISO 3219 / ASTM D2196'),
        'solubility':    ('solubility',    'OECD 105'),
        'flash_point':   ('flash_point',   'ISO 2719 / ASTM D93'),
    }
    for key, (prop, std) in mapping.items():
        if test_data.get(key) is not None:
            props[prop] = meas(test_data[key], std)

    # Yalnızca kullanıcı girer
    for key, std in [('appearance','REACH Ek II §9'), ('odor','Duyusal test'),
                     ('melting_point','ISO 1218 / ASTM D97'),
                     ('auto_ignition','EN 14522 / ASTM E659'),
                     ('decomp_temp','ISO 11357 / DSC'),
                     ('log_kow','OECD 117 / 107')]:
        if test_data.get(key) is not None:
            props[key] = meas(test_data[key], std)


def update_db(cas: str, props: Dict) -> None:
    """Çalışma zamanında veritabanını güncelle (PubChem verisi vb.)."""
    c = cas.strip()
    if not c:
        return
    if props.get('density') is not None:
        DENSITY_DB[c] = props['density']
    # BP: önceden tanımlı null dahil mevcut değerlerin üzerine yazma
    if props.get('boiling_point') is not None and c not in BP_DB:
        BP_DB[c] = props['boiling_point']
    # FP: aynı kural
    if 'flash_point' in props and c not in FP_DB:
        FP_DB[c] = props['flash_point']
    if props.get('vapor_pressure') is not None:
        VP_DB[c] = props['vapor_pressure']
    if props.get('viscosity') is not None:
        VISC_DB[c] = props['viscosity']
    if props.get('solubility') is not None:
        SOL_DB[c] = props['solubility']
    if props.get('mw') is not None:
        MW_DB[c] = props['mw']
    if props.get('lel') is not None:
        LEL_DB[c] = props['lel']
    if props.get('uel') is not None:
        UEL_DB[c] = props['uel']
