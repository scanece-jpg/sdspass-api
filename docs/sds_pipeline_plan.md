# SDSPass — SDS Üretim Süreci ve QA Mimarisi
**Durum:** Faz 1 planı tamamlandı. Faz 2 (PDF extraction) kapsam dışı, ayrı plan gerektirir.
**Kaynak:** SDSPass Kontrol Asistanı denetimleri (DIPL222–DIPL225), 8 doğrulanmış + 1 devam eden bulgu (BULGU 9) üzerinden türetildi.
---
## 1. Veri Akışı (Faz 1 — extraction var olduğu andan itibaren)
```
[Manuel giriş: CAS+konsantrasyon] ──┐
                                      ├──→ Normalize veri modeli ──→ Ön-doğrulama (a0)
[Tedarikçi PDF — Faz 2, AYRI PLAN] ──┘     (CAS+konsantrasyon+ürün bilgisi)
```
- **Faz 1 girdisi:** Sadece manuel giriş. Tedarikçi PDF→veri modeli dönüşümü (OCR/extraction) henüz kurulu değil — bu konuşmanın kapsamı dışında, ayrı bir plan gerektirir.
- **Ön-doğrulama (a0):** CAS no format geçerliliği, konsantrasyon toplamının %100'ü aşmaması, duplikasyon kontrolü. Faz 2 geldiğinde extraction hatalarını (OCR/sütun eşleme yanlışlığı) da kapsayacak şekilde genişletilir.
---
## 2. Motor Bağımlılık Haritası
```
clp_engine ──┐
             ├──→ ppe_engine ──→ transport_engine ──→ p_code_service ──→ sds_sentence_service
eco_engine ──┤
physical ────┘
```
**Kritik kural:** `transport_engine`, `clp_engine` + `physical_engine` + `eco_engine`'in **birleşik** H-kodu çıktısını görmeden çalışmaz (BULGU 2'nin kök nedeni: H314'ü görmeden UN3139/O2 seçimi).
`ppe_engine`, `eco_engine` + `clp_engine`'in birleşik setini görür (H400/H410 bazı PPE kurallarını tetikleyebilir).

**`transport_engine` mimari notu:** Mevcut yapı *enumerated* (`if cls=='5.1' and sub=='8': ...`) — her yeni Sınıf+ikincil-tehlike kombinasyonu için elle branch eklenir. Bu yaklaşımda **asla tam genel olunmaz**, sadece bilinen kombinasyon sayısı artar (BULGU 2 tam buydu: 5.1+8 dalı unutulmuştu). Doğru çözüm branch eklemek değil, motoru ADR §2.1.3.10 öncelik tablosuna **veri olarak** bağlamak (table-driven) — tablo tüm kombinasyonları içeriyorsa hiçbir kombinasyon "unutulamaz"; eksikse bu da (a1) sorunu olur, kod sorunu olmaz.
---
## 3. Kalıcı Kayıt ve Çıktı Formatı
| Format | Rol |
|---|---|
| **JSON** | Birincil, kalıcı kayıt. Ara format değil — versiyonlanan kaynak gerçek. Her revizyon saklanır, diff alınabilir. |
| **PDF** | Resmi dağıtım çıktısı. |
| **Word** | Opsiyonel — sadece manuel düzenleme talebi varsa üretilir. |
---
## 4. QA Taksonomisi — 5 Katman + Severity
| Katman | Kapsam | Severity | Örnek (gerçek bulgu) |
|---|---|---|---|
| **(a0)** Girdi doğrulama | Format/toplam/duplikasyon — Faz 2'de extraction hatalarını da kapsar | KRİTİK | — (Faz 2 kapsamı) |
| **(a1)** Veri bütünlüğü | Kaynak tablo/JSON eksik mi | KRİTİK/UYARI | NaOH `data/annex6/13/1310-73-2.json` boş `"class"` |
| **(a2)** Hesap mantığı | Doğru veri var, formül doğru uygulanıyor mu | KRİTİK/UYARI | ATEmix exclude/unknown karışıklığı (BULGU 8) |
| **(a3)** Plausibility guard | Çıktı makul mü — **otomatik blok değil, sadece sinyal** | BİLGİ | KN=320°C + ≥%25 su içeren sıvı çelişkisi (BULGU 6) |
| **(b)** Bölümler arası tutarlılık | Çıktılar birbirini tutuyor mu — *enumerated branch ile değil, table-driven lookup ile genel hale gelir (bkz. Bölüm 2 `transport_engine` notu)* | KRİTİK/UYARI | UN no ↔ H314 (BULGU 2); M(Akut)/M(Kronik) ↔ B2.1 |
| **(c)** Bölüm içi çakışma/bastırma | Gerçek çelişki mi, yoksa senaryo farklılaşması mı | UYARI | KKE "Tip 3 veya 4" vs "Tip 4 min" (gerçek çelişki — BULGU 4) vs solunum bloğu (senaryo farkı — format sorunu) |

### Operasyonel kararlar
1. **(a1) düzeltmesi (a2)'yi test etmiş sayılmaz.** Kaynak veri dolduktan sonra, kodun "boş veri" durumunu nasıl işlediği **ayrıca**, sahte bir boşlukla test edilmeli.
2. **(a1)'in bulduğu kritik boşluk, mevcut "sertifikalı hazırlayıcı onayı" kapısına otomatik bağlanır** — ayrı mekanizma icat edilmez.
3. **(c)'ye girmeden önce sınıflandırma şart:** gerçek çelişki (öncelik kuralı gerekir) mi, senaryo farklılaşması (format düzeltmesi gerekir) mi? Yanlış sınıflandırma → gerekli bilginin silinmesi riski.

### Uygulama sırası
```
1. (a1) tarama scripti        ← en ucuz, en hızlı geri dönüş (veri pull'ları zaten yakın zamanda oldu)
2. (a2) bilinen hesap hataları ← ATEmix gibi spesifik düzeltmeler (fixture'larla kilitlenir, bkz. Bölüm 6a)
3. (b) bölümler arası kontrol  ← üretim verisiyle hemen test edilebilir
4. (a3) + (c)                  ← false positive kalibrasyonu küçük ölçekte yapıldıktan sonra
```
Bu sıra bir tercih değil zorunluluktur — gerekçe Bölüm 5 temel ilkesinde (AI, motor doğruluğu üstüne çıkamaz).
---
## 5. AI'ın Pipeline'a Yerleşimi
**Temel ilke:**
AI çıktı kalitesi, motor çıktı doğruluğunun üstüne çıkamaz —
sadece onu görünür/anlaşılır kılar. Motor katmanı (a1/a2/b)
doğrulanmadan AI'ya karar/üretim rolü verilmesi, hatayı gizlice
ölçeklendirir: mekanik tablo çıktısı yerine akıcı cümle
görünümünde üretilir, insan denetçi daha fazla effortla yakalar.

**Canlı kanıt:** Bu projede "doğrulama raporu" belgeleri —
satır numaraları, kod blokları, kesin Tablo referansları —
iki fabrikasyon regülasyon iddiası içeriyordu. Format ve ton
"doğru" sinyali verdi, içerik yanlıştı.

### Bölge 1 — AI'ın asla girmediği yer
`clp_engine / eco_engine / physical_engine / transport_engine` — deterministik hesap/eşik/sınıflandırma. Kural-tabanlı kod olarak kalır. Sebep: aynı girdi her zaman aynı çıktıyı vermeli; LLM bunu garanti edemez (bu denetim sürecinde iki kez kanıtlandı: ATEmix'i ilk seferde kontrolsüz kabul etmek, ve dış "doğrulama raporu"nun var olmayan "CLP Tablo 2.13 bileşen eşiği" iddiası).

### Bölge 2 — AI'ın katkı sağladığı yer
| Yer | Görev | Kısıt |
|---|---|---|
| Faz 2 — Extraction | Tedarikçi PDF'inden tablo okuma | Çıkardığı her değer (a0)'dan geçmeden motora gitmez |
| `sds_sentence_service` | B4-B7, B10, B13 serbest metinleri doğal dile dökme | Yeni sayı/bilgi üretme izni yok — sadece motor çıktısını cümleye çevirir |
| Kontrol asistanı | Pipeline dışı, paralel ikinci-göz denetimi | Kendi sayısal sonucunu kod çalıştırarak doğrular, kafadan yazmaz |

### Bölge 3 — Sınırda kalan yer
Manuel giriş asistanı (konuşmalı "H kodu ver, P kodu üreteyim" arayüzü) — motor zincirinin önünde kolaylaştırıcı, motorun kendisi değil. Ürettiği her P kodu/sınıflandırma mutlaka deterministik motorlardan geçer; AI'ın kendi hafızasından kod önermesi yasak.
---
## 6. Guardrail'ler (zorunlu)
1. **AI çıktısı (b) katmanına tabi bir "bölüm" sayılır** — ayrı kontrol icat edilmez, mevcut bölümler-arası-tutarlılık kontrolü AI çıktısını da kapsar.
2. **Atıf doğrulama** — AI'ın yazdığı her madde/tablo numarası, mevcut lookup tablosunda gerçekten var mı diye otomatik string-match'ten geçer.
3. **Dil sızıntısı kontrolü** — KKDİK Ek-2 §0.2.4 (akronim/kısaltma yasağı) AI üretimi metne de uygulanır.
4. **KRİTİK alanlarda AI son söz değil** — B2.1/B14 gibi alanlarda AI taslak üretebilir, nihai değer her zaman deterministik motordan gelir.

### Implementation notu — `sds_sentence_service` çıktı doğrulama
"Sadece ifade üret" kısıtı prompt seviyesinde verilse de mekanik olarak zorlanmalı:
1. Üretilen her cümle regex/parse ile taranır: sayısal değerler (%, mg/kg, °C, pH), H/P/EUH kodları, CAS no, madde/tablo referansları çıkarılır.
2. Her token, o bölüm için AI'a girdi olarak verilen yapılandırılmış motor çıktısında **birebir var mı** kontrol edilir (çıktı token kümesi ⊆ girdi token kümesi).
3. Girdide karşılığı olmayan bir token çıktıda varsa → otomatik blok, render edilmez, **kendi başına KRİTİK** işaretlenir (fabrikasyon riski — "doğrulama raporu" vakasının üretim hattı karşılığı).
---
## 6a. Test Coverage
Mevcut `tests/test_classification_fixtures.py` ~85 satır — (a2) katmanını *sistematik* hale getirmek için yetersiz. Üç bileşen:

1. **Never-regress fixtures (silinmez kategori).** Bu denetim sürecinde bulunan vakalar — NaOH/KOH %4,9→1B (BULGU 1), ATEmix su-exclude (BULGU 8), UN3098 vs UN3139 (BULGU 2) — genel regression setinden **ayrı** işaretlenir. Genel sete gömülürse biri "redundant" diyip silebilir; bunlar silinemez, çünkü her biri gerçek bir denetim maliyetiyle bulundu.

2. **Fixture → üretim bağlantısı (gate).** Üretimde mevcut fixture setiyle eşleşmeyen bir **yeni H-kodu çifti** geçtiğinde **ve** motor bu çift için SCL/ATE değerini **interpolate ediyorsa** otomatik flag — "bu kombinasyon için fixture yok, insan onayı bekliyor." Salt yeni CAS no tetikleyici değildir — bu zaten (a1) kapsamında (kaynak veri var mı kontrolü); aksi halde gate her yeni madde ilk kullanımında çalar, gürültü üretir. (a1)'in onay-kapısı mekanizmasıyla aynı prensip, ama (a2)'ye özel ve daraltılmış.

3. **Zorunlu regülasyon atfı.** Her fixture, beklenen değerle birlikte kaynağını da taşır: `assert ate_mix(input) == 202.10  # CLP Ek-I §3.1.3.6.1 — su exclude edilir`. Atıfsız fixture, "neden bu değer doğru" sorusunu üç ay sonra cevapsız bırakır — biri "yanlış görünüyor" diyip değeri sessizce değiştirebilir.

Önerilen minimum motor kapsamı:
```
clp_service    → ATE hesabı, H300/H301/H302 sınırları, SCL bant geçişleri (NaOH/KOH)
eco_engine     → M-faktörlü ve M-faktörsüz H410/H411 geçişleri
transport      → H280/H281/H270/H314 UN seçimleri (table-driven geçişten sonra)
p_code_service → H281 P282+P336+P315+P403, H280 P410+P403
```
---
## 7. Kapsam Dışı (Faz 2 — ayrı plan gerektirir)
- Tedarikçi PDF → normalize veri modeli (OCR/extraction motoru)
- Extraction'a özgü (a0) genişletmesi (OCR yanlış okuma, sütun eşleme hataları)
---
---
## 8. BULGU 9 — CLP Ek-VI `*` Dipnotu Yanlış Yorumlanmış (Teyit Bekliyor)

**Tespit:** `update_annex_vi.py` `NOTE_TEXTS['*']` ve `pdf_sds_service.py` `_NOTE_FLAG_LABELS['*']` aynı yanlış metni içeriyor:
> "Sınıflandırma koşula bağlı (belirli form veya konsantrasyon)"

**Gerçek anlam (CLP Ek-VI Part 1):** Sınıflandırma tablosunda `Acute Tox. 4*` gibi `h_class` sonundaki tek yıldız = **asgari sınıflandırma** — üretici/ithalatçı daha ağır kategoriye işaret eden veriye sahipse daha ağır sınıflandırma uygulanmalıdır. "Form veya konsantrasyon" farklı bir CLP not türüdür.

**Ölçek:** Annex VI verilerinde 1.640 madde (4.173'ün ~%39'u) `note_flag='*'` taşıyor. Bu maddelerin geçtiği her SDS'te bu yanlış footnote üretiliyor. DIPL223/224/225 denetimlerinde görülen "*" footnote'unun kaynağı bu satır.

**Not ayrımı — kodda doğru olan:**
| Bayrak | PDF metni (mevcut) | Doğru mu? |
|--------|-------------------|-----------|
| `*`    | "form veya konsantrasyon" | **YANLIŞ** — asgari sınıflandırma olmalı |
| `**`   | "Hedef organ ve/veya maruziyet yolu SDS Bölüm 11'de belirtilmeli" | DOĞRU (STOT) |
| `***`  | "Üreme toks. yalnızca belirtilen alt kategori için geçerli" | DOĞRU |
| `****` | "Patlayıcı alt sınıfı belirsiz" | DOĞRU |

**Ayrıca:** `generate_knowledge_lists.py` tüm `note_flag` değerlerini `' **'` (çift yıldız) olarak markdown'a yazıyor — `*`/`**`/`***`/`****` ayrımı kayboluyor, bilgi listesi yanıltıcı hale geliyor.

**Durum:** Birincil kaynaktan (CLP Tüzüğü Ek-VI Part 1 veya SEA Yönetmeliği Ek-6) teyit bekleniyor. Teyit sonrası:
1. `update_annex_vi.py` `NOTE_TEXTS['*']` düzelt
2. `pdf_sds_service.py` `_NOTE_FLAG_LABELS['*']` düzelt
3. `generate_knowledge_lists.py` `note_flag` marker'ını gerçek flag değerini yansıtacak şekilde düzelt
4. `data/annex6/*.json` + `data/cl/*.json` içindeki `"note"` alanlarını yeniden üret (`update_annex_vi.py` ile)
5. Never-regress fixture ekle: `*` bayraklı madde → SDS'te doğru footnote metni

**QA katmanı:** (a2) — veri mevcut ve doğru (`note_flag=True`), ama metin yorumu yanlış → yanlış SDS çıktısı.

---
*Bu belge, SDSPass Kontrol Asistanı'nın DIPL222–DIPL225 denetimlerinde bulduğu 8 doğrulanmış bulgudan (BULGU 1-8) türetilmiştir. BULGU 9 teyit sürecindedir. Her QA katmanı, en az bir gerçek bulguyla doğrulanmıştır — boşta kalan kategori yoktur.*
