/**
 * ConcSelector Module
 *
 * Dinler  : (dropdown onchange → onConcRangeChange)
 * Emit eder: CONCENTRATION_SET { id, lo, hi }
 *            CONCENTRATION_NEEDS_REFINEMENT { id, lo, hi, thresholds }
 */
const ConcSelector = (() => {

  function init() {
    // Geriye dönük uyumluluk: _crpSave global'ini EventBus ile sarmala
    const _origCrpSave = window._crpSave;
    window._crpSaveViaModule = function(id, lo, hi) {
      if (typeof _origCrpSave === 'function') _origCrpSave(id, lo, hi);
      EventBus.emit('CONCENTRATION_SET', { id, lo, hi });
    };
    console.log('[ConcSelector] init OK');
  }

  return { init };
})();
