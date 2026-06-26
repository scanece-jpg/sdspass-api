"""
knowledge_service.py — sds-knowledge/ dosyalarını AI chat'e metin olarak sunar.

Dosyalar değiştirilmez. PDF: pdfplumber (okuma), DOCX: zipfile+xml (stdlib).
Sorguya göre en alakalı 1-3 belge seçilir; her belgeden max 5000 karakter alınır.
"""

import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

_ROOT = Path(__file__).parent.parent.parent
_KD   = _ROOT / "sds-knowledge"

# ── Dosya kataloğu ─────────────────────────────────────────────────────────────
# key: kısa isim  →  (path, açıklama, anahtar kelimeler)
_CATALOGUE: dict[str, tuple[Path, str, list[str]]] = {
    "tr_yonetmelik": (
        _KD / "tr" / "31330 tr yönetmelik.pdf",
        "SEA Yönetmeliği (CLP TR) — sınıflandırma, etiketleme, ambalajlama",
        ["sea", "yönetmelik", "clp tr", "31330", "madde", "tüzük"],
    ),
    "tr_kkdik_ek2": (
        _KD / "tr" / "KKDİK_EK-02.docx",
        "KKDİK Ek-2 — GBF/SDS bölüm gereklilikleri (TR)",
        ["kkdik ek", "ek-2", "ek 2", "gbf bölüm", "sds bölüm",
         "güvenlik bilgi formu bölüm", "gbf içerik", "sds içerik"],
    ),
    "tr_ek5_muaf": (
        _KD / "tr" / "ek-5-kayittan-muaf-rehber.docx",
        "KKDİK Ek-5 — Kayıttan muaf maddeler rehberi",
        ["muaf", "kayıt muaf", "ek-5", "ek 5", "polimer", "monomer"],
    ),
    "tr_kkdik_usul": (
        _KD / "tr" / "kkdik-usul-esas.pdf",
        "KKDİK Usul ve Esaslar — kayıt, bildirim, SVHC, yetkilendirme",
        ["kkdik", "kayıt", "bildirim", "svhc", "reach tr",
         "usul", "esas", "yetkilendirme", "kısıtlama", "tonaj"],
    ),
    "tr_sea_etiket": (
        _KD / "tr" / "sea-etiketleme-ambalajlama-rehberi.pdf",
        "SEA Etiketleme ve Ambalajlama Rehberi (TR)",
        ["etiket", "ambalaj", "piktogram", "uyarı kelimesi", "tehlike ifadesi",
         "önlem ifadesi", "sinyal kelime", "p kodu etiket", "h kodu etiket",
         "etiket element", "label"],
    ),
    "tr_zarar_sinif": (
        _KD / "tr" / "zararlı mad ve kar sınıflandırılması ve etiketlenmesi.pdf",
        "Zararlı Madde Sınıflandırma ve Etiketleme Rehberi (TR)",
        ["sınıflandırma kriteri", "kategori", "akut toks", "cilt", "göz",
         "kanserojen", "mutajen", "üreme", "nörotoks", "spesifik organ",
         "solunum", "patlayıcı", "alevlenir", "oksitleyici", "baskı altı",
         "çevre", "aquatik", "ozon", "karışım sınıflandırma"],
    ),
    "tr_sea_ek6": (
        _KD / "tr" / "sea_ek6_l-ste_15062020-20200618142549.docx",
        "SEA Ek-6 — Türkiye harmonize sınıflandırma listesi (Word kaynak)",
        ["sea ek-6", "sea ek 6", "harmonize liste", "ek-6 liste",
         "tr sınıflandırma listesi"],
    ),
    "en_reach_annex2": (
        _KD / "en" / "reach_annex2_2020_878.pdf",
        "REACH Annex II — SDS gereklilikleri 2020/878 (EN)",
        ["reach annex ii", "reach annex 2", "sds requirement",
         "sds section", "safety data sheet section", "annex ii", "2020/878"],
    ),
    "en_echa_sds": (
        _KD / "en" / "echa_sds_guidance_v4.pdf",
        "ECHA SDS Hazırlama Rehberi v4 (EN)",
        ["gbf", "sds", "güvenlik bilgi formu", "safety data sheet",
         "echa guidance", "sds hazırlama", "bölüm 1", "bölüm 2",
         "bölüm 3", "bölüm 8", "bölüm 9", "section"],
    ),
    "en_clp_part2": (
        _KD / "en" / "clp_part2_v5.pdf",
        "CLP Sınıflandırma Kriterleri Part 2 v5 (EN)",
        ["clp part", "classification criteria", "sınıflandırma kriter",
         "ghs", "physical hazard", "health hazard", "environmental hazard"],
    ),
    "en_clp_reg": (
        _KD / "en" / "CELEX_32008R1272_EN_TXT.pdf",
        "CLP Tüzüğü 1272/2008 tam metin (EN)",
        ["1272/2008", "clp regulation", "clp article", "clp annex",
         "regulation 1272"],
    ),
    "en_clp_guide1": (
        _KD / "en" / "echa-guidance" / "clp_part1_en.pdf",
        "ECHA CLP Rehberi Part 1 — genel bilgiler (EN)",
        ["clp guide part 1", "clp rehber genel"],
    ),
    "en_clp_guide2": (
        _KD / "en" / "echa-guidance" / "clp_part2_en.pdf",
        "ECHA CLP Rehberi Part 2 — fiziksel tehlikeler (EN)",
        ["explosive", "flammable", "oxidising", "fiziksel tehlike",
         "patlayıcı kriteri", "alevlenir kriteri"],
    ),
    "en_clp_guide3": (
        _KD / "en" / "echa-guidance" / "clp_part3_en.pdf",
        "ECHA CLP Rehberi Part 3 — sağlık tehlikeleri (EN)",
        ["acute toxicity", "skin corrosion", "eye damage", "respiratory",
         "carcinogen", "mutagenic", "reproductive", "specific organ",
         "aspiration", "sağlık tehlike kriter"],
    ),
    "en_clp_guide45": (
        _KD / "en" / "echa-guidance" / "clp_parts4-5_en.pdf",
        "ECHA CLP Rehberi Part 4-5 — çevresel tehlikeler ve karışımlar (EN)",
        ["aquatic", "ozone", "mixture", "karışım sınıflandırma",
         "environmental", "çevre tehlike", "m-factor", "m faktör"],
    ),
    "en_adr_vol1": (
        _KD / "en" / "2412006_E_ECE_TRANS_352_Vol.I_WEB_0.pdf",
        "ADR 2025 Cilt I — tehlikeli madde kara taşımacılığı (EN)",
        ["adr", "taşıma", "transport", "un no", "packing group",
         "ambalaj grubu", "tehlikeli madde taşı", "kara taşıma"],
    ),
    "en_adr_vol2": (
        _KD / "en" / "2412010_E_ECE_TRANS_352_Vol.II_WEB.pdf",
        "ADR 2025 Cilt II — tank, konteyner, IBC (EN)",
        ["adr cilt 2", "adr vol 2", "tank", "konteyner", "ibc"],
    ),
}

_MAX_CHARS = 12_000  # belge başına max karakter (~3K token)


# ── PDF metin çıkarıcı ────────────────────────────────────────────────────────

def _read_pdf(path: Path, max_chars: int = _MAX_CHARS) -> str:
    """pdfplumber ile PDF'ten düz metin çıkarır. Dosyaya dokunmaz."""
    try:
        import pdfplumber
        text_parts = []
        total = 0
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                t = page.extract_text() or ""
                text_parts.append(t)
                total += len(t)
                if total >= max_chars * 2:
                    break
        return " ".join(text_parts)[:max_chars]
    except Exception as e:
        return f"[PDF okunamadı: {e}]"


# ── DOCX metin çıkarıcı ───────────────────────────────────────────────────────

_DOCX_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

def _read_docx(path: Path, max_chars: int = _MAX_CHARS) -> str:
    """zipfile + xml.etree ile DOCX'ten metin çıkarır. Dosyaya dokunmaz."""
    try:
        with zipfile.ZipFile(path, "r") as z:
            xml_bytes = z.read("word/document.xml")
        root = ET.fromstring(xml_bytes)
        parts = []
        for el in root.iter(f"{{{_DOCX_NS}}}t"):
            if el.text:
                parts.append(el.text)
        return " ".join(parts)[:max_chars]
    except Exception as e:
        return f"[DOCX okunamadı: {e}]"


# ── Belge seçici ──────────────────────────────────────────────────────────────

def _score(query_lower: str, keywords: list[str]) -> int:
    return sum(1 for kw in keywords if kw in query_lower)


def select_docs(query: str, max_docs: int = 3) -> list[str]:
    """Sorguya göre en alakalı max_docs belge anahtarını döner."""
    q = query.lower()
    scored = []
    for key, (path, _, keywords) in _CATALOGUE.items():
        if not path.exists():
            continue
        s = _score(q, keywords)
        if s > 0:
            scored.append((s, key))
    scored.sort(reverse=True)
    return [k for _, k in scored[:max_docs]]


# ── Bağlam bloğu üretici ─────────────────────────────────────────────────────

def build_context_blocks(query: str) -> list[dict]:
    """
    Seçilen belgelerden metin çıkarır ve Anthropic Messages API
    text content bloklarını döner.
    """
    keys = select_docs(query)
    blocks: list[dict] = []

    for key in keys:
        path, desc, _ = _CATALOGUE[key]
        if not path.exists():
            continue

        suffix = path.suffix.lower()
        if suffix == ".pdf":
            text = _read_pdf(path)
        elif suffix == ".docx":
            text = _read_docx(path)
        else:
            continue

        if text:
            blocks.append({
                "type": "text",
                "text": f"=== KAYNAK: {desc} ===\n{text}\n=== KAYNAK SONU ===",
            })

    return blocks


def list_available() -> list[dict]:
    """Arayüz için katalog özeti döner."""
    return [
        {
            "key": k,
            "description": desc,
            "exists": path.exists(),
            "suffix": path.suffix,
        }
        for k, (path, desc, _) in _CATALOGUE.items()
    ]
