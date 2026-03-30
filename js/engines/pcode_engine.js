/**
 * PCodeEngine — CLP (AT) No 1272/2008 Ek III
 * Girdi : { hCodes[], signal, usage }
 * Çıktı : { codes[], details[], by_category{}, total }
 *
 * Events: dinler  → H_CODES_READY { hCodes, signal }
 *         emit eder → P_CODES_READY { codes, details, by_category, total, label, sds }
 */
const PCodeEngine = (() => {

  const H_TO_P = {
    // ── Patlayıcılar (CLP Ek III Tablo 1) ───────────────────────────────────
    'H200':['P210','P230','P234','P240','P250','P280','P370+P380','P372','P373','P401','P501'],
    'H201':['P210','P230','P234','P240','P250','P280','P370+P380','P372','P373','P401','P501'],
    'H202':['P210','P230','P234','P240','P250','P280','P370+P380','P372','P373','P401','P501'],
    'H203':['P210','P234','P240','P250','P280','P370+P378','P401','P501'],
    'H204':['P210','P234','P240','P250','P280','P370+P378','P401','P501'],
    // ── Yanıcı Gazlar ───────────────────────────────────────────────────────
    'H220':['P210','P377','P381','P403'],
    'H221':['P210','P377','P381','P403'],
    'H232':['P210','P222','P280','P377','P381','P403'],   // Pirofor gaz — hava teması önle
    // ── Aerosoller ──────────────────────────────────────────────────────────
    'H222':['P210','P211','P251','P410+P412'],
    'H223':['P210','P211','P251','P410+P412'],
    'H229':['P251','P410+P412'],
    // ── Kendiliğinden Parçalanmalar / Organik Peroksitler ───────────────────
    'H240':['P201','P210','P220','P234','P280','P283','P370+P378','P401','P405','P501'],
    'H241':['P210','P220','P234','P280','P283','P370+P378','P401','P405','P501'],
    'H242':['P210','P220','P234','P280','P370+P378','P401','P405','P501'],
    // ── Pirofor / Kendiliğinden Isınan ──────────────────────────────────────
    'H250':['P222','P231+P232','P233','P280','P302+P334','P370+P378','P422'],
    'H251':['P235','P280','P407','P413','P420','P501'],
    'H252':['P235','P280','P407','P413','P420','P501'],
    // ── Su ile Reaksiyon Veren ───────────────────────────────────────────────
    'H260':['P223','P231+P232','P280','P335+P334','P370+P378','P402+P404','P501'],
    'H261':['P223','P231+P232','P280','P335+P334','P370+P378','P402+P404','P501'],
    // ── Oksitleyici Gaz / Basınçlı Gaz ─────────────────────────────────────
    'H270':['P220','P244','P370+P376','P403'],
    'H280':['P403','P410+P403'],
    'H281':['P403','P410+P403'],
    // ── Metal Korozifi ───────────────────────────────────────────────────────
    'H290':['P234','P390','P406'],
    // ── Laktasyon Toksisitesi ────────────────────────────────────────────────
    'H362':['P201','P260','P263','P264','P270','P308+P313'],
    // ── Yanıcı Sıvılar ──────────────────────────────────────────────────────
    'H224':['P210','P233','P241','P242','P243','P280','P303+P361+P353','P370+P378','P403+P235','P501'],
    'H225':['P210','P233','P241','P242','P243','P280','P303+P361+P353','P370+P378','P403+P235','P501'],
    'H226':['P210','P233','P280','P370+P378','P403+P235','P501'],
    'H228':['P210','P240','P241','P280','P370+P378','P501'],
    'H271':['P210','P220','P280','P306+P360','P370+P378','P405','P501'],
    'H272':['P210','P220','P221','P280','P370+P378','P501'],
    'H300':['P264','P270','P301+P310','P321','P330','P405','P501'],
    'H301':['P264','P270','P301+P310','P321','P330','P405','P501'],
    'H302':['P264','P270','P301+P312','P330','P501'],
    'H304':['P260','P264','P270','P301+P310','P331','P405','P501'],
    'H310':['P262','P264','P270','P280','P302+P350','P310','P361','P405','P501'],
    'H311':['P280','P302+P352','P312','P361','P405','P501'],
    'H312':['P280','P302+P352','P312','P501'],
    'H314':['P260','P264','P280','P301+P330+P331','P303+P361+P353','P304+P340','P305+P351+P338','P310','P321','P363','P405','P501'],
    'H315':['P264','P280','P302+P352','P321','P332+P313','P362','P501'],
    'H317':['P261','P272','P280','P302+P352','P333+P313','P321','P363','P501'],
    'H318':['P264','P280','P305+P351+P338','P310','P501'],
    'H319':['P264','P280','P305+P351+P338','P337+P313','P501'],
    'H330':['P260','P271','P284','P304+P340','P310','P403+P233','P405','P501'],
    'H331':['P261','P271','P304+P340','P311','P403+P233','P405','P501'],
    'H332':['P261','P271','P304+P340','P312','P501'],
    'H334':['P260','P271','P284','P304+P340','P342+P311','P501'],
    'H335':['P261','P271','P304+P340','P312','P501'],
    'H336':['P261','P271','P304+P340','P312','P501'],
    'H340':['P201','P202','P280','P308+P313','P405','P501'],
    'H341':['P201','P202','P280','P308+P313','P405','P501'],
    'H350':['P201','P202','P280','P308+P313','P405','P501'],
    'H351':['P201','P202','P280','P308+P313','P405','P501'],
    'H360':['P201','P202','P263','P280','P308+P313','P405','P501'],
    'H361':['P201','P202','P263','P280','P308+P313','P405','P501'],
    'H370':['P260','P264','P270','P307+P311','P405','P501'],
    'H371':['P260','P264','P270','P308+P313','P405','P501'],
    'H372':['P260','P264','P270','P314','P501'],
    'H373':['P260','P314','P501'],
    'H400':['P273','P391','P501'],
    'H410':['P273','P391','P501'],
    'H411':['P273','P501'],
    'H412':['P273','P501'],
    'H413':['P273','P501'],
    'H420':['P502'],
  };

  // Geçersiz kılma: güçlü kod varsa zayıfları sil (SEA / CLP Annex III)
  const SUPERSEDES = {
    // P310 (derhal ara) daha güçlü — zayıf acil kodlarını ezer
    'P310':        ['P311','P312','P301+P312'],   // H314+H302: P310+P301+P330+P331 kalır
    'P301+P310':   ['P301+P312'],                 // Doğrudan P301+P310 varsa da ezer
    'P260':        ['P261'],                       // Tam solunumdan kaçın > kısmen kaçın
    'P271':        ['P261'],                       // Açık hava > az soluma
    'P314':        ['P312'],                       // Tıbbi yardım al > hissetmiyorsan ara
    // P403+P233 varsa ayrı P233 gereksiz (aynı bilgi kombine formda)
    'P403+P233':   ['P233'],
    // P410+P403 varsa ayrı P403 gereksiz
    'P410+P403':   ['P403'],
    // P231+P232 varsa ayrı P231 gereksiz
    'P231+P232':   ['P231','P232'],
    // P335+P334 varsa ayrı P334/P335 gereksiz
    'P335+P334':   ['P334','P335'],
    // P402+P404 varsa ayrı P402/P404 gereksiz
    'P402+P404':   ['P402','P404'],
  };

  // ── Etiket öncelik puanı (yüksek = önce seçilir) ────────────────────────────
  // Kaynak: CLP Annex IV Not 3 — tehlike şiddeti öncelik sırası
  // Fiziksel tehlike > Akut hayat tehlikesi > Akut sağlık > Kronik > Önlem > Bertaraf
  const LABEL_PRIORITY = {
    // ── Yangın / Patlama (Fiziksel — en kritik) ──────────────────────────────
    'P210': 100,                   // Tutuşma kaynağından uzak tut
    'P211': 99,                    // Aleve veya diğer tutuşma kaynaklarına sıkma
    'P222': 98,                    // Hava ile temasına izin verme (pirofor)
    'P223': 98,                    // Su ile temasına izin verme
    'P220': 97,                    // Oksitleyici — yanıcılardan uzak tut
    'P370+P380': 96,               // Yangın → bölgeyi boşalt
    'P372': 96,                    // Yangında patlama riski
    'P370+P378': 95,               // Yangın müdahale
    'P370+P376': 95,               // Yangın → gaz beslemesini kapat
    'P306+P360': 94,               // Giysiye temas — hemen durula
    'P373': 93,                    // Yangın patlamaya ulaştığında söndürme
    'P377': 92,                    // Yanan sızdırma gazı — söndürmeyiniz
    'P381': 91,                    // Tutuşma kaynaklarını ortadan kaldır
    'P244': 89,                    // Oksitleyici gaz — yağ/gres'ten uzak tut
    'P283': 88,                    // Yanmaya dayanıklı/alev almaz giysiler giy
    'P250': 87,                    // Sürtme/şoka/titreşime maruz bırakma
    'P230': 86,                    // ... ile ıslatılmış halde tut
    'P231+P232': 85,               // İnert gaz altında işle, nem'den koru

    // ── Akut hayati müdahale ──────────────────────────────────────────────────
    'P301+P310': 93,               // Yutulursa → derhal ara (H300/H301)
    'P301+P330+P331': 92,          // Yutulursa → ağzı çalkala, kusturma (H314 korozif)
    'P310': 90,                    // Derhal ZEHİR MERKEZİ ara
    'P311': 88,                    // ZEHİR MERKEZİ ara
    'P331': 87,                    // Kusturmayın (korozif)
    'P304+P340': 86,               // Solunursa → temiz havaya çık
    'P342+P311': 85,               // Solunum belirtisi → ara
    'P308+P313': 83,               // CMR/üreme toksik — maruz kalırsa

    // ── Cilt / Göz müdahale ───────────────────────────────────────────────────
    'P303+P361+P353': 80,          // Cilde/saça temas → hemen çıkar, duş al
    'P305+P351+P338': 78,          // Göze temas → su ile yıka
    'P302+P350': 75,               // Cilt temas → sabunla yıka (H310)
    'P302+P352': 72,               // Cilt temas → su ile yıka
    'P337+P313': 68,               // Göz tahrişi devam → doktor

    // ── Önleyici — kritik ─────────────────────────────────────────────────────
    'P260': 70,                    // Solunum koruma — mutlak
    'P221': 67,                    // Oksitleyici — yanıcı karışımı önle
    'P280': 65,                    // KKD giy
    'P284': 63,                    // Solunum cihazı
    'P271': 60,                    // Açık hava / iyi havalandırma
    'P201': 58,                    // CMR — talimat al
    'P202': 57,                    // CMR — oku anla

    // ── Depolama / Saklama ────────────────────────────────────────────────────
    'P403+P235': 45,               // Serin + havalandırılmış
    'P403+P233': 44,               // Havalandırılmış + kapalı kap
    'P410+P403': 44,               // Güneşten koru + havalandırılmış
    'P410+P412': 43,               // Güneşten koru + 50°C'yi aşma
    'P405': 42,                    // Kilitli sakla
    'P407': 42,                    // Yığınlar arasında hava aralığı bırak
    'P413': 41,                    // Dökme yığın — sınırlı sıcaklıkta sakla
    'P420': 40,                    // Diğer maddelerden uzakta sakla
    'P233': 40,                    // Kabı kapalı tut
    'P401': 39,                    // Uygun yerde sakla
    'P402+P404': 38,               // Kuru yerde + kapalı kapta sakla
    'P403': 37,                    // İyi havalandırılmış yerde sakla
    'P406': 36,                    // Korozyona dayanıklı kapta sakla
    'P422': 35,                    // İçeriği ... altında sakla
    'P390': 34,                    // Çevre kirlenmesini önle — döküleni emer

    // ── Genel / Hijyen ────────────────────────────────────────────────────────
    'P264': 35,                    // Kullanım sonrası yıka
    'P270': 33,                    // Yeme/içme/sigara yok
    'P273': 30,                    // Çevreye verme

    // ── Bertaraf ─────────────────────────────────────────────────────────────
    'P501': 10,                    // İmha
  };

  // ── Birbirini tamamlayan çiftler — biri seçilirse diğeri de eklenir ─────────
  const PAIRS = [
    ['P301+P310',      'P331'],            // H300/H301: yuttuysan → kusturma
    ['P301+P330+P331', 'P310'],            // H314: korozif yutma → derhal ara
    ['P304+P340',      'P310'],            // Solunum → acil
    ['P303+P361+P353', 'P305+P351+P338'], // Cilt temas → göz de kontrol et
  ];

  const P_CATEGORIES = { 1:'general', 2:'prevention', 3:'response', 4:'storage', 5:'disposal' };

  function calculate({ hCodes, signal, usage = 'industrial' }) {
    const assigned = new Set();

    for (const h of hCodes) {
      const hc = h.replace(/[*\s]/g,'').substring(0,4);
      (H_TO_P[hc] || []).forEach(p => assigned.add(p));
    }

    // Çakışma çözümü
    for (const [strong, weaks] of Object.entries(SUPERSEDES)) {
      if (assigned.has(strong)) weaks.forEach(w => assigned.delete(w));
    }

    // Kullanım tipine göre P101/P102/P103
    if (usage === 'consumer') {
      assigned.add('P101'); assigned.add('P102'); assigned.add('P103');
    } else if (usage === 'professional') {
      assigned.add('P101');
      if (signal !== 'Danger') assigned.add('P103');
    }

    const cats = { general:[], prevention:[], response:[], storage:[], disposal:[] };
    const details = [];
    const sorted = [...assigned].sort((a,b) => a.localeCompare(b));

    for (const code of sorted) {
      const first = code.split('+')[0];
      const n = parseInt(first[1]) || 0;
      const cat = P_CATEGORIES[n] || 'general';
      const d = { code, category: cat, combined: code.includes('+') };
      details.push(d);
      (cats[cat] || cats.general).push(d);
    }

    // ── Etiket için "Akıllı Seçim" — max 6 (10'a kadar çıkabilir) ──────────────
    // SEA / KKDİK Ek-2: etiket üzerinde 6 P-kodu önerilir
    const labelSelected = [];

    // 1. Öncelik puanına göre sırala
    const byPriority = [...sorted].sort((a, b) => {
      const pa = LABEL_PRIORITY[a] || 20;
      const pb = LABEL_PRIORITY[b] || 20;
      return pb - pa;
    });

    // 2. İlk 6'yı al
    for (const code of byPriority) {
      if (labelSelected.length >= 6) break;
      labelSelected.push(code);
    }

    // 3. Çift kuralı: seçilmiş bir kodun partneri eksikse ve 10 limiti aşılmıyorsa ekle
    for (const [a, b] of PAIRS) {
      if (labelSelected.includes(a) && !labelSelected.includes(b) && labelSelected.length < 10) {
        labelSelected.push(b);
      }
      if (labelSelected.includes(b) && !labelSelected.includes(a) && labelSelected.length < 10) {
        labelSelected.unshift(a); // partneri daha öne al
      }
    }

    // 4. Tekrar öncelik sıralaması
    labelSelected.sort((a, b) => (LABEL_PRIORITY[b] || 20) - (LABEL_PRIORITY[a] || 20));

    return {
      codes: sorted,
      details,
      by_category: cats,
      total: sorted.length,
      label_codes: labelSelected,        // etiket için seçilmiş (max 10)
    };
  }

  function init() {
    if (typeof EventBus !== 'undefined') {
      EventBus.on('H_CODES_READY', (data) => {
        const usage = document.getElementById('pusage')?.value || 'industrial';
        const result = calculate({ hCodes: data.hCodes, signal: data.signal, usage });
        EventBus.emit('P_CODES_READY', { ...result, signal: data.signal, usage });
      });
    }
    console.log('[PCodeEngine] init OK');
  }

  return { init, calculate };
})();
