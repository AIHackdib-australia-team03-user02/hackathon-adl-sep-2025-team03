from autogen import AssistantAgent

NETWORK_SYSTEM = (
    "You are NetworkAgent. Review NSGs/firewall/gateway configs and network diagrams for segmentation, egress control, CDS/proxy rules, Wi‑Fi rules (if in scope). "
    "Output JSON: {segments:[...], risky_flows:[...], egress_controls:{...}, wifi:{...}, remediations:[...] }"
)

def make_network_agent(llm_cfg):
    return AssistantAgent("network_agent", llm_config=llm_cfg, system_message=NETWORK_SYSTEM)
