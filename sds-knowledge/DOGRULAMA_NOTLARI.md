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

### UN3098 → UN3093 Sınıf Değişikliği (KULLANICI AKSİYONU BEKLİYOR)
- **Ürünler:** DIPOL 206, DIPOL 207, DIPOL 208
- **Mevcut:** UN3098 / Sınıf 5.1 / PG III
- **Önerilen:** UN3093 / Sınıf 8 / PG I
- **Gerekçe:**
  - ADR §2.1.3.5.5 — test verisi yoksa en kötü senaryo uygulanır
  - pH ≤ 2 → CLP Cilt Aş. 1 (H314) → ADR aşındırıcılık PG I (ihtiyaten)
  - ADR §2.1.3.10 matrisine göre Sınıf 8 PG I, Sınıf 5.1'i her durumda yener
  - UN3093 PG I ADR değerleri (resmi ADR 2025 onaylı):
    - Kemler: 885 | Tünel: E | Taşıma kategorisi: 1 | Etiket: 8 (5.1)
- **Aksiyon:** Ürün editöründe her üç ürünün taşımacılık bölümünde
  UN3098 → UN3093 ve PG III → PG I olarak güncellenmeli.
- **Not:** Gerçek ADR korozivite test verisi (§2.2.8.1.4.1, zaman-bazlı doku hasarı)
  mevcut olursa PG II veya III'e revize edilebilir — o zaman UN3093/PG II
  (kemler 85, tünel E) veya UN3098/PG III geçerli olabilir.
- **Durum:** ⏳ Kullanıcı frontend güncellemesi bekliyor

---

## MgCl2 Bileşen Verisi (KULLANICI AKSİYONU BEKLİYOR)

- **Sorun:** DIPOL 206, 207, 208 ürünlerinde magnezyum diklorür (7786-30-3) bileşeni
  Bölüm 3.2'de H318 + H319 birlikte listelenmiş (çakışan ECHA C&L bildirimi).
- **Doğru sınıflandırma:** Yalnızca H318 (Göz Hasar. 1, Danger, GHS05)
- **Backend düzeltmesi:** `data/substances_custom.json`'a H318-only kayıt eklendi (commit 60af6882).
  Bundan sonraki aramalar doğru veriyi döndürür.
- **Aksiyon:** Her üç üründe ürün editöründe MgCl2 bileşeni yeniden
  aratılıp kaydedilmeli (H319 düşer, H318 kalır).
- **Durum:** ⏳ Kullanıcı frontend güncellemesi bekliyor (3 ürün)

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
