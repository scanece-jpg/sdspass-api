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
    cancer_h = {'H340','H341','H350','H351',
                'H360','H360D','H360F','H360FD',
                'H361','H361D','H361F','H361FD',
                'H362'}
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


def _ewc_code_bullet(h_codes: list, lang: str = 'TR') -> str:
    """
    H kodlarından gösterge EWC/Ek-4 atık kodu üret.
    KKDİK Ek-2 §13.1: atık tanımlama kodu zorunlu unsurdur.
    Öncelik sırası: CMR > yanıcı çözücü > korozif/toksik > genel tehlikeli > tehlikesiz.
    """
    h_set = set(h_codes or [])

    if h_set & {'H340','H341','H350','H351',
                'H360','H360D','H360F','H360FD',
                'H361','H361D','H361F','H361FD',
                'H362'}:
        code = '16 05 06*'
        desc_tr = 'Tehlikeli madde içeren atık laboratuvar kimyasalları'
        desc_en = 'Laboratory chemicals, consisting of or containing dangerous substances'
    elif h_set & {'H224', 'H225', 'H226'}:
        code = '14 06 03*'
        desc_tr = 'Diğer çözücüler ve çözücü karışımları'
        desc_en = 'Other solvents and solvent mixtures'
    elif h_set & {'H314', 'H300', 'H301', 'H302', 'H310', 'H311',
                  'H330', 'H331', 'H400', 'H410', 'H411'}:
        code = '07 01 08*'
        desc_tr = 'Tehlikeli madde içeren diğer dip artıkları ve reaksiyon kalıntıları'
        desc_en = 'Other still bottoms and reaction residues containing dangerous substances'
    elif h_set & {'H412', 'H413', 'H315', 'H317', 'H319', 'H332', 'H335', 'H336'}:
        code = '07 01 99'
        desc_tr = 'Başka türlü tanımlanmamış atık'
        desc_en = 'Wastes not otherwise specified'
    else:
        code = '07 01 08*'
        desc_tr = 'Tehlikeli madde içeren diğer dip artıkları ve reaksiyon kalıntıları'
        desc_en = 'Other still bottoms and reaction residues containing dangerous substances'

    if lang == 'TR':
        return (
            f"Atık tanımlama kodu (gösterge): {code} — {desc_tr} "
            f"(Atık Yönetimi Yönetmeliği Ek-4). "
            f"Kesin kod için yetkili çevre danışmanına veya lisanslı atık bertaraf şirketine başvurun."
        )
    return (
        f"Indicative waste code: {code} — {desc_en} "
        f"(Turkish Hazardous Waste Regulations Annex 4 / EU Waste Catalogue). "
        f"Confirm the exact code with a licensed waste management consultant."
    )


def get_disposal_regulation(lang: str = 'TR') -> str:
    """Bölüm 13 için atık yönetimi mevzuat metni (geriye dönük uyumluluk)."""
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


def get_disposal_content(h_codes: list = None, lang: str = 'TR') -> dict:
    """
    KKDİK Ek-2 §13.1 gerekliliklerine uygun dinamik bertaraf içeriği üret.

    Returns:
        {
            'product_bullets': List[str],  — ürün bertaraf maddeleri (bullet listesi)
            'packaging_text':  str,        — kontamine ambalaj metni (her zaman)
            'drain_note':      str | None, — kanalizasyon yasağı (sucul tehlike varsa)
        }
    """
    from app.services.i18n_sds import S

    h_codes = h_codes or []
    reg     = TR_REGULATIONS['atik']

    # ── 1. Mevzuat referansı (her zaman) ─────────────────────────────────────
    if lang == 'TR':
        ref_bullet = (
            f"{reg['full']} ({reg['rg_date']} tarihli ve {reg['rg_no']} sayılı RG) "
            f"ve yerel atık yönetimi düzenlemelerine uygun olarak bertaraf edin."
        )
    else:
        ref_bullet = (
            f"Dispose of in accordance with Turkish Hazardous Waste Regulations "
            f"(Official Gazette {reg['rg_no']}, {reg['rg_date']}) and local regulations."
        )

    # ── 2. Bertaraf yöntemi (her zaman) ──────────────────────────────────────
    method_bullet = S(lang, 'disposal_method_general')

    # ── 3. Sucul tehlike → kanalizasyon yasağı ───────────────────────────────
    _aquatic_h = {'H400', 'H410', 'H411', 'H412', 'H413'}
    drain_note = None
    if any(h in h_codes for h in _aquatic_h):
        drain_note = S(lang, 'drain_prohibition')

    # ── 4. Yanıcı sıvılar → yakma yöntemi vurgusu ───────────────────────────
    _flam_h = {'H224', 'H225', 'H226'}
    if lang == 'TR' and any(h in h_codes for h in _flam_h):
        method_bullet = (
            'Yanıcı sıvı — lisanslı tehlikeli atık tesisinde kontrollü yakma yöntemiyle '
            'bertaraf edin. Açık alev veya kıvılcım kaynağına yakın bertaraf etmeyin.'
        )
    elif any(h in h_codes for h in _flam_h) and lang != 'TR':
        method_bullet = (
            'Flammable liquid — dispose of by controlled incineration at a licensed '
            'hazardous waste facility. Keep away from ignition sources during disposal.'
        )

    # ── 5. EWC atık kodu (KKDİK Ek-2 §13.1 zorunlu unsur) ───────────────────
    ewc_bullet = _ewc_code_bullet(h_codes, lang)

    # ── 6. CMR maddeler → ek uyarı ───────────────────────────────────────────
    _cmr_h = {'H340','H341','H350','H351',
              'H360','H360D','H360F','H360FD',
              'H361','H361D','H361F','H361FD',
              'H362'}
    product_bullets = [ref_bullet, method_bullet, ewc_bullet]
    if any(h in h_codes for h in _cmr_h):
        if lang == 'TR':
            product_bullets.append(
                'CMR maddesi (kanserojen/mutajen/üreme toksik) — bertaraf işlemi yalnızca '
                'eğitimli personel tarafından ve uygun KKE kullanılarak gerçekleştirilmelidir.'
            )
        else:
            product_bullets.append(
                'CMR substance (carcinogenic/mutagenic/reprotoxic) — disposal operations '
                'must be carried out by trained personnel using appropriate PPE.'
            )

    # ── 6. Kontamine ambalaj (her zaman — KKDİK Ek-2 §13.1 zorunlu) ────────
    packaging_text = S(lang, 'contaminated_packaging')

    return {
        'product_bullets': product_bullets,
        'packaging_text':  packaging_text,
        'drain_note':      drain_note,
    }


if __name__ == '__main__':
    print(get_section15_text(['H225', 'H315', 'H350'], has_biocide=False))
    print()
    print(get_disposal_regulation('TR'))
    print()
    import json
    print(json.dumps(get_disposal_content(['H226', 'H410', 'H350'], 'TR'), ensure_ascii=False, indent=2))
