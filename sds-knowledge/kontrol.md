# SDSPass — Araştırma Notları ve Askıdaki Bulgular

> Bu dosya, motor denetimleri sırasında yapılan mevzuat araştırmalarının
> sonuçlarını ve netleşmeyi bekleyen açık soruları kaydeder.

---

## BULGU 1 — eco_engine H411 bileşen → H412 üretiyor

**Durum:** ⏸ ASKIDA — Koda dokunulmaz

**Konu:** DIPOL 126 GBF denetiminde tespit edildi.  
n-Hekzan (H411, %20) içeren karışımda eco_engine H412 üretiyor.  
Auditor beklentisi: H411.

**eco_engine.py mevcut davranışı (toplamsal yöntem, CLP §4.1.3.5.5):**
```
K2 = 20 / 100 = 0.20
h411_sum = 10×0 + 0.20 = 0.20 < 0.25 → H411 yok
h412_sum = 100×0 + 10×0.20 + 0 = 2.00 ≥ 0.25 → H412 atanır
```
CLP Tablo 4.1.2 formülüyle birebir uyumlu.

---

### §4.1.3.5.4 "Daha koruyucu sonucu seç" kuralı — Araştırma Sonucu

**Tarih:** 2026-06-13  
**Kaynaklar:** ReachOnline (CLP Annex I), Alchemy Compliance, mixclass.net

**Doğrudan metin:**
> *"If a mixture is classified in more than one way, the method yielding the more conservative result shall be used."*

**Araştırma, bu kuralın hangi iki yöntem arasında geçerli olduğunu netleştirdi:**

| "İki yöntem" senaryosu | §4.1.3.5.4 uygulanır mı? |
|---|---|
| §4.1.3.5.2 (L(E)C50 verisi ile additivity formülü) vs §4.1.3.5.5 (H-kodu toplamsal yöntemi) | ✅ EVET |
| Köprüleme ilkeleri (§4.1.3.4) vs toplamsal yöntem (§4.1.3.5) | ✅ EVET |
| Test edilmiş karışım verisi vs bileşen bazlı yöntem | ✅ EVET |
| Kesme değeri tablosu vs toplamsal formül (her ikisi de §4.1.3.5.5 içinde) | ❓ **Belirsiz** |

**Alchemy Compliance alıntısı:**
> *"The calculation can be simplified to threshold concentrations only in the cases where the above do not apply."*

Kesme değeri tablosu, toplamsal formülün **uygulanamadığı durumlarda** kullanılan
basitleştirilmiş alternatif — eş zamanlı çalıştırılan paralel bir yöntem değil.

**Sonuç:** §4.1.3.5.4 kuralının kesme değeri tablosu vs toplamsal formül arasında
uygulanıp uygulanmadığı **kesin olarak netleşmedi.**

---

### Neden askıda?

Bu oturumda aynı soru için üç farklı analiz sonucu üretildi:

1. Kod doğru → BULGU 1 geçersiz (toplamsal yöntem CLP uyumlu)
2. §4.1.3.5.4 bunu kapsar → BULGU 1 geçerli (daha koruyucu seçilmeli)
3. §4.1.3.5.4'ün gerçek kapsamı → BULGU 1 muhtemelen geçersiz (kesme değeri alternatif yöntem)

Karar için **ECHA Guidance on Application of CLP Criteria** Bölüm 4 gerekiyor.  
Spesifik bölüm: §4.1.3.5 yöntem seçimi, kesme değeri tablosu ile toplamsal formül ilişkisi.

---

### Gerekli Belge

**ECHA Guidance on Application of CLP Criteria**  
Kaynak: https://echa.europa.eu/guidance-documents/guidance-on-clp  
İlgili bölüm: Chapter 4 — Hazardous to the aquatic environment  
Alt bölüm: §4.1.3.5 — Summation method vs generic concentration limits

> **Not:** Bu belgeye 2026-06-13 tarihinde HTTP 403 nedeniyle erişilemedi.
> Bir sonraki denetimden önce manuel olarak indirilmeli ve projeye eklenmeli.

---

## BULGU 3 — GHS07 H302 için üretilmiyor

**Durum:** ❌ GEÇERSİZ — Kod doğru

**Konu:** H302 (Akut Toks. Kat.4 oral) varlığında GHS07 piktogramının eksik göründüğü iddiası.

**ghs_pictogram.py davranışı:**
- Kural 1: GHS06 (kurukafa) varsa → GHS07 tamamen kaldırılır (CLP §1.2.1.2 kural a)
- Kural 2: GHS05 varsa ve GHS06 yoksa → H302/H312/H332/H317/H335/H336'dan biri varsa GHS07 KALIR

H302 varken GHS07'nin bastırılması yalnızca GHS06'nın da mevcut olduğu durumda gerçekleşir.
Bu CLP §1.2.1.2 dominance kuralının doğru uygulamasıdır.

---

*SDSPass sds-knowledge/kontrol.md — Güncelleme: 2026-06-13*
