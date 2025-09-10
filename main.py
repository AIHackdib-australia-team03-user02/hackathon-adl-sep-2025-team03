# main.py

import os

def llm_config_default():
    """
    Returns an AutoGen config_list. Tries Azure OpenAI, then OpenAI.
    If neither is configured, returns None to signal OFFLINE mode.
    """
    # Azure OpenAI
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

    # OpenAI
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

    # Nothing configured → OFFLINE
    return None


# Offline stub that mimics an agent when no LLM is configured
class OfflineAgent:
    def __init__(self, name): self.name = name
    def generate_reply(self, messages):
        # Return a minimal, deterministic line so the pipeline can write P/Q/R
        last = (messages[-1]["content"] if messages else "")
        if any(k in last for k in ["Decide Comply", "Comply|Partial|Gap"]):
            return "Comply – blueprint baseline assumed. (offline)"
        return f"[{self.name} offline stub]"


# --- Import your existing agents and supervisor factory ---
from agents.policy import make_policy_agent
from agents.hardening import make_hardening_agent
from agents.monitoring import make_monitoring_agent
from agents.crypto import make_crypto_agent
from agents.network import make_network_agent
from agents.docgen import make_docgen_agent
from agents.supervisor import make_supervisor   # expects run_ssp with gold_blueprint, test_system_path

def main():
    llm_cfg = llm_config_default()

    if llm_cfg is None:
        # OFFLINE mode for local I/O testing (no HTTP calls)
        policy     = OfflineAgent("policy_agent")
        hardening  = OfflineAgent("hardening_agent")
        monitoring = OfflineAgent("monitoring_agent")
        crypto     = OfflineAgent("crypto_agent")
        network    = OfflineAgent("network_agent")
        docgen     = OfflineAgent("docgen_agent")
        ingestion  = None
        sup_cfg    = None          # <-- important: pass None, not {}
    else:
        # Online mode
        policy     = make_policy_agent(llm_cfg)
        hardening  = make_hardening_agent(llm_cfg)
        monitoring = make_monitoring_agent(llm_cfg)
        crypto     = make_crypto_agent(llm_cfg)
        network    = make_network_agent(llm_cfg)
        docgen     = make_docgen_agent(llm_cfg)
        ingestion  = None
        sup_cfg    = llm_cfg

    supervisor = make_supervisor(
        sup_cfg, ingestion, policy, hardening, monitoring, crypto, network, docgen
    )

    ism_pdf          = r".\standards\Information security manual (March 2025).pdf"
    ssp_xlsx_in      = r".\standards\System security plan annex template (March 2025).xlsx"
    ssp_xlsx_out     = r".\standards\SSP_filled.xlsx"
    gold_blueprint   = r".\standards\asd-blueprint.zip"
    test_system_path = r".\systems\test-system"   # folder or .zip

    res = supervisor.execute_tool(
        "run_ssp",
        ism_pdf=ism_pdf,
        ssp_xlsx_in=ssp_xlsx_in,
        ssp_xlsx_out=ssp_xlsx_out,
        gold_blueprint=gold_blueprint,
        test_system_path=test_system_path,
        max_rows=5
    )
    print(res)



if __name__ == "__main__":
    # Close Excel before running so the file isn’t locked.
    main()
