# main.py

from __future__ import annotations  # must be first (after optional docstring/comments)

import os
import sys
import argparse
from pathlib import Path
from typing import Iterable, Optional

# Force UTF-8 on Windows consoles (prevents UnicodeEncodeError)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ---------- LLM config ----------
def llm_config_default():
    """
    Return an AutoGen llm_config dict if Azure/OpenAI env vars are available, else None.
    """
    az_ep  = os.getenv("AZURE_OPENAI_ENDPOINT")
    az_key = os.getenv("AZURE_OPENAI_API_KEY")
    az_dep = os.getenv("AZURE_OPENAI_DEPLOYMENT")
    az_ver = os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview")
    if az_ep and az_key and az_dep:
        return {
            "config_list": [{
                "model": az_dep,
                "base_url": az_ep.rstrip("/"),
                "api_key": az_key,
                "api_type": "azure",
                "api_version": az_ver,
                "temperature": 0.2,
                "timeout": 120,
                "max_tokens": 2000,
            }]
        }

    oai_key = os.getenv("OPENAI_API_KEY")
    if oai_key:
        return {
            "config_list": [{
                "model": "gpt-4o-mini",
                "base_url": "https://api.openai.com/v1",
                "api_key": oai_key,
                "temperature": 0.2,
                "timeout": 120,
                "max_tokens": 2000,
            }]
        }
    return None

# ---------- Imports for your agents ----------
from agents.policy import make_policy_agent
from agents.hardening import make_hardening_agent
from agents.monitoring import make_monitoring_agent
from agents.crypto import make_crypto_agent
from agents.network import make_network_agent
from agents.docgen import make_docgen_agent
from agents.supervisor import make_supervisor

REPO_ROOT = Path(__file__).resolve().parent
STANDARDS_DIR = REPO_ROOT / "standards"


# ---------- Public entrypoint usable by Streamlit (direct import) ----------
def run_blueprint_assessment(
    workdir: str,
    outdir: Optional[str] = None,
    max_rows: Optional[int] = None,
) -> Iterable[str]:
    """
    Execute the compliance/SSP pipeline using your multi-agent supervisor.

    - workdir: folder containing the uploaded/unzipped 'test system' (two blueprint subfolders)
    - outdir:  where to write outputs (defaults to workdir)
    - max_rows: optional row limit. If None, process the entire file.

    Yields log lines for streaming UIs.
    """
    workdir_path = Path(workdir).resolve()
    outdir_path = Path(outdir).resolve() if outdir else workdir_path

    yield f"[main] start | workdir={workdir_path} outdir={outdir_path}"
    if not workdir_path.exists() or not workdir_path.is_dir():
        raise FileNotFoundError(f"Input folder does not exist or is not a directory: {workdir_path}")

    # Standards/artifacts
    ism_pdf         = STANDARDS_DIR / "Information security manual (March 2025).pdf"
    ssp_xlsx_in     = STANDARDS_DIR / "System security plan annex template (March 2025).xlsx"
    ssp_xlsx_out    = outdir_path / "SSP_filled.xlsx"
    gold_blueprint  = STANDARDS_DIR
    test_system_dir = workdir_path

    # LLM config + agents
    llm_cfg = llm_config_default()
    yield f"[main] llm_config: {'set' if llm_cfg else 'None'}"

    policy     = make_policy_agent(llm_cfg)
    hardening  = make_hardening_agent(llm_cfg)
    monitoring = make_monitoring_agent(llm_cfg)
    crypto     = make_crypto_agent(llm_cfg)
    network    = make_network_agent(llm_cfg)
    docgen     = make_docgen_agent(llm_cfg)
    supervisor = make_supervisor(llm_cfg, None, policy, hardening, monitoring, crypto, network, docgen)

    # Build kwargs for the tool; only include max_rows when specified
    kwargs = dict(
        ism_pdf=str(ism_pdf),
        ssp_xlsx_in=str(ssp_xlsx_in),
        ssp_xlsx_out=str(ssp_xlsx_out),
        gold_blueprint=str(gold_blueprint),
        test_system_path=str(test_system_dir),
    )
    if max_rows is None:
        yield "[main] max_rows = ALL"
    else:
        kwargs["max_rows"] = int(max_rows)
        yield f"[main] max_rows = {max_rows}"

    yield "[main] running supervisor.execute_tool('run_ssp', ...)"
    res = supervisor.execute_tool("run_ssp", **kwargs)

    yield f"[supervisor] {res}"
    yield "[main] done"


# ---------- CLI (usable by: python -m main --input ... --out ...) ----------
def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run blueprint assessment pipeline.")
    p.add_argument("--input", dest="workdir", required=True, help="Folder with the test system (two blueprint subfolders).")
    p.add_argument("--out",   dest="outdir", default=None, help="Output folder (defaults to --input).")
    p.add_argument("--max-rows", type=int, default=None, help="Optional row limit. Omit to process all.")
    return p.parse_args(argv)

def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    for line in run_blueprint_assessment(workdir=args.workdir, outdir=args.outdir, max_rows=args.max_rows):
        print(str(line), flush=True)
    return 0

if __name__ == "__main__":
    sys.exit(main())
