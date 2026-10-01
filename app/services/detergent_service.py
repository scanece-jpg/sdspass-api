"""
Deterjanlar Hakkında Yönetmelik (RG 27.01.2018/30314; Ticaret Bakanlığı) — Ek-7 A içerik beyanı.

Ek-7 A "İçeriğin etikette belirtilmesi" (resmî ek metninden):
  * Aşağıdaki sınıflar ağırlıkça %0,2'nin üzerinde eklenmişse %5'ten az / %5–<15 / %15–<30 /
    %30 ve daha çok aralıklarıyla belirtilir: fosfatlar, fosfonatlar, anyonik / katyonik /
    amfoterik / noniyonik yüzey aktif maddeler, oksijen bazlı ağartıcılar, klor bazlı ağartıcılar,
    EDTA ve tuzları, fenoller ve halojenli fenoller, para-diklorobenzen, aromatik / alifatik /
    halojenli hidrokarbonlar, sabun, zeolitler, polikarboksilatlar.
  * Enzimler, dezenfektanlar, optik parlatıcılar, parfümler konsantrasyondan bağımsız listelenir.
  * Koruyucu maddeler konsantrasyondan bağımsız (Kozmetik Yönetmeliği ortak terminolojisiyle).
  * Kozmetik Yönetmeliği Ek-III'teki koku alerjenleri ağırlıkça %0,01'i geçerse listelenir.
  * Son paragraf: "Endüstriyel ve kurumsal sektörde kullanılması amaçlanan ve halkın kullanımına
    sunulmayan deterjanlar için; teknik veri belgesi, malzeme güvenlik veri belgesi veya benzer
    şekildeki belgeler aracılığı ile eş değer bilgilerin temin edilmesi halinde, yukarıda bahsi
    geçen gerekliliklerin karşılanması zorunlu değildir." → profesyonel üründe bu bilgi GBF 15.1'de.

Bileşenin sınıfı: kullanıcının bileşen satırında seçtiği sınıf (det_class) önce gelir; seçilmemişse
aşağıdaki CAS tablosundan. Tabloda olmayan bileşen beyana girmez (tahmin yapılmaz).
"""
from typing import Dict, List

# Ek-7 A sınıfları — anahtar: (TR adı, EN adı, bant mı?)
CLASSES: Dict[str, tuple] = {
    'phosphate':      ('fosfatlar', 'phosphates', True),
    'phosphonate':    ('fosfonatlar', 'phosphonates', True),
    'anionic':        ('anyonik yüzey aktif maddeler', 'anionic surfactants', True),
    'cationic':       ('katyonik yüzey aktif maddeler', 'cationic surfactants', True),
    'amphoteric':     ('amfoterik yüzey aktif maddeler', 'amphoteric surfactants', True),
    'nonionic':       ('noniyonik yüzey aktif maddeler', 'non-ionic surfactants', True),
    'oxygen_bleach':  ('oksijen bazlı ağartıcılar', 'oxygen-based bleaching agents', True),
    'chlorine_bleach': ('klor bazlı ağartıcılar', 'chlorine-based bleaching agents', True),
    'edta':           ('EDTA ve tuzları', 'EDTA and salts thereof', True),
    'phenol':         ('fenoller ve halojenli fenoller', 'phenols and halogenated phenols', True),
    'pdcb':           ('para-diklorobenzen', 'paradichlorobenzene', True),
    'aromatic_hc':    ('aromatik hidrokarbonlar', 'aromatic hydrocarbons', True),
    'aliphatic_hc':   ('alifatik hidrokarbonlar', 'aliphatic hydrocarbons', True),
    'halogenated_hc': ('halojenli hidrokarbonlar', 'halogenated hydrocarbons', True),
    'soap':           ('sabun', 'soap', True),
    'zeolite':        ('zeolitler', 'zeolites', True),
    'polycarboxylate': ('polikarboksilatlar', 'polycarboxylates', True),
    # konsantrasyondan bağımsız listelenenler
    'enzyme':         ('enzimler', 'enzymes', False),
    'disinfectant':   ('dezenfektanlar', 'disinfectants', False),
    'optical_brightener': ('optik parlatıcılar', 'optical brighteners', False),
    'perfume':        ('parfümler', 'perfumes', False),
    'preservative':   ('koruyucu maddeler', 'preservation agents', False),
}

# Sık kullanılan deterjan hammaddeleri — CAS → Ek-7 A sınıfı
CAS_CLASS: Dict[str, str] = {
    # fosfatlar
    '7758-29-4': 'phosphate', '7601-54-9': 'phosphate', '7722-88-5': 'phosphate', '10124-56-8': 'phosphate',
    '7758-16-9': 'phosphate', '13845-36-8': 'phosphate', '7558-79-4': 'phosphate', '7558-80-7': 'phosphate',
    '7778-53-2': 'phosphate',
    # fosfonatlar
    '2809-21-4': 'phosphonate', '29329-71-3': 'phosphonate', '6419-19-8': 'phosphonate',
    '15827-60-8': 'phosphonate', '22042-96-2': 'phosphonate', '37971-36-1': 'phosphonate',
    '20592-85-2': 'phosphonate', '3794-83-0': 'phosphonate',
    # anyonik
    '68411-30-3': 'anionic', '25155-30-0': 'anionic', '27176-87-0': 'anionic', '68584-22-5': 'anionic',
    '85536-14-7': 'anionic', '68891-38-3': 'anionic', '9004-82-4': 'anionic', '151-21-3': 'anionic',
    '68585-47-7': 'anionic', '68439-57-6': 'anionic', '1300-72-7': 'anionic', '28348-53-0': 'anionic',
    '26836-07-7': 'anionic', '139-96-8': 'anionic', '68081-81-2': 'anionic', '85117-50-6': 'anionic',
    # katyonik (dezenfektan olarak da kullanılır — kullanıcı det_class ile değiştirebilir)
    '68424-85-1': 'cationic', '63449-41-2': 'cationic', '7173-51-5': 'cationic', '8001-54-5': 'cationic',
    '139-07-1': 'cationic', '61789-71-7': 'cationic',
    # amfoterik
    '61789-40-0': 'amphoteric', '86438-79-1': 'amphoteric', '1643-20-5': 'amphoteric',
    '70592-80-2': 'amphoteric', '68155-09-9': 'amphoteric', '683-10-3': 'amphoteric',
    # noniyonik
    '68213-23-0': 'nonionic', '68439-46-3': 'nonionic', '69011-36-5': 'nonionic', '9002-92-0': 'nonionic',
    '68131-39-5': 'nonionic', '160875-66-1': 'nonionic', '68515-73-1': 'nonionic', '110615-47-9': 'nonionic',
    '9043-30-5': 'nonionic', '68551-12-2': 'nonionic', '84133-50-6': 'nonionic', '68002-97-1': 'nonionic',
    '9016-45-9': 'nonionic', '127087-87-0': 'nonionic', '9036-19-5': 'nonionic', '26183-52-8': 'nonionic',
    '68154-97-2': 'nonionic', '9003-11-6': 'nonionic', '61791-12-6': 'nonionic',
    # ağartıcılar
    '15630-89-4': 'oxygen_bleach', '7632-04-4': 'oxygen_bleach', '10486-00-7': 'oxygen_bleach',
    '11138-47-9': 'oxygen_bleach', '7722-84-1': 'oxygen_bleach', '79-21-0': 'oxygen_bleach',
    '10332-33-9': 'oxygen_bleach',
    '7681-52-9': 'chlorine_bleach', '7778-54-3': 'chlorine_bleach', '2893-78-9': 'chlorine_bleach',
    '51580-86-0': 'chlorine_bleach', '87-90-1': 'chlorine_bleach', '10049-04-4': 'chlorine_bleach',
    # EDTA ve tuzları
    '60-00-4': 'edta', '64-02-8': 'edta', '6381-92-6': 'edta', '139-33-3': 'edta', '17421-79-3': 'edta',
    '10378-23-1': 'edta',
    # fenoller / p-DCB / hidrokarbonlar
    '108-95-2': 'phenol', '3380-34-5': 'phenol', '59-50-7': 'phenol', '88-04-0': 'phenol',
    '106-46-7': 'pdcb',
    '1330-20-7': 'aromatic_hc', '108-88-3': 'aromatic_hc', '64742-95-6': 'aromatic_hc',
    '64742-47-8': 'aliphatic_hc', '64742-48-9': 'aliphatic_hc', '64742-46-7': 'aliphatic_hc',
    '64771-72-8': 'aliphatic_hc', '8042-47-5': 'aliphatic_hc', '64741-65-7': 'aliphatic_hc',
    '127-18-4': 'halogenated_hc', '75-09-2': 'halogenated_hc', '79-01-6': 'halogenated_hc',
    # sabun
    '61790-79-7': 'soap', '61789-30-8': 'soap', '61790-44-6': 'soap', '822-16-2': 'soap',
    '143-18-0': 'soap', '61789-31-9': 'soap', '67701-10-4': 'soap',
    # zeolit / polikarboksilat
    '1318-02-1': 'zeolite', '1344-00-9': 'zeolite',
    '9003-04-7': 'polycarboxylate', '52255-49-9': 'polycarboxylate', '9003-01-4': 'polycarboxylate',
    '25987-30-8': 'polycarboxylate', '76774-25-9': 'polycarboxylate',
    # enzimler
    '9014-01-1': 'enzyme', '9000-90-2': 'enzyme', '9000-85-5': 'enzyme', '9001-62-1': 'enzyme',
    '9012-54-8': 'enzyme', '37278-89-0': 'enzyme', '9068-59-1': 'enzyme', '9025-70-1': 'enzyme',
    # optik parlatıcılar
    '16090-02-1': 'optical_brightener', '27344-41-8': 'optical_brightener', '4193-55-9': 'optical_brightener',
    # koruyucular (deterjanlarda yaygın)
    '2682-20-4': 'preservative', '26172-55-4': 'preservative', '55965-84-9': 'preservative',
    '2634-33-5': 'preservative', '52-51-7': 'preservative', '532-32-1': 'preservative',
    '24634-61-5': 'preservative',
}

# Kozmetik Yönetmeliği Ek-III koku alerjenleri (klasik 26 madde; Ek-III'e sonradan eklenenler
# de Ek-7 A gereği listelenmelidir — bu tablo güncel listeyle genişletilmelidir)
ALLERGENS: Dict[str, str] = {
    '122-40-7': 'AMYL CINNAMAL', '100-51-6': 'BENZYL ALCOHOL', '104-54-1': 'CINNAMYL ALCOHOL',
    '5392-40-5': 'CITRAL', '97-53-0': 'EUGENOL', '107-75-5': 'HYDROXYCITRONELLAL',
    '97-54-1': 'ISOEUGENOL', '101-85-9': 'AMYLCINNAMYL ALCOHOL', '118-58-1': 'BENZYL SALICYLATE',
    '104-55-2': 'CINNAMAL', '91-64-5': 'COUMARIN', '106-24-1': 'GERANIOL',
    '31906-04-4': 'HYDROXYISOHEXYL 3-CYCLOHEXENE CARBOXALDEHYDE', '105-13-5': 'ANISE ALCOHOL',
    '103-41-3': 'BENZYL CINNAMATE', '4602-84-0': 'FARNESOL', '80-54-6': 'BUTYLPHENYL METHYLPROPIONAL',
    '78-70-6': 'LINALOOL', '120-51-4': 'BENZYL BENZOATE', '106-22-9': 'CITRONELLOL',
    '101-86-0': 'HEXYL CINNAMAL', '5989-27-5': 'LIMONENE', '138-86-3': 'LIMONENE',
    '111-12-6': 'METHYL 2-OCTYNOATE', '127-51-5': 'ALPHA-ISOMETHYL IONONE',
    '90028-68-5': 'EVERNIA PRUNASTRI EXTRACT', '90028-67-4': 'EVERNIA FURFURACEA EXTRACT',
}

_BANDS = [(30.0, '%30 ve daha çok', '30% and more'),
          (15.0, '%15 veya daha çok, ancak %30\'dan az', '15% or over but less than 30%'),
          (5.0, '%5 veya daha çok, ancak %15\'ten az', '5% or over but less than 15%'),
          (0.0, '%5\'ten az', 'less than 5%')]


def _conc(c: dict) -> float:
    try:
        return float(c.get('concMax') or c.get('conc') or c.get('concentration') or 0)
    except (TypeError, ValueError):
        return 0.0


def ek7a_declaration(components: List[dict]) -> Dict:
    """Ek-7 A içerik beyanı: {'bands': [(band_tr, band_en, [sınıf anahtarları])], 'always': [...],
    'allergens': [...], 'unassigned': [bileşen adı]}"""
    sums: Dict[str, float] = {}
    always: List[str] = []
    allergens: List[str] = []
    for c in components or []:
        cas = str(c.get('cas_no') or c.get('cas') or '').strip()
        conc = _conc(c)
        cls = (c.get('det_class') or '').strip() or CAS_CLASS.get(cas)
        if cls == 'none':
            cls = None
        if cls in CLASSES:
            if CLASSES[cls][2]:
                sums[cls] = sums.get(cls, 0.0) + conc
            elif cls not in always:
                always.append(cls)
        if cas in ALLERGENS and conc > 0.01 and ALLERGENS[cas] not in allergens:
            allergens.append(ALLERGENS[cas])
    bands = []
    for i, (lo, tr, en) in enumerate(_BANDS):
        hi = _BANDS[i - 1][0] if i > 0 else None
        keys = [k for k, v in sums.items() if v > 0.2 and v >= lo and (hi is None or v < hi)]
        if keys:
            bands.append((tr, en, sorted(keys, key=lambda k: list(CLASSES).index(k))))
    return {'bands': bands, 'always': always, 'allergens': allergens}


def ek7a_lines(components: List[dict], usage: str = 'industrial', lang: str = 'TR') -> List[str]:
    """GBF 15.1 satırları."""
    d = ek7a_declaration(components)
    tr = lang == 'TR'
    out = [('Deterjanlar Hakkında Yönetmelik (RG: 27.01.2018, Sayı: 30314) — Ek-7 A içerik beyanı:' if tr else
            'Detergents Regulation (TR Official Gazette 27.01.2018, No. 30314; EU 648/2004) — Annex VII A '
            'ingredients:')]
    for btr, ben, keys in d['bands']:
        names = ', '.join(CLASSES[k][0 if tr else 1] for k in keys)
        out.append(f"• {btr if tr else ben}: {names}")
    if d['always']:
        out.append(('• Ayrıca: ' if tr else '• Also: ') + ', '.join(CLASSES[k][0 if tr else 1] for k in d['always']))
    if d['allergens']:
        out.append(('• Koku alerjenleri (%0,01 üzeri): ' if tr else '• Fragrance allergens (> 0.01%): ')
                   + ', '.join(d['allergens']))
    if len(out) == 1:
        out.append('• Ek-7 A kapsamında beyan edilecek bileşen sınıfı bulunmamaktadır.' if tr else
                   '• No ingredient classes subject to Annex VII A declaration.')
    if usage != 'consumer':
        out.append('Ürün endüstriyel/kurumsal kullanıma yöneliktir ve halka sunulmamaktadır; Ek-7 A içerik '
                   'bilgisi bu Güvenlik Bilgi Formu ile sağlanmaktadır (Ek-7 A son paragraf).' if tr else
                   'Product intended for industrial/institutional use and not made available to the general '
                   'public; Annex VII A information is provided by this SDS.')
    return out
