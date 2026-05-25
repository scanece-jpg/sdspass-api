---
name: TR SDS Sınıflandırma Arama Hiyerarşisi
description: TR SDS hazırlamak için kimyasal veri kaynakları öncelik sırası (kullanıcı tanımlı)
type: project
---

TR SDS için kimyasal sınıflandırma verisi bu sırayla aranır:

| Sıra | Kaynak | Dosya | Not |
|------|--------|-------|-----|
| 1 | SEA Yönetmeliği Ek-6 (TR Annex VI) | `substances_annex_vi.json` | Mutlak — CAS eşleşirse bu sınıflandırma ve M-faktörü kullanılır |
| 2 | ECHA C&L Arşivi | `data/echa_cl_archive.json` | Kalıcı lokal arşiv — önceki API çekimleri |
| 3 | ECHA C&L Inventory (PubChem API) | Canlı çekim | En yüksek bildirim sayılı sınıflandırma → arşive otomatik kaydedilir |
| 4 | Tedarikçi SDS (Kullanıcı girişi) | `substances_custom.json` | Kullanıcının elle girdiği veriler |
| 5 | Hesaplama Modülü | `clp_engine.js` | M-faktörü yoksa toksisite verilerinden hesapla |
| 6 | TR Ek-1 Tablo 3.1.2 | — | LD50/LC50 yoksa ATE değerleri (henüz uygulanmadı) |

**Why:** Kullanıcı bu sıralamayı TR mevzuatına uygun SDS hazırlama için belirledi.

**How to apply:** Yeni CAS lookup özelliği eklenirken her zaman bu hiyerarşiyi izle. EU için ayrı bir hiyerarşi verilecek (ileride).
