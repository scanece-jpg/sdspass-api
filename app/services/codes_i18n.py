"""
SDSPass — Kod Metinleri Çok Dilli Kütüphane
============================================
H, EUH, P kodları + depolama/taşıma/KKE cümleleri
Tüm dillerde tek kaynak.

Desteklenen diller: TR, EN, DE, PL, BG, RO, HU, CZ, SK, HR, LT, US_EN
"""

from functools import lru_cache

# ══════════════════════════════════════════════════════════════════════════════
# H KODU METİNLERİ
# ══════════════════════════════════════════════════════════════════════════════

H_STMTS = {
    'TR': {
        'H200':'Kararsız patlayıcı.',
        'H201':'Patlayıcı; kütlesel patlama tehlikesi.',
        'H202':'Patlayıcı; ciddi saçılma tehlikesi.',
        'H203':'Patlayıcı; yangın, patlama veya saçılma tehlikesi.',
        'H204':'Yangın veya saçılma tehlikesi.',
        'H220':'Son derece alevlenir gaz.',
        'H221':'Alevlenir gaz.',
        'H222':'Son derece alevlenir aerosol.',
        'H223':'Alevlenir aerosol.',
        'H224':'Son derece alevlenir sıvı ve buhar.',
        'H225':'Kolay alevlenir sıvı ve buhar.',
        'H226':'Alevlenir sıvı ve buhar.',
        'H228':'Alevlenir katı.',
        'H229':'Basınçlı kap: ısıtıldığında patlayabilir.',
        'H232':'Hava ile temas halinde kendiliğinden tutuşabilir.',
        'H230':'Hava olmaksızın patlayıcı reaksiyon verebilir.',
        'H231':'Yüksek basınç ve/veya sıcaklıkta hava olmaksızın patlayıcı reaksiyon verebilir.',
        'H240':'Isındığında patlayabilir.',
        'H241':'Isındığında yangına veya patlamaya yol açabilir.',
        'H242':'Isındığında yangına yol açabilir.',
        'H250':'Havaya maruz kaldığında kendiliğinden tutuşur.',
        'H251':'Kendi kendine ısınır; büyük miktarlarda tutuşabilir.',
        'H252':'Büyük miktarlarda kendi kendine ısınır; yangına yol açabilir.',
        'H260':'Su ile temas halinde kendiliğinden tutuşabilen alevlenir gazlar açığa çıkar.',
        'H261':'Su ile temas halinde alevlenir gaz açığa çıkar.',
        'H270':'Yangına yol açabilir veya şiddetlendirebilir; yükseltgen.',
        'H271':'Yangına veya patlamaya yol açabilir; güçlü yükseltgen.',
        'H272':'Yangını şiddetlendirebilir; yükseltgen.',
        'H280':'Basınç altında gaz içerir; ısındığında patlayabilir.',
        'H281':'Soğutulmuş gaz içerir; kriyojenik yanıklara veya yaralanmalara yol açabilir.',
        'H290':'Metallere karşı aşındırıcı olabilir.',
        'H300':'Yutulması halinde öldürücüdür.',
        'H301':'Yutulması halinde toksiktir.',
        'H302':'Yutulması halinde zararlıdır.',
        'H303':'Yutulması halinde zararlı olabilir.',
        'H304':'Yutulması ve soluk yoluna girmesi halinde öldürücü olabilir.',
        'H305':'Yutulması ve soluk yoluna girmesi halinde zararlı olabilir.',
        'H310':'Cilt ile teması halinde öldürücüdür.',
        'H311':'Cilt ile teması halinde toksiktir.',
        'H312':'Cilt ile teması halinde zararlıdır.',
        'H313':'Cilt ile teması halinde zararlı olabilir.',
        'H314':'Ciddi cilt yanıklarına ve göz hasarına yol açar.',
        'H315':'Cilt tahrişine yol açar.',
        'H316':'Hafif cilt tahrişine yol açar.',
        'H317':'Alerjik cilt reaksiyonuna yol açabilir.',
        'H318':'Ciddi göz hasarına yol açar.',
        'H319':'Ciddi göz tahrişine yol açar.',
        'H320':'Göz tahrişine yol açar.',
        'H330':'Solunması halinde öldürücüdür.',
        'H331':'Solunması halinde toksiktir.',
        'H332':'Solunması halinde zararlıdır.',
        'H333':'Solunması halinde zararlı olabilir.',
        'H334':'Solunması halinde alerji veya astım belirtilerine ya da solunum güçlüklerine yol açabilir.',
        'H335':'Solunum yolu tahrişine yol açabilir.',
        'H336':'Uyuşukluğa veya baş dönmesine yol açabilir.',
        'H340':'Kalıtsal genetik hasara yol açabilir.',
        'H341':'Kalıtsal genetik hasara yol açabileceğinden şüphelenilmektedir.',
        'H350':'Kansere yol açabilir.',
        'H351':'Kansere yol açtığından şüphelenilmektedir.',
        'H360':'Doğurganlığa veya doğmamış çocuğa zarar verebilir.',
        'H361':'Doğurganlığa veya doğmamış çocuğa zarar verebileceğinden şüphelenilmektedir.',
        'H362':'Emzirilen çocuğa zarar verebilir.',
        'H370':'Organlara hasar verir.',
        'H371':'Organlara hasar verebilir.',
        'H372':'Uzun süreli veya tekrarlanan maruziyetle organlara hasar verir.',
        'H373':'Uzun süreli veya tekrarlanan maruziyetle organlara hasar verebilir.',
        'H400':'Sucul organizmalar için çok toksiktir.',
        'H401':'Sucul organizmalar için toksiktir.',
        'H402':'Sucul organizmalar için zararlıdır.',
        'H410':'Uzun süre kalıcı etkiyle sucul organizmalar için çok toksiktir.',
        'H411':'Uzun süre kalıcı etkiyle sucul organizmalar için toksiktir.',
        'H412':'Uzun süre kalıcı etkiyle sucul organizmalar için zararlıdır.',
        'H413':'Sucul organizmalar üzerinde uzun süre kalıcı zararlı etkilere yol açabilir.',
        'H420':'Üst atmosferdeki ozonu tahrip ederek halk sağlığına ve çevreye zarar verir.',
    },
    'EN': {
        'H200':'Unstable explosive.',
        'H201':'Explosive; mass explosion hazard.',
        'H202':'Explosive; severe projection hazard.',
        'H203':'Explosive; fire, blast or projection hazard.',
        'H204':'Fire or projection hazard.',
        'H220':'Extremely flammable gas.',
        'H221':'Flammable gas.',
        'H222':'Extremely flammable aerosol.',
        'H223':'Flammable aerosol.',
        'H224':'Extremely flammable liquid and vapour.',
        'H225':'Highly flammable liquid and vapour.',
        'H226':'Flammable liquid and vapour.',
        'H228':'Flammable solid.',
        'H229':'Pressurised container: may burst if heated.',
        'H240':'Heating may cause an explosion.',
        'H241':'Heating may cause a fire or explosion.',
        'H242':'Heating may cause a fire.',
        'H250':'Catches fire spontaneously if exposed to air.',
        'H260':'In contact with water releases flammable gases which may ignite spontaneously.',
        'H261':'In contact with water releases flammable gas.',
        'H270':'May cause or intensify fire; oxidiser.',
        'H271':'May cause fire or explosion; strong oxidiser.',
        'H272':'May intensify fire; oxidiser.',
        'H280':'Contains gas under pressure; may explode if heated.',
        'H281':'Contains refrigerated gas; may cause cryogenic burns or injury.',
        'H290':'May be corrosive to metals.',
        'H300':'Fatal if swallowed.',
        'H301':'Toxic if swallowed.',
        'H302':'Harmful if swallowed.',
        'H303':'May be harmful if swallowed.',
        'H304':'May be fatal if swallowed and enters airways.',
        'H310':'Fatal in contact with skin.',
        'H311':'Toxic in contact with skin.',
        'H312':'Harmful in contact with skin.',
        'H313':'May be harmful in contact with skin.',
        'H314':'Causes severe skin burns and eye damage.',
        'H315':'Causes skin irritation.',
        'H316':'Causes mild skin irritation.',
        'H317':'May cause an allergic skin reaction.',
        'H318':'Causes serious eye damage.',
        'H319':'Causes serious eye irritation.',
        'H320':'Causes eye irritation.',
        'H330':'Fatal if inhaled.',
        'H331':'Toxic if inhaled.',
        'H332':'Harmful if inhaled.',
        'H333':'May be harmful if inhaled.',
        'H334':'May cause allergy or asthma symptoms or breathing difficulties if inhaled.',
        'H335':'May cause respiratory irritation.',
        'H336':'May cause drowsiness or dizziness.',
        'H340':'May cause genetic defects.',
        'H341':'Suspected of causing genetic defects.',
        'H350':'May cause cancer.',
        'H351':'Suspected of causing cancer.',
        'H360':'May damage fertility or the unborn child.',
        'H361':'Suspected of damaging fertility or the unborn child.',
        'H362':'May cause harm to breast-fed children.',
        'H370':'Causes damage to organs.',
        'H371':'May cause damage to organs.',
        'H372':'Causes damage to organs through prolonged or repeated exposure.',
        'H373':'May cause damage to organs through prolonged or repeated exposure.',
        'H400':'Very toxic to aquatic life.',
        'H401':'Toxic to aquatic life.',
        'H402':'Harmful to aquatic life.',
        'H410':'Very toxic to aquatic life with long lasting effects.',
        'H411':'Toxic to aquatic life with long lasting effects.',
        'H412':'Harmful to aquatic life with long lasting effects.',
        'H413':'May cause long lasting harmful effects to aquatic life.',
        'H420':'Harms public health and the environment by destroying ozone in the upper atmosphere.',
    },
    'DE': {
        'H220':'Extrem entzündbares Gas.',
        'H221':'Entzündbares Gas.',
        'H224':'Extrem entzündbarer flüssiger Stoff und Dampf.',
        'H225':'Leichtentzündbarer flüssiger Stoff und Dampf.',
        'H226':'Entzündbarer flüssiger Stoff und Dampf.',
        'H228':'Entzündbarer Feststoff.',
        'H270':'Kann Brand verursachen oder verstärken; Oxidationsmittel.',
        'H271':'Kann Brand oder Explosion verursachen; starkes Oxidationsmittel.',
        'H272':'Kann Brand verstärken; Oxidationsmittel.',
        'H280':'Enthält Gas unter Druck; kann bei Erwärmung explodieren.',
        'H290':'Kann gegenüber Metallen korrosiv sein.',
        'H300':'Lebensgefährlich bei Verschlucken.',
        'H301':'Giftig bei Verschlucken.',
        'H302':'Gesundheitsschädlich bei Verschlucken.',
        'H304':'Kann bei Verschlucken und Eindringen in die Atemwege tödlich sein.',
        'H310':'Lebensgefährlich bei Hautkontakt.',
        'H311':'Giftig bei Hautkontakt.',
        'H312':'Gesundheitsschädlich bei Hautkontakt.',
        'H314':'Verursacht schwere Verätzungen der Haut und schwere Augenschäden.',
        'H315':'Verursacht Hautreizungen.',
        'H317':'Kann allergische Hautreaktionen verursachen.',
        'H318':'Verursacht schwere Augenschäden.',
        'H319':'Verursacht schwere Augenreizung.',
        'H330':'Lebensgefährlich bei Einatmen.',
        'H331':'Giftig bei Einatmen.',
        'H332':'Gesundheitsschädlich bei Einatmen.',
        'H334':'Kann bei Einatmen Allergie, asthmaartige Symptome oder Atembeschwerden verursachen.',
        'H335':'Kann die Atemwege reizen.',
        'H336':'Kann Schläfrigkeit und Benommenheit verursachen.',
        'H340':'Kann genetische Defekte verursachen.',
        'H350':'Kann Krebs erzeugen.',
        'H351':'Kann vermutlich Krebs erzeugen.',
        'H360':'Kann die Fruchtbarkeit beeinträchtigen oder das Kind im Mutterleib schädigen.',
        'H370':'Schädigt die Organe.',
        'H372':'Schädigt die Organe bei längerer oder wiederholter Exposition.',
        'H400':'Sehr giftig für Wasserorganismen.',
        'H410':'Sehr giftig für Wasserorganismen mit langfristiger Wirkung.',
        'H411':'Giftig für Wasserorganismen mit langfristiger Wirkung.',
        'H412':'Schädlich für Wasserorganismen mit langfristiger Wirkung.',
        'H413':'Kann für Wasserorganismen schädlich sein mit langfristiger Wirkung.',
    },
}
# Diğer diller için EN fallback
H_STMTS['US_EN'] = H_STMTS['EN']


# ══════════════════════════════════════════════════════════════════════════════
# EUH KODU METİNLERİ
# ══════════════════════════════════════════════════════════════════════════════

EUH_STMTS = {
    'TR': {
        'EUH001':'Kuru hâlde patlayıcıdır.',
        'EUH006':'Hava ile veya havasız patlayıcıdır.',
        'EUH014':'Su ile şiddetli reaksiyon verir.',
        'EUH018':'Kullanım sırasında alevlenir/patlayıcı buhar-hava karışımı oluşturabilir.',
        'EUH019':'Patlayıcı peroksitler oluşturabilir.',
        'EUH029':'Su ile temas halinde toksik gaz çıkarır.',
        'EUH031':'Asitlerle temas halinde toksik gaz çıkarır.',
        'EUH032':'Asitlerle temas halinde çok toksik gaz çıkarır.',
        'EUH044':'Kapalı alanda ısındığında patlama riski taşır.',
        'EUH059':'Ozon tabakasına zararlıdır.',
        'EUH066':'Tekrarlı maruziyetle deri kuruması veya çatlamasına yol açabilir.',
        'EUH070':'Gözle temas halinde toksiktir.',
        'EUH071':'Solunum yoluna aşındırıcıdır.',
        'EUH201':'Kurşun içerir. Çocukların erişebileceği yerlerde kullanılmamalıdır.',
        'EUH201A':'Dikkat! Kurşun içerir.',
        'EUH202':'Siyanakrilat. Tehlike. Saniyeler içinde cilde ve göze yapışır. Çocukların erişemeyeceği yerde tutun.',
        'EUH203':'Krom (VI) içerir. Alerjik reaksiyona yol açabilir.',
        'EUH204':'İzosiyonat içerir. Alerjik reaksiyona yol açabilir.',
        'EUH205':'Epoksi bileşenleri içerir. Alerjik reaksiyona yol açabilir.',
        'EUH206':'Dikkat! Diğer ürünlerle birlikte kullanmayın. Tehlikeli gazlar çıkabilir.',
        'EUH207':'Dikkat! Kadmiyum içerir. Kullanım sırasında tehlikeli dumanlar oluşur.',
        'EUH208':'{substance} içerir. Alerjik reaksiyona yol açabilir.',
        'EUH209':'Kullanımda yüksek alevlenir hâle gelebilir.',
        'EUH209A':'Kullanımda alevlenir hâle gelebilir.',
        'EUH210':'İstek üzerine güvenlik bilgi formu temin edilebilir.',
        'EUH401':'İnsan sağlığına ve çevreye yönelik riskleri önlemek için kullanım talimatlarına uyun.',
    },
    'EN': {
        'EUH001':'Explosive when dry.',
        'EUH006':'Explosive with or without contact with air.',
        'EUH014':'Reacts violently with water.',
        'EUH018':'In use may form flammable/explosive vapour-air mixture.',
        'EUH019':'May form explosive peroxides.',
        'EUH029':'Contact with water liberates toxic gas.',
        'EUH031':'Contact with acids liberates toxic gas.',
        'EUH032':'Contact with acids liberates very toxic gas.',
        'EUH044':'Risk of explosion if heated under confinement.',
        'EUH059':'Hazardous to the ozone layer.',
        'EUH066':'Repeated exposure may cause skin dryness or cracking.',
        'EUH070':'Toxic by eye contact.',
        'EUH071':'Corrosive to the respiratory tract.',
        'EUH201':'Contains lead. Should not be used on surfaces liable to be chewed or sucked by children.',
        'EUH201A':'Warning! Contains lead.',
        'EUH202':'Cyanoacrylate. Danger. Bonds skin and eyes in seconds. Keep out of the reach of children.',
        'EUH203':'Contains chromium(VI). May produce an allergic reaction.',
        'EUH204':'Contains isocyanates. May produce an allergic reaction.',
        'EUH205':'Contains epoxy constituents. May produce an allergic reaction.',
        'EUH206':'Warning! Do not use together with other products. May release dangerous gases (chlorine).',
        'EUH207':'Warning! Contains cadmium. Dangerous fumes are formed during use.',
        'EUH208':'Contains {substance}. May produce an allergic reaction.',
        'EUH209':'Can become highly flammable in use.',
        'EUH209A':'Can become flammable in use.',
        'EUH210':'Safety data sheet available on request.',
        'EUH401':'To avoid risks to human health and the environment, comply with the instructions for use.',
    },
    'DE': {
        'EUH001':'Im trockenen Zustand explosiv.',
        'EUH014':'Reagiert heftig mit Wasser.',
        'EUH019':'Kann explosionsfähige Peroxide bilden.',
        'EUH029':'Entwickelt bei Berührung mit Wasser giftige Gase.',
        'EUH031':'Entwickelt bei Berührung mit Säure giftige Gase.',
        'EUH044':'Explosionsgefahr bei Erhitzen unter Einschluss.',
        'EUH059':'Die Ozonschicht schädigend.',
        'EUH066':'Wiederholter Kontakt kann zu spröder oder rissiger Haut führen.',
        'EUH070':'Giftig bei Augenkontakt.',
        'EUH071':'Ätzend für die Atemwege.',
        'EUH201':'Enthält Blei. Nicht für Kinder zugängliche Oberflächen verwenden.',
        'EUH202':'Cyanacrylat. Gefahr. Klebt innerhalb von Sekunden Haut und Augenlider zusammen.',
        'EUH203':'Enthält Chrom(VI). Kann allergische Reaktionen hervorrufen.',
        'EUH204':'Enthält Isocyanate. Kann allergische Reaktionen hervorrufen.',
        'EUH205':'Enthält Epoxid-Bestandteile. Kann allergische Reaktionen hervorrufen.',
        'EUH210':'Sicherheitsdatenblatt auf Anfrage erhältlich.',
        'EUH401':'Zur Vermeidung von Risiken für Mensch und Umwelt die Gebrauchsanleitung einhalten.',
    },
}
EUH_STMTS['US_EN'] = EUH_STMTS['EN']


# ══════════════════════════════════════════════════════════════════════════════
# P KODU METİNLERİ
# ══════════════════════════════════════════════════════════════════════════════

P_STMTS = {
    'TR': {
        'P101':'Tıbbi tavsiye için, mümkünse ürün kabını veya etiketini hazır bulundurun.',
        'P102':'Çocukların ulaşamayacağı yerde saklayın.',
        'P103':'Kullanmadan önce etiketi okuyun.',
        'P201':'Kullanmadan önce özel talimatları edinin.',
        'P202':'Tüm güvenlik talimatlarını okuyup anlamadan kullanmayın.',
        'P210':'Isı, kıvılcım, açık alev ve sıcak yüzeylerden uzak tutun. Sigara içmeyin.',
        'P211':'Açık alev veya diğer tutuşturma kaynaklarına karşı püskürtmeyin.',
        'P220':'Giysi, yanıcı maddeler ve organik maddelerden uzakta saklayın.',
        'P221':'Yanıcı maddelerle karışmasını önlemek için gerekli önlemleri alın.',
        'P222':'Hava ile temasına izin vermeyin.',
        'P223':'Suyla temasına izin vermeyin.',
        'P230':'Nemlendirilmiş halde saklayın.',
        'P231':'Inert gaz altında işleyin ve saklayın.',
        'P231+P232':'İnert gaz altında işleyin. Nemi önleyin.',
        'P232':'Nemi önleyin.',
        'P233':'Kabı sıkıca kapalı tutun.',
        'P234':'Yalnızca orijinal kabında saklayın.',
        'P235':'Serin yerde saklayın.',
        'P235+P410':'Serin yerde saklayın. Güneş ışığından koruyun.',
        'P240':'Kaba ve alıcı ekipmana toprak bağlantısı yapın.',
        'P241':'Patlamadan korunmalı elektrikli/havalandırma/aydınlatma teçhizatı kullanın.',
        'P242':'Sadece kıvılcım çıkarmayan aletler kullanın.',
        'P243':'Statik elektriği önleyici tedbirler alın.',
        'P244':'Basınçlı gazları yağ ve gres yağından uzak tutun.',
        'P250':'Taşlamaya, sürtünmeye, darbeye veya çarpışmaya maruz bırakmayın.',
        'P251':'Delmeyin veya yakmayın; kullanımdan sonra bile.',
        'P260':'Toz/duman/gaz/sis/buhar/sprey solumayın.',
        'P261':'Toz/duman/gaz/sis/buhar/sprey solumaktan mümkün olduğunca kaçının.',
        'P262':'Gözlerle, ciltle veya giysilerle temasına izin vermeyin.',
        'P263':'Hamilelik ve emzirme döneminde temastan kaçının.',
        'P264':'Kullanımdan sonra ellerinizi iyice yıkayın.',
        'P270':'Bu ürünü kullanırken yiyip içmeyin veya sigara içmeyin.',
        'P271':'Yalnızca açık alanda veya iyi havalandırılmış bir alanda kullanın.',
        'P272':'Kirlenmiş iş giysisinin işyeri dışına çıkarılmasına izin vermeyin.',
        'P273':'Çevreye salınımından kaçının.',
        'P280':'Koruyucu eldiven/koruyucu giysi/göz koruyucu/yüz koruyucu kullanın.',
        'P281':'Gerekli kişisel koruyucu ekipmanı kullanın.',
        'P282':'Soğutma eldiveni/yüz koruyucu/göz koruyucu kullanın.',
        'P283':'Alev almaz veya alev geciktirici giysi kullanın.',
        'P284':'Yeterli havalandırma sağlanamıyorsa solunum koruyucu kullanın.',
        'P285':'Yeterli havalandırma sağlanamıyorsa solunum koruyucu kullanın.',
        'P301+P310':'YUTULMASI HALİNDE: Hemen Zehir Danışma Merkezi\'ni (114) veya doktoru arayın.',
        'P301+P312':'YUTULMASI HALİNDE: Kendinizi iyi hissetmiyorsanız Zehir Danışma Merkezi\'ni (114) veya doktoru arayın.',
        'P301+P330+P331':'YUTULMASI HALİNDE: Ağzı çalkalayın. Kusturmayın.',
        'P302+P334':'CİLDE TEMAS DURUMUNDA: Soğuk suya sokun ya da ıslak pansuman yapın.',
        'P302+P350':'CİLDE TEMAS DURUMUNDA: Bol su ve sabunla dikkatlice yıkayın.',
        'P302+P352':'CİLDE TEMAS DURUMUNDA: Bol sabun ve su ile yıkayın.',
        'P303+P361+P353':'CİLDE (veya SAÇA) TEMAS DURUMUNDA: Kirlenmiş giysileri hemen çıkarın. Cilt suyla durulanır/duş alınır.',
        'P304+P340':'SOLUNMASI HALİNDE: Kişiyi temiz havaya çıkarın. Nefes almakta güçlük çekiyorsa solunum kolaşlaştırıcı pozisyona getirin.',
        'P304+P341':'SOLUNMASI HALİNDE: Solunumu güçleştiriyorsa, kişiyi temiz havaya çıkarın ve nefes almayı kolaylaştıracak pozisyona getirin.',
        'P305+P351+P338':'GÖZ İLE TEMAS HALİNDE: Birkaç dakika suyla dikkatlice durulayın. Varsa ve çıkarması kolaysa kontak lensleri çıkartın. Durulamaya devam edin.',
        'P306+P360':'GİYSİ İLE TEMAS HALİNDE: Giysileri çıkarmadan önce etkilenen alanı suyla iyice durulayın.',
        'P307+P311':'MARUZ KALINMASI HALİNDE: Zehir Danışma Merkezi\'ni (114) veya doktoru arayın.',
        'P308+P313':'MARUZ KALMA VEYA ENDİŞE DURUMUNDA: Tıbbi yardım/bakım alın.',
        'P310':'Hemen Zehir Danışma Merkezi\'ni (114) veya doktoru arayın.',
        'P311':'Zehir Danışma Merkezi\'ni (114) veya doktoru arayın.',
        'P312':'Kendinizi iyi hissetmiyorsanız Zehir Danışma Merkezi\'ni (114) veya doktoru arayın.',
        'P313':'Tıbbi yardım alın.',
        'P314':'Kendinizi iyi hissetmiyorsanız tıbbi yardım/bakım alın.',
        'P315':'Derhal tıbbi yardım/bakım alın.',
        'P320':'Derhal özel tedavi uygulanması zorunludur (bakınız bu etiket).',
        'P321':'Özel tedavi (bakınız bu etiket).',
        'P322':'Özel tedbirler (bakınız bu etiket).',
        'P330':'Ağzı çalkalayın.',
        'P331':'KUSTURMAYINIZ.',
        'P332+P313':'CİLT TAHRİŞİ OLUŞMASI HALİNDE: Tıbbi yardım alın.',
        'P333+P313':'CİLT TAHRİŞİ VEYA DÖKÜNTÜLERİ OLUŞMASI HALİNDE: Tıbbi yardım alın.',
        'P334':'Soğuk suya sokun ya da ıslak pansuman yapın.',
        'P335+P334':'Deriden gevşek partikülleri fırçalayın. Soğuk suya sokun ya da ıslak pansuman yapın.',
        'P336+P315':'Donmuş kısımları ılık suyla eritin. Donmuş alanı ovalamayın. Derhal tıbbi yardım alın.',
        'P337+P313':'GÖZ TAHRİŞİ DEVAM ETMESİ HALİNDE: Tıbbi yardım alın.',
        'P338':'Mümkün ise kontak lensleri çıkartın. Durulamaya devam edin.',
        'P340':'Kişiyi temiz havaya çıkarın ve nefes almayı kolaylaştıracak pozisyona getirin.',
        'P342+P311':'SOLUNUM SEMPTOMLARININ OLUŞMASI HALİNDE: Zehir Danışma Merkezi\'ni (114) veya doktoru arayın.',
        'P351':'Birkaç dakika suyla dikkatlice durulayın.',
        'P352':'Bol su ile yıkayın.',
        'P353':'Cilt suyla durulanır/duş alınır.',
        'P360':'Giysileri çıkarmadan önce etkilenen alanı suyla iyice durulayın.',
        'P361':'Kirlenmiş giysileri hemen çıkarın.',
        'P361+P364':'Kirlenmiş giysileri derhal çıkarın ve yeniden giymeden önce yıkayın.',
        'P362':'Kirlenmiş giysileri çıkarın.',
        'P362+P364':'Kirlenmiş giysileri çıkarın ve yeniden giymeden önce yıkayın.',
        'P363':'Yeniden giymeden önce kirlenmiş giysileri yıkayın.',
        'P364':'Yeniden kullanmadan önce yıkayın.',
        'P370+P376':'YANGIN HALINDE: Tehlike yoksa sızıntıyı durdurun.',
        'P370+P378':'YANGIN HALINDE: Kuru kimyasal, CO₂ veya alkole dayanıklı köpük kullanın.',
        'P370+P380':'YANGIN HALINDE: Bölgeden uzaklaşın.',
        'P371+P380+P375':'BÜYÜK YANGIN VE BÜYÜK MİKTARLAR HALİNDE: Bölgeden uzaklaşın. Uzaktan söndürün.',
        'P372':'Yangın halinde patlama riski.',
        'P373':'Yangın patlayıcıya ulaştığında YANGINLA MÜCADELE ETMEYİN.',
        'P374':'Yangın söndürmek için normal önlemler alın.',
        'P375':'Patlama riski nedeniyle uzaktan yangınla mücadele edin.',
        'P376':'Tehlike yoksa sızıntıyı durdurun.',
        'P377':'SIZINTI YAPAN GAZ YANGINI: Söndürmeye çalışmayın. Sızıntı güvenle durdurulamazsa.',
        'P378':'Söndürmek için ... kullanın.',
        'P380':'Bölgeden uzaklaşın.',
        'P381':'Güvenli ise tüm tutuşturma kaynaklarını ortadan kaldırın.',
        'P390':'Çevrenin kirlenmesini önlemek için döküleni/saçılanı emdir.',
        'P391':'Döküntüyü toplayın.',
        'P401':'... maddesine uygun şekilde saklayın.',
        'P402':'Kuru yerde saklayın.',
        'P402+P404':'Kuru yerde ve kapalı kapta saklayın.',
        'P403':'İyi havalandırılmış yerde saklayın.',
        'P403+P233':'İyi havalandırılmış yerde saklayın. Kabı sıkıca kapalı tutun.',
        'P403+P235':'İyi havalandırılmış serin yerde saklayın.',
        'P404':'Kapalı kapta saklayın.',
        'P405':'Kilitli yerde saklayın.',
        'P406':'Aşındırmaya dayanıklı/... iç yüzeyine sahip kapta saklayın.',
        'P407':'Yığınlar veya paletler arasında hava aralığı bırakın.',
        'P410':'Güneş ışığından koruyun.',
        'P410+P403':'Güneş ışığından koruyun. Serin, iyi havalandırılmış yerde saklayın.',
        'P410+P412':'50°C/122°F\'ı aşan sıcaklıklara maruz bırakmayın.',
        'P411':'... °C/... °F\'ı aşmayan sıcaklıkta saklayın.',
        'P412':'50°C/122°F\'ı aşan sıcaklıklara maruz bırakmayın.',
        'P413':'Dökme yığınlarını ... °C/... °F\'ı aşmayan sıcaklıkta saklayın.',
        'P420':'Diğer maddelerden uzakta saklayın.',
        'P422':'İçeriği ... altında saklayın.',
        'P501':'İçeriği/kabı yerel/bölgesel/ulusal/uluslararası düzenlemelere uygun olarak imha edin.',
        'P502':'Geri dönüşüm veya geri kazanım hakkında üretici veya tedarikçiden bilgi alın.',
    },
    'EN': {
        'P101':'If medical advice is needed, have product container or label at hand.',
        'P102':'Keep out of reach of children.',
        'P103':'Read label before use.',
        'P201':'Obtain special instructions before use.',
        'P202':'Do not handle until all safety precautions have been read and understood.',
        'P210':'Keep away from heat, hot surfaces, sparks, open flames and other ignition sources. No smoking.',
        'P211':'Do not spray on an open flame or other ignition source.',
        'P220':'Keep away from clothing and other combustible materials.',
        'P233':'Keep container tightly closed.',
        'P234':'Keep only in original container.',
        'P235':'Keep cool.',
        'P240':'Ground and bond container and receiving equipment.',
        'P241':'Use explosion-proof electrical/ventilating/lighting equipment.',
        'P242':'Use non-sparking tools.',
        'P243':'Take action to prevent static discharges.',
        'P250':'Do not subject to grinding/shock/friction.',
        'P260':'Do not breathe dust/fume/gas/mist/vapours/spray.',
        'P261':'Avoid breathing dust/fume/gas/mist/vapours/spray.',
        'P262':'Do not get in eyes, on skin, or on clothing.',
        'P264':'Wash hands thoroughly after handling.',
        'P270':'Do not eat, drink or smoke when using this product.',
        'P271':'Use only outdoors or in a well-ventilated area.',
        'P273':'Avoid release to the environment.',
        'P280':'Wear protective gloves/protective clothing/eye protection/face protection.',
        'P301+P310':'IF SWALLOWED: Immediately call a POISON CENTER or doctor.',
        'P301+P330+P331':'IF SWALLOWED: Rinse mouth. Do NOT induce vomiting.',
        'P302+P352':'IF ON SKIN: Wash with plenty of soap and water.',
        'P303+P361+P353':'IF ON SKIN (or hair): Take off immediately all contaminated clothing. Rinse skin with water/shower.',
        'P304+P340':'IF INHALED: Remove person to fresh air and keep comfortable for breathing.',
        'P305+P351+P338':'IF IN EYES: Rinse cautiously with water for several minutes. Remove contact lenses if present and easy to do. Continue rinsing.',
        'P308+P313':'IF exposed or concerned: Get medical advice/attention.',
        'P310':'Immediately call a POISON CENTER or doctor.',
        'P312':'Call a POISON CENTER or doctor if you feel unwell.',
        'P313':'Get medical advice/attention.',
        'P330':'Rinse mouth.',
        'P331':'Do NOT induce vomiting.',
        'P332+P313':'IF SKIN irritation occurs: Get medical advice/attention.',
        'P333+P313':'IF SKIN irritation or rash occurs: Get medical advice/attention.',
        'P337+P313':'IF eye irritation persists: Get medical advice/attention.',
        'P340':'Remove person to fresh air and keep comfortable for breathing.',
        'P351':'Rinse cautiously with water for several minutes.',
        'P352':'Wash with plenty of water.',
        'P353':'Rinse skin with water/shower.',
        'P361':'Take off immediately all contaminated clothing.',
        'P362':'Take off contaminated clothing.',
        'P370+P378':'IN CASE OF FIRE: Use dry chemical, CO₂ or alcohol-resistant foam for extinction.',
        'P391':'Collect spillage.',
        'P402':'Store in a dry place.',
        'P403':'Store in a well-ventilated place.',
        'P403+P233':'Store in a well-ventilated place. Keep container tightly closed.',
        'P403+P235':'Store in a cool, well-ventilated place.',
        'P404':'Store in a closed container.',
        'P405':'Store locked up.',
        'P410':'Protect from sunlight.',
        'P410+P403':'Protect from sunlight. Store in a cool, well-ventilated place.',
        'P410+P412':'Protect from sunlight. Do not expose to temperatures exceeding 50°C/122°F.',
        'P412':'Do not expose to temperatures exceeding 50°C/122°F.',
        'P501':'Dispose of contents/container in accordance with local/national regulations.',
    },
    'DE': {
        'P101':'Ist ärztlicher Rat erforderlich, Verpackung oder Kennzeichnungsetikett bereithalten.',
        'P102':'Darf nicht in die Hände von Kindern gelangen.',
        'P210':'Von Hitze, heißen Oberflächen, Funken, offenen Flammen sowie anderen Zündquellen fernhalten. Nicht rauchen.',
        'P233':'Behälter dicht verschlossen halten.',
        'P260':'Staub/Rauch/Gas/Nebel/Dampf/Aerosol nicht einatmen.',
        'P273':'Freisetzung in die Umwelt vermeiden.',
        'P280':'Schutzhandschuhe/Schutzkleidung/Augenschutz/Gesichtsschutz tragen.',
        'P301+P310':'BEI VERSCHLUCKEN: Sofort GIFTINFORMATIONSZENTRUM oder Arzt anrufen.',
        'P302+P352':'BEI BERÜHRUNG MIT DER HAUT: Mit viel Wasser waschen.',
        'P304+P340':'BEI EINATMEN: An die frische Luft bringen und in einer Position ruhigstellen, die das Atmen erleichtert.',
        'P305+P351+P338':'BEI KONTAKT MIT DEN AUGEN: Einige Minuten lang behutsam mit Wasser ausspülen. Vorhandene Kontaktlinsen nach Möglichkeit entfernen. Weiter ausspülen.',
        'P310':'Sofort GIFTINFORMATIONSZENTRUM oder Arzt anrufen.',
        'P331':'KEIN Erbrechen herbeiführen.',
        'P370+P378':'BEI BRAND: Trockenlöschmittel, CO₂ oder alkoholbeständigen Schaum verwenden.',
        'P391':'Verschüttete Mengen aufnehmen.',
        'P403+P235':'An einem gut belüfteten Ort aufbewahren. Kühl halten.',
        'P405':'Unter Verschluss aufbewahren.',
        'P501':'Inhalt/Behälter gemäß lokalen Vorschriften entsorgen.',
    },
}
P_STMTS['US_EN'] = P_STMTS['EN']


# ══════════════════════════════════════════════════════════════════════════════
# KKE (PPE) METİNLERİ
# ══════════════════════════════════════════════════════════════════════════════

PPE_TEXTS = {
    'TR': {
        'gloves_nitril':  'Nitril veya lateks eldiven (EN 374)',
        'gloves_chem':    'Kimyasala dayanıklı eldiven (nitril ≥0.5mm veya neopren, EN 374)',
        'gloves_heavy':   'Ağır tip kimyasal dirençli eldiven (butil/neopren)',
        'eyes_goggles':   'Kimyasal güvenlik gözlüğü (EN 166)',
        'eyes_shield':    'Yüz siperi veya kimyasal gözlük (EN 166)',
        'resp_half':      'Organik buhar filtreli (A tipi) yarım yüz maskesi',
        'resp_full':      'ABEK filtreli tam yüz maskesi veya SCBA',
        'resp_p2':        'P2/P3 partikül filtreli yarım yüz maskesi',
        'body_anti':      'Antistatik ve kimyasala dayanıklı koruyucu giysi',
        'body_acid':      'Kimyasala dayanıklı koruyucu giysi ve çizme',
        'body_standard':  'Uygun iş giysisi',
    },
    'EN': {
        'gloves_nitril':  'Nitrile or latex gloves (EN 374)',
        'gloves_chem':    'Chemical resistant gloves (nitrile ≥0.5mm or neoprene, EN 374)',
        'gloves_heavy':   'Heavy-duty chemical resistant gloves (butyl/neoprene)',
        'eyes_goggles':   'Chemical safety goggles (EN 166)',
        'eyes_shield':    'Face shield or chemical splash goggles (EN 166)',
        'resp_half':      'Half-face respirator with organic vapour filter (type A)',
        'resp_full':      'Full-face respirator with ABEK filter or SCBA',
        'resp_p2':        'Half-face respirator with P2/P3 particulate filter',
        'body_anti':      'Antistatic and chemical resistant protective clothing',
        'body_acid':      'Chemical resistant protective clothing and boots',
        'body_standard':  'Appropriate work clothing',
    },
    'DE': {
        'gloves_nitril':  'Nitril- oder Latexhandschuhe (EN 374)',
        'gloves_chem':    'Chemikalienbeständige Handschuhe (Nitril ≥0,5mm oder Neopren, EN 374)',
        'eyes_goggles':   'Chemikalienschutzbrille (EN 166)',
        'eyes_shield':    'Gesichtsschutz oder Chemikalienschutzbrille (EN 166)',
        'resp_half':      'Halbmaske mit Organikdampffilter (Typ A)',
        'resp_full':      'Vollmaske mit ABEK-Filter oder Atemschutzgerät (SCBA)',
        'body_anti':      'Antistatische und chemikalienbeständige Schutzkleidung',
        'body_standard':  'Geeignete Arbeitskleidung',
    },
}
PPE_TEXTS['US_EN'] = PPE_TEXTS['EN']


# ══════════════════════════════════════════════════════════════════════════════
# DEPOLAMA / TAŞIMA / BERTARAF CÜMLELERİ
# ══════════════════════════════════════════════════════════════════════════════

SDS_SENTENCES = {
    'TR': {
        # Depolama
        'storage_flam':   'Orijinal ambalajında, serin ve iyi havalandırılmış yerde, tutuşturma kaynaklarından uzakta saklayın.',
        'storage_corr':   'Aşındırmaya dayanıklı kapta, metallerden uzakta saklayın.',
        'storage_ox':     'Yanıcı ve organik maddelerden uzakta, kilitli yerde saklayın.',
        'storage_tox':    'Güvenli kilitli yerde, gıda ve yemden ayrı olarak saklayın.',
        'storage_default':'Orijinal ambalajında, serin ve kuru yerde saklayın. Çocukların erişemeyeceği yerde tutun.',
        # İlk yardım
        'fa_inhal':  'Kişiyi temiz havaya çıkarın. Nefes almakta güçlük çekiyorsa oksijen uygulayın. Tıbbi yardım alın.',
        'fa_skin':   'Kirlenmiş giysileri çıkarın. Cildi bol su ve sabunla en az 15 dakika yıkayın. Tahriş devam ederse tıbbi yardım alın.',
        'fa_eye':    'Gözleri bol su ile en az 15 dakika yıkayın, göz kapaklarını açık tutun. Kontakt lens varsa çıkarın. Tıbbi yardım alın.',
        'fa_oral':   'Ağzı su ile çalkalayın. Kusturmayın. Hemen tıbbi yardım alın / Zehir Merkezini arayın: 114.',
        # Yangın
        'fire_ext_flam': 'Kuru kimyasal, CO₂ veya alkole dayanıklı köpük kullanın.',
        'fire_ext_water': 'Suyu yalnızca sprey olarak kullanın. Doğrudan su fışkırtmayın.',
        'fire_ppe':       'Yangın ekibi tam koruma elbisesi ve bağımsız solunum cihazı (SCBA) kullanmalıdır.',
        'fire_hazard':    'Yanma sırasında zehirli/tahriş edici dumanlar açığa çıkabilir.',
        # Döküntü
        'spill_ppe':      'Uygun KKE kullanın. Tutuşturma kaynaklarını ortadan kaldırın. Yeterli havalandırma sağlayın.',
        'spill_absorb':   'Kuru absorban malzeme (vermikülit, kum veya tahta talaşı) ile toplayın. Uygun etiketli atık kabına koyun.',
        'spill_env':      'Su kaynaklarına, kanalizasyona veya toprağa karışmasını önleyin.',
        # Bertaraf
        'disposal_default': 'Tehlikeli Atıkların Kontrolü Yönetmeliği\'ne uygun olarak lisanslı atık işleyicisine verin.',
        # Acil
        'emergency_default': 'Ulusal Zehir Danışma Merkezi (UZEM): 114',
    },
    'EN': {
        # Storage
        'storage_flam':   'Store in original container in a cool, well-ventilated place, away from ignition sources.',
        'storage_corr':   'Store in corrosion-resistant container, away from metals.',
        'storage_ox':     'Store away from combustible and organic materials in a locked place.',
        'storage_tox':    'Store in a secure locked place, separate from food and feed.',
        'storage_default':'Store in original container in a cool, dry place. Keep out of reach of children.',
        # First aid
        'fa_inhal':  'Remove person to fresh air. If breathing is difficult, administer oxygen. Seek medical attention.',
        'fa_skin':   'Remove contaminated clothing. Wash skin with soap and plenty of water for at least 15 minutes. If irritation persists, seek medical attention.',
        'fa_eye':    'Rinse eyes with plenty of water for at least 15 minutes, keeping eyelids open. Remove contact lenses if present. Seek medical attention.',
        'fa_oral':   'Rinse mouth with water. Do not induce vomiting. Seek immediate medical attention / call Poison Center: national number.',
        # Fire
        'fire_ext_flam': 'Use dry chemical, CO₂ or alcohol-resistant foam.',
        'fire_ext_water': 'Use water spray only. Do not use a direct water stream.',
        'fire_ppe':       'Firefighters should wear full protective clothing and self-contained breathing apparatus (SCBA).',
        'fire_hazard':    'Combustion may produce toxic/irritating fumes.',
        # Spill
        'spill_ppe':      'Use appropriate PPE. Eliminate ignition sources. Ensure adequate ventilation.',
        'spill_absorb':   'Collect with dry absorbent material (vermiculite, sand or sawdust). Place in labelled waste container.',
        'spill_env':      'Prevent entry into water courses, drains or soil.',
        # Disposal
        'disposal_default': 'Dispose of via a licensed hazardous waste handler in accordance with local regulations.',
        # Emergency
        'emergency_default': 'National Poison Center — local emergency number.',
    },
    'DE': {
        'storage_flam':   'Im Originalbehälter an einem kühlen, gut belüfteten Ort, fernhalten von Zündquellen aufbewahren.',
        'storage_default':'Im Originalbehälter an einem kühlen, trockenen Ort aufbewahren. Von Kindern fernhalten.',
        'fa_inhal':  'Person an die frische Luft bringen. Bei Atemschwierigkeiten Sauerstoff geben. Arzt aufsuchen.',
        'fa_skin':   'Kontaminierte Kleidung entfernen. Haut mindestens 15 Minuten mit Seife und viel Wasser waschen.',
        'fa_eye':    'Augen bei geöffneten Lidern mindestens 15 Minuten mit Wasser spülen. Kontaktlinsen entfernen. Arzt aufsuchen.',
        'fa_oral':   'Mund mit Wasser spülen. Kein Erbrechen herbeiführen. Sofort Arzt aufsuchen.',
        'fire_ext_flam': 'Trockenlöschmittel, CO₂ oder alkoholbeständigen Schaum verwenden.',
        'fire_ppe':  'Feuerwehr muss vollständige Schutzausrüstung und umgebungsluftunabhängiges Atemschutzgerät tragen.',
        'spill_absorb': 'Mit trockenem Absorptionsmittel (Vermiculit, Sand) aufnehmen. In gekennzeichneten Abfallbehälter geben.',
        'disposal_default': 'Gemäß lokalen Vorschriften über einen zugelassenen Entsorgungsbetrieb entsorgen.',
        'emergency_default': 'Giftnotruf — nationale Rufnummer.',
    },
}
SDS_SENTENCES['US_EN'] = SDS_SENTENCES['EN']


# ══════════════════════════════════════════════════════════════════════════════
# YARDIMCI FONKSİYONLAR
# ══════════════════════════════════════════════════════════════════════════════

def _fallback(lang: str) -> str:
    """EN fallback dili"""
    return 'EN' if lang not in ('TR',) else 'TR'


@lru_cache(maxsize=2000)
def get_h(lang: str, code: str) -> str:
    """H kodu metnini dönür. Yoksa EN, yoksa kodu döner."""
    lang = lang.upper()
    result = H_STMTS.get(lang, {}).get(code)
    if not result:
        result = H_STMTS.get('EN', {}).get(code, code)
    return result or code


def get_euh(lang: str, code: str, substance: str = '') -> str:
    """EUH kodu metnini döner. EUH208 için substance adı gerekli."""
    lang = lang.upper()
    result = EUH_STMTS.get(lang, {}).get(code)
    if not result:
        result = EUH_STMTS.get('EN', {}).get(code, code)
    result = result or code
    # EUH208 — ... yerine madde adı koy
    if code == 'EUH208' and '{substance}' in result:
        if substance:
            result = result.replace('{substance}', substance)
        else:
            result = result.replace('{substance} ', '').replace('{substance}', '...')
    return result


@lru_cache(maxsize=1000)
def get_p(lang: str, code: str) -> str:
    """P kodu metnini döner."""
    lang = lang.upper()
    result = P_STMTS.get(lang, {}).get(code)
    if not result:
        result = P_STMTS.get('EN', {}).get(code, code)
    return result or code


def get_ppe(lang: str, key: str) -> str:
    """KKE metnini döner."""
    lang = lang.upper()
    result = PPE_TEXTS.get(lang, {}).get(key)
    if not result:
        result = PPE_TEXTS.get('EN', {}).get(key, key)
    return result or key


def get_sentence(lang: str, key: str) -> str:
    """SDS cümlesini döner."""
    lang = lang.upper()
    result = SDS_SENTENCES.get(lang, {}).get(key)
    if not result:
        result = SDS_SENTENCES.get('EN', {}).get(key, '')
    return result or ''


if __name__ == '__main__':
    # Test
    for lang in ['TR', 'EN', 'DE']:
        print(f"\n{lang}:")
        print(f"  H226: {get_h(lang,'H226')}")
        print(f"  EUH066: {get_euh(lang,'EUH066')}")
        print(f"  P302+P352: {get_p(lang,'P302+P352')}")
        print(f"  storage_flam: {get_sentence(lang,'storage_flam')[:60]}")


# ══════════════════════════════════════════════════════════════════════════════
# CLP SINIF KISA İSİMLERİ — TÜRKÇE ÇEVİRİ
# Kaynak: KKDİK Ek-1 / CLP Regulation Tablo 3.1
# ══════════════════════════════════════════════════════════════════════════════

CLP_CLASS_TR = {
    # Fiziksel tehlikeler
    'Expl. Div. 1.1': 'Patlayıcı Bl. 1.1',
    'Expl. Div. 1.2': 'Patlayıcı Bl. 1.2',
    'Expl. Div. 1.3': 'Patlayıcı Bl. 1.3',
    'Expl. Div. 1.4': 'Patlayıcı Bl. 1.4',
    'Unstable Expl.': 'Kararsız Patlayıcı',
    'Flam. Gas 1':    'Alev. Gaz 1',
    'Flam. Gas 2':    'Alev. Gaz 2',
    'Flam. Gas 1A':   'Alev. Gaz 1A',
    'Flam. Gas 1B':   'Alev. Gaz 1B',
    'Aerosol 1':      'Aerosol 1',
    'Aerosol 2':      'Aerosol 2',
    'Aerosol 3':      'Aerosol 3',
    'Press. Gas':     'Basınçlı Gaz',
    'Flam. Liq. 1':   'Alev. Sıv. 1',
    'Flam. Liq. 2':   'Alev. Sıv. 2',
    'Flam. Liq. 3':   'Alev. Sıv. 3',
    'Flam. Sol. 1':   'Alev. Kat. 1',
    'Flam. Sol. 2':   'Alev. Kat. 2',
    'Self-react. A':  'Kendi Ken. Tep. A',
    'Self-react. B':  'Kendi Ken. Tep. B',
    'Self-react. C':  'Kendi Ken. Tep. C',
    'Self-react. D':  'Kendi Ken. Tep. D',
    'Self-react. E':  'Kendi Ken. Tep. E',
    'Self-react. F':  'Kendi Ken. Tep. F',
    'Pyr. Liq. 1':    'Pirofor Sıv. 1',
    'Pyr. Sol. 1':    'Pirofor Kat. 1',
    'Self-heat. 1':   'Kend. Isın. 1',
    'Self-heat. 2':   'Kend. Isın. 2',
    'Water-react. 1': 'Su Reak. 1',
    'Water-react. 2': 'Su Reak. 2',
    'Water-react. 3': 'Su Reak. 3',
    'Ox. Gas 1':      'Oks. Gaz 1',
    'Ox. Liq. 1':     'Oks. Sıv. 1',
    'Ox. Liq. 2':     'Oks. Sıv. 2',
    'Ox. Liq. 3':     'Oks. Sıv. 3',
    'Ox. Sol. 1':     'Oks. Kat. 1',
    'Ox. Sol. 2':     'Oks. Kat. 2',
    'Ox. Sol. 3':     'Oks. Kat. 3',
    'Org. Perox. A':  'Org. Peroks. A',
    'Org. Perox. B':  'Org. Peroks. B',
    'Org. Perox. C':  'Org. Peroks. C',
    'Org. Perox. D':  'Org. Peroks. D',
    'Org. Perox. E':  'Org. Peroks. E',
    'Org. Perox. F':  'Org. Peroks. F',
    'Met. Corr. 1':   'Metal Aş. 1',
    # Sağlık tehlikeleri
    'Acute Tox. 1':   'Akut Toks. 1',
    'Acute Tox. 2':   'Akut Toks. 2',
    'Acute Tox. 3':   'Akut Toks. 3',
    'Acute Tox. 4':   'Akut Toks. 4',
    'Skin Corr. 1':   'Cilt Aş. 1',
    'Skin Corr. 1A':  'Cilt Aş. 1A',
    'Skin Corr. 1B':  'Cilt Aş. 1B',
    'Skin Corr. 1C':  'Cilt Aş. 1C',
    'Skin Irrit. 2':  'Cilt Tahriş. 2',
    'Skin Irrit. 3':  'Cilt Tahriş. 3',
    'Eye Dam. 1':     'Göz Hasar. 1',
    'Eye Irrit. 2':   'Göz Tahriş. 2',
    'Resp. Sens. 1':  'Sol. Duyar. 1',
    'Resp. Sens. 1A': 'Sol. Duyar. 1A',
    'Resp. Sens. 1B': 'Sol. Duyar. 1B',
    'Skin Sens. 1':   'Cilt Duyar. 1',
    'Skin Sens. 1A':  'Cilt Duyar. 1A',
    'Skin Sens. 1B':  'Cilt Duyar. 1B',
    'Muta. 1A':       'Muta. 1A',
    'Muta. 1B':       'Muta. 1B',
    'Muta. 2':        'Muta. 2',
    'Carc. 1A':       'Kans. 1A',
    'Carc. 1B':       'Kans. 1B',
    'Carc. 2':        'Kans. 2',
    'Repr. 1A':       'Üreme Toks. 1A',
    'Repr. 1B':       'Üreme Toks. 1B',
    'Repr. 2':        'Üreme Toks. 2',
    'Lact.':          'Emzirme Toks.',
    'STOT SE 1':      'BHOT Tek Mar. 1',
    'STOT SE 2':      'BHOT Tek Mar. 2',
    'STOT SE 3':      'BHOT Tek Mar. 3',
    'STOT RE 1':      'BHOT Tkr. Mar. 1',
    'STOT RE 2':      'BHOT Tkr. Mar. 2',
    'Asp. Tox. 1':    'Asp. Toks. 1',
    'Asp. Tox. 2':    'Asp. Toks. 2',
    # Çevresel tehlikeler
    'Aquatic Acute 1':    'Suk. Akut 1',
    'Aquatic Acute 2':    'Suk. Akut 2',
    'Aquatic Acute 3':    'Suk. Akut 3',
    'Aquatic Chronic 1':  'Suk. Kron. 1',
    'Aquatic Chronic 2':  'Suk. Kron. 2',
    'Aquatic Chronic 3':  'Suk. Kron. 3',
    'Aquatic Chronic 4':  'Suk. Kron. 4',
    'Ozone 1':            'Ozon Tah. 1',
}


def translate_hclass(h_class: str, lang: str = 'TR') -> str:
    """
    CLP hazard class kısa ismini dile çevir.
    TR → Türkçe kısaltma
    Diğer → orijinal bırak (uluslararası standart)
    """
    if lang != 'TR':
        return h_class
    return CLP_CLASS_TR.get(h_class.strip(), h_class)


def translate_hclass_list(classes: str, lang: str = 'TR') -> str:
    """
    Noktalı virgülle ayrılmış sınıf listesini çevir.
    Örn: "Flam. Liq. 3; Skin Irrit. 2" → "Alev. Sıv. 3; Cilt Tahriş. 2"
    """
    if lang != 'TR' or not classes:
        return classes
    parts = [c.strip() for c in classes.split(';')]
    return '; '.join(translate_hclass(p, lang) for p in parts)
