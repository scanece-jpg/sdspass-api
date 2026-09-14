---
name: sds-olustur
description: >
  Kullanıcıdan bilgileri adım adım toplayarak KKDİK/SEA uyumlu 16 bölümlü
  SDS (GBF) metni üretir. Motorları API üzerinden çağırır, matematiksel
  hesapları backend yapar, Claude kalan bölümleri mevzuata göre yazar.
  Değişiklik isteklerinde etkilenen tüm bölümleri yeniden hesaplar.
---

# SDS Oluşturma Skill'i

## Genel Akış

1. **Bilgi Toplama** — Sohbetle topla, seçenek gerektiren her şeyi AskUserQuestion ile sor
2. **Motor Çağrısı** — `/api/v1/sds/calculate` + `/api/v1/adr/auto-detect` + `/api/v1/svhc/check`
3. **SDS Üretimi** — Motor çıktıları + mevzuat bilgisiyle 16 bölüm yaz
4. **Değişiklik** — Kullanıcı düzeltme isterse etkilenen motorları yeniden çağır, değişen bölümleri listele

---

## Adım 1 — Bilgi Toplama

### 1.1 Ürün Bilgileri (metin sor)
- Ürün adı / ticari adı
- Revizyon numarası (yoksa "00" kabul et)
- Revizyon tarihi (yoksa bugünün tarihi)
- Ürünü hazırlayan firma adı ve adresi
- Acil telefon numarası

### 1.2 Seçimler (AskUserQuestion ile)
```
Kullanım tipi?
  [Endüstriyel]  [Profesyonel]  [Tüketici]

Fiziksel hal?
  [Sıvı]  [Katı]  [Gaz/Aerosol]

SDS Dili?
  [Türkçe (TR)]  [İngilizce (EN)]
```

### 1.3 Bileşenler (metin sor)
Her bileşen için:
- CAS numarası
- Konsantrasyon (% tam değer veya min-max aralık)
- Bileşen fiziksel hali (sıvı/katı farklıysa)

Önce CAS ile madde verilerini çek: `GET /api/v1/sds/substance/lookup?cas={CAS}`
- Madde bulunursa: adı, tehlike sınıflarını göster, onay iste
- Bulunmazsa: tehlike sınıflarını kullanıcıdan iste

**ÖNEMLİ:** Lookup sonucundan şu alanları API payload'a aynen kopyala:
- `hazards` → bileşenin `hazards` alanı
- `m_factors` → bileşenin `m_factors` alanı (sucul M-faktörleri — boş bırakma!)
- `scl` → bileşenin `scl` alanı (özel konsantrasyon limitleri)
- `ate` → bileşenin `ate` alanı (akut toksisite verileri)

Eco motoru M-faktörsüz çalışırsa sucul sınıflandırma yanlış çıkar.

### 1.4 Fiziksel Özellikler (metin sor — ölçülen değerler)
Aşağıdakileri sor, bilinmeyenler için "—" yaz:
- Görünüm ve renk (ör: "berrak sarı sıvı")
- Koku (ör: "hafif karakteristik")
- pH değeri
- Parlama noktası °C (varsa — fiziksel tehlike hesabı için kritik)
- Kaynama noktası °C
- Yoğunluk g/cm³ veya g/mL
- Buhar basıncı (ör: "< 1 hPa, 20°C")
- Suda çözünürlük
- Viskozite (varsa)
- Kendiliğinden tutuşma sıcaklığı (varsa)

---

## Adım 2 — Motor Çağrıları

### ÖNEMLİ: API Çağrı Kuralları

**Encoding:** API'ye JSON gönderirken Türkçe karakterler (`ş ğ ü ö ç İ` vb.) bozulur.
Her zaman JSON'u bir geçici dosyaya yaz (`/tmp/payload.json`), sonra `curl` ile gönder:
```bash
# DOĞRU yöntem — dosyadan gönder
cat > /tmp/payload.json << 'JSONEOF'
{ "components": [...] }
JSONEOF
curl -s -X POST https://sdspass-api-3.onrender.com/api/v1/sds/calculate \
  -H "Content-Type: application/json; charset=utf-8" \
  --data-binary @/tmp/payload.json
```
**Asla** Türkçe içerikli JSON'u doğrudan `-d '...'` ile gönderme.

**Worst-case konsantrasyon:** CLP kuralı gereği sınıflandırma her zaman aralığın
**en yüksek** değeriyle yapılmalıdır. Konsantrasyon aralık (min/max) ise:
- `conc` = üst sınır (max)
- `concMax` = üst sınır (max)

Örnek: "%5-10" aralığı → `"conc": 10.0, "concMax": 10.0`

---

### Ana Hesap
`POST /api/v1/sds/calculate`
```json
{
  "components": [
    {
      "cas": "7646-85-7",
      "name": "Cinko klorur",
      "conc": 30.0,
      "concMax": 30.0,
      "hazards": [],
      "m_factors": {},
      "scl": []
    }
  ],
  "form": "liquid",
  "user_fp": null,
  "mixture_ph": null,
  "test_data": {
    "density": "1.15",
    "boiling_point": "102"
  },
  "usage": "industrial",
  "lang": "TR"
}
```
**Not:** `name` alanında Türkçe karakter kullanma — API yanıtı etkiler. Madde adını
ASCII'ye çevir (ör. "Çinko" → "Cinko"). B3 tablosunda doğru Türkçe adı sen yaz.

Döner: `h_codes, signal, clp_passed, pictograms, euh, p_codes, physical, stot, eco, theo_props`

### ADR Taşımacılık
`POST /api/v1/adr/auto-detect`
```json
{"h_codes": [...], "form": "liquid", "flash_point": null, "lang": "TR"}
```

### SVHC Kontrolü
`POST /api/v1/svhc/check`
```json
{"components": [{"cas": "...", "name": "...", "concentration": 30.0}]}
```

### OEL (her bileşen için)
`GET /api/v1/oel/{cas}`

---

## Adım 3 — 16 Bölüm Üretimi

Motor çıktılarını ve kullanıcı bilgilerini kullanarak her bölümü yaz.

### B1 — Kimyasal ürün ve firma tanımlaması
Kullanıcıdan toplanan: ürün adı, firma, adres, acil tel, revizyon, kullanım tipi

### B2 — Tehlike tanımlaması
Motor çıktısından: `h_codes`, `signal`, `pictograms`, `clp_passed`
- CLP/SEA sınıflandırma tablosu
- Etiket unsurları (piktogram, sinyal, H kodları, P kodları)
- Diğer tehlikeler

### B3 — Bileşim/İçindekiler
Kullanıcıdan toplanan bileşenler + madde lookup verileri
- Her bileşen: ad, CAS, EC, index no, konsantrasyon, H kodları
- Ticari sır varsa aralık göster

### B4 — İlk yardım önlemleri
Mevzuat bilgisinden: maruziyet yoluna göre standart metinler
- İnhalasyon, deri, göz, yutma
- H kodlarına göre özel notlar (H314 → acil tıbbi müdahale vb.)

### B5 — Yangınla mücadele
Motor çıktısından: `physical` (yanıcılık sınıfı, parlama noktası)
- Uygun söndürücüler
- Kaçınılacak söndürücüler (H314 varsa su püskürtme dikkat)
- Koruyucu donanım

### B6 — Kaza sonucu yayılmaya karşı önlemler
H kodlarına + fiziksel hale göre: döküntü prosedürleri, kişisel koruma, çevre önlemleri

### B7 — Elleçleme ve depolama
P kodlarından + H kodlarından: güvenli elleçleme, depolama koşulları, uyumsuzluklar

### B8 — Maruziyet kontrolleri/Kişisel korunma
OEL verilerinden + PPE engine çıktısından:
- Mesleki maruziyet sınırları (KKDİK Ek-14)
- Solunum, el, göz, vücut koruyucu

### B9 — Fiziksel ve kimyasal özellikler
Kullanıcı girişi + `theo_props` motor çıktısı:
- Görünüm, koku, pH, kaynama, parlama, yoğunluk vb.
- Teorik tahminler için "hesaplama ile tahmin" notu ekle

### B10 — Kararlılık ve reaktivite
`cameo_service` uyumsuzlukları + mevzuat bilgisi:
- Kaçınılacak koşullar, kaçınılacak maddeler
- Tehlikeli bozunma ürünleri

### B11 — Toksikoloji
Motor çıktısından: `clp_passed` (ATE değerleri dahil)
- Maruziyet yolları, semptomlar
- LD50/LC50 değerleri bileşen bazlı

### B12 — Ekoloji
Motor çıktısından: `eco` (sucul tehlike hesabı)
- H400/H410/H411/H412 gerekçesi
- PBT/vPvB değerlendirmesi
- Biyobozunurluk notu

### B13 — Bertaraf
H kodlarına + form'a göre: atık kodu, bertaraf yöntemi, yasal dayanak

### B14 — Taşımacılık
ADR motor çıktısından: UN no, taşımacılık adı, sınıf, PG, Kemler, tünel kodu
- Karayolu (ADR), Deniz (IMDG), Hava (IATA) — motor vermişse

### B15 — Mevzuat
SVHC kontrolünden + mevzuat bilgisinden:
- KKDİK/SEA, REACH referansları
- SVHC listesi durumu
- Biyosit/ODS kontrolü

### B16 — Diğer bilgiler
- Revizyon bilgisi, değiştirilen bölümler
- Sorumluluk reddi
- Kısaltmalar

---

## Adım 4 — Değişiklik Yönetimi

Kullanıcı bir değişiklik istediğinde:

1. **Etkiyi belirle** — hangi motorlar bu bilgiyi kullanıyor?
2. **Yeniden hesapla** — ilgili API çağrılarını tekrar yap
3. **Rapor et** — değişiklik öncesi/sonrası:
   ```
   ✅ B8 güncellendi
   ⚠️ Bu değişiklik şunları da etkiledi:
      - B2: H315 kaldırıldı, sinyal "Warning"→"Danger" değişmedi
      - B14: ADR sınıfı değişmedi
   ```
4. **Güncelle** — sadece değişen bölümleri yeniden yaz, kalanlar aynı kalır

### Etki Haritası
| Değişen | Etkilenen Bölümler |
|---|---|
| Bileşen ekleme/çıkarma | B2, B3, B8, B11, B12, B14, B15 |
| Konsantrasyon değişimi | B2, B3, B11, B12, B14, B15 |
| Parlama noktası | B2, B5, B9, B14 |
| pH değişimi | B2, B4, B9 |
| Kullanım tipi | B1, B8, B15 |

---

## Kurallar

- **Motor çıktısı yetkilidir.** H kodları, ADR, eco, piktogram — tüm matematiksel sonuçlar motorden gelir. "Beklenen şu olmalıydı", "teorik olarak şu çıkmalıydı", "motor M-faktörünü işlememiş olabilir" gibi yorumlar yapma. Motor ne diyorsa SDS'e onu yaz.
- Motor boş/null döndürdüyse o sınıflandırma yoktur — SDS'e "belirlenmedi" yaz, tahmin etme. B12 ekoloji boş gelirse "Sucul tehlike sınıflandırması: Bu karışım için sucul tehlike eşiği aşılmamıştır." yaz, motor sınırlaması yorumu yapma.
- **Gaz fazı vs. çözelti:** Bir madde veritabanında gaz fazı H kodlarıyla (H280, H331 vb.) kayıtlıysa ve ürün sulu çözelti ise, bunu kullanıcıya sor — tedarikçi SDS'indeki H kodlarını al. Alt kategori sorusu sorma, sadece H kodunu iste.
- **Hiçbir zaman** motor çıktısını görmeden H kodu üretme.
- **Hiçbir zaman** mevzuattan uydurma CAS no, index no, EC no yazma.
- Bilinmeyen fiziksel özellik için "—" yaz, asla tahmin etme.
- Tüm mevzuat atıfları KKDİK/SEA/ADR TR versiyonuna olsun.
- API erişilemiyorsa kullanıcıya bildir, SDS üretmeyi durdur.

---

## API Base URL
`https://sdspass-api-3.onrender.com`
