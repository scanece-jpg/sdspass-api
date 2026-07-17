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
import re as _re
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
import json as _json

def _register_fonts():
    """DejaVu Sans — 12 dil Unicode desteği (TR/PL/RO/BG/CZ/HR vs.)

    Font arama sırası:
    1. Uygulama ile gelen fonts/ klasörü (Render.com için güvenilir)
    2. Linux sistem klasörü (/usr/share/fonts/truetype/dejavu/)
    3. Debian/Ubuntu alternatif yollar
    """
    # Olası font dizinleri — önce yerel, sonra sistem (Linux ve Windows)
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

    # Windows fallback: DejaVuSans bulunamadıysa Arial ile ikame et
    # Arial Türkçe karakterleri destekler (Ç, Ş, Ğ, İ, Ö, Ü vb.)
    if registered == 0:
        print('[Font] UYARI: DejaVu fontları bulunamadı — Windows Arial ile ikame deneniyor')
        _WIN_FONTS = os.environ.get('WINDIR', 'C:\\Windows') + '\\Fonts'
        _fallback_map = {
            'DejaVuSans':          ('arial.ttf',   'arialbd.ttf'),   # normal → bold de kullanılır
            'DejaVuSans-Bold':     ('arialbd.ttf', 'arialbd.ttf'),
            'DejaVuSans-Oblique':  ('ariali.ttf',  'arialbd.ttf'),
            'DejaVuSansMono':      ('cour.ttf',    'courbd.ttf'),     # Courier Mono
            'DejaVuSansMono-Bold': ('courbd.ttf',  'courbd.ttf'),
        }
        for name, (fname, _) in _fallback_map.items():
            if name in pdfmetrics.getRegisteredFontNames():
                registered += 1
                continue
            path = os.path.join(_WIN_FONTS, fname)
            if os.path.exists(path):
                try:
                    pdfmetrics.registerFont(TTFont(name, path))
                    registered += 1
                    print(f'[Font] {name} → {fname} (Windows Arial ikamesi)')
                except Exception as e:
                    print(f'[Font] Windows Arial kayıt hatası ({fname}): {e}')

    if registered == 0:
        print('[Font] UYARI: Hiçbir unicode font bulunamadı — Helvetica kullanılacak (Unicode desteği sınırlı)')
    else:
        print(f'[Font] {registered}/{len(font_files)} font kayıt edildi')

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
from app.services.clp_service import normalize_ph_display as _normalize_ph
from app.services.codes_i18n import get_h, get_euh, get_p, get_ppe, get_sentence, translate_hclass, translate_hclass_list, EUH_STMTS, correct_hclass
from app.services.ghs_pictogram import get_ghs_codes, pictogram_table
from app.services.transport_adr_service import get_adr_details
from app.services.tr_oel_service import get_oel_table, format_oel_row
from app.services.tr_mevzuat_service import get_section15_text, get_disposal_regulation, get_disposal_content
from app.services.gbf_author_service import format_author_block, validate_certificate
from app.services.sds_sentence_service import (
    generate_section3, generate_section, get_echa_range, generate_section_42
)


# ─── RENKLER ─────────────────────────────────────────────────────────────────

C_SECTION_BG    = HexColor('#000000')   # Bölüm başlık arkaplan (siyah)
C_SECTION_TEXT  = HexColor('#ffffff')   # Bölüm başlık yazı (beyaz)
C_SUB_BG        = HexColor('#000000')   # Alt başlık arkaplan (siyah — bölüm başlıklarıyla uyumlu)
C_SUB_TEXT      = HexColor('#ffffff')   # Alt başlık yazı (beyaz)
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
        'tbl_header': ParagraphStyle(
            'TblHeader',
            fontName='DejaVuSans-Bold',
            fontSize=8,
            leading=11,
            textColor=HexColor('#ffffff'),  # Tablo başlık satırı — beyaz yazı
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
    'H372':'Uzun süreli veya tekrarlı maruz kalma sonucu organlarda hasara yol açar.',
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


def _build_stot_organ_map(components: list) -> dict:
    """
    Bileşen listesinden STOT hedef organ haritası oluştur.
    H372/H373 (STOT RE) ve H370/H371 (STOT SE) her ikisini kapsar.
    Döner: {h_code: organ_name_en}  (yalnızca organ bilinen sonuçlar)
    """
    import re as _re
    from app.services.stot_engine import calculate as calculate_stot_re, GENERAL_ORGAN
    stot_comps = [
        {'cas': c.get('cas_no', ''), 'name': c.get('name', ''),
         'conc': c.get('concentration', 0), 'hazards': c.get('hazards', [])}
        for c in components
    ]
    stot_res = calculate_stot_re(stot_comps)
    organ_map = {}
    for sr in stot_res.get('results', []):
        h = sr['h_code']
        organ = sr['organ']
        if organ == GENERAL_ORGAN:
            continue
        if h not in organ_map:
            organ_map[h] = organ

    # H370/H371 (STOT SE) — bileşen tehlike kodu içindeki parentez bilgisinden organ çıkar
    # Örnek: 'H370 (nervous system)' → organ_map['H370'] = 'nervous system'
    for comp in components:
        for haz in (comp.get('hazards') or []):
            raw = (haz.get('h_code') or '').strip()
            h_base = raw.replace('*', '').strip()[:4]
            if h_base in ('H370', 'H371') and h_base not in organ_map:
                m = _re.search(r'\(([^)]+)\)', raw)
                if m:
                    organs = [p.strip().lower() for p in m.group(1).split(',') if p.strip()]
                    if organs:
                        organ_map[h_base] = ', '.join(organs)
    return organ_map


def get_stot_stmt(h_code: str, lang: str, organ_en: str) -> str:
    """H370/H371/H372/H373 için hedef organ adı içeren H ifadesi üret."""
    from app.services.stot_engine import ORGAN_TR
    if lang == 'TR':
        organ = ORGAN_TR.get(organ_en.lower(), organ_en)
        if h_code == 'H370':
            return f'Organlara ({organ}) hasar verir.'
        elif h_code == 'H371':
            return f'Organlara ({organ}) hasar verebilir.'
        elif h_code == 'H372':
            return f'Uzun süreli veya tekrarlı maruz kalma sonucu organlarda ({organ}) hasara yol açar.'
        return f'Uzun süreli veya tekrarlanan maruziyetle organlarda ({organ}) hasar verebilir.'
    else:
        if h_code == 'H370':
            return f'Causes damage to {organ_en} following single exposure.'
        elif h_code == 'H371':
            return f'May cause damage to {organ_en} following single exposure.'
        elif h_code == 'H372':
            return f'Causes damage to {organ_en} through prolonged or repeated exposure.'
        return f'May cause damage to {organ_en} through prolonged or repeated exposure.'


# ─── UN NUMARASI OTOMATİK TESPİTİ (KALDIRILDI) ──────────────────────────────
# _auto_un() kaldırıldı. Transport sınıflandırması tek kaynaktan yapılır:
#   js/engines/transport_engine.js → frontend gönderir → _map_transport() → PDF
# Fallback gerekirse transport_engine.js'i düzeltin, buraya duplicate yazmayın.
# ─────────────────────────────────────────────────────────────────────────────
def _auto_un(h_codes: list, state: str = 'liquid') -> dict | None:
    """KALDIRILDI — her zaman None döner. Transport verisi frontend'den gelir."""
    return None


# ─── ADR 3.1.2.8: B.N.O. GİRİŞLERİ İÇİN TEKNİK İSİM SEÇİCİ ────────────────
# Her UN numarası için tehlike grupları — sıralama önemli (önce birincil tehlike)
_NOS_HAZARD_GROUPS: dict[str, list] = {
    # Yanıcı + Korozif
    'UN2924': [{'H224','H225','H226'}, {'H314'}],
    # Zehirli + Korozif
    'UN2927': [{'H300','H310','H330'}, {'H301','H311','H331'}],
    # Yanıcı + Toksik
    'UN1992': [{'H224','H225','H226'}, {'H300','H301','H310','H311','H330','H331'}],
    # Korozif + Oksitleyici
    'UN3093': [{'H314'}, {'H271','H272'}],
    # Oksitleyici sıvı
    'UN2912': [{'H271'}],
    'UN3139': [{'H272'}],
    # Pirofor / Kendiliğinden Isınan
    'UN2845': [{'H250'}],
    'UN3088': [{'H251'}],
    'UN3190': [{'H252'}],
    # Su ile tepkiyen
    'UN3148': [{'H260','H261'}],
    # Oksitleyici gaz
    'UN3156': [{'H270'}],
    # Yanıcı gaz
    'UN1954': [{'H220','H221'}],
    # Yanıcı sıvı (tekil)
    'UN1993': [{'H224','H225','H226'}],
    # Korozif sıvı (tekil)
    'UN1760': [{'H314'}],
    # Zehirli sıvı (tekil)
    'UN2810': [{'H300','H301','H310','H311','H330','H331'}],
    # Çevre için tehlikeli
    'UN3082': [{'H400','H410','H411'}],
    'UN3077': [{'H400','H410','H411'}],
}


def _nos_technical_names(un_no: str, components: list, lang: str = 'TR') -> str:
    """ADR 3.1.2.8 — B.N.O. sevkiyat adına eklenecek teknik isimler.

    Her tehlike grubundan en yüksek konsantrasyonlu bileşeni seçer.
    Sonuç: en fazla 2 bileşen adı, virgülle ayrılmış.
    """
    # "UN 2924" → "UN2924" normalizasyonu
    un_key = un_no.replace(' ', '')
    groups = _NOS_HAZARD_GROUPS.get(un_key, [])
    if not groups or not components:
        return ''

    selected: list[str] = []
    seen: set[str] = set()

    for group_hcodes in groups:
        candidates: list[tuple[float, str]] = []
        for c in components:
            comp_hcodes = {
                h.get('h_code', '').replace('*', '').strip()
                for h in c.get('hazards', [])
            }
            if not (comp_hcodes & group_hcodes):
                continue
            # Türkçe ise name_tr, değilse name, yoksa CAS
            raw = (c.get('name_tr', '') if lang == 'TR' else '') or \
                  c.get('name', '') or c.get('cas_no', '')
            # ADR teknik isim: sadece birincil ad — çoklu izomer/eşanlamlı
            # listelerinden ("heptan; n-heptan [1]\n2,4-dimetilpentan [2]…")
            # yalnızca ilk ismi al; satır ve noktalı virgül ayıraçlarını
            # temizle; "[1]" gibi numara eklerini kaldır.
            primary = raw.split('\n')[0].split(';')[0]
            primary = _re.sub(r'\s*\[\d+\]', '', primary).strip()
            name = primary
            if not name or name in seen:
                continue
            conc = float(c.get('concentration', 0) or 0)
            candidates.append((conc, name))

        if candidates:
            # Konsantrasyon azalan sırada — en baskın katkı sağlayan önce
            candidates.sort(key=lambda x: x[0], reverse=True)
            best = candidates[0][1]
            selected.append(best)
            seen.add(best)

        if len(selected) >= 2:
            break

    return ', '.join(selected)


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
    """Siyah zemin üzerine beyaz yazı alt başlık bloğu (bölüm başlıklarıyla uyumlu)"""
    tbl = Table(
        [[Paragraph(title, styles['sub_title'])]],
        colWidths=[PAGE_W],
    )
    tbl.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), C_SUB_BG),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
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
                s = styles['tbl_header'] if (header and i == 0) else styles['body']
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
    # CLP Ek-VI ** notları için kullanıcı girişleri: {'H372': 'Böbrekler; solunum yolu', ...}
    _clp_note_overrides: dict = sds_data.get('clp_note_overrides', {}) or {}

    # STOT RE hedef organ haritası — Bölüm 2.2 ve 11'de kullanılır
    _stot_organ_map = _build_stot_organ_map(components)

    # ── H314 Nötralizasyon Override — kullanıcı "kaldır" seçtiyse ────────────
    _h314_removed = bool(sds_data.get('h314_neutralization_removed', False))
    _H314_COVERED = {'H314', 'H318', 'H315', 'H319'}  # H314 kaldırılınca bunlar da düşer
    if _h314_removed:
        clp = dict(clp)
        # h_codes (etiket) — H314 ve kapsanan kodları kaldır
        clp['h_codes'] = [h for h in clp.get('h_codes', [])
                          if h not in _H314_COVERED]
        # all_h_codes (Bölüm 2.1 sınıflandırma tablosu) — aynı filtreyi uygula
        clp['all_h_codes'] = [h for h in (clp.get('all_h_codes') or clp.get('h_codes', []))
                              if h not in _H314_COVERED]
        # passed (gerekçe tablosu) — H314 satırını kaldır  [key: 'passed', not 'clp_passed']
        clp['passed'] = [r for r in clp.get('passed', [])
                         if r.get('h_code','').replace('*','').strip()[:4] not in _H314_COVERED]
        # Piktogramlar — korozif ikonu kaldır
        clp['pictograms'] = [p for p in clp.get('pictograms', []) if p != 'GHS05']
        # Signal word: başka Tehlike H kodu yoksa Uyarı'ya düşür
        _danger_h = {'H200','H201','H202','H203','H204','H205',
                     'H220','H222','H224','H225','H240','H241',
                     'H250','H260','H270','H271','H272',
                     'H300','H301','H310','H311','H330','H331',
                     'H334','H340','H350','H360','H370','H372'}
        if not any(h in _danger_h for h in clp['h_codes']):
            clp['signal_word'] = 'Warning'

    # Validator devre dışı
    _validation_issues = []
    disclosure = sds_data.get('disclosure_map', {})
    phys = sds_data.get('phys_props', {})
    phys_methods = sds_data.get('phys_methods', {})
    rev = sds_data.get('revision', {})
    p_data = sds_data.get('p_codes', {})
    eco = sds_data.get('eco', {})
    # ATE karışım detayları — Bölüm 2.2 zorunlu ibare + Bölüm 11 tablosu için erken yükle
    # Backend fallback Bölüm 11'de ek hesap yapabilir; buradaki değer §2.2 için yeterli
    ate_mix_details = sds_data.get('ate_mix_details') or {}

    # US_EN — OSHA HazCom format uyarlaması
    is_us = lang == 'US_EN'
    product_name = product.get('name', 'Product Name' if is_us else 'Ürün Adı')
    rev_date = rev.get('date', datetime.now().strftime(L.get('date_format', '%d.%m.%Y')))
    rev_no = rev.get('no', '1')
    version = rev.get('version', '1.0')

    # Header/Footer için callback fonksiyonları
    header_text = product_name
    footer_text = f"Rev.{rev_no} | {rev_date}"

    # Font güvenlik kontrolü — DejaVuSans yoksa Helvetica fallback
    _registered = pdfmetrics.getRegisteredFontNames()
    _F_BOLD   = 'DejaVuSans-Bold'  if 'DejaVuSans-Bold'  in _registered else 'Helvetica-Bold'
    _F_NORMAL = 'DejaVuSans'        if 'DejaVuSans'        in _registered else 'Helvetica'

    def _draw_page(canvas, doc_obj):
        canvas.saveState()
        w, h = A4
        # Header
        canvas.setFont(_F_BOLD, 7)
        canvas.setFillColor(HexColor('#64748b'))
        canvas.drawString(15*mm, h - 12*mm, header_text)
        canvas.drawRightString(w - 15*mm, h - 12*mm, f"SDS | {footer_text}")
        canvas.setStrokeColor(HexColor('#e2e8f0'))
        canvas.setLineWidth(0.3)
        canvas.line(15*mm, h - 14*mm, w - 15*mm, h - 14*mm)
        # Footer
        canvas.line(15*mm, 14*mm, w - 15*mm, 14*mm)
        canvas.setFont(_F_NORMAL, 6.5)
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
    if all_h_codes:
        hc_str = '  '.join(all_h_codes)
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

    # Kullanım tipi etiketi — REACH Annex II §1.2 / KKDİK Ek-2
    _usage_val = product.get('usage', 'industrial')
    _usage_labels = {
        'industrial':   ('Endüstriyel / Profesyonel kullanım', 'Industrial / Professional use'),
        'professional': ('Endüstriyel / Profesyonel kullanım', 'Industrial / Professional use'),
        'consumer':     ('Tüketici kullanımı',                 'Consumer use'),
    }
    _usage_lbl_tr, _usage_lbl_en = _usage_labels.get(_usage_val, ('Endüstriyel kullanım', 'Industrial use'))
    _usage_lbl = _usage_lbl_tr if lang == 'TR' else _usage_lbl_en
    story.append(Paragraph(
        f"<b>{'Kullanım kategorisi' if lang=='TR' else 'Use category'}:</b> {_usage_lbl}",
        styles['body']
    ))
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
        'H240','H241','H250','H251','H260','H270','H271','H272',
        'H300','H301','H304','H310','H311',
        'H314','H318','H330','H331',
        'H334','H340','H350','H360','H360D','H360F','H360FD','H370','H372',
    }
    _hc_set = {h.split()[0] for h in h_codes}
    signal = 'Danger' if (_hc_set & _DANGER_H) else 'Warning'
    sig_color = C_DANGER if signal=='Danger' else (C_WARNING if signal=='Warning' else black)

    # ── Bileşen bazlı not bayrak haritası (note_flag / note) ─────────────────
    # Bileşenlerin tehlike verilerinden H kodu → (not_flag, not_metni) haritası oluştur.
    # Bu harita; `passed` listesinde açık not olmasa bile fallback satırları için kullanılır.
    _comp_note_map: dict = {}   # {h_code_4: {'flag': str, 'note': str}}
    for _cc in (sds_data.get('components') or []):
        for _hh in (_cc.get('hazards') or []):
            _hc4 = (_hh.get('h_code') or '').replace('*','').strip()[:4]
            _nf  = _hh.get('note_flag')
            _nt  = _hh.get('note')
            if _hc4 and _nf and _hc4 not in _comp_note_map:
                _comp_note_map[_hc4] = {'flag': _nf, 'note': _nt or ''}

    # H kodu → görüntüleme rotası (oral/dermal/inhalasyon)
    # h_class'ta rota saklanmaz; PDF render sırasında H kodundan türetilir
    _ROUTE_SUFFIX_TR = {
        'H300': ' (ağız)',    'H301': ' (ağız)',    'H302': ' (ağız)',    'H303': ' (ağız)',
        'H310': ' (deri)',    'H311': ' (deri)',    'H312': ' (deri)',    'H313': ' (deri)',
        'H330': ' (solunum)', 'H331': ' (solunum)', 'H332': ' (solunum)', 'H333': ' (solunum)',
        'H335': ' (solunum yolu tahrişi)', 'H336': ' (uyuşukluk/baş dönmesi)',
    }
    _ROUTE_SUFFIX_EN = {
        'H300': ' (oral)',       'H301': ' (oral)',       'H302': ' (oral)',       'H303': ' (oral)',
        'H310': ' (dermal)',     'H311': ' (dermal)',     'H312': ' (dermal)',     'H313': ' (dermal)',
        'H330': ' (inhalation)', 'H331': ' (inhalation)', 'H332': ' (inhalation)', 'H333': ' (inhalation)',
        'H335': ' (respiratory irritation)', 'H336': ' (narcosis)',
    }
    _route_sfx = _ROUTE_SUFFIX_TR if lang == 'TR' else _ROUTE_SUFFIX_EN

    clf_rows = []
    seen_clf  = set()
    clf_notes = {}   # {h_code_4: {'flag': str, 'note': str}} — tabloda gösterilecek notlar

    for entry in clp.get('passed', []):
        _hc_full = (entry.get('h_code','') or '').replace('*','').strip()
        # Preserve H360D/F/FD and H361D/F/FD sub-codes; truncate others to 4 chars
        hc = _hc_full if (_hc_full[4:].upper().replace('D','').replace('F','') == '') else _hc_full[:4]
        if hc in seen_clf:
            continue
        seen_clf.add(hc)
        reason = entry.get('reason','')
        conc_info = reason or entry.get('cutoff_used','') or '—'
        # h_code'dan yetkili h_class türet (DB bozukluğuna karşı düzelt)
        raw_hclass  = entry.get('h_class', '')
        raw_hcode   = entry.get('h_code', '')
        fixed_hclass = correct_hclass(raw_hcode, raw_hclass) or raw_hclass
        # Hâlâ boşsa: H300/H310/H330 gibi ATE Cat.1/2 belirsiz kodlar için
        # h_code bazlı son çare eşleme (pratikte nadir)
        if not fixed_hclass:
            _ACUTE_CODE_FALLBACK = {
                'H300': 'Acute Tox. 1',  'H310': 'Acute Tox. 1',  'H330': 'Acute Tox. 1',
                'H303': 'Acute Tox. 5',  'H313': 'Acute Tox. 5',  'H333': 'Acute Tox. 5',
            }
            fixed_hclass = _ACUTE_CODE_FALLBACK.get(raw_hcode[:4], '')
        clf_rows.append([
            translate_hclass(fixed_hclass, lang) + _route_sfx.get(raw_hcode[:4], ''),
            raw_hcode,
            conc_info,
        ])
        # not bayrak bilgisini topla (passed listesinden veya bileşen haritasından)
        nf = entry.get('note_flag') or (_comp_note_map.get(hc) or {}).get('flag')
        nt = entry.get('note')      or (_comp_note_map.get(hc) or {}).get('note') or ''
        if nf and hc not in clf_notes:
            clf_notes[hc] = {'flag': nf, 'note': nt, 'h_code': raw_hcode}

    # passed boş veya eksikse all_h_codes'dan fallback satırlar ekle
    # all_h_codes: domine edilenler dahil tüm sınıflandırmalar (CLP Ek I § 1.2.2)
    # H kodu → h_class ters eşlemesi (fallback için)
    from app.services.clp_service import CLP_CUTOFFS_DICT
    from app.services.codes_i18n import H_CODE_TO_CANONICAL_CLASS
    _h_to_class = {}
    for cls, rule in CLP_CUTOFFS_DICT.items():
        h = rule.get('h','')
        if h and h not in _h_to_class:
            _h_to_class[h] = cls
    # H360 sub-code overrides (CLP_CUTOFFS_DICT anahtarları 4 karakter olduğundan)
    _h_to_class.update({
        'H360D':  'Repr. 1A/1B', 'H360F':  'Repr. 1A/1B', 'H360FD': 'Repr. 1A/1B',
        'H361D':  'Repr. 2',     'H361F':  'Repr. 2',     'H361FD': 'Repr. 2',
    })
    # Fiziksel / eko H kodları — CLP_CUTOFFS_DICT'te yok, canonical dict'ten ekle
    # (H224/H225/H226/H304/H410 vb. — passed loop H_CODE_TO_CANONICAL_CLASS üzerinden
    #  zaten çözüyor; burası all_h_codes fallback loop için güvenlik ağı)
    for _hc, _cls in H_CODE_TO_CANONICAL_CLASS.items():
        if _hc not in _h_to_class:
            _h_to_class[_hc] = _cls
    dom_note = 'Baskın tehlike sınıfı kapsamında' if lang == 'TR' else 'Covered by dominant hazard class'
    for hc_raw in all_h_codes:
        hc = (hc_raw or '').replace('*','').strip()
        # Preserve sub-codes (H360D/F/FD, H361D/F/FD); truncate others to 4 chars
        if hc and not hc[4:].replace('D','').replace('F','') == '':
            hc = hc[:4]
        if not hc or hc in seen_clf:
            continue
        # H229 ayrı satır değil — CLP Tablo 2.3.1'e göre H222/H223 ile birlikte
        # verilir; ayrı "Aerosol 3" kategorisi yoktur. H222/H223 satırına eklenir.
        if hc == 'H229':
            for row in clf_rows:
                if row[1] in ('H222', 'H223'):
                    if 'H229' not in row[1]:
                        row[1] = row[1] + ' + H229'
            seen_clf.add('H229')
            continue
        seen_clf.add(hc)
        hclass_fallback = translate_hclass(_h_to_class.get(hc, ''), lang) + _route_sfx.get(hc, '')
        clf_rows.append([hclass_fallback, hc_raw, dom_note])
        # fallback satır için de not bayrak kontrolü
        if hc in _comp_note_map and hc not in clf_notes:
            clf_notes[hc] = {**_comp_note_map[hc], 'h_code': hc_raw}

    if clf_rows:
        reason_lbl = 'Kesme Değeri / Gerekçe' if lang=='TR' else 'Cut-off / Reason'
        h_code_lbl = 'H Kodu' if lang=='TR' else 'H Code'
        story.append(data_table(
            [[term(lang,'classification'), h_code_lbl, reason_lbl]] + clf_rows,
            [90*mm, 30*mm, 60*mm], styles
        ))
        # ── CLP Ek-VI not bayrakları (*, **, ***, ****) ──────────────────────
        # Belirlenen not bayraklarını tablodan sonra göster.
        # ** (hedef organ) ve *** (üreme alt kategorisi) yasal açıdan önemlidir.
        if clf_notes:
            story.append(Spacer(1, 4))
            _NOTE_FLAG_LABELS = {
                '*':    ('*',    'Asgari sınıflandırmadır — mevcut verilere göre gerçek sınıf daha yüksek olabilir (CLP Ek-VI §1.2.1)',
                                 'This is a minimum classification — the actual classification may be higher based on available data (CLP Annex VI §1.2.1)'),
                '**':   ('**',   'Hedef organ ve/veya maruziyet yolunun SDS Bölüm 11\'de belirtilmesi zorunludur (CLP Ek-VI dipnotu).',
                                 'Target organ and/or route of exposure must be specified in SDS Section 11 (CLP Annex VI footnote).'),
                '***':  ('***',  'Bu sınıflandırma yalnızca belirtilen üreme toksisitesi alt kategorisi için geçerlidir (F=Fertilite, D=Gelişim).',
                                 'Classification applies only to the specified reproductive toxicity sub-category (F=Fertility, D=Development).'),
                '****': ('****', 'Patlayıcı alt sınıfı belirsiz — test verisiyle manuel değerlendirme gereklidir.',
                                 'Explosive sub-class undetermined — manual assessment with test data required.'),
            }
            shown_flags = set()
            for _hc4, _nd in sorted(clf_notes.items()):
                _fl = _nd.get('flag','')
                _hcode_disp = _nd.get('h_code', _hc4)
                # ** — kullanıcı hedef organ girişi varsa onu göster, yoksa genel uyarı
                if _fl == '**':
                    _override = _clp_note_overrides.get(_hc4, '').strip()
                    if _override:
                        _txt = (
                            f'Hedef organ / Maruziyet yolu: <b>{_override}</b> (CLP Ek-VI **)'
                            if lang == 'TR' else
                            f'Target organ / Route of exposure: <b>{_override}</b> (CLP Annex VI **)'
                        )
                    else:
                        _txt = (
                            'Hedef organ ve/veya maruziyet yolunun SDS Bölüm 11\'de belirtilmesi '
                            'zorunludur (CLP Ek-VI dipnotu).'
                            if lang == 'TR' else
                            'Target organ and/or route of exposure must be specified in SDS '
                            'Section 11 (CLP Annex VI footnote).'
                        )
                    story.append(Paragraph(
                        f'<font color="#555555"><i>** {_hcode_disp}: {_txt}</i></font>',
                        styles['small']
                    ))
                    continue
                if _fl in shown_flags:
                    continue
                shown_flags.add(_fl)
                _stars, _txt_tr, _txt_en = _NOTE_FLAG_LABELS.get(_fl, (_fl, _nd.get('note',''), _nd.get('note','')))
                _txt = _txt_tr if lang == 'TR' else _txt_en
                story.append(Paragraph(
                    f'<font color="#555555"><i>{_stars} {_hcode_disp}: {_txt}</i></font>',
                    styles['small']
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

    # ── Fiziksel özellik aralık notları (PCN hazırlık) ────────────────────────
    # Sınıflandırmayı etkileyen bir özellik aralık olarak girildiyse
    # hangi ucun kullanıldığını şeffaf biçimde belirt.
    try:
        from app.services.phys_props_parser import get_range_notes as _get_range_notes
        _rng_notes = _get_range_notes(phys, lang)
        if _rng_notes:
            story.append(Spacer(1, 4))
            _rng_title = (
                'Sınıflandırmada kullanılan fiziksel özellik değerleri:'
                if lang == 'TR' else
                'Physical property values used for classification:'
            )
            story.append(Paragraph(
                f'<font color="#555555"><i>{_rng_title}</i></font>',
                styles['small']
            ))
            for _rn in _rng_notes:
                story.append(Paragraph(
                    f'<font color="#555555"><i>• {_rn}</i></font>',
                    styles['small']
                ))
    except Exception:
        pass

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
            hc_base = hc.split('(')[0].split()[0]
            if hc.startswith('EUH'):
                stmt = get_euh(lang, hc)
                if not stmt or stmt == hc:
                    # euh_details'dan bul
                    stmt = next((d.get('text_tr' if lang=='TR' else 'text','') for d in euh.get('euh_details',[]) if d.get('code')==hc), hc)
            elif hc_base in ('H370', 'H371', 'H372', 'H373') and hc_base in _stot_organ_map:
                stmt = get_stot_stmt(hc_base, lang, _stot_organ_map[hc_base])
            else:
                stmt = get_h_stmt(hc_base, lang)
            story.append(Paragraph(f'• <b>{hc_base}:</b> {stmt}', styles['bullet']))

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
        # P501 — bertaraf kodu, 6 limitinin dışında "+1 Bertaraf Kodu" olarak her zaman basılır
        mandatory = label_p.get('mandatory', [])
        if mandatory:
            for m in mandatory:
                txt = get_p(lang, m) or P_TEXTS.get(m, m)
                story.append(Paragraph(f"• <b>{m}:</b> {txt}", styles['bullet']))

        # Limit aşım notu — birden fazla tehlike sınıfı olan ürünlerde öncelikli seçim yapıldı
        if label_p.get('limit_exceeded'):
            _exc_note = (
                'Birden fazla tehlike sınıfı bulunduğundan öncelikli P kodları seçilmiştir. '
                'Tam liste SDS Bölüm 2\'de yer almaktadır (CLP Madde 28(3)).'
                if lang == 'TR' else
                'Due to multiple hazard classes, priority P-codes have been selected. '
                'Full list is provided in SDS Section 2 (CLP Article 28(3)).'
            )
            story.append(Spacer(1, 2))
            story.append(Paragraph(f"<i>{_exc_note}</i>", styles['small']))

    # ─── SEA §3.1.3.6.2.2 — Zorunlu ibare: bilinmeyen akut toksisite ≥%1 ─────────
    # Trigger: herhangi bir bilinmeyen bileşen bireysel olarak ≥%1 konsantrasyonda
    # statementNeeded bayrağı JS motorundan gelir; yoksa unknownPct≥1'den türet
    _stmt_needed = False
    _unk_pct_for_stmt = 0.0
    if ate_mix_details:
        for _rd in ate_mix_details.values():
            if _rd.get('statementNeeded', False):
                _stmt_needed = True
            _upct = float(_rd.get('unknownPct', 0) or 0)
            if _upct > _unk_pct_for_stmt:
                _unk_pct_for_stmt = _upct
        # Fallback: statementNeeded bayrağı yoksa unknownPct≥1 kontrolü yap
        if not _stmt_needed and _unk_pct_for_stmt >= 1.0:
            _stmt_needed = True
    # Bileşen listesinden doğrudan da türet (her iki motor için güvence)
    if not _stmt_needed:
        for _cmp in components:
            _cmp_conc = float(_cmp.get('concentration') or _cmp.get('conc') or 0)
            if _cmp_conc < 1.0:
                continue
            _cmp_annex = _cmp.get('annex_vi', False)
            _cmp_ate_unk = _cmp.get('ate_unknown', False)
            _cmp_ate_dict = _cmp.get('ate_dict') or {}
            _has_acute = any(
                (h.get('h_code','') or '').replace('*','').strip()[:4]
                in {'H300','H301','H302','H310','H311','H312','H330','H331','H332'}
                for h in _cmp.get('hazards', [])
            )
            _has_user_ate = bool(_cmp_ate_dict.get('oral') or _cmp_ate_dict.get('dermal') or _cmp_ate_dict.get('inhal'))
            if _cmp_ate_unk or (not _has_acute and not _cmp_annex and not _has_user_ate):
                _stmt_needed = True
                _unk_pct_for_stmt += _cmp_conc
    if _stmt_needed and _unk_pct_for_stmt <= 0:
        _stmt_needed = False  # Yüzde hesaplanamıyorsa ibare gösterilmez
    if _stmt_needed:
        _unk_x = round(_unk_pct_for_stmt, 1)
        if lang == 'TR':
            _stmt_text = (f"Karışımın %{_unk_x}'i bilinmeyen akut toksisiteye sahip "
                          f"bileşenlerden oluşmaktadır.")
        else:
            _stmt_text = (f"{_unk_x}% of the mixture consists of ingredient(s) of "
                          f"unknown acute toxicity.")
        story.append(Spacer(1, 4))
        story.append(Paragraph(f"<b>{_stmt_text}</b>", styles['body']))

    # ─── Duyarlılaştırıcı Madde Kimliği — CLP Ek II §2.8 (ZORUNLU) ─────────────
    # §2.8 yalnızca Skin Sens. (H317) ve Resp. Sens. (H334) için zorunludur.
    # H319, H411 vb. için madde adı etikette ZORUNLU DEĞİL (denetim hatası).
    SENS_H = {'H317','H334'}
    contrib_sens = []
    for comp_c in components:
        comp_hcodes = {h.get('h_code','').replace('*','').strip() for h in comp_c.get('hazards',[])}
        if comp_hcodes & SENS_H:
            _cn = comp_c.get('name_tr','') if lang=='TR' else ''
            _cn = _cn or comp_c.get('name','') or comp_c.get('cas_no','')
            if _cn:
                contrib_sens.append(_cn)
    if contrib_sens:
        # EUH208 zaten sensitizer adını içeriyor; burada da açık liste göster
        lbl_s = 'Duyarlılaştırıcı içerir' if lang=='TR' else 'Contains sensitiser'
        story.append(Spacer(1, 3))
        story.append(Paragraph(
            f"<b>{lbl_s} (CLP Ek II §2.8 / SEA Madde 20):</b> {', '.join(set(contrib_sens))}",
            styles['body']
        ))

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

        cas_hdr  = ('CAS No\nEC / KKDİK No' if lang=='TR' else 'CAS No\nEC / REACH')
        name_hdr = S(lang,'ingredient_label')
        conc_hdr = term(lang,'concentration')
        clf_hdr  = term(lang,'classification')

        # Başlık hücrelerini Paragraph olarak sarıyoruz — header style data_table içinde uygulanacak
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
            # Ad ve konsantrasyon Paragraph'a sarılır — kelime kırılmasını ve
            # PDF text extraction artifaktlarını önler
            _name_para = Paragraph(r['name'] or '', styles['body'])
            _conc_para = Paragraph(r['concentration'] or '', styles['body'])
            tbl_data.append([
                cas_cell,
                _name_para,
                _conc_para,
                _clf_para,
            ])

        # Toplam 175mm: CAS(35) + Ad(51) + Konst.(30) + Sınıf(59)
        # Not: 18mm çok dar, 25mm de "Konsantrasyo n" bölünüyordu → 30mm'ye çıkarıldı
        story.append(data_table(tbl_data,
            [35*mm, 51*mm, 30*mm, 59*mm], styles))
        # REACH eksik not
        if missing_reach:
            story.append(Paragraph(
                f"* KKDİK kayıt numarası bulunamayan maddeler için tedarikçiye başvurun: {', '.join(missing_reach)}" if lang=='TR'
                else f"* REACH/KKDİK registration numbers not found for: {', '.join(missing_reach)}. Obtain from supplier.",
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
    _sym_bullets = generate_section_42(h_codes)
    if _sym_bullets:
        story += bullet_list(_sym_bullets, styles)
    else:
        story.append(Paragraph(S(lang, 'symptoms_general'), styles['body']))

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
    # H kodu bazlı depolama metinleri (slot 72) — H224/H225/H226/H314 için özel
    sec72 = generate_section(72, h_codes)
    if sec72['bullets']:
        story += bullet_list(sec72['bullets'], styles)
    else:
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

    # Python PPE motoru çıktısı (sds_data['ppe']) tercih edilir;
    # yoksa generate_section fallback kullanılır.
    _ppe_engine_data = sds_data.get('ppe') or {}

    def _ppe_items_text(items: list) -> str:
        """[{ppe, level}] listesini okunabilir metne çevir."""
        mandatory   = [i['ppe'] for i in items if i.get('level') == 1]
        recommended = [i['ppe'] for i in items if i.get('level') == 2]
        parts = mandatory
        if recommended:
            rec_label = 'Tavsiye' if lang == 'TR' else 'Recommended'
            parts += [f"({rec_label}: {p})" for p in recommended]
        return '; '.join(parts) if parts else term(lang, 'not_applicable')

    if _ppe_engine_data:
        # Yeni PPE motoru verisi mevcut — detaylı tablo
        _na = term(lang, 'not_applicable')
        ppe_rows = [
            [
                term(lang, 'ppe_resp'),
                _ppe_items_text(_ppe_engine_data.get('respiratory', [])) or _na,
            ],
            [
                term(lang, 'ppe_gloves'),
                _ppe_items_text(_ppe_engine_data.get('hands', [])) or _na,
            ],
            [
                term(lang, 'ppe_eyes'),
                _ppe_items_text(_ppe_engine_data.get('eyes', [])) or _na,
            ],
            [
                term(lang, 'ppe_body'),
                _ppe_items_text(_ppe_engine_data.get('body', [])) or _na,
            ],
        ]
        story.append(data_table(ppe_rows, [50*mm, 130*mm], styles, header=False))

        # Genel hijyen önlemleri
        _gen = _ppe_engine_data.get('general', [])
        if _gen:
            _gen_label = 'Genel Hijyen Önlemleri:' if lang == 'TR' else 'General Hygiene Measures:'
            story.append(Paragraph(f"<b>{_gen_label}</b>", styles['body']))
            for g in _gen:
                story.append(Paragraph(f"• {g}", styles['bullet']))
    else:
        # Fallback — eski generate_section yöntemi
        sec8 = generate_section(8, h_codes)
        ppe_old = sec8.get('ppe', {})
        ppe_map = {
            'gloves': term(lang, 'ppe_gloves'),
            'eyes':   term(lang, 'ppe_eyes'),
            'resp':   term(lang, 'ppe_resp'),
            'body':   term(lang, 'ppe_body'),
        }
        ppe_rows = []
        for key, label in ppe_map.items():
            val = ppe_old.get(key, term(lang, 'not_applicable'))
            ppe_rows.append([label, val])
        story.append(data_table(ppe_rows, [50*mm, 130*mm], styles, header=False))

    story.append(PageBreak())

    # ─────────────────────────────────────────────────────────────────────────
    # BÖLÜM 9 — Fiziksel Özellikler
    # ─────────────────────────────────────────────────────────────────────────
    story += section_block(section_title(lang, 9), styles)
    story += sub_block(f"9.1 {sub_title(lang,'9.1')}", styles)

    na = term(lang,'not_available')

    _prod_form     = product.get('form', '')
    _is_solid_form = _prod_form in ('solid', 'powder')
    _is_gas_form   = _prod_form == 'gas'

    # PCN zorunlu alanlar kontrolü — yalnızca API yanıtına/uygulama içi uyarıya eklenir,
    # PDF çıktısına iç teknik mesaj basılmaz.
    _pcn_base = ['ph', 'density', 'flash_point']
    # Gaz ve katı formda parlama noktası uygulanamaz — PCN kontrolünden çıkar
    if _is_solid_form or _is_gas_form:
        _pcn_base = [k for k in _pcn_base if k != 'flash_point']
    pcn_required = _pcn_base
    pcn_missing = [k for k in pcn_required if not phys.get(k)]

    # Sıvı ürün + yanıcı sıvı bileşen girilmemişse parlama noktası hesaplanamaz uyarısı
    _FLAM_LIQ_H = {'H224', 'H225', 'H226', 'H227'}
    # Su (7732-18-5) veya seyreltici CAS'lar girilmişse parlama noktası hesabı zaten anlamsız
    # (su için uyarı bastırılır — yanıcı değil ama sıvı karışım oluşturur).
    _DILUENT_CAS = {'7732-18-5', '7664-41-7', '124-38-9', '7727-37-9'}
    _comp_cas_all = {(c.get('cas_no') or c.get('cas') or '').strip() for c in components}
    if (lang == 'TR'
            and product.get('form', '') == 'liquid'
            and not phys.get('flash_point')
            and not (_comp_cas_all & _DILUENT_CAS)):
        _comp_h_all = set()
        for _c in components:
            for _h in (_c.get('h_codes') or _c.get('hazard_statements') or []):
                _comp_h_all.add(_h if isinstance(_h, str) else _h.get('code', ''))
        if not (_comp_h_all & _FLAM_LIQ_H):
            story.append(Paragraph(
                "<font color='orange'>⚠ Ürün formu sıvı ancak hiçbir bileşende yanıcı sıvı "
                "(H224/H225/H226) bulunmuyor. Parlama noktası hesaplanamaz — "
                "bileşen listesini kontrol edin.</font>",
                styles['small']
            ))

    # Sıvı ürün için viskozite ve çözünürlük eksikliği uyarısı
    # KKDİK Ek-2 Bölüm 9: Sıvı karışımlarda bu parametreler "Bilgi yok" bırakılamaz
    def _method_note(key):
        """Hesap yöntemi/kaynağı notu — KKDİK Ek-2 §9 REACH Annex II zorunluluğu"""
        pm = phys_methods.get(key, {})
        if not pm:
            return ''
        std = _re.sub(r'<[^>]+>', '', pm.get('standard') or '').strip()
        if std and ' / ' in std:
            std = std.split(' / ')[0].strip()
        err = pm.get('error_pct')
        if pm.get('measured'):
            parts = ['ölçülen']
            if std and std not in ('', '—'):
                parts.append(std)
        else:
            parts = ['hesaplanmış']
            if std and std not in ('', '—'):
                parts.append(std)
            if err:
                parts.append(f'±%{err}')
        return f'<br/><font size="6" color="#888888">{" – ".join(parts)}</font>'

    def _pv(key, unit=''):
        v = phys.get(key)
        if v is None or v == '': return na
        # Yeni yapılandırılmış format (phys_props_parser çıktısı)
        if isinstance(v, dict):
            if v.get('nd') or v.get('na'):
                return v.get('display') or na
            raw_display = v.get('display')
            if not raw_display:
                return na
            v_str = raw_display
        else:
            v_str = str(v)
        # Birim zaten değerin içindeyse tekrar ekleme.
        # calc=None olan dict'ler metin açıklamasıdır (Karışır, Belirlenmemiştir vb.) — birim ekleme.
        _is_text_only = isinstance(v, dict) and v.get('calc') is None
        if unit and unit not in v_str and not _is_text_only:
            val_str = f"{v_str} {unit}"
        else:
            val_str = v_str
        # Log Kow için ECHA Kılavuz v4 §9.1(n) zorunluluğu:
        # "It shall be indicated whether the reported value is based on testing or on calculation"
        if key == 'log_kow' and not phys_methods.get('log_kow'):
            _kow_src = (
                '<br/><font size="6" color="#888888">hesaplanmış (yöntem belirtilmedi)</font>'
                if lang == 'TR' else
                '<br/><font size="6" color="#888888">calculated (method not specified)</font>'
            )
            val_str += _kow_src
        else:
            val_str += _method_note(key)
        return val_str

    def _pv_ph():
        """pH display — yeni dict formatını ve eski string formatını destekler."""
        raw = phys.get('ph')
        if raw is None or raw == '':
            return na
        if isinstance(raw, dict):
            if raw.get('nd') or raw.get('na'):
                return raw.get('display') or na
            ph_str = raw.get('display') or ''
            if not ph_str:
                return na
        else:
            ph_str = str(raw)
        return _normalize_ph(ph_str) + _method_note('ph')

    def _text(key):
        """Birimsiz metin alanı — hem string hem dict formatını destekler.
        Bulunamadığında None döner (or-zinciri için)."""
        v = phys.get(key)
        if v is None or v == '':
            return None
        if isinstance(v, dict):
            if v.get('nd') or v.get('na'):
                return v.get('display') or None
            return v.get('display') or None
        s = str(v).strip()
        return s if s else None

    _mp_lbl  = 'Donma/Erime Noktası' if lang=='TR' else 'Melting/Freezing Point'
    _rd_lbl  = 'Bağıl Yoğunluk (su=1)' if lang=='TR' else 'Relative Density (water=1)'
    _vd_lbl  = 'Buhar Yoğunluğu (hava=1)' if lang=='TR' else 'Vapor Density (air=1)'
    _ai_lbl  = 'Kendiliğinden Tutuşma' if lang=='TR' else 'Auto-ignition Temp.'
    _ex_lbl  = 'Patlama Sınırları (LEL/UEL)' if lang=='TR' else 'Explosive Limits (LEL/UEL)'

    _ex_val = na
    _lel_raw = phys.get('lel')
    _uel_raw = phys.get('uel')
    if _lel_raw or _uel_raw:
        _lel_str = (_lel_raw.get('display') if isinstance(_lel_raw, dict)
                    else str(_lel_raw) if _lel_raw else '?')
        _uel_str = (_uel_raw.get('display') if isinstance(_uel_raw, dict)
                    else str(_uel_raw) if _uel_raw else '?')
        _ex_val = f"%{_lel_str} – %{_uel_str}"
        _ex_val += _method_note('lel')   # LEL yöntemi (UEL aynı kaynaktan)

    _vp_raw = phys.get('vapor_pressure')
    _vp_display = (_vp_raw.get('display') if isinstance(_vp_raw, dict)
                   else (str(_vp_raw) if _vp_raw not in (None, '') else None))
    if _vp_display:
        # Birim zaten içeriyorsa dokunma, sadece sayısal değere hPa ekle
        _vp_val = (_vp_display if any(u in _vp_display for u in ('hPa','kPa','mmHg','bar','Pa'))
                   else f"{_vp_display} hPa")
        _vp_val += _method_note('vapor_pressure')
    elif phys.get('vapor_pressure_num'):
        _vp_val = f"{phys.get('vapor_pressure_num')} hPa"
    else:
        _vp_val = na

    _er_lbl  = 'Buharlaşma Hızı' if lang=='TR' else 'Evaporation Rate'
    _kow_lbl = 'Dağılım Katsayısı (log Kow)' if lang=='TR' else 'Partition Coeff. (log Kow)'

    _ph_conc_raw   = phys.get('ph_conc') or '1'
    if lang == 'TR':
        _ph_conc_lbl = f'pH Değeri (%{_ph_conc_raw} sulu çözeltide)'
    else:
        _ph_conc_lbl = f'pH Value ({_ph_conc_raw}% aqueous solution)'

    all_phys_rows = [
        [phys_prop(lang,'appearance'),
         _text(f'appearance_{lang}') or _text('appearance') or na],
        [phys_prop(lang,'color'),         _text('color') or na],
        [phys_prop(lang,'odor'),          _text('odor')  or na],
        [(_ph_conc_lbl if _is_solid_form else phys_prop(lang,'ph')), _pv_ph()],
        [phys_prop(lang,'flash_point'),   _pv('flash_point','°C')],
        [phys_prop(lang,'boiling_point'), _pv('boiling_point','°C')],
        [_mp_lbl,                         _pv('melting_point','°C')],
        [_er_lbl,                         _text('evap_rate') or na],
        [phys_prop(lang,'density'),       _pv('density','g/cm³')],
        [_rd_lbl,                         _pv('rel_density')],
        [phys_prop(lang,'viscosity'),     _pv('viscosity','cSt @40°C')],
        [phys_prop(lang,'solubility'),    _pv('solubility', 'mg/L')],
        [phys_prop(lang,'vapor_pressure'),_vp_val],
        [_vd_lbl,                         _pv('vapor_density')],
        [_kow_lbl,                        _pv('log_kow')],
        [_ai_lbl,                         _pv('auto_ignition','°C')],
        [_ex_lbl,                         _ex_val],
    ]
    # Koku eşiği
    _ot_lbl = 'Koku Eşiği' if lang=='TR' else 'Odour Threshold'
    _ot_val = _pv('odour_threshold')

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
    # Katı/toz formlar için erime noktası zorunlu (KKDİK Ek-2 §9)
    _fp_lbl  = phys_prop(lang, 'flash_point')
    _bp_lbl  = phys_prop(lang, 'boiling_point')
    _ph_lbl  = phys_prop(lang, 'ph')
    _vis_lbl = phys_prop(lang, 'viscosity')
    _optional = {_rd_lbl, _vd_lbl, _ai_lbl, _ex_lbl, _ot_lbl, _dc_lbl, _er_lbl, _kow_lbl}
    if not _is_solid_form:
        _optional.add(_mp_lbl)
    # Katı/toz formda pH ve viskozite uygulanamaz — değer girilmemişse gizle
    if _is_solid_form:
        _optional.add(_ph_lbl)
        _optional.add(_ph_conc_lbl)
        _optional.add(_vis_lbl)

    # ECHA Kılavuz v4 §9.1(h)(e): Gaz/katı formda parlama/kaynama noktası "uygulanamaz"
    # olarak açıkça belirtilmeli — gizlemek yerine "Uygulanamaz (gaz)" göster.
    _na_gas = (
        term(lang, 'not_applicable') +
        (' (gaz form)' if lang == 'TR' else ' (gas form)')
    )
    _na_solid = (
        term(lang, 'not_applicable') +
        (' (katı/toz form)' if lang == 'TR' else ' (solid/powder form)')
    )
    # "Veri yok" (frontend display) veya "Bilgi yok" (i18n) — her ikisini de yakala
    _NO_DATA_VALS = {na, '', 'Veri yok', 'Veri Yok', 'Bilgi yok', 'Bilgi Yok',
                     'No data available', 'No data', 'N/A', '-'}
    _WATER_CAS = {'7732-18-5', '7647-01-0', '1310-73-2', '1310-58-3'}
    _comp_cas_set_fp = {(c.get('cas_no') or c.get('cas') or '').strip() for c in components}
    _has_aqueous = any(
        (c.get('cas_no') or c.get('cas') or '').strip() == '7732-18-5'
        and float(c.get('concMax') or c.get('concentration') or c.get('conc') or 0) >= 50
        for c in components
    )
    _na_aqueous = (
        term(lang, 'not_applicable') +
        (' (sulu karışım — su içeriyor)' if lang == 'TR' else ' (aqueous mixture — contains water)')
    )
    # Aerosol form: CLP Ek-I §2.3 Not 2 — alevlenirlik H222/H223 üzerinden iletilir,
    # bileşen parlama noktası aerosol için uygulanamaz.
    _is_aerosol_form = _prod_form == 'aerosol'
    if _is_aerosol_form:
        _h_codes_all = clp.get('h_codes', []) + clp.get('all_h_codes', [])
        _aerosol_h_ref = 'H222' if 'H222' in _h_codes_all else ('H223' if 'H223' in _h_codes_all else 'H222')
        _na_aerosol_tr = (
            f"Uygulanamaz — Ürün aerosol dispenser olarak sınıflandırılmıştır "
            f"(bkz. Bölüm 2, {_aerosol_h_ref}). CLP Ek-I §2.3 Not 2 uyarınca aerosoller "
            f"ayrıca alevlenebilir sıvı (§2.6) kriterine göre sınıflandırılmaz; "
            f"alevlenirlik ısı yanma değeri ve/veya beyan edilen yanıcı içerik yüzdesi "
            f"üzerinden değerlendirilir."
        )
        _na_aerosol_en = (
            f"Not applicable — Product is classified as an aerosol dispenser "
            f"(see Section 2, {_aerosol_h_ref}). Per CLP Annex I §2.3 Note 2, aerosols are "
            f"not additionally classified under flammable liquids (§2.6); flammability is "
            f"assessed via heat of combustion and/or declared flammable content percentage."
        )
        _na_aerosol = _na_aerosol_tr if lang == 'TR' else _na_aerosol_en
        for row in all_phys_rows:
            if row[0] == _fp_lbl:
                row[1] = _na_aerosol
    elif _is_gas_form:
        for row in all_phys_rows:
            if row[0] in (_fp_lbl, _bp_lbl) and row[1] in _NO_DATA_VALS:
                row[1] = _na_gas
    elif _is_solid_form:
        for row in all_phys_rows:
            if row[0] in (_fp_lbl, _bp_lbl) and row[1] in _NO_DATA_VALS:
                row[1] = _na_solid
    elif _has_aqueous:
        # KKDİK Ek-2 §9.1: "Bilgi yok" için neden belirtilmeli; sulu karışımda FP uygulanamaz
        for row in all_phys_rows:
            if row[0] == _fp_lbl and row[1] in _NO_DATA_VALS:
                row[1] = _na_aqueous

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
    # NH\u2083 yaln\u0131zca bile\u015fende amonyak veya amonyak \u00e7\u00f6zeltisi varsa olu\u015fur
    # (CAS 1336-21-6 = amonyak \u00e7\u00f6zeltisi, 7664-41-7 = susuz amonyak)
    if any(comp.get('cas_no', comp.get('cas','')) in {'1336-21-6','7664-41-7'}
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
            'H360D':'Üreme toksisitesi — gelişimsel (kategori 1)',
            'H360F':'Üreme toksisitesi — fertilite (kategori 1)',
            'H360FD':'Üreme toksisitesi — gelişimsel + fertilite (kategori 1)',
            'H361D':'Üreme toksisitesi — gelişimsel (kategori 2)',
            'H361F':'Üreme toksisitesi — fertilite (kategori 2)',
            'H361FD':'Üreme toksisitesi — gelişimsel + fertilite (kategori 2)',
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
            'H360D':'Reproductive toxicity — developmental (cat.1)',
            'H360F':'Reproductive toxicity — fertility (cat.1)',
            'H360FD':'Reproductive toxicity — developmental + fertility (cat.1)',
            'H361D':'Reproductive toxicity — developmental (cat.2)',
            'H361F':'Reproductive toxicity — fertility (cat.2)',
            'H361FD':'Reproductive toxicity — developmental + fertility (cat.2)',
            'H362':'Effects on/via lactation',
            'H370':'STOT-SE (single exposure)','H371':'STOT-SE (single exposure)',
            'H372':'STOT-RE (repeated exposure)','H373':'STOT-RE (repeated exposure)',
            'H304':'Aspiration hazard',
        }
    added_routes = set()
    for h in h_codes:
        h_base = h.split('(')[0].split()[0]
        route = exposure_map.get(h_base)
        if route and route not in added_routes:
            if h_base in ('H370', 'H371', 'H372', 'H373') and h_base in _stot_organ_map:
                stmt = get_stot_stmt(h_base, lang, _stot_organ_map[h_base])
            else:
                stmt = get_h_stmt(h_base, lang)
            tox_rows.append([h_base + f' — {route}', stmt])
            added_routes.add(route)

    if len(tox_rows) > 1:
        story.append(data_table(tox_rows, [75*mm, 105*mm], styles))
        # ── CLP Ek-VI ** notları: hedef organ/maruziyet yolu belirtme zorunluluğu ──
        # Bileşenlerden ** bayraklı STOT veya diğer H kodlarını topla
        _sec11_notes_shown = set()
        for _cc11 in (sds_data.get('components') or []):
            for _hh11 in (_cc11.get('hazards') or []):
                _nf11 = _hh11.get('note_flag','')
                _hc11 = (_hh11.get('h_code') or '').replace('*','').strip()[:4]
                if not _nf11 or _hc11 in _sec11_notes_shown:
                    continue
                # Yalnızca sınıflandırma sonucunda kullanılan H kodlarını göster
                if _hc11 not in h_codes:
                    continue
                _sec11_notes_shown.add(_hc11)
                if _nf11 == '**':
                    _override11 = _clp_note_overrides.get(_hc11, '').strip()
                    if _override11:
                        _note_txt_tr = (
                            f'<font color="#555555"><i>** {_hc11} — Hedef organ / Maruziyet yolu: '
                            f'<b>{_override11}</b></i></font>'
                        )
                        _note_txt_en = (
                            f'<font color="#555555"><i>** {_hc11} — Target organ / Route of exposure: '
                            f'<b>{_override11}</b></i></font>'
                        )
                    else:
                        _note_txt_tr = (
                            f'<font color="#555555"><i>** {_hc11}: CLP Ek-VI dipnotuna göre hedef organ '
                            f've/veya maruziyet yolunun bu bölümde belirtilmesi gerekmektedir.</i></font>'
                        )
                        _note_txt_en = (
                            f'<font color="#555555"><i>** {_hc11}: Per CLP Annex VI footnote, the '
                            f'target organ and/or route of exposure must be specified in this section.</i></font>'
                        )
                    story.append(Spacer(1, 3))
                    story.append(Paragraph(
                        _note_txt_tr if lang == 'TR' else _note_txt_en,
                        styles['small']
                    ))
                elif _nf11 == '***' and _hh11.get('repro_sub'):
                    _sub = _hh11['repro_sub']
                    _sub_txt_tr = 'fertilite (F)' if _sub == 'F' else 'gelişim (D)'
                    _sub_txt_en = 'fertility (F)' if _sub == 'F' else 'development (D)'
                    _rtxt_tr = (
                        f'<font color="#555555"><i>*** {_hc11}: Bu sınıflandırma yalnızca '
                        f'{_sub_txt_tr} üreme toksisitesi alt kategorisi için geçerlidir.</i></font>'
                    )
                    _rtxt_en = (
                        f'<font color="#555555"><i>*** {_hc11}: Classification applies only to '
                        f'the {_sub_txt_en} reproductive toxicity sub-category.</i></font>'
                    )
                    story.append(Spacer(1, 3))
                    story.append(Paragraph(
                        _rtxt_tr if lang == 'TR' else _rtxt_en,
                        styles['small']
                    ))
    else:
        story.append(Paragraph(na, styles['body']))

    # ─── ATE Karışım Hesabı — KKDİK Ek-2 Bölüm 11 gereği ────────────────────
    # CLP Ek I §3.1.3 — 1/ATEmix = Σ(Ci/ATEi) / 100
    # Hem sınıflandırılan hem sınıflandırılmayan durumlar raporlanır
    ACUTE_TOX_CLASSES = {'Acute Tox. 1','Acute Tox. 2','Acute Tox. 3','Acute Tox. 4',
                         'Acute Tox. 1*','Acute Tox. 2*','Acute Tox. 3*','Acute Tox. 4*'}
    ACUTE_H = {'H300','H301','H302','H310','H311','H312','H330','H331','H332'}

    comp_has_acute = any(
        (hz.get('h_code') or '').replace('*','').strip()[:4] in ACUTE_H
        for comp_item in sds_data.get('components', [])
        for hz in comp_item.get('hazards', [])
    )

    # Frontend'den gelen ATEmix detayları (JS engine hesabı)
    ate_mix_details = sds_data.get('ate_mix_details', {})

    # Backend fallback: frontend boş gönderirse backend hesapla
    # clp_service.calculate_ate_health_h_codes — buhar/toz ayrımı dahil doğru ATE formülü
    if not ate_mix_details and comp_has_acute:
        from app.services.clp_service import calculate_ate_health_h_codes as _calc_ate
        _, ate_mix_details = _calc_ate(
            sds_data.get('components', []),
            form=sds_data.get('form', ''),
        )

    _ROUTE_LABEL_TR = {'oral': 'Oral (Ağız)', 'dermal': 'Dermal (Deri)', 'inhal': 'İnhalasyon (Solunum)'}
    _ROUTE_LABEL_EN = {'oral': 'Oral', 'dermal': 'Dermal', 'inhal': 'Inhalation'}
    _ROUTE_UNIT     = {'oral': 'mg/kg', 'dermal': 'mg/kg', 'inhal': 'mg/L/4h'}

    if ate_mix_details:
        story.append(Spacer(1, 4))
        # Başlık
        ate_header = ('ATE Karışım Hesabı — CLP Ek I §3.1.3' if lang == 'TR'
                      else 'ATEmix Calculation — CLP Annex I §3.1.3')
        story.append(Paragraph(ate_header, styles['sub_title']))
        story.append(Spacer(1, 3))

        # Her yol için sonuç satırı
        result_rows = [[
            ('Maruziyet Yolu' if lang == 'TR' else 'Route'),
            ('ATEmix Değeri'  if lang == 'TR' else 'ATEmix Value'),
            ('Sonuç H Kodu'   if lang == 'TR' else 'Result H Code'),
        ]]
        for route, detail in ate_mix_details.items():
            ate_val   = detail.get('ateMix')
            res_code  = detail.get('resultCode') or ('—' if lang == 'TR' else '—')
            unk_pct   = detail.get('unknownPct', 0)
            r_lbl = (_ROUTE_LABEL_TR if lang == 'TR' else _ROUTE_LABEL_EN).get(route, route)
            unit  = _ROUTE_UNIT.get(route, 'mg/kg')
            unk_note = (f' (bilinmeyen %{unk_pct} — revize formül)' if unk_pct > 10 else '')
            result_rows.append([
                r_lbl,
                f'{ate_val} {unit}{unk_note}' if ate_val is not None else '—',
                res_code,
            ])

        if len(result_rows) > 1:
            story.append(data_table(result_rows, [55*mm, 70*mm, 55*mm], styles))
            story.append(Spacer(1, 3))

        # Bileşen detay tablosu
        comp_rows = [[
            ('Madde'         if lang == 'TR' else 'Substance'),
            ('Konst. (%)'    if lang == 'TR' else 'Conc. (%)'),
            ('H Kodu'        if lang == 'TR' else 'H Code'),
            ('ATE (nokta tahmini)' if lang == 'TR' else 'ATE (point estimate)'),
        ]]
        for route, detail in ate_mix_details.items():
            unit = _ROUTE_UNIT.get(route, 'mg/kg')
            for c in detail.get('components', []):
                comp_rows.append([
                    str((c.get('name_tr','') if lang=='TR' else '') or c.get('name', c.get('cas', '—'))),
                    f"{c.get('conc', '—')}",
                    str(c.get('code', '—')),
                    f"{c.get('ate', '—')} {unit}",
                ])
        if len(comp_rows) > 1:
            story.append(data_table(comp_rows, [60*mm, 20*mm, 20*mm, 80*mm], styles))

        # Açıklama notu
        # h_codes (etiket) yerine ate_mix_details resultCode'larına bak:
        # h_codes dominance nedeniyle H312/H332 içermeyebilir (H310/H330 baskın),
        # ama ATE hesabı gerçekten bir sınıflandırma ürettiyse doğru notu göster.
        # CLP Annex I §3.1.1: ATE ≤ eşik (dahil) → sınıflandırma tetiklenir.
        mix_has_acute = any(
            detail.get('resultCode')
            for detail in ate_mix_details.values()
        ) or bool(set(h_codes) & ACUTE_H)
        if mix_has_acute:
            ate_note = (
                'Yukarıdaki ATEmix değerleri hesaplanmış olup karışım akut toksisite '
                'sınıflandırması (H300/H301/H302/H310/H311/H312/H330/H331/H332) '
                'bu hesaba dayanmaktadır. Kullanılan nokta tahminleri SEA/CLP Ek I Tablo 3.1.2\'den alınmıştır.'
            ) if lang == 'TR' else (
                'The ATEmix values above have been calculated and the mixture acute toxicity '
                'classification is based on this calculation. Point estimates are from '
                'CLP Annex I Table 3.1.2.'
            )
        else:
            ate_note = (
                'ATEmix hesabı yapılmış, ancak hesaplanan değer sınıflandırma eşiğini '
                'aşmadığından akut toksisite sınıflandırması atanmamıştır.'
            ) if lang == 'TR' else (
                'ATEmix was calculated but did not exceed the classification threshold; '
                'no acute toxicity classification assigned.'
            )
        story.append(Spacer(1, 3))
        story.append(Paragraph(ate_note, styles['small']))

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

    # 12.4 Toprak hareketliliği — ecological_service'den
    _soil_detail = sds12.get('12.4_detail', {})
    _soil_comps  = _soil_detail.get('components', []) if isinstance(_soil_detail, dict) else []
    if _soil_comps:
        _known = [c for c in _soil_comps if c.get('log_koc') is not None]
        if _known:
            _soil_txt = '; '.join(
                f"{(c.get('name_tr') or c['name']) if lang == 'TR' else c['name']}: {c['mobility']}"
                for c in _known
            )
        else:
            _soil_txt = ('Toprak adsorpsiyon verisi mevcut değil.' if lang=='TR'
                         else 'No soil adsorption data available.')
    else:
        _soil_txt = na

    # log Kow'dan da değerlendirme yapılabilir (phys_props)
    _lkow = phys.get('log_kow')
    if _soil_txt == na and _lkow is not None:
        try:
            _lk = float(_lkow)
            if _lk < 1:
                _soil_txt = ('Yüksek hareketlilik beklenir (log Kow < 1)' if lang=='TR'
                             else 'High mobility expected (log Kow < 1)')
            elif _lk < 3:
                _soil_txt = (f'Orta hareketlilik (log Kow={_lk})' if lang=='TR'
                             else f'Moderate mobility (log Kow={_lk})')
            else:
                _soil_txt = (f'Düşük hareketlilik, toprakta adsorpsiyon beklenir (log Kow={_lk})' if lang=='TR'
                             else f'Low mobility, soil adsorption expected (log Kow={_lk})')
        except (ValueError, TypeError):
            pass

    eco_rows = [
        [sub_title(lang,'12.1'), sds12.get('12.1', na)],
        [sub_title(lang,'12.2'), bio.get('assessment') or sds12.get('12.2', na)],
        [sub_title(lang,'12.3'), sds12.get('12.3', na)],
        [sub_title(lang,'12.4'), _soil_txt],
        [sub_title(lang,'12.5'), pbt_summary],
        [sub_title(lang,'12.6'), (lambda v:
            ('Endokrin bozucu özellik tespit edilmemiştir.' if lang=='TR' else 'No endocrine disrupting properties identified.')
            if 'ECHA SVHC' in v or 'kontrol edin' in v else v
        )(sds12.get('12.6', na))],
    ]
    story.append(data_table(eco_rows, [65*mm, 115*mm], styles, header=False))

    # M Faktör tablosu — CLP Annex I Tablo 4.1.3
    # Zorunluluk: Bileşende H400 (Aquatic Acute 1) veya H410 (Aquatic Chronic 1) varsa
    # tablo KESİNLİKLE gösterilmeli — karışım sınıflandırmasından bağımsız.
    # CLP §4.1.3.5.5: M-faktörü bilinmiyorsa M=1 varsayılır ve bu durum tabloda belirtilir.
    _eco_aq = eco_sections.aquatic if hasattr(eco_sections,'aquatic') else (
              eco_sections.get('aquatic') if isinstance(eco_sections,dict) else None)
    _mf_details = (getattr(_eco_aq,'component_details',None) or []) if _eco_aq else []

    # Fallback: eco_result.aquatic yoksa veya component_details boşsa
    # bileşen listesinden H400/H410 sınıflı maddeleri topla
    if not _mf_details:
        _DATA_ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'data'))

        def _lookup_m_factors(cas: str) -> dict:
            """CAS numarasıyla annex6 → cl sırasıyla m_factors ara. Bulunamazsa {} döner."""
            if not cas:
                return {}
            _prefix = cas[:2]  # '55965-84-9' → '55'
            for _subdir in ('annex6', 'cl'):
                _fp = os.path.join(_DATA_ROOT, _subdir, _prefix, f'{cas}.json')
                try:
                    with open(_fp, encoding='utf-8') as _f:
                        _raw = _json.load(_f)
                        # m_factors, classification altında veya üst seviyede olabilir
                        _mf = (_raw.get('classification') or {}).get('m_factors') or _raw.get('m_factors')
                        if _mf:
                            return _mf
                except (FileNotFoundError, OSError, _json.JSONDecodeError, KeyError):
                    pass
            return {}

        _M_FACTOR_H_CODES   = {'H400', 'H401', 'H410'}   # H411 dahil değil — Kronik 2'nin M-faktörü yok
        _M_FACTOR_CLASSES   = {'Aquatic Acute 1', 'Aquatic Chronic 1'}
        for _comp in sds_data.get('components', []):
            _comp_hazards   = _comp.get('hazards', [])
            _comp_h_codes   = {(h.get('h_code') or '').strip() for h in _comp_hazards}
            _comp_h_classes = {(h.get('h_class') or '').strip() for h in _comp_hazards}
            _has_aa1 = bool(_comp_h_codes & {'H400','H401'} or _comp_h_classes & {'Aquatic Acute 1'})
            # H411 (Suk. Kron. 2) M-faktör gerektirmez — sadece H410 (Suk. Kron. 1) tabloya girer
            _has_ac1 = bool(_comp_h_codes & {'H410'} or _comp_h_classes & {'Aquatic Chronic 1'})
            if _has_aa1 or _has_ac1:
                _cas_key = str(_comp.get('cas_no') or _comp.get('cas') or '').strip()
                # Bileşen objesinde m_factors yoksa annex6/cl DB'den doğrudan oku
                _mf_raw  = _comp.get('m_factors') or _lookup_m_factors(_cas_key)
                _m_a    = float(_mf_raw.get('acute',   1) or 1) if _mf_raw else 1
                _m_c    = float(_mf_raw.get('chronic', _m_a) or _m_a) if _mf_raw else _m_a
                _mf_details.append({
                    'cas':      _cas_key,
                    'name':     _comp.get('name', ''),
                    'name_tr':  _comp.get('name_tr', _comp.get('name', '')),
                    'm_acute':   _m_a,
                    'm_chronic': _m_c,
                    'h_class':  'Aquatic Acute 1' if _has_aa1 else 'Aquatic Chronic 1',
                    'h_code':   'H400' if _has_aa1 else 'H410',
                    '_m_default': not bool(_mf_raw),  # True → DB'de de bulunamadı, M=1 gerçekten varsayılan
                })

    _M_FACTOR_CLASSES = {'Aquatic Acute 1', 'Aquatic Chronic 1'}
    _aquatic_comps = [d for d in _mf_details if d.get('h_class') in _M_FACTOR_CLASSES]
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
            _any_m_default = False
            for _d in _aquatic_comps:
                _mf_name = (_d.get('name_tr','') if lang=='TR' else '') or _d.get('name','')
                _m_a_val = _d.get('m_acute',   1)
                _m_c_val = _d.get('m_chronic',  1)
                # M=1 varsayıldıysa değerin yanına * işareti ekle
                _m_a_str = f"{_m_a_val}*" if _d.get('_m_default') else str(_m_a_val)
                _m_c_str = f"{_m_c_val}*" if _d.get('_m_default') else str(_m_c_val)
                if _d.get('_m_default'):
                    _any_m_default = True
                _mf_rows.append([
                    _d.get('cas',''),
                    _mf_name,
                    translate_hclass(correct_hclass(_d.get('h_code',''), _d.get('h_class','')), lang),
                    _m_a_str,
                    _m_c_str,
                ])
            story.append(data_table(_mf_rows,
                [24*mm, 52*mm, 42*mm, 22*mm, 22*mm], styles))
            # M=1 varsayılan bileşen varsa dipnot ekle
            if _any_m_default:
                _mf_note = ('* M-faktörü belirlenmemiş; CLP Ek-I §4.1.3.5.5 uyarınca M=1 varsayıldı. '
                            'Tedarikçiden EC50/LC50 verisi alınarak doğrulanmalıdır.'
                            if lang == 'TR' else
                            '* M-factor not determined; M=1 assumed per CLP Annex I §4.1.3.5.5. '
                            'Verify with EC50/LC50 data from supplier.')
                story.append(Paragraph(_mf_note, styles['small']))
            # Kaynaktan gelen M değerleri varsa kaynak dipnotu
            if any(not _d.get('_m_default') for _d in _aquatic_comps):
                _mf_src = ('M-faktörü değerleri SEA Ek-6 (TR) harmonik sınıflandırması '
                           've/veya ECHA CLP Ek-VI (ATP22) esas alınarak belirlenmiştir.'
                           if lang == 'TR' else
                           'M-factor values are based on TR SEA Annex VI harmonised '
                           'classification and/or ECHA CLP Annex VI (ATP22).')
                story.append(Paragraph(_mf_src, styles['small']))
            story.append(Spacer(1, 3))

    # ─────────────────────────────────────────────────────────────────────────
    # BÖLÜM 13 — Bertaraf (KKDİK Ek-2 §13.1)
    # ─────────────────────────────────────────────────────────────────────────
    story += section_block(section_title(lang, 13), styles)
    story += sub_block(f"13.1 {sub_title(lang,'13.1')}", styles)

    _disp = get_disposal_content(h_codes, lang)

    # 13.1a — Ürün bertaraf yöntemleri (dinamik bullet listesi)
    story += bullet_list(_disp['product_bullets'], styles)

    # 13.1b — Kanalizasyon yasağı (sucul tehlike H kodları varsa)
    if _disp.get('drain_note'):
        story.append(Paragraph(_disp['drain_note'], styles['body']))

    # 13.1c — Kontamine ambalaj yönetimi (her zaman — KKDİK Ek-2 §13.1 zorunlu)
    story.append(Spacer(1, 3))
    story.append(Paragraph(_disp['packaging_text'], styles['body']))

    # ─────────────────────────────────────────────────────────────────────────
    # BÖLÜM 14 — Taşımacılık
    # ─────────────────────────────────────────────────────────────────────────
    story += section_block(section_title(lang, 14), styles)
    transport = sds_data.get('transport', {})

    # Otomatik UN tespiti — kullanıcı vermemişse H kodlarından
    _phys_state = (phys.get('state') or phys.get('physical_state') or 'liquid').lower()
    # not_regulated bayrağı — tehlikeli madde değil, tablo yerine açıklama notu yaz
    _not_regulated = transport.get('not_regulated', False) and not transport.get('un_no')
    _not_reg_text  = (transport.get('note') or '').strip() or (
        'Bu ürün ADR/RID, IMDG ve IATA-DGR kapsamında tehlikeli madde olarak sınıflandırılmamıştır.'
        if lang == 'TR' else
        'This product is not classified as dangerous goods under ADR/RID, IMDG or IATA-DGR.'
    )
    auto_t = _auto_un(h_codes, state=_phys_state) if not transport.get('un_no') else None
    t_src = transport if transport.get('un_no') else (auto_t or {})
    un_no = t_src.get('un_no', '—')
    ship_name = t_src.get('shipping_name', na)
    # ADR 3.1.2.8 — B.N.O. girişlerinde teknik isim zorunlu
    if 'B.N.O.' in ship_name and components:
        tech = _nos_technical_names(un_no, components, lang)
        if tech:
            ship_name = f"{ship_name} ({tech})"
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
        'H400','H401','H410','H411',  # Sucul — ADR 2.2.9.1.10: sadece Akut 1, Kron. 1, Kron. 2
        'H420',                       # Ozon
        # H412 (Kron. 3) ve H413 (Kron. 4) ADR 2.2.9.1.10 kapsamı dışı — kaldırıldı
    }
    is_env_hazard = any(h in h_codes for h in env_h_codes)

    
    _t_env = transport.get('env_hazard')
    # env_hazard bool True olarak gelebilir (main.py: env_mark) — Türkçeleştir
    if _t_env and not isinstance(_t_env, bool):
        env_haz = _t_env   # zaten string ise direkt kullan
    elif _t_env or is_env_hazard:
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

    # ── Mod bazlı sınıf bilgisi (road/sea/air ayrı) ──────────────────────────
    _road = t_src.get('road') or {}
    _sea  = t_src.get('sea')  or {}
    _air  = t_src.get('air')  or {}
    # Her mod için tehlike sınıfı — yoksa ana sınıf kullan
    _cls_road = _road.get('class') or haz_class
    _cls_sea  = _sea.get('class')  or haz_class
    _cls_air  = _air.get('class')  or haz_class
    # Sınıf etiket (sayı + yan tehlike)
    def _cls_str(cls_val, sub):
        if not cls_val or cls_val == '—': return '—'
        lbl = CLASS_LABELS.get(str(cls_val), str(cls_val))
        return f"Sınıf {cls_val} — {lbl}" if lang == 'TR' else f"Class {cls_val} — {CLASS_LABELS.get(str(cls_val), str(cls_val))}"
    _road_lbl = f"Sınıf {_cls_road}" + (f" ({sub_class})" if sub_class and _cls_road != '—' else '') if lang == 'TR' else f"Class {_cls_road}" + (f" ({sub_class})" if sub_class and _cls_road != '—' else '')
    _sea_lbl  = f"Sınıf {_cls_sea}"  if _cls_sea  != '—' else '—'
    _air_lbl  = f"Sınıf {_cls_air}"  if _cls_air  != '—' else '—'
    if _cls_road == '—': _road_lbl = na
    if _cls_sea  == '—': _sea_lbl  = na
    if _cls_air  == '—': _air_lbl  = na

    # Marine Pollutant (IMDG) — çevre H kodları varsa
    _marine_lbl = 'Evet — Deniz Kirletici (Marine Pollutant)' if lang == 'TR' else 'Yes — Marine Pollutant'
    _marine_no  = term(lang, 'not_applicable')
    # env_mark: main.py Step 6'da IMDG §2.10.3 bileşen bazlı hesap ile set edilir.
    # Eski transport datası gelirse is_env_hazard'a fallback.
    _sea_env_mark = _sea.get('env_mark')
    _imdg_env = _marine_lbl if (_sea_env_mark if _sea_env_mark is not None else is_env_hazard) else _marine_no

    # 14.6 — Kullanıcı için özel önlemler (standart metin)
    _sec14_6 = 'Bkz. Bölüm 6 (Kaza önleme), 7 (Elleçleme/depolama) ve 8 (KKD).' if lang == 'TR' \
               else 'See Section 6 (accidental release), 7 (handling/storage) and 8 (PPE).'

    transport_rows = [
        [sub_title(lang,'14.1') + ' (UN No)',   un_no + auto_note],
        [sub_title(lang,'14.2'),                 ship_name],
        # 14.3 — Her mod için ayrı satır
        [('14.3 ' + sub_title(lang,'14.3') + '\n  ↳ Karayolu / Demiryolu (ADR/RID)'
          if lang == 'TR' else
          '14.3 ' + sub_title(lang,'14.3') + '\n  ↳ Road / Rail (ADR/RID)'),
         _road_lbl],
        ['  ↳ Denizyolu (IMDG)' if lang == 'TR' else '  ↳ Sea (IMDG)',  _sea_lbl],
        ['  ↳ Havayolu (IATA)'  if lang == 'TR' else '  ↳ Air (IATA)',  _air_lbl],
        [sub_title(lang,'14.4'),                 pack_grp],
        [sub_title(lang,'14.5'),                 env_haz],
        ['  ↳ Deniz Kirletici (IMDG)' if lang == 'TR' else '  ↳ Marine Pollutant (IMDG)', _imdg_env],
        [('14.6 Kullanıcı için özel önlemler' if lang == 'TR'
          else '14.6 Special precautions for user'),  _sec14_6],
        # ADR'ye özgü teknik bilgiler
        ['— Sınıflandırma Kodu (ADR)' if lang == 'TR' else '— Classification Code (ADR)', cl_code],
        ['— Kemler Kodu / Tehlike No'  if lang == 'TR' else '— Hazard ID No (Kemler)',     kemler],
        ['— Tünel Kısıtlama Kodu'      if lang == 'TR' else '— Tunnel Restriction Code',   tunnel],
    ]
    # ADR 5.2.1.8 — ÇTM satırını koşullu ekle (is_env_hazard varsa)
    if is_env_hazard:
        _ctm_label = '— ADR Çevresel İşaret (ÇTM)' if lang == 'TR' else '— ADR Environmental Mark'
        _ctm_value = (
            'Zorunlu — ADR 5.2.1.8: ambalaj ve taşıma belgelerinde '
            'Çevresel Tehlikeli Madde (balık+ağaç) işareti gereklidir.'
            if lang == 'TR' else
            'Required — ADR 5.2.1.8: Environmental Hazard mark (fish+tree) '
            'must appear on packages and transport documents.'
        )
        transport_rows.append([_ctm_label, _ctm_value])
    if _not_regulated:
        story.append(Paragraph(_not_reg_text, styles['body']))
        story.append(Spacer(1, 4))
    else:
        story.append(data_table(transport_rows, [75*mm, 105*mm], styles, header=False))
    if not _not_regulated and auto_t:
        story.append(Paragraph(
            '* Taşımacılık sınıflandırması CLP tehlike sınıfına göre otomatik belirlenmiştir. Sevkiyat öncesi yetkili taşımacılık uzmanına danışınız.' if lang=='TR'
            else '* Transport classification determined automatically from CLP hazard class. Consult a transport specialist before shipment.',
            styles['small']
        ))

    # ── Deniz Kirletici hesap gerekçesi (IMDG §2.10.3) ───────────────────────
    _imdg_mp_h = {'H400', 'H410', 'H411'}
    _mp_comps = []
    for _c in sds_data.get('components', []):
        _c_h_codes = {(h.get('h_code') or '').strip() for h in (_c.get('hazards') or [])}
        _c_mp_h = _c_h_codes & _imdg_mp_h
        if not _c_mp_h:
            continue
        _conc = float(_c.get('concMax') or _c.get('conc') or _c.get('concentration') or 0)
        _mf_raw = _c.get('m_factors') or {}
        _m_a = float(_mf_raw.get('acute', 1)) if _mf_raw else 1.0
        _name = (_c.get('name_tr', '') if lang == 'TR' else '') or _c.get('name', '')
        _cas  = _c.get('cas_no', _c.get('cas', ''))
        _dominant_h = 'H400' if ('H400' in _c_mp_h or 'H410' in _c_mp_h) else 'H411'
        _mp_comps.append({
            'cas':    _cas,
            'name':   _name or _cas,
            'conc':   _conc,
            'm':      _m_a,
            'h_code': _dominant_h,
        })

    if _mp_comps:
        _mp_title = ('Deniz Kirletici Hesap Gerekçesi (IMDG §2.10.3)'
                     if lang == 'TR' else
                     'Marine Pollutant Calculation (IMDG §2.10.3)')
        story.append(Spacer(1, 4))
        story.append(Paragraph(f"<b>{_mp_title}:</b>", styles['body_bold']))

        _col1 = 'CAS No'
        _col2 = 'Madde'          if lang == 'TR' else 'Substance'
        _col3 = 'C (%)'
        _col4 = 'M'
        _col5 = 'C×M'
        _col6 = 'Eşik (%)'       if lang == 'TR' else 'Threshold (%)'
        _mp_rows = [[_col1, _col2, _col3, _col4, _col5, _col6]]

        _sum_acute  = 0.0
        _sum_h411   = 0.0
        for _mp in _mp_comps:
            _is_acute_mp = _mp['h_code'] in {'H400', 'H410'}
            _thr = '≥ 0.1' if _is_acute_mp else '≥ 1.0'
            if _is_acute_mp:
                # Test 1: akut M-faktörlü — Σ(C×M) ≥ 0.1
                _cxm      = _mp['conc'] * _mp['m']
                _m_str    = f"{int(_mp['m'])}"
                _cxm_str  = f"{_cxm:.2f}"
                _sum_acute += _cxm
            else:
                # Test 2: H411 kronik bileşen — Σ(C) ≥ 1.0, M-faktör uygulanmaz
                _cxm     = _mp['conc']   # katkı = C (M-faktörsüz)
                _m_str   = '—'
                _cxm_str = f"{_cxm:.1f}*"  # * = Test 2, M-faktör yok
                _sum_h411 += _mp['conc']
            _mp_rows.append([
                _mp['cas'],
                Paragraph(_mp['name'], styles['small']),
                f"{_mp['conc']:.1f}",
                _m_str,
                _cxm_str,
                _thr,
            ])

        story.append(data_table(_mp_rows, [24*mm, 50*mm, 18*mm, 12*mm, 18*mm, 22*mm], styles))

        _is_mp = (_sum_acute >= 0.1) or (_sum_h411 >= 1.0)
        if _sum_acute > 0 and _sum_h411 > 0:
            _sum_txt = (f"Σ(C×M) = {_sum_acute:.2f}% (H400/H410) | "
                        f"Σ(C) = {_sum_h411:.2f}% (H411)")
        elif _sum_acute > 0:
            _sum_txt = f"Σ(C×M) = {_sum_acute:.2f}%"
        else:
            _sum_txt = f"Σ(C) = {_sum_h411:.2f}%"

        if _is_mp:
            _verdict = ('Deniz Kirletici: Evet — IMDG §2.10.3 eşiği aşıldı.'
                        if lang == 'TR' else
                        'Marine Pollutant: Yes — IMDG §2.10.3 threshold exceeded.')
        else:
            _verdict = ('Deniz Kirletici: Hayır — IMDG §2.10.3 eşiği aşılmadı.'
                        if lang == 'TR' else
                        'Marine Pollutant: No — IMDG §2.10.3 threshold not exceeded.')
        story.append(Paragraph(f"{_sum_txt} → {_verdict}", styles['small']))

        # H411 bileşeni varsa Test 2 dipnotu ekle
        if any(_mp['h_code'] == 'H411' for _mp in _mp_comps):
            _t2_note = (
                '* H411 (Sucul Kronik 2): M-faktör uygulanmaz. '
                'IMDG §2.10.3 Test 2 kapsamında konsantrasyon değeri doğrudan toplanır — eşik: Σ(C) ≥ %1,0.'
                if lang == 'TR' else
                '* H411 (Aquatic Chronic 2): No M-factor applies. '
                'IMDG §2.10.3 Test 2: concentration summed directly — threshold: Σ(C) ≥ 1.0%.'
            )
            story.append(Paragraph(_t2_note, styles['small']))

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

    # ── Kullanım tipine göre ek mevzuat notu ─────────────────────────────────
    if _usage_val == 'consumer' and lang == 'TR':
        story.append(Spacer(1, 4))
        story.append(Paragraph(
            '• Bu ürün tüketici kullanımına yönelik olup 7223 sayılı Ürün Güvenliği ve '
            'Teknik Düzenlemeler Kanunu kapsamında değerlendirilir. '
            'Ürün güvenliği gereklilikleri bakımından Ticaret Bakanlığı denetimine tabidir.',
            styles['body']
        ))
    elif _usage_val == 'consumer' and not is_us:
        story.append(Spacer(1, 4))
        story.append(Paragraph(
            '• This product is intended for consumer use and may be subject to applicable '
            'consumer product safety legislation in the country of sale.',
            styles['body']
        ))

    # ── SVHC Kontrolü — REACH Madde 33 / KKDİK Madde 35 ────────────────────
    try:
        from app.services.svhc_service import check_svhc_mixture, svhc_section15_text
        svhc_result = check_svhc_mixture(components)
        svhc_lines = svhc_section15_text(svhc_result, lang=lang)
        story.append(Spacer(1, 4))
        for line in svhc_lines:
            if line.startswith('⚠') or line.startswith('  •'):
                st = styles.get('body_bold', styles['body']) if line.startswith('⚠') else styles['body']
                color = '#cc0000' if line.startswith('⚠') else '#333333'
                story.append(Paragraph(
                    f'<font color="{color}">{line}</font>', st
                ))
            else:
                story.append(Paragraph(line, styles['small']))
    except Exception:
        pass

    story += sub_block(f"15.2 {sub_title(lang,'15.2') if '15.2' in L.get('sub',{}) else 'Kimyasal güvenlik değerlendirmesi'}", styles)

    # CSA zorunluluğu kontrolü — KKDİK Madde 14: yıllık ≥1 ton üretim/ithalat +
    # SVHC/kanserojen/mutajen/üreme toksik ise KGA (Kimyasal Güvenlik Değerlendirmesi) zorunlu
    _cmr_h = {'H340','H341','H350','H350i','H351',
              'H360','H360D','H360F','H360FD',
              'H361','H361d','H361f','H361fd','H361D','H361F','H361FD',
              'H334'}
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
            hc_base = hc.split('(')[0].strip()  # organ notasyonunu at: "H370 (organ)" → "H370"
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
                if hc_base in ('H370', 'H371', 'H372', 'H373') and hc_base in _stot_organ_map:
                    stmt = get_stot_stmt(hc_base, lang, _stot_organ_map[hc_base])
                else:
                    stmt = get_h_stmt(hc_base, lang)
            if stmt and stmt != hc_base:
                story.append(Paragraph(f'• <b>{hc_base}:</b> {stmt}', styles['small']))
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
        f"SDS — Safety Data Sheet | "
        + ("KKE — Kişisel Koruyucu Ekipman | KKD — Kişisel Koruyucu Donanım" if lang == 'TR'
           else "PPE — Personal Protective Equipment"),
        styles['small']
    ))

    # Fiziksel tehlike metodoloji notu (CLP §1.6.3.2)
    _phys_no_test = [
        w for w in clp.get('warnings', [])
        if isinstance(w, dict) and w.get('code', '').startswith('PHYS_NO_TEST_BASIS')
    ]
    if _phys_no_test:
        _affected_h = ', '.join(sorted({w['h_code'] for w in _phys_no_test}))
        _note_tr = (
            f"Not: {_affected_h} fiziksel tehlike sınıflandırması bileşen geçişkenliğine dayanır. "
            f"CLP Ek-I §1.6.3.2 gereği fiziksel tehlikeler için resmi köprüleme ilkesi tanımlı "
            f"değildir — karışımın test edilmesi önerilir."
        )
        _note_en = (
            f"Note: {_affected_h} physical hazard classification is based on component pass-through. "
            f"Per CLP Annex I §1.6.3.2, no formal bridging principle is defined for physical hazards "
            f"— testing of the mixture is recommended."
        )
        story.append(Spacer(1, 4))
        story.append(Paragraph(
            _note_tr if lang == 'TR' else _note_en,
            styles['small']
        ))

    # Aerosol parlama noktası fallback uyarısı
    _aerosol_fp_warn = any(
        isinstance(w, dict) and w.get('code') == 'AEROSOL_FP_FALLBACK'
        for w in clp.get('warnings', [])
    )
    if _aerosol_fp_warn:
        _aw_tr = (
            "Not: Aerosol yanıcılık sınıflandırması (H222/H223) onaylı aerosol testi veya "
            "beyan edilen yanıcı içerik yüzdesi yerine bileşen parlama noktaları üzerinden "
            "tahmin edilmiştir. CLP Ek-I §2.3 uyarınca test ile doğrulama önerilir."
        )
        _aw_en = (
            "Note: Aerosol flammability classification (H222/H223) is estimated from component "
            "flash points rather than an approved aerosol test or declared flammable content "
            "percentage. Verification by testing per CLP Annex I §2.3 is recommended."
        )
        story.append(Spacer(1, 4))
        story.append(Paragraph(_aw_tr if lang == 'TR' else _aw_en, styles['small']))

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
