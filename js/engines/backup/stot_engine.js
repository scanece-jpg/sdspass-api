/**
 * STOTEngine — CLP (AT) No 1272/2008 Ek I §3.9 — SDS Bölüm 11
 * STOT RE (Tekrarlı Maruziyet) hesaplama
 *
 * H372 (STOT RE 1): organ Cat1 toplamı ≥ %10.0 (generic) VEYA madde SCL_H372 ≤ konsantrasyon
 * H373 (STOT RE 2): Cat1 %1.0–%10.0 VEYA Cat2 ≥ %10.0 (generic) VEYA SCL_H373 ≤ konsantrasyon
 * SCL generic eşiğin önüne geçer — CLP Madde 10(3)
 * Kaynak: CLP Ek-1 §3.9, Tablo 3.9.4
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

  /** Bileşenin SCL listesinden H kodu için c_min döndürür; yoksa null. */
  function getSCLCmin(comp, hCode4) {
    const scl = comp.scl;
    if (!scl) return null;
    if (Array.isArray(scl)) {
      for (const s of scl) {
        if (!s || typeof s !== 'object') continue;
        const sh = (s.h_code || '').replace(/\*/g, '').trim().substring(0, 4);
        if (sh === hCode4 && s.c_min != null) return parseFloat(s.c_min);
      }
      return null;
    }
    if (typeof scl === 'object') {
      const val = scl[hCode4];
      return val != null ? parseFloat(val) : null;
    }
    return null;
  }

  /** SCL organ takibini güncelle — H372 > H373 önceliği. */
  function sclUpdate(sclOrgan, org, trigH, reason) {
    if (!sclOrgan[org]) {
      sclOrgan[org] = { h: trigH, reasons: [reason] };
    } else {
      if (trigH === 'H372' && sclOrgan[org].h === 'H373') sclOrgan[org].h = 'H372';
      sclOrgan[org].reasons.push(reason);
    }
  }

  function calculate(comps) {
    const organSums = {};
    let generalCat1 = 0, generalCat2 = 0;
    const results = [], analyticResults = [];
    const sclOrgan = {};  // org → { h: 'H372'|'H373', reasons: [] }

    for (const c of comps) {
      const conc = parseFloat(c.concMax || c.conc) || 0;
      if (conc <= 0) continue;

      const name = c.name || c.cas || '';

      for (const h of (c.hazards || [])) {
        const code = (h.h_code || '').replace(/[*\s]/g,'').substring(0,4);
        const cat = code === 'H372' ? 1 : code === 'H373' ? 2 : null;
        if (!cat) continue;

        const organs = extractOrgans(h.h_code || '');

        // SCL kontrolü — CLP Art. 10(3): SCL generic eşiğin yerini alır
        const sclH372 = getSCLCmin(c, 'H372');
        const sclH373 = getSCLCmin(c, 'H373');

        if (cat === 1 && (sclH372 !== null || sclH373 !== null)) {
          // SCL tanımlı → bireysel değerlendirme, generic havuza katılmaz
          const targets = organs.length > 0 ? organs : ['Genel (organ belirsiz)'];
          for (const org of targets) {
            if (sclH372 !== null && conc >= sclH372) {
              sclUpdate(sclOrgan, org, 'H372',
                `${name} %${+conc.toFixed(3)} ≥ SCL_H372=%${sclH372}`);
            } else if (sclH373 !== null && conc >= sclH373) {
              sclUpdate(sclOrgan, org, 'H373',
                `${name} %${+conc.toFixed(3)} ≥ SCL_H373=%${sclH373}`);
            }
            // SCL eşiği altındaysa katkı yok
          }

        } else if (cat === 2 && sclH373 !== null) {
          // H373 + SCL → bireysel değerlendirme
          const targets = organs.length > 0 ? organs : ['Genel (organ belirsiz)'];
          for (const org of targets) {
            if (conc >= sclH373) {
              sclUpdate(sclOrgan, org, 'H373',
                `${name} %${+conc.toFixed(3)} ≥ SCL_H373=%${sclH373}`);
            }
          }

        } else {
          // Generic additive havuz — mevcut davranış
          if (organs.length === 0) {
            if (cat === 1) generalCat1 += conc;
            else            generalCat2 += conc;
          } else {
            organs.forEach(org => {
              if (!organSums[org]) organSums[org] = { cat1:0, cat2:0, sources:[] };
              if (cat === 1) organSums[org].cat1 += conc;
              else           organSums[org].cat2 += conc;
              organSums[org].sources.push({ name, conc, cat });
            });
          }
        }
      }
    }

    // Organ belirsiz maddeler tüm organlara muhafazakâr olarak eklenir
    const allOrgans = Object.keys(organSums);
    for (const org of allOrgans) {
      organSums[org].cat1 += generalCat1;
      organSums[org].cat2 += generalCat2;
    }

    // Generic sonuçlar — Tablo 3.9.4
    for (const [org, sums] of Object.entries(organSums)) {
      if (sums.cat1 >= 10.0) {
        results.push({ h:'H372', h_class:'STOT RE 1', organ: org, signal:'Danger',
          reason:`${org}: STOT RE 1 toplamı %${sums.cat1.toFixed(1)} ≥ %10.0 (KKDİK Ek-2, Tablo 3.9.4)` });
      } else if (sums.cat1 >= 1.0 || sums.cat2 >= 10.0) {
        const parts = [];
        if (sums.cat1 >= 1.0) parts.push(`STOT RE 1 toplamı %${sums.cat1.toFixed(1)} (%1.0–%10.0 → H373)`);
        if (sums.cat2 >= 10.0) parts.push(`STOT RE 2 toplamı %${sums.cat2.toFixed(1)} ≥ %10.0`);
        results.push({ h:'H373', h_class:'STOT RE 2', organ: org, signal:'Warning',
          reason:`${org}: ${parts.join('; ')} (KKDİK Ek-2, Tablo 3.9.4)` });
      }
    }

    // SCL sonuçlarını ekle veya mevcut generic sonuçla birleştir
    const genericByOrgan = {};
    for (const r of results) genericByOrgan[r.organ] = r;

    for (const [org, sd] of Object.entries(sclOrgan)) {
      const trigH  = sd.h;
      const sclRsn = `${org}: ${sd.reasons.join('; ')} (CLP Art.10(3), Tablo 3.9.4)`;
      if (!genericByOrgan[org]) {
        results.push({
          h: trigH, h_class: trigH === 'H372' ? 'STOT RE 1' : 'STOT RE 2',
          organ: org, signal: trigH === 'H372' ? 'Danger' : 'Warning',
          reason: sclRsn, scl_based: true,
        });
      } else if (trigH === 'H372' && genericByOrgan[org].h === 'H373') {
        // SCL H372 generic H373'ü geçersiz kılar
        const r = genericByOrgan[org];
        r.h       = 'H372';
        r.h_class = 'STOT RE 1';
        r.signal  = 'Danger';
        r.reason += `; + SCL: ${sclRsn}`;
        r.scl_based = true;
      }
    }

    // Analitik mod: organ belirsiz hariç — generic
    for (const [org, sums] of Object.entries(organSums)) {
      const c1 = sums.cat1 - generalCat1;
      const c2 = sums.cat2 - generalCat2;
      if (c1 >= 10.0) {
        analyticResults.push({ h:'H372', h_class:'STOT RE 1', organ: org, signal:'Danger',
          reason:`${org}: Eşleşen Cat1=%${c1.toFixed(1)} ≥ %10.0`, general_excl: generalCat1 });
      } else if (c1 >= 1.0 || c2 >= 10.0) {
        const parts = [];
        if (c1 >= 1.0) parts.push(`Eşleşen Cat1=%${c1.toFixed(1)} (%1.0–%10.0 → H373)`);
        if (c2 >= 10.0) parts.push(`Eşleşen Cat2=%${c2.toFixed(1)} ≥ %10.0`);
        analyticResults.push({ h:'H373', h_class:'STOT RE 2', organ: org, signal:'Warning',
          reason:`${org}: ${parts.join('; ')}`, general_excl: generalCat1 });
      }
    }

    // SCL sonuçları analitik listede de yer alır
    for (const [org, sd] of Object.entries(sclOrgan)) {
      const trigH = sd.h;
      analyticResults.push({
        h: trigH, h_class: trigH === 'H372' ? 'STOT RE 1' : 'STOT RE 2',
        organ: org, signal: trigH === 'H372' ? 'Danger' : 'Warning',
        reason: `${org}: ${sd.reasons.join('; ')} (SCL)`,
        scl_based: true,
      });
    }

    // Organ belirsiz — genel havuz (hiç organ eşleşmesi yoksa)
    if (Object.keys(organSums).length === 0) {
      if (generalCat1 >= 10.0) {
        results.push({ h:'H372', h_class:'STOT RE 1', organ:'Genel (organ belirsiz)', signal:'Danger',
          reason:`Genel: Cat1=%${generalCat1.toFixed(1)} ≥ %10.0 (Tablo 3.9.4)` });
      } else if (generalCat1 >= 1.0 || generalCat2 >= 10.0) {
        const parts = [];
        if (generalCat1 >= 1.0) parts.push(`Cat1=%${generalCat1.toFixed(1)} (%1.0–%10.0 → H373)`);
        if (generalCat2 >= 10.0) parts.push(`Cat2=%${generalCat2.toFixed(1)} ≥ %10.0`);
        results.push({ h:'H373', h_class:'STOT RE 2', organ:'Genel (organ belirsiz)', signal:'Warning',
          reason:`Genel: ${parts.join('; ')} (Tablo 3.9.4)` });
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
