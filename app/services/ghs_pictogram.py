"""
GHS Piktogram Motoru
====================
UNECE resmi PNG piktogramlarını kullanır.
Resimler: data/ghs_icons/GHS01.png ... GHS09.png

İndirme kaynağı:
  https://unece.org/transport/dangerous-goods/ghs-pictograms
"""

from pathlib import Path
from reportlab.platypus import Flowable, Image
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os as _os

# DejaVu fontlarını kayıt et (Türkçe karakter desteği)
def _register_fonts():
    font_paths = [
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        '/usr/share/fonts/TTF/DejaVuSans.ttf',
        '/usr/share/fonts/dejavu/DejaVuSans.ttf',
    ]
    for p in font_paths:
        if _os.path.exists(p):
            try:
                pdfmetrics.registerFont(TTFont('DejaVuSans', p))
            except Exception:
                pass
            break

_register_fonts()
from reportlab.lib.units import mm

# Piktogram dizini
ICONS_DIR = Path(__file__).parent.parent.parent / 'data' / 'ghs_icons'

# H kodu → GHS eşlemesi
H_TO_GHS = {
    'GHS01': {'H200','H201','H202','H203','H204','H205','H240','H241'},
    'GHS02': {'H224','H225','H226','H228','H242','H250','H251','H252','H260','H261','H222','H223','H229'},
    'GHS03': {'H270','H271','H272'},
    'GHS04': {'H280','H281'},
    'GHS05': {'H290','H314','H318'},
    'GHS06': {'H300','H301','H310','H311','H330','H331'},
    'GHS07': {'H302','H312','H315','H316','H317','H319','H320','H332','H335','H336'},
    'GHS08': {'H304','H334','H340','H341','H350','H351','H360','H361','H362','H370','H371','H372','H373'},
    'GHS09': {'H400','H401','H410','H411','H412','H413'},
}

GHS_LABELS_TR = {
    'GHS01': 'Patlayıcı',    'GHS02': 'Alevlenir',
    'GHS03': 'Oksitleyici',  'GHS04': 'Basınçlı Gaz',
    'GHS05': 'Aşındırıcı',   'GHS06': 'Toksik',
    'GHS07': 'Tahriş Edici', 'GHS08': 'Sağlık Teh.',
    'GHS09': 'Çevre Teh.',
}

GHS_LABELS_EN = {
    'GHS01': 'Explosive',    'GHS02': 'Flammable',
    'GHS03': 'Oxidising',    'GHS04': 'Press.Gas',
    'GHS05': 'Corrosive',    'GHS06': 'Toxic',
    'GHS07': 'Warning',      'GHS08': 'Health Haz.',
    'GHS09': 'Environ.',
}


def get_ghs_codes(h_codes: list) -> list:
    """H kodlarından ilgili GHS piktogram kodlarını döndür.
    SEA Madde 28 öncelik kuralları uygulanır.
    """
    pics = set()
    for ghs, h_set in H_TO_GHS.items():
        if any(h in h_set for h in h_codes):
            pics.add(ghs)

    # ── SEA Madde 28 — Piktogram Öncelik İlkeleri ────────────────────────────
    # (a) GHS01 varsa GHS02 ve GHS03 isteğe bağlı
    if 'GHS01' in pics:
        pics.discard('GHS02')
        pics.discard('GHS03')
    # (b) GHS06 varsa GHS07 kaldırılır
    if 'GHS06' in pics:
        pics.discard('GHS07')
    # (c) GHS05 varsa deri/göz tahrişi için GHS07 kaldırılır
    if 'GHS05' in pics and 'GHS06' not in pics:
        pics.discard('GHS07')
    # (ç) GHS08 solunum hassasiyeti (H334) için geçerliyse GHS07 kaldırılır
    if 'GHS08' in pics and any(h.startswith('H334') for h in h_codes):
        pics.discard('GHS07')
    # (d) GHS02 veya GHS06 varsa GHS04 isteğe bağlı
    if 'GHS02' in pics or 'GHS06' in pics:
        pics.discard('GHS04')

    return sorted(pics)


def get_icon_path(ghs_code: str) -> Path | None:
    """GHS kodu için PNG dosya yolunu döndür."""
    p = ICONS_DIR / f'{ghs_code}.png'
    return p if p.exists() else None


def pictogram_table(h_codes: list, size_mm: float = 15, lang: str = 'TR'):
    """
    H kodlarından piktogram tablosu oluştur (PDF Bölüm 2.2 için).
    PNG dosyaları yoksa placeholder metin kullanır.

    Returns: ReportLab Table veya None
    """
    from reportlab.platypus import Table, TableStyle, Paragraph
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.colors import HexColor, black
    from reportlab.lib import colors

    ghs_list = get_ghs_codes(h_codes)
    if not ghs_list:
        return None

    size = size_mm * mm
    labels = GHS_LABELS_TR if lang == 'TR' else GHS_LABELS_EN

    lbl_style = ParagraphStyle(
        'ghslbl',
        fontName='DejaVuSans',
        fontSize=5.5,
        leading=7,
        alignment=1,  # CENTER
        textColor=HexColor('#333333'),
    )

    cells = []
    for ghs in ghs_list:
        icon_path = get_icon_path(ghs)
        if icon_path:
            img = Image(str(icon_path), width=size, height=size)
            cells.append(img)
        else:
            # PNG yoksa çerçeveli placeholder
            cells.append(
                Paragraph(
                    f"<font size='7' color='#cc0000'><b>{ghs}</b></font>",
                    ParagraphStyle('ph', fontName='DejaVuSans', alignment=1, fontSize=7,
                                   textColor=HexColor('#cc0000'),
                                   borderWidth=1, borderColor=HexColor('#cc0000'),
                                   borderPadding=3)
                )
            )

    label_cells = [Paragraph(labels.get(g, g), lbl_style) for g in ghs_list]

    col_w = size + 4
    tbl = Table(
        [cells, label_cells],
        colWidths=[col_w] * len(ghs_list),
        rowHeights=[size + 2, 10],
    )
    tbl.setStyle(TableStyle([
        ('ALIGN',        (0,0), (-1,-1), 'CENTER'),
        ('VALIGN',       (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING',   (0,0), (-1,-1), 1),
        ('BOTTOMPADDING',(0,0), (-1,-1), 1),
        ('LEFTPADDING',  (0,0), (-1,-1), 1),
        ('RIGHTPADDING', (0,0), (-1,-1), 1),
    ]))
    return tbl


def icons_available() -> bool:
    """PNG dosyaları mevcut mu kontrol et."""
    return any((ICONS_DIR / f'GHS0{i}.png').exists() for i in range(1,10))


if __name__ == '__main__':
    print(f"Icons dir: {ICONS_DIR}")
    print(f"Icons available: {icons_available()}")
    print(f"H226+H315+H411 → {get_ghs_codes(['H226','H315','H411'])}")

    # Test PDF
    from reportlab.platypus import SimpleDocTemplate, Spacer, Paragraph
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.pagesizes import A4
    import io

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=20*mm, rightMargin=20*mm)
    styles = getSampleStyleSheet()
    story = []
    story.append(Paragraph("GHS Piktogramları — KSILOCLEAN PRO-40", styles['h2']))
    story.append(Spacer(1,5))
    tbl = pictogram_table(['H226','H315','H317','H411'], size_mm=18, lang='TR')
    if tbl:
        story.append(tbl)
    doc.build(story)
    with open('/tmp/ghs_png_test.pdf','wb') as f:
        f.write(buf.getvalue())
    print(f"✓ Test PDF: {len(buf.getvalue())//1024} KB")
