# utils/blueprint_io.py
from __future__ import annotations
import os, zipfile, tempfile, glob, re
from typing import Optional, Tuple, List, Dict

# ---------- preferred locations ----------
_PREFERRED_SUBDIRS = [
    "static/content/files/configscripts",
    "static/content/files/text",
    "config", "configs", "policies",
]

# ---------- extension priorities (higher = more preferred) ----------
_EXT_PRIORITY: Dict[str, int] = {
    # scripts / configs
    ".ps1": 100, ".psm1": 100, ".bat": 95, ".cmd": 95, ".sh": 95,
    ".reg": 95, ".json": 90, ".yaml": 90, ".yml": 90, ".ini": 90,
    ".cfg": 90, ".conf": 90, ".xml": 85, ".toml": 85,
    # text
    ".txt": 70,
    # docs (fallback only)
    ".md": 20, ".rst": 15, ".adoc": 15,
}
_ALLOWED_EXTS = set(_EXT_PRIORITY.keys())

# ---------- zip / dir handling ----------
def _ensure_root_from_zip(zip_path: str) -> str:
    root = tempfile.mkdtemp(prefix="sysroot_")
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(root)
    return root

def _normalize_root(path_or_zip: Optional[str]) -> Optional[str]:
    if not path_or_zip:
        return None
    p = os.path.abspath(path_or_zip)
    if os.path.isdir(p): return p
    if os.path.isfile(p) and p.lower().endswith(".zip"): return _ensure_root_from_zip(p)
    return None

# ---------- i/o helpers ----------
def _read_small_text(path: str) -> str:
    try:
        if not os.path.isfile(path): return ""
        if os.path.getsize(path) > 512_000: return ""  # cap at 500 KB
        with open(path, "rb") as f:
            return f.read().decode("utf-8", errors="ignore")
    except Exception:
        return ""

# ---------- keywording ----------
_HINTS: Dict[str, List[str]] = {
    # ISM-1955: 30-day password age
    "ISM-1955": ["MaximumPasswordAge", "password age", "password expiry",
                 "Netlogon\\Parameters", "Netlogon/Parameters"],
}

def _keywords_from_description(desc: str) -> List[str]:
    d = (desc or "").lower()
    kws: List[str] = []
    if "password" in d:
        kws += ["password", "password age", "password expiry", "maximum password age", "MaximumPasswordAge"]
    if any(k in d for k in ["rotate", "rotation", "changed", "change"]):
        kws += ["rotate", "rotation", "changed", "change"]
    if "30" in d or "thirty" in d:
        kws += ["30", "thirty"]
    # unique, preserve order
    return list(dict.fromkeys(kws))

# ---------- discovery ----------
def _list_candidate_files(root: str) -> List[str]:
    """List files under preferred subdirs first, then the whole tree; filter by allowed extensions."""
    files: List[str] = []
    # 1) preferred subdirs (if present)
    for sub in _PREFERRED_SUBDIRS:
        sp = os.path.join(root, sub)
        if os.path.isdir(sp):
            for dp, _, fns in os.walk(sp):
                for fn in fns:
                    ext = os.path.splitext(fn)[1].lower()
                    if ext in _ALLOWED_EXTS:
                        files.append(os.path.join(dp, fn))
    # 2) fallback: entire tree
    for dp, _, fns in os.walk(root):
        for fn in fns:
            ext = os.path.splitext(fn)[1].lower()
            if ext in _ALLOWED_EXTS:
                files.append(os.path.join(dp, fn))

    # de-dup preserving order
    seen, out = set(), []
    for p in files:
        ap = os.path.abspath(p)
        if ap not in seen:
            seen.add(ap); out.append(ap)
    return out

def _name_has_any(name: str, words: List[str]) -> bool:
    low = name.lower()
    return any(w.lower() in low for w in words if w)

def _score_file(path: str, control_id: str, words: List[str]) -> int:
    """
    Relevance score to prioritise *real config* over docs:
      + ext priority (config >> txt >> md)
      + 10 if filename contains control_id (rare but strong)
      + 8  if filename contains any keyword
      + up to +6 for content hits (≤ 6 keywords * 1)
      + 5  if under a preferred subdir
      + tiny preference for shorter filenames (more specific)
    """
    score = 0
    base = os.path.basename(path)
    name = base.lower()
    ext  = os.path.splitext(base)[1].lower()
    txt  = _read_small_text(path).lower()

    # extension weight
    score += _EXT_PRIORITY.get(ext, 0)

    # control id in filename?
    if control_id.lower() in name:
        score += 10

    # keywords in name?
    if _name_has_any(name, words):
        score += 8

    # keywords in content (cap at 6 hits so huge files don't dominate)
    hits = 0
    for w in words:
        wl = w.lower()
        if wl and wl in txt:
            hits += 1
            if hits >= 6:
                break
    score += hits  # +1 per hit (≤ 6)

    # preferred subdir bonus
    for sub in _PREFERRED_SUBDIRS:
        if sub.replace("/", os.sep) in path:
            score += 5
            break

    # shorter names slightly preferred (more specific)
    score += max(0, 40 - len(base)) // 10  # +4..0

    return score

# ---------- evidence ----------
def _evidence_for_control(root: Optional[str], control_id: str, desc: Optional[str]) -> dict:
    if not root:
        return {"has": False, "snippet": "", "files": []}
    ctrl = control_id.upper()
    words = _HINTS.get(ctrl, []) + _keywords_from_description(desc or "")
    cands = _list_candidate_files(root)
    if not cands:
        return {"has": False, "snippet": "", "files": []}

    # Score candidates with our config-first strategy
    scored = sorted(
        cands,
        key=lambda p: _score_file(p, ctrl, words),
        reverse=True
    )
    # Keep the top set (already prioritised: config > txt > md)
    top = scored[:20]
    return {"has": bool(top), "snippet": os.path.basename(top[0]) if top else "", "files": top}

def evidence_summary(control_id: str, gold_path: Optional[str], test_path: Optional[str], description: Optional[str] = None) -> dict:
    gold_root = _normalize_root(gold_path)
    test_root = _normalize_root(test_path)
    return {
        "test": _evidence_for_control(test_root, control_id, description),
        "gold": _evidence_for_control(gold_root, control_id, description),
        "id": control_id.upper(),
        "desc": description or "",
    }

# ---------- control-specific validators ----------
def _validator_ism_1955(file_paths: List[str]) -> Tuple[Optional[str], Optional[str]]:
    """
    ISM-1955: credentials changed if not changed in past 30 days.
    Noncompliant (Gap) when MaximumPasswordAge > 30.
    """
    AGE_REs = [
        re.compile(r"\bMaximumPasswordAge\b[^0-9xa-f]{0,40}\b(0x[0-9A-Fa-f]+|\d{1,3})\b", re.I),
        re.compile(r"\bmax\s*(?:password)?\s*age\b[^0-9xa-f]{0,40}\b(0x[0-9A-Fa-f]+|\d{1,3})\b", re.I),
        re.compile(r"\bpassword[^0-9\n\r]{0,50}age[^0-9xa-f]{0,40}\b(0x[0-9A-Fa-f]+|\d{1,3})\b", re.I),
        re.compile(r"\bMaximumPasswordAge\b.*?\b(DWORD)\b[^0-9xa-f]{0,20}\b(0x[0-9A-Fa-f]+|\d{1,3})\b", re.I | re.S),
    ]

    def _to_int(s: str) -> int:
        s = s.strip()
        return int(s, 16) if s.lower().startsWith("0x") else int(s)

    # 0) PRIORITISE files that actually mention 'MaximumPasswordAge' in content
    prioritized = []
    others = []
    for p in file_paths:
        txt = _read_small_text(p)
        if "maximumpasswordage" in txt.lower():
            prioritized.append(p)
        else:
            others.append(p)
    search_order = prioritized + others

    best = None
    for p in search_order:
        txt = _read_small_text(p)
        if not txt:
            continue
        for rx in AGE_REs:
            m = rx.search(txt)
            if m:
                # prefer last group that looks like a number/hex (covers DWORD + value)
                groups = [g for g in (m.groups() or ()) if g]
                # try from right-most group
                for g in reversed(groups):
                    g2 = g.strip()
                    if re.match(r"^(0x[0-9A-Fa-f]+|\d{1,3})$", g2):
                        try:
                            val = int(g2, 16) if g2.lower().startswith("0x") else int(g2)
                            best = (val, os.path.basename(p))
                            break
                        except Exception:
                            pass
                if best:
                    break
        if best:
            break

    if best:
        days, src = best
        if days > 30:
            return ("Gap", f"Password age {days} days > 30 (file: {src})")
        else:
            return ("Comply", f"Password age {days} days ≤ 30 (file: {src})")
    return (None, None)

_CONTROL_VALIDATORS: Dict[str, callable] = {
    "ISM-1955": _validator_ism_1955,
}

# ---------- TEST-ONLY decision ----------
def decide_status_from_evidence(ev: dict) -> Tuple[str, str]:
    """
    Decide from TEST evidence only.
      1) If a control-specific validator exists:
         - If it returns a decision -> use it (Comply/Gap + concrete note)
         - If it returns None (no explicit value found) -> treat as Gap (needs explicit evidence)
      2) If no validator exists for this control:
         - If evidence files exist -> Comply with a brief note (best-effort)
         - Else -> Gap (no evidence) with empty comment (supervisor will keep R blank)
    """
    control_id = (ev.get("id") or "").upper()
    test = ev.get("test", {}) or {}
    files = test.get("files", []) or []

    # 1) control-specific path
    validator = _CONTROL_VALIDATORS.get(control_id)
    if validator:
        status, comment = validator(files)
        if status:   # decided
            return (status, comment)
        # validator exists but couldn't find an explicit value -> require explicit evidence
        return ("Gap", "")  # comment empty; supervisor will put remediation

    # 2) generic path (no validator for this control)
    if files:
        return ("Comply", f"Evidence present in test: {os.path.basename(files[0])}")
    return ("Gap", "")
