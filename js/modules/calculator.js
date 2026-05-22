/**
 * Calculator Module — Python API Modu
 *
 * Tüm hesaplamalar /api/v1/sds/calculate endpoint'inde Python tarafından yapılır.
 * JS engine'ler (clp_engine.js, physical_engine.js vb.) yedek olarak korunur,
 * ancak bu modül tarafından çağrılmaz.
 *
 * Dinler  : CALC_REQUESTED { showExtra }
 * Emit eder: CALC_STARTED {}
 *            CALC_COMPLETE { hCodes, signal, pictograms, stot, euh, pCodes, eco,
 *                            clpPassed, phys, theoPhys, phAssess, chipHCodes }
 *            CALC_ERROR { message }
 */
const CalculatorModule = (() => {

  const API_BASE = window.API_BASE || '';

  function init() {
    EventBus.on('CALC_REQUESTED', ({ showExtra }) => {
      run(showExtra);
    });
    console.log('[Calculator] init OK — Python API modu aktif');
  }

  async function run(showExtra) {
    EventBus.emit('CALC_STARTED', {});

    const comps = getComps();
    if (!comps.length) {
      EventBus.emit('CALC_ERROR', { message: 'En az bir bileşen girin.' });
      return;
    }

    // %100 toplam kontrolü
    const totalConc = comps.reduce((s, c) => s + (parseFloat(c.conc) || 0), 0);
    EventBus.emit('CALC_TOTAL_CONC', { total: totalConc });

    const form    = document.getElementById('pform')?.value || 'liquid';
    const usage   = document.getElementById('pusage')?.value || 'industrial';
    const phRaw   = document.getElementById('tf_ph')?.value?.trim() || '';
    const fpRaw   = document.getElementById('tf_fp')?.value?.trim() || '';
    const userFP  = fpRaw ? parseFloat(fpRaw) : null;

    // Kullanıcı girdiği test verileri
    const testData = {};
    const _td = (id, key) => {
      const v = document.getElementById(id)?.value?.trim();
      if (v) testData[key] = parseFloat(v) || v;
    };
    _td('tf_density',     'density');
    _td('tf_bp',          'boiling_point');
    _td('tf_viscosity',   'viscosity');
    _td('tf_solubility',  'solubility');
    if (phRaw) testData.ph = phRaw;

    const payload = {
      components:  comps,
      form,
      user_fp:     isNaN(userFP) ? null : userFP,
      mixture_ph:  phRaw || null,
      test_data:   testData,
      usage,
      lang:        (typeof getSdsLang === 'function' ? getSdsLang() : null) || 'TR',
    };

    try {
      const resp = await fetch(`${API_BASE}/api/v1/sds/calculate`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify(payload),
      });

      if (!resp.ok) {
        const err = await resp.text();
        throw new Error(`API hatası ${resp.status}: ${err.substring(0, 200)}`);
      }

      const data = await resp.json();
      if (!data.success) throw new Error(data.detail || 'Hesaplama başarısız');

      // Teorik fiziksel alanları forma doldur
      const theoPhys = data.theo_props || {};
      if (typeof _fillPhysFormFields === 'function') _fillPhysFormFields(theoPhys);

      // pH değerlendirmesi (client-side yeterli — form alanı okuma)
      const phAssess = (typeof assessPH === 'function') ? assessPH(comps) : {};

      // API yanıtını CALC_COMPLETE formatına dönüştür
      const pRes = data.p_codes || {};
      const result = {
        hCodes:     data.h_codes     || [],
        signal:     data.signal      || 'Warning',
        pictograms: data.pictograms  || [],
        stot:       data.stot        || {},
        euh:        data.euh         || {},
        euhCodes:   data.euh_codes   || [],
        euhDetails: data.euh_details || [],
        pCodes:     pRes.p_codes     || pRes.codes || [],
        pRes,
        eco:        data.eco         || {},
        clpPassed:  data.clp_passed  || [],
        phys:       data.physical    || {},
        transport:  data.transport   || null,
        theoPhys,
        phAssess,
        chipHCodes: [],
        comps,
        showExtra:  showExtra || false,
        ateDetails: data.ate_details || {},
        _source:    'python-api',   // izleme için kaynak etiketi
      };

      StateStore.setCalcResult(result);
      EventBus.emit('CALC_COMPLETE', result);

    } catch(e) {
      console.error('[Calculator] API hatası:', e);
      EventBus.emit('CALC_ERROR', { message: e.message });
    }
  }

  /* ── YEDEK JS MOTORLARI ────────────────────────────────────────────────────
   * Aşağıdaki fonksiyon API erişimi olmadığında kullanılabilir.
   * Üretimde çağrılmaz — sadece acil durum yedeği olarak korunur.
   * ISO 27001: tüm hesaplar sunucu tarafında yapılmalıdır.
   *
  function _runLocalFallback(comps, form, showExtra) {
    const euhRes   = checkEUH(comps);
    const physRes  = calcPhysHazards(comps, form, null, showExtra || false);
    const stotRes  = calcStotRe(comps);
    const ecoRes   = calcEcological(comps, {});
    // ... (eski JS motor kodu burada)
  }
   * ─────────────────────────────────────────────────────────────────────────*/

  return { init, run };
})();
