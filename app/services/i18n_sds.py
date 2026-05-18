"""
SDS Çok Dilli Kütüphanesi (i18n)
==================================
KKDİK Ek-2 / EU CLP SDS — Bölüm başlıkları ve standart ifadeler

Desteklenen diller:
  TR — Türkçe (KKDİK, ÇSGB)
  EN — İngilizce (EU CLP default)
  DE — Almanca (REACH-Deu)
  PL — Lehçe
  RO — Rumence
  BG — Bulgarca
  HU — Macarca

Mimari:
  - Her dil için T() (translate) fonksiyonu
  - Bölüm başlıkları standart — çeviri zorunlu
  - Serbest metin (cümleler) dil kütüphanesinde
  - SDS standartları: EU 2020/878, KKDİK 2013/30466

Ekleme: Yeni dil eklemek için LANG_DATA'ya ekle.
"""

from typing import Dict, Optional


# ─── DİL VERİTABANI ──────────────────────────────────────────────────────────

LANG_DATA: Dict[str, Dict] = {

    # ── TÜRKÇE ───────────────────────────────────────────────────────────────
    'TR': {
        'name': 'Türkçe',
        'code': 'TR',
        'regulation': 'KKDİK (30105/2017)',
        'date_format': '%d.%m.%Y',
        'decimal_sep': ',',

        # Bölüm başlıkları
        'sections': {
            1:  'BÖLÜM 1: Madde/Karışım ve Şirket/İş Sahibi Hakkında Bilgiler',
            2:  'BÖLÜM 2: Zararlılık Tanımlaması',
            3:  'BÖLÜM 3: Bileşim/İçindekiler Hakkında Bilgi',
            4:  'BÖLÜM 4: İlk Yardım Önlemleri',
            5:  'BÖLÜM 5: Yangınla Mücadele Önlemleri',
            6:  'BÖLÜM 6: Kaza Sonucu Yayılmaya Karşı Önlemler',
            7:  'BÖLÜM 7: Elleçleme ve Depolama',
            8:  'BÖLÜM 8: Maruziyet Kontrolleri/Kişisel Korunma',
            9:  'BÖLÜM 9: Fiziksel ve Kimyasal Özellikler',
            10: 'BÖLÜM 10: Kararlılık ve Tepkime',
            11: 'BÖLÜM 11: Toksikolojik Bilgi',
            12: 'BÖLÜM 12: Ekolojik Bilgi',
            13: 'BÖLÜM 13: Bertaraf Bilgileri',
            14: 'BÖLÜM 14: Taşımacılık Bilgileri',
            15: 'BÖLÜM 15: Mevzuat Bilgileri',
            16: 'BÖLÜM 16: Diğer Bilgiler',
        },

        # Alt başlıklar
        'sub': {
            '1.1': 'Ürün tanımlayıcısı',
            '1.2': 'Madde veya karışımın belirlenmiş kullanımları ve tavsiye edilmeyen kullanımları',
            '1.3': 'Güvenlik bilgi formu tedarikçisinin bilgileri',
            '1.4': 'Acil durum telefon numarası',
            '2.1': 'Madde veya karışımın sınıflandırılması',
            '2.2': 'Etiket unsurları',
            '2.3': 'Diğer tehlikeler',
            '3.1': 'Maddeler',
            '3.2': 'Karışımlar',
            '4.1': 'İlk yardım önlemlerinin tanımlanması',
            '4.2': 'En önemli akut ve gecikmiş semptomlar ile etkiler',
            '4.3': 'Tıbbi müdahale ve özel tedavi gerekliliğinin belirtilmesi',
            '5.1': 'Söndürme maddeleri',
            '5.2': 'Maddeden veya karışımdan kaynaklanan özel tehlikeler',
            '5.3': 'Yangın söndürme ekibine tavsiyeler',
            '6.1': 'Kişisel önlemler, koruyucu ekipman ve acil durum prosedürleri',
            '6.2': 'Çevresel önlemler',
            '6.3': 'Sınırlandırma ve temizleme için yöntemler ve materyaller',
            '6.4': 'Diğer bölümlere atıflar',
            '7.1': 'Güvenli elleçleme için önlemler',
            '7.2': 'Güvenli depolama koşulları (uyumsuz maddeler dahil)',
            '7.3': 'Belirli son kullanımlar',
            '8.1': 'Kontrol parametreleri',
            '8.2': 'Maruziyet kontrolleri',
            '9.1': 'Temel fiziksel ve kimyasal özellikler hakkında bilgiler',
            '9.2': 'Diğer bilgiler',
            '10.1': 'Tepkimelilik',
            '10.2': 'Kimyasal kararlılık',
            '10.3': 'Tehlikeli tepkimelerin olasılığı',
            '10.4': 'Kaçınılması gereken koşullar',
            '10.5': 'Bağdaşmayan maddeler',
            '10.6': 'Tehlikeli bozunma ürünleri',
            '11.1': 'Toksikolojik etkiler hakkında bilgi',
            '12.1': 'Toksisite',
            '12.2': 'Kalıcılık ve bozunabilirlik',
            '12.3': 'Biyobirikim potansiyeli',
            '12.4': 'Topraktaki hareketlilik',
            '12.5': 'PBT ve vPvB değerlendirmesinin sonuçları',
            '12.6': 'Endokrin bozucu özellikler',
            '12.7': 'Diğer olumsuz etkiler',
            '13.1': 'Atık arıtma yöntemleri',
            '14.1': 'UN numarası veya ID numarası',
            '14.2': 'UN uygun nakliye adı',
            '14.3': 'Taşımacılık tehlike sınıfı/sınıfları',
            '14.4': 'Ambalaj grubu',
            '14.5': 'Çevre tehlikeleri',
            '14.6': 'Kullanıcı için özel önlemler',
            '14.7': 'MARPOL ve IBC Kodu uyarınca dökme taşımacılık',
            '15.1': 'Madde veya karışıma özgü güvenlik, sağlık ve çevre mevzuatı',
            '15.2': 'Kimyasal güvenlik değerlendirmesi',
            '16.1': 'Revizyonlar',
            '16.2': 'Kısaltmalar ve Kısaltmaların Anlamları',
            '16.3': 'Önemli kaynaklar',
        },

        # Etiket unsurları
        'label': {
            'signal_word':    'Uyarı Sözcüğü',
            'danger':         'Tehlike',
            'warning':        'Uyarı',   # KKDİK Ek-3 / SEA Yönetmeliği doğru karşılık
            'none':           'Yok',
            'hazard_stmts':   'Tehlike İfadeleri',
            'precaut_stmts':  'Önlem İfadeleri',
            'pictograms':     'Zararlılık İşaretleri',
            'contains':       'İçerir:',
            'supp_labels':    'Ek Etiket Unsurları (EUH)',
        },

        # Genel terimler
        'terms': {
            'product_name':   'Ürün Adı',
            'product_code':   'Ürün Kodu',
            'manufacturer':   'Üretici / Tedarikçi',
            'address':        'Adres',
            'phone':          'Telefon',
            'email':          'E-posta',
            'emergency_tel':  'Acil Durum Telefonu',
            'poison_center':  'Ulusal Zehir Danışma Merkezi (UZEM): 114',
            'revision_date':  'Revizyon Tarihi',
            'revision_no':    'Revizyon No',
            'sds_date':       'GBF Tarihi',
            'version':        'Sürüm',
            'page':           'Sayfa',
            'of':             '/',
            'continued':      'Devamı var',
            'cas_no':         'CAS No',
            'ec_no':          'EC No',
            'concentration':  'Konsantrasyon',
            'classification': 'Sınıflandırma',
            'disposal': 'Bertaraf', 'information': 'Bilgi', 'not_classified': 'Sınıflandırılmamış',
            'disposal':    'Bertaraf',
            'information': 'Bilgi',
    'not_applicable': 'Uygulanamaz',
            'not_available':  'Bilgi yok',
            'see_section':    'Bkz. Bölüm',
            'trade_secret':   'Ticari sır',
            'mixture':        'Karışım',
            'substance':      'Madde',
            'all_sections':   'Tüm bölümlere bakın',
            'pbt_not':        'Bu karışım PBT veya vPvB kriterlerini karşılamamaktadır.',
            'no_info':        'Bu konuda bilgi bulunmamaktadır.',
            'ghs_label':      'GHS/CLP Etiket Bilgileri',
            'ppe_gloves':     'El Koruması',
            'ppe_eyes':       'Göz Koruması',
            'ppe_resp':       'Solunum Koruması',
            'ppe_body':       'Vücut Koruması',
            'disposal_reg':   'T.C. Tehlikeli Atıkların Kontrolü Yönetmeliği\'ne uygun bertaraf edin.',
        },

        # Bölüm 9 — fiziksel özellik etiketleri
        'phys_props': {
            'appearance':       'Görünüm',
            'color':            'Renk',
            'odor':             'Koku',
            'odor_threshold':   'Koku eşiği',
            'ph':               'pH',
            'melting_point':    'Erime/donma noktası',
            'boiling_point':    'İlk kaynama noktası',
            'flash_point':      'Parlama noktası',
            'evap_rate':        'Buharlaşma hızı',
            'flammability':     'Yanıcılık',
            'ufl':              'Patlama sınırları (üst)',
            'lfl':              'Patlama sınırları (alt)',
            'vapor_pressure':   'Buhar basıncı',
            'vapor_density':    'Buhar yoğunluğu',
            'density':          'Yoğunluk',
            'solubility':       'Çözünürlük',
            'partition_coeff':  'n-oktanol/su bölüşüm katsayısı',
            'auto_ignition':    'Kendiliğinden tutuşma sıcaklığı',
            'decomp_temp':      'Bozunma sıcaklığı',
            'viscosity':        'Viskozite',
        },
    },

    # ── İNGİLİZCE ────────────────────────────────────────────────────────────
    'EN': {
        'name': 'English',
        'code': 'EN',
        'regulation': 'EU CLP (EC) 1272/2008 / REACH (EC) 1907/2006',
        'date_format': '%d/%m/%Y',
        'decimal_sep': '.',

        'sections': {
            1:  'SECTION 1: Identification of the substance/mixture and of the company/undertaking',
            2:  'SECTION 2: Hazards identification',
            3:  'SECTION 3: Composition/information on ingredients',
            4:  'SECTION 4: First-aid measures',
            5:  'SECTION 5: Firefighting measures',
            6:  'SECTION 6: Accidental release measures',
            7:  'SECTION 7: Handling and storage',
            8:  'SECTION 8: Exposure controls/personal protection',
            9:  'SECTION 9: Physical and chemical properties',
            10: 'SECTION 10: Stability and reactivity',
            11: 'SECTION 11: Toxicological information',
            12: 'SECTION 12: Ecological information',
            13: 'SECTION 13: Disposal considerations',
            14: 'SECTION 14: Transport information',
            15: 'SECTION 15: Regulatory information',
            16: 'SECTION 16: Other information',
        },

        'sub': {
            '1.1': 'Product identifier',
            '1.2': 'Relevant identified uses and uses advised against',
            '1.3': 'Details of the supplier of the safety data sheet',
            '1.4': 'Emergency telephone number',
            '2.1': 'Classification of the substance or mixture',
            '2.2': 'Label elements',
            '2.3': 'Other hazards',
            '3.2': 'Mixtures',
            '4.1': 'Description of first aid measures',
            '4.2': 'Most important symptoms and effects',
            '4.3': 'Indication of immediate medical attention required',
            '5.1': 'Extinguishing media',
            '5.2': 'Special hazards arising from the substance or mixture',
            '5.3': 'Advice for firefighters',
            '6.1': 'Personal precautions, protective equipment and emergency procedures',
            '6.2': 'Environmental precautions',
            '6.3': 'Methods and material for containment and cleaning up',
            '6.4': 'Reference to other sections',
            '7.1': 'Precautions for safe handling',
            '7.2': 'Conditions for safe storage',
            '7.3': 'Specific end use(s)',
            '8.1': 'Control parameters',
            '8.2': 'Exposure controls',
            '12.1': 'Toxicity',
            '12.2': 'Persistence and degradability',
            '12.3': 'Bioaccumulative potential',
            '12.4': 'Mobility in soil',
            '12.5': 'Results of PBT and vPvB assessment',
            '12.6': 'Endocrine disrupting properties',
            '14.1': 'UN number or ID number',
            '14.2': 'UN proper shipping name',
            '14.3': 'Transport hazard class(es)',
            '14.4': 'Packing group',
            '14.5': 'Environmental hazards',
        },

        'label': {
            'signal_word':   'Signal Word',
            'danger':        'Danger',
            'warning':       'Warning',
            'none':          'None',
            'hazard_stmts':  'Hazard Statements',
            'precaut_stmts': 'Precautionary Statements',
            'pictograms':    'Hazard Pictograms',
            'contains':      'Contains:',
            'supp_labels':   'Supplemental Label Elements (EUH)',
        },

        'terms': {
            'product_name':   'Product Name',
            'product_code':   'Product Code',
            'manufacturer':   'Manufacturer / Supplier',
            'address':        'Address',
            'phone':          'Phone',
            'email':          'Email',
            'emergency_tel':  'Emergency Telephone',
            'poison_center':  'Poison Center: see national list',
            'revision_date':  'Revision Date',
            'revision_no':    'Revision No.',
            'sds_date':       'SDS Date',
            'version':        'Version',
            'page':           'Page',
            'of':             'of',
            'continued':      'continued',
            'cas_no':         'CAS No.',
            'ec_no':          'EC No.',
            'concentration':  'Concentration',
            'classification': 'Classification',
            'disposal': 'Disposal', 'information': 'Information', 'not_classified': 'Not classified',
            'not_applicable': 'N/A',
            'not_available':  'No data available',
            'see_section':    'See Section',
            'trade_secret':   'Trade secret',
            'mixture':        'Mixture',
            'substance':      'Substance',
            'pbt_not':        'This mixture does not meet the criteria for PBT or vPvB.',
            'no_info':        'No data available.',
            'ghs_label':      'GHS/CLP Label Information',
            'ppe_gloves':     'Hand Protection',
            'ppe_eyes':       'Eye Protection',
            'ppe_resp':       'Respiratory Protection',
            'ppe_body':       'Body Protection',
            'disposal_reg':   'Dispose in accordance with local/national regulations.',
        },

        'phys_props': {
            'appearance':       'Appearance',
            'color':            'Color',
            'odor':             'Odor',
            'odor_threshold':   'Odor threshold',
            'ph':               'pH',
            'melting_point':    'Melting/freezing point',
            'boiling_point':    'Initial boiling point',
            'flash_point':      'Flash point',
            'evap_rate':        'Evaporation rate',
            'flammability':     'Flammability',
            'ufl':              'Upper explosive limit',
            'lfl':              'Lower explosive limit',
            'vapor_pressure':   'Vapour pressure',
            'vapor_density':    'Vapour density',
            'density':          'Density',
            'solubility':       'Solubility',
            'partition_coeff':  'Partition coefficient n-octanol/water',
            'auto_ignition':    'Auto-ignition temperature',
            'decomp_temp':      'Decomposition temperature',
            'viscosity':        'Viscosity',
        },
    },

    # ── ALMANCA ──────────────────────────────────────────────────────────────
    'DE': {
        'name': 'Deutsch',
        'code': 'DE',
        'regulation': 'EU CLP (EG) 1272/2008 / REACH (EG) 1907/2006',
        'date_format': '%d.%m.%Y',
        'decimal_sep': ',',

        'sections': {
            1:  'ABSCHNITT 1: Stoff-/Gemischbezeichnung und Firmen-/Unternehmensbezeichnung',
            2:  'ABSCHNITT 2: Mögliche Gefahren',
            3:  'ABSCHNITT 3: Zusammensetzung/Angaben zu Bestandteilen',
            4:  'ABSCHNITT 4: Erste-Hilfe-Maßnahmen',
            5:  'ABSCHNITT 5: Maßnahmen zur Brandbekämpfung',
            6:  'ABSCHNITT 6: Maßnahmen bei unbeabsichtigter Freisetzung',
            7:  'ABSCHNITT 7: Handhabung und Lagerung',
            8:  'ABSCHNITT 8: Expositionsgrenzwerte und persönliche Schutzausrüstung',
            9:  'ABSCHNITT 9: Physikalische und chemische Eigenschaften',
            10: 'ABSCHNITT 10: Stabilität und Reaktivität',
            11: 'ABSCHNITT 11: Toxikologische Angaben',
            12: 'ABSCHNITT 12: Umweltbezogene Angaben',
            13: 'ABSCHNITT 13: Hinweise zur Entsorgung',
            14: 'ABSCHNITT 14: Angaben zum Transport',
            15: 'ABSCHNITT 15: Rechtsvorschriften',
            16: 'ABSCHNITT 16: Sonstige Angaben',
        },

        'label': {
            'signal_word':   'Signalwort',
            'danger':        'Gefahr',
            'warning':       'Achtung',
            'none':          'Kein',
            'hazard_stmts':  'Gefahrenhinweise',
            'precaut_stmts': 'Sicherheitshinweise',
            'pictograms':    'Piktogramme',
            'contains':      'Enthält:',
            'supp_labels':   'Ergänzende Kennzeichnung (EUH)',
        },

        'terms': {
            'product_name':   'Produktname',
            'manufacturer':   'Hersteller / Lieferant',
            'address':        'Adresse',
            'phone':          'Telefon',
            'emergency_tel':  'Notrufnummer',
            'poison_center':  'Giftinformationszentrale (GIZ)',
            'revision_date':  'Revisionsdatum',
            'page':           'Seite',
            'of':             'von',
            'continued':      'Fortsetzung',
            'cas_no':         'CAS-Nr.',
            'ec_no':          'EG-Nr.',
            'concentration':  'Konzentration',
            'classification': 'Einstufung',
            'disposal': 'Entsorgung', 'information': 'Information', 'not_classified': 'Nicht eingestuft',
            'not_applicable': 'Nicht zutreffend',
            'not_available':  'Keine Daten verfügbar',
            'trade_secret':   'Betriebsgeheimnis',
            'mixture':        'Gemisch',
            'pbt_not':        'Das Gemisch erfüllt nicht die Kriterien für PBT oder vPvB.',
            'no_info':        'Keine Informationen verfügbar.',
            'ppe_gloves':     'Handschutz',
            'ppe_eyes':       'Augenschutz',
            'ppe_resp':       'Atemschutz',
            'ppe_body':       'Körperschutz',
            'disposal_reg':   'Gemäß lokalen/nationalen Vorschriften entsorgen.',
        },

        'sub': {
            '1.1': 'Produktidentifikator',
            '1.2': 'Relevante identifizierte Verwendungen des Stoffs oder Gemischs und Verwendungen, von denen abgeraten wird',
            '1.3': 'Einzelheiten zum Lieferanten, der das Sicherheitsdatenblatt bereitstellt',
            '1.4': 'Notrufnummer',
            '2.1': 'Einstufung des Stoffs oder Gemischs',
            '2.2': 'Kennzeichnungselemente',
            '2.3': 'Sonstige Gefahren',
            '3.1': 'Stoffe',
            '3.2': 'Gemische',
            '4.1': 'Beschreibung der Erste-Hilfe-Maßnahmen',
            '4.2': 'Wichtigste akute und verzögert auftretende Symptome und Wirkungen',
            '4.3': 'Hinweise auf ärztliche Soforthilfe oder Spezialbehandlung',
            '5.1': 'Löschmittel',
            '5.2': 'Besondere vom Stoff oder Gemisch ausgehende Gefahren',
            '5.3': 'Hinweise für die Brandbekämpfung',
            '6.1': 'Persönliche Vorsichtsmaßnahmen, Schutzausrüstungen und Notfallverfahren',
            '6.2': 'Umweltschutzmaßnahmen',
            '6.3': 'Methoden und Material für Rückhaltung und Reinigung',
            '6.4': 'Verweis auf andere Abschnitte',
            '7.1': 'Schutzmaßnahmen für eine sichere Handhabung',
            '7.2': 'Bedingungen zur sicheren Lagerung unter Berücksichtigung von Unverträglichkeiten',
            '7.3': 'Spezifische Endanwendungen',
            '8.1': 'Kontrollparameter',
            '8.2': 'Expositionsbegrenzung und persönliche Schutzausrüstungen',
            '9.1': 'Angaben zu den grundlegenden physikalischen und chemischen Eigenschaften',
            '9.2': 'Weitere Angaben',
            '10.1': 'Reaktivität',
            '10.2': 'Chemische Stabilität',
            '10.3': 'Möglichkeit gefährlicher Reaktionen',
            '10.4': 'Zu vermeidende Bedingungen',
            '10.5': 'Unverträgliche Materialien',
            '10.6': 'Gefährliche Zersetzungsprodukte',
            '11.1': 'Angaben zu den in der Verordnung (EG) Nr. 1272/2008 definierten Gefahrenklassen',
            '12.1': 'Toxizität',
            '12.2': 'Persistenz und Abbaubarkeit',
            '12.3': 'Bioakkumulationspotenzial',
            '12.4': 'Mobilität im Boden',
            '12.5': 'Ergebnisse der PBT- und vPvB-Beurteilung',
            '12.6': 'Endokrine Störwirkungen',
            '12.7': 'Andere schädliche Wirkungen',
            '13.1': 'Abfallbehandlungsverfahren',
            '14.1': 'UN-Nummer oder ID-Nummer',
            '14.2': 'Ordnungsgemäße UN-Versandbezeichnung',
            '14.3': 'Transportgefahrenklasse(n)',
            '14.4': 'Verpackungsgruppe',
            '14.5': 'Umweltgefahren',
            '14.6': 'Besondere Vorsichtsmaßnahmen für den Verwender',
            '14.7': 'Massengutbeförderung gemäß IMO-Instrumenten',
            '15.1': 'Vorschriften und Rechtsakte zu Sicherheit, Gesundheits- und Umweltschutz',
            '15.2': 'Beurteilung der chemischen Sicherheit',
            '16.1': 'Revisionsangaben',
            '16.2': 'Abkürzungen und Akronyme',
        },

        'phys_props': {
            'appearance': 'Erscheinungsform',
            'color': 'Farbe',
            'odor': 'Geruch',
            'ph': 'pH-Wert',
            'melting_point': 'Schmelz-/Gefrierpunkt',
            'boiling_point': 'Siedebeginn',
            'flash_point': 'Flammpunkt',
            'density': 'Dichte',
            'viscosity': 'Viskosität',
        },
    },

    # ── LEHÇE ─────────────────────────────────────────────────────────────────
    'PL': {
        'name': 'Polski',
        'code': 'PL',
        'regulation': 'CLP (WE) 1272/2008 / REACH (WE) 1907/2006',
        'date_format': '%d.%m.%Y',
        'decimal_sep': ',',

        'sections': {
            1:  'SEKCJA 1: Identyfikacja substancji/mieszaniny i identyfikacja przedsiębiorstwa',
            2:  'SEKCJA 2: Identyfikacja zagrożeń',
            3:  'SEKCJA 3: Skład/informacja o składnikach',
            4:  'SEKCJA 4: Środki pierwszej pomocy',
            5:  'SEKCJA 5: Postępowanie w przypadku pożaru',
            6:  'SEKCJA 6: Postępowanie w przypadku niezamierzonego uwolnienia do środowiska',
            7:  'SEKCJA 7: Postępowanie z substancją/mieszaniną i jej magazynowanie',
            8:  'SEKCJA 8: Kontrola narażenia/środki ochrony indywidualnej',
            9:  'SEKCJA 9: Właściwości fizyczne i chemiczne',
            10: 'SEKCJA 10: Stabilność i reaktywność',
            11: 'SEKCJA 11: Informacje toksykologiczne',
            12: 'SEKCJA 12: Informacje ekologiczne',
            13: 'SEKCJA 13: Postępowanie z odpadami',
            14: 'SEKCJA 14: Informacje dotyczące transportu',
            15: 'SEKCJA 15: Informacje dotyczące przepisów prawnych',
            16: 'SEKCJA 16: Inne informacje',
        },

        'label': {
            'signal_word':   'Hasło ostrzegawcze',
            'danger':        'Niebezpieczeństwo',
            'warning':       'Uwaga',
            'none':          'Brak',
            'hazard_stmts':  'Zwroty wskazujące rodzaj zagrożenia',
            'precaut_stmts': 'Zwroty wskazujące środki ostrożności',
            'pictograms':    'Piktogramy',
            'contains':      'Zawiera:',
        },

        'terms': {
            'product_name':   'Nazwa produktu',
            'manufacturer':   'Producent / Dostawca',
            'address':        'Adres',
            'phone':          'Telefon',
            'emergency_tel':  'Numer alarmowy',
            'poison_center':  'Centrum Informacji Toksykologicznej',
            'revision_date':  'Data aktualizacji',
            'page':           'Strona',
            'of':             'z',
            'continued':      'kontynuacja',
            'cas_no':         'Nr CAS',
            'concentration':  'Stężenie',
            'classification': 'Klasyfikacja',
            'disposal': 'Utylizacja', 'information': 'Informacja', 'not_classified': 'Niesklasyfikowany',
            'not_applicable': 'Nie dotyczy',
            'not_available':  'Brak danych',
            'trade_secret':   'Tajemnica handlowa',
            'mixture':        'Mieszanina',
            'pbt_not':        'Mieszanina nie spełnia kryteriów PBT ani vPvB.',
            'no_info':        'Brak dostępnych danych.',
            'ppe_gloves':     'Ochrona rąk',
            'ppe_eyes':       'Ochrona oczu',
            'ppe_resp':       'Ochrona układu oddechowego',
            'ppe_body':       'Ochrona ciała',
            'disposal_reg':   'Utylizować zgodnie z lokalnymi/krajowymi przepisami.',
        },

        'sub': {
            '1.1': 'Identyfikator produktu',
            '1.2': 'Istotne zidentyfikowane zastosowania substancji lub mieszaniny oraz zastosowania odradzane',
            '1.3': 'Dane dotyczące dostawcy karty charakterystyki',
            '1.4': 'Numer telefonu alarmowego',
            '2.1': 'Klasyfikacja substancji lub mieszaniny',
            '2.2': 'Elementy oznakowania',
            '2.3': 'Inne zagrożenia',
            '3.1': 'Substancje',
            '3.2': 'Mieszaniny',
            '4.1': 'Opis środków pierwszej pomocy',
            '4.2': 'Najważniejsze ostre i opóźnione objawy oraz skutki narażenia',
            '4.3': 'Wskazania dotyczące wszelkiej natychmiastowej pomocy lekarskiej',
            '5.1': 'Środki gaśnicze',
            '5.2': 'Szczególne zagrożenia związane z substancją lub mieszaniną',
            '5.3': 'Informacje dla straży pożarnej',
            '6.1': 'Indywidualne środki ostrożności, wyposażenie ochronne i procedury w sytuacjach awaryjnych',
            '6.2': 'Środki ostrożności w zakresie ochrony środowiska',
            '6.3': 'Metody i materiały zapobiegające rozprzestrzenianiu się skażenia i służące do usuwania skażenia',
            '6.4': 'Odniesienia do innych sekcji',
            '7.1': 'Środki ostrożności dotyczące bezpiecznego postępowania',
            '7.2': 'Warunki bezpiecznego magazynowania, łącznie z informacjami dotyczącymi wszelkich wzajemnych niezgodności',
            '7.3': 'Szczególne zastosowanie(-a) końcowe',
            '8.1': 'Parametry kontrolne',
            '8.2': 'Kontrola narażenia',
            '9.1': 'Informacje na temat podstawowych właściwości fizycznych i chemicznych',
            '9.2': 'Inne informacje',
            '10.1': 'Reaktywność',
            '10.2': 'Stabilność chemiczna',
            '10.3': 'Możliwość występowania niebezpiecznych reakcji',
            '10.4': 'Warunki, których należy unikać',
            '10.5': 'Materiały niezgodne',
            '10.6': 'Niebezpieczne produkty rozkładu',
            '11.1': 'Informacje o klasach zagrożenia zdefiniowanych w rozporządzeniu (WE) nr 1272/2008',
            '12.1': 'Toksyczność',
            '12.2': 'Trwałość i zdolność do rozkładu',
            '12.3': 'Zdolność do bioakumulacji',
            '12.4': 'Mobilność w glebie',
            '12.5': 'Wyniki oceny właściwości PBT i vPvB',
            '12.6': 'Właściwości endokrynnie zakłócające',
            '13.1': 'Metody unieszkodliwiania odpadów',
            '14.1': 'Numer UN lub numer identyfikacyjny',
            '14.2': 'Prawidłowa nazwa przewozowa UN',
            '14.3': 'Klasa(-y) zagrożenia w transporcie',
            '14.4': 'Grupa pakowania',
            '14.5': 'Zagrożenia dla środowiska',
            '15.1': 'Przepisy prawne dotyczące bezpieczeństwa, zdrowia i ochrony środowiska',
            '15.2': 'Ocena bezpieczeństwa chemicznego',
        },

        'phys_props': {
            'appearance': 'Wygląd',
            'color': 'Barwa',
            'odor': 'Zapach',
            'ph': 'pH',
            'boiling_point': 'Temperatura wrzenia',
            'flash_point': 'Temperatura zapłonu',
            'density': 'Gęstość',
            'viscosity': 'Lepkość',
        },
    },

    # ── RUMENCE ───────────────────────────────────────────────────────────────
    'RO': {
        'name': 'Română',
        'code': 'RO',
        'regulation': 'CLP (CE) 1272/2008 / REACH (CE) 1907/2006',
        'date_format': '%d.%m.%Y',
        'decimal_sep': ',',

        'sections': {
            1:  'SECȚIUNEA 1: Identificarea substanței/amestecului și a societății/întreprinderii',
            2:  'SECȚIUNEA 2: Identificarea pericolelor',
            3:  'SECȚIUNEA 3: Compoziție/informații privind componenții',
            4:  'SECȚIUNEA 4: Măsuri de prim ajutor',
            5:  'SECȚIUNEA 5: Măsuri de combatere a incendiilor',
            6:  'SECȚIUNEA 6: Măsuri de luat în caz de dispersie accidentală',
            7:  'SECȚIUNEA 7: Manipulare și depozitare',
            8:  'SECȚIUNEA 8: Controale ale expunerii/protecția personală',
            9:  'SECȚIUNEA 9: Proprietăți fizice și chimice',
            10: 'SECȚIUNEA 10: Stabilitate și reactivitate',
            11: 'SECȚIUNEA 11: Informații toxicologice',
            12: 'SECȚIUNEA 12: Informații ecologice',
            13: 'SECȚIUNEA 13: Considerații privind eliminarea',
            14: 'SECȚIUNEA 14: Informații referitoare la transport',
            15: 'SECȚIUNEA 15: Informații privind reglementările',
            16: 'SECȚIUNEA 16: Alte informații',
        },

        'label': {
            'signal_word':   'Cuvânt de avertizare',
            'danger':        'Pericol',
            'warning':       'Atenție',
            'none':          'Niciuna',
            'hazard_stmts':  'Fraze de pericol',
            'precaut_stmts': 'Fraze de precauție',
            'pictograms':    'Pictograme de pericol',
            'contains':      'Conține:',
        },

        'terms': {
            'product_name':   'Denumirea produsului',
            'manufacturer':   'Producător / Furnizor',
            'address':        'Adresă',
            'phone':          'Telefon',
            'emergency_tel':  'Telefon de urgență',
            'poison_center':  'Centrul de Toxicologie',
            'revision_date':  'Data revizuirii',
            'page':           'Pagina',
            'of':             'din',
            'cas_no':         'Nr. CAS',
            'concentration':  'Concentrație',
            'classification': 'Clasificare',
            'disposal': 'Eliminare', 'information': 'Informație', 'not_classified': 'Neclasificat',
            'not_applicable': 'Nu se aplică',
            'not_available':  'Date nedisponibile',
            'trade_secret':   'Secret comercial',
            'mixture':        'Amestec',
            'pbt_not':        'Amestecul nu îndeplinește criteriile PBT sau vPvB.',
            'no_info':        'Nu există date disponibile.',
            'disposal_reg':   'A se elimina conform reglementărilor locale/naționale.',
        },

        'sub': {
            '1.1': 'Identificatorul produsului',
            '1.2': 'Utilizări identificate relevante ale substanței sau amestecului și utilizări contraindicate',
            '1.3': 'Detalii privind furnizorul fișei cu date de securitate',
            '1.4': 'Număr de telefon pentru urgențe',
            '2.1': 'Clasificarea substanței sau a amestecului',
            '2.2': 'Elemente de etichetare',
            '2.3': 'Alte pericole',
            '3.1': 'Substanțe',
            '3.2': 'Amestecuri',
            '4.1': 'Descrierea măsurilor de prim ajutor',
            '4.2': 'Cele mai importante simptome și efecte, atât acute, cât și cu întârziere',
            '4.3': 'Indicarea oricărui tip de asistență medicală imediată',
            '5.1': 'Mijloace de stingere a incendiilor',
            '5.2': 'Pericole speciale generate de substanță sau de amestec',
            '5.3': 'Sfaturi pentru pompieri',
            '6.1': 'Precauții individuale, echipament de protecție și proceduri de urgență',
            '6.2': 'Precauții pentru mediul înconjurător',
            '6.3': 'Metode și materiale pentru izolarea și curățarea deversărilor',
            '6.4': 'Trimiteri la alte secțiuni',
            '7.1': 'Precauții pentru manipularea în condiții de securitate',
            '7.2': 'Condiții de depozitare în condiții de securitate',
            '7.3': 'Utilizări finale specifice',
            '8.1': 'Parametri de control',
            '8.2': 'Controale ale expunerii',
            '9.1': 'Informații privind proprietățile fizice și chimice de bază',
            '10.1': 'Reactivitate',
            '10.2': 'Stabilitate chimică',
            '11.1': 'Informații privind clasele de pericol definite în Regulamentul (CE) nr. 1272/2008',
            '12.1': 'Toxicitate',
            '12.2': 'Persistență și degradabilitate',
            '12.3': 'Potențial de bioacumulare',
            '12.4': 'Mobilitate în sol',
            '12.5': 'Rezultatele evaluării PBT și vPvB',
            '13.1': 'Metode de tratare a deșeurilor',
            '14.1': 'Număr ONU sau număr de identificare',
            '14.2': 'Denumirea corectă a ONU pentru expediție',
            '14.3': 'Clasa(-ele) de pericol pentru transport',
            '14.4': 'Grupul de ambalare',
            '14.5': 'Pericole pentru mediu',
            '15.1': 'Reglementări privind securitatea, sănătatea și mediul specific pentru substanță sau amestec',
            '15.2': 'Evaluarea securității chimice',
        },

        'phys_props': {
            'appearance': 'Aspect',
            'color': 'Culoare',
            'odor': 'Miros',
            'ph': 'pH',
            'boiling_point': 'Punct de fierbere',
            'flash_point': 'Punct de inflamabilitate',
            'density': 'Densitate',
            'viscosity': 'Vâscozitate',
        },
    },

    # ── BULGARCA ──────────────────────────────────────────────────────────────
    'BG': {
        'name': 'Български',
        'code': 'BG',
        'regulation': 'CLP (ЕО) 1272/2008 / REACH (ЕО) 1907/2006',
        'date_format': '%d.%m.%Y',
        'decimal_sep': ',',

        'sections': {
            1:  'РАЗДЕЛ 1: Идентификация на веществото/сместа и на дружеството/предприятието',
            2:  'РАЗДЕЛ 2: Идентифициране на опасностите',
            3:  'РАЗДЕЛ 3: Състав/информация за съставките',
            4:  'РАЗДЕЛ 4: Мерки за първа помощ',
            5:  'РАЗДЕЛ 5: Противопожарни мерки',
            6:  'РАЗДЕЛ 6: Мерки при аварийно изпускане',
            7:  'РАЗДЕЛ 7: Работа и съхранение',
            8:  'РАЗДЕЛ 8: Контрол на експозицията/лични предпазни средства',
            9:  'РАЗДЕЛ 9: Физични и химични свойства',
            10: 'РАЗДЕЛ 10: Стабилност и реактивност',
            11: 'РАЗДЕЛ 11: Токсикологична информация',
            12: 'РАЗДЕЛ 12: Екологична информация',
            13: 'РАЗДЕЛ 13: Обезвреждане на отпадъците',
            14: 'РАЗДЕЛ 14: Информация за транспорта',
            15: 'РАЗДЕЛ 15: Регулаторна информация',
            16: 'РАЗДЕЛ 16: Друга информация',
        },

        'label': {
            'signal_word':   'Сигнална дума',
            'danger':        'Опасност',
            'warning':       'Внимание',
            'none':          'Няма',
            'hazard_stmts':  'Предупреждения за опасност',
            'precaut_stmts': 'Препоръки за безопасност',
            'pictograms':    'Пиктограми',
            'contains':      'Съдържа:',
        },

        'terms': {
            'product_name':   'Наименование на продукта',
            'manufacturer':   'Производител / Доставчик',
            'address':        'Адрес',
            'phone':          'Телефон',
            'emergency_tel':  'Спешен телефон',
            'revision_date':  'Дата на ревизия',
            'page':           'Страница',
            'of':             'от',
            'cas_no':         'CAS №',
            'concentration':  'Концентрация',
            'classification': 'Класификация',
            'disposal': 'Изхвърляне', 'information': 'Информация', 'not_classified': 'Некласифицирано',
            'not_applicable': 'Неприложимо',
            'not_available':  'Няма данни',
            'trade_secret':   'Търговска тайна',
            'mixture':        'Смес',
            'pbt_not':        'Сместа не отговаря на критериите за PBT или vPvB.',
            'no_info':        'Няма налична информация.',
            'disposal_reg':   'Изхвърляйте съгласно местните/националните разпоредби.',
        },

        'sub': {
            '1.1': 'Идентификатор на продукта',
            '1.2': 'Съответни идентифицирани употреби на веществото или сместа',
            '1.3': 'Данни за доставчика на информационния лист за безопасност',
            '1.4': 'Спешен телефонен номер',
            '2.1': 'Класификация на веществото или сместа',
            '2.2': 'Елементи на етикета',
            '2.3': 'Други опасности',
            '3.1': 'Вещества',
            '3.2': 'Смеси',
            '4.1': 'Описание на мерките за оказване на първа помощ',
            '5.1': 'Пожарогасителни средства',
            '6.1': 'Лични предпазни мерки, защитно оборудване и аварийни процедури',
            '7.1': 'Предпазни мерки за безопасно боравене',
            '8.1': 'Контролни параметри',
            '8.2': 'Контрол на експозицията',
            '9.1': 'Информация за основните физични и химични свойства',
            '11.1': 'Информация за класовете на опасност, определени в Регламент (ЕО) № 1272/2008',
            '12.1': 'Токсичност',
            '12.2': 'Устойчивост и разградимост',
            '13.1': 'Методи за третиране на отпадъци',
            '14.1': 'Номер на ООН или идентификационен номер',
            '15.1': 'Разпоредби относно безопасността, здравето и околната среда, специфични за веществото или сместа',
            '15.2': 'Оценка на химичната безопасност',
        },

        'phys_props': {
            'appearance': 'Вид',
            'color': 'Цвят',
            'odor': 'Мирис',
            'ph': 'pH',
            'boiling_point': 'Точка на кипене',
            'flash_point': 'Температура на запалване',
            'density': 'Плътност',
            'viscosity': 'Вискозитет',
        },
    },

    # ── MACARCA ───────────────────────────────────────────────────────────────
    'HU': {
        'name': 'Magyar',
        'code': 'HU',
        'regulation': 'CLP (EK) 1272/2008 / REACH (EK) 1907/2006',
        'date_format': '%Y.%m.%d.',
        'decimal_sep': ',',

        'sections': {
            1:  '1. SZAKASZ: Az anyag/keverék és a vállalat/vállalkozás azonosítása',
            2:  '2. SZAKASZ: A veszély azonosítása',
            3:  '3. SZAKASZ: Összetétel vagy az összetevőkre vonatkozó adatok',
            4:  '4. SZAKASZ: Elsősegély-nyújtási intézkedések',
            5:  '5. SZAKASZ: Tűzvédelmi intézkedések',
            6:  '6. SZAKASZ: Intézkedések véletlenszerű expozíció esetén',
            7:  '7. SZAKASZ: Kezelés és tárolás',
            8:  '8. SZAKASZ: Az expozíció ellenőrzése/egyéni védelem',
            9:  '9. SZAKASZ: Fizikai és kémiai tulajdonságok',
            10: '10. SZAKASZ: Stabilitás és reakciókészség',
            11: '11. SZAKASZ: Toxikológiai adatok',
            12: '12. SZAKASZ: Ökológiai adatok',
            13: '13. SZAKASZ: Ártalmatlanítási szempontok',
            14: '14. SZAKASZ: Szállítási adatok',
            15: '15. SZAKASZ: Szabályozói információk',
            16: '16. SZAKASZ: Egyéb adatok',
        },

        'label': {
            'signal_word':   'Figyelmeztetés',
            'danger':        'Veszély',
            'warning':       'Figyelem',
            'none':          'Nincs',
            'hazard_stmts':  'Figyelmeztető mondatok',
            'precaut_stmts': 'Óvintézkedésre vonatkozó mondatok',
            'pictograms':    'Piktogramok',
            'contains':      'Tartalmaz:',
        },

        'terms': {
            'product_name':   'Termék neve',
            'manufacturer':   'Gyártó / Szállító',
            'address':        'Cím',
            'phone':          'Telefon',
            'emergency_tel':  'Segélyhívó szám',
            'revision_date':  'Felülvizsgálat dátuma',
            'page':           'Oldal',
            'of':             '/',
            'cas_no':         'CAS-szám',
            'concentration':  'Koncentráció',
            'classification': 'Besorolás',
            'disposal': 'Ártalmatlanítás', 'information': 'Információ', 'not_classified': 'Nem besorolt',
            'not_applicable': 'Nem alkalmazható',
            'not_available':  'Nincs adat',
            'trade_secret':   'Üzleti titok',
            'mixture':        'Keverék',
            'pbt_not':        'A keverék nem felel meg a PBT vagy vPvB kritériumoknak.',
            'no_info':        'Nem áll rendelkezésre adat.',
            'disposal_reg':   'A helyi/nemzeti előírásoknak megfelelően ártalmatlanítsa.',
        },

        'sub': {
            '1.1': 'Termékazonosító',
            '1.2': 'Az anyag vagy keverék megfelelő azonosított felhasználásai, illetve ellenjavallt felhasználásai',
            '1.3': 'A biztonsági adatlap szállítójának adatai',
            '1.4': 'Sürgősségi telefonszám',
            '2.1': 'Az anyag vagy keverék besorolása',
            '2.2': 'Címkézési elemek',
            '2.3': 'Egyéb veszélyek',
            '3.1': 'Anyagok',
            '3.2': 'Keverékek',
            '4.1': 'Az elsősegély-nyújtási intézkedések ismertetése',
            '4.2': 'A legfontosabb akut és késleltetett tünetek, illetve hatások',
            '4.3': 'Azonnali orvosi ellátás szükségességére vonatkozó jelzés',
            '5.1': 'Oltóanyagok',
            '5.2': 'Az anyagból vagy keverékből eredő különleges veszélyek',
            '5.3': 'Tűzoltóknak szóló javaslatok',
            '6.1': 'Személyi óvintézkedések, egyéni védőeszközök és vészhelyzeti eljárások',
            '6.2': 'Környezetvédelmi óvintézkedések',
            '6.3': 'A területi elhatárolás és a szennyezésmentesítés módszerei és anyagai',
            '6.4': 'Hivatkozás más szakaszokra',
            '7.1': 'A biztonságos kezelésre vonatkozó óvintézkedések',
            '7.2': 'A biztonságos tárolás feltételei',
            '7.3': 'Meghatározott végfelhasználás(-ok)',
            '8.1': 'Ellenőrzési paraméterek',
            '8.2': 'Az expozíció ellenőrzése',
            '9.1': 'Az alapvető fizikai és kémiai tulajdonságokra vonatkozó információk',
            '10.1': 'Reakciókészség',
            '10.2': 'Kémiai stabilitás',
            '11.1': 'Az 1272/2008/EK rendeletben meghatározott veszélyességi osztályokra vonatkozó információk',
            '12.1': 'Toxicitás',
            '12.2': 'Perzisztencia és lebonthatóság',
            '12.3': 'Bioakkumulációs potenciál',
            '12.4': 'Mobilitás a talajban',
            '12.5': 'A PBT- és vPvB-értékelés eredményei',
            '13.1': 'A hulladékkezelési módszerek ismertetése',
            '14.1': 'UN-szám vagy azonosítószám',
            '14.2': 'Az ENSZ szerinti szállítási megnevezés',
            '14.3': 'Szállítási veszélyességi osztály(ok)',
            '14.4': 'Csomagolási csoport',
            '14.5': 'Környezeti veszélyek',
            '15.1': 'Az anyagra vagy keverékre vonatkozó biztonsági, egészségügyi és környezetvédelmi előírások',
            '15.2': 'Kémiai biztonsági értékelés',
        },

        'phys_props': {
            'appearance': 'Megjelenés',
            'color': 'Szín',
            'odor': 'Szag',
            'ph': 'pH',
            'boiling_point': 'Forráspontja',
            'flash_point': 'Lobbanáspont',
            'density': 'Sűrűség',
            'viscosity': 'Viszkozitás',
        },
    },
    # ── ÇEKÇE ─────────────────────────────────────────────────────────────────
    'CZ': {
        'name': 'Čeština', 'code': 'CZ',
        'regulation': 'CLP (ES) 1272/2008 / REACH (ES) 1907/2006',
        'date_format': '%d.%m.%Y', 'decimal_sep': ',',
        'sections': {
            1:'ODDÍL 1: Identifikace látky/směsi a společnosti/podniku',
            2:'ODDÍL 2: Identifikace nebezpečnosti',
            3:'ODDÍL 3: Složení/informace o složkách',
            4:'ODDÍL 4: Pokyny pro první pomoc',
            5:'ODDÍL 5: Opatření pro hašení požáru',
            6:'ODDÍL 6: Opatření v případě náhodného úniku',
            7:'ODDÍL 7: Zacházení a skladování',
            8:'ODDÍL 8: Omezování expozice/osobní ochranné prostředky',
            9:'ODDÍL 9: Fyzikální a chemické vlastnosti',
            10:'ODDÍL 10: Stabilita a reaktivita',
            11:'ODDÍL 11: Toxikologické informace',
            12:'ODDÍL 12: Ekologické informace',
            13:'ODDÍL 13: Pokyny pro odstraňování',
            14:'ODDÍL 14: Informace pro přepravu',
            15:'ODDÍL 15: Informace o předpisech',
            16:'ODDÍL 16: Další informace',
        },
        'label': {
            'signal_word':'Signální slovo','danger':'Nebezpečí','warning':'Varování',
            'none':'Žádné','hazard_stmts':'Standardní věty o nebezpečnosti',
            'precaut_stmts':'Pokyny pro bezpečné zacházení','pictograms':'Výstražné symboly nebezpečnosti',
            'contains':'Obsahuje:',
        },
        'terms': {
            'product_name':'Název výrobku','manufacturer':'Výrobce / Dodavatel',
            'address':'Adresa','phone':'Telefon','emergency_tel':'Tísňová linka',
            'revision_date':'Datum revize','page':'Strana','of':'z',
            'cas_no':'Č. CAS','concentration':'Koncentrace','classification':'Klasifikace',
            'not_classified':'Neklasifikováno','not_applicable':'Nelze použít',
            'not_available':'Nejsou k dispozici žádné údaje','trade_secret':'Obchodní tajemství',
            'mixture':'Směs','pbt_not':'Směs nesplňuje kritéria pro PBT ani vPvB.',
            'no_info':'Nejsou k dispozici žádné informace.',
            'disposal_reg':'Zlikvidujte v souladu s místními/vnitrostátními předpisy.',
            'ppe_gloves':'Ochrana rukou','ppe_eyes':'Ochrana očí',
            'ppe_resp':'Ochrana dýchadel','ppe_body':'Ochrana těla',
        },
        'sub': {
            '1.1': 'Identifikátor výrobku',
            '1.2': 'Příslušná určená použití látky nebo směsi a nedoporučená použití',
            '1.3': 'Podrobné údaje o dodavateli bezpečnostního listu',
            '1.4': 'Telefonní číslo pro naléhavé situace',
            '2.1': 'Klasifikace látky nebo směsi',
            '2.2': 'Prvky označení',
            '2.3': 'Jiná nebezpečí',
            '3.1': 'Látky',
            '3.2': 'Směsi',
            '4.1': 'Popis opatření první pomoci',
            '4.2': 'Nejdůležitější akutní a opožděné symptomy a účinky',
            '4.3': 'Pokyn týkající se okamžité lékařské pomoci',
            '5.1': 'Hasiva',
            '5.2': 'Zvláštní nebezpečí vyplývající z látky nebo směsi',
            '5.3': 'Pokyny pro hasiče',
            '6.1': 'Osobní bezpečnostní opatření, ochranné prostředky a nouzové postupy',
            '6.2': 'Opatření na ochranu životního prostředí',
            '6.3': 'Metody a materiály pro omezení úniku a pro čistění',
            '6.4': 'Odkaz na jiné oddíly',
            '7.1': 'Opatření pro bezpečné zacházení',
            '7.2': 'Podmínky pro bezpečné skladování látek a směsí',
            '7.3': 'Specifická konečná použití',
            '8.1': 'Kontrolní parametry',
            '8.2': 'Omezování expozice',
            '9.1': 'Informace o základních fyzikálních a chemických vlastnostech',
            '10.1': 'Reaktivita',
            '10.2': 'Chemická stabilita',
            '11.1': 'Informace o třídách nebezpečnosti vymezených v nařízení (ES) č. 1272/2008',
            '12.1': 'Toxicita',
            '12.2': 'Perzistence a rozložitelnost',
            '12.3': 'Potenciál bioakumulace',
            '12.4': 'Mobilita v půdě',
            '12.5': 'Výsledky posouzení PBT a vPvB',
            '13.1': 'Metody nakládání s odpady',
            '14.1': 'Číslo OSN nebo identifikační číslo',
            '14.2': 'Náležitý název OSN pro zásilku',
            '14.3': 'Třída nebezpečnosti pro přepravu',
            '14.4': 'Obalová skupina',
            '14.5': 'Nebezpečí pro životní prostředí',
            '15.1': 'Nařízení/právní předpisy specifické pro látku nebo směs v oblasti bezpečnosti, zdraví a životního prostředí',
            '15.2': 'Posouzení chemické bezpečnosti',
        },
    },

    # ── SLOVAKÇA ──────────────────────────────────────────────────────────────
    'SK': {
        'name': 'Slovenčina', 'code': 'SK',
        'regulation': 'CLP (ES) 1272/2008 / REACH (ES) 1907/2006',
        'date_format': '%d.%m.%Y', 'decimal_sep': ',',
        'sections': {
            1:'ODDIEL 1: Identifikácia látky/zmesi a spoločnosti/podniku',
            2:'ODDIEL 2: Identifikácia nebezpečnosti',
            3:'ODDIEL 3: Zloženie/informácie o zložkách',
            4:'ODDIEL 4: Opatrenia prvej pomoci',
            5:'ODDIEL 5: Protipožiarne opatrenia',
            6:'ODDIEL 6: Opatrenia pri náhodnom uvoľnení',
            7:'ODDIEL 7: Zaobchádzanie a skladovanie',
            8:'ODDIEL 8: Kontroly expozície/osobná ochrana',
            9:'ODDIEL 9: Fyzikálne a chemické vlastnosti',
            10:'ODDIEL 10: Stabilita a reaktivita',
            11:'ODDIEL 11: Toxikologické informácie',
            12:'ODDIEL 12: Ekologické informácie',
            13:'ODDIEL 13: Informácie o likvidácii',
            14:'ODDIEL 14: Informácie o doprave',
            15:'ODDIEL 15: Regulačné informácie',
            16:'ODDIEL 16: Iné informácie',
        },
        'label': {
            'signal_word':'Signálne slovo','danger':'Nebezpečenstvo','warning':'Pozor',
            'none':'Žiadne','hazard_stmts':'Štandardné vety o nebezpečnosti',
            'precaut_stmts':'Bezpečnostné upozornenia','pictograms':'Výstražné piktogramy',
            'contains':'Obsahuje:',
        },
        'terms': {
            'product_name':'Názov výrobku','manufacturer':'Výrobca / Dodávateľ',
            'address':'Adresa','phone':'Telefón','emergency_tel':'Tiesňová linka',
            'revision_date':'Dátum revízie','page':'Strana','of':'z',
            'cas_no':'Č. CAS','concentration':'Koncentrácia','classification':'Klasifikácia',
            'not_classified':'Neklasifikované','not_applicable':'Nevzťahuje sa',
            'not_available':'Údaje nie sú k dispozícii','trade_secret':'Obchodné tajomstvo',
            'mixture':'Zmes','pbt_not':'Zmes nespĺňa kritériá PBT ani vPvB.',
            'no_info':'Nie sú dostupné žiadne informácie.',
            'disposal_reg':'Likvidujte v súlade s miestnymi/vnútroštátnymi predpismi.',
            'ppe_gloves':'Ochrana rúk','ppe_eyes':'Ochrana očí',
            'ppe_resp':'Ochrana dýchacích ciest','ppe_body':'Ochrana tela',
        },
        'sub': {
            '1.1': 'Identifikátor produktu',
            '1.2': 'Relevantné identifikované použitia látky alebo zmesi a použitia, ktoré sa neodporúčajú',
            '1.3': 'Údaje o dodávateľovi karty bezpečnostných údajov',
            '1.4': 'Núdzové telefónne číslo',
            '2.1': 'Klasifikácia látky alebo zmesi',
            '2.2': 'Prvky označovania',
            '2.3': 'Iné nebezpečnosti',
            '3.1': 'Látky',
            '3.2': 'Zmesi',
            '4.1': 'Opis opatrení prvej pomoci',
            '5.1': 'Hasiace prostriedky',
            '6.1': 'Osobné preventívne opatrenia, ochranné vybavenie a núdzové postupy',
            '7.1': 'Opatrenia na zaistenie bezpečného zaobchádzania',
            '7.2': 'Podmienky na bezpečné skladovanie',
            '8.1': 'Kontrolné parametre',
            '8.2': 'Kontrola expozície',
            '9.1': 'Informácie o základných fyzikálnych a chemických vlastnostiach',
            '11.1': 'Informácie o triedach nebezpečnosti vymedzených v nariadení (ES) č. 1272/2008',
            '12.1': 'Toxicita',
            '12.2': 'Perzistencia a degradovateľnosť',
            '13.1': 'Metódy spracovania odpadu',
            '14.1': 'Číslo OSN alebo identifikačné číslo',
            '15.1': 'Predpisy/právne predpisy špecifické pre látku alebo zmes',
            '15.2': 'Posúdenie chemickej bezpečnosti',
        },
    },

    # ── HIRVATÇA ──────────────────────────────────────────────────────────────
    'HR': {
        'name': 'Hrvatski', 'code': 'HR',
        'regulation': 'CLP (EZ) 1272/2008 / REACH (EZ) 1907/2006',
        'date_format': '%d.%m.%Y', 'decimal_sep': ',',
        'sections': {
            1:'ODJELJAK 1: Identifikacija tvari/smjese i društva/poduzetnika',
            2:'ODJELJAK 2: Identifikacija opasnosti',
            3:'ODJELJAK 3: Sastav/podaci o sastojcima',
            4:'ODJELJAK 4: Mjere prve pomoći',
            5:'ODJELJAK 5: Mjere gašenja požara',
            6:'ODJELJAK 6: Mjere kod slučajnog ispuštanja',
            7:'ODJELJAK 7: Rukovanje i skladištenje',
            8:'ODJELJAK 8: Nadzor izloženosti/osobna zaštita',
            9:'ODJELJAK 9: Fizikalna i kemijska svojstva',
            10:'ODJELJAK 10: Stabilnost i reaktivnost',
            11:'ODJELJAK 11: Toksikološki podaci',
            12:'ODJELJAK 12: Ekološki podaci',
            13:'ODJELJAK 13: Napomene o odlaganju',
            14:'ODJELJAK 14: Podaci o prijevozu',
            15:'ODJELJAK 15: Regulatorni podaci',
            16:'ODJELJAK 16: Ostali podaci',
        },
        'label': {
            'signal_word':'Signalna riječ','danger':'Opasnost','warning':'Upozorenje',
            'none':'Nema','hazard_stmts':'Oznake opasnosti','precaut_stmts':'Obavijesti o mjerama opreza',
            'pictograms':'Piktogrami opasnosti','contains':'Sadrži:',
        },
        'terms': {
            'product_name':'Naziv proizvoda','manufacturer':'Proizvođač / Dobavljač',
            'address':'Adresa','phone':'Telefon','emergency_tel':'Hitna linija',
            'revision_date':'Datum revizije','page':'Stranica','of':'od',
            'cas_no':'CAS br.','concentration':'Koncentracija','classification':'Razvrstavanje',
            'not_classified':'Nije razvrstano','not_applicable':'Nije primjenjivo',
            'not_available':'Nema podataka','trade_secret':'Poslovna tajna',
            'mixture':'Smjesa','pbt_not':'Smjesa ne ispunjava kriterije za PBT ni vPvB.',
            'no_info':'Nema dostupnih podataka.',
            'disposal_reg':'Zbrinite sukladno lokalnim/nacionalnim propisima.',
            'ppe_gloves':'Zaštita ruku','ppe_eyes':'Zaštita očiju',
            'ppe_resp':'Zaštita dišnih putova','ppe_body':'Zaštita tijela',
        },
        'sub': {
            '1.1': 'Identifikator proizvoda',
            '1.2': 'Relevantna identificirana uporaba tvari ili smjese i uporabe koje se ne preporučaju',
            '1.3': 'Podaci o dobavljaču sigurnosno-tehničkog lista',
            '1.4': 'Broj telefona za hitne slučajeve',
            '2.1': 'Razvrstavanje tvari ili smjese',
            '2.2': 'Elementi označivanja',
            '2.3': 'Ostale opasnosti',
            '3.1': 'Tvari',
            '3.2': 'Smjese',
            '4.1': 'Opis mjera prve pomoći',
            '5.1': 'Sredstva za gašenje požara',
            '6.1': 'Osobne mjere opreza, zaštitna oprema i postupci u slučaju opasnosti',
            '7.1': 'Mjere opreza za sigurno rukovanje',
            '7.2': 'Uvjeti za sigurno skladištenje',
            '8.1': 'Kontrolni parametri',
            '8.2': 'Kontrola izloženosti',
            '9.1': 'Podaci o osnovnim fizikalnim i kemijskim svojstvima',
            '11.1': 'Podaci o razredima opasnosti definiranim Uredbom (EZ) br. 1272/2008',
            '12.1': 'Toksičnost',
            '12.2': 'Postojanost i razgradivost',
            '13.1': 'Metode obrade otpada',
            '14.1': 'UN broj ili identifikacijski broj',
            '15.1': 'Propisi o sigurnosti, zdravlju i zaštiti okoliša specifični za tvar ili smjesu',
            '15.2': 'Procjena kemijske sigurnosti',
        },
    },

    # ── LITVANCA ──────────────────────────────────────────────────────────────
    'LT': {
        'name': 'Lietuvių', 'code': 'LT',
        'regulation': 'CLP (EB) 1272/2008 / REACH (EB) 1907/2006',
        'date_format': '%Y-%m-%d', 'decimal_sep': ',',
        'sections': {
            1:'1 SKIRSNIS: Cheminės medžiagos/mišinio ir bendrovės/įmonės identifikavimas',
            2:'2 SKIRSNIS: Pavojingumo identifikavimas',
            3:'3 SKIRSNIS: Sudėtis/informacija apie sudedamąsias dalis',
            4:'4 SKIRSNIS: Pirmosios pagalbos priemonių aprašymas',
            5:'5 SKIRSNIS: Priešgaisrinės apsaugos priemonės',
            6:'6 SKIRSNIS: Avarijų likvidavimo priemonės',
            7:'7 SKIRSNIS: Naudojimas ir laikymas',
            8:'8 SKIRSNIS: Poveikio kontrolė/asmeninė apsauga',
            9:'9 SKIRSNIS: Fizinės ir cheminės savybės',
            10:'10 SKIRSNIS: Stabilumas ir reaktingumas',
            11:'11 SKIRSNIS: Toksikologinė informacija',
            12:'12 SKIRSNIS: Ekologinė informacija',
            13:'13 SKIRSNIS: Šalinimo informacija',
            14:'14 SKIRSNIS: Transportavimo informacija',
            15:'15 SKIRSNIS: Informacija apie teisės aktus',
            16:'16 SKIRSNIS: Kita informacija',
        },
        'label': {
            'signal_word':'Signaliniai žodžiai','danger':'Pavojinga','warning':'Atsargiai',
            'none':'Nėra','hazard_stmts':'Pavojingumo frazės','precaut_stmts':'Atsargumo frazės',
            'pictograms':'Pavojingumo piktogramos','contains':'Sudėtyje yra:',
        },
        'terms': {
            'product_name':'Produkto pavadinimas','manufacturer':'Gamintojas / Tiekėjas',
            'address':'Adresas','phone':'Telefonas','emergency_tel':'Pagalbos telefonas',
            'revision_date':'Peržiūros data','page':'Puslapis','of':'iš',
            'cas_no':'CAS Nr.','concentration':'Koncentracija','classification':'Klasifikavimas',
            'not_classified':'Neklasifikuojama','not_applicable':'Netaikoma',
            'not_available':'Duomenų nėra','trade_secret':'Komercinė paslaptis',
            'mixture':'Mišinys','pbt_not':'Mišinys neatitinka PBT arba vPvB kriterijų.',
            'no_info':'Duomenų nėra.','disposal_reg':'Utilizuokite pagal vietines/nacionalines taisykles.',
            'ppe_gloves':'Rankų apsauga','ppe_eyes':'Akių apsauga',
            'ppe_resp':'Kvėpavimo takų apsauga','ppe_body':'Kūno apsauga',
        },
        'sub': {
            '1.1': 'Produkto identifikatorius',
            '1.2': 'Atitinkamas nustatytas medžiagos arba mišinio naudojimas ir nerekomenduojamas naudojimas',
            '1.3': 'Saugos duomenų lapą pateikiančio tiekėjo duomenys',
            '1.4': 'Avariniu atveju skambinti',
            '2.1': 'Medžiagos ar mišinio klasifikavimas',
            '2.2': 'Ženklinimo elementai',
            '2.3': 'Kiti pavojai',
            '3.1': 'Medžiagos',
            '3.2': 'Mišiniai',
            '4.1': 'Pirmosios pagalbos priemonių aprašymas',
            '5.1': 'Gesinimo priemonės',
            '6.1': 'Asmeninės atsargumo priemonės, apsauginė įranga ir avarinio reagavimo procedūros',
            '7.1': 'Saugaus tvarkymo atsargumo priemonės',
            '8.1': 'Kontrolės parametrai',
            '8.2': 'Poveikio kontrolė',
            '9.1': 'Informacija apie pagrindines fizines ir chemines savybes',
            '11.1': 'Informacija apie pavojingumo klases, apibrėžtas Reglamente (EB) Nr. 1272/2008',
            '12.1': 'Toksiškumas',
            '12.2': 'Patvarumas ir skaidumas',
            '13.1': 'Atliekų tvarkymo metodai',
            '14.1': 'JT numeris arba identifikacinis numeris',
            '15.1': 'Su medžiaga ar mišiniu susijęs saugos, sveikatos ir aplinkos apsaugos reglamentavimas',
            '15.2': 'Cheminės saugos vertinimas',
        },
    },

    # ── ABD (OSHA HazCom 2012) ─────────────────────────────────────────────
    'US_EN': {
        'name': 'English (US/OSHA)', 'code': 'US_EN',
        'regulation': 'OSHA HazCom 2012 (29 CFR 1910.1200) — GHS aligned',
        'date_format': '%m/%d/%Y', 'decimal_sep': '.',
        'sections': {
            1:'SECTION 1: Identification',
            2:'SECTION 2: Hazard(s) Identification',
            3:'SECTION 3: Composition/Information on Ingredients',
            4:'SECTION 4: First-Aid Measures',
            5:'SECTION 5: Fire-Fighting Measures',
            6:'SECTION 6: Accidental Release Measures',
            7:'SECTION 7: Handling and Storage',
            8:'SECTION 8: Exposure Controls/Personal Protection',
            9:'SECTION 9: Physical and Chemical Properties',
            10:'SECTION 10: Stability and Reactivity',
            11:'SECTION 11: Toxicological Information',
            12:'SECTION 12: Ecological Information',
            13:'SECTION 13: Disposal Considerations',
            14:'SECTION 14: Transport Information',
            15:'SECTION 15: Regulatory Information',
            16:'SECTION 16: Other Information',
        },
        'label': {
            'signal_word':'Signal Word','danger':'DANGER','warning':'WARNING',
            'none':'None','hazard_stmts':'Hazard Statements','precaut_stmts':'Precautionary Statements',
            'pictograms':'Hazard Pictogram(s)','contains':'Contains:',
            'supp_labels':'Supplemental Information',
        },
        'terms': {
            'product_name':'Product Name','product_code':'Product Number',
            'manufacturer':'Manufacturer/Supplier','address':'Address','phone':'Phone',
            'email':'Email','emergency_tel':'Emergency Phone',
            'poison_center':'CHEMTREC: 1-800-424-9300 (US) | 1-703-527-3887 (International)',
            'revision_date':'Revision Date','revision_no':'Version','sds_date':'Issue Date',
            'version':'Version','page':'Page','of':'of','continued':'continued',
            'cas_no':'CAS #','ec_no':'EC #','concentration':'%','classification':'Classification',
            'not_classified':'Not classified','not_applicable':'N/A',
            'not_available':'No data available','see_section':'See Section',
            'trade_secret':'Trade Secret (see 29 CFR 1910.1200(i))',
            'mixture':'Mixture','substance':'Substance',
            'pbt_not':'This mixture does not meet PBT or vPvB criteria.',
            'no_info':'No data available.',
            'ghs_label':'GHS Label Elements',
            'ppe_gloves':'Hand Protection','ppe_eyes':'Eye Protection',
            'ppe_resp':'Respiratory Protection','ppe_body':'Body Protection',
            'disposal_reg':'Dispose of contents/container in accordance with local, state, and federal regulations.',
            'regulation': 'OSHA 29 CFR 1910.1200 | CERCLA | RCRA | TSCA',
        },
        'sub': {
            '1.1':'Product Identifier','1.2':'Recommended Use and Restrictions on Use',
            '1.3':'Supplier Details','1.4':'Emergency Phone Number',
            '2.1':'Classification of the Substance or Mixture',
            '2.2':'GHS Label Elements','2.3':'Other Hazards',
            '3.2':'Mixtures','4.1':'First Aid Measures',
            '8.1':'Exposure Limits / OSHA PELs / ACGIH TLVs',
            '8.2':'Engineering Controls / PPE',
        },
        'phys_props': {
            'appearance':'Appearance','color':'Color','odor':'Odor',
            'odor_threshold':'Odor Threshold','ph':'pH',
            'melting_point':'Melting Point/Freezing Point',
            'boiling_point':'Initial Boiling Point/Range',
            'flash_point':'Flash Point','evap_rate':'Evaporation Rate',
            'flammability':'Flammability (solid, gas)',
            'ufl':'Upper/Lower Flammability or Explosive Limits (UFL)',
            'lfl':'Upper/Lower Flammability or Explosive Limits (LFL)',
            'vapor_pressure':'Vapor Pressure','vapor_density':'Vapor Density',
            'density':'Relative Density','solubility':'Solubility(ies)',
            'partition_coeff':'Partition Coefficient: n-octanol/water',
            'auto_ignition':'Auto-ignition Temperature',
            'decomp_temp':'Decomposition Temperature',
            'viscosity':'Viscosity',
        },
    },
}

SUPPORTED_LANGUAGES = list(LANG_DATA.keys())


# ─── ÇEVIRI FONKSİYONLARI ────────────────────────────────────────────────────

def T(lang: str, category: str, key: str, default: str = '') -> str:
    """
    Çeviri al.
    T('TR', 'terms', 'product_name') → 'Ürün Adı'
    T('DE', 'sections', 1) → 'ABSCHNITT 1: ...'
    """
    lang_data = LANG_DATA.get(lang.upper(), LANG_DATA['EN'])
    cat_data = lang_data.get(category, {})
    return cat_data.get(key, default or key)


def get_lang(lang: str) -> dict:
    """Dil verisini al, yoksa EN döndür"""
    return LANG_DATA.get(lang.upper(), LANG_DATA['EN'])


def section_title(lang: str, num: int) -> str:
    return T(lang, 'sections', num, f'SECTION {num}')


def sub_title(lang: str, key: str) -> str:
    """Alt başlık — eksikse EN'den fallback yap"""
    result = T(lang, 'sub', key, '')
    if not result:
        result = T('EN', 'sub', key, key)
    return result


# Teknik terimler — tüm dillerde aynı veya EN varsayılan
_COMMON_TERMS = {
    'product_code': 'Code / Kód / Kod',
    'version': 'Version',
    'sds_date': 'SDS Date',
    'regulation': 'Regulation',
    'see_section': 'See Section / Bkz. Bölüm',
    'continued': '...',
    'of': '/',
}
# Dil bazlı product_code çevirileri
_PRODUCT_CODE_TRANS = {
    'TR':'Ürün Kodu','EN':'Product Code','DE':'Produktcode','PL':'Kod produktu',
    'RO':'Cod produs','BG':'Код на продукта','HU':'Termékszám',
    'CZ':'Kód výrobku','SK':'Kód produktu','HR':'Šifra proizvoda',
    'LT':'Produkto kodas','US_EN':'Product Code / Part No.',
}
_VERSION_TRANS = {
    'TR':'Sürüm','EN':'Version','DE':'Version','PL':'Wersja',
    'RO':'Versiune','BG':'Версия','HU':'Verzió',
    'CZ':'Verze','SK':'Verzia','HR':'Verzija','LT':'Versija','US_EN':'Version',
}
_REGULATION_TRANS = {
    'TR':'Mevzuat','EN':'Regulation','DE':'Rechtsvorschrift','PL':'Rozporządzenie',
    'RO':'Regulament','BG':'Регламент','HU':'Rendelet',
    'CZ':'Nařízení','SK':'Nariadenie','HR':'Uredba','LT':'Reglamentas','US_EN':'Regulation',
}

def term(lang: str, key: str, default: str = '') -> str:
    """Terimi al — önce dil, sonra EN fallback, sonra özel sözlükler"""
    # Özel sözlükler
    if key == 'product_code':
        return _PRODUCT_CODE_TRANS.get(lang.upper(), 'Product Code')
    if key == 'version':
        return _VERSION_TRANS.get(lang.upper(), 'Version')
    if key == 'regulation':
        return _REGULATION_TRANS.get(lang.upper(), 'Regulation')
    # Normal lookup
    result = T(lang, 'terms', key, '')
    if not result:
        result = T('EN', 'terms', key, default or key)
    return result


def label_term(lang: str, key: str) -> str:
    return T(lang, 'label', key, key)


def phys_prop(lang: str, key: str) -> str:
    return T(lang, 'phys_props', key, key)


def signal_word(lang: str, danger_level: str) -> str:
    """'Danger'/'Warning'/'None' → dile çevir"""
    key = danger_level.lower()
    if key == 'danger':
        return label_term(lang, 'danger')
    elif key == 'warning':
        return label_term(lang, 'warning')
    return label_term(lang, 'none')


# ─── SABIT CÜMLELER (PDF bölümleri için) ─────────────────────────────────────

_SENTENCES: dict = {
    'usage_default': {
        'TR':'Sanayi ve mesleki kullanım.',
        'EN':'Industrial and professional use.',
        'DE':'Industrielle und berufliche Verwendung.',
        'PL':'Zastosowanie przemysłowe i zawodowe.',
        'RO':'Utilizare industrială și profesională.',
        'BG':'Промишлена и професионална употреба.',
        'HU':'Ipari és szakmai felhasználás.',
        'CZ':'Průmyslové a profesionální použití.',
        'SK':'Priemyselné a profesionálne použitie.',
        'HR':'Industrijska i profesionalna uporaba.',
        'LT':'Pramoninė ir profesionali naudojimas.',
        'US_EN':'Industrial and professional use.',
    },
    'symptoms_general': {
        'TR':'Başlıca semptomlar maruziyet tipine göre değişir.',
        'EN':'Main symptoms depend on route of exposure.',
        'DE':'Die Hauptsymptome hängen vom Expositionsweg ab.',
        'PL':'Główne objawy zależą od drogi narażenia.',
        'RO':'Principalele simptome depind de calea de expunere.',
        'BG':'Основните симптоми зависят от пътя на излагане.',
        'HU':'A legfontosabb tünetek az expozíció módjától függnek.',
        'CZ':'Hlavní příznaky závisí na cestě expozice.',
        'SK':'Hlavné príznaky závisia od cesty expozície.',
        'HR':'Glavni simptomi ovise o putu izloženosti.',
        'LT':'Pagrindiniai simptomai priklauso nuo poveikio kelio.',
        'US_EN':'Main symptoms depend on route of exposure.',
    },
    'firefighter_ppe': {
        'TR':'Yangın söndürme ekibi uygun KKE ve bağımsız solunum cihazı (SCBA) kullanmalıdır.',
        'EN':'Firefighters should wear appropriate PPE and self-contained breathing apparatus (SCBA).',
        'DE':'Feuerwehrleute sollten geeignete PSA und umluftunabhängige Atemschutzgeräte (SCBA) tragen.',
        'PL':'Strażacy powinni używać odpowiednich ŚOI i aparatów oddechowych (SCBA).',
        'RO':'Pompierii trebuie să poarte EIP adecvat și aparat de respirat autonom (SCBA).',
        'BG':'Пожарникарите трябва да носят подходящи ЛПС и автономни дихателни апарати (SCBA).',
        'HU':'A tűzoltók viseljék a megfelelő egyéni védőeszközöket és önálló légzőkészüléket (SCBA).',
        'CZ':'Hasiči musí nosit vhodné OOPP a autonomní dýchací přístroje (SCBA).',
        'SK':'Hasiči musia nosiť vhodné OOPP a autonómne dýchacie prístroje (SCBA).',
        'HR':'Vatrogasci moraju nositi odgovarajuću OZO i autonomne uređaje za disanje (SCBA).',
        'LT':'Ugniagesiai turi dėvėti tinkamas AAP ir autonominius kvėpavimo aparatus (SCBA).',
        'US_EN':'Firefighters should wear full protective gear and SCBA.',
    },
    'spill_instructions': {
        'TR':'Kuru absorban malzeme (vermikülit, kum) ile toplayın. Uygun atık kabına koyun.',
        'EN':'Collect with dry absorbent material (vermiculite, sand). Place in suitable waste container.',
        'DE':'Mit trockenem Absorptionsmittel (Vermiculit, Sand) aufnehmen. In geeignetem Abfallbehälter entsorgen.',
        'PL':'Zebrać za pomocą suchego materiału absorbującego (wermikulit, piasek). Umieścić w odpowiednim pojemniku na odpady.',
        'RO':'Colectați cu material absorbant uscat (vermiculit, nisip). Puneți în recipiente de deșeuri adecvate.',
        'BG':'Съберете с изсушаващ материал (вермикулит, пясък). Поставете в подходящ контейнер за отпадъци.',
        'HU':'Száraz abszorbens anyaggal (vermikulit, homok) gyűjtse össze. Helyezze megfelelő hulladéktárolóba.',
        'CZ':'Shromážděte suchým absorpčním materiálem (vermikulit, písek). Vložte do vhodné nádoby na odpad.',
        'SK':'Zhromaždiť suchým absorpčným materiálom (vermikulit, piesok). Vložiť do vhodnej nádoby na odpad.',
        'HR':'Sakupite suhim apsorpcijskim materijalom (vermikulit, pijesak). Stavite u odgovarajući spremnik za otpad.',
        'LT':'Surinkite sausu absorbciniu medžiaga (vermikulitu, smėliu). Sudėkite į tinkamą atliekų talpyklą.',
        'US_EN':'Collect with dry absorbent material (vermiculite, dry sand). Place in suitable waste container.',
    },
    'personal_precautions': {
        'TR':'Kişisel koruyucu ekipman (KKE) kullanın. Uygun solunum koruması sağlayın.',
        'EN':'Use appropriate personal protective equipment (PPE). Ensure adequate respiratory protection.',
        'DE':'Geeignete persönliche Schutzausrüstung (PSA) verwenden. Für ausreichenden Atemschutz sorgen.',
        'PL':'Używać odpowiednich środków ochrony indywidualnej (ŚOI). Zapewnić odpowiednią ochronę dróg oddechowych.',
        'RO':'Utilizați echipamentul individual de protecție (EIP) adecvat. Asigurați protecție respiratorie adecvată.',
        'BG':'Използвайте подходящи лични предпазни средства (ЛПС). Осигурете подходяща защита на дихателните пътища.',
        'HU':'Megfelelő egyéni védőeszközöket (PPE) használjon. Biztosítson megfelelő légzésvédelmet.',
        'CZ':'Používejte vhodné osobní ochranné prostředky (OOPP). Zajistěte odpovídající ochranu dýchacích cest.',
        'SK':'Používajte vhodné osobné ochranné pomôcky (OOP). Zabezpečte primeranú ochranu dýchacích ciest.',
        'HR':'Koristite odgovarajuću osobnu zaštitnu opremu (OZO). Osigurajte odgovarajuću zaštitu dišnih putova.',
        'LT':'Naudokite tinkamas asmenines apsaugos priemones (AAP). Užtikrinkite tinkamą kvėpavimo apsaugą.',
        'US_EN':'Use appropriate PPE. Ensure adequate ventilation and respiratory protection.',
    },
    'oel_reference': {
        'TR':'Mesleki maruziyet sınır değerleri için ulusal mevzuata başvurun.',
        'EN':'Refer to national legislation for occupational exposure limit values.',
        'DE':'Für Arbeitsplatz-Grenzwerte sind die nationalen Rechtsvorschriften zu beachten.',
        'PL':'W celu uzyskania informacji o wartościach NDS należy zapoznać się z przepisami krajowymi.',
        'RO':'Consultați legislația națională pentru valorile limită de expunere profesională.',
        'BG':'Вижте националното законодателство за граничните стойности на професионалното излагане.',
        'HU':'A foglalkozási expozíciós határértékeket illetően tanulmányozza a nemzeti jogszabályokat.',
        'CZ':'Pro mezní hodnoty expozice na pracovišti viz vnitrostátní právní předpisy.',
        'SK':'Pozrite si vnútroštátne právne predpisy pre hodnoty NDS.',
        'HR':'Za granične vrijednosti profesionalne izloženosti pogledajte nacionalno zakonodavstvo.',
        'LT':'Dėl profesinės ekspozicijos ribinių verčių žiūrėkite nacionalinius teisės aktus.',
        'US_EN':'Refer to OSHA PELs, ACGIH TLVs, and NIOSH RELs for occupational exposure limits.',
    },
    'stable_conditions': {
        'TR':'Normal koşullarda kararlıdır.',
        'EN':'Stable under normal conditions.',
        'DE':'Unter normalen Bedingungen stabil.',
        'PL':'Stabilny w normalnych warunkach.',
        'RO':'Stabil în condiții normale.',
        'BG':'Стабилен при нормални условия.',
        'HU':'Normál körülmények között stabil.',
        'CZ':'Stabilní za normálních podmínek.',
        'SK':'Stabilný za normálnych podmienok.',
        'HR':'Stabilan u normalnim uvjetima.',
        'LT':'Stabilus normaliomis sąlygomis.',
        'US_EN':'Stable under normal conditions of use.',
    },
    'avoid_conditions': {
        'TR':'Yüksek ısı, açık alev, oksitleyici maddeler.',
        'EN':'Heat, open flames, oxidising agents.',
        'DE':'Hitze, offene Flammen, Oxidationsmittel.',
        'PL':'Ciepło, otwarte płomienie, środki utleniające.',
        'RO':'Căldură, flăcări deschise, agenți oxidanți.',
        'BG':'Топлина, открит огън, окислители.',
        'HU':'Hő, nyílt láng, oxidálószerek.',
        'CZ':'Teplo, otevřený oheň, oxidační látky.',
        'SK':'Teplo, otvorený oheň, oxidačné látky.',
        'HR':'Toplina, otvoreni plamen, oksidacijska sredstva.',
        'LT':'Šiluma, atvira ugnis, oksiduojančios medžiagos.',
        'US_EN':'Heat, sparks, open flames, oxidizing agents.',
    },
    'incompatible': {
        'TR':'Güçlü oksitleyiciler, kuvvetli asitler ve bazlar.',
        'EN':'Strong oxidisers, strong acids and bases.',
        'DE':'Starke Oxidationsmittel, starke Säuren und Basen.',
        'PL':'Silne utleniacze, mocne kwasy i zasady.',
        'RO':'Agenți oxidanți puternici, acizi tari și baze tari.',
        'BG':'Силни окислители, силни киселини и основи.',
        'HU':'Erős oxidálószerek, erős savak és bázisok.',
        'CZ':'Silná oxidační činidla, silné kyseliny a zásady.',
        'SK':'Silné oxidačné látky, silné kyseliny a zásady.',
        'HR':'Jaki oksidansi, jake kiseline i baze.',
        'LT':'Stiprūs oksiduojantys agentai, stiprios rūgštys ir bazės.',
        'US_EN':'Strong oxidizers, strong acids, strong bases.',
    },
    'decomp_products': {
        'TR':'Karbondioksit (CO₂), karbon monoksit (CO).',
        'EN':'Carbon dioxide (CO2), carbon monoxide (CO).',
        'DE':'Kohlendioxid (CO2), Kohlenmonoxid (CO).',
        'PL':'Dwutlenek węgla (CO2), tlenek węgla (CO).',
        'RO':'Dioxid de carbon (CO2), monoxid de carbon (CO).',
        'BG':'Въглероден диоксид (CO2), въглероден оксид (CO).',
        'HU':'Szén-dioxid (CO2), szén-monoxid (CO).',
        'CZ':'Oxid uhličitý (CO2), oxid uhelnatý (CO).',
        'SK':'Oxid uhličitý (CO2), oxid uhoľnatý (CO).',
        'HR':'Ugljikov dioksid (CO2), ugljikov monoksid (CO).',
        'LT':'Anglies dioksidas (CO2), anglies monoksidas (CO).',
        'US_EN':'Carbon dioxide (CO2), carbon monoxide (CO).',
    },
    'no_csa': {
        'TR':'Bu karışım için kimyasal güvenlik değerlendirmesi yapılmamıştır.',
        'EN':'No chemical safety assessment has been carried out for this mixture.',
        'DE':'Für dieses Gemisch wurde keine Stoffsicherheitsbeurteilung durchgeführt.',
        'PL':'Nie przeprowadzono oceny bezpieczeństwa chemicznego dla tej mieszaniny.',
        'RO':'Nu a fost efectuată nicio evaluare a securității chimice pentru acest amestec.',
        'BG':'За тази смес не е извършена оценка на химическа безопасност.',
        'HU':'Ehhez a keverékhez nem végeztek kémiai biztonsági értékelést.',
        'CZ':'Pro tuto směs nebyla provedena žádná hodnocení chemické bezpečnosti.',
        'SK':'Pre túto zmes nebolo vykonané hodnotenie chemickej bezpečnosti.',
        'HR':'Za ovaj se nije provjera kemijske sigurnosti.',
        'LT':'Šiam mišiniui nebuvo atliktas cheminio saugos vertinimas.',
        'US_EN':'No chemical safety assessment has been performed for this mixture.',
    },
    'route_label': {
        'TR':'Maruziyet Yolu',
        'EN':'Route of Exposure',
        'DE':'Expositionsweg',
        'PL':'Droga narażenia',
        'RO':'Calea de expunere',
        'BG':'Път на излагане',
        'HU':'Expozíciós út',
        'CZ':'Cesta expozice',
        'SK':'Cesta expozície',
        'HR':'Put izloženosti',
        'LT':'Poveikio kelias',
        'US_EN':'Route of Exposure',
    },
    'hazard_codes_label': {
        'TR':'Tehlike Kodları',
        'EN':'Hazard Codes',
        'DE':'Gefahrencodes',
        'PL':'Kody zagrożeń',
        'RO':'Coduri de pericol',
        'BG':'Кодове за опасност',
        'HU':'Veszélyességi kódok',
        'CZ':'Kódy nebezpečnosti',
        'SK':'Kódy nebezpečnosti',
        'HR':'Kodovi opasnosti',
        'LT':'Pavojingumo kodai',
        'US_EN':'Hazard Codes',
    },
    'revision_history': {
        'TR':'Revizyon Geçmişi',
        'EN':'Revision History',
        'DE':'Revisionsgeschichte',
        'PL':'Historia rewizji',
        'RO':'Istoricul revizuirilor',
        'BG':'История на ревизиите',
        'HU':'Revíziós előzmények',
        'CZ':'Historie revizí',
        'SK':'História revízií',
        'HR':'Povijest revizija',
        'LT':'Peržiūrų istorija',
        'US_EN':'Revision History',
    },
    'precaut_full': {
        'TR':'Güvenlik Önlemleri (Tam Liste)',
        'EN':'Precautionary Statements (Full List)',
        'DE':'Sicherheitshinweise (Vollständige Liste)',
        'PL':'Zalecenia bezpieczeństwa (pełna lista)',
        'RO':'Fraze de precauție (lista completă)',
        'BG':'Препоръки за безопасност (пълен списък)',
        'HU':'Óvintézkedésre vonatkozó mondatok (teljes lista)',
        'CZ':'Pokyny pro bezpečné zacházení (úplný seznam)',
        'SK':'Bezpečnostné upozornenia (úplný zoznam)',
        'HR':'Obavijesti o mjerama opreza (potpuni popis)',
        'LT':'Atsargumo frazės (pilnas sąrašas)',
        'US_EN':'Precautionary Statements (Full List)',
    },
    'sds_compliance': {
        'TR':'Bu GBF KKDİK Ek-2 formatına uygundur.',
        'EN':'This SDS complies with EU CLP 2020/878.',
        'DE':'Dieses SDB entspricht EU CLP 2020/878.',
        'PL':'Niniejsza KCH jest zgodna z UE CLP 2020/878.',
        'RO':'Această FDS este conformă cu UE CLP 2020/878.',
        'BG':'Този ИЛБ отговаря на EU CLP 2020/878.',
        'HU':'Ez a BAL megfelel az EU CLP 2020/878 előírásainak.',
        'CZ':'Tento BL je v souladu s EU CLP 2020/878.',
        'SK':'Tento KBÚ je v súlade s EU CLP 2020/878.',
        'HR':'Ovaj STL je u skladu s EU CLP 2020/878.',
        'LT':'Šis SDL atitinka ES CLP 2020/878.',
        'US_EN':'This SDS complies with OSHA HazCom 2012 (29 CFR 1910.1200).',
    },
    
    'evaluate_label':{'TR':'Değerlendirmeli','EN':'Evaluate','DE':'Bewerten','BG':'Оценка','PL':'Ocena',
        'RO':'Evaluare','HU':'Értékelés','CZ':'Hodnotit','SK':'Hodnotiť','HR':'Procijeni','LT':'Įvertinti','US_EN':'Evaluate'},
    'optional_label':{'TR':'Opsiyonel','EN':'Optional','DE':'Optional','BG':'По избор','PL':'Opcjonalnie',
        'RO':'Opțional','HU':'Opcionális','CZ':'Volitelné','SK':'Voliteľné','HR':'Neobavezno','LT':'Neprivaloma','US_EN':'Optional'},
    'abbreviations_label':{'TR':'Kısaltmalar','EN':'Abbreviations','DE':'Abkürzungen','BG':'Съкращения','PL':'Skróty',
        'RO':'Abrevieri','HU':'Rövidítések','CZ':'Zkratky','SK':'Skratky','HR':'Kratice','LT':'Sutrumpinimai','US_EN':'Abbreviations'},
    'sds_legal_note_1':{'TR':'Bu Güvenlik Bilgi Formu KKDİK Ek-2 formatına uygun olarak hazırlanmıştır.',
        'EN':'This Safety Data Sheet has been prepared in accordance with EU CLP 2020/878.',
        'DE':'Dieses Sicherheitsdatenblatt wurde gemäß EU CLP 2020/878 erstellt.',
        'BG':'Този информационен лист за безопасност е изготвен в съответствие с EU CLP 2020/878.',
        'PL':'Niniejsza karta charakterystyki została sporządzona zgodnie z EU CLP 2020/878.',
        'RO':'Această fișă cu date de securitate a fost pregătită în conformitate cu EU CLP 2020/878.',
        'HU':'Ez a biztonsági adatlap az EU CLP 2020/878 szerint készült.',
        'CZ':'Tento bezpečnostní list byl sestaven v souladu s EU CLP 2020/878.',
        'SK':'Tento karta bezpečnostných údajov bola zostavená v súlade s EU CLP 2020/878.',
        'HR':'Ovaj sigurnosno-tehnički list pripremljen je u skladu s EU CLP 2020/878.',
        'LT':'Šis saugos duomenų lapas parengtas pagal EU CLP 2020/878.',
        'US_EN':'This Safety Data Sheet has been prepared in accordance with OSHA HazCom 2012 (29 CFR 1910.1200).'},
    'sds_legal_note_2':{'TR':'Verilen bilgiler mevcut bilgi düzeyini yansıtmaktadır.',
        'EN':'The information provided reflects our current state of knowledge.',
        'DE':'Die bereitgestellten Informationen spiegeln unseren aktuellen Kenntnisstand wider.',
        'BG':'Предоставената информация отразява нашето текущо ниво на знания.',
        'PL':'Podane informacje odzwierciedlają nasz aktualny stan wiedzy.',
        'RO':'Informațiile furnizate reflectă nivelul nostru actual de cunoaștere.',
        'HU':'A megadott információk jelenlegi ismereteink szintjét tükrözik.',
        'CZ':'Poskytnuté informace odrážejí náš aktuální stav znalostí.',
        'SK':'Poskytnuté informácie odrážajú náš aktuálny stav znalostí.',
        'HR':'Navedene informacije odražavaju naše trenutno stanje znanja.',
        'LT':'Pateikta informacija atspindi esamą mūsų žinių lygį.',
        'US_EN':'The information provided reflects our current state of knowledge.'},
    'sds_legal_note_3':{'TR':'Kullanıcı bu bilgileri kendi koşullarına uygunluğu açısından değerlendirmelidir.',
        'EN':'The user must evaluate the suitability of this information for their specific conditions.',
        'DE':'Der Verwender muss die Eignung dieser Informationen für seine spezifischen Bedingungen beurteilen.',
        'BG':'Потребителят трябва да оцени пригодността на тази информация за своите специфични условия.',
        'PL':'Użytkownik musi ocenić przydatność tych informacji dla swoich warunków.',
        'RO':'Utilizatorul trebuie să evalueze adecvarea acestor informații pentru condițiile sale specifice.',
        'HU':'A felhasználónak értékelnie kell az információk alkalmasságát saját körülményeihez.',
        'CZ':'Uživatel musí posoudit vhodnost těchto informací pro své specifické podmínky.',
        'SK':'Používateľ musí posúdiť vhodnosť týchto informácií pre svoje špecifické podmienky.',
        'HR':'Korisnik mora procijeniti prikladnost ovih informacija za svoje specifične uvjete.',
        'LT':'Naudotojas turi įvertinti šios informacijos tinkamumą savo specifinėms sąlygoms.',
        'US_EN':'The user must evaluate the suitability of this information for their specific conditions.'},
    'mandatory_label': {
        'TR':'Zorunlu','EN':'Mandatory','DE':'Pflicht','PL':'Obowiązkowe',
        'RO':'Obligatoriu','BG':'Задължително','HU':'Kötelező',
        'CZ':'Povinné','SK':'Povinné','HR':'Obavezno','LT':'Privaloma','US_EN':'Mandatory',
    },
    'ingredient_label': {
        'TR':'İçerik / Madde','EN':'Ingredient','DE':'Bestandteil','PL':'Składnik',
        'RO':'Ingredient','BG':'Съставка','HU':'Összetevő',
        'CZ':'Složka','SK':'Zložka','HR':'Sastojak','LT':'Sudedamoji dalis','US_EN':'Ingredient',
    },
    'storage_default': {
        'TR':'Orijinal ambalajında, serin ve kuru yerde saklayın.',
        'EN':'Store in original container in a cool, dry place.',
        'DE':'Im Originalbehälter an einem kühlen, trockenen Ort lagern.',
        'PL':'Przechowywać w oryginalnym opakowaniu w chłodnym, suchym miejscu.',
        'RO':'Depozitați în recipientul original într-un loc răcoros și uscat.',
        'BG':'Съхранявайте в оригиналния съд на хладно и сухо място.',
        'HU':'Eredeti csomagolásban, hűvös, száraz helyen tárolandó.',
        'CZ':'Uchovávejte v původním obalu na chladném a suchém místě.',
        'SK':'Uchovávajte v pôvodnom obale na chladnom a suchom mieste.',
        'HR':'Čuvajte u originalnoj ambalaži na hladnom i suhom mjestu.',
        'LT':'Laikykite originalioje talpykloje vėsioje, sausoje vietoje.',
        'US_EN':'Store in original container in a cool, dry, well-ventilated area.',
    },

    # ── BÖLÜM 13 — Bertaraf (KKDİK Ek-2 §13.1 zorunlu unsurlar) ────────────────
    'contaminated_packaging': {
        'TR': (
            'KONTAMİNE AMBALAJ: Ambalajları mümkün olduğunca tamamen boşaltın. '
            'Artık ürün içeren ambalajlar tehlikeli atık olarak değerlendirilmeli ve '
            'Atık Yönetimi Yönetmeliği (29314 sayılı RG) çerçevesinde lisanslı bertaraf '
            'kuruluşuna teslim edilmelidir. Temizlenmiş ve ürün kalıntısı içermediği '
            'doğrulanmış ambalajlar yerel geri dönüşüm programlarına dahil edilebilir.'
        ),
        'EN': (
            'CONTAMINATED PACKAGING: Empty containers as completely as possible. '
            'Containers with residual product must be treated as hazardous waste and '
            'disposed of via a licensed waste management company. '
            'Thoroughly cleaned containers may be sent for recycling where permitted by local regulations.'
        ),
        'DE': (
            'KONTAMINIERTE VERPACKUNGEN: Behälter so vollständig wie möglich entleeren. '
            'Behälter mit Produktrückständen als gefährlichen Abfall behandeln und einem '
            'zugelassenen Entsorgungsunternehmen übergeben. '
            'Gereinigte Behälter können dem lokalen Recyclingprogramm zugeführt werden.'
        ),
        'PL': (
            'ZANIECZYSZCZONE OPAKOWANIA: Opróżnić pojemniki jak najbardziej całkowicie. '
            'Pojemniki z resztkami produktu traktować jako odpad niebezpieczny i przekazać '
            'licencjonowanej firmie zajmującej się unieszkodliwianiem odpadów. '
            'Oczyszczone opakowania można przekazać do recyklingu zgodnie z lokalnymi przepisami.'
        ),
        'RO': (
            'AMBALAJE CONTAMINATE: Goliți recipientele cât mai complet posibil. '
            'Recipientele cu resturi de produs trebuie tratate ca deșeuri periculoase și '
            'predate unei companii autorizate de gestionare a deșeurilor. '
            'Recipientele bine curățate pot fi trimise la reciclare conform reglementărilor locale.'
        ),
        'BG': (
            'ЗАМЪРСЕНИ ОПАКОВКИ: Изпразнете контейнерите напълно. '
            'Контейнерите с остатъци от продукт трябва да се третират като опасни отпадъци. '
            'Предайте на лицензирана компания за управление на отпадъци.'
        ),
        'HU': (
            'SZENNYEZETT CSOMAGOLÁS: A tartályokat a lehető legjobban ürítse ki. '
            'A termékmaradványt tartalmazó csomagolást veszélyes hulladékként kell kezelni, '
            'és engedéllyel rendelkező hulladékkezelő vállalatnak kell átadni. '
            'Az alaposan megtisztított csomagolás helyi előírások szerint újrahasznosítható.'
        ),
        'CZ': (
            'KONTAMINOVANÉ OBALY: Nádoby co nejúplněji vyprázdněte. '
            'Nádoby se zbytky produktu musí být považovány za nebezpečný odpad '
            'a předány oprávněné společnosti pro nakládání s odpady. '
            'Důkladně vyčištěné obaly lze podle místních předpisů recyklovat.'
        ),
        'SK': (
            'KONTAMINOVANÉ OBALY: Nádoby čo najúplnejšie vyprázdnite. '
            'Nádoby so zvyškami produktu sa musia považovať za nebezpečný odpad '
            'a odovzdať oprávnenej spoločnosti na nakladanie s odpadmi. '
            'Dôkladne vyčistené obaly možno recyklovať podľa miestnych predpisov.'
        ),
        'HR': (
            'KONTAMINIRANI AMBALAŽNI MATERIJAL: Posude ispraznite što je moguće potpunije. '
            'Posude s ostacima proizvoda treba tretirati kao opasan otpad '
            'i predati ovlaštenoj tvrtki za upravljanje otpadom. '
            'Temeljito očišćeni kontejneri mogu se reciklirati u skladu s lokalnim propisima.'
        ),
        'LT': (
            'UŽTERŠTA PAKUOTĖ: Ištuštinkite konteinerius kiek įmanoma labiau. '
            'Konteineriai su produkto liekanomis turi būti traktuojami kaip pavojingos atliekos '
            'ir perduoti licencijuotai atliekų tvarkymo įmonei.'
        ),
        'US_EN': (
            'CONTAMINATED PACKAGING: Empty containers as completely as possible. '
            'Containers with residual product must be treated as hazardous waste under '
            'applicable federal, state, and local regulations. '
            'Contact a licensed waste management company for disposal.'
        ),
    },
    'drain_prohibition': {
        'TR': (
            'Ürünü kanalizasyona, zemin suyuna, yüzey suyuna veya toprağa boşaltmayın. '
            'Su ortamı için zararlıdır — sucul organizmalar üzerinde uzun süreli olumsuz etkiler '
            'oluşturabilir (KKDİK Ek-2 §13 / SEA Yönetmeliği).'
        ),
        'EN': (
            'Do not dispose of into drains, groundwater, surface water, or soil. '
            'Harmful to aquatic environment — may cause long-term adverse effects on aquatic organisms '
            '(EU CLP 2020/878 Annex II §13 / CLP Regulation).'
        ),
        'DE': (
            'Nicht in Kanalisation, Grundwasser, Oberflächenwasser oder Boden einleiten. '
            'Schädlich für die Wasserumwelt — kann langfristige schädliche Wirkungen auf Wasserorganismen haben.'
        ),
        'PL': (
            'Nie usuwać do kanalizacji, wód gruntowych, wód powierzchniowych ani gleby. '
            'Szkodliwy dla środowiska wodnego — może powodować długotrwałe niekorzystne skutki w środowisku wodnym.'
        ),
        'RO': (
            'Nu eliminați în canalizare, ape subterane, ape de suprafață sau sol. '
            'Nociv pentru mediul acvatic cu efecte de lungă durată asupra organismelor acvatice.'
        ),
        'BG': (
            'Да не се изхвърля в канализацията, подземните води, повърхностните води или почвата. '
            'Вредно за водната среда с дълготрайни последствия.'
        ),
        'HU': (
            'Ne engedje csatornába, talajvízbe, felszíni vizekbe vagy talajba. '
            'Káros a vízi környezetre — hosszan tartó káros hatásokat okozhat a vízi szervezetekre.'
        ),
        'CZ': (
            'Nevypouštět do kanalizace, podzemních vod, povrchových vod ani půdy. '
            'Škodlivé pro vodní prostředí s dlouhodobými účinky na vodní organismy.'
        ),
        'SK': (
            'Nevypúšťajte do kanalizácie, podzemných vôd, povrchových vôd ani pôdy. '
            'Škodlivé pre vodné prostredie s dlhodobými účinkami na vodné organizmy.'
        ),
        'HR': (
            'Ne odlagati u kanalizaciju, podzemne vode, površinske vode ni tlo. '
            'Štetno za vodeni okoliš s dugotrajnim učincima na vodene organizme.'
        ),
        'LT': (
            'Neišpilti į kanalizaciją, požeminius vandenis, paviršinius vandenis ar dirvą. '
            'Kenksminga vandens aplinkai su ilgalaikiu poveikiu vandens organizmams.'
        ),
        'US_EN': (
            'Do not discharge to drains, groundwater, waterways, or soil. '
            'Harmful to aquatic organisms with long-lasting effects.'
        ),
    },
    'disposal_method_general': {
        'TR': (
            'Lisanslı tehlikeli atık bertaraf tesisinde bertaraf edin. '
            'Tercih edilen yöntem: lisanslı tesiste kontrollü yakma (insinorasyon). '
            'Atık kodunu belirlemek için Atık Yönetimi Yönetmeliği Ek-4 listesine (AVY Atık Kataloğu) başvurun.'
        ),
        'EN': (
            'Dispose of at a licensed hazardous waste treatment facility. '
            'Preferred method: controlled incineration at a licensed facility. '
            'Refer to the European Waste Catalogue (EWC/LoW) for appropriate waste classification code.'
        ),
        'DE': (
            'In einer zugelassenen Sonderabfallbehandlungsanlage entsorgen. '
            'Bevorzugte Methode: kontrollierte Verbrennung in einer zugelassenen Anlage. '
            'Abfallcode gemäß Europäischem Abfallverzeichnis (AVV) bestimmen.'
        ),
        'PL': (
            'Unieszkodliwić w licencjonowanym zakładzie przetwarzania odpadów niebezpiecznych. '
            'Preferowana metoda: kontrolowane spalanie w licencjonowanym zakładzie. '
            'Kod odpadu zgodnie z Europejskim Wykazem Odpadów (EWC).'
        ),
        'RO': (
            'Eliminați la o instalație autorizată de tratare a deșeurilor periculoase. '
            'Metoda preferată: incinerare controlată la o instalație autorizată. '
            'Consultați Catalogul European al Deșeurilor (CED) pentru codul de deșeuri aplicabil.'
        ),
        'BG': (
            'Унищожете в лицензирано съоръжение за третиране на опасни отпадъци. '
            'Предпочитан метод: контролирано изгаряне в лицензирано съоръжение.'
        ),
        'HU': (
            'Engedéllyel rendelkező veszélyes hulladékkezelő létesítményben ártalmatlanítsa. '
            'Ajánlott módszer: ellenőrzött égetés engedélyezett létesítményben. '
            'Az alkalmazandó hulladékkódhoz lásd az Európai Hulladékkatalógust (EWC).'
        ),
        'CZ': (
            'Zlikvidujte v oprávněném zařízení pro zpracování nebezpečných odpadů. '
            'Upřednostňovaná metoda: řízené spalování v oprávněném zařízení. '
            'Kód odpadu určte podle Evropského katalogu odpadů (EWC).'
        ),
        'SK': (
            'Zlikvidujte v oprávnenom zariadení na spracovanie nebezpečných odpadov. '
            'Uprednostňovaná metóda: riadené spaľovanie v oprávnenom zariadení. '
            'Kód odpadu určte podľa Európskeho katalógu odpadov (EWC).'
        ),
        'HR': (
            'Zbrinite u ovlaštenoj instalaciji za obradu opasnog otpada. '
            'Preporučena metoda: kontrolirano spaljivanje u ovlaštenoj instalaciji. '
            'Kod otpada odredite prema Europskom katalogu otpada (EWC).'
        ),
        'LT': (
            'Utilizuokite licencijuotame pavojingų atliekų tvarkymo objekte. '
            'Pageidaujamas metodas: kontroliuojamas deginimas licencijuotame objekte.'
        ),
        'US_EN': (
            'Dispose of at a licensed hazardous waste facility. '
            'Preferred method: incineration at a permitted facility. '
            'Classify waste per applicable federal and state regulations (40 CFR 261).'
        ),
    },
}


def S(lang: str, key: str) -> str:
    """Sabit cümle çevir. S('BG', 'stable_conditions') → Bulgarca"""
    lang = lang.upper()
    d = _SENTENCES.get(key, {})
    return d.get(lang, d.get('EN', key))
