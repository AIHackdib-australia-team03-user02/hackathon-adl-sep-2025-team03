# utils/ism_controls.py
import re
from typing import List, Dict
from pypdf import PdfReader  # pip install pypdf

CTRL_RE = re.compile(r"Control:\s*(ISM-\d+);.*?Applicability:\s*([^;]+);", re.I | re.S)

def parse_ism_controls(pdf_path: str) -> List[Dict]:
    """Parse ISM PDF → [{'id': 'ISM-0580', 'applicability': ['NC','OS','P','S','TS']}]."""
    pdf = PdfReader(pdf_path)
    full = "\n".join(page.extract_text() or "" for page in pdf.pages)
    out = []
    for m in CTRL_RE.finditer(full):
        cid = m.group(1).strip()
        appl = [a.strip() for a in m.group(2).split(",")]
        out.append({"id": cid, "applicability": appl})
    return out
