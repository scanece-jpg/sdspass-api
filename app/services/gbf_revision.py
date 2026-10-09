"""
GBF revizyon yönetimi — KKDİK Ek-2 0.2.5 ve Bölüm 16(a).

0.2.5: "Güvenlik Bilgi Formunun hazırlanma tarihi ilk sayfada verilir. ... güncellendiğinde ... ‘Revizyon: (tarih)’
olarak tanımlanan hazırlanma tarihi ayrıca versiyon numarası, revizyon numarası, değiştirme tarihi ve hangi
versiyonun değiştirildiğine ilişkin diğer veriler ilk sayfada yer alır."
16(a): revizyonda önceki versiyonda yapılan değişiklikler (başka bölümde belirtilmediyse) Bölüm 16'da verilir.

Önceki versiyonu bilmek için GBF'ye görünmez bir özet gömülür (PDF bilgi sözlüğünde "SDSPassOzet"). Özet YALNIZ
GBF'de zaten basılı bilgiyi içerir (sınıflandırma, etiket, Bölüm 3'te listelenen satırlar, Bölüm 9 satırları,
taşıma) — listelenmeyen bileşenler ve tam reçete yüzdeleri gömülmez; PDF'i alan alıcı GBF'de görmediği bir bilgiyi
özetten öğrenemez. Revizyonda kullanıcı eski PDF'i yükler (veya aynı tarayıcıda son versiyon saklıdır); program
önceki versiyon / tarihi ilk sayfaya yazar ve değişiklik listesini önerir (KDU düzenler).
"""
import base64
import json
from typing import Dict, List, Optional

OZET_KEY = 'SDSPassOzet'
OZET_SURUM = 1

_B9_KEYS = ('flash_point', 'boiling_point', 'melting_point', 'ph', 'density', 'vapor_pressure', 'solubility',
            'viscosity', 'auto_ignition')
_B9_AD = {'flash_point': 'parlama noktası', 'boiling_point': 'kaynama noktası', 'melting_point': 'erime noktası',
          'ph': 'pH', 'density': 'yoğunluk', 'vapor_pressure': 'buhar basıncı', 'solubility': 'çözünürlük',
          'viscosity': 'viskozite', 'auto_ignition': 'kendiliğinden tutuşma sıcaklığı'}


def _disp(v) -> str:
    if isinstance(v, dict):
        if v.get('na') or v.get('nd'):
            return str(v.get('display') or '').strip()
        return str(v.get('display') if v.get('display') not in (None, '') else (v.get('calc') or '')).strip()
    return str(v if v is not None else '').strip()


def ozet(sds_data: Dict) -> Dict:
    """GBF'de basılı bilgilerden özet (generate_sds_pdf sonrası — Bölüm 3 satırları sds_data['_sec3_rows'])."""
    clp = sds_data.get('clp') or {}
    p = sds_data.get('p_codes') or {}
    t = sds_data.get('transport') or {}
    rev = sds_data.get('revision') or {}
    prod = sds_data.get('product') or {}
    phys = sds_data.get('phys_props') or {}
    return {
        'surum': OZET_SURUM,
        'urun': {'ad': prod.get('name', ''), 'kod': prod.get('code', ''), 'form': prod.get('form', '')},
        'revizyon': {'versiyon': str(rev.get('version') or ''), 'no': str(rev.get('no') or ''),
                     'tarih': str(rev.get('date') or '')},
        'b2': {
            'siniflandirma': sorted(clp.get('all_h_codes') or clp.get('h_codes') or []),
            'uyari': clp.get('signal_word') or '',
            'piktogram': sorted(clp.get('pictograms') or []),
            'h': sorted(clp.get('h_codes') or []),
            'euh': sorted((sds_data.get('euh') or {}).get('euh_codes') or []),
            'p': list(((p.get('label') or {}).get('selected')) or []),
        },
        'b3': [{'cas': r.get('cas', ''), 'ad': r.get('name', ''), 'derisim': r.get('concentration', ''),
                'siniflandirma': r.get('hazards', '')} for r in (sds_data.get('_sec3_rows') or [])],
        'b9': {k: _disp(phys.get(k)) for k in _B9_KEYS if _disp(phys.get(k))},
        'b14': ({'tehlikeli_degil': True} if t.get('not_regulated') else
                {'un': t.get('un_no') or '', 'ad': t.get('shipping_name') or '', 'sinif': t.get('hazard_class') or '',
                 'ambalaj_grubu': t.get('packing_group') or ''}),
    }


def gom(pdf_bytes: bytes, oz: Dict) -> bytes:
    """Özeti PDF bilgi sözlüğüne gömer (görünmez; sayfa içeriği değişmez)."""
    import fitz
    doc = fitz.open(stream=pdf_bytes, filetype='pdf')
    try:
        kind, val = doc.xref_get_key(-1, 'Info')
        if kind != 'xref':
            doc.set_metadata(doc.metadata or {})
            kind, val = doc.xref_get_key(-1, 'Info')
        info_xref = int(val.split()[0])
        payload = base64.b64encode(json.dumps(oz, ensure_ascii=False).encode('utf-8')).hex()
        doc.xref_set_key(info_xref, OZET_KEY, f'<{payload}>')
        return doc.tobytes(garbage=0, deflate=True)
    finally:
        doc.close()


def oku(pdf_bytes: bytes) -> Optional[Dict]:
    """Eski GBF'den özeti okur; SDSPass özeti yoksa None."""
    import fitz
    try:
        doc = fitz.open(stream=pdf_bytes, filetype='pdf')
    except Exception:
        return None
    try:
        kind, val = doc.xref_get_key(-1, 'Info')
        if kind != 'xref':
            return None
        kind, raw = doc.xref_get_key(int(val.split()[0]), OZET_KEY)
        if kind != 'string' or not raw:
            return None
        oz = json.loads(base64.b64decode(raw).decode('utf-8'))
        return oz if isinstance(oz, dict) and oz.get('surum') else None
    except Exception:
        return None
    finally:
        doc.close()


def _liste(a: List[str], b: List[str]) -> str:
    eklenen = [x for x in b if x not in a]
    cikan = [x for x in a if x not in b]
    parts = []
    if eklenen:
        parts.append('eklendi: ' + ', '.join(eklenen))
    if cikan:
        parts.append('çıkarıldı: ' + ', '.join(cikan))
    return '; '.join(parts)


def farklar(onceki: Dict, simdiki: Dict) -> List[str]:
    """Bölüm bölüm değişiklik satırları (Bölüm 16(a) önerisi — KDU düzenler)."""
    out: List[str] = []
    a2, b2 = onceki.get('b2') or {}, simdiki.get('b2') or {}
    s = _liste(a2.get('siniflandirma') or [], b2.get('siniflandirma') or [])
    if s:
        out.append(f'Bölüm 2.1 sınıflandırma — {s}.')
    _uk = {'Danger': 'Tehlike', 'Warning': 'Dikkat'}
    if (a2.get('uyari') or '') != (b2.get('uyari') or ''):
        out.append(f"Bölüm 2.2 uyarı kelimesi: {_uk.get(a2.get('uyari'), a2.get('uyari') or 'yok')} → "
                   f"{_uk.get(b2.get('uyari'), b2.get('uyari') or 'yok')}.")
    for k, ad in (('piktogram', 'piktogramlar'), ('euh', 'EUH ifadeleri'), ('p', 'etiket önlem ifadeleri')):
        s = _liste(a2.get(k) or [], b2.get(k) or [])
        if s:
            out.append(f'Bölüm 2.2 {ad} — {s}.')
    def _ad(r, k):
        return (r.get('ad') or k or '').split(';')[0].strip()
    a3 = {r.get('cas') or r.get('ad'): r for r in (onceki.get('b3') or [])}
    b3 = {r.get('cas') or r.get('ad'): r for r in (simdiki.get('b3') or [])}
    for k, r in b3.items():
        if k not in a3:
            out.append(f"Bölüm 3: {_ad(r, k)} eklendi.")
        else:
            o = a3[k]
            if (o.get('derisim') or '') != (r.get('derisim') or ''):
                out.append(f"Bölüm 3: {_ad(r, k)} derişimi {o.get('derisim')} → {r.get('derisim')}.")
            if (o.get('siniflandirma') or '') != (r.get('siniflandirma') or ''):
                out.append(f"Bölüm 3: {_ad(r, k)} sınıflandırması güncellendi.")
    for k, r in a3.items():
        if k not in b3:
            out.append(f"Bölüm 3: {_ad(r, k)} çıkarıldı.")
    a9, b9 = onceki.get('b9') or {}, simdiki.get('b9') or {}
    for k in _B9_KEYS:
        if (a9.get(k) or '') != (b9.get(k) or ''):
            out.append(f"Bölüm 9: {_B9_AD[k]} güncellendi.")
    a14, b14 = onceki.get('b14') or {}, simdiki.get('b14') or {}
    if a14 != b14:
        def _t(x):
            return 'tehlikeli madde değil' if x.get('tehlikeli_degil') else \
                f"{x.get('un', '')} {x.get('ad', '')}, sınıf {x.get('sinif', '')}, ambalaj grubu {x.get('ambalaj_grubu', '') or '—'}".strip()
        out.append(f'Bölüm 14 taşımacılık: {_t(a14)} → {_t(b14)}.')
    return out
