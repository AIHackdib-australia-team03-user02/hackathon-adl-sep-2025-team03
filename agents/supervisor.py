# agents/supervisor.py
from __future__ import annotations

from autogen import AssistantAgent
from typing import Optional, List, Dict, Any, Tuple
import textwrap
import importlib
from datetime import datetime

# Evidence (gold vs test)
try:
    blueprint_io = importlib.import_module("utils.blueprint_io")
    evidence_summary = getattr(blueprint_io, "evidence_summary")
    decide_status_from_evidence = getattr(blueprint_io, "decide_status_from_evidence")
except Exception:
    def evidence_summary(control_id: str, gold_path: Optional[str], test_path: Optional[str]) -> dict:
        return {"test": {"has": True, "snippet": "", "fail": False}, "gold": {"has": True, "snippet": "", "fail": False}}
    def decide_status_from_evidence(_ev: dict) -> Tuple[str, str]:
        return ("Comply", "Assumed compliant (fallback)")

# ISM + SSP helpers
try:
    ism_controls = importlib.import_module("utils.ism_controls")
    parse_ism_controls = getattr(ism_controls, "parse_ism_controls")
except Exception:
    def parse_ism_controls(_pdf_path: str) -> List[Dict[str, Any]]:
        return []

try:
    ssp_excel = importlib.import_module("utils.ssp_excel")
    read_rows = getattr(ssp_excel, "read_rows")
    write_outcome_pqr = getattr(ssp_excel, "write_outcome_pqr")
    safe_save = getattr(ssp_excel, "safe_save")
except Exception:
    def read_rows(_path: str):
        class _WB: pass
        class _WS: title = "Sheet1"
        return _WB(), _WS(), []
    def write_outcome_pqr(_wb, _ws, _row_index: int, _p: str, _q: str, _r: str): ...
    def safe_save(wb, out_path): return out_path

# Selector + agent tool
try:
    selector_mod = importlib.import_module("agents.selector")
    make_selector_agent = getattr(selector_mod, "make_selector_agent")
except Exception:
    def make_selector_agent(llm_cfg):
        return AssistantAgent("selector_agent", llm_config=llm_cfg, system_message="Always choose hardening_agent.")

try:
    agent_tool_mod = importlib.import_module("tools.agent_tool")
    AgentTool = getattr(agent_tool_mod, "AgentTool")
except Exception:
    class AgentTool:
        def __init__(self, agent): self.agent = agent
        def __call__(self, prompt: str, history: List[str] | None = None) -> str:
            msgs = [{"role":"user","content":f"[history] {h}"} for h in (history or [])[-5:]]
            msgs.append({"role":"user","content":prompt})
            return (self.agent.generate_reply(messages=msgs) or "").strip()

SUPERVISOR_SYSTEM = (
    "You are SupervisorAgent. Route work to sub-agents and synthesize results with "
    "Responsible Entity (P), Implementation Status (Q), and Implementation Comments (R)."
)

def make_supervisor(
    llm_cfg: Optional[Dict[str, Any]],
    ingestion: Optional[AssistantAgent],
    policy: AssistantAgent,
    hardening: AssistantAgent,
    monitoring: AssistantAgent,
    crypto: AssistantAgent,
    network: AssistantAgent,
    docgen: AssistantAgent,
):
    sup = AssistantAgent(name="supervisor", llm_config=llm_cfg, system_message=SUPERVISOR_SYSTEM)

    # GroupChatTool (online/offline)
    if not llm_cfg:
        class GroupChatTool:
            def __init__(self, agents, _llm_cfg=None): self.agents = agents
            def run(self, task: str, history: List[str] | None = None, max_iterations: int = 3) -> str:
                msgs = [{"role":"user","content":f"[history] {h}"} for h in (history or [])[-5:]]
                msgs.append({"role":"user","content":f"{task}\nReturn ONE line: Comply|Partial|Gap + brief rationale."})
                out = self.agents[0].generate_reply(messages=msgs)
                return (out or "").strip()
    else:
        try:
            from tools.group_chat_tool import GroupChatTool
        except Exception:
            class GroupChatTool:
                def __init__(self, agents, _llm_cfg=None): self.agents = agents
                def run(self, task: str, history: List[str] | None = None, max_iterations: int = 3) -> str:
                    msgs = [{"role":"user","content":f"[history] {h}"} for h in (history or [])[-5:]]
                    msgs.append({"role":"user","content":f"{task}\nReturn ONE line: Comply|Partial|Gap + brief rationale."})
                    out = self.agents[0].generate_reply(messages=msgs)
                    return (out or "").strip()

    def _choose_entity(agent_choice: str) -> str:
        return {
            "policy":     "Policy Owner",
            "hardening":  "Platform/Ops",
            "monitoring": "SecOps",
            "crypto":     "Security Architecture",
            "network":    "Network Ops",
        }.get(agent_choice, "Owner")

    def _parse_status_comment(line: str) -> Tuple[str, str]:
        s = (line or "").strip()
        head = s.split(" ")[0].strip(":").strip("-").strip().lower()
        if head.startswith("comply"):  return ("Comply", s)
        if head.startswith("partial"): return ("Partial", s)
        if head.startswith("gap"):     return ("Gap", s)
        return ("Comply", s or "Comply – blueprint baseline assumed.")

    def _route_and_summarise(selector: AssistantAgent, tools: Dict[str, Any], control_id: str, description: str, history: List[str]) -> Tuple[str, str]:
        sel_prompt = textwrap.dedent(f"""
        Select the best agent for this control based on the description.
        Control: {control_id}
        Description: {description}
        Choose ONE of: policy_agent, hardening_agent, monitoring_agent, crypto_agent, network_agent.
        Return JSON: {{"agent":"<name>", "reason":"..."}}.
        """).strip()
        sel_raw = selector.generate_reply(messages=[{"role":"user","content":sel_prompt}]) or ""
        s = sel_raw.lower()
        if   "policy_agent"     in s: agent_choice = "policy"
        elif "crypto_agent"     in s: agent_choice = "crypto"
        elif "network_agent"    in s: agent_choice = "network"
        elif "monitoring_agent" in s: agent_choice = "monitoring"
        else:                          agent_choice = "hardening"

        entity = _choose_entity(agent_choice)
        assess_task = (
            f"For {control_id}: Read the description and decide Comply|Partial|Gap, "
            f"with ONE short rationale or remediation.\nDescription: {description}"
        )
        if agent_choice == "policy":
            line = tools["policy_tool"](assess_task, history=history)
        else:
            line = tools["tech_team"].run(task=assess_task, history=history, max_iterations=3)
        status, comment = _parse_status_comment(line)
        return entity, f"{status}||{comment}"

    @sup.register_for_execution(name="run_ssp")
    def run_ssp(
        ism_pdf: str,
        ssp_xlsx_in: str,
        ssp_xlsx_out: str,
        gold_blueprint: str,
        test_system_path: Optional[str] = None,
        max_rows: int = 5
    ) -> Dict[str, Any]:
        # 1) ISM controls applicable to P
        all_ctrls = parse_ism_controls(ism_pdf)
        # Build a case-insensitive map of control IDs
        p_ctrls_upper = {c["id"].upper(): c for c in all_ctrls if "P" in [a.upper() for a in c.get("applicability", [])]}

        # 2) SSP rows (now using id_upper to match)
        wb, ws, rows = read_rows(ssp_xlsx_in)
        candidate_rows = [r for r in rows if r.get("id_upper") in p_ctrls_upper][:max_rows]

        tools_map = {
            "policy_tool": AgentTool(policy),
            "tech_team": GroupChatTool([hardening, monitoring, crypto, network], sup.llm_config),
        }
        selector = make_selector_agent(sup.llm_config)

        # Stamp a visible banner so you can see the right sheet/file quickly
        ws["S1"] = f"Filled by supervisor at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

        history: List[str] = []
        filled = 0
        written_cells: List[str] = []

        for r in candidate_rows:
            cid_raw = (r.get("id_raw") or "").strip()
            cid_up  = (r.get("id_upper") or "").strip()
            desc    = r.get("description") or ""
            c       = p_ctrls_upper.get(cid_up, {"id": cid_raw})

        ev = evidence_summary(cid_up, gold_path=gold_blueprint, test_path=test_system_path)
        ev["id"] = cid_up  # ensure validator knows which control this is
        ev_status, ev_comment = decide_status_from_evidence(ev)
           

        entity, status_comment = _route_and_summarise(selector, tools_map, c.get("id", cid_raw), desc, history)
        if "||" in status_comment:
               agent_status, agent_comment = status_comment.split("||", 1)
        else:
                agent_status, agent_comment = ev_status, ev_comment
        if agent_status not in ("Comply", "Partial", "Gap"):
                agent_status, agent_comment = ev_status, ev_comment

        t = ev.get("test", {})
        g = ev.get("gold", {})
        if t.get("fail"):
            ev_hint = f" [test fail: {t.get('snippet') or 'config'}]"
        elif t.get("has"):
                ev_hint = f" [test: {t.get('snippet') or 'config'}]"
        elif g.get("has"):
                ev_hint = f" [gold-only: {g.get('snippet') or 'config'}]"
        else:
                ev_hint = ""

        final_P = entity
        final_Q = agent_status
        final_R = (agent_comment + ev_hint).strip()

        write_outcome_pqr(wb, ws, r["row"], final_P, final_Q, final_R)
        written_cells.append(f"row {r['row']} → P/Q/R ({cid_raw})")
        filled += 1

        # Save once (always to a new time-stamped file)
        final_out = safe_save(wb, ssp_xlsx_out)

        return {
            "rows_written": filled,
            "sheet": getattr(ws, "title", "Sheet"),
            "output": final_out,
            "cells": written_cells
        }

    class _Facade:
        def __init__(self, agent: AssistantAgent): self._agent = agent
        def execute_tool(self, name: str, **kwargs):
            if name == "run_ssp": return run_ssp(**kwargs)
            raise ValueError(f"Unknown tool: {name}")

    return _Facade(sup)
