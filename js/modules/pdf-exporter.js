/**
 * PDFExporter Module
 *
 * Dinler  : CALC_COMPLETE → PDF butonu aktif et, state'i sakla
 *           PDF_REQUESTED  → PDF oluştur ve indir
 */
const PDFExporter = (() => {

  function init() {
    EventBus.on('CALC_COMPLETE', _onCalcComplete);
    EventBus.on('PDF_REQUESTED', _onPdfRequested);
    EventBus.on('SDS_LANG_CHANGED', ({ lang }) => {
      setSdsLang(lang);  // mevcut global fonksiyon
    });
    console.log('[PDFExporter] init OK');
  }

  function _onCalcComplete(result) {
    // PDF butonu aktif — mevcut state zaten window._ değişkenlerinde
    const btn = document.querySelector('.btn-pdf');
    if (btn) btn.disabled = false;
  }

  function _onPdfRequested() {
    // Mevcut showSdsModal() global fonksiyonunu çağır
    if (typeof showSdsModal === 'function') showSdsModal();
  }

  return { init };
})();
