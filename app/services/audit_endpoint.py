"""
GBF Denetimi — /api/v1/audit

Herhangi bir GBF PDF'ini (bizim ürettiğimiz veya kullanıcının yüklediği) KKDİK Ek-2 kapsamlı soru
listesine (data/sds_audit_checklist.json) göre denetler ve tek rapor döner:
  - kod kontrolleri  → app/services/audit_checks.py
  - Jev soruları     → app/services/audit_jev.py (yalnız KVKK onayı verildiyse; metin dış servise gider)
  - KDU / görsel     → "KDU baksın" maddeleri
Karar grupları: eksik / kdu (KDU baksın) / uygun / kontrol_yok.
"""
import base64
import os

from fastapi import APIRouter, Body, HTTPException

router = APIRouter()
MAX_PDF_BYTES = 15 * 1024 * 1024


@router.post('/api/v1/audit')
async def audit_sds(data: dict = Body(...)):
    """Girdi: {pdf_base64, dosya_adi?, jev_onay: bool}"""
    import fitz
    from app.services.audit_checks import run_code_checks
    from app.services.audit_jev import run_jev_audit, load_checklist, applies, split_sections, derive_facts

    b64 = (data.get('pdf_base64') or '').split(',')[-1]
    try:
        raw = base64.b64decode(b64, validate=False)
    except Exception:
        raise HTTPException(400, 'PDF okunamadı (base64 hatalı).')
    if not raw or len(raw) > MAX_PDF_BYTES:
        raise HTTPException(400, 'PDF boş veya 15 MB sınırından büyük.')
    try:
        doc = fitz.open(stream=raw, filetype='pdf')
        pages = [p.get_text() for p in doc]
    except Exception:
        raise HTTPException(400, 'Dosya PDF olarak açılamadı.')
    text = '\n'.join(pages)
    if len(text.strip()) < 300:
        raise HTTPException(422, 'PDF\'ten metin çıkarılamadı — taranmış (resim) PDF olabilir. '
                                 'Metin içeren bir PDF yükleyin.')
    secs = split_sections(text)
    if len(secs) < 8:
        raise HTTPException(422, f'GBF bölümleri tanınamadı (bulunan bölüm sayısı: {len(secs)}). '
                                 'Belge bir GBF olmayabilir.')
    facts = derive_facts(secs, text)

    code = run_code_checks(pages, facts)['sonuclar']
    for r in code:
        r['yontem'] = 'kod'

    jev_info = {'calisti': False, 'neden': '', 'token': 0}
    jev_rows = []
    jev_qs = [q for q in load_checklist()['sorular'] if q['yontem'] == 'jev' and applies(q['kosul'], facts)]
    if not data.get('jev_onay'):
        jev_info['neden'] = 'KVKK onayı verilmedi — metin dış servise gönderilmedi.'
    elif not os.environ.get('TYPESAFE_API_KEY', '').strip():
        jev_info['neden'] = 'Jev (TypeSafe) anahtarı sunucuda tanımlı değil.'
    else:
        try:
            jr = await run_jev_audit(text, facts=facts)
            jev_info.update(calisti=True, token=jr['token'], hatalar=jr['hatalar'])
            for r in jr['sonuclar']:
                p = r.get('p')
                r['aciklama'] = (f'Jev seçimi: {r["secim"]} ({p})' if r.get('secim') else
                                 f'Jev olasılığı: {p}' if p is not None else 'Jev cevap vermedi.')
                r['yontem'] = 'jev'
                jev_rows.append(r)
        except Exception as e:
            jev_info['neden'] = f'Jev çalıştırılamadı: {e}'
    if not jev_info['calisti']:
        jev_rows = [{'id': q['id'], 'bolum': q['bolum'], 'dayanak': q['dayanak'], 'onem': q['onem'],
                     'soru': q['soru_tr'], 'karar': 'kontrol_yok', 'aciklama': jev_info['neden'], 'yontem': 'jev'}
                    for q in jev_qs]

    order = {q['id']: n for n, q in enumerate(load_checklist()['sorular'])}
    rows = sorted(code + jev_rows, key=lambda x: order.get(x['id'], 0))
    ozet = {k: sum(1 for r in rows if r['karar'] == k) for k in ('eksik', 'kdu', 'uygun', 'kontrol_yok')}
    # Önem sırası: zorunlu eksikler hata, koşullu eksikler uyarı
    ozet['zorunlu_eksik'] = sum(1 for r in rows if r['karar'] == 'eksik' and r['onem'] == 'zorunlu')
    return {
        'dosya': data.get('dosya_adi') or 'GBF.pdf', 'sayfa': len(pages), 'kosullar': sorted(facts),
        'ozet': ozet, 'jev': jev_info, 'sonuclar': rows,
        'dayanak': 'KKDİK Ek-2 (RG 23.06.2017/30105 Mükerrer); SEA Yönetmeliği; KKDİK Usul ve Esaslar (2025)',
    }
