"""
Review Kuralları Unit Test Matrisi
====================================
Her kural için 2 senaryo: pozitif (bulgu çıkmamalı) + negatif (bulgu çıkmalı).

Çalıştırma:
    python -m pytest tests/test_review_rules.py -v

Bu testler API'yi çağırmaz — sadece SDS metnini oluşturur ve
sistem promptunun istediği bilgilerin metinde olup olmadığını doğrular.
Böylece deploy'a gerek kalmadan kurallarda regresyon yakalanır.

Asıl Claude API testi için test_review_e2e.py (ayrı, pahalı, elle çalıştırılır).
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.review_endpoint import _build_sds_text, _format_ate_b11

# ─────────────────────────────────────────────────────────────────────────────
# YARDIMCI: minimal sds_data fabrikası
# ─────────────────────────────────────────────────────────────────────────────

def _base_sds(overrides: dict | None = None) -> dict:
    """Tüm zorunlu alanları olan minimal geçerli sds_data döndürür."""
    data = {
        "product":  {"name": "Test Karışımı", "code": "TST-001", "form": "liquid", "usage": "industrial"},
        "supplier": {
            "name": "DİPOL KİMYA",
            "address": "Ankara",
            "phone": "+90 312 000 0000",
            "email": "info@dipol.com",
            "emergency_tel": "114",
        },
        "clp": {
            "all_h_codes": [],
            "h_codes": [],
            "signal_word": "danger",
            "pictograms": [],
        },
        "euh": {"codes": []},
        "p_codes": {
            "label": {"selected": ["P260", "P280"]},
            "sds": {"mandatory": ["P260"], "evaluate": []},
        },
        "eco": {"h_codes": []},
        "ppe": {"eye": "Koruyucu gözlük", "skin": "Nitril eldiven", "resp": "", "hand": ""},
        "transport": {"road": {"un": "1760", "class": "8", "pg": "II", "shipping_name": "KOROZIF SIVI"}},
        "revision": {"date": "12.07.2026", "no": "85", "notes": "Test revizyonu"},
        "phys_props": {
            "flash_point": None,
            "boiling_point": "130",
            "density": "1.05",
            "ph": "1.2",
            "vapor_pressure": None,
            "viscosity": None,
            "solubility": "tamamen miscible",
            "auto_ignition": None,
            "log_kow": None,
            "melting_point": None,
        },
        "ate_mix_details": {},
        "components": [],
    }
    if overrides:
        for k, v in overrides.items():
            if isinstance(v, dict) and isinstance(data.get(k), dict):
                data[k].update(v)
            else:
                data[k] = v
    return data


def _build(sds: dict, h_codes: list, components: list | None = None) -> str:
    """_build_sds_text sarmalayıcısı."""
    return _build_sds_text(
        sds_data=sds,
        h_codes=h_codes,
        phys_props=sds.get("phys_props", {}),
        components=components or sds.get("components", []),
    )


# ─────────────────────────────────────────────────────────────────────────────
# KURAL 1 — ATEmix hesabı
# ─────────────────────────────────────────────────────────────────────────────

class TestKural1_ATEmix:
    """
    H302 (Oral Akut Kat.4) varsa B11'de ATEmix satırı beklenir.
    Yoksa denetçi bunu hata olarak işaretlemelidir.
    """

    def test_pozitif__atEmix_mevcut_bulgu_cikmamali(self):
        """ATEmix hesabı B11'de varsa → denetçi bu konuyu hata olarak yazmamalı."""
        sds = _base_sds({
            "ate_mix_details": {
                "oral": {
                    "ateMix": 1250.0,
                    "resultCode": "H302",
                    "unknownPct": 0,
                }
            }
        })
        text = _build(sds, ["H302"])
        # Metin ATEmix satırını içeriyor mu?
        assert "ATEmix" in text, "ATEmix hesabı SDS metninde bulunmalı"
        assert "1250" in text or "1250.0" in text, "ATEmix değeri metinde görünmeli"

    def test_negatif__atEmix_yok_metin_eksik(self):
        """H302 var ama ate_mix_details boş → B11'de ATEmix satırı yok."""
        sds = _base_sds({"ate_mix_details": {}})
        text = _build(sds, ["H302"])
        # Metin ATEmix içermiyor → denetçi bunu yakalamalı
        # (Biz burada sadece metin üretimini doğruluyoruz;
        #  denetçinin bunu hata yazacağını e2e testi doğrular)
        assert "ATEmix" not in text, "ate_mix_details boşken ATEmix satırı üretilmemeli"


# ─────────────────────────────────────────────────────────────────────────────
# KURAL 2 — CLP Dominance (H314 → H318 etiketten çıkar)
# ─────────────────────────────────────────────────────────────────────────────

class TestKural2_Dominance:
    """
    H314 varsa H318 etiket listesinde (B2.2) yer almaz — bu normaldir.
    Sistem prompt bunu açıkça belirtir; denetçi bunu hata saymamalı.
    """

    def test_pozitif__h314_var_h318_etikette_yok_normal(self):
        """
        B2.1'de H314+H318 var, B2.2 etikette yalnızca H314 var.
        Metin bunu açıkça Not ile açıklıyor → denetçi hata yazmamalı.
        """
        sds = _base_sds({
            "clp": {
                "all_h_codes": ["H314", "H318"],
                "h_codes": ["H314"],          # B2.2 — dominance uygulandı
                "signal_word": "danger",
                "pictograms": ["GHS05"],
            }
        })
        text = _build(sds, ["H314"])
        assert "H314" in text
        assert "dominance" in text.lower() or "H314 zaten H318" in text, \
            "Dominance notu SDS metninde bulunmalı"

    def test_negatif__b21_de_h_kodu_var_bilesende_yok(self):
        """
        B2.1'de H331 (Toksik-inhalasyon) var ama hiçbir bileşende H331 dayanağı yok.
        Denetçi bu tutarsızlığı yakalamalı.
        """
        sds = _base_sds({
            "clp": {
                "all_h_codes": ["H331"],
                "h_codes": ["H331"],
                "signal_word": "danger",
                "pictograms": ["GHS06"],
            },
            "components": [
                {
                    "name_tr": "Formik Asit",
                    "conc": "85",
                    "cas_no": "64-18-6",
                    "reach_no": "01-2119983628-23",
                    "hazards": [
                        {"h_code": "H314"},   # H331 dayanağı YOK
                    ],
                }
            ],
        })
        text = _build(sds, ["H331"])
        # H331 B2.1'de ama bileşen H listesinde yok
        assert "H331" in text
        # Sadece B3 bölümünü al (B4'e kadar)
        b3_start = text.find("BÖLÜM 3")
        b4_start = text.find("BÖLÜM 4")
        comp_section = text[b3_start:b4_start] if b4_start > b3_start else text[b3_start:]
        assert "H331" not in comp_section, "Bileşende H331 dayanağı olmadığı için B3 bileşen listesinde görünmemeli"


# ─────────────────────────────────────────────────────────────────────────────
# KURAL 3 — Zorunlu / Opsiyonel ayrımı
# ─────────────────────────────────────────────────────────────────────────────

class TestKural3_ZorunluOpsiyonel:
    """
    Ürün kodu gibi mevzuatta format şartı olmayan alanlar için
    denetçi "zorunlu hata" yazmamalı.
    UZEM (B1.4) gibi gerçekten zorunlu alanlar boş olursa hata yazmalı.
    """

    def test_pozitif__urun_kodu_tire_gecerli(self):
        """
        Ürün kodu '-' olarak girilmiş — mevzuatta format şartı yok → bulgu olmaz.
        Metin '-' değerini olduğu gibi aktarıyor.
        """
        sds = _base_sds({"product": {"code": "-"}})
        text = _build(sds, ["H314"])
        # Ürün kodu SDS metnine geçiyor mu?
        assert "Ürün kodu" in text
        # '-' değeri metinde korunuyor mu?
        product_line = [l for l in text.splitlines() if "Ürün kodu" in l]
        assert product_line, "Ürün kodu satırı bulunmalı"
        assert "-" in product_line[0], "Tire değeri korunmalı"

    def test_negatif__uzem_acil_tel_zorunlu(self):
        """
        KKDİK Ek-2 B1.4 uyarınca UZEM (114) zorunludur.
        Metin bu notu içeriyor → denetçi boş bırakılamayacağını bilmeli.
        """
        text = _build(_base_sds(), ["H314"])
        # Sistem her zaman UZEM satırını ekliyor
        assert "UZEM" in text or "114" in text, "UZEM/114 bilgisi B1 metninde olmalı"
        assert "zorunlu" in text.lower(), "KKDİK zorunluluk notu bulunmalı"


# ─────────────────────────────────────────────────────────────────────────────
# KURAL 5 — Başlık / B2.1 tutarsızlığı
# ─────────────────────────────────────────────────────────────────────────────

class TestKural5_BaslikB21:
    """
    B2.1 (all_h_codes) ile B2.2 (etiket h_codes) farkı dominance nedeniyle normaldir.
    Ama B2.1'deki bir H kodu etiket listesinde *ve* bileşenlerde de yoksa tutarsızlık var.
    """

    def test_pozitif__b21_b22_tutarli(self):
        """B2.1 ve B2.2 H kodları dominance kuralı açıklamasıyla birlikte tutarlı görünüyor."""
        sds = _base_sds({
            "clp": {
                "all_h_codes": ["H302", "H314"],
                "h_codes": ["H302", "H314"],   # etiket = sınıflandırma (dominance yok)
                "signal_word": "danger",
                "pictograms": ["GHS05", "GHS07"],
            }
        })
        text = _build(sds, ["H302", "H314"])
        # Her iki H kodu B2.1'de görünüyor
        b2_section = text[text.find("BÖLÜM 2"):text.find("BÖLÜM 3")]
        assert "H302" in b2_section
        assert "H314" in b2_section

    def test_negatif__b21_de_h302_b22_de_eksik_gercek_hata(self):
        """
        B2.1'de H302 var ama B2.2 etikette H302 yok VE dominance gerekçesi de yok
        (H302'yi baskılayan bir H kodu yok).
        Bu gerçek bir tutarsızlıktır.
        """
        sds = _base_sds({
            "clp": {
                "all_h_codes": ["H302", "H314"],
                "h_codes": ["H314"],   # H302 etikette yok, ama H314 H302'yi dominance etmez
                "signal_word": "danger",
                "pictograms": ["GHS05"],
            }
        })
        text = _build(sds, ["H314"])
        b2_section = text[text.find("BÖLÜM 2"):text.find("BÖLÜM 3")]
        # B2.1'de H302 var ama B2.2 etikette yok
        assert "H302" in b2_section, "H302 B2.1'de görünmeli"
        # Etikette sadece H314 var
        etiket_line = [l for l in b2_section.splitlines() if "Etiket H kodları" in l]
        assert etiket_line
        assert "H302" not in etiket_line[0], "H302 etiket satırında olmamalı"


# ─────────────────────────────────────────────────────────────────────────────
# KURAL 6 — Kaynak sınırlaması / M-faktör bağlam kısıtlaması
# ─────────────────────────────────────────────────────────────────────────────

class TestKural6_KaynakSinirlamasi:
    """
    Kural 6: Sistem promptunda olmayan hükümleri uydurma.
    Kural 6a: M-faktör YALNIZCA sucul toksisite (H400/H410-H412) için geçerlidir.
    H314/H318 bağlamında M-faktör iddiası halüsinasyondur.
    """

    def test_pozitif__sucul_toks_h410_mfaktor_gecerli_baglam(self):
        """
        H410 (Sucul Akut+Kronik Kat.1) varsa M-faktör mantıklı bağlamdır.
        Metin sucul H kodlarını içeriyor → denetçi M-faktörü doğru bağlamda değerlendirebilir.
        """
        sds = _base_sds({
            "eco": {"h_codes": ["H410"]},
            "clp": {
                "all_h_codes": ["H314", "H410"],
                "h_codes": ["H314", "H410"],
                "signal_word": "danger",
                "pictograms": ["GHS05", "GHS09"],
            },
        })
        text = _build(sds, ["H314", "H410"])
        eco_section = text[text.find("BÖLÜM 12"):]
        assert "H410" in eco_section, "H410 B12'de görünmeli"

    def test_negatif__h314_icin_mfaktor_iddiasi_olmamali(self):
        """
        Karışımda yalnızca H314 (cilt aşındırıcı) var, H4xx yok.
        Ekolojik bölümde M-faktörü zorunlu kılan hiçbir şey bulunmuyor.
        Denetçi bu durumda M-faktör gerekliliği *iddia etmemelidir*.
        Bu testi bir kural değil, bağlam doğrulaması olarak kullanıyoruz.
        """
        sds = _base_sds({
            "eco": {"h_codes": []},  # sucul tehlike yok
            "clp": {
                "all_h_codes": ["H314"],
                "h_codes": ["H314"],
                "signal_word": "danger",
                "pictograms": ["GHS05"],
            },
        })
        text = _build(sds, ["H314"])
        eco_section = text[text.find("BÖLÜM 12"):]
        # Sucul tehlike sınıfı yok → M-faktör bağlamı yok
        assert "H400" not in eco_section
        assert "H410" not in eco_section
        assert "Sucul tehlike sınıfı yok" in eco_section, \
            "Sucul tehlike yoksa metin bunu açıkça belirtmeli"


# ─────────────────────────────────────────────────────────────────────────────
# BONUS — ate_mix_details format doğrulaması
# ─────────────────────────────────────────────────────────────────────────────

class TestATEMixFormat:
    """_format_ate_b11 fonksiyonunun doğru çıktı ürettiğini doğrular."""

    def test_bos_details_bos_liste(self):
        assert _format_ate_b11({}) == []
        assert _format_ate_b11({"ate_mix_details": {}}) == []

    def test_oral_rota_formatli_cikti(self):
        sds = {"ate_mix_details": {"oral": {"ateMix": 800.0, "resultCode": "H302", "unknownPct": 0}}}
        lines = _format_ate_b11(sds)
        assert len(lines) >= 2
        assert "Oral" in lines[1]
        assert "800" in lines[1]
        assert "H302" in lines[1]

    def test_bilinmeyen_konsantrasyon_gosterilir(self):
        sds = {"ate_mix_details": {"dermal": {"ateMix": 500.0, "resultCode": "H310", "unknownPct": 5.2}}}
        lines = _format_ate_b11(sds)
        combined = " ".join(lines)
        assert "5.2" in combined or "bilinmeyen" in combined.lower()
