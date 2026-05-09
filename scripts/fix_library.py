"""
SDSPass — Kütüphane Otomatik Düzeltme Scripti
==============================================
ATP22 Excel kaynağından tespit edilen gerçek hataları düzeltir:

  B3  — Signal word uyuşmazlığı (4 madde)
  B2  — JSON'da eksik H kodları (Excel kaynaklı, CMR dahil)

Kullanım:
    python scripts/fix_library.py [--dry-run]

    --dry-run : Değişiklikleri dosyaya yazmadan sadece rapor eder.
"""

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

# ─── Yollar ───────────────────────────────────────────────────────────────────
EXCEL_PATH = r"C:\Users\user\Desktop\annex_vi_clp_table_atp22_en.xlsx"
CL_DIR     = r"C:\Users\user\Desktop\sdspass\data\cl"
ANNEX6_DIR = r"C:\Users\user\Desktop\sdspass\data\annex6"
REPORT_OUT = r"C:\Users\user\Desktop\sdspass\scripts\fix_library_report.txt"

# ─── H kodu → Pictogram eşlemesi ──────────────────────────────────────────────
H_TO_PICTO = {
    "H200": "GHS01", "H201": "GHS01", "H202": "GHS01", "H203": "GHS01",
    "H204": "GHS01", "H205": "GHS01",
    "H220": "GHS02", "H221": "GHS02", "H222": "GHS02", "H223": "GHS02",
    "H224": "GHS02", "H225": "GHS02", "H226": "GHS02", "H228": "GHS02",
    "H229": "GHS02",
    "H240": "GHS01", "H241": "GHS01", "H242": "GHS02",
    "H250": "GHS02", "H251": "GHS02", "H252": "GHS02",
    "H260": "GHS02", "H261": "GHS02",
    "H270": "GHS03", "H271": "GHS03", "H272": "GHS03",
    "H280": "GHS04", "H281": "GHS04",
    "H290": "GHS05",
    "H300": "GHS06", "H301": "GHS06", "H302": "GHS07",
    "H304": "GHS08",
    "H310": "GHS06", "H311": "GHS06", "H312": "GHS07",
    "H314": "GHS05", "H315": "GHS07", "H317": "GHS07", "H318": "GHS05",
    "H319": "GHS07",
    "H330": "GHS06", "H331": "GHS06", "H332": "GHS07",
    "H334": "GHS08", "H335": "GHS07", "H336": "GHS07",
    "H340": "GHS08", "H341": "GHS08",
    "H350": "GHS08", "H351": "GHS08",
    "H360": "GHS08", "H360D": "GHS08", "H360F": "GHS08",
    "H360FD": "GHS08", "H360Df": "GHS08", "H360Fd": "GHS08",
    "H361": "GHS08", "H361d": "GHS08", "H361f": "GHS08",
    "H361fd": "GHS08",
    "H362": "GHS08",
    "H370": "GHS08", "H371": "GHS08", "H372": "GHS08", "H373": "GHS08",
    "H400": "GHS09", "H410": "GHS09", "H411": "GHS09", "H412": "GHS09",
    "H413": "GHS09",
}

# H kodu → Tehlike sınıfı (classification.hazards için varsayılan)
H_TO_CLASS = {
    "H200": "Expl.", "H201": "Expl. 1.1", "H202": "Expl. 1.2",
    "H203": "Expl. 1.3", "H204": "Expl. 1.4", "H205": "Expl. 1.5",
    "H220": "Flam. Gas 1", "H221": "Flam. Gas 2",
    "H222": "Flam. Aerosol 1", "H223": "Flam. Aerosol 2",
    "H224": "Flam. Liq. 1", "H225": "Flam. Liq. 2",
    "H226": "Flam. Liq. 3", "H228": "Flam. Sol. 1",
    "H240": "Self-react. A", "H241": "Self-react. B",
    "H242": "Self-react. C-F",
    "H250": "Pyr. Liq. 1", "H252": "Self-heat. 1",
    "H260": "Water-react. 1", "H261": "Water-react. 2",
    "H270": "Ox. Gas 1", "H271": "Ox. Liq. 1",
    "H272": "Ox. Liq. 2", "H280": "Press. Gas",
    "H290": "Met. Corr. 1",
    "H300": "Acute Tox. 1", "H301": "Acute Tox. 3",
    "H302": "Acute Tox. 4",
    "H304": "Asp. Tox. 1",
    "H310": "Acute Tox. 1", "H311": "Acute Tox. 3",
    "H312": "Acute Tox. 4",
    "H314": "Skin Corr. 1B", "H315": "Skin Irrit. 2",
    "H317": "Skin Sens. 1", "H318": "Eye Dam. 1",
    "H319": "Eye Irrit. 2",
    "H330": "Acute Tox. 1", "H331": "Acute Tox. 3",
    "H332": "Acute Tox. 4",
    "H334": "Resp. Sens. 1", "H335": "STOT SE 3",
    "H336": "STOT SE 3",
    "H340": "Muta. 1B", "H341": "Muta. 2",
    "H350": "Carc. 1B", "H351": "Carc. 2",
    "H360": "Repr. 1B", "H360D": "Repr. 1B", "H360F": "Repr. 1B",
    "H360FD": "Repr. 1B", "H360Df": "Repr. 1B", "H360Fd": "Repr. 1B",
    "H361": "Repr. 2", "H361d": "Repr. 2", "H361f": "Repr. 2",
    "H361fd": "Repr. 2",
    "H362": "Repr. Add. Cat.",
    "H370": "STOT SE 1", "H371": "STOT SE 2",
    "H372": "STOT RE 1", "H373": "STOT RE 2",
    "H400": "Aquatic Acute 1", "H410": "Aquatic Chronic 1",
    "H411": "Aquatic Chronic 2", "H412": "Aquatic Chronic 3",
    "H413": "Aquatic Chronic 4",
}

# Danger gerektiren H kodları (base kodu ile eşleşme yapılır)
DANGER_H_BASES = {
    "H200", "H201", "H202", "H203", "H204", "H205",
    "H220", "H221", "H222", "H224", "H225",
    "H240", "H241", "H242",
    "H260", "H261",
    "H270", "H271", "H272",
    "H280", "H281",
    "H290",
    "H300", "H301", "H304", "H310", "H311", "H314", "H318",
    "H330", "H331", "H334", "H340", "H350", "H360", "H362",
    "H370", "H372",
}


def h_base(code: str) -> str:
    """H361d → H361, H372(hearing_organs) → H372"""
    m = re.match(r"(H\d{3})", code)
    return m.group(1) if m else code


def is_danger_code(code: str) -> bool:
    base = h_base(code)
    # H360x ailesi → her zaman Danger (Repr 1B)
    if re.match(r"H360", code):
        return True
    # H361x ailesi → Danger (Repr 2)
    if re.match(r"H361", code):
        return True
    return base in DANGER_H_BASES


# ─── Excel okuma ──────────────────────────────────────────────────────────────

def load_excel(path: str) -> dict:
    """CAS → {h_codes: set, signal: str, pictograms: set} mapping döndürür."""
    print("Excel okunuyor...")
    df = pd.read_excel(path, header=4)
    df.columns = [
        "index_no", "name", "ec_no", "cas_no",
        "hazard_classes", "h_codes_class",
        "pictogram_signal", "h_codes_label",
        "suppl_h", "scl", "notes", "atp"
    ]
    df = df[df["index_no"].notna() &
            (df["index_no"] != "Hazard Class and Category Code(s)")].copy()

    mapping = {}
    for _, row in df.iterrows():
        raw_cas = str(row.get("cas_no", "")).strip()
        if not raw_cas or raw_cas in ("-", "nan", ""):
            continue
        for cas in re.split(r"[\n\r]+", raw_cas):
            cas = cas.strip()
            if not cas or cas == "-":
                continue
            h_text  = str(row.get("h_codes_label", "")) if pd.notna(row.get("h_codes_label")) else ""
            ps_text = str(row.get("pictogram_signal", "")) if pd.notna(row.get("pictogram_signal")) else ""
            h_codes = set(re.findall(r"H\d{3}[A-Za-z]*", h_text))
            pictos  = set(re.findall(r"GHS\d{2}", ps_text))
            signal  = ("Danger" if "Dgr" in ps_text or "Danger" in ps_text else
                       "Warning" if "Wng" in ps_text or "Warning" in ps_text else None)
            if cas not in mapping:
                mapping[cas] = {"h_codes": h_codes, "signal": signal, "pictograms": pictos}
    print(f"  CAS eşleşmeli kayıt: {len(mapping)}\n")
    return mapping


# ─── Dosya bul ────────────────────────────────────────────────────────────────

def find_json_for_cas(cas: str, base_dir: str) -> Path | None:
    """CAS numarasına göre JSON dosyasını bul."""
    prefix = cas.split("-")[0] if "-" in cas else cas
    search_dir = Path(base_dir) / prefix
    if search_dir.exists():
        target = search_dir / f"{cas}.json"
        if target.exists():
            return target
    # Prefix dizini yoksa tüm ağacı tara (yavaş ama güvenli)
    for f in Path(base_dir).rglob(f"{cas}.json"):
        return f
    return None


def all_json_files(base_dir: str):
    """Dizindeki tüm JSON dosyalarını CAS → Path şeklinde döndürür."""
    result = {}
    for f in Path(base_dir).rglob("*.json"):
        try:
            with open(f, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            cas = data.get("cas", "").strip()
            if cas:
                result[cas] = (f, data)
        except Exception:
            pass
    return result


# ─── Düzeltme fonksiyonları ───────────────────────────────────────────────────

def fix_signal(data: dict, new_signal: str) -> bool:
    """labelling.signal'ı düzelt. True → değişti."""
    old = data.get("labelling", {}).get("signal", "")
    if old == new_signal:
        return False
    data.setdefault("labelling", {})["signal"] = new_signal
    return True


def fix_missing_h_codes(data: dict, missing_h: set) -> dict:
    """
    Eksik H kodlarını labelling.h_codes ve classification.hazards'a ekle.
    Pictogramları ve signal word'ü de güncelle.
    Returns: {added_h, added_pictos, signal_changed}
    """
    changes = {"added_h": [], "added_pictos": [], "signal_changed": False}
    labelling = data.setdefault("labelling", {})
    classification = data.setdefault("classification", {})

    current_h_label = set(labelling.get("h_codes", []))
    current_pictos  = set(labelling.get("pictograms", []))
    current_signal  = labelling.get("signal", "Warning")
    current_haz_set = {h["h_code"] for h in classification.get("hazards", [])}

    for h in sorted(missing_h):
        # labelling.h_codes'a ekle
        if h not in current_h_label:
            current_h_label.add(h)
            changes["added_h"].append(h)

        # classification.hazards'a ekle (zaten yoksa)
        if h not in current_haz_set:
            cls_name = H_TO_CLASS.get(h, "")
            if cls_name:
                classification.setdefault("hazards", []).append(
                    {"class": cls_name, "h_code": h}
                )
                current_haz_set.add(h)

        # Pictogram ekle
        picto = H_TO_PICTO.get(h)
        if picto and picto not in current_pictos:
            current_pictos.add(picto)
            changes["added_pictos"].append(picto)

    # Signal word güncelle
    all_h = current_h_label | current_haz_set
    if any(is_danger_code(c) for c in all_h) and current_signal != "Danger":
        labelling["signal"] = "Danger"
        changes["signal_changed"] = True

    # Sıralı listeler olarak kaydet
    labelling["h_codes"]    = sorted(current_h_label)
    labelling["pictograms"] = sorted(current_pictos)

    return changes


# ─── Ana işlem ────────────────────────────────────────────────────────────────

def process_directory(base_dir: str, excel_map: dict, dry_run: bool) -> list:
    """Dizindeki tüm JSON'ları tara, düzelt, sonuçları döndür."""
    label = Path(base_dir).name
    print(f"\n{'='*60}")
    print(f"  {label} taranıyor...")
    print(f"{'='*60}")

    all_files = all_json_files(base_dir)
    report = []
    b2_fixed = 0
    b3_fixed = 0

    for cas, (fpath, data) in sorted(all_files.items()):
        if cas not in excel_map:
            continue

        xl = excel_map[cas]
        xl_h      = xl["h_codes"]
        xl_signal = xl["signal"]

        labelling = data.get("labelling", {})
        json_h    = set(labelling.get("h_codes", []))
        json_suppl = set(labelling.get("suppl_h", []))
        json_signal = labelling.get("signal", "")

        changed = False
        entry = {"cas": cas, "name": data.get("name", ""), "file": str(fpath),
                 "b3": None, "b2_added": [], "b2_pictos": [], "signal_auto": False}

        # ── B3: Signal word uyuşmazlığı ─────────────────────────────────────
        if xl_signal and json_signal and xl_signal != json_signal:
            entry["b3"] = f"{json_signal} → {xl_signal}"
            if not dry_run:
                data["labelling"]["signal"] = xl_signal
            changed = True
            b3_fixed += 1

        # ── B2: Eksik H kodları ──────────────────────────────────────────────
        missing = xl_h - json_h - json_suppl
        if missing:
            if not dry_run:
                chg = fix_missing_h_codes(data, missing)
                entry["b2_added"]  = chg["added_h"]
                entry["b2_pictos"] = chg["added_pictos"]
                entry["signal_auto"] = chg["signal_changed"]
            else:
                entry["b2_added"]  = sorted(missing)
                # Hangi pictogramlar eklenir?
                new_pictos = {H_TO_PICTO[h] for h in missing if h in H_TO_PICTO}
                cur_pictos = set(labelling.get("pictograms", []))
                entry["b2_pictos"] = sorted(new_pictos - cur_pictos)
                entry["signal_auto"] = (
                    json_signal != "Danger" and
                    any(is_danger_code(h) for h in missing)
                )
            changed = True
            b2_fixed += 1

        # ── Kaydet ──────────────────────────────────────────────────────────
        if changed:
            report.append(entry)
            if not dry_run:
                with open(fpath, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"  B3 düzeltme: {b3_fixed}")
    print(f"  B2 düzeltme: {b2_fixed}")
    return report


# ─── Rapor yaz ───────────────────────────────────────────────────────────────

def write_report(cl_report: list, a6_report: list, dry_run: bool):
    lines = []
    def w(s=""): lines.append(s)

    mode = "[DRY-RUN — Değişiklik YOK]" if dry_run else "[GERÇEK — Değişiklikler kaydedildi]"
    w("=" * 70)
    w(f"SDSPass — Kütüphane Düzeltme Raporu  {mode}")
    w("=" * 70)
    w()

    for src, rpt in [("data/cl", cl_report), ("data/annex6", a6_report)]:
        b3_items = [r for r in rpt if r["b3"]]
        b2_items = [r for r in rpt if r["b2_added"]]
        w(f"── {src} ─────────────────────────────────────────────")
        w(f"   B3 signal düzeltme : {len(b3_items)}")
        w(f"   B2 H kodu ekleme   : {len(b2_items)}")
        w()

        if b3_items:
            w("  [B3 — Signal Word Düzeltmeleri]")
            for r in b3_items:
                w(f"    {r['cas']:20s} {r['name'][:40]}")
                w(f"         {r['b3']}")
            w()

        if b2_items:
            w("  [B2 — Eksik H Kodu Eklemeleri]")
            for r in b2_items:
                sig_note = " ← signal Danger yapıldı" if r["signal_auto"] else ""
                w(f"    {r['cas']:20s} {r['name'][:38]}")
                w(f"         H eklendi : {r['b2_added']}")
                if r["b2_pictos"]:
                    w(f"         Picto eklendi: {r['b2_pictos']}")
                if sig_note:
                    w(f"         {sig_note}")
            w()

    report_text = "\n".join(lines)
    with open(REPORT_OUT, "w", encoding="utf-8") as f:
        f.write(report_text)
    print(f"\nRapor kaydedildi: {REPORT_OUT}")
    return report_text


# ─── Giriş noktası ───────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="SDSPass kütüphane otomatik düzeltme")
    parser.add_argument("--dry-run", action="store_true",
                        help="Değişiklikleri kaydetme, sadece rapor et")
    args = parser.parse_args()

    dry_run = args.dry_run
    if dry_run:
        print("*** DRY-RUN modu — hiçbir dosya değiştirilmeyecek ***\n")

    # 1. Excel
    excel_map = load_excel(EXCEL_PATH)

    # 2. data/cl
    cl_report = process_directory(CL_DIR, excel_map, dry_run)

    # 3. data/annex6
    a6_report = process_directory(ANNEX6_DIR, excel_map, dry_run)

    # 4. Rapor
    report = write_report(cl_report, a6_report, dry_run)
    safe_report = report[:3000].encode("cp1254", errors="replace").decode("cp1254")
    print(safe_report)  # İlk 3000 karakteri ekrana yazdır

    total = len(cl_report) + len(a6_report)
    print(f"\nToplam değiştirilen madde: {total}")
    if dry_run:
        print("Gerçekten uygulamak için: python scripts/fix_library.py")
    else:
        print("Değişiklikler uygulandı. Doğrulamak için validate_library.py'yi tekrar çalıştırın.")


if __name__ == "__main__":
    main()
