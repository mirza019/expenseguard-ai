"""Bounded LangGraph plan → execute → validate → inspect audit workflow."""

from collections.abc import Callable

from langgraph.graph import END, START, StateGraph

from app.agents.finance_agent import OllamaPlanner
from app.agents.state import ACTIONS, AuditState, Decision
from app.agents.tools import build_tools
from app.config import Settings
from app.services.analytics import TOOLS, validate_result
from app.services.policy_rag import PolicyDocument
from app.services.reporting import build_report
from app.services.validation import ToolResult, ValidatedData


def run_audit(
    data: ValidatedData,
    goal: str = "Audit all expenses",
    mode: str = "deterministic",
    planner: Callable[[dict], Decision] | None = None,
    config: Settings | None = None,
    generate_pdf: bool = False,
    policies: tuple[PolicyDocument, ...] = (),
) -> AuditState:
    """Run session-local state; failures fall back explicitly, never masquerading as AI."""
    if mode not in {"agent", "deterministic"}:
        raise ValueError("Unknown execution mode.")
    if not goal.strip() or len(goal) > 2000:
        raise ValueError("Provide a goal between 1 and 2,000 characters.")
    config = config or Settings()
    if mode == "agent" and planner is None:
        planner = OllamaPlanner(config)

    registered = build_tools(data)

    def plan(state: AuditState) -> dict:
        remaining = [name for name in TOOLS if name not in state["results"]]
        if state["mode"] == "deterministic":
            return {"pending": remaining[0] if remaining else "", "done": not remaining}
        if state["calls"] >= config.max_calls or not remaining:
            # Allow one final inspection/explanation turn, but no more tool execution.
            remaining = []
        evidence = [
            {
                "finding_id": f"{name}:{i}",
                "rule": finding.rule,
                "severity": finding.severity,
                "evidence": finding.evidence,
            }
            for name, result in state["results"].items()
            for i, finding in enumerate(result.findings)
        ][:40]
        context = {
            "goal": state["goal"],
            "remaining_tools": remaining,
            "completed_tools": list(state["results"]),
            "findings": evidence,
            "instructions": "Select finish if remaining_tools is empty.",
            "approved_actions": ACTIONS,
            "registered_tools": {name: registered[name].description for name in remaining},
        }
        if len(state["results"]) == len(TOOLS):
            context["registered_tools"]["generate_report"] = (
                "Generate a verified PDF after all checks."
            )
        try:
            decision = Decision.model_validate(planner(context).model_dump())
            if decision.tool == "generate_report" and len(state["results"]) != len(TOOLS):
                raise ValueError("Complete all checks before requesting a PDF.")
            if (
                decision.tool not in {"finish", "generate_report"}
                and decision.tool not in remaining
            ):
                raise ValueError("Model selected an unavailable or repeated tool.")
            available_ids = {item["finding_id"] for item in evidence}
            if any(r.finding_id not in available_ids for r in decision.recommendations):
                raise ValueError("Model referenced unavailable evidence.")
            recs = [
                {"finding_id": r.finding_id, "action": ACTIONS[r.action]}
                for r in decision.recommendations
            ]
            return {
                "pending": "" if decision.tool in {"finish", "generate_report"} else decision.tool,
                "done": decision.tool in {"finish", "generate_report"},
                "pdf_requested": state["pdf_requested"] or decision.tool == "generate_report",
                "recommendations": recs,
                "trace": [*state["trace"], f"Model selected {decision.tool}"],
            }
        except Exception:
            # Never expose response bodies, record text or endpoint exception details.
            retries = state["retries"] + 1
            fallback = retries > config.max_retries
            return {
                "retries": retries,
                "pending": "",
                "done": False,
                "pdf_requested": generate_pdf,
                "policies": policies,
                "mode": "deterministic" if fallback else "agent",
                "errors": [
                    *state["errors"],
                    "Model unavailable or invalid decision; "
                    + ("switched to deterministic audit." if fallback else "retrying."),
                ],
                "trace": [*state["trace"], "Model decision rejected"],
            }

    def execute(state: AuditState) -> dict:
        name = state["pending"]
        try:
            result = ToolResult.model_validate(registered[name].invoke({}))
            validate_result(result, state["data"], name)
            return {
                "results": {**state["results"], name: result},
                "calls": state["calls"] + 1,
                "trace": [*state["trace"], f"Executed and verified {name}"],
            }
        except Exception:
            return {
                "done": True,
                "errors": [*state["errors"], f"Tool {name} failed validation; audit stopped."],
                "trace": [*state["trace"], f"Tool {name} failed"],
            }

    def validate(state: AuditState) -> dict:
        for name, result in state["results"].items():
            validate_result(result, state["data"], name)
        return {}

    def finish(state: AuditState) -> dict:
        return {
            "report": build_report(
                state["data"],
                state["results"],
                state["mode"],
                state["errors"],
                state["recommendations"],
            )
        }

    def render_pdf(state: AuditState) -> dict:
        from app.services.reporting import pdf_report

        try:
            dates = state["data"].cleaned["date"].dropna()
            if dates.empty:
                raise ValueError("No dated transactions.")
            _, content = pdf_report(
                state["data"],
                state,
                dates.min().date(),
                dates.max().date(),
                include_ai=True,
                policies=state["policies"],
            )
            return {
                "pdf_bytes": content,
                "trace": [*state["trace"], "Validated and generated PDF report"],
            }
        except Exception:
            return {
                "pdf_error": "PDF validation or rendering failed; no PDF was issued.",
                "trace": [*state["trace"], "PDF generation failed"],
            }

    graph = StateGraph(AuditState)
    graph.add_node("plan", plan)
    graph.add_node("execute", execute)
    graph.add_node("validate", validate)
    graph.add_node("finish", finish)
    graph.add_node("render_pdf", render_pdf)
    graph.add_edge(START, "plan")
    graph.add_conditional_edges(
        "plan", lambda s: "finish" if s.get("done") else ("execute" if s.get("pending") else "plan")
    )
    graph.add_conditional_edges("execute", lambda s: "finish" if s.get("done") else "validate")
    graph.add_edge("validate", "plan")
    graph.add_conditional_edges("finish", lambda s: "render_pdf" if s["pdf_requested"] else END)
    graph.add_edge("render_pdf", END)
    return graph.compile().invoke(
        {
            "data": data,
            "goal": goal,
            "mode": mode,
            "results": {},
            "calls": 0,
            "retries": 0,
            "errors": [],
            "trace": [],
            "recommendations": [],
            "done": False,
            "pdf_requested": generate_pdf,
            "policies": policies,
        },
        config={"recursion_limit": 40},
    )
