"""
check_json_conflicts.py — JSON veritabanlarını resmi belgelerle karşılaştırır.

Kontrol edilen dosyalar:
  data/sea_ek6_tr.json   → SEA Ek-6 Word belgesi (KKDİK Ek-6)
  data/substance_db.json → CLP Annex VI belgeleri (ECHA ATP22)

Her 10 kayıt bir API çağrısında toplu gönderilir. Bulunan çelişkiler
data/conflict_report.md dosyasına yazılır.

Kullanım:
  python scripts/check_json_conflicts.py                  # her dosyadan 50 kayıt
  python scripts/check_json_conflicts.py --n 100          # 100 kayıt
  python scripts/check_json_conflicts.py --file sea       # sadece sea_ek6_tr.json
  python scripts/check_json_conflicts.py --file substance # sadece substance_db.json
  python scripts/check_json_conflicts.py --all            # tümü (pahalı!)
"""

import argparse
import json
import math
import os
import sys
import time
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv()

import anthropic
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

MODEL       = "claude-haiku-4-5-20251001"
BATCH_SIZE  = 10   # kayıt/çağrı
REPORT_PATH   = ROOT / "data" / "conflict_report.md"
PROGRESS_PATH = ROOT / "data" / "conflict_progress.json"  # taranan CAS'lar burada

# ── Belge metinleri ────────────────────────────────────────────────────────────

def _load_doc_text(path: Path, max_chars: int = 15_000) -> str:
    """pdfplumber veya zipfile ile belge metni çıkarır."""
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        try:
            import pdfplumber
            parts = []
            with pdfplumber.open(path) as pdf:
                for page in pdf.pages:
                    t = page.extract_text() or ""
                    try:
                        t = t.encode("latin-1").decode("utf-8")
                    except (UnicodeEncodeError, UnicodeDecodeError):
                        pass
                    parts.append(t)
                    if sum(len(p) for p in parts) >= max_chars * 2:
                        break
            return " ".join(parts)[:max_chars]
        except Exception as e:
            return f"[PDF okunamadı: {e}]"
    elif suffix == ".docx":
        import zipfile
        import xml.etree.ElementTree as ET
        NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
        try:
            with zipfile.ZipFile(path) as z:
                xml_bytes = z.read("word/document.xml")
            root = ET.fromstring(xml_bytes)
            parts = [el.text for el in root.iter(f"{{{NS}}}t") if el.text]
            return " ".join(parts)[:max_chars]
        except Exception as e:
            return f"[DOCX okunamadı: {e}]"
    return ""


# Belgeleri bir kez yükle (tekrar yüklememek için)
_DOC_CACHE: dict[str, str] = {}

def _get_doc(name: str) -> str:
    if name not in _DOC_CACHE:
        paths = {
            "sea_ek6_docx": ROOT / "sds-knowledge" / "tr" / "sea_ek6_l-ste_15062020-20200618142549.docx",
            "clp_part2":    ROOT / "sds-knowledge" / "en" / "clp_part2_v5.pdf",
            "echa_sds":     ROOT / "sds-knowledge" / "en" / "echa_sds_guidance_v4.pdf",
            "tr_zarar":     ROOT / "sds-knowledge" / "tr" / "zararlı mad ve kar sınıflandırılması ve etiketlenmesi.pdf",
        }
        p = paths.get(name)
        _DOC_CACHE[name] = _load_doc_text(p) if (p and p.exists()) else ""
    return _DOC_CACHE[name]


# ── Toplu kontrol ─────────────────────────────────────────────────────────────

SEA_SYSTEM = """Sen bir kimyasal sınıflandırma denetçisisin.
Sana SEA Ek-6 referans belgesi ve JSON kayıtları verilecek.

GÖREV: Her kayıt için H kodları, tehlike sınıfı ve notların referans belgeyle çakışıp çakışmadığını kontrol et.

KURALLAR:
- Sadece gerçek çelişkileri raporla
- Format farkları (boşluk, büyük/küçük harf) çelişki DEĞİL
- Referans belgede olmayan maddeler için yorum yapma

ÇIKIŞ FORMATI (kesinlikle bu şablonu kullan, başka hiçbir şey yazma):
Çelişki yoksa tek satır: CELISKI_YOK
Çelişki varsa her biri için tek satır, pipe ile ayrılmış 5 alan:
CAS_NO | alan_adı | json_degeri | belgedeki_deger | kisa_aciklama

Örnek:
7637-07-2 | h_codes | H314 | H330 | Boron trifluoride için yanlış H kodu"""

SUBSTANCE_SYSTEM = """Sen bir kimyasal sınıflandırma denetçisisin.
Sana CLP belgesi ve substance_db.json kayıtları verilecek.

GÖREV: classification, m_factors, notes alanlarında CLP kriterlerine aykırı mantıksal tutarsızlık var mı kontrol et.

KURALLAR:
- Sadece gerçek tutarsızlıkları raporla
- Yorum veya açıklama paragrafı yazma

ÇIKIŞ FORMATI (kesinlikle bu şablonu kullan, başka hiçbir şey yazma):
Çelişki yoksa tek satır: CELISKI_YOK
Çelişki varsa her biri için tek satır, pipe ile ayrılmış 5 alan:
CAS_NO | alan_adı | json_degeri | beklenen_deger | kisa_aciklama

Örnek:
1333-74-0 | classification | Press. Gas / boş | H280 gerekli | Basınç altı gaz H280 olmadan geçersiz"""


def _check_batch(entries: list[dict], source: str, doc_text: str) -> str:
    """10 kaydı tek API çağrısında kontrol et. Çelişki satırlarını döndür."""
    system = SEA_SYSTEM if source == "sea" else SUBSTANCE_SYSTEM

    doc_label = "SEA Ek-6 referans belgesi" if source == "sea" else "CLP Annex VI / ECHA ATP22 belgesi"

    content = [
        {
            "type": "text",
            "text": f"=== {doc_label} (ilk 15.000 karakter) ===\n{doc_text}\n=== BELGE SONU ===\n\n"
                    f"=== Kontrol edilecek JSON kayıtları ===\n"
                    + json.dumps(entries, ensure_ascii=False, indent=2),
        }
    ]

    resp = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=system,
        messages=[{"role": "user", "content": content}],
    )
    return resp.content[0].text.strip()


# ── Ana akış ──────────────────────────────────────────────────────────────────

def _load_progress() -> dict:
    """Daha önce taranan CAS'ları yükle."""
    if PROGRESS_PATH.exists():
        return json.loads(PROGRESS_PATH.read_text(encoding="utf-8"))
    return {"sea": [], "substance": []}


def _save_progress(progress: dict):
    PROGRESS_PATH.write_text(json.dumps(progress, ensure_ascii=False, indent=2), encoding="utf-8")


def load_sea_entries(n: int | None, done_cas: set) -> list[dict]:
    path = ROOT / "data" / "sea_ek6_tr.json"
    db: dict = json.loads(path.read_text(encoding="utf-8"))
    entries = []
    for cas, v in db.items():
        if isinstance(v, dict) and "_alias" not in v and cas not in done_cas:
            entries.append({"cas": cas, **{k: v[k] for k in
                ("name_tr", "name_en", "h_codes", "classification", "notes")
                if k in v}})
    if n:
        entries = entries[:n]
    return entries


def load_substance_entries(n: int | None, done_cas: set) -> list[dict]:
    path = ROOT / "data" / "substance_db.json"
    db: dict = json.loads(path.read_text(encoding="utf-8"))
    entries = []
    for cas, v in db.items():
        if isinstance(v, dict) and "_alias" not in v and cas not in done_cas:
            entries.append({"cas": cas, **{k: v[k] for k in
                ("index_no", "classification", "m_factors", "notes", "euh_codes")
                if k in v}})
    if n:
        entries = entries[:n]
    return entries


def run(source: str, entries: list[dict], doc_text: str, progress: dict) -> list[str]:
    """Tüm kayıtları batch'ler halinde kontrol et. Tamamlananları progress'e kaydet."""
    conflicts: list[str] = []
    batches = math.ceil(len(entries) / BATCH_SIZE)

    for i in range(batches):
        batch = entries[i * BATCH_SIZE : (i + 1) * BATCH_SIZE]
        print(f"  Batch {i+1}/{batches} ({len(batch)} kayıt)...", end=" ", flush=True)
        try:
            result = _check_batch(batch, source, doc_text)
            lines = [l.strip() for l in result.splitlines() if l.strip()
                     and "CELISKI_YOK" not in l and "|" in l]
            if lines:
                conflicts.extend(lines)
                print(f"⚠️  {len(lines)} çelişki")
            else:
                print("✓")
            # Başarıyla taranan CAS'ları kaydet
            progress[source].extend(e["cas"] for e in batch)
            _save_progress(progress)
        except Exception as e:
            print(f"HATA: {e}")
        time.sleep(0.5)

    return conflicts


def _load_existing_conflicts() -> tuple[list[str], list[str]]:
    """Önceki çalıştırmalardaki çelişkileri conflict_report.md'den oku."""
    sea, sub = [], []
    if not REPORT_PATH.exists():
        return sea, sub
    current = None
    for line in REPORT_PATH.read_text(encoding="utf-8").splitlines():
        if "sea_ek6_tr.json" in line:
            current = "sea"
        elif "substance_db.json" in line:
            current = "sub"
        elif line.startswith("| ") and "|--" not in line and "CAS |" not in line:
            row = line.strip("| ").strip()
            if current == "sea":
                sea.append(row)
            elif current == "sub":
                sub.append(row)
    return sea, sub


def write_report(sea_conflicts: list[str], sub_conflicts: list[str], args):
    lines = [
        f"# JSON Çelişki Raporu",
        f"Tarih: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"Model: {MODEL}",
        "",
    ]

    if sea_conflicts:
        lines += [
            f"## sea_ek6_tr.json — {len(sea_conflicts)} çelişki",
            "",
            "| CAS | Alan | JSON Değeri | Belgede Olan | Açıklama |",
            "|-----|------|-------------|--------------|----------|",
        ]
        for c in sea_conflicts:
            parts = [p.strip() for p in c.split("|")]
            if len(parts) >= 4:
                lines.append("| " + " | ".join(parts) + " |")
            else:
                lines.append(f"| — | — | {c} | — | — |")
    else:
        lines.append("## sea_ek6_tr.json — Çelişki bulunamadı ✓")

    lines.append("")

    if sub_conflicts:
        lines += [
            f"## substance_db.json — {len(sub_conflicts)} çelişki",
            "",
            "| CAS | Alan | JSON Değeri | Beklenen | Açıklama |",
            "|-----|------|-------------|----------|----------|",
        ]
        for c in sub_conflicts:
            parts = [p.strip() for p in c.split("|")]
            if len(parts) >= 4:
                lines.append("| " + " | ".join(parts) + " |")
            else:
                lines.append(f"| — | — | {c} | — | — |")
    else:
        lines.append("## substance_db.json — Çelişki bulunamadı ✓")

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nRapor kaydedildi: {REPORT_PATH}")


def estimate_cost(n_sea: int, n_sub: int) -> float:
    calls = math.ceil(n_sea / BATCH_SIZE) + math.ceil(n_sub / BATCH_SIZE)
    # ~18K token input (15K belge + 3K kayıtlar), ~500 output per call
    cost = calls * (18_000 * 0.80 + 500 * 4.0) / 1_000_000
    return cost


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="JSON — resmi belge çelişki tarayıcısı")
    parser.add_argument("--n",    type=int, default=50,
                        help="Her dosyadan kaç kayıt kontrol edilsin (varsayılan: 50)")
    parser.add_argument("--file", choices=["sea", "substance", "both"], default="both",
                        help="Hangi dosya kontrol edilsin")
    parser.add_argument("--all",     action="store_true",
                        help="Tüm kayıtları tara (pahalı olabilir!)")
    parser.add_argument("--reset",   action="store_true",
                        help="İlerlemeyi sıfırla, baştan başla")
    parser.add_argument("--recheck", nargs="+", metavar="CAS",
                        help="Belirtilen CAS numaralarını tekrar kontrol et "
                             "(örn: --recheck 7637-07-2 1333-74-0)")
    args = parser.parse_args()

    if args.reset:
        PROGRESS_PATH.unlink(missing_ok=True)
        REPORT_PATH.unlink(missing_ok=True)
        print("İlerleme sıfırlandı.\n")

    progress = _load_progress()

    # --recheck: belirtilen CAS'ları progress'ten çıkar → yeniden taranır
    if args.recheck:
        recheck_set = set(args.recheck)
        progress["sea"]      = [c for c in progress.get("sea", [])      if c not in recheck_set]
        progress["substance"] = [c for c in progress.get("substance", []) if c not in recheck_set]
        _save_progress(progress)
        # Rapordaki o CAS'ların eski satırlarını da temizle
        prev_sea, prev_sub = _load_existing_conflicts()
        prev_sea = [r for r in prev_sea if not any(c in r for c in recheck_set)]
        prev_sub = [r for r in prev_sub if not any(c in r for c in recheck_set)]
        write_report(prev_sea, prev_sub, args)
        print(f"Yeniden taranacak: {', '.join(recheck_set)}\n")

    done_sea = set(progress.get("sea", []))
    done_sub = set(progress.get("substance", []))

    n = None if args.all else (args.n if not args.recheck else None)

    do_sea       = args.file in ("sea", "both")
    do_substance = args.file in ("substance", "both")

    sea_entries = load_sea_entries(n, done_sea)       if do_sea      else []
    sub_entries = load_substance_entries(n, done_sub) if do_substance else []

    # recheck modunda sadece istenen CAS'ları tara
    if args.recheck:
        recheck_set = set(args.recheck)
        sea_entries = [e for e in sea_entries if e["cas"] in recheck_set]
        sub_entries = [e for e in sub_entries if e["cas"] in recheck_set]

    if done_sea or done_sub:
        print(f"Daha önce tarananlar atlanıyor: {len(done_sea)} SEA, {len(done_sub)} substance")
        print()

    cost_est = estimate_cost(len(sea_entries), len(sub_entries))
    print(f"Taranacak: {len(sea_entries)} SEA + {len(sub_entries)} substance kaydı")
    print(f"Tahmini maliyet: ~${cost_est:.3f}")
    print()

    # Önceki çalıştırmalardaki çelişkileri yükle
    prev_sea, prev_sub = _load_existing_conflicts()

    new_sea = []
    new_sub = []

    if do_sea and sea_entries:
        print(f"sea_ek6_tr.json kontrol ediliyor ({len(sea_entries)} yeni kayıt)...")
        doc = _get_doc("sea_ek6_docx")
        new_sea = run("sea", sea_entries, doc, progress)
        print(f"  → {len(new_sea)} yeni çelişki\n")
    elif do_sea:
        print("sea_ek6_tr.json: Taranacak yeni kayıt yok.\n")

    if do_substance and sub_entries:
        print(f"substance_db.json kontrol ediliyor ({len(sub_entries)} yeni kayıt)...")
        doc = _get_doc("clp_part2")
        new_sub = run("substance", sub_entries, doc, progress)
        print(f"  → {len(new_sub)} yeni çelişki\n")
    elif do_substance:
        print("substance_db.json: Taranacak yeni kayıt yok.\n")

    write_report(prev_sea + new_sea, prev_sub + new_sub, args)
