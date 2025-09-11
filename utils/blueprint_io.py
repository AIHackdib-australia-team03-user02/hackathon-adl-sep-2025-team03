# utils/blueprint_io.py
from __future__ import annotations
import os, zipfile, tempfile, re
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
        if os.path.getsize(path) > 512_000: return ""  # cap ~500 KB
        with open(path, "rb") as f:
            return f.read().decode("utf-8", errors="ignore")
    except Exception:
        return ""

# ---------- keywording ----------
_HINTS: Dict[str, List[str]] = {
    "ISM-1955": [
        "MaximumPasswordAge", "password age", "password expiry",
        "Netlogon\\Parameters", "Netlogon/Parameters"
    ],
}

def _keywords_from_description(desc: str) -> List[str]:
    d = (desc or "").lower()
    kws: List[str] = []
    if "password" in d:
        kws += ["password", "password age", "password expiry", "maximum password age", "MaximumPasswordAge"]
    if any(k in d for k in ["rotate", "rotation", "changed", "change"]):
        kws += ["rotate", "rotation", "changed", "change"]
    return list(dict.fromkeys(kws))

# ---------- discovery ----------
def _list_candidate_files(root: str) -> List[str]:
    files: List[str] = []
    for sub in _PREFERRED_SUBDIRS:
        sp = os.path.join(root, sub)
        if os.path.isdir(sp):
            for dp, _, fns in os.walk(sp):
                for fn in fns:
                    ext = os.path.splitext(fn)[1].lower()
                    if ext in _ALLOWED_EXTS:
                        files.append(os.path.join(dp, fn))
    for dp, _, fns in os.walk(root):
        for fn in fns:
            ext = os.path.splitext(fn)[1].lower()
            if ext in _ALLOWED_EXTS:
                files.append(os.path.join(dp, fn))
    seen, out = set(), []
    for p in files:
        ap = os.path.abspath(p)
        if ap not in seen:
            seen.add(ap); out.append(ap)
    return out

def _name_has_any(name: str, words: List[str]) -> bool:
    low = name.lower()
    return any(w and w.lower() in low for w in words)

def _score_file(path: str, control_id: str, words: List[str]) -> int:
    score = 0
    base = os.path.basename(path)
    name = base.lower()
    ext  = os.path.splitext(base)[1].lower()
    txt  = _read_small_text(path).lower()

    score += _EXT_PRIORITY.get(ext, 0)
    if control_id.lower() in name: score += 10
    if _name_has_any(name, words): score += 8

    hits = 0
    for w in words:
        wl = (w or "").lower()
        if wl and wl in txt:
            hits += 1
            if hits >= 6:
                break
    score += hits

    for sub in _PREFERRED_SUBDIRS:
        if sub.replace("/", os.sep) in path:
            score += 5
            break

    score += max(0, 40 - len(base)) // 10
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
    scored = sorted(cands, key=lambda p: _score_file(p, ctrl, words), reverse=True)
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

# ---------- parse threshold from description ----------
def _parse_days_from_description(desc: str, default: int = 30) -> int:
    if not desc:
        return default
    matches = re.findall(r'(\d{1,3})\s*-\s*day|\b(\d{1,3})\s*day(?:s)?', desc, flags=re.IGNORECASE)
    nums: List[int] = []
    for a, b in matches:
        if a and a.isdigit(): nums.append(int(a))
        if b and b.isdigit(): nums.append(int(b))
    return min(nums) if nums else default

# ---------- control-specific validators ----------
def _extract_max_password_age(text: str) -> Optional[int]:
    """
    Extract MaximumPasswordAge value from typical config and PowerShell forms.
    """
    # Normalise once
    t = text

    patterns = [
        # PowerShell: -Name MaximumPasswordAge -Value 20
        re.compile(r"-Name\s+MaximumPasswordAge\b.*?-Value\s+(0x[0-9A-Fa-f]+|\d{1,3})", re.I | re.S),

        # Set-ItemProperty / New-ItemProperty ... MaximumPasswordAge ... -Value 20
        re.compile(r"(?:Set|New)-ItemProperty\b.*?MaximumPasswordAge\b.*?-Value\s+(0x[0-9A-Fa-f]+|\d{1,3})", re.I | re.S),

        # Registry-like lines e.g. MaximumPasswordAge=20 or : 20
        re.compile(r"\bMaximumPasswordAge\b[^0-9xa-f]{0,200}\b(0x[0-9A-Fa-f]+|\d{1,3})\b", re.I),

        # Generic "max password age ... 20"
        re.compile(r"\bmax(?:imum)?\s*password\s*age\b[^0-9xa-f]{0,200}\b(0x[0-9A-Fa-f]+|\d{1,3})\b", re.I),
    ]

    for rx in patterns:
        m = rx.search(t)
        if m:
            g = next((g for g in reversed(m.groups() or []) if g), None)
            if g:
                try:
                    return int(g, 16) if g.lower().startswith("0x") else int(g)
                except Exception:
                    continue
    return None

def _validator_ism_1955(file_paths: List[str], description: str) -> Tuple[Optional[str], Optional[str]]:
    """
    ISM-1955: credentials changed if not changed within N days (N read from description).
    Noncompliant (Gap) when MaximumPasswordAge > N.
    """
    required_days = _parse_days_from_description(description, default=30)

    # PRIORITISE files that actually mention 'MaximumPasswordAge'
    prioritized, others = [], []
    for p in file_paths:
        txt = _read_small_text(p)
        if "maximumpasswordage" in txt.lower():
            prioritized.append(p)
        else:
            others.append(p)
    search_order = prioritized + others

    for p in search_order:
        txt = _read_small_text(p)
        if not txt:
            continue
        val = _extract_max_password_age(txt)
        if val is not None:
            src = os.path.basename(p)
            if val > required_days:
                return ("Gap", f"Password age {val} days > {required_days} (file: {src})")
            else:
                return ("Comply", f"Password age {val} days ≤ {required_days} (file: {src})")

    # explicit value not found → undecided here; higher-level logic will mark Gap
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
    desc  = ev.get("desc") or ""

    validator = _CONTROL_VALIDATORS.get(control_id)
    if validator:
        status, comment = validator(files, desc)  # pass description
        if status:
            return (status, comment)
        return ("Gap", "")  # validator exists but couldn't find explicit value

    if files:
        return ("Comply", f"Evidence present in test: {os.path.basename(files[0])}")
    return ("Gap", "")
