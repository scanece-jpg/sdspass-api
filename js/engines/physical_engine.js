/**
 * PhysicalEngine — Fiziksel Tehlikeler — SDS Bölüm 2.1 + 9
 * Yanıcı sıvı, aspirasyon, yanıcı katı, oksitleyici hesaplama
 * Girdi : comps[], form, userFP
 * Çıktı : { results[], primary[], extra[], warnings[] }
 *
 * Events: dinler  → PHYSICAL_CALCULATE { comps, form, userFP }
 *         emit eder → PHYSICAL_READY { results, primary, extra, warnings }
 */
const PhysicalEngine = (() => {

  const FP_DB = {
    '110-54-3':-22,'110-82-7':-18,'142-82-5':-4,'111-65-9':13,
    '108-88-3':4,'71-43-2':-11,'1330-20-7':27,'95-47-6':17,
    '100-41-4':21,'95-63-6':44,'67-64-1':-18,'78-93-3':-9,
    '108-10-1':14,'67-63-0':12,'71-23-8':23,'71-36-3':29,
    '78-83-1':28,'64-17-5':13,'111-76-2':62,'112-34-5':78,
    '64742-47-8':21,'64742-48-9':-20,'64742-82-1':61,
    '64742-54-7':220,'8052-41-3':38,'56-81-5':160,
  };
  const BP_DB = {
    '110-54-3':69,'110-82-7':81,'67-64-1':56,'71-43-2':80,
    '78-93-3':80,'67-63-0':82,'64-17-5':78,'71-23-8':97,
    '64742-48-9':60,'71-36-3':118,'78-83-1':108,'111-76-2':171,
    '141-78-6':77,'123-86-4':126,'56-81-5':290,'7732-18-5':100,
  };
  const ASP_CAS = new Set([
    '110-54-3','110-82-7','142-82-5','111-65-9','71-43-2',
    '1330-20-7','64742-47-8','64742-48-9','64742-54-7','8052-41-3',
  ]);
  const OXIDIZING_CAS = new Set(['7722-84-1','7790-98-9','7775-09-9','7727-54-0']);
  const FLAM_SOL_CAS  = new Set(['7704-34-9','1333-86-4','12185-10-3']);

  function clsFlamLiq(fp, bp) {
    if (fp < 23 && (bp === null || bp <= 35)) return { h:'H224', cat:1, label:'Flam. Liq. 1', signal:'Danger' };
    if (fp < 23) return { h:'H225', cat:2, label:'Flam. Liq. 2', signal:'Danger' };
    if (fp >= 23 && fp <= 60) return { h:'H226', cat:3, label:'Flam. Liq. 3', signal:'Warning' };
    return null;
  }

  function calcFlamLiq(comps, userFP) {
    if (userFP !== null && userFP !== undefined && !isNaN(userFP)) {
      return { result: clsFlamLiq(userFP, null), source:`Kullanıcı girişi (${userFP}°C)`, fp: userFP };
    }
    let best = null, bestFP = null, trigger = null;
    for (const c of comps) {
      const cas = (c.cas || '').trim();
      const conc = parseFloat(c.concMax || c.conc) || 0;
      const fp = FP_DB[cas];
      if (fp === undefined || fp === null || fp >= 60) continue;
      const bp = BP_DB[cas] !== undefined ? BP_DB[cas] : null;
      const cls = clsFlamLiq(fp, bp);
      if (!cls) continue;
      const th = cls.cat <= 2 ? 1 : 10;
      if (conc < th) continue;
      if (!best || cls.cat < best.cat) { best = cls; bestFP = fp; trigger = {cas, name:c.name, conc, fp}; }
    }
    return {
      result: best,
      source: trigger ? `${trigger.name||trigger.cas} (%${trigger.conc}, FP=${trigger.fp}°C)` : null,
      fp: bestFP,
    };
  }

  function calcAspTox(comps) {
    let total = 0;
    const triggers = [];
    for (const c of comps) {
      const cas = (c.cas || '').trim();
      const conc = parseFloat(c.concMax || c.conc) || 0;
      const inList = ASP_CAS.has(cas);
      const hasClass = (c.hazards || []).some(h => h.h_class === 'Asp. Tox. 1');
      if ((inList || hasClass) && conc > 0) { triggers.push({cas, name:c.name, conc}); total += conc; }
    }
    if (total >= 10) return {
      result: { h:'H304', label:'Asp. Tox. 1', signal:'Danger' },
      source: triggers.map(t => `${t.name||t.cas} (%${t.conc})`).join(', '),
      total,
    };
    return { result: null, source: null, total };
  }

  function calculate(comps, form = 'liquid', userFP = null, showExtra = false) {
    const primary = [], extra = [], warnings = [];

    // Yanıcı Sıvı
    const fl = calcFlamLiq(comps, userFP);
    if (fl.result) primary.push({ type:'flam_liq', ...fl.result, source: fl.source, fp: fl.fp });

    // Aspirasyon
    const asp = calcAspTox(comps);
    if (asp.result) primary.push({ type:'asp_tox', ...asp.result, source: asp.source, total: asp.total });

    if (showExtra) {
      // Yanıcı Katı
      const fs = comps.filter(c => FLAM_SOL_CAS.has((c.cas||'').trim()) && (parseFloat(c.concMax||c.conc)||0) >= 1);
      if (fs.length) extra.push({ type:'flam_sol', h:'H228', label:'Flam. Sol. 2', signal:'Warning', source: fs.map(c=>c.name||c.cas).join(', ') });
      // Oksitleyici
      const ox = comps.filter(c => OXIDIZING_CAS.has((c.cas||'').trim()) && (parseFloat(c.concMax||c.conc)||0) >= 1);
      if (ox.length) extra.push({ type:'oxidizing', h:'H272', label:'Ox. Liq. 3', signal:'Warning', source: ox.map(c=>c.cas).join(', ') });
    }

    const results = [...primary, ...extra];
    return { results, primary, extra, warnings };
  }

  function init() {
    if (typeof EventBus !== 'undefined') {
      EventBus.on('PHYSICAL_CALCULATE', ({ comps, form, userFP }) => {
        const result = calculate(comps, form, userFP, true);
        EventBus.emit('PHYSICAL_READY', result);
      });
    }
    console.log('[PhysicalEngine] init OK');
  }

  return { init, calculate };
})();
