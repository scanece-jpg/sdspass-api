"""
Annex VI Veri Bütünlüğü Tarama Scripti — QA Katmanı (a1)
=========================================================
data/annex6/ altındaki tüm JSON dosyalarını tarar ve aşağıdaki
sorunları raporlar:

  KRITIK : classification.hazards listesi YOK veya BOŞ
  KRITIK : hazard kaydında 'class' alanı boş string
  KRITIK : zorunlu üst alan eksik (cas, ec_no, classification)
  UYARI  : scl_limits içinde 'class' alanı boş (H314/H315 gibi SCL'li kodlar için önemli)
  UYARI  : labelling.signal eksik veya tanımsız değer
  BILGI  : name_tr boş (tercüme eksikliği — üretimi engellemez)

Kullanım:
  python scripts/scan_annex6_gaps.py              # konsol çıktısı
  python scripts/scan_annex6_gaps.py --csv        # + scan_report.csv kaydeder
  python scripts/scan_annex6_gaps.py --kritik     # sadece KRİTİK bulgular
  python scripts/scan_annex6_gaps.py --cas 1310-73-2   # tek madde
"""

import io
import json
import sys
import argparse
import csv
from pathlib import Path
from typing import List, Dict

# Windows konsolunda UTF-8 zorla
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

_ROOT   = Path(__file__).parent.parent
_A6     = _ROOT / 'data' / 'annex6'
_REPORT = Path(__file__).parent / 'scan_annex6_report.csv'

VALID_SIGNALS = {'Danger', 'Warning', ''}


def scan_file(path: Path) -> List[Dict]:
    findings = []

    try:
        with open(path, encoding='utf-8') as fh:
            data = json.load(fh)
    except json.JSONDecodeError as e:
        findings.append({
            'cas': path.stem, 'path': str(path.relative_to(_ROOT)),
            'severity': 'KRITIK', 'kod': 'JSON_PARSE',
            'mesaj': f'JSON parse hatası: {e}'
        })
        return findings

    cas = data.get('cas', path.stem)
    rel = str(path.relative_to(_ROOT))

    def add(severity, kod, mesaj):
        findings.append({'cas': cas, 'path': rel,
                         'severity': severity, 'kod': kod, 'mesaj': mesaj})

    # ── Zorunlu üst alanlar ──────────────────────────────────────────────
    for field in ('cas', 'ec_no', 'classification'):
        if not data.get(field):
            add('KRITIK', 'ALAN_EKSIK', f"'{field}' alanı eksik veya boş")

    clf = data.get('classification', {})

    # ── classification.hazards ───────────────────────────────────────────
    hazards = clf.get('hazards')
    if hazards is None:
        add('KRITIK', 'HAZARDS_YOK', "'classification.hazards' alanı yok")
    elif not isinstance(hazards, list):
        add('KRITIK', 'HAZARDS_TIP', "'classification.hazards' liste değil")
    elif len(hazards) == 0:
        add('KRITIK', 'HAZARDS_BOS', "'classification.hazards' listesi boş — sınıflandırma yok")
    else:
        for i, h in enumerate(hazards):
            if not isinstance(h, dict):
                add('KRITIK', 'HAZARD_TIP', f"hazards[{i}] dict değil")
                continue
            if not (h.get('h_code') or '').strip():
                add('KRITIK', 'HCODE_BOS', f"hazards[{i}] 'h_code' boş veya null")
            cls = h.get('class') or ''
            if not isinstance(cls, str) or not cls.strip():
                add('KRITIK', 'CLASS_BOS',
                    f"hazards[{i}] ({h.get('h_code','?')}) 'class' alanı boş — "
                    f"SCL bant seçimi ve sınıflandırma bozulur")

    # ── scl_limits ───────────────────────────────────────────────────────
    for i, scl in enumerate(clf.get('scl_limits', [])):
        if not isinstance(scl, dict):
            continue
        h_code = scl.get('h_code') or '?'
        if not (scl.get('class') or '').strip():
            # Boş class SCL'de bazı H kodları için sorunsuz (H315/H319),
            # ama H314 için her zaman KRİTİK
            sev = 'KRITIK' if h_code in ('H314', 'H318', 'H317') else 'UYARI'
            add(sev, 'SCL_CLASS_BOS',
                f"scl_limits[{i}] h_code={h_code} 'class' boş — "
                f"bant geçişi (örn. 1A→1B) çalışmaz")
        c_min = scl.get('c_min')
        c_max = scl.get('c_max')
        if c_min is not None and c_max is not None and c_min >= c_max:
            add('KRITIK', 'SCL_ARALIK',
                f"scl_limits[{i}] h_code={h_code} c_min({c_min}) >= c_max({c_max})")

    # ── labelling ────────────────────────────────────────────────────────
    lbl = data.get('labelling', {})
    signal = lbl.get('signal', '')
    if signal not in VALID_SIGNALS:
        add('UYARI', 'SIGNAL_TANIMSIZ',
            f"labelling.signal='{signal}' — beklenen: Danger | Warning | ''")
    if not lbl.get('pictograms') and hazards:
        add('UYARI', 'PIKTOGRAM_YOK',
            "labelling.pictograms boş ama hazards dolu")

    # ── name_tr ──────────────────────────────────────────────────────────
    if not data.get('name_tr', '').strip():
        add('BILGI', 'NAME_TR_BOS', "name_tr boş — Türkçe ad eksik")

    return findings


def main():
    parser = argparse.ArgumentParser(description='Annex VI veri bütünlüğü taraması')
    parser.add_argument('--csv',    action='store_true', help='Raporu CSV olarak kaydet')
    parser.add_argument('--kritik', action='store_true', help='Sadece KRİTİK bulguları göster')
    parser.add_argument('--cas',    type=str,            help='Tek bir CAS no tara')
    args = parser.parse_args()

    # Dosyaları topla
    if args.cas:
        cas_clean = args.cas.strip()
        # CAS → klasör (ilk sayı grubu)
        prefix = cas_clean.split('-')[0]
        targets = list(_A6.glob(f'{prefix}/{cas_clean}.json'))
        if not targets:
            targets = list(_A6.rglob(f'{cas_clean}.json'))
        if not targets:
            print(f'HATA: {cas_clean}.json bulunamadı')
            sys.exit(1)
    else:
        targets = sorted(_A6.rglob('*.json'))

    total_files = len(targets)
    all_findings: List[Dict] = []

    for path in targets:
        all_findings.extend(scan_file(path))

    # Filtrele
    if args.kritik:
        shown = [f for f in all_findings if f['severity'] == 'KRITIK']
    else:
        shown = all_findings

    # ── Konsol çıktısı ───────────────────────────────────────────────────
    sev_order = {'KRITIK': 0, 'UYARI': 1, 'BILGI': 2}
    shown_sorted = sorted(shown, key=lambda x: (sev_order.get(x['severity'], 9), x['cas']))

    counts = {'KRITIK': 0, 'UYARI': 0, 'BILGI': 0}
    for f in all_findings:
        counts[f['severity']] = counts.get(f['severity'], 0) + 1

    print(f'\n{"="*70}')
    print(f'  ANNEX VI TARAMA RAPORU — {total_files} dosya')
    print(f'{"="*70}')
    print(f'  KRİTİK : {counts["KRITIK"]:>5}')
    print(f'  UYARI  : {counts["UYARI"]:>5}')
    print(f'  BİLGİ  : {counts["BILGI"]:>5}')
    print(f'  TOPLAM : {len(all_findings):>5}')
    print(f'{"="*70}\n')

    if not shown_sorted:
        print('  Bulgu yok.\n')
    else:
        current_sev = None
        for f in shown_sorted:
            if f['severity'] != current_sev:
                current_sev = f['severity']
                print(f'\n── {current_sev} ──────────────────────────────────────')
            print(f"  [{f['kod']}] {f['cas']}")
            print(f"         {f['mesaj']}")
            print(f"         → {f['path']}")

    print()

    # ── CSV çıktısı ──────────────────────────────────────────────────────
    if args.csv:
        with open(_REPORT, 'w', newline='', encoding='utf-8') as fh:
            writer = csv.DictWriter(fh, fieldnames=['severity','kod','cas','mesaj','path'])
            writer.writeheader()
            writer.writerows(shown_sorted)
        print(f'  Rapor kaydedildi: {_REPORT}\n')

    # Exit kodu: KRİTİK bulgu varsa 1
    sys.exit(1 if counts['KRITIK'] > 0 else 0)


if __name__ == '__main__':
    main()
