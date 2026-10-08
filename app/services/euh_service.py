"""
EUH İfadeleri Servisi — SEA Yönetmeliği Ek-2 (RG 10.12.2020/31330)
====================================================================

Birinci Kısım — madde özellikleri (EUH001/014/018/019/029/031/032/044/066/070/071):
  Yalnızca bileşenin SEA Ek-6 / Annex VI uyumlaştırılmış kaydındaki ek zararlılık ifadelerinden
  (suppl_hazards) gelir; kayıttaki konsantrasyon eşiği uygulanır (euh_limits, örn. sodyum
  hipoklorit EUH031 ≥ %5). Sabit CAS/isim listesi kullanılmaz — eski listeler resmî verilerle
  çelişiyordu (örn. sülfürik aside EUH031, hidrojen peroksite EUH019).
  İstisna: SEA Ek-6'da yalnızca CAS'sız grup kaydıyla (006-007-00-5) yer alan siyanür tuzları → EUH032.

İkinci Kısım — belirli karışımlar:
  EUH201  kurşun içeren boya/vernik, kurşun > %0,009
  EUH202  siyanoakrilat
  EUH203  krom (VI)
  EUH204  izosiyanat (isimde tam kelime)
  EUH205  epoksi bileşeni (isimde tam kelime)
  EUH206  aktif klor (hipoklorit)
  EUH207  kadmiyum
  EUH208  hassaslaştırıcı (SCL/10 kuralı)

Üretilmeyenler: EUH059 (CLP'de H420 ile değiştirildi; ekolojik servis H420 verir),
EUH211/EUH212 (TR SEA Ek-2'de yok).
Metinler: codes_i18n.get_euh('TR') → SEA Ek-2 resmî metni.
"""
import re
from typing import List, Dict

from app.services.codes_i18n import get_euh

EUH032_GROUP_CAS = {'143-33-9', '151-50-8'}   # sodyum siyanür, potasyum siyanür

EUH201_CAS = {'10099-74-8', '1314-87-0', '1317-36-8', '1344-37-2', '301-04-2', '7439-92-1',
              '7446-14-2', '75-74-1', '7758-95-4', '78-00-2'}
# Siyanoakrilatlar (SEA Ek-2 2.2). 1309-14-4 geçersiz CAS'tı (hiçbir maddeye karşılık gelmiyor) — çıkarıldı;
# izobütil ve 2-oktil eklendi (PubChem ile doğrulandı). Adında 'cyanoacrylate' geçen bileşen de yakalanır.
EUH202_CAS = {'137-05-3', '7085-85-0', '6606-65-1', '1069-55-2', '133978-15-1'}
EUH203_CAS = {'10588-01-9', '1333-82-0', '13530-65-9', '7738-94-5', '7778-50-9', '7789-00-6'}
EUH206_CAS = {'10022-70-5', '7681-52-9', '7778-54-3'}
EUH207_CAS = {'10108-64-2', '10124-36-4', '1306-23-6', '7440-43-9'}
# Aktif klor payı (Cl2 eşdeğeri / mol kütlesi): NaOCl 70,9/74,44; Ca(OCl)2 141,8/142,98; NaOCl·5H2O 70,9/164,5
_ACTIVE_CL_FACTOR = {'7681-52-9': 0.952, '7778-54-3': 0.992, '10022-70-5': 0.431}

_ISOCYANATE = re.compile(r'isocyanat|izosiyanat|\b(?:p?mdi|tdi|hdi|ipdi|xdi|ndi)\b', re.I)
_CYANOACRYL = re.compile(r'cyano\s*-?\s*acryl|siyano\s*-?\s*akril', re.I)
_EPOXY      = re.compile(r'\bepox|epoksi|glycidyl|glisidil|\boxiran|\boksiran', re.I)

# ─── EUH208 — SCL/10 Kuralı (CLP Annex I 3.4.4.1) ──────────────────────────
# Skin Sens. SCL'si olan maddeler için EUH208 eşiği = SCL / 10
# Annex VI ATP23'ten türetilmiş
SKIN_SENS_SCL_EUH208_THRESHOLD = {
    # NOT: Glutaraldehit (111-30-8) burada tanımlı değil.
    # H334 (Resp. Sens. 1) üzerinden zaten %0.1 GCL eşiği uygulanır → EUH208 tetiklenir.
    # Skin Sens. SCL'si için resmi kaynak (CLP Ek VI) doğrulanmadan değer eklenmez.
    "7789-09-5": 0.02, "10588-01-9": 0.02, "14977-61-8": 0.05, "7789-00-6": 0.05, "7775-11-3": 0.02, "7786-81-4": 0.001, "7718-54-9": 0.001, "13138-45-9": 0.001, "14216-75-2": 0.001, "92129-57-2": 0.001, "13637-71-3": 0.001, "13842-46-1": 0.001, "15699-18-0": 0.001, "13770-89-3": 0.001, "14708-14-6": 0.001, "3349-06-2": 0.001, "15843-02-4": 0.001, "68134-59-8": 0.001, "373-02-4": 0.001, "14998-37-9": 0.001, "553-71-9": 0.001, "3906-55-6": 0.001, "2223-95-2": 0.001, "16039-61-5": 0.001, "4995-91-9": 0.001, "10028-18-9": 0.001, "13462-88-9": 0.001, "13462-90-3": 0.001, "11132-10-8": 0.001, "26043-11-8": 0.001, "15060-62-5": 0.001, "13689-92-4": 0.001, "15586-38-6": 0.001, "67952-43-6": 0.001, "14550-87-9": 0.001, "71720-48-4": 0.001, "16083-14-0": 0.001, "3349-08-4": 0.001, "39819-65-3": 0.001, "18721-51-2": 0.001, "18283-82-4": 0.001, "22605-92-1": 0.001, "4454-16-4": 0.001, "7580-31-6": 0.001, "93983-68-7": 0.001, "29317-63-3": 0.001, "27637-46-3": 0.001, "84852-37-9": 0.001, "93920-10-6": 0.001, "85508-43-6": 0.001, "85508-44-7": 0.001, "51818-56-5": 0.001, "93920-09-3": 0.001, "71957-07-8": 0.001, "52625-25-9": 0.001, "13654-40-5": 0.001, "85508-45-8": 0.001, "85508-46-9": 0.001, "84852-35-7": 0.001, "84852-39-1": 0.001, "85135-77-9": 0.001, "85166-19-4": 0.001, "84852-36-8": 0.001, "85551-28-6": 0.001, "91697-41-5": 0.001, "84776-45-4": 0.001, "72319-19-8": 0.001, "97-54-1": 0.001, "5932-68-3": 0.001, "5912-86-7": 0.001, "104-55-2": 0.001, "14371-10-9": 0.001, "818-61-1": 0.02, "110-16-7": 0.01, "108-31-6": 0.0001, "2918-23-2": 0.02, "999-61-1": 0.02, "25584-83-2": 0.02, "106-90-1": 0.02, "4074-88-8": 0.02, "105512-06-9": 0.0001, "15141-18-1": 0.0001, "26761-45-5": 0.0001, "126-98-7": 0.02, "35691-65-7": 0.0001, "68516-81-4": 0.0001, "2855-13-2": 0.0001, "101-72-4": 0.01, "133-06-2": 0.0001, "133-07-3": 0.0001, "2634-33-5": 0.0036, "26530-20-1": 0.00015, "4719-04-4": 0.01, "55965-84-9": 0.00015, "2682-20-4": 0.00015, "64359-81-5": 0.00015, "2527-66-4": 0.00015, "26172-54-3": 0.00015, "4098-71-9": 0.0001, "5124-30-1": 0.05, "16938-22-0": 0.05, "15646-96-5": 0.05, "822-06-0": 0.05, "3634-83-1": 0.0001, "91-97-4": 0.0001, "79-07-2": 0.01}


def _add(detected: list, codes: set, code: str, cas: str, name: str, **extra) -> None:
    if code in codes:
        return
    detected.append({'code': code, 'text': get_euh('TR', code), 'source_cas': cas, 'source_name': name, **extra})
    codes.add(code)


def check_euh(components: List[Dict],
              mixture_form: str = 'liquid',
              form_sub: str = '',
              usage: str = '') -> Dict:
    """
    Formüldeki bileşenlere göre EUH ifadelerini tespit eder.
    Döner: {'euh_codes': [...], 'euh_details': [{code, text, source_cas, source_name, ...}], 'manual_check': [...]}
    """
    detected = []
    detected_codes = set()
    skin_sens_substances = []  # EUH208 için madde adları

    for comp in components:
        cas = str(comp.get('cas', '') or comp.get('cas_no', '')).strip()
        name = comp.get('name', '') or ''
        name_tr = comp.get('name_tr', '') or name
        hazards = comp.get('hazards', [])
        hazard_classes = {h.get('h_class', '').replace('*', '').strip() for h in hazards}
        comp_conc = float(comp.get('conc', 0) or 0)
        name_all = f'{name} {name_tr}'

        if cas in EUH032_GROUP_CAS:
            _add(detected, detected_codes, 'EUH032', cas, name, source='SEA Ek-6 006-007-00-5 (grup kaydı)')
        # SEA Ek-2 2.1: boya/vernikte kurşun > %0,15 (TR metni; AB'nin sonraki %0,009 değeri TR'de yok).
        # Bileşen yüzdesi kurşun bileşiğinin yüzdesidir — metal olarak kurşun bundan azdır (temkinli).
        if cas in EUH201_CAS and form_sub == 'paint' and comp_conc > 0.15:
            _add(detected, detected_codes, 'EUH201', cas, name, note='Kurşunlu boya/vernik, kurşun > %0,15 (SEA Ek-2 2.1)')
        if cas in EUH202_CAS or _CYANOACRYL.search(name_all):
            _add(detected, detected_codes, 'EUH202', cas, name)
        # SEA Ek-2 2.3: yalnız çimento ve çimento karışımları — çözünebilir krom (VI) > %0,0002;
        # karışım H317 taşıyorsa basılmaz (aşağıda, sınıflandırma sonrası sds_pipeline'da elenir)
        if cas in EUH203_CAS and form_sub == 'cement' and comp_conc > 0.0002:
            _add(detected, detected_codes, 'EUH203', cas, name, note='Çimento, çözünebilir Cr(VI) > %0,0002 (SEA Ek-2 2.3)')
        if _ISOCYANATE.search(name_all):
            _add(detected, detected_codes, 'EUH204', cas, name)
        if _EPOXY.search(name_all):
            _add(detected, detected_codes, 'EUH205', cas, name)
        # SEA Ek-2 2.6 "Halka satılan ve aktif klor içeren karışımlar": aktif klor > %1.
        # Aktif klor = bileşen % × (klor payı): NaOCl 0,952; Ca(OCl)2 0,992; NaOCl·5H2O 0,431
        if cas in EUH206_CAS and usage == 'consumer':
            _cl = comp_conc * _ACTIVE_CL_FACTOR.get(cas, 1.0)
            if _cl > 1.0:
                _add(detected, detected_codes, 'EUH206', cas, name,
                     note=f'Aktif klor ≈ %{_cl:.2f} > %1 (SEA Ek-2 2.6)')
        if cas in EUH207_CAS:
            _add(detected, detected_codes, 'EUH207', cas, name)

        # ── EUH208 — CLP Ek II §2.8 Para 2: "sınıflandırmaya yol açanın EK OLARAK" kuralı
        # Skin Sens. sınıflandırmasına neden olan madde (konc ≥ Skin Sens GCL/SCL) EUH208'e girmez;
        # zaten H317 tehlike ifadesiyle etikette yer alır.
        # EUH208: yalnızca H317 için eşik altı kalan (ama ≥%0.1) ek sensitizerlar listelenir.
        skin_sens_classes = {'Skin Sens. 1', 'Skin Sens. 1A', 'Skin Sens. 1B'}
        resp_sens_classes = {'Resp. Sens. 1', 'Resp. Sens. 1A', 'Resp. Sens. 1B'}
        is_skin_sens = bool(hazard_classes & skin_sens_classes)
        is_resp_sens = bool(hazard_classes & resp_sens_classes)

        if is_skin_sens or is_resp_sens:
            # Sınıflandırma eşiği (SEA Ek-1 Tablo 3.4.5) ve sonuca vardırıcı eşik (Tablo 3.4.6):
            #   cilt 1 / 1B: %1 / %0,1      cilt 1A: %0,1 / %0,01
            #   solunum 1 / 1B: %1 (gaz %0,2) / %0,1      solunum 1A: %0,1 / %0,01
            #   özel sınır (SCL) varsa sınıflandırma eşiği SCL; SCL < %0,1 ise sonuca vardırıcı eşik SCL/10
            # SCL bileşende 'sclRaw' (bant listesi) veya 'scl' (liste/dict) olarak gelir — önceden yalnız
            # 'scl' okunuyordu; sds_pipeline 'sclRaw' gönderdiği için özel sınır yok sayılıyor ve karışımı
            # zaten H317 yapan madde EUH208'e de yazılıyordu.
            from app.services.clp_service import _normalize_scl_list
            _scl_src = comp.get('sclRaw') or comp.get('scl') or []
            if isinstance(_scl_src, dict):
                _scl_src = [{'h_code': k, 'c_min': v} for k, v in _scl_src.items()]
            _scl = {}
            for _e in _normalize_scl_list(_scl_src):
                _hc = (_e.get('h_code') or '').replace('*', '').strip()[:4]
                if _hc in ('H317', 'H334') and _e.get('c_min') is not None:
                    _v = float(_e['c_min'])
                    _scl[_hc] = min(_v, _scl.get(_hc, _v))
            _gas = (mixture_form or '').lower() == 'gas'

            def _thresholds(is_1a: bool, hc: str):
                cls_thr = _scl.get(hc, 0.1 if is_1a else (0.2 if (hc == 'H334' and _gas) else 1.0))
                if hc in _scl and _scl[hc] < 0.1:
                    elic = _scl[hc] / 10
                else:
                    elic = 0.01 if is_1a else 0.1
                return cls_thr, elic

            causes, elic_thr = False, None
            if is_skin_sens:
                _c, _e = _thresholds('Skin Sens. 1A' in hazard_classes, 'H317')
                causes = causes or comp_conc >= _c
                elic_thr = _e if elic_thr is None else min(elic_thr, _e)
            if is_resp_sens:
                _c, _e = _thresholds('Resp. Sens. 1A' in hazard_classes, 'H334')
                causes = causes or comp_conc >= _c
                elic_thr = _e if elic_thr is None else min(elic_thr, _e)
            # ATP listesindeki resmî SCL/10 değeri (yerel SCL verisi yoksa) önceliklidir
            if cas in SKIN_SENS_SCL_EUH208_THRESHOLD and 'H317' not in _scl:
                elic_thr = SKIN_SENS_SCL_EUH208_THRESHOLD[cas]

            # EUH208'e dahil: karışımın sınıflandırılmasına yol açmayan, ama sonuca vardırıcı eşiği aşan
            if not causes and comp_conc >= elic_thr:
                skin_sens_substances.append({
                    'name': name or cas,
                    'name_tr': name_tr or name or cas,
                    'cas': cas,
                    'conc': comp_conc,
                    'threshold': elic_thr,
                    'has_scl': cas in SKIN_SENS_SCL_EUH208_THRESHOLD or bool(_scl),
                })

    # EUH208: Deri sensitizeri varsa + SCL/10 eşiği kontrolü
    if skin_sens_substances and 'EUH208' not in detected_codes:
        sub_names    = '; '.join(s['name']    for s in skin_sens_substances)
        sub_names_tr = '; '.join(s['name_tr'] for s in skin_sens_substances)
        scl_notes = []
        for s in skin_sens_substances:
            if s['has_scl']:
                scl_notes.append(
                    f"{s['name']}: SCL/10 eşiği=%{s['threshold']} — konsantrasyon %{s['conc']} ≥ eşik"
                )
        detected.append({
            'code': 'EUH208',
            'text'         : f'Contains: {sub_names}. May produce an allergic reaction.',
            'text_tr'      : f'İçerir: {sub_names_tr}. Alerjik reaksiyona yol açabilir.',
            'source_cas'   : '; '.join(s['cas'] for s in skin_sens_substances),
            'source_name'  : sub_names,
            'source_name_tr': sub_names_tr,
            'scl_note'     : '; '.join(scl_notes) if scl_notes else None,
        })
        detected_codes.add('EUH208')


    # ── Birinci Kısım — bileşenin uyumlaştırılmış kaydındaki ek zararlılık ifadeleri ──────
    # Kayıtta konsantrasyon eşiği varsa (euh_limits) yalnızca eşiğin üstünde uygulanır.
    for comp in components:
        cas = str(comp.get('cas', '') or comp.get('cas_no', '')).strip()
        name = comp.get('name', '') or ''
        conc = float(comp.get('conc', comp.get('concentration', 0)) or 0)
        limits = {l.get('code'): l for l in (comp.get('euh_limits') or []) if isinstance(l, dict)}
        for euh in comp.get('suppl_hazards') or comp.get('suppl_h') or []:
            code = (euh.get('code') if isinstance(euh, dict) else str(euh)).strip()
            if not re.fullmatch(r'EUH\d{3}A?', code or ''):
                continue
            lim = limits.get(code)
            if lim and lim.get('min') is not None and conc < float(lim['min']):
                continue
            # SEA Ek-2 1.2.5: karışımda EUH070 — kayıtta aksi belirtilmedikçe madde ≥ %0,1
            if code == 'EUH070' and not (lim and lim.get('min') is not None) and conc < 0.1:
                continue
            extra = {'source': 'SEA Ek-6 / Annex VI'}
            if lim and lim.get('min') is not None:
                extra['note'] = f"Uyumlaştırılmış kayıt eşiği: C ≥ %{lim['min']:g}"
            _add(detected, detected_codes, code, cas, name, **extra)

    manual_check = [c for c in ['EUH001', 'EUH018', 'EUH044', 'EUH070', 'EUH071',
                                'EUH209', 'EUH209A', 'EUH401'] if c not in detected_codes]

    return {
        'euh_codes': sorted(detected_codes),
        'euh_details': sorted(detected, key=lambda x: x['code']),
        'manual_check': manual_check,
    }


def euh210_triggers(components: List[Dict], mixture_form: str = 'liquid') -> List[Dict]:
    """SEA Ek-2 2.10 (EUH210 "Talep halinde güvenlik bilgi formu sağlanabilir.") — karışımı bu ifadeye
    götüren bileşenler. Yalnız zararlı olarak SINIFLANDIRILMAYAN ve halkın kullanımı için TASARLANMAYAN
    karışımlarda uygulanır (bu iki koşul çağıran tarafta — sds_pipeline — kontrol edilir).
      - ≥ %0,1: cilt hassaslaştırıcı 1 / 1B, solunum hassaslaştırıcı 1 / 1B, kanserojen Kat.2
      - ≥ %0,01: cilt / solunum hassaslaştırıcı 1A
      - cilt hassaslaştırıcıda özel sınırın 1/10'u; özel sınırı < %0,1 olan solunum hassaslaştırıcıda da
      - ≥ %0,1: üreme sistemine toksik 1A / 1B / 2 veya anne sütü (laktasyon)
      - münferit ≥ %1 (gaz karışımında ≥ %0,2): başka bir sağlık / çevre zararı sınıfı veya TR işyeri
        maruz kalma sınır değeri (28733 Ek-1 / 28730 Ek-2) olan madde
    Döner: [{'cas', 'name', 'conc', 'reason'}]"""
    from app.services.clp_service import _normalize_scl_list
    from app.services.tr_oel_service import get_oel
    gas = (mixture_form or '').lower() == 'gas'
    out = []
    for comp in components:
        cas = str(comp.get('cas', '') or comp.get('cas_no', '')).strip()
        name = comp.get('name_tr') or comp.get('name') or cas
        conc = float(comp.get('concMax') or comp.get('conc') or comp.get('concentration') or 0)
        if conc <= 0:
            continue
        hz = comp.get('hazards') or []
        classes = {(h.get('h_class') or '').replace('*', '').strip() for h in hz}
        codes = {(h.get('h_code') or '').replace('*', '').strip()[:4].upper() for h in hz}
        scl = {}
        for e in _normalize_scl_list(comp.get('sclRaw') or comp.get('scl') or []):
            hc = (e.get('h_code') or '').replace('*', '').strip()[:4]
            if hc in ('H317', 'H334') and e.get('c_min') is not None:
                scl[hc] = min(float(e['c_min']), scl.get(hc, float(e['c_min'])))
        reason = None
        skin1a = any('Skin Sens. 1A' in c or 'Cilt Hassas. 1A' in c for c in classes)
        resp1a = any('Resp. Sens. 1A' in c or 'Solunum Hassas. 1A' in c for c in classes)
        if 'H317' in codes:
            thr = scl['H317'] / 10 if 'H317' in scl else (0.01 if skin1a else 0.1)
            if conc >= thr:
                reason = f'cilt hassaslaştırıcı ≥ %{thr:g}'
        if not reason and 'H334' in codes:
            thr = scl['H334'] / 10 if scl.get('H334', 1) < 0.1 else (0.01 if resp1a else 0.1)
            if conc >= thr:
                reason = f'solunum hassaslaştırıcı ≥ %{thr:g}'
        if not reason and 'H351' in codes and conc >= 0.1:
            reason = 'kanserojen Kat.2 ≥ %0,1'
        if not reason and codes & {'H360', 'H361', 'H362'} and conc >= 0.1:
            reason = 'üreme sistemine toksik / laktasyon ≥ %0,1'
        if not reason and conc >= (0.2 if gas else 1.0):
            health_env = {c for c in codes if c[:2] in ('H3', 'H4')}
            if health_env:
                reason = f'sağlık/çevre zararı sınıfı ({", ".join(sorted(health_env))}) ≥ %{0.2 if gas else 1:g}'
            elif cas and get_oel(cas):
                reason = f'TR işyeri maruz kalma sınır değeri var, ≥ %{0.2 if gas else 1:g}'
        if reason:
            out.append({'cas': cas, 'name': name, 'conc': conc, 'reason': reason})
    return out


