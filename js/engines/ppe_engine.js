/**
 * PPEEngine — SDS Bölüm 8 — Kişisel Koruyucu Donanım
 * Girdi : hCodes[]
 * Çıktı : { respiratory[], hands[], eyes[], body[], general[] }
 *
 * Events: dinler  → H_CODES_READY { hCodes }
 *         emit eder → PPE_READY { respiratory, hands, eyes, body, general }
 */
const PPEEngine = (() => {

  // H kodu → gereken KKD eşlemeleri
  const RULES = {
    // Solunum yolu
    respiratory: [
      { hCodes:['H330','H331'],  ppe:'Tam yüz gaz maskesi — ABEK filtreli (EN 136 / EN 14387)', level:1 },
      { hCodes:['H332','H335','H336'], ppe:'Yarım yüz maskesi veya FFP2 toz maskesi (EN 149)', level:2 },
      { hCodes:['H334'],         ppe:'Tam yüz maskesi — P3 filtreli (EN 136)', level:1 },
      { hCodes:['H370','H371'],  ppe:'Tam yüz SCBA veya ABEK gaz maskesi (EN 136)', level:1 },
      { hCodes:['H340','H350','H360'], ppe:'Tam yüz maskesi — P3 kombine filtre (EN 136)', level:1 },
    ],
    // El koruma
    hands: [
      { hCodes:['H314'],         ppe:'Nitril eldiven ≥0,4 mm kalınlık (EN ISO 374-1 Tip B)', level:1 },
      { hCodes:['H300','H310'],  ppe:'Nitril veya Bütil kauçuk eldiven ≥0,5 mm (EN ISO 374-1 Tip A)', level:1 },
      { hCodes:['H315','H317'],  ppe:'Nitril eldiven ≥0,1 mm (EN ISO 374-1 Tip B)', level:2 },
      { hCodes:['H340','H350','H360'], ppe:'Nitril eldiven ≥0,4 mm — tek kullanımlık değil (EN ISO 374-1)', level:1 },
      { hCodes:['H318','H319'],  ppe:'Koruyucu eldiven (EN ISO 374-1)', level:2 },
    ],
    // Göz/Yüz koruma
    eyes: [
      { hCodes:['H314'],         ppe:'Kimyasal koruyucu yüz kalkanı + sıkı oturan gözlük (EN 166)', level:1 },
      { hCodes:['H318'],         ppe:'Sıkı oturan koruyucu gözlük (EN 166 3B)', level:1 },
      { hCodes:['H319'],         ppe:'Güvenlik gözlüğü (EN 166)', level:2 },
      { hCodes:['H330','H331','H332'], ppe:'Tam yüz maskesi gözlük bölümü yeterli (EN 166)', level:2 },
      { hCodes:['H300','H310'],  ppe:'Sıkı oturan koruyucu gözlük (EN 166 3B)', level:1 },
    ],
    // Vücut/giysi koruma
    body: [
      { hCodes:['H314','H300','H310','H330'], ppe:'Kimyasal koruyucu giysi — Tip 3 veya 4 (EN 14605)', level:1 },
      { hCodes:['H340','H350','H360'],        ppe:'Kimyasal koruyucu giysi — Tip 4 minimum (EN 14605)', level:1 },
      { hCodes:['H315','H317','H331','H332'], ppe:'Kimyasal koruyucu iş elbisesi (EN 13034 Tip 6)', level:2 },
      { hCodes:['H224','H225','H226'],        ppe:'Antistatik giysi + antistatik ayakkabı (EN 1149-5)', level:1 },
    ],
  };

  function select(hCodes) {
    const hSet = new Set(hCodes.map(h => h.replace(/[*\s]/g,'').substring(0,4)));
    const result = { respiratory:[], hands:[], eyes:[], body:[], general:[] };

    for (const [category, ruleList] of Object.entries(RULES)) {
      const added = new Set();
      for (const rule of ruleList) {
        if (rule.hCodes.some(h => hSet.has(h))) {
          if (!added.has(rule.ppe)) {
            result[category].push({ ppe: rule.ppe, level: rule.level });
            added.add(rule.ppe);
          }
        }
      }
    }

    // Genel hijyen önlemleri — her zaman
    result.general = [
      'Çalışma alanında yemeyin, içmeyin, sigara içmeyin',
      'İşten önce ve sonra elleri iyice yıkayın',
      'Yakın çevrede acil göz yıkama istasyonu bulundurun',
    ];

    if (hSet.has('H314') || hSet.has('H300') || hSet.has('H310')) {
      result.general.push('Kontaminasyon durumunda hemen bol su ile yıkayın');
    }
    if (hSet.has('H340') || hSet.has('H350') || hSet.has('H360')) {
      result.general.push('Kanserojen/mutajen/reprodüktif toksin — kapalı sistem kullanın');
    }

    return result;
  }

  function init() {
    if (typeof EventBus !== 'undefined') {
      EventBus.on('H_CODES_READY', (data) => {
        const result = select(data.hCodes);
        EventBus.emit('PPE_READY', result);
      });
    }
    console.log('[PPEEngine] init OK');
  }

  return { init, select };
})();
