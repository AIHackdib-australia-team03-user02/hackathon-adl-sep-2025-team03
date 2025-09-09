# agents/supervisor.py
from __future__ import annotations
from autogen import AssistantAgent
from typing import Optional, List, Dict, Any
import json, textwrap

SUPERVISOR_SYSTEM = (
    "You are SupervisorAgent. Intake a user request, orchestrate sub-agents, "
    "and synthesize a final report with Comply/Partial/Gap + remediation and citations."
)

def make_supervisor(llm_cfg, ingestion, policy, hardening, monitoring, crypto, network, docgen):
    sup = AssistantAgent(name="supervisor", llm_config=llm_cfg, system_message=SUPERVISOR_SYSTEM)

    def _ask(agent: AssistantAgent, prompt: str) -> str:
        try:
            return agent.generate_reply(messages=[{"role":"user","content": prompt}]) or ""
        except Exception as e:
            return f"[ERROR from {agent.name}: {e}]"

    @sup.register_for_execution(name="run")
    def run(task: str, files: Optional[List[str]] = None, repo_url: Optional[str] = None, repo_branch: str = "main", repo_subdir: Optional[str] = None,policy_paths: Optional[List[str]] = None,app_paths: Optional[List[str]] = None,) -> Dict[str, Any]:
        files = files or []
        # 1) Ingestion: summarise what we have
        ing_prompt = textwrap.dedent(f"""
        Task: {task}
        Sources: {files}
        Please list documents found and a short summary per doc. Return concise markdown.
        """).strip()
        ing_summary = _ask(ingestion, ing_prompt)

        # 2) Policy check
        pol_prompt = textwrap.dedent(f"""
        Using the following context, assess policy coverage vs ISM/IRAP and note gaps.
        Context:
        {ing_summary}
        Output JSON with keys: coverage, gaps[], owners?, freshness_issues?.
        """).strip()
        pol_json = _ask(policy, pol_prompt)

        # 3) Hardening / Monitoring / Crypto quick passes
        hard_json = _ask(hardening, "Evaluate baseline configs vs ISM hardening. Output JSON: findings[].")
        mon_json  = _ask(monitoring, "Assess logging coverage, retention, alerts. Output JSON summary.")
        cry_json  = _ask(crypto, "Assess crypto (TLS/SSH/IPsec) vs ISM crypto controls. Output JSON findings[].")
        net_json  = _ask(network, "Assess network segmentation/NSG/Firewall posture vs ISM. Output JSON findings[].")

        # 4) Ask docgen to synthesize markdown sections
        doc_prompt = textwrap.dedent(f"""
        Build three markdown sections from the JSON and notes below:
        - Policy Assessment
        - Compliance Summary (Comply/Partial/Gap table)
        - Remediation Plan (prioritised)

        Inputs:
        Ingestion:
        {ing_summary}

        Policy:
        {pol_json}

        Hardening:
        {hard_json}

        Monitoring:
        {mon_json}

        Crypto:
        {cry_json}

        Network:
        {net_json}
        """).strip()
        docs_md = _ask(docgen, doc_prompt)

        # 5) Minimal splitter if docgen returned one big block
        policy_md = "## Policy Assessment\n\n" + docs_md
        compliance_md = "## Compliance Summary\n\n" + "(populate from docgen or post-process)"
        remediation_md = "## Remediation Plan\n\n" + "(populate from docgen or post-process)"

        intermediate = {
            "task": task,
            "files": files,
            "repo_url": repo_url,
            "notes": "Supervisor orchestration ran.",
            "summaries": {
                "ingestion": ing_summary,
                "policy": pol_json,
                "hardening": hard_json,
                "monitoring": mon_json,
                "crypto": cry_json,
                "network": net_json,
            },
        }
        return {"intermediate": intermediate, "reports": json.dumps({
            "policy_md": policy_md,
            "compliance_md": compliance_md,
            "remediation_md": remediation_md
        })}

    class _Facade:
        def __init__(self, agent: AssistantAgent): self._agent = agent
        def execute_tool(self, name: str, **kwargs):
            if name == "run": return run(**kwargs)
            raise ValueError(f"Unknown tool: {name}")

    return _Facade(sup)
