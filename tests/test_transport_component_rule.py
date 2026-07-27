"""
ADR §3.1.3.2 bileşen sayım ve baskın madde kuralı testleri.

Senaryolar:
1. DIPOL 306 benzeri — NaCl (sınıflandırılmamış) + Na dihidrat (H410) → eco H kodu
   ile UN 3077 Sınıf 9 çıkmalı (CAS araması değil, H kodu yolu).
2. DIPOL 305 benzeri — TCCA %90 baskın, NaCl %8 → UN 2468 Sınıf 5.1 (CAS araması).
3. Nötr karışım — sadece H319'lu bileşen → tetikleyici yok → not_regulated.
4. Fiziksel hal uyumsuzluğu — TCCA kaydı solid, ürün liquid → B.N.O.'ya düş.
5. Konsantrasyon parse hatası → ValueError (fail-closed).
"""
import pytest
from app.services.transport_engine import classify, build_transport_components, Component


# ── Yardımcı ──────────────────────────────────────────────────────────────────

def _cls(h_codes, form='solid', comps=None):
    """classify() için kısa sarmalayıcı."""
    return classify(h_codes=h_codes, form=form, components=comps or [])


# ── Senaryo 1: DIPOL 306 — eco H kodu → UN 3077 ──────────────────────────────

def test_dipol306_eco_to_un3077():
    """
    Na dihidrat (CAS 51580-86-0) seed'de yok → CAS araması boş döner.
    NaCl (7647-14-5) H kodu yok → tetikleyici sayılmaz.
    Sayım = 0 → H kodu yoluna düşer.
    Nihai H kodlarında H411 var (eco motor verisi) → Sınıf 9 → UN 3077.
    """
    comps = [
        Component(cas='51580-86-0', conc=92.0, h_codes=['H302', 'H400', 'H411']),
        Component(cas='7647-14-5',  conc=8.0,  h_codes=[]),
    ]
    # h_codes = nihai karışım H kodları (eco dahil)
    result = _cls(h_codes=['H302', 'H411'], form='solid', comps=comps)
    assert not result.get('not_regulated'), 'Sınıf 9 — regulated olmalı'
    road = result.get('road') or {}
    assert road.get('class') == '9', f"Beklenen Sınıf 9, gelen: {road.get('class')}"
    un = road.get('un', '')
    assert 'UN3077' in un or '3077' in un, f"Beklenen UN3077, gelen: {un}"


# ── Senaryo 2: TCCA baskın — CAS araması → UN 2468 ───────────────────────────

def test_tcca_dominant_cas_lookup():
    """
    TCCA (87-90-1) %90, NaCl %8 — tek tetikleyici + baskın → UN2468 Sınıf 5.1.
    """
    comps = [
        Component(cas='87-90-1',   conc=90.0, h_codes=['H272', 'H302', 'H410']),
        Component(cas='7647-14-5', conc=8.0,  h_codes=[]),
    ]
    result = _cls(h_codes=['H272', 'H302', 'H410'], form='solid', comps=comps)
    assert not result.get('not_regulated'), 'UN2468 — regulated olmalı'
    road = result.get('road') or {}
    un = road.get('un', '')
    assert 'UN2468' in un or '2468' in un, f"Beklenen UN2468, gelen: {un}"
    assert road.get('class') == '5.1', f"Beklenen Sınıf 5.1, gelen: {road.get('class')}"


# ── Senaryo 3: Nötr karışım — tetikleyici yok → not_regulated ────────────────

def test_neutral_mixture_not_regulated():
    """
    H319 tek başına ADR tetiklemez → sayım 0 → tetikleyici yok → not_regulated.
    Karışımın nihai H kodlarında da eco kodu yok.
    """
    comps = [
        Component(cas='1234-56-7', conc=90.0, h_codes=['H319']),
        Component(cas='7647-14-5', conc=10.0, h_codes=[]),
    ]
    result = _cls(h_codes=['H319'], form='liquid', comps=comps)
    assert result.get('not_regulated'), 'Nötr karışım → not_regulated bekleniyor'


# ── Senaryo 4: Fiziksel hal uyumsuzluğu → B.N.O.'ya düş ─────────────────────

def test_physical_state_mismatch_falls_through():
    """
    TCCA seed'de physical_state='solid'; ürün form='liquid' ise CAS araması geri
    çevrilmeli, H kodu B.N.O. yoluna düşmeli.
    TCCA H272 → Sınıf 5.1; liquid + oksitleyici → UN3139 veya uygun B.N.O. çıkar.
    Her durumda UN2468 (KURU) dönemez.
    """
    comps = [
        Component(cas='87-90-1',   conc=10.0, h_codes=['H272', 'H302', 'H410']),
        Component(cas='7647-14-5', conc=90.0, h_codes=[]),
    ]
    # %10 TCCA → tek tetikleyici ama baskın değil (dominant = %90 NaCl) → CAS araması zaten atlanır
    # Baskın kontrolünü test etmek için dominant olanın bileşen olduğu ancak
    # form uyumsuzluğu durumunu ayrıca test edelim:
    comps2 = [
        Component(cas='87-90-1',   conc=95.0, h_codes=['H272', 'H302', 'H410']),
        Component(cas='7647-14-5', conc=5.0,  h_codes=[]),
    ]
    result = _cls(h_codes=['H272', 'H302', 'H410'], form='liquid', comps=comps2)
    road = result.get('road') or {}
    un = road.get('un', '')
    assert 'UN2468' not in un, f"Sıvı ürün için UN2468 (KURU) dönemez, gelen: {un}"


# ── Senaryo 5: Konsantrasyon parse hatası → ValueError ───────────────────────

def test_concentration_parse_error_raises():
    """
    Maskelenmiş string gibi parse edilemeyen konsantrasyon → ValueError.
    Sessiz 0.0 fallback kesinlikle olmamalı.
    """
    raw = [
        {'cas_no': '87-90-1', 'conc': 'GIZLI', 'h_codes': ['H272']},
    ]
    with pytest.raises(ValueError, match='parse edilemedi'):
        build_transport_components(raw)


def test_missing_concentration_raises():
    """Konsantrasyon alanı hiç yoksa da ValueError."""
    raw = [
        {'cas_no': '87-90-1', 'h_codes': ['H272']},
    ]
    with pytest.raises(ValueError, match='konsantrasyon'):
        build_transport_components(raw)
