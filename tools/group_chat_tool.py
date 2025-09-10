# tools/group_chat_tool.py
from autogen import GroupChat, GroupChatManager

class GroupChatTool:
    """Turn a small team (hardening+monitoring+crypto+network) into one callable tool with bounded iterations."""
    def __init__(self, agents, llm_cfg):
        self.agents = agents
        self.llm_cfg = llm_cfg

    def run(self, task: str, history: list[str] | None = None, max_iterations: int = 3) -> str:
        chat = GroupChat(agents=self.agents, messages=[])
        mgr  = GroupChatManager(groupchat=chat, llm_config=self.llm_cfg)
        convo = [{"role":"user","content":f"[history] {h}"} for h in (history or [])[-5:]]
        convo.append({"role":"user","content":f"Task: {task}\nReturn ONE line: Comply|Partial|Gap + brief rationale."})

        final_line = ""
        for _ in range(max_iterations):
            out = mgr.generate_reply(messages=convo)  # manager will pick next speaker
            text = (out or "").strip()
            final_line = text
            if any(text.lower().startswith(k) for k in ("comply", "partial", "gap")):
                break
            convo.append({"role":"assistant","content":text})

        return final_line
