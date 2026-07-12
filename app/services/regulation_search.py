"""
regulation_search.py — Mevzuat arama ve SDS metin doğrulama araçları.

İki public fonksiyon:
  verify_text_in_sds(phrase, sds_text) → {found, phrase, context}
  search_regulation(query, top_k)      → [{title, text, score, source}, ...]

İndeks kaynakları (öncelik sırasıyla):
  1. rule_blocks._H_RULES   — H koduna göre derlenmiş özlü kural metinleri
  2. sds-knowledge/**/*.md  — ek mevzuat notları ve OEL listeleri

Tasarım kısıtları:
  - Vektör DB yok; saf anahtar kelime + TF-IDF benzeri skor
  - Türkçe karakter normalizasyonu (ı/i, ş/s, ç/c, ğ/g, ü/u, ö/o)
  - Import sırasında indeks derlenir, sonra bellekte tutulur (thread-safe)
"""

from __future__ import annotations

import re
import math
import pathlib
import threading
import unicodedata
from typing import Optional

# ---------------------------------------------------------------------------
# Türkçe karakter normalizasyonu
# ---------------------------------------------------------------------------

_TR_LOWER_MAP = str.maketrans(
    "ABCDEFGHIİJKLMNOPQRSTUVWXYZÇĞÖŞÜ",
    "abcdefghıijklmnopqrstuvwxyzçğöşü",
)
_TR_ASCII_MAP = str.maketrans({
    'ç': 'c', 'Ç': 'C',
    'ğ': 'g', 'Ğ': 'G',
    'ı': 'i', 'I': 'I',
    'İ': 'I',
    'ş': 's', 'Ş': 'S',
    'ö': 'o', 'Ö': 'O',
    'ü': 'u', 'Ü': 'U',
})


def _normalize(text: str) -> str:
    """Türkçe karakterleri koruyarak küçük harfe çevirir."""
    return text.translate(_TR_LOWER_MAP)


def _ascii_fold(text: str) -> str:
    """Türkçe özel karakterleri ASCII karşılığına düşürür (arama için)."""
    return _normalize(text).translate(_TR_ASCII_MAP)


def _tokenize(text: str) -> list[str]:
    """Metni anlamlı kelimeler listesine ayırır; 2 karakterden kısa atlanır."""
    folded = _ascii_fold(text)
    return [w for w in re.split(r"[^\w]+", folded) if len(w) >= 2]


# ---------------------------------------------------------------------------
# SDS metin doğrulama
# ---------------------------------------------------------------------------

def verify_text_in_sds(phrase: str, sds_text: str) -> dict:
    """
    SDS metninde bir ifadenin birebir (veya normalize edilmiş) geçip geçmediğini
    kontrol eder. Halüsinasyon önleme için: 'bu cümle SDS'te yazıyor mu?' sorusunu
    yanıtlar.

    Dönüş:
      {
        "found":   bool,
        "phrase":  str,          # aranan ifade
        "context": str | None,   # eşleşme çevresindeki ~120 karakter
        "match":   str | None,   # SDS'teki gerçek eşleşen metin
      }
    """
    if not phrase or not sds_text:
        return {"found": False, "phrase": phrase, "context": None, "match": None}

    phrase_n = _normalize(phrase.strip())
    text_n   = _normalize(sds_text)

    idx = text_n.find(phrase_n)
    if idx == -1:
        # ASCII fold ile ikinci deneme (ş→s, ç→c vb. farkları tolere et)
        phrase_f = _ascii_fold(phrase.strip())
        text_f   = _ascii_fold(sds_text)
        idx_f    = text_f.find(phrase_f)
        if idx_f == -1:
            return {"found": False, "phrase": phrase, "context": None, "match": None}
        # Orijinal metinde konumu tahmin et (ascii fold 1:1 karakter eşlemeli)
        idx = idx_f

    # Bağlam: eşleşme etrafında 60'ar karakter
    start   = max(0, idx - 60)
    end     = min(len(sds_text), idx + len(phrase) + 60)
    context = ("…" if start > 0 else "") + sds_text[start:end].strip() + ("…" if end < len(sds_text) else "")
    match   = sds_text[idx: idx + len(phrase)]

    return {
        "found":   True,
        "phrase":  phrase,
        "context": context,
        "match":   match,
    }


# ---------------------------------------------------------------------------
# Mevzuat indeksi
# ---------------------------------------------------------------------------

_lock       = threading.Lock()
_INDEX: Optional[list[dict]] = None    # [{title, text, source, tokens}]
_IDF:   Optional[dict[str, float]] = None


def _build_index() -> tuple[list[dict], dict[str, float]]:
    """Tüm kaynaklardan belge listesi + IDF ağırlık tablosu üretir."""
    docs: list[dict] = []

    # ── 1. rule_blocks._H_RULES ──────────────────────────────────────────────
    try:
        from app.services.rule_blocks import _H_RULES  # type: ignore
        for h_prefix, (title, text) in _H_RULES.items():
            docs.append({
                "title":  f"{h_prefix} — {title}",
                "text":   text,
                "source": "rule_blocks",
                "tokens": _tokenize(title + " " + text),
            })
    except Exception:
        pass

    # ── 2. sds-knowledge/**/*.md ─────────────────────────────────────────────
    _KNOWLEDGE_DIR = pathlib.Path(__file__).parents[2] / "sds-knowledge"
    for md_file in sorted(_KNOWLEDGE_DIR.rglob("*.md")):
        try:
            text = md_file.read_text(encoding="utf-8")
            # Her ## başlık bloğunu ayrı belge yap
            sections = re.split(r"\n##\s+", text)
            for i, sec in enumerate(sections):
                lines    = sec.strip().splitlines()
                if not lines:
                    continue
                title    = lines[0].lstrip("#").strip()
                body     = "\n".join(lines[1:]).strip()
                if len(body) < 20:
                    continue
                docs.append({
                    "title":  f"{md_file.stem} — {title}" if i > 0 else title,
                    "text":   body[:1500],           # indeks hafıza koruması
                    "source": str(md_file.relative_to(_KNOWLEDGE_DIR)),
                    "tokens": _tokenize(title + " " + body),
                })
        except Exception:
            pass

    # ── IDF (belge frekansının tersi) ────────────────────────────────────────
    df: dict[str, int] = {}
    for doc in docs:
        for tok in set(doc["tokens"]):
            df[tok] = df.get(tok, 0) + 1

    N = max(len(docs), 1)
    idf = {tok: math.log(N / freq) for tok, freq in df.items()}

    return docs, idf


def _get_index() -> tuple[list[dict], dict[str, float]]:
    global _INDEX, _IDF
    if _INDEX is None:
        with _lock:
            if _INDEX is None:
                _INDEX, _IDF = _build_index()
    return _INDEX, _IDF


# ---------------------------------------------------------------------------
# Mevzuat arama
# ---------------------------------------------------------------------------

def search_regulation(query: str, top_k: int = 5) -> list[dict]:
    """
    Mevzuat kural bloklarında anahtar kelime araması yapar.

    Puanlama: TF-IDF benzeri — sorgu kelimelerinin belgede kaç kez geçtiği
    × log(N/df) ağırlığı. Başlıkta geçen kelimeler 2× ağırlık alır.

    Dönüş: [{title, text, score, source}, ...] — skora göre azalan sıra.
    score=0 sonuçlar dahil edilmez.

    Kullanım örneği:
      results = search_regulation("H318 dominance H314 etiket")
      for r in results:
          print(r["title"], "→", r["text"][:200])
    """
    if not query:
        return []

    docs, idf = _get_index()
    query_tokens = _tokenize(query)
    if not query_tokens:
        return []

    scored: list[dict] = []
    for doc in docs:
        doc_tok_set  = set(doc["tokens"])
        title_n      = _ascii_fold(doc["title"])

        score = 0.0
        for tok in query_tokens:
            if tok not in doc_tok_set:
                continue
            w = idf.get(tok, 0.0)
            # Başlıkta geçiyorsa 2× bonus
            if tok in title_n:
                w *= 2
            tf = doc["tokens"].count(tok) / max(len(doc["tokens"]), 1)
            score += tf * w

        if score > 0:
            scored.append({
                "title":  doc["title"],
                "text":   doc["text"],
                "score":  round(score, 4),
                "source": doc["source"],
            })

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]
