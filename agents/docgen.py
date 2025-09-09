from autogen import AssistantAgent
import os, json

DOCGEN_SYSTEM = (
    "You are DocGenAgent. Transform aggregated findings into three Markdown outputs: "
    "(a) IRAP Company Policy draft, (b) Compliance Report (control‑by‑control), (c) Remediation Plan (prioritised). "
    "Return JSON: {policy_md, compliance_md, remediation_md}. Keep it concise, with tables where helpful."
)

def make_docgen_agent(llm_cfg):
    return AssistantAgent("docgen_agent", llm_config=llm_cfg, system_message=DOCGEN_SYSTEM)

def write_reports(payload: dict, outdir: str = "reports"):
    os.makedirs(outdir, exist_ok=True)
    with open(os.path.join(outdir, "IRAP_Company_Policy.md"), "w", encoding="utf-8") as f:
        f.write(payload.get("policy_md", ""))
    with open(os.path.join(outdir, "Compliance_Report.md"), "w", encoding="utf-8") as f:
        f.write(payload.get("compliance_md", ""))
    with open(os.path.join(outdir, "Remediation_Plan.md"), "w", encoding="utf-8") as f:
        f.write(payload.get("remediation_md", ""))
