/**
 * CLPEngine — KKDİK Ek-2 / CLP (AT) No 1272/2008
 * Girdi : comps[] = [{ cas, name, conc, concMin, concMax, hazards:[{h_class,h_code}] }]
 * Çıktı : { hCodes[], signal, pictograms[], dominated[] }
 *
 * Events: dinler  → CLP_CALCULATE { comps }
 *         emit eder → H_CODES_READY { hCodes, signal, pictograms, dominated }
 */
const CLPEngine = (() => {

  // ── CLP Annex I Kesme Değerleri ──────────────────────────────────────────────
  const CUTOFFS = {
    'H300':1.0,'H301':1.0,'H302':5.0,
    'H310':1.0,'H311':1.0,'H312':5.0,
    'H330':1.0,'H331':1.0,'H332':5.0,
    'H314':1.0,'H315':10.0,'H318':1.0,'H319':10.0,
    'H317':1.0,'H334':0.1,
    'H340':0.1,'H341':1.0,
    'H350':0.1,'H351':1.0,
    'H360':0.1,'H361':1.0,'H362':0.1,
    'H370':10.0,'H371':10.0,'H372':1.0,'H373':10.0,
    'H335':20.0,'H336':20.0,
    'H304':10.0,
    'H400':0.1,'H410':0.1,'H411':1.0,'H412':10.0,'H413':25.0,
  };

  // ── CLP Dominance (Üstünlük) Kuralları ──────────────────────────────────────
  // Üst sınıf → alt sınıfları kaldır
  const DOMINANCE = {
    // Cilt/Göz: H314 "ciddi cilt yanıkları VE göz hasarı" — H318/H315/H319 gereksiz
    'H314': ['H318','H315','H319'],
    'H318': ['H319'],
    // Akut Toksisite — aynı yolda üst kategori alttakileri süpürür
    'H300': ['H301','H302'], 'H301': ['H302'],
    'H310': ['H311','H312'], 'H311': ['H312'],
    'H330': ['H331','H332'], 'H331': ['H332'],
    // STOT SE
    'H370': ['H371','H335','H336'], 'H371': ['H335','H336'],
    // STOT RE
    'H372': ['H373'],
    // CMR
    'H340': ['H341'], 'H350': ['H351'], 'H360': ['H361'],
    // Sucul Kronik
    'H410': ['H411','H412','H413'],
    'H411': ['H412','H413'],
    'H412': ['H413'],
    // Yanıcı Sıvı
    'H224': ['H225','H226'], 'H225': ['H226'],
  };

  // ── H kodu → GHS piktogram ───────────────────────────────────────────────────
  const H_TO_GHS = {
    'H200':'GHS01','H201':'GHS01','H202':'GHS01','H203':'GHS01','H204':'GHS01','H205':'GHS01',
    'H220':'GHS02','H221':'GHS02','H222':'GHS02','H223':'GHS02',
    'H224':'GHS02','H225':'GHS02','H226':'GHS02','H228':'GHS02',
    'H240':'GHS01','H241':'GHS01','H242':'GHS02',
    'H250':'GHS02','H251':'GHS02','H252':'GHS02',
    'H260':'GHS02','H261':'GHS02',
    'H270':'GHS03','H271':'GHS03','H272':'GHS03',
    'H280':'GHS04','H281':'GHS04',
    'H290':'GHS05',
    'H300':'GHS06','H301':'GHS06','H302':'GHS07',
    'H304':'GHS08',
    'H310':'GHS06','H311':'GHS06','H312':'GHS07',
    'H314':'GHS05','H315':'GHS07','H317':'GHS07',
    'H318':'GHS05','H319':'GHS07',
    'H330':'GHS06','H331':'GHS06','H332':'GHS07',
    'H334':'GHS08','H335':'GHS07','H336':'GHS07',
    'H340':'GHS08','H341':'GHS08','H350':'GHS08','H351':'GHS08',
    'H360':'GHS08','H361':'GHS08','H362':'GHS08',
    'H370':'GHS08','H371':'GHS08','H372':'GHS08','H373':'GHS08',
    'H400':'GHS09','H410':'GHS09','H411':'GHS09','H412':'GHS09','H413':'GHS09',
    'H420':'GHS07',
  };
  const GHS_ORDER = ['GHS01','GHS02','GHS03','GHS04','GHS05','GHS06','GHS07','GHS08','GHS09'];

  const DANGER_H = new Set([
    'H200','H201','H202','H203','H204','H205',
    'H220','H221','H222','H224','H225','H240','H241',
    'H250','H251','H252','H260','H261','H270','H271',
    'H290','H300','H301','H304','H310','H311',
    'H314','H317','H318','H330','H331','H334',
    'H340','H341','H350','H351','H360','H361','H362',
    'H370','H371','H372',
  ]);

  const FLAM_SKIP = new Set(['H220','H221','H222','H223','H224','H225','H226','H227','H228','H229']);

  function getGhsCodes(hcodes) {
    const pics = new Set();
    hcodes.forEach(h => {
      const base = h.replace(/[^H0-9]/g,'').substring(0,4);
      const ghs = H_TO_GHS[base] || H_TO_GHS[h];
      if (ghs) pics.add(ghs);
    });
    return GHS_ORDER.filter(g => pics.has(g));
  }

  function classify(comps) {
    // 1. Her bileşenden kesme değeri geçen H kodlarını topla
    //    Öncelik: SCL (maddeye özel) → GCL (genel tablo)
    //    comp.scl = { 'H314': 2.0, 'H315': 0.5, ... }  — CAS lookup'tan gelir

    // cutoffUsed: hangi H kodu için hangi eşik kullanıldı + kaynak (SCL/GCL)
    const cutoffUsed = {}; // { 'H314': { value: 2.0, source: 'SCL', cas: '1310-73-2' } }

    const raw = comps.flatMap(c => {
      const conc = parseFloat(c.concMax || c.conc) || 0;
      return (c.hazards || []).flatMap(h => {
        const code = (h.h_code || '').replace(/[*\s]/g,'').substring(0,4);
        if (!code.startsWith('H')) return [];
        if (FLAM_SKIP.has(code)) return []; // Yanıcılık fiziksel engine'de

        // ── Öncelik 1: SCL — maddeye özel (Annex VI, KKDİK Ek-1) ──────────────
        const scl = c.scl && c.scl[code] !== undefined ? c.scl[code] : null;

        // ── Öncelik 3: GCL — genel CLP tablo (Annex I §3.x) ──────────────────
        const gcl = CUTOFFS[code];

        // Hangi eşiği kullanacağız?
        const cutoff = scl !== null ? scl : gcl;
        const source = scl !== null ? 'SCL' : 'GCL';

        if (cutoff === undefined) return [code]; // Bilinmeyen → muhafazakâr
        if (conc >= cutoff) {
          // En düşük (en kısıtlayıcı) eşiği kaydet
          if (!cutoffUsed[code] || cutoff < cutoffUsed[code].value) {
            cutoffUsed[code] = { value: cutoff, source, cas: c.cas || '' };
          }
          return [code];
        }
        return [];
      });
    });

    // 2. Deduplikasyon
    const result = [...new Set(raw)];

    // 3. Dominance uygula
    const dominated = [];
    Object.entries(DOMINANCE).forEach(([dominant, subordinates]) => {
      if (result.includes(dominant)) {
        subordinates.forEach(sub => {
          const i = result.indexOf(sub);
          if (i > -1) { result.splice(i, 1); dominated.push(sub); }
        });
      }
    });

    // 4. Sinyal sözcüğü
    const signal = result.some(h => DANGER_H.has(h)) ? 'Danger' : 'Warning';

    // 5. Piktogramlar
    const pictograms = getGhsCodes(result);

    return { hCodes: result, signal, pictograms, dominated, cutoffUsed, getGhsCodes };
  }

  function init() {
    if (typeof EventBus !== 'undefined') {
      EventBus.on('CLP_CALCULATE', ({ comps }) => {
        const result = classify(comps);
        EventBus.emit('H_CODES_READY', result);
      });
    }
    console.log('[CLPEngine] init OK');
  }

  return { init, classify, getGhsCodes, CUTOFFS, DOMINANCE };
})();
