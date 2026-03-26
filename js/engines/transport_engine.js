/**
 * TransportEngine — ADR/IMDG/IATA — SDS Bölüm 14
 * Girdi : hCodes[], physProps{}
 * Çıktı : { road{}, sea{}, air{}, not_regulated }
 *
 * Events: dinler  → H_CODES_READY { hCodes }
 *         emit eder → TRANSPORT_READY { road, sea, air, not_regulated }
 */
const TransportEngine = (() => {

  // UN numarası, ADR sınıf, PG kuralları
  // Öncelik sırası: ilk eşleşen kazanır
  const RULES = [
    // Patlayıcılar
    { hCodes:['H200','H201','H202','H203','H204','H205'], un:'UN 0000*', class:'1', pg:null, label:'Patlayıcı', note:'UN numarası maddeye özgü belirlenir' },
    // Oksitleyiciler
    { hCodes:['H271'], un:'UN 2912', class:'5.1', pg:'I',   label:'Oksitleyici Sıvı' },
    { hCodes:['H272'], un:'UN 3139', class:'5.1', pg:'II',  label:'Oksitleyici Sıvı' },
    // Yanıcı Gazlar
    { hCodes:['H220','H221'], un:'UN 1978', class:'2.1', pg:null, label:'Yanıcı Gaz' },
    // Su ile tepkime
    { hCodes:['H260'], un:'UN 3148', class:'4.3', pg:'I',   label:'Su ile Tepkiyen Sıvı' },
    { hCodes:['H261'], un:'UN 3148', class:'4.3', pg:'II',  label:'Su ile Tepkiyen Sıvı' },
    // Akut Toksisite Kat.1-2
    { hCodes:['H300','H310','H330'], un:'UN 2810', class:'6.1', pg:'I',   label:'Zehirli Madde' },
    // Akut Toksisite Kat.3
    { hCodes:['H301','H311','H331'], un:'UN 2810', class:'6.1', pg:'II',  label:'Zehirli Madde' },
    // Akut Toksisite Kat.4
    { hCodes:['H302','H312','H332'], un:'UN 3077', class:'6.1', pg:'III', label:'Zehirli Madde (Çeşitli)' },
    // Cilt Korozif
    { hCodes:['H314'], un:'UN 1760', class:'8',   pg:'II',  label:'Korozif Madde', note:'pH ve konsantrasyona göre PG I veya III olabilir' },
    // Yanıcı Sıvı Kat.1
    { hCodes:['H224'], un:'UN 1993', class:'3',   pg:'I',   label:'Yanıcı Sıvı' },
    // Yanıcı Sıvı Kat.2
    { hCodes:['H225'], un:'UN 1993', class:'3',   pg:'II',  label:'Yanıcı Sıvı' },
    // Yanıcı Sıvı Kat.3
    { hCodes:['H226'], un:'UN 1993', class:'3',   pg:'III', label:'Yanıcı Sıvı' },
    // Aspirasyon
    { hCodes:['H304'], un:'UN 3082', class:'3',   pg:'III', label:'Aspirasyon Tehlikeli Sıvı' },
    // Çevre tehlikesi
    { hCodes:['H400','H410','H411','H412'], un:'UN 3082', class:'9',   pg:'III', label:'Çevre Tehlikesi' },
  ];

  const CLASS_LABELS = {
    '1':'Patlayıcı Maddeler', '2.1':'Yanıcı Gazlar', '2.2':'Yanıcı Olmayan Gazlar',
    '3':'Yanıcı Sıvılar', '4.1':'Yanıcı Katılar', '4.2':'Kendiliğinden Alışan Maddeler',
    '4.3':'Su ile Tepkiyen Maddeler', '5.1':'Oksitleyici Maddeler', '5.2':'Organik Peroksitler',
    '6.1':'Zehirli Maddeler', '6.2':'Bulaşıcı Maddeler', '7':'Radyoaktif Maddeler',
    '8':'Aşındırıcı Maddeler', '9':'Çeşitli Tehlikeli Maddeler ve Nesneler',
  };

  function classify(hCodes) {
    const hSet = new Set(hCodes.map(h => h.replace(/[*\s]/g,'').substring(0,4)));

    let matched = null;
    for (const rule of RULES) {
      if (rule.hCodes.some(h => hSet.has(h))) {
        matched = rule;
        break;
      }
    }

    if (!matched) {
      return {
        not_regulated: true,
        road: null, sea: null, air: null,
        note: 'Bu madde/karışım tehlikeli madde olarak sınıflandırılmamıştır.',
      };
    }

    const entry = {
      un:    matched.un,
      class: matched.class,
      class_label: CLASS_LABELS[matched.class] || matched.class,
      pg:    matched.pg,
      label: matched.label,
      note:  matched.note || null,
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
