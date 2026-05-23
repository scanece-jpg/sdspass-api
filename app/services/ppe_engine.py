"""
PPEEngine — SDS Bölüm 8 — Kişisel Koruyucu Donanım (KKD)
=========================================================
js/engines/ppe_engine.js'nin Python karşılığı.

Girdi : h_codes: List[str]  — karışımın H kodları
Çıktı : {
    'respiratory': [{'ppe': str, 'level': int}],
    'hands':       [{'ppe': str, 'level': int}],
    'eyes':        [{'ppe': str, 'level': int}],
    'body':        [{'ppe': str, 'level': int}],
    'general':     [str],
}

level: 1 = zorunlu, 2 = tavsiye edilen

Uygulanan Standartlar:
  EN 136        — Tam yüz maskesi
  EN 149        — FFP2/FFP3 tek kullanımlık maskeler
  EN 14387      — Filtre sınıfları (ABEK, P3)
  EN ISO 374-1  — Kimyasallara karşı koruyucu eldivenler
  EN 166        — Göz koruması
  EN 14605      — Kimyasal koruyucu giysiler (Tip 3/4)
  EN 13034      — Sıvı kimyasallara karşı giysiler (Tip 6)
  EN 1149-5     — Antistatik giysiler
"""

from typing import List, Dict, Any

# ── KKD KURALLARI — H kodu eşlemesi ────────────────────────────────────────
# Her kural: h_codes (tetikleyiciler), ppe (TR/EN metin), level (1=zorunlu/2=tavsiye)
# Kurallar öncelik sırasına göre listelenmiştir (ilk eşleşen kazanır).

RULES: Dict[str, List[Dict[str, Any]]] = {

    # ── Solunum Yolu Koruma ────────────────────────────────────────────────
    'respiratory': [
        {
            'h_codes': ['H330', 'H331'],
            'ppe': {
                'TR': 'Tam yüz gaz maskesi — ABEK filtreli (EN 136 / EN 14387)',
                'EN': 'Full-face gas mask with ABEK filter (EN 136 / EN 14387)',
            },
            'level': 1,
        },
        {
            'h_codes': ['H334'],
            'ppe': {
                'TR': 'Tam yüz maskesi — P3 filtreli (EN 136)',
                'EN': 'Full-face mask with P3 filter (EN 136)',
            },
            'level': 1,
        },
        {
            'h_codes': ['H370', 'H371'],
            'ppe': {
                'TR': 'Tam yüz SCBA veya ABEK gaz maskesi (EN 136)',
                'EN': 'Full-face SCBA or ABEK gas mask (EN 136)',
            },
            'level': 1,
        },
        {
            'h_codes': ['H340', 'H350', 'H360', 'H360D', 'H360F', 'H360FD'],
            'ppe': {
                'TR': 'Tam yüz maskesi — P3 kombine filtre (EN 136)',
                'EN': 'Full-face mask with P3 combination filter (EN 136)',
            },
            'level': 1,
        },
        {
            'h_codes': ['H332', 'H335', 'H336'],
            'ppe': {
                'TR': 'Yarım yüz maskesi veya FFP2 toz maskesi (EN 149)',
                'EN': 'Half-face mask or FFP2 dust mask (EN 149)',
            },
            'level': 2,
        },
    ],

    # ── El Koruma ─────────────────────────────────────────────────────────
    'hands': [
        {
            'h_codes': ['H314'],
            'ppe': {
                'TR': 'Nitril eldiven ≥0,4 mm kalınlık (EN ISO 374-1 Tip B)',
                'EN': 'Nitrile gloves ≥0.4 mm thickness (EN ISO 374-1 Type B)',
            },
            'level': 1,
        },
        {
            'h_codes': ['H300', 'H310'],
            'ppe': {
                'TR': 'Nitril veya Bütil kauçuk eldiven ≥0,5 mm (EN ISO 374-1 Tip A)',
                'EN': 'Nitrile or Butyl rubber gloves ≥0.5 mm (EN ISO 374-1 Type A)',
            },
            'level': 1,
        },
        {
            'h_codes': ['H340', 'H350', 'H360', 'H360D', 'H360F', 'H360FD'],
            'ppe': {
                'TR': 'Nitril eldiven ≥0,4 mm — tek kullanımlık değil (EN ISO 374-1)',
                'EN': 'Nitrile gloves ≥0.4 mm — not disposable (EN ISO 374-1)',
            },
            'level': 1,
        },
        {
            'h_codes': ['H315', 'H317'],
            'ppe': {
                'TR': 'Nitril eldiven ≥0,1 mm (EN ISO 374-1 Tip B)',
                'EN': 'Nitrile gloves ≥0.1 mm (EN ISO 374-1 Type B)',
            },
            'level': 2,
        },
        {
            'h_codes': ['H318', 'H319'],
            'ppe': {
                'TR': 'Koruyucu eldiven (EN ISO 374-1)',
                'EN': 'Protective gloves (EN ISO 374-1)',
            },
            'level': 2,
        },
    ],

    # ── Göz / Yüz Koruma ─────────────────────────────────────────────────
    'eyes': [
        {
            'h_codes': ['H314'],
            'ppe': {
                'TR': 'Kimyasal koruyucu yüz kalkanı + sıkı oturan gözlük (EN 166)',
                'EN': 'Chemical face shield + tight-fitting goggles (EN 166)',
            },
            'level': 1,
        },
        {
            'h_codes': ['H300', 'H310'],
            'ppe': {
                'TR': 'Sıkı oturan koruyucu gözlük (EN 166 3B)',
                'EN': 'Tight-fitting protective goggles (EN 166 3B)',
            },
            'level': 1,
        },
        {
            'h_codes': ['H318'],
            'ppe': {
                'TR': 'Sıkı oturan koruyucu gözlük (EN 166 3B)',
                'EN': 'Tight-fitting protective goggles (EN 166 3B)',
            },
            'level': 1,
        },
        {
            'h_codes': ['H330', 'H331', 'H332'],
            'ppe': {
                'TR': 'Tam yüz maskesi gözlük bölümü yeterli (EN 166)',
                'EN': 'Full-face mask visor section sufficient (EN 166)',
            },
            'level': 2,
        },
        {
            'h_codes': ['H319'],
            'ppe': {
                'TR': 'Güvenlik gözlüğü (EN 166)',
                'EN': 'Safety goggles (EN 166)',
            },
            'level': 2,
        },
    ],

    # ── Vücut / Giysi Koruma ──────────────────────────────────────────────
    'body': [
        {
            'h_codes': ['H314', 'H300', 'H310', 'H330'],
            'ppe': {
                'TR': 'Kimyasal koruyucu giysi — Tip 3 veya 4 (EN 14605)',
                'EN': 'Chemical protective suit — Type 3 or 4 (EN 14605)',
            },
            'level': 1,
        },
        {
            'h_codes': ['H340', 'H350', 'H360', 'H360D', 'H360F', 'H360FD'],
            'ppe': {
                'TR': 'Kimyasal koruyucu giysi — Tip 4 minimum (EN 14605)',
                'EN': 'Chemical protective suit — minimum Type 4 (EN 14605)',
            },
            'level': 1,
        },
        {
            'h_codes': ['H224', 'H225', 'H226'],
            'ppe': {
                'TR': 'Antistatik giysi + antistatik ayakkabı (EN 1149-5)',
                'EN': 'Antistatic clothing + antistatic footwear (EN 1149-5)',
            },
            'level': 1,
        },
        {
            'h_codes': ['H315', 'H317', 'H331', 'H332'],
            'ppe': {
                'TR': 'Kimyasal koruyucu iş elbisesi (EN 13034 Tip 6)',
                'EN': 'Chemical-resistant work clothing (EN 13034 Type 6)',
            },
            'level': 2,
        },
    ],
}

# ── Genel Hijyen Önlemleri ─────────────────────────────────────────────────
_GENERAL_ALWAYS = {
    'TR': [
        'Çalışma alanında yemeyin, içmeyin, sigara içmeyin.',
        'İşten önce ve sonra elleri iyice yıkayın.',
        'Yakın çevrede acil göz yıkama istasyonu bulundurun.',
    ],
    'EN': [
        'Do not eat, drink or smoke in work area.',
        'Wash hands thoroughly before and after work.',
        'Keep an emergency eye wash station nearby.',
    ],
}

_GENERAL_CORROSIVE = {
    'TR': 'Kontaminasyon durumunda hemen bol su ile yıkayın.',
    'EN': 'In case of contamination, wash immediately with plenty of water.',
}

_GENERAL_CMR = {
    'TR': 'Kanserojen/mutajen/reprodüktif toksin — kapalı sistem kullanın.',
    'EN': 'Carcinogen/mutagen/reproductive toxin — use closed system.',
}


def select(h_codes: List[str], lang: str = 'TR') -> Dict[str, Any]:
    """
    H kodlarına göre KKD önerileri üret.

    Args:
        h_codes : karışımın H kodları (örn. ['H314', 'H412'])
        lang    : 'TR' veya 'EN'

    Returns:
        {
          'respiratory': [{'ppe': str, 'level': int}],
          'hands':       [{'ppe': str, 'level': int}],
          'eyes':        [{'ppe': str, 'level': int}],
          'body':        [{'ppe': str, 'level': int}],
          'general':     [str],
        }
    """
    lang = (lang or 'TR').upper()
    if lang not in ('TR', 'EN'):
        lang = 'TR'

    # H kodlarını normalize et: H360D/F/FD sub-kodlarını 6 karakterde tut
    h_set = set()
    for h in h_codes:
        s = (h or '').replace('*', '').replace(' ', '').upper()
        if len(s) > 4 and s[:4] in ('H360', 'H361'):
            # H360D, H360F, H360FD, H361D, H361F, H361FD — sub-kodu koru (max 6 karakter)
            h_set.add(s[:6])
        h_set.add(s[:4])

    result: Dict[str, Any] = {
        'respiratory': [],
        'hands':       [],
        'eyes':        [],
        'body':        [],
        'general':     [],
    }

    for category, rule_list in RULES.items():
        added_texts: set = set()
        for rule in rule_list:
            if any(hc in h_set for hc in rule['h_codes']):
                ppe_text = rule['ppe'].get(lang, rule['ppe']['TR'])
                if ppe_text not in added_texts:
                    result[category].append({
                        'ppe':   ppe_text,
                        'level': rule['level'],
                    })
                    added_texts.add(ppe_text)

    # Varsayılan KKD — eşleşme yoksa minimum öneri
    if not result['hands']:
        result['hands'].append({
            'ppe': ('Nitril veya lateks eldiven (EN ISO 374-1)'
                    if lang == 'TR'
                    else 'Nitrile or latex gloves (EN ISO 374-1)'),
            'level': 2,
        })
    if not result['eyes']:
        result['eyes'].append({
            'ppe': ('Güvenlik gözlüğü (EN 166)'
                    if lang == 'TR'
                    else 'Safety goggles (EN 166)'),
            'level': 2,
        })
    if not result['body']:
        result['body'].append({
            'ppe': ('Uygun iş giysisi'
                    if lang == 'TR'
                    else 'Suitable work clothing'),
            'level': 2,
        })

    # Genel hijyen önlemleri — her zaman
    general = list(_GENERAL_ALWAYS.get(lang, _GENERAL_ALWAYS['TR']))

    corrosive_h = {'H314', 'H300', 'H310'}
    if h_set & corrosive_h:
        general.append(_GENERAL_CORROSIVE.get(lang, _GENERAL_CORROSIVE['TR']))

    cmr_h = {'H340', 'H350', 'H360', 'H360D', 'H360F', 'H360FD'}
    if h_set & cmr_h:
        general.append(_GENERAL_CMR.get(lang, _GENERAL_CMR['TR']))

    result['general'] = general

    return result


def select_flat(h_codes: List[str], lang: str = 'TR') -> Dict[str, str]:
    """
    PDF/SDS'nin mevcut tek-satır formatı için yardımcı fonksiyon.
    Her kategori için virgülle birleştirilmiş tek metin döndürür.

    Returns:
        {'resp': str, 'gloves': str, 'eyes': str, 'body': str, 'general': str}
    """
    raw = select(h_codes, lang)

    def _join(items: list) -> str:
        # Önce level=1 (zorunlu), sonra level=2 (tavsiye)
        mandatory   = [i['ppe'] for i in items if i.get('level') == 1]
        recommended = [i['ppe'] for i in items if i.get('level') == 2]
        parts = mandatory + recommended
        return '; '.join(parts) if parts else ('Gerekli değil' if lang == 'TR' else 'Not required')

    return {
        'resp':    _join(raw['respiratory']),
        'gloves':  _join(raw['hands']),
        'eyes':    _join(raw['eyes']),
        'body':    _join(raw['body']),
        'general': ' '.join(raw['general']),
    }
