# utils/blueprint_io.py
from __future__ import annotations
import os, zipfile, tempfile, glob, re
from typing import Optional, Tuple, List, Dict

# ---------------- generic fail cues (still supported, but optional) ----------------
_FAIL_NAME_RE    = re.compile(r"(fail|noncompliant|non-compliant|notcompliant)", re.I)
_FAIL_CONTENT_RE = re.compile(r"(?<![#/])\b(enabled\s*:\s*false|disabled\s*:\s*true|enforce\s*:\s*0)\b", re.I)

# ---------------- zip / dir roots ----------------
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

# ---------------- small text read ----------------
def _read_small_text(path: str) -> str:
    try:
        if not os.path.isfile(path): return ""
        if os.path.getsize(path) > 512_000: return ""  # 500KB cap
        with open(path, "rb") as f:
            return f.read().decode("utf-8", errors="ignore")
    except Exception:
        return ""

# ---------------- evidence collection ----------------
def _collect_files_by_id(root: str, control_id: str) -> List[str]:
    return glob.glob(os.path.join(root, "**", f"*{control_id}*"), recursive=True)

def _looks_failing_path(path: str) -> bool:
    return bool(_FAIL_NAME_RE.search(os.path.basename(path)))

def _looks_failing_content(path: str) -> bool:
    return bool(_FAIL_CONTENT_RE.search(_read_small_text(path)))

# ----- Hints to find files even when control ID is NOT in the filename -----
_HINTS: Dict[str, List[str]] = {
    # ISM-1955: “changed if compromised / suspected / not changed in past 30 days”
    # Many orgs keep password max-age in registry/policies/scripts; look for these keys/snippets.
    "ISM-1955": ["MaximumPasswordAge", "password age", "Netlogon\\Parameters", "Netlogon/Parameters"],
    # Add more per-control hints as you expand validators
}

def _collect_files_by_hints(root: str, control_id: str) -> List[str]:
    hints = _HINTS.get(control_id.upper(), [])
    files: List[str] = []
    for h in hints:
        # match filename or folder segments containing the hint
        files.extend(glob.glob(os.path.join(root, "**", f"*{h}*"), recursive=True))
    # de-dup + keep only files
    out = [os.path.abspath(p) for p in set(files) if os.path.isfile(p)]
    return sorted(out)

def _evidence_for_control(root: Optional[str], control_id: str) -> dict:
    """
    Return a rich evidence dict so validators can inspect actual files:
      {
        "has": bool,
        "snippet": "one-file-name",
        "fail": bool,                # generic fail cues (name/content)
        "files": [absolute_paths...]
      }
    """
    if not root:
        return {"has": False, "snippet": "", "fail": False, "files": []}
    files = _collect_files_by_id(root, control_id)
    if not files:
        files = _collect_files_by_hints(root, control_id)
    if not files:
        return {"has": False, "snippet": "", "fail": False, "files": []}
    fail = any(_looks_failing_path(f) or _looks_failing_content(f) for f in files)
    return {"has": True, "snippet": os.path.basename(files[0]), "fail": fail, "files": files}

def evidence_summary(control_id: str, gold_path: Optional[str], test_path: Optional[str]) -> dict:
    gold_root = _normalize_root(gold_path)
    test_root = _normalize_root(test_path)
    return {
        "test": _evidence_for_control(test_root, control_id),
        "gold": _evidence_for_control(gold_root, control_id),
        # carry control id for validators
        "id": control_id.upper(),
    }

# ---------------- control-specific validators ----------------
def _validator_ism_1955(file_paths: List[str]) -> Tuple[Optional[str], Optional[str]]:
    """
    ISM-1955: credentials changed if compromised / suspected / not changed in past 30 days.
    Treat MaximumPasswordAge > 30 as noncompliant (Gap). Accept common variants.
    """
    AGE_REs = [
        re.compile(r"\bMaximumPasswordAge\b[^0-9]{0,40}\b(\d{1,3})\b", re.I),
        re.compile(r"\bmax(password)?\s*age\b[^0-9]{0,40}\b(\d{1,3})\b", re.I),
        re.compile(r"\bpassword.*age\b[^0-9]{0,40}\b(\d{1,3})\b", re.I),
    ]
    best = None
    for p in file_paths:
        txt = _read_small_text(p)
        if not txt:
            continue
        for rx in AGE_REs:
            m = rx.search(txt)
            if m:
                # pick the last numeric group found (handles alternative regexes)
                groups = [g for g in m.groups() if g and g.isdigit()]
                if groups:
                    val = int(groups[-1])
                    best = (val, os.path.basename(p))
                    break
        if best:
            break
    if best:
        days, src = best
        if days > 30:
            return ("Gap", f"Password age {days} days > 30 (file: {src})")
        else:
            return ("Comply", f"Password age {days} days ≤ 30 (file: {src})")
    # No explicit age found → don’t decide here
    return (None, None)

_CONTROL_VALIDATORS = {
    "ISM-1955": _validator_ism_1955,
}

# ---------------- final decision ----------------
def decide_status_from_evidence(ev: dict) -> Tuple[str, str]:
    """
    Decision order:
      1) If a control-specific validator exists and decides → use it.
      2) Otherwise generic rules:
         - TEST fail cue -> Gap
         - TEST has evidence -> Comply
         - GOLD has evidence but TEST missing -> Partial
         - Else -> Partial (insufficient evidence)
    """
    control_id = (ev.get("id") or "").upper()
    validator = _CONTROL_VALIDATORS.get(control_id)

    if validator:
        test_files = ev.get("test", {}).get("files", [])
        status, comment = validator(test_files)
        if status:
            return (status, comment)

    # Fallback generic
    t = ev.get("test", {})
    g = ev.get("gold", {})
    if t.get("fail"):
        return ("Gap", f"Fail signal in test: {t.get('snippet') or 'config'}")
    if t.get("has"):
        return ("Comply", f"Evidence present in test: {t.get('snippet') or 'config'}")
    if g.get("has") and not t.get("has"):
        return ("Partial", f"Present in gold but missing in test: {g.get('snippet') or 'config'}")
    return ("Partial", "Insufficient evidence in test/gold")
