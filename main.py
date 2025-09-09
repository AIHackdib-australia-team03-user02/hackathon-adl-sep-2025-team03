from dotenv import load_dotenv
import json, os, pathlib

from utils.azure_cfg import llm_config_default
from agents.ingestion import make_ingestion_agent
from agents.policy import make_policy_agent
from agents.hardening import make_hardening_agent
from agents.monitoring import make_monitoring_agent
from agents.crypto import make_crypto_agent
from agents.network import make_network_agent
from agents.docgen import make_docgen_agent, write_reports
from agents.supervisor import make_supervisor

# ---------- helpers ----------

# File types we want to ingest (add more if needed)
ALLOWED_EXTS = {
    ".pdf", ".md", ".txt", ".json", ".yaml", ".yml", ".tf", ".bicep",
    ".ini", ".conf", ".ps1", ".sh", ".csv"
}

def expand_inputs(paths_or_dirs):
    """Expand files/dirs/globs into a deduped list of files we care about."""
    out = []
    for item in paths_or_dirs:
        p = pathlib.Path(item)
        # glob pattern?
        if any(c in str(item) for c in "*?[]"):
            out += [str(x) for x in pathlib.Path().glob(str(item)) if x.is_file()]
        elif p.is_dir():
            out += [str(x) for x in p.rglob("*") if x.is_file()]
        elif p.is_file():
            out.append(str(p))
    # filter by extension and normalize
    out = [f for f in out if pathlib.Path(f).suffix.lower() in ALLOWED_EXTS]
    return sorted(set(os.path.normpath(f) for f in out))

def latest_policy_version_dir(base="knowledge/policies"):
    """
    Return the path to the newest 'vYYYY-MM' subfolder under knowledge/policies.
    Falls back to base if none found.
    """
    root = pathlib.Path(base)
    if not root.exists():
        return None
    # pick directories that start with 'v' and sort descending
    cand = [d for d in root.iterdir() if d.is_dir() and d.name.lower().startswith("v")]
    if not cand:
        return None
    # lexical sort works for vYYYY-MM style
    return sorted(cand, key=lambda d: d.name, reverse=True)[0]

# ---------- main pipeline ----------

def run_local_demo():
    load_dotenv()
    llm_cfg = llm_config_default()

    # Build agents
    ingestion  = make_ingestion_agent(llm_cfg)
    policy     = make_policy_agent(llm_cfg)
    hardening  = make_hardening_agent(llm_cfg)
    monitoring = make_monitoring_agent(llm_cfg)
    crypto     = make_crypto_agent(llm_cfg)
    network    = make_network_agent(llm_cfg)
    docgen     = make_docgen_agent(llm_cfg)

    supervisor = make_supervisor(
        llm_cfg, ingestion, policy, hardening, monitoring, crypto, network, docgen
    )

    # ---- Default input locations (no CLI needed) ----
    latest = latest_policy_version_dir("knowledge/policies")
    standards_dir = (latest / "standards") if latest else pathlib.Path("knowledge/policies")
    mappings_dir  = (latest / "mappings") if latest else pathlib.Path("knowledge/policies")

    default_sources = [
        str(standards_dir),
        str(mappings_dir),
        "submissions/configs",
        "submissions/docs",
    ]

    files = expand_inputs(default_sources)

    # Kick off the supervisor (keeps your existing API shape)
    res = supervisor.execute_tool(
        "run",
        task=(
            "Assess ISM/IRAP compliance for provided configs/policies. "
            "Output consolidated Comply/Partial/Gap with citations and a prioritised remediation plan."
        ),
        files=files,
        repo_url=None,
    )

    print("\n== Intermediate findings (truncated) ==")
    merged = (res or {}).get("intermediate", {})
    print(str(merged)[:800], "...\n")

    print("== Writing reports ==")
    reports_json = (res or {}).get("reports") or "{}"
    try:
        payload = json.loads(reports_json)
    except Exception:
        payload = {"policy_md": str(reports_json), "compliance_md": "", "remediation_md": ""}
    write_reports(payload)
    print("Reports saved to ./reports")

if __name__ == "__main__":
    run_local_demo()
