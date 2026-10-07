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

  // Son başarılı hesabın girdisi ve özeti — PDF aynı girdiyle üretilir, sonuç bununla karşılaştırılır
  let _lastPayload = null;
  let _lastSummary = null;

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

    const payload = buildPayload(comps);
    await _send(payload, showExtra, comps);
  }

  // Formdaki güncel değerlerden hesap girdisini kur (sağ panel ve PDF aynı girdiyi kullanır)
  function buildPayload(comps) {
    comps = comps || getComps();
    const form    = document.getElementById('pform')?.value || 'liquid';
    const usage   = document.getElementById('pusage')?.value || 'industrial';
    const phRaw   = document.getElementById('tf_ph')?.value?.trim() || '';
    // Motorun doldurduğu (data-source="theo") değerler geri gönderilmez — aksi halde
    // ikinci hesaplamada tahmin "kullanıcı ölçümü" gibi işlenir.
    const _isTheo = id => document.getElementById(id)?.dataset?.source === 'theo';
    const fpRaw   = _isTheo('tf_fp') ? '' : (document.getElementById('tf_fp')?.value?.trim() || '');
    const userFP  = fpRaw ? parseFloat(fpRaw) : null;
    const fpStatus = userFP == null ? (document.getElementById('fp_status')?.value || '') : '';

    // Kullanıcı girdiği test verileri
    const testData = {};
    const _td = (id, key) => {
      if (_isTheo(id)) return;
      const v = document.getElementById(id)?.value?.trim();
      if (v) testData[key] = parseFloat(v) || v;
    };
    _td('tf_density',     'density');
    _td('tf_bp',          'boiling_point');
    _td('tf_visc',        'viscosity');
    _td('tf_sol',         'solubility');
    _td('tf_mp',          'melting_point');
    _td('tf_ait',         'auto_ignition');
    _td('tf_decomp',      'decomp_temp');
    _td('tf_vp',          'vapor_pressure');
    _td('tf_aerosol_flam_pct', 'aerosol_flam_pct');
    const _gasType = document.getElementById('sel_gas_type')?.value;
    if (_gasType) testData.gas_type = _gasType;            // SEA Ek-1 Tablo 2.5.1 alt kategorisi
    if (_gasType === 'refrigerated') testData.cryo_gas = true;   // H281
    if (phRaw) testData.ph = phRaw;
    const _evapRaw = document.getElementById('tf_evap')?.value?.trim();
    if (_evapRaw) testData.evap_rate = _evapRaw;

    // Uzman karışım test override (sonuç ekranındaki gizli panel)
    const _ovVal = id => document.getElementById(id)?.value || null;
    const ov_wr   = _ovVal('ov_wr');
    const ov_pyro = _ovVal('ov_pyro');
    const ov_sh   = _ovVal('ov_sh');
    const ov_mc   = _ovVal('ov_mc');
    const ov_op   = _ovVal('ov_op');
    if (ov_wr)   testData.water_reactive   = ov_wr;
    if (ov_pyro) testData.pyrophoric       = ov_pyro;
    if (ov_sh)   testData.self_heating     = ov_sh;
    if (ov_mc)   testData.metal_corrosive  = ov_mc;
    if (ov_op)   testData.organic_peroxide = ov_op;

    // Sağ paneldeki "Karar gerekli" yanıtları (oksitleyici test sonucu vb.).
    // Bileşen listesi değişince sıfırlanır — eski karar başka ürüne taşınmasın.
    const casKey = comps.map(c => (c.cas || '').trim()).sort().join('|');
    if (window._physDecisionsKey !== casKey) {
      window._physDecisions = {};
      window._physDecisionLabels = {};
      window._physDecisionsKey = casKey;
      window._gloveSel = null;   // eldiven seçimi de başka ürüne taşınmasın
    }
    Object.assign(testData, window._physDecisions || {});

    const formSub  = document.getElementById('pform_sub')?.value || '';
    const vocRaw   = parseFloat(document.getElementById('tf_voc')?.value);

    const payload = {
      components:  comps,
      form,
      form_sub:    formSub || null,
      user_fp:     isNaN(userFP) ? null : userFP,
      fp_status:   fpStatus || null,
      mixture_ph:  phRaw || null,
      // SEA Ek-1 Tablo 3.2.4 / 3.3.4 — KDU "toplama yöntemi uygulanamaz" dediyse (varsayılan Tablo 3.2.3 / 3.3.3)
      additivity_na: !!document.getElementById('cb_additivity_na')?.checked,
      test_data:   testData,
      usage,
      lang:        (typeof getSdsLang === 'function' ? getSdsLang() : null) || 'TR',
      voc_content: (!isNaN(vocRaw) && vocRaw >= 0) ? vocRaw : null,
      // H314 nötralizasyon diyaloğunda "Kaldır" seçildiyse (PDF akışı) panel de aynı kararla hesaplar
      h314_neutralization_removed: !!window._h314Removed,
      // Eldiven malzeme/kalınlık seçimi (KKD panelindeki eldiven kartı) — panel ve PDF aynı metni üretir
      glove_material:  (window._gloveSel && window._gloveSel.material)  || null,
      glove_thickness: (window._gloveSel && window._gloveSel.thickness) || null,
    };
    return payload;
  }

  async function _send(payload, showExtra, comps) {
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

      // Teorik fiziksel alanları forma doldur (renderResults çağrısından önce hemen uygula)
      const theoPhys = data.theo_props || {};
      if (typeof _autofillPhysFields === 'function') _autofillPhysFields(theoPhys);

      // pH değerlendirmesi (client-side yeterli — form alanı okuma)
      const phAssess = (typeof assessPH === 'function') ? assessPH(comps) : {};

      // API yanıtını CALC_COMPLETE formatına dönüştür
      const pRes = data.p_codes || {};
      // Panelin etiket kutusu bu alanları okur — API'de label.selected / label.mandatory / p_codes
      // olarak gelir; eşlenmezse panelde etiket P kodları boş görünüyordu.
      pRes.label_codes      = pRes.label?.selected  || pRes.label_codes     || [];
      pRes.label_mandatory  = pRes.label?.mandatory || pRes.label_mandatory || [];
      pRes.codes            = pRes.p_codes || pRes.codes || [];
      pRes.label_components = data.label_components || [];   // etikette adı zorunlu bileşenler
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
        ppe:        data.ppe         || {},
        theoPhys,
        phAssess,
        chipHCodes: data.h_codes    || [],   // tüm H kodları (renderResults allH olarak kullanır)
        comps,
        showExtra:  showExtra || false,
        ateDetails: data.ate_details || {},
        _source:    'python-api',   // izleme için kaynak etiketi
      };

      // Ek-6'daki maddelere ECHA bildirimlerinden eklenen (Ek-6 dışı) sınıflar — sağ panelde gösterilir
      window._lastEk6Supp = data.ek6_supplements || [];
      // Eldiven önerisi (EN ISO 374-1 harf/tip + malzeme seçenekleri + uyarılar) — KKD panelinde kart
      window._lastGlove = data.glove || {};
      _lastPayload = payload;
      _lastSummary = data.summary || null;
      StateStore.setCalcResult(result);
      EventBus.emit('CALC_COMPLETE', result);

    } catch(e) {
      // Başarısız hesapta eski sonuç "güncel" sayılmasın (PDF eski girdiyle üretilmez)
      _lastPayload = null;
      _lastSummary = null;
      console.error('[Calculator] API hatası:', e);
      EventBus.emit('CALC_ERROR', { message: e.message });
    }
  }

  // Formdaki değerler son hesaptan beri değiştiyse (veya hesap yoksa) yeniden hesapla.
  // Dönüş: PDF'e gönderilecek girdi (sağ panelin kullandığıyla birebir aynı) — hata varsa null.
  async function ensureFresh() {
    const comps = getComps();
    if (!comps.length) return null;
    const p = buildPayload(comps);
    if (!_lastPayload || JSON.stringify(p) !== JSON.stringify(_lastPayload)) {
      await run(false);
    }
    return _lastPayload;
  }

  const lastPayload = () => _lastPayload;
  const lastSummary = () => _lastSummary;

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

  return { init, run, buildPayload, ensureFresh, lastPayload, lastSummary };
})();
