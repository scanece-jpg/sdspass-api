"""
Etiket Teknik Rehber Kartı — A4
CLP 1272/2008 + KKDİK uyumlu etiket bilgi kartı.
"""

import io
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, black, white
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame,
    Paragraph, Spacer, Table, TableStyle, Image,
    HRFlowable, KeepTogether,
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT

from app.services.ghs_pictogram import get_ghs_codes, get_icon_path, GHS_LABELS_TR
from app.services.codes_i18n import get_h, get_p

try:
    from app.services.pdf_sds_service import _register_fonts as _reg
    _reg()
except Exception:
    pass

_FONT      = 'DejaVuSans'
_FONT_BOLD = 'DejaVuSans-Bold'
_RED       = HexColor('#CC0000')
_ORANGE    = HexColor('#CC6600')
_DARK      = HexColor('#1A1A2E')
_GRAY      = HexColor('#444444')
_LGRAY     = HexColor('#888888')
_BG        = HexColor('#F7F8FA')
_ACCENT    = HexColor('#1A5276')
_BORDER    = HexColor('#CCCCCC')


def _label_size(volume_l: float):
    if volume_l <= 3:
        return 52, 74, 10
    if volume_l <= 50:
        return 74, 105, 12
    if volume_l <= 500:
        return 105, 148, 16
    return 148, 210, 16


def _st():
    return {
        'title':   ParagraphStyle('gt', fontName=_FONT_BOLD, fontSize=14, textColor=_DARK, leading=18),
        'sub':     ParagraphStyle('gs', fontName=_FONT,      fontSize=8,  textColor=_LGRAY, leading=11),
        'h1':      ParagraphStyle('g1', fontName=_FONT_BOLD, fontSize=9,  textColor=_ACCENT, leading=12),
        'body':    ParagraphStyle('gb', fontName=_FONT,      fontSize=8,  textColor=_GRAY,  leading=11),
        'small':   ParagraphStyle('gm', fontName=_FONT,      fontSize=7,  textColor=_LGRAY, leading=10),
        'code':    ParagraphStyle('gc', fontName=_FONT_BOLD, fontSize=8,  textColor=_ACCENT, leading=11),
        'note':    ParagraphStyle('gn', fontName=_FONT,      fontSize=7,  textColor=_LGRAY, leading=10),
        'footer':  ParagraphStyle('gf', fontName=_FONT,      fontSize=6.5,textColor=_LGRAY, leading=9,
                                  alignment=TA_CENTER),
    }


def _p(text, style):
    text = str(text).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    return Paragraph(text, style)


def _section(text, st):
    return KeepTogether([
        HRFlowable(width='100%', thickness=0.6, color=_ACCENT, spaceBefore=3*mm, spaceAfter=1.5*mm),
        Paragraph(f'<b>{text}</b>', st['h1']),
        Spacer(1, 1.5*mm),
    ])


def _code_tbl(rows, col1_w, total_w, st):
    if not rows:
        return Paragraph('—', st['small'])
    data = []
    for code, txt in rows:
        c = str(code).replace('&', '&amp;')
        t = str(txt).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        data.append([Paragraph(f'<b>{c}</b>', st['code']),
                     Paragraph(t, st['body'])])
    t = Table(data, colWidths=[col1_w, total_w - col1_w])
    t.setStyle(TableStyle([
        ('VALIGN',       (0,0),(-1,-1),'TOP'),
        ('TOPPADDING',   (0,0),(-1,-1),2),
        ('BOTTOMPADDING',(0,0),(-1,-1),2),
        ('LEFTPADDING',  (0,0),(-1,-1),3),
        ('RIGHTPADDING', (0,0),(-1,-1),3),
        ('ROWBACKGROUNDS',(0,0),(-1,-1),[white,_BG]),
        ('LINEBELOW',    (0,0),(-1,-1),0.25,_BORDER),
    ]))
    return t


def generate_label_guide_pdf(data: dict) -> bytes:
    product    = data.get('product', {})
    components = data.get('components', [])
    clp        = data.get('clp', {})
    supplier   = data.get('supplier', {})
    volume_l   = float(data.get('volume_l', 1.0))
    ufi        = data.get('ufi', '')

    h_codes    = clp.get('h_codes', [])
    p_codes    = clp.get('p_codes', [])
    signal_raw = clp.get('signal_word', '').lower()
    is_danger  = signal_raw == 'danger'
    signal_txt = 'TEHLİKE' if is_danger else 'UYARI'
    signal_col = _RED if is_danger else _ORANGE

    w_mm, h_mm, pic_min_mm = _label_size(volume_l)
    ghs_codes = get_ghs_codes(h_codes)

    st  = _st()
    buf = io.BytesIO()
    pw, ph = A4
    mg    = 14 * mm
    inner = pw - 2 * mg

    doc = BaseDocTemplate(buf, pagesize=A4,
                          leftMargin=mg, rightMargin=mg,
                          topMargin=mg, bottomMargin=mg)

    def _on_page(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(_RED)
        canvas.rect(0, ph - 8*mm, pw, 8*mm, fill=1, stroke=0)
        canvas.setFillColor(white)
        canvas.setFont(_FONT_BOLD, 8)
        canvas.drawString(mg, ph - 5.5*mm, 'ETİKET TEKNİK REHBER KARTI')
        canvas.setFont(_FONT, 7)
        canvas.drawRightString(pw - mg, ph - 5.5*mm, 'SDSPass')
        canvas.setStrokeColor(_BORDER)
        canvas.setLineWidth(0.4)
        canvas.line(mg, 11*mm, pw - mg, 11*mm)
        canvas.setFillColor(_LGRAY)
        canvas.setFont(_FONT, 6.5)
        canvas.drawCentredString(pw/2, 7.5*mm,
            'Bu kart SDSPass tarafından otomatik olarak üretilmiştir.')
        canvas.restoreState()

    frame = Frame(mg, 15*mm, inner, ph - mg - 15*mm,
                  leftPadding=0, rightPadding=0, topPadding=8*mm, bottomPadding=0)
    doc.addPageTemplates([PageTemplate(id='main', frames=[frame], onPage=_on_page)])

    story = []
    sp = lambda n=1: Spacer(1, n*mm)
    vol_str = f'{int(volume_l)} L' if volume_l == int(volume_l) else f'{volume_l} L'

    # ── BAŞLIK + FİRMA + ACİL ────────────────────────────────────────────────
    story.append(Paragraph(product.get('name', '—'), st['title']))
    story.append(Paragraph('Etiket Teknik Rehber Kartı', st['sub']))
    story.append(sp(1.5))

    # Firma ve acil tel üstte yan yana
    sup_block = [Paragraph('<b>Tedarikçi</b>', st['h1'])]
    for k in ['name', 'address', 'phone']:
        if supplier.get(k):
            sup_block.append(_p(supplier[k], st['body']))

    acil_block = [
        Paragraph('<b>Acil Durum Telefonu</b>', st['h1']),
        Paragraph('114 — Ulusal Zehir Danışma (7/24)', st['body']),
    ]
    if supplier.get('phone'):
        acil_block.append(_p(f'Firma: {supplier["phone"]}', st['body']))

    top_tbl = Table([[sup_block, acil_block]], colWidths=[inner*0.6, inner*0.4])
    top_tbl.setStyle(TableStyle([
        ('VALIGN',      (0,0),(-1,-1),'TOP'),
        ('TOPPADDING',  (0,0),(-1,-1),0),
        ('BOTTOMPADDING',(0,0),(-1,-1),0),
        ('LEFTPADDING', (0,0),(-1,-1),0),
        ('RIGHTPADDING',(0,0),(-1,-1),0),
        ('LINEAFTER',   (0,0),(0,-1),0.4,_BORDER),
        ('LEFTPADDING', (1,0),(1,-1),8),
    ]))
    story.append(top_tbl)

    # ── ETİKET BOYUTU ─────────────────────────────────────────────────────────
    story.append(_section('Etiket Boyutu', st))
    story.append(Paragraph(
        f'Bu ambalaj ({vol_str}) için minimum etiket boyutu: '
        f'<b>{w_mm:.0f} × {h_mm:.0f} mm</b> · '
        f'Minimum piktogram boyutu: <b>{pic_min_mm} × {pic_min_mm} mm</b>',
        st['body']))
    story.append(sp(0.5))
    story.append(Paragraph(
        'Not: Bu boyut CLP Tüzüğü Ek-I §1.2.1 kapsamında belirlenen minimum değerdir. '
        'Etiket bu ölçüden küçük olamaz, daha büyük olabilir.',
        st['note']))

    # ── PİKTOGRAMLAR ──────────────────────────────────────────────────────────
    story.append(_section('GHS Piktogramları', st))
    if ghs_codes:
        pic_size = min(18*mm, (inner - 4*mm) / len(ghs_codes) - 4*mm)
        imgs, names, descs = [], [], []
        for ghs in ghs_codes:
            path = get_icon_path(ghs)
            imgs.append(Image(str(path), width=pic_size, height=pic_size) if path
                        else _p(ghs, st['code']))
            names.append(Paragraph(f'<b>{ghs}</b>', ParagraphStyle('pn', fontName=_FONT_BOLD,
                          fontSize=7, textColor=_ACCENT, leading=9, alignment=TA_CENTER)))
            descs.append(Paragraph(GHS_LABELS_TR.get(ghs,''), ParagraphStyle('pd', fontName=_FONT,
                          fontSize=6.5, textColor=_GRAY, leading=9, alignment=TA_CENTER)))
        col_w_pic = inner / len(ghs_codes)
        pt = Table([imgs, names, descs], colWidths=[col_w_pic]*len(ghs_codes))
        pt.setStyle(TableStyle([
            ('ALIGN',        (0,0),(-1,-1),'CENTER'),
            ('VALIGN',       (0,0),(-1,-1),'MIDDLE'),
            ('TOPPADDING',   (0,0),(-1,-1),2),
            ('BOTTOMPADDING',(0,0),(-1,-1),2),
        ]))
        story.append(pt)
        story.append(sp(1))
        story.append(Paragraph(
            f'Teknik özellik: Beyaz zemin · Kırmızı çerçeve (#CC0000) · Siyah sembol · '
            f'Min. boyut: {pic_min_mm} × {pic_min_mm} mm',
            st['small']))
    else:
        story.append(Paragraph('Bu ürün için piktogram gerekmemektedir.', st['body']))

    # ── SİNYAL KELİMESİ ───────────────────────────────────────────────────────
    story.append(_section('Sinyal Kelimesi', st))
    sig_color_hex = '#CC0000' if is_danger else '#CC6600'
    renk_kodu    = '#CC0000' if is_danger else '#CC6600'
    renk_adi     = 'Kirmizi' if is_danger else 'Turuncu'
    sig_aciklama = (
        f'Bu urun TEHLIKELIDIR. Etiket uzerine buyuk, kalin ve {renk_adi} ({renk_kodu}) renkte yazilmalidir.'
        if is_danger else
        f'Bu urun UYARI gerektirir. Etiket uzerine buyuk, kalin ve {renk_adi} ({renk_kodu}) renkte yazilmalidir.'
    )
    story.append(Paragraph(
        f'<font color="{sig_color_hex}"><b>{signal_txt}</b></font>',
        ParagraphStyle('sig', fontName=_FONT_BOLD, fontSize=16, leading=20, alignment=TA_CENTER,
                       textColor=signal_col)))
    story.append(sp(0.8))
    story.append(Paragraph(sig_aciklama, st['note']))

    # ── TEHLİKE İFADELERİ (H) ─────────────────────────────────────────────────
    h_rows = []
    seen = set()
    for h in h_codes:
        base = h.split()[0]
        if base in seen: continue
        seen.add(base)
        txt = get_h('TR', base) or ''
        h_rows.append((base, txt))

    story.append(_section(f'Tehlike İfadeleri — {len(h_rows)} kod', st))
    story.append(_code_tbl(h_rows, 20*mm, inner, st))

    # ── ÖNLEM İFADELERİ (P) ───────────────────────────────────────────────────
    p_rows = []
    seen_p = set()
    for p in p_codes:
        if p in seen_p: continue
        seen_p.add(p)
        txt = get_p('TR', p) or ''
        p_rows.append((p, txt))

    story.append(_section(f'Önlem İfadeleri — {len(p_rows)} kod', st))
    story.append(_code_tbl(p_rows, 28*mm, inner, st))

    # ── UFI + TEHLİKELİ BİLEŞENLER ───────────────────────────────────────────
    hazardous = [c for c in components if c.get('hCodes') or c.get('h_codes')]

    if ufi or hazardous:
        story.append(_section('Diğer Zorunlu Unsurlar', st))
        extra_items = []

        if ufi:
            extra_items.append([
                Paragraph('<b>UFI Kodu</b>', st['h1']),
                _p(ufi, st['code']),
            ])

        if hazardous:
            comp_rows = []
            for c in hazardous[:6]:
                name = c.get('name','')
                cas  = c.get('cas') or c.get('cas_no','')
                cmax = c.get('concMax','')
                conc = f' <%{cmax}' if cmax else ''
                comp_rows.append(_p(f'{name} (CAS {cas}){conc}'.strip(), st['small']))
            if len(hazardous) > 6:
                comp_rows.append(Paragraph(f'... +{len(hazardous)-6} bileşen daha', st['small']))
            extra_items.append([Paragraph('<b>Tehlikeli Bileşenler</b>', st['h1'])] + comp_rows)

        for item in extra_items:
            story.append(KeepTogether(item))
            story.append(sp(1))

    # ── OKUNABİLİRLİK GEREKSİNİMLERİ ────────────────────────────────────────
    story.append(_section('Okunabilirlik ve Görünürlük Gereksinimleri', st))
    okun_rows = [
        ('Okunabilirlik', f'Min. 6 punto, gozle rahatca okunabilmeli. '
                          f'Koyu yazi + acik zemin (yuksek kontrast). '
                          f'Sinyal kelimesi renk kodu: {renk_kodu}.'),
        ('Dayaniklilik',  'Yazilar ve piktogramlar normal kullanim, tasima ve saklama '
                          'kosullarinda silinmez olmali. Etiket ambalaja saglamca yapismali.'),
        ('Dil / Zemin',   'Turkiye pazarinda Turkce zorunlu. Piktogramlar beyaz zemin, '
                          'kirmizi cerceve (#CC0000) ile net baskilmali.'),
    ]
    lbl_s = ParagraphStyle('okl', fontName=_FONT_BOLD, fontSize=7.5, textColor=_ACCENT, leading=10)
    val_s = ParagraphStyle('okv', fontName=_FONT,      fontSize=7.5, textColor=_GRAY,  leading=10)
    ok_data = [[Paragraph(r[0], lbl_s), Paragraph(r[1], val_s)] for r in okun_rows]
    ok_tbl = Table(ok_data, colWidths=[30*mm, inner - 30*mm])
    ok_tbl.setStyle(TableStyle([
        ('VALIGN',        (0,0),(-1,-1),'TOP'),
        ('TOPPADDING',    (0,0),(-1,-1),3),
        ('BOTTOMPADDING', (0,0),(-1,-1),3),
        ('LEFTPADDING',   (0,0),(-1,-1),4),
        ('RIGHTPADDING',  (0,0),(-1,-1),4),
        ('ROWBACKGROUNDS',(0,0),(-1,-1),[white, _BG]),
        ('LINEBELOW',     (0,0),(-1,-1),0.25,_BORDER),
    ]))
    story.append(ok_tbl)
    story.append(sp(1.5))

    # ── MEVZUAT BİLGİ NOTU ────────────────────────────────────────────────────
    story.append(sp(3))
    story.append(HRFlowable(width='100%', thickness=0.5, color=_BORDER,
                            spaceBefore=0, spaceAfter=2*mm))
    mevzuat_notu = (
        'Bu etiket aşağıdaki mevzuat kapsamında hazırlanmıştır:\n'
        'CLP Tüzüğü (AT) 1272/2008 — Md.17 (zorunlu unsurlar) · Md.18 (tehlikeli bileşenler) · '
        'Md.20 (sinyal kelimesi) · Md.21 (tehlike ifadeleri) · Md.22 (önlem ifadeleri, maks. 6) · '
        'Md.45 (UFI) · Ek-I §1.2.1 (etiket boyutu ve piktogram boyutu) · Ek-I §1.2.1.2 (piktogram öncelik kuralları)\n'
        'KKDİK Yönetmeliği — Ek-2 Bölüm 1.4 (acil durum telefon numarası)\n'
        'GHS — BM Küresel Uyumlaştırılmış Sistem, 7. Revize Edilmiş Baskı'
    )
    story.append(Paragraph(mevzuat_notu, st['note']))

    doc.build(story)
    return buf.getvalue()
