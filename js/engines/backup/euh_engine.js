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
    // EUH019 — Patlayıcı peroksit oluşturanlar
    '75-21-8':   ['EUH019'],           // Etilen oksit
    '7722-84-1': ['EUH019'],           // Hidrojen peroksit
    '109-99-9':  ['EUH019'],           // Tetrahidrofuran (THF)
    '123-91-1':  ['EUH019'],           // 1,4-Dioksan
    '60-29-7':   ['EUH019'],           // Dietil eter
    '108-20-3':  ['EUH019'],           // Diizopropil eter
    '107-30-2':  ['EUH019'],           // Klorometil metil eter

    // EUH029 — Su ile temas → zehirli gaz (PH3, AsH3, vb.)
    '20859-73-8':['EUH029'],           // Alüminyum fosfür → PH3
    '1314-84-7': ['EUH029'],           // Çinko fosfür → PH3
    '12057-74-8':['EUH029'],           // Magnezyum fosfür → PH3
    '10124-50-2':['EUH029'],           // Potasyum arsenat → AsH3 riski
    '26628-22-8':['EUH029','EUH032'],  // Sodyum azit → HN3

    // EUH031 — Asitlerle temas → zehirli gaz (SO2, H2S, HCN, vb.)
    '7681-52-9': ['EUH031'],           // Sodyum hipoklorit → Cl2
    '7757-83-7': ['EUH031'],           // Sodyum sülfit → SO2
    '1313-82-2': ['EUH031'],           // Sodyum sülfür → H2S
    '1312-73-8': ['EUH031'],           // Potasyum sülfür → H2S
    '16721-80-5':['EUH031'],           // Sodyum hidrosülfür → H2S
    '1317-37-9': ['EUH031'],           // Demir(II) sülfür → H2S

    // EUH032 — Asitlerle temas → çok zehirli gaz (HCN, PH3, vb.)
    '143-33-9':  ['EUH032'],           // Sodyum siyanür → HCN
    '151-50-8':  ['EUH032'],           // Potasyum siyanür → HCN
    '592-01-8':  ['EUH032'],           // Kalsiyum siyanür → HCN
    '460-19-5':  ['EUH032'],           // Siyanür → HCN (genel)
    '20859-73-8':['EUH029','EUH032'],  // Alüminyum fosfür (zaten EUH029'da)

    // EUH066 — Tekrarlayan maruziyet → deri kuruluğu/çatlama
    '110-54-3':  ['EUH066'],           // n-Hekzan
    '142-82-5':  ['EUH066'],           // n-Heptan
    '110-82-7':  ['EUH066'],           // Siklohekzan
    '108-87-2':  ['EUH066'],           // Metilsiklohekzan
    '8052-41-3': ['EUH066'],           // Stoddard solvent / White spirit
    '64742-82-1':['EUH066'],           // Nafta (hafif aromatik)
    '64742-89-8':['EUH066'],           // Nafta (hafif alifatik)

    // EUH071 — Solunum yolunu aşındırıcı
    '7664-39-3': ['EUH071'],           // Hidroflorik asit
    '107-13-1':  ['EUH071'],           // Akrilonitril
    '75-44-5':   ['EUH071'],           // Fosgen

    // EUH201 / EUH201A — Kurşun içeriği
    '7439-92-1': ['EUH201'],           // Kurşun (element)
    '1317-36-8': ['EUH201'],           // Kurşun(II) oksit
    '7446-14-2': ['EUH201'],           // Kurşun(II) sülfat
    '301-04-2':  ['EUH201'],           // Kurşun(II) asetat
    '1344-37-2': ['EUH201'],           // Kurşun kromat
    '78-00-2':   ['EUH201'],           // Tetraetilkurşun
    '75-74-1':   ['EUH201'],           // Tetrametilkurşun

    // EUH202 — Siyanoakrilat yapıştırıcılar
    '7085-85-0': ['EUH202'],           // Etil siyanoakrilat
    '137-05-3':  ['EUH202'],           // Metil siyanoakrilat
    '133978-15-1':['EUH202'],          // Oktil siyanoakrilat
    '1069-48-3': ['EUH202'],           // Butil siyanoakrilat

    // EUH203 — Krom(VI)
    '1333-82-0': ['EUH203'],           // Krom trioksit (CrO3)
    '7778-50-9': ['EUH203'],           // Potasyum dikromat
    '10588-01-9':['EUH203'],           // Sodyum dikromat
    '7789-00-6': ['EUH203'],           // Potasyum kromat
    '7789-09-5': ['EUH203'],           // Amonyum dikromat
    '13530-65-9':['EUH203'],           // Çinko kromat
    '1189-85-1': ['EUH203'],           // tert-Butil kromat

    // EUH207 — Kadmiyum
    '7440-43-9': ['EUH207'],           // Kadmiyum (element)
    '1306-19-0': ['EUH207'],           // Kadmiyum oksit
    '1306-23-6': ['EUH207'],           // Kadmiyum sülfür
    '10108-64-2':['EUH207'],           // Kadmiyum klorür
    '10124-36-4':['EUH207'],           // Kadmiyum sülfat
    '543-90-8':  ['EUH207'],           // Kadmiyum asetat
  };

  // H kodu eşlemesi bazında EUH
  const H_TO_EUH = {
    'H290': ['EUH014'],                // Metal korozifi → su ile tepkime
    'H260': ['EUH014'],
    'H261': ['EUH014'],
  };

  // İsim bazlı tespitler (CAS bilinmese de bileşen adından tetiklenir)
  // Kaynak: CLP (AT) No 1272/2008 Ek II
  const NAME_PATTERNS = [
    { pattern: /izosiyanat|isocyanate/i,      code: 'EUH204' },
    { pattern: /epoksi|epoxy|bisfenol|bisphenol/i, code: 'EUH205' },
    { pattern: /hipoklorit|hypochlorite/i,    code: 'EUH031' },
    { pattern: /sülfür|sülfid|sulfide|sulphide/i, code: 'EUH031' },
    { pattern: /siyanür|cyanide/i,            code: 'EUH032' },
    { pattern: /fosfür|phosphide/i,           code: 'EUH029' },
  ];

  // Ozon tüketen CAS
  const OZONE_CAS = new Set([
    '75-69-4','75-71-8','76-13-1','76-14-2','75-72-9',
    '75-63-8','74-83-9','74-87-3','56-23-5','67-66-3','79-01-6',
  ]);

  function calculate(comps) {
    const codes = new Set();
    const details = [];
    const warnings = [];

    // ── EUH209 / EUH209A ön-kontrol ──────────────────────────────────────────
    // CLP Ek II §2.9: EUH209 yalnızca karışım H224/H225 ALMIYORSA geçerlidir.
    // Karışımda ≥%1 H224/H225 bileşen varsa → karışım zaten H225 sınıfına girer
    // → EUH209 UYGULANMAZ (zaten yanıcı sınıfında).
    // Benzer şekilde EUH209A: ≥%10 H226 bileşen varsa → karışım H226 alır → EUH209A yok.
    const _flamH12 = h => { const c = (h.h_code||'').replace(/[*\s]/g,'').substring(0,4); return c==='H224'||c==='H225'; };
    const _flamH3  = h => (h.h_code||'').replace(/[*\s]/g,'').substring(0,4) === 'H226';
    const mixAlreadyFlam12 = comps.some(c =>
      (parseFloat(c.concMax||c.conc)||0) >= 1.0 && (c.hazards||[]).some(_flamH12)
    );
    const mixAlreadyFlam3  = comps.some(c =>
      (parseFloat(c.concMax||c.conc)||0) >= 10.0 && (c.hazards||[]).some(_flamH3)
    );

    const sensitizerNames = [];  // EUH208: tüm sensitizer adları toplanır

    for (const c of comps) {
      const cas = (c.cas || '').trim();
      const conc = parseFloat(c.concMax || c.conc) || 0;
      const name = c.name_tr || c.name || cas;  // Türkçe isim öncelikli

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

      // EUH209 / EUH209A — CLP Ek II §2.9 / §2.10
      // Koşul: bileşen eşik altında FAKAT karışım H224/H225 sınıfına GİRMİYORSA
      // (mixAlreadyFlam12/3 ön-kontrolünde bu durum tespit edilir)
      const flamCodes = (c.hazards || []).map(h => (h.h_code||'').replace(/[*\s]/g,'').substring(0,4));
      if (!codes.has('EUH209') && !mixAlreadyFlam12 &&
          (flamCodes.includes('H224') || flamCodes.includes('H225')) &&
          conc >= 0.1 && conc < 1.0) {
        codes.add('EUH209');
        details.push({ code:'EUH209', text: EUH_TEXTS['EUH209'], source: `${name} — H224/H225, %${conc} (eşik altı yanıcı bileşen)`, type:'auto' });
      }
      // EUH209A: yalnızca karışım H224/H225/H226 ALMIYORSA geçerlidir (CLP Ek II §2.10)
      if (!codes.has('EUH209A') && !mixAlreadyFlam12 && !mixAlreadyFlam3 &&
          flamCodes.includes('H226') && conc >= 1.0 && conc < 10.0) {
        codes.add('EUH209A');
        details.push({ code:'EUH209A', text: EUH_TEXTS['EUH209A'], source: `${name} — H226, %${conc} (eşik altı yanıcı bileşen)`, type:'auto' });
      }

      // İsim bazlı tespitler (EUH204, EUH205 vb.)
      for (const { pattern, code } of NAME_PATTERNS) {
        if (pattern.test(name) && !codes.has(code)) {
          codes.add(code);
          details.push({ code, text: EUH_TEXTS[code] || code, source: `${name} — isim eşleşmesi`, type:'auto' });
        }
      }

      // Ozon tüketen maddeler
      if (OZONE_CAS.has(cas) && conc >= 0.1) {
        if (!codes.has('EUH059')) {
          codes.add('EUH059');
          details.push({ code:'EUH059', text: EUH_TEXTS['EUH059'], source: `${name} (CAS: ${cas})`, type:'auto' });
        }
      }

      // EUH208 — CLP Ek II §2.8 Para 2: "sınıflandırmaya yol açanın EK OLARAK" kuralı
      // Skin Sens. sınıflandırmasına neden olan madde (konc ≥ Skin Sens GCL/SCL) EUH208'e girmez;
      // zaten H317 tehlike ifadesiyle etikette yer alır.
      // EUH208: yalnızca H317 için eşik altı kalan (ama ≥%0.1) ek sensitizerlar listelenir.
      const hasRespSens = (c.hazards || []).some(h =>
        (h.h_code||'').replace(/[*\s]/g,'').substring(0,4) === 'H334'
      );
      const hasSkinSens = (c.hazards || []).some(h =>
        (h.h_code||'').replace(/[*\s]/g,'').substring(0,4) === 'H317'
      );

      if (hasRespSens || hasSkinSens) {
        // Skin Sens. sınıflandırma eşiği: SCL varsa kullan, yoksa kategori bazlı GCL
        // CLP Ek I Tablo 3.4.3: Skin Sens. 1A → GCL=%0.1 | Skin Sens. 1B / 1 → GCL=%1.0
        const skinSensHazard = (c.hazards || []).find(h =>
          (h.h_code||'').replace(/[*\s]/g,'').substring(0,4) === 'H317'
        );
        const skinSensClass = (skinSensHazard && (skinSensHazard.h_class || skinSensHazard.class || '')) || '';
        // 1A ise GCL=0.1, diğer tüm durumlar (1B, 1, belirtilmemiş) → GCL=1.0
        let skinClassThreshold = /1A/i.test(skinSensClass) ? 0.1 : 1.0;
        if (hasSkinSens) {
          // scl iki formatta gelebilir:
          //   Object (getComps): { H317: 0.5, H314: 2.0 }  ← _sclMap
          //   Array  (API):      [{h_code:'H317', c_min:0.5}, ...]  ← _sclRaw
          if (Array.isArray(c.scl)) {
            for (const s of c.scl) {
              const sh = (s.h_code || '').replace(/[*\s]/g,'').substring(0,4);
              if (sh === 'H317' && s.c_min != null) { skinClassThreshold = s.c_min; break; }
            }
          } else if (c.scl && typeof c.scl === 'object' && c.scl['H317'] != null) {
            skinClassThreshold = c.scl['H317'];
          }
        }
        // Madde H317 sınıflandırmasına neden oluyor mu?
        const causesSkinClass = hasSkinSens && conc >= skinClassThreshold;

        // EUH208'e dahil: sınıflandırmaya neden olmayan sensitizerlar (≥%0.1)
        if (!causesSkinClass && conc >= 0.1) {
          if (!sensitizerNames.includes(name)) sensitizerNames.push(name);
        }
      }
    }

    // EUH208 — tüm sensitizerlar toplandıktan sonra tek ifade oluştur
    if (sensitizerNames.length > 0) {
      codes.add('EUH208');
      const allNames = sensitizerNames.join('; ');
      details.push({
        code: 'EUH208',
        text: EUH_TEXTS['EUH208'].replace('...', allNames),
        source: `${allNames} — H317/H334, ≥%0.1 eşik`,
        type: 'auto',
      });
    }

    // EUH210 — CLP Ek II §2.10: YALNIZCA tehlikeli sınıflandırılmamış karışımlar için
    // REACH Madde 31(1): Tehlikeli sınıflandırılmış karışımlarda SDS otomatik verilmeli
    // → tehlikeli karışımlarda EUH210 UYGULANMAZ (sanayi/mesleki kullanım için yanıltıcıdır)
    // Bu sistem tehlikeli kimyasallar içindir; EUH210 otomatik olarak EKLENMEMELİDİR.
    // (Tamamen tehlikesiz karışımlara EUH210 eklenebilir — ancak bu sistem kapsamı dışı)

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
