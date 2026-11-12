"""Controlled audit execution and transparent results."""

import pandas as pd
import streamlit as st

from app.agents.graph import run_audit
from app.config import settings
from app.services.analytics import TOOLS, execute_tool
from app.services.model_manager import ModelStatus
from app.services.reporting import json_report, markdown_report
from app.services.validation import ValidatedData


def audit_panel(data: ValidatedData) -> None:
    """Run independent tools or a complete non-LLM audit."""
    st.subheader("Audit analysis")
    available_tools = list(TOOLS)
    selected = st.selectbox(
        "Individual analytical check", available_tools, key="individual_audit_tool_v2"
    )
    if selected not in available_tools:
        selected = available_tools[0]
    if st.button("Run selected check"):
        with st.spinner("Running check…"):
            result = execute_tool(selected, data)
            st.session_state["individual"] = result.model_dump()
    if "individual" in st.session_state:
        st.json(st.session_state["individual"], expanded=False)
    if st.button("Run complete deterministic audit", type="primary"):
        with st.spinner("Executing four verified checks…"):
            st.session_state["audit"] = run_audit(
                data,
                policy_index=st.session_state.get("policy_index"),
                policy_root=st.session_state.get("policy_root"),
            )
        st.rerun()


def agent_panel(data: ValidatedData, model_status: ModelStatus | None = None) -> None:
    """Optional local inference; explicit fallback status is shown in final state."""
    st.subheader("AI-guided audit")
    st.write(
        "Choose what you want to investigate. The AI selects from verified audit checks; "
        "Python calculates the financial results and your data is not changed."
    )
    choices = {
        "Complete risk review": "Audit the expenses and identify the biggest financial risks.",
        "Possible duplicate payments": "Find possible duplicate payments and explain why each was flagged.",
        "Budget overruns": "Which departments exceeded their represented budgets, and by how much?",
        "Unusually large expenses": "Which unusually large expenses require investigation?",
        "Missing or invalid data": "Which records have missing or invalid information?",
        "Custom question": "",
    }
    focus = st.selectbox(
        "What do you want to check?", list(choices), key="ai_audit_focus_v2"
    )
    if focus not in choices:
        focus = "Complete risk review"
    goal = choices[focus]
    if focus == "Custom question":
        goal = st.text_area(
            "Your audit question",
            placeholder="Describe the financial issue you want to investigate…",
            max_chars=2000,
        )
    else:
        st.caption(goal)
    ready = model_status is not None and model_status.state == "ready"
    if ready:
        st.success("Local AI is ready.")
    else:
        st.warning("Local AI is unavailable. The standard verified audit still works without it.")
    if st.button(
        "Run AI-guided audit",
        type="primary",
        width="stretch",
        disabled=not ready or not goal.strip(),
    ):
        try:
            with st.spinner("Agent selecting tools and inspecting evidence…"):
                st.session_state["audit"] = run_audit(
                    data,
                    goal,
                    mode="agent",
                    config=settings(),
                    policies=tuple(st.session_state.get("policy_documents", ())),
                    policy_index=st.session_state.get("policy_index"),
                    policy_root=st.session_state.get("policy_root"),
                )
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))
    audit = st.session_state.get("audit")
    if audit:
        st.success(
            f"Audit complete in {audit['mode']} mode. Review the results in "
            "**Reports & Governance → Findings**."
        )
        for error in audit["errors"]:
            st.warning(error)
        if audit.get("pdf_error"):
            st.warning(audit["pdf_error"])
        if audit.get("pdf_bytes"):
            st.download_button(
                "Download agent-requested PDF",
                audit["pdf_bytes"],
                "FinContext_AI_Agent_Audit_Report.pdf",
                mime="application/pdf",
            )
        with st.expander("How the AI reached this result"):
            st.write("Execution mode:", audit["mode"])
            st.write("Verified tool activity:", audit["trace"])


def report_panel(data: ValidatedData | None = None) -> None:
    """Display structured findings and export evidence, preserving all source references."""
    audit = st.session_state.get("audit")
    if not audit:
        st.info("Run an audit to generate a report.")
        return
    data = audit.get("data", data)
    report = audit["report"]
    st.subheader("Evidence-based audit report")
    st.write("Mode:", report["mode"])
    st.write("Tools executed:", ", ".join(report["tools_run"]))
    if len(report["tools_run"]) < 4:
        st.warning("Partial audit: tools not listed above were not executed.")
    if report["errors"]:
        st.warning(
            "Audit contains execution errors or fallback events; inspect the execution trace."
        )
    if report["findings"]:
        frame = pd.DataFrame(report["findings"])
        severity = st.multiselect(
            "Finding severity", ["high", "medium"], default=["high", "medium"]
        )
        st.dataframe(frame[frame["severity"].isin(severity)], hide_index=True)
    else:
        st.success("No flags from the checks executed. This is not an assurance of no errors.")
    if report["recommendations"]:
        st.write("Model-selected investigation actions:", report["recommendations"])
    for limitation in report["limitations"]:
        st.caption(limitation)
    st.download_button(
        "Download Markdown report",
        markdown_report(report),
        "expense-audit.md",
        mime="text/markdown",
    )
    st.download_button(
        "Download complete JSON evidence",
        json_report(report),
        "expense-audit.json",
        mime="application/json",
    )
    # Prevent spreadsheet-formula execution when exported text is opened in Excel.
    if report["findings"]:
        export = pd.DataFrame(report["findings"]).astype(str)
        export = export.map(
            lambda value: "'" + value if value.startswith(("=", "+", "-", "@")) else value
        )
        st.download_button(
            "Download findings CSV",
            export.to_csv(index=False),
            "expense-findings.csv",
            mime="text/csv",
        )

    if data is not None:
        from app.ui.report_panel import pdf_report_panel

        pdf_report_panel(data, audit)
