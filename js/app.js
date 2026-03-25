/**
 * App — Uygulama başlatma ve modül koordinasyonu
 */
(function initApp() {
  // Modülleri başlat
  CASLookup.init();
  ComponentManager.init();
  ConcSelector.init();
  CalculatorModule.init();
  ResultsRenderer.init();
  PDFExporter.init();

  // Mevcut global calculate() fonksiyonunu EventBus üzerinden çalıştır
  // Geriye dönük uyumluluk: HTML'deki onclick="calculate()" çalışmaya devam eder
  const _origCalculate = window.calculate;
  window.calculate = function(showExtra) {
    // Önce orijinal fonksiyonu çalıştır (mevcut davranışı koru)
    if (typeof _origCalculate === 'function') {
      _origCalculate(showExtra);
    }
    // EventBus'a da bildir (yeni modüller dinleyebilir)
    // Not: CALC_COMPLETE, calculate() içinde renderResults çağrıldıktan sonra emit edilecek
  };

  // CAS lookup: eski echaLookup() → CASLookup.lookup()
  const _origEchaLookup = window.echaLookup;
  window.echaLookup = function(casInput, compId) {
    // Eski implementasyonu çalıştır (geriye dönük uyumluluk)
    if (typeof _origEchaLookup === 'function') {
      _origEchaLookup(casInput, compId);
    }
  };

  console.log('[App] HazardDesk modüler mimari aktif');
  console.log('[App] EventBus olayları için: EventBus.debug()');
})();
