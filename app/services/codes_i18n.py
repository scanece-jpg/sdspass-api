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
        'H360D':'Doğmamış çocuğa zarar verebilir.',
        'H360F':'Doğurganlığa zarar verebilir.',
        'H360FD':'Doğurganlığa veya doğmamış çocuğa zarar verebilir.',
        'H361':'Doğurganlığa veya doğmamış çocuğa zarar verebileceğinden şüphelenilmektedir.',
        'H361D':'Doğmamış çocuğa zarar verebileceğinden şüphelenilmektedir.',
        'H361F':'Doğurganlığa zarar verebileceğinden şüphelenilmektedir.',
        'H361FD':'Doğurganlığa veya doğmamış çocuğa zarar verebileceğinden şüphelenilmektedir.',
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
        'H230':'Can react explosively even without air.',
        'H231':'Can react explosively even without air at elevated pressure and/or temperature.',
        'H232':'May ignite spontaneously if exposed to air.',
        'H240':'Heating may cause an explosion.',
        'H241':'Heating may cause a fire or explosion.',
        'H242':'Heating may cause a fire.',
        'H250':'Catches fire spontaneously if exposed to air.',
        'H251':'Self-heating; may catch fire.',
        'H252':'Self-heating in large quantities; may catch fire.',
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
        'H305':'May be harmful if swallowed and enters airways.',
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
        'H360D':'May damage the unborn child.',
        'H360F':'May damage fertility.',
        'H360FD':'May damage fertility or the unborn child.',
        'H361':'Suspected of damaging fertility or the unborn child.',
        'H361D':'Suspected of damaging the unborn child.',
        'H361F':'Suspected of damaging fertility.',
        'H361FD':'Suspected of damaging fertility or the unborn child.',
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
        'H200':'Instabiler Sprengstoff.',
        'H201':'Sprengstoff; Gefahr der Massenexplosion.',
        'H202':'Sprengstoff; große Gefahr durch Splitter, Spreng- und Wurfstücke.',
        'H203':'Sprengstoff; Gefahr durch Feuer, Explosion oder Sprengstücke.',
        'H204':'Gefahr durch Feuer oder Sprengstücke.',
        'H220':'Extrem entzündbares Gas.',
        'H221':'Entzündbares Gas.',
        'H222':'Extrem entzündbares Aerosol.',
        'H223':'Entzündbares Aerosol.',
        'H224':'Extrem entzündbarer flüssiger Stoff und Dampf.',
        'H225':'Leichtentzündbarer flüssiger Stoff und Dampf.',
        'H226':'Entzündbarer flüssiger Stoff und Dampf.',
        'H228':'Entzündbarer Feststoff.',
        'H229':'Druckbehälter: Kann bei Erwärmung bersten.',
        'H230':'Kann auch ohne Luft explosionsartig reagieren.',
        'H231':'Kann auch ohne Luft bei erhöhtem Druck und/oder erhöhter Temperatur explosionsartig reagieren.',
        'H232':'Kann sich bei Kontakt mit Luft spontan entzünden.',
        'H240':'Explosionsgefährlich; Gefahr der Massenexplosion bei Erwärmung.',
        'H241':'Entzündungs- oder Explosionsgefahr bei Erwärmung.',
        'H242':'Entzündungsgefahr bei Erwärmung.',
        'H250':'Entzündet sich in Berührung mit Luft von selbst.',
        'H251':'Selbsterhitzungsfähig; kann in Brand geraten.',
        'H252':'Selbsterhitzungsfähig in großen Mengen; kann in Brand geraten.',
        'H260':'In Berührung mit Wasser entstehen entzündbare Gase, die sich spontan entzünden können.',
        'H261':'In Berührung mit Wasser entstehen entzündbare Gase.',
        'H270':'Kann Brand verursachen oder verstärken; Oxidationsmittel.',
        'H271':'Kann Brand oder Explosion verursachen; starkes Oxidationsmittel.',
        'H272':'Kann Brand verstärken; Oxidationsmittel.',
        'H280':'Enthält Gas unter Druck; kann bei Erwärmung explodieren.',
        'H281':'Enthält tiefgekühltes Gas; kann Kälteverbrennungen oder -verletzungen verursachen.',
        'H290':'Kann gegenüber Metallen korrosiv sein.',
        'H300':'Lebensgefährlich bei Verschlucken.',
        'H301':'Giftig bei Verschlucken.',
        'H302':'Gesundheitsschädlich bei Verschlucken.',
        'H303':'Kann bei Verschlucken schädlich sein.',
        'H304':'Kann bei Verschlucken und Eindringen in die Atemwege tödlich sein.',
        'H305':'Kann bei Verschlucken und Eindringen in die Atemwege schädlich sein.',
        'H310':'Lebensgefährlich bei Hautkontakt.',
        'H311':'Giftig bei Hautkontakt.',
        'H312':'Gesundheitsschädlich bei Hautkontakt.',
        'H313':'Kann bei Hautkontakt schädlich sein.',
        'H314':'Verursacht schwere Verätzungen der Haut und schwere Augenschäden.',
        'H315':'Verursacht Hautreizungen.',
        'H316':'Verursacht leichte Hautreizungen.',
        'H317':'Kann allergische Hautreaktionen verursachen.',
        'H318':'Verursacht schwere Augenschäden.',
        'H319':'Verursacht schwere Augenreizung.',
        'H320':'Verursacht Augenreizung.',
        'H330':'Lebensgefährlich bei Einatmen.',
        'H331':'Giftig bei Einatmen.',
        'H332':'Gesundheitsschädlich bei Einatmen.',
        'H333':'Kann bei Einatmen schädlich sein.',
        'H334':'Kann bei Einatmen Allergie, asthmaartige Symptome oder Atembeschwerden verursachen.',
        'H335':'Kann die Atemwege reizen.',
        'H336':'Kann Schläfrigkeit und Benommenheit verursachen.',
        'H340':'Kann genetische Defekte verursachen.',
        'H341':'Kann vermutlich genetische Defekte verursachen.',
        'H350':'Kann Krebs erzeugen.',
        'H351':'Kann vermutlich Krebs erzeugen.',
        'H360':'Kann die Fruchtbarkeit beeinträchtigen oder das Kind im Mutterleib schädigen.',
        'H360D':'Kann das Kind im Mutterleib schädigen.',
        'H360F':'Kann die Fruchtbarkeit beeinträchtigen.',
        'H360FD':'Kann die Fruchtbarkeit beeinträchtigen oder das Kind im Mutterleib schädigen.',
        'H361':'Kann vermutlich die Fruchtbarkeit beeinträchtigen oder das Kind im Mutterleib schädigen.',
        'H361D':'Kann vermutlich das Kind im Mutterleib schädigen.',
        'H361F':'Kann vermutlich die Fruchtbarkeit beeinträchtigen.',
        'H361FD':'Kann vermutlich die Fruchtbarkeit beeinträchtigen oder das Kind im Mutterleib schädigen.',
        'H362':'Kann Säuglinge über die Muttermilch schädigen.',
        'H370':'Schädigt die Organe.',
        'H371':'Kann die Organe schädigen.',
        'H372':'Schädigt die Organe bei längerer oder wiederholter Exposition.',
        'H373':'Kann die Organe schädigen bei längerer oder wiederholter Exposition.',
        'H400':'Sehr giftig für Wasserorganismen.',
        'H401':'Giftig für Wasserorganismen.',
        'H402':'Schädlich für Wasserorganismen.',
        'H410':'Sehr giftig für Wasserorganismen mit langfristiger Wirkung.',
        'H411':'Giftig für Wasserorganismen mit langfristiger Wirkung.',
        'H412':'Schädlich für Wasserorganismen mit langfristiger Wirkung.',
        'H413':'Kann für Wasserorganismen schädlich sein mit langfristiger Wirkung.',
        'H420':'Schädigt die öffentliche Gesundheit und die Umwelt durch Abbau von Ozon in der oberen Atmosphäre.',
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
        'EUH211':'Dikkat! Kullanımda akciğerlere ulaşabilecek tehlikeli damlacıklar oluşabilir. Sprey veya sis solumayın.',
        'EUH212':'Dikkat! Kullanımda solunum yoluyla maruz kalınabilecek tehlikeli ince partiküller (nano) oluşabilir. Solumayın.',
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
        'EUH211':'Warning! Hazardous respirable droplets may be formed when sprayed. Do not breathe spray or mist.',
        'EUH212':'Warning! Hazardous respirable dust may be formed when used. Do not breathe dust.',
        'EUH401':'To avoid risks to human health and the environment, comply with the instructions for use.',
    },
    'DE': {
        'EUH001':'Im trockenen Zustand explosiv.',
        'EUH006':'Explosiv mit und ohne Kontakt mit Luft.',
        'EUH014':'Reagiert heftig mit Wasser.',
        'EUH018':'Kann bei Verwendung explosionsfähige/entzündbare Dampf/Luft-Gemische bilden.',
        'EUH019':'Kann explosionsfähige Peroxide bilden.',
        'EUH029':'Entwickelt bei Berührung mit Wasser giftige Gase.',
        'EUH031':'Entwickelt bei Berührung mit Säure giftige Gase.',
        'EUH032':'Entwickelt bei Berührung mit Säure sehr giftige Gase.',
        'EUH044':'Explosionsgefahr bei Erhitzen unter Einschluss.',
        'EUH059':'Die Ozonschicht schädigend.',
        'EUH066':'Wiederholter Kontakt kann zu spröder oder rissiger Haut führen.',
        'EUH070':'Giftig bei Augenkontakt.',
        'EUH071':'Ätzend für die Atemwege.',
        'EUH201':'Enthält Blei. Nicht für Kinder zugängliche Oberflächen verwenden.',
        'EUH201A':'Achtung! Enthält Blei.',
        'EUH202':'Cyanacrylat. Gefahr. Klebt innerhalb von Sekunden Haut und Augenlider zusammen.',
        'EUH203':'Enthält Chrom(VI). Kann allergische Reaktionen hervorrufen.',
        'EUH204':'Enthält Isocyanate. Kann allergische Reaktionen hervorrufen.',
        'EUH205':'Enthält Epoxid-Bestandteile. Kann allergische Reaktionen hervorrufen.',
        'EUH206':'Achtung! Nicht zusammen mit anderen Produkten verwenden. Kann gefährliche Gase (Chlor) freisetzen.',
        'EUH207':'Achtung! Enthält Cadmium. Bei Verwendung entstehen gefährliche Dämpfe.',
        'EUH208':'Enthält {substance}. Kann allergische Reaktionen hervorrufen.',
        'EUH209':'Kann bei Verwendung leicht entzündlich werden.',
        'EUH209A':'Kann bei Verwendung entzündlich werden.',
        'EUH210':'Sicherheitsdatenblatt auf Anfrage erhältlich.',
        'EUH211':'Achtung! Beim Sprühen können gefährliche lungengängige Tröpfchen entstehen. Spray oder Nebel nicht einatmen.',
        'EUH212':'Achtung! Beim Gebrauch können gefährliche lungengängige Stäube entstehen. Staub nicht einatmen.',
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
        'P304+P340':'SOLUNMASI HALİNDE: Kişiyi temiz havaya çıkarın. Nefes almakta güçlük çekiyorsa solunum kolaylaştırıcı pozisyona getirin.',
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
        'P221':'Take precautionary measures against mixing with combustibles.',
        'P222':'Do not allow contact with air.',
        'P223':'Do not allow contact with water.',
        'P230':'Keep moistened with [...].',
        'P231':'Handle under inert gas.',
        'P231+P232':'Handle under inert gas. Protect from moisture.',
        'P232':'Protect from moisture.',
        'P233':'Keep container tightly closed.',
        'P234':'Keep only in original container.',
        'P235':'Keep cool.',
        'P235+P410':'Keep cool. Protect from sunlight.',
        'P240':'Ground and bond container and receiving equipment.',
        'P241':'Use explosion-proof electrical/ventilating/lighting equipment.',
        'P242':'Use non-sparking tools.',
        'P243':'Take action to prevent static discharges.',
        'P244':'Keep valves and fittings free from oil and grease.',
        'P250':'Do not subject to grinding/shock/friction.',
        'P251':'Do not pierce or burn, even after use.',
        'P260':'Do not breathe dust/fume/gas/mist/vapours/spray.',
        'P261':'Avoid breathing dust/fume/gas/mist/vapours/spray.',
        'P262':'Do not get in eyes, on skin, or on clothing.',
        'P263':'Avoid contact during pregnancy and while nursing.',
        'P264':'Wash hands thoroughly after handling.',
        'P270':'Do not eat, drink or smoke when using this product.',
        'P271':'Use only outdoors or in a well-ventilated area.',
        'P272':'Contaminated work clothing should not be allowed out of the workplace.',
        'P273':'Avoid release to the environment.',
        'P280':'Wear protective gloves/protective clothing/eye protection/face protection.',
        'P281':'Use required personal protective equipment.',
        'P282':'Wear cold insulating gloves/face shield/eye protection.',
        'P283':'Wear fire resistant/retardant clothing.',
        'P284':'In case of inadequate ventilation wear respiratory protection.',
        'P285':'In case of inadequate ventilation wear respiratory protection.',
        'P301+P310':'IF SWALLOWED: Immediately call a POISON CENTER or doctor.',
        'P301+P312':'IF SWALLOWED: Call a POISON CENTER or doctor if you feel unwell.',
        'P301+P330+P331':'IF SWALLOWED: Rinse mouth. Do NOT induce vomiting.',
        'P302+P334':'IF ON SKIN: Immerse in cool water or wrap in wet bandages.',
        'P302+P350':'IF ON SKIN: Wash gently with plenty of soap and water.',
        'P302+P352':'IF ON SKIN: Wash with plenty of soap and water.',
        'P303+P361+P353':'IF ON SKIN (or hair): Take off immediately all contaminated clothing. Rinse skin with water/shower.',
        'P304+P340':'IF INHALED: Remove person to fresh air and keep comfortable for breathing.',
        'P304+P341':'IF INHALED: If breathing is difficult, remove person to fresh air and keep comfortable for breathing.',
        'P305+P351+P338':'IF IN EYES: Rinse cautiously with water for several minutes. Remove contact lenses if present and easy to do. Continue rinsing.',
        'P306+P360':'IF ON CLOTHING: Rinse immediately contaminated clothing and skin with plenty of water before removing clothes.',
        'P307+P311':'IF exposed: Call a POISON CENTER or doctor.',
        'P308+P313':'IF exposed or concerned: Get medical advice/attention.',
        'P310':'Immediately call a POISON CENTER or doctor.',
        'P311':'Call a POISON CENTER or doctor.',
        'P312':'Call a POISON CENTER or doctor if you feel unwell.',
        'P313':'Get medical advice/attention.',
        'P314':'Get medical advice/attention if you feel unwell.',
        'P315':'Get immediate medical advice/attention.',
        'P320':'Specific treatment is urgently required (see ... on this label).',
        'P321':'Specific treatment (see ... on this label).',
        'P322':'Specific measures (see ... on this label).',
        'P330':'Rinse mouth.',
        'P331':'Do NOT induce vomiting.',
        'P332+P313':'IF SKIN irritation occurs: Get medical advice/attention.',
        'P333+P313':'IF SKIN irritation or rash occurs: Get medical advice/attention.',
        'P334':'Immerse in cool water or wrap in wet bandages.',
        'P335+P334':'Brush off loose particles from skin. Immerse in cool water or wrap in wet bandages.',
        'P336+P315':'Thaw frosted parts with lukewarm water. Do not rub affected areas. Get immediate medical advice/attention.',
        'P337+P313':'IF eye irritation persists: Get medical advice/attention.',
        'P338':'Remove contact lenses, if present and easy to do. Continue rinsing.',
        'P340':'Remove person to fresh air and keep comfortable for breathing.',
        'P342+P311':'IF experiencing respiratory symptoms: Call a POISON CENTER or doctor.',
        'P351':'Rinse cautiously with water for several minutes.',
        'P352':'Wash with plenty of water.',
        'P353':'Rinse skin with water/shower.',
        'P360':'Rinse immediately contaminated clothing and skin with plenty of water before removing clothes.',
        'P361':'Take off immediately all contaminated clothing.',
        'P361+P364':'Take off immediately all contaminated clothing and wash it before reuse.',
        'P362':'Take off contaminated clothing.',
        'P362+P364':'Take off contaminated clothing and wash it before reuse.',
        'P363':'Wash contaminated clothing before reuse.',
        'P364':'And wash it before reuse.',
        'P370+P376':'IN CASE OF FIRE: Stop leak if safe to do so.',
        'P370+P378':'IN CASE OF FIRE: Use dry chemical, CO₂ or alcohol-resistant foam for extinction.',
        'P370+P380':'IN CASE OF FIRE: Evacuate area.',
        'P371+P380+P375':'IN CASE OF MAJOR FIRE AND LARGE QUANTITIES: Evacuate area. Fight fire remotely due to the risk of explosion.',
        'P372':'Explosion risk.',
        'P373':'Do NOT fight fire when fire reaches explosives.',
        'P374':'Fight fire with normal precautions from a reasonable distance.',
        'P375':'Fight fire remotely due to the risk of explosion.',
        'P376':'Stop leak if safe to do so.',
        'P377':'Leaking gas fire: Do not extinguish, unless leak can be stopped safely.',
        'P378':'Use [...] for extinction.',
        'P380':'Evacuate area.',
        'P381':'In case of leakage, eliminate all ignition sources.',
        'P390':'Absorb spillage to prevent material damage.',
        'P391':'Collect spillage.',
        'P401':'Store in accordance with [...].',
        'P402':'Store in a dry place.',
        'P402+P404':'Store in a dry place. Store in a closed container.',
        'P403':'Store in a well-ventilated place.',
        'P403+P233':'Store in a well-ventilated place. Keep container tightly closed.',
        'P403+P235':'Store in a cool, well-ventilated place.',
        'P404':'Store in a closed container.',
        'P405':'Store locked up.',
        'P406':'Store in a corrosive resistant container with a resistant inner liner.',
        'P407':'Maintain air gap between stacks or pallets.',
        'P410':'Protect from sunlight.',
        'P411':'Store at temperatures not exceeding [...] °C/[...] °F.',
        'P410+P403':'Protect from sunlight. Store in a cool, well-ventilated place.',
        'P410+P412':'Protect from sunlight. Do not expose to temperatures exceeding 50°C/122°F.',
        'P412':'Do not expose to temperatures exceeding 50°C/122°F.',
        'P413':'Store bulk masses greater than [...] kg/[...] lbs at temperatures not exceeding [...] °C/[...] °F.',
        'P420':'Store separately.',
        'P422':'Store contents under [...].',
        'P501':'Dispose of contents/container in accordance with local/national regulations.',
        'P502':'Refer to manufacturer/supplier for information on recovery/recycling.',
    },
    'DE': {
        'P101':'Ist ärztlicher Rat erforderlich, Verpackung oder Kennzeichnungsetikett bereithalten.',
        'P102':'Darf nicht in die Hände von Kindern gelangen.',
        'P103':'Vor Gebrauch Etikett lesen.',
        'P201':'Vor Gebrauch besondere Anweisungen einholen.',
        'P202':'Vor Gebrauch alle Sicherheitshinweise lesen und verstehen.',
        'P210':'Von Hitze, heißen Oberflächen, Funken, offenen Flammen sowie anderen Zündquellen fernhalten. Nicht rauchen.',
        'P211':'Nicht gegen offene Flamme oder andere Zündquellen sprühen.',
        'P220':'Von Kleidung und anderen brennbaren Materialien fernhalten.',
        'P233':'Behälter dicht verschlossen halten.',
        'P234':'Nur im Originalbehälter aufbewahren.',
        'P235':'Kühl halten.',
        'P240':'Behälter und zu befüllende Anlage erden.',
        'P241':'Explosionsgeschützte elektrische Betriebsmittel/Lüftungsanlagen/Beleuchtung verwenden.',
        'P242':'Funkenfreies Werkzeug verwenden.',
        'P243':'Maßnahmen gegen elektrostatische Aufladung treffen.',
        'P250':'Nicht schleifen/stoßen/reiben.',
        'P260':'Staub/Rauch/Gas/Nebel/Dampf/Aerosol nicht einatmen.',
        'P261':'Einatmen von Staub/Rauch/Gas/Nebel/Dampf/Aerosol vermeiden.',
        'P262':'Kontakt mit Augen, Haut oder Kleidung vermeiden.',
        'P264':'Nach Gebrauch Hände gründlich waschen.',
        'P270':'Bei Benutzung des Produkts nicht essen, trinken oder rauchen.',
        'P271':'Nur im Freien oder in gut belüfteten Räumen verwenden.',
        'P272':'Kontaminierte Arbeitskleidung nicht außerhalb des Arbeitsplatzes tragen.',
        'P273':'Freisetzung in die Umwelt vermeiden.',
        'P280':'Schutzhandschuhe/Schutzkleidung/Augenschutz/Gesichtsschutz tragen.',
        'P301+P310':'BEI VERSCHLUCKEN: Sofort GIFTINFORMATIONSZENTRUM oder Arzt anrufen.',
        'P301+P330+P331':'BEI VERSCHLUCKEN: Mund ausspülen. KEIN Erbrechen herbeiführen.',
        'P302+P352':'BEI BERÜHRUNG MIT DER HAUT: Mit viel Wasser waschen.',
        'P303+P361+P353':'BEI BERÜHRUNG MIT DER HAUT (oder dem Haar): Alle beschmutzten Kleidungsstücke sofort ausziehen. Haut mit Wasser abwaschen/abduschen.',
        'P304+P340':'BEI EINATMEN: An die frische Luft bringen und in einer Position ruhigstellen, die das Atmen erleichtert.',
        'P305+P351+P338':'BEI KONTAKT MIT DEN AUGEN: Einige Minuten lang behutsam mit Wasser ausspülen. Vorhandene Kontaktlinsen nach Möglichkeit entfernen. Weiter ausspülen.',
        'P308+P313':'BEI Exposition oder falls betroffen: Ärztlichen Rat einholen/ärztliche Hilfe hinzuziehen.',
        'P310':'Sofort GIFTINFORMATIONSZENTRUM oder Arzt anrufen.',
        'P312':'Bei Unwohlsein GIFTINFORMATIONSZENTRUM oder Arzt anrufen.',
        'P313':'Ärztlichen Rat einholen/ärztliche Hilfe hinzuziehen.',
        'P314':'Bei Unwohlsein ärztlichen Rat einholen/ärztliche Hilfe hinzuziehen.',
        'P330':'Mund ausspülen.',
        'P331':'KEIN Erbrechen herbeiführen.',
        'P332+P313':'Bei Hautreizung: Ärztlichen Rat einholen/ärztliche Hilfe hinzuziehen.',
        'P333+P313':'Bei Hautreizung oder -ausschlag: Ärztlichen Rat einholen/ärztliche Hilfe hinzuziehen.',
        'P337+P313':'Bei anhaltender Augenreizung: Ärztlichen Rat einholen/ärztliche Hilfe hinzuziehen.',
        'P340':'Die betroffene Person an die frische Luft bringen und in einer Position ruhigstellen, die das Atmen erleichtert.',
        'P342+P311':'BEI Auftreten von Atemsymptomen: GIFTINFORMATIONSZENTRUM oder Arzt anrufen.',
        'P351':'Einige Minuten lang behutsam mit Wasser spülen.',
        'P352':'Mit viel Wasser waschen.',
        'P353':'Haut mit Wasser abspülen/abduschen.',
        'P361':'Alle kontaminierten Kleidungsstücke sofort ausziehen.',
        'P361+P364':'Alle kontaminierten Kleidungsstücke sofort ausziehen und vor erneutem Tragen waschen.',
        'P362':'Kontaminierte Kleidung ausziehen.',
        'P362+P364':'Kontaminierte Kleidung ausziehen und vor erneutem Tragen waschen.',
        'P363':'Kontaminierte Kleidung vor erneutem Tragen waschen.',
        'P370+P378':'BEI BRAND: Trockenlöschmittel, CO₂ oder alkoholbeständigen Schaum verwenden.',
        'P391':'Verschüttete Mengen aufnehmen.',
        'P402':'Trocken aufbewahren.',
        'P402+P404':'Trocken und in einem geschlossenen Behälter aufbewahren.',
        'P403':'An einem gut belüfteten Ort aufbewahren.',
        'P403+P233':'An einem gut belüfteten Ort aufbewahren. Behälter dicht verschlossen halten.',
        'P403+P235':'An einem gut belüfteten Ort aufbewahren. Kühl halten.',
        'P404':'In einem geschlossenen Behälter aufbewahren.',
        'P405':'Unter Verschluss aufbewahren.',
        'P410':'Vor Sonnenlicht schützen.',
        'P410+P403':'Vor Sonnenlicht schützen. An einem kühlen, gut belüfteten Ort aufbewahren.',
        'P410+P412':'Vor Sonnenlicht schützen. Nicht Temperaturen über 50 °C aussetzen.',
        'P412':'Nicht Temperaturen über 50 °C aussetzen.',
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
    'Acute Tox. 5':   'Akut Toks. 5',
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
    'Repr. Lact.':    'Emzirme Toks.',   # DB bazen "Repr. Lact." bazen sadece "Lact." döndürür
    'STOT SE 1':      'BHOT Tek Mar. 1',
    'STOT SE 2':      'BHOT Tek Mar. 2',
    'STOT SE 3':      'BHOT Tek Mar. 3',
    'STOT RE 1':      'BHOT Tkr. Mar. 1',
    'STOT RE 2':      'BHOT Tkr. Mar. 2',
    'Asp. Tox. 1':    'Asp. Toks. 1',
    'Asp. Tox. 2':    'Asp. Toks. 2',
    # ── Fallback birleşik gösterimler (H360 sub-code _h_to_class) ────────────
    'Repr. 1A/1B':    'Üreme Toks. 1A/1B',
    # ── H320 (Eye Irrit. 3) — nadir ama CLP'de var ─────────────────────────
    'Eye Irrit. 3':   'Göz Tahriş. 3',
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


# ─── Yetkili H kodu → h_class eşlemesi (SEA Ek-3 / CLP Annex III) ─────────────
# Veritabanı girdilerinde h_class/h_code uyumsuzluğu olabilir (veri bozukluğu).
# Bu tablo H kodunu birincil kaynak olarak kullanır; görüntülemede DB h_class'ını düzeltir.
#
# NOT: Aynı H kodunu veren birden fazla sınıf varsa (Acute Tox.1/2 → H300,
# Carc.1A/1B → H350, Repr.1A/1B → H360 vb.) DB'deki h_class korunur
# çünkü alt-kategori bilgisi önemlidir. Sadece kategori yanlışsa düzeltilir.
_H_CODE_CATEGORY = {
    # Patlayıcı
    'H200':'expl','H201':'expl','H202':'expl','H203':'expl','H204':'expl','H205':'expl',
    # Alevlenir / Aerosol
    'H220':'flam','H221':'flam','H222':'flam','H223':'flam',
    'H224':'flam','H225':'flam','H226':'flam','H227':'flam','H228':'flam','H229':'flam',
    # Pirofor / Kendi ısınan / Su reaktif
    'H240':'self','H241':'self','H242':'self',
    'H250':'pyr','H251':'self','H252':'self',
    'H260':'water','H261':'water',
    # Oksitleyici
    'H270':'ox','H271':'ox','H272':'ox','H273':'ox',
    # Basınçlı gaz
    'H280':'gas','H281':'gas',
    # Metal aşındırıcı
    'H290':'met',
    # Akut toksisite (oral/dermal/inhalasyon)
    'H300':'acute','H301':'acute','H302':'acute','H303':'acute',
    'H304':'asp',   # Aspirasyon
    'H310':'acute','H311':'acute','H312':'acute','H313':'acute',
    # Cilt
    'H314':'skin','H315':'skin','H316':'skin',
    # Cilt / Solunum duyarlılaştırma
    'H317':'sens',
    # Göz
    'H318':'eye','H319':'eye','H320':'eye',
    # İnhalasyon akut
    'H330':'acute','H331':'acute','H332':'acute','H333':'acute',
    # Solunum duyarlılaştırma
    'H334':'resp',
    # STOT Tek maruziyet
    'H335':'stot','H336':'stot',
    # Mutajenez
    'H340':'muta','H341':'muta',
    # Kanserojenez
    'H350':'carc','H351':'carc',
    # Üreme toksisitesi
    'H360':'repr','H361':'repr','H362':'repr',
    # STOT Tek maruziyet (sistemik)
    'H370':'stot','H371':'stot',
    # STOT Tekrarlanan maruziyet
    'H372':'stot','H373':'stot',
    # Sucul
    'H400':'aqua','H401':'aqua','H410':'aqua','H411':'aqua','H412':'aqua','H413':'aqua',
    # Ozon
    'H420':'ozone',
}

# h_class metninin hangi kategoriye ait olduğu
_CLASS_CATEGORY = {
    'Expl':'expl',
    'Flam. Gas':'flam','Aerosol':'flam','Flam. Liq':'flam','Flam. Sol':'flam',
    'Self-react':'self','Self-heat':'self','Pyr. Liq':'pyr','Pyr. Sol':'pyr',
    'Water-react':'water','Org. Perox':'self',
    'Ox. Gas':'ox','Ox. Liq':'ox','Ox. Sol':'ox',
    'Press. Gas':'gas','Met. Corr':'met',
    'Acute Tox':'acute','Asp. Tox':'asp',
    'Skin Corr':'skin','Skin Irrit':'skin',
    'Skin Sens':'sens','Resp. Sens':'resp',
    'Eye Dam':'eye','Eye Irrit':'eye',
    'Muta':'muta','Carc':'carc',
    'Repr':'repr','Lact':'repr',
    'STOT SE':'stot','STOT RE':'stot',
    'Aquatic':'aqua','Ozone':'ozone',
}

# H kodu → canonical h_class (tek sınıflı H kodları için)
# Birden fazla alt-kategorisi olanlar (H300 Tox.1/2, H350 1A/1B vb.) buraya EKLENMEZ
# çünkü alt-kategori bilgisi sadece DB'de vardır.
H_CODE_TO_CANONICAL_CLASS: dict = {
    # ── Fiziksel tehlikeler — physical_hazard_service.py / PhysicalEngine ────────
    # Bu kodların h_class'ı component hazards listesinde yoksa (fiziksel motor sonucu)
    # boş kalır; buradaki canonical değer PDF sınıflandırma tablosunu düzeltir.
    'H220': 'Flam. Gas 1A',
    'H221': 'Flam. Gas 2',
    'H222': 'Aerosol 1',
    'H223': 'Aerosol 3',
    'H224': 'Flam. Liq. 1',
    'H225': 'Flam. Liq. 2',
    'H226': 'Flam. Liq. 3',   # ← fiziksel motor / kullanıcı FP girişi için kritik
    'H232': 'Flam. Gas 1A',   # Pirofor gaz
    'H270': 'Ox. Gas 1',
    'H271': 'Ox. Liq. 1',
    'H280': 'Press. Gas',      # Basınçlı gaz (sıkıştırılmış/sıvılaştırılmış/çözülmüş)
    'H281': 'Press. Gas',      # Soğutulmuş gaz
    'H290': 'Met. Corr. 1',   # Metal aşındırıcı
    'H304': 'Asp. Tox. 1',    # aspirasyon toksisitesi — karışım seviyesi
    'H305': 'Asp. Tox. 2',    # aspirasyon toksisitesi Kat.2
    # ── Çevresel tehlikeler — eco_engine.js / ecological_service.py ─────────────
    'H410': 'Aquatic Chronic 1',  # ← eksikti; H411/H412/H413 listede vardı
    # ── Akut toksisite — Cat.3/4 tek kategorilidir (H300/H310/H330 belirsiz: 1 veya 2) ──
    # DB h_class bazen "(oral)"/"(dermal)"/"(inhal.)" yol son eki içerebilir;
    # canonical map her zaman saf sınıf adını döndürür → çift son ek sorununu önler.
    'H301': 'Acute Tox. 3',   # oral kat.3 — TEK canonical
    'H302': 'Acute Tox. 4',   # oral kat.4 — TEK canonical
    'H311': 'Acute Tox. 3',   # dermal kat.3 — TEK canonical
    'H312': 'Acute Tox. 4',   # dermal kat.4 — TEK canonical
    'H331': 'Acute Tox. 3',   # inhalasyon kat.3 — TEK canonical
    'H332': 'Acute Tox. 4',   # inhalasyon kat.4 — TEK canonical
    # ── Sağlık tehlikeleri — tek kategorili (canonical) H kodları ────────────────
    'H315': 'Skin Irrit. 2',
    'H316': 'Skin Irrit. 3',
    'H317': 'Skin Sens. 1',
    'H318': 'Eye Dam. 1',
    'H319': 'Eye Irrit. 2',
    'H320': 'Eye Irrit. 3',
    'H334': 'Resp. Sens. 1',
    'H335': 'STOT SE 3',
    'H336': 'STOT SE 3',
    'H341': 'Muta. 2',
    'H351': 'Carc. 2',
    'H362': 'Repr. Lact.',
    'H370': 'STOT SE 1',
    'H371': 'STOT SE 2',
    'H400': 'Aquatic Acute 1',
    'H401': 'Aquatic Acute 2',
    'H411': 'Aquatic Chronic 2',
    'H412': 'Aquatic Chronic 3',
    'H413': 'Aquatic Chronic 4',
    'H420': 'Ozone 1',
}


def _hclass_category(h_class: str) -> str:
    """h_class metninin kategori grubunu döndür."""
    s = h_class.strip()
    for prefix, cat in _CLASS_CATEGORY.items():
        if s.startswith(prefix):
            return cat
    return '?'


def correct_hclass(h_code: str, h_class: str) -> str:
    """
    DB'den gelen h_class'ın h_code ile kategorik uyumunu kontrol et.
    Uyumsuzsa (ör: H317 → 'Aquatic Acute 1') canonical değeri döndür.

    Öncelik kuralı: h_code kesin doğrudur; h_class yanlışsa düzelt.
    Alt-kategorili kodlarda (Carc.1A/1B, Repr.1A/1B) mevcut h_class korunur.
    """
    code4 = h_code.replace('*','').strip()[:4]
    if not code4.startswith('H'):
        return h_class

    # Önce canonical single-class map'e bak
    canonical = H_CODE_TO_CANONICAL_CLASS.get(code4)
    if canonical:
        return canonical  # Bu H kodunun tek canonical sınıfı var, her zaman kullan

    # Çok alt-kategorili H kodlar: kategori yanlışsa düzelt, doğruysa koru
    exp_cat = _H_CODE_CATEGORY.get(code4)
    got_cat = _hclass_category(h_class)
    if exp_cat and got_cat != '?' and exp_cat != got_cat:
        # Kategori tamamen yanlış — h_class'ı boş bırak (çevirici None/'' ile başa çıkır)
        return ''

    return h_class


def translate_hclass(h_class: str, lang: str = 'TR') -> str:
    """
    CLP hazard class kısa ismini dile çevir.
    TR → Türkçe kısaltma (SEA Ek-3 Tablo 1.2)
    Diğer → orijinal bırak (uluslararası standart)

    Akut toksisite maruziyet yolu son eklerini de çevirir:
      "(oral)" → "(ağız)"  |  "(dermal)" → "(deri)"  |  "(inhal.)" → "(solunum)"
    """
    if lang != 'TR':
        return h_class
    key = h_class.strip()
    suffix = '†' if key.endswith('†') else ''
    if suffix:
        key = key[:-1].strip()
    # CLP Ek-VI yıldız notasyonu — "Acute Tox. 4 *" → "Acute Tox. 4" (yıldız çeviri anahtarı değil)
    if key.endswith(' *'):
        key = key[:-2].strip()

    # Akut toksisite yol son eki — "(oral)", "(dermal)", "(inhal.)"
    _ROUTE_TR = {'(oral)': '(ağız)', '(dermal)': '(deri)', '(inhal.)': '(solunum)'}
    route_part = ''
    for en_route, tr_route in _ROUTE_TR.items():
        if key.endswith(' ' + en_route):
            route_part = ' ' + tr_route
            key = key[: -len(en_route) - 1].strip()
            break

    translated = CLP_CLASS_TR.get(key, key)
    return translated + route_part + suffix


def translate_hclass_list(classes: str, lang: str = 'TR') -> str:
    """
    Noktalı virgülle ayrılmış sınıf listesini çevir.
    Örn: "Flam. Liq. 3 H226; Skin Irrit. 2 H315" → "Alev. Sıv. 3 H226; Cilt Tahriş. 2 H315"
    H-kodu ve † eki varsa ayrıştırılır, yalnızca sınıf adı çevrilir, H-kodu korunur.
    """
    import re as _re
    if lang != 'TR' or not classes:
        return classes
    parts = [c.strip() for c in classes.split(';')]
    result = []
    for p in parts:
        # "Flam. Liq. 3 H226†" → cls="Flam. Liq. 3", h_code="H226", suffix="†"
        m = _re.match(r'^(.*?)\s+([A-Z]{1,3}\d{3}\w*)(†?)$', p.strip())
        if m:
            cls_part = m.group(1).strip()
            h_code   = m.group(2)
            suffix   = m.group(3)
            result.append(f'{translate_hclass(cls_part, lang)} {h_code}{suffix}')
        else:
            result.append(translate_hclass(p, lang))
    return '; '.join(result)
