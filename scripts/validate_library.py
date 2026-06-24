"""
SDSPass Library Validation Script
Karşılaştırma: data/cl ve data/annex6 JSON dosyaları vs ATP22 Excel kaynağı
"""

import json
import os
import sys
import re
import pandas as pd
from pathlib import Path
from collections import defaultdict

# ─── Yollar ───────────────────────────────────────────────────────────────────
EXCEL_PATH = r"C:\Users\user\Desktop\annex_vi_clp_table_atp22_en.xlsx"
CL_DIR     = r"C:\Users\user\Desktop\sdspass\data\cl"
ANNEX6_DIR = r"C:\Users\user\Desktop\sdspass\data\annex6"
OUT_PATH   = r"C:\Users\user\Desktop\sdspass\scripts\validate_library_out.txt"

# ─── H kodu → signal word kuralları ──────────────────────────────────────────
DANGER_H_CODES = {
    "H200","H201","H202","H203","H204","H205",
    "H220","H221","H222","H224","H225",
    "H240","H241","H242",
    "H260","H261",
    "H270","H271","H272",
    "H280","H281",
    "H290",
    "H300","H301","H304","H310","H311","H314","H317","H318",
    "H330","H331","H334","H340","H350","H360","H362","H370",
    "H371","H372","H400","H410",
}

# H kodu → beklenen piktogramlar (en az biri eşleşmeli)
HCODE_PICTOGRAM_MAP = {
    "H224": "GHS02", "H225": "GHS02", "H226": "GHS02",
    "H220": "GHS02", "H221": "GHS02", "H222": "GHS02",
    "H228": "GHS02", "H242": "GHS02",
    "H314": "GHS05", "H290": "GHS05", "H318": "GHS05",
    "H300": "GHS06", "H301": "GHS06", "H302": "GHS06",
    "H310": "GHS06", "H311": "GHS06", "H312": "GHS06",
    "H330": "GHS06", "H331": "GHS06", "H332": "GHS06",
    "H340": "GHS08", "H350": "GHS08", "H360": "GHS08",
    "H334": "GHS08", "H317": "GHS08", "H341": "GHS08",
    "H351": "GHS08", "H361": "GHS08", "H370": "GHS08",
    "H371": "GHS08", "H372": "GHS08", "H373": "GHS08",
    "H400": "GHS09", "H410": "GHS09", "H411": "GHS09",
    "H412": "GHS09", "H413": "GHS09",
}

# ATE gerektiren H kodları
ATE_ORAL_H      = {"H300", "H301", "H302"}
ATE_DERMAL_H    = {"H310", "H311", "H312"}
ATE_INHAL_H     = {"H330", "H331", "H332"}

# ─── Yardımcı fonksiyonlar ────────────────────────────────────────────────────

def parse_h_codes(text):
    """Serbest metinden H kodlarını çıkarır."""
    if not isinstance(text, str):
        return set()
    return set(re.findall(r"H\d{3}[A-Z]?", text))

def parse_signal(text):
    """Pictogram/Signal sütunundan sinyal kelimesini çıkarır."""
    if not isinstance(text, str):
        return None
    if "Dgr" in text or "Danger" in text:
        return "Danger"
    if "Wng" in text or "Warning" in text:
        return "Warning"
    return None

def parse_pictograms(text):
    """Pictogram/Signal sütunundan piktogram listesini çıkarır."""
    if not isinstance(text, str):
        return set()
    return set(re.findall(r"GHS\d{2}", text))


# ─── ADIM 1: Excel'i oku ──────────────────────────────────────────────────────

def load_excel(path):
    print("Excel okunuyor...")
    # Satır 4 (0-indexed) başlık satırı, satır 5 alt başlık
    df = pd.read_excel(path, header=4)
    # Sütun adlarını düzelt
    df.columns = [
        "index_no", "name", "ec_no", "cas_no",
        "hazard_classes", "h_codes_class",
        "pictogram_signal", "h_codes_label",
        "suppl_h", "scl", "notes", "atp"
    ]
    # İlk satır alt başlık satırı, at
    df = df[df["index_no"].notna() & (df["index_no"] != "Hazard Class and Category Code(s)")].copy()
    df.reset_index(drop=True, inplace=True)

    print(f"  Toplam Excel satırı: {len(df)}")
    print(f"  Sütunlar: {list(df.columns)}")
    print(f"  İlk 3 satır:")
    print(df[["index_no","name","cas_no","h_codes_label","pictogram_signal"]].head(3).to_string())
    print()
    return df


def build_excel_mapping(df):
    """CAS → {h_codes, signal, pictograms, scl_raw} mapping"""
    mapping = {}
    no_cas = 0
    for _, row in df.iterrows():
        cas = str(row["cas_no"]).strip() if pd.notna(row["cas_no"]) else ""
        if not cas or cas in ("-", "nan", ""):
            no_cas += 1
            continue
        # Birden fazla CAS varsa (satır içi newline ile ayrılmış olabilir)
        for c in re.split(r"[\n\r]+", cas):
            c = c.strip()
            if not c or c == "-":
                continue
            h_codes = parse_h_codes(str(row.get("h_codes_label", "")))
            signal  = parse_signal(str(row.get("pictogram_signal", "")))
            pictos  = parse_pictograms(str(row.get("pictogram_signal", "")))
            scl_raw = str(row.get("scl", "")) if pd.notna(row.get("scl")) else ""
            if c not in mapping:
                mapping[c] = {"h_codes": h_codes, "signal": signal,
                               "pictograms": pictos, "scl": scl_raw}
    print(f"  CAS-eşleşmeli Excel kayıtları: {len(mapping)}")
    print(f"  CAS numarası olmayan Excel satırları: {no_cas}")
    print()
    return mapping


# ─── ADIM 2: JSON kontrolleri ────────────────────────────────────────────────

def check_json(data, excel_map, source_label, errors):
    """Tek bir JSON dosyasını kontrol eder, hataları errors dict'ine ekler."""
    cas = data.get("cas", "")
    name = data.get("name", "")
    key = f"{cas} ({name}) [{source_label}]"

    labelling = data.get("labelling", {})
    classification = data.get("classification", {})
    hazards = classification.get("hazards", [])
    scl_limits = classification.get("scl_limits", [])

    json_h_codes_label  = set(labelling.get("h_codes", []))
    json_h_codes_class  = {h["h_code"] for h in hazards if "h_code" in h}
    json_signal         = labelling.get("signal", "")
    json_pictograms     = set(labelling.get("pictograms", []))
    json_suppl          = set(labelling.get("suppl_h", []))
    all_h_codes         = json_h_codes_label | json_h_codes_class

    # A1: name_tr boş mu?
    if not data.get("name_tr", "").strip():
        errors["A1_name_tr_empty"].append(key)

    # A2: Signal word vs H codes tutarlılığı
    has_danger_code = bool(all_h_codes & DANGER_H_CODES)
    if has_danger_code and json_signal == "Warning":
        danger_codes = all_h_codes & DANGER_H_CODES
        errors["A2_signal_should_be_danger"].append(
            f"{key} | Danger gerektiren kodlar: {sorted(danger_codes)}"
        )
    elif not has_danger_code and all_h_codes and json_signal == "Danger":
        errors["A2_signal_should_be_warning"].append(
            f"{key} | Mevcut H kodları: {sorted(all_h_codes)}"
        )

    # A3: Piktogram vs H codes
    for h_code, expected_ghs in HCODE_PICTOGRAM_MAP.items():
        if h_code in all_h_codes and expected_ghs not in json_pictograms:
            errors["A3_missing_pictogram"].append(
                f"{key} | {h_code} var ama {expected_ghs} yok | Mevcut: {sorted(json_pictograms)}"
            )

    # A4: ATE değerleri (basit varlık kontrolü — json içinde "ate" alanı aranır)
    ate_data = data.get("ate", {}) or {}
    if all_h_codes & ATE_ORAL_H and not ate_data.get("oral"):
        errors["A4_missing_ate_oral"].append(
            f"{key} | {sorted(all_h_codes & ATE_ORAL_H)} var ama oral ATE yok"
        )
    if all_h_codes & ATE_DERMAL_H and not ate_data.get("dermal"):
        errors["A4_missing_ate_dermal"].append(
            f"{key} | {sorted(all_h_codes & ATE_DERMAL_H)} var ama dermal ATE yok"
        )
    if all_h_codes & ATE_INHAL_H and not ate_data.get("inhalation"):
        errors["A4_missing_ate_inhalation"].append(
            f"{key} | {sorted(all_h_codes & ATE_INHAL_H)} var ama inhalasyon ATE yok"
        )

    # A5: SCL c_min/c_max 0-100 arasında mı?
    for scl in scl_limits:
        c_min = scl.get("c_min")
        c_max = scl.get("c_max")
        if c_min is not None and not (0 <= float(c_min) <= 100):
            errors["A5_scl_out_of_range"].append(
                f"{key} | c_min={c_min} geçersiz"
            )
        if c_max is not None and not (0 <= float(c_max) <= 100):
            errors["A5_scl_out_of_range"].append(
                f"{key} | c_max={c_max} geçersiz"
            )

    # B: Excel karşılaştırması
    match_result = {"cas": cas, "matched": False}
    if cas and cas in excel_map:
        match_result["matched"] = True
        xl = excel_map[cas]
        xl_h = xl["h_codes"]
        xl_signal = xl["signal"]

        # B1: JSON'da olan ama Excel'de olmayan H kodları
        extra_in_json = json_h_codes_label - xl_h - json_suppl
        # Bazı kodlar sadece sınıflandırmada olup etiketlemede olmayabilir — yalnızca labelling H kodlarını karşılaştır
        if extra_in_json:
            errors["B1_json_extra_h"].append(
                f"{key} | JSON'da fazla: {sorted(extra_in_json)} | Excel: {sorted(xl_h)}"
            )

        # B2: Excel'de olan ama JSON'da olmayan H kodları
        missing_in_json = xl_h - json_h_codes_label - json_suppl
        if missing_in_json:
            errors["B2_json_missing_h"].append(
                f"{key} | JSON'da eksik: {sorted(missing_in_json)} | Excel: {sorted(xl_h)}"
            )

        # B3: Signal word uyuşmazlığı
        if xl_signal and json_signal and xl_signal != json_signal:
            errors["B3_signal_mismatch"].append(
                f"{key} | JSON={json_signal} | Excel={xl_signal}"
            )

    return match_result


def scan_directory(base_dir, excel_map, source_label):
    """Dizin altındaki tüm JSON'ları tarar."""
    errors = defaultdict(list)
    total = 0
    matched = 0
    unmatched_cas = []

    base = Path(base_dir)
    json_files = list(base.rglob("*.json"))
    print(f"  {source_label}: {len(json_files)} JSON dosyası bulundu")

    for jf in json_files:
        try:
            with open(jf, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            errors["PARSE_ERROR"].append(f"{jf}: {e}")
            continue

        total += 1
        res = check_json(data, excel_map, source_label, errors)
        if res["matched"]:
            matched += 1
        else:
            unmatched_cas.append(res["cas"])

    return errors, total, matched, unmatched_cas


# ─── ADIM 3: Rapor yaz ───────────────────────────────────────────────────────

ERROR_LABELS = {
    "A1_name_tr_empty":         "A1 — name_tr boş",
    "A2_signal_should_be_danger":  "A2 — Signal 'Danger' olmalı",
    "A2_signal_should_be_warning": "A2 — Signal 'Warning' olmalı",
    "A3_missing_pictogram":     "A3 — Eksik piktogram",
    "A4_missing_ate_oral":      "A4 — Eksik oral ATE",
    "A4_missing_ate_dermal":    "A4 — Eksik dermal ATE",
    "A4_missing_ate_inhalation":"A4 — Eksik inhalasyon ATE",
    "A5_scl_out_of_range":      "A5 — SCL değeri 0-100 dışı",
    "B1_json_extra_h":          "B1 — JSON'da Excel'de olmayan H kodu",
    "B2_json_missing_h":        "B2 — JSON'da Excel kaynağından eksik H kodu",
    "B3_signal_mismatch":       "B3 — Signal word uyuşmazlığı",
    "PARSE_ERROR":              "PARSE — JSON parse hatası",
}

MAX_EXAMPLES = 20


def build_report(cl_errors, cl_total, cl_matched, cl_unmatched,
                 a6_errors, a6_total, a6_matched, a6_unmatched):
    lines = []
    def w(s=""):
        lines.append(s)

    w("=" * 80)
    w("SDSPass — ATP22 Doğrulama Raporu")
    w("=" * 80)
    w()

    # Özet
    w("── ÖZET ──────────────────────────────────────────────────────────────────────")
    w(f"  data/cl    : {cl_total} madde kontrol edildi")
    w(f"    Excel eşleşen   : {cl_matched}")
    w(f"    Excel eşleşmeyen: {len(cl_unmatched)}  (CAS yok veya Excel'de bulunmuyor)")
    w()
    w(f"  data/annex6: {a6_total} madde kontrol edildi")
    w(f"    Excel eşleşen   : {a6_matched}")
    w(f"    Excel eşleşmeyen: {len(a6_unmatched)}  (CAS yok veya Excel'de bulunmuyor)")
    w()

    # Hata sayıları
    all_keys = sorted(set(list(cl_errors.keys()) + list(a6_errors.keys())))
    w("── HATA SAYILARI ─────────────────────────────────────────────────────────────")
    w(f"  {'Hata Tipi':<45} {'data/cl':>10} {'data/annex6':>12}")
    w(f"  {'-'*45} {'-'*10} {'-'*12}")
    grand_cl = 0
    grand_a6 = 0
    for k in all_keys:
        label = ERROR_LABELS.get(k, k)
        n_cl = len(cl_errors.get(k, []))
        n_a6 = len(a6_errors.get(k, []))
        grand_cl += n_cl
        grand_a6 += n_a6
        w(f"  {label:<45} {n_cl:>10} {n_a6:>12}")
    w(f"  {'TOPLAM':<45} {grand_cl:>10} {grand_a6:>12}")
    w()

    # Detaylar
    for src_label, errors in [("data/cl", cl_errors), ("data/annex6", a6_errors)]:
        w("=" * 80)
        w(f"  DETAYLAR — {src_label}")
        w("=" * 80)
        for k in all_keys:
            items = errors.get(k, [])
            if not items:
                continue
            label = ERROR_LABELS.get(k, k)
            w(f"\n  [{label}]  ({len(items)} adet)")
            for i, item in enumerate(items[:MAX_EXAMPLES]):
                w(f"    {i+1:>3}. {item}")
            if len(items) > MAX_EXAMPLES:
                w(f"    ... ve {len(items) - MAX_EXAMPLES} kayıt daha")
        w()

    return "\n".join(lines)


# ─── ANA AKIŞ ────────────────────────────────────────────────────────────────

def main():
    output_lines = []
    import io

    # Windows konsolunda UTF-8 zorla
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass

    class Tee:
        def __init__(self, *files):
            self.files = files
        def write(self, data):
            for f in self.files:
                try:
                    f.write(data)
                except UnicodeEncodeError:
                    f.write(data.encode('ascii', errors='replace').decode('ascii'))
        def flush(self):
            for f in self.files:
                f.flush()

    buf = io.StringIO()
    orig_stdout = sys.stdout
    sys.stdout = Tee(orig_stdout, buf)

    try:
        print("=" * 80)
        print("SDSPass — ATP22 Doğrulama Scripti")
        print("=" * 80)
        print()

        # 1. Excel oku
        print("ADIM 1: Excel okunuyor...")
        df = load_excel(EXCEL_PATH)

        # 2. Mapping oluştur
        print("ADIM 2: CAS -> Excel mapping olusturuluyor...")
        excel_map = build_excel_mapping(df)

        # 3. data/cl tara
        print("ADIM 3: data/cl taranıyor...")
        cl_errors, cl_total, cl_matched, cl_unmatched = scan_directory(
            CL_DIR, excel_map, "cl"
        )
        print(f"  Tamamlandı. {cl_total} madde, {sum(len(v) for v in cl_errors.values())} hata.\n")

        # 4. data/annex6 tara
        print("ADIM 4: data/annex6 taranıyor...")
        a6_errors, a6_total, a6_matched, a6_unmatched = scan_directory(
            ANNEX6_DIR, excel_map, "annex6"
        )
        print(f"  Tamamlandı. {a6_total} madde, {sum(len(v) for v in a6_errors.values())} hata.\n")

        # 5. Rapor
        print("ADIM 5: Rapor oluşturuluyor...")
        report = build_report(
            cl_errors, cl_total, cl_matched, cl_unmatched,
            a6_errors, a6_total, a6_matched, a6_unmatched
        )
        print(report)

    finally:
        sys.stdout = orig_stdout
        content = buf.getvalue()
        with open(OUT_PATH, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"\nÇıktı dosyaya kaydedildi: {OUT_PATH}")


if __name__ == "__main__":
    main()
