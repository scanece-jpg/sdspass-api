# SDS / ADR Doğrulama Notları

Bu dosya, sistem denetimleri sırasında tespit edilen ve **resmi kaynaktan teyit gerektiren**
veya **kullanıcı tarafından aksiyona ihtiyaç duyan** maddeleri takip eder.

---

## ADR Taşımacılık

### UN3093 — Tünel Kodu (KAPATILDI)
- **Sorun:** `adr_data.json`'da UN3093 PG I için tünel kodu `B/E` olarak girilmişti.
- **Resmi kaynak:** ADR 2025 Tablo A (sds-knowledge/tr/adr-2025-cilt-i-vurgulu.pdf, sayfa 499)
- **Doğru değerler:**
  - PG I: Kemler = 885, Tünel = **E**
  - PG II: Kemler = 85, Tünel = **E**
- **Düzeltme:** `data/adr_data.json` güncellendi (commit: bir sonraki commit).
- **Durum:** ✅ Kapatıldı

---

### UN3098 → UN3093 Sınıf Değişikliği (KAPATILDI — BACKEND OTOMATİK)
- **Ürünler:** DIPOL 206, DIPOL 207, DIPOL 208
- **Eski çıktı:** UN3098 / Sınıf 5.1 / PG III
- **Yeni çıktı:** UN3093 / Sınıf 8 / PG I (otomatik)
- **Backend düzeltmesi (commit 0db7a6a5):**
  - `H_TO_ADR['H314']`: PG II → **PG I** (ADR §2.1.3.5.5 en kötü senaryo)
  - `resolve_conflict`: Sınıf 5.1 vs 8 için erken çıkış kuralı — Sınıf 8 PG I olduğunda kazanır
  - `_get_un_entry`: Sınıf 8 + yan tehlike 5.1 → **UN3093** Korozif Sıvı, Oksitleyici
- **Doğrulanan ADR değerleri (ADR 2025 Tablo A, sayfa 499):**
  - Kemler: 885 | Tünel: E | Sınıflandırma kodu: CO1 | Etiket: 8 (5.1)
- **Not:** Gerçek ADR korozivite test verisi (§2.2.8.1.4.1, zaman-bazlı doku hasarı)
  mevcut olursa motor güncellenebilir — PG II veya III'e revize mümkün.
- **Durum:** ✅ Kapatıldı (backend otomatik olarak doğru UN3093/PG I üretir)

---

## MgCl2 H318/H319 Çakışması (KAPATILDI — BACKEND OTOMATİK)

- **Sorun:** DIPOL 206, 207, 208 ürünlerinde magnezyum diklorür (7786-30-3) bileşeni
  Bölüm 3.2'de H318 + H319 birlikte listeleniyordu (PubChem çakışan ECHA C&L bildirimi).
- **Kök neden:** ECHA C&L Inventory'de farklı firmalar H318 (Göz Hasar. 1) veya H319
  (Göz Tahriş. 2) bildirmiş; PubChem ikisini birleştirip döndürüyor. MgCl2 harmonize
  listede (SEA Ek-6) yer almadığından tek bir resmi sınıflandırma yok.
- **Doğru sınıflandırma:** Yalnızca H318 (Göz Hasar. 1) — H318 varken H319 CLP gereği geçersiz.
- **Backend düzeltmeleri (commit 3a72c34b):**
  - `echa_service.py`'e `_dedupe_h_codes()` fonksiyonu eklendi.
  - Her API çekiminde (hem ECHA hem PubChem) ve önbellek okumada CLP dominans
    kuralları uygulanır: H318 varsa H319 otomatik düşer; H314 varsa H315+H319 düşer vb.
  - Temizlenen veri önbelleğe (echa_cache.json) geri yazılır — sonraki sorgular temiz gelir.
  - `clp_service.py` (commit 60af6882): Eye Irrit. 2 çift sayım hatası da düzeltildi
    (H318 olan bileşen Eye Dam. 1 toplamına eklenirken yanlışlıkla Eye Irrit. 2
    toplamına da ekleniyordu).
- **Kapsam:** Bu düzeltme MgCl2'ye özgü değil — tüm maddelerde çakışan H kodları
  otomatik temizlenir (2026-06-28 itibarıyla sistem doğru çalışmaktadır).
- **Durum:** ✅ Kapatıldı

---

## Magnesium Dinitrate — SEA Ek-6 Index Numarası (DOĞRULANDI — BOŞ KALMASI DOĞRU)

- **Soru:** Magnesium dinitrate (10377-60-3) için SDS Bölüm 3.2'de KKDİK/SEA
  index numarası neden yok?
- **Araştırma (2026-06-28):** SEA Ek-6 (sea_ek6_l-ste_15062020-20200618142549.docx)
  Tablo 3 incelendi. Magnesium nitrate/dinitrate bu listede yer almıyor.
  Listede yalnızca şu magnezyum bileşikleri var: hexafluorosilicate (009-018-00-3),
  powder pyrophoric (012-001-00-3), powder/turnings (012-002-00-9),
  alkyls (012-003-00-4), phosphide (015-005-00-3) ve birkaç kompleks tuz.
- **Sonuç:** Harmonize sınıflandırma listesinde olmayan maddeler için
  SEA/CLP index numarası yoktur. SDS'de bu alanın boş kalması **doğru ve mevzuata uygundur**.
- **Durum:** ✅ Doğrulandı — sistem doğru davranıyor

---

## Genel Notlar

### ADR Veri Kaynağı Güvenilirliği
- `data/adr_data.json` dosyasının tüm girişleri resmi ADR 2023/2025 Tablo A ile
  karşılaştırılarak doğrulanmamıştır.
- Kritik UN numaraları için değerleri her zaman
  `sds-knowledge/tr/adr-2025-cilt-i-vurgulu.pdf` ile teyit edin.
- Özellikle dikkat: Kemler kodu ve tünel kısıtlama kodu PG'ye göre farklılaşabilir
  (örn. UN3094 PG I → D/E, PG II → E).

### ADR §2.1.3.5.5 — En Kötü Senaryo Kuralı
Test verisi mevcut olmadığında en yüksek tehlike kategorisi atanır.
- pH ≤ 2 veya pH ≥ 11.5 olan karışımlar için ADR aşındırıcılık PG'si
  test yapılmadıkça **PG I** olarak değerlendirilir.
- Bu kural §2.1.3.10 matrisiyle birlikte UN numarasını belirler.
