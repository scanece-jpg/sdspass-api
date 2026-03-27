"""
Türkiye Mevzuat Metinleri Servisi
===================================
SDS Bölüm 15 için KKDİK ve ilgili Türk yönetmelikleri
tam metinleri ve referansları.

Kaynak:
  - KKDİK: 23.06.2017 tarihli ve 30105 sayılı Resmî Gazete
  - BKK: 31.12.2008 tarihli ve 27097 sayılı Resmî Gazete
  - KKDIK güncellemeleri: 2019, 2021, 2023
"""


# ── Temel mevzuat listesi ─────────────────────────────────────────────────────
TR_REGULATIONS = {
    'kkdik': {
        'name': 'KKDİK',
        'full': 'Kimyasalların Kaydı, Değerlendirilmesi, İzni ve Kısıtlanması Hakkında Yönetmelik',
        'rg_no': '30105',
        'rg_date': '23.06.2017',
        'eu_equivalent': 'REACH (EC) No 1907/2006',
    },
    'bkk': {
        'name': 'BKK',
        'full': 'Biyo-Sidal Ürünler Hakkında Yönetmelik',
        'rg_no': '27097',
        'rg_date': '31.12.2008',
        'eu_equivalent': 'BPR (EU) No 528/2012',
    },
    'kkdik_ek2': {
        'name': 'KKDİK Ek-2',
        'full': 'KKDİK Yönetmeliği Ek-2 — Güvenlik Bilgi Formu Hazırlama Rehberi',
        'rg_no': '30105',
        'rg_date': '23.06.2017',
        'eu_equivalent': 'EU CLP 2020/878 (SDS Annex)',
    },
    'sea': {
        'name': 'SEA Yönetmeliği',
        'full': 'Maddelerin ve Karışımların Sınıflandırılması, Etiketlenmesi ve Ambalajlanması Hakkında Yönetmelik',
        'rg_no': '28848',
        'rg_date': '11.12.2013',
        'eu_equivalent': 'CLP (EC) No 1272/2008',
    },
    'kanserojen': {
        'name': 'Kanserojen/Mutajen Yönetmeliği',
        'full': 'Kanserojen veya Mutajen Maddelerle Çalışmalarda Sağlık ve Güvenlik Önlemleri Hakkında Yönetmelik',
        'rg_no': '25328',
        'rg_date': '26.12.2003',
        'eu_equivalent': 'CMD Directive 2004/37/EC',
    },
    'kimyasal_is': {
        'name': 'Kimyasal Maddeler Yönetmeliği',
        'full': 'Kimyasal Maddelerle Çalışmalarda Sağlık ve Güvenlik Önlemleri Hakkında Yönetmelik',
        'rg_no': '28733',
        'rg_date': '12.08.2013',
        'eu_equivalent': 'Chemical Agents Directive 98/24/EC',
    },
    'atik': {
        'name': 'Atık Yönetimi Yönetmeliği',
        'full': 'Atık Yönetimi Yönetmeliği',
        'rg_no': '29314',
        'rg_date': '02.04.2015',
        'eu_equivalent': 'Waste Framework Directive 2008/98/EC',
    },
    'adr_tr': {
        'name': 'ADR (Türkiye)',
        'full': 'Tehlikeli Maddelerin Karayoluyla Taşınması Hakkında Yönetmelik',
        'rg_no': '30754',
        'rg_date': '24.04.2019',
        'eu_equivalent': 'ADR 2023',
    },
}


def get_section15_text(
    h_codes: list,
    has_biocide: bool = False,
    lang: str = 'TR'
) -> str:
    """
    H kodlarına göre ilgili mevzuatı otomatik seç.
    SDS Bölüm 15.1 için metin oluştur.
    """
    applicable = ['kkdik', 'sea', 'kimyasal_is', 'adr_tr', 'atik']

    # Kanserojenik/mutajenik maddeler
    cancer_h = {'H340','H341','H350','H351','H360','H361','H362'}
    if any(h in h_codes for h in cancer_h):
        applicable.append('kanserojen')

    # Biyosit içeriyorsa
    if has_biocide:
        applicable.append('bkk')

    # Kanserojenik/mutajenik — ek yönetmelik
    cancer_h_extra = {'H340','H341','H350','H351'}
    if any(h in h_codes for h in cancer_h_extra):
        if 'kanserojen' not in applicable:
            applicable.append('kanserojen')

    # Metin oluştur
    if lang == 'TR':
        lines = ['Bu ürün aşağıdaki Türk mevzuatı kapsamında sınıflandırılmıştır:']
        for key in applicable:
            reg = TR_REGULATIONS.get(key)
            if reg:
                lines.append(
                    f"• {reg['name']} — {reg['full']} "
                    f"(RG: {reg['rg_date']}, Sayı: {reg['rg_no']})"
                )
    else:
        lines = ['This product is classified under the following Turkish legislation:']
        for key in applicable:
            reg = TR_REGULATIONS.get(key)
            if reg:
                lines.append(
                    f"• {reg['name']} — {reg['full']} "
                    f"[TR equivalent of {reg['eu_equivalent']}]"
                )

    return '\n'.join(lines)


def get_disposal_regulation(lang: str = 'TR') -> str:
    """Bölüm 13 için atık yönetimi mevzuat metni."""
    reg = TR_REGULATIONS['atik']
    if lang == 'TR':
        return (
            f"{reg['full']} ({reg['rg_date']} tarihli ve {reg['rg_no']} sayılı RG) "
            f"ve yerel atık yönetimi düzenlemelerine uygun olarak bertaraf edin. "
            f"Atık kodu için yetkili çevre danışmanına başvurun."
        )
    return (
        f"Dispose of in accordance with Turkish Hazardous Waste Regulations "
        f"(Official Gazette {reg['rg_no']}, {reg['rg_date']}) and local regulations. "
        f"Consult a licensed waste disposal company."
    )


if __name__ == '__main__':
    print(get_section15_text(['H225', 'H315', 'H350'], has_biocide=False))
    print()
    print(get_disposal_regulation('TR'))
