# DIPOL 108 Denetim Düzeltme Kılavuzu
# SDSPass Rev.18 — Yanlış Yorumlanan Bulgular

Oluşturulma: 2026-06-10  
Amaç: Gelecekteki otomatik denetim AI'larının aynı hataları yapmaması için doğru kural referansları.

---

## ÖZET: Denetimlerin Sistematik Hata Kaynakları

1. **P kodları**: Karışım sınıflandırması bazlıdır. Bileşen H kodlarına bakılmaz.
2. **ECHA konsantrasyon bantları**: "≥25%" geçerli üst bant — üst sınır beklenmez.
3. **H318 dominance**: H314 ile gizlenmesi doğrudur (B2.2'de), B2.1'de görünmesi zorunludur.
4. **H314 → H318**: B2.1 sınıflandırma tablosunda her ikisi de gösterilmelidir.

---

## F1 — Deniz Kirletici Hesabı Gösterilmemiş (GERÇEK SORUN)

**Denetim Bulgusu:** B14'te deniz kirletici hesabı yok, sadece "Uygulanamaz" yazıyor.

**Değerlendirme: DOĞRU — SDSPass'ta gerçek eksiklik.**

**Doğru Davranış:** IMDG §2.10.3 kriterine göre şu hesap gösterilmelidir:
```
Deniz kirletici toplam konsantrasyonu = Σ (bileşen konst% × M-faktörü)
Eşik: H400/H410 → ≥ 0.1%, H411 → ≥ 1%
```
`pdf_sds_service.py` sadece evet/hayır yazar, hesap göstermez. Bu gerçek bir eksikliktir.

**Düzeltme Durumu:** Henüz düzeltilmedi — backlog'da.

---

## F2 — H319 Etiketten Eksik (YANLIŞ BULGU)

**Denetim Bulgusu:** H314 var, H319 etikette yok — "HATA" olarak işaretlenmiş.

**Değerlendirme: YANLIŞ — SDSPass doğru davranıyor.**

**Doğru Kural (CLP Ek-I §3.2.3 + §3.3.1 Tablo):**  
H314 (Deri Koros. 1) varken H319 (Göz Tah. 2) aynı ürün için etiket gerektirmez.  
H314 baskındır — etikette H319 yazılmaz.  
B2.1 sınıflandırma tablosunda her ikisi de gösterilebilir ama etiket sadece H314'ü içerir.

**SDSPass Davranışı:** `clp_service.py` dominance map'i H319'u H314 varken etiket H kodlarından çıkarır. Bu doğrudur.

---

## F3 — P391 Eksik (YANLIŞ BULGU — KRITIK İŞARETİ HATALI)

**Denetim Bulgusu:** "Bileşen olarak H410 var ama karışım etiketinde P391 yok — KRİTİK"

**Değerlendirme: TAMAMEN YANLIŞ — SDSPass doğru davranıyor.**

**Doğru Kural (CLP Ek-I §2.8 / CLP Madde 22):**  
P kodları **karışımın sınıflandırmasına** göre seçilir. Bileşenin H kodlarına bakılmaz.

- DIPOL 108 karışımı → H412 (Uzun Süreli Sucul Zararlar, Kategori 3)
- H412 → P273 gerekli, P501 gerekli
- **P391 sadece H400/H410 için gereklidir** (akut sucul tehlike Kategori 1/2)
- H412 için P391 zorunlu değildir

`p_code_service.py` satır 260 onayı:
```python
'H412': ['P273','P501'],  # Cat.3: P273 yeterli, P391 zorunlu değil
```

**Kural:** Bileşen H410'sa da karışım H412 ise etiket H412 kurallarını uygular.  
Denetim AI'ı bileşen bazlı düşündü — bu CLP'nin açıkça yasakladığı bir yaklaşımdır.

---

## F4 — H318 B2.2'de Yok (YANLIŞ BULGU)

**Denetim Bulgusu:** "H318 etiket H kodlarında görünmüyor — HATA"

**Değerlendirme: YANLIŞ — SDSPass doğru davranıyor.**

**Doğru Kural (CLP Ek-I §3.3.1.4 + SEA Madde 28):**  
H314 (Ciddi Göz Hasarı/Deri Korozyonu) varken H318 etiket H kodları listesinde yazılmaz.  
H314 hem deriye hem göze zarar verir ve piktogram/sinyal bakımından H318'den baskındır.

**SDSPass Davranışı:**
- B2.1 tablosunda H318 **gösterilir** (sınıflandırma kaydı olarak)
- B2.2 etiket H kodu listesinde H318 **yazılmaz** (H314 baskılar)

Bu bilinçli ve doğru bir davranıştır. Hata değildir.

---

## F5 — H318 B2.1'de Eksik (GERÇEK SORUN — ÖNCEKİ VERSİYONDA)

**Denetim Bulgusu:** H314 var ama B2.1 tablosunda H318 satırı yok.

**Değerlendirme: Önceden gerçek sorundu, düzeltildi.**

**Doğru Kural (CLP §3.3.1.4):**  
H314 varlığında H318 otomatik olarak sınıflandırma tablosuna (B2.1) eklenmeli.

**Düzeltme:** `app/main.py` reconciliation bloğuna Step 5 eklendi (commit: bakınız git log).  
H314 varsa H318 `all_h_codes` ve `py_clp_passed`'a otomatik ekleniyor.

---

## F19 — Etil Asetat Konsantrasyon Aralığı "≥25%" Geçersiz (YANLIŞ BULGU)

**Denetim Bulgusu:** "≥25% aralığı eksik — '≥25–<70%' şeklinde olmalı — UYARI"

**Değerlendirme: TAMAMEN YANLIŞ — SDSPass doğru kullanıyor.**

**Doğru Kural (ECHA SDS Rehberi Bölüm 3.2 / KKDİK Ek-2 B3.2):**  
ECHA 5 standart konsantrasyon bandı tanımlar:
```
< 1%
≥ 1% – < 5%
≥ 5% – < 10%
≥ 10% – < 25%
≥ 25%          ← Üst bant, üst sınır yoktur
```
"≥25%" formatı doğrudur. "≥25–<70%" veya "≥25–<100%" gibi özel aralıklar ECHA standartlarına aykırıdır.

`concentration_ranges.py`'daki tanım:
```python
ECHA_RANGES = [
    (0.0,   1.0,   '< 1%'),
    (1.0,   5.0,   '≥ 1% – < 5%'),
    (5.0,   10.0,  '≥ 5% – < 10%'),
    (10.0,  25.0,  '≥ 10% – < 25%'),
    (25.0,  100.01,'≥ 25%'),         # üst sınır kasıtlı olarak 100.01 — kapsama dahil
]
```
Bu doğrudur. Denetim AI'ı "üst sınır bekliyorum" diye özel aralık üretmek istedi — bu kural ihlali olurdu.

---

## Genel Audit Tuzakları — Özet

| Tuzak | Hatalı Yaklaşım | Doğru Yaklaşım |
|-------|-----------------|----------------|
| P kodu denetimi | Bileşen H kodlarına bak | Karışım sınıflandırmasına bak |
| Konsantrasyon aralığı | "Üst sınır olmalı" beklentisi | ECHA 5-bant sistemine bak |
| H318 etikette yok | "Eksik" say | H314 baskısı kuralını kontrol et |
| H319 etikette yok | "Eksik" say | Dominance map'te hangi H kodunun baskın olduğunu kontrol et |
| H318 B2.1'de var | "Fazla" say | B2.1 sınıflandırma tablosu, etiket farklı — ikisi aynı olmak zorunda değil |

---

*Bu dosya SDSPass audit süreçlerinde yanlış bulunan düzeltilmiş kural yorumlarını içerir.*
*Son güncelleme: 2026-06-10*
