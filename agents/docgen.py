# agents/docgen.py
from __future__ import annotations

from autogen import AssistantAgent
from pathlib import Path
from datetime import datetime
import json
import shutil
import os, stat, time
from typing import Any, Dict, Optional


DOCGEN_SYSTEM = (
    "You are DocGenAgent. Given structured findings and evidence from other agents, "
    "produce clear, auditor-friendly Markdown for:\n"
    "1) Policy Assessment, 2) Compliance Summary (Comply/Partial/Gap), "
    "3) Remediation Plan (prioritised, with owners and timeframes). "
    "Use concise headings, tables where useful, and include short cited snippets if provided."
)


def make_docgen_agent(llm_cfg: Dict[str, Any]) -> AssistantAgent:
    """
    Factory for the document-generation agent.
    """
    return AssistantAgent(
        name="docgen_agent",
        llm_config=llm_cfg,
        system_message=DOCGEN_SYSTEM,
    )


def _ensure_text_blocks(payload: Any) -> Dict[str, str]:
    """
    Accepts a dict or JSON string and returns a dict with string values
    for 'policy_md', 'compliance_md', and 'remediation_md'.
    """
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except Exception:
            # Fallback: treat the whole string as policy_md
            return {
                "policy_md": str(payload),
                "compliance_md": "",
                "remediation_md": "",
            }

    payload = payload or {}
    return {
        "policy_md": (payload.get("policy_md") or "").strip(),
        "compliance_md": (payload.get("compliance_md") or "").strip(),
        "remediation_md": (payload.get("remediation_md") or "").strip(),
    }


def _write_html_index(index_md: str, title: str, out_dir: Path) -> None:
    """
    Optionally render index.html if the 'markdown' package is available.
    """
    try:
        import markdown  # type: ignore
    except Exception:
        return  # silently skip HTML generation if markdown isn't installed

    html_body = markdown.markdown(index_md, extensions=["toc", "tables"])  # basic extensions
    html_page = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>{title}</title>
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <style>
    body {{ font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; margin: 2rem; line-height: 1.55; }}
    pre, code {{ background: #f6f8fa; padding: .2rem .4rem; border-radius: 4px; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border: 1px solid #ddd; padding: .5rem; }}
    th {{ background: #fafafa; text-align: left; }}
    a {{ text-decoration: none; }}
    h1, h2, h3 {{ margin-top: 1.2em; }}
  </style>
</head>
<body>
{html_body}
</body>
</html>"""
    (out_dir / "index.html").write_text(html_page, encoding="utf-8")


def _wipe_dir_contents(dirpath: Path) -> None:
    """
    Best-effort: remove files & subdirs inside dirpath without removing dirpath itself.
    Safer on Windows where open handles can block rmdir.
    """
    dirpath.mkdir(parents=True, exist_ok=True)
    # try a few times in case of transient locks from previews
    for _ in range(3):
        ok = True
        for p in list(dirpath.iterdir()):
            try:
                if p.is_file() or p.is_symlink():
                    try:
                        os.chmod(p, stat.S_IWRITE)  # clear read-only if set
                    except Exception:
                        pass
                    p.unlink(missing_ok=True)
                else:
                    shutil.rmtree(p, ignore_errors=True)
            except Exception:
                ok = False
        if ok:
            break
        time.sleep(0.2)


def write_reports(
    payload: Any,
    out_dir: str = "reports",
    title: str = "IRAP Assessment",
    mirror_latest: bool = True,
) -> None:
    """
    Writes separate Markdown files for policy, compliance, and remediation,
    plus a simple index.md. If the 'markdown' package is available, also
    writes index.html. Mirrors the most recent run to reports/latest.

    Parameters
    ----------
    payload : dict | JSON str
        Either a dict with keys {'policy_md','compliance_md','remediation_md'}
        or a JSON string containing those keys. If missing, placeholders are used.
    out_dir : str
        Base output directory (default: 'reports').
    title : str
        Title used in index files.
    mirror_latest : bool
        If True, mirrors the generated files into '<out_dir>/latest'.
    """
    blocks = _ensure_text_blocks(payload)

    policy_md = blocks["policy_md"] or "## Policy Assessment\n\n(no content)"
    compliance_md = blocks["compliance_md"] or "## Compliance Summary\n\n(no content)"
    remediation_md = blocks["remediation_md"] or "## Remediation Plan\n\n(no content)"

    # Timestamped run directory
    ts = datetime.now().strftime("%Y-%m-%d_%H%M")
    run_dir = Path(out_dir) / ts
    run_dir.mkdir(parents=True, exist_ok=True)

    # Write individual reports (no JSON dumps into these files)
    (run_dir / "IRAP_Company_Policy.md").write_text(policy_md, encoding="utf-8")
    (run_dir / "Compliance_Report.md").write_text(compliance_md, encoding="utf-8")
    (run_dir / "Remediation_Plan.md").write_text(remediation_md, encoding="utf-8")

    # Index.md
    index_md = f"""# {title}
Generated: {ts}

- [IRAP Company Policy](IRAP_Company_Policy.md)
- [Compliance Report](Compliance_Report.md)
- [Remediation Plan](Remediation_Plan.md)

> Tip: In VS Code, open this folder and press **Ctrl+K, V** to preview Markdown.
"""
    (run_dir / "index.md").write_text(index_md, encoding="utf-8")

    # Optional HTML index if 'markdown' is installed
    _write_html_index(index_md, title=title, out_dir=run_dir)

    # Mirror to reports/latest for convenience (Windows-safe)
    if mirror_latest:
        latest = Path(out_dir) / "latest"
        _wipe_dir_contents(latest)
        # Copy current run outputs into latest (overwrite if present)
        for name in ["index.md", "IRAP_Company_Policy.md", "Compliance_Report.md", "Remediation_Plan.md", "index.html"]:
            src = run_dir / name
            if src.exists():
                shutil.copy2(src, latest / name)

    print(f"Reports saved to {run_dir}" + (f" (and mirrored to {Path(out_dir) / 'latest'})" if mirror_latest else ""))
