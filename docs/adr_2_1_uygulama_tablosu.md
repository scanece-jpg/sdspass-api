# ADR 2025 Bölüm 2.1 — madde madde uygulama tablosu

Kaynak: ECE/TRANS/352 Cilt I (sds-knowledge/en/2412006_E_ECE_TRANS_352_Vol.I_WEB_0.pdf).
Kod: `app/services/transport_engine.py` (TE), `app/services/transport_adr_service.py` (TAS), veri `data/adr_data.json`
(Tablo A), `data/adr_cas_map.json` (CAS → adlı giriş), `data/adr_group_map.json` (kimyasal grup). Test: `scripts/kontrol_seti.py` (KS).
Durum: **✓ uygulandı · ◐ kısmen · ✗ yok · — GBF kapsamı dışı**. Son gözden geçirme: 2026-10-10.

| Madde | Konu | Durum | Uygulama | Test / not |
|---|---|---|---|---|
| 2.1.1.1 | Sınıflar | ✓ | TE `H_TO_ADR`, `CLASS_LABELS` | KS ürün testleri |
| 2.1.1.2 | Giriş türleri A–D | ✓ | A: CAS haritası; B: UN 3149/1796/1786 vb.; C: `_GROUP_NOS`; D: genel B.B.B. | KS "2.1.3.6" |
| 2.1.1.3 | Ambalaj grubu | ✓ | TE sınıf PG'leri; Sınıf 8 2.2.8.1.6.3 hesabı; Tablo A PG listesi (301 giriş düzeltildi) | KS PG testleri, Tablo A tutarlılık |
| 2.1.2.1 | Sınıf ölçütleri 2.2.x.1 | ◐ | SEA H kodlarından türetiliyor (köprü); ADR'ye özgü ölçütler (ör. 6.1 buhar uçuculuğu 2.2.61.1.9) yok — H331 → 6.1 ihtiyatlı | Bilinen sınır |
| 2.1.2.2 | Adıyla geçen madde Tablo A'ya göre | ✓ | TAS seed + adr_cas_map (≈ 600 madde) | KS harita testi |
| 2.1.2.3 | Teknik safsızlık / katkı | ◐ | %1 altı bileşen sayılmıyor (Sınıf 8: 2.2.8.1.6.3.2; diğerleri SEA Ek-1 1.1.2.2.1 eşiği) | |
| 2.1.2.4 | Taşınması yasak maddeler (2.2.x.2) | ✗ | — | Nadir; KDU |
| 2.1.2.5 | Adıyla geçmeyen → toplu giriş | ✓ | TE `_get_un_entry` | |
| 2.1.2.6 | Test sonucuna göre sınıflandırma | ◐ | Kullanıcı test kararları (oksitleyici, metal aşındırıcılık, FP) | KS karar soruları |
| 2.1.2.7 | Erime noktası ≤ 20 °C → sıvı | ◐ | Ürün formu kullanıcıdan; erime noktasından otomatik hal belirlenmiyor | |
| 2.1.2.8 | Yetkili makam onaylı ek yan tehlike | — | Gönderen / yetkili makam işi | |
| 2.1.3.1 | Adıyla geçmeyen: tehlike derecesine göre | ✓ | TE | |
| 2.1.3.2 | Tek tehlikeli → o sınıf | ✓ | TE | |
| 2.1.3.3 | Baskın adlı madde + ADR dışı maddeler | ◐ | Sınıf, yan tehlike, PG, hal kontrolü ✓; (b) "yalnız saf madde" adları kısmen (hal); (d) acil müdahale farkı ✗ (uzman kararı) | KS etanol/aseton/formik testleri |
| 2.1.3.4.1 | İçeren karışım her zaman aynı girişte | ◐ | `_ALWAYS_SAME_ENTRY`: propilenimin, etilenimin, Ni/Fe karbonil, metil/etil izosiyanat, brom | HCN (1051/1613/1614/3294), HF > %85, erimiş POBr3 ✗ |
| 2.1.3.4.2 | PCB / polihalojenli bifeniller | ◐ | UN 2315 (başka tehlikeli bileşen yoksa) | 3151/3152/3432 ✗ |
| 2.1.3.4.3 | PCB içeren kullanılmış eşya | — | GBF kapsamı dışı | |
| 2.1.3.5.1 | Özellik ölçüm / hesap | ◐ | SEA hesabı + kullanıcı ölçümleri | |
| 2.1.3.5.2 | Belirlenemezse ana tehlike | ✓ | Belirsizse karar sorusu / "belirlenmemiştir" (KKDİK Ek-2 B14) | KS ADR_NAMED_UNKNOWN |
| 2.1.3.5.3 | Öncelikli zararlar (7, 1, 2, …) | ◐ | Sınıf 1, 2, 5.2 önceliği ✓; 6.1 soluma PG I özel kuralı ✗ | |
| 2.1.3.5.4 | Öncelik tablosu 2.1.3.10 | ✓ | TE `resolve_conflict`, `_PT` | KS |
| 2.1.3.5.5 | Atık | — | GBF kapsamı dışı | |
| 2.1.3.6 | En özel toplu giriş | ✓ | `_GROUP_NOS` + `adr_group_map.json` (alkol, keton, ester, eter, aldehit, hidrokarbon, amin, kostik alkali) | KS "2.1.3.6"; grup üyeliği IUPAC ad ekleriyle, KDU gözden geçirmeli |
| 2.1.3.7 | Oksitleyici karışımın patlayıcı özelliği | ✗ | — | Uzman / test |
| 2.1.3.8 | Çevreye zararlı (ek olarak) / UN 3077–3082 | ✓ | TE `env_mark`, Sınıf 9 | KS |
| 2.1.3.9 | Basel atıkları | — | GBF kapsamı dışı | |
| 2.1.3.10 | Öncelik tablosu | ✓ | TE `_PT` | KS |
| 2.1.4 | Numuneler | — | GBF kapsamı dışı | |
| 2.1.5 | Tehlikeli mal içeren eşya | — | GBF kapsamı dışı | |
| 2.1.6 | Boş temizlenmemiş ambalaj | — | GBF kapsamı dışı | |

## Açık maddeler (✗ / ◐) — sırayla ele alınacak
1. 2.1.2.1 / 2.1.3.5.3: 6.1 soluma ölçütü (buhar uçuculuğu V, 2.2.61.1.9) — şu an H331 → 6.1 ihtiyatlı.
2. 2.1.3.4.1: HCN, HF > %85, erimiş POBr3 satırları.
3. 2.1.3.3 (d) ve 2.1.3.7: uzman kararı gerektirir — panelde not olarak.
4. 2.1.2.7: erime noktasından hal belirleme.
