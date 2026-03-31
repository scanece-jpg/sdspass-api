/**
 * TransportEngine — ADR/IMDG/IATA — SDS Bölüm 14
 * Kaynak: ADR 2023 Tablo 3.1, IMDG Kod 2022, IATA-DGR 2024
 *         ADR 2.1.3.5.4 — Çoklu tehlike öncelik tablosu (Tablo 2.1.3.10)
 *
 * Girdi : hCodes[], form ('liquid'|'solid'|'aerosol')
 * Çıktı : { road{}, sea{}, air{}, not_regulated }
 *
 * Events: dinler  → H_CODES_READY { hCodes }
 *         emit eder → TRANSPORT_READY { road, sea, air, not_regulated }
 */
const TransportEngine = (() => {

  const CLASS_LABELS = {
    '1':'Patlayıcı Maddeler', '2.1':'Yanıcı Gazlar', '2.2':'Yanıcı Olmayan Gazlar',
    '3':'Yanıcı Sıvılar', '4.1':'Yanıcı Katılar', '4.2':'Kendiliğinden Alışan Maddeler',
    '4.3':'Su ile Tepkiyen Maddeler', '5.1':'Oksitleyici Maddeler', '5.2':'Organik Peroksitler',
    '6.1':'Zehirli Maddeler', '6.2':'Bulaşıcı Maddeler', '7':'Radyoaktif Maddeler',
    '8':'Aşındırıcı Maddeler', '9':'Çeşitli Tehlikeli Maddeler ve Nesneler',
  };

  // ── Kombinasyon kuralları — ADR 2023 Tablo 2.1.3.10 öncelik sırası ──────────
  // Öncelik: 1 > 2 > 4.2 > 4.3 > 5.1 > 5.2 > 6.1 > 3 > 8 > 9
  // ÖNEMLİ: Daha yüksek öncelikli / daha spesifik kurallar ÖNCE gelmelidir
  // un_liquid / un_solid: form'a göre seçilir; ikisi aynıysa sadece un kullanılır
  // label_liquid / label_solid: UN etiket adı (form'a göre)
  const COMBO_RULES = [
    // ── Sınıf 1: Patlayıcı — her şeyin önünde ───────────────────────────────
    {
      must:['H200','H201','H202','H203','H204','H205'],
      un:'UN 0000*', class:'1', pg:null,
      label:'Patlayıcı',
      note:'UN numarası maddeye özgü belirlenir; patlayıcı sınıfı tüm yan tehlikeleri ezer',
    },
    // ── Sınıf 5.2: Organik Peroksit — yüksek öncelik ────────────────────────
    {
      must:['H241'], any:['H224','H225','H226','H314','H300','H310','H330'],
      un:'UN 3105', class:'5.2', pg:null,
      label:'Organik Peroksit, Tip D, E, F, Sıvı',
      note:'ADR 2023 Sınıf 5.2 — Tam tip belirlenmesi (A-G) uzman laboratuvarı gerektirir; UN3105 varsayılan',
    },
    // ── Sınıf 8+5.1: Korozif + Oksitleyici ─────────────────────────────────
    {
      must:['H314'], any:['H271'],
      un:'UN 3093', class:'8', pg:'I',
      label:'Korozif Sıvı, Oksitleyici, B.N.O.',
      sub_class:'5.1',
      note:'ADR 2023: H314 + H271 kombinasyonu — yan tehlike Sınıf 5.1',
    },
    {
      must:['H314'], any:['H272'],
      un:'UN 3093', class:'8', pg:'II',
      label:'Korozif Sıvı, Oksitleyici, B.N.O.',
      sub_class:'5.1',
      note:'ADR 2023: H314 + H272 kombinasyonu — yan tehlike Sınıf 5.1',
    },
    // ── Sınıf 3+8: Yanıcı Sıvı + Korozif — ADR: UN 2924 ─────────────────────
    // H224/H225/H226 = sıvı H kodu → bu combo sadece sıvı için geçerli
    {
      must:['H314'], any:['H224'],
      un:'UN 2924', class:'3', pg:'I',
      label:'Yanıcı Sıvı, Korozif, B.N.O.',
      sub_class:'8',
      note:'ADR 2023: Yanıcı sıvı (kat.1) + Korozif kombinasyonu — yan tehlike Sınıf 8',
    },
    {
      must:['H314'], any:['H225'],
      un:'UN 2924', class:'3', pg:'II',
      label:'Yanıcı Sıvı, Korozif, B.N.O.',
      sub_class:'8',
      note:'ADR 2023: Yanıcı sıvı (kat.2) + Korozif kombinasyonu — yan tehlike Sınıf 8',
    },
    {
      must:['H314'], any:['H226'],
      un:'UN 2924', class:'3', pg:'III',
      label:'Yanıcı Sıvı, Korozif, B.N.O.',
      sub_class:'8',
      note:'ADR 2023: Yanıcı sıvı (kat.3) + Korozif kombinasyonu — yan tehlike Sınıf 8',
    },
    // ── Sınıf 6.1+8: Toksik + Korozif — liquid: UN 2927 / solid: UN 2928 ────
    {
      must:['H314'], any:['H300','H310','H330'],
      un_liquid:'UN 2927', un_solid:'UN 2928', class:'6.1', pg:'I',
      label_liquid:'Zehirli Sıvı, Korozif, Organik B.N.O.',
      label_solid:'Zehirli Katı, Korozif, Organik B.N.O.',
      sub_class:'8',
      note:'Organik yapı için UN 2927/2928; inorganik için UN 3289/3290 — uzman onayı gerekir',
    },
    {
      must:['H314'], any:['H301','H311','H331'],
      un_liquid:'UN 2927', un_solid:'UN 2928', class:'6.1', pg:'II',
      label_liquid:'Zehirli Sıvı, Korozif, Organik B.N.O.',
      label_solid:'Zehirli Katı, Korozif, Organik B.N.O.',
      sub_class:'8',
      note:'Organik yapı için UN 2927/2928; inorganik için UN 3289/3290',
    },
    // ── Sınıf 3+6.1: Yanıcı Sıvı + Toksik ──────────────────────────────────
    // H224 (kat.1 yanıcı) + Toksik kat.1 → PG I
    {
      must:['H224'], any:['H300','H310','H330'],
      un:'UN 1992', class:'3', pg:'I',
      label:'Yanıcı Sıvı, Toksik, B.N.O.',
      sub_class:'6.1',
      note:'ADR 2023: Yanıcı sıvı (kat.1) + Toksik (kat.1-2) kombinasyonu',
    },
    // H225 (kat.2 yanıcı) + Toksik kat.1 → PG II
    {
      must:['H225'], any:['H300','H310','H330'],
      un:'UN 1992', class:'3', pg:'II',
      label:'Yanıcı Sıvı, Toksik, B.N.O.',
      sub_class:'6.1',
      note:'ADR 2023: Yanıcı sıvı (kat.2) + Toksik (kat.1-2) kombinasyonu',
    },
    // H224/H225 + Toksik kat.3 → PG II
    {
      must:['H224'], any:['H301','H311','H331'],
      un:'UN 1992', class:'3', pg:'II',
      label:'Yanıcı Sıvı, Toksik, B.N.O.',
      sub_class:'6.1',
      note:'ADR 2023: Yanıcı sıvı (kat.1) + Toksik (kat.3) kombinasyonu',
    },
    {
      must:['H225'], any:['H301','H311','H331'],
      un:'UN 1992', class:'3', pg:'II',
      label:'Yanıcı Sıvı, Toksik, B.N.O.',
      sub_class:'6.1',
      note:'ADR 2023: Yanıcı sıvı (kat.2) + Toksik (kat.3) kombinasyonu',
    },
    // H226 (kat.3 yanıcı) + herhangi toksik → PG III
    {
      must:['H226'], any:['H300','H310','H330','H301','H311','H331'],
      un:'UN 1992', class:'3', pg:'III',
      label:'Yanıcı Sıvı, Toksik, B.N.O.',
      sub_class:'6.1',
      note:'ADR 2023: Yanıcı sıvı (kat.3) + Toksik kombinasyonu',
    },
  ];

  // ── Tekil kurallar — form'a göre UN seçimi ───────────────────────────────
  // un_liquid / un_solid: yoksa un kullanılır
  // label_liquid / label_solid: yoksa label kullanılır
  const RULES = [
    // Sınıf 5.2 — Organik Peroksit
    { hCodes:['H241'], un:'UN 3105', class:'5.2', pg:null,
      label:'Organik Peroksit, Tip D, E, F, Sıvı',
      note:'ADR Sınıf 5.2 — Tip belirlenmesi (A-G) gereklidir; UN3105 Tip D/E/F varsayılan' },
    { hCodes:['H242'], un:'UN 3109', class:'5.2', pg:null,
      label:'Organik Peroksit, Tip F, Sıvı',
      note:'ADR Sınıf 5.2 — Tip G ise düzenlemeye tabi değildir; uzman onayı gerekir' },
    // Sınıf 4.2 — Pirofor ve Kendiliğinden Isınan
    { hCodes:['H250'], un:'UN 2845', class:'4.2', pg:'I',
      label:'Pirofor Sıvı, Organik, B.N.O.',
      note:'H250: Hava temasında kendiliğinden alışır — PG I, özel ambalaj gerekir' },
    { hCodes:['H251'], un:'UN 3088', class:'4.2', pg:'II',
      label:'Kendiliğinden Isınan Katı, Organik, B.N.O.' },
    { hCodes:['H252'], un:'UN 3190', class:'4.2', pg:'III',
      label:'Kendiliğinden Isınan Katı, Organik, B.N.O.' },
    // Sınıf 2.2(O) — Oksitleyici Gaz
    { hCodes:['H270'], un:'UN 3156', class:'2.2', pg:null,
      label:'Sıkıştırılmış Gaz, Oksitleyici, B.N.O.',
      note:'ADR Sınıf 2.2 (oksitleyici) — basınç altındaki gaz; tüp/tank için özel kural geçerlidir' },
    // Sınıf 2.1 — Yanıcı Gaz
    { hCodes:['H220','H221'], un:'UN 1954', class:'2.1', pg:null,
      label:'Yanıcı Gaz, B.N.O.',
      note:'Maddeye özgü UN numarası (ör. UN1978 propan, UN1002 asetilen) önceliklidir' },
    // Sınıf 5.1 — Oksitleyici Sıvı/Katı
    { hCodes:['H271'], un:'UN 2912', class:'5.1', pg:'I',   label:'Oksitleyici Sıvı, B.N.O.' },
    { hCodes:['H272'], un:'UN 3139', class:'5.1', pg:'II',  label:'Oksitleyici Sıvı, B.N.O.' },
    // Sınıf 4.3 — Su ile Tepkiyen
    { hCodes:['H260'], un:'UN 3148', class:'4.3', pg:'I',   label:'Su ile Tepkiyen Sıvı, B.N.O.' },
    { hCodes:['H261'], un:'UN 3148', class:'4.3', pg:'II',  label:'Su ile Tepkiyen Sıvı, B.N.O.' },
    // Sınıf 6.1 — Akut Toksisite — SIVI: UN2810 / KATI: UN2811
    { hCodes:['H300','H310','H330'],
      un_liquid:'UN 2810', un_solid:'UN 2811', class:'6.1', pg:'I',
      label_liquid:'Zehirli Sıvı, Organik, B.N.O.',
      label_solid:'Zehirli Katı, Organik, B.N.O.',
      note:'UN 2810/2811 organik bileşikler için; inorganik → UN 3287/3288' },
    { hCodes:['H301','H311','H331'],
      un_liquid:'UN 2810', un_solid:'UN 2811', class:'6.1', pg:'II',
      label_liquid:'Zehirli Sıvı, Organik, B.N.O.',
      label_solid:'Zehirli Katı, Organik, B.N.O.',
      note:'UN 2810/2811 organik bileşikler için; inorganik → UN 3287/3288' },
    { hCodes:['H302','H312','H332'],
      un_liquid:'UN 2810', un_solid:'UN 2811', class:'6.1', pg:'III',
      label_liquid:'Zehirli Sıvı, Organik, B.N.O.',
      label_solid:'Zehirli Katı, Organik, B.N.O.',
      note:'Akut toksisite Kat.4 — ADR Sınıf 6.1 PG III; madde ADR kriterini sağlamazsa düzenlemeye tabi olmayabilir' },
    // Sınıf 8 — Korozif — SIVI: UN1760 / KATI: UN1759
    { hCodes:['H314'],
      un_liquid:'UN 1760', un_solid:'UN 1759', class:'8', pg:'II',
      label_liquid:'Korozif Sıvı, B.N.O.',
      label_solid:'Korozif Katı, B.N.O.',
      note:'Asidik inorganik sıvı → UN 3264 | Bazik → UN 3266 | Organik → UN 1760 | Katı → UN 1759 | PG I için uzman onayı' },
    // Sınıf 3 — Yanıcı Sıvı (H224/H225/H226 zaten sıvı kodları)
    { hCodes:['H224'], un:'UN 1993', class:'3', pg:'I',   label:'Yanıcı Sıvı, B.N.O.' },
    { hCodes:['H225'], un:'UN 1993', class:'3', pg:'II',  label:'Yanıcı Sıvı, B.N.O.' },
    { hCodes:['H226'], un:'UN 1993', class:'3', pg:'III', label:'Yanıcı Sıvı, B.N.O.' },
    // Sınıf 4.1 — Yanıcı Katı (H228 = sadece katı kodudur)
    { hCodes:['H228'], un:'UN 1325', class:'4.1', pg:'II',
      label:'Yanıcı Katı, Organik, B.N.O.',
      note:'ADR Sınıf 4.1 — Maddeye özgü UN numarası önceliklidir; PG I/III için uzman onayı' },
    // Sınıf 9 — Aspirasyon tehlikesi
    { hCodes:['H304'], un:'UN 3082', class:'9', pg:'III', label:'Çeşitli Tehlikeli Madde, B.N.O.' },
    // Sınıf 9 — Çevre tehlikesi — SIVI: UN3082 / KATI: UN3077
    { hCodes:['H400','H410','H411','H412'],
      un_liquid:'UN 3082', un_solid:'UN 3077', class:'9', pg:'III',
      label_liquid:'Çevre için Tehlikeli Madde, Sıvı, B.N.O.',
      label_solid:'Çevre için Tehlikeli Madde, Katı, B.N.O.' },
  ];

  function classify(hCodes, form) {
    const isSolid = (form || 'liquid') === 'solid';
    const hSet = new Set(hCodes.map(h => h.replace(/[*\s]/g,'').substring(0,4)));

    // 1) Kombinasyon kurallarını önce dene
    let matched = null;
    for (const rule of COMBO_RULES) {
      const mustMatch = (rule.must || []).some(h => hSet.has(h));
      const anyMatch  = !rule.any || rule.any.some(h => hSet.has(h));
      if (mustMatch && anyMatch) { matched = rule; break; }
    }

    // 2) Kombinasyon eşleşmediyse tekil kuralları dene
    if (!matched) {
      for (const rule of RULES) {
        if (rule.hCodes.some(h => hSet.has(h))) { matched = rule; break; }
      }
    }

    if (!matched) {
      return {
        not_regulated: true,
        road: null, sea: null, air: null,
        note: 'Bu madde/karışım tehlikeli madde olarak sınıflandırılmamıştır.',
      };
    }

    // Form'a göre UN ve etiket seç
    const un    = isSolid
      ? (matched.un_solid    || matched.un    || '')
      : (matched.un_liquid   || matched.un    || '');
    const label = isSolid
      ? (matched.label_solid  || matched.label || '')
      : (matched.label_liquid || matched.label || '');

    const subClass = matched.sub_class
      ? ` (Yan Tehlike: Sınıf ${matched.sub_class})`
      : '';

    const entry = {
      un,
      class:       matched.class,
      class_label: (CLASS_LABELS[matched.class] || matched.class) + subClass,
      pg:          matched.pg,
      label,
      sub_class:   matched.sub_class || null,
      note:        matched.note || null,
      env_mark:    hSet.has('H400') || hSet.has('H410') || hSet.has('H411') || hSet.has('H412'),
    };

    return {
      not_regulated: false,
      road: { ...entry, regulation: 'ADR 2023' },
      sea:  { ...entry, regulation: 'IMDG Kod 2022' },
      air:  { ...entry, regulation: 'IATA-DGR 2024' },
    };
  }

  function init() {
    if (typeof EventBus !== 'undefined') {
      EventBus.on('H_CODES_READY', (data) => {
        const result = classify(data.hCodes, data.form);
        EventBus.emit('TRANSPORT_READY', result);
      });
    }
    console.log('[TransportEngine] init OK');
  }

  return { init, classify };
})();
