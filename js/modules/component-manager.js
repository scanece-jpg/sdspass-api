/**
 * ComponentManager Module
 *
 * Dinler  : SUBSTANCE_FOUND     → bileşen kartını doldur
 *           SUBSTANCE_NOT_FOUND → uyarı göster
 *           CONCENTRATION_SET   → hidden input'ları güncelle
 * Emit eder: COMPONENT_ADDED { id }
 *            COMPONENT_REMOVED { id }
 */
const ComponentManager = (() => {

  function init() {
    EventBus.on('SUBSTANCE_FOUND', _onSubstanceFound);
    EventBus.on('SUBSTANCE_NOT_FOUND', _onSubstanceNotFound);
    EventBus.on('CONCENTRATION_SET', _onConcentrationSet);
    console.log('[ComponentManager] init OK');
  }

  function _onSubstanceFound({ cas, compId, name, hazard_classes, ec_no, reach_no, signal, source, annex_vi }) {
    // Madde adını doldur
    const ni = document.getElementById(`ni${compId}`);
    if (ni && !ni.value && name) ni.value = name;

    // Hazard chip'lerini ekle
    if (hazard_classes && hazard_classes.length > 0) {
      hazard_classes.forEach(hc => { if (hc) addChip(compId, hc, ''); });
    }

    // EC No
    const ecInput = document.getElementById('ec' + compId);
    if (ecInput && ec_no && !ecInput.value) {
      ecInput.value = ec_no;
      ecInput.style.borderColor = 'var(--accent)';
    }

    // REACH No
    const reachInput = document.getElementById('reach' + compId);
    if (reachInput && reach_no && !reachInput.value) {
      reachInput.value = reach_no;
    }

    // Bayrak rengi + Annex VI bayrağı (ATE revize formülü için DOM'da sakla)
    const card = document.getElementById('cc' + compId);
    if (card) {
      card.classList.remove('fe', 'fn', 'fs');
      if (source === 'Annex VI') card.classList.add('fn');
      else if (source === 'Custom DB' || source === 'ECHA C&L') card.classList.add('fs');
      card.dataset.annexVi = annex_vi ? '1' : '0';
    }
  }

  function _onSubstanceNotFound({ cas, compId }) {
    const card = document.getElementById('cc' + compId);
    if (card) card.classList.add('fe');
  }

  function _onConcentrationSet({ id, lo, hi }) {
    const minEl = document.getElementById('cmin' + id);
    const maxEl = document.getElementById('cmax' + id);
    if (minEl) minEl.value = lo > 0 ? lo : 0;
    if (maxEl) maxEl.value = hi;
  }

  return { init };
})();
