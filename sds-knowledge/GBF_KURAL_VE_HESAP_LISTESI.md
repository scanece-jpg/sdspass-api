# GBF/SDS Hazırlayan AI İçin Kural ve Hesap Listesi
> Kaynaklar: CLP Tüzüğü Kılavuzu (Part 1-5), CLP Annex I/IV/VI, SEA Yönetmeliği, KKDİK Ek-2,
> ADR 2025, Türkiye OEL listesi — proje bilgi tabanındaki belgelerden derlenmiştir.
> Bu liste, bir GBF'nin B1-B16 bölümlerinin doğru üretilmesi için gereken tüm mantık adımlarını,
> eşikleri ve formülleri kapsar. Her madde kaynak belgeye atıfla verilmiştir.

---

## 0. Genel İş Akışı (Doğru Sıra Önemli)

```
1. Madde tanımlama → Annex VI'da doğru girdiyi bul (fiziksel form/Not B'ye dikkat)
2. Bileşen uyumlaştırılmış sınıflandırmasını al (varsa)
3. Uyumlaştırılmamış tehlike sınıfları için kendi-sınıflandırma (self-classification)
4. Her tehlike sınıfı için: SCL var mı? → varsa SCL kullan, GCL kullanma
5. Karışım sınıflandırmasını hesapla (additivity / summation / M-faktör / ATEmix)
6. B2.1 tam sınıflandırmayı oluştur (dominance uygulanmadan ÖNCEki tam liste)
7. B2.2 etiketi oluştur (dominance/redundancy kurallarını uygula)
8. P-kodlarını hazard class/kategoriye göre seç (Annex IV Tablo 6.1)
9. B3.2 bileşen tablosunu B2.1 ile çapraz-tutarlı doldur
10. B14 taşımacılığı B2 sonucuna göre türet (CLP-ADR eşleşme tablosu)
11. Format kontrolü (KKDİK Ek-2 16 bölüm)
```

---

## 1. Madde Tanımlama ve Annex VI Sorgulama

### 1.1 Girdi seçim kuralları

- **CAS No ile arama yeterli DEĞİL.** Annex VI'da bazı girdiler (özellikle Not B — sulu çözelti girdileri) CAS alanını **boş** bırakır, yalnızca EC No taşır. Hem CAS hem madde adı/EC No ile çapraz arama yapılmalı.
- **Aynı EC No'ya birden fazla Index No bağlı olabilir** (örn. hidrojen klorür: 017-002-00-2 = gaz formu, 017-002-01-X = sulu çözelti "hydrochloric acid ...%" formu). **Ürünün fiziksel/kimyasal formuna uygun girdi seçilmeli** — aksi halde tamamen yanlış alt kategori/SCL kullanılır.
- Not B girdileri: madde sulu çözelti halinde piyasaya sürülüyorsa kullanılmalı; GCL/SCL karşılaştırması seyreltilmemiş maddenin konsantrasyonuna göre yapılır (Not B tanımı, CLP Part 1 §1.1.10).
- Girdi bulunamazsa → kendi-sınıflandırma (self-classification) protokolüne geç.

### 1.2 Uyumlaştırılmış sınıflandırmanın zorunluluğu

- CLP Madde 4(1): Annex VI'da uyumlaştırılmış sınıflandırması olan bir madde için bu sınıflandırma **zorunlu kullanılır**, kendi-sınıflandırma ile değiştirilemez.
- **Minimum sınıflandırma (*) işareti:** Bazı Annex VI girdileri "*" ile işaretlidir — bu, mevcut verilerle daha şiddetli bir kategori gösteriliyorsa, o kategorinin kullanılması gerektiği anlamına gelir (CLP Part 1 §1.2.1).
- Uyumlaştırma bazı tehlike sınıflarını kapsamıyorsa (örn. sadece CMR+solunum duyarlılaştırıcı harmonize, diğerleri boş), **kalan tehlike sınıfları için kendi-sınıflandırma zorunludur** (CLP Madde 4(3), Recital 17).
- Safsızlık/katkı maddesi madde sınıflandırmasını daha şiddetli hale getiriyorsa, bu dikkate alınmalı; etiket adına "≥x% [safsızlık adı] içeren" eklenmeli (Annex VI §1.1.1.4).

---

## 2. Karışım Sınıflandırma Kuralları — Sağlık Zararları

### 2.1 Öncelik sırası (her tehlike sınıfı için)

1. Karışımın kendisi test edilmiş mi? → varsa doğrudan madde kriterleri uygulanır
2. Bridging principles (benzer test edilmiş karışım) uygulanabilir mi?
3. Bileşen verisine dayalı hesaplama (additivity/summation)

### 2.2 Cilt Aşınması/Tahrişi (Skin Corr./Irrit.)

**Genel Konsantrasyon Limitleri (GCL) — Tablo 3.2.3 (additivity uygulanabilirse):**

| Bileşen sınıfı | Karışım: Kategori 1 | Karışım: Kategori 2 |
|---|---|---|
| Skin Corr. 1A/1B/1C | ≥%5 | %1≤C<%5 |
| Skin Irrit. 2 | — | ≥%10 |
| (10×Skin Corr.1) + Skin Irrit.2 | — | ≥%10 |

**Alt-kategori belirleme notu:** 1A bileşenleri toplamı <%5 ama 1A+1B toplamı ≥%5 ise → karışım **1B**; 1A+1B<%5 ama 1A+1B+1C≥%5 ise → **1C**.

**Additivity uygulanamadığında (Tablo 3.2.4) — güçlü asit/baz, inorganik tuz, aldehit, fenol, surfaktan içeren karışımlar:**

| Bileşen | Konsantrasyon | Sonuç |
|---|---|---|
| pH ≤ 2 asit | ≥%1 | Skin Corr. Kategori 1 |
| pH ≥ 11,5 baz | ≥%1 | Skin Corr. Kategori 1 |
| Diğer aşındırıcı (1A/1B/1C) | ≥%1 | Kategori 1 |
| Diğer tahriş edici (Kat.2) | ≥%3 | Kategori 2 |

**🔑 KRİTİK ÖNCELİK KURALI — pH-ekstrem vs SCL çakışması:**

> "Where the mixture has an extreme pH value but the only corrosive/irritant ingredient present in the mixture is an acid or base with an **assigned SCL** (Annex VI veya tedarikçi tarafından Madde 10(1)'e göre belirlenmiş), then the mixture should be classified **according to the SCL**. pH of the mixture should **not** be considered a second time." *(clp_part3_en.pdf §3.3.3.2.1.1)*

→ **Uygulama sırası: Önce ilgili bileşenin Annex VI'da atanmış bir SCL'si var mı diye bak. Varsa SCL bağlayıcıdır, pH-ekstrem kuralına gerek yok. SCL yoksa VE karışım güçlü asit/baz içeriyorsa VE pH ölçülmüşse → pH-ekstrem kuralı (Tablo 3.2.4) uygulanır.**

**Asit/alkali rezervi istisnası:** pH-ekstrem kuralı uygulanacaksa bile, asit/alkali rezervi (tampon kapasitesi) verisi karışımın aslında aşındırıcı olmayabileceğini gösteriyorsa, bu in-vitro testle doğrulanmalı; doğrulama yapılmazsa varsayılan olarak Kategori 1 atanır (§3.2.3.2.1.1, Şekil 3.2).

### 2.3 Ciddi Göz Hasarı/Tahrişi (Eye Dam./Irrit.)

- **Cilt aşınması Kategori 1 → göz hasarı Kategori 1 otomatik dahildir** ama **etikette H318 AYRICA yazılmaz** (H314 metni zaten "causes severe skin burns **and eye damage**" içerir — redundancy). B2.1 tam sınıflandırmada H318 gösterilebilir/gösterilmelidir, ancak B2.2 etikette gösterilmez.
- Aynı GCL/SCL öncelik mantığı Skin Corr için geçerlidir; **cilt için geçerli SCL, göz için de otomatik olarak dikkate alınır** — ayrı bir göz SCL'si yoksa cilt SCL'sinden türetilir (Annex VI girdisinde genelde H314+H318/H319 birlikte SCL tablosunda listelenir).
- pH-ekstrem kuralı (ayrı, tekrar): pH≤2 veya ≥11,5 → Eye Dam. 1, asit/alkali rezervi verisi yoksa varsayılan.
- GCL Tablo 3.3.3 (additivity): Skin Corr.1A/1B/1C veya Eye Dam.1 bileşenleri ≥%3 → Eye Dam.1; %1≤C<%3 → Eye Irrit.2; Eye Irrit.2 bileşenleri ≥%10 → Eye Irrit.2.
- Tablo 3.3.4 (additivity uygulanamıyorsa): pH≤2/≥11,5 asit/baz ≥%1 → Eye Dam.1; diğer aşındırıcı ≥%1 → Kategori1; diğer tahriş edici ≥%3 → Kategori2.

### 2.4 Akut Toksisite (ATE / ATEmix hesabı)

**Formül:**
```
100 / ATEmix = Σ (Ci / ATEi)
```
- Ci = bileşen i'nin karışımdaki konsantrasyonu (% a/a veya h/h)
- ATEi = bileşen i'nin Akut Toksisite Tahmini
- Suya/şekere benzer toksik olmayan bileşenler formülden **hariç tutulur**
- Oral limit testinde 2000 mg/kg'da toksisite göstermeyen bileşenler **hariç tutulur**
- Bilinmeyen akut toksisiteye sahip bileşenlerin toplamı **>%10** ise, bu düzeltme formülde dikkate alınmalı (1 - bilinmeyen/100)

**ATE değeri yoksa dönüştürülmüş nokta tahmini (cATpE) — Tablo 3.1.2:**

| Yol | Kategori aralığı | cATpE |
|---|---|---|
| Oral (mg/kg) | Kat.1 (≤5) / Kat.2 (≤50) / Kat.3 (≤300) / Kat.4 (≤2000) | 0,5 / 5 / 100 / 500 |
| Dermal (mg/kg) | Kat.1(≤50)/Kat.2(≤200)/Kat.3(≤1000)/Kat.4(≤2000) | 5 / 50 / 300 / 1100 |
| Gaz (ppmV) | Kat.1(≤100)/Kat.2(≤500)/Kat.3(≤2500)/Kat.4(≤20000) | 10 / 100 / 700 / 4500 |
| Buhar (mg/l) | Kat.1(≤0,5)/Kat.2(≤2)/Kat.3(≤10)/Kat.4(≤20) | 0,05 / 0,5 / 3 / 11 |
| Toz/Sis (mg/l) | Kat.1(≤0,05)/Kat.2(≤0,5)/Kat.3(≤1)/Kat.4(≤5) | 0,005 / 0,05 / 0,5 / 1,5 |

**Sonuç kategori eşikleri (Tablo 3.1.1):**

| Yol | Kat.1 | Kat.2 | Kat.3 | Kat.4 |
|---|---|---|---|---|
| Oral (mg/kg) | ≤5 | 5-50 | 50-300 | 300-2000 |
| Dermal (mg/kg) | ≤50 | 50-200 | 200-1000 | 1000-2000 |
| Gaz (ppmV) | ≤100 | 100-500 | 500-2500 | 2500-20000 |
| Buhar (mg/l) | ≤0,5 | 0,5-2,0 | 2,0-10,0 | 10,0-20,0 |
| Toz/Sis (mg/l) | ≤0,05 | 0,05-0,5 | 0,5-1,0 | 1,0-5,0 |

**Özel durum — inhalasyon (gaz/buhar/toz karışık bileşenler):** Additivity formülü doğrudan uygulanamaz; her fiziksel form (gaz/buhar/toz-sis) için AYRI hesaplanır:
```
fraction = Σ (limit / ATEi) × Ci / 100
```
En şiddetli kategori, üç formun fraction toplamı ≥1 olduğu kategoridir.

**Uyumlaştırılmış ATE varsa** (madde harmonize sınıflandırmasında belirtilmişse), bu formülde **zorunlu kullanılır** — kendi ATE tahmini yerine geçmez.

**Çoklu maruziyet yolu:** Karışım birden fazla yol için farklı kategoriye giriyorsa (örn. oral Kat.4 + inhalasyon Kat.2), her ikisi de sınıflandırmaya girer; etiket **en şiddetli kategoriye ait piktogram+sinyal kelimeyi** kullanır, ama her iki H-kodu da (H302 + H330) yazılır.

### 2.5 Belirli Hedef Organ Toksisitesi — Tek Maruziyet (STOT SE)

**Kategori 1/2 — GCL (Tablo 3.8.3):**

| Bileşen | Karışım Kat.1 | Karışım Kat.2 |
|---|---|---|
| Kategori 1 STOT | ≥%10 | %1≤C<%10 |
| Kategori 2 STOT | — | ≥%10 |

- Kategori 1/2'de additivity **yoktur** — her bileşen tek başına eşiği geçerse karışım o kategoriye girer.

**Kategori 3 (narkotik etki + solunum yolu tahrişi) — additivity VAR, ayrı ayrı hesaplanır:**

- Genel eşik: **%20** (varsayılan GCL, madde bazında uzman kararıyla değiştirilebilir — §3.8.3.4.5)
- **H335 (solunum yolu tahrişi) ve H336 (narkotik etki) BİRBİRİNDEN BAĞIMSIZ toplanır** — aynı kategori altında olsalar da farklı etkilerdir, birbirinin yerine KULLANILAMAZ.
  ```
  Σ%(Kat.3-Narkotik bileşenler) ≥ %20 → H336
  Σ%(Kat.3-Solunum tahrişi bileşenler) ≥ %20 → H335
  ```
- Bir bileşenin Annex VI'da atanmış özel bir SCL'si varsa (örn. "STOT SE 3; H335: C≥%10"), bu **GCL'nin (%20) yerine geçer** ve doğrudan bağlayıcıdır.
- **Bileşenin taşıdığı spesifik H-kodu (H335 veya H336) karışıma AYNEN aktarılmalı** — motor tarafında H335↔H336 birbirinin yerine kullanılması bir hesaplama hatasıdır.

### 2.6 Aşındırıcılık/Tahriş — Genel Not

- Karışım pH bilgisi varsa VE güçlü asit/baz içeriyorsa, sınıflandırma gerekçesinde **hangi kuralın (SCL mi, pH-ekstrem mi) uygulandığı açıkça belgelenmeli.**

---

## 3. Karışım Sınıflandırma Kuralları — Çevresel Zararlar (Sucul Ortam)

### 3.1 M-Faktörü

- M-faktörü yalnızca **Akut Kategori 1** ve **Kronik Kategori 1** bileşenler için uygulanır.
- Annex VI'da madde için M-faktörü verilmişse **zorunlu kullanılır** (Madde 10(4)); verilmemişse üretici/ithalatçı kendi hesaplamalıdır (Madde 10(2)).

**M-faktör tablosu (L(E)C50'ye göre):**

| L(E)C50 aralığı (mg/l) | M-faktör |
|---|---|
| 0,1 < C ≤ 1 | 1 |
| 0,01 < C ≤ 0,1 | 10 |
| 0,001 < C ≤ 0,01 | 100 |
| 0,0001 < C ≤ 0,001 | 1.000 |
| 0,00001 < C ≤ 0,0001 | 10.000 |
| (10'un katları ile devam) | ... |

### 3.2 Toplamsallık (Summation) Yöntemi — Kronik

| Sınıflandırılan bileşenlerin toplamı | Karışım sınıfı |
|---|---|
| Kronik 1 × M ≥ %25 | Kronik 1 |
| (M×10×Kronik1) + Kronik2 ≥ %25 | Kronik 2 |
| (M×100×Kronik1) + (10×Kronik2) + Kronik3 ≥ %25 | Kronik 3 |
| Kronik1+2+3+4 toplamı ≥ %25 | Kronik 4 |

- **Daha şiddetli sınıflandırma daha az şiddetliyi geçersiz kılar** — Kronik 1 sonucu çıkarsa daha ileri hesaba gerek yok.
- Akut Kategori 1 için benzer mantık: Σ(% × M-faktör) > %25 → tüm karışım Akut 1.

### 3.3 Additivity Formülü (test verisi kısmi mevcutsa)

**Akut:**
```
L(E)C50m = Σ Ci / Σ (Ci / L(E)C50i)
```

**Kronik (hızlı/yavaş bozunan düzeltmesi ile):**
```
EqNOECm = (Ci + Cj) / [Σ(Ci/NOECi) + Σ(Cj/(10×NOECj))]
```
- Ci = hızlı bozunan bileşenler, Cj = hızlı bozunmayan bileşenler (10× ağırlıklandırma cezası alır)

### 3.4 Bilinmeyen bileşenler

- Sucul zararlılık için kullanılabilir bilgi olmayan bileşen(ler) varsa, karışım yalnızca bilinen bileşenlere göre sınıflandırılır ve GBF'ye şu ifade eklenir: *"Karışım, sucul ortama zararları bilinmeyen bileşenlerin %X'ini içermektedir."*

---

## 4. Etiketleme Kuralları (B2.2)

### 4.1 Dominance / Redundancy (Etikette H-kodu bastırma)

| Durum | Etikette görünen | B2.1'de (tam sınıflandırma) |
|---|---|---|
| H314 mevcut | H314 (H318 metne dahil, ayrıca yazılmaz) | H314 + H318 birlikte |
| H314 mevcut, H315 hesaplanmış olsa dahi | Yalnızca H314 (H315 uygulanmaz — mutually exclusive kategori sonucu) | Yalnızca H314 |
| Skin Corr.1 + Eye Dam.1 aynı anda | GHS05, "Tehlike" | H314+H318 |

### 4.2 Sinyal Kelime / Piktogram Seçimi

- Birden fazla tehlike sınıfı varsa, **en şiddetli kategori** piktogram+sinyal kelimeyi belirler (bkz. §2.4 çoklu maruziyet yolu örneği).
- "Tehlike" (Danger) ve "Uyarı" (Warning) aynı anda tetiklenmişse, yalnızca **Tehlike** etikette gösterilir.

### 4.3 P-Kodu Seçim Kuralları (CLP Annex IV, Tablo 6.1)

- Her P-kodunun tetiklenme koşulu **hazard class + kategori** ile eşleşmelidir — bu tablo satır satır kontrol edilmeden P-kodu eklenmemeli/kaldırılmamalı.
- **P260 örneği:** yalnızca Akut Toksisite-İnhalasyon **Kategori 1-2** ve STOT SE/RE **Kategori 1-2** için zorunlu. Kategori 3/4 için P260 **zorunlu DEĞİLDİR** — bu ayrım motor tarafında sık karışan bir noktadır.
- Aşındırıcı (Skin Corr.1) için standart P-kod seti (Annex I Tablo 3.2.5):
  - Önlem: P260, P264, P280
  - Müdahale: P301+P330+P331, P303+P361+P353, P363, P304+P340, P310, P321, P305+P351+P338
  - Depolama: P405 | Bertaraf: P501
- Zorunlu P-kodu sayısı 6'yı aşabilir — bu bir HATA değildir (CLP Madde 22(4)).

### 4.4 Etiket ↔ Bileşen Tutarlılığı

- B3.2'de bileşene atanan spesifik H-kodu (örn. H335) ile B2.1/B2.2'de karışıma yansıyan H-kodu (örn. H336) **birebir tutarlı** olmalı; motor bunları birbirinin yerine geçirmemeli.

---

## 5. Bileşim Bildirimi (B3.2) Eşikleri — KKDİK Ek-2

**Karışımda listelenmesi gereken madde/zararlılık sınıfı ve konsantrasyon eşiği:**

| Zararlılık sınıfı | Eşik (%) |
|---|---|
| Akut Toksisite Kat.1,2,3 | ≥0,1 |
| Akut Toksisite Kat.4 | ≥1 |
| Cilt aşınması/tahrişi Kat.1 (1A/1B/1C), Kat.2 | ≥1 |
| Ciddi göz hasarı/tahrişi Kat.1, Kat.2 | ≥1 |
| Solunum/cilt hassasiyeti | ≥0,1 |
| Eşey hücre mutajenitesi 1A/1B | ≥0,1 |
| Eşey hücre mutajenitesi Kat.2 | ≥1 |
| Kanserojenite 1A/1B/2 | ≥0,1 |
| Üreme tox. 1A/1B/2 + laktasyon etkisi | ≥0,1 |
| BHOT Tek Mar. Kat.1,2 | ≥1 |
| BHOT Tekrarlı Mar. Kat.1,2 | ≥1 |
| Aspirasyon zararı | ≥10 |
| Sucul Akut Kat.1 | ≥0,1 |
| Sucul Kronik Kat.1 | ≥0,1 |
| Sucul Kronik Kat.2,3,4 | ≥1 |
| Ozon tabakası zararlısı | ≥0,1 |

- **PBT/vPvB veya işyeri maruziyet limiti olan maddeler:** ≥%0,1 (sınıflandırma kriteri karşılanmasa dahi listelenir).
- **Sınıflandırılmamış karışımlar için** (SEA kriterlerini karşılamıyorsa): gaz-dışı karışımlarda ağırlıkça ≥%1, gaz karışımlarında hacimce ≥%0,2 olan maddeler (insan sağlığı/çevre zararlısı olarak sınıflandırılmışsa veya işyeri maruziyet limiti varsa) listelenir.
- **Konsantrasyon gizliliği:** CLP Madde 24(2) uyarınca ticari sır gerekçesiyle aralık verilebilir, ancak hesaplamalarda gerçek (nokta) değer kullanılmalı — aralığın en muhafazakar ucu değil.

---

## 6. Fiziksel Zararlar — Özel Notlar

- **Fiziksel zararlar additivity/summation ile hesaplanmaz** — doğrudan karışımın kendisi test edilerek belirlenir (istisnai bazı durumlar hariç, örn. oksitleyici, patlayıcı).
- **Fiziksel form bağımlılığı:** Bir maddenin harmonize fiziksel tehlike sınıfı (örn. "Press. Gas") yalnızca o madde/karışım **gerçekten o fiziksel halde** ise uygulanır. CLP tanımı: Gaz = 50°C'de buhar basıncı >300 kPa VEYA 20°C'de 101,3 kPa'da tamamen gaz halinde. Sulu çözelti/sıvı halindeki bir ürün için gaz-bazlı fiziksel tehlike (H280 vb.) uygulanmaz, bileşenin saf/gaz formundan miras alınmaz.
- H-kodu ↔ fiziksel parametre eşleştirmesi (parlama noktası, pH, viskozite vb.) her zaman SEA/CLP Annex I ilgili bölümünden okunmalı, sabit kodlanmamalı.

---

## 7. Taşımacılık (B14)

### 7.1 CLP → ADR Fiziksel Zarar Eşleşmesi

- Class 8 (Aşındırıcı): CLP Skin Corr. sınıflandırmasıyla ilişkilendirilir — ancak **doğrudan otomatik eşleme değildir**; ADR §2.2.8 kendi test/pH/temas-süresi kriterlerine göre PG (I/II/III) atar.
- **Tasarım kararı:** ADR/IMDG/IATA motoru karışımın pH değerine BAKMAZ; yalnızca B2.1'in ürettiği nihai H kodlarını kullanır. B2.1'de H314 VAR → ADR Sınıf 8; H314 YOK (yalnızca H315/H319) → ADR Sınıf 8 yok. pH'a bakıp ikinci kez Sınıf 8 atamak çifte hesaplama hatasıdır.
- Diğer fiziksel zarar sınıfları (Gazlar, Alevlenir sıvılar, vb.) için CLP-ADR eşleşme tablosu kullanılır (bkz. clp_part2_en.pdf Tablo I.1).

### 7.2 Deniz Kirletici (Marine Pollutant) — B14 özel hesap

- IMDG §2.10.3 ile ADR §2.2.9.1.10 **özdeştir** (ikisi de UN Model Regulations §2.9.3'ten türer) — ADR dosyası bu amaçla referans olarak kullanılabilir.
- Hesap: **Σ(C × M_akut)** — kronik CLP hesabından **bağımsızdır**. H412 (Kronik 3) tek başına marine pollutant kriteri değildir.
- Sonuç "Uygulanamaz" ise VE B14 hesap tablosu da eşiği geçmiyorsa → tutarlı, hata yok. İkisi çelişiyorsa → bulgu.

### 7.3 Öncelik Tabloları (birden fazla tehlike sınıfı — hangi Class/PG öncelikli)

- ADR §2.1.3.10/Tablo (örn. adr2025_part2_213_precedence.md): birden fazla tehlike sınıfı çakıştığında (örn. Sınıf 3 + Sınıf 6.1 + Sınıf 8) satır/sütun kesişim tablosuyla öncelik belirlenir; sabit "en yüksek sınıf kazanır" varsayımı yapılmamalı, tablo kullanılmalı.

---

## 8. Maruziyet Kontrolü (B8) — OEL

- Kaynak öncelik sırası: (1) Kimyasal Maddelerle Çalışmalarda Sağlık ve Güvenlik Önlemleri Hakkında Yönetmelik Ek-1, (2) Kanserojen/Mutajen Maddeler Yönetmeliği, (3) diğer ulusal limitler, (4) biyolojik limit değerleri.
- Her madde için TWA (8s) ve varsa STEL (15dk) hem ppm hem mg/m³ birimiyle verilmeli; kaynak yönetmelik/tarih/sayı GBF'de atıfla belirtilmeli.
- KKD/mühendislik kontrol önerileri madde bazlı zararlılığa (H-kodlarına) dayanmalı, jenerik ifade kullanılmamalı.

---

## 9. Format/Yapı Kontrol Listesi (KKDİK Ek-2)

- [ ] 16 bölümün tamamı mevcut ve sırayla
- [ ] B1: Ürün tanımlayıcı + tedarikçi + acil durum telefonu (UZEM 114 dahil)
- [ ] B2.1 ve B2.2 tutarlı (dominance kuralları hariç fark yok)
- [ ] B3.2: CAS/EC/KKDİK No + konsantrasyon + sınıflandırma her bileşen için tam
- [ ] B9 fiziksel parametreler + kullanılan test yöntemi/standart referansı
- [ ] B11 toksikolojik veri, ATEmix hesabı varsa gösterilmiş
- [ ] B14 UN No / Sınıf / PG / deniz kirletici sonucu tutarlı
- [ ] B15 geçerli TR mevzuatına atıflar (KKDİK, SEA, ADR, Atık Yönetimi vb.)
- [ ] B16 revizyon geçmişi + kısaltmalar + tam H/P ifadeleri

---

## 10. AI'nın Kendi Kendini Denetlemesi İçin Kritik Kontrol Noktaları

Aşağıdaki maddeler, bu projede tespit edilen gerçek motor hatalarından türetilmiştir — bir SDS-üretici AI'nın çıktısını vermeden önce kendi kendine sorması gereken sorulardır:

1. **Annex VI sorgusu CAS-only mu yapıldı?** → EC No/isim ile de çapraz kontrol et; Not B (sulu çözelti) girdilerini kaçırma.
2. **Doğru fiziksel form girdisi mi kullanıldı?** (gaz vs. çözelti, farklı Index No/alt kategori/SCL taşıyabilir)
3. **SCL var mı, yok mu önce kontrol edildi mi?** (Annex VI SKS alanı boşsa GCL'ye, strong acid/base ise pH-ekstrem kuralına geç — ama SCL varsa pH'ı ikinci kez değerlendirme.)
4. **B2.1'deki her H-kodunun B3.2'de izlenebilir bir bileşen dayanağı var mı?** (Yoksa ayrı bulgu.)
5. **B3.2 bileşen H-kodu ile B2.1/B2.2 karışım H-kodu birebir aynı mı?** (H335↔H336 gibi kategori-içi farklı kodların karıştırılmadığından emin ol.)
6. **ATEmix hesabı H332/H331 gibi akut toksisite kodları için B11'de gösteriliyor mu?**
7. **P-kod seçimi Annex IV Tablo 6.1'deki kategori sütunuyla (1-2 mi, 3-4 mü) birebir kontrol edildi mi?**
8. **Etikette dominance uygulanan H-kodlar (H318, fazladan H315 vb.) doğru bastırıldı mı — ama B2.1'de hâlâ mevcutlar mı?**
9. **B14 sonucu B2 sınıflandırmasıyla tutarlı mı?** (B2'de aşındırıcı çıkan bir karışım "tehlikeli madde değildir" diyemez.)
10. **M-faktör/SCL Annex VI'da veriliyorsa kendi hesaplanan değerle DEĞİL, Annex VI değeriyle mi kullanıldı?**
11. **Üçüncü taraf denetim yapılıyorsa** (gerçek konsantrasyon bilinmiyor, yalnızca gizlilik aralığı görünüyorsa): eşik kontrolü aralığın üst sınırıyla (worst-case) yapılmalı — ancak SDS'yi hazırlayan taraf her zaman gerçek nokta değeri kullanmalıdır.

---

## 11. Kritik Mevzuat Referansları ve Sabit Kurallar

> Bu bölüm, agent tarafından SDS yazılırken sık hata yapılan noktalara ait kesin
> değerleri ve kuralları içerir. Buradaki bilgiler ezbere YAZILMAZ — bu bölümden okunur.

### 11.1 TR Mevzuat Referansları (B15 için)

| Yönetmelik | Resmi Gazete | Açıklama |
|---|---|---|
| KKDİK | **30105 / 11 Temmuz 2017** | Kimyasal Maddeler Hakkında Yönetmelik |
| SEA | **28848 / 26 Aralık 2013** | Sınıflandırma, Etiketleme ve Ambalajlama Yönetmeliği |
| ADR (TR onayı) | 2025 yılı baskısı | Tehlikeli Malların Karayoluyla Taşınması |
| Kimyasal Maddelerle Çalışma (OEL) | **29204 / 12 Ağustos 2013** | Ek-1: TWA/STEL limitleri |
| Kanserojen/Mutajen Maddeler | 26792 / 2007 | CMR madde sınırları |
| Acil durum telefonu | UZEM: **114** (7/24, ücretsiz) | B1'e mutlaka yazılır |

### 11.2 UN Numarası Kuralı (B14 için)

- **UN numarası `detect_adr` tool sonucundan alınır.** Motor "not_regulated: true" döndürdüyse "Tehlikeli madde değildir" yazılır.
- **Hiçbir zaman ezberden/tahminden UN numarası yazılmaz.** Motor çağrılmadan B14 tamamlanamaz.
- Ortak referans: HCl sulu çözelti → UN 1789 | NaOH çözelti → UN 1824 | H₂SO₄ → UN 1830 (bunlar örnektir, motordan teyit alınır).

### 11.3 Sulu Çözelti Fiziksel Tehlike Kuralları

- **Sulu çözelti (aqueous solution) H260/H261 (Su ile tepkimeli) almaz** — bu kodlar yalnızca katı/saf madde formuna aittir, çözeltiye miras almaz.
- **Sulu çözelti H280/H281 (Basınçlı gaz) almaz** — gaz formu sulu çözeltiye aktarılmaz (CLP §6 Fiziksel zararlar, fiziksel form bağımlılığı).
- HCl sulu çözeltisi (%18) için B10'da "Su ile tepkimeli" uyarısı **yazılmaz**.

### 11.4 H335 Karışım Eşiği (HCl örneği)

- HCl (7647-01-0) Annex VI'da STOT SE 3 H335 için SCL: **C ≥ %10**
- %18 HCl için H335 eşiği aşılmıştır → **B2.1 karışım tablosuna H335 eklenir**, B2.2 etikette de gösterilir.
- B2'ye yansıtılmazsa B3 ile tutarsızlık oluşur — bu bir hata.

### 11.5 Sıkça Karıştırılan Noktalar

| Konu | Yanlış | Doğru |
|---|---|---|
| KKDİK no | "32345/2023" | **30105/2017** |
| UN numarası | Ezberden yaz | Motor sonucunu kullan |
| HCl sulu çözelti B10 | "Su ile ekzotermik reaksiyon" | Hayır — sulu çözeltidir, H260/H261 yok |
| H318 etikette | Her zaman yaz | H314 varsa H318 etiketten çıkar (B2.1'de kalır) |
| P-kodu sayısı | 6'yı geçemez | Yanlış — geçebilir (CLP Madde 22(4)) |

---

*Bu belge, proje bilgi tabanındaki CLP Kılavuzu Part 1-5, CLP Annex I/IV/VI, SEA Yönetmeliği,
KKDİK Ek-2 ve ADR 2025 belgelerinden derlenmiştir. Yeni mevzuat/ATP güncellemelerinde
ilgili tablo ve eşik değerleri güncel Annex VI/Annex I sürümüyle yeniden doğrulanmalıdır.*
