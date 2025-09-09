# agents/policy.py
from autogen import AssistantAgent
from typing import Optional
# add: from utils.policy_kb import PolicyKB

POLICY_SYSTEM = (
    "You are PolicyAgent. Use the provided policy evidence to assess coverage vs ISM/IRAP and identify gaps. "
    "Always cite the specific excerpts you were given."
)

def make_policy_agent(llm_cfg, kb: Optional["PolicyKB"] = None):
    agent = AssistantAgent("policy_agent", llm_config=llm_cfg, system_message=POLICY_SYSTEM)

    if kb:
        @agent.register_for_execution(name="search_policy")
        def search_policy(query: str, k: int = 8):
            return kb.search(query, k)
    return agent
