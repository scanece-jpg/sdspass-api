/**
 * EUHEngine — CLP (AT) No 1272/2008 Ek II — SDS Bölüm 15
 * EUH kodu hesaplama motoru
 * Girdi : comps[]
 * Çıktı : { codes[], details[], warnings[] }
 *
 * Events: dinler  → EUH_CALCULATE { comps }
 *         emit eder → EUH_READY { codes, details, warnings }
 */
const EUHEngine = (() => {

  // EUH kodu metinleri (Türkçe — KKDİK Ek-2)
  const EUH_TEXTS = {
    'EUH001':'Kuru hâlde patlayıcıdır.',
    'EUH006':'Havaya maruz kalma durumunda ya da kalmaksızın patlayıcıdır.',
    'EUH014':'Su ile şiddetli reaksiyon gösterir.',
    'EUH018':'Kullanım sırasında yanıcı/patlayıcı buhar-hava karışımı oluşabilir.',
    'EUH019':'Patlayıcı peroksitler oluşturabilir.',
    'EUH029':'Su ile temas hâlinde zehirli gaz açığa çıkarır.',
    'EUH031':'Asitlerle temasında zehirli gaz açığa çıkarır.',
    'EUH032':'Asitlerle temasında çok zehirli gaz açığa çıkarır.',
    'EUH044':'Kapalı alanda ısıtıldığında patlama riski.',
    'EUH059':'Ozon tabakasına zararlıdır.',
    'EUH066':'Tekrarlayan maruziyetle deri kuruluğuna veya çatlamaya yol açabilir.',
    'EUH070':'Gözle temasında zehirlidir.',
    'EUH071':'Solunum yolunu aşındırıcıdır.',
    'EUH201':'Kurşun içerir.',
    'EUH201A':'Dikkat! Kurşun içerir.',
    'EUH202':'Siyanoakrilat. Tehlike. Göz kapaklarına ve deriye saniyeler içinde yapışır.',
    'EUH203':'Krom(VI) içerir.',
    'EUH204':'İzosiyanat içerir.',
    'EUH205':'Epoksi bileşenler içerir.',
    'EUH206':'Dikkat! Diğer müstahzarlarla birlikte kullanmayın.',
    'EUH207':'Dikkat! Kadmiyum içerir.',
    'EUH208':'... içerir. Alerjik reaksiyona yol açabilir.',
    'EUH209':'Kullanım sırasında kolayca yanıcı hâle gelebilir.',
    'EUH209A':'Kullanım sırasında yanıcı hâle gelebilir.',
    'EUH210':'Güvenlik bilgi formu talep üzerine temin edilir.',
    'EUH211':'Dikkat! Potansiyel olarak tehlikeli partiküller oluşturan aerosolün solunmasından kaçının.',
    'EUH212':'Dikkat! Potansiyel olarak tehlikeli partiküller oluşturan tehlikeli kuru spreyin solunmasından kaçının.',
    'EUH401':'Çevreye zarar vermemek için kullanım talimatlarına uyunuz.',
  };

  // Belirli CAS'lar için zorunlu EUH kodları
  const CAS_TO_EUH = {
    '7681-52-9': ['EUH031'],           // Sodyum hipoklorit — asitle EUH031
    '7664-39-3': ['EUH071'],           // Hidroflorik asit
    '107-13-1':  ['EUH071'],           // Akrilonitril
    '75-21-8':   ['EUH019'],           // Etilen oksit
    '7722-84-1': ['EUH019'],           // Hidrojen peroksit
  };

  // H kodu eşlemesi bazında EUH
  const H_TO_EUH = {
    'H290': ['EUH014'],                // Metal korozifi → su ile tepkime
    'H260': ['EUH014'],
    'H261': ['EUH014'],
  };

  // Ozon tüketen CAS
  const OZONE_CAS = new Set([
    '75-69-4','75-71-8','76-13-1','76-14-2','75-72-9',
    '75-63-8','74-83-9','74-87-3','56-23-5','67-66-3','79-01-6',
  ]);

  function calculate(comps) {
    const codes = new Set();
    const details = [];
    const warnings = [];

    for (const c of comps) {
      const cas = (c.cas || '').trim();
      const conc = parseFloat(c.concMax || c.conc) || 0;
      const name = c.name || cas;

      // CAS'a özel EUH kodları
      if (CAS_TO_EUH[cas]) {
        CAS_TO_EUH[cas].forEach(code => {
          if (!codes.has(code)) {
            codes.add(code);
            details.push({ code, text: EUH_TEXTS[code] || code, source: `${name} (CAS: ${cas})`, type:'auto' });
          }
        });
      }

      // H kodu bazlı EUH
      for (const h of (c.hazards || [])) {
        const hcode = (h.h_code || '').replace(/[*\s]/g,'').substring(0,4);
        if (H_TO_EUH[hcode]) {
          H_TO_EUH[hcode].forEach(euhCode => {
            if (!codes.has(euhCode)) {
              codes.add(euhCode);
              details.push({ code: euhCode, text: EUH_TEXTS[euhCode] || euhCode, source: `${name} — ${hcode}`, type:'auto' });
            }
          });
        }
      }

      // Ozon tüketen maddeler
      if (OZONE_CAS.has(cas) && conc >= 0.1) {
        if (!codes.has('EUH059')) {
          codes.add('EUH059');
          details.push({ code:'EUH059', text: EUH_TEXTS['EUH059'], source: `${name} (CAS: ${cas})`, type:'auto' });
        }
      }

      // EUH208 — duyarlılaştırıcı içerik
      const hasSensitizer = (c.hazards || []).some(h =>
        ['H317','H334'].includes((h.h_code||'').replace(/[*\s]/g,'').substring(0,4))
      );
      if (hasSensitizer && conc >= 0.1) {
        if (!codes.has('EUH208')) {
          codes.add('EUH208');
          details.push({
            code:'EUH208',
            text: EUH_TEXTS['EUH208'].replace('...', name),
            source: `${name} — H317/H334 duyarlılaştırıcı, %${conc} ≥ %0.1 eşik`,
            type:'auto',
          });
        }
      }
    }

    // EUH210 — tehlikeli sınıflandırma varsa SDS zorunlu
    if (comps.some(c => (c.hazards || []).length > 0)) {
      codes.add('EUH210');
      details.push({ code:'EUH210', text: EUH_TEXTS['EUH210'], source:'Tehlikeli madde içeren karışım', type:'advisory' });
    }

    return {
      codes: [...codes],
      euh_codes: [...codes],
      details,
      euh_details: details,
      warnings,
    };
  }

  function init() {
    if (typeof EventBus !== 'undefined') {
      EventBus.on('EUH_CALCULATE', ({ comps }) => {
        const result = calculate(comps);
        EventBus.emit('EUH_READY', result);
      });
    }
    console.log('[EUHEngine] init OK');
  }

  return { init, calculate };
})();
