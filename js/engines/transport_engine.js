/**
 * TransportEngine — ADR/IMDG/IATA — SDS Bölüm 14
 * Kaynak: ADR 2023 Tablo 3.1, IMDG Kod 2022, IATA-DGR 2024
 *         ADR 2.1.3.5 — Çoklu tehlike öncelik matrisi (Tablo 2.1.3.10)
 *
 * MİMARİ: Önceki "ilk eşleşen kural kazanır" yaklaşımı yerine
 *         PG tabanlı çelişki çözme matrisi kullanılır.
 *
 * Girdi : H_CODES_READY { hCodes[] }   — CLP motorundan
 *         PHYSICAL_READY { results[] } — Fiziksel motordan (H224/H225/H226)
 *         PIPELINE_START { form }      — Form bilgisi (liquid/solid/aerosol)
 * Çıktı : TRANSPORT_READY { road{}, sea{}, air{}, not_regulated, conflict_warning }
 */
const TransportEngine = (() => {

  const CLASS_LABELS = {
    '1'  : 'Patlayıcı Maddeler',
    '2.1': 'Yanıcı Gazlar',
    '2.2': 'Yanıcı Olmayan/Zehirli Gazlar',
    '3'  : 'Yanıcı Sıvılar',
    '4.1': 'Yanıcı Katılar',
    '4.2': 'Kendiliğinden Alışan Maddeler',
    '4.3': 'Su ile Tepkiyen Maddeler',
    '5.1': 'Oksitleyici Maddeler',
    '5.2': 'Organik Peroksitler',
    '6.1': 'Zehirli Maddeler',
    '6.2': 'Bulaşıcı Maddeler',
    '7'  : 'Radyoaktif Maddeler',
    '8'  : 'Aşındırıcı Maddeler',
    '9'  : 'Çeşitli Tehlikeli Maddeler ve Nesneler',
  };

  // ── H Kodu → ADR Sınıfı + Ambalaj Grubu ────────────────────────────────────
  // ADR 2023 Bölüm 2: Her H kodunun birincil ADR sınıfı ve PG'si
  // PG: 'I' (en tehlikeli) > 'II' > 'III' (en az tehlikeli) | null (uygulanmıyor)
  const H_TO_ADR = {
    // Sınıf 1 — Patlayıcı
    'H200':{'class':'1','pg':'I'},'H201':{'class':'1','pg':'I'},'H202':{'class':'1','pg':'I'},
    'H203':{'class':'1','pg':'I'},'H204':{'class':'1','pg':'I'},'H205':{'class':'1','pg':'I'},
    // Sınıf 2.1 — Yanıcı Gaz
    'H220':{'class':'2.1','pg':null},'H221':{'class':'2.1','pg':null},
    'H222':{'class':'2.1','pg':null},'H223':{'class':'2.1','pg':null},
    // Sınıf 2.2 — Oksitleyici Gaz
    'H270':{'class':'2.2','pg':null},
    // Sınıf 3 — Yanıcı Sıvı (parlama noktasına göre PG)
    'H224':{'class':'3','pg':'I'},    // FP < 23°C, BP ≤ 35°C
    'H225':{'class':'3','pg':'II'},   // FP < 23°C, BP > 35°C
    'H226':{'class':'3','pg':'III'},  // 23°C ≤ FP ≤ 60°C
    // Sınıf 4.1 — Yanıcı Katı
    'H228':{'class':'4.1','pg':'II'},
    // Sınıf 4.2 — Kendiliğinden Alışan / Isınan
    'H250':{'class':'4.2','pg':'I'},
    'H251':{'class':'4.2','pg':'II'},
    'H252':{'class':'4.2','pg':'III'},
    // Sınıf 4.3 — Su ile Tepkiyen
    'H260':{'class':'4.3','pg':'I'},
    'H261':{'class':'4.3','pg':'II'},
    // Sınıf 5.1 — Oksitleyici
    'H271':{'class':'5.1','pg':'I'},
    'H272':{'class':'5.1','pg':'II'},
    // Sınıf 5.2 — Organik Peroksit
    'H241':{'class':'5.2','pg':null},
    'H242':{'class':'5.2','pg':null},
    // Sınıf 6.1 — Akut Toksisite (en tehlikeli maruz kalma yolunun PG'si)
    'H300':{'class':'6.1','pg':'I'},  // Oral Kat.1
    'H310':{'class':'6.1','pg':'I'},  // Dermal Kat.1
    'H330':{'class':'6.1','pg':'I'},  // İnhalasyon Kat.1
    'H301':{'class':'6.1','pg':'II'}, // Oral Kat.2-3
    'H311':{'class':'6.1','pg':'II'}, // Dermal Kat.2-3
    'H331':{'class':'6.1','pg':'II'}, // İnhalasyon Kat.2-3
    'H302':{'class':'6.1','pg':'III'},// Oral Kat.4
    'H312':{'class':'6.1','pg':'III'},// Dermal Kat.4
    'H332':{'class':'6.1','pg':'III'},// İnhalasyon Kat.4
    // Sınıf 8 — Korozif (H314 = Skin Corr. 1A → ADR varsayılan PG II)
    // Not: kuvvetli asit/baz konsantrasyonuna göre PG I olabilir — uzman onayı gerekir
    'H314':{'class':'8','pg':'II'},
    // Sınıf 9 — Aspirasyon ve Çevre Tehlikesi
    'H304':{'class':'9','pg':'III'},
    'H400':{'class':'9','pg':'III'},
    'H410':{'class':'9','pg':'III'},
    'H411':{'class':'9','pg':'III'},
    'H412':{'class':'9','pg':'III'},
  };

  // ── ADR Tablo 2.1.3.10: Çoklu Tehlike Öncelik Matrisi ─────────────────────
  // Sınıf öncelik sırası (PG bağımsız üst seviye):
  // 1 > 5.2 > 4.2 > 4.3 > 5.1 > 2.1 > {3 / 6.1 / 8 arası PG matrisi} > 4.1 > 9
  const CLASS_RANK = {
    '1':10, '5.2':9, '4.2':8, '4.3':7, '5.1':6, '2.1':5, '2.2':4,
    '3':3, '6.1':3, '8':3,   // Bu üçlü için rank eşit → PG matrisi devreye girer
    '4.1':2, '9':1,
  };

  function _pgNum(pg) {
    return pg === 'I' ? 1 : pg === 'II' ? 2 : pg === 'III' ? 3 : 4; // null/unknown → 4
  }

  /**
   * resolveConflict — ADR Tablo 2.1.3.10 PG matrisi
   * İki ADR sınıfını karşılaştırır; birincil (kazanan) ve yan (ikincil) sınıfı döner.
   * @returns {{ winner:string, winPG:string, loser:string|null }}
   */
  function resolveConflict(clsA, pgA, clsB, pgB) {
    const rankA = CLASS_RANK[clsA] || 0;
    const rankB = CLASS_RANK[clsB] || 0;

    // Üst sıralama farklıysa büyük olan kazanır (PG'ye bakılmaz)
    if (rankA > rankB) return { winner:clsA, winPG:pgA, loser:clsB };
    if (rankB > rankA) return { winner:clsB, winPG:pgB, loser:clsA };

    // Rank eşit → Sınıf 3 / 6.1 / 8 üçgeni: PG matrisi uygula
    const pA = _pgNum(pgA), pB = _pgNum(pgB);

    // ── Sınıf 3 vs Sınıf 6.1 ─────────────────────────────────────────────────
    // ADR Tablo 2.1.3.10 (alıntı):
    //   3-I   + 6.1-I   → 6.1    3-II  + 6.1-I   → 6.1
    //   3-I   + 6.1-II  → 3      3-II  + 6.1-II  → 3
    //   3-I   + 6.1-III → 3      3-II  + 6.1-III → 3
    //   3-III + 6.1-I   → 6.1    3-III + 6.1-II  → 6.1    3-III + 6.1-III → 3
    if ((clsA === '3' && clsB === '6.1') || (clsA === '6.1' && clsB === '3')) {
      const pg3  = clsA === '3'   ? pA : pB;
      const pg61 = clsA === '6.1' ? pA : pB;
      const wins61 = (pg61 <= 2) && (pg3 === 3 || pg61 < pg3);
      // Özet: 6.1 kazanır eğer → 6.1 PG I/II VE (3 PG III VEYA 6.1 daha tehlikeli)
      const w = wins61 ? '6.1' : '3';
      return {
        winner: w,
        winPG:  w === '6.1' ? (clsA === '6.1' ? pgA : pgB) : (clsA === '3' ? pgA : pgB),
        loser:  w === '6.1' ? '3' : '6.1',
      };
    }

    // ── Sınıf 3 vs Sınıf 8 ───────────────────────────────────────────────────
    // ADR Tablo 2.1.3.10:
    //   3-I   + 8-I   → 8      3-I   + 8-II  → 3      3-I   + 8-III → 3
    //   3-II  + 8-I   → 8      3-II  + 8-II  → 3      3-II  + 8-III → 3
    //   3-III + 8-I   → 8      3-III + 8-II  → 8      3-III + 8-III → 3
    if ((clsA === '3' && clsB === '8') || (clsA === '8' && clsB === '3')) {
      const pg3 = clsA === '3' ? pA : pB;
      const pg8 = clsA === '8' ? pA : pB;
      const wins8 = (pg8 === 1) || (pg8 === 2 && pg3 === 3);
      const w = wins8 ? '8' : '3';
      return {
        winner: w,
        winPG:  w === '8' ? (clsA === '8' ? pgA : pgB) : (clsA === '3' ? pgA : pgB),
        loser:  w === '8' ? '3' : '8',
      };
    }

    // ── Sınıf 6.1 vs Sınıf 8 ─────────────────────────────────────────────────
    // ADR Tablo 2.1.3.10:
    //   6.1-I   + 8-I   → 6.1(+8)    6.1-I   + 8-II  → 6.1
    //   6.1-II  + 8-I   → 8          6.1-II  + 8-II  → 6.1
    //   6.1-III + 8-I   → 8          6.1-III + 8-II  → 8       6.1-III + 8-III → 6.1
    if ((clsA === '6.1' && clsB === '8') || (clsA === '8' && clsB === '6.1')) {
      const pg61 = clsA === '6.1' ? pA : pB;
      const pg8  = clsA === '8'   ? pA : pB;
      const wins8 = (pg61 >= 2 && pg8 === 1) || (pg61 === 3 && pg8 === 2);
      const w = wins8 ? '8' : '6.1';
      return {
        winner: w,
        winPG:  w === '8'   ? (clsA === '8'   ? pgA : pgB) : (clsA === '6.1' ? pgA : pgB),
        loser:  w === '8'   ? '6.1' : '8',
      };
    }

    // Aynı sınıf: en düşük PG numarası (en tehlikeli) kazanır
    if (clsA === clsB) {
      return pA <= pB
        ? { winner:clsA, winPG:pgA, loser:null }
        : { winner:clsB, winPG:pgB, loser:null };
    }

    // Bilinmeyen çift — A kazanır (muhafazakâr yaklaşım)
    return { winner:clsA, winPG:pgA, loser:clsB };
  }

  // ── UN Numarası Arama Tablosu ──────────────────────────────────────────────
  // Birincil sınıf + PG + yan tehlike + form → { un, label, note }
  function _getUNEntry(cls, pg, sub, isSolid) {
    if (cls === '1') return {
      un:'UN 0000*', label:'Patlayıcı',
      note:'UN numarası maddeye özgü belirlenir; patlayıcı sınıfı tüm yan tehlikeleri ezer',
    };
    if (cls === '2.1') return {
      un:'UN 1954', label:'Yanıcı Gaz, B.N.O.',
      note:'Maddeye özgü UN numarası önceliklidir (ör. UN1978 propan, UN1001 asetilen)',
    };
    if (cls === '2.2') return {
      un:'UN 3156', label:'Sıkıştırılmış Gaz, Oksitleyici, B.N.O.',
      note:'ADR Sınıf 2.2 oksitleyici — tüp/tank özel kuralları geçerlidir',
    };
    if (cls === '3') {
      if (sub === '8')   return { un:'UN 2924', label:'Yanıcı Sıvı, Korozif, B.N.O.',
        note:'ADR 2023: Sınıf 3 birincil, Sınıf 8 yan tehlike' };
      if (sub === '6.1') return { un:'UN 1992', label:'Yanıcı Sıvı, Toksik, B.N.O.',
        note:'ADR 2023: Sınıf 3 birincil, Sınıf 6.1 yan tehlike' };
      return { un:'UN 1993', label:'Yanıcı Sıvı, B.N.O.' };
    }
    if (cls === '4.1') return {
      un:'UN 1325', label:'Yanıcı Katı, Organik, B.N.O.',
      note:'Maddeye özgü UN önceliklidir; PG I/III uzman onayı gerekir',
    };
    if (cls === '4.2') {
      if (pg === 'I')   return { un:'UN 2845', label:'Pirofor Sıvı, Organik, B.N.O.',
        note:'H250: Hava temasında kendiliğinden alışır — PG I, özel ambalaj' };
      if (pg === 'II')  return { un:'UN 3088', label:'Kendiliğinden Isınan Katı, Organik, B.N.O.' };
      return { un:'UN 3190', label:'Kendiliğinden Isınan Katı, Organik, B.N.O.' };
    }
    if (cls === '4.3') return {
      un:'UN 3148', label:'Su ile Tepkiyen Sıvı, B.N.O.',
    };
    if (cls === '5.1') {
      if (pg === 'I') return { un:'UN 2912', label:'Oksitleyici Sıvı, B.N.O.' };
      return { un:'UN 3139', label:'Oksitleyici Sıvı, B.N.O.' };
    }
    if (cls === '5.2') return {
      un:'UN 3105', label:'Organik Peroksit, Tip D, E, F, Sıvı',
      note:'Tip belirlenmesi (A-G) gereklidir; UN3105 Tip D/E/F varsayılan',
    };
    if (cls === '6.1') {
      // Sınıf 6.1 birincil + yan tehlike 3 → UN 2929
      if (sub === '3') return {
        un: isSolid ? 'UN 2929' : 'UN 2929',
        label: isSolid ? 'Zehirli Katı, Yanıcı, Organik, B.N.O.' : 'Zehirli Sıvı, Yanıcı, Organik, B.N.O.',
        note:'ADR 2023: Sınıf 6.1 birincil, Sınıf 3 yan tehlike (ADR Tablo 2.1.3.10)',
      };
      // Sınıf 6.1 + Sınıf 8
      if (sub === '8') return {
        un: isSolid ? 'UN 2928' : 'UN 2927',
        label: isSolid ? 'Zehirli Katı, Korozif, Organik, B.N.O.' : 'Zehirli Sıvı, Korozif, Organik, B.N.O.',
        note:'Organik yapı için UN 2927/2928; inorganik → UN 3289/3290',
      };
      return {
        un: isSolid ? 'UN 2811' : 'UN 2810',
        label: isSolid ? 'Zehirli Katı, Organik, B.N.O.' : 'Zehirli Sıvı, Organik, B.N.O.',
        note:'UN 2810/2811 organik bileşikler için; inorganik → UN 3287/3288',
      };
    }
    if (cls === '8') {
      // Sınıf 8 birincil + yan tehlike 3 → UN 2920 (sıvı) / UN 2921 (katı)
      if (sub === '3') return {
        un: isSolid ? 'UN 2921' : 'UN 2920',
        label: isSolid ? 'Korozif Katı, Yanıcı, B.N.O.' : 'Korozif Sıvı, Yanıcı, B.N.O.',
        note:'ADR 2023: Sınıf 8 birincil, Sınıf 3 yan tehlike (ADR Tablo 2.1.3.10)',
      };
      // Sınıf 8 + Sınıf 6.1 → UN 2927
      if (sub === '6.1') return {
        un: isSolid ? 'UN 2928' : 'UN 2927',
        label: isSolid ? 'Zehirli Katı, Korozif, Organik, B.N.O.' : 'Zehirli Sıvı, Korozif, Organik, B.N.O.',
      };
      return {
        un: isSolid ? 'UN 1759' : 'UN 1760',
        label: isSolid ? 'Korozif Katı, B.N.O.' : 'Korozif Sıvı, B.N.O.',
        note:'Asidik inorganik → UN 3264 | Bazik → UN 3266 | Organik → UN 1760 | PG I uzman onayı',
      };
    }
    if (cls === '9') return {
      un: isSolid ? 'UN 3077' : 'UN 3082',
      label: isSolid ? 'Çevre için Tehlikeli Madde, Katı, B.N.O.' : 'Çevre için Tehlikeli Madde, Sıvı, B.N.O.',
    };
    return { un:'—', label:'Bilinmiyor' };
  }

  // ── Ana Sınıflandırma Fonksiyonu ───────────────────────────────────────────
  /**
   * classify(hCodes, form, physHCodes)
   * @param {string[]} hCodes    — CLP motorundan gelen H kodları
   * @param {string}   form      — 'liquid' | 'solid' | 'aerosol'
   * @param {string[]} physHCodes — Fiziksel motordan gelen H22x/H228 kodları
   */
  function classify(hCodes, form, physHCodes) {
    const isSolid = (form || 'liquid') === 'solid';

    // Tüm H kodlarını birleştir: CLP + Fiziksel motor (H224/H225/H226 burada eklenir)
    const allH = [...new Set([
      ...(hCodes     || []).map(h => h.replace(/[*\s]/g,'').substring(0,4)),
      ...(physHCodes || []).map(h => h.replace(/[*\s]/g,'').substring(0,4)),
    ])].filter(h => h.startsWith('H'));
    const hSet = new Set(allH);

    // Çevre tehlike işareti
    const envMark = hSet.has('H400') || hSet.has('H410') || hSet.has('H411') || hSet.has('H412');

    // ── Adım 1: Aktif ADR tehlikelerini çıkar ─────────────────────────────────
    // Aynı sınıf için en tehlikeli PG'yi (en küçük sayı) sakla
    const classMap = {}; // { cls: { pg, pgNum } }
    for (const h of allH) {
      const adr = H_TO_ADR[h];
      if (!adr) continue;
      const existing = classMap[adr.class];
      const newNum   = _pgNum(adr.pg);
      if (!existing || newNum < existing.pgNum) {
        classMap[adr.class] = { pg: adr.pg, pgNum: newNum };
      }
    }

    const detected = Object.entries(classMap).map(([cls, { pg }]) => ({ class:cls, pg }));

    if (!detected.length) {
      return {
        not_regulated: true,
        road:null, sea:null, air:null,
        note:'Bu madde/karışım tehlikeli madde olarak sınıflandırılmamıştır.',
      };
    }

    // ── Adım 2: Birincil sınıfı ADR Tablo 2.1.3.10 matrisiyle belirle ─────────
    let primary = { class: detected[0].class, pg: detected[0].pg };
    for (let i = 1; i < detected.length; i++) {
      const res = resolveConflict(primary.class, primary.pg, detected[i].class, detected[i].pg);
      if (res.winner !== primary.class) {
        primary = { class: res.winner, pg: res.winPG };
      }
    }

    // ── Adım 3: Yan tehlikeleri belirle (en tehlikeli PG'ye göre sırala) ──────
    const subs = detected
      .filter(d => d.class !== primary.class)
      .sort((a, b) => _pgNum(a.pg) - _pgNum(b.pg));
    const subClass = subs.length > 0 ? subs[0].class : null;

    // ── Adım 4: UN ve etiket ──────────────────────────────────────────────────
    const unEntry = _getUNEntry(primary.class, primary.pg, subClass, isSolid);

    // ── Adım 5: H22x çelişki kontrolü (güvenlik ağı) ──────────────────────────
    // Fiziksel motor H22x kodlarını CLP motoruna iletmediğinden kalıcı uyarı
    const flamPresent = ['H224','H225','H226'].filter(h => hSet.has(h));
    let conflictWarning = null;
    if (flamPresent.length && primary.class !== '3' && primary.class !== '2.1') {
      conflictWarning = {
        level:   'CRITICAL',
        message: `Alevlenirlik tehlikesi (${flamPresent.join('/')}) tespit edildi ancak ` +
                 `birincil taşımacılık sınıfı Sınıf ${primary.class}. ` +
                 `Parlama noktası ≤ 60°C ise ADR 2023 kapsamında Sınıf 3 değerlendirilmelidir.`,
      };
    }

    // Yan tehlike etiketi
    const allSubLabels = subs.map(s => `Sınıf ${s.class}`).join(', ');
    const subLabel = allSubLabels ? ` (Yan Tehlike: ${allSubLabels})` : '';

    const entry = {
      un:           unEntry.un,
      class:        primary.class,
      class_label:  (CLASS_LABELS[primary.class] || primary.class) + subLabel,
      pg:           primary.pg,
      label:        unEntry.label,
      sub_class:    subClass,
      note:         unEntry.note || null,
      env_mark:     envMark,
      conflict_warning: conflictWarning,
    };

    return {
      not_regulated: false,
      road: { ...entry, regulation:'ADR 2023'       },
      sea:  { ...entry, regulation:'IMDG Kod 2022'  },
      air:  { ...entry, regulation:'IATA-DGR 2024'  },
      conflict_warning: conflictWarning,
    };
  }

  // ── Event Pipeline ─────────────────────────────────────────────────────────
  // CLP (H_CODES_READY) ve Fiziksel motor (PHYSICAL_READY) ayrı zamanlarda gelir.
  // Debounce ile ikisi birleştirildikten sonra TRANSPORT_READY emitted.
  let _clpHCodes  = [];
  let _physHCodes = [];
  let _form       = 'liquid';
  let _timer      = null;

  function _scheduleEmit() {
    if (_timer) clearTimeout(_timer);
    _timer = setTimeout(() => {
      const result = classify(_clpHCodes, _form, _physHCodes);
      if (typeof EventBus !== 'undefined') EventBus.emit('TRANSPORT_READY', result);
      _timer = null;
    }, 20); // 20ms: her iki event'in gelmesi için yeterli
  }

  function init() {
    if (typeof EventBus === 'undefined') return;

    // Form bilgisini pipeline başlangıcında al ve state'i sıfırla
    EventBus.on('PIPELINE_START', ({ form }) => {
      _form       = form || 'liquid';
      _clpHCodes  = [];
      _physHCodes = [];
    });

    // CLP motorundan gelen tehlike kodları (H300, H314, H371 vb.)
    EventBus.on('H_CODES_READY', ({ hCodes }) => {
      _clpHCodes = hCodes || [];
      _scheduleEmit();
    });

    // Fiziksel motordan gelen H22x kodları (H224/H225/H226 — CLP motoruna dahil değil)
    EventBus.on('PHYSICAL_READY', ({ results }) => {
      const PHYS_TRANSPORT = new Set(['H224','H225','H226','H228']);
      _physHCodes = (results || [])
        .map(r => (r.h || r.h_code || '').replace(/[*\s]/g,'').substring(0,4))
        .filter(h => PHYS_TRANSPORT.has(h));
      _scheduleEmit();
    });

    console.log('[TransportEngine] init OK — ADR 2023 Tablo 2.1.3.10 matris motoru aktif');
  }

  return { init, classify, resolveConflict };
})();
