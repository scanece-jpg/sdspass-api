---
name: sds-kontrol
description: >
  Mevcut bir SDS metnini veya PDF'ini KKDİK/SEA mevzuatına göre denetler.
  Her bölümü kontrol eder, hataları ve eksiklikleri raporlar.
  Motorları kullanarak matematiksel tutarsızlıkları doğrular.
---

# SDS Kontrol Skill'i

## Genel Akış

1. **SDS Al** — Kullanıcı metin yapıştırır veya PDF yükler
2. **Bölüm Bölüm Denetle** — Her bölümü mevzuat kurallarına göre kontrol et
3. **Motor Doğrulaması** — Bileşen verileri varsa H kodlarını/ADR'yi yeniden hesapla, tutarsızlık var mı bak
4. **Rapor** — Hataları önem sırasına göre listele (❌ Hata / ⚠️ Uyarı / ℹ️ Bilgi)

---

## Kontrol Listesi

### B1 — Kimyasal Ürün ve Firma
- [ ] Ürün adı var mı?
- [ ] GBF tarihi ve revizyon no var mı?
- [ ] Tedarikçi adı, adresi, telefonu var mı?
- [ ] Acil telefon numarası var mı? (KKDİK Md.31)
- [ ] Kullanım tanımı var mı?

### B2 — Tehlike Tanımlaması
- [ ] CLP/SEA sınıflandırması yazılmış mı?
- [ ] Piktogramlar H kodlarıyla tutarlı mı?
- [ ] Sinyal kelimesi doğru mu? (Danger/Warning)
- [ ] H kodları eksiksiz mi?
- [ ] P kodları H kodlarıyla tutarlı mı?
- [ ] GHS07 baskınlık kuralları doğru uygulanmış mı? (CLP Madde 26 / SEA Madde 28)

### B3 — Bileşim/İçindekiler
- [ ] Tehlikeli bileşenler listelenmiş mi?
- [ ] CAS, EC, index numaraları var mı?
- [ ] Konsantrasyon veya aralık belirtilmiş mi?
- [ ] Her bileşenin H kodları doğru mu?
- [ ] Su veya inert bileşenler "Sınıflandırılmamış" olarak belirtilmiş mi?

### B4-B8 — Güvenlik Önlemleri
- [ ] İlk yardım talimatları maruziyet yollarını kapsıyor mu?
- [ ] Yangın söndürücüler fiziksel tehlikeyle tutarlı mı?
- [ ] OEL değerleri KKDİK Ek-14'ten mi alınmış?
- [ ] KKE seçimi H kodlarıyla uyumlu mu?

### B9 — Fiziksel Özellikler
- [ ] Parlama noktası B2/B14 ile tutarlı mı?
- [ ] "Hesaplama ile tahmin" edilen değerler belirtilmiş mi?
- [ ] Kritik özellikler eksik mi?

### B14 — Taşımacılık
- [ ] UN numarası var mı?
- [ ] Taşımacılık tehlike sınıfı doğru mu?
- [ ] Ambalaj grubu (PG) belirtilmiş mi?
- [ ] Kemler kodu doğru mu?
- [ ] ADR, IMDG, IATA ayrı ayrı belirtilmiş mi?

### B15 — Mevzuat
- [ ] SVHC beyanı var mı?
- [ ] ≥%0.1 SVHC bileşeni varsa bildirim yükümlülüğü belirtilmiş mi?
- [ ] KKDİK/SEA atıfları doğru mu?

### B16 — Diğer Bilgiler
- [ ] Revizyon geçmişi var mı?
- [ ] Sorumluluk reddi var mı?

---

## Motor Doğrulaması

Bileşen listesi ve konsantrasyonlar mevcutsa:

1. `POST /api/v1/sds/calculate` — H kodlarını yeniden hesapla
2. SDS'teki H kodlarıyla karşılaştır
3. Fark varsa ❌ olarak işaretle ve doğru değeri göster

---

## Rapor Formatı

```
## SDS Kontrol Raporu — [Ürün Adı]

### ❌ Hatalar (Düzeltilmesi Zorunlu)
- B2: H314 var ama GHS05 piktogramı eksik
- B14: UN2920 için Kemler kodu 83 olmalı, 30 yazılmış

### ⚠️ Uyarılar (Gözden Geçirilmeli)
- B3: Sodyum dikromat (7789-12-0) SVHC listesinde, B15'te belirtilmemiş
- B9: Parlama noktası belirtilmemiş

### ℹ️ Bilgi
- B1: Revizyon tarihi 2 yıldan eski, güncelleme değerlendirin

### Özet
Toplam: 2 hata, 2 uyarı, 1 bilgi
```

---

## Kurallar

- Motor doğrulaması yapılmadan matematiksel hata iddiasında bulunma
- Mevzuat madde numaralarını doğru yaz (KKDİK, SEA, ADR 2025)
- Şüpheli durumlarda ⚠️ kullan, kesin ise ❌

---

## API Base URL
`https://sdspass-api-3.onrender.com`
