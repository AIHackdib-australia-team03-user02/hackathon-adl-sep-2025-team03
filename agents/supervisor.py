# agents/supervisor.py
from __future__ import annotations
from autogen import AssistantAgent
from typing import Optional, List, Dict, Any, Tuple
import textwrap, importlib
from datetime import datetime

# Evidence (gold vs test)
blueprint_io = importlib.import_module("utils.blueprint_io")
evidence_summary = getattr(blueprint_io, "evidence_summary")
decide_status_from_evidence = getattr(blueprint_io, "decide_status_from_evidence")

# SSP helpers
ssp_excel = importlib.import_module("utils.ssp_excel")
read_rows = getattr(ssp_excel, "read_rows")
write_outcome_pqr = getattr(ssp_excel, "write_outcome_pqr")
safe_save = getattr(ssp_excel, "safe_save")

# Selector + tool wrappers (kept minimal; owner selection only)
def make_selector_agent(llm_cfg):
    return AssistantAgent("selector_agent", llm_config=llm_cfg,
        system_message="Select the most appropriate owner for a control based on its description. "
                       "Return JSON: {\"agent\":\"policy|hardening|monitoring|crypto|network\",\"reason\":\"...\"}")

class AgentTool:
    def __init__(self, agent): self.agent = agent
    def __call__(self, prompt: str, history: List[str] | None = None) -> str:
        msgs = [{"role":"user","content":f"[history] {h}"} for h in (history or [])[-5:]]
        msgs.append({"role":"user","content":prompt})
        out = self.agent.generate_reply(messages=msgs)
        return (out or "").strip()

class GroupChatTool:
    def __init__(self, agents, _llm_cfg=None): self.agents = agents
    def run(self, task: str, history: List[str] | None = None, max_iterations: int = 3) -> str:
        # very light stub that just calls the first agent
        msgs = [{"role":"user","content":f"[history] {h}"} for h in (history or [])[-5:]]
        msgs.append({"role":"user","content":task})
        out = self.agents[0].generate_reply(messages=msgs)
        return (out or "").strip()

SUPERVISOR_SYSTEM = (
    "You are SupervisorAgent. For each SSP row, write P (owner), Q (Implementation Status), "
    "and R (Implementation Comments). Outcomes are decided from the TEST system only."
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

    def _choose_entity(agent_choice: str) -> str:
        return {
            "policy":     "Policy Owner",
            "hardening":  "Platform/Ops",
            "monitoring": "SecOps",
            "crypto":     "Security Architecture",
            "network":    "Network Ops",
        }.get(agent_choice, "Owner")

    def _route_and_choose_owner(selector: AssistantAgent, control_id: str, description: str, history: List[str]) -> str:
        sel_prompt = textwrap.dedent(f"""
        Select the best owner for this control.
        Control: {control_id}
        Description: {description}
        Choose ONE of: policy, hardening, monitoring, crypto, network.
        Return JSON: {{"agent":"<one of the five>","reason":"..."}}.
        """).strip()
        raw = selector.generate_reply(messages=[{"role":"user","content":sel_prompt}]) or ""
        s = raw.lower()
        if   "\"policy\""     in s or "policy"     in s: agent_choice = "policy"
        elif "\"crypto\""     in s or "crypto"     in s: agent_choice = "crypto"
        elif "\"network\""    in s or "network"    in s: agent_choice = "network"
        elif "\"monitoring\"" in s or "monitoring" in s: agent_choice = "monitoring"
        else:                                          agent_choice = "hardening"
        return _choose_entity(agent_choice)

    def _remediation_for(control_id: str) -> str:
        cid = control_id.upper()
        if cid == "ISM-1955":
            return "Set MaximumPasswordAge ≤ 30 days and rotate any compromised/suspected credentials."
        return "Provide configuration/evidence to meet the control and re-run validation."

    @sup.register_for_execution(name="run_ssp")
    def run_ssp(
        ism_pdf: str,
        ssp_xlsx_in: str,
        ssp_xlsx_out: str,
        gold_blueprint: str,
        test_system_path: Optional[str] = None,
        max_rows: Optional[int] = None,
    ) -> Dict[str, Any]:

        wb, ws, rows, colmap = read_rows(ssp_xlsx_in)
        ws.cell(row=1, column=max(colmap.values()) + 1,
                value=f"Filled by supervisor at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        work_rows = rows if not max_rows or max_rows <= 0 else rows[:max_rows]

        selector = make_selector_agent(sup.llm_config)
        tech_team = GroupChatTool([hardening, monitoring, crypto, network], sup.llm_config)
        policy_tool = AgentTool(policy)

        written_cells: List[str] = []
        filled = 0

        for r in work_rows:
            cid_raw = (r.get("id_raw") or "").strip()
            cid_up  = (r.get("id_upper") or "").strip()
            desc    = r.get("description") or ""
            is_p    = bool(r.get("is_p"))

            # Source of truth for applicability is Column I
            if not is_p:
                write_outcome_pqr(wb, ws, r["row"], "Owner", "N/A (not P)", "Not applicable to Protected per Column I.", colmap)
                written_cells.append(f"row {r['row']} → N/A not P ({cid_raw})")
                filled += 1
                continue

            # TEST-ONLY evidence (also uses Column O description keywords)
            ev = evidence_summary(cid_up, gold_path=gold_blueprint, test_path=test_system_path, description=desc)
            ev["id"] = cid_up
            ev_status, ev_comment = decide_status_from_evidence(ev)

            # Owner only (do not mix selector text into R)
            owner = _route_and_choose_owner(selector, cid_up, desc, history=[])

            # Column R rule you requested:
            # - Comply  -> put what we found (ev_comment). If evidence present but no value, we keep the brief note.
            # - Gap/Fail-> provide remediation.
            # - No evidence -> leave blank (R="")
            final_P = owner
            final_Q = ev_status
            final_R = ""

            if ev_status == "Comply":
                final_R = ev_comment or ""
            elif ev_status in ("Gap", "Fail"):
                rem = _remediation_for(cid_up)
                final_R = (ev_comment + " " + rem).strip() if ev_comment else rem
            else:
                # Partial or any other -> treat like "no evidence" for comment purposes
                final_R = ""

            write_outcome_pqr(wb, ws, r["row"], final_P, final_Q, final_R, colmap)
            written_cells.append(f"row {r['row']} → P/Q/R ({cid_raw})")
            filled += 1

        final_out = safe_save(wb, ssp_xlsx_out)
        return {
            "rows_written": filled,
            "sheet": getattr(ws, "title", "Sheet"),
            "columns": colmap,
            "output": final_out,
            "cells": written_cells
        }

    class _Facade:
        def __init__(self, agent: AssistantAgent): self._agent = agent
        def execute_tool(self, name: str, **kwargs):
            if name == "run_ssp": return run_ssp(**kwargs)
            raise ValueError(f"Unknown tool: {name}")

    return _Facade(sup)
