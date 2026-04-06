/**
 * CASLookup Module
 *
 * Dinler  : (kullanıcı CAS girer → DOM event)
 * Emit eder: SUBSTANCE_FOUND { cas, name, hazard_classes, hazards, ec_no, reach_no, signal, pictograms, source }
 *            SUBSTANCE_NOT_FOUND { cas }
 */
const CASLookup = (() => {

  function _apiBase() {
    return (window.HAZARDDESK_API_URL || '/api/v1/sds/pdf')
      .replace('/sds/pdf', '');
  }

  async function lookup(cas, compId) {
    const cleanCas = (cas || '').trim();
    if (!cleanCas) return;

    try {
      const r = await fetch(`${_apiBase()}/sds/substance/lookup?cas=${encodeURIComponent(cleanCas)}`);
      if (!r.ok) {
        EventBus.emit('SUBSTANCE_NOT_FOUND', { cas: cleanCas, compId });
        return;
      }
      const data = await r.json();

      if (!data || !data.found) {
        EventBus.emit('SUBSTANCE_NOT_FOUND', { cas: cleanCas, compId });
        return;
      }

      const hazardClasses = (data.hazards || []).map(h => h.h_class).filter(Boolean);

      EventBus.emit('SUBSTANCE_FOUND', {
        cas:           cleanCas,
        compId:        compId,
        name:          data.name          || '',
        hazard_classes:hazardClasses,
        hazards:       data.hazards       || [],
        ec_no:         data.ec_no         || '',
        reach_no:      data.reach_no      || '',
        signal:        data.signal        || '',
        pictograms:    data.pictograms    || [],
        source:        data.source        || '',
        m_factors:     data.m_factors     || {},
        scl:           data.scl           || [],
      });
    } catch(e) {
      console.warn('[CASLookup] API error:', e);
      EventBus.emit('SUBSTANCE_NOT_FOUND', { cas: cleanCas, compId });
    }
  }

  // Module başlatma
  function init() {
    // Geriye dönük uyumluluk: eski echaLookup() çağrıları için
    window.echaLookupViaModule = lookup;
    console.log('[CASLookup] init OK');
  }

  return { lookup, init };
})();
