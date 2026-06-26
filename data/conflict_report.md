# JSON Çelişki Raporu
Tarih: 2026-06-26 13:54
Model: claude-haiku-4-5-20251001

## sea_ek6_tr.json — 9 çelişki

| CAS | Alan | JSON Değeri | Belgede Olan | Açıklama |
|-----|------|-------------|--------------|----------|
| 1333-74-0 | h_codes | H280 | H220 | Basınç Gaz için H280 değil H220 kodlanmalıdır |
| 7637-07-2 | h_codes | H280 | H330 | Basınç Gaz için H280 değil H330 kodlanmalıdır |
| 10294-34-5 | h_codes | H280 | H330 | Basınç Gaz için H280 değil H330 kodlanmalıdır |
| 630-08-0 | h_codes | H280 | H220 | Basınç Gaz için H280 değil H220 kodlanmalıdır |
| 75-44-5 | h_codes | H280 | H330 | Basınç Gaz için H280 değil H330 kodlanmalıdır |
| 142-59-6 | h_codes | H410 | H410 | Sucul Kronik 1 için H410 değil boş olmamalıdır (H410 doğru) |
| 7664-41-7 | kayit_bulunamadi | ammonia, anhydrous | - | CAS No referans belgede bulunmamaktadır |
| 7782-44-7 | kayit_bulunamadi | oxygen | - | CAS No referans belgede bulunmamaktadır |
| 2699-79-8 | kayit_bulunamadi | sulphuryl difluoride | - | CAS No referans belgede bulunmamaktadır |

## substance_db.json — 42 çelişki

| CAS | Alan | JSON Değeri | Beklenen | Açıklama |
|-----|------|-------------|----------|----------|
| 74-90-8 | m_factors | {} | {"acute": 1, "chronic": 1} | Aquatic Acute 1 ve Aquatic Chronic 1 sınıflandırması m_factors gerektirir |
| 119-38-0 | classification | Acute Tox. 1 (H310) + Acute Tox. 2 (H300) | Tutarsız | Aynı madde için iki farklı Acute Tox kategorisi geçersiz |
| 137-42-8 | m_factors | {} | {"acute": 1, "chronic": 1} | Aquatic Acute 1 ve Aquatic Chronic 1 sınıflandırması m_factors gerektirir |
| 60568-05-0 | m_factors | {} | {"acute": 10, "chronic": 10} | Aquatic Acute 1 (H400) ve Aquatic Chronic 1 (H410) sınıflandırması m_factors gerektirir |
| 2094-99-7 | m_factors | {} | {"acute": 1, "chronic": 1} | Aquatic Acute 1 (H400) ve Aquatic Chronic 1 (H410) sınıflandırması m_factors gerektirir |
| 24934-91-6 | m_factors | acute: 10, chronic: 10 | acute: 1, chronic: 1 | Aquatic Acute 1 ve Chronic 1 için m-factor minimum 1 olmalı, ancak daha yüksek değerler justifikasyon gerektirir - standart CLP H400/H410 için tipik m-factor 1'dir |
| 21923-23-9 | m_factors | acute: 1000, chronic: 1000 | acute: 1, chronic: 1 | Aquatic Acute 1 ve Chronic 1 için m-factor 1000 aşırı yüksektir - CLP standart m-factor 1 veya maksimum 10'dur |
| 7778-54-3 | m_factors | chronic: 10 | chronic: 1 | Aquatic Acute 1 (H400) sınıflandırması varken Aquatic Chronic sınıflandırması yoktur, chronic m-factor geçersizdir |
| 1317-38-0 | m_factors | acute: 100 | acute: 10 | Aquatic Acute 1 (H400) standardı m-faktörü 10 olmalıdır, 100 değeri CLP kriterlerine aykırıdır |
| 8011-63-0 | m_factors | chronic: 1 | chronic: 10 | Aquatic Chronic 1 (H410) standardı m-faktörü 10 olmalıdır, 1 değeri CLP kriterlerine aykırıdır |
| 7758-99-8 | m_factors | chronic: 1 | chronic: 10 | Aquatic Chronic 1 (H410) standardı m-faktörü 10 olmalıdır, 1 değeri CLP kriterlerine aykırıdır |
| 15571-58-1 | classification | H372 (immune system) | H372 | H kodu organ spesifik notasyonu içeremez, sadece H372 olmalıdır |
| 57583-35-4 | classification | H372 (nervous system, immune system) | H372 | H kodu organ spesifik notasyonu içeremez, sadece H372 olmalıdır |
| 102851-06-9 | m_factors | {} | acute ve chronic m_factors gerekli | Aquatic Acute 1 (H400) ve Aquatic Chronic 1 (H410) için m_factors tanımlanması zorunlu |
| 87392-12-9 | m_factors | acute: 10, chronic: 10 | acute: 1, chronic: 1 | Aquatic Acute 1 ve Aquatic Chronic 1 için M-faktör 1 olmalıdır |
| 16484-77-8 | m_factors | acute: 10, chronic: 10 | acute: 1, chronic: 1 | Aquatic Acute 1 ve Aquatic Chronic 1 için M-faktör 1 olmalıdır |
| 163520-33-0 | m_factors | {} | {"acute": 1, "chronic": 1} | Aquatic Acute 1 (H400) ve Aquatic Chronic 1 (H410) sınıflandırması m_factor gerektirir |
| 500791-70-8 | m_factors | {"acute": 10, "chronic": 10} | {"acute": 1, "chronic": 1} | Aquatic Acute 1 (H400) için m_factor 1 olmalı, Aquatic Chronic 1 (H410) için m_factor 1 olmalı |
| 69094-18-4 | classification | Expl. 1.1 / H201 | uyumsuz | Patlayıcı 1.1 ile Cilt Corr. 1A, Skin Sens. 1 ve Aquatic sınıflandırması çelişkilidir; patlayıcı madde olarak tehlikeli-tepkiselliği baskındır |
| 104206-82-8 | classification | H373 (eyes, nervous system) | H373 | H-kodu tanım içermemeli; "H373" kullanılmalı |
| 52645-53-1 | classification | Skin Sens. 1 | Skin Sens. 1A veya 1B | H317 için CLP'de Skin Sens. 1 geçersiz, 1A/1B alt kategorileri zorunlu |
| 52645-53-1 | m_factors | acute: 1000, chronic: 1000 | acute: 1, chronic: 1 | Aquatic Acute 1 ve Chronic 1 için m-factor 1000 geçersizdir, standart değer 1'dir |
| 15662-33-6 | m_factors | {} (boş) | acute: 1, chronic: 1 | Aquatic Acute 1 ve Chronic 1 için m-factor tanımlanması gerekir |
| 161326-34-7 | m_factors | {} | {"acute": 1, "chronic": 1} | Aquatic Acute 1 (H400) ve Aquatic Chronic 1 (H410) için m_factors gereklidir |
| 72963-72-5 | classification | Aquatic Chronic 1 / H boş | H410 gerekli | Aquatic Chronic 1 sınıflandırması H410 hazard statement'ı gerektir |
| 142469-14-5 | m_factors | acute:10, chronic:10 | boş {} | Skin Sens. 1 için M-faktör tanımlanmamıştır, aquatic için M-faktör uygunsuz |
| 138182-18-0 | m_factors | acute: 1, chronic: 1 | {} | Aquatic Acute 1 ve Chronic 1 sınıflandırması m_factor tanımı gerektirir ama değerler CLP kriterlerine uymuyor |
| 422556-08-9 | m_factors | acute: 100, chronic: 100 | acute: 1, chronic: 1 | Aquatic Acute 1 ve Aquatic Chronic 1 için m-factor 1 olmalı, 100 değil |
| 100784-20-1 | m_factors | acute: 1000, chronic: 1000 | acute: 100, chronic: 100 | Aquatic Acute 1 ve Aquatic Chronic 1 için m-factor maksimum 100 olmalı |
| 1085-98-9 | m_factors | {"acute": 10} | boş veya M-factor belirtilmemesi | Aquatic Acute 1 (H400) M-factor gerektirmez; m_factors alanı sadece akut aquatik toksisite M-factor'ü içeriyorsa geçerlidir |
| 1918-16-7 | classification | Aquatic Acute 1 + Aquatic Chronic 1 | H410 veya H400 tek başına | Aynı anda hem H410 hem H400 ile sınıflandırma mantıksal tutarsız; H410 zaten H400'ü içerir |
| 15263-52-2 | m_factors | {} | acute: 1 | Aquatic Acute 1 (H400) H410 gerektirir m_factor |
| 15972-60-8 | classification | Aquatic Chronic 1 (H410) | M-factor chronic: 1 eksik | H410 için m_factor chronic gerekli |
| 5836-73-7 | m_factors | {} | acute: 1 | Acute Tox. 2 (H300) m_factor gerekli |
| 101794-74-5 | notes | ["M"] | [] | Carc. 1B için M-factor notu geçersiz; M-factorlar yalnızca akut/kronik toksisitede uygulanır |
| 101794-75-6 | notes | ["M"] | [] | Carc. 1B için M-factor notu geçersiz; M-factorlar yalnızca akut/kronik toksisitede uygulanır |
| 101794-76-7 | notes | ["M"] | [] | Carc. 1B için M-factor notu geçersiz; M-factorlar yalnızca akut/kronik toksisitede uygulanır |
| 68187-57-5 | notes | ["M"] | [] | Carc. 1B için M-factor notu geçersiz; M-factorlar yalnızca akut/kronik toksisitede uygulanır |
| 122070-78-4 | notes | ["M"] | [] | Carc. 1B için M-factor notu geçersiz; M-factorlar yalnızca akut/kronik toksisitede uygulanır |
| 84989-10-6 | notes | ["M"] | [] | Carc. 1B için M-factor notu geçersiz; M-factorlar yalnızca akut/kronik toksisitede uygulanır |
| 90640-80-5 | notes | ["M"] | [] | Carc. 1B için M-factor notu geçersiz; M-factorlar yalnızca akut/kronik toksisitede uygulanır |
| 92061-93-3 | notes | ["M"] | [] | Carc. 1B için M-factor notu geçersiz; M-factorlar yalnızca akut/kronik toksisitede uygulanır |