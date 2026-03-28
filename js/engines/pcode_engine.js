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
  };

  // Etiket öncelik puanı (yüksek = önce seçilir)
  // Fiziksel tehlike > Hayati sağlık > Organ/Kronik > Genel önlem > Bertaraf
  const LABEL_PRIORITY = {
    'P210':100, 'P233':90,                         // Yanıcılık — en kritik
    'P301+P310':95, 'P331':90,                     // Yutma + kusturma
    'P304+P340':88, 'P310':85,                     // Solunum + acil
    'P308+P313':80,                                // CMR / üreme
    'P303+P361+P353':78, 'P370+P378':75,           // Yangın müdahale
    'P260':70, 'P271':68,                          // Solunumdan kaçın
    'P280':65,                                     // KKD giy
    'P305+P351+P338':60, 'P337+P313':55,           // Göz
    'P302+P352':50, 'P332+P313':45,                // Deri
    'P403+P235':40,                                // Serin/havalandırılmış
    'P264':35, 'P270':33,                          // Yıkama / yeme/içme yok
    'P273':30,                                     // Sucul — çevreye verme
    'P501':10,                                     // Bertaraf — en düşük
  };

  // Birbirini tamamlayan çiftler — birini alırsan diğerini de al
  const PAIRS = [
    ['P301+P310', 'P331'],   // Yuttuysan → kusturma
    ['P304+P340', 'P310'],   // Nefes aldıysa → acil
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
