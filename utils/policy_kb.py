# utils/policy_kb.py
from __future__ import annotations
from pathlib import Path
from typing import List, Dict, Any
from pypdf import PdfReader
from rank_bm25 import BM25Okapi

ALLOWED = {".pdf", ".md", ".txt"}

def _read_text(path: Path) -> str:
    ext = path.suffix.lower()
    if ext == ".pdf":
        out = []
        try:
            r = PdfReader(str(path))
            for p in r.pages:
                out.append(p.extract_text() or "")
        except Exception:
            return ""
        return "\n".join(out)
    else:
        try:
            return path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return ""

def _chunk(text: str, max_chars: int = 1600, overlap: int = 200) -> List[str]:
    text = text.replace("\r", "")
    chunks, i, n = [], 0, len(text)
    while i < n:
        j = min(i + max_chars, n)
        chunk = text[i:j]
        chunks.append(chunk)
        i = j - overlap
        if i < 0: i = 0
        if i >= n: break
    return [c.strip() for c in chunks if c and c.strip()]

class PolicyKB:
    def __init__(self, paths: List[str]) -> None:
        self.docs: List[Dict[str, Any]] = []
        for p in paths:
            pth = Path(p)
            if pth.is_dir():
                files = [x for x in pth.rglob("*") if x.suffix.lower() in ALLOWED and x.is_file()]
            else:
                files = [pth] if pth.suffix.lower() in ALLOWED and pth.is_file() else []
            for f in files:
                text = _read_text(f)
                for idx, ch in enumerate(_chunk(text)):
                    self.docs.append({"path": str(f), "chunk_id": idx, "text": ch})
        # tokenise corpus
        tokenised = [d["text"].lower().split() for d in self.docs]
        self.bm25 = BM25Okapi(tokenised)

    def search(self, query: str, k: int = 8) -> List[Dict[str, Any]]:
        if not self.docs:
            return []
        q_tokens = query.lower().split()
        scores = self.bm25.get_scores(q_tokens)
        top = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]
        out = []
        for i in top:
            d = self.docs[i]
            out.append({
                "path": d["path"],
                "chunk_id": d["chunk_id"],
                "score": float(scores[i]),
                "snippet": d["text"][:1200]
            })
        return out
