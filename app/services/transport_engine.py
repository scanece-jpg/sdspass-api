"""
TransportEngine — ADR/IMDG/IATA — SDS Bölüm 14
Kaynak: ADR 2023 Tablo 3.1, IMDG Kod 2022, IATA-DGR 2024
        ADR 2.1.3.5 — Çoklu tehlike öncelik matrisi (Tablo 2.1.3.10)

JS transport_engine.js'nin Python karşılığı.
"""

from typing import List, Optional, Dict

CLASS_LABELS: Dict[str, str] = {
    '1'  : 'Patlayıcı Maddeler',
    '2.1': 'Yanıcı Gazlar',
    '2.2': 'Yanıcı Olmayan/Zehirli Gazlar',
    '3'  : 'Yanıcı Sıvılar',
    '4.1': 'Yanıcı Katılar',
    '4.2': 'Kendiliğinden Alışan Maddeler',
    '4.3': 'Su ile Tepkiyen Maddeler',
    '5.1': 'Oksitleyici Maddeler',
    '5.2': 'Organik Peroksitler',
    '6.1': 'Zehirli Maddeler',
    '6.2': 'Bulaşıcı Maddeler',
    '7'  : 'Radyoaktif Maddeler',
    '8'  : 'Aşındırıcı Maddeler',
    '9'  : 'Çeşitli Tehlikeli Maddeler ve Nesneler',
}

# H Kodu → ADR Sınıfı + Ambalaj Grubu
# ADR 2023 Bölüm 2: Her H kodunun birincil ADR sınıfı ve PG'si
# PG: 'I' (en tehlikeli) > 'II' > 'III' (en az tehlikeli) | None (uygulanmıyor)
H_TO_ADR: Dict[str, Dict] = {
    # Sınıf 1 — Patlayıcı
    'H200': {'class': '1', 'pg': 'I'}, 'H201': {'class': '1', 'pg': 'I'},
    'H202': {'class': '1', 'pg': 'I'}, 'H203': {'class': '1', 'pg': 'I'},
    'H204': {'class': '1', 'pg': 'I'}, 'H205': {'class': '1', 'pg': 'I'},
    # Sınıf 2.1 — Yanıcı Gaz
    'H220': {'class': '2.1', 'pg': None}, 'H221': {'class': '2.1', 'pg': None},
    'H222': {'class': '2.1', 'pg': None}, 'H223': {'class': '2.1', 'pg': None},
    # Sınıf 2.2 — Oksitleyici Gaz + Yanıcı Olmayan Sıkıştırılmış/Soğutulmuş Gaz
    'H270': {'class': '2.2', 'pg': None},
    'H280': {'class': '2.2', 'pg': None},   # Sıkıştırılmış/sıvılaştırılmış gaz (CLP §2.5)
    'H281': {'class': '2.2', 'pg': None},   # Soğutulmuş sıvılaştırılmış gaz (kriyojenik)
    # Sınıf 3 — Yanıcı Sıvı (parlama noktasına göre PG)
    'H224': {'class': '3', 'pg': 'I'},    # FP < 23°C, BP ≤ 35°C
    'H225': {'class': '3', 'pg': 'II'},   # FP < 23°C, BP > 35°C
    'H226': {'class': '3', 'pg': 'III'},  # 23°C ≤ FP ≤ 60°C
    # Sınıf 4.1 — Yanıcı Katı
    'H228': {'class': '4.1', 'pg': 'II'},
    # Sınıf 4.2 — Kendiliğinden Alışan / Isınan
    'H250': {'class': '4.2', 'pg': 'I'},
    'H251': {'class': '4.2', 'pg': 'II'},
    'H252': {'class': '4.2', 'pg': 'III'},
    # Sınıf 4.3 — Su ile Tepkiyen
    'H260': {'class': '4.3', 'pg': 'I'},
    'H261': {'class': '4.3', 'pg': 'II'},
    # Sınıf 5.1 — Oksitleyici
    'H271': {'class': '5.1', 'pg': 'I'},
    'H272': {'class': '5.1', 'pg': 'II'},
    # Sınıf 5.2 — Organik Peroksit
    'H241': {'class': '5.2', 'pg': None},
    'H242': {'class': '5.2', 'pg': None},
    # Sınıf 6.1 — Akut Toksisite
    # ÖNEMLİ: H302/H312/H332 (CLP Kat.4) H_TO_ADR'ye dahil EDİLMEZ.
    # Sebep: CLP Kat.4 oral aralığı 300–2000 mg/kg; ADR 6.1 PG III eşiği ≤300 mg/kg.
    # ATE > 300 mg/kg olan maddeler ADR Sınıf 6.1 kriterini karşılamaz (ADR 2.6.2.2).
    'H300': {'class': '6.1', 'pg': 'I'},   # Oral Kat.1   (LD50 ≤ 5 mg/kg)
    'H310': {'class': '6.1', 'pg': 'I'},   # Dermal Kat.1
    'H330': {'class': '6.1', 'pg': 'I'},   # İnhalasyon Kat.1
    'H301': {'class': '6.1', 'pg': 'II'},  # Oral Kat.2-3
    'H311': {'class': '6.1', 'pg': 'II'},  # Dermal Kat.2-3
    'H331': {'class': '6.1', 'pg': 'II'},  # İnhalasyon Kat.2-3
    # Sınıf 8 — Korozif
    # ADR §2.1.3.5.5: Test verisi yoksa en kötü senaryo → PG I varsayılan.
    'H314': {'class': '8', 'pg': 'I'},
    # Sınıf 9 — Çevre Tehlikesi
    # ADR 2.2.9.1.10: H412/H413 ADR Sınıf 9 kriterini karşılamaz
    # H304 (Aspirasyon Tehlikesi): ADR'de bağımsız Sınıf 9 oluşturmaz;
    # yanıcı sıvılarla birlikte Sınıf 3 kapsamında değerlendirilir.
    'H400': {'class': '9', 'pg': 'III'},
    'H410': {'class': '9', 'pg': 'III'},
    'H411': {'class': '9', 'pg': 'III'},
}

# ADR Tablo 2.1.3.10: Sınıf öncelik sırası
CLASS_RANK: Dict[str, int] = {
    '1': 10, '5.2': 9, '4.2': 8, '4.3': 7, '5.1': 6, '2.1': 5, '2.2': 4,
    '3': 3, '6.1': 3, '8': 3,   # Bu üçlü için rank eşit → PG matrisi devreye girer
    '4.1': 2, '9': 1,
}


def _pg_num(pg: Optional[str]) -> int:
    """PG stringini sayıya çevirir. I=1 (en tehlikeli), III=3, None=4."""
    return {'I': 1, 'II': 2, 'III': 3}.get(pg, 4)


def resolve_conflict(cls_a: str, pg_a: Optional[str],
                     cls_b: str, pg_b: Optional[str]) -> Dict:
    """
    ADR Tablo 2.1.3.10 PG matrisi.
    İki ADR sınıfını karşılaştırır; kazananı ve kaybedeni döner.
    Returns: { winner, win_pg, loser }
    """
    # ── ÖZEL KURAL: Sınıf 5.1 vs Sınıf 8 — rank hesabından önce ──────────────
    # ADR §2.1.3.10: Sınıf 8 PG I, Sınıf 5.1'i (tüm PG) yener.
    # CLASS_RANK 5.1>8 verir; bu kural rank'tan önce uygulanarak doğru sonuç sağlanır.
    if {cls_a, cls_b} == {'5.1', '8'}:
        pg8 = _pg_num(pg_a if cls_a == '8' else pg_b)
        if pg8 == 1:
            win_pg8 = pg_a if cls_a == '8' else pg_b
            return {'winner': '8', 'win_pg': win_pg8, 'loser': '5.1'}
        win_pg51 = pg_a if cls_a == '5.1' else pg_b
        return {'winner': '5.1', 'win_pg': win_pg51, 'loser': '8'}

    rank_a = CLASS_RANK.get(cls_a, 0)
    rank_b = CLASS_RANK.get(cls_b, 0)

    # Üst sıralama farklıysa büyük olan kazanır
    if rank_a > rank_b:
        return {'winner': cls_a, 'win_pg': pg_a, 'loser': cls_b}
    if rank_b > rank_a:
        return {'winner': cls_b, 'win_pg': pg_b, 'loser': cls_a}

    # Rank eşit → Sınıf 3 / 6.1 / 8 üçgeni: PG matrisi uygula
    p_a = _pg_num(pg_a)
    p_b = _pg_num(pg_b)

    # ── Sınıf 3 vs Sınıf 6.1 ──────────────────────────────────────────────────
    if {cls_a, cls_b} == {'3', '6.1'}:
        pg3  = p_a if cls_a == '3'   else p_b
        pg61 = p_a if cls_a == '6.1' else p_b
        wins_61 = (pg61 <= 2) and (pg3 == 3 or pg61 < pg3)
        w = '6.1' if wins_61 else '3'
        win_pg = (pg_a if cls_a == '6.1' else pg_b) if w == '6.1' else (pg_a if cls_a == '3' else pg_b)
        return {'winner': w, 'win_pg': win_pg, 'loser': '3' if w == '6.1' else '6.1'}

    # ── Sınıf 3 vs Sınıf 8 ────────────────────────────────────────────────────
    if {cls_a, cls_b} == {'3', '8'}:
        pg3 = p_a if cls_a == '3' else p_b
        pg8 = p_a if cls_a == '8' else p_b
        wins_8 = (pg8 == 1) or (pg8 == 2 and pg3 == 3)
        w = '8' if wins_8 else '3'
        win_pg = (pg_a if cls_a == '8' else pg_b) if w == '8' else (pg_a if cls_a == '3' else pg_b)
        return {'winner': w, 'win_pg': win_pg, 'loser': '3' if w == '8' else '8'}

    # ── Sınıf 6.1 vs Sınıf 8 ──────────────────────────────────────────────────
    if {cls_a, cls_b} == {'6.1', '8'}:
        pg61 = p_a if cls_a == '6.1' else p_b
        pg8  = p_a if cls_a == '8'   else p_b
        wins_8 = (pg61 >= 2 and pg8 == 1) or (pg61 == 3 and pg8 == 2)
        w = '8' if wins_8 else '6.1'
        win_pg = (pg_a if cls_a == '8' else pg_b) if w == '8' else (pg_a if cls_a == '6.1' else pg_b)
        return {'winner': w, 'win_pg': win_pg, 'loser': '6.1' if w == '8' else '8'}

    # Aynı sınıf: en düşük PG (en tehlikeli) kazanır
    if cls_a == cls_b:
        if p_a <= p_b:
            return {'winner': cls_a, 'win_pg': pg_a, 'loser': None}
        return {'winner': cls_b, 'win_pg': pg_b, 'loser': None}

    # Bilinmeyen çift — A kazanır (muhafazakâr)
    return {'winner': cls_a, 'win_pg': pg_a, 'loser': cls_b}


def _get_un_entry(cls: str, pg: Optional[str], sub: Optional[str], is_solid: bool,
                  h_set: set = None) -> Dict:
    """UN numarası ve etiket belirle."""
    h_set = h_set or set()
    if cls == '1':
        return {
            'un': 'UN 0000*', 'label': 'Patlayıcı',
            'note': 'UN numarası maddeye özgü belirlenir; patlayıcı sınıfı tüm yan tehlikeleri ezer',
        }
    if cls == '2.1':
        return {
            'un': 'UN 1954', 'label': 'Yanıcı Gaz, B.N.O.',
            'note': 'Maddeye özgü UN numarası önceliklidir (ör. UN1978 propan, UN1001 asetilen)',
        }
    if cls == '2.2':
        if 'H270' in h_set:
            return {
                'un': 'UN 3156', 'label': 'Sıkıştırılmış Gaz, Oksitleyici, B.N.O.',
                'note': 'ADR Sınıf 2.2 oksitleyici — tüp/tank özel kuralları geçerlidir',
            }
        if 'H281' in h_set:
            return {
                'un': 'UN 3158', 'label': 'Basınç Altında Soğutulmuş Gaz, Yanıcı Olmayan, B.N.O.',
                'note': 'Kriyojenik gaz — özel yalıtımlı tank gerektirir (ADR P203)',
            }
        return {
            'un': 'UN 1956', 'label': 'Sıkıştırılmış Gaz, Yanıcı Olmayan, B.N.O.',
            'note': 'Maddeye özgü UN numarası önceliklidir (ör. UN1066 azot, UN1046 helyum)',
        }
    if cls == '3':
        if sub == '8':
            return {
                'un': 'UN 2924', 'label': 'Yanıcı Sıvı, Korozif, B.N.O.',
                'note': (
                    'UN 2924 seçim gerekçesi (ADR 2023): '
                    'Alevlenir sıvı (H224/H225/H226, Sınıf 3) + aşındırıcı (H314, Sınıf 8) kombinasyonu. '
                    'ADR Tablo 2.1.3.10: Sınıf 3 birincil, Sınıf 8 yan tehlike — '
                    'birincil sınıf Sınıf 3 PG ≤ II ile aşındırıcı PG II birlikteliğinde Sınıf 3 önceliği korur. '
                    'ADR 3.1.2.8.1: Ürüne özgü UN girişi yoksa UN 2924 N.O.S. uygulanır. '
                    'Ambalaj grubu birincil sınıfın PG değerinden belirlenir. '
                    'Taşımacılık uzmanı onayı önerilir.'
                ),
            }
        if sub == '6.1':
            return {'un': 'UN 1992', 'label': 'Yanıcı Sıvı, Toksik, B.N.O.',
                    'note': 'ADR 2023: Sınıf 3 birincil, Sınıf 6.1 yan tehlike'}
        return {'un': 'UN 1993', 'label': 'Yanıcı Sıvı, B.N.O.'}
    if cls == '4.1':
        return {
            'un': 'UN 1325', 'label': 'Yanıcı Katı, Organik, B.N.O.',
            'note': 'Maddeye özgü UN önceliklidir; PG I/III uzman onayı gerekir',
        }
    if cls == '4.2':
        if pg == 'I':
            return {'un': 'UN 2845', 'label': 'Pirofor Sıvı, Organik, B.N.O.',
                    'note': 'H250: Hava temasında kendiliğinden alışır — PG I, özel ambalaj'}
        if pg == 'II':
            return {'un': 'UN 3088', 'label': 'Kendiliğinden Isınan Katı, Organik, B.N.O.'}
        return {'un': 'UN 3190', 'label': 'Kendiliğinden Isınan Katı, Organik, B.N.O.'}
    if cls == '4.3':
        if is_solid:
            return {'un': 'UN 3132', 'label': 'Su ile Tepkiyen Katı, Yanıcı, B.N.O.'}
        return {'un': 'UN 3148', 'label': 'Su ile Tepkiyen Sıvı, B.N.O.'}
    if cls == '5.1':
        if sub == '8':
            if is_solid:
                return {
                    'un': 'UN 3085', 'label': 'Oksitleyici Katı, Aşındırıcı, B.N.O.',
                    'note': 'ADR 2025: Oksitleyici katı (Sınıf 5.1) + aşındırıcı (Sınıf 8) → UN 3085.',
                }
            return {
                'un': 'UN 3098', 'label': 'Oksitleyici Sıvı, Aşındırıcı, B.N.O.',
                'note': (
                    'UN 3098 (OC1) seçim gerekçesi (ADR 2025): '
                    'Oksitleyici sıvı (Sınıf 5.1) + aşındırıcı (H314, Sınıf 8) kombinasyonu. '
                    'ADR §2.1.3.10 Tehlike Öncelik Tablosu: 5.1+8 → UN3098 (kod OC1). '
                    'Taşımacılık uzmanı onayı önerilir.'
                ),
            }
        if is_solid:
            return {'un': 'UN 1479', 'label': 'Oksitleyici Katı, B.N.O.'}
        if pg == 'I':
            return {'un': 'UN 2912', 'label': 'Oksitleyici Sıvı, B.N.O.'}
        return {'un': 'UN 3139', 'label': 'Oksitleyici Sıvı, B.N.O.'}
    if cls == '5.2':
        if is_solid:
            return {
                'un': 'UN 3106', 'label': 'Organik Peroksit, Tip D, E, F, Katı',
                'note': 'Tip belirlenmesi (A-G) gereklidir; UN3106 Tip D/E/F katı varsayılan',
            }
        return {
            'un': 'UN 3105', 'label': 'Organik Peroksit, Tip D, E, F, Sıvı',
            'note': 'Tip belirlenmesi (A-G) gereklidir; UN3105 Tip D/E/F varsayılan',
        }
    if cls == '6.1':
        if sub == '3':
            lbl = ('Zehirli Katı, Yanıcı, Organik, B.N.O.' if is_solid
                   else 'Zehirli Sıvı, Yanıcı, Organik, B.N.O.')
            return {'un': 'UN 2929', 'label': lbl,
                    'note': 'ADR 2023: Sınıf 6.1 birincil, Sınıf 3 yan tehlike (ADR Tablo 2.1.3.10)'}
        if sub == '8':
            return {
                'un': 'UN 2928' if is_solid else 'UN 2927',
                'label': ('Zehirli Katı, Korozif, Organik, B.N.O.' if is_solid
                          else 'Zehirli Sıvı, Korozif, Organik, B.N.O.'),
                'note': 'Organik yapı için UN 2927/2928; inorganik → UN 3289/3290',
            }
        return {
            'un': 'UN 2811' if is_solid else 'UN 2810',
            'label': ('Zehirli Katı, Organik, B.N.O.' if is_solid
                      else 'Zehirli Sıvı, Organik, B.N.O.'),
            'note': 'UN 2810/2811 organik bileşikler için; inorganik → UN 3287/3288',
        }
    if cls == '8':
        if sub == '5.1':
            if is_solid:
                return {
                    'un': 'UN 3084',
                    'label': 'Korozif Katı, Oksitleyici, B.N.O.',
                    'note': 'ADR 2025: Aşındırıcı katı (Sınıf 8) + oksitleyici (Sınıf 5.1) → UN 3084.',
                }
            return {
                'un': 'UN 3093',
                'label': 'Korozif Sıvı, Oksitleyici, B.N.O.',
                'note': (
                    'UN 3093 (CO1) seçim gerekçesi (ADR 2025): '
                    'Aşındırıcı sıvı (H314, Sınıf 8 PG I) + oksitleyici (H271/H272, Sınıf 5.1) kombinasyonu. '
                    'ADR §2.1.3.10: Sınıf 8 PG I, Sınıf 5.1\'i her durumda yener. '
                    'ADR §2.1.3.5.5: Test verisi yoksa en kötü senaryo (PG I) uygulanır. '
                    'ADR 2025 Tablo A UN3093 PG I: kemler=885, tünel=E. '
                    'Gerçek korozivite test verisi (§2.2.8.1.4.1) mevcutsa PG II veya III\'e revize edilebilir.'
                ),
            }
        if sub == '3':
            return {
                'un': 'UN 2921' if is_solid else 'UN 2920',
                'label': ('Korozif Katı, Yanıcı, B.N.O.' if is_solid
                          else 'Korozif Sıvı, Yanıcı, B.N.O.'),
                'note': 'ADR 2023: Sınıf 8 birincil, Sınıf 3 yan tehlike (ADR Tablo 2.1.3.10)',
            }
        if sub == '6.1':
            return {
                'un': 'UN 2928' if is_solid else 'UN 2927',
                'label': ('Zehirli Katı, Korozif, Organik, B.N.O.' if is_solid
                          else 'Zehirli Sıvı, Korozif, Organik, B.N.O.'),
            }
        return {
            'un': 'UN 1759' if is_solid else 'UN 1760',
            'label': 'Korozif Katı, B.N.O.' if is_solid else 'Korozif Sıvı, B.N.O.',
            'note': 'Asidik inorganik → UN 3264 | Bazik → UN 3266 | Organik → UN 1760 | PG I uzman onayı',
        }
    if cls == '9':
        return {
            'un': 'UN 3077' if is_solid else 'UN 3082',
            'label': ('Çevre için Tehlikeli Madde, Katı, B.N.O.' if is_solid
                      else 'Çevre için Tehlikeli Madde, Sıvı, B.N.O.'),
        }
    return {'un': '—', 'label': 'Bilinmiyor'}


def classify(h_codes: List[str], form: str = 'liquid',
             phys_h_codes: Optional[List[str]] = None) -> Dict:
    """
    ADR/IMDG/IATA sınıflandırması.

    Args:
        h_codes      : CLP motorundan gelen H kodları
        form         : 'liquid' | 'solid' | 'aerosol' | 'gas'
        phys_h_codes : Fiziksel motordan gelen H22x/H228 kodları

    Returns:
        {
          not_regulated, road, sea, air,
          conflict_warning, adr_caution
        }
    """
    is_solid = (form or 'liquid') in ('solid', 'powder')

    # H kodlarını temizle ve birleştir
    def _clean(h: str) -> str:
        return h.replace('*', '').replace(' ', '')[:4]

    all_h = list(dict.fromkeys(
        [_clean(h) for h in (h_codes or []) if h]
        + [_clean(h) for h in (phys_h_codes or []) if h]
    ))
    all_h = [h for h in all_h if h.startswith('H')]
    h_set = set(all_h)

    # Çevre tehlike işareti — ADR 2.2.9.1.10: sadece H400, H410, H411
    env_mark = bool(h_set & {'H400', 'H410', 'H411'})

    # ── Adım 1: Aktif ADR tehlikelerini çıkar ────────────────────────────────
    # Aynı sınıf için en tehlikeli PG'yi (en küçük sayı) sakla
    class_map: Dict[str, Dict] = {}
    for h in all_h:
        adr = H_TO_ADR.get(h)
        if not adr:
            continue
        cls = adr['class']
        existing = class_map.get(cls)
        new_num = _pg_num(adr['pg'])
        if not existing or new_num < existing['pg_num']:
            class_map[cls] = {'pg': adr['pg'], 'pg_num': new_num}

    detected = [{'class': cls, 'pg': v['pg']} for cls, v in class_map.items()]

    if not detected:
        return {
            'not_regulated': True,
            'road': None, 'sea': None, 'air': None,
            'note': 'Bu madde/karışım tehlikeli madde olarak sınıflandırılmamıştır.',
            'conflict_warning': None, 'adr_caution': None,
        }

    # ── Adım 2: Birincil sınıfı ADR Tablo 2.1.3.10 matrisiyle belirle ────────
    primary = {'class': detected[0]['class'], 'pg': detected[0]['pg']}
    for item in detected[1:]:
        res = resolve_conflict(primary['class'], primary['pg'],
                               item['class'], item['pg'])
        if res['winner'] != primary['class']:
            primary = {'class': res['winner'], 'pg': res['win_pg']}

    # ── Adım 3: Yan tehlikeleri belirle ──────────────────────────────────────
    subs = sorted(
        [d for d in detected if d['class'] != primary['class']],
        key=lambda d: _pg_num(d['pg'])
    )
    sub_class = subs[0]['class'] if subs else None

    # ── Adım 4: UN ve etiket ──────────────────────────────────────────────────
    un_entry = _get_un_entry(primary['class'], primary['pg'], sub_class, is_solid, h_set)

    # Aerosol formu — her zaman UN 1950 (CLP §2.3.6 / ADR 2023 Sınıf 2)
    # H222/H223 → Sınıf 2.1 doğru; ama UN 1954 değil UN 1950 kullanılır
    if form == 'aerosol':
        _aero_lbl = 'Aerosol, Yanıcı' if h_set & {'H222', 'H223'} else 'Aerosol'
        un_entry = {
            'un':   'UN 1950',
            'label': _aero_lbl + ', B.N.O.',
            'note': 'Aerosol dispensers her zaman UN 1950 — CLP §2.3.6 / ADR 2023',
        }

    # ── Adım 5: Uyarılar ─────────────────────────────────────────────────────
    # (a) H22x çelişki kontrolü
    flam_present = [h for h in ['H224', 'H225', 'H226'] if h in h_set]
    conflict_warning = None
    if flam_present and primary['class'] not in ('3', '2.1'):
        conflict_warning = {
            'level': 'CRITICAL',
            'message': (
                f"Alevlenirlik tehlikesi ({'/'.join(flam_present)}) tespit edildi ancak "
                f"birincil taşımacılık sınıfı Sınıf {primary['class']}. "
                f"Parlama noktası ≤ 60°C ise ADR 2023 kapsamında Sınıf 3 değerlendirilmelidir."
            ),
        }

    # (b) H302/H312/H332 bilgi notu — CLP Kat.4 ADR eşiğini karşılamayabilir
    kat4_present = [h for h in ['H302', 'H312', 'H332'] if h in h_set]
    adr_caution = None
    if kat4_present:
        adr_caution = {
            'level': 'INFO',
            'message': (
                f"{'/'.join(kat4_present)} (CLP Akut Toksisite Kat.4) mevcut. "
                f"ADR Sınıf 6.1 PG III için LD50 ≤ 300 mg/kg gerekir (ADR 2.6.2.2). "
                f"Karışımın ATE değeri bu eşiği aşıyorsa ADR Sınıf 6.1 uygulanmaz — "
                f"taşımacılık uzmanına danışın."
            ),
        }

    # (c) H304 bilgi notu — aspirasyon tehlikesi tek başına ADR Sınıf 9 oluşturmaz
    if 'H304' in h_set and adr_caution is None:
        adr_caution = {
            'level': 'INFO',
            'message': (
                "H304 (Aspirasyon Tehlikesi Kat.1) mevcut. "
                "ADR 2023: Aspirasyon tehlikesi bağımsız bir ADR sınıfı oluşturmaz — "
                "yanıcı sıvı (Sınıf 3) kapsamında değerlendirilir. "
                "Parlama noktası > 60°C ise taşımacılık uzmanı değerlendirmesi önerilir."
            ),
        }

    # (d) H370/H371 bilgi notu — STOT SE doğrudan ADR Sınıf 6.1'e eşlenmez
    stot_se_present = [h for h in ['H370', 'H371'] if h in h_set]
    if stot_se_present and adr_caution is None:
        acute_tox_present = bool(h_set & {'H300', 'H301', 'H310', 'H311', 'H330', 'H331'})
        if not acute_tox_present:
            adr_caution = {
                'level': 'INFO',
                'message': (
                    f"{'/'.join(stot_se_present)} (STOT Tek Maruziyet) mevcut ancak "
                    f"akut toksisite kodu (H300/H301/H310/H311/H330/H331) bulunmuyor. "
                    f"ADR 2023: STOT SE kodları doğrudan ADR Sınıf 6.1'e eşlenmez. "
                    f"LD50/LC50 verisi mevcutsa ADR 2.6.2.2 kapsamında Sınıf 6.1 "
                    f"uygulanabilirliği taşımacılık uzmanı tarafından değerlendirilmelidir."
                ),
            }

    # Yan tehlike etiketi
    all_sub_labels = ', '.join(f"Sınıf {s['class']}" for s in subs)
    sub_label = f' (Yan Tehlike: {all_sub_labels})' if all_sub_labels else ''

    entry = {
        'un':              un_entry['un'],
        'class':           primary['class'],
        'class_label':     CLASS_LABELS.get(primary['class'], primary['class']) + sub_label,
        'pg':              primary['pg'],
        'label':           un_entry['label'],
        'sub_class':       sub_class,
        'note':            un_entry.get('note'),
        'env_mark':        env_mark,
        'conflict_warning': conflict_warning,
        'adr_caution':     adr_caution,
    }

    return {
        'not_regulated':    False,
        'road': {**entry, 'regulation': 'ADR 2023'},
        'sea':  {**entry, 'regulation': 'IMDG Kod 2022'},
        'air':  {**entry, 'regulation': 'IATA-DGR 2024'},
        'conflict_warning': conflict_warning,
        'adr_caution':      adr_caution,
    }
