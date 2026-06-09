# SDSPass — Hesaplama Motoru Kontrol Kriterleri

> Bu dosya Claude.ai Project'te SDS PDF'ini kontrol ederken başvuru kaynağıdır.
> Her motor için: ne kontrol edilir, hangi hata nasıl görünür, nasıl raporlanır.

---

## B2.1 — Sınıflandırma Tablosu

**Motorlar:** `clp_service`, `physical_engine`, `stot_engine`, `eco_engine`

### Kontrol soruları:
1. Tabloda her tehlike sınıfı için hem TR hem EN sütunu var mı?
2. Sucul tehlike varsa (H400/H410/H411) tabloda "Sucul çevre..." satırı görünüyor mu?
3. STOT varsa (H370/H371/H372/H373) "Hedef organ..." satırı var mı?
4. Patlayıcı/oksitleyici H kodu varsa fiziksel tehlike satırı var mı?
5. Tablo "Sınıflandırma yapılmamıştır" diyorsa ama B2.2'de H kodu varsa → çelişki.

### Kırmızı bayraklar:
- B2.1'de H400 var, B2.2'de GHS09 piktogram yok → motor senkron sorunu
- "Sınıflandırma yok" + B2.2'de H kodu → hata
- ATE değerleri aşırı düşük/yüksek (< 1 mg/kg veya > 50.000 mg/kg) → veri sorunu

---

## B2.2 — Etiket Unsurları (Sinyal, Piktogram, H/P Kodları)

**Motorlar:** `clp_service` (h_codes), `ghs_pictogram`, `p_code_service`, `euh_service`

### Kontrol soruları:
1. **Sinyal kelimesi** doğru mu?
   - Danger H kodları (H300, H301, H310, H314, H318, H340, H350, H360, H370, H372, H224, H225) → "Tehlike / Danger"
   - Diğerleri → "Uyarı / Warning"
2. **Piktogramlar** H kodlarıyla örtüşüyor mu?
   - H400/H410/H411 → GHS09 (çevre)
   - H314/H318 → GHS05 (aşındırıcı)
   - H225/H226 → GHS02 (alev)
   - H330/H331/H332 → GHS06 (kuru kafa)
3. **Her H kodu için hazard statement** var mı?
   - Özellikle H400 ifadesi ("Sucul organizmalar için çok toksik") görünüyor mu?
4. **P kodları** H kodlarına uygun mu?
   - H314 → P280, P301+P330+P331, P310 zorunlu
   - H400/H410 → P273, P391 zorunlu
   - H225/H226 → P210 zorunlu
5. **EUH kodları** varsa ifadeleri yazıyor mu?
6. P kodu sayısı 6'yı aşıyorsa — bu **ihlal değil**, CLP Md. 22(4) uyarınca zorunlu olabilir.

### Kırmızı bayraklar:
- H400 var → GHS09 yok → piktogram motoru sorunu
- H314 var → P310 yok → p_code_service sorunu
- H400 var → P273 yok → p_code_service sorunu
- Sinyal kelimesi "Warning" ama H300 var → clp_service sorunu

---

## B3 — Bileşim / İçerik Bilgisi

**Motorlar:** `substance_lookup`, `concentration_ranges`, `svhc_service`

### Kontrol soruları:
1. Her bileşen için CAS numarası, EC numarası, konsantrasyon aralığı var mı?
2. Konsantrasyon aralıkları KKDİK EK-2 B3'e uygun mu? (Örn: %10-25 değil %10-<25)
3. Konsantrasyon aralıklarının toplamı %100'ü mantıklı kapsıyor mu?
4. SVHC maddesi varsa "Aday Liste" notu var mı?
5. KKDİK Ek-6'daki sınıflandırma ile tablodaki sınıflandırma örtüşüyor mu?
6. CLP Annex VI'daki limit konsantrasyonlar dikkate alınmış mı?

### Kırmızı bayraklar:
- EC numarası boş veya "Bilinmiyor" → reach_db sorunu
- Konsantrasyon aralığı ">%99" ama birden fazla bileşen var → veri hatası
- SVHC bileşen var ama B15'te kayıt no yok

---

## B4–B7 — İlk Yardım / Yangın / Kaza / Elleçleme

**Motor:** `sds_sentence_service`, `p_code_service`

### Kontrol soruları:
1. **B4 (İlk Yardım):** Maruz kalma yollarının hepsi var mı? (göz, deri, soluma, yutma)
   - H314 varsa → göz ve deri için acil yıkama talimatı zorunlu
   - H330/H331 varsa → soluma için "temiz havaya çık + tıbbi yardım" zorunlu
2. **B5 (Yangın):** Uygun söndürücü maddeler belirtilmiş mi?
   - H225/H226 varsa → köpük, CO2, kuru kimyasal
   - Su reaktif (H260/H261) varsa → "suyla söndürmeyin" uyarısı
3. **B6 (Kaza):** Döküntü için toprak/su ayrımı var mı?
4. **B7 (Elleçleme):** Depolama sıcaklık sınırı ve bağdaşmayan maddeler belirtilmiş mi?

### Kırmızı bayraklar:
- H314 var → B4'te "hemen tıbbi yardım" yok
- H226 var → B5'te yanıcı sıvı söndürme talimatı yok
- B7 tamamen boş/genel

---

## B8 — Maruziyet Kontrolü / KKE

**Motorlar:** `tr_oel_service`, `ppe_engine`, `sds_sentence_service`

### Kontrol soruları:
1. **B8.1 OEL tablosu:**
   - Her bileşen için TWA ve/veya STEL değeri var mı?
   - Değerler mg/m³ ve ppm cinsinden mi?
   - Kaynak "Türkiye KKDİK" olarak gösteriliyor mu?
2. **B8.2 KKE:**
   - El koruma: Eldiven malzemesi belirtilmiş mi? (nitril, neopren, vb.)
   - Göz koruma: Gözlük tipi (kimyasal gözlük / siperlik)?
   - Solunum: H330/H331/H334 varsa solunum maskesi tipi belirtilmiş mi?
   - H334 varsa → SCBA veya tam yüz maskesi zorunlu

### Kırmızı bayraklar:
- OEL tablosu boş ama bilinen bileşenler var (NaOH, HCl vb.) → tr_oel_service sorunu
- KKE "gerekmiyor" ama H314 (aşındırıcı) var → ppe_engine sorunu
- H334 var → solunum koruyucu belirsiz/yetersiz

---

## B9 — Fiziksel ve Kimyasal Özellikler

**Motorlar:** `physical_engine`, `phys_props_parser`, `pubchem_phys_service`

### Kontrol soruları:
1. Parlama noktası: H226 varsa ≤60°C mi? H225 varsa ≤23°C mi?
2. Viskozite: H304 varsa viskozite değeri var mı ve <20 mm²/s mi?
3. pH: H314 (aşındırıcı) varsa pH <2 veya >11.5 mi?
4. Yoğunluk ve çözünürlük birbiriyle fiziksel olarak uyumlu mu?
   - Çözünürlük (mg/L) < Yoğunluk × 1.000.000 olmalı
5. Kaynama noktası: H225 için <35°C mi?

### Kırmızı bayraklar:
- Parlama noktası yok ama H226 var → V001 hatası
- pH 7 ama H314 var → V006 uyarısı (nötralizasyon veya veri hatası)
- Viskozite yok ama H304 var → V003 hatası

---

## B11 — Toksikoloji Bilgisi

**Motorlar:** `stot_engine`, `clp_service` (ATE), `sds_sentence_service`

### Kontrol soruları:
1. ATE (Akut Toksisite Tahmini) hesabı var mı?
   - Değer LD50 mg/kg veya LC50 mg/L cinsinden mi?
2. STOT SE/RE varsa hangi organ(lar) etkilendiği belirtilmiş mi?
3. H350 (kanserojen) varsa IARC/NTP sınıfı ve açıklama var mı?
4. H360 (üreme toksik) varsa "Üreme sistemine zarar verebilir" metni var mı?
5. Maruz kalma yollarına göre toksikoloji açıklaması var mı? (deri, soluma, yutma)

### Kırmızı bayraklar:
- H301 var → B11'de "LD50 değeri bilinmiyor" → eksik veri
- STOT RE var → hedef organ boş
- ATE hesabı yok ama akut toksisite H kodu var

---

## B12 — Ekoloji Bilgisi

**Motorlar:** `eco_engine`, `ecological_service`

### Kontrol soruları:
1. **B12.1 Zehirlilik:** H400/H410/H411 sınıfı doğru yazıyor mu?
   - "Sucul Akut 1" veya "Sucul Kronik 1/2/3" gibi tam sınıf adı var mı?
   - "Sınıflandırma yok" yazıyorsa B2.1'de sucul H kodu var mı? → Çelişki
2. **B12.2 Kalıcılık/Biyobozunurluk:** "Biyolojik olarak parçalanabilir/parçalanamaz" var mı?
3. **B12.3 Biyobirikim:** Log Kow değeri varsa değerlendirme var mı?
4. **B12.4 Toprak hareketliliği:** En azından "veri yok" yazıyor mu?
5. **B12.5 PBT/vPvB:** Sonuç net mi? ("PBT değildir" veya "PBT kriterleri karşılanmaktadır")
6. **M-Faktörü tablosu:** H400/H410 bileşeni varsa M-faktörü tablosu var mı?

### Kırmızı bayraklar:
- B2.1'de H400 var, B12.1'de "Sınıflandırma yok" → eco_engine/ecological_service senkron sorunu
- M-Faktörü tablosu boş ama H400 bileşeni var

---

## B14 — Taşımacılık

**Motor:** `transport_engine`

### Kontrol soruları:
1. UN numarası doğru mu? (karışım için UN3082 sucul çevre tehlikesi gibi)
2. ADR sınıfı H kodlarıyla uyumlu mu?
   - H225/H226 → ADR Sınıf 3 (yanıcı sıvı)
   - H400/H410 (çevre tehlikesi) → "Çevre tehlikesine zararlı" ek uyarı
3. IMDG ve IATA sütunları dolu mu?
4. Ambalaj grubu (PG I/II/III) belirtilmiş mi?

### Kırmızı bayraklar:
- ADR "N/A" ama H225 var → transport_engine sorunu
- UN numarası yok ama tehlikeli madde → zorunlu

---

## B15 — Mevzuat Bilgisi

**Motorlar:** `tr_mevzuat_service`, `svhc_service`, `reach_db`

### Kontrol soruları:
1. KKDİK kayıt numarası var mı? (bileşen için)
2. REACH kayıt numarası (01-XXXX...) doğru formatta mı?
3. SVHC bileşen varsa "Yetkilendirme Listesi" referansı var mı?
4. Türkiye-spesifik mevzuat atıfları doğru mu? (KKDİK, SEA Yönetmeliği)

---

## Genel Çapraz Kontroller (sds_validator)

`sds_validator.py` şu kontrolleri otomatik yapar — PDF'de doğrulama raporu varsa bakın:

| Kod | Kural |
|-----|-------|
| V001 | H226 var → parlama noktası zorunlu |
| V002 | H226 ama parlama noktası >60°C |
| V003 | H304 var → viskozite zorunlu |
| V004 | H304 ama viskozite >20 mm²/s |
| V005 | H314 var → pH önerilir |
| V006 | H314 ama pH 2–11.5 arası (aşındırıcı eşiği dışı) |
| V009 | H272 var → B10'da bağdaşmayan maddeler belirtilmeli |
| V010 | H260/H261 var → B7'de nem uyarısı |
| V011 | CMR madde → B8'de özel KKE |
| V012 | H334 var → SCBA/tam yüz maskesi |
| V013 | 6'dan fazla P kodu (CLP 22(4) — zorunluysa geçerli) |
| V014 | Danger H kodu var ama sinyal "Warning" |
| V016 | Çözünürlük > yoğunluk × 10⁶ (fizik imkânsız) |

---

*Son güncelleme: 2026-06-09*
