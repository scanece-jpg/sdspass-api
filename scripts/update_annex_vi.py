"""
ECHA CLP Annex VI Güncelleme Scripti
=====================================
Kullanım:
  python scripts/update_annex_vi.py <annex_vi_excel_yolu> [--atp ATP18]

Gereksinim:
  pip install openpyxl

Adımlar:
  1. ECHA sitesinden Annex VI Excel'i indir:
     https://echa.europa.eu/information-on-chemicals/annex-vi-to-clp
  2. Bu scripti çalıştır:
     python scripts/update_annex_vi.py C:/Downloads/clp_annex_vi.xlsx --atp ATP20

Çıktı:
  - data/annex6/**/{cas}.json dosyaları güncellenir / yenileri eklenir
  - data/cl/ ile karşılaştırma raporu yazdırılır (daha sıkı sınıf varsa uyarı verilir)
  - scripts/annex_vi_update_report.txt dosyasına özet yazılır
"""

import sys, json, re, argparse
from pathlib import Path

try:
    import openpyxl
except ImportError:
    print("HATA: openpyxl kurulu değil. Çalıştır: pip install openpyxl")
    sys.exit(1)

# ── Yollar ───────────────────────────────────────────────────────────────────
_ROOT      = Path(__file__).parent.parent
_ANNEX6    = _ROOT / 'data' / 'annex6'
_CL_DIR    = _ROOT / 'data' / 'cl'
_REPORT    = Path(__file__).parent / 'annex_vi_update_report.txt'

_ANNEX6.mkdir(parents=True, exist_ok=True)

# ── Yardımcılar ──────────────────────────────────────────────────────────────

# Signal word kısaltmaları
_SIGNAL = {'dgr': 'Danger', 'wng': 'Warning', 'danger': 'Danger', 'warning': 'Warning'}

# Tehlike kategorisi sertlik sırası (küçük = daha tehlikeli)
_SEVERITY: dict[str, int] = {
    # Repr
    'H360': 1, 'H361': 2, 'H362': 3,
    # Carc / Muta
    'H340': 1, 'H341': 2,
    'H350': 1, 'H351': 2,
    # Akut toks
    'H300': 1, 'H301': 2, 'H302': 3,
    'H310': 1, 'H311': 2, 'H312': 3,
    'H330': 1, 'H331': 2, 'H332': 3,
    # Cilt / Göz
    'H314': 1, 'H315': 2,
    'H318': 1, 'H319': 2,
    # STOT
    'H370': 1, 'H371': 2,
    'H372': 1, 'H373': 2,
    # Sucul
    'H400': 1, 'H401': 2, 'H402': 3,
    'H410': 1, 'H411': 2, 'H412': 3, 'H413': 4,
}

_H_CLASS_GROUP: dict[str, str] = {
    'H224': 'flam_liq',  'H225': 'flam_liq',  'H226': 'flam_liq',
    'H300': 'acute_oral','H301': 'acute_oral', 'H302': 'acute_oral',
    'H310': 'acute_derm','H311': 'acute_derm', 'H312': 'acute_derm',
    'H330': 'acute_inh', 'H331': 'acute_inh',  'H332': 'acute_inh',
    'H314': 'skin',      'H315': 'skin',
    'H318': 'eye',       'H319': 'eye',
    'H317': 'skin_sens', 'H334': 'resp_sens',
    'H340': 'muta',      'H341': 'muta',
    'H350': 'carc',      'H351': 'carc',
    'H360': 'repr',      'H361': 'repr',  'H362': 'repr',
    'H370': 'stot_se',   'H371': 'stot_se',
    'H372': 'stot_re',   'H373': 'stot_re',
    'H400': 'aq_acute',  'H401': 'aq_acute',  'H402': 'aq_acute',
    'H410': 'aq_chron',  'H411': 'aq_chron',  'H412': 'aq_chron', 'H413': 'aq_chron',
}

def _h4(code: str) -> str:
    """H kodundan ilk 4 karakteri al (H360, H361 vs.)."""
    return re.sub(r'[^A-Z0-9]', '', code.upper())[:4]


def _is_stricter(new_code: str, old_code: str) -> bool:
    """new_code, old_code'dan daha mı sıkı?"""
    n = _h4(new_code)
    o = _h4(old_code)
    sn = _SEVERITY.get(n, 99)
    so = _SEVERITY.get(o, 99)
    return sn < so


# ── Excel okuma ──────────────────────────────────────────────────────────────

def _cell(row, idx):
    """Satırdaki hücreyi güvenli oku."""
    try:
        v = row[idx].value
        return str(v).strip() if v is not None else ''
    except IndexError:
        return ''


def _parse_pictograms(text: str) -> list[str]:
    """GHS01, GHS02 … kodlarını listele."""
    return re.findall(r'GHS\d{2}', text.upper())


def _parse_m_factors(text: str) -> dict:
    """M=X (acute) ve M=X (chronic) değerlerini çek."""
    m = {}
    for match in re.finditer(r'M\s*=\s*(\d+)\s*\(?\s*(acute|chronic)', text, re.IGNORECASE):
        val  = int(match.group(1))
        kind = match.group(2).lower()
        m[kind] = val
    return m


def _parse_hazards(class_col: str, hcode_col: str) -> list[dict]:
    """
    Tehlike sınıfı sütunu (örn. "Flam. Liq. 2*; Acute Tox. 3*")
    ile H kodu sütununu (örn. "H225; H301") eşleştir.
    """
    classes = [c.strip() for c in re.split(r'[;\n]', class_col) if c.strip()]
    hcodes  = [h.strip() for h in re.split(r'[;\n]', hcode_col) if h.strip()]
    hazards = []
    for i, cls in enumerate(classes):
        hcode = hcodes[i] if i < len(hcodes) else ''
        hazards.append({'class': cls, 'h_code': hcode})
    return hazards


def _detect_columns(ws) -> dict | None:
    """
    İlk 5 satırı tarayarak sütun indekslerini otomatik tespit et.
    Döndürür: {index, name, ec, cas, haz_class, haz_code, pict, signal, suppl, scl, notes}
    """
    header_keywords = {
        'index':     ['index no', 'index number'],
        'name':      ['international chemical', 'substance name', 'name'],
        'ec':        ['ec no', 'ec number', 'einecs'],
        'cas':       ['cas no', 'cas number', 'cas-no'],
        'haz_class': ['hazard class and category', 'hazard class'],
        'haz_code':  ['hazard statement code', 'h code', 'h-code'],
        'pict':      ['pictogram', 'signal word'],
        'signal':    ['signal word'],
        'scl':       ['specific conc', 'm-factor', 'ate'],
        'notes':     ['notes'],
    }

    for row in ws.iter_rows(min_row=1, max_row=6):
        vals = [str(c.value or '').lower().strip() for c in row]
        if not any(vals):
            continue
        mapping = {}
        for key, keywords in header_keywords.items():
            for kw in keywords:
                for i, v in enumerate(vals):
                    if kw in v and key not in mapping:
                        mapping[key] = i
        if 'cas' in mapping and 'haz_code' in mapping:
            return mapping

    return None


# ── Annex6 dosya okuma / yazma ───────────────────────────────────────────────

def _read_annex6(cas: str) -> dict | None:
    p = _ANNEX6 / cas[:2] / f'{cas}.json'
    if p.exists():
        try:
            return json.loads(p.read_text(encoding='utf-8'))
        except Exception:
            return None
    return None


def _write_annex6(cas: str, data: dict):
    d = _ANNEX6 / cas[:2]
    d.mkdir(parents=True, exist_ok=True)
    (d / f'{cas}.json').write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8'
    )


def _read_cl(cas: str) -> dict | None:
    p = _CL_DIR / cas[:2] / f'{cas}.json'
    if p.exists():
        try:
            return json.loads(p.read_text(encoding='utf-8'))
        except Exception:
            return None
    return None


# ── Ana işlem ────────────────────────────────────────────────────────────────

def process_excel(xlsx_path: str, atp_label: str):
    print(f"\n[1/4] Excel açılıyor: {xlsx_path}")
    wb = openpyxl.load_workbook(xlsx_path, read_only=True, data_only=True)

    # Annex VI sayfasını bul
    ws = None
    for name in wb.sheetnames:
        if 'annex' in name.lower() or 'table' in name.lower() or 'clp' in name.lower():
            ws = wb[name]
            break
    if ws is None:
        ws = wb.active
    print(f"    Sayfa: '{ws.title}'")

    print("[2/4] Sütunlar tespit ediliyor...")
    col_map = _detect_columns(ws)
    if col_map is None:
        print("HATA: Sütun yapısı tanınamadı.")
        print("      Lütfen Excel'i açıp sütun başlıklarını kontrol edin.")
        print("      Beklenen başlıklar: 'Index No', 'CAS No', 'Hazard class and category code(s)'")
        sys.exit(1)
    print(f"    Eşleşen sütunlar: { {k: v for k, v in col_map.items()} }")

    added    = []
    updated  = []
    skipped  = []
    warnings = []  # cl/ ile çelişen maddeler

    print("[3/4] Satırlar işleniyor...")
    row_count = 0
    for row in ws.iter_rows(min_row=2):
        cas_raw = _cell(row, col_map['cas'])
        if not re.match(r'\d{2,7}-\d{2}-\d', cas_raw):
            continue  # CAS değil, atla

        cas        = cas_raw.strip()
        name       = _cell(row, col_map.get('name', 1))
        ec_no      = _cell(row, col_map.get('ec', 2))
        index_no   = _cell(row, col_map.get('index', 0))
        haz_class  = _cell(row, col_map.get('haz_class', 4))
        haz_code   = _cell(row, col_map.get('haz_code', 5))
        pict_raw   = _cell(row, col_map.get('pict', 6))
        signal_raw = _cell(row, col_map.get('signal', 6))
        scl_raw    = _cell(row, col_map.get('scl', 9))
        notes_raw  = _cell(row, col_map.get('notes', 10))

        if not haz_code and not haz_class:
            continue

        # Signal word
        signal = _SIGNAL.get(signal_raw.split()[-1].lower() if signal_raw else '', '')
        if not signal:
            for w in signal_raw.split():
                s = _SIGNAL.get(w.lower(), '')
                if s:
                    signal = s
                    break

        hazards    = _parse_hazards(haz_class, haz_code)
        pictograms = _parse_pictograms(pict_raw + ' ' + haz_class)
        m_factors  = _parse_m_factors(scl_raw)
        notes      = [n.strip() for n in re.split(r'[;,]', notes_raw) if n.strip()]

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
                'scl_limits': [],
            },
            'labelling': {
                'signal'    : signal,
                'pictograms': pictograms,
                'h_codes'   : [h['h_code'] for h in hazards if h['h_code']],
                'suppl_h'   : [],
            },
        }

        existing = _read_annex6(cas)
        if existing is None:
            _write_annex6(cas, new_entry)
            added.append(cas)
        else:
            # ATP güncelleme kontrolü
            old_atp = existing.get('atp', 'CLP00')
            atp_num = lambda s: int(re.sub(r'\D', '', s) or '0')
            if atp_num(atp_label) > atp_num(old_atp):
                _write_annex6(cas, new_entry)
                updated.append(f"{cas} ({old_atp} → {atp_label})")
            else:
                skipped.append(cas)

        # cl/ ile karşılaştır — daha sıkı tehlike var mı?
        cl_entry = _read_cl(cas)
        if cl_entry:
            cl_hazards = {
                _H_CLASS_GROUP.get(_h4(h.get('h_code', '')), None): h.get('h_code', '')
                for h in cl_entry.get('classification', {}).get('hazards', [])
            }
            for h in hazards:
                code  = _h4(h['h_code'])
                group = _H_CLASS_GROUP.get(code)
                if group and group in cl_hazards:
                    cl_code = _h4(cl_hazards[group])
                    if _is_stricter(code, cl_code):
                        warnings.append(
                            f"  ⚠  {cas} ({name[:40]}): "
                            f"cl/={cl_code} ← Annex VI={code} daha sıkı! "
                            f"cl/ dosyası güncellenmeli."
                        )

        row_count += 1
        if row_count % 500 == 0:
            print(f"    ... {row_count} satır işlendi")

    print(f"    Toplam {row_count} madde işlendi.")

    # ── Rapor ────────────────────────────────────────────────────────────────
    print("\n[4/4] Rapor yazılıyor...")
    report_lines = [
        f"ECHA CLP Annex VI Güncelleme Raporu — {atp_label}",
        "=" * 60,
        f"Toplam işlenen: {row_count}",
        f"Yeni eklenen  : {len(added)}",
        f"Güncellenen   : {len(updated)}",
        f"Atlanan(güncel): {len(skipped)}",
        "",
    ]

    if added:
        report_lines += [f"\nYeni Eklenenler ({len(added)}):"] + [f"  + {c}" for c in added[:50]]
        if len(added) > 50:
            report_lines.append(f"  ... ve {len(added)-50} madde daha")

    if updated:
        report_lines += [f"\nGüncellenenler ({len(updated)}):"] + [f"  ↑ {u}" for u in updated]

    if warnings:
        report_lines += [
            f"\ncl/ ile Çelişen Maddeler ({len(warnings)}) — Manuel Güncelleme Gerekli:",
        ] + warnings

    report_text = '\n'.join(report_lines)
    _REPORT.write_text(report_text, encoding='utf-8')

    print(report_text)
    print(f"\nRapor kaydedildi: {_REPORT}")


# ── Giriş noktası ─────────────────────────────────────────────────────────────

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='ECHA CLP Annex VI güncelleme scripti')
    parser.add_argument('excel', help='İndirilen ECHA Annex VI Excel dosyası (.xlsx)')
    parser.add_argument('--atp', default='ATP20', help='ATP sürüm etiketi (örn. ATP20)')
    args = parser.parse_args()

    if not Path(args.excel).exists():
        print(f"HATA: Dosya bulunamadı: {args.excel}")
        sys.exit(1)

    process_excel(args.excel, args.atp)
