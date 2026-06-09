# SDSPass — Hesaplama Motoru → SDS Bölüm Haritası

> KKDİK Ek-2 + CLP uyumlu 16 bölümlü GBF/SDS sistemi.
> Her satır: hangi motor, ne hesaplar, hangi bölüme yazar.

---

## Tam Motor–Bölüm Tablosu

| Motor (servis dosyası) | Ne Hesaplar | Ana Değişken (main.py) | Beslediği SDS Bölümleri |
|------------------------|-------------|------------------------|-------------------------|
| `clp_service` — `classify_mixture_clp` | CLP karışım sınıflandırması (cut-off, ATE, dilüsyon) | `py_clp_passed`, `h_codes` | **B2.1** (sınıflandırma tablosu), **B2.2** (H ifadeleri), **B11** (ATE karışım) |
| `physical_engine` — `calculate` | Fiziksel tehlikeler (parlama noktası, patlayıcı, oksitleyici) | `_phys_res` | **B2.1**, **B9** (fiziksel özellikler), **B10** (stabilite/reaktivite) |
| `stot_engine` — `calculate` | Hedef organ toksisitesi (STOT SE/RE sınıflandırması) | `_stot_res` | **B2.1**, **B11** (toksikoloji) |
| `eco_engine` — `calculate` | Sucul ekotoksisite (M-faktör, eşik, H400/410/411) | `_eco_res2` | **B2.1**, **B12.1** (M-faktör tablosu) |
| `ecological_service` — `calculate_ecological` | PBT, biyobozunurluk, biyobirikim, endokrin bozucu, toprak | `eco_result` | **B2.3** (PBT/vPvB), **B12.1–12.6** |
| `transport_engine` — `classify` | UN numarası, ADR/RID/IMDG/IATA sınıflandırması | `py_transport` | **B14** (taşımacılık) |
| `ppe_engine` — `select` | KKE seçimi (eldiven, gözlük, solunum, tulum) | `py_ppe` | **B8.2** (KKE tablosu) |
| `p_code_service` — `assign_p_codes` | Tüm P kodlarının atanması (H koduna göre) | `p_result['p_codes']` | **B4** (ilk yardım P), **B5** (yangın P), **B6** (kaza P), **B7** (elleçleme P) |
| `p_code_service` — `select_label_p_codes` | Etiket için P kodu seçimi (CLP Md. 22) | `p_result['label']` | **B2.2** (etiket P kodları) |
| `ghs_pictogram` — `get_ghs_codes` | GHS piktogram listesi (H kodundan) | `clp['pictograms']` | **B2.2** (piktogramlar) |
| `euh_engine` / `euh_service` | EUH ek tehlike ifadeleri | `euh_result` | **B2.2** (EUH kodları) |
| `sds_sentence_service` — `generate_all_sections` | B4–B7 güvenlik önlemi metinleri | `sections` | **B4, B5, B6, B7** |
| `sds_sentence_service` — `generate_section(8,...)` | B8 maruziyet kontrol önlemleri metni | `sections[8]` | **B8** (genel metin) |
| `sds_sentence_service` — `generate_section(11,...)` | B11 toksikoloji metin blokları | `sections[11]` | **B11** |
| `tr_oel_service` — `get_oel` | Türkiye OEL (MAS) değerleri (CAS bazlı) | `oel_table` | **B8.1** (OEL tablosu) |
| `svhc_service` — `check_svhc_mixture` | SVHC aday madde tespiti | (dahili) | **B3** (bileşen uyarısı), **B15** (mevzuat) |
| `physical_hazard_service` — `calc_physical_hazards` | Detaylı fiziksel tehlike analizi | (dahili) | **B9, B10** |
| `sds_validator` — `validate_sds` | Çapraz bölüm tutarlılık kontrolü | `_validation_issues` | **B1–B16** (doğrulama raporu) |
| `tr_mevzuat_service` — `get_disposal_content` | Bertaraf mevzuat metni (H koduna göre) | (dahili) | **B13** |
| `gbf_author_service` | GBF hazırlayıcı bilgisi, sertifika no | `author` | **B1, B16** |

---

## Bölüm Bazlı Özet

### B2 — Zararlılık Tanımlaması (en kritik bölüm)
| Alt bölüm | Motorlar |
|-----------|---------|
| B2.1 Sınıflandırma tablosu | `clp_service`, `physical_engine`, `stot_engine`, `eco_engine` |
| B2.2 H/EUH/P kodları, piktogram | `clp_service` (h_codes), `euh_service`, `p_code_service`, `ghs_pictogram` |
| B2.3 PBT/vPvB | `ecological_service` |

### B3 — Bileşim / İçerik Bilgisi
- `substance_lookup` (CAS/EC no, sınıflandırma DB)
- `concentration_ranges` (konsantrasyon aralıkları)
- `svhc_service` (SVHC uyarısı)

### B4–B7 — İlk Yardım / Yangın / Kaza / Elleçleme
- `sds_sentence_service` → H kodu bazlı metin üretimi
- `p_code_service` → P kodu ataması

### B8 — Maruziyet Kontrolü / KKE
- B8.1 OEL: `tr_oel_service`
- B8.2 KKE: `ppe_engine`
- Genel metin: `sds_sentence_service`

### B9 — Fiziksel ve Kimyasal Özellikler
- `physical_engine` (tehlikeli fiziksel özellikler)
- `phys_props_parser` (parlama noktası, kaynama, viskozite vb.)
- `pubchem_phys_service` (PubChem'den otomatik veri)

### B10 — Kararlılık ve Reaktivite
- `physical_engine` (patlayıcı, oksitleyici, su reaktif)
- `stot_engine` (ayrışma ürünleri)

### B11 — Toksikoloji Bilgisi
- `stot_engine` (STOT SE/RE)
- `clp_service` (ATE hesabı)
- `sds_sentence_service`

### B12 — Ekoloji Bilgisi
- `eco_engine` (sucul sınıf, M-faktör)
- `ecological_service` (PBT, biyobozunurluk, biyobirikim, toprak, endokrin)

### B14 — Taşımacılık
- `transport_engine` (UN, ADR/RID, IMDG, IATA)

### B15 — Mevzuat Bilgisi
- `tr_mevzuat_service`
- `svhc_service`
- `reach_db` (kayıt no)

### B16 — Diğer Bilgiler
- `gbf_author_service` (hazırlayıcı, revizyon)
- `sds_validator` (doğrulama özeti)

---

*Son güncelleme: 2026-06-09 — SDSPass sdspass-api main branch*
