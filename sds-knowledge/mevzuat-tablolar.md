# Mevzuat Tablolar — CLP / SEA / KKDİK Karışım Sınıflandırma Eşikleri
# Versiyon: 1.0 | Tarih: 2026-06-10
# Kaynak: CLP (AT) No 1272/2008 Ek-1 ≡ SEA Yönetmeliği Ek-1 ≡ KKDİK Ek-2
# Amaç: Audit AI'ın görüntü tabanlı PDF'lerde bulamadığı sayısal eşiklere
#        madde/tablo numarasıyla doğrudan erişmesi için metin referans dosyası.

---

## §3.1 — Akut Toksisite (Acute Toxicity)

### Tablo 3.1.1 — ATEmix Sınıflandırma Eşikleri

Karışım ATE'si (ATEmix) aşağıdaki değerlerin ALTINDA veya EŞİTİNDE kalırsa ilgili kategori uygulanır.

| Maruziyet Yolu | Kat. 1 | Kat. 2 | Kat. 3 | Kat. 4 |
|---|---|---|---|---|
| Oral (mg/kg) | ≤ 5 | ≤ 50 | ≤ 300 | ≤ 2000 |
| Deri (mg/kg) | ≤ 50 | ≤ 200 | ≤ 1000 | ≤ 2000 |
| İnhalasyon — Buhar (mg/L/4h) | ≤ 0,5 | ≤ 2,0 | ≤ 10 | ≤ 20 |
| İnhalasyon — Toz/Sis (mg/L/4h) | ≤ 0,05 | ≤ 0,5 | ≤ 1,0 | ≤ 5,0 |

H kodu ataması: Kat.1–2 → H300 / H310 / H330 | Kat.3 → H301 / H311 / H331 | Kat.4 → H302 / H312 / H332

### Tablo 3.1.2 — ATE Nokta Tahminleri (Formülde kullanılan değerler — sınır değil)

Bu değerler ATEmix formülünde (100/ATEmix = Σ Ci/ATEi) bileşen ATE'si bilinmediğinde kullanılır.

| H kodu | Kategori | Oral (mg/kg) | Deri (mg/kg) | İnhalasyon Buhar (mg/L/4h) | İnhalasyon Toz (mg/L/4h) |
|---|---|---|---|---|---|
| H300 | Kat. 1 | 0,5 | 5 | 0,05 | 0,005 |
| H300 | Kat. 2 | 5 | 50 | 0,5 | 0,05 |
| H301 | Kat. 3 | 100 | 300 | 3,0 | 0,5 |
| H302 | Kat. 4 | 500 | 1100 | 11 | 1,5 |
| H310 | Kat. 1 | — | 5 | — | — |
| H311 | Kat. 3 | — | 300 | — | — |
| H312 | Kat. 4 | — | 1100 | — | — |
| H330 | Kat. 1 | — | — | 0,05 | 0,005 |
| H331 | Kat. 3 | — | — | 3,0 | 0,5 |
| H332 | Kat. 4 | — | — | 11 | 1,5 |

**Formül:** ATEmix = 100 / Σ(Ci / ATEi)
Bilinmeyen bileşen toplamı > %10 ise revize formül: ATEmix = (100 − ΣC_bilinmeyen) / Σ(Ci / ATEi)

---

## §3.2 — Deri Aşındırıcı / Tahriş (Skin Corr./Irrit.)

### Tablo 3.2.3 — Karışım Kesme Değerleri

| Bileşen Sınıfı | H kodu | Karışım için eşik |
|---|---|---|
| Skin Corr. 1 / 1A / 1B / 1C | H314 | ≥ %5 → karışım H314 |
| Skin Irrit. 2 | H315 | ≥ %10 → karışım H315 |

**Toplamsal kural (H315 için):**
10 × Σ[Skin Corr. 1 bileşenler] + Σ[Skin Irrit. 2 bileşenler] ≥ %10 → karışım H315

Not: H314 bileşen, toplamsal göz değerlendirmesinde Eye Dam. 1 olarak sayılır.

---

## §3.3 — Göz Hasarı / Tahriş (Eye Dam./Irrit.)

### Tablo 3.3.3 — Karışım Kesme Değerleri

| Bileşen Sınıfı | H kodu | Karışım için eşik |
|---|---|---|
| Eye Dam. 1 veya Skin Corr. 1 | H318 | ≥ %3 → karışım H318 |
| Eye Irrit. 2 | H319 | ≥ %10 → karışım H319 |

**Toplamsal kural (H318 için):**
Σ[Eye Dam. 1 + Skin Corr. 1 bileşenler] ≥ %3 → karışım H318

**Toplamsal kural (H319 için):**
Σ[Eye Dam. 1 + Skin Corr. 1 bileşenler] ≥ %1 VE Σ tüm göz tahriş bileşenler ≥ %10 → karışım H319

**Dominance:** H314 varsa H318 etiket dominance kuralı gereği B2.2'ye yazılmaz; B2.1'de yer alır.

---

## §3.4 — Deri ve Solunum Sensitizasyonu

### Tablo 3.4.4 — Karışım Kesme Değerleri

| Bileşen Sınıfı | H kodu | Karışım için eşik |
|---|---|---|
| Resp. Sens. 1 / 1A / 1B | H334 | ≥ %0,1 |
| Skin Sens. 1A | H317 | ≥ %0,1 |
| Skin Sens. 1B veya 1 (genel) | H317 | ≥ %1,0 |

---

## §3.5 — Germ Hücre Mutajenitesi

### Tablo 3.5.3 — Karışım Kesme Değerleri

| Bileşen Sınıfı | H kodu | Karışım için eşik |
|---|---|---|
| Muta. 1A veya 1B | H340 | ≥ %0,1 |
| Muta. 2 | H341 | ≥ %1,0 |

---

## §3.6 — Kanserojenisite (Carcinogenicity)

### Tablo 3.6.4 — Karışım Kesme Değerleri

| Bileşen Sınıfı | H kodu | Karışım için eşik |
|---|---|---|
| Carc. 1A veya 1B | H350 | ≥ %0,1 |
| Carc. 2 | H351 | ≥ %1,0 |

---

## §3.7 — Üreme Toksisitesi (Reproductive Toxicity)

### Tablo 3.7.4 — Karışım Kesme Değerleri

| Bileşen Sınıfı | H kodu | Karışım için eşik |
|---|---|---|
| Repr. 1A veya 1B | H360 | ≥ %0,3 |
| Repr. 2 | H361 | ≥ %3,0 |
| Laktasyon | H362 | ≥ %0,3 |

---

## §3.8 — STOT Tek Maruziyet (STOT SE)

### Tablo 3.8.3 — Karışım Kesme Değerleri

| Bileşen sınıfı | Karışım H370 (STOT SE 1) eşiği | Karışım H371 (STOT SE 2) eşiği |
|---|---|---|
| STOT SE 1 (H370) | C ≥ %10 | %1 ≤ C < %10 |
| STOT SE 2 (H371) | — | C ≥ %20 |
| STOT SE 3 Uyuşturucu (H336) | — | C ≥ %20 → H336 |
| STOT SE 3 Solunum (H335) | — | C ≥ %20 → H335 |

---

## §3.9 — STOT Tekrarlı Maruziyet (STOT RE)

### Tablo 3.9.4 — Karışım Kesme Değerleri

| Bileşen sınıfı | Karışım H372 (STOT RE 1) eşiği | Karışım H373 (STOT RE 2) eşiği |
|---|---|---|
| STOT RE 1 (H372) | C ≥ %10 | %1 ≤ C < %10 |
| STOT RE 2 (H373) | — | C ≥ %10 |

**Önemli:** H373 bileşeninin karışımı H373 olarak sınıflandırabilmesi için konsantrasyonu **≥ %10** olmalıdır.
H373 bileşeni %10'dan düşük konsantrasyonda ise karışım H373 almaz (belirlenmiş SCL olmadıkça).

---

## §3.10 — Aspirasyon Tehlikesi (Aspiration Hazard)

### Tablo 3.10.4 — Karışım Kesme Değerleri

| Bileşen Sınıfı | H kodu | Karışım için eşik |
|---|---|---|
| Asp. Tox. 1 | H304 | ≥ %10 → karışım H304 |

Not: Kinematik viskozite > 20,5 mm²/s (40 °C) → H304 uygulanmaz.

---

## §4.1 — Sucul Çevre Toksisitesi (Aquatic Toxicity)

### §4.1.2.1 — Akut Sucul Toksisite (M-faktörlü toplamlı yöntem)

**Karışım H400 (Aquatic Acute 1) eşiği:**
Σ (Ci × Mi_akut) ≥ %0,1 → karışım H400

M-faktörü belirtilmemişse M = 1 (varsayılan).

### §4.1.3.5.4 — Kronik Sucul Toksisite: Kesme Değeri Yöntemi (Alternatif)

> **Not:** Bu tablo CLP §4.1.3.5.4'teki basit kesme değeri yaklaşımını gösterir.
> SDSPass bu yöntemi KULLANMAZ — §4.1.3.5.5 toplamsal yöntemini kullanır (aşağıya bakın).
> İki yöntem CLP'de **alternatif** olarak tanımlanmıştır; birbirini geçersiz kılmaz.

| Bileşen sınıfı | Karışım H410 (Chr.1) eşiği | Karışım H411 (Chr.2) eşiği | Karışım H412 (Chr.3) eşiği |
|---|---|---|---|
| H410 (Aquatic Chr. 1) | Σ(Ci × Mi_kronik) ≥ %0,1 | — | — |
| H411 (Aquatic Chr. 2) | — | Σ Ci ≥ %1,0 | — |
| H412 (Aquatic Chr. 3) | — | — | Σ Ci ≥ %1,0 |
| H413 (Aquatic Chr. 4) | — | — | — |
| H400 (sadece Akut, BCF yok) | Σ(Ci × Mi_akut) ≥ %0,1 | Σ(Ci × Mi_akut) ≥ %1,0 | Σ(Ci × Mi_akut) ≥ %10 |

---

### §4.1.3.5.5 — Kronik Sucul Toksisite: Toplamsal Yöntem (SDSPass kullanır — tercih edilen)

> Kaynak: CLP Ek-I §4.1.3.5.5, Tablo 4.1.2
> Eşik: **%25** (tüm formüller için)
> K1 = Σ(Ci × M_kronik) / 100 [H410 bileşenler]
> K2 = Σ(Ci) / 100            [H411 bileşenler]
> K3 = Σ(Ci) / 100            [H412 + H413 bileşenler]

| Koşul | Karışım sınıfı |
|---|---|
| K1 × M ≥ %25 (eşd. K1 ≥ 0,25) | H410 (Kronik 1) |
| 10×K1 + K2 ≥ %25 (eşd. ≥ 0,25) | H411 (Kronik 2) |
| 100×K1 + 10×K2 + K3 ≥ %25 (eşd. ≥ 0,25) | H412 (Kronik 3) |
| K1 + K2 + K3 ≥ %25 (eşd. ≥ 0,25) | H413 (Kronik 4) |

**Örnek:** H411 bileşen %20 konsantrasyonda (K1=0, K2=0,20):
- H411 kontrolü: 10×0 + 0,20 = 0,20 < 0,25 → H411 yok
- H412 kontrolü: 100×0 + 10×0,20 + 0 = 2,00 ≥ 0,25 → **Karışım H412** ✓ (CLP uyumlu)

**Audit notu:** Kesme değeri yönteminde %20 H411 bileşen → H411 görünür. Toplamsal yöntemde → H412 çıkar.
Bu bir hata değil; iki meşru yöntemin farklı sonuç vermesidir (CLP §4.1.3.5.3).

---

**M-faktörü:** L(E)C50 değerine göre tablo (CLP §4.1.3.5.5):

| Akut L(E)C50 (mg/L) | M_akut |
|---|---|
| 0,1 < L(E)C50 ≤ 1 | 1 |
| 0,01 < L(E)C50 ≤ 0,1 | 10 |
| 0,001 < L(E)C50 ≤ 0,01 | 100 |
| 0,0001 < L(E)C50 ≤ 0,001 | 1000 |

| Kronik NOEC (mg/L) | M_kronik |
|---|---|
| 0,1 < NOEC ≤ 1 | 1 |
| 0,01 < NOEC ≤ 0,1 | 10 |
| 0,001 < NOEC ≤ 0,01 | 100 |

---

## IMDG §2.10.3 — Deniz Kirletici (Marine Pollutant)

### Karışım Marine Pollutant Belirleme Kriterleri

IMDG Kodu §2.10.3 — iki ayrı test (bağımsız, CLP kronik hesabından farklı):

**Test 1 (Akut M-faktör tabanlı):**
Σ (Ci × Mi_akut) ≥ %0,1 → Deniz Kirletici

**Test 2 (H411 bileşenler için):**
Σ [H411 bileşen konsantrasyonları] ≥ %1,0 → Deniz Kirletici

H412 (CLP Kronik 3) bileşeni bu testte değerlendirilmez — IMDG §2.10.3 yalnızca akut M-faktörlü değerlendirme yapar.
H412 nedeniyle CLP kronik sınıflandırması olan bir karışım Marine Pollutant olmayabilir.

---

## SCL Notu — Maddeye Özel Kesme Değerleri

Yukarıdaki değerler genel (generic) kesme değerleridir.
Annex VI / KKDİK Ek-1'de madde için SCL (Specific Concentration Limit) belirlenmişse
SCL genel kesme değerinin önüne geçer (CLP Madde 10(3)).

Örnek: Bir madde için Annex VI'da H314 SCL = %2 ise,
genel %5 eşiği yerine %2 eşiği uygulanır.

---

*SDSPass sds-knowledge/mevzuat-tablolar.md — v1.0 | CLP (AT) No 1272/2008 Ek-1*
