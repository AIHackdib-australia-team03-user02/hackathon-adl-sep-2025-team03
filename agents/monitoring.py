from autogen import AssistantAgent
from utils.kql import run_kql

MONITOR_SYSTEM = (
    "You are MonitoringAgent. Assess logging coverage, retention, alert rules, and include evidence snippets. "
    "Inputs: KQL queries, Defender signals. "
    'Output JSON: {"coverage": "...", "gaps": [...], "alerts": [...], "retention_days": 0, "evidence": [...]}'
)

def make_monitoring_agent(llm_cfg):
    agent = AssistantAgent(
        name="monitoring_agent",
        llm_config=llm_cfg,
        system_message=MONITOR_SYSTEM
    )

    @agent.register_for_execution()
    def kql(workspace_id: str, query: str):
        """Run a KQL query against a workspace and return the results."""
        return run_kql(workspace_id, query)

    return agent
