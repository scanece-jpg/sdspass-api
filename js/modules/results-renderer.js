/**
 * ResultsRenderer Module
 *
 * Dinler  : CALC_COMPLETE → sonuçları render et
 *           CALC_ERROR    → hata mesajı göster
 *           CALC_TOTAL_CONC → %100 uyarısı
 */
const ResultsRenderer = (() => {

  function init() {
    EventBus.on('CALC_COMPLETE', result => render(result));
    EventBus.on('CALC_ERROR',   ({ message }) => renderErr(message));
    EventBus.on('CALC_TOTAL_CONC', ({ total }) => {
      const warn = document.getElementById('pct-warning');
      if (!warn) return;
      if (total > 100.05) {
        warn.style.display = 'flex';
        warn.textContent = `⚠ Toplam konsantrasyon %${total.toFixed(1)} — %100'ü aşıyor!`;
      } else {
        warn.style.display = 'none';
      }
    });
    console.log('[ResultsRenderer] init OK');
  }

  function render(result) {
    const { hCodes, signal, stot, euh, pRes, eco, phys, phAssess, theoPhys,
            chipHCodes, comps, showExtra, transport, ppe, pictograms, clpPassed } = result;

    // theoPhys'ı phys nesnesine göm (renderAll phys.theoProps olarak bekler)
    const physWithTheo = Object.assign({}, phys || {}, { theoProps: theoPhys || null });

    // renderResults global fonksiyonunu çağır (mevcut implementasyon)
    renderResults(
      euh,
      physWithTheo,
      stot,
      eco,
      pRes,
      comps,
      showExtra || false,
      [...new Set(chipHCodes || [])],
      transport   || null,
      ppe         || {},
      signal      || 'None',
      pictograms  || [],
      clpPassed   || []
    );
  }

  return { init, render };
})();
