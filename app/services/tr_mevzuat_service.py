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


# ── Atık kodu (gösterge) — Atık Yönetimi Yönetmeliği (RG 02.04.2015/29314) ─────────────
# Md.12(1): atık kodunu atık sahibi Ek-1 hiyerarşisine göre belirler. KKDİK Ek-2 13.1 kod
# istemez; GBF'de yalnız kullanılmamış/standart dışı ürün için gösterge verilir:
#   16 03 "Standart dışı ürün grupları ve kullanılmamış ürünler" — (M) ayna kayıtlar:
#   16 03 03* / 16 03 04 (inorganik), 16 03 05* / 16 03 06 (organik).
# Tehlikelilik: Ek-3/B eşik konsantrasyonları. Yönetmelik eşikleri R ifadeleriyle verir. SEA'nın
# çevrim tablosu (Ek-7) RG 10.12.2020/31330 ile yürürlükten kalktığından R → H karşılıkları AB CLP
# (EC 1272/2008) Ek-VII çevrim tablosundan alınmıştır. Tablo tek yönlüdür (R → H); bir H kodu
# birden çok R ifadesine karşılık geliyorsa en sıkı eşik uygulanır (örn. H370: T+;R39/26-28 veya
# T;R39/23-25 → T+). Kat. 1C cilt aşındırıcı Ek-VII'de yoktur (eski sistemde 1C yoktu); R34
# grubunda değerlendirilir. Duyarlılaştırıcılar (H317/H334) için Ek-3/B'de eşik yoktur. Ek-3/B Açıklama (5):
# atık yalnız ekotoksik (H14) olduğu için tehlikeli sayılmaz → sucul H kodları listede yok.
_EK3B = [
    # (H kodları, alt kategori filtresi, eşik %, Ek-3/B bendi, açıklama)
    ({'H300', 'H310', 'H330', 'H370'}, None, 0.1, 'b', 'yüksek seviyede zehirli (H300/H310/H330/H370)'),
    ({'H301', 'H311', 'H331', 'H372'}, None, 3.0, 'c', 'zehirli (H301/H311/H331/H372)'),
    ({'H302', 'H312', 'H332', 'H371', 'H373', 'H304'}, None, 25.0, 'ç', 'zararlı (H302/H312/H332/H371/H373/H304)'),
    ({'H314'}, 'R35', 1.0, 'd', 'R35 aşındırıcı (H314 Kat. 1A)'),
    ({'H314'}, 'R34', 5.0, 'e', 'R34 aşındırıcı (H314 Kat. 1B/1C)'),
    ({'H318'}, None, 10.0, 'f', 'R41 tahriş edici (H318)'),
    ({'H315', 'H319', 'H335'}, None, 20.0, 'g', 'R36/R37/R38 tahriş edici (H315/H319/H335)'),
    ({'H350'}, None, 0.1, 'ğ', 'kanserojen Kat. 1A/1B (H350)'),
    ({'H351'}, None, 1.0, 'h', 'kanserojen Kat. 2 (H351)'),
    ({'H360'}, None, 0.5, 'ı', 'üreme sistemine toksik Kat. 1A/1B (H360)'),
    ({'H361'}, None, 5.0, 'i', 'üreme sistemine toksik Kat. 2 (H361)'),
    ({'H340'}, None, 0.1, 'j', 'mutajen Kat. 1A/1B (H340)'),
    ({'H341'}, None, 1.0, 'k', 'mutajen Kat. 2 (H341)'),
]

# Bilinen inorganik maddeler (organik/inorganik ayrımı için; su hesaba katılmaz)
_INORGANIC_CAS = {
    '497-19-8', '144-55-8', '15630-89-4', '7632-04-4', '10486-00-7', '1310-73-2', '1310-58-3',
    '7647-01-0', '7664-93-9', '7664-38-2', '7697-37-2', '7681-52-9', '7778-54-3', '7647-14-5',
    '7757-82-6', '1344-09-8', '6834-92-0', '1318-02-1', '7758-29-4', '7601-54-9', '7722-84-1',
    '7664-41-7', '1336-21-6', '1305-62-0', '1305-78-8', '584-08-7', '7758-98-7', '7646-85-7',
    '13463-67-7', '7631-86-9', '1332-58-7', '14808-60-7', '7775-27-1', '7722-88-5', '5329-14-6',
    '7664-39-3', '10043-35-3', '7783-20-2', '12125-02-9', '7447-40-7', '10043-52-4', '7786-30-3',
}
_WATER = '7732-18-5'


def _comp_conc(c: dict) -> float:
    try:
        return float(c.get('concMax') or c.get('concentration') or c.get('conc') or 0)
    except (TypeError, ValueError):
        return 0.0


def waste_assessment(components: list, mixture_h: list = None) -> dict:
    """Kullanılmamış ürün için gösterge atık kodu ve Ek-3/B gerekçesi."""
    comps = components or []
    met = []
    for codes, sub, limit, item, label in _EK3B:
        total = 0.0
        for c in comps:
            hit = False
            for h in c.get('hazards') or []:
                hc = str(h.get('h_code') or '').replace('*', '').strip()[:4]
                if hc not in codes:
                    continue
                if sub:
                    cls = str(h.get('h_class') or '').replace(' ', '').upper()
                    is_1bc = cls.endswith('1B') or cls.endswith('1C')
                    if (sub == 'R34') != is_1bc:   # alt kategorisiz "Skin Corr. 1" → R35 (en kötü durum)
                        continue
                hit = True
            if hit:
                total += _comp_conc(c)
        if total >= limit:
            met.append({'item': item, 'label': label, 'total': round(total, 2), 'limit': limit})
    mix = {str(h)[:4] for h in (mixture_h or [])}
    if mix & {'H224', 'H225', 'H226'}:
        met.insert(0, {'item': 'a', 'label': ('parlama noktası ≤ 55 °C (alevlenir sıvı' +
                                             ('; H226 için parlama noktası 55–60 °C ise bu bent uygulanmaz)'
                                              if not (mix & {'H224', 'H225'}) else ')')),
                       'total': None, 'limit': None})
    hazardous = bool(met)

    w_inorg = sum(_comp_conc(c) for c in comps
                  if (c.get('cas_no') or c.get('cas') or '').strip() in _INORGANIC_CAS)
    w_all = sum(_comp_conc(c) for c in comps
                if (c.get('cas_no') or c.get('cas') or '').strip() not in ('', _WATER))
    inorganic = w_all > 0 and w_inorg / w_all > 0.5
    if inorganic:
        code, desc = (('16 03 03*', 'Tehlikeli maddeler içeren anorganik atıklar') if hazardous
                      else ('16 03 04', '16 03 03 dışındaki anorganik atıklar'))
    else:
        code, desc = (('16 03 05*', 'Tehlikeli maddeler içeren organik atıklar') if hazardous
                      else ('16 03 06', '16 03 05 dışındaki organik atıklar'))
    return {'hazardous': hazardous, 'criteria': met, 'inorganic': inorganic, 'code': code, 'desc': desc}


def _ewc_code_bullet(wa: dict, lang: str = 'TR') -> str:
    if lang == 'TR':
        if wa['criteria']:
            c0 = wa['criteria'][0]
            why = (f"Ek-3/B ({c0['item']}) {c0['label']}"
                   # Kesin toplam yazılmaz — Bölüm 3'te aralıkla verilen konsantrasyonları açığa çıkarır
                   + (f": ilgili bileşenlerin toplamı eşik değeri (%{c0['limit']:g}) aşmaktadır"
                      if c0['total'] is not None else ''))
        else:
            why = 'Ek-3/B eşik konsantrasyonlarının hiçbiri aşılmıyor'
        return (f"Kullanılmamış / standart dışı ürün için gösterge atık kodu: {wa['code']} — {wa['desc']} "
                f"(Atık Yönetimi Yönetmeliği Ek-4, 16 03 Standart Dışı Gruplar ve Kullanılmamış Ürünler). Gerekçe: {why}. Kullanım sonrası oluşan atığın "
                f"kodunu, atığın kaynağına göre Ek-1 atık kodu belirleme hiyerarşisini uygulayarak atık sahibi "
                f"belirler (Md.12).")
    return (f"Indicative waste code for unused / off-specification product: {wa['code']} "
            f"(Turkish Waste Management Regulation Annex 4, 16 03). The waste holder determines the final code "
            f"according to the source of the waste (Art. 12).")


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


def get_disposal_content(h_codes: list = None, lang: str = 'TR', components: list = None) -> dict:
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

    # ── 2. Bertaraf yöntemi — atığın tehlikelilik durumuna göre (Ek-3/B) ───────
    wa = waste_assessment(components or [], h_codes)
    if wa['hazardous'] and wa['inorganic']:
        # İnorganik atıkta yakma uygun yöntem değildir (KKDİK Ek-2 13.1(a): yöntem belirtilir)
        method_bullet = ('Lisanslı tehlikeli atık bertaraf tesisine teslim edin. Uygun yöntem: fiziko-kimyasal '
                         'arıtma (nötralizasyon/çöktürme) ve ardından düzenli depolama.' if lang == 'TR' else
                         'Deliver to a licensed hazardous waste facility. Suitable method: physico-chemical '
                         'treatment (neutralisation/precipitation) followed by landfill.')
    elif wa['hazardous']:
        method_bullet = S(lang, 'disposal_method_general')
    else:
        method_bullet = ('Atık, Ek-3/B eşiklerine göre tehlikeli değildir; lisanslı bir atık işleme tesisine '
                         'teslim edin. Mümkünse geri kazanım tercih edilir.' if lang == 'TR' else
                         'Not hazardous waste per the threshold concentrations; deliver to a licensed waste '
                         'treatment facility. Recovery is preferred where possible.')

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
    ewc_bullet = _ewc_code_bullet(wa, lang)

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
    if wa['hazardous']:
        packaging_text = S(lang, 'contaminated_packaging') + (
            ' Ürün kalıntısı içeren ambalaj: 15 01 10* — Tehlikeli maddelerin kalıntılarını içeren ya da '
            'tehlikeli maddelerle kontamine olmuş ambalajlar (Ek-4).' if lang == 'TR' else
            ' Packaging containing residues: 15 01 10* (Annex 4).')
    else:
        packaging_text = ('KONTAMİNE AMBALAJ: Ambalajları mümkün olduğunca tamamen boşaltın. Ürün tehlikeli atık '
                          'sayılmadığından boş ambalajlar malzeme türüne göre ambalaj atığı (15 01 01 – 15 01 09) '
                          'olarak geri kazanıma verilebilir.' if lang == 'TR' else
                          'CONTAMINATED PACKAGING: Empty containers completely; as the product is not hazardous '
                          'waste, empty packaging may be recycled as packaging waste (15 01 01 – 15 01 09).')

    return {
        'product_bullets': product_bullets,
        'packaging_text':  packaging_text,
        'drain_note':      drain_note,
        'waste':           wa,
    }


if __name__ == '__main__':
    print(get_section15_text(['H225', 'H315', 'H350'], has_biocide=False))
    print()
    print(get_disposal_regulation('TR'))
    print()
    import json
    print(json.dumps(get_disposal_content(['H226', 'H410', 'H350'], 'TR'), ensure_ascii=False, indent=2))
