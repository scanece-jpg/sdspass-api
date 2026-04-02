/**
 * CLPEngine — KKDİK Ek-2 / CLP (AT) No 1272/2008
 * Girdi : comps[] = [{ cas, name, conc, concMin, concMax, hazards:[{h_class,h_code}] }]
 * Çıktı : { hCodes[], signal, pictograms[], dominated[] }
 *
 * Events: dinler  → CLP_CALCULATE { comps }
 *         emit eder → H_CODES_READY { hCodes, signal, pictograms, dominated }
 */
const CLPEngine = (() => {

  // ── CLP Annex I Kesme Değerleri ──────────────────────────────────────────────
  // NOT: H300-H332 (Akut Toksisite) GCL ile değil, SEA Tablo 3.1.2 ATE formülü
  // ile sınıflandırılır (bkz. ATE_POINT / calculateATE). GCL buradan çıkarıldı.
  const CUTOFFS = {
    'H314':1.0,'H315':10.0,'H318':1.0,'H319':10.0,
    'H317':1.0,'H334':0.1,
    'H340':0.1,'H341':1.0,
    'H350':0.1,'H351':1.0,
    'H360':0.1,'H361':1.0,'H362':0.1,
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
    'H310':  0.5,   // Kat. 1 (Kat.2 → 50)
    'H311':  200,   // Kat. 3
    'H312':  1000,  // Kat. 4
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
  // Kaynak: CLP (AT) No 1272/2008, Annex V, Tablo 1.3
  // ÖNEMLİ KURALLAR:
  //   H412 (Aquatic Chronic 3) → piktogram YOK (CLP Annex V §1.3)
  //   H413 (Aquatic Chronic 4) → piktogram YOK
  //   H412/H413 → uyarı kelimesi YOK (etiket kuralı)
  const H_TO_GHS = {
    // Patlayıcılar
    'H200':'GHS01','H201':'GHS01','H202':'GHS01','H203':'GHS01','H204':'GHS01','H205':'GHS01',
    // Yanıcı gazlar/sıvılar/katılar
    'H220':'GHS02','H221':'GHS02','H222':'GHS02','H223':'GHS02',
    'H224':'GHS02','H225':'GHS02','H226':'GHS02','H228':'GHS02',
    'H229':'GHS02',                               // Pressurised container — GHS02 (flame)
    'H232':'GHS02',                               // Flam. Gas (reacts w/air) — GHS02
    'H240':'GHS01','H241':'GHS01','H242':'GHS02',
    'H250':'GHS02','H251':'GHS02','H252':'GHS02',
    'H260':'GHS02','H261':'GHS02',
    // Oksitleyiciler
    'H270':'GHS03','H271':'GHS03','H272':'GHS03',
    // H273 (Ox. Liq./Sol. 3) → piktogram YOK (CLP Annex V), sadece Warning sinyal kelimesi
    // Basınçlı gaz
    'H280':'GHS04','H281':'GHS04',
    // Aşındırıcı / Metal korozif
    'H290':'GHS05',                             // Met. Corr. 1 — GHS05 ✓
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
    // H412 (Chronic 3) ve H413 (Chronic 4) → piktogram YOK (CLP Annex V §1.3)
    'H400':'GHS09','H410':'GHS09','H411':'GHS09',
    // H412: piktogram yok
    // H413: piktogram yok
  };
  const GHS_ORDER = ['GHS01','GHS02','GHS03','GHS04','GHS05','GHS06','GHS07','GHS08','GHS09'];

  // ── Sinyal kelimesi — CLP Annex III ──────────────────────────────────────────
  // DANGER: CLP Annex III Tablo 1.1
  const DANGER_H = new Set([
    'H200','H201','H202','H203','H204','H205',       // Patlayıcı Kat.1-3
    'H220','H222','H224','H225',                     // Yanıcı Gaz 1A, Aer.1, Sıvı 1/2
    'H228',                                          // Yanıcı Katı 1
    'H240','H241',                                   // Self-react. A/B
    'H250','H251',                                   // Piroforik / Self-heat.1
    'H260',                                          // Su ile temas → H2
    'H270','H271',                                   // Ox. Gas 1, Ox. Liq. 1
    'H300','H301',                                   // Acute Tox. 1-2-3 (Oral)
    'H304',                                          // Asp. Tox. 1
    'H310','H311',                                   // Acute Tox. 1-2-3 (Derm.)
    'H314','H318',                                   // Skin Corr. 1, Eye Dam. 1
    'H330','H331',                                   // Acute Tox. 1-2-3 (Inhal.)
    'H334',                                          // Resp. Sens. 1
    'H340','H350','H360',                            // CMR Kat.1
    'H370','H372',                                   // STOT SE 1, STOT RE 1
  ]);

  // WARNING: CLP Annex III Tablo 1.2
  const WARNING_H = new Set([
    'H221','H223','H226','H227',                     // Yanıcı Gaz 1B, Aer.2/3, Sıvı 3/4
    'H229','H232',                                   // Aer. basınçlı, Flam. Gas (hava ile)
    'H242','H252','H261','H272','H273','H280','H281',// Self-react.G, Self-heat.2, Su/H2-2, Ox.2/3, Gaz
    'H290',                                          // Met. Corr. 1 — WARNING (Danger değil!)
    'H302','H303','H312','H313','H332','H333',       // Acute Tox. 4/5
    'H315','H316','H317','H319','H320',              // Skin/Eye Irrit. + Skin Sens.
    'H335','H336',                                   // STOT SE 3
    'H341','H351','H361','H362',                     // CMR Kat.2 + Laktasyon
    'H371','H373',                                   // STOT SE 2, STOT RE 2
    'H400','H410','H411',                            // Aquatic Acute 1, Chronic 1/2
    'H420',                                          // Ozon
    // H412, H413 → WARNING_H'da YOK → sinyal kelimesi yok
    // H273 → WARNING (Ox. Liq./Sol. 3) — piktogram yok, sadece Warning sinyal
  ]);

  // Yanıcılık/basınç H kodları — fiziksel engine'de hesaplanır, CLPEngine atlar
  const FLAM_SKIP = new Set([
    'H220','H221','H222','H223','H224','H225','H226','H227','H228','H229','H232',
  ]);

  // Sucul tehlike H kodları — EcoEngine M-faktörlü toplamlı yöntemle hesaplar
  // CLP Annex V Tablo 4.1.0: M-faktörsüz eşik %25, basit %0.1 GCL YANLIŞ.
  // Bu kodlar CLPEngine'de atlanır; EcoEngine'den gelir.
  const ECO_SKIP = new Set(['H400','H410','H411','H412','H413']);

  function getGhsCodes(hcodes) {
    const pics = new Set();
    hcodes.forEach(h => {
      const base = h.replace(/[^H0-9]/g,'').substring(0,4);
      const ghs = H_TO_GHS[base] || H_TO_GHS[h];
      if (ghs) pics.add(ghs);
    });

    // ── SEA Madde 28 Piktogram Önceliği ─────────────────────────────────────
    // (a) GHS01 varsa GHS02 ve GHS03 isteğe bağlı (burada kaldırıyoruz)
    if (pics.has('GHS01')) { pics.delete('GHS02'); pics.delete('GHS03'); }
    // (b) GHS06 varsa GHS07 kaldırılır
    if (pics.has('GHS06')) pics.delete('GHS07');
    // (c) GHS05 varsa deri/göz tahrişi için GHS07 kaldırılır
    //     (GHS05 aynı zamanda GHS06 gerektirmiyorsa GHS07'yi kaldır)
    if (pics.has('GHS05') && !pics.has('GHS06')) pics.delete('GHS07');
    // (ç) GHS08 solunum hassasiyeti (H334) için geçerliyse GHS07 kaldırılır
    if (pics.has('GHS08') && hcodes.some(h => h.startsWith('H334'))) pics.delete('GHS07');
    // (d) GHS02 veya GHS06 varsa GHS04 isteğe bağlı
    if (pics.has('GHS02') || pics.has('GHS06')) pics.delete('GHS04');

    return GHS_ORDER.filter(g => pics.has(g));
  }

  function classify(comps) {
    // 1. Her bileşenden kesme değeri geçen H kodlarını topla
    //    Öncelik: SCL (maddeye özel) → GCL (genel tablo)
    //    comp.scl = { 'H314': 2.0, 'H315': 0.5, ... }  — CAS lookup'tan gelir

    // cutoffUsed: hangi H kodu için hangi eşik kullanıldı + kaynak (SCL/GCL)
    const cutoffUsed = {}; // { 'H314': { value: 2.0, source: 'SCL', cas: '1310-73-2' } }

    const raw = comps.flatMap(c => {
      const conc = parseFloat(c.concMax || c.conc) || 0;
      return (c.hazards || []).flatMap(h => {
        const code = (h.h_code || '').replace(/[*\s]/g,'').substring(0,4);
        if (!code.startsWith('H')) return [];
        if (FLAM_SKIP.has(code))  return []; // Yanıcılık fiziksel engine'de
        if (ECO_SKIP.has(code))   return []; // Sucul tehlike EcoEngine'de (M-faktörlü)
        if (ATE_HCODES.has(code)) return []; // Akut Toksisite → ATE engine'de (SEA Tablo 3.1.2)

        // ── Öncelik 1: SCL — maddeye özel (Annex VI, KKDİK Ek-1) ──────────────
        const scl = c.scl && c.scl[code] !== undefined ? c.scl[code] : null;

        // ── Öncelik 3: GCL — genel CLP tablo (Annex I §3.x) ──────────────────
        const gcl = CUTOFFS[code];

        // Hangi eşiği kullanacağız?
        const cutoff = scl !== null ? scl : gcl;
        const source = scl !== null ? 'SCL' : 'GCL';

        if (cutoff === undefined) return [code]; // Bilinmeyen → muhafazakâr

        // ── STOT SE 1→2 geçiş kuralı (CLP Ek I Tablo 3.8.2) ──────────────────
        // H370 (STOT SE 1) bileşeni:
        //   %≥10 → karışım H370 (STOT SE 1)
        //   %1–10 → karışım H371 (STOT SE 2)  ← SCL yoksa GCL kuralı
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
          // En düşük (en kısıtlayıcı) eşiği kaydet
          if (!cutoffUsed[code] || cutoff < cutoffUsed[code].value) {
            cutoffUsed[code] = { value: cutoff, source, cas: c.cas || '' };
          }
          return [code];
        }
        return [];
      });
    });

    // CLP Tablo 3.2.4 / 3.3.4: Toplama Kuralı ────────────────────────────────
    // Tek bileşen GCL altında olsa da birden fazla Skin/Eye Irrit. 2 bileşenin
    // TOPLAMI ≥ %10 ise karışım H315/H319 olarak sınıflandırılır.
    // Örnek: Maleik asit %5 + Bakır sülfat %8 = %13 ≥ %10 → H315 ✓
    if (!raw.includes('H315') && !raw.includes('H314')) {
      const sumSI2 = comps.reduce((s, c) => {
        const conc = parseFloat(c.concMax || c.conc) || 0;
        return (c.hazards || []).some(h => (h.h_code||'').replace(/[*\s]/g,'').substring(0,4) === 'H315')
          ? s + conc : s;
      }, 0);
      if (sumSI2 >= 10.0) {
        raw.push('H315');
        cutoffUsed['H315'] = { value: 10.0, source: 'GCL-sum', cas: 'KARIŞIM' };
      }
    }
    if (!raw.includes('H319') && !raw.includes('H318')) {
      const sumEI2 = comps.reduce((s, c) => {
        const conc = parseFloat(c.concMax || c.conc) || 0;
        return (c.hazards || []).some(h => (h.h_code||'').replace(/[*\s]/g,'').substring(0,4) === 'H319')
          ? s + conc : s;
      }, 0);
      if (sumEI2 >= 10.0) {
        raw.push('H319');
        cutoffUsed['H319'] = { value: 10.0, source: 'GCL-sum', cas: 'KARIŞIM' };
      }
    }

    // ── SEA/CLP Bölüm 3.1.3.6.1: ATE Formülü ────────────────────────────────────
    // Her maruziyet yolu (oral/dermal/inhal) için ayrı hesap:
    //   ATE_mix = 100 / Σ(Ci / ATEi)
    // Bileşen ATE değeri: Tablo 3.1.2 nokta tahmini (Kat.4 oral = 500 mg/kg).
    // Sonuç Tablo 3.1.1 eşikleriyle karşılaştırılır.
    Object.entries(ATE_ROUTES).forEach(([route, codes]) => {
      const codeSet = new Set(codes);
      let sumInv = 0;
      let hasAny = false;

      comps.forEach(c => {
        const conc = parseFloat(c.concMax || c.conc) || 0;
        (c.hazards || []).forEach(h => {
          const code = (h.h_code || '').replace(/[*\s]/g, '').substring(0, 4);
          if (!codeSet.has(code)) return;
          let ate = ATE_POINT[code];
          if (!ate) return;
          // Kat.2 bileşen düzeltmesi (Tablo 3.1.2)
          // "Acute Tox. 2 *" (inhalasyon) → * temizlenerek "Acute Tox. 2" eşleşmesi sağlanır
          const hclass = (h.h_class || '').replace(/\*/g, '').trim();
          if (hclass === 'Acute Tox. 2' && ATE_CAT2[code] !== undefined) {
            ate = ATE_CAT2[code];
          }
          sumInv += conc / ate;
          hasAny = true;
        });
      });

      if (!hasAny || sumInv === 0) return;
      const ate_mix = 100 / sumInv;

      // Tablo 3.1.1: ATE_mix → H kodu
      let resultCode = null;
      for (const { max, h } of ATE_CLASSIFY[route]) {
        if (ate_mix <= max) { resultCode = h; break; }
      }
      if (!resultCode) return; // ate_mix > 2000 → sınıflandırma yok

      if (!raw.includes(resultCode)) {
        raw.push(resultCode);
        cutoffUsed[resultCode] = {
          value: Math.round(ate_mix * 10) / 10,
          source: 'ATE',
          cas: 'KARIŞIM',
        };
      }
    });

    // 2. Deduplikasyon
    const result = [...new Set(raw)];

    // 3. Dominance uygula
    const dominated = [];
    Object.entries(DOMINANCE).forEach(([dominant, subordinates]) => {
      if (result.includes(dominant)) {
        subordinates.forEach(sub => {
          const i = result.indexOf(sub);
          if (i > -1) { result.splice(i, 1); dominated.push(sub); }
        });
      }
    });

    // 4. Sinyal sözcüğü — CLP Annex III
    // H412/H413 gibi kodlar ne DANGER ne WARNING'de → sinyal kelimesi YOK
    const hasDanger  = result.some(h => DANGER_H.has(h));
    const hasWarning = result.some(h => WARNING_H.has(h));
    const signal = hasDanger ? 'Danger' : (hasWarning ? 'Warning' : 'None');

    // 5. Piktogramlar
    const pictograms = getGhsCodes(result);

    return { hCodes: result, signal, pictograms, dominated, cutoffUsed, getGhsCodes };
  }

  function init() {
    if (typeof EventBus !== 'undefined') {
      EventBus.on('CLP_CALCULATE', ({ comps }) => {
        const result = classify(comps);
        EventBus.emit('H_CODES_READY', result);
      });
    }
    console.log('[CLPEngine] init OK');
  }

  return { init, classify, getGhsCodes, CUTOFFS, DOMINANCE, DANGER_H, WARNING_H };
})();
