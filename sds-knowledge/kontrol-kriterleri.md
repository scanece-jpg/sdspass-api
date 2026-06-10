# SDSPass — Motor Mimarisi ve Validator Referansı

> **Bu belge bir yönetmelik kaynağı değildir.**
> Mevzuat kuralları için projeye yüklenen KKDİK Ek-2, SEA Yönetmeliği ve CLP belgelerini kullanın.
>
> Bu dosya yalnızca şu soruyu yanıtlar:
> **"PDF'deki bu hata hangi SDSPass motoruna işaret eder?"**
>
> Her bölüm için: hangi motor besliyor, ne kontrol edilir, hata varsa hangi engine'i şüphelendir.

---

## Denetim Metodolojisi

Bir bulgu hata olarak işaretlenmeden önce şu adımlar izlenmelidir:

1. **Yönetmeliği doğrula** — Bulguyu projeye yüklenen kaynak belgelere karşı kontrol et:
   - P kodları için: **CLP Ek-I §2–§3 tabloları** (karışımın H koduna göre zorunlu P listesi)
   - Konsantrasyon aralıkları için: **ECHA SDS Rehberi Bölüm 3.2** (standart bantlar)
   - H kodu baskı/dominance için: **CLP Ek-I §3.x.x tabloları** (hangi H kodu hangisini bastırır)
   - Taşımacılık kriterleri için: **IMDG Kodu §2.10** / **ADR Bölüm 2**

2. **SDSPass motorunu doğrula** — Yönetmelik doğruysa ilgili motoru incele (bu dosyadaki motor haritasına bak). Bulgu, mevzuata aykırı bir çıktı ise hata; mevzuata uygunsa hata değildir.

3. **Emin olmadan işaretleme** — "Muhtemelen hata" veya "eksik görünüyor" yeterli değildir. Yönetmelik referansı gösterilemeyen bulgular raporlanmamalıdır.

---

## Motor Haritası (Özet)

| Bölüm | Birincil Motor | İkincil Motor |
|-------|---------------|---------------|
| B1 | Kullanıcı girişi (frontend) | — |
| B2.1 | `clp_service` | `physical_engine`, `stot_engine`, `eco_engine` |
| B2.2 | `clp_service`, `ghs_pictogram` | `p_code_service`, `euh_service` |
| B3 | `substance_lookup` | `reach_db`, `concentration_ranges` |
| B4–B7 | `sds_sentence_service` | `p_code_service` |
| B8 | `tr_oel_service`, `ppe_engine` | `sds_sentence_service` |
| B9 | `physical_engine`, `phys_props_parser` | `pubchem_phys_service` |
| B10 | `sds_sentence_service` | `physical_engine` |
| B11 | `stot_engine`, `clp_service` (ATE) | `sds_sentence_service` |
| B12 | `eco_engine`, `ecological_service` | — |
| B13 | `sds_sentence_service` | — |
| B14 | `transport_engine` | — |
| B15 | `tr_mevzuat_service`, `svhc_service` | `reach_db` |
| B16 | Kullanıcı girişi (revision) | — |

---

## B1 — Madde/Karışım ve Şirket Bilgileri

**Motor:** Kullanıcı girişi — `product` ve `supplier` alanları

### Motor bağlamı:
- Ürün adı, kodu, kullanım amacı → frontend `product` objesi
- Tedarikçi adı, adres, telefon, e-posta → frontend `supplier` objesi
- Acil durum telefonu → `supplier.emergency_tel` alanı

### Kırmızı bayraklar (motor kaynağı):
- Acil durum telefonu boş → `supplier.emergency_tel` frontend'den iletilmemiş
- Tedarikçi bilgileri eksik → frontend'de doldurulmamış alan
- Ürün kullanım amacı yok → `product.usage_desc` boş

---

## B2.1 — Sınıflandırma Tablosu

**Motorlar:** `clp_service`, `physical_engine`, `stot_engine`, `eco_engine`

### Motor bağlamı:
- Sağlık tehlikeleri (H3xx) → `clp_service.classify_mixture_clp()`
- Fiziksel tehlikeler (H22x, H26x) → `physical_engine.calculate()`
- Hedef organ (H370–H373) → `stot_engine.calculate()`
- Sucul tehlike (H400–H413) → `eco_engine.calculate()` + `ecological_service`
- Tablo satırları `py_clp_passed` listesinden üretilir

### Kırmızı bayraklar:
- H400/H410/H411 var → B2.1'de sucul satır yok → `eco_engine` veya reconciliation sorunu
- "Sınıflandırma yok" ama B2.2'de H kodu var → `clp_service` veya veri senkron sorunu
- ATE değerleri aşırı (< 1 mg/kg veya > 50.000 mg/kg) → `clp_service` ATE hesabı sorunu

### H318 kuralı (V020):
- H314 varsa → H318, `all_h_codes`'ta bulunmalı (B2.1 tablosunda görünmeli)
- H318, etikette (B2.2) **yazmamalı** — H314 baskın gelir (dominance)
- Detay: `sds_validator.py` → V020

---

## B2.2 — Etiket Unsurları (Sinyal, Piktogram, H/P Kodları)

**Motorlar:** `clp_service`, `ghs_pictogram`, `p_code_service`, `euh_service`

### Motor bağlamı:
- Piktogram listesi → `ghs_pictogram.get_ghs_codes(h_codes)`
- P kodları → `p_code_service.assign_p_codes()` + `select_label_p_codes()`
- EUH kodları → `euh_service`
- Sinyal kelimesi → `clp_service.DANGER_H` seti ile hesaplanır

### GHS09 özel durumu:
- H400/H410/H411 → GHS09 **gerekli**
- H412/H413 → GHS09 **gerekmez** (validator V019 bunu denetler)
- PDF'de GHS09 var ama validator "eksik" diyorsa → `sds_data['clp']['pictograms']` senkron sorunu

### Kırmızı bayraklar:
- GHS09 eksik ama H400/H410/H411 var → `ghs_pictogram` veya `eco_engine` senkron sorunu (V019)
- H314 var → P310 yok → `p_code_service` sorunu
- Sinyal "Warning" ama Danger H kodu var → `clp_service.DANGER_H` listesi sorunu (V014)

---

## B3 — Bileşim / İçerik Bilgisi

**Motorlar:** `substance_lookup`, `concentration_ranges`, `svhc_service`

### Motor bağlamı:
- CAS/EC/REACH no → `substance_lookup` + `reach_db`
- Konsantrasyon aralıkları → `concentration_ranges.build_concentration_ranges()`
- SVHC kontrolü → `svhc_service`
- Kaynak önceliği: SEA Ek-6 (source_priority=1) > Annex VI (2) > Custom (3) > ECHA C&L (4) > PubChem (5)

### Kırmızı bayraklar:
- EC numarası boş → `reach_db` sorunu
- REACH no boş, source_priority ≥ 4 → V018 uyarısı (ECHA/PubChem kaynaklı, kayıt no doğrulanamaz)
- SVHC bileşen var ama B15'te kayıt no yok → `svhc_service` sorunu

---

## B4–B7 — İlk Yardım / Yangın / Kaza / Elleçleme

**Motor:** `sds_sentence_service`, `p_code_service`

### Motor bağlamı:
- B4–B7 metinleri H kodlarına göre `sds_sentence_service` tarafından üretilir
- H kodu listesi değişirse cümleler otomatik güncellenir

### Kırmızı bayraklar:
- H314 var → B4'te göz/deri için acil yıkama + tıbbi yardım yok → `sds_sentence_service` sorunu
- H226 var → B5'te yanıcı sıvı söndürme talimatı yok → `sds_sentence_service` sorunu
- H260/H261 var → B5'te "suyla söndürmeyin" uyarısı yok → `sds_sentence_service` sorunu

---

## B8 — Maruziyet Kontrolü / KKE

**Motorlar:** `tr_oel_service`, `ppe_engine`, `sds_sentence_service`

### Motor bağlamı:
- OEL değerleri → `tr_oel_service.get_oel(cas)` — TR KKDİK veritabanı
- KKE seçimi → `ppe_engine.select(h_codes)` — H koduna göre otomatik
- KKE metinleri → `sds_sentence_service`

### Kırmızı bayraklar:
- OEL tablosu boş ama bilinen bileşenler var → `tr_oel_service` veri eksikliği
- KKE "gerekmiyor" ama H314 var → `ppe_engine` sorunu
- H334 var → solunum koruyucu belirsiz → `ppe_engine` sorunu (V012)

---

## B9 — Fiziksel ve Kimyasal Özellikler

**Motorlar:** `physical_engine`, `phys_props_parser`, `pubchem_phys_service`

### Motor bağlamı:
- Kullanıcı değerleri → `phys_props_parser.parse_all_phys_props()`
- Teorik hesaplama → `physical_engine` → `theo_props` (backfill ile B9'a yazılır)
- PubChem önbellek → `pubchem_phys_service.fetch_phys(cas)` — TTL: kritik alanlar 90 gün, diğerleri 365 gün
- `_classification_h22x` değişirse önbellek geçersiz sayılır

### Kırmızı bayraklar:
- Parlama noktası yok ama H226 var → V001 hatası
- Parlama noktası >60°C ama H226 var → V002 uyarısı
- Viskozite yok ama H304 var → V003 hatası
- pH 7 ama H314 var → V006 uyarısı

---

## B10 — Kararlılık ve Tepkime

**Motor:** `sds_sentence_service`, `physical_engine`

### Motor bağlamı:
- B10 metinleri H kodlarına göre `sds_sentence_service` tarafından üretilir
- H272 (oksitleyici) → bağdaşmayan maddeler listesi otomatik eklenmeli
- H260/H261 (su reaktif) → nem/su uyarısı otomatik eklenmeli

### Kırmızı bayraklar:
- H272 var → "bağdaşmayan maddeler" bölümü boş → `sds_sentence_service` sorunu (V009)
- H260/H261 var → nem uyarısı yok → `sds_sentence_service` sorunu (V010)
- Tehlikeli bozunma ürünleri bölümü tamamen boş → `sds_sentence_service` veri eksikliği

---

## B11 — Toksikoloji Bilgisi

**Motorlar:** `stot_engine`, `clp_service` (ATE), `sds_sentence_service`

### Motor bağlamı:
- ATE hesabı → `clp_service` (karışım LD50/LC50)
- STOT organ listesi → `stot_engine.calculate()`
- Toksikoloji metinleri → `sds_sentence_service`

### Kırmızı bayraklar:
- H301 var → B11'de LD50 değeri yok → `clp_service` ATE eksikliği
- STOT RE/SE var → hedef organ boş → `stot_engine` sorunu (V017)
- ATE hesabı yok ama akut toksisite H kodu var → `clp_service` sorunu

---

## B12 — Ekoloji Bilgisi

**Motorlar:** `eco_engine`, `ecological_service`

### Motor bağlamı:
- Sucul sınıflandırma → `eco_engine.calculate()` (CLP Ek-I Tablo 4.1.1/4.1.2)
- B12.1 metni → `ecological_service.calculate_ecological()` → `sds_section_12['12.1']`
- Divergence çözümü: M-faktörleri eksiksizse `eco_engine` kazanır (high confidence); eksikse daha tehlikeli seçilir
- `ecological_service`, `eco_engine_aquatic` parametresiyle eco_engine sonucunu devralır

### Kırmızı bayraklar:
- B2.1'de H400 var, B12.1'de "Sınıflandırma yok" → `eco_engine`/`ecological_service` senkron sorunu
- M-Faktörü tablosu boş ama H400 bileşeni var → `eco_engine` veri eksikliği
- B12.1 ↔ B2.1 sucul H kodu uyuşmuyor → reconciliation bloğu sorunu

---

## B13 — Bertaraf

**Motor:** `sds_sentence_service`

### Motor bağlamı:
- Bertaraf metinleri `sds_sentence_service` tarafından üretilir
- EWC atık kodu sistem tarafından önerilmez — kullanıcı girişi veya `sds_sentence_service` şablonu
- Tehlikeli H kodu varsa bertaraf yöntemi "normal atık" olamaz

### Kırmızı bayraklar:
- EWC atık kodu yok → `sds_sentence_service` şablon eksikliği
- H kodlu ürün için "evsel atık gibi bertaraf" ifadesi → `sds_sentence_service` hatalı şablon
- TR atık mevzuatı atfı yok → `sds_sentence_service` sorunu

---

## B14 — Taşımacılık

**Motor:** `transport_engine`

### Motor bağlamı:
- ADR/IMDG/IATA sınıflandırması → `transport_engine.classify(h_codes, form, phys_h_codes)`
- UN numarası, ambalaj grubu, çevre tehlike işareti otomatik belirlenir
- Fiziksel motor H kodları (H22x) transport_engine'e iletilir

### Deniz kirletici hesabı (IMDG §2.10.3):
- Marine Pollutant kriteri: H400/H410 → ≥0.1%, H411 → ≥1% konsantrasyon eşiği
- B14'te sadece "Evet/Hayır" değil, **hesap gerekçesi** gösterilmelidir
- Gerekçe formatı: `Σ (bileşen konst% × M-faktörü)` ile eşik karşılaştırması
- Hesap gerekçesi (Σ C×M tablosu + sonuç satırı) B14 sonunda gösterilir — `pdf_sds_service.py`

### Kırmızı bayraklar:
- ADR "Düzenlemeye tabi değil" ama H225 var → `transport_engine` sorunu
- UN numarası yok ama tehlikeli madde → zorunlu alan
- Çevre tehlike işareti yok ama H400/H410 var → `transport_engine` env_mark sorunu
- Deniz kirletici evet/hayır var ama hesap gerekçesi yok → `pdf_sds_service` eksikliği

---

## B15 — Mevzuat Bilgisi

**Motorlar:** `tr_mevzuat_service`, `svhc_service`, `reach_db`

### Motor bağlamı:
- REACH kayıt numarası → `reach_db.get_reg_no(cas)`
- SVHC kontrolü → `svhc_service`
- TR mevzuat atıfları → `tr_mevzuat_service`

---

## B16 — Diğer Bilgiler

**Motor:** Kullanıcı girişi — `revision` objesi

### Motor bağlamı:
- Revizyon tarihi → `revision.date`
- Versiyon numarası → `revision.version`
- Değişiklik özeti → `revision.notes`

### Kırmızı bayraklar:
- Revizyon tarihi yok → `revision.date` boş veya iletilmemiş
- Versiyon numarası yok → `revision.version` boş
- İkinci+ revizyon ama değişiklik özeti "İlk yayın" → `revision.notes` güncellenmemiş

---

## Otomatik Validator Kuralları (sds_validator.py)

PDF header'ında `X-SDS-Issues` ve `X-SDS-Issue-Counts` alanları bu kuralların sonucunu taşır.

| Kod | Kural | Seviye |
|-----|-------|--------|
| V001 | H226 var → parlama noktası zorunlu | error |
| V002 | H226 ama parlama noktası >60°C | warning |
| V003 | H304 var → viskozite zorunlu | error |
| V004 | H304 ama viskozite >20 mm²/s | warning |
| V005 | H314 var → pH önerilir | info |
| V006 | H314 ama pH 2–11.5 arası | warning |
| V009 | H272 var → B10'da bağdaşmayan maddeler belirtilmeli | warning |
| V010 | H260/H261 var → B7'de nem uyarısı | warning |
| V011 | CMR madde → B8'de özel KKE | warning |
| V012 | H334 var → SCBA/tam yüz maskesi | warning |
| V013 | 6'dan fazla P kodu (CLP 22(4) — zorunluysa ihlal değil) | info |
| V014 | Danger H kodu var ama sinyal "Warning" | error |
| V016 | Çözünürlük > yoğunluk × 10⁶ (fiziksel imkânsız) | warning |
| V017 | STOT RE var ama bileşen verisi erişilemez | warning |
| V018 | ECHA/PubChem kaynaklı bileşende REACH no eksik | warning |
| V019 | GHS09 tutarsızlığı: H400/410/411 varken yok, ya da H412/413 ile birlikte var | warning |
| V020-A | H314 var ama all_h_codes'ta H318 yok (B2.1 eksik) | warning |
| V020-B | H314 var ve H318 etiket H kodlarında görünüyor (kaldırılmalı) | info |

---

*Son güncelleme: 2026-06-10*
