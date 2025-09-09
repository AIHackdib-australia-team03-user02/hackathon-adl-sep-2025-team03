from dotenv import load_dotenv
import json
from utils.azure_cfg import llm_config_default
from agents.ingestion import make_ingestion_agent
from agents.policy import make_policy_agent
from agents.hardening import make_hardening_agent
from agents.monitoring import make_monitoring_agent
from agents.crypto import make_crypto_agent
from agents.network import make_network_agent
from agents.docgen import make_docgen_agent, write_reports
from agents.supervisor import make_supervisor

def run_local_demo():
    load_dotenv()
    llm_cfg = llm_config_default()

    # Build agents
    ingestion = make_ingestion_agent(llm_cfg)
    policy = make_policy_agent(llm_cfg)
    hardening = make_hardening_agent(llm_cfg)
    monitoring = make_monitoring_agent(llm_cfg)
    crypto = make_crypto_agent(llm_cfg)
    network = make_network_agent(llm_cfg)
    docgen = make_docgen_agent(llm_cfg)

    # Supervisor
    supervisor = make_supervisor(
        llm_cfg, ingestion, policy, hardening, monitoring, crypto, network, docgen
    )

    # Kick off the run
    res = supervisor.execute_tool(
        "run",
        task=(
            "Assess ISM/IRAP compliance for provided configs/policies. "
            "Output consolidated Comply/Partial/Gap with citations and a prioritised remediation plan."
        ),
        files=["./samples/configs", "./samples/docs"],
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

    return res

if __name__ == "__main__":
    run_local_demo()
