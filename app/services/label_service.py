"""
CLP Etiket Üretici
==================
KKDİK / CLP 1272/2008 Madde 31 uyumlu etiket PDF üretir.

Boyutlar (ambalaj hacmine göre — CLP Ek-I §1.2.1):
  ≤ 3 L   → 52 × 74 mm
  3–50 L  → 74 × 105 mm
  50–500 L → 105 × 148 mm
  > 500 L  → 148 × 210 mm

Minimum piktogram boyutu (CLP Ek-I §1.2.1.2):
  ≤ 3 L   → 10 × 10 mm  (etiket alanının ≥ 1/15'i)
  3–50 L  → 12 × 12 mm
  > 50 L  → 16 × 16 mm

Zorunlu unsurlar (CLP Madde 17):
  1. Tedarikçi adı, adresi, telefonu
  2. Nominal miktar
  3. Ürün tanımlayıcı
  4. Piktogramlar
  5. Sinyal kelimesi
  6. Tehlike ifadeleri (H)
  7. Önlem ifadeleri (P)  ← zorunlu
  8. EUH ifadeleri (varsa)
  9. UFI kodu (karışımlar)

Yerleşim (CLP Ek-I §1.2.1.3):
  - Piktogramlar: beyaz zemin, kırmızı çerçeve, köşegen kare
  - Sinyal kelimesi + H + P bir arada gruplanmalı
"""

import io
from typing import List, Dict, Optional

from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.colors import HexColor, black, white, red
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame,
    Paragraph, Spacer, Table, TableStyle, Image, KeepTogether,
    HRFlowable,
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas as rl_canvas
import os

from app.services.ghs_pictogram import get_ghs_codes, get_icon_path
from app.services.codes_i18n import get_h, get_p

try:
    from app.services.pdf_sds_service import _register_fonts as _reg
    _reg()
except Exception:
    pass
_FONT      = 'DejaVuSans'
_FONT_BOLD = 'DejaVuSans-Bold'

_RED   = HexColor('#CC0000')
_BLACK = HexColor('#000000')
_GRAY  = HexColor('#444444')


# ── CLP boyut tablosu ─────────────────────────────────────────────────────────

def _label_size(volume_l: float):
    """Hacme göre (W mm, H mm, min piktogram mm) döndür."""
    if volume_l <= 3:
        return 52, 74, 10
    if volume_l <= 50:
        return 74, 105, 12
    if volume_l <= 500:
        return 105, 148, 16
    return 148, 210, 16


# ── Yardımcı ─────────────────────────────────────────────────────────────────

def _para(text: str, style) -> Paragraph:
    text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    return Paragraph(text, style)


def _build_styles(font_base: float):
    common = dict(fontName=_FONT,      leading=font_base * 1.3)
    bold   = dict(fontName=_FONT_BOLD, leading=font_base * 1.35)
    return {
        'product':  ParagraphStyle('lbl_product',  fontSize=font_base + 3,
                                   alignment=TA_CENTER, **bold,
                                   textColor=_BLACK),
        'vol':      ParagraphStyle('lbl_vol',      fontSize=font_base,
                                   alignment=TA_CENTER, **common,
                                   textColor=_GRAY),
        'supplier': ParagraphStyle('lbl_supplier', fontSize=font_base - 0.5,
                                   alignment=TA_CENTER, **common,
                                   textColor=_GRAY),
        'signal_danger':  ParagraphStyle('lbl_sig_d', fontSize=font_base + 2,
                                         alignment=TA_CENTER, **bold,
                                         textColor=_RED),
        'signal_warning': ParagraphStyle('lbl_sig_w', fontSize=font_base + 2,
                                         alignment=TA_CENTER, **bold,
                                         textColor=HexColor('#CC6600')),
        'sec':      ParagraphStyle('lbl_sec',      fontSize=font_base - 0.5,
                                   fontName=_FONT_BOLD,
                                   leading=(font_base - 0.5) * 1.3,
                                   textColor=_BLACK),
        'stmt':     ParagraphStyle('lbl_stmt',     fontSize=font_base - 1,
                                   alignment=TA_LEFT, **common,
                                   textColor=_GRAY),
        'ufi':      ParagraphStyle('lbl_ufi',      fontSize=font_base - 0.5,
                                   alignment=TA_CENTER, **bold,
                                   textColor=_BLACK),
        'comp':     ParagraphStyle('lbl_comp',     fontSize=font_base - 1,
                                   alignment=TA_LEFT, **common,
                                   textColor=_GRAY),
        'warn':     ParagraphStyle('lbl_warn',     fontSize=font_base,
                                   alignment=TA_CENTER, **bold,
                                   textColor=_RED),
    }


def _divider(color=None):
    return HRFlowable(width='100%', thickness=0.5,
                      color=color or HexColor('#CCCCCC'), spaceAfter=1.5*mm, spaceBefore=1.5*mm)


# ── Ölçü oku çizici ──────────────────────────────────────────────────────────

def _draw_arrow(canvas, x1, y1, x2, y2, arrow_size=3):
    """x1,y1 → x2,y2 yönünde ok çiz (her iki uçta ok başı)."""
    import math
    canvas.line(x1, y1, x2, y2)
    for (ax, ay, bx, by) in [(x1, y1, x2, y2), (x2, y2, x1, y1)]:
        angle = math.atan2(by - ay, bx - ax)
        for side in (+0.4, -0.4):
            ex = ax + arrow_size * math.cos(angle + math.pi + side)
            ey = ay + arrow_size * math.sin(angle + math.pi + side)
            canvas.line(ax, ay, ex, ey)


# ── Sayfa kenarlığı + ölçü notasyonu çizen canvas callback ───────────────────

def _make_page_callback(lbl_x, lbl_y, w_pt, h_pt, w_mm, h_mm):
    """
    Her sayfaya:
      - Etiket etrafına kırmızı kenarlık
      - Alt: yatay ölçü oku + "XX mm" yazısı
      - Sağ: dikey ölçü oku + "XX mm" yazısı
    çizer.
    lbl_x, lbl_y: etiketin sol-alt köşesi (pt cinsinden sayfa koordinatı)
    """
    ANN   = 10 * mm   # ölçü çizgisi mesafesi
    TICK  = 2.5 * mm  # referans çizgisi uzunluğu
    COL   = HexColor('#444444')
    ARROW = 4

    def _draw(canvas, doc):
        canvas.saveState()

        # Etiket kenarlığı
        canvas.setStrokeColor(_RED)
        canvas.setLineWidth(1.2)
        canvas.rect(lbl_x, lbl_y, w_pt, h_pt)

        # Ölçü çizgileri rengi
        canvas.setStrokeColor(COL)
        canvas.setFillColor(COL)
        canvas.setLineWidth(0.5)

        # ── Genişlik oku (altta) ───────────────────────────────────────────
        ay = lbl_y - ANN
        # Sol ve sağ referans çizgileri
        canvas.line(lbl_x,        lbl_y - TICK * 0.3, lbl_x,        lbl_y - ANN - TICK * 0.5)
        canvas.line(lbl_x + w_pt, lbl_y - TICK * 0.3, lbl_x + w_pt, lbl_y - ANN - TICK * 0.5)
        # Ok
        _draw_arrow(canvas, lbl_x + 1, ay, lbl_x + w_pt - 1, ay, ARROW)
        # Yazı
        canvas.setFont('Helvetica', 6.5)
        canvas.drawCentredString(lbl_x + w_pt / 2, ay - 4, f'{w_mm:.0f} mm')

        # ── Yükseklik oku (sağda) ─────────────────────────────────────────
        ax = lbl_x + w_pt + ANN
        # Alt ve üst referans çizgileri
        canvas.line(lbl_x + w_pt + TICK * 0.3, lbl_y,        ax + TICK * 0.5, lbl_y)
        canvas.line(lbl_x + w_pt + TICK * 0.3, lbl_y + h_pt, ax + TICK * 0.5, lbl_y + h_pt)
        # Ok
        _draw_arrow(canvas, ax, lbl_y + 1, ax, lbl_y + h_pt - 1, ARROW)
        # Yazı — dikey
        canvas.saveState()
        canvas.translate(ax + 5, lbl_y + h_pt / 2)
        canvas.rotate(90)
        canvas.drawCentredString(0, 0, f'{h_mm:.0f} mm')
        canvas.restoreState()

        canvas.restoreState()

    return _draw


# ── Piktogram tablosu ─────────────────────────────────────────────────────────

def _pic_table(ghs_codes, pic_size_mm, inner_w):
    """GHS piktogramlarını tek satır tablo olarak döndür."""
    if not ghs_codes:
        return None
    pic_pt  = pic_size_mm * mm
    cells   = []
    for ghs in ghs_codes:
        path = get_icon_path(ghs)
        if path:
            cells.append(Image(str(path), width=pic_pt, height=pic_pt))
        else:
            cells.append(_para(f'[{ghs}]',
                               ParagraphStyle('ph', fontName=_FONT, fontSize=7,
                                              alignment=TA_CENTER, textColor=_RED)))
    n      = len(cells)
    col_w  = inner_w / n
    tbl    = Table([cells], colWidths=[col_w] * n)
    tbl.setStyle(TableStyle([
        ('ALIGN',        (0,0), (-1,-1), 'CENTER'),
        ('VALIGN',       (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING',   (0,0), (-1,-1), 1),
        ('BOTTOMPADDING',(0,0), (-1,-1), 1),
    ]))
    return tbl


# ── Ana üretici ───────────────────────────────────────────────────────────────

def generate_label_pdf(data: dict) -> bytes:
    """
    Veri sözlüğünden CLP uyumlu etiket PDF'i üret.

    data anahtarları:
      product    : {name, form, usage}
      components : [{name, cas, concMin, concMax, hCodes, hClass}]
      clp        : {h_codes, signal_word, p_codes}
      supplier   : {name, address, phone}
      volume_l   : float
      lang       : 'TR' | 'EN'
      ufi        : str (isteğe bağlı)
      euh        : {codes, details} (isteğe bağlı)
    """
    lang       = data.get('lang', 'TR')
    product    = data.get('product', {})
    components = data.get('components', [])
    clp        = data.get('clp', {})
    supplier   = data.get('supplier', {})
    volume_l   = float(data.get('volume_l', 1.0))
    ufi        = data.get('ufi', '')
    usage      = product.get('usage', 'industrial')

    h_codes    = clp.get('h_codes', [])
    p_codes    = clp.get('p_codes', [])
    signal_raw = clp.get('signal_word', '').lower()
    is_danger  = signal_raw == 'danger'
    if lang == 'TR':
        signal_txt = 'TEHLİKE' if is_danger else 'UYARI'
    else:
        signal_txt = 'DANGER'  if is_danger else 'WARNING'

    w_mm, h_mm, pic_min_mm = _label_size(volume_l)
    # Görsel kalite için min'den büyük piktogram — sayfanın %20'si max
    pic_mm    = max(pic_min_mm, min(w_mm * 0.18, 22))
    font_base = max(5.5, min(8.5, h_mm / 14))

    styles  = _build_styles(font_base)
    buf     = io.BytesIO()

    # Etiket boyutları
    w_pt = w_mm * mm
    h_pt = h_mm * mm

    # Ölçü notasyonu için sayfa etrafına ekstra boşluk
    ANN_B = 18 * mm   # alt (genişlik oku)
    ANN_R = 18 * mm   # sağ (yükseklik oku)
    ANN_T = 6  * mm   # üst boşluk
    ANN_L = 6  * mm   # sol boşluk

    page_w = w_pt + ANN_L + ANN_R
    page_h = h_pt + ANN_B + ANN_T

    # Etiket sol-alt köşesi sayfa koordinatında
    lbl_x = ANN_L
    lbl_y = ANN_B

    margin  = 3.5 * mm
    inner_w = w_pt - 2 * margin

    doc = BaseDocTemplate(
        buf,
        pagesize=(page_w, page_h),
        leftMargin=lbl_x + margin,
        rightMargin=ANN_R + margin,
        topMargin=ANN_T + margin,
        bottomMargin=lbl_y + margin,
    )
    frame = Frame(lbl_x + margin, lbl_y + margin,
                  inner_w, h_pt - 2 * margin,
                  leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    doc.addPageTemplates([PageTemplate(
        id='label', frames=[frame],
        onPage=_make_page_callback(lbl_x, lbl_y, w_pt, h_pt, w_mm, h_mm),
    )])

    story = []
    sp    = lambda n=1: Spacer(1, n * mm)

    # ── 1. Ürün adı ──────────────────────────────────────────────────────────
    prod_name = product.get('name', '').strip()
    if prod_name:
        story.append(_para(prod_name, styles['product']))
        story.append(sp(0.5))

    # Nominal miktar (CLP Md.17(1)(c))
    vol_str = f'{int(volume_l)} L' if volume_l == int(volume_l) else f'{volume_l} L'
    story.append(_para(vol_str, styles['vol']))
    story.append(sp(1))

    # ── 2. Tedarikçi bilgisi ─────────────────────────────────────────────────
    sup_lines = [l for l in [
        supplier.get('name',''), supplier.get('address',''), supplier.get('phone','')
    ] if l]
    if sup_lines:
        for sl in sup_lines:
            story.append(_para(sl, styles['supplier']))
        story.append(sp(1.5))

    story.append(_divider(_RED))

    # ── 3. Piktogramlar ──────────────────────────────────────────────────────
    ghs_codes = get_ghs_codes(h_codes)
    tbl = _pic_table(ghs_codes, pic_mm, inner_w)
    if tbl:
        story.append(tbl)
        story.append(sp(1.5))

    # ── 4. Sinyal kelimesi ───────────────────────────────────────────────────
    if signal_txt:
        sig_style = styles['signal_danger'] if is_danger else styles['signal_warning']
        story.append(_para(signal_txt, sig_style))
        story.append(sp(1.5))

    story.append(_divider())

    # ── 5. Tehlike ifadeleri (H) ─────────────────────────────────────────────
    h_texts, seen_h = [], set()
    for h in h_codes:
        base = h.split()[0]
        if base in seen_h:
            continue
        seen_h.add(base)
        txt = get_h(lang, base)
        if txt and txt != base:
            h_texts.append(f'{base}: {txt}')

    if h_texts:
        story.append(_para(
            'Tehlike İfadeleri:' if lang == 'TR' else 'Hazard Statements:',
            styles['sec']))
        story.append(sp(0.5))
        for t in h_texts:
            story.append(_para(t, styles['stmt']))
        story.append(sp(1.5))

    # ── 6. Önlem ifadeleri (P) — CLP Madde 17(1)(f) ZORUNLU ─────────────────
    p_texts, seen_p = [], set()
    for p in p_codes:
        if p in seen_p:
            continue
        seen_p.add(p)
        txt = get_p(lang, p)
        if txt and txt != p:
            p_texts.append(f'{p}: {txt}')

    if p_texts:
        story.append(_para(
            'Önlem İfadeleri:' if lang == 'TR' else 'Precautionary Statements:',
            styles['sec']))
        story.append(sp(0.5))
        for t in p_texts:
            story.append(_para(t, styles['stmt']))
        story.append(sp(1.5))

    # ── 7. EUH ifadeleri ────────────────────────────────────────────────────
    euh_data    = data.get('euh', {})
    euh_details = euh_data.get('details', [])
    euh_codes   = euh_data.get('codes', [])
    euh_texts, seen_euh = [], set()
    for d in euh_details:
        code = d.get('code', '')
        if code in seen_euh:
            continue
        seen_euh.add(code)
        txt = d.get('text_tr') or d.get('text') or ''
        if txt:
            euh_texts.append(f'{code}: {txt}')
    for code in euh_codes:
        if code in seen_euh:
            continue
        seen_euh.add(code)
        from app.services.codes_i18n import EUH_STMTS
        txt = EUH_STMTS.get('EN' if lang == 'EN' else 'TR', {}).get(code, '')
        if txt:
            euh_texts.append(f'{code}: {txt}')
    if euh_texts:
        story.append(_para(
            'Ek Etiket Unsurları (EUH):' if lang == 'TR' else 'Supplemental Hazard Info (EUH):',
            styles['sec']))
        story.append(sp(0.5))
        for t in euh_texts:
            story.append(_para(t, styles['stmt']))
        story.append(sp(1.5))

    story.append(_divider())

    # ── 8. Tüketici ürünü ek uyarıları (CLP Madde 35) ───────────────────────
    if usage == 'consumer':
        warns = (
            ['Çocukların erişemeyeceği yerlerde saklayın.',
             'Zehirlenme şüphesinde: 114 Ulusal Zehir Danışma Merkezi']
            if lang == 'TR' else
            ['Keep out of reach of children.',
             'In case of poisoning: contact local Poison Centre.']
        )
        for w in warns:
            story.append(_para(w, styles['warn']))
        story.append(sp(1))

    # ── 9. UFI kodu ─────────────────────────────────────────────────────────
    if ufi:
        story.append(_para(f'UFI: {ufi}', styles['ufi']))
        story.append(sp(1))

    # ── 10. Tehlikeli bileşenler ─────────────────────────────────────────────
    hazardous = [c for c in components if c.get('hCodes') or c.get('h_codes')]
    if hazardous:
        story.append(_para(
            'İçerik (Tehlikeli Bileşenler):' if lang == 'TR' else 'Contents (Hazardous Ingredients):',
            styles['sec']))
        story.append(sp(0.5))
        for c in hazardous:
            name     = c.get('name', '')
            cas      = c.get('cas') or c.get('cas_no') or ''
            conc_min = c.get('concMin', '')
            conc_max = c.get('concMax', '')
            if conc_min and conc_max and str(conc_min) != str(conc_max):
                conc_str = f'%{conc_min}–{conc_max}'
            elif conc_max:
                conc_str = f'<%{conc_max}'
            else:
                conc_str = ''
            line = name
            if cas:
                line += f' (CAS {cas})'
            if conc_str:
                line += f' {conc_str}'
            story.append(_para(line, styles['comp']))

    doc.build(story)
    return buf.getvalue()
