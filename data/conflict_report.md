# JSON Çelişki Raporu
Tarih: 2026-06-26 12:34
Model: claude-haiku-4-5-20251001

## sea_ek6_tr.json — 1 çelişki

| CAS | Alan | JSON Değeri | Belgede Olan | Açıklama |
|-----|------|-------------|--------------|----------|
| 7637-07-2 | classification | H314 ile "Akut Tok. 2" eşleşmesi | H330 ile "Akut Tok. 2" eşleşmesi | Boron trifluoride için H kodları yanlış sıralandı |

## substance_db.json — 4 çelişki

| CAS | Alan | JSON Değeri | Beklenen | Açıklama |
|-----|------|-------------|----------|----------|
| 1333-74-0 | classification | Press. Gas / boş h_code | H280 gerekli | Basınç altı gaz H280 olmadan geçersiz |
| 7637-07-2 | classification | Press. Gas / H330 | H280 gerekli | Basınç altı gaz H330 ile eşleşmiyor |
| 7637-07-2 | classification | Acute Tox. 2 / H314 | H330 gerekli | Acute Tox. 2 sınıfı H314 ile uyumsuz |
| 7637-07-2 | classification | Skin Corr. 1A / boş | H314 gerekli | Skin Corr. 1A sınıfı h_code olmadan geçersiz |