# JSON Çelişki Raporu
Tarih: 2026-06-26 12:39
Model: claude-haiku-4-5-20251001

## sea_ek6_tr.json — 3 çelişki

| CAS | Alan | JSON Değeri | Belgede Olan | Açıklama |
|-----|------|-------------|--------------|----------|
| 7637-07-2 | classification | H314 paired with Akut Tok. 2 | H330 paired with Akut Tok. 2; H314 paired with Cilt Aşnd. 1A | Boron trifluoride: H kodu ve sınıf eşleştirmesi yanlış |
| 10294-34-5 | h_codes | H330, H300, H314 | H330, H300, H314 | Boron trichloride için "Basınç Gaz" sınıfına H kodu atanmamış (JSON'da boş) |
| 10294-34-5 | notes | [] | U | Boron trichloride için U notu eksik |

## substance_db.json — 6 çelişki

| CAS | Alan | JSON Değeri | Beklenen | Açıklama |
|-----|------|-------------|----------|----------|
| 1333-74-0 | classification | Press. Gas / boş | H280 gerekli | Basınç altı gaz H280 olmadan geçersiz |
| 7637-07-2 | classification | Press. Gas / H330 | H280 gerekli | Basınç altı gaz H330 ile etiketlenemez |
| 7637-07-2 | classification | Acute Tox. 2 / H314 | H330 gerekli | Akut Toks. 2 için H330 (solunum) beklenir, H314 cilt korozyondur |
| 7637-07-2 | classification | Skin Corr. 1A / boş | H314 gerekli | Cilt Korozyon 1A sınıfı H314 hazard kodu olmadan geçersiz |
| 10294-34-5 | classification | Skin Corr. 1B / H314 boş | Skin Corr. 1B için H314 gerekli | Skin Corr. 1B sınıfı H314 hazard statement olmadan eksiktir |
| 10294-34-5 | classification | Press. Gas / H330 | H280 gerekli | Basınç altı gaz için H330 yanlış, H280 olmalıdır |