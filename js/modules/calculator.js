/**
 * Calculator Module
 *
 * Dinler  : CALC_REQUESTED { showExtra }
 * Emit eder: CALC_STARTED {}
 *            CALC_COMPLETE { hCodes, signal, pictograms, stot, euh, pCodes, eco,
 *                            clpPassed, phys, theoPhys, phAssess, chipHCodes }
 *            CALC_ERROR { message }
 */
const CalculatorModule = (() => {

  function init() {
    EventBus.on('CALC_REQUESTED', ({ showExtra }) => {
      run(showExtra);
    });
    console.log('[Calculator] init OK');
  }

  function run(showExtra) {
    EventBus.emit('CALC_STARTED', {});

    const comps = getComps();   // component-manager'dan global fonksiyon
    if (!comps.length) {
      EventBus.emit('CALC_ERROR', { message: 'En az bir bileşen girin.' });
      return;
    }

    try {
      // %100 toplam kontrolü
      const totalConc = comps.reduce((s, c) => s + (parseFloat(c.conc) || 0), 0);
      EventBus.emit('CALC_TOTAL_CONC', { total: totalConc });

      // Motorları çalıştır (mevcut global fonksiyonlar)
      const form       = document.getElementById('pform')?.value || 'liquid';
      const euhRes     = checkEUH(comps);
      const physRes    = calcPhysHazards(comps, form, null, showExtra || false);
      const stotRes    = calcStotRe(comps);
      const secondaryRes = calcSecondaryClassification(comps);

      if (secondaryRes.extra.length) {
        (physRes.results = physRes.results || []).push(...secondaryRes.extra.map(e => ({ ...e, type: 'secondary' })));
        (physRes.primary = physRes.primary || []).push(...secondaryRes.extra.map(e => ({ ...e, type: 'secondary' })));
        (physRes.warnings = physRes.warnings || []).push(...secondaryRes.warnings);
      }

      const ecoRes = calcEcological(comps, {});

      // CLP cutoff tablosu
      const CLP_CUTOFFS = {
        'H300':1.0,'H310':1.0,'H330':1.0,
        'H301':1.0,'H311':1.0,'H331':1.0,
        'H302':5.0,'H312':5.0,'H332':5.0,
        'H314':1.0,'H315':10.0,'H318':1.0,'H319':10.0,
        'H317':1.0,'H334':0.1,
        'H340':0.1,'H341':1.0,
        'H350':0.1,'H351':1.0,
        'H360':0.1,'H361':1.0,
        'H362':0.1,
        'H370':10.0,'H371':10.0,'H372':1.0,'H373':10.0,
        'H335':20.0,'H336':20.0,
        'H304':10.0,
        'H400':0.1,'H410':0.1,'H411':1.0,'H412':10.0,'H413':25.0,
      };
      const FLAM_SKIP = new Set(['H220','H221','H222','H223','H224','H225','H226','H227','H228','H229']);

      const chipHCodes = comps.flatMap(c => {
        const conc = parseFloat(c.concMax || c.conc) || 0;
        return (c.hazards || []).flatMap(h => {
          const code = (h.h_code || '').replace(/[*\s]/g, '').substring(0, 4);
          if (!code.startsWith('H')) return [];
          if (FLAM_SKIP.has(code)) return [];
          const cutoff = CLP_CUTOFFS[code];
          if (cutoff === undefined) return [code];
          return conc >= cutoff ? [code] : [];
        });
      });

      const allHCodes = new Set([
        ...(physRes.results || []).map(r => r.h || r.h_code),
        ...(stotRes.h_codes || []),
        ...chipHCodes,
      ]);
      const allHCodesArr = [...allHCodes].filter(h => h && h.startsWith('H') && h.length >= 4);

      const DANGER_SET = new Set(['H200','H201','H202','H203','H204','H205',
        'H220','H221','H222','H224','H225','H240','H241','H250','H251','H252','H260','H261',
        'H270','H271','H272','H290','H300','H301','H304','H310','H311','H314','H317','H318',
        'H330','H331','H334','H340','H341','H350','H351','H360','H361','H362','H370','H371','H372']);
      const signal  = allHCodesArr.some(h => DANGER_SET.has(h)) ? 'Danger' : 'Warning';
      const usage   = document.getElementById('pusage')?.value || 'industrial';
      const pRes    = calcPCodes(allHCodesArr, signal, usage);
      pRes.label    = selectLabelPCodes(pRes.codes, 6, usage);
      pRes.usage    = usage;
      pRes.sds      = classifySdsPCodes(pRes.codes);

      // Fiziksel prop hesaplama
      const theoPhys = calcPhysProps_theoretical(comps);
      const userPHEntered = parseFloat(document.getElementById('tf_ph')?.value);
      const phAssess = assessPH(comps);
      theoPhys.phAssess = phAssess;
      theoPhys.userPH   = isNaN(userPHEntered) ? null : userPHEntered;
      _fillPhysFormFields(theoPhys);

      // _chipPassed (PDF için)
      const _physCodes = new Set((physRes.results || []).map(e => (e.h || e.h_code || '').replace(/[*\s]/g,'').substring(0,4)));
      const _chipPassed = comps.flatMap(c => {
        const conc = parseFloat(c.concMax || c.conc) || 0;
        return (c.hazards || []).flatMap(h => {
          const code = (h.h_code || '').replace(/[*\s]/g,'').substring(0,4);
          if (!code.startsWith('H') || _physCodes.has(code)) return [];
          if (FLAM_SKIP.has(code)) return [];
          const cutoff = CLP_CUTOFFS[code];
          if (cutoff === undefined || conc >= cutoff) {
            const entry = {
              h_class:    h.h_class    || '',
              h_code:     h.h_code     || '',
              reason:     cutoff !== undefined ? `%${conc} ≥ %${cutoff} kesme değeri` : 'Bileşen sınıflandırması',
              cutoff_used:cutoff !== undefined ? `%${cutoff}` : '—',
            };
            if (h.note_flag) entry.note_flag = h.note_flag;
            if (h.note)      entry.note      = h.note;
            if (h.repro_sub) entry.repro_sub = h.repro_sub;
            return [entry];
          }
          return [];
        });
      });
      const _seenCP = new Set();
      const clpPassed = [...(physRes.results||[]).map(r=>({
        h_class:r.h_class||r.hazard_class||r.label||'', h_code:r.h||r.h_code||'',
        reason:r.reason||r.source||'', cutoff_used:r.cutoff_used||r.reason||''
      })), ..._chipPassed].filter(e => {
        const c = (e.h_code||'').replace(/[*\s]/g,'').substring(0,4);
        if (_seenCP.has(c)) return false;
        _seenCP.add(c); return true;
      });

      const result = {
        hCodes:     allHCodesArr,
        signal,
        pictograms: getGhsCodes(allHCodesArr),
        stot:       stotRes,
        euh:        euhRes,
        euhCodes:   euhRes.euh_codes || [],
        euhDetails: euhRes.euh_details || [],
        pCodes:     pRes.codes || pRes.p_codes || [],
        pRes,
        eco:        ecoRes,
        clpPassed,
        phys:       physRes,
        theoPhys,
        phAssess,
        chipHCodes: [...new Set(chipHCodes)],
        comps,
        showExtra:  showExtra || false,
      };

      StateStore.setCalcResult(result);
      EventBus.emit('CALC_COMPLETE', result);

    } catch(e) {
      console.error('[Calculator] Error:', e);
      EventBus.emit('CALC_ERROR', { message: e.message });
    }
  }

  return { init, run };
})();
