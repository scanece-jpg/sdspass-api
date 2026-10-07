"""Kontrol seti — referans ürünlerle GBF regresyon kontrolü (her push öncesi).

Her referans ürün için sağ panel hesabı (/api/v1/sds/calculate) ve GBF PDF'i (/api/v1/sds/pdf) üretilir, denetimin
kod kontrolleri (audit_checks) çalıştırılır ve sonuçlar aşağıdaki beklenenlerle karşılaştırılır:
  - H kodları ve uyarı kelimesi (yönetmelik kurallarıyla elle doğrulanmış değerler, 2026-10-07)
  - GBF metninde bulunması / bulunmaması gereken ifadeler (uydurma varsayılan cümleler dahil)
  - Denetimde "eksik" çıkmaması (beklenen istisnalar hariç)
Beklenenden farklı bir sonuç çıkarsa çıkış kodu 1 olur (pre-push kancası push'u durdurur).

Kullanım:  python scripts/kontrol_seti.py          (yalnız kod kontrolleri — ücretsiz)
           python scripts/kontrol_seti.py --jev    (DIPOL 369 için Jev de çalışır — TYPESAFE_API_KEY, ücretli)
Not: test sırasında data/substances_custom.json'a eklenen kayıtlar çalışma sonunda geri alınır.
"""
import asyncio
import base64
import os
import re
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
sys.stdout.reconfigure(encoding='utf-8')

CUSTOM = os.path.join(ROOT, 'data', 'substances_custom.json')

# ── Referans ürünler ─────────────────────────────────────────────────────────
# h: beklenen H kodları (sıra önemsiz); signal: 'Danger' / 'Warning' / '' (uyarı kelimesi yok)
# var / yok: GBF metninde (boşluklar tek boşluğa indirgenmiş) bulunması / bulunmaması gereken ifadeler
# s3_yok: Bölüm 3'te listelenmemesi gereken CAS'lar; kdu_ok: "eksik" yerine beklenen KDU maddeleri
# Not: bileşen H kodları Bölüm 3/16'da geçtiği için karışımın H kodları metinle değil 'h' ile kontrol edilir.
_UYDURMA = ['Uygun yangın söndürücü kullanın.', 'Sınıflandırma ve etiketleme bilgileri güncellenmiştir',
            '(Tavsiye: İyi havalandırma sağlayın)', 'beyan edilecek bileşen sınıfı bulunmamaktadır']
URUNLER = [
    {'ad': 'Nitrik asit %15 (aşındırıcı, ADR)', 'bil': [('7697-37-2', 15), ('7732-18-5', 85)],
     'h': ['H314'], 'signal': 'Danger',
     'var': ['UN2031', '14.1 UN Numarası', 'Uygun olmayan söndürücüler', 'Doğrudan su jeti'],
     'yok': _UYDURMA, 's3_yok': ['7732-18-5']},
    {'ad': 'DIPOL 369 (su bazlı deterjan, H318)', 'det': True, 'kullanim': 'mutfak temizleme ürünü',
     'bil': [('68439-50-9', 2.9), ('141-43-5', 0.2), ('7732-18-5', 96.9)],
     'h': ['H318'], 'signal': 'Danger',
     'var': ["%5'ten az: noniyonik yüzey aktif maddeler", 'Uygulanamaz — tehlikeli madde değildir',
             'Uygulanamaz — sulu, alevlenir olarak sınıflandırılmamış ürün',
             'Bölüm 1 zararlılık kategorilerinin hiçbirinde', 'Kirlenmiş giysiler', 'İlk yardım yapanlar',
             'Tip C (delinme süresi ≥ 10 dk', 'ABEK-P2', 'Atık işlemeyi etkileyen özellikler'],
     'yok': _UYDURMA + ['Tavsiye: İyi havalandırma'], 's3_yok': ['7732-18-5'], 'kdu_ok': ['T-hesap']},
    {'ad': 'Toluen + %0,5 benzen (alevlenir, CMR)', 'bil': [('108-88-3', 99.5), ('71-43-2', 0.5)],
     'h': ['H225', 'H304', 'H315', 'H336', 'H340', 'H350', 'H361D', 'H373'], 'signal': 'Danger',
     'var': ['28730 sayılı Kanserojen', 'Ek-17 madde 48', 'Ek-17 madde 5', 'Alkole dayanıklı köpük',
             'P5c (Alevlenir sıvılar', '%1.1 – %', 'hesaplanmış – ISO 10156'],
     'yok': _UYDURMA},
    {'ad': 'Benzil benzoat %20 (yalnız H412)', 'bil': [('120-51-4', 20), ('7732-18-5', 80)],
     'h': ['H412'], 'signal': '', 'var': ['Uyarı Kelimesi Yok'], 'yok': _UYDURMA + ['Uyarı Kelimesi Dikkat'],
     's3_yok': ['7732-18-5'], 'kdu_ok': ['T-hesap']},
    {'ad': 'Gliserin %5 (tehlikesiz)', 'bil': [('56-81-5', 5), ('7732-18-5', 95)],
     'h': [], 'signal': '', 'var': ['belirtilmesi gereken madde bulunmamaktadır', 'İlk yayın.'],
     'yok': _UYDURMA, 's3_yok': ['7732-18-5', '56-81-5'], 'kdu_ok': ['T-hesap']},
    {'ad': 'Metanol %60 (akut toksik, BEKRA Bölüm 2)', 'bil': [('67-56-1', 60), ('7732-18-5', 40)],
     'h': ['H225', 'H301', 'H311', 'H331', 'H370'], 'signal': 'Danger',
     'var': ['Bölüm 2 adlandırılmış madde: Metanol', '28733 sayılı Kimyasal Maddelerle'],
     'yok': _UYDURMA, 's3_yok': ['7732-18-5']},
    {'ad': 'NPE %5 deterjan (Ek-17 madde 46, ÖBK)', 'det': True, 'kullanim': 'endüstriyel temizleme ürünü',
     'bil': [('9016-45-9', 5), ('7732-18-5', 95)], 'h': ['H410'], 'signal': 'Warning',
     'var': ['Ek-17 madde 46', 'İhracatta Md.8'], 'yok': _UYDURMA, 's3_yok': ['7732-18-5'],
     'kdu_ok': ['15.1-izin-kisit', 'T-hesap']},
    {'ad': 'Etanolamin %2 (SEA Tablo 3.2.3 eşiği)', 'bil': [('141-43-5', 2), ('7732-18-5', 98)],
     'h': ['H315', 'H319'], 'signal': 'Warning', 'var': ['Ağırlıklı: 10x2.0', '(CLP Tablo 3.2.3)'], 'yok': _UYDURMA,
     's3_yok': ['7732-18-5']},
]


def _norm(t: str) -> str:
    t = re.sub(r'Sayfa \d+ / \d+\s.*?formatına uygundur\.\s', ' ', t, flags=re.S)
    return re.sub(r'\s+', ' ', t)


def main(run_jev: bool) -> int:
    from fastapi.testclient import TestClient
    from app.main import app
    import fitz
    from app.services.audit_checks import run_code_checks

    c = TestClient(app)

    def comp(cas, conc):
        r = c.get('/api/v1/sds/substance/lookup', params={'cas': cas, 'form': 'liquid'}).json()
        return {'cas': cas, 'name': r.get('name') or cas, 'name_tr': r.get('name_tr', ''), 'ec_no': r.get('ec_no', ''),
                'conc': conc, 'concMax': conc, 'hazards': r.get('hazards', []), 'sclRaw': r.get('scl', []),
                'm_factors': {}, 'ate': None}

    hatalar, t0 = 0, time.time()
    dipol_pages = None
    for u in URUNLER:
        sorun = []
        comps = [comp(a, b) for a, b in u['bil']]
        calc = {'components': comps, 'form': 'liquid', 'usage': 'industrial', 'lang': 'TR'}
        r = c.post('/api/v1/sds/calculate', json=calc).json()
        h = sorted(str(x).split()[0].upper() for x in (r.get('h_codes') or []))
        if h != sorted(x.upper() for x in u['h']):
            sorun.append(f"H kodları {h} — beklenen {sorted(u['h'])}")
        if (r.get('signal') or '') != u['signal']:
            sorun.append(f"uyarı kelimesi {r.get('signal')!r} — beklenen {u['signal']!r}")
        body = {'lang': 'TR', 'product': {'name': u['ad'][:40], 'form': 'liquid', 'usage': 'industrial',
                                          'is_detergent': bool(u.get('det')), 'usage_desc': u.get('kullanim', '')},
                'supplier': {'name': 'Kontrol Seti A.Ş.', 'address': 'Örnek Mah. No:1 İstanbul', 'phone': '0212 000 00 00',
                             'email': 'kontrol@ornek.com'},
                'components': comps, 'calc_input': calc, 'phys_props': {}, 'phys_methods': {},
                'revision': {'no': '1', 'date': '07.10.2026', 'notes': ''}}
        j = c.post('/api/v1/sds/pdf', json=body).json()
        b64 = next((v for v in j.values() if isinstance(v, str) and len(v) > 5000), None)
        if not b64:
            print(f"✗ {u['ad']}: PDF üretilemedi — {str(j)[:200]}")
            hatalar += 1
            continue
        pages = [p.get_text() for p in fitz.open(stream=base64.b64decode(b64), filetype='pdf')]
        if u.get('det'):
            dipol_pages = dipol_pages or pages
        t = _norm('\n'.join(pages))
        for s in u['var']:
            if s not in t:
                sorun.append(f'GBF\'de yok: "{s}"')
        for s in u['yok']:
            if s in t:
                sorun.append(f'GBF\'de olmamalı: "{s}"')
        a, b = t.find('3.2 Karışımlar'), t.find('BÖLÜM 4')
        s3 = t[a:b] if a >= 0 else ''
        for cas in u.get('s3_yok', []):
            if cas in s3:
                sorun.append(f'Bölüm 3\'te listelenmemeli: {cas}')
        au = run_code_checks(pages)['sonuclar']
        eksik = [x['id'] for x in au if x['karar'] == 'eksik']
        if eksik:
            sorun.append('denetimde eksik: ' + ', '.join(eksik))
        kdu_beklenen = set(u.get('kdu_ok', []))
        for x in au:
            if x['id'] in ('15.1-izin-kisit', '15.1-deterjan', '2.2-tutarlilik') and x['karar'] == 'kdu' \
                    and x['id'] not in kdu_beklenen:
                sorun.append(f"beklenmeyen KDU: {x['id']} — {x['aciklama'][:90]}")
        for k in kdu_beklenen - {'T-hesap'}:
            if not any(x['id'] == k and x['karar'] == 'kdu' for x in au):
                sorun.append(f'beklenen KDU uyarısı çıkmadı: {k}')
        if sorun:
            hatalar += 1
            print(f"✗ {u['ad']}")
            for s in sorun:
                print(f'    - {s}')
        else:
            print(f"✓ {u['ad']}")

    if run_jev and dipol_pages:
        from app.services.audit_jev import run_jev_audit
        jr = asyncio.run(run_jev_audit('\n'.join(dipol_pages)))
        jeksik = sorted(x.get('id') for x in jr.get('sonuclar', []) if x.get('karar') == 'eksik')
        beklenen = ['16-kdu']    # Bölüm 16 KDU bilgisi henüz eklenmedi (bilinçli)
        if jeksik != beklenen:
            hatalar += 1
            print(f'✗ Jev (DIPOL 369): eksik {jeksik} — beklenen {beklenen}')
        else:
            print(f"✓ Jev (DIPOL 369): yalnız beklenen eksik {beklenen} ({jr.get('token')} token)")

    print(f"\n{len(URUNLER)} ürün, {round(time.time() - t0)} sn — "
          + ('HATA YOK' if not hatalar else f'{hatalar} üründe HATA — push yapılmamalı'))
    return 1 if hatalar else 0


if __name__ == '__main__':
    _yedek = open(CUSTOM, 'rb').read() if os.path.exists(CUSTOM) else None
    try:
        kod = main('--jev' in sys.argv)
    finally:
        if _yedek is not None:
            open(CUSTOM, 'wb').write(_yedek)   # testin eklediği madde kayıtlarını geri al
    sys.exit(kod)
