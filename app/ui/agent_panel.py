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
    selected = st.selectbox("Individual analytical check", list(TOOLS))
    if st.button("Run selected check"):
        with st.spinner("Running check…"):
            result = execute_tool(selected, data)
            st.session_state["individual"] = result.model_dump()
    if "individual" in st.session_state:
        st.json(st.session_state["individual"], expanded=False)
    if st.button("Run complete deterministic audit", type="primary"):
        with st.spinner("Executing four verified checks…"):
            st.session_state["audit"] = run_audit(data)
        st.rerun()


def agent_panel(data: ValidatedData, model_status: ModelStatus | None = None) -> None:
    """Optional local inference; explicit fallback status is shown in final state."""
    st.subheader("Local AI agent")
    st.info(
        "Agent mode uses LangGraph and your local Ollama service. If unavailable, "
        "bounded retries switch to a clearly labeled deterministic audit."
    )
    goal = st.text_area(
        "Audit goal",
        value="Audit the expenses and identify the biggest financial risks.",
        max_chars=2000,
    )
    if st.button("Run agent", disabled=model_status is None or model_status.state != "ready"):
        try:
            with st.spinner("Agent selecting tools and inspecting evidence…"):
                st.session_state["audit"] = run_audit(
                    data,
                    goal,
                    mode="agent",
                    config=settings(),
                    policies=tuple(st.session_state.get("policy_documents", ())),
                )
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))
    audit = st.session_state.get("audit")
    if audit:
        st.write("Active result mode:", audit["mode"])
        st.write("Execution trace:", audit["trace"])
        for error in audit["errors"]:
            st.warning(error)
        if audit.get("pdf_error"):
            st.warning(audit["pdf_error"])
        if audit.get("pdf_bytes"):
            st.download_button(
                "Download agent-requested PDF",
                audit["pdf_bytes"],
                "ExpenseGuard_Agent_Audit_Report.pdf",
                mime="application/pdf",
            )


def report_panel(data: ValidatedData | None = None) -> None:
    """Display structured findings and export evidence, preserving all source references."""
    audit = st.session_state.get("audit")
    if not audit:
        st.info("Run an audit to generate a report.")
        return
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
