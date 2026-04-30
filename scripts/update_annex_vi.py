"""
ECHA CLP Annex VI Güncelleme Scripti
=====================================
Kullanım:
  python scripts/update_annex_vi.py <excel_yolu> [--dry-run]

Örnek:
  python scripts/update_annex_vi.py "C:/Users/user/Desktop/annex_vi_clp_table_atp22_en.xlsx"
  python scripts/update_annex_vi.py "C:/Users/user/Desktop/annex_vi_clp_table_atp22_en.xlsx" --dry-run

Excel sütun yapısı (ECHA ATP22):
  Satır 5-6 : Başlık satırları
  Satır 7+  : Veri
  Sütun 0   : Index No
  Sütun 1   : Madde adı
  Sütun 2   : EC No
  Sütun 3   : CAS No          ← anahtar
  Sütun 4   : Hazard class(lar) — satır sonu ile ayrılmış
  Sütun 5   : H-kod(lar)       — sütun 4 ile eşleşik
  Sütun 6   : Piktogram + sinyal kelimesi (son satır = Dgr/Wng)
  Sütun 7   : Etiket H-kodları
  Sütun 8   : Ek tehlike ifadeleri (EUH)
  Sütun 9   : SCL / M-faktörler / ATE
  Sütun 10  : Notlar
  Sütun 11  : ATP

Çıktı:
  - data/annex6/**/{cas}.json güncellenir / yeni eklenir
  - data/cl/ ile karşılaştırılır — daha sıkı sınıf varsa uyarı verilir
  - scripts/annex_vi_update_report.txt özet raporu
"""

import sys, json, re, argparse
from pathlib import Path

try:
    import openpyxl
except ImportError:
    print("HATA: openpyxl kurulu değil → pip install openpyxl")
    sys.exit(1)

# ── Yollar ───────────────────────────────────────────────────────────────────
_ROOT      = Path(__file__).parent.parent
_ANNEX6    = _ROOT / 'data' / 'annex6'
_CL_DIR    = _ROOT / 'data' / 'cl'
_REPORT    = Path(__file__).parent / 'annex_vi_update_report.txt'
_ANNEX6.mkdir(parents=True, exist_ok=True)

# ── Tehlike sınıfı → ATP sertlik sıralaması ───────────────────────────────────
_SEVERITY: dict[str, int] = {
    'H360': 1, 'H361': 2, 'H362': 3,
    'H340': 1, 'H341': 2,
    'H350': 1, 'H351': 2,
    'H300': 1, 'H301': 2, 'H302': 3,
    'H310': 1, 'H311': 2, 'H312': 3,
    'H330': 1, 'H331': 2, 'H332': 3,
    'H314': 1, 'H315': 2,
    'H318': 1, 'H319': 2,
    'H370': 1, 'H371': 2,
    'H372': 1, 'H373': 2,
    'H400': 1, 'H401': 2, 'H402': 3,
    'H410': 1, 'H411': 2, 'H412': 3, 'H413': 4,
}

_H_CLASS_GROUP: dict[str, str] = {
    'H224': 'flam_liq',   'H225': 'flam_liq',   'H226': 'flam_liq',
    'H300': 'acute_oral', 'H301': 'acute_oral',  'H302': 'acute_oral',
    'H310': 'acute_derm', 'H311': 'acute_derm',  'H312': 'acute_derm',
    'H330': 'acute_inh',  'H331': 'acute_inh',   'H332': 'acute_inh',
    'H314': 'skin',       'H315': 'skin',
    'H318': 'eye',        'H319': 'eye',
    'H317': 'skin_sens',  'H334': 'resp_sens',
    'H340': 'muta',       'H341': 'muta',
    'H350': 'carc',       'H351': 'carc',
    'H360': 'repr',       'H361': 'repr',        'H362': 'repr',
    'H370': 'stot_se',    'H371': 'stot_se',
    'H372': 'stot_re',    'H373': 'stot_re',
    'H400': 'aq_acute',   'H401': 'aq_acute',    'H402': 'aq_acute',
    'H410': 'aq_chron',   'H411': 'aq_chron',    'H412': 'aq_chron', 'H413': 'aq_chron',
}

_SIGNAL = {'dgr': 'Danger', 'wng': 'Warning', 'danger': 'Danger', 'warning': 'Warning'}


# ── Yardımcılar ───────────────────────────────────────────────────────────────

def _cell(row, idx: int) -> str:
    try:
        v = row[idx].value
        return str(v).strip() if v is not None else ''
    except IndexError:
        return ''


def _lines(text: str) -> list[str]:
    """Satır sonu ile ayrılmış değerleri temizleyerek listele."""
    return [s.strip() for s in re.split(r'[\n\r]+', text) if s.strip()]


def _parse_hazards(class_col: str, hcode_col: str) -> list[dict]:
    """Sütun 4 ve 5'i eşleştirerek hazard listesi oluştur."""
    classes = _lines(class_col)
    hcodes  = _lines(hcode_col)
    result  = []
    for i, cls in enumerate(classes):
        hcode = hcodes[i] if i < len(hcodes) else ''
        # H kodu temizle: 'H372 **' → 'H372', 'H372 (thyroid)' → 'H372(thyroid)'
        hcode = _clean_hcode(hcode)
        cls   = re.sub(r'\s*\*+\s*$', '', cls).strip()
        if cls:
            result.append({'class': cls, 'h_code': hcode})
    return result


def _clean_hcode(code: str) -> str:
    code = code.strip()
    organ = re.search(r'\(([^)]+)\)', code)
    if organ:
        base = re.sub(r'\s*\([^)]+\)', '', code).strip().split()
        return f'{base[0]}({organ.group(1).strip().replace(" ", "_")})' if base else ''
    parts = code.split()
    return parts[0] if parts else ''


def _parse_labelling(pict_col: str) -> tuple[list[str], str]:
    """Sütun 6: GHS kodları + son satır sinyal kelimesi."""
    items   = _lines(pict_col)
    signal  = ''
    pictos  = []
    for item in items:
        if re.match(r'GHS\d{2}', item, re.IGNORECASE):
            pictos.append(item.upper()[:5])
        elif item.lower() in _SIGNAL:
            signal = _SIGNAL[item.lower()]
    return pictos, signal


def _parse_m_factors(scl_col: str) -> dict:
    """M=X (acute) / M=X (chronic) değerlerini çek."""
    m = {}
    for match in re.finditer(r'M\s*=\s*(\d+)\s*\(?\s*(acute|chronic)', scl_col, re.IGNORECASE):
        m[match.group(2).lower()] = int(match.group(1))
    return m


def _parse_scl(scl_col: str) -> list[dict]:
    """Basit SCL parse: C >= X% H314 → {h_code, c_min}"""
    result = []
    for line in _lines(scl_col):
        h_match = re.search(r'(H\d{3})', line)
        c_match = re.search(r'(\d+(?:\.\d+)?)\s*%', line)
        if h_match and c_match:
            result.append({
                'h_code': h_match.group(1),
                'class' : '',
                'c_min' : float(c_match.group(1)),
                'c_max' : None,
            })
    return result


def _atp_rank(atp: str) -> int:
    """'CLP00'→0, 'ATP01'→1, 'ATP22'→22, 'CLP00/ATP01'→1 (max al)"""
    nums = re.findall(r'\d+', str(atp))
    return max((int(n) for n in nums), default=0)


def _h4(code: str) -> str:
    return re.sub(r'[^A-Z0-9]', '', code.upper())[:4]


def _is_stricter(new_code: str, old_code: str) -> bool:
    return _SEVERITY.get(_h4(new_code), 99) < _SEVERITY.get(_h4(old_code), 99)


# ── Dosya IO ──────────────────────────────────────────────────────────────────

def _read_json(path: Path) -> dict | None:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding='utf-8'))
        except Exception:
            return None
    return None


def _write_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def _annex6_path(cas: str) -> Path:
    return _ANNEX6 / cas[:2] / f'{cas}.json'


def _cl_path(cas: str) -> Path:
    return _CL_DIR / cas[:2] / f'{cas}.json'


# ── Ana işlem ─────────────────────────────────────────────────────────────────

def process(xlsx_path: str, dry_run: bool = False):
    print(f"\n{'[DRY-RUN] ' if dry_run else ''}Excel açılıyor: {xlsx_path}")
    wb = openpyxl.load_workbook(xlsx_path, read_only=True, data_only=True)
    ws = wb.active
    print(f"Sayfa: '{ws.title}'")

    added    = []
    updated  = []
    skipped  = []
    warnings = []

    row_num = 0
    for row in ws.iter_rows(min_row=7):  # Satır 7'den veri başlıyor
        cas_raw = _cell(row, 3)
        # Birden fazla CAS varsa (örn. "10043-35-3 [1]\n11113-50-1 [2]") → ilkini al
        cas_candidates = re.findall(r'\d{2,7}-\d{2}-\d', cas_raw)
        if not cas_candidates:
            continue
        cas = cas_candidates[0]
        name      = _cell(row, 1)
        ec_no     = _cell(row, 2)
        index_no  = _cell(row, 0)
        haz_class = _cell(row, 4)
        haz_code  = _cell(row, 5)
        pict_raw  = _cell(row, 6)
        suppl_raw = _cell(row, 8)
        scl_raw   = _cell(row, 9)
        notes_raw = _cell(row, 10)
        atp_raw   = _cell(row, 11)

        # ATP etiketi: 'CLP00/ATP01' → 'ATP01' (en yüksek olanı al)
        atp_nums = re.findall(r'ATP(\d+)', atp_raw, re.IGNORECASE)
        atp_label = f'ATP{max(int(n) for n in atp_nums)}' if atp_nums else 'CLP00'

        hazards        = _parse_hazards(haz_class, haz_code)
        pictograms, sg = _parse_labelling(pict_raw)
        m_factors      = _parse_m_factors(scl_raw)
        scl_limits     = _parse_scl(scl_raw)
        suppl_h        = [s for s in _lines(suppl_raw) if re.match(r'EUH\d+', s)]
        notes          = [n for n in _lines(notes_raw) if n]

        new_entry = {
            'cas'      : cas,
            'name'     : name,
            'name_tr'  : '',
            'ec_no'    : ec_no,
            'index_no' : index_no,
            'atp'      : atp_label,
            'notes'    : notes,
            'classification': {
                'hazards'   : hazards,
                'm_factors' : m_factors,
                'scl_limits': scl_limits,
            },
            'labelling': {
                'signal'    : sg,
                'pictograms': pictograms,
                'h_codes'   : [h['h_code'] for h in hazards if h['h_code']],
                'suppl_h'   : suppl_h,
            },
        }

        # ── annex6/ güncelleme kararı ─────────────────────────────────────
        existing = _read_json(_annex6_path(cas))
        if existing is None:
            if not dry_run:
                _write_json(_annex6_path(cas), new_entry)
            added.append(f'{cas} ({name[:40]})')
        else:
            old_rank = _atp_rank(existing.get('atp', 'CLP00'))
            new_rank = _atp_rank(atp_label)
            if new_rank > old_rank:
                if not dry_run:
                    _write_json(_annex6_path(cas), new_entry)
                updated.append(f'{cas} — {existing.get("atp","?")} → {atp_label}')
            else:
                skipped.append(cas)

        # ── cl/ ile karşılaştırma ─────────────────────────────────────────
        cl_entry = _read_json(_cl_path(cas))
        if cl_entry:
            cl_hazards_by_group = {}
            for h in cl_entry.get('classification', {}).get('hazards', []):
                code  = _h4(h.get('h_code', ''))
                group = _H_CLASS_GROUP.get(code)
                if group:
                    cl_hazards_by_group[group] = code

            for h in hazards:
                code  = _h4(h.get('h_code', ''))
                group = _H_CLASS_GROUP.get(code)
                if group and group in cl_hazards_by_group:
                    cl_code = cl_hazards_by_group[group]
                    if _is_stricter(code, cl_code):
                        warnings.append(
                            f'  ⚠  {cas} ({name[:35]}): '
                            f'cl/={cl_code} ← Annex VI={code} daha sıkı — cl/ güncellenmeli'
                        )

        row_num += 1
        if row_num % 500 == 0:
            print(f'  ... {row_num} satır işlendi')

    # ── Rapor ────────────────────────────────────────────────────────────────
    lines = [
        f"ECHA CLP Annex VI Güncelleme Raporu {'[DRY-RUN]' if dry_run else ''}",
        '=' * 60,
        f'Excel        : {xlsx_path}',
        f'Toplam madde : {row_num}',
        f'Yeni eklenen : {len(added)}',
        f'Güncellenen  : {len(updated)}',
        f'Atlanan      : {len(skipped)}',
        f'cl/ uyarısı  : {len(warnings)}',
        '',
    ]
    if added:
        lines += [f'\nYeni Eklenenler ({len(added)}):'] + [f'  + {a}' for a in added[:100]]
        if len(added) > 100:
            lines.append(f'  ... ve {len(added)-100} madde daha')
    if updated:
        lines += [f'\nGüncellenenler ({len(updated)}):'] + [f'  ↑ {u}' for u in updated]
    if warnings:
        lines += [f'\ncl/ ile Çelişenler — Manuel Güncelleme Gerekli ({len(warnings)}):'] + warnings

    report = '\n'.join(lines)
    # Windows terminali için güvenli çıktı
    safe_report = report.encode('utf-8', errors='replace').decode('utf-8', errors='replace')
    try:
        print('\n' + safe_report)
    except UnicodeEncodeError:
        print('\n' + safe_report.encode('ascii', errors='replace').decode('ascii'))

    if not dry_run:
        _REPORT.write_text(report, encoding='utf-8')
        print(f'\nRapor kaydedildi: {_REPORT}')
    else:
        print('\n[DRY-RUN] Hicbir dosya degistirilmedi.')


# ── Giriş ─────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='ECHA CLP Annex VI güncelleme scripti')
    parser.add_argument('excel', help='ECHA Annex VI Excel dosyası (.xlsx)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Dosya yazmadan sadece rapor göster')
    args = parser.parse_args()

    if not Path(args.excel).exists():
        print(f'HATA: Dosya bulunamadı: {args.excel}')
        sys.exit(1)

    process(args.excel, dry_run=args.dry_run)
