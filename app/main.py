"""ExpenseGuard AI Streamlit entry point: streamlit run app/main.py."""

import sys
from pathlib import Path

# Direct Streamlit execution must also resolve the application package.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st  # noqa: E402

from app.ui.agent_panel import agent_panel, audit_panel, report_panel  # noqa: E402
from app.ui.dashboard import dashboard  # noqa: E402
from app.ui.model_setup import model_setup_panel  # noqa: E402
from app.ui.upload import upload_panel


def main() -> None:
    """Render a single-session, in-memory audit application."""
    st.set_page_config(page_title="ExpenseGuard AI", page_icon="🧾", layout="wide")
    st.markdown(
        """<style>
    .stApp {background:#FAF8F9;} h1,h2,h3 {color:#711D3C;}
    [data-testid="stMetric"] {background:white;padding:1rem;border-radius:10px;
      border:1px solid #E7DAE0;}
    </style>""",
        unsafe_allow_html=True,
    )
    st.title("ExpenseGuard AI")
    st.caption("Evidence-first expense auditing · Local AI optional · Human review required")
    model_status = model_setup_panel()
    tabs = st.tabs(["Upload", "Overview", "Audit analysis", "AI agent", "Audit report"])
    with tabs[0]:
        data = upload_panel()
    if data is None:
        return
    with tabs[1]:
        audit = st.session_state.get("audit")
        dashboard(data, audit["report"] if audit else None)
    with tabs[2]:
        audit_panel(data)
    with tabs[3]:
        agent_panel(data, model_status)
    with tabs[4]:
        report_panel(data)


if __name__ == "__main__":
    main()
