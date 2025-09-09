from autogen import AssistantAgent

HARDENING_SYSTEM = (
    "You are HardeningAgent. Evaluate OS/App/Auth/Virtualisation config vs ISM controls and ASD Hardening guidance. "
    "Inputs: Azure Policy states, Defender assessments, blueprint refs. "
    'Output JSON: {"findings":[{"control_id": "...", "pass": true, "rationale": "...", "evidence_path": "...", "remediation": "..."}]}'
)

def make_hardening_agent(llm_cfg):
    return AssistantAgent(
        name="hardening_agent",
        llm_config=llm_cfg,
        system_message=HARDENING_SYSTEM
    )
