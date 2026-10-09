"""
Eldiven seçimi — KKDİK Ek-2 A 8.2.2.2(b)(i): eldiven tipi; materyal tipi ve kalınlığı; tipik veya
minimum delinme ("aşınma") süresi; uygun CEN standardına atıf.

Minimum süre standarttan gelir: EN ISO 374-1:2016 eldivenleri 18 test kimyasalıyla (harf A–T) sınıflandırır.
Tip A/B işaretli eldiven, üzerinde harfi bulunan kimyasal için en az seviye 2 (≥ 30 dk, EN 16523-1);
Tip C en az seviye 1 (≥ 10 dk) sağlar. Bileşenler bu test kimyasallarının temsil ettiği sınıflara eşlenir.

Malzeme ve kalınlık standartta yoktur. Kaynak sırası (2026-10-09):
  1. Kayıt yaptıranın önerisi — ECHA kayıt dosyası "11 Guidance on safe use" el koruması metni
     (component_phys.glove; serbest metinden çıkarılan malzeme / kalınlık / delinme süresi, ham cümle panelde).
     Karışımda ilgili bütün bileşenlerin önerisi varsa ortak malzeme seçilir.
  2. Yoksa sınıfa göre genel kimya bilgisine dayalı ÖNERİ (aşağıdaki tablolar — resmî dayanağı yoktur);
     panelde "doğrulayın" uyarısı verilir.
KDU arayüzde onaylar/değiştirir; GBF'ye seçilen malzeme yazılır. Uyarılar yalnız arayüzde gösterilir.
"""
from typing import Dict, List, Optional

# EN ISO 374-1 test kimyasalları: harf → (sınıf TR, sınıf EN, test kimyasalı TR, EN, CAS, test konsantrasyonu %)
EN374: Dict[str, tuple] = {
    'A': ('alkol', 'alcohol', 'metanol', 'methanol', '67-56-1', 100),
    'B': ('keton', 'ketone', 'aseton', 'acetone', '67-64-1', 100),
    'C': ('nitril bileşiği', 'nitrile compound', 'asetonitril', 'acetonitrile', '75-05-8', 100),
    'D': ('klorlu çözücü', 'chlorinated solvent', 'diklorometan', 'dichloromethane', '75-09-2', 100),
    'E': ('kükürtlü organik bileşik', 'sulphur-containing organic compound', 'karbon disülfür',
          'carbon disulphide', '75-15-0', 100),
    'F': ('aromatik hidrokarbon', 'aromatic hydrocarbon', 'toluen', 'toluene', '108-88-3', 100),
    'G': ('amin', 'amine', 'dietilamin', 'diethylamine', '109-89-7', 100),
    'H': ('eter / heterosiklik bileşik', 'ether / heterocyclic compound', 'tetrahidrofuran', 'tetrahydrofuran',
          '109-99-9', 100),
    'I': ('ester', 'ester', 'etil asetat', 'ethyl acetate', '141-78-6', 100),
    'J': ('alifatik hidrokarbon', 'aliphatic hydrocarbon', 'n-heptan', 'n-heptane', '142-82-5', 100),
    'K': ('inorganik baz', 'inorganic base', 'sodyum hidroksit', 'sodium hydroxide', '1310-73-2', 40),
    'L': ('inorganik mineral asit', 'inorganic mineral acid', 'sülfürik asit', 'sulphuric acid', '7664-93-9', 96),
    'M': ('oksitleyici mineral asit', 'oxidising mineral acid', 'nitrik asit', 'nitric acid', '7697-37-2', 65),
    'N': ('organik asit', 'organic acid', 'asetik asit', 'acetic acid', '64-19-7', 99),
    'O': ('organik/zayıf baz', 'organic/weak base', 'amonyak', 'ammonia', '1336-21-6', 25),
    'P': ('peroksit', 'peroxide', 'hidrojen peroksit', 'hydrogen peroxide', '7722-84-1', 30),
    'S': ('hidroflorik asit', 'hydrofluoric acid', 'hidroflorik asit', 'hydrofluoric acid', '7664-39-3', 40),
    'T': ('aldehit', 'aldehyde', 'formaldehit', 'formaldehyde', '50-00-0', 37),
}

# Yaygın hammaddeler → sınıf harfi (test kimyasalının temsil ettiği kimyasal sınıf)
CAS_CLASS: Dict[str, str] = {
    # A alkoller / glikoller
    '67-56-1': 'A', '64-17-5': 'A', '67-63-0': 'A', '71-23-8': 'A', '71-36-3': 'A', '78-83-1': 'A',
    '78-92-2': 'A', '107-21-1': 'A', '57-55-6': 'A', '100-51-6': 'A', '56-81-5': 'A', '111-46-6': 'A',
    '112-34-5': 'A', '111-76-2': 'A', '107-98-2': 'A', '34590-94-8': 'A',
    # B ketonlar
    '67-64-1': 'B', '78-93-3': 'B', '108-10-1': 'B', '108-94-1': 'B', '141-79-7': 'B',
    # C nitriller
    '75-05-8': 'C',
    # D klorlu çözücüler
    '75-09-2': 'D', '67-66-3': 'D', '79-01-6': 'D', '127-18-4': 'D', '71-55-6': 'D', '107-06-2': 'D',
    # E kükürtlü organikler
    '75-15-0': 'E',
    # F aromatikler
    '108-88-3': 'F', '1330-20-7': 'F', '71-43-2': 'F', '100-41-4': 'F', '95-47-6': 'F', '106-42-3': 'F',
    '108-38-3': 'F', '64742-95-6': 'F', '98-82-8': 'F', '100-42-5': 'F',
    # G aminler (etanolaminler dâhil)
    '109-89-7': 'G', '121-44-8': 'G', '141-43-5': 'G', '111-42-2': 'G', '102-71-6': 'G', '124-40-3': 'G',
    '75-50-3': 'G',
    # H eterler
    '109-99-9': 'H', '60-29-7': 'H', '123-91-1': 'H', '1634-04-4': 'H',
    # I esterler
    '141-78-6': 'I', '123-86-4': 'I', '108-65-6': 'I', '79-20-9': 'I', '110-19-0': 'I', '108-21-4': 'I',
    # J alifatik hidrokarbonlar / yağlar
    '142-82-5': 'J', '110-54-3': 'J', '110-82-7': 'J', '64742-48-9': 'J', '64742-47-8': 'J', '8042-47-5': 'J',
    '8052-41-3': 'J', '64742-81-0': 'J', '64742-46-7': 'J',
    # K inorganik bazlar
    '1310-73-2': 'K', '1310-58-3': 'K', '1305-62-0': 'K', '6834-92-0': 'K', '1344-09-8': 'K', '1310-65-2': 'K',
    # L inorganik mineral asitler (nitrik asit hariç)
    # borik asit (10043-35-3) çıkarıldı: zayıf asit, "inorganik mineral asit" (test kimyasalı %96 H2SO4) sınıfına girmez
    '7664-93-9': 'L', '7647-01-0': 'L', '7664-38-2': 'L', '5329-14-6': 'L',
    # M oksitleyici mineral asit
    '7697-37-2': 'M',
    # N organik asitler
    '64-19-7': 'N', '64-18-6': 'N', '77-92-9': 'N', '5949-29-1': 'N', '79-14-1': 'N', '50-21-5': 'N',
    '79-33-4': 'N', '6915-15-7': 'N', '144-62-7': 'N', '6153-56-6': 'N', '79-09-4': 'N', '87-69-4': 'N',
    '110-15-6': 'N', '124-04-9': 'N', '10605-21-7': 'N',
    # O organik/zayıf bazlar
    '1336-21-6': 'O', '7664-41-7': 'O',
    # P peroksitler
    # amonyum persülfat (7727-54-0) çıkarıldı: persülfat tuzu, "peroksit" (test kimyasalı %30 H2O2) sınıfına girmez
    '7722-84-1': 'P', '79-21-0': 'P', '15630-89-4': 'P',
    # S hidroflorik asit ve HF açığa çıkaranlar
    '7664-39-3': 'S', '1341-49-7': 'S', '12125-01-8': 'S',
    # T aldehitler
    '50-00-0': 'T', '111-30-8': 'T',
}

# Sınıfa göre genelde uygun eldiven malzemeleri (genel kimya bilgisi — ÖNERİ; kullanıcı onaylar)
SUITABLE: Dict[str, List[str]] = {
    'A': ['nitril', 'neopren', 'butil'], 'B': ['butil', 'laminat'], 'C': ['butil', 'laminat'],
    'D': ['viton', 'laminat'], 'E': ['viton', 'laminat'], 'F': ['viton', 'laminat'], 'G': ['butil', 'neopren'],
    'H': ['laminat'], 'I': ['butil', 'laminat'], 'J': ['nitril', 'viton'], 'K': ['nitril', 'neopren', 'butil'],
    'L': ['butil', 'viton', 'neopren'], 'M': ['butil', 'neopren', 'viton'], 'N': ['butil', 'neopren'],
    'O': ['nitril', 'neopren', 'butil'], 'P': ['nitril', 'neopren', 'butil'], 'S': ['neopren', 'butil'],
    'T': ['nitril', 'butil'],
}
# Seyreltik (≤ %30) sulu asit çözeltilerinde nitril de genelde uygundur
DILUTE_OK = {'L': ['nitril', 'neopren'], 'M': ['nitril', 'neopren'], 'N': ['nitril']}
PREF = ['nitril', 'neopren', 'butil', 'viton', 'laminat', 'pvc', 'pva', 'dogal_kaucuk']
# Varsayılan kalınlıklar genel değerdir (üretici verisi değil); kayıt yaptıranın kalınlığı varsa o kullanılır.
# PVC / PVA / doğal kauçuk yalnız kayıt yaptıranın önerisinde geçerse seçenek olur — varsayılan kalınlık yok.
MATERIAL = {
    'nitril':  ('nitril kauçuk', 'nitrile rubber', 0.4),
    'neopren': ('neopren (polikloropren)', 'neoprene (polychloroprene)', 0.5),
    'butil':   ('bütil kauçuk', 'butyl rubber', 0.5),
    'viton':   ('florokauçuk (FKM)', 'fluoroelastomer (FKM)', 0.7),
    'laminat': ('çok katmanlı laminat', 'multilayer laminate', 0.06),
    'pvc':     ('polivinil klorür (PVC)', 'polyvinyl chloride (PVC)', None),
    'pva':     ('polivinil alkol (PVA)', 'polyvinyl alcohol (PVA)', None),
    'dogal_kaucuk': ('doğal kauçuk (lateks)', 'natural rubber (latex)', None),
}

SKIN_SEVERE = {'H310', 'H311', 'H312', 'H314', 'H340', 'H341', 'H350', 'H350i', 'H351', 'H360', 'H360D',
               'H360F', 'H360FD', 'H360Df', 'H360Fd', 'H361', 'H361d', 'H361f', 'H361fd'}
SKIN_LIGHT = {'H315', 'H317', 'H318', 'H319', 'EUH066'}


def _h(c: dict) -> set:
    return {str(h.get('h_code') or '').replace('*', '').strip() for h in (c.get('hazards') or [])} - {''}


def _conc(c: dict) -> float:
    for k in ('concMax', 'conc_max', 'concentration', 'conc'):
        try:
            v = float(c.get(k) or 0)
        except (TypeError, ValueError):
            v = 0.0
        if v:
            return v
    return 0.0


def select(components: List[dict], h_codes: List[str], lang: str = 'TR',
           material: Optional[str] = None, thickness: Optional[float] = None) -> dict:
    """Eldiven önerisi ve GBF metni.
    Döner: {applies, letters:[{letter, sinif, kimyasal}], tip, min_sure_dk, malzeme, kalinlik_mm,
            malzeme_secenekleri, level, text, note, uyarilar:[str]}"""
    tr = lang == 'TR'
    hs = {str(h).replace('*', '').strip() for h in (h_codes or [])}
    severe = bool(hs & SKIN_SEVERE)
    if not severe and not (hs & SKIN_LIGHT):
        return {'applies': False}

    letters, warns, hit = [], [], {}
    for c in components or []:
        cas = str(c.get('cas_no') or c.get('cas') or '').strip()
        if cas == '7732-18-5':
            continue
        conc = _conc(c)
        letter = CAS_CLASS.get(cas)
        name = (c.get('name_tr') if tr else '') or c.get('name') or cas
        if letter and conc < 1 and letter != 'S':   # eser bileşen eldiven sınıfını belirlemez (HF hariç)
            continue
        if letter:
            hit.setdefault(letter, []).append((cas, conc, name))
            test_cas, test_conc = EN374[letter][4], EN374[letter][5]
            if cas == test_cas and conc > test_conc:
                warns.append(f'{name} %{conc:g}: EN ISO 374-1 test konsantrasyonundan (%{test_conc}) yüksek — '
                             f'"{letter}" harfinin minimum süre garantisi bu konsantrasyonu kapsamaz.')
            if letter == 'S':
                warns.append(f'{name}: hidroflorik asit / HF açığa çıkaran madde — eldiven ve ilk yardım '
                             '(kalsiyum glukonat) özel değerlendirme gerektirir.')
        elif _h(c) and conc >= 1:
            warns.append(f'{name} (CAS {cas or "—"}): EN ISO 374-1 kimyasal sınıfı belirlenemedi — malzemeyi '
                         'doğrulayın.')
    for L in sorted(hit):
        letters.append({'letter': L, 'sinif': EN374[L][0] if tr else EN374[L][1],
                        'kimyasal': EN374[L][2] if tr else EN374[L][3]})

    # 1) Kayıt yaptıranın önerisi (ECHA kayıt dosyası, 11 Guidance on safe use) — ilgili bileşenler: ≥ %1 ve
    #    sınıflandırılmış ya da EN 374 sınıfı olan (su hariç)
    from app.services.component_phys import glove as _reg_glove
    relevant, reg, kaynaklar = [], {}, []
    for c in components or []:
        cas = str(c.get('cas_no') or c.get('cas') or '').strip()
        if not cas or cas == '7732-18-5' or _conc(c) < 1 or not (_h(c) or CAS_CLASS.get(cas)):
            continue
        name = ((c.get('name_tr') if tr else '') or c.get('name') or cas).split(';')[0].strip()
        relevant.append((cas, name))
        g = _reg_glove(cas)
        if g.get('malzemeler'):
            reg[cas] = g
            kaynaklar.append({'ad': name, 'ref': g.get('ref'), 'metin': g.get('metin'),
                              'malzemeler': g['malzemeler'], 'kalinlik_mm': g.get('kalinlik_mm'),
                              'delinme_dk': g.get('delinme_dk')})
    reg_common = None
    if relevant and len(reg) == len(relevant):
        for g in reg.values():
            reg_common = set(g['malzemeler']) if reg_common is None else reg_common & set(g['malzemeler'])
    kaynak = 'kayit' if reg_common else 'genel'
    if kaynak == 'kayit':
        options = [m for m in PREF if m in reg_common]
    else:
        # 2) Genel tablo (resmî dayanağı yok): tüm sınıflara uygun ortak malzeme
        common = None
        for L, items in hit.items():
            ok = set(SUITABLE[L])
            if L in DILUTE_OK and all(cc <= 30 for _, cc, _ in items):
                ok |= set(DILUTE_OK[L])
            common = ok if common is None else common & ok
        options = [m for m in PREF if common and m in common] if hit else ['nitril']
        if hit and not options:
            warns.append('Bileşen sınıflarının hepsine uygun ortak bir eldiven malzemesi bulunamadı — '
                         'malzemeyi seçin (gerekirse çok katmanlı laminat).')
            options = [m for m in PREF if MATERIAL[m][2] is not None]
        if not hit and not warns:
            warns.append('Hiçbir bileşen için EN ISO 374-1 kimyasal sınıfı belirlenemedi — malzemeyi doğrulayın.')
        eksik = [n for cas, n in relevant if cas not in reg]
        if reg and reg_common is not None and not reg_common:
            warns.append('Kayıt yaptıranların önerdiği malzemelerde bileşenlerin hepsine ortak bir malzeme yok — '
                         'eldiven üreticisine danışarak seçin.')
        warns.append('Malzeme / kalınlık genel kimya bilgisine dayalı öneridir (resmî dayanağı yok)'
                     + (f'; kayıt yaptıran önerisi bulunamayan bileşen: {", ".join(eksik)}' if eksik else '')
                     + ' — eldiven üreticisinin verisiyle doğrulayın.')

    mat = material if material in MATERIAL else options[0]
    mat_tr, mat_en, t_default = MATERIAL[mat]
    if kaynak == 'kayit' and mat not in reg_common:
        # KDU kayıt yaptıranın önermediği bir malzeme seçti — kaynak gösterilmez, doğrulama uyarısı
        kaynak = 'secim'
        warns.append(f'Seçilen malzeme ({mat_tr}) kayıt yaptıranın önerisinde yok — eldiven üreticisinin verisiyle '
                     'doğrulayın.')
    # Kayıt yaptıranın bu malzeme için verdiği kalınlık (en büyüğü) varsayılandan önce gelir
    _reg_t = [g['kalinlik_mm'] for g in reg.values() if g.get('kalinlik_mm') and mat in g['malzemeler']]
    _t_from_reg = bool(_reg_t and kaynak == 'kayit')
    if _t_from_reg:
        t_default = max(_reg_t)
    try:
        t = float(thickness) if thickness not in (None, '') else t_default
    except (TypeError, ValueError):
        t = t_default
    t_txt = (f'{t:g}'.replace('.', ',') if tr else f'{t:g}') if t is not None else None
    if t is not None and kaynak == 'kayit' and not _t_from_reg and thickness in (None, ''):
        warns.append(f'Kalınlık kayıt yaptıranın önerisinde yok — genel değer ({t_txt} mm) kullanıldı; eldiven '
                     'üreticisinin verisiyle doğrulayın.')
    if t is None:
        warns.append('Kalınlık girilmedi — KKDİK Ek-2 8.2.2.2(b)(i) malzeme kalınlığını ister; eldiven üreticisinin '
                     'verisini girin.')
    # Tipik delinme süresi: kayıt yaptıranların verdiği değerlerin en küçüğü (saf madde için)
    _reg_bt = [g['delinme_dk'] for g in reg.values() if g.get('delinme_dk') and mat in g['malzemeler']]
    typ_bt = min(_reg_bt) if (kaynak == 'kayit' and _reg_bt and len(_reg_bt) == len(reg)) else None
    _src_tr = (' (malzeme: kayıt yaptıranın önerisi — ' + '; '.join(sorted({g['ref'] for g in reg.values()})) + ')'
               if kaynak == 'kayit' else '')
    _bt_tr = (f' Tipik delinme süresi > {typ_bt} dk (kayıt yaptıranın verisi, saf madde için).' if typ_bt else '')
    _thk_tr = f', ≥ {t_txt} mm' if t_txt else ''
    _thk_en = f', ≥ {t_txt} mm' if t_txt else ''

    tip = 'A veya B' if severe else 'A, B veya C'
    tip_en = 'A or B' if severe else 'A, B or C'
    min_dk, lvl = (30, 2) if severe else (10, 1)
    if letters:
        many = len(letters) > 1
        if tr:
            lt = ', '.join(f'"{x["letter"]}" ({x["sinif"]}; test kimyasalı {x["kimyasal"]})' for x in letters)
            text = (f'Kimyasal koruyucu eldiven: {mat_tr}{_src_tr}{_thk_tr}. EN ISO 374-1 Tip {tip}, {lt} '
                    f'harf{"leri" if many else "i"} ile işaretli; işaretli test kimyasal{"ları" if many else "ı"} '
                    f'için minimum delinme süresi ≥ {min_dk} dk (EN 16523-1, seviye {lvl}).{_bt_tr}')
        else:
            lt = ', '.join(f'"{x["letter"]}" ({x["sinif"]}; test chemical {x["kimyasal"]})' for x in letters)
            text = (f'Chemical protective gloves: {mat_en}{_thk_en}. EN ISO 374-1 Type {tip_en}, marked with '
                    f'letter{"s" if many else ""} {lt}; minimum breakthrough time for the marked test '
                    f'chemical{"s" if many else ""} ≥ {min_dk} min (EN 16523-1, level {lvl}).')
        note = ('Eldivenler hasar, bozulma veya kirlenme belirtisinde hemen değiştirilmelidir; delinme süresi '
                'kullanım koşullarında (sıcaklık, mekanik zorlanma) laboratuvar değerinden kısa olabilir.') if tr else (
                'Replace gloves immediately at signs of damage, degradation or contamination; the breakthrough '
                'time may be shorter than the laboratory value under conditions of use (temperature, mechanical '
                'stress).')
    else:
        text = (f'Kimyasal koruyucu eldiven: {mat_tr}{_src_tr}{_thk_tr} (EN ISO 374-1 Tip {tip}).{_bt_tr}' if tr else
                f'Chemical protective gloves: {mat_en}{_thk_en} (EN ISO 374-1 Type {tip_en}).')
        note = None
    return {
        'applies': True, 'letters': letters, 'tip': tip if tr else tip_en, 'min_sure_dk': min_dk if letters else None,
        'malzeme': mat, 'kalinlik_mm': t, 'malzeme_secenekleri': options,
        'malzeme_adlari': {k: (v[0] if tr else v[1]) for k, v in MATERIAL.items()},
        'varsayilan_kalinlik': {k: v[2] for k, v in MATERIAL.items()},
        'level': 1 if severe else 2, 'text': text, 'note': note, 'uyarilar': warns,
        'kaynak': kaynak, 'kayit_onerileri': kaynaklar,
    }
