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

**Sonuç:** ECHA kılavuzu okundu — **BULGU 1 KESİN OLARAK GEÇERSİZ.**

---

### Karar — KAPANDI ✅

**Tarih:** 2026-06-13  
**Kaynak:** ECHA Guidance on Application of CLP Criteria, Parts 4 and 5 (Version 4.0, Nov 2024)  
**Dosya:** `sds-knowledge/clp_parts4-5_en.pdf`

**Sayfa 63 — Relevance eşikleri:**
> *"The 'relevant components' of a mixture are those which are classified 'Chronic 2',
> 'Chronic 3' or 'Chronic 4' and present in a concentration of 1 % (w/w) or greater."*

`H411 bileşeni ≥ %1` kuralı bir **sınıflandırma eşiği değil**, toplamsal hesaba dahil edilme eşiğidir.
Bu eşiğin üzerindeki bileşen K2 havuzuna eklenir; sınıflandırmayı Tablo 4.1.2 formülü belirler.

**Sayfa 70 — §4.1.3.5.4 "daha koruyucu" kuralının gerçek kapsamı:**
> *"NOTE: If a mixture is classified in more than one way, the method yielding the most
> stringent result should be used."*

Bu kural `§4.1.3.5.2 additivity formülü` ile `§4.1.3.5.5 toplamsal yöntem` arasında geçerlidir.
Kesme değeri tablosu ayrı bir sınıflandırma yöntemi değildir.

**eco_engine.py davranışı: DOĞRU**
- %20 H411 bileşen → K2=0.20 → K2 < 0.25 → H411 yok; 10×K2=2.00 ≥ 0.25 → **H412 ✓**
- CLP Tablo 4.1.2 formülüyle birebir uyumlu

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

## BULGU 4 — H319 için P337+P313 eksik üretiliyordu

**Durum:** ✅ KAPANDI — Kod düzeltildi

**Tarih:** 2026-06-14 | **Ürün:** DIPOL 129 denetiminde tespit edildi

**Konu:** H319 (Göz Tahriş. 2) içeren karışımlarda `p_code_service` P337+P313'ü
üretmiyordu. Sebebi: REDUNDANCY_MAP ve SUPERSEDE_LABEL içinde P305+P351+P338 varlığında
P337+P313 redundant sayılıp düşürülüyordu.

**Mevzuat:** CLP Annex I Tablo 3.3.5 — H319 için zorunlu yanıt P kodları:
P305+P351+P338 VE P337+P313. Farklı senaryolar (anlık müdahale vs. kalıcı tahriş → doktor).

**Yapılan düzeltme (`p_code_service.py`):**
- `H_BASED_LABEL_FORCED['H319']` listesine P337+P313 eklendi
- `REDUNDANCY_MAP`: P305+P351+P338 varlığında P337+P313 artık silinmiyor
- `SUPERSEDE_LABEL`: aynı düzeltme etiket slot seçiminde de uygulandı

**Validator:** V021 olarak eklendi — `kontrol-kriterleri.md`

---

## BULGU 5 — B14 Deniz Kirletici hesap tablosunda M ve C×M sütunları boş

**Durum:** ✅ KAPANDI — Kod düzeltildi

**Tarih:** 2026-06-14 (tespit) / 2026-06-14 (kapatıldı) | **Ürün:** DIPOL 130 denetiminde tespit edildi

**Konu:** H411 bileşeni olan karışımlarda B14 deniz kirletici hesap tablosu üretiliyor
ancak M-faktörü atanmadığında M sütunu ve C×M sütunu boş kalıyordu. Tablo Test 2
(Σ C_H411 ≥ %1) yolunu kullanıyor ama bunu gösteremiyordu. Sonuç doğru; format belirsizdi.

**Örnek (DIPOL 130):**
- n-Hekzan H411, %20 → Σ(C_H411) = %20 ≥ %1 → Deniz Kirletici: Evet ✓
- Eskiden: M=— , C×M=— (Test 1 gibi görünüyordu, hesap yapılmamış izlenimi)

**Yapılan düzeltme (`pdf_sds_service.py`):**
- H411 satırında `_cxm_str = f"{_conc:.1f}*"` — konsantrasyon değeri C×M sütununda gösteriliyor
- Tablo altına dipnot eklendi: "* H411 (Sucul Kronik 2): M-faktör uygulanmaz. Test 2 kapsamında
  konsantrasyon doğrudan toplanır — eşik: Σ(C) ≥ %1,0 (IMDG §2.10.3)."

**Mevzuat:** IMDG §2.10.3 — sonuç doğru; format netleştirildi.

**Validator:** V022 — `kontrol-kriterleri.md`

---

*SDSPass sds-knowledge/kontrol.md — Güncelleme: 2026-06-14 (BULGU 5 kapatıldı)*
