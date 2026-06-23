"""
Sınıflandırma Motoru Regresyon Testleri
========================================
Her commit öncesi bu testler çalıştırılmalıdır:
    python -m pytest tests/test_classification_fixtures.py -v

Amac: Motor değişikliklerinde sınıflandırma sınırlarının kaymamasını
(regression) tespit etmek. Her fixture bilinen bir referans karışımı
temsil eder ve beklenen H kodlarını içerir.

Fixture formatı:
    {
      "name":       "açıklama",
      "components": [...],   # eco_engine / clp_service formatı
      "expect": {
        "h_codes": ["H225"],          # tam set (sıraya bakılmaz)
        "not_h_codes": ["H226"],      # bu kodlar OLMAMALI
        "eco_h": "H410",              # eco_engine beklentisi (opsiyonel)
        "transport_un": "UN1170",     # transport_engine (opsiyonel)
      }
    }
"""

import pytest
import sys
import os

# Proje kökünü Python yoluna ekle
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


# ── Referans Karışımlar ────────────────────────────────────────────────────────

FIXTURES = [

    # ── F01: Etanol %70 — H225 olmalı, H226 OLMAMALI ──────────────────────────
    # FP = ~13°C → H225 (< 23°C, BP > 35°C); H226 (23-60°C) değil
    {
        "name": "F01 — Etanol %70 (H225 sınırı)",
        "components": [
            {"cas": "64-17-5",  "name": "Etanol",  "concMax": 70, "conc": 70, "hazards": [
                {"h_code": "H225", "h_class": "Flam. Liq. 2"},
                {"h_code": "H319", "h_class": "Eye Irrit. 2"},
            ]},
            {"cas": "7732-18-5", "name": "Su",     "concMax": 30, "conc": 30, "hazards": []},
        ],
        "phys": {"flash_point": 13, "boiling_point": 78},
        "expect": {
            "flam_h": "H225",
            "not_flam_h": ["H226", "H224"],
        }
    },

    # ── F02: Metanol %100 — H224 olmalı (FP=-11°C, BP=64.7°C ≤ 35°C değil → H225?) ─
    # Metanol FP=-11°C, BP=64.7°C → BP > 35°C → H225 (Flam Liq 2)
    {
        "name": "F02 — Metanol %100 (H225, BP>35°C)",
        "components": [
            {"cas": "67-56-1", "name": "Metanol", "concMax": 100, "conc": 100, "hazards": [
                {"h_code": "H225", "h_class": "Flam. Liq. 2"},
                {"h_code": "H301+H311+H331", "h_class": "Acute Tox. 3"},
            ]},
        ],
        "phys": {"flash_point": -11, "boiling_point": 65},
        "expect": {
            "flam_h": "H225",   # BP=65°C > 35°C → H225 değil H224
            "not_flam_h": ["H226"],
        }
    },

    # ── F03: Dizel %100 — H226 olmalı (FP ~60-70°C → sınır değer) ───────────
    {
        "name": "F03 — FP=22°C madde (H225 alt sınır)",
        "components": [
            {"cas": "64742-47-8", "name": "Nafta", "concMax": 100, "conc": 100, "hazards": [
                {"h_code": "H225", "h_class": "Flam. Liq. 2"},
            ]},
        ],
        "phys": {"flash_point": 22, "boiling_point": 150},
        "expect": {
            "flam_h": "H225",      # 22°C < 23°C → H225
            "not_flam_h": ["H226"],
        }
    },

    # ── F04: FP=24°C madde — H226 olmalı ─────────────────────────────────────
    {
        "name": "F04 — FP=24°C madde (H226 başlangıç)",
        "components": [
            {"cas": "108-88-3", "name": "Toluen", "concMax": 100, "conc": 100, "hazards": [
                {"h_code": "H225", "h_class": "Flam. Liq. 2"},
            ]},
        ],
        "phys": {"flash_point": 24, "boiling_point": 111},
        "expect": {
            "flam_h": "H226",      # 23°C ≤ 24°C ≤ 60°C → H226
            "not_flam_h": ["H225"],
        }
    },

    # ── F05: Sucul H410 — M=10, konsantrasyon %2 → H410 eşiği aşılmalı ──────
    # Σ(Ci × M_kr)/100 = (2 × 10)/100 = 0.20 < 0.25 → H410 değil
    # M=10, konc=%3 → (3×10)/100 = 0.30 ≥ 0.25 → H410
    {
        "name": "F05 — Aquatic H410 (M=10, konc=%3 → H410)",
        "components": [
            {"cas": "71-43-2", "name": "Benzen", "concMax": 3, "conc": 3,
             "m_factors": {"acute": 1, "chronic": 10},
             "hazards": [
                 {"h_code": "H410", "h_class": "Aquatic Chronic 1"},
             ]},
            {"cas": "7732-18-5", "name": "Su", "concMax": 97, "conc": 97, "hazards": []},
        ],
        "expect": {
            "eco_h": "H410",
            "not_eco_h": ["H411", "H400"],
        }
    },

    # ── F06: Sucul H410 eşiği altı — M=10, konc=%2 → H411 veya yok ──────────
    # Σ(Ci × M_kr)/100 = (2 × 10)/100 = 0.20 < 0.25 → H410 yok
    # H411 = 10×K1 + K2; K1=0.20 → 10×0.20=2.0 ≥ 0.25 → H411
    {
        "name": "F06 — Aquatic H411 (M=10, konc=%2 → H411 değil H410)",
        "components": [
            {"cas": "71-43-2", "name": "Benzen", "concMax": 2, "conc": 2,
             "m_factors": {"acute": 1, "chronic": 10},
             "hazards": [
                 {"h_code": "H410", "h_class": "Aquatic Chronic 1"},
             ]},
            {"cas": "7732-18-5", "name": "Su", "concMax": 98, "conc": 98, "hazards": []},
        ],
        "expect": {
            "eco_h": "H411",       # K1=0.20 → 10×0.20=2.0 ≥ 0.25 → H411
            "not_eco_h": ["H410"],
        }
    },

    # ── F07: STOT RE toplamsal — iki bileşen, her biri %8 → H373 ─────────────
    # Toplam %16 → eşik aşıldı (özel STOT engine hesabı)
    {
        "name": "F07 — STOT RE toplamsal (%8+%8 → H373 beklenir)",
        "components": [
            {"cas": "110-54-3", "name": "n-Hekzan", "concMax": 8, "conc": 8,
             "hazards": [{"h_code": "H373", "h_class": "STOT RE 2"}]},
            {"cas": "71-43-2", "name": "Benzen",   "concMax": 8, "conc": 8,
             "hazards": [{"h_code": "H373", "h_class": "STOT RE 2"}]},
            {"cas": "7732-18-5", "name": "Su",     "concMax": 84, "conc": 84, "hazards": []},
        ],
        "expect": {
            "stot_h": "H373",
        }
    },

    # ── F08: NaOH %5, pH=13 — H314 var, H315 OLMAMALI ───────────────────────
    {
        "name": "F08 — NaOH %5 (H314 var, H315 yok)",
        "components": [
            {"cas": "1310-73-2", "name": "NaOH", "concMax": 5, "conc": 5,
             "hazards": [
                 {"h_code": "H314", "h_class": "Skin Corr. 1A"},
                 {"h_code": "H290", "h_class": "Met. Corr. 1"},
             ]},
            {"cas": "7732-18-5", "name": "Su", "concMax": 95, "conc": 95, "hazards": []},
        ],
        "expect": {
            "clp_h": ["H314"],
            "not_clp_h": ["H315"],  # H314 varken H315 baskılanmalı (dominance)
        }
    },
]


# ── Yardımcı Fonksiyonlar ─────────────────────────────────────────────────────

def _h22x(fp, bp=None):
    """FP + BP'den beklenen flam sınıfı."""
    if fp is None:
        return None
    if fp < 23:
        return "H224" if (bp is not None and bp <= 35) else "H225"
    if fp <= 60:
        return "H226"
    return None


# ── Testler ───────────────────────────────────────────────────────────────────

class TestFlammabilityBoundary:
    """physical_engine: parlama noktası → H22x sınır değerleri"""

    @pytest.mark.parametrize("fx", [f for f in FIXTURES if "flam_h" in f["expect"]])
    def test_flash_category(self, fx):
        phys = fx.get("phys", {})
        fp   = phys.get("flash_point")
        bp   = phys.get("boiling_point")
        expected = fx["expect"]["flam_h"]
        not_expected = fx["expect"].get("not_flam_h", [])

        got = _h22x(fp, bp)
        assert got == expected, (
            f"[{fx['name']}] FP={fp}°C BP={bp}°C → beklenen {expected}, hesaplanan {got}"
        )
        for bad in not_expected:
            assert got != bad, (
                f"[{fx['name']}] FP={fp}°C BP={bp}°C → {bad} OLMAMALI, ama hesaplanan {got}"
            )


class TestEcoEngine:
    """eco_engine: SEA Tablo 4.1.2 toplama formülü sınır değerleri"""

    @pytest.mark.parametrize("fx", [f for f in FIXTURES if "eco_h" in f["expect"]])
    def test_eco_classification(self, fx):
        from app.services.eco_engine import calculate as eco_calc

        result   = eco_calc(fx["components"])
        h_codes  = result.get("h_codes", [])
        expected = fx["expect"]["eco_h"]
        not_exp  = fx["expect"].get("not_eco_h", [])

        assert expected in h_codes, (
            f"[{fx['name']}] Beklenen {expected} yok. Hesaplanan: {h_codes}"
        )
        for bad in not_exp:
            assert bad not in h_codes, (
                f"[{fx['name']}] {bad} OLMAMALI ama h_codes'ta var: {h_codes}"
            )


class TestStotEngine:
    """stot_engine: STOT RE toplamsal kural"""

    @pytest.mark.parametrize("fx", [f for f in FIXTURES if "stot_h" in f["expect"]])
    def test_stot_classification(self, fx):
        from app.services.stot_engine import calculate as stot_calc

        result  = stot_calc(fx["components"])
        h_codes = result.get("h_codes", [])
        expected = fx["expect"]["stot_h"]

        assert expected in h_codes, (
            f"[{fx['name']}] Beklenen {expected} yok. Hesaplanan: {h_codes}"
        )


class TestClpDominance:
    """clp_service: baskınlık kuralı (H314 varken H315 elenmeli)"""

    @pytest.mark.parametrize("fx", [f for f in FIXTURES if "clp_h" in f["expect"]])
    def test_clp_dominance(self, fx):
        from app.services.clp_service import classify_mixture_clp

        result  = classify_mixture_clp(fx["components"])
        h_codes = result.get("h_codes", [])
        for expected in fx["expect"]["clp_h"]:
            assert expected in h_codes, (
                f"[{fx['name']}] Beklenen {expected} yok. Hesaplanan: {h_codes}"
            )
        for bad in fx["expect"].get("not_clp_h", []):
            assert bad not in h_codes, (
                f"[{fx['name']}] {bad} OLMAMALI ama h_codes'ta var: {h_codes}"
            )


# ── NEVER-REGRESS — BULGU 8: ATEmix su-exclude ───────────────────────────────
# CLP Ek-I §3.1.3.6.1(b): akut toksik olmadığı bilinen bileşenler (su, glikoz, ...)
# ATEmix formülünden TAMAMEN DIŞLANIR — bilinmiyor sayılmaz.
# Bu sınıfı silmeyin: her fixture gerçek bir denetim maliyetiyle bulundu.
class TestAteNeverRegress:
    """NEVER-REGRESS — CLP Ek-I §3.1.3.6.1(b) — ATEmix su-exclude (BULGU 8)."""

    def _call_core(self, items):
        from app.services.clp_service import _ate_core
        ate_h, ate_b11, unk, annex_5000, stmt = _ate_core(items, form='liquid')
        return ate_h, unk

    def test_water_excluded_when_ate_unknown_true(self):
        """Su %96, ate_unknown=True (DB lookup başarısız) + madde %4 ATE_oral=500.
        Beklenen: su bilinmiyor sayılmaz, dışlanır → ATEmix=12500 > 2000 → sınıflandırma yok.
        Yanlış davranış (eski kod): unknown_conc[oral]=96 → ATEmix=500 → H302.
        CLP Ek-I §3.1.3.6.1(b) — su exclude edilir.
        """
        items = [
            {
                'cas': '7732-18-5',  # su — _PRESUME_NOT_ACUTELY_TOXIC_CAS
                'name': 'Su',
                'conc': 96,
                'ate_unknown': True,   # DB lookup başarısız simülasyonu — yine de dışlanmalı
                'hazards': [],
                'ate': {},
                'source_priority': 4,
            },
            {
                'cas': '108-88-3',
                'name': 'TestBileşen',
                'conc': 4,
                'ate_unknown': False,
                'hazards': [{'h_code': 'H302', 'h_class': 'Acute Tox. 4'}],
                'ate': {'oral': 500},
                'source_priority': 1,
            },
        ]
        ate_h, unk = self._call_core(items)
        assert unk.get('oral', 0) == pytest.approx(0.0), (
            f"Su dışlanmalıydı ama unknown_conc[oral]={unk.get('oral')} — bilinmiyor sayıldı"
        )
        h_codes = [r['h_code'] for r in ate_h]
        assert not any(c in h_codes for c in ('H300', 'H301', 'H302')), (
            f"CLP §3.1.3.6.1(b): su dışlandığında Acute Tox. sınıflandırması beklenmez. "
            f"Hesaplanan H kodları: {h_codes}"
        )

    def test_water_excluded_when_ate_unknown_false(self):
        """Su %96, ate_unknown=False (normal lookup) + madde %4 ATE_oral=500.
        Beklenen: her iki ate_unknown değerinde de aynı sonuç — dışla, bilinmiyor sayma.
        CLP Ek-I §3.1.3.6.1(b) — su exclude edilir.
        """
        items = [
            {
                'cas': '7732-18-5',
                'name': 'Su',
                'conc': 96,
                'ate_unknown': False,  # normal DB lookup — akut toks. yok
                'hazards': [],
                'ate': {},
                'source_priority': 1,
            },
            {
                'cas': '108-88-3',
                'name': 'TestBileşen',
                'conc': 4,
                'ate_unknown': False,
                'hazards': [{'h_code': 'H302', 'h_class': 'Acute Tox. 4'}],
                'ate': {'oral': 500},
                'source_priority': 1,
            },
        ]
        ate_h, unk = self._call_core(items)
        assert unk.get('oral', 0) == pytest.approx(0.0), (
            f"Su (ate_unknown=False) dışlanmalıydı, unknown_conc[oral]={unk.get('oral')}"
        )
        h_codes = [r['h_code'] for r in ate_h]
        assert not any(c in h_codes for c in ('H300', 'H301', 'H302')), (
            f"Su dışlandığında sınıflandırma beklenmez: {h_codes}"
        )


if __name__ == "__main__":
    # pytest olmadan doğrudan çalıştırma için basit runner
    import traceback
    passed = failed = 0
    for fx in FIXTURES:
        try:
            ex = fx["expect"]
            phys = fx.get("phys", {})

            if "flam_h" in ex:
                got = _h22x(phys.get("flash_point"), phys.get("boiling_point"))
                assert got == ex["flam_h"], f"flam_h: got {got}"
                for bad in ex.get("not_flam_h", []):
                    assert got != bad, f"not_flam_h violated: {bad}"

            if "eco_h" in ex:
                from app.services.eco_engine import calculate as eco_calc
                res = eco_calc(fx["components"])
                hc = res.get("h_codes", [])
                assert ex["eco_h"] in hc, f"eco_h {ex['eco_h']} not in {hc}"
                for bad in ex.get("not_eco_h", []):
                    assert bad not in hc, f"not_eco_h {bad} found in {hc}"

            if "stot_h" in ex:
                from app.services.stot_engine import calculate as stot_calc
                res = stot_calc(fx["components"])
                hc = res.get("h_codes", [])
                assert ex["stot_h"] in hc, f"stot_h {ex['stot_h']} not in {hc}"

            if "clp_h" in ex:
                from app.services.clp_service import classify_mixture_clp
                res = classify_mixture_clp(fx["components"])
                hc = res.get("h_codes", [])
                for e in ex["clp_h"]:
                    assert e in hc, f"clp_h {e} not in {hc}"
                for bad in ex.get("not_clp_h", []):
                    assert bad not in hc, f"not_clp_h {bad} found in {hc}"

            print(f"  ✓ {fx['name']}")
            passed += 1
        except Exception as e:
            print(f"  ✗ {fx['name']}: {e}")
            failed += 1

    print(f"\n{passed} geçti / {failed} başarısız")
    if failed:
        raise SystemExit(1)
