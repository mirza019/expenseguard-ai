"""FinContext AI — Autonomous Financial Intelligence & Context Engineering Platform."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st

from app.ui.agent_panel import agent_panel, audit_panel, report_panel
from app.ui.context_registry import context_registry_panel
from app.ui.dashboard import dashboard
from app.ui.evaluation_lab import evaluation_lab
from app.ui.findings import findings_panel
from app.ui.knowledge_base import knowledge_base, policy_quick_panel
from app.ui.model_setup import model_setup_panel
from app.ui.upload import upload_panel
from app.ui.workflows import monthly_close_panel

PAGES = ["Data & Context", "Dashboard", "Agent Workflows", "Reports & Governance"]


def _style() -> None:
    st.markdown(
        """<style>
        .stApp{background:#F8FAF8;color:#172B24;font-family:Inter,system-ui,sans-serif}
        h1,h2,h3{color:#105C48;letter-spacing:-.025em}p{line-height:1.6}
        [data-testid="stMetric"]{background:#fff;border:1px solid #DCE8DF;border-radius:12px;padding:18px}
        [data-testid="stMetricValue"]{font-variant-numeric:tabular-nums;font-size:1.65rem}
        [data-testid="stSidebar"]{background:#EAF4EE;border-right:1px solid #DCE8DF}
        .block-container{padding-top:2rem;max-width:1500px}
        div[role="radiogroup"]{gap:.45rem;flex-wrap:wrap}
        @media (min-width: 800px){
          [data-testid="stHorizontalBlock"]{
            flex-direction:row!important;
            flex-wrap:nowrap!important;
            align-items:stretch!important;
          }
          [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]{
            min-width:0!important;
            width:auto!important;
          }
          [data-testid="stHorizontalBlock"] [data-testid="stMetric"]{
            height:100%;
          }
        }
        </style>""",
        unsafe_allow_html=True,
    )


def _header() -> str:
    st.title("FinContext AI")
    st.markdown("**Autonomous Financial Intelligence & Context Engineering Platform**")
    st.caption(
        "Local-first financial analytics, governed business knowledge, hybrid retrieval, "
        "and evidence-based workflows with human review."
    )
    with st.sidebar:
        st.markdown("### Navigation")
        return st.radio(
            "Workspace",
            PAGES,
            key="fincontext_primary_workspace_v3",
            help="Choose one of the four primary workspaces.",
        )


def main() -> None:
    st.set_page_config(page_title="FinContext AI", page_icon="◈", layout="wide")
    _style()
    page = _header()
    if page not in PAGES:
        # Older Streamlit/browser sessions may replay an index instead of the option value.
        page = PAGES[0]
    model_status = model_setup_panel()
    data = st.session_state.get("data")

    if page == "Data & Context":
        st.header("Data & Context")
        st.write(
            "Load financial evidence, validate its structure, inspect policy sources, and govern "
            "the definitions used by automated workflows."
        )
        data = upload_panel()
        source, policy, context = st.tabs(["Validated data", "Policy library", "Context registry"])
        with source:
            if data is None:
                st.info("Load a CSV or XLSX file above to create a validated analytical dataset.")
            else:
                st.success(f"{len(data.original):,} source rows are available to workflows.")
        with policy:
            policy_quick_panel()
        with context:
            context_registry_panel()
        return

    if page == "Dashboard":
        st.header("Financial Intelligence Dashboard")
        if data is None:
            st.info(
                "Start in **Data & Context**. Load a financial export or the fictional sample; "
                "FinContext AI will then calculate and investigate without requiring a chat prompt."
            )
            st.markdown(
                "**Workflow:** validate data → resolve governed context → calculate variance → "
                "investigate material changes → prepare a human-review draft."
            )
            return
        audit = st.session_state.get("audit")
        dashboard(data, audit["report"] if audit else None)
        run = st.session_state.get("monthly_close")
        if run:
            st.subheader("Latest autonomous workflow")
            st.write(
                f"{run.reporting_period} · {run.status} · {len(run.drivers)} material department(s) "
                f"· {run.approval_status.replace('_', ' ')}"
            )
        return

    if page == "Agent Workflows":
        st.header("Agent Workflows")
        if data is None:
            st.info("Load validated financial data in **Data & Context** first.")
            return
        monthly, expense, ask = st.tabs(
            ["Monthly financial review", "Expense compliance audit", "Ask AI"]
        )
        with monthly:
            monthly_close_panel(data)
        with expense:
            audit_panel(data)
        with ask:
            agent_panel(data, model_status)
        return

    st.header("Reports & Governance")
    if data is None:
        st.info("Load financial data before reviewing reports and workflow evidence.")
        return
    findings, reports, evaluation, diagnostics = st.tabs(
        ["Findings", "Management reports", "Evaluation", "Diagnostics"]
    )
    with findings:
        findings_panel(data, st.session_state.get("audit"))
    with reports:
        report_panel(data)
    with evaluation:
        evaluation_lab()
    with diagnostics:
        knowledge_base()


if __name__ == "__main__":
    main()
