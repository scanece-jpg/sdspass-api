"""
echa_excel_loader.py — ECHA ATP22 Excel'ini ham satırlara çevirir.

Hiçbir yorum/dönüşüm yapmaz; sadece hücreleri okur ve normalize eder.
Çıktı: list[dict] — her dict bir Index No satırını temsil eder.
"""

import pandas as pd
import re
from pathlib import Path

EXCEL_PATH = Path(__file__).parent.parent / "annex_vi_clp_table_atp22_en.xlsx"

# Sütun indeksleri (0-tabanlı, header=None, skiprows=5)
COL_INDEX_NO   = 0
COL_NAME       = 1
COL_EC_NO      = 2
COL_CAS        = 3
COL_CLASS      = 4   # Hazard Class and Category Code(s)
COL_H_CODE     = 5   # Hazard Statement Code(s)
COL_PICTOGRAM  = 6
COL_LABEL_H    = 7
COL_SUPPL_H    = 8
COL_SCL        = 9   # Specific Conc. Limits, M-factors
COL_NOTES      = 10
COL_ATP        = 11


def _split_lines(cell) -> list[str]:
    """Hücreyi satırlara böler, boşları atar."""
    if pd.isna(cell):
        return []
    return [s.strip() for s in str(cell).split("\n") if s.strip()]


def _parse_cas_list(cell) -> list[str]:
    """
    Hem '\n' hem ';' ile ayrılmış CAS formatlarını destekler.
    '[N]' etiketlerini ve sondaki noktalı virgülleri temizler; '-' ve nan'ı atlar.
    """
    if pd.isna(cell):
        return []
    result = []
    for segment in re.split(r'[\n;]', str(cell)):
        cas = re.sub(r"\s*\[\d+\]", "", segment).strip().rstrip(';').strip()
        if cas and cas != "-":
            result.append(cas)
    return result


def _parse_name_list(cell) -> list[str]:
    """
    'Name [1]\nName2 [2]\n...' formatını isim listesine çevirir.
    """
    result = []
    for line in _split_lines(cell):
        name = re.sub(r"\s*\[\d+\]", "", line).strip()
        if name:
            result.append(name)
    return result


_PRESS_GAS_LABELS = {"Press. Gas", "Basınç Gaz"}

def _zip_class_h(class_cell, h_cell) -> list[dict]:
    """
    Classification ve H-code sütunlarını pozisyona göre eşleştirir.
    Satır 1↔Satır 1, Satır 2↔Satır 2.

    CLP Annex VI Excel'inde "Press. Gas" sınıfı için H kodu sütununda
    H280 satırı bulunmaz (standart sayılır). Bu nedenle sınıf listesinde
    Press. Gas görüldüğünde H kodu listesine H280 enjekte edilir; böylece
    sonraki sınıfların H kodları bir kayma olmadan doğru konuma denk gelir.
    """
    classes = _split_lines(class_cell)
    h_codes = _split_lines(h_cell)

    # Press. Gas olan pozisyonlara H280 enjekte et
    adjusted_h = list(h_codes)
    for i, cls in enumerate(classes):
        if cls.strip() in _PRESS_GAS_LABELS and i <= len(adjusted_h):
            # Bu pozisyonda zaten H280/H281 varsa dokunma
            existing = adjusted_h[i] if i < len(adjusted_h) else ""
            if existing not in ("H280", "H281"):
                adjusted_h.insert(i, "H280")

    length = max(len(classes), len(adjusted_h))
    pairs = []
    for i in range(length):
        cls = classes[i]     if i < len(classes)     else ""
        hc  = adjusted_h[i] if i < len(adjusted_h) else ""
        if cls or hc:
            pairs.append({"class": cls, "h_code": hc})
    return pairs


def load(excel_path: Path = EXCEL_PATH) -> list[dict]:
    """
    Excel'i okur; her Index No satırı için ham dict döner.

    Dönen dict anahtarları:
      index_no, names (list), ec_no, cas_list (list),
      class_h_pairs (list[{class, h_code}]),
      suppl_h (list), scl_raw (str), notes_raw (str), atp (str)
    """
    df = pd.read_excel(excel_path, sheet_name=0, header=None, skiprows=5, dtype=str)

    rows = []
    for _, row in df.iterrows():
        index_no = str(row[COL_INDEX_NO]).strip() if pd.notna(row[COL_INDEX_NO]) else ""
        if not index_no or index_no == "nan":
            continue

        rows.append({
            "index_no":    index_no,
            "names":       _parse_name_list(row[COL_NAME]),
            "ec_no":       str(row[COL_EC_NO]).strip() if pd.notna(row[COL_EC_NO]) else "",
            "cas_list":    _parse_cas_list(row[COL_CAS]),
            "class_h_pairs": _zip_class_h(row[COL_CLASS], row[COL_H_CODE]),
            "suppl_h":     _split_lines(row[COL_SUPPL_H]),
            "scl_raw":     str(row[COL_SCL]).strip() if pd.notna(row[COL_SCL]) else "",
            "notes_raw":   str(row[COL_NOTES]).strip() if pd.notna(row[COL_NOTES]) else "",
            "atp":         str(row[COL_ATP]).strip() if pd.notna(row[COL_ATP]) else "",
        })

    return rows


if __name__ == "__main__":
    import sys, json
    sys.stdout.reconfigure(encoding="utf-8")
    data = load()
    print(f"Toplam satır: {len(data)}")
    print(f"SCL verisi olan: {sum(1 for r in data if r['scl_raw'])}")
    print(f"Çoklu CAS olan: {sum(1 for r in data if len(r['cas_list']) > 1)}")
    print()
    # İlk SCL örneği
    for r in data:
        if r["scl_raw"]:
            print("Örnek SCL satırı:")
            print(json.dumps(r, ensure_ascii=False, indent=2))
            break
