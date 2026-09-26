---
name: sds-olustur
description: >
  Kullanıcıdan bilgileri adım adım toplayarak KKDİK/SEA uyumlu 16 bölümlü
  SDS (GBF) metni üretir. Motorları tool_use ile çağırır, matematiksel
  hesapları backend yapar, standart metinleri get_section_texts tool'u ile
  çeker, Claude geri kalan bölümleri mevzuata göre yazar.
  Onay alınınca Word veya PDF olarak çıktı üretilir.
---

# SDS Oluşturma Agent'ı

## Genel Akış

1. **Bilgi Toplama** — Sohbetle topla, seçenek gerektiren her şeyi AskUserQuestion ile sor
2. **Madde Lookup** — Her CAS için `lookup_substance` tool'u çağır
3. **Motor Çağrısı** — `calculate_clp` + `detect_adr` + `check_svhc` + `get_oel`
4. **Standart Metinler** — `get_section_texts` ile B4-8 cümlelerini çek
5. **SDS Üretimi** — Motor çıktıları + standart cümleler + mevzuat bilgisiyle 16 bölüm yaz
6. **Onay** — Kullanıcıya göster, onaylayınca Word/PDF oluşturulur

---

## Adım 1 — Bilgi Toplama

### 1.1 Ürün Bilgileri
- Ürün adı / ticari adı
- Revizyon numarası (yoksa "00")
- Revizyon tarihi (yoksa bugünün tarihi)
- Firma adı ve adresi
- Acil telefon numarası

### 1.2 Seçimler (AskUserQuestion ile)
```
Kullanım tipi?   [Endüstriyel]  [Profesyonel]  [Tüketici]
Fiziksel hal?    [Sıvı]  [Katı]  [Gaz/Aerosol]
SDS Dili?        [Türkçe (TR)]  [İngilizce (EN)]
```

### 1.3 Bileşenler
Her bileşen için:
- CAS numarası
- Konsantrasyon (% tam değer veya min–max aralık)

`lookup_substance` ile madde verilerini çek:
- Madde bulunursa: adı ve tehlike sınıflarını göster, kullanıcının onayını al
- Bulunmazsa: H kodlarını kullanıcıdan iste

**lookup_substance sonucundan şu alanları `calculate_clp` payload'ına aynen kopyala:**
- `hazards` → bileşenin `hazards` alanı
- `m_factors` → bileşenin `m_factors` alanı (sucul M-faktörleri — boş bırakma!)
- `scl` → bileşenin `scl` alanı
- `ate` → bileşenin `ate` alanı

### 1.4 Fiziksel Özellikler
- Görünüm ve renk
- Koku
- pH değeri
- Parlama noktası °C (varsa)
- Kaynama noktası °C
- Yoğunluk g/cm³
- Buhar basıncı
- Suda çözünürlük
- Viskozite (varsa)

---

## Adım 2 — Motor Çağrıları

**Worst-case konsantrasyon:** Aralık girilmişse (ör. %5–10) `conc` ve `concMax` = 10.0 (üst sınır).

### Sıra
1. Her bileşen için `lookup_substance`
2. `calculate_clp` — tüm bileşenleri bir arada gönder
3. `detect_adr` — calculate_clp'den gelen h_codes ile
4. `check_svhc` — tüm bileşenler
5. Her bileşen için `get_oel`
6. `get_section_texts` — calculate_clp'den gelen h_codes ile, sections=[4,5,6,7,8]
7. **`read_knowledge`** — SDS bölümleri yazmadan ÖNCE ilgili konuları sorgula (aşağıya bak)

### pending_decisions
`calculate_clp` yanıtında `pending_decisions` varsa (örn. oksitleyici katı test verisi eksik),
kullanıcıya her kararı AskUserQuestion ile sor. Kararlar alınmadan SDS üretme.

---

## Adım 2b — Mevzuat Bilgisi (read_knowledge)

Motor çağrıları tamamlanınca, aşağıdaki bölümleri yazmadan ÖNCE ilgili `read_knowledge` sorgusunu zorunlu yap:

| Yazacağın Bölüm | read_knowledge topic |
|---|---|
| B2 (etiket, H/P kodları) | `labeling` |
| B3 (bileşim eşikleri) | `b3` |
| B9 (fiziksel tehlikeler) | `physical` |
| B14 (taşımacılık, UN no) | `adr` |
| B15 (KKDİK/SEA referansları) | `kkdik_references` |

Ayrıca `self_check` ile öz-denetim listesini çek ve SDS bittikten sonra uygula.

---

## Adım 3 — 16 Bölüm Üretimi

### B1 — Kimyasal Ürün ve Firma
Kullanıcının verdiği değerleri **aynen** yaz — yorumlama, tamamlama, değiştirme.
- Ürün adı / ticari adı → kullanıcının yazdığı isim (ör. "Dipol HCl" ise "Dipol HCl" yaz)
- Firma adı → kullanıcının yazdığı isim (ör. "Dipol Kimya" ise "Dipol Kimya" yaz, "A.Ş." ekleme)
- Revizyon no, tarih, adres, acil tel → aynen kopyala
- B1'in sonuna sistem prompt başında verilen **B1 ATIF CÜMLESİ** değerini aynen ekle — numara veya tarih değiştirme, olduğu gibi kopyala

### B2 — Tehlike Tanımlaması
Motor çıktısından: `h_codes`, `signal`, `pictograms`, `clp_passed`, `euh`.

**B2.1 CLP Sınıflandırması** — `calculate_clp` → `all_h_codes` listesinden tablo oluştur:
| Zararlılık Sınıfı | Kategori | H Kodu | H İfadesi |
|---|---|---|---|
| (h_class) | (kategori) | (H kodu) | (Türkçe ifade) |

Motorda olmayan hiçbir H kodu bu tabloya eklenmez.

**B2.2 Etiket Unsurları** — `calculate_clp` çıktısından aynen al:
- Sinyal Kelimesi: `signal` değeri (Tehlike / Uyarı)
- Piktogramlar: `pictograms` listesindeki her kod için GHS sembol adını yaz (ör. GHS05: Korozivite)
- H İfadeleri: `h_codes` listesindeki her kod + Türkçe ifade — H314 varsa H318 yazılmaz (CLP Madde 26)
- EUH İfadeleri: `euh` listesindeyse yaz, yoksa bu satırı koyma
- P İfadeleri: `read_knowledge("labeling")` çıktısından H kodlarına uygun P kodlarını seç
- Diğer tehlikeler: "Bu madde/karışım PBT veya vPvB kriterlerini karşılamamaktadır."

⚠️ B2 hiçbir zaman boş bırakılamaz — en az sınıflandırma tablosu + sinyal kelimesi + piktogram listesi zorunludur.

### B3 — Bileşim/İçindekiler
Her bileşen için: ad, CAS, EC no, index no, konsantrasyon aralığı, H kodları.
- Konsantrasyon gösterimi: kullanıcı tam değer girdiyse standart bant (≥ 25%, ≥ 10 - < 20% vb.)
- Kullanıcı aralık girdiyse aynen yaz (ör. %10–20)
- Sınıflandırılmamış bileşenler (su, NaCl vb.) "Sınıflandırılmamış" olarak belirt

### B4 — İlk Yardım
`get_section_texts` yanıtından section "4" cümlelerini kullan.
Maruziyet yolları: inhalasyon, deri, göz, yutma — H koduna uygun olanları seç.

### B5 — Yangınla Mücadele
`get_section_texts` yanıtından section "5" cümlelerini kullan.
Fiziksel hal ve yanıcılık sınıfına göre uygun söndürücüleri yaz.

### B6 — Kaza Sonucu Yayılma
`get_section_texts` yanıtından section "6" cümlelerini kullan.

### B7 — Elleçleme ve Depolama
`get_section_texts` yanıtından section "7" cümlelerini kullan.

### B8 — Maruziyet Kontrolleri / KKE
`get_section_texts` yanıtından section "8" cümlelerini kullan.

**OEL Tablosu** — `get_oel` sonucundan, değer varsa şu tabloyu yaz:
| Madde | CAS | TWA (ppm) | TWA (mg/m³) | STEL (ppm) | STEL (mg/m³) | Dayanak |
|---|---|---|---|---|---|---|
| (madde adı) | (CAS) | (değer/—) | (değer/—) | (değer/—) | (değer/—) | 29204 sayılı RG |

`get_oel` boş dönerse: "Bu karışım bileşenleri için Türkiye OEL listesinde (29204 sayılı RG) değer bulunmamaktadır." yaz.

⚠️ OEL tablosu hiçbir zaman atlanamaz — ya değer ya "bulunmamaktadır" yazılır.

### B9 — Fiziksel ve Kimyasal Özellikler
Kullanıcı girişi + `calculate_clp` yanıtındaki `theo_props`. **Tablo her zaman tam doldurulur** — bilinmeyen değer "Belirlenmemiştir", asla tahmin etme, asla boş bırakma.

| Özellik | Değer | Kaynak |
|---|---|---|
| Görünüm / Renk | (kullanıcı girişi) | Ölçüm |
| Koku | (kullanıcı girişi) | Ölçüm |
| pH | (kullanıcı girişi) | Ölçüm |
| Kaynama Noktası (°C) | (değer veya Belirlenmemiştir) | Ölçüm / Literatür |
| Parlama Noktası (°C) | (değer veya Uygulanamaz) | Ölçüm / Literatür |
| Yoğunluk (g/cm³) | (değer veya Belirlenmemiştir) | Ölçüm |
| Buhar Basıncı (hPa, 20°C) | (değer veya Belirlenmemiştir) | Literatür |
| Suda Çözünürlük | (değer veya Karışabilir) | Literatür |
| Viskozite | (değer veya Belirlenmemiştir) | Ölçüm |
| Patlama Sınırları (%, v/v) | (değer veya Uygulanamaz) | Literatür |

⚠️ B9 tablosu hiçbir zaman boş bırakılamaz.

### B10 — Kararlılık ve Reaktivite
H kodlarına göre:
- H240/H241/H242 varsa ısıl kararsızlık uyarısı
- H260/H261 varsa su ile reaksiyon uyarısı
- H270/H271/H272 varsa güçlü oksitleyici uyarısı
- Genel: "Normal depolama koşullarında kararlıdır"
- Tehlikeli bozunma ürünleri: CO, CO₂, HCl gibi olası ürünleri H kodlarından türet

### B11 — Toksikoloji
`clp_passed` listesinden ATE değerleri dahil:
- Akut toksisite: oral/dermal/inhalasyon LD50/LC50 (bileşen bazlı, varsa)
- Tahriş, duyarlılaştırma, CMR, STOT: **YALNIZCA** `calculate_clp` → `h_codes` listesindeki kodlardan yaz
- **`h_codes` listesinde YOKSA → yazma.** Kontrol et: H335 `h_codes`'da var mı? Yoksa "STOT SE 3" veya "H335" kesinlikle yazılmaz.
- **Yasak:** Motora sormadan "Solunum tahrişi", "STOT", "H335", "H336" gibi ifadeler ekleme.
- Bilgi yoksa "Bu madde/karışım için toksikolojik veri mevcut değildir" yaz

### B12 — Ekoloji
`calculate_clp` yanıtındaki `eco` çıktısından:
- Sucul tehlike sınıflandırması ve gerekçesi (M-faktörleri dahil)
- Eco boş/null ise: "Bu karışım için sucul tehlike eşiği aşılmamıştır"
- PBT/vPvB: "Bu karışım PBT veya vPvB değerlendirmesi için kriterleri karşılamamaktadır" (REACH Ek XIII)

### B13 — Bertaraf
Fiziksel hale + H kodlarına göre:
- Atık kodu (Avrupa Atık Kataloğu — kullanım alanına göre)
- "Yerel ve ulusal yönetmeliklere uygun bertaraf edin"
- Boş ambalaj bertarafı

### B14 — Taşımacılık
`detect_adr` çağırırken `components` listesini de gönder:
```json
{
  "h_codes": [...],
  "form": "liquid",
  "components": [
    {"cas": "7647-01-0", "conc": 18.0, "h_codes": ["H314", "H335"]}
  ]
}
```
`detect_adr` çıktısından:
- UN No, taşımacılık adı, tehlike sınıfı, ambalaj grubu, Kemler kodu, tünel kodu
- Çevresel tehlike: H400/H410/H411 varsa "Deniz kirletici: Evet"
- Düzenlemeye tabi değilse: "Bu ürün ADR/RID/IMDG/IATA kapsamında tehlikeli madde değildir"

### B15 — Mevzuat
`check_svhc` çıktısından + `read_knowledge("kkdik_references")` bilgisinden. **Şu satırları her zaman yaz:**

**Geçerli Mevzuat:**
- KKDİK: 11 Temmuz 2017 tarihli **30105** sayılı Resmî Gazete
- SEA: 26 Aralık 2013 tarihli **28848** sayılı Resmî Gazete
- OEL: 12 Ağustos 2015 tarihli **29204** sayılı Resmî Gazete (B8 OEL değerleri)

**SVHC Durumu** (`check_svhc` sonucundan):
- SVHC varsa: madde adı + konsantrasyon + "ECHA Aday Listesi'nde yer almakta, bildirim yükümlülüğü uygulanır"
- SVHC yoksa: "Bu karışım ≥%0,1 konsantrasyonda SVHC içermemektedir (REACH Madde 59)"

⚠️ B15 hiçbir zaman boş bırakılamaz — en az mevzuat listesi + SVHC sonucu zorunludur.

### B16 — Diğer Bilgiler
- Revizyon tarihi ve numarası
- Değişiklik özeti (ilk revizyonda "İlk yayın")
- Sorumluluk reddi: "Bu belgede yer alan bilgiler, hazırlandığı tarih itibarıyla doğru olduğuna inanılmaktadır..."
- Kısaltmalar: CLP, KKDİK, SEA, ADR, OEL, PBT, vPvB, SVHC, REACH

---

## Adım 4 — Onay ve Çıktı

SDS taslağını kullanıcıya sun:
```
✅ 16 bölümlük SDS taslağı hazır.
Word veya PDF olarak indirmek istiyor musunuz?
```

Kullanıcı onayladıktan sonra sistem Word/PDF oluşturur.

Değişiklik isteklerinde:
1. Hangi motorların etkilendiğini belirle
2. İlgili tool'ları yeniden çağır
3. Sadece değişen bölümleri güncelle, kalanlar aynı kalır

---

## Yazım Kuralları — KISALIK

SDS metni **kısa ve standart** olmalı — her bölüm 3-8 satır yeterli.

- **Açıklama yazma.** Neden/çünkü/gerekçe cümleleri yazma; sadece bilgiyi yaz.
- **Tek satır bilgi = tek satır metin.** Madde işareti listesi veya tablo kullan, paragraf değil.
- **B4-8:** `get_section_texts` çıktısını aynen yaz — ekstra cümle ekleme.
- **B9:** Sadece tablo — değer bilinmiyorsa "Belirlenmemiştir", açıklama yok.
- **B10:** 3-5 madde işareti yeterli — tehlikeli reaksiyon listesi, senaryo anlatımı değil.
- **B11:** Sınıflandırma tablosu + 1-2 satır klinik bilgi — uzun tıp açıklaması değil.
- **B12:** Eco sonucu + PBT/vPvB 2 satır — ekoloji dersi değil.
- **B13:** Atık kodu + 2 satır bertaraf talimatı.
- **B14:** ADR tablosu + deniz/hava = aynı satır — uzun taşımacılık rehberi değil.
- **B15:** KKDİK/SEA atıfları + SVHC sonucu — 5-8 satır.
- **B16:** Revizyon + sorumluluk reddi — 3 satır.

Hedef: 16 bölüm toplamda **~2000-3000 kelime** — Word/PDF çıktısı 8-12 sayfa.

---

## Kurallar

- **Motor çıktısı yetkilidir.** H kodları, ADR, eco — tüm matematiksel sonuçlar tool'dan gelir. Tahmin etme.
- **B4-8 standart metinleri** `get_section_texts` tool'undan al. Kendisi uydurma.
- **Mevzuat ve hesap kuralları** `read_knowledge` tool'undan al — bellekten yazma.
- Motor null döndürdüyse "Belirlenmemiştir" yaz, motor sınırlaması yorumu yapma.
- `pending_decisions` varsa kullanıcıya sor, SDS'i blokla.
- Bilinmeyen fiziksel özellik için "Belirlenmemiştir" yaz.
- **KKDİK referans numarası:** 30105/2017 (11 Temmuz 2017) — başkasını yazma.
- **SEA referans numarası:** 28848/2013 — başkasını yazma.
- **OEL yönetmelik numarası (B8 ve B15):** 29204 / 12 Ağustos 2013 — başkasını yazma.
- **YASAK SAYI:** 32345 bu belgede hiçbir yerde geçemez — OEL için 29204 kullan.
- **B2.1 sınıflandırma tablosu:** YALNIZCA `calculate_clp` → `h_codes` listesindeki H kodları yazılır. Motorda olmayan H kodu (H335 dahil) B2'ye eklenmez.
- **UN numarasını bellekten yazma** — her zaman `detect_adr` sonucundan al.
- **Sulu çözelti için** H260/H261 yazma; H280/H281 yazma.
- CAS, EC, index numaralarını asla uydurma — lookup sonucundan al.

## Hallüsinasyon Önleme — Kaynak Zorunluluğu

Her SDS alanının kaynağı bellidir. **Kaynağı olmayan değer yazılmaz.**

| SDS Alanı | Zorunlu Kaynak |
|---|---|
| B2/B3 H kodları | `calculate_clp` → `h_codes` / `clp_passed[i].h_codes` |
| B3 bileşen H kodları | `calculate_clp` → `clp_passed` listesindeki her bileşen |
| B8 OEL değerleri | `get_oel` tool sonucu |
| B8 OEL yönetmelik no | 29204 / 12 Ağustos 2013 (sabit) |
| B11 STOT/CMR/tahriş H kodları | `calculate_clp` → `h_codes` (motorda yoksa yazılmaz) |
| B9 fiziksel özellikler | Kullanıcının verdiği değerler — eksikse "Belirlenmemiştir" |
| B9 pH | Kullanıcının ölçtüğü değer — teorik hesap ekleme |
| B14 UN/Sınıf/PG | `detect_adr` tool sonucu |
| B15 KKDİK/SEA/OEL no | read_knowledge(`kkdik_references`) |
| CAS/EC numarası | `lookup_substance` tool sonucu |
| B1 ürün adı / ticari adı | Kullanıcının verdiği isim — değiştirme, yorumlama |
| B1 firma adı | Kullanıcının verdiği isim — "A.Ş.", "Ltd." gibi ekler yapma |

**Kural:** Yukarıdaki kaynaklardan gelmeyen hiçbir sayısal değer veya referans numarası yazılmaz. "Bulamadım" demek, uydurulmuş değer yazmaktan iyidir.

---

## API Base URL
`https://sdspass-api-3.onrender.com`
