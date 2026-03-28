/**
 * TransportEngine — ADR/IMDG/IATA — SDS Bölüm 14
 * Kaynak: ADR 2023 Tablo 3.1, IMDG Kod 2022, IATA-DGR 2024
 *         ADR 2.1.3.5.4 — Çoklu tehlike öncelik tablosu (Tablo 2.1.3.10)
 *
 * Girdi : hCodes[], physProps{}
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

  // ── Kombinasyon kuralları — ADR Tablo 2.1.3.10 öncelik sırası ──────────────
  // Çoklu tehlike varlığında ÖNCE bu kombinasyonlar kontrol edilir
  // ÖNEMLİ: Daha spesifik/yüksek öncelikli kurallar ÖNCE gelmelidir
  const COMBO_RULES = [
    // Patlayıcı her şeyin önünde
    {
      must:['H200','H201','H202','H203','H204','H205'],
      un:'UN 0000*', class:'1', pg:null,
      label:'Patlayıcı',
      note:'UN numarası maddeye özgü belirlenir; patlayıcı sınıfı tüm yan tehlikeleri ezer',
    },
    // Korozif + Oksitleyici (Kat.1) — ADR: UN 3093
    // NOT: Bu kural Toksik+Korozif kuralından ÖNCE gelmeli; oksitleyici özellik belirleyicidir
    {
      must:['H314'], any:['H271'],
      un:'UN 3093', class:'8', pg:'I',
      label:'Korozif Sıvı, Oksitleyici, B.N.O.',
      sub_class:'5.1',
      note:'ADR 2023: H314 + H271 kombinasyonu — yan tehlike Sınıf 5.1',
    },
    // Korozif + Oksitleyici (Kat.2-3) — ADR: UN 3093
    // NOT: HNO3 karışımları (H314+H272+H331) buraya düşmeli — UN 3093 doğru
    {
      must:['H314'], any:['H272'],
      un:'UN 3093', class:'8', pg:'II',
      label:'Korozif Sıvı, Oksitleyici, B.N.O.',
      sub_class:'5.1',
      note:'ADR 2023: H314 + H272 kombinasyonu — yan tehlike Sınıf 5.1',
    },
    // Toksik (Kat.1-2) + Korozif — ADR Tablo 3.1: UN 2927 / UN 2928
    {
      must:['H314'], any:['H300','H310','H330'],
      un:'UN 2927', class:'6.1', pg:'I',
      label:'Zehirli Sıvı, Korozif, Organik B.N.O.',
      sub_class:'8',
      note:'Organik yapı için UN 2927; inorganik yapı için UN 3289 kullanın — uzman onayı gerekir',
    },
    // Toksik (Kat.3) + Korozif
    {
      must:['H314'], any:['H301','H311','H331'],
      un:'UN 2927', class:'6.1', pg:'II',
      label:'Zehirli Sıvı, Korozif, Organik B.N.O.',
      sub_class:'8',
      note:'Organik yapı için UN 2927; inorganik yapı için UN 3289 kullanın',
    },
    // Yanıcı + Toksik (Kat.1-2) — Öncelik tabloya göre değişir; yan tehlike belirt
    {
      must:['H225','H224'], any:['H300','H310','H330'],
      un:'UN 1992', class:'3', pg:'I',
      label:'Yanıcı Sıvı, Toksik, B.N.O.',
      sub_class:'6.1',
      note:'ADR 2023: Yanıcı + Toksik kombinasyonu',
    },
  ];

  // ── Tekil kurallar — öncelik sırası (ADR Tablo 2.1.3.10) ───────────────────
  const RULES = [
    // Oksitleyici Kat.1
    { hCodes:['H271'], un:'UN 2912', class:'5.1', pg:'I',   label:'Oksitleyici Sıvı' },
    // Oksitleyici Kat.2-3
    { hCodes:['H272'], un:'UN 3139', class:'5.1', pg:'II',  label:'Oksitleyici Sıvı' },
    // Yanıcı Gazlar
    { hCodes:['H220','H221'], un:'UN 1978', class:'2.1', pg:null, label:'Yanıcı Gaz' },
    // Su ile tepkime
    { hCodes:['H260'], un:'UN 3148', class:'4.3', pg:'I',   label:'Su ile Tepkiyen Sıvı' },
    { hCodes:['H261'], un:'UN 3148', class:'4.3', pg:'II',  label:'Su ile Tepkiyen Sıvı' },
    // Akut Toksisite Kat.1-2 — NOT: UN 2810 SADECE organik; inorganik → UN 3287
    { hCodes:['H300','H310','H330'], un:'UN 2810', class:'6.1', pg:'I',
      label:'Zehirli Sıvı B.N.O.',
      note:'UN 2810 organik bileşikler için; inorganik toksik sıvı ise UN 3287 kullanın' },
    // Akut Toksisite Kat.3 — NOT: UN 2810 SADECE organik
    { hCodes:['H301','H311','H331'], un:'UN 2810', class:'6.1', pg:'II',
      label:'Zehirli Sıvı B.N.O.',
      note:'UN 2810 organik bileşikler için; inorganik toksik sıvı ise UN 3287 kullanın' },
    // Akut Toksisite Kat.4
    { hCodes:['H302','H312','H332'], un:'UN 3077', class:'9', pg:'III',
      label:'Çeşitli Tehlikeli Madde' },
    // Cilt Korozif — asidik inorganik → UN 3264, bazik inorganik → UN 3266
    { hCodes:['H314'], un:'UN 1760', class:'8', pg:'II',
      label:'Korozif Sıvı B.N.O.',
      note:'Asidik inorganik → UN 3264 | Bazik inorganik → UN 3266 | Organik → UN 1760 — uzman onayı' },
    // Yanıcı Sıvı Kat.1
    { hCodes:['H224'], un:'UN 1993', class:'3', pg:'I',   label:'Yanıcı Sıvı B.N.O.' },
    // Yanıcı Sıvı Kat.2
    { hCodes:['H225'], un:'UN 1993', class:'3', pg:'II',  label:'Yanıcı Sıvı B.N.O.' },
    // Yanıcı Sıvı Kat.3
    { hCodes:['H226'], un:'UN 1993', class:'3', pg:'III', label:'Yanıcı Sıvı B.N.O.' },
    // Aspirasyon tehlikesi
    { hCodes:['H304'], un:'UN 3082', class:'9', pg:'III', label:'Çeşitli Tehlikeli Madde' },
    // Çevre tehlikesi
    { hCodes:['H400','H410','H411','H412'], un:'UN 3082', class:'9', pg:'III',
      label:'Çevre için Tehlikeli Madde B.N.O.' },
  ];

  function classify(hCodes) {
    const hSet = new Set(hCodes.map(h => h.replace(/[*\s]/g,'').substring(0,4)));

    // 1) Kombinasyon kurallarını önce dene
    let matched = null;
    let isCombo = false;
    for (const rule of COMBO_RULES) {
      const mustMatch = (rule.must || []).some(h => hSet.has(h));
      const anyMatch  = !rule.any || rule.any.some(h => hSet.has(h));
      if (mustMatch && anyMatch) {
        matched  = rule;
        isCombo  = true;
        break;
      }
    }

    // 2) Kombinasyon eşleşmediyse tekil kuralları dene
    if (!matched) {
      for (const rule of RULES) {
        if (rule.hCodes.some(h => hSet.has(h))) {
          matched = rule;
          break;
        }
      }
    }

    if (!matched) {
      return {
        not_regulated: true,
        road: null, sea: null, air: null,
        note: 'Bu madde/karışım tehlikeli madde olarak sınıflandırılmamıştır.',
      };
    }

    // Yan tehlike sınıfı (kombinasyon kuralı varsa)
    const subClass = matched.sub_class
      ? ` (Yan Tehlike: Sınıf ${matched.sub_class})`
      : '';

    const entry = {
      un:          matched.un,
      class:       matched.class,
      class_label: (CLASS_LABELS[matched.class] || matched.class) + subClass,
      pg:          matched.pg,
      label:       matched.label,
      sub_class:   matched.sub_class || null,
      note:        matched.note || null,
    };

    // Çevre tehlikesi işareti
    const envMark = hSet.has('H400') || hSet.has('H410') || hSet.has('H411') || hSet.has('H412');

    return {
      not_regulated: false,
      road: { ...entry, regulation: 'ADR 2023', env_mark: envMark },
      sea:  { ...entry, regulation: 'IMDG Kod 2022', env_mark: envMark },
      air:  { ...entry, regulation: 'IATA-DGR 2024', env_mark: envMark },
    };
  }

  function init() {
    if (typeof EventBus !== 'undefined') {
      EventBus.on('H_CODES_READY', (data) => {
        const result = classify(data.hCodes);
        EventBus.emit('TRANSPORT_READY', result);
      });
    }
    console.log('[TransportEngine] init OK');
  }

  return { init, classify };
})();
