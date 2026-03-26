/**
 * EcoEngine — CLP (AT) No 1272/2008 Ek I §4.1 — SDS Bölüm 12
 * Girdi : comps[] + ecoTestData{}
 * Çıktı : { aquatic, ozone, pbt, h_codes[] }
 *
 * Events: dinler  → ECO_CALCULATE { comps }
 *         emit eder → ECO_READY { aquatic, ozone, pbt, h_codes }
 */
const EcoEngine = (() => {

  const LOG_KOW_DB = {
    '110-54-3':3.29,'110-82-7':3.44,'108-88-3':2.73,'1330-20-7':3.12,
    '71-43-2':2.13,'100-41-4':3.15,'64-17-5':-0.31,'67-63-0':0.05,
    '71-36-3':0.88,'67-64-1':-0.24,'111-76-2':0.83,'50-00-0':0.35,
    '7681-52-9':-3.4,'7732-18-5':-1.38,'64742-54-7':7.0,'64742-47-8':4.5,
  };
  const READILY_BIO = new Set(['64-17-5','67-63-0','71-23-8','71-36-3','67-64-1',
    '78-93-3','141-78-6','7732-18-5','57-55-6','56-81-5','77-92-9','64-19-7']);
  const PERSISTENT = new Set(['1330-20-7','108-88-3','110-54-3','71-43-2','100-41-4']);
  const OZONE_CAS  = new Set(['75-69-4','75-71-8','76-13-1','76-14-2','75-72-9',
    '75-63-8','74-83-9','74-87-3','56-23-5','67-66-3','79-01-6']);
  const PBT_CAS    = new Set(['57-74-9','319-84-6','319-85-7','58-89-9','50-29-3','76-44-8']);

  function ec50ToMfactor(ec50) {
    if (ec50 <= 0.01) return 1000;
    if (ec50 <= 0.1)  return 100;
    if (ec50 <= 1.0)  return 10;
    return 1;
  }

  function calculate(comps, ecoTestData = {}) {
    const h_codes = [];
    let sumAcute1=0, sumChronic1=0, sumChronic2=0, sumChronic3=0, sumChronic4=0;
    const ozone=[], pbt=[];

    for (const c of comps) {
      const cas = (c.cas || '').trim();
      const conc = parseFloat(c.concMax || c.conc) || 0;
      if (conc <= 0) continue;

      const mAcute   = (c.m_factors?.acute)   || 1;
      const mChronic = (c.m_factors?.chronic)  || 1;

      let contributed = false;
      for (const h of (c.hazards || [])) {
        const code = (h.h_code || '').replace(/[*\s]/g,'').substring(0,4);
        if (code === 'H400') { sumAcute1   += (conc / 100) * mAcute   * 100; contributed = true; }
        if (code === 'H410') { sumChronic1 += (conc / 100) * mChronic * 100; sumAcute1 += (conc/100)*mAcute*100; contributed = true; }
        if (code === 'H411') { sumChronic2 += conc; contributed = true; }
        if (code === 'H412') { sumChronic3 += conc; contributed = true; }
        if (code === 'H413') { sumChronic4 += conc; contributed = true; }
      }

      if (OZONE_CAS.has(cas) && conc >= 0.1) ozone.push({ name: c.name || cas, cas, conc });
      if (PBT_CAS.has(cas) && conc >= 0.1)   pbt.push({ name: c.name || cas, cas, conc });
    }

    // Akut sınıflandırma
    let aquatic = null;
    if      (sumChronic1 >= 25) aquatic = { h:'H410', cls:'Aquatic Chronic 1', formula:`ΣChronic1×M=%${sumChronic1.toFixed(1)} ≥ 25%` };
    else if (sumChronic1 >= 10) aquatic = { h:'H411', cls:'Aquatic Chronic 2', formula:`ΣChronic1×M=%${sumChronic1.toFixed(1)} ≥ 10%` };
    else if (sumChronic2 >= 25) aquatic = { h:'H411', cls:'Aquatic Chronic 2', formula:`ΣChronic2=%${sumChronic2.toFixed(1)} ≥ 25%` };
    else if (sumChronic2 >= 10 || sumChronic3 >= 25) aquatic = { h:'H412', cls:'Aquatic Chronic 3', formula:`ΣChronic2=%${sumChronic2.toFixed(1)}, ΣChronic3=%${sumChronic3.toFixed(1)}` };
    else if (sumChronic4 >= 25) aquatic = { h:'H413', cls:'Aquatic Chronic 4', formula:`ΣChronic4=%${sumChronic4.toFixed(1)} ≥ 25%` };

    if (aquatic) h_codes.push(aquatic.h);
    if (sumAcute1 >= 25) { if (!h_codes.includes('H400')) h_codes.push('H400'); }
    if (ozone.length)    h_codes.push('H420');

    return { aquatic, ozone, pbt, h_codes };
  }

  function init() {
    if (typeof EventBus !== 'undefined') {
      EventBus.on('ECO_CALCULATE', ({ comps }) => {
        const result = calculate(comps);
        EventBus.emit('ECO_READY', result);
      });
    }
    console.log('[EcoEngine] init OK');
  }

  return { init, calculate };
})();
