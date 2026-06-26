"""
verify_with_api.py — Claude API ile veri doğrulama

Doğrulananlar:
  1. codes_i18n.py H/P/EUH TR metinleri  → sea-etiketleme-ambalajlama-rehberi.pdf
  2. sea_ek6_tr.json örnek girdileri      → sea_ek6_l-ste_...docx

Kullanım:
  python scripts/verify_with_api.py
  python scripts/verify_with_api.py --only codes   # sadece H/P/EUH
  python scripts/verify_with_api.py --only sea_ek6 # sadece SEA Ek-6
"""

import json, base64, os, sys, re, zipfile, random, argparse
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv()

import anthropic
client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))

REPORT_PATH = ROOT / "data" / "verification_report.md"
MODEL       = "claude-sonnet-4-6"
NS          = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}


# ─── Yardımcılar ──────────────────────────────────────────────────────────────

def pdf_block(path: Path) -> dict:
    data = base64.standard_b64encode(path.read_bytes()).decode('utf-8')
    return {
        "type": "document",
        "source": {"type": "base64", "media_type": "application/pdf", "data": data}
    }


def cell_text(cell) -> str:
    lines = []
    for p in cell.findall('.//w:p', NS):
        t = ''.join(e.text or '' for e in p.findall('.//w:t', NS)).replace('\xa0', ' ').strip()
        if t:
            lines.append(t)
    return '\n'.join(lines)


# ─── 1. H / P / EUH doğrulama ────────────────────────────────────────────────

def verify_codes() -> str:
    print("  PDF'ler yükleniyor...")
    pdf1 = pdf_block(ROOT / "sds-knowledge" / "tr" / "sea-etiketleme-ambalajlama-rehberi.pdf")
    pdf2 = pdf_block(ROOT / "sds-knowledge" / "tr" / "31330 tr yönetmelik.pdf")

    from app.services.codes_i18n import H_STMTS, P_STMTS, EUH_STMTS
    h   = H_STMTS.get('TR', {})
    p   = P_STMTS.get('TR', {})
    euh = EUH_STMTS.get('TR', {})

    def fmt(d): return "\n".join(f"  {k}: {v}" for k, v in sorted(d.items()))

    kod_metni = (
        f"H KODLARI ({len(h)} adet):\n{fmt(h)}\n\n"
        f"EUH KODLARI ({len(euh)} adet):\n{fmt(euh)}\n\n"
        f"P KODLARI ({len(p)} adet):\n{fmt(p)}"
    )

    print("  API'ye gönderiliyor...")
    response = client.messages.create(
        model=MODEL,
        max_tokens=8096,
        messages=[{
            "role": "user",
            "content": [
                pdf1, pdf2,
                {"type": "text", "text": f"""Bu iki PDF, Türkiye'nin SEA (Sınıflandırma, Etiketleme ve Ambalajlama)
Yönetmeliği kapsamında yayınlanmış resmi belgelerdir.

Bizim sistemimizde aşağıdaki Türkçe H, EUH ve P kodu metinleri kullanılmaktadır:

{kod_metni}

Lütfen PDF'lerdeki resmi Türkçe metinlerle karşılaştır ve şu formatta raporla:

## HATALI METİNLER
| Kod | Sistemdeki metin | Doğru metin (PDF) |
|-----|-----------------|-------------------|
(tablo buraya)

## EKSİK KODLAR (PDF'de var ama sistemde yok)
- KOD: metin

## FAZLA KODLAR (Sistemde var ama PDF'de yok)
- KOD: metin

## ÖZET
- Kontrol edilen toplam kod: X
- Hatalı: X
- Eksik: X
- Fazla: X
- Doğru: X"""}
            ]
        }]
    )
    return response.content[0].text


# ─── 2. sea_ek6_tr.json doğrulama ────────────────────────────────────────────

def verify_sea_ek6(sample_size: int = 40) -> str:
    print("  JSON ve DOCX yükleniyor...")
    db   = json.loads((ROOT / "data" / "sea_ek6_tr.json").read_text(encoding='utf-8'))
    real = {k: v for k, v in db.items() if '_alias' not in v}

    random.seed(42)
    keys   = random.sample(list(real.keys()), min(sample_size, len(real)))
    sample = {k: real[k] for k in keys}
    cas_set = set(keys)

    docx_path = ROOT / "sds-knowledge" / "tr" / "sea_ek6_l-ste_15062020-20200618142549.docx"
    with zipfile.ZipFile(docx_path) as z:
        xml_str = z.read("word/document.xml").decode("utf-8")
    root = ET.fromstring(xml_str)
    rows = root.findall('.//w:tr', NS)

    found = []
    for row in rows[2:]:
        cells = row.findall('w:tc', NS)
        if len(cells) < 9:
            continue
        cas_raw  = cell_text(cells[5])
        cas_list = re.findall(r'\d{2,7}-\d{2}-\d\b', re.sub(r'\[\d+\]', ' ', cas_raw))
        if not any(c in cas_set for c in cas_list):
            continue
        entry = {
            'cas'        : cas_list[0] if cas_list else '',
            'index_no'   : cell_text(cells[0]),
            'name_en'    : cell_text(cells[1]),
            'name_tr'    : cell_text(cells[2]),
            'notes'      : cell_text(cells[3]),
            'ec_no'      : cell_text(cells[4]),
            'class'      : cell_text(cells[6]) if len(cells) > 6 else '',
            'h_code'     : cell_text(cells[7]) if len(cells) > 7 else '',
            'scl'        : cell_text(cells[11]) if len(cells) > 11 else '',
        }
        found.append(entry)

    print("  API'ye gönderiliyor...")
    response = client.messages.create(
        model=MODEL,
        max_tokens=8096,
        messages=[{
            "role": "user",
            "content": f"""Aşağıda iki veri seti var. Bunları CAS numarasına göre eşleştirip karşılaştır.

## 1. SİSTEMİMİZDEKİ VERİ (sea_ek6_tr.json — {len(sample)} örnek):
{json.dumps(sample, ensure_ascii=False, indent=2)}

## 2. WORD BELGESİNDEN ÇIKARILAN VERİ (sea_ek6_l-ste docx):
{json.dumps(found, ensure_ascii=False, indent=2)}

Şu alanları kontrol et:
- classification listesi (tehlike sınıfı + H kodu çiftleri)
- notes (notlar)
- scl_limits (konsantrasyon sınırları)
- m_factors (M faktörleri)
- euh_codes

Şu formatta raporla:

## HATALI KAYITLAR
| CAS | Alan | Sistemdeki değer | Belgedeki doğru değer |
|-----|------|-----------------|----------------------|
(tablo buraya)

## ÖZET
- Karşılaştırılan madde: X
- Hatalı kayıt: X
- Doğru kayıt: X
- Belge'de bulunup sistemde olmayan: X"""
        }]
    )
    return response.content[0].text


# ─── Ana akış ─────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--only', choices=['codes', 'sea_ek6'], default=None)
    args = parser.parse_args()

    lines = [
        "# SDSPass Doğrulama Raporu",
        f"Tarih: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"Model: {MODEL}",
        "",
    ]

    if args.only != 'sea_ek6':
        print("\n── 1/2  H / P / EUH KOD DOĞRULAMASI ──")
        result = verify_codes()
        lines += ["---", "## 1. H/P/EUH KOD DOĞRULAMASI", "", result, ""]
        print(result)

    if args.only != 'codes':
        print("\n── 2/2  SEA EK-6 DOĞRULAMASI ──")
        result = verify_sea_ek6()
        lines += ["---", "## 2. SEA EK-6 DOĞRULAMASI", "", result, ""]
        print(result)

    REPORT_PATH.parent.mkdir(exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines), encoding='utf-8')
    print(f"\nRapor kaydedildi: {REPORT_PATH}")


if __name__ == '__main__':
    main()
