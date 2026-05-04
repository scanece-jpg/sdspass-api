/**
 * CLPEngine — KKDİK Ek-2 / CLP (AT) No 1272/2008
 * Girdi : comps[] = [{ cas, name, conc, concMin, concMax, hazards:[{h_class,h_code}] }]
 * Çıktı : { hCodes[], signal, pictograms[], dominated[] }
 *
 * Events: dinler  → CLP_CALCULATE { comps, ph }
 *         emit eder → H_CODES_READY { hCodes, signal, pictograms, dominated }
 */
const CLPEngine = (() => {

  // ── CLP Annex I Kesme Değerleri ──────────────────────────────────────────────
  // NOT: H300-H332 (Akut Toksisite) GCL ile değil, SEA Tablo 3.1.2 ATE formülü
  // ile sınıflandırılır (bkz. ATE_POINT / calculateATE). GCL buradan çıkarıldı.
  const CUTOFFS = {
    // H314: CLP Tablo 3.2.3 bireysel GCL = %5 (eski 1.0 yanlıştı; toplamsal da %5)
    // H318: CLP Tablo 3.3.3 bireysel GCL = %3 (eski 1.0 yanlıştı; toplamsal da %3)
    'H314':5.0,'H315':10.0,'H318':3.0,'H319':10.0,
    'H317':1.0,'H334':0.1,
    'H340':0.1,'H341':1.0,
    'H350':0.1,'H351':1.0,
    // H360/H362: SEA Tablo 3.7.2 GCL = %0.3; H361: %3
    'H360':0.3,'H361':3.0,'H362':0.3,
    'H370':10.0,'H371':10.0,'H372':1.0,'H373':10.0,
    'H335':20.0,'H336':20.0,
    'H304':10.0,
    // H400-H413 → EcoEngine'de M-faktörlü toplamlı yöntem (Annex V §4.1.2) — burada yok
  };

  // ── SEA/CLP Tablo 3.1.2 — ATE Nokta Tahminleri ──────────────────────────────
  // Karışım ATE formülünde (100/ATEmix = Σ Ci/ATEi) kullanılacak bileşen değerleri.
  // 2000 mg/kg Kat.4 üst SINIRIDIR; formülde kullanılan NOKTA TAHMİNİ 500 mg/kg'dır.
  const ATE_POINT = {
    // Oral (Ağız yolu) mg/kg
    'H300':  0.5,   // Kat. 1 (Kat.2 için h_class "Acute Tox. 2" → 5)
    'H301':  100,   // Kat. 3
    'H302':  500,   // Kat. 4
    // Deri yolu mg/kg
    'H310':  5,     // Kat. 1 (Kat.2 → 50) — CLP Tablo 3.1.2: Cat.1=5 mg/kg
    'H311':  300,   // Kat. 3 — CLP Tablo 3.1.2: Cat.3=300 mg/kg
    'H312':  1100,  // Kat. 4 — CLP Tablo 3.1.2: Cat.4=1100 mg/kg
    // Soluma - buhar mg/L/4h
    'H330':  0.05,  // Kat. 1 (Kat.2 → 0.5)
    'H331':  3.0,   // Kat. 3
    'H332':  11.0,  // Kat. 4
  };
  // Kat.2 düzeltmesi: h_class "Acute Tox. 2" olduğunda H300/H310/H330 için
  const ATE_CAT2 = { 'H300': 5, 'H310': 50, 'H330': 0.5 };

  // Yol → ilgili H kodları
  const ATE_ROUTES = {
    oral:   ['H300','H301','H302'],
    dermal: ['H310','H311','H312'],
    inhal:  ['H330','H331','H332'],
  };

  // SEA/CLP Tablo 3.1.1 — ATE_mix → H kodu eşikleri
  const ATE_CLASSIFY = {
    oral:   [{max:5,    h:'H300'},{max:50,   h:'H300'},
             {max:300,  h:'H301'},{max:2000, h:'H302'}],
    dermal: [{max:50,   h:'H310'},{max:200,  h:'H310'},
             {max:1000, h:'H311'},{max:2000, h:'H312'}],
    inhal:  [{max:0.5,  h:'H330'},{max:2.0,  h:'H330'},
             {max:10,   h:'H331'},{max:20,   h:'H332'}],
  };

  // ATE formülü ile işlenecek kodlar — flatMap'te GCL atlanır
  const ATE_HCODES = new Set(['H300','H301','H302','H310','H311','H312','H330','H331','H332']);

  // ── CLP Dominance (Üstünlük) Kuralları ──────────────────────────────────────
  // Kaynak: CLP (AT) No 1272/2008, Annex I + Annex V
  // Üst sınıf → alt sınıfları kaldır (etiket + SDS Bölüm 2)
  const DOMINANCE = {
    // Cilt/Göz — CLP Annex I §3.2 / §3.3
    'H314': ['H318','H315','H319'],
    'H318': ['H319'],

    // Akut Toksisite — aynı yolda üst kategori alttakileri süpürür — §3.1
    'H300': ['H301','H302'], 'H301': ['H302'],
    'H310': ['H311','H312'], 'H311': ['H312'],
    'H330': ['H331','H332'], 'H331': ['H332'],

    // STOT SE — §3.8
    'H370': ['H371','H335','H336'], 'H371': ['H335','H336'],
    // STOT RE — §3.9
    'H372': ['H373'],

    // CMR — §3.5 / §3.6 / §3.7
    'H340': ['H341'], 'H350': ['H351'], 'H360': ['H361'],

    // Sucul — CLP Annex V §1.3
    // H410 (Chronic 1) → H400 etiket üzerinde gösterilmez + alt kronikler
    'H410': ['H400','H411','H412','H413'],
    'H411': ['H412','H413'],
    'H412': ['H413'],

    // Yanıcı Sıvı — §2.6
    'H224': ['H225','H226'], 'H225': ['H226'],

    // Okside Edici Sıvı/Katı — §2.13/§2.14
    // H271 (Kat.1, Danger) → H272 (Kat.2/3, Warning) süpürür
    'H271': ['H272'],

    // Su ile Temas / Su ile Reaksiyon — §2.12
    // H260 (Kat.1) → H261 (Kat.2/3) süpürür
    'H260': ['H261'],

    // Kendiliğinden Isınan Maddeler — §2.11
    'H251': ['H252'],

    // Organik Peroksitler / Kendiliğinden Parçalananlar — §2.8 / §2.15
    'H240': ['H241','H242'],
    'H241': ['H242'],
  };

  // ── H kodu → GHS piktogram ───────────────────────────────────────────────────
  const H_TO_GHS = {
    // Patlayıcılar
    'H200':'GHS01','H201':'GHS01','H202':'GHS01','H203':'GHS01','H204':'GHS01','H205':'GHS01',
    // Yanıcı gazlar/sıvılar/katılar
    'H220':'GHS02','H221':'GHS02','H222':'GHS02','H223':'GHS02',
    'H224':'GHS02','H225':'GHS02','H226':'GHS02','H228':'GHS02',
    'H229':'GHS02',
    'H232':'GHS02',
    'H240':'GHS01','H241':'GHS01','H242':'GHS02',
    'H250':'GHS02','H251':'GHS02','H252':'GHS02',
    'H260':'GHS02','H261':'GHS02',
    // Oksitleyiciler
    'H270':'GHS03','H271':'GHS03','H272':'GHS03',
    // Basınçlı gaz
    'H280':'GHS04','H281':'GHS04',
    // Aşındırıcı / Metal korozif
    'H290':'GHS05',
    'H314':'GHS05','H318':'GHS05',
    // Toksik
    'H300':'GHS06','H301':'GHS06',
    'H310':'GHS06','H311':'GHS06',
    'H330':'GHS06','H331':'GHS06',
    // Zararlı / Tahriş edici
    'H302':'GHS07','H312':'GHS07','H332':'GHS07',
    'H315':'GHS07','H317':'GHS07','H319':'GHS07',
    'H335':'GHS07','H336':'GHS07','H420':'GHS07',
    // Aspirasyon / CMR / STOT
    'H304':'GHS08',
    'H334':'GHS08',
    'H340':'GHS08','H341':'GHS08',
    'H350':'GHS08','H351':'GHS08',
    'H360':'GHS08','H361':'GHS08','H362':'GHS08',
    'H370':'GHS08','H371':'GHS08','H372':'GHS08','H373':'GHS08',
    // Sucul tehlike — SADECE Acute 1, Chronic 1 ve 2 piktogram alır
    'H400':'GHS09','H410':'GHS09','H411':'GHS09',
    // H412, H413 → piktogram yok
  };
  const GHS_ORDER = ['GHS01','GHS02','GHS03','GHS04','GHS05','GHS06','GHS07','GHS08','GHS09'];

  // ── Sinyal kelimesi — CLP Annex III ──────────────────────────────────────────
  const DANGER_H = new Set([
    'H200','H201','H202','H203','H204','H205',
    'H220','H222','H224','H225',
    'H228',
    'H232',                          // Pirofor gaz — CLP Annex III → Danger
    'H240','H241',
    'H250','H251',
    'H260',
    'H270','H271',
    'H300','H301',
    'H304',
    'H310','H311',
    'H314','H318',
    'H330','H331',
    'H334',
    'H340','H350','H360',
    'H370','H372',
  ]);

  const WARNING_H = new Set([
    'H221','H223','H226','H227',
    'H229',
    'H242','H252','H261','H272','H273','H280','H281',
    'H290',
    'H302','H303','H312','H313','H332','H333',
    'H315','H316','H317','H319','H320',
    'H335','H336',
    'H341','H351','H361','H362',
    'H371','H373',
    'H400','H410','H411',
    'H420',
  ]);

  // Yanıcılık/basınç H kodları — fiziksel engine'de hesaplanır
  const FLAM_SKIP = new Set([
    'H220','H221','H222','H223','H224','H225','H226','H227','H228','H229','H232',
  ]);

  // Sucul tehlike H kodları — EcoEngine M-faktörlü toplamlı yöntemle hesaplar
  const ECO_SKIP = new Set(['H400','H410','H411','H412','H413']);

  function getGhsCodes(hcodes) {
    const pics = new Set();
    hcodes.forEach(h => {
      const base = h.replace(/[^H0-9]/g,'').substring(0,4);
      const ghs = H_TO_GHS[base] || H_TO_GHS[h];
      if (ghs) pics.add(ghs);
    });

    // SEA Madde 28 / CLP Ek-I §1.2.1.2 Piktogram Önceliği
    if (pics.has('GHS01')) { pics.delete('GHS02'); pics.delete('GHS03'); }

    // Kural (a): GHS06 (kurukafa) varsa GHS07 tamamen kaldırılır
    if (pics.has('GHS06')) pics.delete('GHS07');

    // Kural (b): GHS05 (aşındırıcı) varsa GHS07 yalnızca Cilt/Göz Tahrişi (H315/H319)
    //            nedeniyle eklenmişse kaldırılır. Akut Toks.4 (H302/H312/H332),
    //            Cilt Duyar.1 (H317) veya STOT SE 3 (H335/H336) varsa GHS07 KALIR.
    if (pics.has('GHS05') && !pics.has('GHS06')) {
      const _ghs07NonIrrit = ['H302','H312','H332','H317','H335','H336'];
      const _hasNonIrritSrc = hcodes.some(h => _ghs07NonIrrit.includes(h.replace(/[^H0-9]/g,'').substring(0,4)));
      if (!_hasNonIrritSrc) pics.delete('GHS07');
    }

    // Kural (c): GHS08 + H334 (Solunum Duyar.) varsa GHS07 Cilt Duyar./Tahriş için
    //            kaldırılır; ancak Akut Toks.4 (H302/H312/H332) veya STOT SE (H335/H336)
    //            varsa GHS07 KALIR.
    if (pics.has('GHS08') && hcodes.some(h => h.replace(/[^H0-9]/g,'').substring(0,4) === 'H334')) {
      const _ghs07AcuteTox = ['H302','H312','H332','H335','H336'];
      const _hasAcuteToxSrc = hcodes.some(h => _ghs07AcuteTox.includes(h.replace(/[^H0-9]/g,'').substring(0,4)));
      if (!_hasAcuteToxSrc) pics.delete('GHS07');
    }
    if (pics.has('GHS02') || pics.has('GHS06')) pics.delete('GHS04');

    return GHS_ORDER.filter(g => pics.has(g));
  }

  // ── Ana sınıflandırma fonksiyonu ──────────────────────────────────────────────
  function classify(comps, mixturePH) {
    const cutoffUsed = {};

    // ── pH Kontrolü — SEA Tablo 3.2.3 Notu ─────────────────────────────────────
    // pH ≤ 2 veya pH ≥ 11.5 → Skin Corr. 1 (H314) + Eye Dam. 1 (H318) doğrudan ata
    // Hesaplama yapılmaz; buffer kapasitesi dikkate alınmaz (muhafazakâr yaklaşım)
    const phRaw = parseFloat(mixturePH);
    const phExtreme = !isNaN(phRaw) && (phRaw <= 2.0 || phRaw >= 11.5);
    const phDirect = new Set();
    if (phExtreme) {
      const direction = phRaw <= 2.0 ? '≤ 2' : '≥ 11.5';
      phDirect.add('H314');
      phDirect.add('H318');
      cutoffUsed['H314'] = { value: phRaw, source: `pH=${phRaw} (${direction}) → SEA Tablo 3.2.3`, cas: 'KARIŞIM' };
      cutoffUsed['H318'] = { value: phRaw, source: `pH=${phRaw} (${direction}) → SEA Tablo 3.2.3`, cas: 'KARIŞIM' };
    }

    // SCL nesne formatından c_min'i oku (tek H kodu için)
    function _getSCL(cScl, code) {
      if (!cScl) return null;
      if (Array.isArray(cScl) && cScl.length > 0) {
        const mins = cScl
          .filter(s => (s.h_code || '').replace(/[*\s]/g,'').substring(0,4) === code && s.c_min != null)
          .map(s => s.c_min);
        return mins.length > 0 ? Math.min(...mins) : null;
      }
      if (typeof cScl === 'object') return cScl[code] !== undefined ? cScl[code] : null;
      return null;
    }

    const raw = comps.flatMap(c => {
      const conc = parseFloat(c.concMax || c.conc) || 0;

      // Hazard listesindeki H kodlarını bir Set'e al — SCL-only kodları belirlemek için
      const hazardCodes = new Set(
        (c.hazards || []).map(h => (h.h_code || '').replace(/[*\s]/g,'').substring(0,4))
      );

      const fromHazards = (c.hazards || []).flatMap(h => {
        const code = (h.h_code || '').replace(/[*\s]/g,'').substring(0,4);
        if (!code.startsWith('H')) return [];
        if (FLAM_SKIP.has(code))  return [];
        if (ECO_SKIP.has(code))   return [];
        if (ATE_HCODES.has(code)) return [];

        // pH doğrudan H314/H318 atadıysa tek bileşen GCL kontrolü atlanır
        if (phExtreme && (code === 'H314' || code === 'H318')) return [];

        const scl = _getSCL(c.scl, code);
        const gcl = CUTOFFS[code];
        const cutoff = scl !== null ? scl : gcl;
        const source = scl !== null ? 'SCL' : 'GCL';

        if (cutoff === undefined) return [code];

        // STOT SE 1→2 geçiş kuralı
        if (code === 'H370' && scl === null) {
          if (conc >= 10.0) {
            cutoffUsed['H370'] = { value: 10.0, source: 'GCL', cas: c.cas || '' };
            return ['H370'];
          }
          if (conc >= 1.0) {
            if (!cutoffUsed['H371'] || 1.0 < (cutoffUsed['H371'].value || Infinity)) {
              cutoffUsed['H371'] = { value: 1.0, source: 'GCL-transition', cas: c.cas || '' };
            }
            return ['H371'];
          }
          return [];
        }

        if (conc >= cutoff) {
          if (!cutoffUsed[code] || cutoff < cutoffUsed[code].value) {
            cutoffUsed[code] = { value: cutoff, source, cas: c.cas || '' };
          }
          return [code];
        }
        return [];
      });

      // SCL-only kodlar: hazard listesinde olmayan ama maddeye özgü SCL eşiği tanımlı
      // Örn. nikel sülfat: H372 tehlike listesinde, ama H373 sadece SCL ile (%0.1-%1 arası) tetiklenir
      const fromSCLOnly = [];

      // Nesne formatı { 'H373': 0.1, ... }
      const sclObj = (!Array.isArray(c.scl) && c.scl && typeof c.scl === 'object') ? c.scl : null;
      if (sclObj) {
        Object.entries(sclObj).forEach(([code, sclVal]) => {
          if (!code.startsWith('H') || hazardCodes.has(code)) return;
          if (FLAM_SKIP.has(code) || ECO_SKIP.has(code) || ATE_HCODES.has(code)) return;
          if (typeof sclVal !== 'number') return;
          if (conc >= sclVal) {
            fromSCLOnly.push(code);
            if (!cutoffUsed[code] || sclVal < cutoffUsed[code].value) {
              cutoffUsed[code] = { value: sclVal, source: 'SCL', cas: c.cas || '' };
            }
          }
        });
      }

      // Dizi formatı [{h_code:'H373', c_min:0.1, c_max:1.0}, ...]  — API'den gelen format
      if (Array.isArray(c.scl)) {
        c.scl.forEach(s => {
          const code = (s.h_code || '').replace(/[*\s]/g, '').substring(0, 4);
          if (!code.startsWith('H') || hazardCodes.has(code)) return;
          if (FLAM_SKIP.has(code) || ECO_SKIP.has(code) || ATE_HCODES.has(code)) return;
          const sclVal = typeof s.c_min === 'number' ? s.c_min : null;
          if (sclVal === null) return;
          if (conc >= sclVal) {
            fromSCLOnly.push(code);
            if (!cutoffUsed[code] || sclVal < (cutoffUsed[code].value || Infinity)) {
              cutoffUsed[code] = { value: sclVal, source: 'SCL', cas: c.cas || '' };
            }
          }
        });
      }

      return [...fromHazards, ...fromSCLOnly];
    });

    // pH'tan gelen doğrudan kodları ekle
    phDirect.forEach(code => { if (!raw.includes(code)) raw.push(code); });

    // ── CLP Tablo 3.2.3: Cilt Toplama Kuralı ────────────────────────────────────
    // Kural 1: ΣSkin Corr. 1 ≥ %5 → H314
    // Kural 2: 10×ΣSkin Corr. 1 + ΣSkin Irrit. 2 ≥ %10 → H315 (H314 yoksa)
    if (!raw.includes('H314') && !phExtreme) {
      const sumSC1 = comps.reduce((s, c) => {
        const conc = parseFloat(c.concMax || c.conc) || 0;
        const hasSC1 = (c.hazards || []).some(h => {
          const code = (h.h_code||'').replace(/[*\s]/g,'').substring(0,4);
          return code === 'H314';
        });
        return hasSC1 ? s + conc : s;
      }, 0);
      if (sumSC1 >= 5.0) {
        raw.push('H314');
        cutoffUsed['H314'] = { value: 5.0, source: 'GCL-sum-SC1', cas: 'KARIŞIM' };
      }
    }

    if (!raw.includes('H314') && !raw.includes('H315')) {
      const sumSC1 = comps.reduce((s, c) => {
        const conc = parseFloat(c.concMax || c.conc) || 0;
        const hasSC1 = (c.hazards || []).some(h =>
          (h.h_code||'').replace(/[*\s]/g,'').substring(0,4) === 'H314');
        return hasSC1 ? s + conc : s;
      }, 0);
      const sumSI2 = comps.reduce((s, c) => {
        const conc = parseFloat(c.concMax || c.conc) || 0;
        const hasSI2 = (c.hazards || []).some(h =>
          (h.h_code||'').replace(/[*\s]/g,'').substring(0,4) === 'H315');
        return hasSI2 ? s + conc : s;
      }, 0);
      if (10.0 * sumSC1 + sumSI2 >= 10.0) {
        raw.push('H315');
        cutoffUsed['H315'] = { value: 10.0, source: 'GCL-sum-weighted', cas: 'KARIŞIM' };
      }
    }

    // ── CLP Tablo 3.3.3: Göz Toplama Kuralı ─────────────────────────────────────
    // Kural 1: ΣEye Dam. 1 ≥ %3 → H318
    // Kural 2: 10×ΣEye Dam. 1 + ΣEye Irrit. 2 ≥ %10 → H319 (H318 yoksa)
    if (!raw.includes('H318') && !phExtreme) {
      const sumED1 = comps.reduce((s, c) => {
        const conc = parseFloat(c.concMax || c.conc) || 0;
        const hasED1 = (c.hazards || []).some(h =>
          (h.h_code||'').replace(/[*\s]/g,'').substring(0,4) === 'H318');
        return hasED1 ? s + conc : s;
      }, 0);
      if (sumED1 >= 3.0) {
        raw.push('H318');
        cutoffUsed['H318'] = { value: 3.0, source: 'GCL-sum-ED1', cas: 'KARIŞIM' };
      }
    }

    if (!raw.includes('H318') && !raw.includes('H319')) {
      const sumED1 = comps.reduce((s, c) => {
        const conc = parseFloat(c.concMax || c.conc) || 0;
        const hasED1 = (c.hazards || []).some(h =>
          (h.h_code||'').replace(/[*\s]/g,'').substring(0,4) === 'H318');
        return hasED1 ? s + conc : s;
      }, 0);
      const sumEI2 = comps.reduce((s, c) => {
        const conc = parseFloat(c.concMax || c.conc) || 0;
        const hasEI2 = (c.hazards || []).some(h =>
          (h.h_code||'').replace(/[*\s]/g,'').substring(0,4) === 'H319');
        return hasEI2 ? s + conc : s;
      }, 0);
      if (10.0 * sumED1 + sumEI2 >= 10.0) {
        raw.push('H319');
        cutoffUsed['H319'] = { value: 10.0, source: 'GCL-sum-weighted', cas: 'KARIŞIM' };
      }
    }

    // ── SEA/CLP Bölüm 3.1.3.6.1: ATE Formülü ────────────────────────────────────
    // Uygulama kriterleri:
    //   1. Konsantrasyon ≥%1 olan bileşenler dahil edilir (CLP Ek I §3.1.3.6.2.1)
    //      %1'den az olsa da yüksek toksisitesi biliniyorsa (Kat.1/2) dahil et
    //   2. Bileşenin ATE değeri bilinmiyorsa → Tablo 3.1.2 nokta tahmini kullan
    //   3. ATE'si bilinmeyenlerin toplamı >%10 ise formül revize edilir
    const ateMixDetails = {};  // route → { ateMix, resultCode, components[] } — PDF için

    Object.entries(ATE_ROUTES).forEach(([route, codes]) => {
      const codeSet = new Set(codes);
      let sumInv = 0;
      let knownConc = 0;   // ATE değeri bilinen bileşenlerin toplam konsantrasyonu
      let hasAny = false;
      const ateComps = [];

      comps.forEach(c => {
        const conc = parseFloat(c.concMax || c.conc) || 0;
        let compHasATE = false;

        (c.hazards || []).forEach(h => {
          const code = (h.h_code || '').replace(/[*\s]/g, '').substring(0, 4);
          if (!codeSet.has(code)) return;

          // CLP Ek I §3.1.3.6.2.1: ATE'si bilinen (sınıflandırılmış, Kat.1-4) bileşenler
          // konsantrasyondan bağımsız olarak her zaman dahil edilir.
          // Yalnızca ATE'si bilinmeyen (sınıflandırılmamış) <%1 bileşenler hariç tutulabilir;
          // ancak bu döngüde yalnızca akut toks. H kodları (bilinen ATE) işlenir → filtre kaldırıldı.
          const hclass = (h.h_class || '').replace(/\*/g, '').trim();

          let ate = ATE_POINT[code];
          if (!ate) return;
          if (hclass === 'Acute Tox. 2' && ATE_CAT2[code] !== undefined) {
            ate = ATE_CAT2[code];
          }
          sumInv += conc / ate;
          hasAny = true;
          compHasATE = true;
          ateComps.push({ name: c.name || c.cas, conc, code, ate });
        });

        if (compHasATE) knownConc += conc;
      });

      if (!hasAny || sumInv === 0) return;

      // CLP Ek I §3.1.3.6.2 — Standart formül: ATEmix = 100 / Σ(Ci/ATEi)
      // Sınıflandırılmamış bileşenler (su, dolgu vb.) Ci/ATEi → 0 katkısı yapar,
      // formülden dışlanır; dilüsyon etkisi korunur.
      // NOT: Eski "revize formül" (knownConc/sumInv) dilüsyon etkisini siliyordu
      // ve %8 allilamin gibi durumlarda ATEmix = 100 → H301/kuru kafa piktogramı
      // çıkarıyordu. Doğru sonuç: ATEmix = 100/0.08 = 1250 → H302/GHS07.
      const unknownPct = Math.max(0, 100 - knownConc);  // PDF tablosu için bilgi amaçlı
      const ate_mix = 100 / sumInv;

      let resultCode = null;
      for (const { max, h } of ATE_CLASSIFY[route]) {
        if (ate_mix <= max) { resultCode = h; break; }
      }

      // ATEmix detaylarını kaydet (PDF Bölüm 11 için)
      ateMixDetails[route] = {
        ateMix: Math.round(ate_mix * 10) / 10,
        resultCode,
        unknownPct: Math.round(unknownPct * 10) / 10,
        components: ateComps,
      };

      if (!resultCode) return;

      if (!raw.includes(resultCode)) {
        raw.push(resultCode);
        cutoffUsed[resultCode] = {
          value: Math.round(ate_mix * 10) / 10,
          source: 'ATE',
          cas: 'KARIŞIM',
        };
      }
    });

    // Deduplikasyon
    const result = [...new Set(raw)];

    // Dominance uygula
    const dominated = [];
    Object.entries(DOMINANCE).forEach(([dominant, subordinates]) => {
      if (result.includes(dominant)) {
        subordinates.forEach(sub => {
          const i = result.indexOf(sub);
          if (i > -1) { result.splice(i, 1); dominated.push(sub); }
        });
      }
    });

    // Sinyal sözcüğü
    const hasDanger  = result.some(h => DANGER_H.has(h));
    const hasWarning = result.some(h => WARNING_H.has(h));
    const signal = hasDanger ? 'Danger' : (hasWarning ? 'Warning' : 'None');

    // Piktogramlar
    const pictograms = getGhsCodes(result);

    return { hCodes: result, signal, pictograms, dominated, cutoffUsed, ateMixDetails, getGhsCodes };
  }

  function init() {
    if (typeof EventBus !== 'undefined') {
      EventBus.on('CLP_CALCULATE', ({ comps, ph }) => {
        const result = classify(comps, ph);
        EventBus.emit('H_CODES_READY', result);
      });
    }
    console.log('[CLPEngine] init OK');
  }

  return { init, classify, getGhsCodes, CUTOFFS, DOMINANCE, DANGER_H, WARNING_H, ATE_POINT, ATE_CAT2, ATE_CLASSIFY };
})();
