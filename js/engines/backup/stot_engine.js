/**
 * STOTEngine — CLP (AT) No 1272/2008 Ek I §3.9 — SDS Bölüm 11
 * STOT RE (Tekrarlı Maruziyet) hesaplama
 * Girdi : comps[]
 * Çıktı : { results[], analytic_results[], h_codes[], has_general, general_cat1, general_cat2 }
 *
 * Events: dinler  → STOT_CALCULATE { comps }
 *         emit eder → STOT_READY { results, h_codes, ... }
 */
const STOTEngine = (() => {

  const ORGAN_MAP = {
    'upper respiratory':'üst solunum yolu', 'respiratory':'solunum sistemi',
    'nervous system':'sinir sistemi', 'liver':'karaciğer', 'kidney':'böbrek',
    'blood':'kan', 'heart':'kalp', 'eyes':'gözler', 'skin':'deri',
    'bone marrow':'kemik iliği', 'thyroid':'tiroid',
  };

  function normalizeOrgan(raw) {
    if (!raw) return null;
    const r = raw.toLowerCase().trim();
    for (const [en, tr] of Object.entries(ORGAN_MAP)) {
      if (r.includes(en)) return tr;
    }
    return raw;
  }

  function extractOrgans(hcode) {
    const m = hcode.match(/\(([^)]+)\)/);
    if (!m) return [];
    return m[1].split(/[,;]/).map(s => normalizeOrgan(s.trim())).filter(Boolean);
  }

  function calculate(comps) {
    const organSums = {};
    let generalCat1 = 0, generalCat2 = 0;
    const results = [], analyticResults = [];

    for (const c of comps) {
      const conc = parseFloat(c.concMax || c.conc) || 0;
      if (conc <= 0) continue;

      for (const h of (c.hazards || [])) {
        const code = (h.h_code || '').replace(/[*\s]/g,'').substring(0,4);
        const cat = code === 'H372' ? 1 : code === 'H373' ? 2 : null;
        if (!cat) continue;

        const organs = extractOrgans(h.h_code || '');

        if (organs.length === 0) {
          // Organ belirsiz — genel havuza ekle
          if (cat === 1) generalCat1 += conc;
          else            generalCat2 += conc;
        } else {
          organs.forEach(org => {
            if (!organSums[org]) organSums[org] = { cat1:0, cat2:0, sources:[] };
            if (cat === 1) organSums[org].cat1 += conc;
            else           organSums[org].cat2 += conc;
            organSums[org].sources.push({ name: c.name || c.cas, conc, cat });
          });
        }
      }
    }

    // Muhafazakâr mod: organ belirsiz maddeler tüm organlara eklenir
    const allOrgans = Object.keys(organSums);
    for (const org of allOrgans) {
      organSums[org].cat1 += generalCat1;
      organSums[org].cat2 += generalCat2;
    }

    // Sonuç değerlendirme
    for (const [org, sums] of Object.entries(organSums)) {
      if (sums.cat1 >= 1.0) {
        results.push({ h:'H372', h_class:'STOT RE 1', organ: org, signal:'Danger',
          reason:`${org}: STOT RE 1 toplamı %${sums.cat1.toFixed(1)} ≥ %1.0 (KKDİK Ek-2, Tablo 3.9.4)` });
      } else if (sums.cat2 >= 10.0) {
        results.push({ h:'H373', h_class:'STOT RE 2', organ: org, signal:'Warning',
          reason:`${org}: STOT RE 2 toplamı %${sums.cat2.toFixed(1)} ≥ %10.0 (KKDİK Ek-2, Tablo 3.9.4)` });
      }
    }

    // Analitik mod: organ belirsiz hariç
    for (const [org, sums] of Object.entries(organSums)) {
      const c1 = sums.cat1 - generalCat1;
      const c2 = sums.cat2 - generalCat2;
      if (c1 >= 1.0) {
        analyticResults.push({ h:'H372', h_class:'STOT RE 1', organ: org, signal:'Danger',
          reason:`${org}: Eşleşen Cat1=%${c1.toFixed(1)} ≥ %1.0`, general_excl: generalCat1 });
      } else if (c2 >= 10.0) {
        analyticResults.push({ h:'H373', h_class:'STOT RE 2', organ: org, signal:'Warning',
          reason:`${org}: Eşleşen Cat2=%${c2.toFixed(1)} ≥ %10.0`, general_excl: generalCat2 });
      }
    }

    // Organ belirsiz — genel
    if (Object.keys(organSums).length === 0) {
      if (generalCat1 >= 1.0) {
        results.push({ h:'H372', h_class:'STOT RE 1', organ:'Genel (organ belirsiz)', signal:'Danger',
          reason:`Genel: Cat1=%${generalCat1.toFixed(1)} ≥ %1.0` });
      } else if (generalCat2 >= 10.0) {
        results.push({ h:'H373', h_class:'STOT RE 2', organ:'Genel (organ belirsiz)', signal:'Warning',
          reason:`Genel: Cat2=%${generalCat2.toFixed(1)} ≥ %10.0` });
      }
    }

    const h_codes = [...new Set(results.map(r => r.h))];

    return {
      results, analytic_results: analyticResults, h_codes,
      has_general: generalCat1 > 0 || generalCat2 > 0,
      general_cat1: generalCat1, general_cat2: generalCat2,
      warnings: [],
    };
  }

  function init() {
    if (typeof EventBus !== 'undefined') {
      EventBus.on('STOT_CALCULATE', ({ comps }) => {
        const result = calculate(comps);
        EventBus.emit('STOT_READY', result);
      });
    }
    console.log('[STOTEngine] init OK');
  }

  return { init, calculate };
})();
