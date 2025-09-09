# agents/supervisor.py
from __future__ import annotations
from autogen import AssistantAgent
from typing import Optional, List, Dict, Any
import json

SUPERVISOR_SYSTEM = (
    "You are SupervisorAgent. Intake a user request, orchestrate sub-agents, "
    "and synthesize a final report with Comply/Partial/Gap + remediation and citations."
)

def make_supervisor(
    llm_cfg: dict,
    ingestion: AssistantAgent,
    policy: AssistantAgent,
    hardening: AssistantAgent,
    monitoring: AssistantAgent,
    crypto: AssistantAgent,
    network: AssistantAgent,
    docgen: AssistantAgent,
):
    sup = AssistantAgent(name="supervisor", llm_config=llm_cfg, system_message=SUPERVISOR_SYSTEM)

    # Register a callable tool named "run". You can flesh this out later to actually
    # talk to sub-agents and merge their outputs.
    @sup.register_for_execution(name="run")
    def run(
        task: str,
        files: Optional[List[str]] = None,
        repo_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        # TODO: orchestrate: call sub-agents and merge real results
        intermediate = {
            "task": task,
            "files": files or [],
            "repo_url": repo_url,
            "notes": "Supervisor stub executed.",
        }
        reports_payload = {
            "policy_md": "# Policy Assessment\n\n_Coming soon — supervisor stub._",
            "compliance_md": "# Compliance Summary\n\n_Coming soon — supervisor stub._",
            "remediation_md": "# Remediation Plan\n\n_Coming soon — supervisor stub._",
        }
        return {"intermediate": intermediate, "reports": json.dumps(reports_payload)}

    # Facade so main.py can call supervisor.execute_tool("run", ...)
    class _Facade:
        def __init__(self, agent: AssistantAgent):
            self._agent = agent
        def execute_tool(self, name: str, **kwargs):
            if name == "run":
                return run(**kwargs)  # call the registered function above
            raise ValueError(f"Unknown tool: {name}")

    return _Facade(sup)
