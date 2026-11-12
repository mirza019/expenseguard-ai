"""Autonomous workflow controls and inspectable execution evidence."""

import pandas as pd
import streamlit as st

from app.services.validation import ValidatedData
from app.workflows.monthly_close import run_monthly_close


def monthly_close_panel(data: ValidatedData) -> None:
    st.subheader("Monthly Financial Review & Variance Investigation")
    st.write(
        "Validates the period, calculates budget variance, ranks material departments, and "
        "prepares a draft investigation for human review. No chat question is required."
    )
    periods = sorted(data.eligible["month"].dropna().unique(), reverse=True)
    period = st.selectbox("Reporting period", periods, key="monthly_review_period_v2")
    if period not in periods:
        period = periods[0]
    threshold = st.number_input("Material variance threshold (%)", 0.0, 500.0, 10.0)
    if st.button("Run monthly financial review", type="primary", width="stretch"):
        with st.spinner("Validating, calculating, investigating, and reconciling…"):
            st.session_state["monthly_close"] = run_monthly_close(data, period=period, threshold_percent=threshold)
        st.rerun()
    result = st.session_state.get("monthly_close")
    if not result:
        st.info("No monthly workflow has run in this session.")
        return
    st.success(f"Workflow completed for {result.reporting_period}; draft awaiting human review.")
    metrics = st.columns(4)
    metrics[0].metric("Actual · EUR", f"{result.actual_cents / 100:,.2f}")
    metrics[1].metric("Budget · EUR", f"{result.budget_cents / 100:,.2f}" if result.budget_cents is not None else "Incomplete")
    metrics[2].metric("Variance · EUR", f"{result.variance_cents / 100:,.2f}" if result.variance_cents is not None else "Not evaluable")
    metrics[3].metric("Material departments", len(result.drivers))
    if result.drivers:
        st.dataframe(pd.DataFrame([item.model_dump() for item in result.drivers]), hide_index=True)
    with st.expander("Execution trace and limitations"):
        for step in result.trace:
            st.write("✓", step)
        for limitation in result.limitations:
            st.caption(limitation)
