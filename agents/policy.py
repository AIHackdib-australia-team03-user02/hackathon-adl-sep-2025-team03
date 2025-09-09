from autogen import AssistantAgent
from utils.search import policy_search

POLICY_SYSTEM = (
    "You are PolicyAgent. Map inputs to ISM/DISP/IRAP controls. "
    "Tasks: check doc existence/freshness/owner; draft missing SOP/SSP/IR sections. "
    "Output JSON: {controls:[{id, status, evidence, owner?, freshness?}], missing_docs:[{name, suggested_owner, outline}], citations:[...]}. "
    "Prefer terse, auditable statements."
)

def make_policy_agent(llm_cfg):
    agent = AssistantAgent("policy_agent", llm_config=llm_cfg, system_message=POLICY_SYSTEM)

    @agent.register_for_execution()
    def search_policies(query: str, top: int = 5):
        return policy_search(query, top)

    return agent
