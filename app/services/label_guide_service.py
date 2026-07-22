"""
Etiket Teknik Rehber Kartı — tek sayfa A4
CLP 1272/2008 + KKDİK uyumlu, matbaa için.
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
        'title':   ParagraphStyle('gt', fontName=_FONT_BOLD, fontSize=13, textColor=_DARK, leading=16),
        'sub':     ParagraphStyle('gs', fontName=_FONT,      fontSize=7.5, textColor=_LGRAY, leading=10),
        'h1':      ParagraphStyle('g1', fontName=_FONT_BOLD, fontSize=8.5, textColor=_ACCENT, leading=11),
        'body':    ParagraphStyle('gb', fontName=_FONT,      fontSize=7.5, textColor=_GRAY,  leading=10),
        'small':   ParagraphStyle('gm', fontName=_FONT,      fontSize=6.5, textColor=_LGRAY, leading=9),
        'code':    ParagraphStyle('gc', fontName=_FONT_BOLD, fontSize=7.5, textColor=_ACCENT,leading=10),
        'footer':  ParagraphStyle('gf', fontName=_FONT,      fontSize=6,   textColor=_LGRAY, leading=8,
                                  alignment=TA_CENTER),
    }


def _p(text, style):
    text = str(text).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    return Paragraph(text, style)


def _section(text, st):
    return KeepTogether([
        HRFlowable(width='100%', thickness=0.6, color=_ACCENT, spaceBefore=2*mm, spaceAfter=1*mm),
        Paragraph(f'<b>{text}</b>', st['h1']),
        Spacer(1, 1*mm),
    ])


def _tbl(rows, col_w, st):
    data = []
    for label, value in rows:
        lbl = str(label).replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
        val = str(value).replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
        data.append([Paragraph(f'<b>{lbl}</b>', st['body']),
                     Paragraph(val, st['body'])])
    t = Table(data, colWidths=col_w)
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
    signal_col = '#CC0000' if is_danger else '#CC6600'

    w_mm, h_mm, pic_min_mm = _label_size(volume_l)
    ghs_codes = get_ghs_codes(h_codes)

    st  = _st()
    buf = io.BytesIO()
    pw, ph = A4
    mg = 12 * mm
    inner = pw - 2 * mg

    doc = BaseDocTemplate(buf, pagesize=A4,
                          leftMargin=mg, rightMargin=mg,
                          topMargin=mg, bottomMargin=mg)

    def _on_page(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(_RED)
        canvas.rect(0, ph - 7*mm, pw, 7*mm, fill=1, stroke=0)
        canvas.setFillColor(white)
        canvas.setFont(_FONT_BOLD, 7.5)
        canvas.drawString(mg, ph - 5*mm, 'ETİKET TEKNİK REHBER KARTI')
        canvas.setFont(_FONT, 6.5)
        canvas.drawRightString(pw - mg, ph - 5*mm, 'SDSPass | CLP 1272/2008 + KKDİK')
        canvas.setStrokeColor(_BORDER)
        canvas.setLineWidth(0.4)
        canvas.line(mg, 10*mm, pw - mg, 10*mm)
        canvas.setFillColor(_LGRAY)
        canvas.setFont(_FONT, 6)
        canvas.drawCentredString(pw/2, 7*mm,
            'CLP Tüzüğü (AT) 1272/2008 ve KKDİK Yönetmeliği kapsamında SDSPass tarafından üretilmiştir.')
        canvas.restoreState()

    frame = Frame(mg, 14*mm, inner, ph - mg - 14*mm,
                  leftPadding=0, rightPadding=0, topPadding=7*mm, bottomPadding=0)
    doc.addPageTemplates([PageTemplate(id='main', frames=[frame], onPage=_on_page)])

    story = []
    sp = lambda n=1: Spacer(1, n*mm)

    # BAŞLIK
    story.append(Paragraph(product.get('name', '—'), st['title']))
    story.append(Paragraph('Etiket Teknik Rehber Kartı — CLP 1272/2008 + KKDİK', st['sub']))
    story.append(sp(1.5))

    # ─── ÜST: 2 sütun (Sol: Boyut tablosu | Sağ: Piktogramlar + Sinyal) ──────
    left_w  = 88 * mm
    right_w = inner - left_w - 4*mm

    # -- Sol: Boyut tablosu
    vol_str  = f'{int(volume_l)} L' if volume_l == int(volume_l) else f'{volume_l} L'
    size_idx = 0 if volume_l <= 3 else 1 if volume_l <= 50 else 2 if volume_l <= 500 else 3
    hdr_s = ParagraphStyle('sh', fontName=_FONT_BOLD, fontSize=6.5, textColor=white, leading=9)
    size_rows_data = [
        [Paragraph(c, hdr_s) for c in ['Ambalaj', 'Min. Etiket', 'Min. Pikt.']],
        ['≤ 3 L',      '52×74 mm',   '10×10 mm'],
        ['3–50 L',     '74×105 mm',  '12×12 mm'],
        ['50–500 L',   '105×148 mm', '16×16 mm'],
        ['> 500 L',    '148×210 mm', '16×16 mm'],
    ]
    for i, row in enumerate(size_rows_data[1:], 0):
        sty = st['code'] if i == size_idx else st['small']
        size_rows_data[i+1] = [Paragraph(c, sty) for c in row]

    st_tbl = Table(size_rows_data, colWidths=[22*mm, 34*mm, 28*mm])
    st_tbl.setStyle(TableStyle([
        ('BACKGROUND',    (0,0),(-1,0), _ACCENT),
        ('ALIGN',         (0,0),(-1,-1),'CENTER'),
        ('VALIGN',        (0,0),(-1,-1),'MIDDLE'),
        ('TOPPADDING',    (0,0),(-1,-1),2),
        ('BOTTOMPADDING', (0,0),(-1,-1),2),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[white,_BG]),
        ('LINEBELOW',     (0,0),(-1,-1),0.25,_BORDER),
        ('BACKGROUND',    (0,size_idx+1),(-1,size_idx+1), HexColor('#EAF4FB')),
        ('LINEABOVE',     (0,size_idx+1),(-1,size_idx+1), 1.0, _ACCENT),
        ('LINEBELOW',     (0,size_idx+1),(-1,size_idx+1), 1.0, _ACCENT),
    ]))

    left_block = [
        Paragraph('<b>Etiket Boyutu</b> (CLP Ek-I §1.2.1)', st['h1']),
        sp(0.8),
        st_tbl,
        sp(0.8),
        Paragraph(f'Bu ürün: <b>{w_mm:.0f}×{h_mm:.0f} mm</b> ({vol_str})', st['body']),
    ]

    # -- Sağ: Piktogramlar
    right_block = [Paragraph('<b>Piktogramlar</b> (CLP Ek-I §1.2.1.2)', st['h1']), sp(0.8)]
    if ghs_codes:
        pic_size = min(14*mm, (right_w - 4*mm) / len(ghs_codes) - 2*mm)
        imgs, names = [], []
        for ghs in ghs_codes:
            path = get_icon_path(ghs)
            imgs.append(Image(str(path), width=pic_size, height=pic_size) if path else _p(ghs, st['code']))
            names.append(Paragraph(f'<b>{ghs}</b>', ParagraphStyle('pn', fontName=_FONT_BOLD,
                          fontSize=6, textColor=_ACCENT, leading=8, alignment=TA_CENTER)))
        col_w_pic = right_w / len(ghs_codes)
        pt = Table([imgs, names], colWidths=[col_w_pic]*len(ghs_codes))
        pt.setStyle(TableStyle([('ALIGN',(0,0),(-1,-1),'CENTER'),('VALIGN',(0,0),(-1,-1),'MIDDLE'),
                                ('TOPPADDING',(0,0),(-1,-1),1),('BOTTOMPADDING',(0,0),(-1,-1),1)]))
        right_block.append(pt)
        right_block.append(sp(0.8))
        right_block.append(Paragraph(f'Beyaz zemin · #CC0000 çerçeve · min. {pic_min_mm}×{pic_min_mm} mm', st['small']))
    else:
        right_block.append(Paragraph('Piktogram gerekmemektedir.', st['body']))

    right_block += [
        sp(1.5),
        Paragraph('<b>Sinyal Kelimesi</b> (CLP Md.20)', st['h1']),
        sp(0.5),
        Paragraph(f'<font color="{signal_col}"><b>{signal_txt}</b></font> — Kalın, okunaklı boyut', st['body']),
    ]

    two_col = Table(
        [[left_block, right_block]],
        colWidths=[left_w, right_w],
    )
    two_col.setStyle(TableStyle([
        ('VALIGN',(0,0),(-1,-1),'TOP'),
        ('LEFTPADDING',(0,0),(-1,-1),0),
        ('RIGHTPADDING',(0,0),(-1,-1),0),
        ('TOPPADDING',(0,0),(-1,-1),0),
        ('BOTTOMPADDING',(0,0),(-1,-1),0),
        ('LINEAFTER',(0,0),(0,-1),0.4,_BORDER),
        ('LEFTPADDING',(1,0),(1,-1),4),
    ]))
    story.append(two_col)
    story.append(sp(1.5))

    # ─── H KODLARI + P KODLARI yan yana ──────────────────────────────────────
    h_w = (inner - 4*mm) / 2
    p_w = inner - h_w - 4*mm

    # H kodları
    h_rows = []
    seen = set()
    for h in h_codes:
        base = h.split()[0]
        if base in seen: continue
        seen.add(base)
        txt = get_h('TR', base) or ''
        h_rows.append((base, txt))

    # P kodları
    p_rows = []
    seen_p = set()
    for p in p_codes:
        if p in seen_p: continue
        seen_p.add(p)
        txt = get_p('TR', p) or ''
        p_rows.append((p, txt))

    def _code_tbl(rows, w):
        if not rows:
            return Paragraph('—', st['small'])
        data = []
        for code, txt in rows:
            c = str(code).replace('&','&amp;')
            t = str(txt).replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
            data.append([Paragraph(f'<b>{c}</b>', st['code']),
                         Paragraph(t, st['small'])])
        t = Table(data, colWidths=[14*mm, w - 14*mm])
        t.setStyle(TableStyle([
            ('VALIGN',(0,0),(-1,-1),'TOP'),
            ('TOPPADDING',(0,0),(-1,-1),1),('BOTTOMPADDING',(0,0),(-1,-1),1),
            ('LEFTPADDING',(0,0),(-1,-1),2),('RIGHTPADDING',(0,0),(-1,-1),2),
            ('ROWBACKGROUNDS',(0,0),(-1,-1),[white,_BG]),
            ('LINEBELOW',(0,0),(-1,-1),0.2,_BORDER),
        ]))
        return t

    h_block = [
        Paragraph(f'<b>Tehlike İfadeleri</b> (CLP Md.21) — {len(h_rows)} kod', st['h1']),
        sp(0.8),
        _code_tbl(h_rows, h_w),
    ]
    p_note = ' · maks. 6 önerilir (Md.22)' if len(p_rows) > 0 else ''
    p_block = [
        Paragraph(f'<b>Önlem İfadeleri</b> (CLP Md.22){p_note}', st['h1']),
        sp(0.8),
        _code_tbl(p_rows, p_w),
    ]

    hp_tbl = Table([[h_block, p_block]], colWidths=[h_w, p_w])
    hp_tbl.setStyle(TableStyle([
        ('VALIGN',(0,0),(-1,-1),'TOP'),
        ('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0),
        ('TOPPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),0),
        ('LINEAFTER',(0,0),(0,-1),0.4,_BORDER),
        ('LEFTPADDING',(1,0),(1,-1),4),
    ]))
    story.append(hp_tbl)
    story.append(sp(1.5))

    # ─── ALT BİLGİ SATIRI: Tedarikçi | Acil Tel | UFI | Bileşenler ──────────
    bottom_items = []

    # Tedarikçi (CLP Md.17)
    sup_lines = [Paragraph('<b>Tedarikçi</b> (CLP Md.17)', st['h1'])]
    if supplier.get('name'):
        sup_lines.append(_p(supplier['name'], st['body']))
    if supplier.get('address'):
        sup_lines.append(_p(supplier['address'], st['body']))
    if supplier.get('phone'):
        sup_lines.append(_p(supplier['phone'], st['body']))
    bottom_items.append(sup_lines)

    # Acil Telefon (KKDİK Ek-2 §1.4)
    acil_lines = [
        Paragraph('<b>Acil Telefon</b> (KKDİK Ek-2 §1.4)', st['h1']),
        Paragraph('114 — Ulusal Zehir Danışma', st['body']),
    ]
    if supplier.get('phone'):
        acil_lines.append(_p(f'Firma: {supplier["phone"]}', st['body']))
    bottom_items.append(acil_lines)

    # UFI
    ufi_lines = [Paragraph('<b>UFI</b> (CLP Md.45)', st['h1'])]
    if ufi:
        ufi_lines.append(_p(ufi, st['code']))
    else:
        ufi_lines.append(Paragraph('—', st['body']))
    bottom_items.append(ufi_lines)

    # Tehlikeli bileşenler (CLP Md.18)
    hazardous = [c for c in components if c.get('hCodes') or c.get('h_codes')]
    comp_lines = [Paragraph('<b>Bileşenler</b> (CLP Md.18)', st['h1'])]
    if hazardous:
        for c in hazardous[:4]:
            name = c.get('name','')
            cas  = c.get('cas') or c.get('cas_no','')
            cmax = c.get('concMax','')
            conc = f'<%{cmax}' if cmax else ''
            comp_lines.append(_p(f'{name} CAS {cas} {conc}'.strip(), st['small']))
        if len(hazardous) > 4:
            comp_lines.append(Paragraph(f'+{len(hazardous)-4} bileşen daha', st['small']))
    else:
        comp_lines.append(Paragraph('—', st['body']))
    bottom_items.append(comp_lines)

    n = len(bottom_items)
    col_w_b = inner / n
    bot_tbl = Table([bottom_items], colWidths=[col_w_b]*n)
    bot_tbl.setStyle(TableStyle([
        ('VALIGN',(0,0),(-1,-1),'TOP'),
        ('TOPPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),0),
        ('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0),
        ('LINEAFTER',(0,0),(-2,-1),0.4,_BORDER),
        ('LEFTPADDING',(1,0),(-1,-1),4),
    ]))
    story.append(bot_tbl)
    story.append(sp(1.5))

    # ─── FOOTER ──────────────────────────────────────────────────────────────
    story.append(HRFlowable(width='100%', thickness=0.4, color=_BORDER,
                            spaceBefore=0, spaceAfter=1*mm))
    story.append(Paragraph(
        'Bu kart SDSPass tarafından otomatik üretilmiştir. '
        'CLP Tüzüğü (AT) 1272/2008 · KKDİK Yönetmeliği · GHS 7. Revize Baskı',
        st['footer']))

    doc.build(story)
    return buf.getvalue()
