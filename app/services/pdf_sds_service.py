"""
SDS PDF Üretim Servisi
======================
KKDİK Ek-2 / EU CLP 2020/878 — 16 Bölüm resmi SDS formatı

Özellikler:
  - 7 dil desteği (TR/EN/DE/PL/RO/BG/HU)
  - A4 format, KKDİK'e uygun layout
  - Her sayfada header/footer (ürün adı, sayfa no, revizyon)
  - Bölüm başlıkları koyu arka plan
  - GHS piktogram unicode
  - Bölüm 3: Konsantrasyon gizleme desteği

Bağımlılıklar:
  reportlab, i18n_sds, sds_sentence_service
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib.colors import (
    HexColor, black, white, Color
)
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, KeepTogether
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from io import BytesIO
from datetime import datetime
from typing import Dict, List, Optional
from app.services.sds_validator import validate_sds

# ─── SAYFA DÜZENİ SABİTLERİ ─────────────────────────────────────────────────
PAGE_W   = 180 * mm   # A4 kullanılabilir genişlik (210 - 15 - 15)
COL_L    = 55  * mm   # Sol etiket sütunu
COL_R    = PAGE_W - COL_L  # Sağ değer sütunu, Any

# ─── FONT KAYDI — Unicode desteği (TR/PL/RO/BG/CZ/HR/LT vs.) ──────────────
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os

def _register_fonts():
    """DejaVu Sans — 12 dil Unicode desteği (TR/PL/RO/BG/CZ/HR vs.)

    Font arama sırası:
    1. Uygulama ile gelen fonts/ klasörü (Render.com için güvenilir)
    2. Linux sistem klasörü (/usr/share/fonts/truetype/dejavu/)
    3. Debian/Ubuntu alternatif yollar
    """
    # Olası font dizinleri — önce yerel, sonra sistem
    _THIS_DIR = os.path.dirname(os.path.abspath(__file__))
    _APP_ROOT  = os.path.dirname(os.path.dirname(_THIS_DIR))  # proje kökü
    candidates = [
        os.path.join(_APP_ROOT, 'fonts'),                        # /app/fonts/
        os.path.join(_THIS_DIR, 'fonts'),                        # app/services/fonts/
        '/usr/share/fonts/truetype/dejavu',                      # Debian/Ubuntu standart
        '/usr/share/fonts/dejavu',                               # bazı dağıtımlar
        '/usr/share/fonts/truetype/ttf-dejavu',                  # eski Ubuntu
        '/usr/local/share/fonts/truetype/dejavu',                # manuel kurulum
    ]

    font_files = {
        'DejaVuSans':          'DejaVuSans.ttf',
        'DejaVuSans-Bold':     'DejaVuSans-Bold.ttf',
        'DejaVuSans-Oblique':  'DejaVuSans-Oblique.ttf',
        'DejaVuSansMono':      'DejaVuSansMono.ttf',
        'DejaVuSansMono-Bold': 'DejaVuSansMono-Bold.ttf',
    }

    registered = 0
    for name, fname in font_files.items():
        if name in pdfmetrics.getRegisteredFontNames():
            registered += 1
            continue
        for base in candidates:
            path = os.path.join(base, fname)
            if os.path.exists(path):
                try:
                    pdfmetrics.registerFont(TTFont(name, path))
                    registered += 1
                    break
                except Exception as e:
                    print(f'[Font] {name} kayıt hatası ({path}): {e}')

    if registered == 0:
        print('[Font] UYARI: DejaVu fontları bulunamadı — Helvetica kullanılacak (Unicode desteği sınırlı)')
    else:
        print(f'[Font] {registered}/{len(font_files)} DejaVu fontu kayıt edildi')

    # Font ailesi tanımla (bold/italic otomatik seçim için)
    from reportlab.pdfbase.pdfmetrics import registerFontFamily
    try:
        registerFontFamily(
            'DejaVuSans',
            normal='DejaVuSans',
            bold='DejaVuSans-Bold',
            italic='DejaVuSans-Oblique',
            boldItalic='DejaVuSans-Bold',
        )
    except Exception:
        pass

_register_fonts()

from app.services.i18n_sds import (
    section_title, sub_title, term, label_term, phys_prop,
    signal_word as sig_word, get_lang, S
)
from app.services.reach_db import get_reg_no, get_ec_no
from app.services.codes_i18n import get_h, get_euh, get_p, get_ppe, get_sentence, translate_hclass, translate_hclass_list
from app.services.ghs_pictogram import get_ghs_codes, pictogram_table
from app.services.transport_adr_service import get_adr_details, auto_detect_un
from app.services.tr_oel_service import get_oel_table, format_oel_row
from app.services.tr_mevzuat_service import get_section15_text, get_disposal_regulation
from app.services.gbf_author_service import format_author_block, validate_certificate
from app.services.sds_sentence_service import (
    generate_section3, generate_section, get_echa_range
)


# ─── RENKLER ─────────────────────────────────────────────────────────────────

C_SECTION_BG    = HexColor('#1a1f2e')   # Bölüm başlık arkaplan
C_SECTION_TEXT  = HexColor('#ffffff')   # Bölüm başlık yazı
C_SUB_BG        = HexColor('#e8ecf0')   # Alt başlık arkaplan
C_SUB_TEXT      = HexColor('#1a1f2e')   # Alt başlık yazı
C_DANGER        = HexColor('#cc0000')
C_WARNING       = HexColor('#ff8c00')
C_BORDER        = HexColor('#cccccc')
C_TABLE_HEADER  = HexColor('#2d3748')
C_TABLE_HDR_TXT = HexColor('#ffffff')
C_TABLE_ALT     = HexColor('#f7f9fc')
C_ACCENT        = HexColor('#003087')   # Koyu mavi — resmi görünüm

# GHS Piktogram metinleri (unicode emoji — PDF'te görüntülenir)
GHS_SYMBOLS = {
    'GHS01': '💥', 'GHS02': '🔥', 'GHS03': '🔆',
    'GHS04': '🔵', 'GHS05': '⚗',  'GHS06': '☠',
    'GHS07': '⚠',  'GHS08': '⚕',  'GHS09': '🌿',
}


# ─── STİLLER ─────────────────────────────────────────────────────────────────

def build_styles(lang: str = 'TR') -> dict:
    """ReportLab paragraf stillerini oluştur"""
    styles = getSampleStyleSheet()

    base = {
        'fontName': 'DejaVuSans',
        'fontSize': 8.5,
        'leading': 12,
        'textColor': black,
    }

    return {
        'section_title': ParagraphStyle(
            'SectionTitle',
            fontName='DejaVuSans-Bold',
            fontSize=9,
            leading=13,
            textColor=C_SECTION_TEXT,
            spaceBefore=8,
            spaceAfter=2,
        ),
        'sub_title': ParagraphStyle(
            'SubTitle',
            fontName='DejaVuSans-Bold',
            fontSize=8.5,
            leading=12,
            textColor=C_SUB_TEXT,
            spaceBefore=6,
            spaceAfter=2,
        ),
        'body': ParagraphStyle(
            'Body',
            fontName='DejaVuSans',
            fontSize=8.5,
            leading=12,
            textColor=black,
            spaceBefore=2,
            spaceAfter=2,
        ),
        'body_bold': ParagraphStyle(
            'BodyBold',
            fontName='DejaVuSans-Bold',
            fontSize=8.5,
            leading=12,
            textColor=black,
        ),
        'small': ParagraphStyle(
            'Small',
            fontName='DejaVuSans',
            fontSize=7.5,
            leading=11,
            textColor=HexColor('#555555'),
        ),
        'danger': ParagraphStyle(
            'Danger',
            fontName='DejaVuSans-Bold',
            fontSize=9,
            leading=13,
            textColor=C_DANGER,
        ),
        'warning': ParagraphStyle(
            'Warning',
            fontName='DejaVuSans-Bold',
            fontSize=9,
            leading=13,
            textColor=C_WARNING,
        ),
        'mono': ParagraphStyle(
            'Mono',
            fontName='DejaVuSansMono',
            fontSize=8,
            leading=11,
            textColor=black,
        ),
        'header': ParagraphStyle(
            'Header',
            fontName='DejaVuSans-Bold',
            fontSize=14,
            leading=18,
            textColor=C_ACCENT,
            spaceAfter=4,
        ),
        'bullet': ParagraphStyle(
            'Bullet',
            fontName='DejaVuSans',
            fontSize=8.5,
            leading=12,
            leftIndent=12,
            bulletIndent=4,
            textColor=black,
        ),
    }



# ─── H KODU TAM METİNLERİ (CLP Annex III) ───────────────────────────────────
H_STMTS = {
    'H200':'Unstable explosive.','H201':'Explosive; mass explosion hazard.',
    'H202':'Explosive; severe projection hazard.','H203':'Explosive; fire, blast or projection hazard.',
    'H204':'Fire or projection hazard.','H220':'Extremely flammable gas.',
    'H221':'Flammable gas.','H222':'Extremely flammable aerosol.',
    'H223':'Flammable aerosol.','H224':'Extremely flammable liquid and vapour.',
    'H225':'Highly flammable liquid and vapour.','H226':'Flammable liquid and vapour.',
    'H228':'Flammable solid.','H240':'Heating may cause an explosion.',
    'H242':'Heating may cause a fire.','H250':'Catches fire spontaneously if exposed to air.',
    'H260':'In contact with water releases flammable gases which may ignite spontaneously.',
    'H261':'In contact with water releases flammable gas.',
    'H270':'May cause or intensify fire; oxidiser.','H271':'May cause fire or explosion; strong oxidiser.',
    'H272':'May intensify fire; oxidiser.','H280':'Contains gas under pressure; may explode if heated.',
    'H290':'May be corrosive to metals.',
    'H300':'Fatal if swallowed.','H301':'Toxic if swallowed.','H302':'Harmful if swallowed.',
    'H304':'May be fatal if swallowed and enters airways.',
    'H310':'Fatal in contact with skin.','H311':'Toxic in contact with skin.',
    'H312':'Harmful in contact with skin.',
    'H314':'Causes severe skin burns and eye damage.',
    'H315':'Causes skin irritation.','H317':'May cause an allergic skin reaction.',
    'H318':'Causes serious eye damage.','H319':'Causes serious eye irritation.',
    'H330':'Fatal if inhaled.','H331':'Toxic if inhaled.','H332':'Harmful if inhaled.',
    'H334':'May cause allergy or asthma symptoms or breathing difficulties if inhaled.',
    'H335':'May cause respiratory irritation.','H336':'May cause drowsiness or dizziness.',
    'H340':'May cause genetic defects.','H341':'Suspected of causing genetic defects.',
    'H350':'May cause cancer.','H351':'Suspected of causing cancer.',
    'H360':'May damage fertility or the unborn child.','H361':'Suspected of damaging fertility or the unborn child.',
    'H370':'Causes damage to organs.','H371':'May cause damage to organs.',
    'H372':'Causes damage to organs through prolonged or repeated exposure.',
    'H373':'May cause damage to organs through prolonged or repeated exposure.',
    'H400':'Very toxic to aquatic life.','H401':'Toxic to aquatic life.',
    'H402':'Harmful to aquatic life.',
    'H410':'Very toxic to aquatic life with long lasting effects.',
    'H411':'Toxic to aquatic life with long lasting effects.',
    'H412':'Harmful to aquatic life with long lasting effects.',
    'H413':'May cause long lasting harmful effects to aquatic life.',
    'H420':'Harms public health and the environment by destroying ozone in the upper atmosphere.',
}


H_STMTS_TR = {
    'H220':'Son derece alevlenir gaz.',
    'H221':'Alevlenir gaz.',
    'H222':'Son derece alevlenir aerosol.',
    'H223':'Alevlenir aerosol.',
    'H224':'Son derece alevlenir sıvı ve buhar.',
    'H225':'Yüksek alevlenir sıvı ve buhar.',
    'H226':'Alevlenir sıvı ve buhar.',
    'H228':'Alevlenir katı.',
    'H240':'Isındığında patlayabilir.',
    'H242':'Isındığında yangına yol açabilir.',
    'H250':'Havaya maruz kaldığında kendiliğinden tutuşabilir.',
    'H260':'Su ile temas halinde kendiliğinden tutuşabilen alevlenir gazlar açığa çıkar.',
    'H261':'Su ile temas halinde alevlenir gaz açığa çıkar.',
    'H270':'Yangına yol açabilir veya şiddetlendirebilir; yükseltgen.',
    'H271':'Yangına veya patlamaya yol açabilir; güçlü yükseltgen.',
    'H272':'Yangını şiddetlendirebilir; yükseltgen.',
    'H280':'Basınç altında gaz içerir; ısındığında patlayabilir.',
    'H290':'Metallere karşı aşındırıcı olabilir.',
    'H300':'Yutulması halinde öldürücüdür.',
    'H301':'Yutulması halinde toksiktir.',
    'H302':'Yutulması halinde zararlıdır.',
    'H304':'Yutulması ve soluk yoluna girmesi halinde öldürücü olabilir.',
    'H310':'Cilt ile teması halinde öldürücüdür.',
    'H311':'Cilt ile teması halinde toksiktir.',
    'H312':'Cilt ile teması halinde zararlıdır.',
    'H314':'Ciddi cilt yanıklarına ve göz hasarına yol açar.',
    'H315':'Cilt tahrişine yol açar.',
    'H317':'Alerjik cilt reaksiyonuna yol açabilir.',
    'H318':'Ciddi göz hasarına yol açar.',
    'H319':'Ciddi göz tahrişine yol açar.',
    'H330':'Solunması halinde öldürücüdür.',
    'H331':'Solunması halinde toksiktir.',
    'H332':'Solunması halinde zararlıdır.',
    'H334':'Solunması halinde alerji veya astım belirtilerine ya da solunum güçlüklerine yol açabilir.',
    'H335':'Solunum yolu tahrişine yol açabilir.',
    'H336':'Uyuşukluğa veya baş dönmesine yol açabilir.',
    'H340':'Genetik hasara yol açabilir.',
    'H341':'Genetik hasara yol açtığından şüphelenilmektedir.',
    'H350':'Kansere yol açabilir.',
    'H351':'Kansere yol açtığından şüphelenilmektedir.',
    'H360':'Doğurganlığa veya doğmamış çocuğa zarar verebilir.',
    'H361':'Doğurganlığa veya doğmamış çocuğa zarar verebileceğinden şüphelenilmektedir.',
    'H370':'Organlara hasar verir.',
    'H371':'Organlara hasar verebilir.',
    'H372':'Uzun süreli veya tekrarlanan maruziyetle organlara hasar verir.',
    'H373':'Uzun süreli veya tekrarlanan maruziyetle organlara hasar verebilir.',
    'H400':'Sucul organizmalar için çok toksiktir.',
    'H401':'Sucul organizmalar için toksiktir.',
    'H402':'Sucul organizmalar için zararlıdır.',
    'H410':'Uzun süre kalıcı etkiyle sucul organizmalar için çok toksiktir.',
    'H411':'Uzun süre kalıcı etkiyle sucul organizmalar için toksiktir.',
    'H412':'Uzun süre kalıcı etkiyle sucul organizmalar için zararlıdır.',
    'H413':'Sucul organizmalar üzerinde uzun süre kalıcı zararlı etkilere yol açabilir.',
    'H420':'Üst atmosferdeki ozonu tahrip ederek halk sağlığına ve çevreye zarar verir.',
}

def get_h_stmt(code: str, lang: str) -> str:
    return get_h(lang, code)

# ─── UN NUMARASI OTOMATİK TESPİTİ (ADR/RID Tablo A) ─────────────────────────
def _auto_un(h_codes: list, state: str = 'liquid') -> dict | None:
    """H kodlarından en kritik UN numarasını tespit et — ADR 2023 Tablo 2.1.3.10
    Öncelik sırası: 1 > 5.2 > 4.2 > 4.3 > 2 > 5.1 > 6.1 > 3+8 > 6.1+8 > 3+6.1 > 3 > 8 > 9
    Bu fonksiyon yalnızca frontend transport verisinin gelmediği fallback durumlar için çalışır.
    state: 'liquid' | 'solid' | 'gas' (fiziksel hal — katı/sıvı ayrımı için)
    """
    h = set(h_codes)

    # ── Sınıf 1: Patlayıcı ───────────────────────────────────────────────────
    if h & {'H200','H201','H202','H203','H204','H205'}:
        return {'un_no':'UN0000','shipping_name':'PATLAYICI MADDE — Uzman değerlendirmesi gerekli',
                'hazard_class':'1','packing_group':'I','auto':True}

    # ── Sınıf 5.2: Organik Peroksit ──────────────────────────────────────────
    if 'H241' in h:
        return {'un_no':'UN3105','shipping_name':'ORGANİK PEROKSİT, TİP D, E veya F, SIVI',
                'hazard_class':'5.2','packing_group':None,
                'note':'Tip belirlenmesi (A-G) gereklidir — uzman laboratuvarı','auto':True}
    if 'H242' in h:
        return {'un_no':'UN3109','shipping_name':'ORGANİK PEROKSİT, TİP F, SIVI',
                'hazard_class':'5.2','packing_group':None,
                'note':'Tip G ise taşımacılık düzenlemesi kapsamı dışındadır','auto':True}

    # ── Sınıf 4.2: Pirofor / Kendiliğinden Isınan ────────────────────────────
    if 'H250' in h:
        return {'un_no':'UN2845','shipping_name':'PİROFOR SIVI, ORGANİK, B.N.O.',
                'hazard_class':'4.2','packing_group':'I','auto':True}
    if 'H251' in h:
        return {'un_no':'UN3088','shipping_name':'KENDİLİĞİNDEN ISINAN KATI, ORGANİK, B.N.O.',
                'hazard_class':'4.2','packing_group':'II','auto':True}
    if 'H252' in h:
        return {'un_no':'UN3190','shipping_name':'KENDİLİĞİNDEN ISINAN KATI, ORGANİK, B.N.O.',
                'hazard_class':'4.2','packing_group':'III','auto':True}

    # ── Sınıf 4.3: Su ile Tepkiyen ───────────────────────────────────────────
    if 'H260' in h:
        return {'un_no':'UN3148','shipping_name':'SU İLE TEPKİYEN SIVI, B.N.O.',
                'hazard_class':'4.3','packing_group':'I','auto':True}
    if 'H261' in h:
        return {'un_no':'UN3148','shipping_name':'SU İLE TEPKİYEN SIVI, B.N.O.',
                'hazard_class':'4.3','packing_group':'II','auto':True}

    # ── Sınıf 2.2(O): Oksitleyici Gaz ───────────────────────────────────────
    if 'H270' in h:
        return {'un_no':'UN3156','shipping_name':'SIKIŞTIRILMIŞ GAZ, OKSİTLEYİCİ, B.N.O.',
                'hazard_class':'2.2','packing_group':None,'auto':True}

    # ── Sınıf 2.1: Yanıcı Gaz ───────────────────────────────────────────────
    if h & {'H220','H221'}:
        return {'un_no':'UN1954','shipping_name':'YANICI GAZ, B.N.O.',
                'hazard_class':'2.1','packing_group':None,
                'note':'Maddeye özgü UN numarası varsa önceliklidir (ör. propan→UN1978)','auto':True}

    # ── Sınıf 5.1: Oksitleyici Sıvı ─────────────────────────────────────────
    if 'H271' in h:
        return {'un_no':'UN2912','shipping_name':'OKSİTLEYİCİ SIVI, B.N.O.',
                'hazard_class':'5.1','packing_group':'I','auto':True}
    if 'H272' in h:
        return {'un_no':'UN3139','shipping_name':'OKSİTLEYİCİ SIVI, B.N.O.',
                'hazard_class':'5.1','packing_group':'II','auto':True}

    # ── Kombinasyon: Korozif + Oksitleyici → UN 3093 ─────────────────────────
    if 'H314' in h and 'H271' in h:
        return {'un_no':'UN3093','shipping_name':'KOROZİF SIVI, OKSİTLEYİCİ, B.N.O.',
                'hazard_class':'8','sub_class':'5.1','packing_group':'I','auto':True}
    if 'H314' in h and 'H272' in h:
        return {'un_no':'UN3093','shipping_name':'KOROZİF SIVI, OKSİTLEYİCİ, B.N.O.',
                'hazard_class':'8','sub_class':'5.1','packing_group':'II','auto':True}

    # ── Kombinasyon: Yanıcı + Korozif → UN 2924 ──────────────────────────────
    if 'H314' in h and 'H224' in h:
        return {'un_no':'UN2924','shipping_name':'YANICI SIVI, KOROZİF, B.N.O.',
                'hazard_class':'3','sub_class':'8','packing_group':'I','auto':True}
    if 'H314' in h and 'H225' in h:
        return {'un_no':'UN2924','shipping_name':'YANICI SIVI, KOROZİF, B.N.O.',
                'hazard_class':'3','sub_class':'8','packing_group':'II','auto':True}
    if 'H314' in h and 'H226' in h:
        return {'un_no':'UN2924','shipping_name':'YANICI SIVI, KOROZİF, B.N.O.',
                'hazard_class':'3','sub_class':'8','packing_group':'III','auto':True}

    # ── Kombinasyon: Toksik + Korozif → UN 2927 ──────────────────────────────
    if 'H314' in h and h & {'H300','H310','H330'}:
        return {'un_no':'UN2927','shipping_name':'ZEHİRLİ SIVI, KOROZİF, ORGANİK, B.N.O.',
                'hazard_class':'6.1','sub_class':'8','packing_group':'I','auto':True}
    if 'H314' in h and h & {'H301','H311','H331'}:
        return {'un_no':'UN2927','shipping_name':'ZEHİRLİ SIVI, KOROZİF, ORGANİK, B.N.O.',
                'hazard_class':'6.1','sub_class':'8','packing_group':'II','auto':True}

    # ── Kombinasyon: Yanıcı + Toksik → UN 1992 ───────────────────────────────
    if h & {'H224','H225'} and h & {'H300','H310','H330'}:
        return {'un_no':'UN1992','shipping_name':'YANICI SIVI, TOKSİK, B.N.O.',
                'hazard_class':'3','sub_class':'6.1','packing_group':'I','auto':True}
    if h & {'H224','H225'} and h & {'H301','H311','H331'}:
        return {'un_no':'UN1992','shipping_name':'YANICI SIVI, TOKSİK, B.N.O.',
                'hazard_class':'3','sub_class':'6.1','packing_group':'II','auto':True}

    # ── Sınıf 6.1: Toksik (tekil) ────────────────────────────────────────────
    if h & {'H300','H310','H330'}:
        return {'un_no':'UN2810','shipping_name':'ZEHİRLİ SIVI, ORGANİK, B.N.O.',
                'hazard_class':'6.1','packing_group':'I',
                'note':'UN2810 organik için; inorganik → UN3287','auto':True}
    if h & {'H301','H311','H331'}:
        return {'un_no':'UN2810','shipping_name':'ZEHİRLİ SIVI, ORGANİK, B.N.O.',
                'hazard_class':'6.1','packing_group':'II',
                'note':'UN2810 organik için; inorganik → UN3287','auto':True}
    if h & {'H302','H312','H332'}:
        return {'un_no':'UN2810','shipping_name':'ZEHİRLİ SIVI, ORGANİK, B.N.O.',
                'hazard_class':'6.1','packing_group':'III',
                'note':'Akut toksisite Kat.4 — ADR kriterini sağlamıyorsa düzenlemeye tabi olmayabilir','auto':True}

    # ── Sınıf 3: Yanıcı Sıvı ─────────────────────────────────────────────────
    if 'H224' in h:
        return {'un_no':'UN1993','shipping_name':'YANICI SIVI, B.N.O.',
                'hazard_class':'3','packing_group':'I','auto':True}
    if 'H225' in h:
        return {'un_no':'UN1993','shipping_name':'YANICI SIVI, B.N.O.',
                'hazard_class':'3','packing_group':'II','auto':True}
    if 'H226' in h:
        return {'un_no':'UN1993','shipping_name':'YANICI SIVI, B.N.O.',
                'hazard_class':'3','packing_group':'III','auto':True}

    # ── Sınıf 4.1: Yanıcı Katı ───────────────────────────────────────────────
    if 'H228' in h:
        return {'un_no':'UN1325','shipping_name':'YANICI KATI, ORGANİK, B.N.O.',
                'hazard_class':'4.1','packing_group':'II','auto':True}

    # ── Sınıf 8: Korozif (tek başına) — hal bazlı ────────────────────────────
    if 'H314' in h:
        if state == 'solid':
            return {'un_no':'UN1759','shipping_name':'KOROZİF KATI, B.N.O.',
                    'hazard_class':'8','packing_group':'II',
                    'note':'Asidik inorganik→UN3260 | Bazik inorganik→UN3262 | Organik→UN1759','auto':True}
        else:
            return {'un_no':'UN1760','shipping_name':'KOROZİF SIVI, B.N.O.',
                    'hazard_class':'8','packing_group':'II',
                    'note':'Asidik inorganik→UN3264 | Bazik inorganik→UN3266 | Organik→UN1760','auto':True}
    # Çevre için tehlikeli (sadece)
    if any(h in h_codes for h in ['H400','H410','H411']):
        return {'un_no':'UN3082','shipping_name':'ÇEVRE İÇİN TEHLİKELİ MADDE, SIVI, B.N.O.',
                'hazard_class':'9','packing_group':'III','auto':True}
    return None


def section_block(title: str, styles: dict) -> list:
    """Koyu arka planlı bölüm başlık bloğu"""
    tbl = Table(
        [[Paragraph(title, styles['section_title'])]],
        colWidths=[PAGE_W],
    )
    tbl.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), C_SECTION_BG),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
    ]))
    return [tbl, Spacer(1, 3)]


def sub_block(title: str, styles: dict) -> list:
    """Açık gri alt başlık bloğu"""
    tbl = Table(
        [[Paragraph(title, styles['sub_title'])]],
        colWidths=[PAGE_W],
    )
    tbl.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), C_SUB_BG),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('LINEBELOW', (0,0), (-1,-1), 0.5, C_BORDER),
    ]))
    return [tbl, Spacer(1, 2)]


def _wrap(val, styles):
    """String değerleri Paragraph'a çevir — Unicode font için zorunlu"""
    if isinstance(val, str):
        return Paragraph(val, styles['body'])
    return val

def data_table(rows: list, col_widths: list, styles: dict,
               header: bool = True) -> Table:
    """Genel veri tablosu — tüm string'ler Paragraph'a çevrilir"""
    # Tüm hücreleri Paragraph'a çevir (Unicode font desteği)
    wrapped = []
    for i, row in enumerate(rows):
        new_row = []
        for j, cell in enumerate(row):
            if isinstance(cell, str):
                s = styles['body_bold'] if (header and i == 0) else styles['body']
                new_row.append(Paragraph(cell, s))
            else:
                new_row.append(cell)
        wrapped.append(new_row)

    tbl = Table(wrapped, colWidths=col_widths)
    ts = [
        ('FONTNAME', (0,0), (-1,-1), 'DejaVuSans'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('LEADING', (0,0), (-1,-1), 11),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('GRID', (0,0), (-1,-1), 0.3, C_BORDER),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]
    if header:
        ts += [
            ('BACKGROUND', (0,0), (-1,0), C_TABLE_HEADER),
            ('TEXTCOLOR', (0,0), (-1,0), C_TABLE_HDR_TXT),
            ('FONTNAME', (0,0), (-1,0), 'DejaVuSans-Bold'),
        ]
    for i in range(1 if header else 0, len(wrapped), 2):
        ts.append(('BACKGROUND', (0,i), (-1,i), C_TABLE_ALT))
    tbl.setStyle(TableStyle(ts))
    return tbl


def bullet_list(items: list, styles: dict) -> list:
    """Madde listesi"""
    result = []
    for item in items:
        if item:
            result.append(Paragraph(f"• {item}", styles['bullet']))
    return result


def na_text(lang: str, styles: dict) -> Paragraph:
    return Paragraph(term(lang, 'not_available'), styles['small'])


# ─── ANA PDF OLUŞTURMA ────────────────────────────────────────────────────────

def generate_sds_pdf(sds_data: Dict, lang: str = 'TR') -> bytes:
    """
    SDS PDF oluştur.

    Args:
        sds_data: {
          'product': {'name', 'code', 'form', 'usage'},
          'supplier': {'name', 'address', 'phone', 'email'},
          'clp': calculate_clp() çıktısı,
          'euh': check_euh() çıktısı,
          'physical': calcPhysHazards() çıktısı,
          'stot': calcStotRe() çıktısı,
          'eco': calculate_ecological() çıktısı,
          'p_codes': assign_p_codes() çıktısı,
          'components': bileşen listesi,
          'disclosure_map': {cas: 'show'|'range'|'hide'},
          'phys_props': {flash_point, boiling_point, ...},
          'revision': {'date', 'no', 'version'},
        }
        lang: 'TR' | 'EN' | 'DE' | 'PL' | 'RO' | 'BG' | 'HU'

    Returns:
        bytes — PDF içeriği
    """
    buf = BytesIO()
    lang = lang.upper()
    L = get_lang(lang)  # Dil verisi
    styles = build_styles(lang)

    # Ürün bilgileri
    product = sds_data.get('product', {})
    supplier = sds_data.get('supplier', {})
    clp = sds_data.get('clp', {})
    euh = sds_data.get('euh', {})
    components = sds_data.get('components', [])

    # ── Cross-section validation ──────────────────────────────────────────────
    _validation_issues = validate_sds(
        sds_data   = sds_data,
        h_codes    = clp.get('h_codes', []),
        phys_props = sds_data.get('phys_props', {}),
        components = components,
    )
    disclosure = sds_data.get('disclosure_map', {})
    phys = sds_data.get('phys_props', {})
    rev = sds_data.get('revision', {})
    p_data = sds_data.get('p_codes', {})
    eco = sds_data.get('eco', {})

    # US_EN — OSHA HazCom format uyarlaması
    is_us = lang == 'US_EN'
    product_name = product.get('name', 'Product Name' if is_us else 'Ürün Adı')
    rev_date = rev.get('date', datetime.now().strftime(L.get('date_format', '%d.%m.%Y')))
    rev_no = rev.get('no', '1')
    version = rev.get('version', '1.0')

    # Header/Footer için callback fonksiyonları
    header_text = product_name
    footer_text = f"Rev.{rev_no} | {rev_date}"

    def _draw_page(canvas, doc_obj):
        canvas.saveState()
        w, h = A4
        # Header
        canvas.setFont('DejaVuSans-Bold', 7)
        canvas.setFillColor(HexColor('#64748b'))
        canvas.drawString(15*mm, h - 12*mm, header_text)
        canvas.drawRightString(w - 15*mm, h - 12*mm, f"SDS | {footer_text}")
        canvas.setStrokeColor(HexColor('#e2e8f0'))
        canvas.setLineWidth(0.3)
        canvas.line(15*mm, h - 14*mm, w - 15*mm, h - 14*mm)
        # Footer
        canvas.line(15*mm, 14*mm, w - 15*mm, 14*mm)
        canvas.setFont('DejaVuSans', 6.5)
        footer_lbl = 'Bu GBF KKDİK Ek-2 formatına uygundur.' if lang=='TR' else 'This SDS complies with CLP/REACH format.'
        canvas.drawString(15*mm, 10*mm, footer_lbl)
        canvas.drawRightString(w - 15*mm, 10*mm, f"Sayfa {canvas.getPageNumber()}" if lang=='TR' else f"Page {canvas.getPageNumber()}")
        canvas.restoreState()

    # Document
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=15*mm, rightMargin=15*mm,
        topMargin=20*mm, bottomMargin=18*mm,
        title=f"GBF — {product_name}",
        author='HazardDesk',
        subject=f"Safety Data Sheet | {lang}",
    )

    story = []

    # ── BAŞLIK SAYFASI ───────────────────────────────────────────────────────
    # Üst başlık
    story.append(Paragraph(
        {
            'TR':'GÜVENLİK BİLGİ FORMU','EN':'SAFETY DATA SHEET',
            'DE':'SICHERHEITSDATENBLATT','PL':'KARTA CHARAKTERYSTYKI',
            'RO':'FIȘĂ CU DATE DE SECURITATE','BG':'ИНФОРМАЦИОНЕН ЛИСТ ЗА БЕЗОПАСНОСТ',
            'HU':'BIZTONSÁGI ADATLAP','CZ':'BEZPEČNOSTNÍ LIST',
            'SK':'KARTA BEZPEČNOSTNÝCH ÚDAJOV','HR':'SIGURNOSNO-TEHNIČKI LIST',
            'LT':'SAUGOS DUOMENŲ LAPAS','US_EN':'SAFETY DATA SHEET (OSHA HazCom 2012)',
        }.get(lang,'SAFETY DATA SHEET'),
        styles['header']
    ))

    # Ürün bilgi tablosu
    story.append(data_table([
        [term(lang,'product_name'), Paragraph(f"<b>{product_name.upper()}</b>", styles['body'])],
        [term(lang,'product_code'), product.get('code','—')],
        [term(lang,'revision_date'), rev_date],
        ['Version', version],
        [term(lang,'regulation'), L.get('regulation','')],
    ], [45*mm, 135*mm], styles, header=False))
    story.append(Spacer(1, 8))

    # H kodları — etiket için (dominance uygulanmış) ve SDS 2.1 için (tam sınıflandırma)
    h_codes     = clp.get('h_codes', [])             # Bölüm 2.2 etiket — dominant H-kodları
    all_h_codes = clp.get('all_h_codes') or h_codes  # Bölüm 2.1 sınıflandırma — tüm H-kodları
    if h_codes:
        hc_str = '  '.join(h_codes)
        story.append(Paragraph(
            f"<b>{S(lang,'hazard_codes_label')}:</b> {hc_str}",
            styles['body']
        ))

    story.append(HRFlowable(width='100%', thickness=1, color=C_ACCENT,
                            spaceAfter=6, spaceBefore=6))

    # ─────────────────────────────────────────────────────────────────────────
    # BÖLÜM 1 — Tanımlama
    # ─────────────────────────────────────────────────────────────────────────
    story += section_block(section_title(lang, 1), styles)
    story += sub_block(f"1.1 {sub_title(lang,'1.1')}", styles)

    story.append(data_table([
        [term(lang,'product_name'), Paragraph(f"<b>{product_name.upper()}</b>", styles['body'])],
        [term(lang,'product_code'), product.get('code','—')],
    ], [55*mm, 125*mm], styles, header=False))
    story.append(Spacer(1, 3))

    story += sub_block(f"1.2 {sub_title(lang,'1.2')}", styles)
    usage_desc = product.get('usage_desc',
        S(lang,'usage_default'))
    story.append(Paragraph(usage_desc or S(lang,'usage_default'), styles['body']))
    story.append(Spacer(1, 3))

    story += sub_block(f"1.3 {sub_title(lang,'1.3')}", styles)
    def _up(v): return str(v).upper() if v and v != '—' else '—'
    story.append(data_table([
        [term(lang,'manufacturer'), _up(supplier.get('name','—'))],
        [term(lang,'address'),      _up(supplier.get('address','—'))],
        [term(lang,'phone'),        supplier.get('phone','—')],
        [term(lang,'email'),        supplier.get('email','—')],
    ], [45*mm, 135*mm], styles, header=False))
    story.append(Spacer(1, 3))

    story += sub_block(f"1.4 {sub_title(lang,'1.4')}", styles)
    # UZEM her zaman gösterilir — zorunlu (KKDİK Ek-2)
    _uzem = 'UZEM — Ulusal Zehir Danışma Merkezi: <b>114</b> (T.C. Sağlık Bakanlığı, 7/24)' if lang == 'TR' \
            else 'National Poison Control Center: <b>114</b> (UZEM, Ministry of Health, 24/7)'
    story.append(Paragraph(_uzem, styles['body']))
    # Tedarikçi acil hattı — varsa ayrı satırda
    supplier_tel = supplier.get('emergency_tel', '').strip()
    if supplier_tel:
        story.append(Paragraph(f"Tel: {supplier_tel}", styles['body']))

    # ─────────────────────────────────────────────────────────────────────────
    # BÖLÜM 2 — Zararlılık
    # ─────────────────────────────────────────────────────────────────────────
    story += section_block(section_title(lang, 2), styles)
    story += sub_block(f"2.1 {sub_title(lang,'2.1')}", styles)

    # Sınıflandırma — signal_word: CLP Annex I DANGER_H ile doğrula
    # H221 (Flam.Gas 2) = Warning → kaldırıldı
    # H251 (Self-heat.1) = Danger → eklendi
    # H232 (Pyrophoric gas) = Danger → eklendi
    _DANGER_H = {
        'H200','H201','H202','H203','H204','H205',
        'H220','H222','H224','H225','H228',
        'H232',
        'H240','H241','H250','H251','H260','H270','H271',
        'H300','H301','H304','H310','H311',
        'H314','H318','H330','H331',
        'H334','H340','H350','H360','H370','H372',
    }
    _hc_set = {h.split()[0] for h in h_codes}
    signal = 'Danger' if (_hc_set & _DANGER_H) else 'Warning'
    sig_color = C_DANGER if signal=='Danger' else (C_WARNING if signal=='Warning' else black)

    clf_rows = []
    seen_clf = set()
    for entry in clp.get('passed', []):
        hc = (entry.get('h_code','') or '').replace('*','').strip()[:4]
        if hc in seen_clf:
            continue
        seen_clf.add(hc)
        reason = entry.get('reason','')
        conc_info = reason or entry.get('cutoff_used','—')
        clf_rows.append([
            translate_hclass(entry.get('h_class',''), lang),
            entry.get('h_code',''),
            conc_info,
        ])
    # passed boş veya eksikse all_h_codes'dan fallback satırlar ekle
    # all_h_codes: domine edilenler dahil tüm sınıflandırmalar (CLP Ek I § 1.2.2)
    for hc_raw in all_h_codes:
        hc = (hc_raw or '').replace('*','').strip()[:4]
        if not hc or hc in seen_clf:
            continue
        seen_clf.add(hc)
        clf_rows.append([translate_hclass('', lang), hc_raw, '—'])

    if clf_rows:
        reason_lbl = 'Kesme Değeri / Gerekçe' if lang=='TR' else 'Cut-off / Reason'
        h_code_lbl = 'H Kodu' if lang=='TR' else 'H Code'
        story.append(data_table(
            [[term(lang,'classification'), h_code_lbl, reason_lbl]] + clf_rows,
            [90*mm, 30*mm, 60*mm], styles
        ))
        if lang == 'TR':
            story.append(Spacer(1, 4))
            story.append(Paragraph(
                '<i>H-kodları, 11 Aralık 2013 tarihli ve 28848 sayılı Resmî Gazete\'de yayımlanan '
                'Maddelerin ve Karışımların Sınıflandırılması, Etiketlenmesi ve Ambalajlanması '
                'Hakkında Yönetmelik (SEA) esaslarına göre belirlenmiştir.</i>',
                styles['small']
            ))
    else:
        story.append(Paragraph(term(lang,'not_classified'), styles['body']))
    story.append(Spacer(1, 3))

    story += sub_block(f"2.2 {sub_title(lang,'2.2')}", styles)

    # GHS Piktogramları (UNECE resmi PNG)
    ghs_tbl = pictogram_table(h_codes, size_mm=16, lang=lang)
    if ghs_tbl:
        story.append(ghs_tbl)
        story.append(Spacer(1, 4))

    # Sinyal kelimesi
    story.append(data_table([
        [label_term(lang,'signal_word'),
         Paragraph(f"<b><font color='{'red' if signal=='Danger' else 'orange'}'>"
                  f"{sig_word(lang, signal)}</font></b>", styles['body'])],
    ], [55*mm, 125*mm], styles, header=False))
    story.append(Spacer(1, 3))

    # H ifadeleri
    h_stmts = clp.get('h_codes',[])  # EUH ayrı bölümde gösterilecek
    if h_stmts:
        story.append(Paragraph(f"<b>{label_term(lang,'hazard_stmts')}:</b>",
                               styles['body_bold']))
        for hc in h_stmts:
            if hc.startswith('EUH'):
                stmt = EUH_STMTS_TR.get(hc,'') if lang=='TR' else ''
                if not stmt:
                    # euh_details'dan bul
                    stmt = next((d.get('text','') for d in euh.get('euh_details',[]) if d.get('code')==hc), hc)
            else:
                stmt = get_h_stmt(hc, lang)
            story.append(Paragraph(f'• <b>{hc}:</b> {stmt}', styles['bullet']))

    # EUH
    euh_details = euh.get('euh_details', [])
    if euh_details:
        story.append(Paragraph(f"<b>{label_term(lang,'supp_labels')}:</b>",
                               styles['body_bold']))
        for d in euh_details:
            code = d.get('code','')
            # euh_service'den gelen tam metin öncelikli (EUH208 madde adı içeriyor)
            # lang='TR' → text_tr kullan (Türkçe madde adı içerir)
            if lang == 'TR':
                source_text = (d.get('text_tr') or d.get('text', '')).strip()
            else:
                source_text = d.get('text', '').strip()
            if source_text:
                text = source_text
            else:
                # codes_i18n'den al — EUH208 için source_name'i ilet
                if lang == 'TR':
                    substance = d.get('source_name_tr') or d.get('source_name', '')
                else:
                    substance = d.get('source_name', '')
                text = get_euh(lang, code, substance)
            story.append(Paragraph(f"• <b>{code}:</b> {text}", styles['bullet']))

    # P ifadeleri (etiket - maks 6) — tehlike şiddetine göre sıralı
    label_p = p_data.get('label', {})
    if label_p.get('selected'):
        story.append(Spacer(1, 3))
        story.append(Paragraph(f"<b>{label_term(lang,'precaut_stmts')}:</b>",
                               styles['body_bold']))
        from app.services.p_code_service import P_COMBOS, P_TEXTS, P_LABEL_PRIORITY
        # Etiket kodları şiddet sırasına göre göster (en kritik önce)
        label_codes_sorted = sorted(
            label_p['selected'],
            key=lambda p: P_LABEL_PRIORITY.get(p, 5),
            reverse=True
        )
        for code in label_codes_sorted:
            txt = get_p(lang, code) or P_COMBOS.get(code) or P_TEXTS.get(code, code)
            story.append(Paragraph(f"• <b>{code}:</b> {txt}", styles['bullet']))
        mandatory = label_p.get('mandatory', [])
        if mandatory:
            for m in mandatory:
                txt = get_p(lang, m) or P_TEXTS.get(m, m)
                story.append(Paragraph(f"• <b>{m}:</b> {txt}", styles['bullet']))

    story += sub_block(f"2.3 {sub_title(lang,'2.3')}", styles)
    # PBT/vPvB
    story.append(Paragraph('PBT/vPvB: ' + term(lang,'pbt_not'), styles['small']))
    # Endokrin bozucu
    eco_data = sds_data.get('eco', {})
    # EcoOutput objesi veya dict olabilir
    if hasattr(eco_data, 'endocrine_disruptors'):
        ed_list = eco_data.endocrine_disruptors or []
        _sds12_for_b23 = eco_data.sds_section_12 or {}
    else:
        ed_list = eco_data.get('endocrine_disruptors', [])
        _sds12_for_b23 = eco_data.get('sds_section_12', {})
    ed_note = _sds12_for_b23.get('12.6', '') if isinstance(_sds12_for_b23, dict) else ''
    # ECHA sistem notunu temizle
    if 'ECHA SVHC' in ed_note or 'kontrol edin' in ed_note:
        ed_text = 'Endokrin bozucu özellik tespit edilmemiştir.' if lang=='TR' else 'No endocrine disrupting properties identified.'
    else:
        ed_text = ed_note if ed_note else ('Tespit edilmemiştir.' if lang=='TR' else 'Not identified.')
    story.append(Paragraph(
        f"Endokrin Bozucu Özellikler: {ed_text}", styles['small']
    ))

    # ─────────────────────────────────────────────────────────────────────────
    # BÖLÜM 3 — Bileşimler
    # ─────────────────────────────────────────────────────────────────────────
    story += section_block(section_title(lang, 3), styles)
    story += sub_block(f"3.2 {sub_title(lang,'3.2')}", styles)

    sec3_rows = generate_section3(components, disclosure, lang=lang)
    if sec3_rows:
        # B3.2 Tablo — 4 sütun, A4'e sığacak şekilde
        # CAS No | Madde Adı | Konst. | Sınıflandırma
        # EC No / REACH Kayıt No — CAS hücresinin altına küçük font

        cas_hdr  = 'CAS No\nEC / REACH'
        name_hdr = S(lang,'ingredient_label')
        conc_hdr = term(lang,'concentration')
        clf_hdr  = term(lang,'classification')

        tbl_data = [[ cas_hdr, name_hdr, conc_hdr, clf_hdr ]]

        # B3.2 — M faktör haritası (aquatic olan tüm bileşenler)
        m_factor_map = {}
        eco_aquatic = eco.get('aquatic') if isinstance(eco, dict) else getattr(eco,'aquatic',None)
        if eco_aquatic:
            details = getattr(eco_aquatic,'component_details',None) or []
            for d in (details or []):
                if d.get('h_class',''):  # aquatic sınıfı olan her bileşen
                    m_factor_map[d['cas']] = {
                        'acute':   d.get('m_acute', 1),
                        'chronic': d.get('m_chronic', 1),
                        'h_class': d.get('h_class', ''),
                    }

        missing_reach = []
        for r in sec3_rows:
            cas = r['cas']
            comp_obj = next((comp for comp in components if comp.get('cas_no','')==cas), {})
            ec  = comp_obj.get('ec_no','') or get_ec_no(cas)
            reg = comp_obj.get('reach_no','') or get_reg_no(cas)
            if not reg:
                missing_reach.append(cas)
                reg = '—'
            elif reg == 'exempt':
                reg = 'Muaf' if lang=='TR' else 'Exempt'
            elif reg == 'polymer':
                reg = 'Polimer/muaf' if lang=='TR' else 'Polymer/exempt'

            # CAS + EC + REACH tek hücrede, küçük fontla
            cas_cell = Paragraph(
                f"<b>{cas}</b><br/>"
                f"<font size='6'>{ec or '—'}<br/>{reg or '—'}</font>",
                styles['small']
            )
            # Her sınıflandırma kendi satırında — uzun metinde kelime kırılmasını önle
            _clf_str = translate_hclass_list(r.get('hazards',''), lang) or term(lang,'not_classified')
            _clf_para = Paragraph(_clf_str.replace('; ', '<br/>'), styles['body'])
            tbl_data.append([
                cas_cell,
                r['name'],
                r['concentration'],
                _clf_para,
            ])

        # Toplam 175mm: CAS(35) + Ad(60) + Konst.(18) + Sınıf(62)
        story.append(data_table(tbl_data,
            [35*mm, 60*mm, 18*mm, 62*mm], styles))
        # REACH eksik not
        if missing_reach:
            story.append(Paragraph(
                f"* REACH kayıt numarası bulunamayan maddeler için tedarikçiye başvurun: {', '.join(missing_reach)}" if lang=='TR'
                else f"* REACH registration numbers not found for: {', '.join(missing_reach)}. Obtain from supplier.",
                styles['small']
            ))

        # Gizleme notları
        for r in sec3_rows:
            if r.get('note'):
                story.append(Paragraph(f"* {r['note']}", styles['small']))
    story.append(Spacer(1, 3))

    # ─────────────────────────────────────────────────────────────────────────
    # BÖLÜM 4 — İlk Yardım
    # ─────────────────────────────────────────────────────────────────────────
    story += section_block(section_title(lang, 4), styles)
    story += sub_block(f"4.1 {sub_title(lang,'4.1')}", styles)

    sec4 = generate_section(4, h_codes)
    story += bullet_list(sec4['bullets'], styles) or [na_text(lang, styles)]
    story.append(Spacer(1, 3))

    story += sub_block(f"4.2 {sub_title(lang,'4.2')}", styles)
    story.append(Paragraph(
        S(lang,'symptoms_general'), styles['body']
    ))

    story += sub_block(f"4.3 {sub_title(lang,'4.3')}", styles)
    story.append(Paragraph(
        term(lang,'poison_center'), styles['body']
    ))

    # ─────────────────────────────────────────────────────────────────────────
    # BÖLÜM 5 — Yangın
    # ─────────────────────────────────────────────────────────────────────────
    story += section_block(section_title(lang, 5), styles)
    story += sub_block(f"5.1 {sub_title(lang,'5.1')}", styles)

    sec5 = generate_section(5, h_codes)
    extinguisher = sec5.get('extinguisher') or term(lang,'not_available')
    story.append(Paragraph(extinguisher, styles['body']))

    story += sub_block(f"5.2 {sub_title(lang,'5.2')}", styles)
    story += bullet_list(sec5['bullets'], styles) or [na_text(lang, styles)]

    story += sub_block(f"5.3 {sub_title(lang,'5.3')}", styles)
    story.append(Paragraph(
        S(lang,'firefighter_ppe'),
        styles['body']
    ))

    story.append(PageBreak())

    # ─────────────────────────────────────────────────────────────────────────
    # BÖLÜM 6 — Kaza
    # ─────────────────────────────────────────────────────────────────────────
    story += section_block(section_title(lang, 6), styles)
    story += sub_block(f"6.1 {sub_title(lang,'6.1')}", styles)
    story.append(Paragraph(
        S(lang,'personal_precautions'),
        styles['body']
    ))

    story += sub_block(f"6.2 {sub_title(lang,'6.2')}", styles)
    sec6 = generate_section(6, h_codes)
    story += bullet_list(sec6['bullets'], styles) or [na_text(lang, styles)]

    story += sub_block(f"6.3 {sub_title(lang,'6.3')}", styles)
    story.append(Paragraph(
        S(lang,'spill_instructions'),
        styles['body']
    ))

    story += sub_block(f"6.4 {sub_title(lang,'6.4')}", styles)
    story.append(Paragraph(
        f"{term(lang,'see_section')} 8 ({'KKE' if lang=="TR" else 'PPE'}), 13 ({term(lang,'disposal')})" if True else '',
        styles['small']
    ))

    # ─────────────────────────────────────────────────────────────────────────
    # BÖLÜM 7 — Elleçleme ve Depolama
    # ─────────────────────────────────────────────────────────────────────────
    story += section_block(section_title(lang, 7), styles)
    story += sub_block(f"7.1 {sub_title(lang,'7.1')}", styles)

    sec7 = generate_section(7, h_codes)
    story += bullet_list(sec7['bullets'], styles) or [na_text(lang, styles)]

    story += sub_block(f"7.2 {sub_title(lang,'7.2')}", styles)
    story.append(Paragraph(
        get_sentence(lang,'storage_default') or S(lang,'storage_default'),
        styles['body']
    ))

    story += sub_block(f"7.3 {sub_title(lang,'7.3')}", styles)
    specific_use = sds_data.get('specific_use', '')
    if specific_use:
        story.append(Paragraph(specific_use, styles['body']))
    else:
        story.append(Paragraph(
            'Belirli bir son kullanım önerilmemektedir. Müşteri uygulamalarına yönelik genişletilmiş maruziyet senaryosu için tedarikçiye başvurunuz.'
            if lang == 'TR' else
            'No specific end use is recommended. Contact the supplier for extended exposure scenarios tailored to customer applications.',
            styles['body']
        ))

    # ─────────────────────────────────────────────────────────────────────────
    # BÖLÜM 8 — Maruziyet / KKE
    # ─────────────────────────────────────────────────────────────────────────
    story += section_block(section_title(lang, 8), styles)
    story += sub_block(f"8.1 {sub_title(lang,'8.1')}", styles)
    oel_rows = get_oel_table(components)
    if oel_rows:
        oel_header = 'CAS No / Madde' if lang=='TR' else 'CAS No / Substance'
        tbl_data = [[
            'CAS No',
            'Madde Adı' if lang=='TR' else 'Substance',
            'TWA (8h)',
            'STEL (15dk)' if lang=='TR' else 'STEL (15min)',
            'Not' if lang=='TR' else 'Note',
        ]]
        for row in oel_rows:
            tbl_data.append(format_oel_row(row, lang))
        story.append(data_table(tbl_data, [22*mm, 45*mm, 35*mm, 35*mm, 25*mm], styles))
        story.append(Paragraph(
            'Kaynak: 12.08.2013 tarihli ve 28733 sayılı Kimyasal Maddelerle Çalışmalarda Sağlık ve Güvenlik Önlemleri Hakkında Yönetmelik Ek-1' if lang=='TR'
            else 'Source: Turkish Chemical Agents Regulation (OG No. 28733, 12.08.2013) Annex-1',
            styles['small']
        ))
    else:
        story.append(Paragraph(S(lang,'oel_reference'), styles['body']))

    story += sub_block(f"8.2 {sub_title(lang,'8.2')}", styles)
    sec8 = generate_section(8, h_codes)
    ppe = sec8.get('ppe', {})
    ppe_map = {
        'gloves': term(lang,'ppe_gloves'),
        'eyes':   term(lang,'ppe_eyes'),
        'resp':   term(lang,'ppe_resp'),
        'body':   term(lang,'ppe_body'),
    }
    ppe_rows = []
    for key, label in ppe_map.items():
        val = ppe.get(key, term(lang,'not_applicable'))
        ppe_rows.append([label, val])

    story.append(data_table(ppe_rows, [50*mm, 130*mm], styles, header=False))

    story.append(PageBreak())

    # ─────────────────────────────────────────────────────────────────────────
    # BÖLÜM 9 — Fiziksel Özellikler
    # ─────────────────────────────────────────────────────────────────────────
    story += section_block(section_title(lang, 9), styles)
    story += sub_block(f"9.1 {sub_title(lang,'9.1')}", styles)

    na = term(lang,'not_available')
    
    # PCN zorunlu alanlar kontrolü
    pcn_required = ['ph','solubility','density','flash_point']
    pcn_missing = [k for k in pcn_required if not phys.get(k)]
    if pcn_missing and lang == 'TR':
        missing_labels = {
            'ph': 'pH', 'solubility': 'Çözünürlük',
            'density': 'Yoğunluk', 'flash_point': 'Parlama Noktası'
        }
        warn_text = 'PCN bildirimi için zorunlu eksik alanlar: ' +                     ', '.join(missing_labels.get(k,k) for k in pcn_missing)
        story.append(Paragraph(
            f"<font color='red'>⚠ {warn_text}</font>",
            styles['small']
        ))

    def _pv(key, unit=''):
        v = phys.get(key)
        if v is None or v == '': return na
        return f"{v} {unit}".strip() if unit else str(v)

    _mp_lbl  = 'Donma/Erime Noktası' if lang=='TR' else 'Melting/Freezing Point'
    _rd_lbl  = 'Bağıl Yoğunluk (su=1)' if lang=='TR' else 'Relative Density (water=1)'
    _vd_lbl  = 'Buhar Yoğunluğu (hava=1)' if lang=='TR' else 'Vapor Density (air=1)'
    _ai_lbl  = 'Kendiliğinden Tutuşma' if lang=='TR' else 'Auto-ignition Temp.'
    _ex_lbl  = 'Patlama Sınırları (LEL/UEL)' if lang=='TR' else 'Explosive Limits (LEL/UEL)'

    _ex_val = na
    if phys.get('lel') or phys.get('uel'):
        _ex_val = f"%{phys.get('lel','?')} – %{phys.get('uel','?')}"

    _vp_val = phys.get('vapor_pressure') or               (f"{phys.get('vapor_pressure_num')} hPa" if phys.get('vapor_pressure_num') else na)

    all_phys_rows = [
        [phys_prop(lang,'appearance'),
         phys.get(f'appearance_{lang}') or phys.get('appearance') or na],
        [phys_prop(lang,'color'),         phys.get('color') or na],
        [phys_prop(lang,'odor'),          phys.get('odor') or na],
        [phys_prop(lang,'ph'),            _pv('ph')],
        [phys_prop(lang,'flash_point'),   _pv('flash_point','°C')],
        [phys_prop(lang,'boiling_point'), _pv('boiling_point','°C')],
        [_mp_lbl,                         _pv('melting_point','°C')],
        [phys_prop(lang,'density'),       _pv('density','g/cm³')],
        [_rd_lbl,                         _pv('rel_density')],
        [phys_prop(lang,'viscosity'),     _pv('viscosity','cSt @40°C')],
        [phys_prop(lang,'solubility'),    phys.get('solubility') or na],
        [phys_prop(lang,'vapor_pressure'),_vp_val],
        [_vd_lbl,                         _pv('vapor_density')],
        [_ai_lbl,                         _pv('auto_ignition','°C')],
        [_ex_lbl,                         _ex_val],
    ]
    # Koku eşiği
    _ot_lbl = 'Koku Eşiği' if lang=='TR' else 'Odour Threshold'
    _ot_val = phys.get('odour_threshold') or na

    # Ayrışma sıcaklığı
    _dc_lbl = 'Ayrışma Sıcaklığı' if lang=='TR' else 'Decomposition Temp.'
    _dc_val = _pv('decomposition_temp','°C')

    # Patlayıcı / oksitleyici
    _prop_lbl = 'Patlayıcı/Oksitleyici Özellikler' if lang=='TR' else 'Explosive/Oxidising Properties'
    _props = []
    if phys.get('is_explosive'):
        _props.append('Patlayıcı özellik' if lang=='TR' else 'Explosive')
    if phys.get('is_oxidising'):
        _props.append('Oksitleyici özellik' if lang=='TR' else 'Oxidising')
    if phys.get('is_flammable'):
        _props.append('Yanıcı (katı/gaz)' if lang=='TR' else 'Flammable solid/gas')
    _prop_val = '; '.join(_props) if _props else ('Yok' if lang=='TR' else 'None')

    all_phys_rows += [
        [_ot_lbl,   _ot_val],
        [_dc_lbl,   _dc_val],
        [_prop_lbl, _prop_val],
    ]

    # Opsiyonel satırları — sadece değer varsa göster
    _optional = {_mp_lbl, _rd_lbl, _vd_lbl, _ai_lbl, _ex_lbl, _ot_lbl, _dc_lbl}
    phys_rows = [r for r in all_phys_rows if r[1] != na or r[0] not in _optional]

    story.append(data_table(phys_rows, [75*mm, 105*mm], styles, header=False))

    # ─────────────────────────────────────────────────────────────────────────
    # BÖLÜM 10 — Kararlılık
    # ─────────────────────────────────────────────────────────────────────────
    story += section_block(section_title(lang, 10), styles)

    # ── Bileşen CAS setleri (Bölüm 10 dinamik mantığı için) ──────────────────
    comp_cas_set = {
        comp.get('cas_no', comp.get('cas',''))
        for comp in components
    }
    # Alkol CAS'ları
    ALCOHOL_CAS = {'64-17-5','67-63-0','71-36-3','71-23-8','78-83-1','67-56-1',
                   '71-41-0','75-65-0','100-51-6'}
    # Klorlu bileşik CAS'ları
    CHLORINATED_CAS = {'75-09-2','67-66-3','71-55-6','79-01-6','127-18-4',
                       '7647-01-0','75-00-3','79-00-5','106-93-4'}
    has_alcohol     = bool(comp_cas_set & ALCOHOL_CAS)
    has_chlorinated = bool(comp_cas_set & CHLORINATED_CAS)
    is_flammable    = any(h in h_codes for h in ['H224','H225','H226','H228'])
    is_acid         = any(h in h_codes for h in ['H290','H314']) and any(
                        comp.get('cas_no', comp.get('cas','')) in
                        {'7664-93-9','7647-01-0','7697-37-2','7664-38-2','64-19-7'}
                        for comp in components)
    is_base         = 'H314' in h_codes and any(
                        comp.get('cas_no', comp.get('cas','')) in
                        {'1310-73-2','1310-58-3','1336-21-6','7664-41-7'}
                        for comp in components)

    # ── 10.4 Kaçınılması gereken koşullar — dinamik ──────────────────────────
    avoid_parts = []
    if is_flammable:
        avoid_parts.append(
            'Açık alev, ısı kaynakları, kıvılcım ve statik elektrik' if lang=='TR'
            else 'Open flames, heat sources, sparks and static electricity'
        )
        avoid_parts.append(
            'Yüksek sıcaklıklar ve doğrudan güneş ışığı' if lang=='TR'
            else 'High temperatures and direct sunlight'
        )
    if any(h in h_codes for h in ['H270','H271','H272']):
        avoid_parts.append('Yanıcı maddeler' if lang=='TR' else 'Combustible materials')
    if any(h in h_codes for h in ['H260','H261']):
        avoid_parts.append('Su ve nem' if lang=='TR' else 'Water and moisture')
    if any(h in h_codes for h in ['H240','H241','H242']):
        avoid_parts.append('Isıtma ve sürtünme' if lang=='TR' else 'Heating and friction')
    avoid_parts.append('Oksitleyici maddeler ve kuvvetli asitler' if lang=='TR'
                       else 'Oxidising agents and strong acids')
    avoid_str = '; '.join(avoid_parts) + '.'

    # ── 10.5 Bağdaşmayan maddeler — bileşenlerden dinamik ───────────────────
    comp_incompat = {
        '1330-20-7': ['güçlü oksitleyiciler', 'kuvvetli asitler'],
        '64-17-5':   ['güçlü oksitleyiciler', 'kuvvetli asitler', 'alkali metaller'],
        '67-56-1':   ['güçlü oksitleyiciler', 'klorin bileşikleri'],
        '67-64-1':   ['güçlü oksitleyiciler', 'kloroform'],
        '1310-73-2': ['asitler', 'su (ekzotermik)'],
        '7647-01-0': ['bazlar', 'oksitleyiciler'],
        '71-43-2':   ['güçlü oksitleyiciler', 'kuvvetli asitler'],
        '108-88-3':  ['güçlü oksitleyiciler', 'kuvvetli asitler'],
    }
    incompat_set = set()
    for comp in components:
        cas = comp.get('cas_no', comp.get('cas',''))
        if cas in comp_incompat:
            for item in comp_incompat[cas]:
                incompat_set.add(item)

    if is_flammable:
        incompat_set.add('güçlü oksitleyiciler' if lang=='TR' else 'strong oxidising agents')
    if has_alcohol:
        incompat_set.add('alkali metaller' if lang=='TR' else 'alkali metals')
        incompat_set.add('alüminyum (yüksek sıcaklıkta)' if lang=='TR'
                         else 'aluminium (at elevated temperatures)')
    if is_acid:
        incompat_set.add('bazlar ve aktif metaller' if lang=='TR' else 'bases and reactive metals')
    if is_base:
        incompat_set.add('asitler' if lang=='TR' else 'acids')
    if 'H314' in h_codes and not is_acid and not is_base:
        incompat_set.add('asitler ve bazlar' if lang=='TR' else 'acids and bases')
    if not incompat_set:
        incompat_set.add('güçlü oksitleyiciler, kuvvetli asitler ve bazlar' if lang=='TR'
                         else 'strong oxidising agents, strong acids and bases')

    if lang != 'TR':
        tr_en = {
            'güçlü oksitleyiciler': 'strong oxidising agents',
            'kuvvetli asitler': 'strong acids',
            'alkali metaller': 'alkali metals',
            'alüminyum (yüksek sıcaklıkta)': 'aluminium (at elevated temperatures)',
            'klorin bileşikleri': 'chlorine compounds',
            'kloroform': 'chloroform',
            'asitler, su (ekzotermik)': 'acids, water (exothermic)',
            'bazlar, oksitleyiciler': 'bases, oxidising agents',
            'asitler ve bazlar': 'acids and bases',
            'bazlar ve aktif metaller': 'bases and reactive metals',
            'asitler': 'acids',
        }
        incompat_set = {tr_en.get(i, i) for i in incompat_set}

    incompat_str = (', '.join(sorted(incompat_set)) + '.').capitalize()

    # ── 10.6 Bozunma ürünleri — sadece gerçek bileşenlere göre ──────────────
    decomp_parts = []
    if is_flammable or any(h in h_codes for h in ['H228','H242']):
        decomp_parts.append(
            'Karbon oksitler (CO, CO\u2082)' if lang=='TR'
            else 'Carbon oxides (CO, CO\u2082)'
        )
    if has_chlorinated:
        decomp_parts.append(
            'Klorür bileşikleri (HCl, Cl\u2082)' if lang=='TR'
            else 'Chloride compounds (HCl, Cl\u2082)'
        )
    if is_base or any(h in h_codes for h in ['H314']) and any(
            comp.get('cas_no', comp.get('cas','')) in {'1336-21-6','7664-41-7'}
            for comp in components):
        decomp_parts.append('NH\u2083' if lang=='TR' else 'NH\u2083 (ammonia)')
    if 'H400' in h_codes or 'H411' in h_codes:
        decomp_parts.append(
            'Sucul ortama zararlı organik fragmentler' if lang=='TR'
            else 'Harmful organic fragments to aquatic environment'
        )
    decomp_str = ('; '.join(decomp_parts) + '.') if decomp_parts else S(lang,'decomp_products')

    stability_data = [
        [sub_title(lang,'10.1'), phys.get('reactivity', na)],
        [sub_title(lang,'10.2'), S(lang,'stable_conditions')],
        [sub_title(lang,'10.3'), term(lang,'see_section')+' 7'],
        [sub_title(lang,'10.4'), avoid_str],
        [sub_title(lang,'10.5'), incompat_str],
        [sub_title(lang,'10.6'), decomp_str],
    ]
    story.append(data_table(stability_data, [65*mm, 115*mm], styles, header=False))

    story.append(PageBreak())

    # ─────────────────────────────────────────────────────────────────────────
    # BÖLÜM 11 — Toksikoloji
    # ─────────────────────────────────────────────────────────────────────────
    story += section_block(section_title(lang, 11), styles)
    story += sub_block(f"11.1 {sub_title(lang,'11.1')}", styles)

    tox_rows = [[S(lang,'route_label'), term(lang,'information')]]

    # Test verilerinden LD50/LC50
    phys_tox = sds_data.get('phys_props', {})
    if phys_tox.get('ld50_oral'):
        tox_rows.append([f"LD50 Oral ({term(lang,'rat')})", f"{phys_tox['ld50_oral']} mg/kg"])
    if phys_tox.get('ld50_dermal'):
        tox_rows.append([f"LD50 Dermal ({term(lang,'rat')})", f"{phys_tox['ld50_dermal']} mg/kg"])
    if phys_tox.get('lc50_inhal'):
        tox_rows.append([f"LC50 Inhalation ({term(lang,'rat')}, 4h)", f"{phys_tox['lc50_inhal']} mg/L"])

    # Maruziyet yolları — yalnızca sağlık tehlikesi H kodları (CLP Bölüm 3-5)
    # H224/H225/H226 fiziksel tehlikedir, Section 11'e dahil edilmez
    if lang == 'TR':
        exposure_map = {
            'H300':'Akut oral toksisite','H301':'Akut oral toksisite','H302':'Akut oral toksisite',
            'H310':'Akut dermal toksisite','H311':'Akut dermal toksisite','H312':'Akut dermal toksisite',
            'H330':'Akut inhalasyon toksisitesi','H331':'Akut inhalasyon toksisitesi','H332':'Akut inhalasyon toksisitesi',
            'H314':'Cilt/mukoza aşındırıcısı','H315':'Cilt tahrişi',
            'H317':'Cilt duyarlılaştırması','H318':'Ciddi göz hasarı','H319':'Göz tahrişi',
            'H334':'Solunum duyarlılaştırması',
            'H335':'Solunum yolu tahrişi — Merkezi sinir sistemi',
            'H336':'Narkotik etki — Merkezi sinir sistemi (baş dönmesi, uyuşukluk)',
            'H340':'Genetik hasar (in vivo)',
            'H341':'Genetik hasar (şüpheli)',
            'H350':'Kanserojen (kategori 1)','H351':'Kanserojen (kategori 2)',
            'H360':'Üreme toksisitesi (kategori 1)','H361':'Üreme toksisitesi (kategori 2)',
            'H362':'Emzirilen çocuklara zarar',
            'H370':'STOT-TE (tek maruziyet)','H371':'STOT-TE (tek maruziyet)',
            'H372':'STOT-TM (tekrarlanan maruziyet)','H373':'STOT-TM (tekrarlanan maruziyet)',
            'H304':'Aspirasyon tehlikesi',
        }
    else:
        exposure_map = {
            'H300':'Acute oral toxicity','H301':'Acute oral toxicity','H302':'Acute oral toxicity',
            'H310':'Acute dermal toxicity','H311':'Acute dermal toxicity','H312':'Acute dermal toxicity',
            'H330':'Acute inhalation toxicity','H331':'Acute inhalation toxicity','H332':'Acute inhalation toxicity',
            'H314':'Corrosive to skin/mucous membranes','H315':'Skin irritation',
            'H317':'Skin sensitisation','H318':'Serious eye damage','H319':'Eye irritation',
            'H334':'Respiratory sensitisation',
            'H335':'Respiratory tract irritation — CNS',
            'H336':'Narcotic effects — CNS (dizziness, drowsiness)',
            'H340':'Germ cell mutagenicity (cat.1)','H341':'Germ cell mutagenicity (cat.2)',
            'H350':'Carcinogenicity (cat.1)','H351':'Carcinogenicity (cat.2)',
            'H360':'Reproductive toxicity (cat.1)','H361':'Reproductive toxicity (cat.2)',
            'H362':'Effects on/via lactation',
            'H370':'STOT-SE (single exposure)','H371':'STOT-SE (single exposure)',
            'H372':'STOT-RE (repeated exposure)','H373':'STOT-RE (repeated exposure)',
            'H304':'Aspiration hazard',
        }
    added_routes = set()
    for h in h_codes:
        route = exposure_map.get(h)
        if route and route not in added_routes:
            stmt = get_h_stmt(h, lang)
            tox_rows.append([h + f' — {route}', stmt])
            added_routes.add(route)

    if len(tox_rows) > 1:
        story.append(data_table(tox_rows, [75*mm, 105*mm], styles))
    else:
        story.append(Paragraph(na, styles['body']))

    # ─────────────────────────────────────────────────────────────────────────
    # BÖLÜM 12 — Ekoloji
    # ─────────────────────────────────────────────────────────────────────────
    story += section_block(section_title(lang, 12), styles)

    eco_sections = sds_data.get('eco', {})
    # EcoOutput objesi veya dict olabilir
    if hasattr(eco_sections, 'sds_section_12'):
        sds12 = eco_sections.sds_section_12 or {}
        pbt_list = eco_sections.pbt_results or []
        bio = eco_sections.biodegradability or {}
    else:
        sds12 = eco_sections.get('sds_section_12', {})
        pbt_list = eco_sections.get('pbt_results', [])
        bio = eco_sections.get('biodegradability', {})

    # 12.5 PBT — pbt_results'tan özet
    pbt_summary = na
    if pbt_list:
        pbt_cas = [f"{p['name']}: P={p.get('P','?')} B={p.get('B','?')} T={p.get('T','?')}"
                   for p in pbt_list if p.get('is_pbt') or p.get('is_vpvb')]
        pbt_summary = '; '.join(pbt_cas) if pbt_cas else sds12.get('12.5', term(lang,'pbt_not'))

    eco_rows = [
        [sub_title(lang,'12.1'), sds12.get('12.1', na)],
        [sub_title(lang,'12.2'), bio.get('assessment') or sds12.get('12.2', na)],
        [sub_title(lang,'12.3'), sds12.get('12.3', na)],
        [sub_title(lang,'12.4'), na],
        [sub_title(lang,'12.5'), pbt_summary],
        [sub_title(lang,'12.6'), (lambda v:
            ('Endokrin bozucu özellik tespit edilmemiştir.' if lang=='TR' else 'No endocrine disrupting properties identified.')
            if 'ECHA SVHC' in v or 'kontrol edin' in v else v
        )(sds12.get('12.6', na))],
    ]
    story.append(data_table(eco_rows, [65*mm, 115*mm], styles, header=False))

    # M Faktör tablosu — CLP Annex I Tablo 4.1.3
    _eco_aq = eco_sections.aquatic if hasattr(eco_sections,'aquatic') else (
              eco_sections.get('aquatic') if isinstance(eco_sections,dict) else None)
    if _eco_aq:
        _mf_details = getattr(_eco_aq,'component_details',None) or []
        _aquatic_comps = [d for d in _mf_details if d.get('h_class')]
        if _aquatic_comps:
            _mf_lbl = 'M Faktörleri — CLP Tablo 4.1.3 (Toplamsal Yöntem)' if lang=='TR' \
                      else 'M Factors — CLP Table 4.1.3 (Summation Method)'
            story.append(Spacer(1, 4))
            story.append(Paragraph(f"<b>{_mf_lbl}:</b>", styles['body_bold']))
            _mf_hdr = [
                'CAS No',
                'Madde' if lang=='TR' else 'Substance',
                'Tehlike Sınıfı' if lang=='TR' else 'Hazard Class',
                'M (Akut)' if lang=='TR' else 'M (Acute)',
                'M (Kronik)' if lang=='TR' else 'M (Chronic)',
            ]
            _mf_rows = [_mf_hdr]
            for _d in _aquatic_comps:
                _mf_rows.append([
                    _d.get('cas',''),
                    _d.get('name',''),
                    translate_hclass(_d.get('h_class',''), lang),
                    str(_d.get('m_acute', 1)),
                    str(_d.get('m_chronic', 1)),
                ])
            story.append(data_table(_mf_rows,
                [24*mm, 52*mm, 42*mm, 22*mm, 22*mm], styles))
            story.append(Spacer(1, 3))

    # ─────────────────────────────────────────────────────────────────────────
    # BÖLÜM 13 — Bertaraf
    # ─────────────────────────────────────────────────────────────────────────
    story += section_block(section_title(lang, 13), styles)
    story += sub_block(f"13.1 {sub_title(lang,'13.1')}", styles)
    disposal_txt = get_disposal_regulation(lang) if lang=='TR' else term(lang,'disposal_reg')
    story.append(Paragraph(disposal_txt, styles['body']))

    # ─────────────────────────────────────────────────────────────────────────
    # BÖLÜM 14 — Taşımacılık
    # ─────────────────────────────────────────────────────────────────────────
    story += section_block(section_title(lang, 14), styles)
    transport = sds_data.get('transport', {})

    # Otomatik UN tespiti — kullanıcı vermemişse H kodlarından
    _phys_state = (phys.get('state') or phys.get('physical_state') or 'liquid').lower()
    auto_t = _auto_un(h_codes, state=_phys_state) if not transport.get('un_no') else None
    t_src = transport if transport.get('un_no') else (auto_t or {})
    un_no = t_src.get('un_no', '—')
    ship_name = t_src.get('shipping_name', na)
    haz_class  = t_src.get('hazard_class', '—')
    sub_class  = t_src.get('sub_class', '') or ''
    # Yan tehlike varsa "8 (5.1)" formatında göster — ADR/KKDİK Ek-2 standardı
    # Parantez dışı = asli tehlike, parantez içi = yan tehlike
    if sub_class and sub_class not in haz_class:
        haz_class = f"{haz_class} ({sub_class})"
    # ADR veritabanından label ile doğrula
    pack_grp = t_src.get('packing_group', '—')
    # Çevre tehlikesi — H kodlarına göre otomatik tespit
    env_h_codes = {
        'H400','H401','H410','H411','H412','H413',  # Sucul
        'H420',                                       # Ozon
    }
    is_env_hazard = any(h in h_codes for h in env_h_codes)

    
    if transport.get('env_hazard'):
        env_haz = transport['env_hazard']
    elif is_env_hazard:
        if lang == 'TR':
            # H410/H411 → Marine Pollutant (IMDG)
            mp_codes = {'H400','H410','H411'}
            if any(h in h_codes for h in mp_codes):
                env_haz = 'Evet — Deniz Kirletici (Marine Pollutant)'
            else:
                env_haz = 'Evet — Çevresel Açıdan Tehlikeli'
        else:
            mp_codes = {'H400','H410','H411'}
            if any(h in h_codes for h in mp_codes):
                env_haz = 'Yes — Marine Pollutant'
            else:
                env_haz = 'Yes — Environmentally Hazardous'
    else:
        env_haz = term(lang, 'not_applicable')
    
    auto_note = '' # Sistem notu gizlendi

    # ADR kemler + tünel kodu
    adr_det = get_adr_details(un_no, pack_grp) if un_no != '—' else {}
    kemler     = adr_det.get('kemler', '—')
    tunnel     = adr_det.get('tunnel_code', '—')
    cl_code    = adr_det.get('classification_code', '—')

    transport_rows = [
        [sub_title(lang,'14.1') + ' (UN No)',          un_no + auto_note],
        [sub_title(lang,'14.2'),                        ship_name],
        [sub_title(lang,'14.3') + ' (ADR/IMDG/IATA)',  haz_class],
        [sub_title(lang,'14.4'),                        pack_grp],
        [sub_title(lang,'14.5'),                        env_haz],
        ['Sınıflandırma Kodu (ADR)' if lang=='TR' else 'Classification Code (ADR)', cl_code],
        ['Kemler Kodu / Tehlike No'  if lang=='TR' else 'Hazard ID No (Kemler)',     kemler],
        ['Tünel Kısıtlama Kodu'      if lang=='TR' else 'Tunnel Restriction Code',   tunnel],
    ]
    story.append(data_table(transport_rows, [75*mm, 105*mm], styles, header=False))
    if auto_t:
        story.append(Paragraph(
            '* Taşımacılık sınıflandırması CLP tehlike sınıfına göre otomatik belirlenmiştir. Sevkiyat öncesi yetkili taşımacılık uzmanına danışınız.' if lang=='TR'
            else '* Transport classification determined automatically from CLP hazard class. Consult a transport specialist before shipment.',
            styles['small']
        ))

    # ─────────────────────────────────────────────────────────────────────────
    # BÖLÜM 15 — Mevzuat
    # ─────────────────────────────────────────────────────────────────────────
    story += section_block(section_title(lang, 15), styles)
    story += sub_block(f"15.1 {sub_title(lang,'15.1') if '15.1' in L.get('sub',{}) else 'Mevzuat bilgileri'}", styles)

    if lang == 'TR':
        has_biocide = any(
            'MIT' in c.get('name','') or 'CMIT' in c.get('name','') or
            'isothiazol' in c.get('name','').lower()
            for c in components
        )
        regulatory_text = get_section15_text(h_codes, has_biocide=has_biocide, lang='TR')
    elif is_us:
        regulatory_text = (
            "This product complies with:\n"
            "• OSHA HazCom 2012 (29 CFR 1910.1200)\n"
            "• CERCLA / SARA / RCRA\n"
            "• TSCA Inventory listed"
        )
    else:
        regulatory_text = get_section15_text(h_codes, has_biocide=False, lang='EN')

    for line in (regulatory_text or '').split('\n'):
        story.append(Paragraph(line, styles['body']))

    story += sub_block(f"15.2 {sub_title(lang,'15.2') if '15.2' in L.get('sub',{}) else 'Kimyasal güvenlik değerlendirmesi'}", styles)

    # CSA zorunluluğu kontrolü — KKDİK Madde 14: yıllık ≥1 ton üretim/ithalat +
    # SVHC/kanserojen/mutajen/üreme toksik ise KGA (Kimyasal Güvenlik Değerlendirmesi) zorunlu
    _cmr_h = {'H340','H341','H350','H350i','H351','H360','H360D','H360F','H361','H361d','H361f','H334'}
    _has_cmr = bool(set(h_codes) & _cmr_h)
    if _has_cmr:
        story.append(Paragraph(
            '<font color="#cc0000"><b>⚠ KKDİK Uyarısı:</b></font> Bu karışım kanserojen/mutajen/üreme toksik veya '
            'solunum duyarlılaştırıcı madde içermektedir. Yıllık ≥1 ton üretim veya ithalat durumunda '
            'KKDİK Madde 14 kapsamında Kimyasal Güvenlik Değerlendirmesi (KGA) zorunludur.'
            if lang == 'TR' else
            '<font color="#cc0000"><b>⚠ Regulatory Note:</b></font> This mixture contains CMR or respiratory sensitizer '
            'substances. A Chemical Safety Assessment (CSA) is mandatory under REACH Art.14 / KKDİK '
            'when annual production or import volume is ≥1 tonne.',
            styles['small']
        ))
    else:
        story.append(Paragraph(S(lang,'no_csa'), styles['small']))

    story.append(PageBreak())

    # ─────────────────────────────────────────────────────────────────────────
    # BÖLÜM 16 — Diğer
    # ─────────────────────────────────────────────────────────────────────────
    story += section_block(section_title(lang, 16), styles)

    # Validation uyarıları (varsa)
    _errors   = [i for i in _validation_issues if i['level']=='error']
    _warnings = [i for i in _validation_issues if i['level']=='warning']
    if _errors or _warnings:
        _val_title = 'GBF Doğrulama Uyarıları' if lang=='TR' else 'SDS Validation Warnings'
        story.append(Paragraph(f"<b>⚠ {_val_title}:</b>", styles['body_bold']))
        for iss in _errors + _warnings:
            icon = '❌' if iss['level']=='error' else '⚠'
            story.append(Paragraph(
                f"<font color='{'#cc0000' if iss['level']=='error' else '#e67e00'}'>"
                f"{icon} [{iss['code']}] {iss['section']}: {iss['msg']}</font>",
                styles['small']
            ))
        story.append(Spacer(1,4))

    # H kodu tam metin listesi
    all_h_b16 = list(dict.fromkeys(h_codes))
    all_h = all_h_b16  # EUH Bölüm 2'de gösterildi
    if all_h:
        hdr_txt = 'Tehlike / EUH İfadeleri (Tam Metin):' if lang=='TR' else 'Hazard / EUH Statements (Full Text):'
        story.append(Paragraph(f'<b>{hdr_txt}</b>', styles['body_bold']))
        for hc in all_h:
            if hc.startswith('EUH'):
                # Önce euh_details'dan tam metin
                detail = next((d for d in euh.get('euh_details',[]) if d.get('code')==hc), {})
                if lang == 'TR':
                    raw_text = (detail.get('text_tr') or detail.get('text', '')).strip()
                else:
                    raw_text = detail.get('text', '').strip()
                if raw_text:
                    stmt = raw_text
                else:
                    if lang == 'TR':
                        substance = detail.get('source_name_tr') or detail.get('source_name', '')
                    else:
                        substance = detail.get('source_name', '')
                    stmt = get_euh(lang, hc, substance)
            else:
                stmt = get_h_stmt(hc, lang)
            if stmt and stmt != hc:
                story.append(Paragraph(f'• <b>{hc}:</b> {stmt}', styles['small']))
        story.append(Spacer(1, 4))

    # Revizyon geçmişi
    story.append(Paragraph(
        f"<b>{S(lang,'revision_history')}:</b> "
        f"Rev.{rev_no} — {rev_date}",
        styles['body']
    ))

    # SDS tam P kodu listesi
    if p_data.get('p_codes'):
        story.append(Spacer(1, 4))
        story.append(Paragraph(
            f"<b>{S(lang,'precaut_full')}:</b>",
            styles['body_bold']
        ))
        from app.services.p_code_service import P_COMBOS, P_TEXTS, P_LABEL_PRIORITY, classify_sds_p_codes
        sds_cls = classify_sds_p_codes(p_data['p_codes'])
        for grp_key, icon, lbl in [
            ('mandatory','✓',S(lang,'mandatory_label')),
            ('evaluate','~',S(lang,'evaluate_label')),
            ('optional','○',S(lang,'optional_label')),
        ]:
            codes = sds_cls['groups'].get(grp_key, [])
            if codes:
                story.append(Paragraph(f"<b>{icon} {lbl}:</b>", styles['small']))
                # Grup içi şiddet sırası (yüksek önce)
                codes_sorted = sorted(codes, key=lambda p: P_LABEL_PRIORITY.get(p, 5), reverse=True)
                for code in codes_sorted:
                    txt = get_p(lang, code) or P_COMBOS.get(code) or P_TEXTS.get(code, code)
                    story.append(Paragraph(f"  {code}: {txt}", styles['small']))

    # Kısaltmalar
    story.append(Spacer(1, 6))
    abbrev_tr = (
        "KKDİK — Kimyasalların Kaydı, Değerlendirilmesi, İzni ve Kısıtlanması | "
        "GBF — Güvenlik Bilgi Formu | KKE — Kişisel Koruyucu Ekipman | "
    ) if lang == 'TR' else ''
    story.append(Paragraph(
        f"<b>{S(lang,'abbreviations_label')}:</b> "
        f"CLP — Classification, Labelling and Packaging | "
        f"GHS — Globally Harmonised System | "
        f"{abbrev_tr}"
        f"SDS — Safety Data Sheet | PPE — Personal Protective Equipment",
        styles['small']
    ))

    # Yasal uyarı
    story.append(Spacer(1, 6))
    story.append(HRFlowable(width='100%', thickness=0.5, color=C_BORDER))
    story.append(Spacer(1, 3))
    story.append(Paragraph(
        S(lang,'sds_legal_note_1') + ' ' +
        S(lang,'sds_legal_note_2') + ' ' +
        S(lang,'sds_legal_note_3'),
        styles['small']
    ))

    # GBF Hazırlayıcı Sertifika Bilgisi (KKDİK zorunluluğu)
    author_data = sds_data.get('author', {})
    author_text = format_author_block(author_data, lang)
    story.append(Spacer(1, 6))
    story.append(HRFlowable(width='100%', thickness=0.5, color=C_BORDER))
    story.append(Spacer(1, 3))
    for line in author_text.split('\n'):
        style = styles['small'] if not line.startswith('GBF Hazırlayan') and not line.startswith('Prepared') else styles['body_bold']
        story.append(Paragraph(line, style))

    # ── PDF oluştur ──────────────────────────────────────────────────────────
    doc.build(story, onFirstPage=_draw_page, onLaterPages=_draw_page)

    return buf.getvalue()
