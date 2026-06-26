# SDSPass Doğrulama Raporu
Tarih: 2026-06-26 08:09
Model: claude-sonnet-4-6

---
## 1. H/P/EUH KOD DOĞRULAMASI

Verilen PDF belgelerini ve sistem metinlerini dikkatle karşılaştırıyorum.

## HATALI METİNLER

| Kod | Sistemdeki metin | Doğru metin (PDF) |
|-----|-----------------|-------------------|
| H200 | Kararsız patlayıcı. | Kararsız patlayıcı |
| H201 | Patlayıcı; kütlesel patlama tehlikesi. | Patlayıcı; kütlesel patlama zararı |
| H202 | Patlayıcı; ciddi saçılma tehlikesi. | Patlayıcı; ciddi yansıtım zararı |
| H203 | Patlayıcı; yangın, patlama veya saçılma tehlikesi. | Patlayıcı; yangın, patlama veya yansıtım zararı |
| H204 | Yangın veya saçılma tehlikesi. | Yangın veya yansıtım zararı. |
| H220 | Son derece alevlenir gaz. | Çok kolay alevlenir gaz |
| H222 | Son derece alevlenir aerosol. | Çok kolay alevlenir aerosol |
| H224 | Son derece alevlenir sıvı ve buhar. | Çok kolay alevlenir sıvı ve buhar. |
| H229 | Basınçlı kap: ısıtıldığında patlayabilir. | Basınçlı kap: ısıtıldığında patlayabilir (PDF'de bu kod yer almamaktadır; EUH044 ile karıştırılmamalı) |
| H251 | Kendi kendine ısınır; büyük miktarlarda tutuşabilir. | Kendiliğinden ısınır; alev alabilir. |
| H252 | Büyük miktarlarda kendi kendine ısınır; yangına yol açabilir. | Büyük miktarlarda kendiliğinden ısınır; yangına yol açabilir. |
| H260 | Su ile temas halinde kendiliğinden tutuşabilen alevlenir gazlar açığa çıkar. | Su ile temas ettiğinde kendiliğinden tutuşabilen alevlenir gazlar yayar. |
| H261 | Su ile temas halinde alevlenir gaz açığa çıkar. | Su ile temas ettiğinde alevlenir gazlar yayar. |
| H270 | Yangına yol açabilir veya şiddetlendirebilir; yükseltgen. | Yangına yol açabilir veya yangını şiddetlendirebilir; oksitleyici. |
| H271 | Yangına veya patlamaya yol açabilir; güçlü yükseltgen. | Yangına veya patlamaya yol açabilir; güçlü oksitleyici. |
| H272 | Yangını şiddetlendirebilir; yükseltgen. | Yangını güçlendirebilir; oksitleyici. |
| H280 | Basınç altında gaz içerir; ısındığında patlayabilir. | Basınçlı gaz içerir; ısıtıldığında patlayabilir. |
| H281 | Soğutulmuş gaz içerir; kriyojenik yanıklara veya yaralanmalara yol açabilir. | Soğutulmuş gaz içerir; soğuktan yanma veya yaralanmalara yol açabilir. |
| H290 | Metallere karşı aşındırıcı olabilir. | Metalleri aşındırabilir. |
| H302 | Yutulması halinde zararlıdır. | Yutulması halinde zararlıdır (PDF ile uyumlu, ancak nokta eksik değil) |
| H304 | Yutulması ve soluk yoluna girmesi halinde öldürücü olabilir. | Solunum yoluna nüfuzu ve yutulması halinde öldürücüdür. |
| H317 | Alerjik cilt reaksiyonuna yol açabilir. | Alerjik cilt reaksiyonlarına yol açar. |
| H318 | Ciddi göz hasarına yol açar. | Ciddi göz hasarına yol açar (uyumlu) |
| H334 | Solunması halinde alerji veya astım belirtilerine ya da solunum güçlüklerine yol açabilir. | Solunması halinde nefes alma zorlukları, astım nöbetleri veya alerjiye yol açabilir. |
| H336 | Uyuşukluğa veya baş dönmesine yol açabilir. | Rehavete veya baş dönmesine yol açabilir. |
| H340 | Kalıtsal genetik hasara yol açabilir. | Genetik hasara yol açabilir. |
| H341 | Kalıtsal genetik hasara yol açabileceğinden şüphelenilmektedir. | Genetik hasara yol açma şüphesi var. |
| H350 | Kansere yol açabilir. | Kansere yol açabilir (uyumlu) |
| H351 | Kansere yol açtığından şüphelenilmektedir. | Kansere yol açma şüphesi var. |
| H360 | Doğurganlığa veya doğmamış çocuğa zarar verebilir. | Doğmamış çocukta hasar yol açabilir veya üremeye zarar verebilir. |
| H360D | Doğmamış çocuğa zarar verebilir. | Doğmamış çocukta hasara yol açabilir. |
| H360F | Doğurganlığa zarar verebilir. | Üremeye zarar verebilir. |
| H360FD | Doğurganlığa veya doğmamış çocuğa zarar verebilir. | Doğmamış çocukta hasar yol açabilir veya üremeye zarar verebilir. |
| H361 | Doğurganlığa veya doğmamış çocuğa zarar verebileceğinden şüphelenilmektedir. | Doğmamış çocukta hasar yol açma veya üremeye zarar verme şüphesi var. |
| H370 | Organlara hasar verir. | Organlarda hasara yol açar. |
| H371 | Organlara hasar verebilir. | Organlarda hasara yol açabilir. |
| H372 | Uzun süreli veya tekrarlı maruz kalma sonucu organlarda hasara yol açar. | Uzun süreli veya tekrarlı maruz kalma sonucu organlarda hasara yol açar (uyumlu) |
| H373 | Uzun süreli veya tekrarlanan maruziyetle organlara hasar verebilir. | Uzun süreli veya tekrarlı maruz kalma sonucu organlarda hasara yol açabilir. |
| H400 | Sucul organizmalar için çok toksiktir. | Sucul ortamda çok toksiktir. |
| H401 | Sucul organizmalar için toksiktir. | Sucul ortamda toksiktir. |
| H402 | Sucul organizmalar için zararlıdır. | Sucul ortamda zararlıdır. |
| H410 | Uzun süre kalıcı etkiyle sucul organizmalar için çok toksiktir. | Sucul ortamda uzun süre kalıcı, çok toksik etki. |
| H411 | Uzun süre kalıcı etkiyle sucul organizmalar için toksiktir. | Sucul ortamda uzun süre kalıcı, toksik etki. |
| H412 | Uzun süre kalıcı etkiyle sucul organizmalar için zararlıdır. | Sucul ortamda uzun süre kalıcı, zararlı etki. |
| H413 | Sucul organizmalar üzerinde uzun süre kalıcı zararlı etkilere yol açabilir. | Sucul ortamda uzun süre kalıcı, zararlı etki yapabilir. |
| H420 | Üst atmosferdeki ozonu tahrip ederek halk sağlığına ve çevreye zarar verir. | Atmosferin üst katmanındaki ozon tabakasını tahrip ederek kamu sağlığına ve çevreye zarar verir. |
| EUH014 | Su ile şiddetli reaksiyon verir. | Su ile şiddetli tepkime verir. |
| EUH029 | Su ile temas halinde toksik gaz çıkarır. | Su ile temasında toksik gaz çıkarır. |
| EUH031 | Asitlerle temas halinde toksik gaz çıkarır. | Asitlerle temasında toksik gaz çıkarır. |
| EUH032 | Asitlerle temas halinde çok toksik gaz çıkarır. | Asitlerle temasında çok toksik gaz çıkarır. |
| EUH066 | Tekrarlı maruziyetle deri kuruması veya çatlamasına yol açabilir. | Tekrarlı maruz kalmalarda ciltte kuruluğa veya çatlaklara neden olabilir. |
| EUH070 | Gözle temas halinde toksiktir. | Gözle teması halinde toksiktir. |
| EUH201 | Kurşun içerir. Çocukların erişebileceği yerlerde kullanılmamalıdır. | Kurşun içerir. Çocuklar tarafından çiğnenebilecek veya emilebilecek yüzeylerde kullanılmamalıdır. |
| EUH202 | Siyanakrilat. Tehlike. Saniyeler içinde cilde ve göze yapışır. Çocukların erişemeyeceği yerde tutun. | Siyanoakrilat. Tehlikelidir. Cildi ve gözleri saniyeler içinde yapıştırır. Çocukların erişiminden uzak tutun. |
| EUH203 | Krom (VI) içerir. Alerjik reaksiyona yol açabilir. | Krom (VI) içerir. Alerjik reaksiyonlara neden olabilir. |
| EUH204 | İzosiyonat içerir. Alerjik reaksiyona yol açabilir. | İzosiyanat içerir. Alerjik reaksiyonlara yol açabilir. |
| EUH205 | Epoksi bileşenleri içerir. Alerjik reaksiyona yol açabilir. | Epoksi bileşenleri içerir. Alerjik reaksiyonlara yol açabilir. |
| EUH206 | Dikkat! Diğer ürünlerle birlikte kullanmayın. Tehlikeli gazlar çıkabilir. | Dikkat! Diğer ürünlerle birlikte kullanmayın. Tehlikeli gazlar açığa çıkarabilir (klorür). |
| EUH207 | Dikkat! Kadmiyum içerir. Kullanım sırasında tehlikeli dumanlar oluşur. | Dikkat! Kadmiyum içerir. Kullanım esnasında tehlikeli dumanlara ortaya çıkar. İmalatçı tarafından sağlanan bilgilere başvurun. Güvenlik talimatlarına uyun. |
| EUH208 | {substance} içerir. Alerjik reaksiyona yol açabilir. | (hassaslaştırıcı maddenin adı) içerir. Alerjik reaksiyona yol açabilir. |
| EUH209 | Kullanımda yüksek alevlenir hâle gelebilir. | Kullanım esnasında çok alevlenir hale gelebilir. |
| EUH209A | Kullanımda alevlenir hâle gelebilir. | Kullanım esnasında alevlenir hale gelebilir. |
| EUH210 | İstek üzerine güvenlik bilgi formu temin edilebilir. | Talep halinde güvenlik bilgi formu sağlanabilir. |
| P201 | Kullanmadan önce özel talimatları edinin. | Kullanmadan önce özel talimatları okuyun. |
| P210 | Isı, kıvılcım, açık alev ve sıcak yüzeylerden uzak tutun. Sigara içmeyin. | Isıdan/kıvılcımdan/alevden/sıcak yüzeylerden uzak tutun. – Sigara içilmez. |
| P220 | Giysi, yanıcı maddeler ve organik maddelerden uzakta saklayın. | Kıyafetlerden/.../yanıcı malzemelerden uzak tutun/saklayın. |
| P231 | Inert gaz altında işleyin ve saklayın. | Asal gaz ile elleçleyin. |
| P231+P232 | İnert gaz altında işleyin. Nemi önleyin. | Asal gaz ile elleçleyin. Nemden koruyun. |
| P232 | Nemi önleyin. | Nemden koruyun. |
| P240 | Kaba ve alıcı ekipmana toprak bağlantısı yapın. | Kabı ve alıcı ekipmanı toprağa oturtun/bağlayın. |
| P244 | Basınçlı gazları yağ ve gres yağından uzak tutun. | Kısma vanalarını gres ve yağdan uzak tutun. |
| P250 | Taşlamaya, sürtünmeye, darbeye veya çarpışmaya maruz bırakmayın. | Öğütme/şok/.../sürtünmeye maruz bırakmayın. |
| P260 | Toz/duman/gaz/sis/buhar/sprey solumayın. | Tozunu/dumanını/gazını/sisini/buharını/spreyini solumayın. |
| P261 | Toz/duman/gaz/sis/buhar/sprey solumaktan mümkün olduğunca kaçının. | Tozunu/dumanını/gazını/sisini/buharını/spreyini solumaktan kaçının. |
| P264 | Kullanımdan sonra ellerinizi iyice yıkayın. | Elleçlemeden sonra .... ile iyice yıkayın. |
| P271 | Yalnızca açık alanda veya iyi havalandırılmış bir alanda kullanın. | Sadece dışarıda veya iyi havalandırılan bir alanda kullanın. |
| P273 | Çevreye salınımından kaçının. | Çevreye verilmesinden kaçının. |
| P280 | Koruyucu eldiven/koruyucu giysi/göz koruyucu/yüz koruyucu kullanın. | Koruyucu eldiven/koruyucu kıyafet/göz koruyucu/yüz koruyucu kullanın. |
| P284 | Yeterli havalandırma sağlanamıyorsa solunum koruyucu kullanın. | Solunum koruyucu giyin. |
| P285 | Yeterli havalandırma sağlanamıyorsa solunum koruyucu kullanın. | Yetersiz havalandırma varsa, solunum koruyucu giyin. |
| P301+P310 | YUTULMASI HALİNDE: Hemen Zehir Danışma Merkezi'ni (114) veya doktoru arayın. | YUTULDUĞUNDA: ULUSAL ZEHİR DANIŞMA MERKEZİNİN 114 NOLU TELEFONUNU veya doktoru/hekimi arayın. |
| P301+P312 | YUTULMASI HALİNDE: Kendinizi iyi hissetmiyorsanız Zehir Danışma Merkezi'ni (114) veya doktoru arayın. | YUTULDUĞUNDA: Kendinizi iyi hissetmiyorsanız ULUSAL ZEHİR DANIŞMA MERKEZİNİN 114 NOLU TELEFONUNU veya doktoru/hekimi arayın. |
| P301+P330+P331 | YUTULMASI HALİNDE: Ağzı çalkalayın. Kusturmayın. | YUTULDUĞUNDA: Ağzınızı çalkalayın. İstifra etmeye ÇALIŞMAYIN. |
| P302+P334 | CİLDE TEMAS DURUMUNDA: Soğuk suya sokun ya da ıslak pansuman yapın. | DERİ İLE TEMAS HALİNDE İSE: Soğuk suya daldırın/ıslak bezlerle sarın. |
| P302+P350 | CİLDE TEMAS DURUMUNDA: Bol su ve sabunla dikkatlice yıkayın. | DERİ İLE TEMAS HALİNDE İSE: Bol sabun ve su ile iyice yıkayın. |
| P302+P352 | CİLDE TEMAS DURUMUNDA: Bol sabun ve su ile yıkayın. | DERİ İLE TEMAS HALİNDE İSE: Bol sabun ve su ile yıkayın. |
| P303+P361+P353 | CİLDE (veya SAÇA) TEMAS DURUMUNDA: Kirlenmiş giysileri hemen çıkarın. Cilt suyla durulanır/duş alınır. | DERİ (veya saç) İLE TEMAS HALİNDE İSE: Kirlenmiş tüm giysilerinizi hemen kaldırın/çıkartın. Cildinizi su/duş ile durulayın. |
| P304+P340 | SOLUNMASI HALİNDE: Kişiyi temiz havaya çıkarın. Nefes almakta güçlük çekiyorsa solunum kolaylaştırıcı pozisyona getirin. | SOLUNDUĞUNDA: Zarar gören kişiyi temiz havaya çıkartın ve kolay biçimde nefes alması için rahat bir pozisyonda tutun. |
| P304+P341 | SOLUNMASI HALİNDE: Solunumu güçleştiriyorsa, kişiyi temiz havaya çıkarın ve nefes almayı kolaylaştıracak pozisyona getirin. | SOLUNDUĞUNDA: Nefes alıp vermesi zorlaşmış ise, zarar gören kişiyi temiz havaya çıkartın ve kolay biçimde nefes alması için rahat bir pozisyonda tutun. |
| P305+P351+P338 | GÖZ İLE TEMAS HALİNDE: Birkaç dakika suyla dikkatlice durulayın. Varsa ve çıkarması kolaysa kontak lensleri çıkartın. Durulamaya devam edin. | GÖZ İLE TEMASI HALİNDE: Su ile birkaç dakika dikkatlice durulayın. Takılı ve yapması kolaysa, kontak lensleri çıkartın. Durulamaya devam edin. |
| P306+P360 | GİYSİ İLE TEMAS HALİNDE: Giysileri çıkarmadan önce etkilenen alanı suyla iyice durulayın. | GİYSİ İLE TEMASI HALİNDE: kirlenmiş giysi ve cildinizi, giysilerinizi çıkarmadan önce bol su ile hemen durulayın. |
| P307+P311 | MARUZ KALINMASI HALİNDE: Zehir Danışma Merkezi'ni (114) veya doktoru arayın. | Maruz kalnma halinde: ULUSAL ZEHİR DANIŞMA MERKEZİNİN 114 NOLU TELEFONUNU veya doktoru/hekimi arayın. |
| P308+P313 | MARUZ KALMA VEYA ENDİŞE DURUMUNDA: Tıbbi yardım/bakım alın. | Maruz kalınma veya etkileşme halinde İSE: Tıbbi yardım/bakım alın. |
| P310 | Hemen Zehir Danışma Merkezi'ni (114) veya doktoru arayın. | Hemen ULUSAL ZEHİR DANIŞMA MERKEZİNİN 114 NOLU TELEFONUNU veya doktoru/hekimi arayın. |
| P311 | Zehir Danışma Merkezi'ni (114) veya doktoru arayın. | ULUSAL ZEHİR DANIŞMA MERKEZİNİN 114 NOLU TELEFONUNU veya doktoru/hekimi arayın. |
| P312 | Kendinizi iyi hissetmiyorsanız Zehir Danışma Merkezi'ni (114) veya doktoru arayın. | Kendinizi iyi hissetmezseniz, ULUSAL ZEHİR DANIŞMA MERKEZİNİN 114 NOLU TELEFONUNU veya doktoru/hekimi arayın. |
| P320 | Derhal özel tedavi uygulanması zorunludur (bakınız bu etiket). | Özel acil müdahale gerekli (etikete bakın). |
| P321 | Özel tedavi (bakınız bu etiket). | Özel müdahale gerekli (etikete bakın). |
| P322 | Özel tedbirler (bakınız bu etiket). | Özel önlemler (etikete bakın). |
| P332+P313 | CİLT TAHRİŞİ OLUŞMASI HALİNDE: Tıbbi yardım alın. | Ciltte tahriş söz konusu ise: Tıbbi yardım/müdahale alın. |
| P333+P313 | CİLT TAHRİŞİ VEYA DÖKÜNTÜLERİ OLUŞMASI HALİNDE: Tıbbi yardım alın. | Ciltte tahriş veya kaşıntı söz konusu ise: Tıbbi yardmı/müdahale alın. |
| P334 | Soğuk suya sokun ya da ıslak pansuman yapın. | Soğuk suya daldırın/ıslak bezlerle sarın. |
| P335+P334 | Deriden gevşek partikülleri fırçalayın. Soğuk suya sokun ya da ıslak pansuman yapın. | Parçacıkları cildinizden hafifçe temizleyin. Soğuk suya daldırın/ıslak bezlerle sarın. |
| P336+P315 | Donmuş bölümleri ılık su ile eritin. Etkilenmiş alanı silmeyin. Hemen tıbbi tavsiye/müdahale alın. | Donmuş bölümleri ılık su ile eritn. Etkilenmiş alanı silmeyin. |
| P337+P313 | GÖZ TAHRİŞİ DEVAM ETMESİ HALİNDE: Tıbbi yardım alın. | Göz tahrişi kalıcı ise: Tıbbi yardım/bakım alın. |
| P340 | Kişiyi temiz havaya çıkarın ve nefes almayı kolaylaştıracak pozisyona getirin. | Zarar gören kişiyi temiz havaya çıkartın ve kolay biçimde nefes alması için rahat bir pozisyonda tutun. |
| P342+P311 | SOLUNUM SEMPTOMLARININ OLUŞMASI HALİNDE: Zehir Danışma Merkezi'ni (114) veya doktoru arayın. | Solunum bulguları gösterirse: ULUSAL ZEHİR DANIŞMA MERKEZİNİN 114 NOLU TELEFONUNU veya doktoru/hekimi arayın. |
| P361 | Kirlenmiş giysileri hemen çıkarın. | Kirlenmiş tüm giysilerinizi hemen kaldırın/çıkarın. |
| P361+P364 | Kirlenmiş giysileri derhal çıkarın ve yeniden giymeden önce yıkayın. | Kirlenmiş tüm giysilerinizi hemen kaldırın/çıkartın ve yeniden kullanmadan önce yıkayın. |
| P362 | Kirlenmiş giysileri çıkarın. | Kirlenmiş giysilerinizi çıkarın ve yeniden kullanmadan önce yıkayın. |
| P362+P364 | Kirlenmiş giysileri çıkarın ve yeniden giymeden önce yıkayın. | Kirlenmiş giysilerinizi çıkarın ve yeniden kullanmadan önce yıkayın. |
| P363 | Yeniden giymeden önce kirlenmiş giysileri yıkayın. | Kirlenmiş giysilerinizi yeniden kullanmadan önce yıkayın. |
| P370+P376 | YANGIN HALINDE: Tehlike yoksa sızıntıyı durdurun. | Yangın durumunda: Güvenli ise sızıntıyı durdurun. |
| P370+P378 | YANGIN HALINDE: Kuru kimyasal, CO₂ veya alkole dayanıklı köpük kullanın. | Yangın durumunda: Söndürme için ... kullanın. |
| P370+P380 | YANGIN HALINDE: Bölgeden uzaklaşın. | Yangın durumunda: Alanı boşaltın. |
| P371+P380+P375 | BÜYÜK YANGIN VE BÜYÜK MİKTARLAR HALİNDE: Bölgeden uzaklaşın. Uzaktan söndürün. | Büyük yangın ve büyük miktarlar durumunda: Alanı boşaltın. Patlama riskine karşı yangına uzaktan müdahale edin. |
| P372 | Yangın halinde patlama riski. | Yangın durumunda patlama riski. |
| P373 | Yangın patlayıcıya ulaştığında YANGINLA MÜCADELE ETMEYİN. | Yangın patlayıcılara ulaştığında, yangına MÜDAHALE ETMEYİN. |
| P375 | Patlama riski nedeniyle uzaktan yangınla mücadele edin. | Patlama riskine karşı yangınla uzaktan savaşın. |
| P376 | Tehlike yoksa sızıntıyı durdurun. | Güvenli ise sızıntıyı durdurun. |
| P377 | SIZINTI YAPAN GAZ YANGINI: Söndürmeye çalışmayın. Sızıntı güvenle durdurulamazsa. | Gaz sızıntısına bağlı yangın: Sızıntı güvenli olarak durdurulmadan söndürmeyin. |
| P390 | Çevrenin kirlenmesini önlemek için döküleni/saçılanı emdir. | Maddi hasarı önlemek için sıvı döküntüleri temizleyin. |
| P391 | Döküntüyü toplayın. | Döküleni toplayın. |
| P401 | ... maddesine uygun şekilde saklayın. | ....depolayın. |
| P402 | Kuru yerde saklayın. | Kuru alanda depolayınız. |
| P402+P404 | Kuru yerde ve kapalı kapta saklayın. | Kuru alanda depolayınız. Kapalı bir kapta depolayın. |
| P403 | İyi havalandırılmış yerde saklayın. | İyi havalandırılan yerde depolayın. |
| P403+P233 | İyi havalandırılmış yerde saklayın. Kabı sıkıca kapalı tutun. | İyi havalandırılmış bir alanda depolayınız. Kabı sıkıca kapalı tutun. |
| P403+P235 | İyi havalandırılmış serin yerde saklayın. | İyi havalandırılmış bir alanda depolayın. Soğuk tutun. |
| P404 | Kapalı kapta saklayın. | Kapalı bir kapta depolayın. |
| P405 | Kilitli yerde saklayın. | Kilit altında saklayın. |
| P406 | Aşındırmaya dayanıklı/... iç yüzeyine sahip kapta saklayın. | Aşındırıcılara karşı dayanıklı/dayanıklı bir iç astara sahip...kapta depolayın. |

---
## 2. SEA EK-6 DOĞRULAMASI

Aşağıda her iki veri setini CAS numarasına göre eşleştirerek karşılaştırma sonuçlarını sunuyorum.

---

## HATALI KAYITLAR

| CAS | Alan | Sistemdeki değer | Belgedeki doğru değer |
|-----|------|-----------------|----------------------|
| **109-95-5** (etil nitrit) | classification | H kodu boş olan 5. sınıf: `{"class": "Akut Tok. 4", "h_code": ""}` mevcut + toplam 5 sınıf kaydı var | Belgede yalnızca 4 sınıf: Alev.Gaz 1/H220, Basınç Gaz/H332, Akut Tok. 4/H312, Akut Tok. 4/H302 — 5. boş kayıt YOK |
| **84988-93-2** (fenoller, amonyak) | notes | `["JM"]` (tek string, bitişik) | `"J M"` (ayrı iki not: J ve M) |
| **90640-90-7** (naftalin yağları) | notes | `["JM"]` (tek string, bitişik) | `"J M"` (ayrı iki not: J ve M) |
| **91995-16-3** (antrasen yağı) | notes | `["JM"]` (tek string, bitişik) | `"J M"` (ayrı iki not: J ve M) |
| **133-07-3** (folpet) | m_factors | `{"acute": 10, "chronic": 10}` | Belgede yalnızca `M=10` yazıyor (acute için); chronic M faktörü belirtilmemiş — chronic: 10 fazladan girmiş olabilir. Ancak folpet için Sucul Akut 1 (H400) sınıfı mevcut, Sucul Kronik sınıfı YOK → chronic M faktörü sisteme hatalı girilmiş |
| **422556-08-9** (piroksulam) | m_factors | `{"acute": 100, "chronic": 100}` | Belgede `M = 100` ve `M = 100` (hem acute hem chronic ayrı satırda) — bu alan **DOĞRU** ✓ |
| **141-43-5** (etanolamin) | scl_limits | `[{"h_code": "H335", "class": "BHOT Tek Mrz. 3", "op": ">=", "min": 5.0, "max": null, "unit": "%"}]` | Belgede: `BHOT Tek Mrz. 3; H335: C ≥ %5` — **DOĞRU** ✓ |

---

### Detaylı Açıklamalar

#### 1. CAS 109-95-5 — Etil Nitrit (classification fazladan boş kayıt)

| Sistem | Belge |
|--------|-------|
| Alev.Gaz 1 / H220 ✓ | Alev.Gaz 1 / H220 |
| Basınç Gaz / H332 ✓ | Basınç Gaz / H332 |
| Akut Tok. 4 / H312 ✓ | Akut Tok. 4 / H312 |
| Akut Tok. 4 / H302 ✓ | Akut Tok. 4 / H302 |
| **Akut Tok. 4 / "" ✗** | — (yok) |

> Sistemde 5. satır olarak `{"class": "Akut Tok. 4", "h_code": ""}` şeklinde **H kodu boş** bir kayıt var. Belgede bu 5. kayıt **bulunmuyor**.

---

#### 2. CAS 84988-93-2 / 90640-90-7 / 91995-16-3 — Notes alanı

| CAS | Sistemdeki | Belgedeki |
|-----|-----------|-----------|
| 84988-93-2 | `["JM"]` | `J` ve `M` (ayrı) |
| 90640-90-7 | `["JM"]` | `J` ve `M` (ayrı) |
| 91995-16-3 | `["JM"]` | `J` ve `M` (ayrı) |

> Sistem notları birleştirilmiş tek string olarak saklamış (`"JM"`), ancak `J` ve `M` iki **ayrı** notu ifade etmektedir. Doğru format: `["J", "M"]`

---

#### 3. CAS 133-07-3 — Folpet (m_factors chronic hatası)

| Alan | Sistemdeki | Belgedeki |
|------|-----------|-----------|
| m_factors | `{"acute": 10, "chronic": 10}` | `M=10` (yalnızca acute için — Sucul Akut 1/H400 mevcut) |
| classification | Sucul Akut 1 / H400 var, **Sucul Kronik yok** | Sucul Akut 1 / H400 var, Sucul Kronik **yok** |

> Belgede Folpet için Sucul Kronik sınıflandırması bulunmadığından `chronic: 10` M faktörü **gereksiz/hatalı** girilmiştir.

---

### Eşleşen ve Doğru Olan Kayıtlar (Sorunsuz)

Aşağıdaki CAS numaraları için tüm alanlar **uyumlu**:

| CAS | Madde |
|-----|-------|
| 98377-35-6 | 1-(2-klorofenil)-tetrazol-5-on |
| 104558-95-4 | tiyobis... tepkime kütlesi |
| 34681-10-2 | bütokarboksim |
| 51601-57-1 | 4-(4-toliloksi)bifenil |
| 78-92-2 | bütan-2-ol |
| 141-43-5 | etanolamin |
| 1314-05-2 | nikel selenit |
| 55612-11-8 | timin türevi |
| 123312-54-9 | dimetildioktadesilam. |
| 23783-26-8 | hidroksifosfonoasetik asit |
| 141773-73-1 | siklohekzil propanoat |
| 624-86-2 | O-etilhidroksilamin |
| 86552-32-1 | (4-fenilbütil)fosfinik asit |
| 583-59-5 | 2-metilsiklohekzanol |
| 90-72-2 | 2,4,6-tris(dimetilaminometil)fenol |
| 85136-74-9 | piridinkarbonitril türevi |
| 2687-94-7 | N-(n-oktil)-2-pirrolidon |
| 88558-41-2 | iyodpropinil karbamat |
| 135043-64-0 | 4-amino-2-(aminometil)fenol |
| 108-90-7 | klorobenzen |
| 101896-26-8 | BTX-zengin damıtık |
| 422556-08-9 | piroksulam |
| 452962-97-9 | isoindol-azo türevi |
| 106264-79-3 | bis(metiltiyo)fenilen diamin |
| 129050-62-0 | trisodyum β-alanin |
| 98-00-0 | furfuril alkol |
| 167678-46-8 | klorokarbonil metilfenil asetat |
| 60207-31-0 | azakonazol |
| 90274-24-1 | hidroksifenil prop. fenol HCl |
| 97675-85-9 | C16-20 hidrokarbon |
| 64742-76-3 | naftenik yağlar |
| 75-20-7 | kalsiyum karbür |
| 68512-61-8 | petrol artıkları |
| 64742-38-7 | kil işlem görmüş damıtık |

---

## ÖZET

| Metrik | Değer |
|--------|-------|
| Karşılaştırılan madde sayısı | **40** |
| Hatalı kayıt sayısı | **5** |
| Doğru kayıt sayısı | **35** |
| Belgede bulunup sistemde olmayan | **0** |
| Sistemde bulunup belgede olmayan | **0** |

### Hataların Özeti:
1. **109-95-5** → `classification` listesinde fazladan boş H kodlu kayıt
2. **84988-93-2** → `notes` alanında `"JM"` yerine `["J","M"]` olmalı
3. **90640-90-7** → `notes` alanında `"JM"` yerine `["J","M"]` olmalı
4. **91995-16-3** → `notes` alanında `"JM"` yerine `["J","M"]` olmalı
5. **133-07-3** → `m_factors.chronic = 10` hatalı; belgede yalnızca acute M=10 mevcut
