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
    PageBreak, HRFlowable, KeepTogether, CondPageBreak
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import re as _re
from io import BytesIO
from datetime import datetime
from typing import Dict, List, Optional

# ─── SAYFA DÜZENİ SABİTLERİ ─────────────────────────────────────────────────
PAGE_W   = 180 * mm   # A4 kullanılabilir genişlik (210 - 15 - 15)
COL_L    = 55  * mm   # Sol etiket sütunu

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
from app.services.sds_reg_sections import (
    first_aid as reg_first_aid, accidental_release as reg_accidental_release, hygiene as reg_hygiene,
    handling_p as reg_handling_p, storage_p as reg_storage_p,
    _select_inhal as reg_select_inhal, _p as reg_p_text,
)
from app.services.sds_sentence_service import (
    adapt_for_form, adapt_list_for_form,
    generate_section3, generate_section, generate_section_42
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

    # H370/H371/H372/H373 — bileşen tehlike kodundaki parentez bilgisinden organ (+ yol) çıkar
    # Örnek: 'H370(sinir sistemi; inhalasyon)' → organ_map['H370'] = 'sinir sistemi; inhalasyon'
    for comp in components:
        for haz in (comp.get('hazards') or []):
            raw = (haz.get('h_code') or '').strip()
            h_base = raw.replace('*', '').strip()[:4]
            if h_base in ('H370', 'H371', 'H372', 'H373') and h_base not in organ_map:
                m = _re.search(r'\(([^)]+)\)', raw)
                if m:
                    organ_map[h_base] = m.group(1).strip()
    return organ_map


def get_stot_stmt(h_code: str, lang: str, organ_en: str) -> str:
    """H370/H371/H372/H373 için hedef organ + maruziyet yolu içeren H ifadesi üret.
    organ_en formatı: 'nervous system' veya 'nervous system; inhalation'
    """
    from app.services.stot_engine import ORGAN_TR
    _ROUTE_TR = {'inhalation': 'inhalasyon', 'dermal': 'deri teması', 'oral': 'ağız yolu',
                 'inhalasyon': 'inhalasyon', 'deri teması': 'deri teması', 'ağız yolu': 'ağız yolu'}
    _ROUTE_EN = {'inhalasyon': 'inhalation', 'deri teması': 'dermal contact', 'ağız yolu': 'oral'}
    # organ_en "sinir sistemi; inhalasyon" veya "nervous system; inhalation" formatında gelebilir
    parts = [p.strip() for p in organ_en.split(';')]
    organ_raw = parts[0] if parts else organ_en
    route_raw = parts[1] if len(parts) > 1 else ''
    if lang == 'TR':
        organ = ORGAN_TR.get(organ_raw.lower(), organ_raw)
        route = _ROUTE_TR.get(route_raw.lower(), route_raw) if route_raw else ''
        route_str = f' {route} yoluyla' if route else ''
        if h_code == 'H370':
            return f'Organlara ({organ}){route_str} hasar verir.'
        elif h_code == 'H371':
            return f'Organlara ({organ}){route_str} hasar verebilir.'
        elif h_code == 'H372':
            return f'Uzun süreli veya tekrarlı{route_str} maruz kalma sonucu organlarda ({organ}) hasara yol açar.'
        return f'Uzun süreli veya tekrarlanan{route_str} maruziyetle organlarda ({organ}) hasar verebilir.'
    else:
        organ = organ_raw
        route = _ROUTE_EN.get(route_raw.lower(), route_raw) if route_raw else ''
        route_str = f' via {route}' if route else ''
        if h_code == 'H370':
            return f'Causes damage to {organ}{route_str} following single exposure.'
        elif h_code == 'H371':
            return f'May cause damage to {organ}{route_str} following single exposure.'
        elif h_code == 'H372':
            return f'Causes damage to {organ} through prolonged or repeated{route_str} exposure.'
        return f'May cause damage to {organ} through prolonged or repeated{route_str} exposure.'


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
    # Gaz B.B.B. girişleri (ADR 3.3.1 ÖH 274 — teknik ad zorunlu). Basınçlı gaz (H280/H281)
    # tüm gaz bileşenlerinde ortak olduğundan grup olarak en yüksek konsantrasyonlu iki gaz seçilir.
    'UN1956': [{'H280', 'H281'}, {'H280', 'H281'}],
    'UN3163': [{'H280', 'H281'}, {'H280', 'H281'}],
    'UN3158': [{'H280', 'H281'}, {'H280', 'H281'}],
    'UN3161': [{'H220', 'H221'}],
    'UN3312': [{'H220', 'H221'}],
    'UN3157': [{'H270'}],
    'UN3311': [{'H270'}],
    'UN1953': [{'H330', 'H331'}, {'H220', 'H221'}],
    'UN3160': [{'H330', 'H331'}, {'H220', 'H221'}],
    'UN1955': [{'H330', 'H331'}],
    'UN3162': [{'H330', 'H331'}],
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
    # Aşındırıcı B.B.B. girişleri (ÖH 274) — tehlikeye en çok katkı veren en fazla iki aşındırıcı bileşen
    'UN1760': [{'H314'}, {'H314'}],
    'UN1759': [{'H314'}, {'H314'}],
    'UN3264': [{'H314'}, {'H314'}],
    'UN3265': [{'H314'}, {'H314'}],
    'UN3266': [{'H314'}, {'H314'}],
    'UN3267': [{'H314'}, {'H314'}],
    'UN3260': [{'H314'}, {'H314'}],
    'UN3261': [{'H314'}, {'H314'}],
    'UN3262': [{'H314'}, {'H314'}],
    'UN3263': [{'H314'}, {'H314'}],
    'UN3244': [{'H314'}, {'H314'}],
    # Zehirli sıvı (tekil)
    'UN2810': [{'H300','H301','H310','H311','H330','H331'}],
    # Çevre için tehlikeli
    'UN3082': [{'H400','H410','H411'}],
    'UN3077': [{'H400','H410','H411'}],
}


_EK6_CACHE: dict | None = None

# Ek-6 dışı yaygın maddelerin Türkçe adları — tek kaynak substance_lookup
from app.services.substance_lookup import COMMON_NAMES_TR as _GAS_NAMES_TR


def _ek6_own_name(cas: str, raw: str) -> str:
    """Ek-6'da birden fazla CAS'ı kapsayan girişlerde ("o-ksilen [1]; … ksilen [4]") bileşenin
    kendi CAS'ına karşılık gelen adı döndürür; [n] sırası girişin CAS listesindeki sıradır."""
    global _EK6_CACHE
    if not cas or '[' not in (raw or ''):
        return ''
    if _EK6_CACHE is None:
        try:
            import json as _json
            _p = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'sea_ek6_tr.json')
            with open(_p, encoding='utf-8') as _f:
                _EK6_CACHE = _json.load(_f)
        except Exception:
            _EK6_CACHE = {}
    ent = _EK6_CACHE.get(cas) or {}
    if '_alias' in ent:
        ent = _EK6_CACHE.get(ent['_alias']) or {}
    cas_list = [ent.get('cas')] + list(ent.get('synonyms') or [])
    if cas not in cas_list:
        return ''
    tag = f'[{cas_list.index(cas) + 1}]'
    for seg in _re.split(r'[;\n]', raw):
        if tag in seg:
            return seg
    return ''


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
            _cas_c = str(c.get('cas_no') or c.get('cas') or '').strip()
            raw = ((c.get('name_tr', '') or _GAS_NAMES_TR.get(_cas_c, '')) if lang == 'TR' else '') or \
                  c.get('name', '') or c.get('cas_no', '')
            # ADR teknik isim: sadece birincil ad — çoklu izomer/eşanlamlı
            # listelerinden ("heptan; n-heptan [1]\n2,4-dimetilpentan [2]…")
            # yalnızca ilk ismi al; satır ve noktalı virgül ayıraçlarını
            # temizle; "[1]" gibi numara eklerini kaldır.
            primary = _ek6_own_name(c.get('cas_no') or c.get('cas') or '', raw) or \
                raw.split('\n')[0].split(';')[0]
            primary = _re.sub(r'\s*\[\d+\]', '', primary).strip()
            name = primary
            if not name or name in seen:
                continue
            conc = float(c.get('concentration', 0) or c.get('conc', 0) or 0)
            # ADR 3.1.2.8.1.3: tehlikeye belirgin katkı — ilk ad seçildikten sonra %1'in altındakiler eklenmez
            if selected and conc < 1.0:
                continue
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


# 7.2'de uyumsuz madde satırının yer tutucusu — liste Bölüm 10.5'te hesaplanınca doldurulur
_INCOMPAT_SLOT = '@@UYUMSUZ_MADDELER@@'


def _delayed_effects_text(h_set: set, tr: bool) -> str:
    """Hemen/gecikmeli ve kronik etkiler — sınıflandırmadaki H kodlarından (KKDİK Ek-2 A 4.1.2(a), 11.1.7)."""
    imm = sorted(h_set & {'H300', 'H301', 'H302', 'H310', 'H311', 'H312', 'H330', 'H331', 'H332',
                          'H314', 'H315', 'H318', 'H319', 'H335', 'H336', 'H370', 'H371', 'H304'})
    chron = sorted(h for h in h_set if h[:4] in {'H340', 'H341', 'H350', 'H351', 'H360', 'H361', 'H362',
                                                  'H372', 'H373'})
    sens = sorted(h_set & {'H317', 'H334'})
    out = []
    if imm:
        out.append(('Kısa süreli maruz kalmada etkiler genellikle hemen ortaya çıkar (' + ', '.join(imm) + ').')
                   if tr else ('Effects of short-term exposure generally appear immediately (' + ', '.join(imm) + ').'))
    if sens:
        out.append(('Hassaslaştırıcı etki (' + ', '.join(sens) + ') tekrarlanan temasla gecikmeli (alerjik) '
                    'reaksiyon olarak ortaya çıkabilir.') if tr else
                   ('Sensitising effects (' + ', '.join(sens) + ') may appear as delayed (allergic) reactions '
                    'after repeated contact.'))
    if chron:
        out.append(('Uzun süreli/tekrarlı maruz kalmada kronik etkiler: ' + ', '.join(chron) + '.') if tr
                   else ('Chronic effects on long-term/repeated exposure: ' + ', '.join(chron) + '.'))
    elif not out:
        # Sağlık sınıflandırması yok: Ek-2 A 11.1.7 etkilerin "beklenip beklenmediğini" ister — kısa
        # (ani/gecikmeli) ve uzun süreli maruz kalma birlikte belirtilir
        out.append('Karışım sağlık zararları yönünden sınıflandırılmamıştır; mevcut bilgilere göre kısa veya uzun '
                   'süreli maruz kalmada sınıflandırma gerektiren ani, gecikmeli ya da kronik etki beklenmemektedir.'
                   if tr else
                   'The mixture is not classified for health hazards; based on available data, no immediate, delayed '
                   'or chronic effects requiring classification are expected from short- or long-term exposure.')
    else:
        out.append('Uzun süreli/tekrarlı maruz kalmaya bağlı kronik etki sınıflandırması yoktur.' if tr
                   else 'No classification for chronic effects of long-term/repeated exposure.')
    return ' '.join(out)


def _unclassified_health_text(components, tr: bool, names: dict = None) -> str:
    """Karışım sağlık yönünden sınıflandırılmamışsa 4.2 / 11.1.6 metni (KKDİK Ek-2 A 4.2, 11.1.6).
    Belirti uydurulmaz; sağlık sınıfı olan bileşen varsa eşik altında kaldığı belirtilir.
    names: CAS → Bölüm 3'te basılan ad (gizlilik talebinde genel ad)."""
    parts = []
    for c in components or []:
        hs = sorted({str(x.get('h_code') or '').replace('*', '').strip()[:4] for x in (c.get('hazards') or [])
                     if str(x.get('h_code') or '').strip().startswith('H3')})
        cas = str(c.get('cas_no') or c.get('cas') or '').strip()
        if names is not None:
            nm = _re.sub(r'<[^>]+>', '', str(names.get(cas) or '')).strip()
        else:
            nm = (c.get('name_tr') if tr else '') or c.get('name') or cas
        if hs and nm:
            parts.append(f"{nm} ({', '.join(hs)})")
    txt = ('Karışım sağlık zararları yönünden sınıflandırılmamıştır; mevcut bilgilere göre bilinen önemli akut '
           'veya gecikmiş belirti ve etki yoktur.' if tr else
           'The mixture is not classified for health hazards; based on available data no significant acute or '
           'delayed symptoms and effects are known.')
    if parts:
        txt += ((' Bileşenlerden ' + ', '.join(parts) + ' sağlık zararı yönünden sınıflandırılmıştır; karışımda, '
                 'karışımın sınıflandırılmasına yol açmayan konsantrasyonda bulunmaktadır.') if tr else
                (' Components classified for health hazards (' + ', '.join(parts) + ') are present at '
                 'concentrations that do not lead to classification of the mixture.'))
    return txt


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
            from app.services.clp_service import signal_word_for as _swf
            clp['signal_word'] = _swf(clp['h_codes'])

    # Validator devre dışı
    _validation_issues = []
    disclosure = sds_data.get('disclosure_map', {})
    # Bölüm 3 konsantrasyon metinleri (sds_pipeline.section3_display — KKDİK Ek-2 A 3.2)
    _sec3_disp = sds_data.get('section3_display') or {}
    _sec3_ranged = any(v.get('kind') != 'exact' for v in _sec3_disp.values())
    # Bileşen adına göre de aynı metin (ATE ayrıntılarında CAS yoktur — kesin değer sızmasın)
    _sec3_by_name = {}
    # SEA Md.26 onaylı alternatif ad: gerçek ad/CAS hiçbir bölümde basılmaz
    _hidden_names, _hidden_cas = {}, set()
    for _c0 in components:
        _cas0 = str(_c0.get('cas_no') or _c0.get('cas') or '').strip()
        _d0 = _sec3_disp.get(_cas0)
        _nms0 = [_c0.get('name'), _c0.get('name_tr')] + list(_c0.get('_orig_names') or [])
        if _d0:
            for _n0 in _nms0:
                if _n0:
                    _sec3_by_name[str(_n0).strip().lower()] = _d0
        if _c0.get('disclosure') == 'hide':
            _hidden_cas.add(_cas0)
            for _n0 in _c0.get('_orig_names') or []:
                _hidden_names[str(_n0).strip()] = _c0.get('alt_name') or _c0.get('name')

    def _pub(name):
        """Yayımlanacak ad — alternatif ad onaylıysa gerçek ad yerine alternatif ad."""
        return _hidden_names.get(str(name or '').strip(), name)
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

    def _p_full(code: str) -> str:
        """P ifadesinin tam metni — tedarikçinin dolduracağı "…" kısımları tamamlanır
        (SEA Ek-4); P260/P261 fiziksel hale göre seçilir; P370+P378 söndürücü tehlikeye göre."""
        from app.services.p_code_service import P_COMBOS as _PC, P_TEXTS as _PT
        txt = (reg_p_text(code, lang) if get_p(lang, code) else None) or _PC.get(code) or _PT.get(code, code)
        txt = reg_select_inhal(txt, product.get('form') or 'liquid', lang)
        if code == 'P280':
            from app.services.sds_reg_sections import p280_text as _p280
            txt = _p280(list(clp.get('all_h_codes') or []) + list(clp.get('h_codes') or []), lang)
        if code == 'P370+P378':
            _hs = {str(h)[:4] for h in list(clp.get('h_codes') or []) + list(clp.get('all_h_codes') or [])}
            if _hs & {'H271', 'H272'}:
                txt = ('Yangın durumunda: Söndürmek için bol su kullanın.' if lang == 'TR'
                       else 'In case of fire: Use large amounts of water to extinguish.')
            elif _hs & {'H260', 'H261', 'H250'}:
                txt = ('Yangın durumunda: Söndürmek için kuru kum veya kuru kimyasal toz kullanın. Su kullanmayın.'
                       if lang == 'TR' else
                       'In case of fire: Use dry sand or dry chemical powder to extinguish. Do not use water.')
            else:
                txt = ('Yangın durumunda: Söndürmek için kuru kimyasal toz, karbondioksit veya alkole '
                       'dayanıklı köpük kullanın.' if lang == 'TR' else
                       'In case of fire: Use dry chemical powder, carbon dioxide or alcohol-resistant '
                       'foam to extinguish.')
        return txt
    product_name = product.get('name', 'Product Name' if is_us else 'Ürün Adı')
    _raw_date = rev.get('date', '')
    if not _raw_date or _raw_date.strip().lower() in ('bugün', 'bugun', 'today', ''):
        rev_date = datetime.now().strftime(L.get('date_format', '%d.%m.%Y'))
    else:
        rev_date = _raw_date
    rev_no = rev.get('no', '1')
    version = rev.get('version', '1.0')

    # Header/Footer için callback fonksiyonları
    # Sayfa başlığı kapaktaki ürün adıyla aynı yazılır (fazla boşluklar tekleşir)
    header_text = ' '.join(str(product_name).split()).upper()
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
        # Sayfa numarası "x / toplam" olarak _TotalPagesCanvas.save() içinde yazılır (KKDİK Ek-2 A 0.3.2)
        canvas.restoreState()

    from reportlab.pdfgen.canvas import Canvas as _RLCanvas

    class _TotalPagesCanvas(_RLCanvas):
        """Toplam sayfa sayısı ancak belge bitince bilinir: sayfalar biriktirilir, kayıtta numaralanır."""
        def __init__(self, *a, **kw):
            super().__init__(*a, **kw)
            self._saved_pages = []

        def showPage(self):
            self._saved_pages.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            total = len(self._saved_pages)
            for state in self._saved_pages:
                self.__dict__.update(state)
                self.setFont(_F_NORMAL, 6.5)
                self.setFillColor(HexColor('#64748b'))
                self.drawRightString(A4[0] - 15*mm, 10*mm,
                                     (f"Sayfa {self._pageNumber} / {total}" if lang == 'TR'
                                      else f"Page {self._pageNumber} / {total}"))
                super().showPage()
            super().save()

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
        [term(lang,'version'), version],
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
        _tel_lbl = 'Firma acil telefonu' if lang == 'TR' else 'Company emergency telephone'
        story.append(Paragraph(f"{_tel_lbl}: {supplier_tel}", styles['body']))

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
    # EUH059 (ozon tabakası) sinyal kelimesi CLP Tablo 5.2 gereği "Danger"
    _has_euh059 = 'EUH059' in (euh.get('euh_codes') or [])
    from app.services.clp_service import signal_word_for as _swf
    # SEA Ek-1 Tablo 4.1.4 / 3.7.3: yalnız H411/H412/H413/H362 varsa uyarı kelimesi yok ('None')
    signal = 'Danger' if (_hc_set & _DANGER_H) or _has_euh059 else (_swf(_hc_set) or 'None')
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

    def _mask_concs(text: str) -> str:
        """Metindeki "CAS %49.0" / "ad (%20.0" gibi kesin bileşen konsantrasyonlarını, Bölüm 3'te aralıkla
        verilen bileşenler için Bölüm 3'teki aynı metne çevirir (KKDİK Ek-2 A 3.2 — tutarlı gösterim)."""
        if not text:
            return text
        for _c in components:
            _cas = str(_c.get('cas_no') or _c.get('cas') or '').strip()
            _d = _sec3_disp.get(_cas) or {}
            if not _cas or _d.get('kind', 'exact') == 'exact':
                continue
            _rng = _d['text']
            for _key in {_cas, _c.get('name') or '', _c.get('name_tr') or ''}:
                if _key:
                    text = _re.sub(_re.escape(_key) + r'(\s*\(?)\s*%\s*\d+(?:[.,]\d+)?',
                                   lambda m, k=_key, r=_rng: k + m.group(1) + r, text)
        return text

    clf_rows = []
    seen_clf  = set()
    clf_notes = {}   # {h_code_4: {'flag': str, 'note': str}} — tabloda gösterilecek notlar
    _clf_src  = {}   # {h_code: cutoff_source} — Bölüm 16(ç) yöntem ifadesi için

    for entry in clp.get('passed', []):
        _hc_full = (entry.get('h_code','') or '').replace('*','').strip()
        # Preserve H360D/F/FD and H361D/F/FD sub-codes; truncate others to 4 chars
        hc = _hc_full if (_hc_full[4:].upper().replace('D','').replace('F','') == '') else _hc_full[:4]
        if hc in seen_clf:
            continue
        seen_clf.add(hc)
        # H229 ayrı satır değil — CLP Tablo 2.3.2: H222/H223 ile birlikte basınçlı kap ifadesi
        if hc == 'H229':
            for row in clf_rows:
                if row[1] in ('H222', 'H223') or row[1].startswith('H222') or row[1].startswith('H223'):
                    if 'H229' not in row[1]:
                        row[1] = row[1] + ' + H229'
            continue  # ayrı satır ekleme
        reason = entry.get('reason','')
        # Gerekçe metnindeki kesin konsantrasyonlar Bölüm 3 ile aynı gizlilikte verilir
        # (önceden satırlarda 'conc' alanı taşınmadığı için maskeleme hiç çalışmıyordu)
        reason = _mask_concs(reason)
        # Bölüm 3'te aralık kullanılıyorsa hesap formülü ("10x2.0=20.0", "= %99.5", "Σ…=%3.1") kesin değeri
        # ortaya çıkarır ve aralıkla çelişir: yöntem + eşik + dayanak yazılır (KKDİK Ek-2 A 3.2 — zararlar
        # aralığın en yüksek değerine göre; sds_pipeline.section3_display üst uçta aynı sonucu doğrular).
        if (_sec3_ranged and str(entry.get('h_code') or '')[:2] in ('H3', 'H4')
                and _re.search(r'(?<![<>])=\s*\[?%?\s*\d|\d\s*x\s*\d|Σ', reason or '')):
            # Eşik yalnız yüzde olarak yazılmışsa alınır (oran biçimindeki "≥ 0.25" yüzde değildir)
            _thr = _re.findall(r'>=\s*%\s*(\d+(?:[.,]\d+)?)', reason)
            _ref = _re.findall(r'\(([^()]*(?:Tablo|Ek-1|CLP|SEA)[^()]*)\)', reason)
            reason = ((('Hesaplama yöntemi (bileşenlerin Bölüm 3\'teki konsantrasyon aralıklarıyla)' if lang == 'TR'
                        else 'Calculation method (with the concentration ranges in Section 3)')
                       + (f" — {'eşik' if lang == 'TR' else 'threshold'} %{_thr[-1].replace('.', ',')}" if _thr else '')
                       + (f' ({_ref[-1]})' if _ref else '')))
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
        _clf_src[raw_hcode] = entry.get('cutoff_source')
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
        'H360Df': 'Repr. 1A/1B', 'H360Fd': 'Repr. 1A/1B',
        'H361d':  'Repr. 2',     'H361f':  'Repr. 2',     'H361fd': 'Repr. 2',
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
        if hc and not hc[4:].upper().replace('D','').replace('F','') == '':
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
                '<i>H-kodları, 11 Aralık 2013 tarihli ve 28848 mükerrer sayılı Resmî Gazete\'de yayımlanan '
                'Maddelerin ve Karışımların Sınıflandırılması, Etiketlenmesi ve Ambalajlanması '
                'Hakkında Yönetmelik (SEA) esaslarına göre belirlenmiştir.</i>',
                styles['small']
            ))
        # KKDİK Ek-2 A 2.1: en önemli olumsuz fizikokimyasal, insan sağlığı ve çevresel etkiler, uzman
        # olmayanların anlayacağı şekilde listelenir — sınıflandırmadaki zararlılık ifadeleri gruplanır
        if lang in ('TR', 'EN'):
            _h21 = [h for h in dict.fromkeys(list(all_h_codes or []) + list(h_codes or [])) if h]
            if 'H314' in _h21:
                _h21 = [h for h in _h21 if h != 'H318']   # H314 göz hasarını zaten kapsar
            _grp = {'fiz': [h for h in _h21 if h.startswith('H2')],
                    'sag': [h for h in _h21 if h.startswith('H3')],
                    'cev': [h for h in _h21 if h.startswith('H4')]}
            _TR21 = lang == 'TR'
            _none = {'fiz': 'fizikokimyasal tehlike sınıflandırması yoktur.' if _TR21
                     else 'not classified for physicochemical hazards.',
                     'sag': 'insan sağlığı tehlike sınıflandırması yoktur.' if _TR21
                     else 'not classified for health hazards.',
                     'cev': 'çevre için zararlı olarak sınıflandırılmamıştır.' if _TR21
                     else 'not classified as hazardous to the environment.'}
            _lab = {'fiz': 'Fizikokimyasal etkiler' if _TR21 else 'Physicochemical effects',
                    'sag': 'İnsan sağlığı üzerindeki etkiler' if _TR21 else 'Human health effects',
                    'cev': 'Çevresel etkiler' if _TR21 else 'Environmental effects'}
            story.append(Spacer(1, 3))
            story.append(Paragraph(f"<b>{'En önemli olumsuz etkiler' if _TR21 else 'Most important adverse effects'}:</b>",
                                   styles['body']))
            for _g in ('fiz', 'sag', 'cev'):
                _txt21 = (' '.join(get_h(lang, h).rstrip('.') + '.' for h in _grp[_g]) if _grp[_g]
                          else ('Ürün ' if _TR21 else 'The product is ') + _none[_g])
                story.append(Paragraph(f"• {_lab[_g]}: {_txt21}", styles['bullet']))
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
         Paragraph(f"<b><font color='{'red' if signal=='Danger' else 'orange' if signal=='Warning' else 'black'}'>"
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
        # Tür sırası (P1 genel → P2 önleme → P3 müdahale → P4 depolama → P5 bertaraf), tür içinde şiddet
        label_codes_sorted = sorted(
            label_p['selected'],
            key=lambda p: (str(p)[1:2], -P_LABEL_PRIORITY.get(p, 5))
        )
        for code in label_codes_sorted:
            txt = _p_full(code)
            story.append(Paragraph(f"• <b>{code}:</b> {txt}", styles['bullet']))
        # P501 — bertaraf kodu, 6 limitinin dışında "+1 Bertaraf Kodu" olarak her zaman basılır
        mandatory = label_p.get('mandatory', [])
        if mandatory:
            for m in mandatory:
                if m in label_p['selected']:
                    continue   # seçilenlerde zaten var — önceden P103 iki kez basılıyordu
                txt = _p_full(m)
                story.append(Paragraph(f"• <b>{m}:</b> {txt}", styles['bullet']))

        # Limit aşım notu — birden fazla tehlike sınıfı olan ürünlerde öncelikli seçim yapıldı
        if label_p.get('limit_exceeded'):
            # SEA Md.30(3): zararın ciddiyeti gerektirdiğinde altıdan fazla önlem ifadesi etikette yer alabilir
            _exc_note = (
                'SEA Yönetmeliği Md.30(3): zararın ciddiyeti ve niteliği nedeniyle kesinlikle önerilen '
                'önlem ifadelerinin tamamı etikete alınmıştır (altıdan fazla).'
                if lang == 'TR' else
                'Owing to the severity and nature of the hazards, all strongly recommended precautionary '
                'statements are included on the label (more than six).'
            )
            story.append(Spacer(1, 2))
            story.append(Paragraph(f"<i>{_exc_note}</i>", styles['small']))

    # ─── Etikette adı yazılması zorunlu bileşenler — SEA/CLP Md. 18(3)(b) ───────
    # Akut toksisite, cilt aşındırma/ciddi göz hasarı, CMR, hassaslaştırma, STOT, aspirasyon
    # sınıflandırmasına katkı yapan maddeler (sds_pipeline.label_components)
    _label_comps = [str(n) for n in (sds_data.get('label_components') or []) if n]
    if _label_comps:
        _lc_lbl = ('Etiket üzerinde belirtilmesi zorunlu zararlı bileşenler' if lang == 'TR'
                   else 'Hazardous components which must be listed on the label')
        story.append(Spacer(1, 3))
        story.append(Paragraph(f"<b>{_lc_lbl}:</b> {', '.join(_label_comps)}", styles['body']))

    # ─── SEA §3.1.3.6.2.2 — Zorunlu ibare: bilinmeyen akut toksisite ≥%1 ─────────
    # Trigger: herhangi bir bilinmeyen bileşen bireysel olarak ≥%1 konsantrasyonda
    # statementNeeded bayrağı JS motorundan gelir; yoksa unknownPct≥1'den türet
    _stmt_needed = False
    _unk_pct_for_stmt = 0.0
    _unk_by_route: dict = {}   # yol → bilinmeyen % (ibarede hangi yol için olduğu yazılır)
    if ate_mix_details:
        for _rk, _rd in ate_mix_details.items():
            if not isinstance(_rd, dict):
                continue
            if _rd.get('statementNeeded', False):
                _stmt_needed = True
            _upct = float(_rd.get('unknownPct', 0) or 0)
            if _rk in ('oral', 'dermal', 'inhal') and _upct >= 1.0:
                _unk_by_route[_rk] = round(_upct, 1)
            if _upct > _unk_pct_for_stmt:
                _unk_pct_for_stmt = _upct
        # Fallback: statementNeeded bayrağı yoksa unknownPct≥1 kontrolü yap
        if not _stmt_needed and _unk_pct_for_stmt >= 1.0:
            _stmt_needed = True
    # Bileşen listesinden doğrudan türet — yalnızca ATEmix hesabı hiç gelmediyse (eski istemci).
    # Hesap geldiyse o yetkilidir: resmî kaynaklı / REACH kayıtlı maddeleri "bilinmeyen" saymaz;
    # bu yedek kontrol onları yeniden bilinmeyen sayıp yanlış ibare ekliyordu.
    if not _stmt_needed and not ate_mix_details and not sds_data.get('ate_from_pipeline'):
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
        _RN = {'TR': {'oral': 'ağız', 'dermal': 'cilt', 'inhal': 'solunum'},
               'EN': {'oral': 'oral', 'dermal': 'dermal', 'inhal': 'inhalation'}}
        _rn = _RN['TR' if lang == 'TR' else 'EN']
        # Aynı yüzdeye sahip yollar tek cümlede: "%9.5'i … (cilt, solunum yoluyla)"
        _groups: dict = {}
        for _rk in ('oral', 'dermal', 'inhal'):
            if _rk in _unk_by_route:
                _groups.setdefault(_unk_by_route[_rk], []).append(_rn[_rk])
        if not _groups:   # yol bilgisi yoksa (eski istemci) yolsuz ibare
            _groups = {round(_unk_pct_for_stmt, 1): []}
        _sentences = []
        for _pct, _routes in _groups.items():
            if lang == 'TR':
                _via = f" ({', '.join(_routes)} yoluyla)" if _routes else ''
                _sentences.append(f"Karışımın %{_pct}'i bilinmeyen akut toksisiteye{_via} sahip "
                                  f"bileşenlerden oluşmaktadır.")
            else:
                _via = f" ({', '.join(_routes)})" if _routes else ''
                _sentences.append(f"{_pct}% of the mixture consists of ingredient(s) of "
                                  f"unknown acute toxicity{_via}.")
        story.append(Spacer(1, 4))
        for _stmt_text in _sentences:
            story.append(Paragraph(f"<b>{_stmt_text}</b>", styles['body']))

    # ─── SEA Ek-1 4.1.3.6.1 — Zorunlu ibare: sucul zararı bilinmeyen bileşenler ─────────
    _aqu = sds_data.get('aquatic_unknown') or {}
    if _aqu.get('needed') and float(_aqu.get('pct') or 0) > 0:
        _aq_txt = (f"%{_aqu['pct']:g} oranda sucul çevreye zararı bilinmeyen bileşenler içerir." if lang == 'TR'
                   else f"Contains {_aqu['pct']:g} % of components with unknown hazards to the aquatic environment.")
        story.append(Spacer(1, 3))
        story.append(Paragraph(f"<b>{_aq_txt}</b>", styles['body']))

    # "Duyarlılaştırıcı içerir" satırı kaldırıldı (2026-10-08): hassaslaştırıcı adları SEA Md.20(3)(b) bileşen
    # satırında (sınıflandırmaya katkı yapanlar) ve EUH208'de (Ek-2 2.8 — eşiğin altındakiler) zaten yer alıyor;
    # bu satır konsantrasyona bakmadan her hassaslaştırıcıyı tekrar yazıyordu.

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
    # KKDİK Ek-2 2.3: toz patlaması zararlılığı varsa yönetmelikteki ifade
    if phys.get('dust_explosion') in (True, 'true', '1', 1) and (product.get('form') in ('solid', 'powder')):
        story.append(Paragraph(
            'Eğer yayılırsa, patlayabilen toz-hava karışımı oluşabilir.' if lang == 'TR'
            else 'May form explosible dust-air mixture if dispersed.', styles['small']))

    # ─────────────────────────────────────────────────────────────────────────
    # BÖLÜM 3 — Bileşimler
    # ─────────────────────────────────────────────────────────────────────────
    story += section_block(section_title(lang, 3), styles)
    story += sub_block(f"3.2 {sub_title(lang,'3.2')}", styles)

    def _disp_conc(cas: str, conc_val, name: str = '') -> str:
        """Konsantrasyon gösterimi — Bölüm 3 ile aynı metin (KKDİK Ek-2 A 3.2); CAS yoksa ada göre."""
        _d = _sec3_disp.get(str(cas).strip()) or _sec3_by_name.get(str(name or '').strip().lower())
        if _d:
            return _d['text']
        try:
            c = float(conc_val or 0)
        except (TypeError, ValueError):
            c = 0.0
        return f'{c:g}' if c else '—'

    from app.services.svhc_service import svhc_section3_reason
    from app.services.tr_oel_service import get_oel as _tr_oel

    def _c3max(c) -> float:
        for k in ('concMax', 'conc_max', 'concentration', 'conc'):
            try:
                if c.get(k) not in (None, ''):
                    return float(c.get(k))
            except (TypeError, ValueError):
                pass
        return 0.0

    def _sec3_needed(c) -> bool:
        """KKDİK Ek-2 3.2.1 / 3.2.2: sınıflandırılmış maddeler; sınıflandırılmamışlardan yalnız TR işyeri maruz
        kalma limiti olanlar veya PBT/vPvB/Aday Liste (≥%0,1). Diğerleri (su vb.) listelenmez — Ek-2 bunları
        isteğe bağlı bırakır ("listelemeyi tercih edebilir"); kullanıcı tercihi: listelenmesin."""
        if any((h.get('h_code') or h.get('h_class')) for h in (c.get('hazards') or [])):
            return True
        cas = str(c.get('cas_no') or c.get('cas') or '').strip()
        return bool(cas and (_tr_oel(cas) or svhc_section3_reason(cas, _c3max(c), lang)))

    # KKDİK Ek-2 A 3.2 (a)/(b): kütle veya hacme göre azalan sırada (önceden girildiği sırayla basılıyordu)
    _sec3_comps = sorted((c for c in components if _sec3_needed(c)), key=lambda c: -_c3max(c))
    sec3_rows = generate_section3(_sec3_comps, disclosure, lang=lang, conc_display=_sec3_disp)
    _sec3_names = {str(r.get('cas') or '').strip(): r.get('name') for r in (sec3_rows or [])}
    if not sec3_rows:
        story.append(Paragraph(
            'KKDİK Ek-2 3.2.1 / 3.2.2 uyarınca bu bölümde belirtilmesi gereken madde bulunmamaktadır.'
            if lang == 'TR' else
            'There are no substances that need to be listed in this section (Annex II 3.2.1 / 3.2.2).',
            styles['body']))
    if sec3_rows:
        # B3.2 Tablo — 4 sütun, A4'e sığacak şekilde
        # CAS No | Madde Adı | Konst. | Sınıflandırma
        # EC No / REACH Kayıt No — CAS hücresinin altına küçük font

        cas_hdr  = ('CAS No\nEC / Kayıt No' if lang=='TR' else 'CAS No\nEC / Registration No')
        name_hdr = S(lang,'ingredient_label')
        conc_hdr = term(lang,'concentration')
        # SEA Ek-1: konsantrasyonlar gazlarda hacimce (v/v), diğerlerinde ağırlıkça (w/w)
        _is_gas3 = (product.get('form') or '') == 'gas'
        if lang == 'TR':
            conc_hdr = f"{conc_hdr} ({'% h/h' if _is_gas3 else '% a/a'})"
        else:
            conc_hdr = f"{conc_hdr} ({'% v/v' if _is_gas3 else '% w/w'})"
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

        # Kayıt numaraları: TR (KKDİK) ve AB (REACH) ayrı satır.
        # Kayıt numarası maddeye değil kaydettiren firmaya aittir → KKDİK numarası hammadde
        # tedarikçisinin GBF'sinden gelir (kullanıcı girer). AB numarasında kayıt sahibine özgü
        # son bölüm gösterilmez (REACH Ek-II 3.1 izni) → "XXXX".
        _supplier_txt = 'tedarikçiden temin edilir' if lang == 'TR' else 'obtain from supplier'
        _any_eu = False
        _any_tr_missing = False

        def _eu_no(v: str) -> str:
            v = (v or '').strip()
            if v == 'exempt':
                return 'Muaf' if lang == 'TR' else 'Exempt'
            if v == 'polymer':
                return 'Polimer/muaf' if lang == 'TR' else 'Polymer/exempt'
            return _re.sub(r'^(01-\d{10}-\d{2})-\d{4}$', r'\1-XXXX', v)

        for r in sec3_rows:
            cas = r['cas']
            comp_obj = next((comp for comp in components if (comp.get('cas_no') or comp.get('cas') or '').strip() == cas), {})
            ec  = comp_obj.get('ec_no','') or get_ec_no(cas)
            _eu_raw = (comp_obj.get('reach_no','') or get_reg_no(cas) or '').strip()
            if get_reg_no(cas) == 'exempt':   # veritabanında muaf (örn. su) — ön yüzdeki eski değeri ezer
                _eu_raw = 'exempt'
            eu  = _eu_no(_eu_raw)
            tr  = (comp_obj.get('kkdik_no') or '').strip()
            if not tr and _eu_raw == 'exempt':   # AB'de muaf (Ek-IV/V) → KKDİK'te de muaf (Ek-4/5)
                tr = 'Muaf' if lang == 'TR' else 'Exempt'
            if eu and eu.startswith('01-'):
                _any_eu = True
            if not tr:
                _any_tr_missing = True

            _lbl_tr = 'KKDİK (TR)' if lang == 'TR' else 'KKDİK (TR)'
            _lbl_eu = 'REACH (AB)' if lang == 'TR' else 'REACH (EU)'
            cas_cell = Paragraph(
                f"<b>{cas}</b><br/>"
                f"<font size='6'>EC: {ec or '—'}<br/>"
                f"{_lbl_tr}: {tr or _supplier_txt}<br/>"
                f"{_lbl_eu}: {eu or _supplier_txt}</font>",
                styles['small']
            )
            # Her sınıflandırma kendi satırında — uzun metinde kelime kırılmasını önle
            _clf_str = translate_hclass_list(r.get('hazards',''), lang)
            if not _clf_str:
                _clf_str = term(lang,'not_classified')
                # Ek-2 3.2.3: sınıflandırılmamış madde listede yer alıyorsa nedeni belirtilir
                _svhc_why = svhc_section3_reason(
                    cas, comp_obj.get('concMax') or comp_obj.get('conc_max') or comp_obj.get('concentration')
                    or comp_obj.get('conc'), lang)
                if _svhc_why:
                    _clf_str += f'; {_svhc_why}'
                elif _tr_oel(cas):
                    _clf_str += ('; Listelenme nedeni: işyeri maruz kalma limiti (bkz. 8.1)' if lang == 'TR'
                                 else '; Reason for listing: workplace exposure limit (see 8.1)')
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
        # Gaz karışımı: birim notu (SEA Ek-1 — gazlarda v/v; KKDİK Ek-2 3.2.1 — gazda hacimce %0,2)
        if _is_gas3:
            story.append(Paragraph(
                '* Gaz karışımı: konsantrasyonlar hacimce (h/h) verilmiştir; akut toksisite tahminleri '
                'ppmV cinsindendir (SEA Ek-1 Tablo 3.1.1).' if lang == 'TR' else
                '* Gas mixture: concentrations are given by volume (v/v); acute toxicity estimates in ppmV.',
                styles['small']))
        # Kayıt numarası notları
        if _any_tr_missing:
            story.append(Paragraph(
                "* KKDİK (TR) kayıt numarası, maddeyi Türkiye'de kaydettiren üretici/ithalatçıya aittir; "
                "girilmeyen numaralar hammadde tedarikçisinden temin edilir." if lang == 'TR' else
                "* KKDİK (TR) registration numbers belong to the Turkish registrant; "
                "numbers not given are to be obtained from the raw material supplier.",
                styles['small']
            ))
        if _any_eu:
            story.append(Paragraph(
                "* REACH (AB) numaralarında kayıt sahibine özgü son bölüm gösterilmemiştir (XXXX); "
                "tam numara talep halinde tedarikçiden temin edilir." if lang == 'TR' else
                "* The registrant-specific part of REACH (EU) numbers is omitted (XXXX); "
                "the full number is available from the supplier on request.",
                styles['small']
            ))

        # KKDİK Ek-2 A 3.2: aralık kullanılırsa zararlar en yüksek konsantrasyona göre tanımlanır
        if any(r.get('conc_kind') in ('band', 'narrowed', 'user_range') for r in sec3_rows):
            story.append(Paragraph(
                '* Konsantrasyonlar KKDİK Ek-2 A 3.2(b) uyarınca yüzde aralığı olarak verilmiştir; sağlık ve '
                'çevre zararları her bileşenin aralıktaki en yüksek konsantrasyonuna göre tanımlanmıştır.'
                if lang == 'TR' else
                '* Concentrations are given as percentage ranges; the health and environmental hazards describe '
                'the effects of the highest concentration of each ingredient.', styles['small']))
        # Gizleme notları — aynı not birden fazla bileşende olsa da bir kez yazılır
        for _note in dict.fromkeys(r['note'] for r in sec3_rows if r.get('note')):
            story.append(Paragraph(f"* {_note}", styles['small']))
    story.append(Spacer(1, 3))

    # ─────────────────────────────────────────────────────────────────────────
    # BÖLÜM 4 — İlk Yardım
    # ─────────────────────────────────────────────────────────────────────────
    story += section_block(section_title(lang, 4), styles)
    story += sub_block(f"4.1 {sub_title(lang,'4.1')}", styles)

    # Ürünün fiziksel hali — 4/6/7/8 metinleri buna göre uyarlanır
    _sec_form = product.get('form', '') or 'liquid'
    # Sınıflandırmadaki tüm H kodları (etikette baskın olmayanlar dahil) — yol bazlı ilk yardım için
    _h_all_first_aid = list(dict.fromkeys(list(all_h_codes) + list(h_codes)))
    if lang in ('TR', 'EN'):
        # KKDİK Ek-2 4.1.1: maruz kalma yoluna göre; SEA Ek-4 resmî önlem ifadeleri
        # İyi uygulama: göz hasarı/tahrişinde (H314/H318/H319) yıkama süresi dakika olarak verilir
        _eye_dmg = bool({str(h)[:4] for h in _h_all_first_aid} & {'H314', 'H318', 'H319'})
        _fa_seen_txt = []
        for _fa in reg_first_aid(_h_all_first_aid, _sec_form, lang):
            _fa_txt = _fa['text']
            _fa_seen_txt.append(_fa_txt)
            # Aşındırıcı/göz hasarı: P305+P351+P338 "birkaç dakika" der; iyi uygulama olarak süre eklenir
            if _eye_dmg and _fa['route'] in ('Göz', 'Eyes', 'Eye') and '15' not in _fa_txt:
                _fa_txt += (' Yıkamaya en az 15 dakika devam edin.' if lang == 'TR'
                            else ' Continue rinsing for at least 15 minutes.')
            story.append(Paragraph(f"• <b>{_fa['route']}:</b> {_fa_txt}", styles['bullet']))
        # KKDİK Ek-2 A 4.1.2(a): gecikmiş etkilerin beklenip beklenmediği (11.1.7 ile aynı metin)
        story.append(Paragraph(
            f"• <b>{'Gecikmiş etkiler' if lang == 'TR' else 'Delayed effects'}:</b> "
            f"{_delayed_effects_text(set(_h_all_first_aid), lang == 'TR')}", styles['bullet']))
        # KKDİK Ek-2 A 4.1.2(c): kirlenmiş giysilerin çıkarılması (önlem ifadesinde yoksa) — sağlık
        # sınıflandırması olmayan ürünlerde de verilir
        if not any('giysi' in t.lower() or 'clothing' in t.lower() for t in _fa_seen_txt):
            story.append(Paragraph(
                f"• <b>{'Kirlenmiş giysiler' if lang == 'TR' else 'Contaminated clothing'}:</b> "
                + ('Kirlenmiş giysi ve ayakkabıları çıkarın; tekrar kullanmadan önce yıkayın.' if lang == 'TR'
                   else 'Remove contaminated clothing and shoes; wash before reuse.'), styles['bullet']))
        # KKDİK Ek-2 A 4.1.2(ç): ilk yardım yapanlar için kişisel koruyucu ekipman
        story.append(Paragraph(
            f"• <b>{'İlk yardım yapanlar' if lang == 'TR' else 'First aiders'}:</b> "
            + ('Ürünle temastan kaçının; Bölüm 8.2\'de belirtilen koruyucu ekipmanı (eldiven, göz koruyucu) '
               'kullanın.' if lang == 'TR' else
               'Avoid contact with the product; wear the protective equipment given in Section 8.2 '
               '(gloves, eye protection).'), styles['bullet']))
    else:
        sec4 = generate_section(4, h_codes)
        story += bullet_list(adapt_list_for_form(sec4['bullets'], _sec_form), styles) or [na_text(lang, styles)]
    story.append(Spacer(1, 3))

    story += sub_block(f"4.2 {sub_title(lang,'4.2')}", styles)
    _sym_bullets = adapt_list_for_form(generate_section_42(h_codes), _sec_form)
    _health_h = [h for h in _h_all_first_aid if str(h).startswith('H3')]
    if not _sym_bullets and _health_h and lang in ('TR', 'EN'):
        # Belirti cümlesi tanımlı olmayan sağlık sınıfı: genel cümle yerine resmî H ifadesi
        _sym_bullets = [f"{str(h).split()[0]}: {get_h_stmt(str(h).split()[0], lang)}" for h in _health_h]
    if _sym_bullets:
        story += bullet_list(_sym_bullets, styles)
    elif lang in ('TR', 'EN'):
        # KKDİK Ek-2 A 4.2 — sağlık sınıflandırması yok: "maruziyete göre değişir" gibi içi boş cümle basılmaz
        story.append(Paragraph(_unclassified_health_text(components, lang == 'TR', _sec3_names), styles['body']))
    else:
        story.append(Paragraph(S(lang, 'symptoms_general'), styles['body']))

    story += sub_block(f"4.3 {sub_title(lang,'4.3')}", styles)
    # KKDİK Ek-2 A 4.3: hekime yönelik bilgi (özel antidot verisi yoksa semptomatik tedavi)
    if lang in ('TR', 'EN'):
        story.append(Paragraph(
            'Semptomatik tedavi uygulayın. Hekime bu Güvenlik Bilgi Formunu veya ürün etiketini gösterin.'
            if lang == 'TR' else
            'Treat symptomatically. Show this Safety Data Sheet or the product label to the physician.',
            styles['body']))
        # Ek-2 A 4.3: özel/acil tedavi için işyerinde bulunması gereken araçlar
        if set(_h_all_first_aid) & {'H314', 'H318'}:
            story.append(Paragraph(
                'Çalışma alanında göz duşu ve acil durum duşu bulundurulmalıdır.' if lang == 'TR'
                else 'An eye wash station and an emergency shower should be available in the work area.',
                styles['body']))
        # İyi uygulama — aspirasyon zararı (H304): kusturma yok (P331), solunum yönünden gözlem
        if 'H304' in {str(h)[:4] for h in _h_all_first_aid}:
            story.append(Paragraph(
                'Aspirasyon zararı (H304): kusturmayın. Yutulduktan sonra öksürük veya nefes darlığı görülürse '
                'kimyasal pnömoni olasılığı açısından kişi tıbbi gözlem altında tutulmalıdır.' if lang == 'TR'
                else 'Aspiration hazard (H304): do not induce vomiting. If coughing or shortness of breath occurs '
                     'after swallowing, keep the person under medical observation for possible chemical pneumonitis.',
                styles['body']))
    story.append(Paragraph(
        term(lang,'poison_center'), styles['body']
    ))

    # ─────────────────────────────────────────────────────────────────────────
    # BÖLÜM 5 — Yangın
    # ─────────────────────────────────────────────────────────────────────────
    story += section_block(section_title(lang, 5), styles)
    story += sub_block(f"5.1 {sub_title(lang,'5.1')}", styles)

    sec5 = generate_section(5, h_codes)
    # KKDİK Ek-2 A 5.1: uygun ve uygun olmayan söndürücüler ayrı ayrı
    from app.services.sds_sentence_service import extinguishing_media as _ext_media
    _ext_ok, _ext_no = _ext_media(list(dict.fromkeys(list(all_h_codes or []) + list(h_codes or []))),
                                  (euh or {}).get('euh_codes') or [], lang=lang if lang in ('TR', 'EN') else 'EN')
    # Unicode alt simge (₂) PDF yazı tipinde yok — ReportLab <sub> etiketi kullanılır
    _ext_ok, _ext_no = (x.replace('CO₂', 'CO<sub>2</sub>') for x in (_ext_ok, _ext_no))
    story.append(Paragraph(f"<b>{'Uygun söndürücüler' if lang == 'TR' else 'Suitable extinguishing media'}:</b> "
                           f"{_ext_ok}", styles['body']))
    story.append(Paragraph(f"<b>{'Uygun olmayan söndürücüler' if lang == 'TR' else 'Unsuitable extinguishing media'}:"
                           f"</b> {_ext_no}", styles['body']))

    # Tehlikeli bozunma/yanma ürünleri — 5.2 ve 10.6 aynı metni kullanır (KKDİK Ek-2 5.2: yanma
    # sırasında oluşan tehlikeli ürünler belirtilir)
    _cas_dec = {str(c.get('cas_no') or c.get('cas') or '').strip() for c in components}
    _CHLOR_CAS = {'75-09-2', '67-66-3', '71-55-6', '79-01-6', '127-18-4', '7647-01-0', '75-00-3',
                  '79-00-5', '106-93-4'}
    _dec = []
    # Karbon oksitler: alevlenir ürün veya organik bileşen (inorganik listesinde olmayan, su dışı) varsa
    from app.services.tr_mevzuat_service import _INORGANIC_CAS as _INORG_DEC
    _has_organic = any(c and c not in _INORG_DEC and c != '7732-18-5' for c in _cas_dec)
    if any(h in h_codes for h in ['H224', 'H225', 'H226', 'H228', 'H242']) or _has_organic:
        _dec.append('Karbon oksitler (CO, CO₂)' if lang == 'TR' else 'Carbon oxides (CO, CO₂)')
    # Azot / fosfor / kükürt içeren bileşenler — yanma/bozunmada oksitleri oluşur
    _N_CAS = {'7697-37-2', '7631-99-4', '7757-79-1', '6484-52-2', '10124-37-5', '7632-00-0',
              '141-43-5', '111-42-2', '102-71-6', '57-13-6', '60-00-4', '64-02-8', '6381-92-6',
              '139-13-9', '5064-31-3', '1643-20-5', '68424-85-1', '7173-51-5', '12125-02-9'}
    _P_CAS = {'7664-38-2', '7758-29-4', '7722-88-5', '7601-54-9', '7558-80-7', '7558-79-4',
              '7778-77-0', '2809-21-4', '6419-19-8', '15827-60-8', '10213-79-3'}
    _S_CAS = {'7664-93-9', '5329-14-6', '7681-38-1', '68584-22-5', '25155-30-0', '68891-38-3',
              '151-21-3', '9004-82-4', '85536-14-7'}
    if _cas_dec & _N_CAS:
        _dec.append('Azot oksitler (NOx)' if lang == 'TR' else 'Nitrogen oxides (NOx)')
    if _cas_dec & _P_CAS:
        _dec.append('Fosfor oksitler' if lang == 'TR' else 'Phosphorus oxides')
    if _cas_dec & _S_CAS:
        _dec.append('Kükürt oksitler (SOx)' if lang == 'TR' else 'Sulphur oxides (SOx)')
    if _cas_dec & _CHLOR_CAS:
        _dec.append('Klorür bileşikleri (HCl, Cl₂)' if lang == 'TR' else 'Chloride compounds (HCl, Cl₂)')
    # NH₃ yalnızca bileşende amonyak/amonyak çözeltisi varsa
    if _cas_dec & {'1336-21-6', '7664-41-7'}:
        _dec.append('NH₃' if lang == 'TR' else 'NH₃ (ammonia)')
    if 'H400' in h_codes or 'H411' in h_codes:
        _dec.append('Sucul ortama zararlı organik fragmentler' if lang == 'TR'
                    else 'Harmful organic fragments to aquatic environment')
    if _dec:
        _decomp_str = '; '.join(_dec) + '.'
    elif _cas_dec and not _has_organic:
        # Yalnız inorganik bileşenler (su dahil) — karbon oksit beklenmez
        _decomp_str = ('Normal koşullarda tehlikeli bozunma ürünü oluşması beklenmez.' if lang == 'TR'
                       else 'No hazardous decomposition products expected under normal conditions.')
    else:
        _decomp_str = S(lang, 'decomp_products')

    # Efervesan katı (asit + karbonat/bikarbonat) — 7.2, 10.3 ve 10.4 için
    _SOLID_ACID_CAS = {'77-92-9', '5949-29-1', '5329-14-6', '6915-15-7', '87-69-4', '124-04-9',
                       '110-17-8', '7681-38-1'}
    _CARBONATE_CAS = {'497-19-8', '5968-11-6', '6132-02-1', '144-55-8', '15630-89-4', '584-08-7',
                      '298-14-6'}
    _effervescent = ((product.get('form') or '') in ('solid', 'powder')
                     and bool(_cas_dec & _SOLID_ACID_CAS) and bool(_cas_dec & _CARBONATE_CAS))

    story += sub_block(f"5.2 {sub_title(lang,'5.2')}", styles)
    _GENERIC_52 = {'Yangın gazlarından kaçınınız. Uygun solunum koruması.', 'Yangın gazlarından kaçının. Uygun solunum koruması.'}
    _b52 = [b for b in (sec5.get('bullets') or []) if str(b).strip() not in _GENERIC_52]
    if _dec:
        _b52.append(('Yanma sırasında tehlikeli ürünler oluşabilir: ' + _decomp_str
                     + ' Yanma gazlarını solumayın.') if lang == 'TR' else
                    ('Hazardous combustion products may be formed: ' + _decomp_str
                     + ' Do not breathe combustion gases.'))
    else:
        _b52.append('Ürün yanıcı değildir; çevredeki yangının duman ve gazlarını solumayın.' if lang == 'TR'
                    else 'The product is not combustible; do not breathe smoke and gases from the surrounding fire.')
    story += bullet_list(_b52, styles)

    story += sub_block(f"5.3 {sub_title(lang,'5.3')}", styles)
    story.append(Paragraph(
        S(lang,'firefighter_ppe'),
        styles['body']
    ))

    story.append(CondPageBreak(60*mm))   # yalnız sayfa sonunda yer yoksa yeni sayfa (boş sayfa kalmasın)

    # ─────────────────────────────────────────────────────────────────────────
    # BÖLÜM 6 — Kaza
    # ─────────────────────────────────────────────────────────────────────────
    story += section_block(section_title(lang, 6), styles)
    sec6 = generate_section(6, h_codes)
    if lang in ('TR', 'EN'):
        # KKDİK Ek-2 6.1 kişisel önlemler / 6.2 çevresel / 6.3 kontrol altına alma ve temizleme
        _s6 = reg_accidental_release(_h_all_first_aid, _sec_form, sec6['bullets'], lang)
        story += sub_block(f"6.1 {sub_title(lang,'6.1')}", styles)
        story += bullet_list(_s6['6.1'], styles)
        story += sub_block(f"6.2 {sub_title(lang,'6.2')}", styles)
        story += bullet_list(_s6['6.2'], styles)
        story += sub_block(f"6.3 {sub_title(lang,'6.3')}", styles)
        story += bullet_list(_s6['6.3'], styles)
        # KKDİK Ek-2 A 6 (giriş): dökülme hacmi zarar üzerinde önemliyse büyük ve küçük dökülmeler ayrılır
        if _sec_form not in ('solid', 'powder', 'gas'):
            story += bullet_list([
                ('Küçük dökülmeler: emici malzemeyle toplayıp uygun, etiketli kaplara alın.' if lang == 'TR'
                 else 'Small spills: absorb with absorbent material and place in suitable, labelled containers.'),
                ('Büyük dökülmeler: dökülen ürünü set ile çevreleyin, uygun ekipmanla etiketli kaplara aktarın; '
                 'kanalizasyona veya su kaynaklarına ulaşma riski varsa yetkili makamları bilgilendirin.' if lang == 'TR'
                 else 'Large spills: dike the spilled product, transfer it with suitable equipment into labelled '
                      'containers; notify the authorities if it may reach drains or watercourses.')], styles)
        # KKDİK Ek-2 A 6.3.3: uygunsuz kontrol altına alma / temizlik teknikleri
        _s633 = ['Dökülen ürünü su ile seyrelterek kanalizasyona yıkamayın.' if lang == 'TR'
                 else 'Do not flush spilled product into the sewer with water.']
        if 'H290' in _h_all_first_aid:
            _s633.append('Toplama ve depolama için metal kap veya ekipman kullanmayın.' if lang == 'TR'
                         else 'Do not use metal containers or equipment for collection and storage.')
        story += bullet_list(_s633, styles)
    else:
        story += sub_block(f"6.1 {sub_title(lang,'6.1')}", styles)
        story.append(Paragraph(S(lang,'personal_precautions'), styles['body']))
        story += sub_block(f"6.2 {sub_title(lang,'6.2')}", styles)
        story += bullet_list(adapt_list_for_form(sec6['bullets'], _sec_form), styles) or [na_text(lang, styles)]
        story += sub_block(f"6.3 {sub_title(lang,'6.3')}", styles)
        story.append(Paragraph(adapt_for_form(S(lang,'spill_instructions'), _sec_form), styles['body']))

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

    # Form bilgisi — B9 bloğundan önce burada da okunur
    _b7_form     = product.get('form', '')
    _b7_form_sub = product.get('form_sub', '') or ''
    _b7_is_solid = _b7_form in ('solid', 'powder')

    _p_all_codes = [str(c) for c in (p_data.get('p_codes') or [])]
    if lang in ('TR', 'EN'):
        # 7.1 — yalnızca resmî ifadeler: Ek-2 7.1.1 a) (katı), ürünün önleme ifadeleri (SEA Ek-4
        # P2xx; KKE Bölüm 8'de) ve Ek-2 7.1.2 hijyen (P270/P264 zaten varsa tekrarlanmaz)
        _sec7_bullets = []
        if _b7_is_solid:
            _sec7_bullets.append('Toz oluşumunu önlemek amacıyla kontrol altına alma önlemleri uygulayın.'
                                 if lang == 'TR' else 'Apply containment measures to prevent dust generation.')
        _sec7_bullets += reg_handling_p(_p_all_codes, _sec_form, lang)
        _hyg = reg_hygiene(lang)
        _hyg_skip = {0} if 'P270' in _p_all_codes else set()
        if 'P264' in _p_all_codes:
            _hyg_skip.add(1)
        _sec7_bullets += [x for i, x in enumerate(_hyg) if i not in _hyg_skip]
        # KKDİK Ek-2 A 7.1.1(ç): çevreye yayılmayı azaltma
        _sec7_bullets.append('Çevreye yayılmasını önleyin; dökülmelerin önüne geçin ve kanalizasyondan, su '
                             'yollarından uzak tutun.' if lang == 'TR' else
                             'Prevent release to the environment; avoid spills and keep away from drains and '
                             'watercourses.')
        # KKDİK Ek-2 A 7.1.1(c): özellikleri değiştiren işlemlerden doğan yeni riskler
        _h71 = set(all_h_codes or []) | set(h_codes or [])
        if 'H314' in _h71 and not _b7_is_solid:
            _sec7_bullets.append('Seyreltme ısı açığa çıkarabilir: ürünü suya yavaşça ve karıştırarak ekleyin; '
                                 'ürünün üzerine su eklemeyin.' if lang == 'TR' else
                                 'Dilution may release heat: add the product slowly to water while stirring; '
                                 'never add water to the product.')
        if _h71 & {'H224', 'H225', 'H226', 'H228'}:
            _sec7_bullets.append('Isıtma, püskürtme veya sisleme buhar oluşumunu ve alevlenme riskini artırır.'
                                 if lang == 'TR' else
                                 'Heating, spraying or misting increases vapour formation and the risk of ignition.')
        if not (_h71 & {'H314', 'H224', 'H225', 'H226', 'H228'}):
            _sec7_bullets.append('Isıtma, seyreltme veya başka maddelerle karıştırma ürünün özelliklerini '
                                 'değiştirebilir; bu işlemlerden önce risk değerlendirmesi yapın.' if lang == 'TR'
                                 else 'Heating, dilution or mixing with other substances may change the properties '
                                      'of the product; assess the risks before such operations.')
    else:
        sec7 = generate_section(7, h_codes)
        _sec7_bullets = adapt_list_for_form(sec7['bullets'], _sec_form)
    story += bullet_list(list(dict.fromkeys(_sec7_bullets)), styles) or [na_text(lang, styles)]

    story += sub_block(f"7.2 {sub_title(lang,'7.2')}", styles)
    _incompat_idx = None
    if lang in ('TR', 'EN'):
        # 7.2 — ürünün depolama ifadeleri (SEA Ek-4 P4xx resmî metin)
        _sec72_bullets = reg_storage_p(_p_all_codes, _sec_form, lang)
        # KKDİK Ek-2 7.2: birlikte bulunmaması gereken maddeler + aşındırıcı üründe kap malzemesi
        _h72 = set(all_h_codes or []) | set(h_codes or [])
        if _h72 & {'H314', 'H290'} and 'P406' not in _p_all_codes:   # P406 varsa zaten yazılır
            _sec72_bullets = list(_sec72_bullets) + [
                'Aşınmaya dayanıklı, iç kaplaması uygun orijinal kabında, kapalı olarak saklayın.'
                if lang == 'TR' else
                'Keep only in original corrosion-resistant container with a resistant inner liner, tightly closed.']
        # KKDİK Ek-2 A 7.2(b): sıcaklık/güneş ışığı/havalandırma — ürünün P4xx ifadeleri bunu karşılamıyorsa
        if not ({'P403', 'P235', 'P403+P235', 'P403+P233', 'P410', 'P410+P403', 'P411', 'P412'}
                & set(_p_all_codes)):
            _sec72_bullets = list(_sec72_bullets) + [
                'Serin ve iyi havalandırılan bir yerde, doğrudan güneş ışığından ve ısı kaynaklarından uzakta '
                'saklayın.' if lang == 'TR' else
                'Store in a cool, well-ventilated place away from direct sunlight and sources of heat.']
        # KKDİK Ek-2 A 7.2(d)(i)(ii): havalandırma ve depo tasarımı (tutma)
        if _h72 and _sec_form not in ('solid', 'powder', 'gas'):
            _sec72_bullets = list(_sec72_bullets) + [
                'Depolama alanında dökülmeye karşı sızdırmaz zemin veya tutma havuzu sağlayın; depo iyi '
                'havalandırılmalıdır.' if lang == 'TR' else
                'Provide an impermeable floor or a retention basin against spills in the storage area; the store '
                'must be well ventilated.']
        # KKDİK Ek-2 A 7.2(a)(iv) ve B 7.2 başlığı: birlikte bulunmaması gereken maddeler adıyla.
        # Liste Bölüm 10.5'te hesaplanır; yer tutucu o zaman doldurulur (bkz. _INCOMPAT_SLOT).
        _sec72_bullets = list(_sec72_bullets) + [_INCOMPAT_SLOT]
        if _effervescent:
            _sec72_bullets = list(_sec72_bullets) + [
                'Kuru yerde, nemden koruyarak, orijinal ambalajında depolayın (nemle karbondioksit açığa çıkar).'
                if lang == 'TR' else
                'Store in a dry place, protected from moisture, in the original packaging (releases carbon '
                'dioxide with moisture).']
    else:
        # H kodu bazlı depolama metinleri (slot 72) — H224/H225/H226/H314 için özel
        sec72 = generate_section(72, h_codes)
        _sec72_bullets = adapt_list_for_form(sec72['bullets'], _sec_form)

    # Katı/toz forma özgü depolama notları — H228 olmasa bile gerekli (yalnız diğer diller)
    if _b7_is_solid and lang not in ('TR', 'EN'):
        _solid_storage_TR = [
            'Kuru, serin ve iyi havalandırılmış alanda depolayın.',
            'Toz oluşumundan kaçının; kapları kapalı tutun.',
        ]
        _solid_storage_EN = [
            'Store in a dry, cool and well-ventilated area.',
            'Avoid dust generation; keep containers closed.',
        ]
        _extra_storage = _solid_storage_TR if lang == 'TR' else _solid_storage_EN
        # ATEX uyarısı — powder formu veya powder_fine/nano alt kategorisi
        if _b7_form == 'powder' or _b7_form_sub in ('powder_fine', 'powder_nano'):
            _extra_storage.append(
                'Toz-hava bulutu patlama riski: ATEX 2014/34/AB gerekliliklerini göz önünde bulundurun; antistatik ekipman kullanın.'
                if lang == 'TR' else
                'Risk of dust-air cloud explosion: consider ATEX 2014/34/EU requirements; use antistatic equipment.'
            )
        _sec72_bullets = _extra_storage + _sec72_bullets

    if _sec72_bullets:
        story += bullet_list(_sec72_bullets, styles)
        _incompat_idx = next((i for i in range(len(story) - 1, -1, -1)
                              if _INCOMPAT_SLOT in str(getattr(story[i], 'text', ''))), None)
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
    story.append(CondPageBreak(45*mm))   # 8 başlığı + 8.1 tablo başlığı sayfa sonunda tek kalmasın
    story += section_block(section_title(lang, 8), styles)
    story += sub_block(f"8.1 {sub_title(lang,'8.1')}", styles)
    # Sınır değeri olmayan ve sınıflandırılmamış bileşenler (su vb.) 8.1 tablosuna girmez — Bölüm 3 ile aynı ilke
    oel_rows = get_oel_table([c for c in components if _sec3_needed(c)])
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
            _orow = format_oel_row(row, lang)
            if _orow and str(_orow[0]).strip() in _hidden_cas:   # SEA Md.26 — CAS gösterilmez
                _orow = ['Gizli*' if lang == 'TR' else 'Confidential*'] + list(_orow[1:])
            tbl_data.append(_orow)
        story.append(data_table(tbl_data, [22*mm, 45*mm, 35*mm, 35*mm, 25*mm], styles))
        # Kaynak: her satırın yasal dayanağı (data/tr_oel_limits.json 'regulation'; scripts/verify_tr_oel.py)
        _regs = {r.get('regulation') for r in oel_rows}
        if '28733 Ek-1' in _regs:
            story.append(Paragraph(
                'Kaynak: 12.08.2013 tarihli ve 28733 sayılı Kimyasal Maddelerle Çalışmalarda Sağlık ve Güvenlik '
                'Önlemleri Hakkında Yönetmelik Ek-1 (Değişik: RG 20.10.2023/32345)' if lang == 'TR' else
                'Source: Turkish Regulation on Health and Safety Measures for Work with Chemical Agents '
                '(OG No. 28733, 12.08.2013) Annex-1 (amended OG 20.10.2023/32345)', styles['small']))
        if '28730 Ek-2' in _regs:
            story.append(Paragraph(
                'Kaynak: 06.08.2013 tarihli ve 28730 sayılı Kanserojen veya Mutajen Maddelerle Çalışmalarda Sağlık '
                've Güvenlik Önlemleri Hakkında Yönetmelik Ek-2' if lang == 'TR' else
                'Source: Turkish Regulation on Health and Safety Measures for Work with Carcinogens or Mutagens '
                '(OG No. 28730, 06.08.2013) Annex-2', styles['small']))
        if any(r.get('regulation') == '—' for r in oel_rows):
            story.append(Paragraph(
                'TR sınır değeri yok: bu bileşen için Türkiye mevzuatında (28733 sayılı Yönetmelik Ek-1; 28730 '
                'sayılı Yönetmelik Ek-2) mesleki maruziyet sınır değeri belirlenmemiştir.' if lang == 'TR' else
                'No TR limit: no occupational exposure limit value is set for this component in Turkish '
                'legislation (OG 28733 Annex-1; OG 28730 Annex-2).', styles['small']))
        # KKDİK Ek-2 A 8.1.2: tavsiye edilen izleme usulleri
        if lang in ('TR', 'EN'):
            story.append(Paragraph(
                'İzleme: işyeri havasındaki konsantrasyon ölçümleri TS EN 689 (İşyeri maruziyeti — kimyasal '
                'maddelerin solunum yoluyla maruziyetinin ölçülmesi — sınır değerlere uygunluğun test edilmesi '
                'için strateji) esas alınarak yapılmalıdır.' if lang == 'TR' else
                'Monitoring: workplace air measurements should follow EN 689 (Workplace exposure — measurement of '
                'exposure by inhalation to chemical agents — strategy for testing compliance with occupational '
                'exposure limit values).', styles['small']))
    else:
        story.append(Paragraph(
            'Ürünün bileşenleri için Türkiye mevzuatında (28733 sayılı Yönetmelik Ek-1; 28730 sayılı Yönetmelik '
            'Ek-2) mesleki maruziyet sınır değeri bulunmamaktadır.' if lang == 'TR' and components else
            S(lang, 'oel_reference'), styles['body']))
    # KKDİK Ek-2 A 8.1.4: DNEL/PNEC — karışım için değer verilmiyorsa bu belirtilir
    if lang in ('TR', 'EN') and len(sds_data.get('components') or []) > 1:
        story.append(Paragraph(
            'DNEL/PNEC: karışım için belirlenmemiştir; bileşenlere ait değerler için hammadde tedarikçisinin '
            'GBF\'sine bakınız.' if lang == 'TR' else
            'DNEL/PNEC: not established for the mixture; for component values refer to the raw material '
            'supplier\'s SDS.', styles['small']))

    # Not: "Genel toz limiti (PNOC) 10/4 mg/m³ — 28733 Ek-1" satırı kaldırıldı: resmî yönetmelik
    # metninde (Ek-1) böyle bir değer yoktur.

    story += sub_block(f"8.2 {sub_title(lang,'8.2')}", styles)

    # 8.2.1 Uygun mühendislik kontrolleri (KKDİK Ek-2 8.2.1)
    _f82 = (product.get('form') or 'liquid')
    _h82 = set(all_h_codes or []) | set(h_codes or [])
    if _f82 in ('solid', 'powder'):
        _eng = ('Toz oluşumunu en aza indirin; toz oluşan işlemlerde lokal egzoz havalandırması kullanın.'
                if lang == 'TR' else 'Minimise dust generation; use local exhaust ventilation where dust is formed.')
    elif _f82 in ('gas', 'aerosol'):
        _eng = ('Yeterli genel ve lokal egzoz havalandırması sağlayın; kapalı alanlarda gaz/buhar birikmesini önleyin.'
                if lang == 'TR' else 'Provide adequate general and local exhaust ventilation; prevent accumulation of '
                'gas/vapour in enclosed spaces.')
    elif _h82 & {'H224', 'H225', 'H226', 'H330', 'H331', 'H332', 'H335', 'H336', 'H334'}:
        _eng = ('Buhar/sis oluşan işlemlerde yeterli genel ve lokal egzoz havalandırması sağlayın.'
                if lang == 'TR' else 'Provide adequate general and local exhaust ventilation where vapour/mist is formed.')
    else:
        _eng = ('Yeterli genel havalandırma sağlayın.' if lang == 'TR' else 'Provide adequate general ventilation.')
    # Mesleki maruz kalma sınır değeri olan bileşen varsa (8.1) — sınır değerin altında tutma
    if any(r.get('tw_ppm') or r.get('tw_mgm3') or r.get('stel_ppm') or r.get('stel_mgm3') for r in (oel_rows or [])):
        _eng += (' Ortam konsantrasyonunu 8.1\'deki mesleki maruz kalma sınır değerlerinin altında tutmak için '
                 'gerektiğinde lokal egzoz havalandırması kullanın.' if lang == 'TR' else
                 ' Where necessary use local exhaust ventilation to keep airborne concentrations below the '
                 'occupational exposure limits in 8.1.')
    story.append(Paragraph(
        f"<b>8.2.1 {'Uygun mühendislik kontrolleri' if lang == 'TR' else 'Appropriate engineering controls'}:</b> "
        f"{_eng}", styles['body']))
    story.append(Paragraph(
        f"<b>8.2.2 {'Bireysel koruyucu önlemler, örneğin kişisel koruyucu ekipman' if lang == 'TR' else 'Individual protection measures, such as personal protective equipment'}:</b>",
        styles['body']))

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

    # KKDİK Ek-2 A 8.2.2.2 sırası ve adları: (a) göz/yüz, (b) cilt — (i) eller, (ii) diğerleri,
    # (c) solunum sistemi, (d) ısıl zararlar (yalnız ısıl zarar arz eden üründe)
    _TR822 = lang == 'TR'
    _lbl822 = {
        'eyes':  'a) Göz/yüz korunması' if _TR822 else 'a) Eye/face protection',
        'hands': ('b) Cildin korunması — i) Ellerin korunması' if _TR822
                  else 'b) Skin protection — i) Hand protection'),
        'body':  'b) Cildin korunması — ii) Diğerleri' if _TR822 else 'b) Skin protection — ii) Other',
        'resp':  'c) Solunum sisteminin korunması' if _TR822 else 'c) Respiratory protection',
        'heat':  'd) Isıl zararlar' if _TR822 else 'd) Thermal hazards',
    }
    _thermal = None
    if 'H281' in _h82:   # soğutulmuş sıvılaştırılmış gaz — soğuk yanığı
        _thermal = ('Soğuğa karşı yalıtımlı koruyucu eldiven (EN 511) ve yüz siperi (EN 166) kullanın.' if _TR822
                    else 'Wear cold-insulating gloves (EN 511) and a face shield (EN 166).')

    if _ppe_engine_data:
        # Yeni PPE motoru verisi mevcut — detaylı tablo
        _na = term(lang, 'not_applicable')
        ppe_rows = [
            [_lbl822['eyes'],  _ppe_items_text(_ppe_engine_data.get('eyes', [])) or _na],
            [_lbl822['hands'], _ppe_items_text(_ppe_engine_data.get('hands', [])) or _na],
            [_lbl822['body'],  _ppe_items_text(_ppe_engine_data.get('body', [])) or _na],
            [_lbl822['resp'],  _ppe_items_text(_ppe_engine_data.get('respiratory', [])) or _na],
        ]
        if _thermal:
            ppe_rows.append([_lbl822['heat'], _thermal])
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
            'eyes':   _lbl822['eyes'],
            'gloves': _lbl822['hands'],
            'body':   _lbl822['body'],
            'resp':   _lbl822['resp'],
        }
        ppe_rows = []
        for key, label in ppe_map.items():
            val = ppe_old.get(key, term(lang, 'not_applicable'))
            ppe_rows.append([label, val])
        if _thermal:
            ppe_rows.append([_lbl822['heat'], _thermal])
        story.append(data_table(ppe_rows, [50*mm, 130*mm], styles, header=False))

    # 8.2.2.2(b) — eldiven: malzeme, kalınlık ve minimum delinme süresi (glove_service, EN ISO 374-1)
    _glove = sds_data.get('glove') or {}
    # KKDİK Ek-2 A 8.2.2.1: yangına özgü KKD için Bölüm 5'e atıf
    if lang in ('TR', 'EN'):
        story.append(Paragraph('Yangın sırasında kullanılacak koruyucu ekipman için Bölüm 5.3\'e bakınız.'
                               if lang == 'TR' else
                               'For protective equipment during fire-fighting, see Section 5.3.', styles['small']))
    if _glove.get('note'):
        story.append(Paragraph(_glove['note'], styles['small']))
    else:
        # KKDİK Ek-2 A 8.2.2.2(b)(i): eldiven kartı uygulanmadığında (ürün cilt için sınıflandırılmamış) da
        # delinme süresi belirtilir — EN ISO 374-1 Tip C asgari performans (≥10 dk, EN 16523-1 seviye 1)
        story.append(Paragraph(
            ('Ürün cilt için sınıflandırılmamıştır; eldiven tavsiye niteliğindedir. Sıçrama temasında en az '
             'EN ISO 374-1 Tip C (delinme süresi ≥ 10 dk, seviye 1); uzun süreli/sürekli temasta delinme süresi '
             '≥ 480 dk (seviye 6) olan eldiven seçin. Eldivenler hasar ve kirlenme durumunda değiştirilmelidir.')
            if lang == 'TR' else
            ('The product is not classified for skin effects; gloves are recommended. For splash contact use at '
             'least EN ISO 374-1 Type C (breakthrough time ≥ 10 min, level 1); for prolonged contact choose gloves '
             'with breakthrough time ≥ 480 min (level 6). Replace gloves when damaged or contaminated.'),
            styles['small']))

    # 8.2.3 Çevresel maruz kalma kontrolleri (KKDİK Ek-2 8.2.3)
    _env = ('Ürünün kanalizasyona, yüzey ve yeraltı sularına ve toprağa karışmasını önleyin '
            '(bkz. Bölüm 6.2 ve 13).' if lang == 'TR' else
            'Prevent the product from entering drains, surface water, groundwater and soil (see Sections 6.2 and 13).')
    if _h82 & {'H400', 'H410', 'H411', 'H412', 'H413'}:
        _env += (' Ürün sucul ortam için zararlı olarak sınıflandırılmıştır.' if lang == 'TR'
                 else ' The product is classified as hazardous to the aquatic environment.')
    story.append(Paragraph(
        f"<b>8.2.3 {'Çevresel maruz kalma kontrolleri' if lang == 'TR' else 'Environmental exposure controls'}:</b> "
        f"{_env}", styles['body']))

    # EUH212 nano toz uyarısı — B8 özel notu (CLP (AB) 2021/2030)
    _euh_codes = euh.get('euh_codes', [])
    if 'EUH212' in _euh_codes:
        _euh212_note = (
            '<b>Nano toz uyarısı (EUH212):</b> Tehlikeli nano boyutlu partiküller oluşabilir. '
            'Toz solumaktan kaçının. FFP3 solunum koruyucu (EN 149) veya P3 filtreli yarım yüz '
            'maskesi (EN 14387) kullanın. Nano tozlar için standart FFP2 yeterliliği değerlendirin.'
            if lang == 'TR' else
            '<b>Nano dust warning (EUH212):</b> Hazardous nano-sized particles may be generated. '
            'Avoid inhalation of dust. Use FFP3 respirator (EN 149) or half-face mask with P3 '
            'filter (EN 14387). Assess adequacy of standard FFP2 for nano dusts.'
        )
        story.append(Paragraph(_euh212_note, styles['body']))

    story.append(CondPageBreak(60*mm))   # yalnız sayfa sonunda yer yoksa yeni sayfa (boş sayfa kalmasın)

    # ─────────────────────────────────────────────────────────────────────────
    # BÖLÜM 9 — Fiziksel Özellikler
    # ─────────────────────────────────────────────────────────────────────────
    story += section_block(section_title(lang, 9), styles)
    story += sub_block(f"9.1 {sub_title(lang,'9.1')}", styles)

    na = term(lang,'not_available')

    _prod_form     = product.get('form', '')
    _prod_form_sub = product.get('form_sub', '') or ''
    _is_solid_form = _prod_form in ('solid', 'powder')
    _is_gas_form   = _prod_form == 'gas'
    _is_polymer    = _prod_form_sub == 'polymer'

    # PCN zorunlu alanlar kontrolü — yalnızca API yanıtına/uygulama içi uyarıya eklenir,
    # PDF çıktısına iç teknik mesaj basılmaz.
    _pcn_base = ['ph', 'density', 'flash_point']
    # Gaz ve katı formda parlama noktası uygulanamaz — PCN kontrolünden çıkar
    if _is_solid_form or _is_gas_form:
        _pcn_base = [k for k in _pcn_base if k != 'flash_point']
    pcn_required = _pcn_base
    pcn_missing = [k for k in pcn_required if not phys.get(k)]

    # Not: "⚠ Ürün formu sıvı ancak … bileşen listesini kontrol edin" program uyarısı GBF'ye
    # basılmıyor (resmî belgeye iç teknik mesaj girmez; Bölüm 9(f) zaten gerekçeyi yazar).

    # Sıvı ürün için viskozite ve çözünürlük eksikliği uyarısı
    # KKDİK Ek-2 Bölüm 9: Sıvı karışımlarda bu parametreler "Bilgi yok" bırakılamaz
    def _method_note(key):
        """Hesap yöntemi/kaynağı notu — KKDİK Ek-2 §9 REACH Annex II zorunluluğu"""
        pm = phys_methods.get(key, {})
        if not pm:
            return ''
        # Değer yoksa ("Belirlenmemiştir") yöntem/kaynak notu yazılmaz — "hesaplanmış" çelişkisi
        _v = phys.get(key)
        _vd = (_v.get('display') if isinstance(_v, dict) else _v) or ''
        if (isinstance(_v, dict) and (_v.get('nd') or _v.get('na'))) or str(_vd).strip() in (
                '', 'Belirlenmemiştir', 'Bilgi yok', 'Uygulanamaz', 'Not determined', 'No data'):
            return ''
        if pm.get('note_text'):
            return (f'<br/><font size="6" color="#888888">{pm["note_text"]}</font>'
                    if lang == 'TR' else '')
        std = _re.sub(r'<[^>]+>', '', pm.get('standard') or '').strip()
        if std and ' / ' in std:
            std = std.split(' / ')[0].strip()
        err = pm.get('error_pct')
        if pm.get('method') == 'Kullanıcı beyanı':
            parts = ['kullanıcı beyanı' if lang == 'TR' else 'user-declared']
        elif pm.get('measured'):
            parts = ['ölçülen']
            if std and std not in ('', '—'):
                parts.append(std)
        else:
            parts = ['hesaplanmış']
            # Referans koşulu: bileşen verileri 20 °C (iç tablo) / 15–30 °C (PubChem, aralık dışı alınmaz)
            if key in ('vapor_pressure', 'density', 'rel_density'):
                parts.append('20–25 °C' if lang == 'TR' else '20–25 °C')
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
            if raw_display == 'Belirlenmemiştir' and lang != 'TR':
                raw_display = na
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

    def _appearance():
        """Görünüm — yalnız "Katı"/"Toz" yazılmışsa seçilen alt tür eklenir (örn. "Katı (tablet)")."""
        txt = _text(f'appearance_{lang}') or _text('appearance') or na
        _sub = {'tablet': 'tablet', 'granule': 'granül', 'flake': 'pul', 'powder_fine': 'toz',
                'powder_coarse': 'kaba toz', 'powder_nano': 'nano toz', 'block': 'blok',
                'polymer': 'polimer'}.get(str(sds_data.get('form_sub') or product.get('form_sub') or ''))
        if lang == 'TR' and _sub and str(txt).strip().lower() in ('katı', 'kati', 'toz', 'solid', 'powder'):
            return f'{str(txt).strip()} ({_sub})'
        return txt

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

    # ── KKDİK Ek-2 9.1 (a)–(p): 20 özelliğin hepsi, yönetmelikteki sırayla yazılır ──────────
    # "Belirli bir özelliğin geçerli olmadığı veya … bilgilerin mevcut olmadığı belirtilmiş ise,
    #  nedenleri belirtilir." → boş satır gizlenmez; ürünün fiziksel haline göre gerekçe yazılır.
    # Kullanıcının girdiği / ölçülen değer her zaman önce gelir.
    _TR = lang == 'TR'
    _is_aerosol_form = _prod_form == 'aerosol'
    _is_liq_form = not (_is_solid_form or _is_gas_form or _is_aerosol_form)
    _hs = {str(h)[:4] for h in (list(h_codes) + list(clp.get('all_h_codes') or []))}
    _NO_DATA_VALS = {na, '', 'Veri yok', 'Veri Yok', 'Bilgi yok', 'Bilgi Yok',
                     'No data available', 'No data', 'N/A', '-', 'Belirlenmemiştir'}
    _ND    = ('Belirlenmemiştir (karışım için test yapılmamıştır)' if _TR
              else 'Not determined (no test performed on the mixture)')
    _NA_S  = 'Uygulanamaz (katı)' if _TR else 'Not applicable (solid)'
    _NA_G  = 'Uygulanamaz (gaz)' if _TR else 'Not applicable (gas)'

    def _have(v):
        return v not in (None, '') and _re.sub(r'<[^>]+>', '', str(v)).strip() not in _NO_DATA_VALS

    def _or(v, solid=None, gas=None, aerosol=None, default=None):
        """Değer varsa değer; yoksa fiziksel hale göre gerekçe."""
        if _have(v):
            return v
        if _is_solid_form and solid:
            return solid
        if _is_gas_form and gas:
            return gas
        if _is_aerosol_form and aerosol:
            return aerosol
        return default or _ND

    def _hlist(codes):
        return ', '.join(sorted(_hs & codes))

    def _L(tr, en):
        return tr if _TR else en

    # (a) Görünüm — fiziksel hal ve renk (katıda tane boyutu varsa)
    _state_txt = ({'solid': 'Katı', 'powder': 'Toz', 'gas': 'Gaz', 'aerosol': 'Aerosol', 'paste': 'Pasta',
                   'liquid': 'Sıvı'} if _TR else
                  {'solid': 'Solid', 'powder': 'Powder', 'gas': 'Gas', 'aerosol': 'Aerosol', 'paste': 'Paste',
                   'liquid': 'Liquid'})
    _app = _appearance()
    if not _have(_app):
        _app = _state_txt.get(_prod_form or 'liquid', _state_txt['liquid'])
    _col = _text('color')
    if _have(_col):
        _app = f"{_app}; {_L('renk', 'colour')}: {_col}"
    elif str(_app).strip().lower() in {v.lower() for v in _state_txt.values()}:
        # KKDİK Ek-2 9.1(a) renk ister; girilmemişse renk uydurulmaz, eksik olduğu açıkça yazılır
        _app = f"{_app}; {_L('renk: belirtilmemiştir', 'colour: not specified')}"
    _ps = phys.get('particle_size')
    _ps = _ps.get('display') if isinstance(_ps, dict) else _ps
    if _is_solid_form and _have(_ps):
        _app = f"{_app}; {_L('tane boyutu', 'particle size')}: {_ps}"
    # KKDİK Ek-2 9.1(a): katıda granülometri ve özgül yüzey alanı
    _ssa = phys.get('specific_surface')
    _ssa = _ssa.get('display') if isinstance(_ssa, dict) else _ssa
    if _is_solid_form and _have(_ssa):
        _app = f"{_app}; {_L('özgül yüzey alanı', 'specific surface area')}: {_ssa}"

    # (ç) pH — Ek-2 9.1(ç): ürünün kendisinin ya da sulu çözeltisinin pH'ı; çözeltiyse konsantrasyonu da
    # belirtilir. Konsantrasyon yalnız kullanıcı girdiyse yazılır (önceden katıda girilmese de "%1" basılıyordu).
    _ph_conc_raw = str(phys.get('ph_conc') or '').strip()
    _ph_val = _pv_ph()
    _ph_numeric = bool(_re.match(r'^\s*[<>≤≥~]?\s*\d', str(_ph_val or '')))
    if _ph_conc_raw and _have(_ph_val) and _ph_numeric:
        _ph_lbl_row = _L(f'pH (%{_ph_conc_raw} sulu çözeltide)', f'pH ({_ph_conc_raw}% aqueous solution)')
    elif _is_solid_form and _have(_ph_val) and _ph_numeric:
        _ph_lbl_row = _L('pH (sulu çözeltide — konsantrasyon belirtilmemiştir)',
                         'pH (aqueous solution — concentration not stated)')
    else:
        _ph_lbl_row = phys_prop(lang, 'ph')

    # (d) Erime/donma noktası (polimerde yumuşama noktası)
    _mp_lbl = (_L('Yumuşama noktası (Vicat/VST)', 'Softening point (Vicat/VST)') if _is_polymer
               else _L('Erime noktası/donma noktası', 'Melting point/freezing point'))

    # (f) Parlama noktası
    _fp_na = None
    if _is_aerosol_form:
        _aer_h = 'H222' if 'H222' in _hs else ('H223' if 'H223' in _hs else '')
        _fp_na = _L(f'Uygulanamaz — aerosol (bkz. Bölüm 2{", " + _aer_h if _aer_h else ""}; SEA Ek-1 2.3)',
                    'Not applicable — aerosol (see Section 2)')
    _fp_default = _ND
    if _is_liq_form and not (_hs & {'H224', 'H225', 'H226'}):
        _fp_default = _ND + _L('; alevlenir sıvı olarak sınıflandırılmamıştır',
                               '; not classified as flammable liquid')
    _fp_val = _or(_pv('flash_point', '°C'), solid=_NA_S, gas=_NA_G, aerosol=_fp_na, default=_fp_default)

    # (e) İlk kaynama noktası
    _bp_solid = (_L('Uygulanamaz (polimer — belirli kaynama noktası yok)',
                    'Not applicable (polymer — no defined boiling point)') if _is_polymer else _NA_S)
    _bp_val = _or(_pv('boiling_point', '°C'), solid=_bp_solid)

    # (ğ) Alevlenirlik (katı, gaz)
    if _is_solid_form:
        _fl_val = (_L(f'Alevlenir katı ({_hlist({"H228"})})', f'Flammable solid ({_hlist({"H228"})})')
                   if 'H228' in _hs else
                   _L('Alevlenir katı olarak sınıflandırılmamıştır', 'Not classified as flammable solid'))
    elif _is_gas_form:
        _fl_val = (_L(f'Alevlenir gaz ({_hlist({"H220", "H221"})})', f'Flammable gas ({_hlist({"H220", "H221"})})')
                   if _hs & {'H220', 'H221'} else
                   _L('Alevlenir gaz olarak sınıflandırılmamıştır', 'Not classified as flammable gas'))
    elif _is_aerosol_form:
        _fl_val = (_L(f'Alevlenir aerosol ({_hlist({"H222", "H223"})})',
                      f'Flammable aerosol ({_hlist({"H222", "H223"})})')
                   if _hs & {'H222', 'H223'} else
                   _L('Alevlenir aerosol olarak sınıflandırılmamıştır', 'Not classified as flammable aerosol'))
    else:
        _fl_val = _L('Uygulanamaz (sıvı — bkz. parlama noktası)', 'Not applicable (liquid — see flash point)')

    # (h) Alevlenirlik / patlama limitleri
    _ex_val = None
    _lel_raw, _uel_raw = phys.get('lel'), phys.get('uel')
    # Hesaplanan LEL/UEL yalnız alevlenir bileşenlerin buharından çıkar (su yok sayılır); alevlenir olarak
    # sınıflandırılmamış sulu üründe (su > %50) bileşenin kendi limitleri ürününmüş gibi basılıyordu
    # (örn. %0,2 etanolamin → %3,0–23,5). Ölçülen / kullanıcı beyanı değerler etkilenmez.
    _lel_pm = phys_methods.get('lel', {}) or {}
    _lel_calc = bool(_lel_pm) and not _lel_pm.get('measured') and _lel_pm.get('method') != 'Kullanıcı beyanı'
    _water_pct = sum(float(c.get('concMax') or c.get('conc') or c.get('concentration') or 0)
                     for c in components if str(c.get('cas_no') or c.get('cas') or '').strip() == '7732-18-5')
    _flam_cls = bool((set(h_codes) | set(all_h_codes or [])) & {'H220', 'H221', 'H222', 'H223', 'H224', 'H225',
                                                                 'H226', 'H228'})
    if (_lel_raw or _uel_raw) and _lel_calc and _water_pct > 50 and not _flam_cls:
        _ex_val = _L('Uygulanamaz — sulu, alevlenir olarak sınıflandırılmamış ürün',
                     'Not applicable — aqueous product not classified as flammable')
    elif _lel_raw or _uel_raw:
        _lel_str = _lel_raw.get('display') if isinstance(_lel_raw, dict) else (str(_lel_raw) if _lel_raw else '?')
        _uel_str = _uel_raw.get('display') if isinstance(_uel_raw, dict) else (str(_uel_raw) if _uel_raw else '?')
        _num = lambda x: bool(_re.match(r'^\s*[<>≤≥~]?\s*\d', str(x or '')))
        if _num(_lel_str) and not _num(_uel_str):
            # Le Chatelier yalnız alt sınırı verir (ISO 10156 4.5.1; gaz ve sıvı buharı) — "%x – %?" basılmaz
            _ex_val = _L(f"Alt: %{_lel_str}; üst: belirlenmemiştir (hesapla belirlenemez — ISO 10156:2017 4.5.1; ölçülmemiştir)",
                         f"Lower: {_lel_str} %; upper: not determined (cannot be calculated; not measured)") \
                + _method_note('lel')
        elif _num(_lel_str) or _num(_uel_str):
            _ex_val = f"%{_lel_str} – %{_uel_str}" + _method_note('lel')
        # Sayısal değer yoksa (örn. aerosolde hesap yazılmadı) "%Belirlenmemiştir – %…" basılmaz; aşağıdaki
        # genel "Belirlenmemiştir" ifadesi kullanılır

    # (ı) Buhar basıncı
    _vp_raw = phys.get('vapor_pressure')
    _vp_display = (_vp_raw.get('display') if isinstance(_vp_raw, dict)
                   else (str(_vp_raw) if _vp_raw not in (None, '') else None))
    _vp_val = None
    if _have(_vp_display):
        _vp_val = (_vp_display if any(u in _vp_display for u in ('hPa', 'kPa', 'mmHg', 'bar', 'Pa'))
                   else f"{_vp_display} hPa") + _method_note('vapor_pressure')
    elif phys.get('vapor_pressure_num'):
        _vp_val = f"{phys.get('vapor_pressure_num')} hPa"

    # (i) Buhar yoğunluğu — bağıl değer, referans hava = 1 (birimsiz sayı tek başına anlamsız)
    _vd_val = _pv('vapor_density')
    if (_have(_vd_val) and _re.match(r'^\s*[<>≤≥~]?\s*\d', str(_vd_val))
            and 'hava' not in str(_vd_val).lower() and 'air' not in str(_vd_val).lower()):
        _vd_parts = str(_vd_val).split('<br/>', 1)
        _vd_val = _vd_parts[0] + _L(' (hava = 1)', ' (air = 1)') + ('<br/>' + _vd_parts[1] if len(_vd_parts) > 1 else '')

    # (j) Bağıl yoğunluk — yoksa yoğunluk
    _rd_val = _pv('rel_density')
    _rd_lbl = _L('j) Bağıl yoğunluk', 'm) Relative density')
    if not _have(_rd_val):
        _d = _pv('density', 'g/cm³')
        if _have(_d):
            _rd_val = _d
            _rd_lbl = _L('j) Bağıl yoğunluk (yoğunluk)', 'm) Relative density (density)')

    # (l) Dağılım katsayısı
    _kow_default = _L('Karışım için belirlenmemiştir (bileşen verileri için bkz. Bölüm 12)',
                      'Not determined for the mixture (see Section 12 for components)')

    # (ö) / (p) Patlayıcı ve oksitleyici özellikler — sınıflandırmadan
    _EXP = {'H200', 'H201', 'H202', 'H203', 'H204', 'H205', 'H240', 'H241'}
    _OX = {'H270', 'H271', 'H272'}
    _expl_val = (_L(f'Patlayıcı özellik ({_hlist(_EXP)})', f'Explosive properties ({_hlist(_EXP)})')
                 if (_hs & _EXP or phys.get('is_explosive')) else
                 _L('Patlayıcı olarak sınıflandırılmamıştır', 'Not classified as explosive'))
    _ox_val = (_L(f'Oksitleyici özellik ({_hlist(_OX)})', f'Oxidising properties ({_hlist(_OX)})')
               if (_hs & _OX or phys.get('is_oxidising')) else
               _L('Oksitleyici olarak sınıflandırılmamıştır', 'Not classified as oxidising'))

    phys_rows = [
        [_L('a) Görünüm', 'a) Appearance'), _app],
        # Ek-2 9.1: bilgi yoksa nedeni belirtilir — çıplak "Belirlenmemiştir" basılmaz
        [_L('b) Koku', 'b) Odour'), _or(_text('odor'), default=_L('Belirlenmemiştir (koku değerlendirmesi yapılmamıştır)',
                                                                 'Not determined (odour not assessed)'))],
        [_L('c) Koku eşiği', 'c) Odour threshold'), _or(_pv('odour_threshold'))],
        [_L('ç) ', 'd) ') + _ph_lbl_row, _or(_ph_val, gas=_NA_G)],
        [_L('d) ', 'e) ') + _mp_lbl, _or(_pv('melting_point', '°C'))],
        [_L('e) İlk kaynama noktası ve kaynama aralığı', 'f) Initial boiling point and boiling range'), _bp_val],
        [_L('f) Parlama noktası', 'g) Flash point'), _fp_val],
        [_L('g) Buharlaşma hızı', 'h) Evaporation rate'), _or(_text('evap_rate'), solid=_NA_S, gas=_NA_G)],
        [_L('ğ) Alevlenirlik (katı, gaz)', 'i) Flammability (solid, gas)'), _fl_val],
        [_L('h) Üst/alt alevlenirlik veya patlayıcı limitleri', 'j) Upper/lower flammability or explosive limits'),
         _or(_ex_val)],
        [_L('ı) Buhar basıncı', 'k) Vapour pressure'), _or(_vp_val, solid=_NA_S)],
        # Katıda bileşen MW'sinden ideal gaz hesabı anlamsız → her durumda "Uygulanamaz (katı)"
        [_L('i) Buhar yoğunluğu', 'l) Vapour density'), _NA_S if _is_solid_form else _or(_vd_val)],
        [_rd_lbl, _or(_rd_val)],
        [_L('k) Çözünürlük', 'n) Solubility'), _or(_pv('solubility', 'mg/L'))],
        [_L('l) Dağılım katsayısı: n-oktanol/su', 'o) Partition coefficient: n-octanol/water'),
         _or(_pv('log_kow'), default=_kow_default)],
        [_L('m) Kendiliğinden tutuşma sıcaklığı', 'p) Auto-ignition temperature'), _or(_pv('auto_ignition', '°C'))],
        [_L('n) Bozunma sıcaklığı', 'q) Decomposition temperature'), _or(_pv('decomposition_temp', '°C'))],
        [_L('o) Akışkanlık (viskozite)', 'r) Viscosity'), _or(_pv('viscosity', 'cSt @40°C'), solid=_NA_S, gas=_NA_G)],
        [_L('ö) Patlayıcı özellikler', 's) Explosive properties'), _expl_val],
        [_L('p) Oksitleyici özellikler', 't) Oxidising properties'), _ox_val],
    ]
    story.append(data_table(phys_rows, [75*mm, 105*mm], styles, header=False))

    # 9.2 Diğer bilgiler — değeri olan ek parametreler; yoksa açıkça belirtilir
    _other = []
    _voc_content = sds_data.get('voc_content')
    if _voc_content is not None:
        _other.append([_L('VOC içeriği (2004/42/EC)', 'VOC content (2004/42/EC)'), f"{_voc_content} g/L"])
    _hc = phys.get('henry_constant')
    if isinstance(_hc, dict) and _have(_hc.get('display')):
        _other.append([_L('Henry sabiti', "Henry's law constant"), _hc['display']])
    if _is_solid_form:
        for _k, _lt, _le, _u in (('bulk_density', 'Dökme yoğunluğu', 'Bulk density', 'kg/m³'),
                                 ('dispersibility', 'Dağılabilirlik', 'Dispersibility', ''),
                                 ('hygroscopicity', 'Higroskopiklik', 'Hygroscopicity', '')):
            _v = _pv(_k, _u) if _u else (phys.get(_k) or None)
            if _have(_v):
                _other.append([_L(_lt, _le), _v])
    story += sub_block(f"9.2 {sub_title(lang,'9.2')}", styles)
    if _other:
        story.append(data_table(_other, [75*mm, 105*mm], styles, header=False))
    else:
        story.append(Paragraph(_L('Ek bilgi bulunmamaktadır.', 'No additional information available.'),
                               styles['body']))

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
    if _effervescent and not any(h in h_codes for h in ['H260', 'H261']):
        avoid_parts.append('Nem ve su ile temas (kullanım dışında)' if lang == 'TR'
                           else 'Contact with moisture and water (outside use)')
    avoid_str = ('; '.join(avoid_parts) + '.') if avoid_parts else (
        'Normal kullanım ve depolama koşullarında kaçınılması gereken özel bir durum bilinmemektedir.'
        if lang == 'TR' else 'No specific conditions to avoid are known under normal conditions of use and storage.'
    )

    # ── 10.5 Bağdaşmayan maddeler ────────────────────────────────────────────
    # pre-fetch varsa (main.py/review_endpoint'in async handler'ında önceden çekildi):
    #   None  → fetch başarısız/timeout → senkron fallback dene
    #   list  → kullan (boş liste bile olsa gerçek sonuç, tekrar sorgu yapma)
    _pre = sds_data.get('_cameo_incompat')
    if _pre is not None:
        _api_items = _pre
    else:
        try:
            from app.services.cameo_service import get_mixture_incompatibilities as _get_incompat
            _api_items = _get_incompat(components)
        except Exception:
            _api_items = []
    incompat_set = set(_api_items)

    if is_flammable:
        incompat_set.add('güçlü oksitleyiciler' if lang=='TR' else 'strong oxidising agents')
    if has_alcohol:
        incompat_set.add('alkali metaller' if lang=='TR' else 'alkali metals')
        incompat_set.add('alüminyum (yüksek sıcaklıkta)' if lang=='TR'
                         else 'aluminium (at elevated temperatures)')
    if is_acid:
        incompat_set.add('bazlar ve aktif metaller' if lang=='TR' else 'bases and reactive metals')
    # Asit içeren ürün + hipoklorit (çamaşır suyu) → klor gazı. KKDİK Ek-2 10.5: kaçınılması
    # gereken maddeler sıralanır (yönetmelikte asitli ürünler için hazır ifade yok; yalnız listeye eklenir).
    # Ürünün kendisi hipoklorit içeriyorsa EUH206/EUH031 zaten uyarır.
    _ACID_CAS = {'77-92-9', '5329-14-6', '7664-38-2', '7647-01-0', '7664-93-9', '7697-37-2',
                 '64-18-6', '64-19-7', '50-21-5', '79-33-4', '79-14-1', '144-62-7', '7681-38-1',
                 '6915-15-7', '87-69-4', '75-75-2', '10043-35-3'}
    _HYPOCHLORITE_CAS = {'7681-52-9', '7778-54-3', '10022-70-5'}
    if (comp_cas_set & _ACID_CAS) and not (comp_cas_set & _HYPOCHLORITE_CAS):
        incompat_set.add('hipokloritler (çamaşır suyu)' if lang == 'TR' else 'hypochlorites (bleach)')
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
    # 7.2'deki yer tutucuyu 10.5 listesiyle doldur (iki bölüm aynı maddeleri adıyla söyler)
    if _incompat_idx is not None:
        _inc_low = ', '.join(sorted(incompat_set))
        story[_incompat_idx] = Paragraph(
            f"• {'Şu maddelerden uzak depolayın' if lang == 'TR' else 'Store away from'}: {_inc_low} "
            f"({'bkz. Bölüm 10.5' if lang == 'TR' else 'see Section 10.5'}).", styles['bullet'])

    # ── 10.6 Bozunma ürünleri — 5.2 ile aynı kaynak (_decomp_str) ─────────────
    decomp_str = _decomp_str

    # ── 10.3 Tehlikeli tepkimelerin olasılığı — KKDİK Ek-2 10.3: ürünün basınç/sıcaklık
    #    yayarak tepkimeye gireceği veya başka zararlı koşullar yaratabileceği durumlar ve bu
    #    tepkimelerin oluşabileceği koşullar açıklanır (önceden yalnız "Bkz. Bölüm 7" yazılıyordu).
    _TR10 = lang == 'TR'
    _has_hypo = bool(comp_cas_set & _HYPOCHLORITE_CAS)
    _has_acid_comp = bool(comp_cas_set & _ACID_CAS)
    _react = []
    if _has_acid_comp and not _has_hypo:
        _react.append('Hipoklorit (çamaşır suyu) veya klor içeren ürünlerle temas ederse zehirli klor gazı açığa çıkar.'
                      if _TR10 else 'Releases toxic chlorine gas in contact with hypochlorite (bleach) or chlorine-containing products.')
    if _has_hypo:
        _react.append('Asitlerle veya asidik ürünlerle temas ederse zehirli klor gazı, amonyak veya amonyum tuzları ile '
                      'kloraminler açığa çıkar.' if _TR10 else
                      'Releases toxic chlorine gas in contact with acids and chloramines with ammonia or ammonium salts.')
    if is_base:
        _react.append('Asitlerle şiddetli (ısı açığa çıkaran) tepkime verir.' if _TR10
                      else 'Reacts violently (exothermically) with acids.')
    if 'H290' in h_codes or ((is_acid or is_base) and 'H314' in h_codes):
        _react.append('Alüminyum, çinko gibi metallerle temas ederse alevlenir hidrojen gazı açığa çıkabilir.' if _TR10
                      else 'May release flammable hydrogen gas in contact with metals such as aluminium and zinc.')
    if any(h in h_codes for h in ['H260', 'H261']):
        _react.append('Su ile temas ederse alevlenir gaz açığa çıkarır.' if _TR10
                      else 'Releases flammable gas in contact with water.')
    if any(h in h_codes for h in ['H270', 'H271', 'H272']):
        _react.append('Yanıcı maddelerle temas ederse yangına neden olabilir veya yangını şiddetlendirebilir.' if _TR10
                      else 'May cause or intensify fire in contact with combustible materials.')
    if any(h in h_codes for h in ['H240', 'H241', 'H242']):
        _react.append('Isıtıldığında kendiliğinden hızlanan bozunma ile yangına veya patlamaya neden olabilir.' if _TR10
                      else 'Heating may cause self-accelerating decomposition, fire or explosion.')
    if 'H250' in h_codes:
        _react.append('Hava ile temas ederse kendiliğinden tutuşur.' if _TR10 else 'Catches fire spontaneously if exposed to air.')
    if any(h in h_codes for h in ['H224', 'H225', 'H226']):
        _react.append('Buharları hava ile patlayıcı karışım oluşturabilir.' if _TR10
                      else 'Vapours may form explosive mixtures with air.')
    # Efervesan katı: asit + karbonat/bikarbonat — nem/su ile CO₂ açığa çıkar, kapalı kapta basınç
    if _effervescent:
        _react.append('Nem veya su ile temas ederse asit ve karbonat bileşenleri tepkimeye girerek karbondioksit '
                      'gazı açığa çıkarır; kapalı kaplarda basınç artışına neden olabilir.' if _TR10 else
                      'In contact with moisture or water the acid and carbonate components react and release carbon '
                      'dioxide; may cause pressure build-up in closed containers.')
    react_str = ' '.join(_react) if _react else (
        'Normal kullanım ve depolama koşullarında tehlikeli tepkime beklenmez.' if _TR10
        else 'No hazardous reactions expected under normal conditions of use and storage.')

    # 10.1 Tepkime (KKDİK Ek-2 10.1.1 reaktiflik zararları; 10.1.2 karışım verisi yoksa bileşenlere göre)
    _react_user = phys.get('reactivity')
    if _react_user not in (None, '', na, 'Bilgi yok', 'Veri yok'):
        _react101 = _react_user
    elif _react:
        _react101 = ('Karışım için tepkime test verisi yoktur. Bileşenlere göre bilinen reaktif zararlar ve '
                     'oluştukları koşullar 10.3\'te verilmiştir.' if _TR10 else
                     'No reactivity test data for the mixture. Known reactive hazards based on the components and '
                     'the conditions under which they occur are given in 10.3.')
    else:
        _react101 = ('Karışım için tepkime test verisi yoktur. Bileşenlere göre normal kullanım ve depolama '
                     'koşullarında tepkimeye girmesi beklenmez.' if _TR10 else
                     'No reactivity test data for the mixture. Based on the components, not reactive under '
                     'normal conditions of use and storage.')

    stability_data = [
        [f"10.1 {sub_title(lang,'10.1')}", _react101],
        # KKDİK Ek-2 A 10.2: kararlılık + fiziksel görünüm değişikliğinin güvenlik açısından önemi
        [f"10.2 {sub_title(lang,'10.2')}", S(lang,'stable_conditions') + (
            ' Görünümde beklenmeyen değişiklik (renk değişimi, bulanıklık, çökelti) bozulma belirtisi olabilir; '
            'bu durumda ürünü kullanmayın ve tedarikçiye danışın.' if lang == 'TR' else
            ' An unexpected change in appearance (colour change, turbidity, precipitate) may indicate '
            'deterioration; in that case do not use the product and consult the supplier.'
            if lang == 'EN' else '')],
        [f"10.3 {sub_title(lang,'10.3')}", react_str],
        [f"10.4 {sub_title(lang,'10.4')}", avoid_str],
        [f"10.5 {sub_title(lang,'10.5')}", incompat_str],
        [f"10.6 {sub_title(lang,'10.6')}", decomp_str],
    ]
    story.append(data_table(stability_data, [65*mm, 115*mm], styles, header=False))

    story.append(CondPageBreak(60*mm))   # yalnız sayfa sonunda yer yoksa yeni sayfa (boş sayfa kalmasın)

    # ─────────────────────────────────────────────────────────────────────────
    # BÖLÜM 11 — Toksikoloji
    # ─────────────────────────────────────────────────────────────────────────
    story += section_block(section_title(lang, 11), styles)
    story += sub_block(f"11.1 {sub_title(lang,'11.1')}", styles)

    # ── KKDİK Ek-2 11.1: (a)–(h) zararlılık sınıflarının HER BİRİ için bilgi (11.1.1) ─────────
    # Sınıflandırılmışsa sınıf + gerekçe (hesaplama yöntemi ve katkı veren bileşenler, 11.1.10);
    # sınıflandırılmamışsa Ek-2 11.1.1'in öngördüğü ifade: "Mevcut bilgilere göre, sınıflandırma
    # kriterlerini karşılamamaktadır."
    _TR11 = lang == 'TR'
    _h11 = list(dict.fromkeys(list(all_h_codes or []) + list(h_codes or [])))
    _h11_base = {str(h).split('(')[0].split()[0]: h for h in _h11}
    _NOT_MET = ('Mevcut bilgilere göre, sınıflandırma kriterlerini karşılamamaktadır.' if _TR11
                else 'Based on available data, the classification criteria are not met.')
    _TOX_CLASSES = [
        ('a', 'Akut toksisite', 'Acute toxicity',
         ['H300', 'H301', 'H302', 'H310', 'H311', 'H312', 'H330', 'H331', 'H332']),
        ('b', 'Cilt aşınması/tahrişi', 'Skin corrosion/irritation', ['H314', 'H315']),
        ('c', 'Ciddi göz hasarı/tahrişi', 'Serious eye damage/irritation', ['H318', 'H319']),
        ('ç', 'Solunum yolları veya cilt hassaslaşması', 'Respiratory or skin sensitisation', ['H334', 'H317']),
        ('d', 'Eşey hücre mutajenitesi', 'Germ cell mutagenicity', ['H340', 'H341']),
        ('e', 'Kanserojenite', 'Carcinogenicity', ['H350', 'H351']),
        ('f', 'Üreme sistemi toksisitesi', 'Reproductive toxicity',
         ['H360', 'H360F', 'H360D', 'H360FD', 'H360Fd', 'H360Df', 'H361', 'H361F', 'H361D', 'H361FD', 'H362']),
        ('g', 'BHOT — tek maruz kalma', 'STOT — single exposure', ['H370', 'H371', 'H335', 'H336']),
        ('ğ', 'BHOT — tekrarlı maruz kalma', 'STOT — repeated exposure', ['H372', 'H373']),
        ('h', 'Aspirasyon zararı', 'Aspiration hazard', ['H304']),
    ]
    _comps11 = sds_data.get('components') or components or []

    def _contrib(codes):
        """Bu sınıfa katkı veren bileşenler (bileşen sınıflandırması — SEA Ek-1 hesaplama yöntemi)."""
        out = []
        for _c in _comps11:
            _ch = {str(x.get('h_code') or '').replace('*', '').strip().split('(')[0].split()[0][:4]
                   for x in (_c.get('hazards') or []) if x.get('h_code')}
            if _ch & {c[:4] for c in codes}:
                _nm = (_c.get('name_tr') if _TR11 else '') or _c.get('name') or _c.get('cas_no') or _c.get('cas') or ''
                if _nm and _nm not in out:
                    out.append(_nm)
        return out

    tox_rows = [[('Zararlılık sınıfı (KKDİK Ek-2 11.1)' if _TR11 else 'Hazard class'),
                 ('Değerlendirme' if _TR11 else 'Assessment')]]
    for _k, _ltr, _len, _codes in _TOX_CLASSES:
        _hit = list(dict.fromkeys(_h11_base.get(h, h) for h in _codes if h in _h11_base))
        if _hit:
            _parts = []
            for _h in _hit:
                _hb = str(_h).split('(')[0].split()[0]
                if _hb in ('H370', 'H371', 'H372', 'H373') and _hb in _stot_organ_map:
                    _st = get_stot_stmt(_hb, lang, _stot_organ_map[_hb])
                else:
                    _st = get_h_stmt(_hb, lang)
                _parts.append(f'{_hb}: {_st}')
            _src = _contrib(_codes)
            _basis = ((' Karışım test edilmemiştir; sınıflandırma bileşenlere göre hesaplama yöntemiyle yapılmıştır'
                       if _TR11 else ' Mixture not tested; classified by the calculation method from its components')
                      + (f" ({', '.join(_src)})." if _src else '.'))
            if _k == 'a':
                _basis = (' Karışım test edilmemiştir; sınıflandırma ATEmix hesabıyla yapılmıştır (aşağıda).' if _TR11
                          else ' Mixture not tested; classified by ATEmix calculation (below).')
            # H318 yalnız H314'ten türetilmişse gerekçe bileşen listesi değil, H314'tür
            if _k == 'c' and set(_hit) == {'H318'} and 'H314' in _h11_base:
                _basis = (' Cilt aşındırıcılık (H314) sınıflandırmasından türetilmiştir.' if _TR11 else
                          ' Derived from the skin corrosion (H314) classification.')
            tox_rows.append([f'({_k}) {_ltr if _TR11 else _len}', ' '.join(_parts) + _basis])
        else:
            _src = _contrib(_codes)
            _txt = _NOT_MET
            if _src and _k == 'a':
                _txt += (f" Bu sınıfta sınıflandırılmış bileşenler ({', '.join(_src)}) ile hesaplanan ATEmix "
                         "sınıflandırma eşiğini aşmamaktadır (aşağıda)." if _TR11 else
                         f" ATEmix calculated with the classified components ({', '.join(_src)}) does not reach "
                         "the classification threshold (below).")
            elif _src:
                _txt += (f" Bu sınıfta sınıflandırılmış bileşenler ({', '.join(_src)}) kesme değerlerinin altındadır."
                         if _TR11 else f" Components classified in this class ({', '.join(_src)}) are below the cut-off values.")
            tox_rows.append([f'({_k}) {_ltr if _TR11 else _len}', _txt])

    # Karışımın kendisine ait test verisi (girildiyse) — Ek-2 11.1.2
    phys_tox = sds_data.get('phys_props', {})
    if phys_tox.get('ld50_oral'):
        tox_rows.append([f"LD50 Oral ({term(lang,'rat')})", f"{phys_tox['ld50_oral']} mg/kg"])
    if phys_tox.get('ld50_dermal'):
        tox_rows.append([f"LD50 Dermal ({term(lang,'rat')})", f"{phys_tox['ld50_dermal']} mg/kg"])
    if phys_tox.get('lc50_inhal'):
        tox_rows.append([f"LC50 Inhalation ({term(lang,'rat')}, 4h)", f"{phys_tox['lc50_inhal']} mg/L"])

    # 11.1.5 Olası maruz kalma yolları (fiziksel hale göre)
    _pf11 = (product.get('form') or 'liquid')
    _routes11 = {
        'solid': ('Soluma (toz), cilt ve göz teması, yutma', 'Inhalation (dust), skin and eye contact, ingestion'),
        'powder': ('Soluma (toz), cilt ve göz teması, yutma', 'Inhalation (dust), skin and eye contact, ingestion'),
        'gas': ('Soluma; sıvılaştırılmış gazla cilt ve göz teması', 'Inhalation; skin and eye contact with liquefied gas'),
        'aerosol': ('Soluma (sprey), cilt ve göz teması', 'Inhalation (spray), skin and eye contact'),
    }.get(_pf11, ('Cilt ve göz teması, yutma, buhar/sis soluma', 'Skin and eye contact, ingestion, inhalation of vapour/mist'))
    tox_rows.append([('Olası maruz kalma yolları (11.1.5)' if _TR11 else 'Likely routes of exposure'),
                     _routes11[0 if _TR11 else 1]])

    # 11.1.6 Fiziksel, kimyasal ve toksikolojik özellikler ile ilgili belirtiler — 4.2 ile aynı kaynak
    _sym11 = ' '.join(_re.sub(r'<[^>]+>', '', str(b)).strip() for b in (_sym_bullets or []))
    if not _sym11:
        _sym11 = (_unclassified_health_text(_comps11, _TR11, _sec3_names) if lang in ('TR', 'EN') else
                  'No specific symptoms expected as no health hazard classification applies.')
    tox_rows.append([('Belirtiler (11.1.6)' if _TR11 else 'Symptoms (11.1.6)'), _sym11])

    # 11.1.7 Gecikmeli / hemen ortaya çıkan etkiler ve kronik etkiler (4.1 ile aynı metin)
    tox_rows.append([('Gecikmeli/hemen ortaya çıkan ve kronik etkiler (11.1.7)' if _TR11
                      else 'Delayed/immediate and chronic effects (11.1.7)'),
                     _delayed_effects_text(set(all_h_codes or []) | set(h_codes or []), _TR11)])
    if lang in ('TR', 'EN'):
        # KKDİK Ek-2 A 11.1: bilginin kaynağı (insan/hayvan verisi ya da bileşenlere dayalı hesaplama)
        _mix_tested = any(phys_tox.get(k) for k in ('ld50_oral', 'ld50_dermal', 'lc50_inhal'))
        tox_rows.append([('Veri kaynağı' if _TR11 else 'Source of data'),
                         (('Akut toksisite için karışıma ait test verisi yukarıda verilmiştir; diğer zararlılık '
                           'sınıfları ' if _mix_tested else
                           'Karışımın kendisine ait insan veya hayvan test verisi bulunmamaktadır; değerlendirme ')
                          + 'bileşenlerin sınıflandırmalarına (kaynaklar: Bölüm 16) ve SEA Yönetmeliği Ek-1 '
                            'hesaplama yöntemine dayanır.') if _TR11 else
                         (('Test data on the mixture for acute toxicity are given above; the other hazard classes '
                           if _mix_tested else
                           'No human or animal test data are available for the mixture itself; the assessment ')
                          + 'is based on the classifications of the components (sources: Section 16) and the '
                            'calculation method of the CLP Annex I.')])
        # KKDİK Ek-2 A 11.1.8 / 11.1.11.2(c): etkileşim verisi yoksa varsayım yapılmaz, belirtilir
        tox_rows.append([('Etkileşimli etkiler (11.1.8)' if _TR11 else 'Interactive effects (11.1.8)'),
                         ('Bileşenler arasındaki etkileşimli etkiler hakkında bilgi bulunmamaktadır; bileşenlerin '
                          'etkileri ayrı ayrı değerlendirilmiştir.' if _TR11 else
                          'No information on interactive effects between the components; the effects of each '
                          'component have been assessed separately.')])
        # KKDİK Ek-2 A 11.1.12: sınıflandırma kriterlerince gerekli olmayan diğer olumsuz sağlık etkileri
        tox_rows.append([('Diğer bilgiler (11.1.12)' if _TR11 else 'Other information (11.1.12)'),
                         ('Sınıflandırma kriterleri dışında kalan başka olumsuz sağlık etkisine dair bilgi '
                          'bulunmamaktadır.' if _TR11 else
                          'No information on other adverse health effects beyond the classification criteria.')])

    if len(tox_rows) > 1:
        story.append(data_table(tox_rows, [65*mm, 115*mm], styles))
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
            form=(product.get('form') or sds_data.get('form', '')),
        )

    _ROUTE_LABEL_TR = {'oral': 'Oral (Ağız)', 'dermal': 'Dermal (Deri)', 'inhal': 'İnhalasyon (Solunum)'}
    _ROUTE_LABEL_EN = {'oral': 'Oral', 'dermal': 'Dermal', 'inhal': 'Inhalation'}
    _ROUTE_UNIT     = {'oral': 'mg/kg', 'dermal': 'mg/kg', 'inhal': 'mg/L/4h'}

    if ate_mix_details:
        story.append(Spacer(1, 4))
        # Başlık
        ate_header = ('ATE Karışım Hesabı — SEA Ek-1 3.1.3' if lang == 'TR'
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
            unit  = detail.get('unit') or _ROUTE_UNIT.get(route, 'mg/kg')   # gaz: ppmV
            unk_note = (f' (bilinmeyen %{unk_pct} — revize formül)' if unk_pct > 10 else '')
            _ate_txt = f'{ate_val} {unit}'
            if _sec3_ranged and ate_val is not None:
                # Bölüm 3 aralıklıysa kesin ATEmix değeri bileşen konsantrasyonunu geri hesaplatır: SEA Ek-1
                # Tablo 3.1.1 kategori sınırlarına göre aralık olarak verilir (sınıflandırma bilgisi korunur)
                _pf_ate = (product.get('form') or '')
                _lims = ({'oral': (5, 50, 300, 2000), 'dermal': (50, 200, 1000, 2000)}.get(route)
                         or ((100, 500, 2500, 20000) if 'ppm' in str(unit).lower() else
                             (0.05, 0.5, 1, 5) if _pf_ate in ('solid', 'powder') else (0.5, 2, 10, 20)))
                try:
                    _av = float(ate_val)
                    _f = lambda v: f'{v:g}'.replace('.', ',')
                    if _av > _lims[-1]:
                        _ate_txt = f'> {_f(_lims[-1])} {unit}'
                    else:
                        _lo_l = max([0] + [l for l in _lims if l < _av])
                        _hi_l = min(l for l in _lims if l >= _av)
                        _ate_txt = (f'≤ {_f(_hi_l)} {unit}' if not _lo_l else f'> {_f(_lo_l)} – ≤ {_f(_hi_l)} {unit}')
                except (TypeError, ValueError):
                    pass
            result_rows.append([
                r_lbl,
                f'{_ate_txt}{unk_note}' if ate_val is not None else '—',
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
            unit = detail.get('unit') or _ROUTE_UNIT.get(route, 'mg/kg')
            for c in detail.get('components', []):
                _nm_ate = str((c.get('name_tr','') if lang=='TR' else '') or c.get('name', c.get('cas', '—')))
                comp_rows.append([
                    _pub(_nm_ate),
                    _disp_conc(c.get('cas_no') or c.get('cas',''), c.get('conc'), _nm_ate),
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

    # ─── Bileşenlerin akut toksisite verileri — KKDİK Ek-2 A 11.1.2 ──────────
    # "Varsa, karışımdaki zararlı maddelerin ilgili toksikolojik özellikleri de sağlanır; örneğin: LD50,
    # akut toksisite tahminleri veya LC50." Kaynak: kullanıcının girdiği değer (hammadde GBF'si) veya
    # SEA Ek-6 ATE. Konsantrasyon yazılmaz (Bölüm 3 gizliliği). ATEmix tablosunda aynı değer varsa tekrarlanmaz.
    # ATEmix bileşen kayıtlarında CAS yok — ad + yol + değer ile eşleştirilir
    _shown = set()
    for _rt, _det in (ate_mix_details or {}).items():
        for _c in _det.get('components', []):
            for _n in {_c.get('name'), _c.get('name_tr')} - {None, ''}:
                try:
                    _shown.add((str(_n).strip().lower(), _rt[:5], float(_c.get('ate'))))
                except (TypeError, ValueError):
                    pass
    _is_gas11 = (product.get('form') or '') == 'gas'
    _RT = {'oral': ('oral', 'Ağız yoluyla (LD50/ATE)', 'Oral (LD50/ATE)', 'mg/kg'),
           'dermal': ('dermal', 'Deri yoluyla (LD50/ATE)', 'Dermal (LD50/ATE)', 'mg/kg'),
           'inhal': ('inhal', 'Soluma yoluyla (LC50/ATE)', 'Inhalation (LC50/ATE)', 'ppmV' if _is_gas11 else 'mg/L (4 sa)'),
           'inhalation': ('inhal', 'Soluma yoluyla (LC50/ATE)', 'Inhalation (LC50/ATE)', 'ppmV' if _is_gas11 else 'mg/L (4 sa)')}
    _src_lbl = lambda s: ((('Kullanıcı girişi (hammadde GBF\'si)' if lang == 'TR' else 'User input (raw material SDS)')
                           if s == 'user' else
                           ('SEA Ek-6 (resmî ATE)' if lang == 'TR' else 'Harmonised ATE (Annex VI)')
                           if 'Ek-6' in (s or '') or 'Annex' in (s or '') else (s or '—')))
    _tox_rows = []
    for _c in sds_data.get('components', []):
        _cas = str(_c.get('cas_no') or _c.get('cas') or '').strip()
        _ate = _c.get('ate') or {}
        if _cas == '7732-18-5' or not isinstance(_ate, dict):
            continue
        for _k, _v in _ate.items():
            if _k not in _RT:
                continue
            _val, _unit = (_v.get('value'), _v.get('unit')) if isinstance(_v, dict) else (_v, None)
            try:
                _val = float(_val)
            except (TypeError, ValueError):
                continue
            if _val <= 0:
                continue
            _key, _lt, _le, _u = _RT[_k]
            if any((str(_n).strip().lower(), _key[:5], _val) in _shown
                   for _n in (_c.get('name'), _c.get('name_tr')) if _n):
                continue
            _nm = (_c.get('name_tr') if lang == 'TR' else '') or _c.get('name') or _cas
            _tox_rows.append([_nm, _lt if lang == 'TR' else _le,
                              f"{_val:g} {_unit or _u}", _src_lbl(_c.get('ate_source'))])
    if _tox_rows:
        story.append(Spacer(1, 4))
        story.append(Paragraph(('Bileşenlerin akut toksisite verileri (11.1.2)' if lang == 'TR'
                                else 'Acute toxicity data of components (11.1.2)'), styles['sub_title']))
        story.append(data_table(
            [[('Madde' if lang == 'TR' else 'Substance'), ('Maruz kalma yolu' if lang == 'TR' else 'Route'),
              ('Değer' if lang == 'TR' else 'Value'), ('Kaynak' if lang == 'TR' else 'Source')]] + _tox_rows,
            [55*mm, 50*mm, 30*mm, 45*mm], styles))
    elif lang in ('TR', 'EN') and not any((_d or {}).get('components') for _d in (ate_mix_details or {}).values()):
        # KKDİK Ek-2 A 11.1.2 / 11.1.10: sayısal veri yoksa bu durum zararlı bileşen bazında belirtilir
        # Ad Bölüm 3'te basılan addan alınır (gizlilik talebiyle genel ad verilmişse o kullanılır)
        _s3_name = {str(r.get('cas') or '').strip(): r.get('name') for r in (sec3_rows or [])}
        _hz_names = []
        for _c in sds_data.get('components', []):
            _cas = str(_c.get('cas_no') or _c.get('cas') or '').strip()
            if _cas == '7732-18-5' or not _c.get('hazards') or not _s3_name.get(_cas):
                continue
            _nm = _re.sub(r'<[^>]+>', '', str(_s3_name[_cas])).strip()
            if _nm and _nm not in _hz_names:
                _hz_names.append(_nm)
        if _hz_names:
            story.append(Spacer(1, 4))
            story.append(Paragraph(('Bileşenlerin akut toksisite verileri (11.1.2)' if lang == 'TR'
                                    else 'Acute toxicity data of components (11.1.2)'), styles['sub_title']))
            story.append(Paragraph(
                (f"{', '.join(_hz_names)}: sayısal akut toksisite verisi (LD50, LC50 veya ATE) bu GBF'de "
                 "bulunmamaktadır."
                 + ('' if comp_has_acute else
                    ' Bileşen sınıflandırmalarında (Bölüm 3) akut toksisite sınıfı yoktur.'))
                if lang == 'TR' else
                (f"{', '.join(_hz_names)}: no numerical acute toxicity data (LD50, LC50 or ATE) are available "
                 "in this SDS."
                 + ('' if comp_has_acute else
                    ' The component classifications in Section 3 include no acute toxicity class.')),
                styles['body']))

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
        pbt_cas = [f"{_pub(p['name'])}: P={p.get('P','?')} B={p.get('B','?')} T={p.get('T','?')}"
                   for p in pbt_list if p.get('is_pbt') or p.get('is_vpvb')]
        pbt_summary = '; '.join(pbt_cas) if pbt_cas else sds12.get('12.5', term(lang,'pbt_not'))

    # 12.4 Toprak hareketliliği — ecological_service'den
    _soil_detail = sds12.get('12.4_detail', {})
    _soil_comps  = _soil_detail.get('components', []) if isinstance(_soil_detail, dict) else []
    if _soil_comps:
        _known = [c for c in _soil_comps if c.get('log_koc') is not None]
        if _known:
            _soil_txt = '; '.join(
                f"{_pub((c.get('name_tr') or c['name']) if lang == 'TR' else c['name'])}: {c['mobility']}"
                for c in _known
            )
        else:
            # KKDİK Ek-2 A 12: bilgi yoksa nedeni belirtilir
            _soil_txt = ('Toprak adsorpsiyon verisi mevcut değil: karışım ve bileşenleri için deneysel veya '
                         'tahmini Koc değeri bulunamamıştır.' if lang=='TR'
                         else 'No soil adsorption data available: no experimental or estimated Koc value was '
                              'found for the mixture or its components.')
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
    if _soil_txt == na:
        # KKDİK Ek-2 A 12: bilgi yoksa nedeni belirtilir — çıplak "Bilgi yok" basılmaz
        _soil_txt = ('Toprakta hareketlilik verisi mevcut değil: karışım için test yapılmamıştır ve '
                     'bileşenler için Koc veya log Kow değeri bulunmamaktadır.' if lang == 'TR'
                     else 'No data on mobility in soil: the mixture has not been tested and no Koc or '
                          'log Kow value is available for the components.')

    # 12.2 / 12.3 — KKDİK Ek-2 12.2 ve 12.3: karışımdaki her ilgili madde için ayrı bilgi.
    from app.services.ecological_service import (READILY_BIODEGRADABLE_CAS as _RB_CAS,
                                                 PERSISTENT_CAS as _PERS_CAS, LOG_KOW_DB as _KOW_DB,
                                                 INHERENT_BIODEGRADABLE_CAS as _INH_CAS)
    from app.services.tr_mevzuat_service import _INORGANIC_CAS as _INORG_CAS
    _T = lang == 'TR'
    from app.services.detergent_service import CAS_CLASS as _DET_CLS, SURFACTANT_CLASSES as _SURF_CLS
    _is_det = bool(product.get('is_detergent')) and not is_us

    def _end(t: str) -> str:
        t = (t or '').strip()
        return t if not t or t[-1] in '.!?' else t + '.'

    _deg_parts, _bio_parts = [], []
    for _c in components:
        _cas = str(_c.get('cas_no') or _c.get('cas') or '').strip()
        if _cas == '7732-18-5':        # su — değerlendirme gerekmez
            continue
        _nm = ((_c.get('name_tr') if _T else '') or _c.get('name') or _cas)
        _inorg = _cas in _INORG_CAS
        if _inorg:
            _d = ('uygulanamaz (inorganik madde; biyolojik bozunma yöntemleri uygulanmaz)' if _T
                  else 'not applicable (inorganic substance)')
        elif _cas in _RB_CAS:
            _d = 'kolay biyobozunur' if _T else 'readily biodegradable'
        elif _is_det and ((_c.get('det_class') or '').strip() or _DET_CLS.get(_cas)) in _SURF_CLS:
            _d = 'yüzey aktif madde (aşağıdaki beyana bakınız)' if _T else 'surfactant (see statement below)'
        elif _cas in _INH_CAS:
            _d = ('kolay biyobozunur değil; özünde biyobozunur' if _T
                  else 'not readily biodegradable; inherently biodegradable')
        elif _cas in _PERS_CAS:
            _d = 'kalıcı (zor biyobozunur)' if _T else 'persistent'
        else:
            _d = 'veri yok' if _T else 'no data available'
        _deg_parts.append(f'{_nm}: {_d}')
        _kow = _c.get('log_kow')
        try:
            _kow = float(_kow) if _kow not in (None, '') else _KOW_DB.get(_cas)
        except (TypeError, ValueError):
            _kow = _KOW_DB.get(_cas)
        if _inorg:
            _b = ('uygulanamaz (inorganik madde)' if _T else 'not applicable (inorganic substance)')
        elif _kow is None:
            _b = 'veri yok' if _T else 'no data available'
        elif _kow >= 4:
            _b = (f'log Kow = {_kow:g} — biyobirikim potansiyeli olabilir' if _T
                  else f'log Kow = {_kow:g} — potential to bioaccumulate')
        else:
            _b = (f'log Kow = {_kow:g} — önemli bir biyobirikim beklenmez' if _T
                  else f'log Kow = {_kow:g} — no significant bioaccumulation expected')
        _bio_parts.append(f'{_nm}: {_b}')

    _mix_no_test = ('Karışım için test verisi yoktur.' if _T else 'No test data available for the mixture.')
    # KKDİK Ek-2 A 12 (giriş): bilgi mevcut değilse nedeni belirtilir
    _nd_reason = (' "Veri yok": karışım test edilmemiştir ve bileşen için kullanılan kaynaklarda (SEA Ek-6, '
                  'ECHA, program veritabanı) bu bilgi bulunmamaktadır; hammadde tedarikçisinin GBF\'sine bakınız.'
                  if _T else
                  ' "No data available": the mixture has not been tested and the sources used for the component '
                  '(CLP Annex VI, ECHA, programme database) do not contain this information; see the raw material '
                  "supplier's SDS.")
    if _deg_parts:
        _biodeg_txt = f"{_mix_no_test} {'Bileşenler' if _T else 'Components'}: {' | '.join(_deg_parts)}."
        if any(p.endswith(('veri yok', 'no data available')) for p in _deg_parts):
            _biodeg_txt += _nd_reason
    else:
        _biodeg_txt = _end(bio.get('assessment') or sds12.get('12.2', na))
    if product.get('is_detergent') and not is_us:
        from app.services.detergent_service import has_surfactant, biodegradability_line
        if has_surfactant(components):
            _biodeg_txt = f"{_end(_biodeg_txt)} {biodegradability_line(lang)}" \
                if _biodeg_txt not in (None, '', na) else biodegradability_line(lang)
    if _bio_parts:
        _bioacc_txt = f"{_mix_no_test} {'Bileşenler' if _T else 'Components'}: {' | '.join(_bio_parts)}."
        if any(p.endswith(('veri yok', 'no data available')) for p in _bio_parts):
            _bioacc_txt += _nd_reason
    else:
        _bioacc_txt = sds12.get('12.3', na)

    # 12.1 Toksisite — KKDİK Ek-2 12.1: balık, kabuklu, alg (akut/kronik) verileri; yoksa nedeni.
    _TR12 = lang == 'TR'
    _AQ_H = ['H400', 'H410', 'H411', 'H412', 'H413']
    _mix_aq = [h for h in _AQ_H if h in set(all_h_codes or []) | set(h_codes or [])]
    if _mix_aq:
        _mix_txt = ', '.join(f"{translate_hclass(correct_hclass(h, ''), lang)} ({h})" for h in _mix_aq)
    else:
        _mix_txt = ('sucul ortam için zararlı olarak sınıflandırılmamıştır' if _TR12
                    else 'not classified as hazardous to the aquatic environment')
    _t121 = [('Karışım için ekotoksisite test verisi yoktur; sucul sınıflandırma bileşenlerden toplama '
              f'yöntemiyle yapılmıştır (SEA Ek-1 4.1.3): {_mix_txt}.') if _TR12 else
             ('No ecotoxicity test data for the mixture; aquatic classification by the summation method '
              f'from its components: {_mix_txt}.')]
    _comp_aq = []
    for _c in (sds_data.get('components') or components or []):
        _nm = (_c.get('name_tr') if _TR12 else '') or _c.get('name') or _c.get('cas_no') or _c.get('cas') or ''
        _cls = []
        for _hz in (_c.get('hazards') or []):
            _hc = str(_hz.get('h_code') or '').replace('*', '').strip()[:4]
            if _hc in _AQ_H:
                _cls.append(f"{translate_hclass(correct_hclass(_hc, _hz.get('h_class', '')), lang)} ({_hc})")
        _data = []
        for _key, _ltr, _len in (('ec50_fish', 'LC50 balık (96 sa)', 'LC50 fish (96 h)'),
                                 ('ec50_daphnia', 'EC50 Daphnia (48 sa)', 'EC50 Daphnia (48 h)'),
                                 ('ec50_algae', 'ErC50 alg (72 sa)', 'ErC50 algae (72 h)'),
                                 ('ec50_noec', 'NOEC (kronik)', 'NOEC (chronic)')):
            _v = _c.get(_key)
            if _v not in (None, '', 0):
                _data.append(f"{_ltr if _TR12 else _len}: {_v} mg/L")
        if _cls or _data:
            _comp_aq.append(f"{_nm}: " + '; '.join(_cls + _data))
    if _comp_aq:
        _t121.append(('Bileşenler: ' if _TR12 else 'Components: ') + ' | '.join(_comp_aq) + '.')
    else:
        _t121.append('Bileşenler için sucul toksisite sınıflandırması veya test verisi bulunmamaktadır.' if _TR12
                     else 'No aquatic toxicity classification or test data available for the components.')
    if lang in ('TR', 'EN'):
        # KKDİK Ek-2 A 12.1: diğer organizmalar ve atıksu arıtma tesisine olası etki
        _t121.append('Diğer organizmalar (toprak organizmaları, arılar, kuşlar, bitkiler) için veri bulunmamaktadır.'
                     if _TR12 else 'No data available for other organisms (soil organisms, bees, birds, plants).')
        if 'H314' in (set(all_h_codes or []) | set(h_codes or [])):
            _t121.append('Nötralize edilmemiş ürün, pH etkisiyle atıksu arıtma tesislerindeki mikroorganizmaların '
                         'faaliyetini olumsuz etkileyebilir.' if _TR12 else
                         'Unneutralised product may adversely affect the activity of micro-organisms in sewage '
                         'treatment plants due to its pH.')
        else:
            _t121.append('Atıksu arıtma tesislerine etkisine dair veri bulunmamaktadır.' if _TR12
                         else 'No data available on effects on sewage treatment plants.')

    # 12.6 Diğer olumsuz etkiler (KKDİK Ek-2 12.6) — endokrin bozucu / ozon tabakası bilgisi burada
    _v126 = sds12.get('12.6', na)
    if 'ECHA SVHC' in _v126 or 'kontrol edin' in _v126:
        _v126 = ('Endokrin bozucu özellik tespit edilmemiştir. Bilinen başka bir olumsuz etki yoktur.'
                 if lang == 'TR' else 'No endocrine disrupting properties identified. No other adverse effects known.')
    eco_rows = [
        [f"12.1 {sub_title(lang,'12.1')}", ' '.join(_t121)],
        # KKDİK Ek-2 A 12 (giriş): bozunmadan doğan zararlı dönüşüm ürünleri
        [f"12.2 {sub_title(lang,'12.2')}", _biodeg_txt + (
            ' Zararlı dönüşüm ürünleri hakkında bilgi bulunmamaktadır.' if lang == 'TR' else
            ' No information on hazardous transformation products.' if lang == 'EN' else '')],
        [f"12.3 {sub_title(lang,'12.3')}", _bioacc_txt],
        [f"12.4 {sub_title(lang,'12.4')}", _soil_txt],
        [f"12.5 {sub_title(lang,'12.5')}", pbt_summary],
        [f"12.6 {sub_title(lang,'12.6')}", _v126],
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
            # Kaynaktan gelen M değerleri varsa kaynak dipnotu — her bileşenin gerçek kaynağı
            # (önceden tüm değerler "SEA Ek-6 ve/veya CLP Ek-VI" diye yazılıyordu; ECHA bildirimi olanlar da)
            _msrc_by_cas = {str(c.get('cas_no') or c.get('cas') or '').strip(): c.get('m_source', '')
                            for c in sds_data.get('components', [])}
            _MSRC_TXT = {
                'sea_ek6':  ('SEA Ek-6 (uyumlaştırılmış sınıflandırma)', 'TR SEA Annex 6 (harmonised classification)'),
                'annex_vi': ('AB CLP Ek-VI (uyumlaştırılmış sınıflandırma)', 'EU CLP Annex VI (harmonised classification)'),
                'echa_cl':  ('ECHA C&amp;L Envanteri öz-sınıflandırma bildirimleri (bildirim çoğunluğu; M yazmayan '
                             'bildirimler M=1 sayılır) — tedarikçi verisiyle doğrulanmalıdır',
                             'ECHA C&amp;L Inventory self-classification notifications (majority; notifications '
                             'without an M-factor count as M=1) — verify with supplier data'),
                'user':     ('kullanıcı tarafından girilen değer (tedarikçi verisi)', 'user-entered value (supplier data)'),
            }
            _src_groups: dict = {}
            for _d in _aquatic_comps:
                if _d.get('_m_default'):
                    continue
                _k = _msrc_by_cas.get(_d.get('cas', ''), '') or 'sea_ek6_or_annex'
                _src_groups.setdefault(_k, []).append(_d.get('cas', ''))
            for _k, _cases in _src_groups.items():
                if _k in _MSRC_TXT:
                    _t = _MSRC_TXT[_k][0 if lang == 'TR' else 1]
                else:
                    _t = ('SEA Ek-6 / AB CLP Ek-VI veya veritabanı kaydı' if lang == 'TR'
                          else 'TR SEA Annex 6 / EU CLP Annex VI or database record')
                story.append(Paragraph(
                    (f'M-faktörü kaynağı ({", ".join(_cases)}): {_t}.' if lang == 'TR'
                     else f'M-factor source ({", ".join(_cases)}): {_t}.'), styles['small']))
            story.append(Spacer(1, 3))

    # ─────────────────────────────────────────────────────────────────────────
    # BÖLÜM 13 — Bertaraf (KKDİK Ek-2 §13.1)
    # ─────────────────────────────────────────────────────────────────────────
    story += section_block(section_title(lang, 13), styles)
    story += sub_block(f"13.1 {sub_title(lang,'13.1')}", styles)

    _disp = get_disposal_content(all_h_codes or h_codes, lang, components=components)

    # 13.1a — Ürün bertaraf yöntemleri (dinamik bullet listesi)
    story += bullet_list(_disp['product_bullets'], styles)

    # 13.1b — Kanalizasyon yasağı (sucul tehlike H kodları varsa)
    if _disp.get('drain_note'):
        story.append(Paragraph(_disp['drain_note'], styles['body']))
    elif lang in ('TR', 'EN'):
        # KKDİK Ek-2 A 13.1(c): "Kanalizasyona verilmez."
        story.append(Paragraph(
            'Kanalizasyona verilmez; ürün ve kalıntıları kanalizasyona, yüzey sularına veya toprağa '
            'boşaltılmamalıdır.' if lang == 'TR' else
            'Do not discharge into the sewer; product and residues must not be released to drains, surface '
            'water or soil.', styles['body']))

    # KKDİK Ek-2 A 13.1(b): atık işleme seçeneklerini etkileyebilecek fiziksel/kimyasal özellikler
    if lang in ('TR', 'EN'):
        _h13 = {str(h)[:4] for h in (list(all_h_codes or []) + list(h_codes or []))}
        _eu13 = set((euh or {}).get('euh_codes') or [])
        _p13 = []
        if _h13 & {'H314', 'H290'}:
            _p13.append('aşındırıcıdır — atık, aşınmaya dayanıklı kaplarda toplanmalı; asidik ve bazik atıklar '
                        'birbirine karıştırılmamalıdır' if lang == 'TR' else
                        'corrosive — collect waste in corrosion-resistant containers; do not mix acidic and alkaline waste')
        if _h13 & {'H220', 'H221', 'H222', 'H223', 'H224', 'H225', 'H226', 'H228'}:
            _p13.append('alevlenirdir — atık kapları tutuşturma kaynaklarından uzak tutulmalıdır' if lang == 'TR'
                        else 'flammable — keep waste containers away from ignition sources')
        if _h13 & {'H270', 'H271', 'H272'}:
            _p13.append('oksitleyicidir — yanıcı atıklarla karıştırılmamalıdır' if lang == 'TR'
                        else 'oxidising — do not mix with combustible waste')
        if _h13 & {'H260', 'H261'} or 'EUH014' in _eu13:
            _p13.append('su ile tepkimeye girer — atık kuru tutulmalıdır' if lang == 'TR'
                        else 'reacts with water — keep waste dry')
        if _h13 & {'H400', 'H410', 'H411', 'H412', 'H413'}:
            _p13.append('sucul ortam için zararlıdır — atıksu arıtma tesisine verilmemelidir' if lang == 'TR'
                        else 'harmful to the aquatic environment — do not send to wastewater treatment')
        _w13 = sum(float(c.get('concMax') or c.get('conc') or c.get('concentration') or 0) for c in components
                   if str(c.get('cas_no') or c.get('cas') or '').strip() == '7732-18-5')
        if _w13 > 50:
            _p13.append(f'su bazlıdır (su ~%{_w13:g}; ısıl değeri düşüktür — yakma yerine fizikokimyasal arıtma '
                        f'uygun olabilir)' if lang == 'TR' else
                        f'water-based (water ~{_w13:g}%; low calorific value — physico-chemical treatment may be '
                        f'more suitable than incineration)')
        if not _h13 & {'H220', 'H221', 'H222', 'H223', 'H224', 'H225', 'H226', 'H228'}:
            _p13.append('alevlenir olarak sınıflandırılmamıştır' if lang == 'TR' else 'not classified as flammable')
        story.append(Paragraph(
            (('Atık işlemeyi etkileyen özellikler: ürün ' + '; '.join(_p13) + '.') if _p13 else
             'Atık işleme seçeneklerini etkileyen özel bir fiziksel/kimyasal özellik bilinmemektedir '
             '(bkz. Bölüm 9 ve 10).') if lang == 'TR' else
            (('Properties affecting waste treatment: the product is ' + '; '.join(_p13) + '.') if _p13 else
             'No specific physical/chemical properties affecting waste treatment options are known '
             '(see Sections 9 and 10).'), styles['body']))

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
    if any(k in ship_name for k in ('B.N.O.', 'B.B.B.', 'N.O.S.')) and components:
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
    kemler  = adr_det.get('kemler', '—')
    # Sınıflandırma kodu ve tünel: transport_engine aerosol için hazarda göre hesapladıysa onu kullan
    _road_entry = t_src.get('road') or {}
    cl_code = (_road_entry.get('classification_code')
               or adr_det.get('classification_code', '—'))
    tunnel  = (_road_entry.get('tunnel')
               or adr_det.get('tunnel_code', '—'))

    # ── Mod bazlı sınıf bilgisi (road/sea/air ayrı) ──────────────────────────
    _road = t_src.get('road') or {}
    _sea  = t_src.get('sea')  or {}
    _air  = t_src.get('air')  or {}
    # Her mod için tehlike sınıfı — yoksa ana sınıf kullan
    _cls_road = _road.get('class') or haz_class
    _cls_sea  = _sea.get('class')  or haz_class
    _cls_air  = _air.get('class')  or haz_class
    _road_lbl = f"Sınıf {_cls_road}" + (f" ({sub_class})" if sub_class and _cls_road != '—' else '') if lang == 'TR' else f"Class {_cls_road}" + (f" ({sub_class})" if sub_class and _cls_road != '—' else '')
    _sea_lbl  = f"Sınıf {_cls_sea}"  if _cls_sea  != '—' else '—'
    _air_lbl  = f"Sınıf {_cls_air}"  if _cls_air  != '—' else '—'
    # ADR'de gazların sınıfı "2", 2.1/2.2/2.3 etiket numarasıdır; IMDG/IATA'da bölüm olarak yazılır
    if str(_cls_road) == '2' and _road.get('labels'):
        _road_lbl = (f"Sınıf 2 (etiket: {' + '.join(_road['labels'])})" if lang == 'TR'
                     else f"Class 2 (labels: {' + '.join(_road['labels'])})")
    for _m, _lbl_name in ((_sea, '_sea_lbl'), (_air, '_air_lbl')):
        _sc = _m.get('sub_class')
        if _sc and _m.get('class') and _m.get('class') != '—':
            _v = f"{'Sınıf' if lang == 'TR' else 'Class'} {_m['class']} ({_sc})"
            if _lbl_name == '_sea_lbl':
                _sea_lbl = _v
            else:
                _air_lbl = _v
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
        # KKDİK Ek-2 Bölüm B: alt başlıklar numaralarıyla
        ['14.1 ' + sub_title(lang,'14.1') + ' (UN No)',   un_no + auto_note],
        ['14.2 ' + sub_title(lang,'14.2'),                 ship_name],
        # 14.3 — Her mod için ayrı satır
        [('14.3 ' + sub_title(lang,'14.3') + '\n  ↳ Karayolu / Demiryolu (ADR/RID)'
          if lang == 'TR' else
          '14.3 ' + sub_title(lang,'14.3') + '\n  ↳ Road / Rail (ADR/RID)'),
         _road_lbl],
        ['  ↳ Denizyolu (IMDG)' if lang == 'TR' else '  ↳ Sea (IMDG)',  _sea_lbl],
        ['  ↳ Havayolu (IATA)'  if lang == 'TR' else '  ↳ Air (IATA)',  _air_lbl],
        # Sınıf 2 (gazlar/aerosoller) için ambalaj grubu yoktur
        ['14.4 ' + sub_title(lang,'14.4'),                 pack_grp or term(lang, 'not_applicable')],
        ['14.5 ' + sub_title(lang,'14.5'),                 env_haz],
        ['  ↳ Deniz Kirletici (IMDG)' if lang == 'TR' else '  ↳ Marine Pollutant (IMDG)', _imdg_env],
        ['14.6 ' + sub_title(lang, '14.6'),  _sec14_6],   # Ek-2 B: "Kullanıcılar için özel önlemler"
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
    # 14.7 — KKDİK Ek-2 A 14.7: yalnız MARPOL Ek II / IBC'ye göre dökme taşınması amaçlanan yükler için
    transport_rows.append([
        '14.7 ' + sub_title(lang, '14.7'),
        'Uygulanamaz — ürün ambalajlı olarak taşınır; MARPOL 73/78 Ek II ve IBC Koduna göre dökme '
        'taşımacılık amaçlanmamıştır.' if lang == 'TR' else
        'Not applicable — the product is transported in packages; bulk transport according to '
        'MARPOL 73/78 Annex II and the IBC Code is not intended.'])
    if _not_regulated:
        # KKDİK Ek-2 B: 14.1–14.7 alt başlıkları tehlikeli madde olmayan üründe de bulunur
        # (önceden yalnız açıklama cümlesi basılıyordu; denetimde G-basliklar eksik çıkıyordu)
        story.append(Paragraph(_not_reg_text, styles['body']))
        story.append(Spacer(1, 3))
        _na = term(lang, 'not_applicable')
        _na_dg = (f'{_na} — tehlikeli madde değildir' if lang == 'TR' else f'{_na} — not dangerous goods')
        story.append(data_table([
            ['14.1 ' + sub_title(lang, '14.1') + ' (UN No)', _na_dg],
            ['14.2 ' + sub_title(lang, '14.2'), _na_dg],
            ['14.3 ' + sub_title(lang, '14.3'), _na_dg],
            ['14.4 ' + sub_title(lang, '14.4'), _na_dg],
            ['14.5 ' + sub_title(lang, '14.5'), _na],
            ['14.6 ' + sub_title(lang, '14.6'), _na],
            transport_rows[-1],   # 14.7 — MARPOL Ek II / IBC
        ], [75*mm, 105*mm], styles, header=False))
        story.append(Spacer(1, 4))
    else:
        story.append(data_table(transport_rows, [75*mm, 105*mm], styles, header=False))
    if not _not_regulated and auto_t:
        story.append(Paragraph(
            '* Taşımacılık sınıflandırması CLP tehlike sınıfına göre otomatik belirlenmiştir. Sevkiyat öncesi yetkili taşımacılık uzmanına danışınız.' if lang=='TR'
            else '* Transport classification determined automatically from CLP hazard class. Consult a transport specialist before shipment.',
            styles['small']
        ))

    # ── Deniz Kirletici gerekçe (ADR §2.2.9.1.10.5 / IMDG §2.10.3) ─────────────
    # Karışım CLP'ye göre H400/H410/H411 ise deniz kirletici — ayrı Σ hesabı gerekmez.
    # Karar main.py'de eco_result.aquatic.h_code üzerinden set ediliyor (_sea_env_mark).
    _imdg_mp_h = {'H400', 'H410', 'H411'}
    _mp_comps = []
    for _c in sds_data.get('components', []):
        _c_h_codes = {(h.get('h_code') or '').strip() for h in (_c.get('hazards') or [])}
        _c_mp_h = _c_h_codes & _imdg_mp_h
        if not _c_mp_h:
            continue
        _conc = float(_c.get('concMax') or _c.get('conc') or _c.get('concentration') or 0)
        _mf_raw = _c.get('m_factors') or {}
        _m_a = float(_mf_raw.get('acute',   1)) if _mf_raw else 1.0
        _m_c = float(_mf_raw.get('chronic', 1)) if _mf_raw else 1.0
        _name = (_c.get('name_tr', '') if lang == 'TR' else '') or _c.get('name', '')
        _cas  = _c.get('cas_no', _c.get('cas', ''))
        # Bileşenin gerçek en ağır H kodunu göster (H410 > H400 > H411)
        if 'H410' in _c_mp_h:
            _dominant_h = 'H410'
        elif 'H400' in _c_mp_h:
            _dominant_h = 'H400'
        else:
            _dominant_h = 'H411'
        _mp_comps.append({
            'cas':    _cas,
            'name':   _name or _cas,
            'conc':   _conc,
            'm_a':    _m_a,
            'm_c':    _m_c,
            'h_code': _dominant_h,
        })

    if _mp_comps:
        _mp_title = ('Deniz Kirletici Gerekçesi (ADR §2.2.9.1.10.5)'
                     if lang == 'TR' else
                     'Marine Pollutant Basis (ADR §2.2.9.1.10.5)')
        story.append(Spacer(1, 4))
        story.append(Paragraph(f"<b>{_mp_title}:</b>", styles['body_bold']))

        _col1 = 'CAS No'
        _col2 = 'Madde'    if lang == 'TR' else 'Substance'
        _col3 = 'C (%)'
        _col4 = 'M (akut)' if lang == 'TR' else 'M (acute)'
        _col5 = 'M (kr.)'  if lang == 'TR' else 'M (chr.)'
        _col6 = 'H Kodu'   if lang == 'TR' else 'H Code'
        _mp_rows = [[_col1, _col2, _col3, _col4, _col5, _col6]]
        for _mp in _mp_comps:
            _mp_rows.append([
                ('Gizli*' if lang == 'TR' else 'Confidential*') if str(_mp['cas']).strip() in _hidden_cas
                else _mp['cas'],
                Paragraph(_pub(_mp['name']), styles['small']),
                _disp_conc(_mp['cas'], _mp['conc']),
                f"{int(_mp['m_a'])}",
                f"{int(_mp['m_c'])}",
                _mp['h_code'],
            ])
        story.append(data_table(_mp_rows, [24*mm, 48*mm, 15*mm, 18*mm, 18*mm, 21*mm], styles))

        # Karar _sea_env_mark'tan (eco_result.aquatic.h_code) geliyor
        _is_mp = bool(_sea_env_mark)
        if _is_mp:
            _verdict = ('Karışım CLP ekoloji sınıflandırması H400/H410/H411 → Deniz Kirletici (ADR §2.2.9.1.10.5a).'
                        if lang == 'TR' else
                        'Mixture CLP ecology classification H400/H410/H411 → Marine Pollutant (ADR §2.2.9.1.10.5a).')
        else:
            _verdict = ('Karışım H400/H410/H411 sınıflandırması yok → Deniz Kirletici değil.'
                        if lang == 'TR' else
                        'Mixture not classified H400/H410/H411 → Not a Marine Pollutant.')
        story.append(Paragraph(_verdict, styles['small']))

        # H411 bileşeni varsa Test 2 dipnotu ekle
        if any(_mp['h_code'] in ('H410', 'H411') for _mp in _mp_comps):
            _t2_note = (
                '* Deniz kirletici kararı, CLP Tablo 4.1.1/4.1.2 M-faktörlü toplamsal formülüyle '
                'belirlenen H400/H410/H411 sınıflandırmasına dayanır (ADR §2.2.9.1.10.5a) — '
                'ayrı bir eşik hesabı yoktur.'
                if lang == 'TR' else
                '* Marine pollutant decision is based on H400/H410/H411 classification determined '
                'by the CLP Table 4.1.1/4.1.2 M-factor summation formula (ADR §2.2.9.1.10.5a) — '
                'no separate threshold calculation applies.'
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

    # ── Deterjanlar Hakkında Yönetmelik — Ek-7 A içerik beyanı (KKDİK Ek-2 15.1: ürünün tabi
    #    olduğu mevzuat). Halka sunulmayan endüstriyel/kurumsal deterjanda bu bilgi GBF ile verilir.
    if product.get('is_detergent') and not is_us:
        from app.services.detergent_service import ek7a_lines
        story.append(Spacer(1, 4))
        for _dl in ek7a_lines(components, _usage_val, lang):
            story.append(Paragraph(_dl, styles['body']))

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

    # ── Aday Liste (SVHC) — KKDİK Md.49(1); Ek-2 15.1 ──────────────────────
    try:
        from app.services.svhc_service import check_svhc_mixture, svhc_section15_text
        svhc_result = check_svhc_mixture(components)
        svhc_lines = svhc_section15_text(svhc_result, lang=lang)
        story.append(Spacer(1, 4))
        for line in svhc_lines:
            if line.startswith('⚠') or line.startswith('  •'):
                st = styles.get('body_bold', styles['body']) if line.startswith('⚠') else styles['body']
                color = '#cc0000' if line.startswith('⚠') else '#333333'
                # ⚠ yedek yazı tipinde (Arial) kutu olarak basılıyor — PDF'te renk/kalınlık yeterli
                story.append(Paragraph(
                    f'<font color="{color}">{line.lstrip("⚠ ")}</font>', st
                ))
            else:
                story.append(Paragraph(line, styles['small']))
    except Exception:
        pass

    # ── KKDİK Ek-17 kısıtlamaları — Ek-2 A 15.1 (TR Ek-14 izin listesi yönetmelikte boş) ──
    if not is_us:
        try:
            from app.services.ek17_service import section15_lines
            _ek17_lines = section15_lines(components, lang=lang)
            if _ek17_lines:
                story.append(Spacer(1, 4))
                for line in _ek17_lines:
                    st = styles['body'] if line.startswith('•') else styles['small']
                    story.append(Paragraph(line, st))
        except Exception:
            pass
        # KKDİK Ek-2 Bölüm 15 girişi / 15.1: BEKRA (RG 02.03.2019/30702 — Ek-2'nin atıf yaptığı 2013 tarihli
        # yönetmelik mülga), ozon tabakasını incelten maddeler ve KOK mevzuatına tabi olup olmadığı
        try:
            from app.services.reg15_service import section15_lines as _reg15_lines
            _r15 = _reg15_lines(list(dict.fromkeys(list(all_h_codes or []) + list(h_codes or []))),
                                clp.get('passed') or [], (euh or {}).get('euh_codes') or [], components, lang=lang)
            if _r15:
                story.append(Spacer(1, 4))
                for line in _r15:
                    story.append(Paragraph(f'• {line}', styles['body']))
        except Exception:
            pass

    # KKDİK Ek-2 A 15.1: hükümler sonucu alıcının yapması gereken faaliyetlere dair tavsiye
    if lang in ('TR', 'EN') and h_codes:
        story.append(Spacer(1, 3))
        story.append(Paragraph(
            'Alıcı için tavsiye: işveren, yukarıdaki mevzuat kapsamında işyerinde bu ürün için risk '
            'değerlendirmesi yapmalı (6331 sayılı İş Sağlığı ve Güvenliği Kanunu; Kimyasal Maddelerle '
            'Çalışmalarda Sağlık ve Güvenlik Önlemleri Hakkında Yönetmelik), çalışanları bilgilendirmeli ve '
            'atıkları Atık Yönetimi Yönetmeliğine göre yönetmelidir.' if lang == 'TR' else
            'Advice for the recipient: the employer should carry out a workplace risk assessment for this '
            'product under the legislation above, inform workers, and manage waste according to the waste '
            'legislation.', styles['small']))

    story += sub_block(f"15.2 {sub_title(lang,'15.2') if '15.2' in L.get('sub',{}) else 'Kimyasal güvenlik değerlendirmesi'}", styles)

    # KKDİK Ek-2 A 15.2: tedarikçi bu karışım için kimyasal güvenlik değerlendirmesi yapılıp
    # yapılmadığını belirtir. (KGD yükümlülüğü KKDİK Md.15'e göre ≥10 ton/yıl kayıt ettirene aittir;
    # karışım GBF'sinde CMR içeriğine bağlı "zorunludur" uyarısı basılmaz.)
    story.append(Paragraph(S(lang,'no_csa'), styles['small']))

    story.append(CondPageBreak(60*mm))   # yalnız sayfa sonunda yer yoksa yeni sayfa (boş sayfa kalmasın)

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

    # H kodu tam metin listesi — EUH kodları da dahil (KKDİK Ek-2 §16(d))
    # KKDİK Ek-2 Bölüm 16: 2–15. bölümlerde geçen TÜM H/EUH ifadelerinin tam metni —
    # yalnızca etiket kodları değil, Bölüm 2.1 sınıflandırması ve Bölüm 3 bileşen kodları da.
    def _code_of(h) -> str:
        s = str(h.get('h_code', '') if isinstance(h, dict) else h).replace('*', '').strip()
        m = _re.match(r'(EUH\d{3}A?|H\d{3})([A-Za-z]{0,2})', s)
        if not m:
            return ''
        base, sfx = m.group(1), m.group(2).upper()
        if base in ('H360', 'H361') and sfx:
            sfx = 'FD' if ('F' in sfx and 'D' in sfx) else sfx
            return base + sfx
        return base
    _b16_codes = [_code_of(h) for h in list(all_h_codes) + list(h_codes)]
    for _c3 in components:
        _b16_codes += [_code_of(h) for h in (_c3.get('hazards') or [])]
    _b16_codes = [c for c in dict.fromkeys(_b16_codes) if c and c.startswith('H')]
    all_h_b16 = sorted(_b16_codes, key=lambda c: (int(c[1:4]), c))
    _euh_b16 = [c for c in (euh.get('euh_codes') or []) if c not in all_h_b16]
    all_h = all_h_b16 + _euh_b16
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

    # Sınıflandırma notları — test yerine verilen fiziksel tehlike kararlarının gerekçesi
    _cls_notes = [n.get(lang) or n.get('EN') for n in (sds_data.get('classification_notes') or [])
                  if isinstance(n, dict)]
    if _cls_notes:
        story.append(Paragraph(
            '<b>' + ('Sınıflandırma notları:' if lang == 'TR' else 'Classification notes:') + '</b>',
            styles['body_bold']))
        for _n in _cls_notes:
            _n = str(_n).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            story.append(Paragraph(f'• {_n}', styles['small']))
        story.append(Spacer(1, 4))

    # KKDİK Ek-2 Bölüm 16 (ç): karışımın sınıflandırılmasında SEA Yönetmeliği Md.11'deki
    # bilgi değerlendirme yöntemlerinden hangisinin kullanıldığı — her sınıf için ayrı.
    def _clf_method(hcode: str, reason: str, src) -> str:
        TR = lang == 'TR'
        h4 = (hcode or '')[:4]
        r = reason or ''
        rl = r.lower()
        if r == dom_note:
            return ('Daha yüksek kategorideki sınıflandırma kapsamında değerlendirilmiştir'
                    if TR else 'Covered by the classification in a higher category')
        if h4.startswith('H2'):
            if any(k in rl for k in ('kullanıcı', 'test', 'ölç', 'user', 'measured')):
                return ('Karışımın test verisi / üretici beyanı (SEA Ek-1 Kısım 2)' if TR
                        else 'Test data on the mixture / manufacturer statement (Annex I Part 2)')
            return ('Bileşen verilerine dayalı değerlendirme; karışım test edilmemiştir (SEA Ek-1 Kısım 2)' if TR
                    else 'Assessment based on component data; mixture not tested (Annex I Part 2)')
        if h4 in ('H300', 'H301', 'H302', 'H310', 'H311', 'H312', 'H330', 'H331', 'H332'):
            return ('Hesaplama yöntemi — ATEkarışım formülü (SEA Ek-1 3.1.3.6)' if TR
                    else 'Calculation method — ATEmix formula (Annex I 3.1.3.6)')
        if h4 in ('H400', 'H410', 'H411', 'H412', 'H413'):
            return ('Toplama yöntemi (SEA Ek-1 4.1.3.5)' if TR
                    else 'Summation method (Annex I 4.1.3.5)')
        if h4 == 'H318' and 'H314' in r:
            return ('Cilt aşındırıcılık (H314) sınıflandırmasından türetilmiştir' if TR
                    else 'Derived from the skin corrosion (H314) classification')
        if 'ph' in rl.replace('phys', ''):
            return ('Aşırı pH değerine dayalı değerlendirme (SEA Ek-1)' if TR
                    else 'Assessment based on extreme pH (Annex I)')
        if 'tablo 3.2.4' in rl or 'tablo 3.3.4' in rl:
            return ('Toplama yönteminin uygulanamadığı bileşenler yaklaşımı (SEA Ek-1 Tablo 3.2.4 / 3.3.4)' if TR
                    else 'Approach for ingredients for which additivity does not apply (Annex I Table 3.2.4 / 3.3.4)')
        if 'σ' in rl or 'toplam' in rl:
            return ('Toplama yöntemi (SEA Ek-1 3.2.3.3 / 3.3.3.3)' if TR
                    else 'Additivity (summation) method (Annex I 3.2.3.3 / 3.3.3.3)')
        if str(src or '').upper() == 'SCL':
            return ('Hesaplama yöntemi — özel konsantrasyon sınırı (SEA Ek-6)' if TR
                    else 'Calculation method — specific concentration limit (Annex VI)')
        return ('Hesaplama yöntemi — genel konsantrasyon sınırı (SEA Ek-1)' if TR
                else 'Calculation method — generic concentration limit (Annex I)')

    if clf_rows:
        story.append(Paragraph(
            '<b>' + ('Karışımın sınıflandırılmasında kullanılan yöntem (SEA Yönetmeliği Madde 11):'
                     if lang == 'TR' else
                     'Method used for the classification of the mixture (CLP Article 9):') + '</b>',
            styles['body_bold']))
        story.append(Paragraph(
            ('Karışımın bütünü için sağlık ve çevre tehlikelerine ilişkin test verisi ve köprüleme ilkelerinin '
             'uygulanabileceği benzer test edilmiş karışım verisi bulunmadığından, sınıflandırma bileşen '
             'verileri üzerinden yapılmıştır.') if lang == 'TR' else
            ('No test data on the mixture as a whole and no data on similar tested mixtures allowing the '
             'bridging principles were available for health and environmental hazards; the classification '
             'is based on the data of the ingredients.'),
            styles['small']))
        _m_rows = [[('Sınıflandırma' if lang == 'TR' else 'Classification'),
                    ('H Kodu' if lang == 'TR' else 'H Code'),
                    ('Yöntem' if lang == 'TR' else 'Method')]]
        for _row in clf_rows:
            _m_rows.append([_row[0], _row[1],
                            _clf_method(str(_row[1]), str(_row[2]), _clf_src.get(_row[1]))])
        story.append(data_table(_m_rows, [70*mm, 25*mm, 85*mm], styles))
        story.append(Spacer(1, 4))
    elif lang in ('TR', 'EN'):
        # KKDİK Ek-2 16(ç): sınıflandırılmamış karışımda da kullanılan değerlendirme yöntemi belirtilir
        story.append(Paragraph(
            '<b>' + ('Karışımın sınıflandırılmasında kullanılan yöntem (SEA Yönetmeliği Madde 11):'
                     if lang == 'TR' else
                     'Method used for the classification of the mixture (CLP Article 9):') + '</b>',
            styles['body_bold']))
        story.append(Paragraph(
            ('Karışımın bütünü için test verisi ve köprüleme ilkelerinin uygulanabileceği benzer test edilmiş '
             'karışım verisi bulunmadığından, karışım bileşen verilerine dayalı hesaplama yöntemiyle (SEA '
             'Yönetmeliği Ek-1) değerlendirilmiş ve hiçbir zararlılık sınıfı için sınıflandırma kriterlerini '
             'karşılamamıştır.') if lang == 'TR' else
            ('No test data on the mixture as a whole and no data on similar tested mixtures allowing the '
             'bridging principles were available; the mixture was assessed by the calculation method based on '
             'its ingredients (CLP Annex I) and does not meet the criteria for classification in any hazard class.'),
            styles['small']))
        story.append(Spacer(1, 4))

    # Revizyon geçmişi
    _rev_notes_raw = (rev.get('notes') or '').strip()
    _generic = {'güncelleme', 'update', 'güncellenmiştir', 'updated', '-', ''}
    # KKDİK Ek-2 0.2.5 / 16(a): değişiklikler GBF'yi hazırlayan tarafından belirtilir. Not girilmemişse program
    # değişiklik uydurmaz (önceden "Sınıflandırma ve etiketleme bilgileri güncellenmiştir" yazılıyordu).
    try:
        _first_issue = int(str(rev_no).strip() or '1') <= 1
    except ValueError:
        _first_issue = False
    # 'İ'.lower() Python'da 'i̇' (noktalı birleşik) verir — karşılaştırmadan önce düz 'i' yapılır
    if not _first_issue and _rev_notes_raw.replace('İ', 'i').lower() in ('ilk yayın', 'ilk yayin', 'first issue'):
        _rev_notes_raw = ''   # varsayılan not sonraki revizyonlarda kalmış — ilk yayın değildir
    if _rev_notes_raw.lower() not in _generic:
        rev_notes = _rev_notes_raw
    elif _first_issue:
        rev_notes = 'İlk yayın.' if lang == 'TR' else 'First issue.'
    else:
        rev_notes = ('Önceki sürüme göre yapılan değişiklikler belirtilmemiştir.' if lang == 'TR'
                     else 'Changes from the previous version have not been specified.')
    story.append(Paragraph(
        f"<b>{S(lang,'revision_history')}:</b> "
        f"Rev.{rev_no} — {rev_date}: {rev_notes}",
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
        # Etiketle aynı kaynak (SEA Etiketleme Rehberi 7.3) — endpoint'in hesapladığı gruplar
        sds_cls = p_data.get('sds') if (p_data.get('sds') or {}).get('groups') else classify_sds_p_codes(
            p_data['p_codes'], usage=_usage_val, h_codes=h_codes, form=product.get('form', 'liquid'),
            label=(p_data.get('label') or {}).get('selected'))
        for grp_key, icon, lbl in [
            ('mandatory','✓',S(lang,'mandatory_label')),
            ('evaluate','~',S(lang,'evaluate_label')),
            ('optional','○',S(lang,'optional_label')),
        ]:
            codes = sds_cls['groups'].get(grp_key, [])
            if codes:
                story.append(Paragraph(f"<b>{icon} {lbl}:</b>", styles['small']))
                # Grup içi şiddet sırası (yüksek önce)
                codes_sorted = sorted(codes, key=lambda p: (str(p)[1:2], -P_LABEL_PRIORITY.get(p, 5)))
                for code in codes_sorted:
                    txt = _p_full(code)
                    story.append(Paragraph(f"  {code}: {txt}", styles['small']))

    # Kısaltmalar
    story.append(Spacer(1, 6))
    abbrev_tr = (
        "KKDİK — Kimyasalların Kaydı, Değerlendirilmesi, İzni ve Kısıtlanması | "
        "GBF — Güvenlik Bilgi Formu | "
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

    # KKDİK Ek-2 Bölüm 16 (c): ana literatür referansları ve bilgi kaynakları
    _TR16 = lang == 'TR'
    _echa_used = any(
        (c.get('hazards') and (c.get('source_priority') or 4) >= 3)
        or any(h.get('echa_supplement') for h in (c.get('hazards') or []))
        for c in components)
    _src = [
        ('Bileşenlerin uyumlaştırılmış sınıflandırması: SEA Yönetmeliği Ek-6'
         if _TR16 else 'Harmonised classification of ingredients: CLP Annex VI'),
    ]
    if _echa_used:
        _src.append('Ek-6’da yer almayan maddeler / sınıflar: ECHA Sınıflandırma ve Etiketleme Envanteri bildirimleri'
                    if _TR16 else 'Substances / classes not in Annex VI: ECHA C&amp;L Inventory notifications')
    _src.append('Ürün formülasyonu ve fiziksel/kimyasal veriler: üretici beyanı'
                if _TR16 else 'Product formulation and physical/chemical data: manufacturer information')
    if _TR16:
        _src += [
            'Mesleki maruz kalma sınır değerleri: Kimyasal Maddelerle Çalışmalarda Sağlık ve Güvenlik '
            'Önlemleri Hakkında Yönetmelik',
            'Taşımacılık: ADR 2025, IMDG Kod (Değişiklik 42-24), IATA-DGR 2026',
            'Atık kodları: Atık Yönetimi Yönetmeliği (RG 02.04.2015/29314)',
        ]
        try:
            from app.services.svhc_service import _load_svhc_list, _list_date
            _src.append('Aday Liste (SVHC, KKDİK Md.49): AB (ECHA) Aday Listesi, '
                        f"{_list_date(_load_svhc_list()['meta'])} tarihli liste")
        except Exception:
            pass
        if product.get('is_detergent'):
            _src.append('Deterjan bilgileri: Deterjanlar Hakkında Yönetmelik (RG 27.01.2018/30314)')
        _src.append('BEKRA, ozon, KOK ve ÖBK durumu (Bölüm 15): Büyük Endüstriyel Kazaların Önlenmesi ve Etkilerinin '
                    'Azaltılması Hakkında Yönetmelik Ek-1 (RG 02.03.2019/30702); Ozon Tabakasını İncelten Maddelere '
                    'İlişkin Yönetmelik Ek-5, Ek-8 (RG 07.04.2017/30031); Kalıcı Organik Kirleticiler Hakkında '
                    'Yönetmelik Ek-1, Ek-2 (RG 14.11.2018/30595); Bazı Zararlı Kimyasalların İhracatı ve İthalatı '
                    'Hakkında Yönetmelik Ek-1, Ek-2 (RG 28.01.2023/32087)')
        _src.append('Güvenlik Bilgi Formu: KKDİK Yönetmeliği Ek-2 (RG 23.06.2017/30105 Mükerrer)')
    else:
        _src += ['Transport: ADR 2025, IMDG Code (Amdt. 42-24), IATA-DGR 2026']
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        '<b>' + ('Ana literatür referansları ve bilgi kaynakları:' if _TR16
                 else 'Key literature references and sources for data:') + '</b>',
        styles['body_bold']))
    for _sx in _src:
        story.append(Paragraph(f'• {_sx}', styles['small']))

    # KKDİK Ek-2 Bölüm 16 (e): işçiler için uygun eğitime dair tavsiyeler
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        '<b>' + ('Eğitim tavsiyeleri:' if _TR16 else 'Training advice:') + '</b>', styles['body_bold']))
    story.append(Paragraph(
        ('Bu ürünle çalışan işçilere, insan sağlığı ve çevrenin korunması amacıyla; ürünün tehlikeleri, '
         'güvenli kullanım ve depolama, kişisel koruyucu donanım kullanımı, ilk yardım ve acil durum '
         'önlemleri konularında bu Güvenlik Bilgi Formuna dayalı eğitim verilmelidir (6331 sayılı İş Sağlığı '
         've Güvenliği Kanunu; Kimyasal Maddelerle Çalışmalarda Sağlık ve Güvenlik Önlemleri Hakkında '
         'Yönetmelik).') if _TR16 else
        ('Workers handling this product should receive training, based on this Safety Data Sheet, on its '
         'hazards, safe handling and storage, use of personal protective equipment, first aid and emergency '
         'measures, to protect human health and the environment.'),
        styles['small']))

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
    doc.build(story, onFirstPage=_draw_page, onLaterPages=_draw_page, canvasmaker=_TotalPagesCanvas)

    return buf.getvalue()
