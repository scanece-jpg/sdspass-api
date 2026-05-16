"""
M-Faktör Doğrulama ve Düzeltme Scripti
========================================
ECHA CLP Annex VI Excel'inden M-faktörleri okuyup mevcut JSON dosyalarıyla
karşılaştırır. Farklı olanları raporlar ve isteğe bağlı olarak düzeltir.

name_tr, ate, scl gibi özel alanlar KORUNUR — sadece m_factors güncellenir.

Kullanım:
  python scripts/validate_m_factors.py <excel_yolu>            # sadece rapor
  python scripts/validate_m_factors.py <excel_yolu> --fix      # düzelt + rapor
  python scripts/validate_m_factors.py <excel_yolu> --fix --cl # annex6 + cl/ ikisini de

Örnek:
  python scripts/validate_m_factors.py "C:/Users/user/Desktop/annex_vi_clp_table_atp22_en.xlsx" --fix
"""

import sys, json, re, argparse
from pathlib import Path

try:
    import openpyxl
except ImportError:
    print("HATA: openpyxl kurulu değil → pip install openpyxl")
    sys.exit(1)

_ROOT   = Path(__file__).parent.parent
_A6     = _ROOT / 'data' / 'annex6'
_CL     = _ROOT / 'data' / 'cl'
_REPORT = Path(__file__).parent / 'validate_m_factors_report.txt'


def _cell(row, idx: int) -> str:
    try:
        v = row[idx].value
        return str(v).strip() if v is not None else ''
    except IndexError:
        return ''


def _parse_m_factors(scl_col: str, hazards: list) -> dict:
    """
    M-faktör parse (update_annex_vi.py ile aynı düzeltilmiş mantık).
    Format 1: M=10 (acute) / M=10 (chronic) → açık etiket
    Format 2: M=10 (speciifer yok) → SADECE acute; kronik varsayılan=1
    """
    m = {}
    # Format 1: açıkça etiketlenmiş
    for match in re.finditer(r'M\s*=\s*(\d+)\s*\(?\s*(acute|chronic)', scl_col, re.IGNORECASE):
        m[match.group(2).lower()] = int(match.group(1))
    if m:
        return m

    # Format 2: tek M değeri → sadece acute
    solo = re.search(r'\bM\s*=\s*(\d+)\b', scl_col, re.IGNORECASE)
    if solo:
        mval = int(solo.group(1))
        h_set = {re.sub(r'[^A-Z0-9]', '', h.get('h_code', '').upper())[:4]
                 for h in hazards}
        has_acute   = bool(h_set & {'H400', 'H401', 'H402'})
        has_chronic = bool(h_set & {'H410', 'H411', 'H412', 'H413'})
        if has_acute:
            m['acute'] = mval
            # Kronik belirtilmemiş → varsayılan 1 (CLP Part 4 §4.1)
        elif has_chronic:
            m['chronic'] = mval
        else:
            m['acute'] = mval  # fallback
    return m


def _parse_hazards(haz_class: str, haz_code: str) -> list:
    classes = [l.strip() for l in haz_class.splitlines() if l.strip()]
    norm    = haz_code.replace('\r\n', '\n').replace('\r', '\n')
    hcodes  = [s.strip() for s in norm.split('\n')]
    result  = []
    for cls, hc in zip(classes, hcodes):
        hc_clean = re.sub(r'[^A-Z0-9]', '', hc.upper())[:5]
        if re.match(r'^H\d{3}', hc_clean):
            result.append({'h_class': cls, 'h_code': hc_clean})
    return result


def run(xlsx_path: str, fix: bool, fix_cl: bool):
    print(f"\nExcel açılıyor: {xlsx_path}")
    wb = openpyxl.load_workbook(xlsx_path, read_only=True, data_only=True)
    ws = wb.active
    print(f"Sayfa: '{ws.title}'\n")

    ok_count      = 0
    mismatch_list = []   # (cas, name, json_mf, excel_mf, json_path)
    not_found     = []   # Excel'de var ama JSON yok
    fixed_count   = 0

    for row in ws.iter_rows(min_row=7):
        cas_raw = _cell(row, 3)
        cas_candidates = re.findall(r'\d{2,7}-\d{2}-\d', cas_raw)
        if not cas_candidates:
            continue
        cas      = cas_candidates[0]
        name     = _cell(row, 1)[:60]
        haz_cls  = _cell(row, 4)
        haz_code = _cell(row, 5)
        scl_raw  = _cell(row, 9)

        hazards    = _parse_hazards(haz_cls, haz_code)
        excel_mf   = _parse_m_factors(scl_raw, hazards)

        if not excel_mf:
            continue  # M-faktörü olmayan madde — kontrol gerekmez

        # annex6/ dosyasını kontrol et
        a6_path = _A6 / cas[:2] / f'{cas}.json'
        if not a6_path.exists():
            not_found.append((cas, name))
            continue

        try:
            data = json.loads(a6_path.read_text(encoding='utf-8'))
        except Exception:
            continue

        json_mf = data.get('classification', {}).get('m_factors', {})

        # Karşılaştır
        differs = False
        for key in ['acute', 'chronic']:
            excel_val = excel_mf.get(key, 1)   # belirtilmemişse varsayılan 1
            json_val  = json_mf.get(key, 1)
            if excel_val != json_val:
                differs = True
                break

        if not differs:
            ok_count += 1
            continue

        mismatch_list.append((cas, name, json_mf, excel_mf, a6_path))

        if fix:
            # Sadece m_factors güncelle — diğer her şey korunur
            data['classification']['m_factors'] = excel_mf
            a6_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
            fixed_count += 1

            # cl/ dosyasını da güncelle
            if fix_cl:
                cl_path = _CL / cas[:2] / f'{cas}.json'
                if cl_path.exists():
                    try:
                        cl_data = json.loads(cl_path.read_text(encoding='utf-8'))
                        cl_data['classification']['m_factors'] = excel_mf
                        cl_path.write_text(json.dumps(cl_data, ensure_ascii=False, indent=2), encoding='utf-8')
                    except Exception:
                        pass

    # ── Rapor ─────────────────────────────────────────────────────────────────
    lines = []
    lines.append("=" * 70)
    lines.append("M-FAKTÖR DOĞRULAMA RAPORU")
    lines.append(f"Excel  : {xlsx_path}")
    lines.append(f"Mod    : {'DÜZELT' if fix else 'SADECE RAPOR'}")
    lines.append("=" * 70)
    lines.append(f"\nEşleşen (doğru)  : {ok_count}")
    lines.append(f"Uyuşmayan (hatalı): {len(mismatch_list)}")
    lines.append(f"JSON bulunamayan  : {len(not_found)}")
    if fix:
        lines.append(f"Düzeltilen       : {fixed_count}")

    if mismatch_list:
        lines.append(f"\n{'─'*70}")
        lines.append("UYUŞMAYAN M-FAKTÖRLER:")
        lines.append(f"{'─'*70}")
        for cas, name, jmf, emf, _ in mismatch_list:
            j_a = jmf.get('acute', 1);   j_c = jmf.get('chronic', 1)
            e_a = emf.get('acute', 1);   e_c = emf.get('chronic', 1)
            status = "[DÜZELTİLDİ]" if fix else "[FARKLI]"
            lines.append(f"  {status} {cas}: {name}")
            lines.append(f"    JSON  → akut={j_a}, kronik={j_c}")
            lines.append(f"    Excel → akut={e_a}, kronik={e_c}")

    if not_found:
        lines.append(f"\n{'─'*70}")
        lines.append("EXCEL'DE VAR AMA JSON DOSYASI YOK (yeni eklenecek):")
        for cas, name in not_found[:20]:
            lines.append(f"  {cas}: {name}")
        if len(not_found) > 20:
            lines.append(f"  ... ve {len(not_found)-20} madde daha")

    report_text = '\n'.join(lines)
    print(report_text)
    _REPORT.write_text(report_text, encoding='utf-8')
    print(f"\nRapor kaydedildi: {_REPORT}")


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('xlsx', help='ECHA CLP Annex VI Excel dosyası')
    ap.add_argument('--fix', action='store_true', help='Farklı olanları düzelt')
    ap.add_argument('--cl',  action='store_true', help='data/cl/ klasörünü de güncelle')
    args = ap.parse_args()
    run(args.xlsx, fix=args.fix, fix_cl=args.cl)
