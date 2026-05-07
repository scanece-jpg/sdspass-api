"""
EUH İfadeleri Servisi
=====================
CLP Regulation Ek-2 — Avrupa'ya özgü tehlike ifadeleri

Otomatik Tespit Edilen EUH Kodları (16 kural):
  EUH014  → Water-reactive bileşen
  EUH019  → Organik peroksit / H2O2 (patlayıcı peroksit oluşturabilir)
  EUH029  → Karbür/fosfür (asitle gaz)
  EUH031  → Sülfit/siyanür/hipoklorit/H2SO4 (asitle Cl2/SO2 vb.)
  EUH032  → Fosfür/sülfür (asitle H2S/PH3)
  EUH066  → Kural 1: Solvent CAS listesi | Kural 2: Skin Irrit.2 < cut-off
  EUH201  → Kurşun bileşikleri
  EUH202  → Siyanoakrilat
  EUH203  → Cr(VI) bileşikleri
  EUH204  → İzosiyant (isim anahtar kelime)
  EUH205  → Epoksi bileşeni (isim anahtar kelime)
  EUH206  → Hipoklorit (diğer ürünlerle klor)
  EUH207  → Kadmiyum
  EUH208  → Skin Sens. + SCL/10 kuralı (Annex I 3.4.4.1)
  EUH211  → TiO2 sıvı form ≥%1 (opsiyonel, 2022 mahkeme kararı)
  EUH212  → TiO2 katı form ≥%1 (opsiyonel)

EUH208 SCL/10 Kuralı:
  106 maddede Annex VI SCL var → eşik = SCL/10
  MIT/CMIT: SCL=%0.0015 → eşik=%0.00015
  Nickel: SCL=%0.01 → eşik=%0.001
  SCL yok → generic eşik %1.0

Manuel Kontrol Gereken (10 kod):
  EUH001, 006, 018, 044, 059, 070, 071,
  209, 209A, 401
"""
from typing import List, Dict, Any


# ─── EUH019 — Patlayıcı peroksit oluşturabilir ──────────────────────────────
# Organik peroksitler + H2O2 (yüksek konsantrasyon) + eter/THF grubu
# Ürün içeriyorsa "patlayıcı peroksit oluşturabilir" uyarısı zorunludur.

EUH019_CAS = {
    '7722-84-1',   # hydrogen peroxide (hidrojen peroksit) — tüm konsantrasyonlar
    '94-36-0',     # benzoyl peroxide
    '110-05-4',    # di-tert-butyl peroxide
    '80-43-3',     # dicumyl peroxide
    '3006-82-4',   # tert-butyl peroxybenzoate
    '614-45-9',    # tert-butyl perbenzoate
    '7722-84-1',   # hydrogen peroxide (tekrar — aynı CAS farklı notasyon)
    '109-99-9',    # tetrahydrofuran (THF) — eter grubu, peroksit biriktirir
    '60-29-7',     # diethyl ether — eter grubu
    '557-17-5',    # methyl propyl ether
    '629-14-1',    # 1,2-diethoxyethane
    '111-90-0',    # 2-(2-ethoxyethoxy)ethanol (DCBE)
}

# ─── EUH031 / EUH032 — Asitle gaz çıkaran maddeler ─────────────────────────

EUH031_CAS = {
    # Sülfitler ve bisülfitler
    '7631-90-5',   # sodium bisulphite
    '7681-57-4',   # sodium metabisulphite
    '7757-83-7',   # sodium sulphite
    '10102-15-5',  # sodium thiosulphate
    '7772-98-7',   # sodium thiosulphate anhydrous
    # Siyanürler
    '143-33-9',    # sodium cyanide
    '151-50-8',    # potassium cyanide
    '592-01-8',    # calcium cyanide
    # Hipoklorit
    '7681-52-9',   # sodium hypochlorite
    '7778-54-3',   # calcium hypochlorite
    '10022-70-5',  # sodium hypochlorite pentahydrate
    # Nitrit
    '7632-00-0',   # sodium nitrite
    '7758-09-0',   # potassium nitrite
    # Florür
    '7681-49-4',   # sodium fluoride
    '7789-75-5',   # calcium fluoride
    '16984-48-8',  # fluoride ion
    # Kromat
    '10588-01-9',  # sodium dichromate
    '7789-00-6',   # potassium chromate
    '7778-50-9',   # potassium dichromate
    # Diğer
    '7775-09-9',   # sodium chlorate
    '7758-19-2',   # sodium chlorite
    # Güçlü asitler — diğer maddelerle temas halinde toksik gaz açığa çıkarabilir
    # (sülfürik asit: metalllerle SO2/H2S; karbonatlara CO2; sülfit içerenlere SO2)
    '7664-93-9',   # sulfuric acid (sülfürik asit) — SEA Ek-6 / ECHA SDS uygulaması
    '7647-01-0',   # hydrochloric acid (hidroklorik asit) — metal reaksiyonu → Cl2/H2
    '7697-37-2',   # nitric acid (nitrik asit) — metal reaksiyonu → NOx gazları
}

EUH032_CAS = {
    # Fosfürler — çok toksik PH3 gazı
    '20816-12-0',  # osmium tetroxide
    '1314-80-3',   # phosphorus pentasulphide
    '12037-82-0',  # phosphorus sesquisulphide
    '7723-14-0',   # white phosphorus
    # Sülfürler
    '1313-82-2',   # sodium sulphide
    '1312-73-8',   # potassium sulphide
    '20667-12-3',  # silver sulphide
    # Metal fosfürler
    '12504-13-1',  # calcium phosphide
    '1314-56-3',   # phosphorus pentoxide
    '20859-73-8',  # aluminium phosphide
}

# ─── EUH066 — Cilt kuruluğu yapan çözücüler ─────────────────────────────────

EUH066_CAS = {
    '64-17-5',     # ethanol
    '67-63-0',     # isopropanol (IPA)
    '67-56-1',     # methanol
    '71-36-3',     # n-butanol
    '78-92-2',     # sec-butanol
    '75-65-0',     # tert-butanol
    '111-76-2',    # 2-butoxyethanol
    '110-43-0',    # methyl amyl ketone
    '108-94-1',    # cyclohexanone
    '110-82-7',    # cyclohexane
    '142-82-5',    # heptane
    '110-54-3',    # hexane
    '64-18-6',     # formic acid (dilute)
    '107-98-2',    # PGME (1-methoxy-2-propanol)
    '34590-94-8',  # DPGME
}

# ─── EUH201 — Kurşun ─────────────────────────────────────────────────────────

EUH201_CAS = {
    '7439-92-1',   # lead
    '1314-87-0',   # lead sulphide
    '1344-37-2',   # lead sulphochromate yellow
    '7758-95-4',   # lead chloride
    '10099-74-8',  # lead nitrate
    '7446-14-2',   # lead sulphate
    '1317-36-8',   # lead oxide
}

# ─── EUH202 — Siyanakrilat ───────────────────────────────────────────────────

EUH202_CAS = {
    '7085-85-0',   # ethyl cyanoacrylate
    '137-05-3',    # methyl cyanoacrylate
    '1309-14-4',   # n-butyl cyanoacrylate
    '6606-65-1',   # isobutyl cyanoacrylate
}

# ─── EUH203 — Krom(VI) ───────────────────────────────────────────────────────

EUH203_CAS = {
    '10588-01-9',  # sodium dichromate
    '7789-00-6',   # potassium chromate
    '7778-50-9',   # potassium dichromate
    '13530-65-9',  # zinc chromate
    '7738-94-5',   # chromic acid
    '7440-47-3',   # chromium(VI) trioxide
    '1333-82-0',   # chromium trioxide
}

# ─── EUH206 — Hipoklorit (klor gazı riski) ───────────────────────────────────

EUH206_CAS = {
    '7681-52-9',   # sodium hypochlorite
    '7778-54-3',   # calcium hypochlorite
    '10022-70-5',  # sodium hypochlorite pentahydrate
    '10025-87-3',  # phosphorus oxychloride
}

# ─── EUH207 — Kadmiyum ───────────────────────────────────────────────────────

EUH207_CAS = {
    '7440-43-9',   # cadmium
    '1306-23-6',   # cadmium sulphide
    '10108-64-2',  # cadmium chloride
    '10124-36-4',  # cadmium sulphate
}

# ─── EUH014 — Su ile tepkime (hazard class bazlı) ────────────────────────────

EUH014_CLASSES = {'Water-react. 1', 'Water-react. 2', 'Water-react. 3'}

# ─── EUH029 — Su ile toksik gaz ──────────────────────────────────────────────

EUH029_CAS = {
    '75-20-7',     # calcium carbide
    '1305-99-3',   # calcium phosphide
    '20859-73-8',  # aluminium phosphide
    '12037-82-0',  # phosphorus sesquisulphide
}

# ─── EUH204 — İzosiyanat (isim arama) ────────────────────────────────────────

EUH204_KEYWORDS = {
    'isocyanate', 'diisocyanate', 'triisocyanate',
    'mdi', 'tdi', 'hdi', 'ipdi', 'xdi', 'ndi',
    'methylene diphenyl', 'toluene diisocyanate',
    'hexamethylene diisocyanate'
}

# ─── EUH205 — Epoksi ─────────────────────────────────────────────────────────

EUH205_KEYWORDS = {
    'epoxy', 'epoxide', 'bisphenol', 'dgeba',
    'diglycidyl ether', 'glycidyl', 'oxirane'
}

# ─── EUH208 — SCL/10 Kuralı (CLP Annex I 3.4.4.1) ──────────────────────────
# Skin Sens. SCL'si olan maddeler için EUH208 eşiği = SCL / 10
# Annex VI ATP23'ten türetilmiş
SKIN_SENS_SCL_EUH208_THRESHOLD = {
    # NOT: Glutaraldehit (111-30-8) burada tanımlı değil.
    # H334 (Resp. Sens. 1) üzerinden zaten %0.1 GCL eşiği uygulanır → EUH208 tetiklenir.
    # Skin Sens. SCL'si için resmi kaynak (CLP Ek VI) doğrulanmadan değer eklenmez.
    "7789-09-5": 0.02, "10588-01-9": 0.02, "14977-61-8": 0.05, "7789-00-6": 0.05, "7775-11-3": 0.02, "7786-81-4": 0.001, "7718-54-9": 0.001, "13138-45-9": 0.001, "14216-75-2": 0.001, "92129-57-2": 0.001, "13637-71-3": 0.001, "13842-46-1": 0.001, "15699-18-0": 0.001, "13770-89-3": 0.001, "14708-14-6": 0.001, "3349-06-2": 0.001, "15843-02-4": 0.001, "68134-59-8": 0.001, "373-02-4": 0.001, "14998-37-9": 0.001, "553-71-9": 0.001, "3906-55-6": 0.001, "2223-95-2": 0.001, "16039-61-5": 0.001, "4995-91-9": 0.001, "10028-18-9": 0.001, "13462-88-9": 0.001, "13462-90-3": 0.001, "11132-10-8": 0.001, "26043-11-8": 0.001, "15060-62-5": 0.001, "13689-92-4": 0.001, "15586-38-6": 0.001, "67952-43-6": 0.001, "14550-87-9": 0.001, "71720-48-4": 0.001, "16083-14-0": 0.001, "3349-08-4": 0.001, "39819-65-3": 0.001, "18721-51-2": 0.001, "18283-82-4": 0.001, "22605-92-1": 0.001, "4454-16-4": 0.001, "7580-31-6": 0.001, "93983-68-7": 0.001, "29317-63-3": 0.001, "27637-46-3": 0.001, "84852-37-9": 0.001, "93920-10-6": 0.001, "85508-43-6": 0.001, "85508-44-7": 0.001, "51818-56-5": 0.001, "93920-09-3": 0.001, "71957-07-8": 0.001, "52625-25-9": 0.001, "13654-40-5": 0.001, "85508-45-8": 0.001, "85508-46-9": 0.001, "84852-35-7": 0.001, "84852-39-1": 0.001, "85135-77-9": 0.001, "85166-19-4": 0.001, "84852-36-8": 0.001, "85551-28-6": 0.001, "91697-41-5": 0.001, "84776-45-4": 0.001, "72319-19-8": 0.001, "97-54-1": 0.001, "5932-68-3": 0.001, "5912-86-7": 0.001, "104-55-2": 0.001, "14371-10-9": 0.001, "818-61-1": 0.02, "110-16-7": 0.01, "108-31-6": 0.0001, "2918-23-2": 0.02, "999-61-1": 0.02, "25584-83-2": 0.02, "106-90-1": 0.02, "4074-88-8": 0.02, "105512-06-9": 0.0001, "15141-18-1": 0.0001, "26761-45-5": 0.0001, "126-98-7": 0.02, "35691-65-7": 0.0001, "68516-81-4": 0.0001, "2855-13-2": 0.0001, "101-72-4": 0.01, "133-06-2": 0.0001, "133-07-3": 0.0001, "2634-33-5": 0.0036, "26530-20-1": 0.00015, "4719-04-4": 0.01, "55965-84-9": 0.00015, "2682-20-4": 0.00015, "64359-81-5": 0.00015, "2527-66-4": 0.00015, "26172-54-3": 0.00015, "4098-71-9": 0.0001, "5124-30-1": 0.05, "16938-22-0": 0.05, "15646-96-5": 0.05, "822-06-0": 0.05, "3634-83-1": 0.0001, "91-97-4": 0.0001, "79-07-2": 0.01}




def check_euh(components: List[Dict]) -> Dict:
    """
    Formüldeki bileşenlere göre EUH ifadelerini tespit eder.

    components: [
      {
        'cas': '7631-90-5',
        'name': 'sodium bisulphite',
        'conc': 50.0,
        'hazards': [{'h_class': 'Acute Tox. 4', 'h_code': 'H302'}],
        ...
      }
    ]

    Döner: {
      'euh_codes': ['EUH031', 'EUH208'],
      'euh_details': [
        {'code': 'EUH031', 'text': '...', 'source_cas': '7631-90-5', 'source_name': '...'},
        ...
      ],
      'manual_check': ['EUH018', 'EUH019', ...],  # Kullanıcı kontrol etmeli
    }
    """
    detected = []
    detected_codes = set()
    skin_sens_substances = []  # EUH208 için madde adları

    for comp in components:
        cas = str(comp.get('cas', '')).strip()
        name = comp.get('name', '') or ''
        name_tr = comp.get('name_tr', '') or name  # Türkçe isim (yoksa İngilizce)
        name_lower = name.lower()
        hazards = comp.get('hazards', [])
        hazard_classes = {h.get('h_class', '').replace('*', '').strip() for h in hazards}
        comp_conc = float(comp.get('conc', 0) or 0)

        # ── EUH019 — Patlayıcı peroksit oluşturabilir ───────────────────────
        # Org. peroksitler ve H2O2 içeren ürünler için zorunlu uyarı
        # Ayrıca Org. Perox. tehlike sınıfı taşıyan bileşenler
        EUH019_CLASSES = {'Org. Perox. A', 'Org. Perox. B', 'Org. Perox. C',
                          'Org. Perox. D', 'Org. Perox. E', 'Org. Perox. F',
                          'Self-react. A', 'Self-react. B'}
        if (cas in EUH019_CAS or hazard_classes & EUH019_CLASSES) and 'EUH019' not in detected_codes:
            detected.append({
                'code': 'EUH019',
                'text': 'Patlayıcı peroksitler oluşturabilir.',
                'source_cas': cas,
                'source_name': name,
            })
            detected_codes.add('EUH019')

        # ── EUH031 ──────────────────────────────────────────────────────────
        if cas in EUH031_CAS and 'EUH031' not in detected_codes:
            detected.append({
                'code': 'EUH031',
                'text': 'Asitlerle temasında toksik gaz çıkarır.',
                'source_cas': cas,
                'source_name': name,
            })
            detected_codes.add('EUH031')

        # ── EUH032 ──────────────────────────────────────────────────────────
        if cas in EUH032_CAS and 'EUH032' not in detected_codes:
            detected.append({
                'code': 'EUH032',
                'text': 'Asitlerle temasında çok toksik gaz çıkarır.',
                'source_cas': cas,
                'source_name': name,
            })
            detected_codes.add('EUH032')

        # ── EUH014 — Water-react. ────────────────────────────────────────────
        if hazard_classes & EUH014_CLASSES and 'EUH014' not in detected_codes:
            detected.append({
                'code': 'EUH014',
                'text': 'Su ile şiddetli reaksiyon verir.',
                'source_cas': cas,
                'source_name': name,
            })
            detected_codes.add('EUH014')

        # ── EUH029 ──────────────────────────────────────────────────────────
        if cas in EUH029_CAS and 'EUH029' not in detected_codes:
            detected.append({
                'code': 'EUH029',
                'text': 'Su ile temas halinde toksik gaz oluşturur.',
                'source_cas': cas,
                'source_name': name,
            })
            detected_codes.add('EUH029')

        # ── EUH066 ──────────────────────────────────────────────────────────
        # Kural 1: Bilinen çözücü CAS listesinde
        skin_irrit_classes = {'Skin Irrit. 2'}
        euh066_cutoff = 10.0
        
        if cas in EUH066_CAS and 'EUH066' not in detected_codes:
            detected.append({
                'code': 'EUH066',
                'text': 'Tekrarlı maruz kalma cildin kurumasına veya çatlamasına yol açabilir.',
                'source_cas': cas,
                'source_name': name,
            })
            detected_codes.add('EUH066')

        # Kural 2: Bileşen Skin Irrit. 2 taşıyor AMA karışım H315 almıyor
        # (konsantrasyon cut-off altında — karışım sınıflandırması dışında kaldı)
        # CLP Rehber Dokümanı: Bu durumda EUH066 tavsiye edilir
        elif (hazard_classes & skin_irrit_classes
              and 0 < comp_conc < euh066_cutoff
              and 'EUH066' not in detected_codes):
            detected.append({
                'code': 'EUH066',
                'text': 'Tekrarlı maruz kalma cildin kurumasına veya çatlamasına yol açabilir.',
                'source_cas': cas,
                'source_name': name,
                'note': (f'Tavsiye: {name or cas} Skin Irrit. 2 taşıyor '
                         f'(%{comp_conc} < %{euh066_cutoff} cut-off — '
                         f'karışım H315 almadı, EUH066 tavsiye edilir)')
            })
            detected_codes.add('EUH066')

        # ── EUH201 — Kurşun ─────────────────────────────────────────────────
        if cas in EUH201_CAS and 'EUH201' not in detected_codes:
            detected.append({
                'code': 'EUH201',
                'text': 'Kurşun içerir. Çocukların çiğneyebileceği yüzeylerde kullanılmamalıdır.',
                'source_cas': cas,
                'source_name': name,
            })
            detected_codes.add('EUH201')

        # ── EUH202 — Siyanakrilat ────────────────────────────────────────────
        if cas in EUH202_CAS and 'EUH202' not in detected_codes:
            detected.append({
                'code': 'EUH202',
                'text': 'Siyanakrilat. Tehlike. Anında cilt ve göz yapıştırır. Çocuklardan uzak tutun.',
                'source_cas': cas,
                'source_name': name,
            })
            detected_codes.add('EUH202')

        # ── EUH203 — Krom(VI) ────────────────────────────────────────────────
        if cas in EUH203_CAS and 'EUH203' not in detected_codes:
            detected.append({
                'code': 'EUH203',
                'text': 'Krom (VI) içerir. Alerjik reaksiyona yol açabilir.',
                'source_cas': cas,
                'source_name': name,
            })
            detected_codes.add('EUH203')

        # ── EUH204 — İzosiyanat (isim bazlı) ─────────────────────────────────
        if any(kw in name_lower for kw in EUH204_KEYWORDS) and 'EUH204' not in detected_codes:
            detected.append({
                'code': 'EUH204',
                'text': 'İzosiyanat içerir. Alerjik reaksiyona yol açabilir.',
                'source_cas': cas,
                'source_name': name,
            })
            detected_codes.add('EUH204')

        # ── EUH205 — Epoksi (isim bazlı) ─────────────────────────────────────
        if any(kw in name_lower for kw in EUH205_KEYWORDS) and 'EUH205' not in detected_codes:
            detected.append({
                'code': 'EUH205',
                'text': 'Epoksi bileşenleri içerir. Alerjik reaksiyona yol açabilir.',
                'source_cas': cas,
                'source_name': name,
            })
            detected_codes.add('EUH205')

        # ── EUH206 — Hipoklorit ──────────────────────────────────────────────
        if cas in EUH206_CAS and 'EUH206' not in detected_codes:
            detected.append({
                'code': 'EUH206',
                'text': 'Dikkat! Diğer ürünlerle birlikte kullanmayın. Tehlikeli gaz (klor) salabilir.',
                'source_cas': cas,
                'source_name': name,
            })
            detected_codes.add('EUH206')

        # ── EUH207 — Kadmiyum ────────────────────────────────────────────────
        if cas in EUH207_CAS and 'EUH207' not in detected_codes:
            detected.append({
                'code': 'EUH207',
                'text': 'Dikkat! Kadmiyum içerir. Kullanım sırasında tehlikeli duman oluşur.',
                'source_cas': cas,
                'source_name': name,
            })
            detected_codes.add('EUH207')

        # ── EUH208 — CLP Ek II §2.8 Para 2: "sınıflandırmaya yol açanın EK OLARAK" kuralı
        # Skin Sens. sınıflandırmasına neden olan madde (konc ≥ Skin Sens GCL/SCL) EUH208'e girmez;
        # zaten H317 tehlike ifadesiyle etikette yer alır.
        # EUH208: yalnızca H317 için eşik altı kalan (ama ≥%0.1) ek sensitizerlar listelenir.
        skin_sens_classes = {'Skin Sens. 1', 'Skin Sens. 1A', 'Skin Sens. 1B'}
        resp_sens_classes = {'Resp. Sens. 1', 'Resp. Sens. 1A', 'Resp. Sens. 1B'}
        is_skin_sens = bool(hazard_classes & skin_sens_classes)
        is_resp_sens = bool(hazard_classes & resp_sens_classes)

        if is_skin_sens or is_resp_sens:
            # Skin Sens. sınıflandırma eşiği: SCL varsa kullan, yoksa kategori bazlı GCL
            # CLP Ek I Tablo 3.4.3: Skin Sens. 1A → GCL=%0.1 | Skin Sens. 1B / 1 → GCL=%1.0
            is_skin_sens_1a = 'Skin Sens. 1A' in hazard_classes
            skin_class_threshold = 0.1 if is_skin_sens_1a else 1.0
            if is_skin_sens:
                # SCL varsa GCL'yi geçersiz kılar
                # scl iki formatta gelebilir:
                #   list: [{h_code:'H317', c_min:0.5}, ...]  (API / backend)
                #   dict: {'H317': 0.5, 'H314': 2.0}         (frontend _sclMap)
                scl_data = comp.get('scl', [])
                if isinstance(scl_data, list):
                    for scl_entry in scl_data:
                        if not isinstance(scl_entry, dict):
                            continue
                        scl_h = (scl_entry.get('h_code', '') or '').replace('*', '').strip()[:4]
                        if scl_h == 'H317' and scl_entry.get('c_min') is not None:
                            skin_class_threshold = float(scl_entry['c_min'])
                            break
                elif isinstance(scl_data, dict) and scl_data.get('H317') is not None:
                    skin_class_threshold = float(scl_data['H317'])

            # Madde H317 sınıflandırmasına neden oluyor mu?
            causes_skin_class = is_skin_sens and comp_conc >= skin_class_threshold

            # EUH208'e dahil: sınıflandırmaya neden olmayan sensitizerlar (≥%0.1)
            if not causes_skin_class and comp_conc >= 0.1:
                skin_sens_substances.append({
                    'name': name or cas,
                    'name_tr': name_tr or name or cas,
                    'cas': cas,
                    'conc': comp_conc,
                    'threshold': 0.1,
                    'has_scl': False,
                })

    # EUH208: Deri sensitizeri varsa + SCL/10 eşiği kontrolü
    if skin_sens_substances and 'EUH208' not in detected_codes:
        sub_names    = '; '.join(s['name']    for s in skin_sens_substances)
        sub_names_tr = '; '.join(s['name_tr'] for s in skin_sens_substances)
        scl_notes = []
        for s in skin_sens_substances:
            if s['has_scl']:
                scl_notes.append(
                    f"{s['name']}: SCL/10 eşiği=%{s['threshold']} — konsantrasyon %{s['conc']} ≥ eşik"
                )
        detected.append({
            'code': 'EUH208',
            'text'         : f'Contains: {sub_names}. May produce an allergic reaction.',
            'text_tr'      : f'İçerir: {sub_names_tr}. Alerjik reaksiyona yol açabilir.',
            'source_cas'   : '; '.join(s['cas'] for s in skin_sens_substances),
            'source_name'  : sub_names,
            'source_name_tr': sub_names_tr,
            'scl_note'     : '; '.join(scl_notes) if scl_notes else None,
        })
        detected_codes.add('EUH208')

    # Manuel kontrol gerekli olanlar (EUH019 artık otomatik tespit ediliyor)
    manual_check = [
        'EUH001', 'EUH006', 'EUH018',
        'EUH044', 'EUH059', 'EUH070', 'EUH071',
        'EUH209', 'EUH209A', 'EUH401'
    ]

    return {
        'euh_codes': sorted(list(detected_codes)),
        'euh_details': sorted(detected, key=lambda x: x['code']),
        'manual_check': manual_check,
    }


def get_euh_text(code: str) -> str:
    """EUH kodu için Türkçe metin döner"""
    texts = {
        'EUH001': 'Kuru halde patlayıcı.',
        'EUH006': 'Hava ile veya havasız patlayıcı.',
        'EUH014': 'Su ile şiddetli reaksiyon verir.',
        'EUH018': 'Kullanım sırasında yanıcı/patlayıcı buhar-hava karışımı oluşturabilir.',
        'EUH019': 'Patlayıcı peroksitler oluşturabilir.',
        'EUH029': 'Su ile temas halinde toksik gaz oluşturur.',
        'EUH031': 'Asitlerle temasında toksik gaz çıkarır.',
        'EUH032': 'Asitlerle temasında çok toksik gaz çıkarır.',
        'EUH044': 'Kapalı ortamda ısıtıldığında patlama riski.',
        'EUH059': 'Ozon tabakasına zararlı.',
        'EUH066': 'Tekrarlı maruz kalma cildin kurumasına veya çatlamasına yol açabilir.',
        'EUH070': 'Göze toksik.',
        'EUH071': 'Solunum yollarına aşındırıcı.',
        'EUH201': 'Kurşun içerir. Çocukların çiğneyebileceği yüzeylerde kullanılmamalıdır.',
        'EUH201A': 'Dikkat! Kurşun içerir.',
        'EUH202': 'Siyanakrilat. Tehlike. Anında cilt ve göz yapıştırır. Çocuklardan uzak tutun.',
        'EUH203': 'Krom (VI) içerir. Alerjik reaksiyona yol açabilir.',
        'EUH204': 'İzosiyanat içerir. Alerjik reaksiyona yol açabilir.',
        'EUH205': 'Epoksi bileşenleri içerir. Alerjik reaksiyona yol açabilir.',
        'EUH206': 'Dikkat! Diğer ürünlerle birlikte kullanmayın. Tehlikeli gaz (klor) salabilir.',
        'EUH207': 'Dikkat! Kadmiyum içerir. Kullanım sırasında tehlikeli duman oluşur.',
        'EUH208': 'İçerir [madde adı]. Alerjik reaksiyona yol açabilir.',
        'EUH209': 'Kullanımda kolayca tutuşabilir hale gelebilir.',
        'EUH209A': 'Kullanımda yanıcı hale gelebilir.',
        'EUH210': 'Talep üzerine güvenlik bilgi formu temin edilebilir.',
        'EUH401': 'İnsan sağlığını ve çevreyi korumak için kullanım talimatlarına uyunuz.',
    }
    return texts.get(code, code)
