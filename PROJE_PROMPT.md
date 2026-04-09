# SDSPass — Claude için Tam Proje Bağlamı

## Projenin Amacı

SDSPass, kimyasal karışımlar için **Türkiye KKDİK/SEA yönetmeliğine uygun** 16 bölümlü Güvenlik Bilgi Formu (GBF / SDS) otomatik hazırlayan bir sistemdir. Kullanıcı karışım bileşenlerini ve konsantrasyonlarını girer, sistem tehlike sınıflandırması yapar, PDF üretir.

---

## Yasal Dayanak — HİÇBİR ZAMAN UNUTMA

Bu sistem **yalnızca Türkiye mevzuatı** esas alınarak çalışır:

| Yönetmelik | Kısaltma | Açıklama |
|-----------|----------|----------|
| Maddelerin ve Karışımların Sınıflandırılması, Etiketlenmesi ve Ambalajlanması Hakkında Yönetmelik | **SEA** | AB CLP (1272/2008) ile harmonize — TR GBF'nin omurgası |
| Kimyasalların Kaydı, Değerlendirilmesi, İzni ve Kısıtlanması Yönetmeliği | **KKDİK** | AB REACH ile harmonize — madde kayıt + iletişim zinciri |
| Tehlikeli Maddelerin Karayoluyla Taşınması Yönetmeliği | **ADR** | ADR 2023 Türkiye uyarlaması |
| GHS | **BM GHS Rev.9** | Piktogram/sinyal/H/P kodu formatı |

**Kural:** Avrupa ECHA veritabanı referans alınabilir ama nihai karar daima **SEA Ekleri ve Tabloları** ile verilir.

---

## Proje Dosya Yapısı

```
C:\Users\user\Desktop\sdspass\          ← Ana çalışma dizini (git repo)
│
├── static/
│   └── index.html                      ← Tek sayfa uygulama (SPA) — tüm UI + JS motoru çağrıları
│
├── js/engines/
│   ├── clp_engine.js                   ← CLP sınıflandırma (GCL/SCL/ATE)
│   ├── eco_engine.js                   ← Sucul tehlike (M-faktörlü toplam, SEA Tablo 4.1.2)
│   ├── pcode_engine.js                 ← P kodu atama
│   ├── stot_engine.js                  ← STOT hesaplama
│   ├── phys_engine.js                  ← Fiziksel tehlike (yanıcılık vs.)
│   └── transport_engine.js             ← ADR/IMDG/IATA UN sınıfı
│
├── app/
│   ├── main.py                         ← FastAPI backend — /pdf endpoint, backend override
│   └── services/
│       ├── pdf_sds_service.py          ← ReportLab ile 16 bölümlü PDF üretimi
│       ├── ecological_service.py       ← Backend sucul tehlike hesabı (yetkili sonuç)
│       ├── p_code_service.py           ← Backend P kodu ve etiket seçimi
│       ├── clp_service.py              ← Backend CLP yardımcıları
│       ├── concentration_ranges.py     ← GCL tablosu + SCL birleştirme
│       ├── substance_lookup.py         ← CAS → tehlike verisi arama
│       └── transport_adr_service.py    ← ADR detay servisi
│
├── data/
│   ├── clp_full_data.json              ← Bileşen CAS tehlike veritabanı
│   ├── substances_sea_ek6.json         ← SEA Ek-6 (TR Annex VI) — en yetkili kaynak
│   ├── adr_data.json                   ← ADR UN numaraları
│   └── echa_cl_archive.json            ← ECHA C&L yerel arşiv
│
└── PROJE_PROMPT.md                     ← Bu dosya
```

**Canlı adres:** https://sdspass-api-3.onrender.com/
**GitHub:** scanece-jpg/sdspass-api
**Deploy:** git push → Render.com otomatik (2-3 dk)

---

## Sistem Mimarisi ve Veri Akışı

```
KULLANICI (tarayıcı)
        │
        ▼
[index.html — UI]
        │
        ├─► [clp_engine.js]      → CLP_CALCULATE event → H_CODES_READY
        │       • GCL / SCL ile H314/H315/H317/H319 vb.
        │       • ATE formülü ile H300/H301/H302/H310/H311/H312/H330/H331/H332
        │       • cutoffUsed{} → her H kodu için eşik kaynağı kaydeder
        │
        ├─► [eco_engine.js]      → ECO_CALCULATE event → ECO_READY
        │       • SEA Tablo 4.1.2 M-faktörlü toplam
        │       • sumChronicK1/K2/K3 ayrı takip
        │       • H410/H411/H412 → h_codes[] + aquatic.formula metni
        │
        ├─► [pcode_engine.js]    → P kodu (ön hesap, label için)
        ├─► [stot_engine.js]     → H370/H371/H372/H373
        ├─► [phys_engine.js]     → H225/H226/H228/H242 vb.
        └─► [transport_engine.js]→ ADR/IMDG/IATA UN sınıfı
                │
                ▼
        [renderAll() — index.html ~satır 1280]
        allH = clp.hCodes + eco.h_codes + stot.hCodes + phys.hCodes
        clpPassed[] = allH'dan her H kodu için { h_class, reason, cutoff_used }
                │
                ▼
        [generatePDF() → POST /pdf]
        payload: { h_codes: allH, clp_passed: clpPassed, ... }
                │
                ▼
[FastAPI — app/main.py]
        │
        ├─► ecological_service.py   ← BACKEND YETKİLİ — frontend eco kodlarını REPLACE eder
        │       • H400/H410/H411/H412/H413 önce temizlenir
        │       • Python sonucu eklenir
        │
        ├─► p_code_service.py       ← P kodu (etikette max 6, CLP Madde 22)
        └─► pdf_sds_service.py      ← ReportLab PDF üretimi
                │
                ▼
        [PDF indirilir]
```

---

## Sınıflandırma Veri Kaynağı Öncelik Sırası (TR SEA)

| Öncelik | Kaynak | Dosya | Kural |
|---------|--------|-------|-------|
| 1 | SEA Ek-6 (TR Annex VI) | `substances_sea_ek6.json` | CAS eşleşirse bu sınıflandırma mutlak |
| 2 | ECHA C&L Arşivi (yerel) | `data/echa_cl_archive.json` | Önceki API sonuçları |
| 3 | ECHA C&L Inventory (API) | canlı PubChem | En yüksek bildirim sayılı → arşive kaydedilir |
| 4 | Kullanıcı girişi | `substances_custom.json` | Elle girilmiş tedarikçi verisi |
| 5 | clp_engine.js hesaplama | — | M-faktörü yoksa toksisite verisinden |
| 6 | SEA Tablo 3.1.2 ATE | — | LD50/LC50 varsa point estimate |

---

## Kritik Algoritma Kuralları

### 1. Akut Toksisite (H300–H332) — SEA Bölüm 3.1.3.6.1

**GCL (Generic Concentration Limit) KULLANILAMAZ.** Sadece ATE formülü:

```
ATE_karışım = 100 / Σ(Ci / ATE_i)
```

**SEA Tablo 3.1.2 Point Estimate değerleri:**

| H Kodu | Rota | ATE (mg/kg veya mg/L) |
|--------|------|-----------------------|
| H300 | Oral | 0.5 mg/kg |
| H301 | Oral | 100 mg/kg |
| H302 | Oral | **500 mg/kg** (2000 DEĞİL — 2000 kategori üst sınırıdır) |
| H310 | Dermal | 0.5 mg/kg |
| H311 | Dermal | 200 mg/kg |
| H312 | Dermal | 1000 mg/kg |
| H330 | İnhal | 0.05 mg/L |
| H331 | İnhal | 3.0 mg/L |
| H332 | İnhal | **11.0 mg/L** |

Sınıflandırma eşikleri (oral):
- ATE ≤ 5 → H300 (Kat. 1)
- ATE ≤ 50 → H300 (Kat. 2)
- ATE ≤ 300 → H301 (Kat. 3)
- ATE ≤ 2000 → H302 (Kat. 4)

### 2. Sucul Tehlike — SEA Tablo 4.1.2

Tüm eşikler **%25**'tir (eski yanlış değerler: %10/%1 YANLIŞ).

**H410 (Kronik 1):**
```
Σ(Ci × M_chronic) / 100 ≥ 0.25
```
Dahil etme kesim değeri: konc ≥ 0.1% / M

**H411 (Kronik 2):**
```
10 × Σ[K1×M] + Σ[K2] ≥ 0.25
```
Dahil etme kesim değeri: konc ≥ 1%

**H412 (Kronik 3):**
```
100 × Σ[K1×M] + 10 × Σ[K2] + Σ[K3] ≥ 0.25
```

**0.1%/M = dahil etme kesimi** (inclusion cut-off) — tek başına H410 tetikleyici DEĞİL.

### 3. P Kodu — CLP Madde 22 (SEA Madde 22)

- Etikette maksimum **6 P kodu**
- `P370+P378` H225/H226 için **zorunlu** (yangın müdahale)
- `P273` çevre kodu
- `P280` KKE kodu

### 4. Backend Eco Override Kuralı

`main.py`'de frontend'den gelen `H400/H410/H411/H412/H413` kodları **her zaman silinir**, Python `ecological_service.py` sonucu eklenir. Frontend eco motoru sadece görsel önizleme içindir.

---

## Yapılmış Düzeltmeler (Commit Geçmişi)

| Commit | Değişiklik |
|--------|-----------|
| `dc6c48e` | H302/H410 gerekçe metni — GCL fallback kaldırıldı, ATE/eco doğru gösterim |
| `ee5ad62` | eco_engine.js: SEA Tablo 4.1.2 formülleri + backend replace fix |
| `0424063` | ecological_service.py: H410/H411/H412 eşikleri düzeltildi |
| `b704378` | clp_engine.js: H302 GCL → ATE formülüne geçiş + ATE_POINT tablosu |
| `1a8aecb` | p_code_service.py: P370+P378 öncelik değeri eklendi |
| `e175da9` | H400 yanlış tetiklenme + P332/P333 öncelik |
| `398a064` | H315 toplama kuralı + P273 etiket önceliği |

---

## Bilinen Açık Sorunlar

### 1. Tarayıcı Önbelleği Sorunu
`index.html` güncellendiğinde tarayıcı önbellekli eski sürümü gösterebilir.
→ **Çözüm:** `Ctrl+Shift+R` ile hard-refresh
→ JS motorları için `?v=YYYYMMDD` cache buster kullanılıyor

### 2. Gerekçe Metni Henüz Doğrulanmadı
`CLP_CUTOFFS`'dan H302/H410 silindi ve ATE/eco için ayrı reason formatları eklendi, ama canlı PDF'te "GCL >= %5" ve "GCL >= %0.1" hâlâ görünüyor olabilir.
**Şüpheli ek kaynak:** `cutoffUsed[hc]` boş geliyorsa clp_engine ATE/eco kodlarını `cutoffUsed`'a yazmamış olabilir — kontrol edilmeli.
**Kontrol edilecek satır:** `clp_engine.js` ATE bloku → `cutoffUsed[resultCode]` kaydı var mı?

### 3. eco_engine.js ile ecological_service.py Çıktı Tutarsızlığı
Frontend (eco_engine.js) artık doğru formüle sahip ama backend override nedeniyle frontend sonucu PDF'e yansımaz. İki motor aynı sonucu üretmeli — ileride karşılaştırma testi yapılmalı.

### 4. SCL Gösterimi
Bazı bileşenler için SCL kaydı mevcut ama `_sclMap`/`_sclRaw` üzerinden doğru kategori eşiği gösterilemiyor olabilir.

---

## Geliştirme ve Deploy Akışı

```
1. Kod değiştir → C:\Users\user\Desktop\sdspass\
2. JS motoru değiştiyse → index.html'deki ?v=YYYYMMDD güncelle
3. git add <dosyalar>
4. git commit -m "açıklama"
5. git push → Render.com 2-3 dakikada deploy eder
```

**Lokal test:** `uvicorn app.main:app --host 0.0.0.0 --port 8000`
**Font:** Render.com'da `render.yaml` içinde `fonts-dejavu-core` kurulumu zorunlu (Türkçe karakter)

---

## Karışım Test Senaryosu (Geliştirici Referansı)

Mevcut test karışımı (ürün SDS 36):
- **Etanol** (%30, CAS 64-17-5): H225, H319 → ATE oral=7906 mg/kg
- **İzopropanol** (%20, CAS 67-63-0): H225, H319 → ATE oral=5045 mg/kg
- **Başka bileşen** SCL ile H317 (Skin Sens. 1)

**Beklenen sonuçlar:**
- H302: OLMAMALI (ATE_mix >> 2000 mg/kg)
- H410: OLMAMALI (karışımda Aquatic Chronic bileşen yok veya toplam < %25)
- H225: OLMALI (etanol/izopropanol yanıcı)
- H317: OLMALI (SCL ile)
- H315/H319: OLMALI (GCL %10 ile)
