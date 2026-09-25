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
Kullanıcıdan toplanan: ürün adı, firma, adres, acil tel, revizyon, kullanım tipi.

### B2 — Tehlike Tanımlaması
Motor çıktısından: `h_codes`, `signal`, `pictograms`, `clp_passed`, `euh`.
- CLP/SEA sınıflandırma tablosu (h_class + h_code + kategori)
- Etiket unsurları: piktogram sembol adları, sinyal kelimesi, H ifadeleri, EUH ifadeleri, P ifadeleri
- `all_h_codes` → B2.1 sınıflandırma tablosu (H318 dahil)
- `h_codes` → etiket (H314 varken H318 gizlenir — CLP Madde 26)
- Diğer tehlikeler: PBT/vPvB değil ise "Bu madde/karışım PBT veya vPvB kriterlerini karşılamamaktadır."

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
`get_oel` sonuçlarından OEL değerlerini tabloya ekle.

### B9 — Fiziksel ve Kimyasal Özellikler
Kullanıcı girişi + `calculate_clp` yanıtındaki `theo_props`:
- Teorik/hesaplanan değerler için "hesaplama ile tahmin" notu ekle
- Bilinmeyen değerler için "Belirlenmemiştir" yaz, asla tahmin etme

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
- Tahriş, duyarlılaştırma, CMR, STOT: H kodlarından
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
`detect_adr` çıktısından:
- UN No, taşımacılık adı, tehlike sınıfı, ambalaj grubu, Kemler kodu, tünel kodu
- Çevresel tehlike: H400/H410/H411 varsa "Deniz kirletici: Evet"
- Düzenlemeye tabi değilse: "Bu ürün ADR/RID/IMDG/IATA kapsamında tehlikeli madde değildir"

### B15 — Mevzuat
`check_svhc` çıktısından + mevzuat bilgisinden:
- KKDİK (30105/2017) ve SEA (28848/2013) atıfları
- SVHC durumu: listede varsa madde adı + konsantrasyon + bildirim yükümlülüğü
- SVHC yoksa: "Bu karışım ≥%0,1 konsantrasyonda SVHC içermemektedir"

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

## Kurallar

- **Motor çıktısı yetkilidir.** H kodları, ADR, eco — tüm matematiksel sonuçlar tool'dan gelir. Tahmin etme.
- **B4-8 standart metinleri** `get_section_texts` tool'undan al. Kendisi uydurma.
- **Mevzuat ve hesap kuralları** `read_knowledge` tool'undan al — bellekten yazma.
- Motor null döndürdüyse "Belirlenmemiştir" yaz, motor sınırlaması yorumu yapma.
- `pending_decisions` varsa kullanıcıya sor, SDS'i blokla.
- Bilinmeyen fiziksel özellik için "Belirlenmemiştir" yaz.
- **KKDİK referans numarası:** 30105/2017 (11 Temmuz 2017) — başkasını yazma.
- **SEA referans numarası:** 28848/2013 — başkasını yazma.
- **UN numarasını bellekten yazma** — her zaman `detect_adr` sonucundan al.
- **Sulu çözelti için** H260/H261 yazma; H280/H281 yazma.
- CAS, EC, index numaralarını asla uydurma — lookup sonucundan al.

---

## API Base URL
`https://sdspass-api-3.onrender.com`
