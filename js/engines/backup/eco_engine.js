/**
 * EcoEngine — CLP (AT) No 1272/2008 Ek I §4.1 — SDS Bölüm 12
 * Girdi : comps[] + ecoTestData{}
 * Çıktı : { aquatic, ozone, pbt, h_codes[] }
 *
 * Events: dinler  → ECO_CALCULATE { comps }
 *         emit eder → ECO_READY { aquatic, ozone, pbt, h_codes }
 */
const EcoEngine = (() => {

  const LOG_KOW_DB = {
    '110-54-3':3.29,'110-82-7':3.44,'108-88-3':2.73,'1330-20-7':3.12,
    '71-43-2':2.13,'100-41-4':3.15,'64-17-5':-0.31,'67-63-0':0.05,
    '71-36-3':0.88,'67-64-1':-0.24,'111-76-2':0.83,'50-00-0':0.35,
    '7681-52-9':-3.4,'7732-18-5':-1.38,'64742-54-7':7.0,'64742-47-8':4.5,
  };
  const READILY_BIO = new Set(['64-17-5','67-63-0','71-23-8','71-36-3','67-64-1',
    '78-93-3','141-78-6','7732-18-5','57-55-6','56-81-5','77-92-9','64-19-7']);
  const PERSISTENT = new Set(['1330-20-7','108-88-3','110-54-3','71-43-2','100-41-4']);
  // OZONE_CAS — EUH059/H420; ecological_service.py ile senkron (14 CAS)
  const OZONE_CAS  = new Set([
    '75-69-4','75-71-8','76-13-1','76-14-2','76-15-3',  // CFC-11/12/113/114/115
    '75-72-9','75-63-8',                                 // CFC-13, halon-1301
    '74-83-9','74-87-3',                                 // CH3Br, CH3Cl
    '56-23-5','67-66-3','79-01-6',                       // CCl4, CHCl3, TCE
    '353-59-3','354-23-4',                               // halon-1211, HCFC-22
  ]);
  // PBT_CAS — ECHA SVHC listesi; ecological_service.py ile senkron (16 CAS)
  const PBT_CAS    = new Set([
    '57-74-9','319-84-6','319-85-7','58-89-9',           // chlordane, HCH türevleri, lindane
    '72-54-8','50-29-3','76-44-8',                        // DDD, heptachlor, hexachlorobutadiene
    '118-74-1','87-68-3',                                 // hexachlorobenzene, hexachlorobutadiene
    '757-58-4','36355-01-8','67774-32-7',                 // TEPA, PFOS, PFOA türevleri
    '72629-94-8','1163-19-5',                             // deca-BDE, deca-BDE türevleri
    '68920-70-7','85535-84-8',                            // SCCP, MCCP
  ]);

  function ec50ToMfactor(ec50) {
    if (ec50 <= 0.01) return 1000;
    if (ec50 <= 0.1)  return 100;
    if (ec50 <= 1.0)  return 10;
    return 1;
  }

  function calculate(comps, ecoTestData = {}) {
    const h_codes = [];
    // SEA/CLP Tablo 4.1.2 — Python ecological_service.py ile aynı formül
    // CLP formülü (Ci yüzde): Σ(Ci × Mi) ≥ 25 → Ci/100 kesir olduğundan eşik 0.25
    // sumAcuteM    = Σ(Ci × M_acute)   / 100  → H400: ≥ 0.25 (= %25)
    // sumChronicK1 = Σ(Ci × M_chronic) / 100  (K1: Chronic 1, M-faktörlü)
    // sumChronicK2 = Σ(Ci)             / 100  (K2: Chronic 2, M=1)
    // sumChronicK3 = Σ(Ci)             / 100  (K3: Chronic 3+4, M=1)
    // H410: sumChronicK1 ≥ 0.25 (= %25)
    // H411: 10×sumChronicK1 + sumChronicK2 ≥ 0.25
    // H412: 100×sumChronicK1 + 10×sumChronicK2 + sumChronicK3 ≥ 0.25
    let sumAcuteM = 0, sumChronicK1 = 0, sumChronicK2 = 0, sumChronicK3 = 0;
    const ozone=[], pbt=[];

    for (const c of comps) {
      const cas  = (c.cas || '').trim();
      const conc = parseFloat(c.concMax || c.conc) || 0;
      if (conc <= 0) continue;

      const mAcute   = (c.m_factors?.acute)   || 1;
      const mChronic = (c.m_factors?.chronic)  || 1;

      // Bileşenin tüm sucul tehlike kodlarını bir kez topla.
      // Spinosad gibi maddeler hazard listesinde hem H400 hem H410 taşıyabilir;
      // satır bazlı döngü çift sayıma yol açar — bileşen bazlı Set ile önlenir.
      const hazSet = new Set();
      for (const h of (c.hazards || [])) {
        const code = (h.h_code || '').replace(/[*\s]/g,'').substring(0,4);
        if (['H400','H410','H411','H412','H413'].includes(code)) hazSet.add(code);
      }

      // H410 (Aquatic Chronic 1) — hem akut hem kronik hesaba girer.
      // Dahil etme eşiği: ≥ %0.1 / M_kronik
      // H410 varsa H400 satırını atla: H410 zaten akut katkıyı kapsar (çift sayım önleme)
      if (hazSet.has('H410')) {
        if (conc >= (0.1 / Math.max(mChronic, 1))) {
          sumAcuteM    += (conc * mAcute)   / 100;
          sumChronicK1 += (conc * mChronic) / 100;
        }
      } else if (hazSet.has('H400')) {
        // H400 (Aquatic Acute 1) — sadece H410 yoksa; dahil etme eşiği: ≥ %0.1 / M_akut
        if (conc >= (0.1 / Math.max(mAcute, 1))) {
          sumAcuteM += (conc * mAcute) / 100;
        }
      }

      // H411 (Aquatic Chronic 2) — dahil etme eşiği: ≥ %1.0 (düz, M-faktörsüz)
      if (hazSet.has('H411') && conc >= 1.0) {
        sumChronicK2 += conc / 100;
      }

      // H412/H413 (Aquatic Chronic 3/4) — dahil etme eşiği: ≥ %1.0 (düz)
      if ((hazSet.has('H412') || hazSet.has('H413')) && conc >= 1.0) {
        sumChronicK3 += conc / 100;
      }

      if (OZONE_CAS.has(cas) && conc >= 0.1) ozone.push({ name: c.name || cas, cas, conc });
      if (PBT_CAS.has(cas)   && conc >= 0.1) pbt.push(  { name: c.name || cas, cas, conc });
    }

    // ── SEA Tablo 4.1.2 — Kronik önce, akut sonra (H410 baskınlık kuralı) ──────
    const h411Sum = 10 * sumChronicK1 + sumChronicK2;
    const h412Sum = 100 * sumChronicK1 + 10 * sumChronicK2 + sumChronicK3;
    const h413Sum = sumChronicK1 + sumChronicK2 + sumChronicK3; // düz toplam

    // CLP Ek-I Tablo 4.1.2 — eşik %25; K değerleri Ci/100 kesire çevrildiğinden
    // karşılaştırma 0.25 (= 25/100) ile yapılır.
    let aquatic = null;
    if      (sumChronicK1 >= 0.25) aquatic = { h:'H410', cls:'Aquatic Chronic 1', formula:`Σ(Ci×M_kr)/100=${sumChronicK1.toFixed(4)} ≥ 0.25 [=%${(sumChronicK1*100).toFixed(2)}≥%25]` };
    else if (h411Sum      >= 0.25) aquatic = { h:'H411', cls:'Aquatic Chronic 2', formula:`10×K1+K2=${h411Sum.toFixed(4)} ≥ 0.25` };
    else if (h412Sum      >= 0.25) aquatic = { h:'H412', cls:'Aquatic Chronic 3', formula:`100×K1+10×K2+K3=${h412Sum.toFixed(4)} ≥ 0.25` };
    else if (h413Sum      >= 0.25) aquatic = { h:'H413', cls:'Aquatic Chronic 4', formula:`Σ(Ci tüm kronik)/100=${h413Sum.toFixed(4)} ≥ 0.25` };

    if (aquatic) h_codes.push(aquatic.h);

    // H400: H410 atanmamışsa ve akut eşik aşılmışsa
    // Baskınlık kuralı: H410 varsa H400 eklenmez (H410 zaten akut riski kapsar)
    const hasH410 = h_codes.includes('H410');
    let aquatic_acute = null;
    if (sumAcuteM >= 0.25 && !hasH410) {
      if (!h_codes.includes('H400')) h_codes.push('H400');
      aquatic_acute = {
        h: 'H400',
        cls: 'Aquatic Acute 1',
        formula: `Σ(Ci×M_ak)/100=${sumAcuteM.toFixed(4)} ≥ 0.25 [=%${(sumAcuteM*100).toFixed(2)}≥%25] (SEA Tablo 4.1.1)`,
      };
    }

    if (ozone.length) h_codes.push('H420');

    return { aquatic, aquatic_acute, ozone, pbt, h_codes };
  }

  function init() {
    if (typeof EventBus !== 'undefined') {
      EventBus.on('ECO_CALCULATE', ({ comps }) => {
        const result = calculate(comps);
        EventBus.emit('ECO_READY', result);
      });
    }
    console.log('[EcoEngine] init OK');
  }

  return { init, calculate };
})();
