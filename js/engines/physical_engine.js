/**
 * PhysicalEngine — Fiziksel Tehlikeler + Teorik Fiziksel Özellikler
 * ─────────────────────────────────────────────────────────────────
 * Bölüm 2.1 (Fiziksel tehlike sınıflandırması) + Bölüm 9 (Fiziksel/kimyasal özellikler)
 *
 * ── TEHLİKE HESABI ──────────────────────────────────────────────────────────────
 *   Flam. Liq. 1/2/3  (H224/H225/H226) — CLP Annex I Tablo 2.6
 *   Asp. Tox. 1        (H304)           — CLP Annex I Tablo 3.10
 *   Flam. Sol. 2       (H228)           — CLP Annex I Tablo 2.7
 *   Ox. Liq. 2/3       (H271/H272)      — CLP Annex I Tablo 2.13
 *
 * ── TEORİK FİZİKSEL ÖZELLİKLER ─────────────────────────────────────────────────
 *   Yoğunluk       : ρ_mix = Σwᵢ / Σ(wᵢ/ρᵢ)        Hata: ±3%   (ISO 2811)
 *   Buhar Basıncı  : Raoult Yasası                   Hata: ±20%  (—)
 *   LEL / UEL      : Raoult + Le Chatelier            Hata: ±15%  (ISO 10156 / EN 1839)
 *   Buhar Yoğunl.  : MW_mix / 29                     Hata: ±2%   (Ideal gaz)
 *   Kaynama Noktası: min(BPᵢ) bileşeni               Muhafazakâr (başlangıç KN)
 *
 * Events:
 *   dinler  → PHYSICAL_CALCULATE { comps, form, userFP }
 *   emit eder → PHYSICAL_READY { results, primary, extra, warnings, theoProps }
 */
const PhysicalEngine = (() => {

  // ── PARLAMA NOKTASI VERİTABANI (°C) ──────────────────────────────────────────
  // Kaynak: ECHA C&L / SDS Annex VI / NIST WebBook
  const FP_DB = {
    '110-54-3':-22,  // n-hekzan
    '110-82-7':-18,  // siklohekzan
    '142-82-5': -4,  // n-heptan
    '111-65-9': 13,  // n-oktan
    '108-88-3':  4,  // toluen
    '71-43-2': -11,  // benzen
    '1330-20-7':27,  // ksilen (karışım)
    '95-47-6':  17,  // o-ksilen
    '106-42-3': 25,  // p-ksilen
    '100-41-4': 21,  // etilbenzen
    '95-63-6':  44,  // 1,2,4-trimetilbenzen
    '67-64-1': -18,  // aseton
    '78-93-3':  -9,  // MEK (bütanon)
    '108-10-1': 14,  // MIBK
    '141-78-6': -4,  // etil asetat
    '123-86-4': 22,  // n-bütil asetat
    '64-17-5':  13,  // etanol
    '67-63-0':  12,  // IPA (izopropanol)
    '71-23-8':  23,  // n-propanol
    '71-36-3':  29,  // n-bütanol
    '78-83-1':  28,  // izobütanol
    '111-76-2': 62,  // 2-bütoksietanol (Kat3 sınırında)
    '112-34-5': 78,  // dietilenglikol monobütil eter
    '107-98-2': 32,  // propilenglikol metil eter
    '64742-47-8':21, // nafta (hidrojenlenmiş ağır)
    '64742-48-9':-20,// nafta (hidrojenlenmiş hafif)
    '64742-82-1':61, // white spirit / stoddard
    '64742-54-7':220,// baz yağı ağır parafinik (>60 → yok)
    '8052-41-3': 38, // stoddard solvent
    '56-81-5':  160, // gliserol (>60 → yok)
    '7732-18-5':null,// su — yanmaz
    '7664-93-9':null,// H₂SO₄ — yanmaz
    '1310-73-2':null,// NaOH — yanmaz
    '7681-52-9':null,// NaOCl — yanmaz
  };

  // ── KAYNAMA NOKTASI VERİTABANI (°C) ─────────────────────────────────────────
  // Kaynak: NIST WebBook / Ullmann's Encyclopedia
  const BP_DB = {
    '110-54-3': 69,  '110-82-7': 81,  '67-64-1':  56,  '71-43-2':  80,
    '78-93-3':  80,  '67-63-0':  82,  '64-17-5':  78,  '71-23-8':  97,
    '64742-48-9':60, '71-36-3': 118,  '78-83-1': 108,  '111-76-2':171,
    '141-78-6': 77,  '123-86-4':126,  '56-81-5': 290,  '7732-18-5':100,
    '108-88-3': 111, '1330-20-7':138, '95-47-6': 144,  '100-41-4': 136,
    '107-98-2': 120, '108-10-1': 117, '64742-47-8':175,'8052-41-3':195,
  };

  // ── MOLEKÜLEr AĞIRLIK VERİTABANI (g/mol) ─────────────────────────────────────
  // Kaynak: IUPAC / PubChem
  const MW_DB = {
    '110-54-3': 86.18,  '142-82-5':100.20,  '110-82-7': 84.16,  '111-65-9':114.23,
    '108-88-3': 92.14,  '1330-20-7':106.16, '71-43-2':  78.11,  '100-41-4':106.17,
    '95-47-6': 106.16,  '95-63-6': 120.19,  '67-64-1':  58.08,  '78-93-3':  72.11,
    '108-10-1':100.16,  '141-78-6': 88.11,  '123-86-4':116.16,  '64-17-5':  46.07,
    '67-63-0':  60.10,  '71-36-3':  74.12,  '78-83-1':  74.12,  '111-76-2':118.17,
    '7732-18-5':18.02,  '64742-47-8':120.0, '64742-48-9':100.0, '8052-41-3':145.0,
    '56-81-5':  92.09,  '107-98-2': 90.12,  '95-63-6': 120.19,
  };

  // ── YOĞUNLUK VERİTABANI (g/cm³, 20°C) ──────────────────────────────────────
  // Kaynak: ISO 2811 / ASTM D4052 / NIST
  const DENSITY_DB = {
    '64-17-5':  0.789,  '67-64-1':  0.791,  '108-88-3': 0.867,  '110-54-3': 0.659,
    '110-82-7': 0.684,  '71-43-2':  0.879,  '1330-20-7':0.860,  '67-63-0':  0.786,
    '71-36-3':  0.810,  '78-93-3':  0.805,  '111-76-2': 0.902,  '78-83-1':  0.802,
    '64742-47-8':0.780, '8052-41-3':0.780,  '141-78-6': 0.902,  '123-86-4': 0.882,
    '7732-18-5':1.000,  '100-41-4': 0.867,  '108-10-1': 0.801,  '95-47-6':  0.879,
    '95-63-6':  0.900,  '56-81-5':  1.261,  '107-98-2': 0.922,  '64742-48-9':0.685,
    '142-82-5': 0.684,  '71-23-8':  0.803,  '111-65-9': 0.703,
  };

  // ── ALT/ÜST PATLAMA SINIRI VERİTABANI (%v/v) ─────────────────────────────────
  // Kaynak: EN 1839 / ISO 10156 / GESTIS veritabanı
  const LEL_DB = {
    '110-54-3':1.1, '142-82-5':1.05,'110-82-7':1.3, '111-65-9':1.0,
    '108-88-3':1.1, '1330-20-7':1.0,'71-43-2': 1.2, '100-41-4':1.0,
    '95-47-6': 1.0, '67-64-1': 2.5, '78-93-3': 1.4, '108-10-1':1.2,
    '141-78-6':2.0, '123-86-4':1.4, '64-17-5': 3.1, '67-63-0': 2.0,
    '71-36-3': 1.4, '78-83-1': 1.7, '111-76-2':1.1, '64742-47-8':1.1,
    '64742-48-9':1.2,'8052-41-3':0.6,'107-98-2':1.8,
  };
  const UEL_DB = {
    '110-54-3':7.5, '142-82-5':6.7, '110-82-7':8.4, '111-65-9':6.5,
    '108-88-3':7.1, '1330-20-7':7.0,'71-43-2': 8.0, '100-41-4':7.8,
    '95-47-6': 7.6, '67-64-1':12.8, '78-93-3':11.4, '108-10-1':8.0,
    '141-78-6':11.5,'123-86-4':7.6, '64-17-5':19.0, '67-63-0':12.7,
    '71-36-3':11.2, '78-83-1':10.9, '111-76-2':12.7, '64742-47-8':7.0,
    '64742-48-9':7.7,'8052-41-3':6.5,'107-98-2':13.1,
  };

  // ── BUHAR BASINCI VERİTABANI (hPa, 20°C) ────────────────────────────────────
  // Kaynak: NIST WebBook / Dortmund Veri Bankası (DDB)
  const VP_DB = {
    '110-54-3':160,  '142-82-5': 48,  '110-82-7':103,  '111-65-9': 14,
    '108-88-3': 29,  '1330-20-7': 8,  '71-43-2': 100,  '100-41-4':  9.5,
    '95-47-6':   9,  '67-64-1': 240,  '78-93-3':  96,  '108-10-1': 21,
    '141-78-6': 97,  '123-86-4': 12.5,'64-17-5':  59,  '67-63-0':  43,
    '71-36-3':   6,  '78-83-1':  12,  '111-76-2':  1,  '7732-18-5':23,
    '64742-47-8':50, '64742-48-9':160,'8052-41-3':  1,  '56-81-5': 0.003,
    '107-98-2':  14,
  };

  // ── ASPİRASYON TOKSİSİTESİ CAS LİSTESİ ──────────────────────────────────────
  const ASP_CAS = new Set([
    '110-54-3','110-82-7','142-82-5','111-65-9','71-43-2',
    '1330-20-7','64742-47-8','64742-48-9','64742-82-1',
    '64741-41-9','64741-42-0','64741-44-2','64741-45-3','64741-47-5','64741-48-6',
    '64742-54-7','8052-41-3',
  ]);
  const OXIDIZING_CAS = new Set(['7722-84-1','7790-98-9','7775-09-9','7727-54-0']);
  const FLAM_SOL_CAS  = new Set(['7704-34-9','1333-86-4','12185-10-3']);

  // ── PİROFOR GAZ CAS LİSTESİ (H232) — CLP Ek I §2.2 ─────────────────────────
  // Havayla temas halinde kendiliğinden tutuşan gazlar
  const PYRO_GAS_CAS = new Set([
    '7803-62-5',   // Silan (SiH4)
    '19287-45-7',  // Diboran (B2H6)
    '7782-65-2',   // Jerman (GeH4)
    '7803-52-3',   // Stibin (SbH3)
    '13765-25-8',  // Diklorosilan (SiH2Cl2) — piroforic özelliği var
    '992-94-9',    // Metilsilan (CH3SiH3)
    '7784-42-1',   // Arsin (AsH3) — piroforic, H232
  ]);

  // ── HATA PAYI METAVERİSİ ─────────────────────────────────────────────────────
  // Her hesap metodu için literatür tabanlı belirsizlik değerleri
  const ERROR_META = {
    density: {
      base: 0.03,   // ±%3 — ideal karışım için
      polar: 0.06,  // ±%6 — polar/su içeren sistemler
      method: 'ρ<sub>mix</sub> = Σwᵢ / Σ(wᵢ/ρᵢ)',
      standard: 'ISO 2811',
      note: 'Polar karışımlarda (su > %20) hacim değişimi nedeniyle sapma ±%5-8 olabilir.',
    },
    vapor_pressure: {
      base: 0.20,   // ±%20 — ideal Raoult
      note: 'Raoult Yasası ideal çözeltileri varsayar; non-ideal sistemlerde sapma ±%30\'a çıkabilir.',
      method: 'p<sub>i</sub> = xᵢ · Pᵢ* (Raoult Yasası)',
      standard: '—',
    },
    lel: {
      base: 0.15,   // ±%15 — ISO 10156 standardındaki belirsizlik
      method: '1/LEL<sub>mix</sub> = Σ(yᵢ/LELᵢ) — Le Chatelier (ISO 10156)',
      standard: 'ISO 10156 / EN 1839',
      note: 'ISO 10156 standardında kabul edilen belirsizlik ±%15\'tir.',
    },
    uel: {
      base: 0.20,   // ±%20 — UEL daha az öngörülür
      method: '1/UEL<sub>mix</sub> = Σ(yᵢ/UELᵢ) — Le Chatelier',
      standard: 'ISO 10156 / EN 1839',
      note: 'Üst patlama sınırı (UEL) alt sınıra göre daha büyük belirsizlik taşır.',
    },
    vapor_density: {
      base: 0.02,   // ±%2 — MW biliniyorsa çok doğru
      method: 'VD = MW<sub>mix</sub> / 29',
      standard: 'Ideal gaz yaklaşımı',
      note: 'Moleküler ağırlık bilinen maddeler için yüksek doğruluk.',
    },
    boiling_point: {
      base: null,  // Mutlak hata değil — başlangıç KN yorumu
      method: 'IBP = min(KNᵢ) bileşenleri',
      standard: 'ASTM D86 / ISO 3924',
      note: 'Bu değer başlangıç kaynama noktasıdır (IBP). Gerçek karışım KN eğrisi için distilasyon testi gerekir.',
    },
  };

  // ── HATA PAYI HESAPLAYICI ─────────────────────────────────────────────────────
  // coverage: DB'deki bileşen yüzdesi (0-100)
  // hasWater: polar/su içeriyor mu
  function calcError(property, value, coverage, hasWater = false) {
    const meta = ERROR_META[property];
    if (!meta || meta.base === null) return null;

    let baseRate = meta.base;
    if (property === 'density' && hasWater) baseRate = meta.polar;

    // Düşük kapsama → belirsizliği artır
    let coverageMult = 1.0;
    if (coverage < 50)      coverageMult = 1.8;
    else if (coverage < 70) coverageMult = 1.4;
    else if (coverage < 85) coverageMult = 1.15;

    const rate = baseRate * coverageMult;
    const abs  = parseFloat((value * rate).toFixed(
      property === 'density' ? 3 :
      property === 'vapor_density' ? 2 :
      property === 'boiling_point' ? 1 : 1
    ));
    const pct  = Math.round(rate * 100);
    return { abs, pct, rate };
  }

  // ── TEORİK FİZİKSEL ÖZELLİKLER HESABI ───────────────────────────────────────
  function calcTheoProps(comps) {
    const rows = comps
      .map(c => ({ cas: (c.cas || '').trim(), w: (parseFloat(c.concMax || c.conc) || 0) / 100 }))
      .filter(r => r.w > 0);

    if (!rows.length) return null;

    let densNum = 0, densDenom = 0;
    let mwDenom = 0, totalW = 0;
    let minBP = null;
    const vpData    = [];
    const flamRows  = [];
    let hasWater    = false;
    let coveredW    = 0;

    for (const { cas, w } of rows) {
      const rho = DENSITY_DB[cas];
      const mw  = MW_DB[cas];
      const lel = LEL_DB[cas];
      const uel = UEL_DB[cas];
      const vp  = VP_DB[cas];
      const bp  = BP_DB[cas];

      if (cas === '7732-18-5' && w * 100 >= 20) hasWater = true;

      // Yoğunluk: ağırlık harmonik ortalaması
      if (rho != null) { densNum += w; densDenom += w / rho; coveredW += w; }

      // MW karışımı
      if (mw != null) { mwDenom += w / mw; totalW += w; }

      // Buhar basıncı (Raoult): mol mol sayısı × VP
      if (mw != null && vp != null) vpData.push({ n: w / mw, vp });

      // Kaynama noktası: en düşük bileşen (başlangıç KN)
      if (bp != null && w * 100 >= 1 && (minBP === null || bp < minBP)) minBP = bp;

      // LEL/UEL için: mol sayısı + VP + LEL + UEL tamamlanmış satırlar
      if (mw != null && vp != null && lel != null && uel != null && w > 0) {
        flamRows.push({ n: w / mw, vp, lel, uel });
      }
    }

    // DB kapsama yüzdesi
    const totalWAll = rows.reduce((s, r) => s + r.w, 0);
    const coverage  = totalWAll > 0 ? Math.round((coveredW / totalWAll) * 100) : 0;

    const res = { coverage, hasWater };

    // ── Yoğunluk ──────────────────────────────────────────────────────────────
    if (densDenom > 0) {
      const val = parseFloat((densNum / densDenom).toFixed(3));
      const err = calcError('density', val, coverage, hasWater);
      res.density = { value: val, error: err, ...ERROR_META.density };
    }

    // ── Buhar Yoğunluğu + Raoult Buhar Basıncı ────────────────────────────────
    if (mwDenom > 0 && totalW > 0) {
      const mwMix = totalW / mwDenom;
      const vdVal = parseFloat((mwMix / 29).toFixed(2));
      res.vapor_density = {
        value: vdVal,
        error: calcError('vapor_density', vdVal, coverage),
        ...ERROR_META.vapor_density,
      };

      if (vpData.length) {
        const totN  = vpData.reduce((s, e) => s + e.n, 0);
        const vpVal = parseFloat(vpData.reduce((s, e) => s + (e.n / totN) * e.vp, 0).toFixed(1));
        res.vapor_pressure = {
          value: vpVal,
          error: calcError('vapor_pressure', vpVal, coverage),
          ...ERROR_META.vapor_pressure,
        };
      }
    }

    // ── LEL / UEL — Raoult + Le Chatelier (ISO 10156) ─────────────────────────
    // Adım 1: Sıvı mol fraksiyonları (xᵢ = nᵢ / Σnⱼ)
    // Adım 2: Raoult → kısmi buhar basınçları (pᵢ = xᵢ · Pᵢ*)
    // Adım 3: Buhar fazı mol fraksiyonları (yᵢ = pᵢ / Σpⱼ)
    // Adım 4: Le Chatelier → 1/LEL_mix = Σ(yᵢ/LELᵢ)
    if (flamRows.length) {
      const totFlamN = flamRows.reduce((s, e) => s + e.n, 0);
      const withP    = flamRows.map(e => ({ ...e, p: (e.n / totFlamN) * e.vp }));
      const pTot     = withP.reduce((s, e) => s + e.p, 0);

      if (pTot > 0) {
        const vy     = withP.map(e => ({ ...e, y: e.p / pTot }));
        const lelInv = vy.reduce((s, e) => s + e.y / e.lel, 0);
        const uelInv = vy.reduce((s, e) => s + e.y / e.uel, 0);

        if (lelInv > 0) {
          const lelVal = parseFloat((1 / lelInv).toFixed(1));
          const uelVal = parseFloat((1 / uelInv).toFixed(1));
          res.lel = { value: lelVal, error: calcError('lel', lelVal, coverage), ...ERROR_META.lel };
          res.uel = { value: uelVal, error: calcError('uel', uelVal, coverage), ...ERROR_META.uel };
        }
      }
    }

    // ── Kaynama Noktası ────────────────────────────────────────────────────────
    if (minBP !== null) {
      res.boiling_point = { value: minBP, error: null, ...ERROR_META.boiling_point };
    }

    return res;
  }

  // ── TEHLİKE SINIFLANDIRMASI ───────────────────────────────────────────────────
  function clsFlamLiq(fp, bp) {
    if (fp < 23 && (bp === null || bp <= 35)) return { h:'H224', cat:1, label:'Flam. Liq. 1', signal:'Danger' };
    if (fp < 23) return { h:'H225', cat:2, label:'Flam. Liq. 2', signal:'Danger' };
    if (fp >= 23 && fp <= 60) return { h:'H226', cat:3, label:'Flam. Liq. 3', signal:'Warning' };
    return null;
  }

  function calcFlamLiq(comps, userFP) {
    if (userFP !== null && userFP !== undefined && !isNaN(userFP)) {
      return { result: clsFlamLiq(userFP, null), source:`Kullanıcı girişi (${userFP}°C)`, fp: userFP };
    }

    // CLP Annex I Tablo 2.6 — Toplamlı eşik yaklaşımı
    // Her kategori için konsantrasyonları topla; birden fazla bileşen birlikte eşiği geçebilir
    const catSum = { 1: 0, 2: 0, 3: 0 };
    const catTriggers = { 1: [], 2: [], 3: [] };
    const catFP = { 1: null, 2: null, 3: null };

    for (const c of comps) {
      const cas  = (c.cas || '').trim();
      const conc = parseFloat(c.concMax || c.conc) || 0;
      const fp   = FP_DB[cas];
      if (fp === undefined || fp === null || fp >= 60) continue;
      const bp  = BP_DB[cas] !== undefined ? BP_DB[cas] : null;
      const cls = clsFlamLiq(fp, bp);
      if (!cls) continue;
      catSum[cls.cat]     = (catSum[cls.cat] || 0) + conc;
      catFP[cls.cat]      = catFP[cls.cat] === null ? fp : Math.min(catFP[cls.cat], fp);
      catTriggers[cls.cat].push({ cas, name: c.name, conc, fp });
    }

    // CLP Annex I Tablo 2.6 kademeli eşik:
    //   Cat.1 : Σ(Cat.1)           ≥ %1
    //   Cat.2 : Σ(Cat.1 + Cat.2)   ≥ %1   (üst kategoriler de sayılır)
    //   Cat.3 : Σ(Cat.1+2+3)       ≥ %10  (tüm yanıcı bileşenler)
    const sum1   = catSum[1];
    const sum12  = catSum[1] + catSum[2];
    const sum123 = catSum[1] + catSum[2] + catSum[3];

    const allTriggers = [...catTriggers[1], ...catTriggers[2], ...catTriggers[3]];
    const minFPAll = [catFP[1], catFP[2], catFP[3]].filter(v => v !== null);
    const lowestFP = minFPAll.length ? Math.min(...minFPAll) : null;

    if (sum1 >= 1) {
      const src = catTriggers[1].map(t => `${t.name||t.cas} (%${t.conc}, FP=${t.fp}°C)`).join(' + ');
      return { result: { h:'H224', cat:1, label:'Flam. Liq. 1', signal:'Danger' }, source: src, fp: catFP[1] };
    }
    if (sum12 >= 1) {
      const triggers = [...catTriggers[1], ...catTriggers[2]];
      const src = triggers.map(t => `${t.name||t.cas} (%${t.conc}, FP=${t.fp}°C)`).join(' + ');
      return { result: { h:'H225', cat:2, label:'Flam. Liq. 2', signal:'Danger' }, source: src, fp: Math.min(...[catFP[1],catFP[2]].filter(v=>v!==null)) };
    }
    if (sum123 >= 10) {
      const src = allTriggers.map(t => `${t.name||t.cas} (%${t.conc}, FP=${t.fp}°C)`).join(' + ');
      return { result: { h:'H226', cat:3, label:'Flam. Liq. 3', signal:'Warning' }, source: src, fp: lowestFP };
    }
    return { result: null, source: null, fp: null };
  }

  // ── H232 — Pirofor Gaz (CLP Ek I §2.2.3) ────────────────────────────────────
  // Bileşen H232 içeriyorsa VEYA bilinen pirofor CAS listesindeyse:
  //   konsantrasyon ≥ %1 → karışım H220 (Flam. Gas 1A) + H232 alır
  function calcFlamGas(comps) {
    const triggers = [];
    for (const c of comps) {
      const cas  = (c.cas || '').trim();
      const conc = parseFloat(c.concMax || c.conc) || 0;
      if (conc < 1.0) continue;
      const hasH232 = (c.hazards || []).some(h =>
        (h.h_code || '').replace(/[*\s]/g,'').substring(0,4) === 'H232'
      );
      if (hasH232 || PYRO_GAS_CAS.has(cas)) {
        triggers.push({ cas, name: c.name || cas, conc });
      }
    }
    if (triggers.length) return {
      result_h220: { h:'H220', label:'Flam. Gas 1A', signal:'Danger' },
      result_h232: { h:'H232', label:'Flam. Gas 1A — Pirofor', signal:'Danger' },
      source: triggers.map(t => `${t.name} (%${t.conc})`).join(', '),
    };
    return { result_h220: null, result_h232: null, source: null };
  }

  function calcAspTox(comps, testData = {}) {
    // ── CLP Ek I §3.10.4 Viskozite Filtresi ─────────────────────────────────
    // Karışımın kinematik viskozitesi > 20.5 mm²/s (40°C) ise H304 uygulanmaz.
    // testData.viscosity değeri kinematik viskozite (mm²/s = cSt) olarak kabul edilir.
    // Değer girilmemişse kural muhafazakâr şekilde uygulanır (H304 eklenir).
    const kinVisc = testData.viscosity != null ? parseFloat(testData.viscosity) : null;
    if (kinVisc !== null && !isNaN(kinVisc) && kinVisc > 20.5) {
      return {
        result: null,
        source: `Kinematik viskozite ${kinVisc} mm²/s > 20.5 mm²/s — CLP §3.10.4 gereği H304 uygulanmaz`,
        total: 0,
        viscosityExcluded: true,
      };
    }

    let total = 0;
    const triggers = [];
    for (const c of comps) {
      const cas  = (c.cas || '').trim();
      const conc = parseFloat(c.concMax || c.conc) || 0;
      const inList   = ASP_CAS.has(cas);
      const hasClass = (c.hazards || []).some(h => h.h_class === 'Asp. Tox. 1');
      if ((inList || hasClass) && conc > 0) { triggers.push({ cas, name: c.name, conc }); total += conc; }
    }
    if (total >= 10) {
      const viscNote = kinVisc === null
        ? ' (viskozite girilmedi — doğrulayın)'
        : '';
      return {
        result: { h:'H304', label:'Asp. Tox. 1', signal:'Danger' },
        source: triggers.map(t => `${t.name || t.cas} (%${t.conc})`).join(', ') + viscNote,
        total,
      };
    }
    return { result: null, source: null, total };
  }

  // ── TEST VERİSİ → TEORİK ÜZERINE YAZAR ──────────────────────────────────────
  // testData: { density, boiling_point, ph, viscosity, solubility } — kullanıcı girişi
  function applyTestData(theoProps, testData) {
    if (!theoProps || !testData) return theoProps;
    const out = { ...theoProps };

    const meas = (value, standard, note) => ({
      value, measured: true,
      method: 'Kullanıcı girişi (ölçülen/beyan değer)',
      standard, note: note || 'Test verisinden alındı.',
      error: null,
    });

    // ── Motor ile hesaplanan, override edilebilir alanlar ──
    if (testData.density != null)
      out.density       = meas(testData.density,       'ISO 2811 / ASTM D4052',  'Ölçülen değer — teorik hesap devre dışı.');
    if (testData.boiling_point != null)
      out.boiling_point = meas(testData.boiling_point, 'ASTM D86 / ISO 3924');
    if (testData.ph != null)
      out.ph            = meas(testData.ph,            'ISO 4316 / ASTM E70');
    if (testData.viscosity != null)
      out.viscosity     = meas(testData.viscosity,     'ISO 3219 / ASTM D2196',  'Dinamik viskozite.');
    if (testData.solubility != null)
      out.solubility    = meas(testData.solubility,    'OECD 105');
    if (testData.flash_point != null)
      out.flash_point   = meas(testData.flash_point,   'ISO 2719 / ASTM D93',    'Ölçülen değer — DB değeri devre dışı.');

    // ── Yalnızca kullanıcı girer (motor hesaplamaz) ──────
    if (testData.appearance)
      out.appearance    = { value: testData.appearance,  measured: true, method: 'Gözlem', standard: 'REACH Ek II §9' };
    if (testData.odor)
      out.odor          = { value: testData.odor,         measured: true, method: 'Duyusal test', standard: 'REACH Ek II §9' };
    if (testData.odor_threshold != null)
      out.odor_threshold = meas(testData.odor_threshold, 'EN 13725');
    if (testData.melting_point != null)
      out.melting_point  = meas(testData.melting_point,  'ISO 1218 / ASTM D97');
    if (testData.auto_ignition != null)
      out.auto_ignition  = meas(testData.auto_ignition,  'EN 14522 / ASTM E659');
    if (testData.decomp_temp != null)
      out.decomp_temp    = meas(testData.decomp_temp,    'ISO 11357 / DSC analizi');
    if (testData.log_kow != null)
      out.log_kow        = meas(testData.log_kow,        'OECD 117 / 107');
    if (testData.evap_rate)
      out.evap_rate      = { value: testData.evap_rate,  measured: true, method: 'Beyan değer', standard: 'ASTM D3539' };
    if (testData.flam_sg)
      out.flam_sg        = { value: testData.flam_sg,    measured: true, method: 'Beyan değer', standard: 'CLP Annex I' };
    if (testData.explosive)
      out.explosive      = { value: testData.explosive,  measured: true, method: 'Beyan değer', standard: 'CLP Annex I' };
    if (testData.oxidizing)
      out.oxidizing      = { value: testData.oxidizing,  measured: true, method: 'Beyan değer', standard: 'CLP Annex I' };
    if (testData.sol_other)
      out.sol_other      = { value: testData.sol_other,  measured: true, method: 'Beyan değer', standard: 'REACH Ek II §9' };

    return out;
  }

  function calculate(comps, form = 'liquid', userFP = null, testData = {}) {
    const primary = [], extra = [], warnings = [];

    // Yanıcı Sıvı
    const fl = calcFlamLiq(comps, userFP);
    if (fl.result) primary.push({ type:'flam_liq', ...fl.result, source: fl.source, fp: fl.fp });

    // Aspirasyon Toksisitesi — viskozite kontrolü dahil (CLP §3.10.4)
    const asp = calcAspTox(comps, testData);
    if (asp.result) primary.push({ type:'asp_tox', ...asp.result, source: asp.source, total: asp.total });
    if (asp.viscosityExcluded) warnings.push('H304: ' + asp.source);

    // Pirofor Gaz — H232 (CLP Ek I §2.2.3)
    const fg = calcFlamGas(comps);
    if (fg.result_h232) {
      primary.push({ type:'flam_gas', ...fg.result_h220, source: fg.source });
      primary.push({ type:'flam_gas_pyro', ...fg.result_h232, source: fg.source });
    }

    // Yanıcı Katı
    const fs = comps.filter(c => FLAM_SOL_CAS.has((c.cas||'').trim()) && (parseFloat(c.concMax||c.conc)||0) >= 1);
    if (fs.length) extra.push({ type:'flam_sol', h:'H228', label:'Flam. Sol. 2', signal:'Warning', source: fs.map(c => c.name||c.cas).join(', ') });

    // Oksitleyici
    const ox = comps.filter(c => OXIDIZING_CAS.has((c.cas||'').trim()) && (parseFloat(c.concMax||c.conc)||0) >= 1);
    if (ox.length) extra.push({ type:'oxidizing', h:'H272', label:'Ox. Liq. 3', signal:'Warning', source: ox.map(c => c.cas).join(', ') });

    // Teorik fiziksel özellikler (Bölüm 9)
    let theoProps = (form === 'liquid' || form === 'paste' || form === 'aerosol')
      ? calcTheoProps(comps)
      : null;

    // Test verisi varsa teorik değerlerin üzerine yaz
    if (theoProps && testData && Object.keys(testData).length > 0) {
      theoProps = applyTestData(theoProps, testData);
    } else if (!theoProps && testData && Object.keys(testData).length > 0) {
      // Sıvı olmayan formda bile test verisi varsa göster
      theoProps = applyTestData({ coverage: 0, hasWater: false }, testData);
    }

    // Parlama noktasını theoProps'a ekle (Bölüm 9 modal için)
    if (theoProps) {
      if (testData && testData.flash_point != null) {
        theoProps.flash_point = {
          value: testData.flash_point,
          measured: true,
          method: 'Kullanıcı girişi (ölçülen değer)',
          standard: 'ISO 2719 / ASTM D93',
          note: 'Test verisinden alındı.',
        };
      } else if (fl.fp != null) {
        theoProps.flash_point = {
          value: fl.fp,
          measured: false,
          method: fl.source || 'DB sorgusu',
          standard: 'CLP Annex VI / NIST WebBook',
          note: fl.result ? `Sınıflandırma: ${fl.result.label} (${fl.result.h})` : '',
        };
      } else {
        theoProps.flash_point = {
          value: null, measured: false,
          method: 'DB sorgusu',
          standard: 'CLP Annex VI / NIST WebBook',
          note: 'Parlama noktası yok (yanmaz madde)',
        };
      }
    }

    const results = [...primary, ...extra];
    return { results, primary, extra, warnings, theoProps };
  }

  function init() {
    if (typeof EventBus !== 'undefined') {
      EventBus.on('PHYSICAL_CALCULATE', ({ comps, form, userFP, testData }) => {
        const result = calculate(comps, form, userFP, testData || {});
        EventBus.emit('PHYSICAL_READY', result);
      });
    }
    console.log('[PhysicalEngine] init OK — Teorik modül + hata payı + test verisi aktif');
  }

  return { init, calculate, calcTheoProps, DENSITY_DB, MW_DB, VP_DB, LEL_DB, UEL_DB };
})();
