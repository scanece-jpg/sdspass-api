"""
Önlem ifadesi (P) öneri dereceleri — SEA Etiketleme ve Ambalajlama Rehberi, Bölüm 7.3
(sds-knowledge/tr/sea-etiketleme-ambalajlama-rehberi.pdf s. 53–134), elle doğrulanmış.
Rehberde tablosu olmayanlar (H200, H229, H420) SEA Ek-1 tablolarından alınmıştır.

Yasal çerçeve — SEA Yönetmeliği:
  Md. 24  P ifadeleri Ek-1 tablolarından, H kodları ve kullanım dikkate alınarak seçilir.
  Md. 30(1) Açıkça fazla/gereksiz olanlar etikete konmaz.
  Md. 30(2) Bertaraf ifadesi (P501) halka arz edilen ürünlerde etikette yer alır.
  Md. 30(3) Zararın ciddiyeti gerektirmedikçe etikette altıdan fazla P ifadesi olmaz.

Dereceler (her giriş: (P kodu, halka satış, endüstriyel/profesyonel)):
  K  kesinlikle önerilir       → etikette
  O  önerilir                  → yer varsa etikette (6'ya kadar)
  C  koşullu (özel söndürücü, panzehir, uçuculuk …) → GBF'de değerlendirilir
  CK / CO  soluma koşuluna bağlı (uçucu, gaz, sprey, solunabilir toz): koşul sağlanırsa K / O;
     gaz/aerosol/toz ürünlerde sağlanmış sayılır (INHAL), aksi hâlde C
  S  GBF'ye eklenmesi önerilir → etikette değil
  X  opsiyonel
  -  bu kullanıcı grubu için uygulanmaz
"""
from typing import Dict, List, Tuple

# Soluma koşuluna bağlı ifadeler. Rehber: P260/P261/P284 "çok uçucu, gaz, sprey veya solunabilir
# toz" ise → gaz/aerosol ve katı/toz ürünlerde koşul sağlanmış sayılır (katıda toz oluşumu).
# P403+P233 ise "ürün uçucu ve zararlı atmosfer yaratması olasıysa" → yalnız gaz/aerosol.
INHAL = {'P260', 'P261', 'P284'}
VOLATILE = {'P403+P233'}

# Rehberdeki eski kodlar → sistemin ürettiği güncel CLP kodları
ALIAS = {
    'P281': 'P280', 'P322': 'P321', 'P304+P341': 'P304+P340', 'P307+P311': 'P308+P311',
    'P309+P311': 'P308+P311', 'P362': 'P362+P364', 'P361': 'P361+P364',
}

_P501 = ('P501', 'K', 'C')          # halka: tehlikeli atıksa K (Md.30(2)); prof: özel bertaraf varsa
_CMR1 = [('P201', 'K', 'K'), ('P202', 'X', 'X'), ('P280', 'K', 'K'), ('P308+P313', 'K', 'K'),
         ('P405', 'K', 'X'), _P501]
_CMR2 = [('P201', 'O', 'O'), ('P202', 'X', 'X'), ('P280', 'K', 'K'), ('P308+P313', 'O', 'O'),
         ('P405', 'K', 'X'), _P501]
_EXPL = [('P210', 'K', 'K'), ('P230', 'C', 'C'), ('P240', 'C', 'C'), ('P250', 'C', 'C'),
         ('P280', 'X', 'K'), ('P234', 'K', 'K'), ('P370+P380', 'K', 'K'), ('P372', 'K', 'K'),
         ('P373', 'O', 'O'), ('P401', 'S', 'S'), ('P501', 'S', 'S')]
_FLAM_LIQ = [('P240', 'S', 'S'), ('P241', 'S', 'S'), ('P242', 'S', 'S'), ('P243', 'S', 'S'),
             ('P280', 'X', 'X'), ('P303+P361+P353', 'X', 'X'), ('P370+P378', 'C', 'C'), _P501]
_SELF_REACT = [('P210', 'K', 'K'), ('P220', 'O', 'O'), ('P234', 'K', 'K'), ('P280', 'K', 'K'),
               ('P370+P378', 'C', 'C'), ('P403+P235', 'K', 'K'), ('P411', 'C', 'C'),
               ('P420', 'C', 'C'), _P501]
# SEA Ek-1 Tablo 2.13.2 / 2.14.2 (2020 değişikliği): tedbir ifadeleri P210, P220, P280 — P221 kaldırıldı
# (2013 tarihli Rehber hâlâ P221'i gösterir; yönetmelik tablosu esas alınır)
_OXID = [('P210', 'K', 'K'), ('P220', 'K', 'K'), ('P280', 'O', 'O'),
         ('P370+P378', 'C', 'C'), _P501]
_AQ = [('P273', 'O', 'O'), ('P391', 'O', 'O'), _P501]

GUIDANCE: Dict[str, List[Tuple[str, str, str]]] = {
    # ── Fiziksel ─────────────────────────────────────────────────────────────
    'H200': [('P201', 'K', 'K'), ('P250', 'K', 'K'), ('P280', 'K', 'K'), ('P370+P380', 'K', 'K'),
             ('P372', 'K', 'K'), ('P373', 'K', 'K'), ('P401', 'S', 'S'), ('P501', 'S', 'S')],
    'H201': _EXPL, 'H202': _EXPL, 'H203': _EXPL, 'H205': _EXPL,
    'H204': _EXPL + [('P374', 'C', 'C')],
    'H220': [('P210', 'K', 'K'), ('P377', 'K', 'K'), ('P381', 'O', 'O'), ('P403', 'K', 'K')],
    'H221': [('P210', 'K', 'K'), ('P377', 'K', 'K'), ('P381', 'O', 'O'), ('P403', 'K', 'K')],
    'H222': [('P210', 'K', 'K'), ('P211', 'K', 'K'), ('P251', 'K', 'K'), ('P410+P412', 'K', 'K')],
    'H223': [('P210', 'K', 'K'), ('P211', 'K', 'K'), ('P251', 'K', 'K'), ('P410+P412', 'K', 'K')],
    'H229': [('P210', 'K', 'K'), ('P251', 'K', 'K'), ('P410+P412', 'K', 'K')],
    'H270': [('P220', 'K', 'K'), ('P244', 'K', 'K'), ('P370+P376', 'S', 'S'), ('P403', 'K', 'K')],
    # SEA Ek-1 Tablo 2.5 / Ek-4: P410+P403 yalnız UN RTDG P200 taşınabilir gaz silindirlerinde yazılmayabilir.
    # Ambalaj türü (silindir / tank) programda bilinmediğinden her zaman yazılır (kullanıcı kararı 2026-10-08).
    'H280': [('P410+P403', 'K', 'K')],
    'H281': [('P282', 'C', 'C'), ('P336+P315', 'K', 'K'), ('P403', 'X', 'X')],
    'H224': [('P210', 'K', 'K'), ('P233', 'K', 'K'), ('P403+P235', 'K', 'K')] + _FLAM_LIQ,
    'H225': [('P210', 'K', 'K'), ('P233', 'O', 'O'), ('P403+P235', 'C', 'C')] + _FLAM_LIQ,
    'H226': [('P210', 'K', 'K'), ('P233', 'X', 'X'), ('P403+P235', 'C', 'C')] + _FLAM_LIQ,
    'H228': [('P210', 'K', 'K'), ('P240', 'S', 'S'), ('P241', 'S', 'S'), ('P280', 'X', 'X'),
             ('P370+P378', 'C', 'C')],
    'H240': [('P210', 'K', 'K'), ('P220', 'O', 'O'), ('P234', 'C', 'C'), ('P280', 'K', 'K'),
             ('P370+P380', 'K', 'K'), ('P403+P235', 'K', 'K'), ('P411', 'C', 'C'), ('P420', 'C', 'C'),
             ('P501', 'S', 'S')],
    'H241': _SELF_REACT + [('P370+P380+P375', 'K', 'K')],
    'H242': _SELF_REACT,
    'H250': [('P210', 'K', 'K'), ('P222', 'X', 'X'), ('P280', 'K', 'K'), ('P231', 'O', 'O'),
             ('P302+P334', 'K', 'K'), ('P335+P334', 'K', 'K'), ('P370+P378', 'C', 'C'), ('P422', 'O', 'O')],
    'H251': [('P235+P410', 'K', 'O'), ('P280', 'X', 'X'), ('P407', 'K', 'K'), ('P413', 'C', 'C'),
             ('P420', 'C', 'C')],
    'H252': [('P235+P410', 'K', 'O'), ('P280', 'X', 'X'), ('P407', 'K', 'K'), ('P413', 'C', 'C'),
             ('P420', 'C', 'C')],
    'H260': [('P223', 'X', 'X'), ('P231+P232', 'C', 'C'), ('P280', 'O', 'O'), ('P335+P334', 'K', 'K'),
             ('P370+P378', 'C', 'C'), ('P402+P404', 'O', 'O'), _P501],
    'H261': [('P231+P232', 'C', 'C'), ('P280', 'O', 'O'), ('P370+P378', 'C', 'C'),
             ('P402+P404', 'O', 'O'), _P501],
    'H271': _OXID + [('P283', 'S', 'S'), ('P306+P360', 'O', 'O'), ('P371+P380+P375', 'K', 'K')],
    'H272': _OXID,
    'H290': [('P234', 'O', 'X'), ('P390', 'O', 'O'), ('P406', 'X', 'X')],
    # ── Akut toksisite ───────────────────────────────────────────────────────
    'H300': [('P264', 'K', 'O'), ('P270', 'K', 'X'), ('P301+P310', 'K', 'K'), ('P321', 'C', 'C'),
             ('P330', 'K', 'O'), ('P405', 'K', 'X'), _P501],
    'H301': [('P264', 'K', 'O'), ('P270', 'O', 'X'), ('P301+P310', 'K', 'K'), ('P321', 'C', 'C'),
             ('P330', 'O', 'X'), ('P405', 'K', 'X'), _P501],
    'H302': [('P264', 'O', 'X'), ('P270', 'O', 'X'), ('P301+P312', 'X', 'X'), ('P330', 'X', 'X'), _P501],
    'H310': [('P262', 'X', 'X'), ('P264', 'K', 'X'), ('P270', 'K', 'X'), ('P280', 'K', 'K'),
             ('P302+P350', 'O', 'S'), ('P310', 'K', 'K'), ('P321', 'C', 'C'), ('P363', 'O', 'O'),
             ('P405', 'K', 'X'), _P501],
    'H311': [('P280', 'K', 'K'), ('P302+P352', 'O', 'S'), ('P312', 'O', 'O'), ('P321', 'C', 'C'),
             ('P363', 'O', 'O'), ('P405', 'K', 'X'), _P501],
    'H312': [('P280', 'O', 'O'), ('P302+P352', 'X', 'X'), ('P312', 'O', 'O'), ('P321', 'C', 'C'),
             ('P363', 'X', 'X'), _P501],
    'H330': [('P260', 'CK', 'CK'), ('P271', 'K', 'X'), ('P284', 'CO', 'CO'), ('P304+P340', 'K', 'K'),
             ('P310', 'K', 'K'), ('P320', 'C', 'C'), ('P403+P233', 'CK', 'CK'), ('P405', 'K', 'X'), _P501],
    'H331': [('P261', 'CO', 'CO'), ('P271', 'K', 'X'), ('P304+P340', 'O', 'O'), ('P311', 'O', 'O'),
             ('P321', 'C', 'C'), ('P403+P233', 'CK', 'CK'), ('P405', 'K', 'X'), _P501],
    'H332': [('P261', 'CO', 'CO'), ('P271', 'K', 'X'), ('P304+P340', 'X', 'X'), ('P312', 'O', 'O')],
    # ── Cilt / göz / hassaslaştırıcı ─────────────────────────────────────────
    'H314': [('P260', 'CK', 'CK'), ('P264', 'X', 'X'), ('P280', 'K', 'K'), ('P301+P330+P331', 'K', 'O'),
             ('P303+P361+P353', 'K', 'K'), ('P363', 'O', 'S'), ('P304+P340', 'X', 'X'), ('P310', 'K', 'K'),
             ('P321', 'C', 'C'), ('P305+P351+P338', 'K', 'K'), ('P405', 'K', 'X'), _P501],
    'H315': [('P264', 'X', 'X'), ('P280', 'O', 'O'), ('P302+P352', 'X', 'S'), ('P321', 'C', 'C'),
             ('P332+P313', 'X', 'X'), ('P362+P364', 'X', 'S')],
    'H318': [('P280', 'K', 'K'), ('P305+P351+P338', 'K', 'K'), ('P310', 'K', 'K')],
    'H319': [('P264', 'X', 'X'), ('P280', 'O', 'O'), ('P305+P351+P338', 'O', 'S'), ('P337+P313', 'O', 'O')],
    'H334': [('P260', 'CK', 'CK'), ('P261', 'CK', 'CK'), ('P284', 'CK', 'CK'), ('P304+P340', 'K', 'K'), ('P342+P311', 'K', 'K'), _P501],
    'H317': [('P260', 'CO', 'CO'), ('P261', 'CO', 'CO'), ('P272', '-', 'X'), ('P280', 'K', 'K'), ('P302+P352', 'O', 'S'),
             ('P333+P313', 'O', 'O'), ('P321', 'C', 'C'), ('P363', 'O', 'O'), ('P362+P364', 'O', 'O'), _P501],
    # ── CMR ──────────────────────────────────────────────────────────────────
    'H340': _CMR1, 'H350': _CMR1, 'H350i': _CMR1, 'H360': _CMR1, 'H360F': _CMR1, 'H360D': _CMR1,
    'H360FD': _CMR1, 'H360Fd': _CMR1, 'H360Df': _CMR1,
    'H341': _CMR2, 'H351': _CMR2, 'H361': _CMR2, 'H361f': _CMR2, 'H361d': _CMR2, 'H361fd': _CMR2,
    'H362': [('P201', 'K', 'K'), ('P260', 'CK', 'CK'), ('P263', 'K', 'K'), ('P264', 'X', 'X'),
             ('P270', 'O', 'X'), ('P308+P313', 'O', 'O')],
    # ── STOT / aspirasyon ────────────────────────────────────────────────────
    'H370': [('P260', 'CK', 'CK'), ('P264', 'X', 'X'), ('P270', 'O', 'X'), ('P308+P311', 'K', 'K'),
             ('P321', 'C', 'C'), ('P405', 'K', 'X'), _P501],
    'H371': [('P260', 'CK', 'CK'), ('P264', 'X', 'X'), ('P270', 'O', 'X'), ('P308+P311', 'O', 'O'),
             ('P405', 'K', 'X'), _P501],
    'H335': [('P260', 'CO', 'CO'), ('P261', 'CO', 'CO'), ('P271', 'K', 'X'), ('P304+P340', 'X', 'X'), ('P312', 'O', 'O'),
             ('P403+P233', 'CO', 'CO'), ('P405', 'K', 'X'), _P501],
    'H336': [('P260', 'CO', 'CO'), ('P261', 'CO', 'CO'), ('P271', 'K', 'X'), ('P304+P340', 'X', 'X'), ('P312', 'O', 'O'),
             ('P403+P233', 'CO', 'CO'), ('P405', 'K', 'X'), _P501],
    'H372': [('P260', 'CK', 'CK'), ('P264', 'X', 'X'), ('P270', 'O', 'X'), ('P314', 'O', 'O'), _P501],
    'H373': [('P260', 'CK', 'CK'), ('P314', 'O', 'O'), _P501],
    'H304': [('P301+P310', 'K', 'K'), ('P331', 'K', 'K'), ('P405', 'K', 'X'), _P501],
    # ── Çevre ────────────────────────────────────────────────────────────────
    'H400': _AQ, 'H410': _AQ, 'H411': _AQ,
    'H412': [('P273', 'O', 'O'), _P501], 'H413': [('P273', 'O', 'O'), _P501],
    'H420': [('P502', 'O', 'O')],
}

# Md. 30(1) — biri varken diğeri gereksiz (rehberdeki "…zaten varsa kullanmayın/yoksa" notları)
REDUNDANT: Dict[str, List[str]] = {
    'P260': ['P261'], 'P284': ['P285'], 'P201': ['P202'], 'P234': ['P406'],
    'P301+P310': ['P301+P312'],
    'P301+P330+P331': ['P330'],
    'P303+P361+P353': ['P302+P352', 'P361+P364'],
    'P305+P351+P338': ['P337+P313'],
    'P310': ['P311', 'P312', 'P313', 'P314'], 'P311': ['P312', 'P313', 'P314'],
    'P308+P311': ['P308+P313', 'P312'], 'P333+P313': ['P332+P313'], 'P280': ['P262'],
    'P410+P403': ['P403'],
}

RANK = {'K': 5, 'O': 4, 'C': 3, 'S': 2, 'X': 1, '-': 0}


def _canon(p: str) -> str:
    return ALIAS.get(p, p)


def levels(h_codes: List[str], usage: str = 'industrial', form: str = 'liquid') -> Dict[str, str]:
    """Her P kodu için, sınıflandırmadaki H kodları arasında en güçlü öneri derecesi."""
    col = 1 if usage == 'consumer' else 2
    inhal_ok = form in ('gas', 'aerosol', 'powder', 'solid')
    volatile_ok = form in ('gas', 'aerosol')
    out: Dict[str, str] = {}
    for h in h_codes:
        rows = GUIDANCE.get(h) or GUIDANCE.get(h[:4]) or []
        for row in rows:
            p, lvl = row[0], row[col]
            if lvl in ('CK', 'CO'):
                met = (p in INHAL and inhal_ok) or (p in VOLATILE and volatile_ok)
                lvl = lvl[1] if met else 'C'
            if RANK[lvl] > RANK.get(out.get(p, '-'), 0):
                out[p] = lvl
    return out


def known(h_codes: List[str]) -> bool:
    return any(GUIDANCE.get(h) or GUIDANCE.get(h[:4]) for h in h_codes)


def select_label(all_p: List[str], h_codes: List[str], usage: str, form: str,
                 priority: Dict[str, int], max_codes: int = 6) -> Dict:
    lv = levels(h_codes, usage, form)
    cand = {}
    for p in all_p:
        l = lv.get(_canon(p)) or lv.get(p)
        if l:
            cand[p] = l
    if usage == 'consumer' and 'P501' in all_p:
        cand['P501'] = 'K'                                   # Md. 30(2)
    # Rehber 7.3.1 Genel önlem ifadeleri (halka satılan ürün): P101 sağlık zararı sınıflı her üründe,
    # P102 yalnız çevre zararı sınıflı olanlar dışında her üründe "kesinlikle önerilir"; P103 opsiyonel.
    if usage == 'consumer':
        _hs = [str(h)[:4].upper() for h in h_codes if h]
        if 'P101' in all_p and any(h.startswith('H3') for h in _hs):
            cand['P101'] = 'K'
        if 'P102' in all_p and _hs and not all(h.startswith('H4') for h in _hs):
            cand['P102'] = 'K'
    by_prio = lambda ps: sorted(ps, key=lambda p: priority.get(p, 5), reverse=True)
    _gen = [p for p in ('P101', 'P102') if cand.get(p) == 'K']    # genel ifadeler başta
    must = _gen + by_prio([p for p, l in cand.items() if l == 'K' and p not in _gen])
    opt = by_prio([p for p, l in cand.items() if l == 'O'])

    # Kesinlikle önerilen bir ifadenin kapsadıkları sıradan bağımsız düşer (örn. H220 P403 + H280 P410+P403)
    chosen, dropped = [], {q for p in must for q in REDUNDANT.get(_canon(p), [])}
    for p in must + opt:
        if p in dropped or p in chosen:
            continue
        if cand[p] == 'O' and len(chosen) >= max_codes:
            continue
        chosen.append(p)
        dropped.update(REDUNDANT.get(_canon(p), []))
    # SEA Md.17(1)(f): etikette ilgili önlem ifadeleri bulunur — Rehber'de bu kullanım için kesinlikle önerilen/önerilen
    # ifade yoksa (örn. endüstriyel H302: hepsi opsiyonel) etiket boş kalmaz; opsiyonel olanlar öncelik sırasıyla alınır.
    _opt_used = False
    if not chosen:
        for p in by_prio([p for p, l in cand.items() if l == 'X']):
            if p in dropped or p in chosen or len(chosen) >= max_codes:
                continue
            chosen.append(p)
            dropped.update(REDUNDANT.get(_canon(p), []))
            _opt_used = True
    n_must = len([p for p in chosen if cand[p] == 'K'])
    note = (f'SEA Md. 24/30 + SEA Etiketleme Rehberi Bölüm 7.3: {n_must} kesinlikle önerilen'
            + (' (kesinlikle önerilen/önerilen ifade olmadığı için opsiyonel ifadeler — SEA Md.17(1)(f))' if _opt_used else '')
            + (f', {len(chosen) - n_must} ' + ('opsiyonel' if _opt_used else 'önerilen') if len(chosen) > n_must else '')
            + f' ({"halka arz" if usage == "consumer" else "endüstriyel/profesyonel"}).')
    if len(chosen) > max_codes:
        note += ' Kesinlikle önerilenler altıyı aştığı için hepsi etikette (Md. 30(3) istisnası).'
    return {'selected': chosen, 'levels': {p: cand.get(p) or lv.get(_canon(p), '') for p in all_p},
            'excluded': [p for p in all_p if p not in chosen], 'limit_exceeded': len(chosen) > max_codes,
            'mandatory': [], 'forced_by_h': [p for p in chosen if cand[p] == 'K'], 'note': note}


def sds_groups(all_p: List[str], h_codes: List[str], usage: str, form: str, label: List[str]) -> Dict:
    """Bölüm 2/16 gruplaması — etiketle aynı kaynaktan: etiketteki her kod 'mandatory' ya da 'evaluate'."""
    lv = levels(h_codes, usage, form)
    groups = {'mandatory': [], 'evaluate': [], 'optional': []}
    for p in all_p:
        l = 'K' if (usage == 'consumer' and p == 'P501') else (lv.get(_canon(p)) or lv.get(p) or '')
        if l == 'K':
            groups['mandatory'].append(p)
        elif l in ('O', 'C', 'S') or p in label:
            groups['evaluate'].append(p)
        else:
            groups['optional'].append(p)
    return groups
