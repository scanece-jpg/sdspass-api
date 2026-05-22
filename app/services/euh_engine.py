"""
EUHEngine — CLP (AT) No 1272/2008 Ek II
EUH kodu hesaplama

JS euh_engine.js'nin Python karşılığı.
"""

import re
from typing import List, Dict

# ── EUH KOD METİNLERİ (Türkçe — KKDİK Ek-2) ────────────────────────────────
EUH_TEXTS = {
    'EUH001':  'Kuru hâlde patlayıcıdır.',
    'EUH006':  'Havaya maruz kalma durumunda ya da kalmaksızın patlayıcıdır.',
    'EUH014':  'Su ile şiddetli reaksiyon gösterir.',
    'EUH018':  'Kullanım sırasında yanıcı/patlayıcı buhar-hava karışımı oluşabilir.',
    'EUH019':  'Patlayıcı peroksitler oluşturabilir.',
    'EUH029':  'Su ile temas hâlinde zehirli gaz açığa çıkarır.',
    'EUH031':  'Asitlerle temasında zehirli gaz açığa çıkarır.',
    'EUH032':  'Asitlerle temasında çok zehirli gaz açığa çıkarır.',
    'EUH044':  'Kapalı alanda ısıtıldığında patlama riski.',
    'EUH059':  'Ozon tabakasına zararlıdır.',
    'EUH066':  'Tekrarlayan maruziyetle deri kuruluğuna veya çatlamaya yol açabilir.',
    'EUH070':  'Gözle temasında zehirlidir.',
    'EUH071':  'Solunum yolunu aşındırıcıdır.',
    'EUH201':  'Kurşun içerir.',
    'EUH201A': 'Dikkat! Kurşun içerir.',
    'EUH202':  'Siyanoakrilat. Tehlike. Göz kapaklarına ve deriye saniyeler içinde yapışır.',
    'EUH203':  'Krom(VI) içerir.',
    'EUH204':  'İzosiyanat içerir.',
    'EUH205':  'Epoksi bileşenler içerir.',
    'EUH206':  'Dikkat! Diğer müstahzarlarla birlikte kullanmayın.',
    'EUH207':  'Dikkat! Kadmiyum içerir.',
    'EUH208':  '... içerir. Alerjik reaksiyona yol açabilir.',
    'EUH209':  'Kullanım sırasında kolayca yanıcı hâle gelebilir.',
    'EUH209A': 'Kullanım sırasında yanıcı hâle gelebilir.',
    'EUH210':  'Güvenlik bilgi formu talep üzerine temin edilir.',
    'EUH401':  'Çevreye zarar vermemek için kullanım talimatlarına uyunuz.',
}

# ── CAS → EUH ZORUNLU KODLAR ─────────────────────────────────────────────────
CAS_TO_EUH: Dict[str, List[str]] = {
    # EUH019
    '75-21-8':    ['EUH019'], '7722-84-1': ['EUH019'], '109-99-9':  ['EUH019'],
    '123-91-1':   ['EUH019'], '60-29-7':   ['EUH019'], '108-20-3':  ['EUH019'],
    '107-30-2':   ['EUH019'],
    # EUH029
    '20859-73-8': ['EUH029', 'EUH032'], '1314-84-7':  ['EUH029'],
    '12057-74-8': ['EUH029'],           '10124-50-2': ['EUH029'],
    '26628-22-8': ['EUH029', 'EUH032'],
    # EUH031
    '7681-52-9':  ['EUH031'], '7757-83-7': ['EUH031'], '1313-82-2': ['EUH031'],
    '1312-73-8':  ['EUH031'], '16721-80-5':['EUH031'], '1317-37-9': ['EUH031'],
    # EUH032
    '143-33-9':   ['EUH032'], '151-50-8':  ['EUH032'], '592-01-8':  ['EUH032'],
    '460-19-5':   ['EUH032'],
    # EUH066
    '110-54-3':   ['EUH066'], '142-82-5':  ['EUH066'], '110-82-7':  ['EUH066'],
    '108-87-2':   ['EUH066'], '8052-41-3': ['EUH066'], '64742-82-1':['EUH066'],
    '64742-89-8': ['EUH066'],
    # EUH071
    '7664-39-3':  ['EUH071'], '107-13-1':  ['EUH071'], '75-44-5':   ['EUH071'],
    # EUH201
    '7439-92-1':  ['EUH201'], '1317-36-8': ['EUH201'], '7446-14-2': ['EUH201'],
    '301-04-2':   ['EUH201'], '1344-37-2': ['EUH201'], '78-00-2':   ['EUH201'],
    '75-74-1':    ['EUH201'],
    # EUH202
    '7085-85-0':  ['EUH202'], '137-05-3':  ['EUH202'], '133978-15-1':['EUH202'],
    '1069-48-3':  ['EUH202'],
    # EUH203
    '1333-82-0':  ['EUH203'], '7778-50-9': ['EUH203'], '10588-01-9':['EUH203'],
    '7789-00-6':  ['EUH203'], '7789-09-5': ['EUH203'], '13530-65-9':['EUH203'],
    '1189-85-1':  ['EUH203'],
    # EUH207
    '7440-43-9':  ['EUH207'], '1306-19-0': ['EUH207'], '1306-23-6': ['EUH207'],
    '10108-64-2': ['EUH207'], '10124-36-4':['EUH207'], '543-90-8':  ['EUH207'],
}

# ── H KODU → EUH ─────────────────────────────────────────────────────────────
H_TO_EUH: Dict[str, List[str]] = {
    'H290': ['EUH014'],
    'H260': ['EUH014'],
    'H261': ['EUH014'],
}

# ── İSİM PATTERN → EUH ──────────────────────────────────────────────────────
NAME_PATTERNS = [
    (re.compile(r'izosiyanat|isocyanate', re.I),           'EUH204'),
    (re.compile(r'epoksi|epoxy|bisfenol|bisphenol', re.I), 'EUH205'),
    (re.compile(r'hipoklorit|hypochlorite', re.I),         'EUH031'),
    (re.compile(r'sülfür|sülfid|sulfide|sulphide', re.I),  'EUH031'),
    (re.compile(r'siyanür|cyanide', re.I),                 'EUH032'),
    (re.compile(r'fosfür|phosphide', re.I),                'EUH029'),
]

OZONE_CAS = {
    '75-69-4','75-71-8','76-13-1','76-14-2','75-72-9',
    '75-63-8','74-83-9','74-87-3','56-23-5','67-66-3','79-01-6',
}


def calculate(comps: List[Dict]) -> Dict:
    """
    EUH kodlarını hesapla.

    Returns:
        {
          'codes': [...],
          'euh_codes': [...],
          'details': [...],
          'euh_details': [...],
          'warnings': []
        }
    """
    codes:   set  = set()
    details: list = []
    warnings: list = []

    # EUH209 / EUH209A ön-kontrol: karışım zaten yanıcı sınıfına giriyorsa uygulanmaz
    def _is_flam12(h): return (h.get('h_code') or '').replace('*','').strip()[:4] in ('H224','H225')
    def _is_flam3(h):  return (h.get('h_code') or '').replace('*','').strip()[:4] == 'H226'

    mix_already_flam12 = any(
        float(c.get('concMax') or c.get('conc') or 0) >= 1.0
        and any(_is_flam12(h) for h in (c.get('hazards') or []))
        for c in comps
    )
    mix_already_flam3 = any(
        float(c.get('concMax') or c.get('conc') or 0) >= 10.0
        and any(_is_flam3(h) for h in (c.get('hazards') or []))
        for c in comps
    )

    sensitizer_names: list = []

    for c in comps:
        cas  = (c.get('cas') or c.get('cas_no') or '').strip()
        conc = float(c.get('concMax') or c.get('conc') or 0)
        name = c.get('name_tr') or c.get('name') or cas

        # CAS bazlı EUH
        for code in CAS_TO_EUH.get(cas, []):
            if code not in codes:
                codes.add(code)
                details.append({'code': code, 'text': EUH_TEXTS.get(code, code),
                                 'source': f'{name} (CAS: {cas})', 'type': 'auto'})

        # H kodu bazlı EUH
        for h in (c.get('hazards') or []):
            hcode = (h.get('h_code') or '').replace('*','').strip()[:4]
            for euh_code in H_TO_EUH.get(hcode, []):
                if euh_code not in codes:
                    codes.add(euh_code)
                    details.append({'code': euh_code, 'text': EUH_TEXTS.get(euh_code, euh_code),
                                     'source': f'{name} — {hcode}', 'type': 'auto'})

        # EUH209 / EUH209A
        flam_codes = [(h.get('h_code') or '').replace('*','').strip()[:4]
                      for h in (c.get('hazards') or [])]
        if ('EUH209' not in codes and not mix_already_flam12
                and ('H224' in flam_codes or 'H225' in flam_codes)
                and 0.1 <= conc < 1.0):
            codes.add('EUH209')
            details.append({'code': 'EUH209', 'text': EUH_TEXTS['EUH209'],
                             'source': f'{name} — H224/H225, %{conc} (eşik altı yanıcı bileşen)',
                             'type': 'auto'})

        if ('EUH209A' not in codes and not mix_already_flam12 and not mix_already_flam3
                and 'H226' in flam_codes and 1.0 <= conc < 10.0):
            codes.add('EUH209A')
            details.append({'code': 'EUH209A', 'text': EUH_TEXTS['EUH209A'],
                             'source': f'{name} — H226, %{conc} (eşik altı yanıcı bileşen)',
                             'type': 'auto'})

        # İsim bazlı tespitler
        for pattern, code in NAME_PATTERNS:
            if pattern.search(name) and code not in codes:
                codes.add(code)
                details.append({'code': code, 'text': EUH_TEXTS.get(code, code),
                                 'source': f'{name} — isim eşleşmesi', 'type': 'auto'})

        # Ozon tüketen
        if cas in OZONE_CAS and conc >= 0.1 and 'EUH059' not in codes:
            codes.add('EUH059')
            details.append({'code': 'EUH059', 'text': EUH_TEXTS['EUH059'],
                             'source': f'{name} (CAS: {cas})', 'type': 'auto'})

        # EUH208 — sınıflandırmaya yol açmayan sensitizerlar
        has_resp_sens = any((h.get('h_code') or '').replace('*','').strip()[:4] == 'H334'
                            for h in (c.get('hazards') or []))
        has_skin_sens = any((h.get('h_code') or '').replace('*','').strip()[:4] == 'H317'
                            for h in (c.get('hazards') or []))

        if has_resp_sens or has_skin_sens:
            skin_threshold = 1.0
            skin_h = next((h for h in (c.get('hazards') or [])
                           if (h.get('h_code') or '').replace('*','').strip()[:4] == 'H317'), None)
            if skin_h:
                skin_class = (skin_h.get('h_class') or skin_h.get('class') or '')
                if re.search(r'1A', skin_class, re.I):
                    skin_threshold = 0.1
                # SCL override
                scl = c.get('scl')
                if isinstance(scl, list):
                    for s in scl:
                        if (s.get('h_code') or '').replace('*','').strip()[:4] == 'H317' and s.get('c_min') is not None:
                            skin_threshold = s['c_min']
                            break
                elif isinstance(scl, dict) and scl.get('H317') is not None:
                    skin_threshold = scl['H317']

            causes_skin_class = has_skin_sens and conc >= skin_threshold
            if not causes_skin_class and conc >= 0.1:
                if name not in sensitizer_names:
                    sensitizer_names.append(name)

    # EUH208 — tüm sensitizerlar toplandıktan sonra
    if sensitizer_names:
        codes.add('EUH208')
        all_names = '; '.join(sensitizer_names)
        details.append({
            'code':   'EUH208',
            'text':   EUH_TEXTS['EUH208'].replace('...', all_names),
            'source': f'{all_names} — H317/H334, ≥%0.1 eşik',
            'type':   'auto',
        })

    codes_list = list(codes)
    return {
        'codes':       codes_list,
        'euh_codes':   codes_list,
        'details':     details,
        'euh_details': details,
        'warnings':    warnings,
    }
