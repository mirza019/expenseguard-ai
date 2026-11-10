"""ExpenseGuard AI — cohesive local financial audit and policy-intelligence workspace."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st

from app.agents.graph import run_audit
from app.ui.agent_panel import agent_panel, audit_panel, report_panel
from app.ui.dashboard import dashboard
from app.ui.evaluation_lab import evaluation_lab
from app.ui.findings import findings_panel
from app.ui.knowledge_base import knowledge_base
from app.ui.model_setup import model_setup_panel
from app.ui.upload import upload_panel


def main() -> None:
    st.set_page_config(page_title="ExpenseGuard AI", page_icon="◈", layout="wide")
    st.markdown(
        """<style>
    .stApp{background:#F8FAF8;color:#172B24;font-family:Inter,system-ui,sans-serif;}
    h1,h2,h3{color:#105C48;letter-spacing:-.025em;}p{line-height:1.65;}
    [data-testid="stMetric"]{background:#fff;border:1px solid #DCE8DF;border-radius:12px;padding:18px;box-shadow:0 2px 8px #172b2405;}
    [data-testid="stMetricValue"]{font-variant-numeric:tabular-nums;font-size:1.65rem;}
    [data-testid="stSidebar"]{background:#EAF4EE;border-right:1px solid #DCE8DF;}
    [data-baseweb="tab-list"]{gap:10px;flex-wrap:wrap;}[data-baseweb="tab"]{font-size:13px;}
    .block-container{padding-top:2rem;max-width:1500px;}
    </style>""",
        unsafe_allow_html=True,
    )
    st.title("ExpenseGuard AI")
    st.caption(
        "Agentic Financial Audit & Policy Intelligence Platform · Evidence first. Decisions stay human."
    )
    model_status = model_setup_panel()
    tabs = st.tabs(
        [
            "Overview",
            "Data Workspace",
            "Policy Knowledge Base",
            "AI Audit Assistant",
            "Audit Findings",
            "Reports",
            "RAG Evaluation Lab",
            "System Status",
        ]
    )
    with tabs[1]:
        data = upload_panel()
    with tabs[2]:
        knowledge_base()
    with tabs[6]:
        evaluation_lab()
    with tabs[7]:
        st.subheader("System Status")
        st.write(
            "Financial engine: deterministic Python / DuckDB. Local model:",
            model_status.state if model_status else "unconfigured",
        )
        st.caption(
            "Policy indexing and financial auditing do not require Ollama. Neural embeddings are an optional explicit setup."
        )
        if model_status:
            st.write("Model:", model_status.model)
    if data is None:
        with tabs[0]:
            st.info(
                "Start in Data Workspace: load a fictional demo or upload your expense export, then run a full audit."
            )
        return
    dates = data.cleaned["date"].dropna()
    if not dates.empty:
        import hashlib

        from app.services.report_validation import select_period

        low, high = dates.min().date(), dates.max().date()
        with st.sidebar.expander("Financial analysis period"):
            first = st.date_input(
                "Analysis start", low, min_value=low, max_value=high, key="analysis_start"
            )
            last = st.date_input(
                "Analysis end", high, min_value=low, max_value=high, key="analysis_end"
            )
        try:
            key = hashlib.sha256(
                (data.original.to_json() + str(first) + str(last)).encode()
            ).hexdigest()
            if st.session_state.get("analysis_scope_key") != key:
                for name in ["audit", "pdf_artifact", "pdf_scoped_audit"]:
                    st.session_state.pop(name, None)
                st.session_state["analysis_scope_key"] = key
            if (first, last) != (low, high):
                data = select_period(data, first, last)
        except ValueError as exc:
            st.error(str(exc))
            return
    with tabs[0]:
        if st.button("Run Full Audit", type="primary"):
            with st.spinner("Executing financial controls and applicable policy checks…"):
                st.session_state["audit"] = run_audit(
                    data,
                    policy_index=st.session_state.get("policy_index"),
                    policy_root=st.session_state.get("policy_root"),
                )
            st.rerun()
        current = st.session_state.get("audit")
        dashboard(current["data"] if current else data, current["report"] if current else None)
    with tabs[3]:
        agent_panel(data, model_status)
    with tabs[4]:
        audit_panel(data)
        findings_panel(
            st.session_state["audit"]["data"] if st.session_state.get("audit") else data,
            st.session_state.get("audit"),
        )
    with tabs[5]:
        report_panel(data)


if __name__ == "__main__":
    main()
