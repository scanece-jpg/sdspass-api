"""
TransportEngine — ADR/IMDG/IATA — SDS Bölüm 14
Kaynak: ADR 2025 Tablo 3.1, IMDG Kod 42-24, IATA-DGR 2026
        ADR 2.1.3.5 — Çoklu tehlike öncelik matrisi (Tablo 2.1.3.10)

JS transport_engine.js'nin Python karşılığı.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict
from app.services.transport_adr_service import lookup_by_cas as _lookup_by_cas


@dataclass
class Component:
    """Taşıma sayımı ve B3 render için birleşik bileşen nesnesi.

    h_codes: B3 render ile AYNI kaynak — bu nesnenin kopyası değil, aynı listesi.
    conc:    ham % değer (maske render'da uygulanır, burada ham sayı).
    m_acute/m_chronic: deniz kirletici gerekçe tablosu için (şimdilik None kabul).
    """
    cas:       str
    conc:      float
    h_codes:   list
    ec:        'str | None' = None
    name:      str = ''
    m_acute:   'int | None' = None
    m_chronic: 'int | None' = None
    h_classes: 'list | None' = None   # örn. 'Skin Corr. 1A' — Sınıf 8 PG hesabı (ADR 2.2.8.1.6.3)


# ADR Bölüm 2'ye göre taşıma sınıfı tetikleyen H kodları.
# Kapsam: Sınıf 3/4/5/6.1/8/9 — portföy ağırlıklı biyosid + kimyasal.
# Kasıtlı dışarıda bırakılanlar (buraya eklenmeden önce ADR Tablo A'da doğrulayın):
#   H200-H206 (Sınıf 1, patlayıcı)       — portföyde yok; CAS araması tüm sınıfları kapsar
#   H280/H281 (Sınıf 2, basınçlı gaz)    — aerosol eklenince buraya eklenmeli
#   H290 (Sınıf 8, metallere aşındırıcı, H314 olmadan tek başına) — şimdilik dışarıda; TODO
#   H302/H312/H332 (Kat.4 akut toksisite) — ADR 6.1 LD50 ≤300 mg/kg eşiği; Kat.4 yetmez
#   H315/H317/H319/H335/H336             — ADR sınıfı tetiklemez
#   H412/H413                             — ADR sınıfı tetiklemez (H411 sınırı)
_TRANSPORT_TRIGGER_H: frozenset = frozenset({
    # Fiziksel tehlikeler
    'H220', 'H221', 'H222', 'H223', 'H224', 'H225', 'H226', 'H228',
    'H240', 'H241', 'H242', 'H250', 'H251', 'H252', 'H260', 'H261',
    'H270', 'H271', 'H272',
    # Akut toksisite Kat.1-3
    'H300', 'H301', 'H310', 'H311', 'H330', 'H331',
    # Aşındırıcılık
    'H314',
    # Sucul — ADR §2.2.9.1.10
    'H400', 'H410', 'H411',
})


def build_transport_components(raw_components: list) -> 'list[Component]':
    """Ham bileşen listesini (request body dict'leri) Component nesnelerine dönüştürür.

    Konsantrasyon parse edilemezse ValueError yükseltir — sessiz 0.0 fallback yoktur.
    Çağıran try bloğu içinde çağırmalı; hata PDF üretimini durdurur.
    """
    result: list[Component] = []
    for c in raw_components:
        cas = str(c.get('cas_no') or c.get('cas') or '').strip()
        if not cas:
            continue
        raw_conc = c.get('conc') or c.get('concentration') or c.get('concMax')
        if raw_conc is None:
            raise ValueError(
                f'Bileşen {cas}: konsantrasyon alanı eksik — '
                'transport §3.1.3.2 sayımı yapılamaz'
            )
        try:
            conc = float(
                str(raw_conc)
                .replace('%', '').replace('≥', '').replace('≤', '')
                .replace('>', '').replace('<', '').strip()
                .split('-')[0] or '0'
            )
        except (ValueError, TypeError) as _e:
            raise ValueError(
                f'Bileşen {cas}: konsantrasyon parse edilemedi ({raw_conc!r}) — {_e}'
            ) from _e
        # H kodları: flat 'h_codes' listesi varsa kullan, yoksa 'hazards' listesinden çek.
        # PDF endpoint'inde _refresh_comp sonrası kodlar hazards[*].h_code'da saklanır.
        _raw_h = c.get('h_codes')
        if not _raw_h:
            _raw_h = [h['h_code'] for h in (c.get('hazards') or []) if h.get('h_code')]
        _raw_cls = [h.get('h_class') or '' for h in (c.get('hazards') or []) if h.get('h_code')]
        result.append(Component(
            cas=cas,
            conc=conc,
            h_codes=list(_raw_h),
            ec=c.get('ec_no') or None,
            name=c.get('name') or '',
            m_acute=c.get('m_acute') or None,
            m_chronic=c.get('m_chronic') or None,
            h_classes=_raw_cls,
        ))
    return result

CLASS_LABELS: Dict[str, str] = {
    # ADR 2025 (TR) 2.1.1.1 sınıf başlıkları; 2.1/2.2/2.3 için 2.2.2.1.3 grupları
    '1'  : 'Patlayıcı maddeler ve nesneler',
    '2.1': 'Gazlar — alevlenebilir',
    '2.2': 'Gazlar — alevlenebilir olmayan, zehirli olmayan',   # ADR 2.2.2.1 (yükseltgen gazlar da 2.2 etiketli)
    '2.3': 'Gazlar — zehirli',
    '3'  : 'Alevlenebilir sıvılar',
    '4.1': 'Alevlenebilir katılar, kendiliğinden tepkimeye giren maddeler, polimerleştirici maddeler ve duyarlılığı azaltılmış katı patlayıcılar',
    '4.2': 'Kendiliğinden yanmaya yatkın maddeler',
    '4.3': 'Su ile temas ettiğinde alevlenebilir gazlar açığa çıkartan maddeler',
    '5.1': 'Yükseltgen (Oksitleyici) maddeler',
    '5.2': 'Organik peroksitler',
    '6.1': 'Zehirli maddeler',
    '6.2': 'Bulaşıcı maddeler',
    '7'  : 'Radyoaktif malzemeler',
    '8'  : 'Aşındırıcı maddeler',
    '9'  : 'Muhtelif tehlikeli maddeler ve nesneler',
}

# H Kodu → ADR Sınıfı + Ambalaj Grubu
# ADR 2025 Bölüm 2: Her H kodunun birincil ADR sınıfı ve PG'si
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
    # H232 (pirofor gaz) TR SEA'da yok; AB kaynaklı bileşen kaydında gelirse gaz olarak Sınıf 2 (F) — 4.2 değil
    'H232': {'class': '2.1', 'pg': None},
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
    # ATE > 300 mg/kg olan maddeler ADR Sınıf 6.1 kriterini karşılamaz (ADR 2.2.61.1.7).
    # ADR 2.2.61.1.7 PG sınırları CLP kategori sınırlarıyla örtüşür:
    #   oral  I ≤5 / II ≤50 / III ≤300 mg/kg  = Kat.1 / Kat.2 / Kat.3
    #   dermal I ≤50 / II ≤200 / III ≤1000    = Kat.1 / Kat.2 / Kat.3
    #   toz/sis (4 sa LC50 × 4 = 1 sa LC50): I ≤0,05 / II ≤0,5 / III ≤1,0 mg/l = Kat.1 / 2 / 3
    # H300 Kat.1 ve Kat.2'yi birlikte kapsar → kategori bilinmiyorsa PG I (en kötü durum).
    # Kategori biliniyorsa (ATEmix) _tox61_pg() kesin PG'yi verir.
    'H300': {'class': '6.1', 'pg': 'I'},   # Oral Kat.1-2
    'H310': {'class': '6.1', 'pg': 'I'},   # Dermal Kat.1-2
    'H330': {'class': '6.1', 'pg': 'I'},   # İnhalasyon Kat.1-2
    'H301': {'class': '6.1', 'pg': 'III'}, # Oral Kat.3 (50–300 mg/kg)
    'H311': {'class': '6.1', 'pg': 'III'}, # Dermal Kat.3 (200–1000 mg/kg)
    'H331': {'class': '6.1', 'pg': 'II'},  # İnhalasyon Kat.3 — buhar için uçuculuk (V) bilinmeden
                                           # kesin PG verilemez (ADR 2.2.61.1.8); PG II en kötü durum
    # Sınıf 8 — Korozif
    # ADR §2.1.3.5.5: Test verisi yoksa en kötü senaryo → PG I varsayılan.
    'H314': {'class': '8', 'pg': 'I'},
    # ADR 2.2.8.1.5.3 (c)(ii): cilde aşındırıcı olmayan ama çelik/alüminyumda 55 °C'de yılda > 6,25 mm aşındıran
    # maddeler Sınıf 8 PG III — SEA Ek-1 2.16 (H290, UN Test C.1) ile aynı ölçüt
    'H290': {'class': '8', 'pg': 'III'},
    # Sınıf 9 — Çevre Tehlikesi
    # ADR 2.2.9.1.10: H412/H413 ADR Sınıf 9 kriterini karşılamaz
    # H304 (Aspirasyon Tehlikesi): ADR'de bağımsız Sınıf 9 oluşturmaz;
    # yanıcı sıvılarla birlikte Sınıf 3 kapsamında değerlendirilir.
    'H400': {'class': '9', 'pg': 'III'},
    'H410': {'class': '9', 'pg': 'III'},
    'H411': {'class': '9', 'pg': 'III'},
}

# ADR 2.1.3.5.3: tehlike önceliği tablosundan önce gelen sınıflar (büyük değer önce gelir).
# (d) Sınıf 3 duyarlılığı azaltılmış patlayıcılar ve (e) Sınıf 4.1 kendiliğinden tepkimeye
# girenler portföyde H koduyla ayırt edilemediğinden listede yok.
# '4.2' yalnızca PG I (piroforik, H250) için; '6.1i' = PG I soluma zehirliliği ((h) bendi).
# Sınıf 2 kendi içinde: zehirli (2.3) > alevlenir (2.1) > yanıcı olmayan (2.2) — ADR 2.2.2.1.5 grup sırası
# (T… > F > A). Önceden üçü eşitti; bileşim sırasına göre 2.2 kazanabiliyordu (LPG → UN 3163).
_PRIORITY_2135: Dict[str, float] = {
    '1': 9, '2.3': 8.3, '2.1': 8.2, '2.2': 8.1, '4.2P': 6, '5.2': 5, '6.1i': 4,
}

# ADR 2.1.3.10 Tehlike önceliği tablosu (ADR 2025 Cilt I, s.101 — birebir aktarım).
# Satır anahtarı "sınıf,PG[,yol]"; yol: D=dermal, O=oral, I=soluma (yalnızca 6.1).
# Sütun sırası _PT_COLS. Hücre: "sınıf,PG" veya "S:…|L:…" (katı | sıvı ayrımı);
# "*" = karşı tarafın PG'si (tabloda PG yazmayan "KATI 4.1/4.2" hücreleri).
_PT_COLS = ['4.1,II', '4.1,III', '4.2,II', '4.2,III', '4.3,I', '4.3,II', '4.3,III',
            '5.1,I', '5.1,II', '5.1,III', '6.1,I,D', '6.1,I,O', '6.1,II', '6.1,III',
            '8,I', '8,II', '8,III', '9']
_N = None
_PT_ROWS: Dict[str, list] = {
    '3,I':    ['S:4.1,*|L:3,I', 'S:4.1,*|L:3,I', 'S:4.2,*|L:3,I', 'S:4.2,*|L:3,I',
               '4.3,I', '4.3,I', '4.3,I', 'S:5.1,I|L:3,I', 'S:5.1,I|L:3,I', 'S:5.1,I|L:3,I',
               '3,I', '3,I', '3,I', '3,I', '3,I', '3,I', '3,I', '3,I'],
    '3,II':   ['S:4.1,*|L:3,II', 'S:4.1,*|L:3,II', 'S:4.2,*|L:3,II', 'S:4.2,*|L:3,II',
               '4.3,I', '4.3,II', '4.3,II', 'S:5.1,I|L:3,I', 'S:5.1,II|L:3,II', 'S:5.1,II|L:3,II',
               '3,I', '3,I', '3,II', '3,II', '8,I', '3,II', '3,II', '3,II'],
    '3,III':  ['S:4.1,*|L:3,II', 'S:4.1,*|L:3,III', 'S:4.2,*|L:3,II', 'S:4.2,*|L:3,III',
               '4.3,I', '4.3,II', '4.3,III', 'S:5.1,I|L:3,I', 'S:5.1,II|L:3,II', 'S:5.1,III|L:3,III',
               '6.1,I', '6.1,I', '6.1,II', '3,III', '8,I', '8,II', '3,III', '3,III'],
    '4.1,II': [_N, _N, '4.2,II', '4.2,II', '4.3,I', '4.3,II', '4.3,II', '5.1,I', '4.1,II', '4.1,II',
               '6.1,I', '6.1,I', 'S:4.1,II|L:6.1,II', 'S:4.1,II|L:6.1,II',
               '8,I', 'S:4.1,II|L:8,II', 'S:4.1,II|L:8,II', '4.1,II'],
    '4.1,III':[_N, _N, '4.2,II', '4.2,III', '4.3,I', '4.3,II', '4.3,III', '5.1,I', '4.1,II', '4.1,III',
               '6.1,I', '6.1,I', '6.1,II', 'S:4.1,III|L:6.1,III',
               '8,I', '8,II', 'S:4.1,III|L:8,III', '4.1,III'],
    '4.2,II': [_N] * 4 + ['4.3,I', '4.3,II', '4.3,II', '5.1,I', '4.2,II', '4.2,II',
               '6.1,I', '6.1,I', '4.2,II', '4.2,II', '8,I', '4.2,II', '4.2,II', '4.2,II'],
    '4.2,III':[_N] * 4 + ['4.3,I', '4.3,II', '4.3,III', '5.1,I', '5.1,II', '4.2,III',
               '6.1,I', '6.1,I', '6.1,II', '4.2,III', '8,I', '8,II', '4.2,III', '4.2,III'],
    '4.3,I':  [_N] * 7 + ['5.1,I', '4.3,I', '4.3,I', '6.1,I', '4.3,I', '4.3,I', '4.3,I',
               '4.3,I', '4.3,I', '4.3,I', '4.3,I'],
    '4.3,II': [_N] * 7 + ['5.1,I', '4.3,II', '4.3,II', '6.1,I', '4.3,I', '4.3,II', '4.3,II',
               '8,I', '4.3,II', '4.3,II', '4.3,II'],
    '4.3,III':[_N] * 7 + ['5.1,I', '5.1,II', '4.3,III', '6.1,I', '6.1,I', '6.1,II', '4.3,III',
               '8,I', '8,II', '4.3,III', '4.3,III'],
    '5.1,I':  [_N] * 10 + ['5.1,I'] * 8,
    '5.1,II': [_N] * 10 + ['6.1,I', '5.1,I', '5.1,II', '5.1,II', '8,I', '5.1,II', '5.1,II', '5.1,II'],
    '5.1,III':[_N] * 10 + ['6.1,I', '6.1,I', '6.1,II', '5.1,III', '8,I', '8,II', '5.1,III', '5.1,III'],
    '6.1,I,D':  [_N] * 14 + ['S:6.1,I|L:8,I', '6.1,I', '6.1,I', '6.1,I'],
    '6.1,I,O':  [_N] * 14 + ['S:6.1,I|L:8,I', '6.1,I', '6.1,I', '6.1,I'],
    '6.1,II,I': [_N] * 14 + ['S:6.1,I|L:8,I', '6.1,II', '6.1,II', '6.1,II'],
    '6.1,II,D': [_N] * 14 + ['S:6.1,I|L:8,I', 'S:6.1,II|L:8,II', '6.1,II', '6.1,II'],
    '6.1,II,O': [_N] * 14 + ['8,I', 'S:6.1,II|L:8,II', '6.1,II', '6.1,II'],
    '6.1,III':  [_N] * 14 + ['8,I', '8,II', '8,III', '6.1,III'],
    '8,I':    [_N] * 17 + ['8,I'],
    '8,II':   [_N] * 17 + ['8,II'],
    '8,III':  [_N] * 17 + ['8,III'],
}
_PT_ORDER = ['3', '4.1', '4.2', '4.3', '5.1', '6.1', '8', '9']


def _pg_num(pg: Optional[str]) -> int:
    """PG stringini sayıya çevirir. I=1 (en tehlikeli), III=3, None=4."""
    return {'I': 1, 'II': 2, 'III': 3}.get(pg, 4)


def _tox61_routes(h_set: set, acute_tox: Optional[List[Dict]], form: str) -> Dict[str, Dict]:
    """Sınıf 6.1 PG'sini zehirlilik yoluna göre döndürür: {'O'|'D'|'I': {pg, dust?, vapour?}}.

    ADR 2.2.61.1.7 PG sınırları CLP akut toksisite kategorileriyle örtüşür (oral, dermal ve
    toz/sis için 4 sa LC50 × 4 = 1 sa LC50 — 2.2.61.1.7 son paragraf): Kat.1→I, Kat.2→II,
    Kat.3→III, Kat.4→6.1 değil. Buhar için PG uçuculuğa (V) bağlıdır (2.2.61.1.8); V bilinmediği
    için Kat.1-2→I, Kat.3→II en kötü durum alınır.
    """
    out: Dict[str, Dict] = {}

    def _put(r, pg, **kw):
        if pg and (r not in out or _pg_num(pg) < _pg_num(out[r]['pg'])):
            out[r] = {'pg': pg, **kw}

    if acute_tox:
        for e in acute_tox:
            n = e.get('cat_num')
            route = e.get('route') or ''
            if not n:
                continue
            if route == 'oral':
                _put('O', {1: 'I', 2: 'II', 3: 'III'}.get(n))
            elif route == 'dermal':
                _put('D', {1: 'I', 2: 'II', 3: 'III'}.get(n))
            elif route == 'inhalation_dust':
                _put('I', {1: 'I', 2: 'II', 3: 'III'}.get(n), dust=True)
            elif route.startswith('inhalation'):
                _put('I', {1: 'I', 2: 'I', 3: 'II'}.get(n), vapour=True)
    # ATEmix sonucu olmayan yollar için H kodu (en kötü durum)
    _hroute = {'H300': 'O', 'H301': 'O', 'H310': 'D', 'H311': 'D', 'H330': 'I', 'H331': 'I'}
    _solid = (form or '') in ('solid', 'powder')
    for h, r in _hroute.items():
        if h in h_set and r not in out:
            pg = H_TO_ADR[h]['pg']
            if h == 'H331' and _solid:
                pg = 'III'   # katıda soluma = toz; Kat.3 toz → PG III (2.2.61.1.7)
            _put(r, pg, dust=_solid)
    return out


# ── Sınıf 8 — ADR 2.2.8.1.6.3 hesaplama yöntemi ─────────────────────────────────
# Bileşenin Sınıf 8 PG'si ("atanmış PG"): madde Tablo A'da adıyla varsa oradaki PG (örn. NaOH
# UN1824 PG II, H3PO4 UN1805 PG III); yoksa CLP cilt aşındırma alt kategorisi — ADR 2.2.8.1.5.3
# tablosunun temas/gözlem süreleri CLP ile aynıdır → 1A = PG I, 1B = PG II, 1C = PG III.
# Alt kategorisi belirtilmemiş "Skin Corr. 1" en kötü durum PG I sayılır.
def _comp_corr_pg(comp: 'Component') -> Optional[str]:
    if 'H314' not in {str(h).replace('*', '').strip()[:4] for h in (comp.h_codes or [])}:
        return None
    try:
        from app.services.transport_adr_service import class8_pg_for_cas
        _ta = class8_pg_for_cas(comp.cas)
        if _ta:
            return _ta
    except Exception:
        pass
    best = None
    for cls in comp.h_classes or []:
        c = str(cls).replace(' ', '').upper()
        if not (c.startswith('SKINCORR') or c.startswith('CİLTAŞ') or c.startswith('CILTAS')):
            continue
        pg = 'II' if c.endswith('1B') else 'III' if c.endswith('1C') else 'I'
        if best is None or _pg_num(pg) < _pg_num(best):
            best = pg
    return best or 'I'


def corrosive_mixture_pg(components: 'List[Component]') -> Optional[str]:
    """ADR 2.2.8.1.6.3 Şekil 2.2.8.1.6.3 (genel konsantrasyon sınırları, Tablo A'da SCL yok):
    ΣPG I ≥ %1 → (ΣPG I ≥ %5 ise PG I, değilse PG II);
    değilse ΣPG I + ΣPG II ≥ %5 → PG II; değilse ΣPG I+II+III ≥ %5 → PG III; değilse Sınıf 8 değil.
    Yalnız ≥ %1 bileşenler toplanır (2.2.8.1.6.3.2)."""
    s = {'I': 0.0, 'II': 0.0, 'III': 0.0}
    for c in components or []:
        pg = _comp_corr_pg(c)
        if pg and (c.conc or 0) >= 1.0:
            s[pg] += c.conc
    if s['I'] >= 1:
        return 'I' if s['I'] >= 5 else 'II'
    if s['I'] + s['II'] >= 5:
        return 'II'
    if s['I'] + s['II'] + s['III'] >= 5:
        return 'III'
    return None


# Sınıf 8 B.B.B. girişinin seçimi (ADR 2.1.2 — en uygun/özel B.B.B. girişi): asidik/bazik ve
# inorganik/organik. Yalnızca bilinen maddelerden karar verilir; belirsizse C9/C10 genel giriş.
_CORR_INORG_ACID = {'7647-01-0', '7664-93-9', '7697-37-2', '7664-38-2', '7664-39-3', '10035-10-6',
                    '7790-93-4', '13780-03-5', '5329-14-6'}
_CORR_INORG_BASE = {'1310-73-2', '1310-58-3', '7664-41-7', '1336-21-6', '6834-92-0', '1344-09-8',
                    '7681-52-9', '7778-54-3', '1305-62-0'}
_CORR_ORG_ACID   = {'64-18-6', '64-19-7', '79-14-1', '75-75-2', '27176-87-0', '68584-22-5',
                    '79-11-8', '76-05-1', '107-92-6', '79-09-4'}
_CORR_ORG_BASE   = {'141-43-5', '111-42-2', '124-68-5', '109-89-7', '107-15-3', '110-91-8',
                    '102-71-6', '75-59-2'}
_CORR_NOS = {  # (asidik?, inorganik?, katı?) → UN
    (True, True, False): 'UN 3264',  (True, False, False): 'UN 3265',
    (False, True, False): 'UN 3266', (False, False, False): 'UN 3267',
    (True, True, True): 'UN 3260',   (True, False, True): 'UN 3261',
    (False, True, True): 'UN 3262',  (False, False, True): 'UN 3263',
}
_CORR_NOS_NAME = {
    'UN 3264': 'AŞINDIRICI SIVI, ASİDİK, İNORGANİK, B.B.B.', 'UN 3265': 'AŞINDIRICI SIVI, ASİDİK, ORGANİK, B.B.B.',
    'UN 3266': 'AŞINDIRICI SIVI, BAZİK, İNORGANİK, B.B.B.',  'UN 3267': 'AŞINDIRICI SIVI, BAZİK, ORGANİK, B.B.B.',
    'UN 3260': 'AŞINDIRICI KATI, ASİDİK, İNORGANİK, B.B.B.', 'UN 3261': 'AŞINDIRICI KATI, ASİDİK, ORGANİK, B.B.B.',
    'UN 3262': 'AŞINDIRICI KATI, BAZİK, İNORGANİK, B.B.B.',  'UN 3263': 'AŞINDIRICI KATI, BAZİK, ORGANİK, B.B.B.',
}


def _corr_nos(components: 'List[Component]', is_solid: bool, mixture_ph=None) -> Optional[str]:
    corr = [c for c in components or [] if _comp_corr_pg(c)]
    if not corr:
        return None
    cas = {c.cas for c in corr}
    acid_set = _CORR_INORG_ACID | _CORR_ORG_ACID
    base_set = _CORR_INORG_BASE | _CORR_ORG_BASE
    if cas <= (_CORR_INORG_ACID | _CORR_INORG_BASE):
        inorganic = True
    elif cas <= (_CORR_ORG_ACID | _CORR_ORG_BASE):
        inorganic = False
    else:
        return None
    acidic = None
    try:
        ph = float(str(mixture_ph).replace(',', '.')) if mixture_ph not in (None, '') else None
    except ValueError:
        ph = None
    if ph is not None and ph != 7:
        acidic = ph < 7
    elif cas <= acid_set:
        acidic = True
    elif cas <= base_set:
        acidic = False
    if acidic is None:
        return None
    return _CORR_NOS[(acidic, inorganic, bool(is_solid))]


def _prio_key(cls: str, pg: Optional[str], route: Optional[str]) -> str:
    """ADR 2.1.3.5.3 öncelik anahtarı ('' = öncelik listesinde değil → 2.1.3.10 tablosu)."""
    if cls == '4.2' and pg == 'I':
        return '4.2P'
    if cls == '6.1' and pg == 'I' and route == 'I':
        return '6.1i'
    return cls if cls in _PRIORITY_2135 else ''


def _pt_key(cls: str, pg: Optional[str], route: Optional[str], as_row: bool) -> str:
    if cls == '9':
        return '9'
    if cls == '6.1':
        if pg == 'I':
            return '6.1,I,' + ('O' if route == 'O' else 'D')
        if pg == 'II':
            return '6.1,II,' + (route if route in ('I', 'D', 'O') else 'D') if as_row else '6.1,II'
    return f'{cls},{pg}'


def resolve_conflict(cls_a: str, pg_a: Optional[str],
                     cls_b: str, pg_b: Optional[str],
                     route_a: Optional[str] = None, route_b: Optional[str] = None,
                     solid: bool = False) -> Dict:
    """
    ADR 2.1.3.5.3 öncelik listesi + 2.1.3.10 tehlike önceliği tablosu.
    route_*: yalnızca Sınıf 6.1 için zehirliliğin yolu ('O' oral, 'D' dermal, 'I' soluma).
    solid: tablodaki KATI/SIVI ayrımlı hücreler için ürünün fiziksel hali.
    Returns: { winner, win_pg, loser }  — win_pg tablo gereği yükseltilmiş olabilir
             (örn. Sınıf 3 PG II + 6.1 PG I → Sınıf 3 PG I).
    """
    if cls_a == cls_b:
        if _pg_num(pg_a) <= _pg_num(pg_b):
            return {'winner': cls_a, 'win_pg': pg_a, 'loser': None}
        return {'winner': cls_b, 'win_pg': pg_b, 'loser': None}

    # ── ADR 2.1.3.5.3: öncelikli sınıflar ────────────────────────────────────
    ka, kb = _prio_key(cls_a, pg_a, route_a), _prio_key(cls_b, pg_b, route_b)
    pa, pb = _PRIORITY_2135.get(ka, 0), _PRIORITY_2135.get(kb, 0)
    if pa or pb:
        if pa >= pb:
            return {'winner': cls_a, 'win_pg': pg_a, 'loser': cls_b}
        return {'winner': cls_b, 'win_pg': pg_b, 'loser': cls_a}

    # ── ADR 2.1.3.10 tablosu ─────────────────────────────────────────────────
    ia = _PT_ORDER.index(cls_a) if cls_a in _PT_ORDER else -1
    ib = _PT_ORDER.index(cls_b) if cls_b in _PT_ORDER else -1
    if ia >= 0 and ib >= 0:
        if ia <= ib:
            row_c, row_pg, row_r, col_c, col_pg, col_r = cls_a, pg_a, route_a, cls_b, pg_b, route_b
        else:
            row_c, row_pg, row_r, col_c, col_pg, col_r = cls_b, pg_b, route_b, cls_a, pg_a, route_a
        row = _PT_ROWS.get(_pt_key(row_c, row_pg, row_r, True))
        ck = _pt_key(col_c, col_pg, col_r, False)
        cell = row[_PT_COLS.index(ck)] if (row and ck in _PT_COLS) else None
        if cell:
            if cell.startswith('S:'):
                s_part, l_part = cell[2:].split('|L:')
                cell = s_part if solid else l_part
            w_cls, w_pg = cell.split(',')
            if w_pg == '*':
                w_pg = row_pg if w_cls == row_c else col_pg
            loser = col_c if w_cls == row_c else row_c
            return {'winner': w_cls, 'win_pg': w_pg, 'loser': loser}

    # Tabloda olmayan çift (örn. 4.1 PG I) — daha düşük PG (daha tehlikeli) kazanır
    if _pg_num(pg_b) < _pg_num(pg_a):
        return {'winner': cls_b, 'win_pg': pg_b, 'loser': cls_a}
    return {'winner': cls_a, 'win_pg': pg_a, 'loser': cls_b}




# ADR 2.2.2.3 — zehirli olmayan gazlar için B.B.B. girişleri (grup → fiziksel durum → UN)
_GAS_NOS = {
    'F': {'compressed': 'UN1954', 'liquefied': 'UN3161', 'refrigerated': 'UN3312'},
    'A': {'compressed': 'UN1956', 'liquefied': 'UN3163', 'refrigerated': 'UN3158'},
    'O': {'compressed': 'UN3156', 'liquefied': 'UN3157', 'refrigerated': 'UN3311'},
}
_GAS_NOS_ALL = {u for g in _GAS_NOS.values() for u in g.values()}
# UN1965 "HİDROKARBON GAZ KARIŞIMI, SIVILAŞTIRILMIŞ" — C1–C4 hidrokarbon gazları
_HC_GAS_CAS = {
    '74-82-8',   # metan
    '74-84-0',   # etan
    '74-85-1',   # etilen
    '74-98-6',   # propan
    '115-07-1',  # propilen
    '106-97-8',  # bütan
    '75-28-5',   # izobütan
    '106-98-9',  # 1-büten
    '107-01-7',  # 2-büten
    '115-11-7',  # izobütilen
    '68476-85-7',  # petrol gazları, sıvılaştırılmış
    '68476-86-8',  # petrol gazları, sıvılaştırılmış, tatlandırılmış
}


def _get_un_entry(cls: str, pg: Optional[str], sub: Optional[str], is_solid: bool,
                  h_set: set = None, form: str = 'liquid',
                  components: 'Optional[List[Component]]' = None,
                  mixture_ph=None) -> Dict:
    """UN numarası ve etiket belirle."""
    h_set = h_set or set()
    if cls == '1':
        return {
            'un': 'UN 0000*', 'label': 'Patlayıcı',
            'note': 'UN numarası maddeye özgü belirlenir; patlayıcı sınıfı tüm yan tehlikeleri ezer',
        }
    if cls == '2.1':
        return {
            'un': 'UN 1954', 'label': 'SIKIŞTIRILMIŞ GAZ, ALEVLENEBİLİR, B.B.B.',
            'note': 'Maddeye özgü UN numarası önceliklidir (ör. UN1978 propan, UN1001 asetilen)',
        }
    if cls == '2.2':
        if 'H270' in h_set:
            return {
                'un': 'UN 3156', 'label': 'SIKIŞTIRILMIŞ GAZ, YÜKSELTGEN, B.B.B.',
                'note': 'ADR Sınıf 2.2 oksitleyici — tüp/tank özel kuralları geçerlidir',
            }
        if 'H281' in h_set:
            return {
                'un': 'UN 3158', 'label': 'GAZ, SOĞUTULMUŞ SIVI, B.B.B.',
                'note': 'Kriyojenik gaz — özel yalıtımlı tank gerektirir (ADR P203)',
            }
        return {
            'un': 'UN 1956', 'label': 'SIKIŞTIRILMIŞ GAZ, B.B.B.',
            'note': 'Maddeye özgü UN numarası önceliklidir (ör. UN1066 azot, UN1046 helyum)',
        }
    if cls == '3':
        if sub == '8':
            return {
                'un': 'UN 2924', 'label': 'ALEVLENEBİLİR SIVI, AŞINDIRICI, B.B.B.',
                'note': (
                    'UN 2924 seçim gerekçesi (ADR 2025): '
                    'Alevlenir sıvı (H224/H225/H226, Sınıf 3) + aşındırıcı (H314, Sınıf 8) kombinasyonu. '
                    'ADR Tablo 2.1.3.10: Sınıf 3 birincil, Sınıf 8 yan tehlike — '
                    'birincil sınıf Sınıf 3 PG ≤ II ile aşındırıcı PG II birlikteliğinde Sınıf 3 önceliği korur. '
                    'ADR 3.1.2.8.1: Ürüne özgü UN girişi yoksa UN 2924 B.B.B. girişi uygulanır. '
                    'Ambalaj grubu birincil sınıfın PG değerinden belirlenir. '
                    'Taşımacılık uzmanı onayı önerilir.'
                ),
            }
        if sub == '6.1':
            return {'un': 'UN 1992', 'label': 'ALEVLENEBİLİR SIVI, ZEHİRLİ, B.B.B.',
                    'note': 'ADR 2025: Sınıf 3 birincil, Sınıf 6.1 yan tehlike'}
        return {'un': 'UN 1993', 'label': 'ALEVLENEBİLİR SIVI, B.B.B.'}
    if cls == '4.1':
        return {
            'un': 'UN 1325', 'label': 'ALEVLENEBİLİR KATI, ORGANİK, B.B.B.',
            'note': 'Maddeye özgü UN önceliklidir; PG I/III uzman onayı gerekir',
        }
    if cls == '4.2':
        if pg == 'I':
            if is_solid:
                return {'un': 'UN 2846', 'label': 'PİROFORİK KATI, ORGANİK, B.B.B.',
                        'note': 'H250: Hava ile temasında kendiliğinden tutuşur — PG I. İnorganik katı ise UN 3200.'}
            return {'un': 'UN 2845', 'label': 'PİROFORİK SIVI, ORGANİK, B.B.B.',
                    'note': 'H250: Hava ile temasında kendiliğinden tutuşur — PG I. İnorganik sıvı ise UN 3194.'}
        # UN 3088 organik (PG II/III); inorganik katı UN 3190 — bileşimden ayırt edilemiyor
        return {'un': 'UN 3088', 'label': 'KENDİLİĞİNDEN ISINAN KATI, ORGANİK, B.B.B.',
                'note': 'İnorganik katı ise UN 3190; sıvı ise UN 3183 (organik) / UN 3186 (inorganik).'}
    if cls == '4.3':
        # ADR Tablo A: UN 3132 (WF2) alevlenir yan tehlikeli katıdır (etiket 4.3 + 4.1); yalnız su ile
        # tepkimeye giren katı UN 2813 (W2). Önceden her katıya UN 3132 veriliyordu.
        if is_solid:
            if 'H228' in h_set:
                return {'un': 'UN 3132', 'label': 'SU İLE TEPKİMEYE GİREN KATI, ALEVLENEBİLİR, B.B.B.'}
            return {'un': 'UN 2813', 'label': 'SU İLE TEPKİMEYE GİREN, KATI, B.B.B.'}
        return {'un': 'UN 3148', 'label': 'SU İLE TEPKİMEYE GİREN SIVI, B.B.B.'}
    if cls == '5.1':
        if sub == '8':
            if is_solid:
                return {
                    'un': 'UN 3085', 'label': 'YÜKSELTGEN KATI, AŞINDIRICI, B.B.B.',
                    'note': 'ADR 2025: Oksitleyici katı (Sınıf 5.1) + aşındırıcı (Sınıf 8) → UN 3085.',
                }
            return {
                'un': 'UN 3098', 'label': 'YÜKSELTGEN SIVI, AŞINDIRICI, B.B.B.',
                'note': (
                    'UN 3098 (OC1) seçim gerekçesi (ADR 2025): '
                    'Oksitleyici sıvı (Sınıf 5.1) + aşındırıcı (H314, Sınıf 8) kombinasyonu. '
                    'ADR §2.1.3.10 Tehlike Öncelik Tablosu: 5.1+8 → UN3098 (kod OC1). '
                    'Taşımacılık uzmanı onayı önerilir.'
                ),
            }
        if is_solid:
            return {'un': 'UN 1479', 'label': 'YÜKSELTGEN KATI, B.B.B.'}
        # UN 3139 PG I/II/III (Tablo A). Önceden PG I'de UN 2912 veriliyordu — o numara
        # radyoaktif madde (LSA-I) kaydıdır.
        return {'un': 'UN 3139', 'label': 'YÜKSELTGEN SIVI, B.B.B.'}
    if cls == '5.2':
        # H241 = Organik peroksit Tip B (SEA Ek-1 Tablo 2.15) → ADR UN 3101 (sıvı) / UN 3102 (katı), etiket 5.2 + 1
        if 'H241' in h_set:
            return ({'un': 'UN 3102', 'label': 'ORGANİK PEROKSİT TİP B, KATI',
                     'labels': ['5.2', '1'], 'note': 'Tip B — ADR Tablo A: etiket 5.2 + 1; sıcaklık kontrolü gerekiyorsa UN 3112'}
                    if is_solid else
                    {'un': 'UN 3101', 'label': 'ORGANİK PEROKSİT TİP B, SIVI',
                     'labels': ['5.2', '1'], 'note': 'Tip B — ADR Tablo A: etiket 5.2 + 1; sıcaklık kontrolü gerekiyorsa UN 3111'})
        if is_solid:
            return {
                'un': 'UN 3106', 'label': 'ORGANİK PEROKSİT TİP D, KATI',
                'note': ('H242 Tip C–F kapsar; Tip D varsayıldı — tip belirlenmeli (katı: C → UN 3104, '
                         'E → UN 3108, F → UN 3110; sıcaklık kontrollüler UN 3113–3120)'),
            }
        return {
            'un': 'UN 3105', 'label': 'ORGANİK PEROKSİT TİP D, SIVI',
            'note': ('H242 Tip C–F kapsar; Tip D varsayıldı — tip belirlenmeli (sıvı: C → UN 3103, '
                     'E → UN 3107, F → UN 3109; sıcaklık kontrollüler UN 3113–3120)'),
        }
    if cls == '6.1':
        if sub == '3':
            # UN 2929 sıvıdır; katı karşılığı UN 2930 (ADR Tablo A). Önceden katıya da 2929 veriliyordu.
            return {'un': 'UN 2930' if is_solid else 'UN 2929',
                    'label': ('ZEHİRLİ KATI, ALEVLENEBİLİR, ORGANİK, B.B.B.' if is_solid
                              else 'ZEHİRLİ SIVI, ALEVLENEBİLİR, ORGANİK, B.B.B.'),
                    'note': 'ADR 2025: Sınıf 6.1 birincil, Sınıf 3 yan tehlike (ADR Tablo 2.1.3.10)'}
        if sub == '8':
            return {
                'un': 'UN 2928' if is_solid else 'UN 2927',
                'label': ('ZEHİRLİ KATI, AŞINDIRICI, ORGANİK, B.B.B.' if is_solid
                          else 'ZEHİRLİ SIVI, AŞINDIRICI, ORGANİK, B.B.B.'),
                'note': 'Organik yapı için UN 2927/2928; inorganik → UN 3289/3290',
            }
        return {
            'un': 'UN 2811' if is_solid else 'UN 2810',
            'label': ('ZEHİRLİ KATI, ORGANİK, B.B.B.' if is_solid
                      else 'ZEHİRLİ SIVI, ORGANİK, B.B.B.'),
            'note': 'UN 2810/2811 organik bileşikler için; inorganik → UN 3287/3288',
        }
    if cls == '8':
        if sub == '5.1':
            if is_solid:
                return {
                    'un': 'UN 3084',
                    'label': 'AŞINDIRICI KATI, YÜKSELTGEN, B.B.B.',
                    'note': 'ADR 2025: Aşındırıcı katı (Sınıf 8) + oksitleyici (Sınıf 5.1) → UN 3084.',
                }
            return {
                'un': 'UN 3093',
                'label': 'AŞINDIRICI SIVI, YÜKSELTGEN, B.B.B.',
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
                'label': ('AŞINDIRICI KATI, ALEVLENEBİLİR, B.B.B.' if is_solid
                          else 'AŞINDIRICI SIVI, ALEVLENEBİLİR, B.B.B.'),
                'note': 'ADR 2025: Sınıf 8 birincil, Sınıf 3 yan tehlike (ADR Tablo 2.1.3.10)',
            }
        if sub == '6.1':
            # Sınıf 8 birincil + 6.1 yan tehlike → UN 2922/2923 (CT1/CT2). Önce 6.1 birincil
            # girişine (UN 2927/2928, TC) gidiyordu — sınıf ile UN numarası çelişiyordu.
            return {
                'un': 'UN 2923' if is_solid else 'UN 2922',
                'label': ('AŞINDIRICI KATI, ZEHİRLİ, B.B.B.' if is_solid
                          else 'AŞINDIRICI SIVI, ZEHİRLİ, B.B.B.'),
                'note': 'ADR 2025: Sınıf 8 birincil, Sınıf 6.1 yan tehlike (ADR Tablo 2.1.3.10)',
            }
        # Sınıf 8, yan tehlike yok — önce CAS bazlı spesifik arama yap
        if components:
            _prod_state = 'solid' if is_solid else ('gas' if form == 'gas' else 'liquid')
            # Tetikleyici (H314 taşıyan) bileşenler arasında en yüksek konsantrasyona sahip olanı al
            trigger8 = [c for c in components if 'H314' in c.h_codes]
            # Adlı giriş (örn. UN1824 sodyum hidroksit çözeltisi) yalnız tek aşındırıcı bileşen varsa;
            # başka aşındırıcı bileşen de varsa karışım B.B.B. girişine gider (ADR 2.1.3.3).
            if len(trigger8) == 1:
                dominant8 = max(trigger8, key=lambda c: c.conc)
                _det = _lookup_by_cas(dominant8.cas, concentration=dominant8.conc,
                                      physical_state=_prod_state)
                if _det:
                    _seed_state = _det.get('physical_state')
                    if not _seed_state or _seed_state == _prod_state:
                        return {
                            'un':     _det['un_no'],
                            'label':  _det.get('name_tr') or _det.get('name', ''),
                            'class':  _det.get('class', '8'),
                            'pg':     _det.get('packing_group', pg or ''),
                            'kemler': _det.get('kemler', '80'),
                            'tunnel': _det.get('tunnel_code', 'E'),
                            'note':   (f"CAS {dominant8.cas} için spesifik ADR girişi: "
                                       f"{_det['un_no']} Sınıf {_det.get('class','8')}, "
                                       f"PG {_det.get('packing_group','')} — "
                                       "ADR §3.1.2.8.1: mevcut spesifik giriş B.B.B. girişine tercih edilir."
                                       + (f" {_det['seed_note']}" if _det.get('seed_note') else '')),
                        }
        _nos = _corr_nos(components, is_solid, mixture_ph)
        if _nos:
            return {'un': _nos, 'label': _CORR_NOS_NAME[_nos],
                    'note': 'ADR 2.1.2: aşındırıcı bileşenlerin asidik/bazik ve inorganik/organik '
                            'yapısına göre en uygun B.B.B. girişi seçildi.'}
        return {
            'un': 'UN 1759' if is_solid else 'UN 1760',
            'label': 'AŞINDIRICI KATI, B.B.B.' if is_solid else 'AŞINDIRICI SIVI, B.B.B.',
            'note': ('Aşındırıcı bileşenlerin asidik/bazik veya inorganik/organik yapısı belirlenemedi — '
                     'genel giriş kullanıldı. Asidik inorganik → UN 3264/3260, asidik organik → 3265/3261, '
                     'bazik inorganik → 3266/3262, bazik organik → 3267/3263.'),
        }
    if cls == '9':
        if is_solid:
            return {
                'un': 'UN 3077',
                'label': 'ÇEVREYE ZARARLI MADDE, KATI, B.B.B.',
            }
        # UN 3082 — ÖH 375 viskozite muafiyeti (ADR 2025 Bölüm 3.3.1)
        _visc = (h_set or set())  # visc bilgisi h_set üzerinden gelemiyor;
        # viscosity değeri dışarıdan geçilecek — bkz. classify() fonksiyonu
        return {
            'un': 'UN 3082',
            'label': 'ÇEVREYE ZARARLI MADDE, SIVI, B.B.B.',
            '_sp375_check': True,  # classify() içinde viskozite kontrolü yapılacak
        }
    return {'un': '—', 'label': 'Bilinmiyor'}


def classify(h_codes: List[str], form: str = 'liquid',
             phys_h_codes: Optional[List[str]] = None,
             viscosity: Optional[float] = None,
             components: 'Optional[List[Component]]' = None,
             acute_tox: Optional[List[Dict]] = None,
             mixture_ph=None,
             gas_type: Optional[str] = None) -> Dict:
    """
    ADR/IMDG/IATA sınıflandırması.

    Args:
        h_codes      : Nihai karışım H kodları (CLP + eco birleşimi) — env_mark bu parametreden türer
        form         : 'liquid' | 'solid' | 'aerosol' | 'gas'
        phys_h_codes : Fiziksel motordan gelen H22x/H228 kodları
        viscosity    : Kinematik viskozite (mm²/s @40°C) — UN 3082 ÖH 375 kontrolü için
        components   : Bileşen listesi — §3.1.3.2 tetikleyici sayımı + baskın madde denetimi için
        acute_tox    : ATEmix sonuçları [{h_code, route, cat_num}] — Sınıf 6.1 PG'si kategoriden
                       kesin belirlenir (ADR 2.2.61.1.7). None ise H kodundan (en kötü durum).
        gas_type     : Gazda 'compressed' | 'liquefied' | 'refrigerated' | 'dissolved' (ADR 2.2.2.1.2)
                       — B.B.B. girişinin seçimi (1… sıkıştırılmış / 2… sıvılaştırılmış / 3… soğutulmuş).

    Returns:
        {not_regulated, road, sea, air, conflict_warning, adr_caution}
    """
    is_solid = (form or 'liquid') in ('solid', 'powder')

    # ── ADR §3.1.3.2: Baskın madde + spesifik Tablo A girişi ─────────────────
    # Tetikleyici bileşenler: en az bir _TRANSPORT_TRIGGER_H kodu taşıyanlar.
    # (H302/H312/H332/H315/H319/H335/H412/H413 → taşımayı tetiklemez.)
    # env_mark her zaman nihai karışım H kodlarından (h_codes parametresi) türer —
    # bileşen-bazlı hesap değil; karışımın Σ eco sınıflandırması belirler.
    _mixture_env_mark = bool(set(h_codes or []) & {'H400', 'H410', 'H411'})

    _comps = components or []
    if _comps:
        triggering = [c for c in _comps if set(c.h_codes) & _TRANSPORT_TRIGGER_H]
        dominant   = max(_comps, key=lambda c: c.conc)

        if len(triggering) == 1 and triggering[0] is dominant:
            # §3.1.3.2: tek tetikleyici bileşen + o bileşen baskın → adlı giriş zorunlu
            _t = triggering[0]
            _prod_state = 'solid' if is_solid else ('gas' if form == 'gas' else 'liquid')
            _details = _lookup_by_cas(_t.cas, concentration=_t.conc, physical_state=_prod_state)
            if _details:
                # §3.1.3.2(c): spesifik girişin fiziksel hali ürünle uyuşmalı.
                # Uyuşmazlık (ör. katı TCCA girişi ama sıvı ürün) → B.N.O.'ya düş.
                _seed_state = _details.get('physical_state')
                if _seed_state and _seed_state != _prod_state:
                    pass  # hal uyumsuzluğu — aşağıya, B.N.O.'ya düş
                else:
                    _road = {
                        'un':     _details['un_no'],
                        'label':  _details.get('name_tr') or _details.get('name', ''),
                        'class':  _details.get('class', ''),
                        'pg':     _details.get('packing_group', ''),
                        'kemler': _details.get('kemler', ''),
                        'tunnel': _details.get('tunnel_code', ''),
                        'note':   (f"ADR §3.1.3.2 — Baskın madde {_t.cas}: "
                                   f"{_details['un_no']} Sınıf {_details.get('class','')}, "
                                   f"PG {_details.get('packing_group','')}."
                                   + (f" {_details['seed_note']}" if _details.get('seed_note') else '')),
                        'env_mark': _mixture_env_mark,
                        'labels': _details.get('labels') or None,
                        'classification_code': _details.get('classification_code'),
                        'regulation': 'ADR 2025',
                    }
                    _sea = {**_road, 'regulation': 'IMDG Kod (Değişiklik 42-24)'}
                    _lb = _details.get('labels') or []
                    if str(_road['class']) == '2' and _lb:
                        # IMDG/IATA'da gaz bölümü sınıf yerine yazılır (örn. 2.3), ek etiketler yan tehlike
                        _sea.update({'class': _lb[0], 'sub_class': '+'.join(_lb[1:]) or None})
                    elif len(_lb) > 1:
                        _road['sub_class'] = '+'.join(_lb[1:])
                        _sea['sub_class'] = _road['sub_class']
                    _air = {**_sea, 'regulation': 'IATA-DGR 2026'}
                    return {
                        'not_regulated': False,
                        'road': _road,
                        'sea':  _sea,
                        'air':  _air,
                        'env_mark': _mixture_env_mark,
                        'conflict_warning': None,
                        'adr_caution': None,
                    }
        # len(triggering) == 0 → H-kodu yoluna düş (not_regulated veya eco → Sınıf 9)
        # len(triggering) >= 2 → B.N.O. yolu; CAS araması uygulanmaz

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
    # Aynı sınıf için en tehlikeli PG'yi (en küçük sayı) sakla. Sınıf 6.1 ayrıca yol bazında
    # tutulur (2.1.3.10 tablosunda oral/dermal/soluma satırları farklıdır).
    class_map: Dict[str, Dict] = {}
    tox_routes = _tox61_routes(h_set, acute_tox, form)
    for h in all_h:
        adr = H_TO_ADR.get(h)
        if not adr or adr['class'] == '6.1':
            continue
        cls = adr['class']
        existing = class_map.get(cls)
        new_num = _pg_num(adr['pg'])
        if not existing or new_num < existing['pg_num']:
            class_map[cls] = {'pg': adr['pg'], 'pg_num': new_num}

    # Sınıf 8 PG — ADR 2.2.8.1.6.3 hesaplama yöntemi (karışım testi yoksa). Bileşen alt
    # kategorisi bilinmiyorsa (bileşen listesi yok) H314 → PG I en kötü durum kalır.
    corr_note = None
    if '8' in class_map and 'H314' not in h_set:
        corr_note = ('Sınıf 8 PG III: metallere aşındırıcı (H290) — ADR 2.2.8.1.5.3 (c)(ii) (çelik/alüminyum '
                     'aşınma hızı > 6,25 mm/yıl, UN Test C.1).')
    elif '8' in class_map and _comps:
        _pg8 = corrosive_mixture_pg(_comps)
        if _pg8:
            class_map['8'] = {'pg': _pg8, 'pg_num': _pg_num(_pg8)}
            corr_note = (f'Sınıf 8 PG {_pg8}: ADR 2.2.8.1.6.3 hesaplama yöntemi (bileşenlerin cilt aşındırma '
                         'alt kategorisi 1A/1B/1C → PG I/II/III). Karışım test edilmişse test sonucu esastır.')
        else:
            corr_note = ('H314 bileşen toplamından değil (örn. pH kuralından) geliyor; ADR 2.2.8.1.6.3 hesabı '
                         'Sınıf 8 vermedi. PG I en kötü durum varsayıldı — OECD 404/435/431 testi ile doğrulayın.')

    route61 = None
    if tox_routes:
        # En tehlikeli PG; eşitlikte soluma > dermal > oral (6.1 lehine en ağır satır)
        route61 = min(tox_routes, key=lambda r: (_pg_num(tox_routes[r]['pg']), 'IDO'.index(r)))
        class_map['6.1'] = {'pg': tox_routes[route61]['pg'], 'pg_num': _pg_num(tox_routes[route61]['pg'])}

    detected = [{'class': cls, 'pg': v['pg'], 'route': route61 if cls == '6.1' else None}
                for cls, v in class_map.items()]

    if not detected and form == 'aerosol':
        detected = [{'class': '2.2', 'pg': None, 'route': None}]   # her aerosol UN 1950'dir
    if not detected:
        return {
            'not_regulated': True,
            'road': None, 'sea': None, 'air': None,
            'note': 'Bu madde/karışım tehlikeli madde olarak sınıflandırılmamıştır.',
            'conflict_warning': None, 'adr_caution': None,
        }

    # ── Adım 2: Birincil sınıf — ADR 2.1.3.5.3 öncelik listesi + 2.1.3.10 tablosu ─
    primary = dict(detected[0])
    for item in detected[1:]:
        res = resolve_conflict(primary['class'], primary['pg'], item['class'], item['pg'],
                               route_a=primary.get('route'), route_b=item.get('route'),
                               solid=is_solid)
        w_route = primary.get('route') if res['winner'] == primary['class'] else item.get('route')
        primary = {'class': res['winner'], 'pg': res['win_pg'], 'route': w_route}

    # ADR 2.1.3.5.3 (h) istisnası: Sınıf 8 kriterini karşılayan, toz/sis solunumu PG I olan ve
    # oral/dermal zehirliliği yalnızca PG III veya daha az olan maddeler Sınıf 8'e girer.
    if (primary['class'] == '6.1' and route61 == 'I' and tox_routes['I'].get('dust')
            and primary['pg'] == 'I' and '8' in class_map
            and all(_pg_num(tox_routes[r]['pg']) >= 3 for r in ('O', 'D') if r in tox_routes)):
        primary = {'class': '8', 'pg': class_map['8']['pg'], 'route': None}

    # ── Adım 3: Yan tehlikeleri belirle ──────────────────────────────────────
    # Sınıf 9 (çevre için tehlikeli) hiçbir zaman yan tehlike olarak yazılmaz — çevre için
    # tehlikeli madde işareti ile gösterilir (ADR 5.2.1.8 / 5.4.1.1.18).
    # Gazda 2.2 (yanıcı olmayan, zehirli olmayan gaz) yalnızca gaz yanıcı/zehirli değilse etikettir;
    # alevlenir (2.1) veya zehirli (2.3) gazda H280 basınç özelliği ayrıca 2.2 etiketi getirmez
    # (ADR 2.2.2.1.5 / Tablo A, örn. UN1954 etiket 2.1).
    _gas_primary = str(primary['class']) in ('2.1', '2.3')
    subs = sorted(
        [d for d in detected if d['class'] not in (primary['class'], '9')
         and not (_gas_primary and d['class'] == '2.2')],
        key=lambda d: _pg_num(d['pg'])
    )
    sub_class = subs[0]['class'] if subs else None

    # ── Adım 4: UN ve etiket ──────────────────────────────────────────────────
    un_entry = _get_un_entry(primary['class'], primary['pg'], sub_class, is_solid, h_set, form,
                             components=_comps, mixture_ph=mixture_ph)
    if corr_note and '8' in (primary['class'], sub_class):
        un_entry['note'] = ((un_entry.get('note') or '') + ' ' + corr_note).strip()

    # UN 3082 — ADR 3.3.1 Özel Hüküm 375 viskozite muafiyeti
    if un_entry.get('_sp375_check') and primary['class'] == '9':
        if viscosity is not None and viscosity >= 2500:
            un_entry['note'] = (
                f'ÖH 375 (ADR 3.3.1): Kinematik viskozite {viscosity:.0f} mm²/s ≥ 2500 mm²/s — '
                'UN 3082 ambalaj hükümleri (P501, LP01) uygulanmaz; '
                'muafiyet koşulları tam karşılanıyorsa taşıma belgesi düzenlenmeyebilir. '
                'Taşımacılık uzmanı onayı önerilir.'
            )
        elif viscosity is not None:
            un_entry['note'] = (
                f'Kinematik viskozite {viscosity:.0f} mm²/s < 2500 mm²/s — '
                'ÖH 375 muafiyeti uygulanmaz; UN 3082 tam hükümler geçerlidir.'
            )
        else:
            un_entry['note'] = (
                'ÖH 375 (ADR 3.3.1): Viskozite girilmedi — '
                '≥ 2500 mm²/s ise ambalaj muafiyeti uygulanabilir. Kontrol edin.'
            )
        del un_entry['_sp375_check']

    # Aerosol formu — her zaman UN 1950 (ADR 2025 Tablo A Sınıf 2)
    # Sınıflandırma kodu hazard setine göre seçilir (ADR 2025 Tablo A).
    # CMR (H340/H350) ADR anlamında "toksik" değildir — LC50 kriterleri (Div.2.3) geçerli.
    if form == 'aerosol':
        # ADR 2.2.2.1.6: aerosol grubu içeriğin tehlike özelliklerine göre atanır —
        # T: içerik Sınıf 6.1 kriterini karşılar; C: Sınıf 8; O: yükseltgen; F: alevlenebilir.
        # Etiket ve tünel kodları ADR 2025 Tablo A UN 1950 satırlarından birebir alınmıştır.
        _is_flam = bool(h_set & {'H222', 'H223'})
        _is_tox  = bool(tox_routes)
        _is_ox   = bool(h_set & {'H270', 'H271', 'H272'})
        _is_corr = 'H314' in h_set
        _aero_code = '5' + ('T' if _is_tox else '') + ('F' if _is_flam else '')                      + ('O' if (_is_ox and not _is_flam) else '') + ('C' if _is_corr else '')
        if _aero_code == '5':
            _aero_code = '5A'
        if _aero_code not in ('5A', '5C', '5CO', '5F', '5FC', '5O', '5T', '5TC', '5TF',
                              '5TFC', '5TO', '5TOC'):
            _aero_code = _aero_code.replace('O', '')   # Tablo A'da F ile O birlikte yok
        _AERO_LABELS = {
            '5A': ['2.2'], '5C': ['2.2', '8'], '5CO': ['2.2', '5.1', '8'],
            '5F': ['2.1'], '5FC': ['2.1', '8'], '5O': ['2.2', '5.1'],
            '5T': ['2.2', '6.1'], '5TC': ['2.2', '6.1', '8'], '5TF': ['2.1', '6.1'],
            '5TFC': ['2.1', '6.1', '8'], '5TO': ['2.2', '5.1', '6.1'],
            '5TOC': ['2.2', '5.1', '6.1', '8'],
        }
        _AERO_TUNNEL = {
            '5A': 'E', '5C': 'E', '5CO': 'E', '5F': 'D', '5FC': 'D', '5O': 'E',
            '5T': 'D', '5TC': 'D', '5TF': 'D', '5TFC': 'D', '5TO': 'D', '5TOC': 'D',
        }
        _AERO_NAMES = {
            '5A':   ('AEROSOLS, asphyxiant',                  'AEROSOLLER, asfiksant'),
            '5C':   ('AEROSOLS, corrosive',                   'AEROSOLLER, aşındırıcı'),
            '5CO':  ('AEROSOLS, corrosive, oxidizing',        'AEROSOLLER, aşındırıcı, yükseltgen'),
            '5F':   ('AEROSOLS, flammable',                   'AEROSOLLER, alevlenebilir'),
            '5FC':  ('AEROSOLS, flammable, corrosive',        'AEROSOLLER, alevlenebilir, aşındırıcı'),
            '5O':   ('AEROSOLS, oxidizing',                   'AEROSOLLER, yükseltgen'),
            '5T':   ('AEROSOLS, toxic',                       'AEROSOLLER, zehirli'),
            '5TC':  ('AEROSOLS, toxic, corrosive',            'AEROSOLLER, zehirli, aşındırıcı'),
            '5TF':  ('AEROSOLS, toxic, flammable',            'AEROSOLLER, zehirli, alevlenebilir'),
            '5TFC': ('AEROSOLS, toxic, flammable, corrosive', 'AEROSOLLER, zehirli, alevlenebilir, aşındırıcı'),
            '5TO':  ('AEROSOLS, toxic, oxidizing',            'AEROSOLLER, zehirli, yükseltgen'),
            '5TOC': ('AEROSOLS, toxic, oxidizing, corrosive', 'AEROSOLLER, zehirli, yükseltgen, aşındırıcı'),
        }
        _al = _AERO_LABELS[_aero_code]
        primary = {'class': _al[0], 'pg': ''}
        subs = [{'class': c, 'pg': ''} for c in _al[1:]]
        sub_class = '+'.join(_al[1:]) or None
        _en_name, _tr_name = _AERO_NAMES.get(_aero_code, ('AEROSOLS', 'AEROSOLLER'))
        un_entry = {
            'un':    'UN 1950',
            'label': _tr_name,
            'classification_code': _aero_code,
            'labels':   _al,
            'tunnel':   _AERO_TUNNEL[_aero_code],
            'name':     _en_name,
            'name_tr':  _tr_name,
            'pg':       '',
            'note': (f'UN 1950 {_aero_code} — ADR 2025 Tablo A / 2.2.2.1.6 (grup içeriğin tehlike '
                     'özelliklerinden seçildi). İçeriği Sınıf 6.1 veya 8 PG I kriterini karşılayan '
                     'aerosoller taşımaya kabul edilmez (2.2.2.1.6).'),
        }

    # Gaz — ADR 2.2.2.1.5: zehirli gaz = 1 sa LC50 ≤ 5000 ml/m3 (CLP 4 sa LC50 × 2 → H330/H331
    # sınırıyla örtüşür) VEYA aşındırıcılığı nedeniyle zehirlilik kriterini karşılayan gaz
    # ("aşındırıcı gazlar zehirli olarak sınıflandırılır", ikincil aşındırıcı riskli) → kod T…,
    # etiket 2.3; yanıcı (2.1), yükseltgen (5.1), aşındırıcı (8) ek etiket.
    # Maddeye özgü giriş (örn. UN1050, UN1005) yukarıda önceliklidir.
    if form == 'gas' and (h_set & {'H330', 'H331'} or 'H314' in h_set):
        _g_flam = bool(h_set & {'H220', 'H221'})
        _g_ox   = 'H270' in h_set
        _g_corr = 'H314' in h_set
        _key = (_g_flam, _g_ox, _g_corr)
        _compressed = {(False, False, False): 'UN1955', (False, False, True): 'UN3304',
                       (True, False, False): 'UN1953', (False, True, False): 'UN3303',
                       (True, False, True): 'UN3305', (False, True, True): 'UN3306'}
        _liquefied  = {(False, False, False): 'UN3162', (False, False, True): 'UN3308',
                       (True, False, False): 'UN3160', (False, True, False): 'UN3307',
                       (True, False, True): 'UN3309', (False, True, True): 'UN3310'}
        _un_c = _compressed.get(_key, 'UN1955')
        _un_l = _liquefied.get(_key, 'UN3162')
        _tox_liq = gas_type in ('liquefied', 'refrigerated')
        _un_sel = _un_l if _tox_liq else _un_c
        try:
            from app.services.transport_adr_service import get_adr_details as _gad
            _gd = _gad(_un_sel, '')
        except Exception:
            _gd = {}
        _labels = ['2.3'] + (['2.1'] if _g_flam else []) + (['5.1'] if _g_ox else []) + (['8'] if _g_corr else [])
        primary = {'class': '2.3', 'pg': ''}
        subs = [{'class': c, 'pg': ''} for c in _labels[1:]]
        sub_class = '+'.join(_labels[1:]) or None
        _why = ('soluma yoluyla zehirli gaz (H330/H331)' if h_set & {'H330', 'H331'}
                else 'aşındırıcı gaz (H314) — ADR 2.2.2.1.5 gereği zehirli gaz sayılır')
        un_entry = {
            'un':    _un_sel[:2] + ' ' + _un_sel[2:],
            'label': _gd.get('name_tr') or 'SIKIŞTIRILMIŞ GAZ, ZEHİRLİ, B.B.B.',
            'classification_code': _gd.get('classification_code', ''),
            'tunnel': _gd.get('tunnel_code'),
            'labels': _labels,
            'pg':    '',
            'note':  (f'ADR 2.2.2.1.5: {_why} → Sınıf 2, etiket {" + ".join(_labels)}. '
                      + (f'Sıvılaştırılmış gaz → {_un_l[:2]} {_un_l[2:]}. ' if _tox_liq else
                         f'Sıkıştırılmış gaz{"" if gas_type else " varsayıldı (gaz türü seçilmedi)"}; '
                         f'sıvılaştırılmış gaz ise {_un_l[:2]} {_un_l[2:]}. ') +
                      'Maddeye özgü UN numarası önceliklidir (örn. UN1050 hidrojen klorür, susuz; '
                      'UN1005 amonyak, susuz).'),
        }

    # Gaz (zehirli olmayan) — ADR 2.2.2.1.2/2.2.2.3: B.B.B. girişi gazın fiziksel durumuna göre
    # seçilir: 1… sıkıştırılmış, 2… sıvılaştırılmış, 3… soğutulmuş sıvılaştırılmış.
    # Yalnız hidrokarbon gazlardan oluşan sıvılaştırılmış yanıcı karışım → UN1965 (2F grubunda
    # UN3161'den önce gelir). Çözünmüş gazlar için B.B.B. girişi yoktur (örn. UN1001 asetilen).
    if form == 'gas' and str(un_entry.get('un', '')).replace(' ', '') in _GAS_NOS_ALL:
        _grp = ('F' if primary['class'] == '2.1' else
                'O' if (primary['class'] == '2.2' and 'H270' in h_set) else
                'A' if primary['class'] == '2.2' else None)
        _gt = 'refrigerated' if 'H281' in h_set else (gas_type or '')
        if _grp:
            _un_g = _GAS_NOS[_grp].get(_gt) or _GAS_NOS[_grp]['compressed']
            if (_grp == 'F' and _gt == 'liquefied' and _comps
                    and all(c.cas in _HC_GAS_CAS for c in _comps if c.conc > 0)):
                _un_g = 'UN1965'
            try:
                from app.services.transport_adr_service import get_adr_details as _gad2
                _gd2 = _gad2(_un_g, '') or {}
            except Exception:
                _gd2 = {}
            _gt_tr = {'compressed': 'sıkıştırılmış', 'liquefied': 'sıvılaştırılmış',
                      'refrigerated': 'soğutulmuş sıvılaştırılmış', 'dissolved': 'çözünmüş'}.get(_gt)
            if not _gt_tr:
                _gnote = 'Gaz türü seçilmedi — sıkıştırılmış gaz varsayıldı. '
            elif _gt == 'dissolved':
                _gnote = ('Çözünmüş gazlar için B.B.B. girişi yoktur — maddeye özgü UN numarası '
                          'kullanılmalıdır (örn. UN1001 asetilen, çözünmüş). ')
            else:
                _gnote = f'Gaz türü: {_gt_tr} (ADR 2.2.2.1.2). '
            un_entry = {
                **un_entry,
                'un': _un_g[:2] + ' ' + _un_g[2:],
                'label': _gd2.get('name_tr') or un_entry.get('label'),
                'classification_code': _gd2.get('classification_code') or un_entry.get('classification_code'),
                'tunnel': _gd2.get('tunnel_code') or un_entry.get('tunnel'),
                # ADR Tablo A sütun 5 — oksitleyici gaz (1O/2O/3O) etiketi 2.2 + 5.1
                'labels': _gd2.get('labels') or un_entry.get('labels'),
                'pg': '',
                'note': (_gnote + 'Maddeye özgü UN numarası önceliklidir (örn. UN1978 propan, '
                         'UN1075 LPG, UN1066 azot).'),
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
                f"Parlama noktası ≤ 60°C ise ADR 2025 kapsamında Sınıf 3 değerlendirilmelidir."
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
                f"ADR Sınıf 6.1 PG III için LD50 ≤ 300 mg/kg gerekir (ADR 2.2.61.1.7). "
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
                "ADR 2025: Aspirasyon tehlikesi bağımsız bir ADR sınıfı oluşturmaz — "
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
                    f"ADR 2025: STOT SE kodları doğrudan ADR Sınıf 6.1'e eşlenmez. "
                    f"LD50/LC50 verisi mevcutsa ADR 2.2.61.1.7 kapsamında Sınıf 6.1 "
                    f"uygulanabilirliği taşımacılık uzmanı tarafından değerlendirilmelidir."
                ),
            }

    # Yan tehlike etiketi
    all_sub_labels = ', '.join(f"Sınıf {s['class']}" for s in subs)
    sub_label = f' (Yan Tehlike: {all_sub_labels})' if all_sub_labels else ''

    # ADR/RID'de gazların sınıfı "2"dir; 2.1/2.2/2.3 etiket numarasıdır (2.2.2.1). IMDG ve
    # IATA'da ise "2.1/2.2/2.3" bölüm (division) olarak sınıf yerine yazılır.
    _is_gas_cls = str(primary['class']).startswith('2.')
    _labels_out = un_entry.get('labels') or (
        [primary['class']] + [s['class'] for s in subs] if _is_gas_cls else None)
    entry = {
        'un':                  un_entry['un'],
        'class':               primary['class'],
        'labels':              _labels_out,
        'class_label':         CLASS_LABELS.get(primary['class'], primary['class']) + sub_label,
        # Spesifik UN girişinin Tablo A PG'si, H-kodundan türetilen en-kötü-durum PG'sine üstündür
        # (örn. H314 → PG I varsayılır ama UN1824'ün Tablo A'da PG I'i yoktur)
        'pg':                  un_entry.get('pg') or primary['pg'],
        'label':               un_entry['label'],
        # Gaz B.B.B. girişinin Tablo A yan etiketi (örn. UN 3156 → 5.1) IMDG/IATA'da yan tehlike olarak yazılır
        'sub_class':           sub_class or ('+'.join(_labels_out[1:]) if _labels_out
                                             and len(_labels_out) > 1 else None),
        'note':                un_entry.get('note'),
        'env_mark':            env_mark,
        'conflict_warning':    conflict_warning,
        'adr_caution':         adr_caution,
        'classification_code': un_entry.get('classification_code'),  # aerosol için hazarda göre seçildi
        'tunnel':              un_entry.get('tunnel'),
    }

    _road = {**entry, 'regulation': 'ADR 2025'}
    if _is_gas_cls:
        _road.update({'class': '2', 'sub_class': None,
                      'class_label': 'Gazlar — etiket ' + ' + '.join(_labels_out or [primary['class']])})
    return {
        'not_regulated':    False,
        'road': _road,
        'sea':  {**entry, 'regulation': 'IMDG Kod (Değişiklik 42-24)'},
        'air':  {**entry, 'regulation': 'IATA-DGR 2026'},
        'env_mark':         env_mark,
        'conflict_warning': conflict_warning,
        'adr_caution':      adr_caution,
    }
