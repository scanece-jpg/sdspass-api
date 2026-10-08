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
  * Kozmetik Yönetmeliği Ek-III'teki koku alerjenleri ağırlıkça %0,01'i geçerse listelenir. Ek-7 A
    23/5/2005 tarihli ve 25823 sayılı Kozmetik Yönetmeliği'ne atıf yapar; bu yönetmelik, 8/5/2023
    tarihli ve 32184 (mükerrer) sayılı RG'de yayımlanan Kozmetik Ürünler Yönetmeliği (TİTCK) Md.38 ile
    yürürlükten kalkmıştır — güncel liste bu yönetmeliğin Ek-III'üdür.
  * Son paragraf: "Endüstriyel ve kurumsal sektörde kullanılması amaçlanan ve halkın kullanımına
    sunulmayan deterjanlar için; teknik veri belgesi, malzeme güvenlik veri belgesi veya benzer
    şekildeki belgeler aracılığı ile eş değer bilgilerin temin edilmesi halinde, yukarıda bahsi
    geçen gerekliliklerin karşılanması zorunlu değildir." → profesyonel üründe bu bilgi GBF 15.1'de.

Bileşenin sınıfı: kullanıcının bileşen satırında seçtiği sınıf (det_class) önce gelir; seçilmemişse
aşağıdaki CAS tablosundan. Tabloda olmayan bileşen beyana girmez (tahmin yapılmaz).
"""
import re
from typing import Dict, List

# Adı yüzey aktif maddeye işaret eden bileşenler (yalnız uyarı için — sınıf tahmini YAPILMAZ)
_SURF_NAME = re.compile(r'(?i)ethoxyl|etoksil|propoxyl|sulfat|sulphat|sülfat|sulfonat|sulphonat|sülfonat|'
                        r'betain|glucosid|glukozit|glikozit|amine oxide|amin oksit|quaternary|kuaterner|'
                        r'alkyl ?poly|sarcosin|isethion|taurat|sabun|soap')

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
    # yağ alkolü etoksilatları (alkol etoksilatlar) — noniyonik
    '68439-50-9': 'nonionic', '68439-49-6': 'nonionic', '68131-40-8': 'nonionic', '66455-14-9': 'nonionic',
    '68951-67-7': 'nonionic', '34398-01-1': 'nonionic', '24938-91-8': 'nonionic', '9004-98-2': 'nonionic',
    '68920-66-1': 'nonionic',
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
    '61789-30-8': 'soap', '822-16-2': 'soap',   # 61790-79-7 / 61790-44-6 geçersiz CAS'tı — çıkarıldı
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

# Kozmetik Ürünler Yönetmeliği Ek III koku alerjenleri — klasik 26 madde (2024 listesi aşağıda eklenir)
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

# Kozmetik Ürünler Yönetmeliği Ek III — RG 05.03.2024/32480 değişikliğiyle eklenen/değiştirilen koku
# alerjenleri (Ek III sıra no → etiket adı; gruplanmış alerjenlerde grup adı, h sütunu). Kaynak: Resmî
# Gazete taranmış ek metni, sayfa sayfa okunarak; TİTCK KÜD-KLVZ-57 kılavuzu (11.06.2026) ile uyumlu.
# Yürürlük dipnotu (40): 31.07.2026'dan itibaren uymayan ürün piyasaya arz edilemez.
ALLERGENS_EK3_2024: Dict[str, tuple] = {
    '45': ('BENZYL ALCOHOL', ['100-51-6']),
    '46': ('6-METHYL COUMARIN', ['92-48-8']),
    '70': ('CITRAL', ['5392-40-5', '141-27-5', '106-26-3']),
    '73': ('ISOEUGENOL', ['97-54-1', '5932-68-3', '5912-86-7']),
    '86': ('CITRONELLOL', ['106-22-9', '26489-01-0', '1117-61-9', '7540-51-4']),
    '88': ('LIMONENE', ['138-86-3', '7705-14-8', '5989-27-5', '5989-54-8']),
    '109': ('PINUS MUGO', ['90082-72-7']),
    '114': ('PINUS PUMILA', ['97676-05-6']),
    '122': ('CEDRUS ATLANTICA OIL/EXTRACT', ['92201-55-3', '8023-85-6']),
    '124': ('TURPENTINE', ['9005-90-7', '8006-64-2', '8052-14-0']),
    '131': ('ALPHA-TERPINENE', ['99-86-5']),
    '133': ('TERPINOLENE', ['586-62-9']),
    '154': ('MYROXYLON PEREIRAE OIL/EXTRACT', ['8007-00-9']),
    '157': ('ROSE KETONES', ['43052-87-5', '23726-94-5', '24720-09-0', '23696-85-7', '57378-68-4', '71048-82-3', '23726-92-3', '23726-91-2']),
    '175': ('3-PROPYLIDENEPHTHALIDE', ['17369-59-4']),
    '196': ('LIPPIA CITRIODORA ABSOLUTE', ['8024-12-2', '85116-63-8']),
    '324': ('METHYL SALICYLATE', ['119-36-8']),
    '327': ('ACETYL CEDRENE', ['32388-55-9']),
    '328': ('AMYL SALICYLATE', ['2050-08-0']),
    '329': ('ANETHOLE', ['104-46-1', '4180-23-8']),
    '330': ('BENZALDEHYDE', ['100-52-7']),
    '331': ('CAMPHOR', ['76-22-2', '21368-68-3', '464-49-3', '464-48-2']),
    '332': ('BETA-CARYOPHYLLENE', ['87-44-5']),
    '333': ('CARVONE', ['99-49-0', '6485-40-1', '2244-16-8']),
    '334': ('DIMETHYL PHENETHYL ACETATE', ['151-05-3']),
    '335': ('HEXADECANOLACTONE', ['109-29-5']),
    '336': ('HEXAMETHYLINDANOPYRAN', ['1222-05-5']),
    '337': ('LINALYL ACETATE', ['115-95-7']),
    '338': ('MENTHOL', ['89-78-1', '1490-04-6', '2216-51-5', '15356-60-2']),
    '339': ('TRIMETHYLCYCLOPENTENYL METHYLISOPENTENOL', ['67801-20-1']),
    '340': ('SALICYLALDEHYDE', ['90-02-8']),
    '341': ('SANTALOL', ['11031-45-1', '115-71-9', '77-42-9']),
    '342': ('SCLAREOL', ['515-03-7']),
    '343': ('TERPINEOL', ['8000-41-7', '98-55-5', '138-87-4', '586-81-2']),
    '344': ('TETRAMETHYL ACETYLOCTAHYDRONAPHTHALENES', ['54464-57-2', '54464-59-4', '68155-66-8', '68155-67-9']),
    '345': ('TRIMETHYLBENZENEPROPANOL', ['103694-68-4']),
    '346': ('VANILLIN', ['121-33-5']),
    '347': ('CANANGA ODORATA OIL/EXTRACT', ['83863-30-3', '8006-81-3', '68606-83-7', '93686-30-7']),
    '348': ('CINNAMOMUM CASSIA LEAF OIL', ['8007-80-5', '84961-46-6']),
    '349': ('CINNAMOMUM ZEYLANICUM BARK OIL', ['8015-91-6', '84649-98-9']),
    '350': ('CITRUS AURANTIUM FLOWER OIL', ['72968-50-4', '8028-48-6', '8016-38-4']),
    '351': ('CITRUS AURANTIUM PEEL OIL', ['68916-04-1', '97766-30-8', '8008-57-9']),
    '352': ('CITRUS AURANTIUM BERGAMIA PEEL OIL', ['8007-75-8', '89957-91-5', '68648-33-9', '85049-52-1']),
    '353': ('CITRUS LIMON PEEL OIL', ['84929-31-7', '8008-56-8']),
    '354': ('LEMONGRASS OIL', ['8007-02-1', '89998-16-3', '91844-92-7']),
    '355': ('EUCALYPTUS GLOBULUS OIL', ['97926-40-4', '8000-48-4']),
    '356': ('EUGENIA CARYOPHYLLUS OIL', ['8000-34-8', '8015-97-2', '84961-50-2']),
    '357': ('JASMINE OIL/EXTRACT', ['84776-64-7', '90045-94-6', '8022-96-6', '8024-43-9']),
    '358': ('JUNIPERUS VIRGINIANA OIL', ['8000-27-9', '85085-41-2']),
    '359': ('LAURUS NOBILIS LEAF OIL', ['8002-41-3', '8007-48-5', '84603-73-6']),
    '360': ('LAVANDULA OIL/EXTRACT', ['91722-69-9', '8022-15-9', '93455-96-0', '93455-97-1', '92623-76-2', '84776-65-8', '8000-28-0', '90063-37-9']),
    '361': ('MENTHA PIPERITA OIL', ['8006-90-4', '84082-70-2']),
    '362': ('MENTHA VIRIDIS LEAF OIL', ['8008-79-5', '84696-51-5']),
    '363': ('NARCISSUS EXTRACT', ['90064-26-9', '68917-12-4', '90064-27-0', '90064-25-8']),
    '364': ('PELARGONIUM GRAVEOLENS FLOWER OIL', ['90082-51-2', '8000-46-2']),
    '365': ('POGOSTEMON CABLIN OIL', ['8014-09-3', '84238-39-1']),
    '366': ('ROSE FLOWER OIL/EXTRACT', ['8007-01-0', '90106-38-0', '93334-48-6', '84696-47-9', '84604-12-6', '84604-13-7', '92347-25-6']),
    '367': ('SANTALUM ALBUM OIL', ['8006-87-9', '84787-70-2']),
    '368': ('EUGENYL ACETATE', ['93-28-7']),
    '369': ('GERANYL ACETATE', ['105-87-3']),
    '370': ('ISOEUGENYL ACETATE', ['93-29-8']),
    '371': ('PINENE', ['80-56-8', '7785-70-8', '127-91-3', '18172-67-3']),
}

# CAS → etiket adı (klasik 26 + 2024 genişletilmiş liste; aynı CAS birden çok satırda ise ilk satır)
for _ref, (_name, _cases) in ALLERGENS_EK3_2024.items():
    for _c in _cases:
        ALLERGENS.setdefault(_c, _name)

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
    al_sum: Dict[str, float] = {}   # gruplanmış alerjenlerde grup üyelerinin toplamı (KÜD-KLVZ-57 Ek-2)
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
        if cas in ALLERGENS:
            al_sum[ALLERGENS[cas]] = al_sum.get(ALLERGENS[cas], 0.0) + conc
    allergens = [n for n, v in al_sum.items() if v > 0.01]   # Ek-7 A: ağırlıkça %0,01'i geçen
    # Sınıfı belirlenmemiş ama adı yüzey aktif maddeye işaret eden bileşenler — sınıf tahmin edilmez,
    # yalnız "beyan edilecek sınıf yok" gibi yanlış bir kesin ifade basılmasın diye ayrıca bildirilir
    unassigned = []
    for c in components or []:
        cas = str(c.get('cas_no') or c.get('cas') or '').strip()
        cls = (c.get('det_class') or '').strip() or CAS_CLASS.get(cas)
        nm = str(c.get('name_tr') or c.get('name') or cas)
        if not cls and cas != '7732-18-5' and _SURF_NAME.search(nm):
            unassigned.append(nm)
    bands = []
    for i, (lo, tr, en) in enumerate(_BANDS):
        hi = _BANDS[i - 1][0] if i > 0 else None
        keys = [k for k, v in sums.items() if v > 0.2 and v >= lo and (hi is None or v < hi)]
        if keys:
            bands.append((tr, en, sorted(keys, key=lambda k: list(CLASSES).index(k))))
    return {'bands': bands, 'always': always, 'allergens': allergens, 'unassigned': unassigned}


SURFACTANT_CLASSES = {'anionic', 'cationic', 'amphoteric', 'nonionic', 'soap'}


def has_surfactant(components: List[dict]) -> bool:
    for c in components or []:
        cas = str(c.get('cas_no') or c.get('cas') or '').strip()
        cls = (c.get('det_class') or '').strip() or CAS_CLASS.get(cas)
        if cls in SURFACTANT_CLASSES:
            return True
    return False


def biodegradability_line(lang: str = 'TR') -> str:
    """12.2 — Deterjanlar Hakkında Yönetmelik Md.6(1): Ek-3'teki nihai aerobik biyolojik
    parçalanabilirlik kriterlerine uyan yüzey aktif maddeler kısıtlamasız piyasaya arz edilir
    (Md.6(2): endüstriyel/kurumsal üründe istisna talep edilebilir — istisnalı üründe kullanılmamalı)."""
    return ('Üründe bulunan yüzey aktif maddeler, Deterjanlar Hakkında Yönetmelik (RG: 27.01.2018, Sayı: 30314) '
            'Md.6 ve Ek-3\'te belirtilen nihai aerobik biyolojik parçalanabilirlik kriterlerine uygundur.'
            if lang == 'TR' else
            'The surfactant(s) contained in this product comply with the ultimate aerobic biodegradability '
            'criteria of the Detergents Regulation (TR Official Gazette 30314; EU 648/2004).')


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
    if d.get('unassigned'):
        out.append(('• Ek-7 A sınıfı belirlenmemiş (yüzey aktif madde olabilecek) bileşen: ' if tr else
                    '• Component(s) without an Annex VII A class (possibly surfactant): ')
                   + ', '.join(d['unassigned'])
                   + (' — sınıfı KDU tarafından belirlenmelidir.' if tr else ' — class to be determined.'))
    elif len(out) == 1:
        out.append('• Ek-7 A kapsamında beyan edilecek bileşen sınıfı bulunmamaktadır.' if tr else
                   '• No ingredient classes subject to Annex VII A declaration.')
    if usage != 'consumer':
        out.append('Ürün endüstriyel/kurumsal kullanıma yöneliktir ve halka sunulmamaktadır; Ek-7 A içerik '
                   'bilgisi bu Güvenlik Bilgi Formu ile sağlanmaktadır (Ek-7 A son paragraf).' if tr else
                   'Product intended for industrial/institutional use and not made available to the general '
                   'public; Annex VII A information is provided by this SDS.')
    return out
