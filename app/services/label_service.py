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
"""

import io
from typing import List, Dict, Optional

from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.colors import HexColor, black, white
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame,
    Paragraph, Spacer, Table, TableStyle, Image, KeepTogether,
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os

from app.services.ghs_pictogram import get_ghs_codes, get_icon_path
from app.services.codes_i18n import get_h, get_p

# Font kayıt — pdf_sds_service ile aynı mekanizma
try:
    from app.services.pdf_sds_service import _register_fonts as _reg
    _reg()
except Exception:
    pass
_FONT      = 'DejaVuSans'
_FONT_BOLD = 'DejaVuSans-Bold'

# ── CLP boyut tablosu ─────────────────────────────────────────────────────────

def _label_size(volume_l: float):
    """Hacme göre (W mm, H mm, piktogram mm) döndür."""
    if volume_l <= 3:
        return 52, 74, 10
    if volume_l <= 50:
        return 74, 105, 12
    if volume_l <= 500:
        return 105, 148, 16
    return 148, 210, 16


# ── Yardımcı ─────────────────────────────────────────────────────────────────

def _para(text: str, style) -> Paragraph:
    # HTML özel karakterleri temizle
    text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    return Paragraph(text, style)


def _build_styles(font_size_base: float):
    """Etiket boyutuna göre ölçeklenmiş stiller."""
    common = dict(fontName=_FONT, leading=font_size_base * 1.25)
    bold   = dict(fontName=_FONT_BOLD, leading=font_size_base * 1.3)
    return {
        'product':   ParagraphStyle('lbl_product',   fontSize=font_size_base + 2,
                                    alignment=TA_CENTER, **bold),
        'supplier':  ParagraphStyle('lbl_supplier',  fontSize=font_size_base - 1,
                                    alignment=TA_CENTER, **common),
        'signal':    ParagraphStyle('lbl_signal',    fontSize=font_size_base + 1,
                                    alignment=TA_CENTER,
                                    fontName=_FONT_BOLD,
                                    leading=(font_size_base + 1) * 1.3),
        'h_stmt':    ParagraphStyle('lbl_h',         fontSize=font_size_base - 0.5,
                                    alignment=TA_LEFT, **common),
        'p_stmt':    ParagraphStyle('lbl_p',         fontSize=font_size_base - 0.5,
                                    alignment=TA_LEFT, **common),
        'section':   ParagraphStyle('lbl_sec',       fontSize=font_size_base - 0.5,
                                    fontName=_FONT_BOLD,
                                    leading=(font_size_base - 0.5) * 1.3),
        'normal':    ParagraphStyle('lbl_norm',      fontSize=font_size_base - 1,
                                    alignment=TA_LEFT, **common),
        'ufi':       ParagraphStyle('lbl_ufi',       fontSize=font_size_base - 1,
                                    alignment=TA_CENTER,
                                    fontName=_FONT_BOLD,
                                    leading=(font_size_base - 1) * 1.3),
        'warning':   ParagraphStyle('lbl_warn',      fontSize=font_size_base,
                                    alignment=TA_CENTER,
                                    fontName=_FONT_BOLD,
                                    leading=font_size_base * 1.3,
                                    textColor=HexColor('#cc0000')),
    }


# ── Ana üretici ───────────────────────────────────────────────────────────────

def generate_label_pdf(data: dict) -> bytes:
    """
    Veri sözlüğünden CLP uyumlu etiket PDF'i üret ve bytes olarak döndür.

    data anahtarları:
      product      : {name, form, usage}
      components   : [{name, cas, concMin, concMax, hCodes, hClass}]
      clp          : {h_codes, signal_word, p_codes}
      supplier     : {name, address, phone}
      volume_l     : float  — ambalaj hacmi (litre)
      lang         : 'TR' | 'EN'
      ufi          : str (isteğe bağlı)
    """
    lang        = data.get('lang', 'TR')
    product     = data.get('product', {})
    components  = data.get('components', [])
    clp         = data.get('clp', {})
    supplier    = data.get('supplier', {})
    volume_l    = float(data.get('volume_l', 1.0))
    ufi         = data.get('ufi', '')
    usage       = product.get('usage', 'industrial')

    h_codes   = clp.get('h_codes', [])
    p_codes   = clp.get('p_codes', [])
    signal_tr = 'Tehlike' if clp.get('signal_word', '').lower() == 'danger' else 'Uyarı'
    signal_en = clp.get('signal_word', 'Warning')
    signal    = signal_tr if lang == 'TR' else signal_en

    w_mm, h_mm, pic_mm = _label_size(volume_l)
    font_base = max(5.5, min(8.0, h_mm / 16))

    styles = _build_styles(font_base)
    buf    = io.BytesIO()

    # Sayfa = tam etiket boyutu
    doc = BaseDocTemplate(
        buf,
        pagesize=(w_mm * mm, h_mm * mm),
        leftMargin=3 * mm, rightMargin=3 * mm,
        topMargin=3 * mm, bottomMargin=3 * mm,
    )
    inner_w = w_mm * mm - 6 * mm
    frame   = Frame(3 * mm, 3 * mm, inner_w, h_mm * mm - 6 * mm,
                    leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    doc.addPageTemplates([PageTemplate(id='label', frames=[frame])])

    story = []
    sp = lambda n=1: Spacer(1, n * mm)

    # ── 1. Ürün adı + nominal miktar ─────────────────────────────────────────
    story.append(_para(product.get('name', ''), styles['product']))
    story.append(sp(0.5))
    # Nominal miktar — CLP Md.17(1)(c): ambalaj hacmi etikette yer almalı
    vol_str = f'{int(volume_l)} L' if volume_l == int(volume_l) else f'{volume_l} L'
    story.append(_para(vol_str, styles['supplier']))
    story.append(sp(1.5))

    # ── 2. Tedarikçi bilgisi ──────────────────────────────────────────────────
    sup_lines = []
    if supplier.get('name'):
        sup_lines.append(supplier['name'])
    if supplier.get('address'):
        sup_lines.append(supplier['address'])
    if supplier.get('phone'):
        sup_lines.append(supplier['phone'])
    if sup_lines:
        for _sl in sup_lines:
            story.append(_para(_sl, styles['supplier']))
        story.append(sp(1.5))

    # ── 3. Piktogramlar ───────────────────────────────────────────────────────
    ghs_codes = get_ghs_codes(h_codes)
    if ghs_codes:
        pic_size = pic_mm * mm
        cells    = []
        for ghs in ghs_codes:
            path = get_icon_path(ghs)
            if path:
                cells.append(Image(str(path), width=pic_size, height=pic_size))
            else:
                cells.append(_para(ghs, styles['normal']))
        # Tek satıra sığdır, yoksa iki satıra böl
        cols_per_row = min(len(cells), max(1, int(inner_w / (pic_size + 2 * mm))))
        rows = [cells[i:i+cols_per_row] for i in range(0, len(cells), cols_per_row)]
        col_w = inner_w / cols_per_row
        pic_tbl = Table(rows, colWidths=[col_w] * cols_per_row)
        pic_tbl.setStyle(TableStyle([
            ('ALIGN',     (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN',    (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING',(0, 0), (-1, -1), 1),
            ('BOTTOMPADDING',(0,0),(-1,-1), 1),
        ]))
        story.append(pic_tbl)
        story.append(sp(1.5))

    # ── 4. Sinyal kelimesi ────────────────────────────────────────────────────
    if signal:
        story.append(_para(signal, styles['signal']))
        story.append(sp(1.5))

    # ── 5. Tehlike ifadeleri (H) ──────────────────────────────────────────────
    h_texts = []
    seen_h  = set()
    for h in h_codes:
        base = h.split()[0]
        if base in seen_h:
            continue
        seen_h.add(base)
        txt = get_h(lang, base)
        if txt and txt != base:
            h_texts.append(f'{base}: {txt}')
    if h_texts:
        story.append(_para('Tehlike İfadeleri:' if lang == 'TR' else 'Hazard Statements:',
                           styles['section']))
        story.append(sp(0.5))
        for t in h_texts:
            story.append(_para(t, styles['h_stmt']))
        story.append(sp(1.5))

    # ── 6. Önlem ifadeleri (P) ────────────────────────────────────────────────
    p_texts = []
    seen_p  = set()
    for p in p_codes:
        if p in seen_p:
            continue
        seen_p.add(p)
        txt = get_p(lang, p)
        if txt and txt != p:
            p_texts.append(f'{p}: {txt}')
    if p_texts:
        story.append(_para('Önlem İfadeleri:' if lang == 'TR' else 'Precautionary Statements:',
                           styles['section']))
        story.append(sp(0.5))
        for t in p_texts:
            story.append(_para(t, styles['p_stmt']))
        story.append(sp(1.5))

    # ── 7. EUH ifadeleri (CLP Ek-II) ─────────────────────────────────────────
    euh_data    = data.get('euh', {})
    euh_details = euh_data.get('details', [])
    euh_codes   = euh_data.get('codes', [])
    euh_texts   = []
    seen_euh    = set()
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
        _euh_lang = 'EN' if lang == 'EN' else 'TR'
        txt = EUH_STMTS.get(_euh_lang, {}).get(code, '')
        if txt:
            euh_texts.append(f'{code}: {txt}')
    if euh_texts:
        story.append(_para('Ek Etiket Unsurları (EUH):' if lang == 'TR' else 'Supplemental Hazard Info (EUH):',
                           styles['section']))
        story.append(sp(0.5))
        for t in euh_texts:
            story.append(_para(t, styles['h_stmt']))
        story.append(sp(1.5))

    # ── 9. Tüketici ürünü — ek zorunluluklar (CLP Madde 35) ──────────────────
    if usage == 'consumer':
        consumer_warns = []
        if lang == 'TR':
            consumer_warns.append('Çocukların erişemeyeceği yerlerde saklayın.')
            consumer_warns.append('Zehirleme şüphesinde: 114 Ulusal Zehir Danışma Merkezi')
        else:
            consumer_warns.append('Keep out of reach of children.')
            consumer_warns.append('In case of poisoning: contact local Poison Centre.')
        for w in consumer_warns:
            story.append(_para(w, styles['warning']))
        story.append(sp(1))

    # ── 10. UFI kodu ──────────────────────────────────────────────────────────
    if ufi:
        story.append(_para(f'UFI: {ufi}', styles['ufi']))
        story.append(sp(1))

    # ── 11. Tehlikeli bileşenler ──────────────────────────────────────────────
    hazardous = [
        c for c in components
        if c.get('hCodes') or c.get('h_codes')
    ]
    if hazardous:
        story.append(_para(
            'İçerik (Tehlikeli Bileşenler):' if lang == 'TR' else 'Contents (Hazardous Ingredients):',
            styles['section']))
        story.append(sp(0.5))
        for c in hazardous:
            name = c.get('name', '')
            cas  = c.get('cas') or c.get('cas_no') or ''
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
            story.append(_para(line, styles['normal']))
        story.append(sp(1))

    doc.build(story)
    return buf.getvalue()
