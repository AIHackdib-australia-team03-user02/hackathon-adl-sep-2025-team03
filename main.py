# main.py
import os

def llm_config_default():
    # Use your Azure/OpenAI config if available; otherwise None (offline)
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

from agents.policy import make_policy_agent
from agents.hardening import make_hardening_agent
from agents.monitoring import make_monitoring_agent
from agents.crypto import make_crypto_agent
from agents.network import make_network_agent
from agents.docgen import make_docgen_agent
from agents.supervisor import make_supervisor

def main():
    llm_cfg = llm_config_default()

    policy     = make_policy_agent(llm_cfg)
    hardening  = make_hardening_agent(llm_cfg)
    monitoring = make_monitoring_agent(llm_cfg)
    crypto     = make_crypto_agent(llm_cfg)
    network    = make_network_agent(llm_cfg)
    docgen     = make_docgen_agent(llm_cfg)

    supervisor = make_supervisor(llm_cfg, None, policy, hardening, monitoring, crypto, network, docgen)

    # Paths → use FOLDERS (not zips)
    ism_pdf          = r".\standards\Information security manual (March 2025).pdf"
    ssp_xlsx_in      = r".\standards\System security plan annex template (March 2025).xlsx"
    ssp_xlsx_out     = r".\systems\SSP_filled.xlsx"   # <— save into ./systems as requested
    gold_blueprint   = r".\standards"                 # folder with static/content/etc
    test_system_path = r".\systems\test-system"       # your test folder

    res = supervisor.execute_tool(
        "run_ssp",
        ism_pdf=ism_pdf,
        ssp_xlsx_in=ssp_xlsx_in,
        ssp_xlsx_out=ssp_xlsx_out,
        gold_blueprint=gold_blueprint,
        test_system_path=test_system_path,
        #max_rows=5 
    )
    print(res)

if __name__ == "__main__":
    main()
