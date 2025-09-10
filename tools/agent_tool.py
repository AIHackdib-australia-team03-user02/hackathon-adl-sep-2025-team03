# tools/agent_tool.py
class AgentTool:
    """Wrap a single AutoGen agent so it can be called like a function."""
    def __init__(self, agent):
        self.agent = agent

    def __call__(self, prompt: str, history: list[str] | None = None) -> str:
        msgs = [{"role":"user","content":f"[history] {h}"} for h in (history or [])[-5:]]
        msgs.append({"role":"user","content":prompt})
        reply = self.agent.generate_reply(messages=msgs)
        return (reply or "").strip()
