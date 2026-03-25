/**
 * StateStore — Uygulama durumu tek kaynağı
 *
 * State yapısı:
 *   components[]     → bileşen listesi
 *   calcResult       → son hesaplama sonucu
 *   product          → ürün bilgileri
 *   disclosureMap    → CAS gizleme haritası
 */
const StateStore = (() => {
  let _state = {
    components: [],          // [{id,cas,name,conc,concMin,concMax,hazards,ec,reach}]
    calcResult: null,        // { hCodes, signal, pictograms, stot, euh, pCodes, eco, clpPassed, phys }
    product: {},             // { name, code, form, usage, ... }
    disclosureMap: {},       // { cas: 'show'|'range'|'hide' }
    uiLang: 'TR',            // arayüz dili
    sdsLang: 'TR',           // SDS PDF dili
  };

  // ── Bileşenler ──────────────────────────────────────────────────────────────

  function getComponents() {
    return _state.components.slice();
  }

  function setComponents(comps) {
    _state.components = comps;
    EventBus.emit('COMPONENT_CHANGED', { components: comps });
  }

  function updateComponent(id, patch) {
    _state.components = _state.components.map(c =>
      c.id === id ? { ...c, ...patch } : c
    );
    EventBus.emit('COMPONENT_CHANGED', { components: _state.components });
  }

  // ── Hesaplama Sonucu ────────────────────────────────────────────────────────

  function setCalcResult(result) {
    _state.calcResult = result;
    // window._ değişkenlerini geriye dönük uyumluluk için koru
    window._lastHCodes     = result.hCodes     || [];
    window._lastSignal     = result.signal     || '';
    window._lastEuhCodes   = result.euhCodes   || [];
    window._lastEuhDetails = result.euhDetails || [];
    window._lastPCodes     = result.pCodes     || [];
    window._lastClpPassed  = result.clpPassed  || [];
    window._lastTheoPhys   = result.theoPhys   || {};
    window._lastPHAssessment = result.phAssess || null;
  }

  function getCalcResult() {
    return _state.calcResult;
  }

  // ── Ürün ────────────────────────────────────────────────────────────────────

  function setProduct(product) {
    _state.product = product;
  }

  function getProduct() {
    return { ..._state.product };
  }

  // ── Gizleme Haritası ────────────────────────────────────────────────────────

  function setDisclosure(cas, level) {
    _state.disclosureMap[cas] = level;
    EventBus.emit('DISCLOSURE_CHANGED', { cas, level, map: { ..._state.disclosureMap } });
  }

  function getDisclosureMap() {
    return { ..._state.disclosureMap };
  }

  // ── Dil ────────────────────────────────────────────────────────────────────

  function setUILang(lang) {
    _state.uiLang = lang;
  }

  function setSdsLang(lang) {
    _state.sdsLang = lang;
    EventBus.emit('SDS_LANG_CHANGED', { lang });
  }

  function getSdsLang() {
    return _state.sdsLang;
  }

  // ── Genel ───────────────────────────────────────────────────────────────────

  function getState() {
    return { ..._state };
  }

  function reset() {
    _state.components = [];
    _state.calcResult = null;
    EventBus.emit('STATE_RESET', {});
  }

  return {
    getComponents, setComponents, updateComponent,
    setCalcResult, getCalcResult,
    setProduct, getProduct,
    setDisclosure, getDisclosureMap,
    setUILang, setSdsLang, getSdsLang,
    getState, reset,
  };
})();
