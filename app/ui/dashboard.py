"""Emerald financial decision-support overview; every chart reconciles to eligible expense facts."""

import pandas as pd
import plotly.express as px
import streamlit as st

from app.database.duckdb_service import summarize
from app.services.planning import planning_insights
from app.services.validation import ValidatedData
from app.tools.budget import check_budget

GREEN = "#167D61"


def polish(fig):
    fig.update_layout(
        font={"family": "Inter, system-ui, sans-serif", "color": "#172B24"},
        paper_bgcolor="white",
        plot_bgcolor="white",
        margin={"l": 20, "r": 20, "t": 65, "b": 35},
        legend={"orientation": "h", "y": 1.12},
        hoverlabel={"font_size": 12},
    )
    fig.update_yaxes(gridcolor="#EAF0EC", rangemode="tozero")
    return fig


def dashboard(data: ValidatedData, report: dict | None) -> None:
    if data.cleaned["date"].notna().any():
        st.caption(
            f"Result scope: {data.cleaned['date'].min().date()} to {data.cleaned['date'].max().date()} · {len(data.cleaned):,} source rows"
        )
    budget = check_budget(data).metrics
    columns = st.columns(4)
    columns[0].metric("Eligible expenses · EUR", f"{budget['total_actual_cents'] / 100:,.2f}")
    columns[1].metric(
        "Represented budget · EUR",
        f"{budget['total_budget_cents'] / 100:,.2f}"
        if budget["total_budget_cents"] is not None
        else "Incomplete",
    )
    columns[2].metric(
        "Expense − budget · EUR",
        f"{budget['variance_cents'] / 100:,.2f}"
        if budget["variance_cents"] is not None
        else "Not evaluable",
    )
    columns[3].metric(
        "Audit-flagged source rows", report["flagged_rows"] if report else "Run audit"
    )
    st.caption(
        "Scope: current uploaded data · EUR · all payment statuses · potential duplicates retained. Unknown budgets are not zero."
    )
    if report:
        policy = report.get("indexed_policy_findings") if not report.get("policy_error") else None
        st.caption(
            f"Financial audit: complete · Quality issues: {len(data.issues)} · Policy exceptions: "
            + str(sum(f["status"] == "potential_violation" for f in policy))
            if policy is not None
            else f"Financial audit complete · Quality issues: {len(data.issues)} · Policy compliance not evaluated"
        )
    if report:
        counts = st.columns(3)
        duplicates = {r for f in report["findings"] if f["tool"] == "duplicates" for r in f["rows"]}
        counts[0].metric("Potential duplicate source rows", len(duplicates))
        policy = report.get("indexed_policy_findings") if not report.get("policy_error") else None
        counts[1].metric(
            "Potential policy exceptions",
            sum(f["status"] == "potential_violation" for f in policy)
            if policy is not None
            else "Not evaluated",
        )
        counts[2].metric("Data-quality issues", len(data.issues))
    left, right = st.columns(2)
    for target, dim in [(left, "department"), (right, "category")]:
        frame = summarize(data, dim)
        frame["amount_eur"] = frame["amount_cents"] / 100
        frame = frame.sort_values("amount_eur")
        fig = px.bar(
            frame,
            x="amount_eur",
            y=dim,
            orientation="h",
            title=f"Recorded spending by {dim}",
            labels={"amount_eur": "Expense (EUR)", dim: dim.title()},
            color_discrete_sequence=[GREEN],
            hover_data={"amount_eur": ":,.2f", "amount_cents": False},
        )
        fig.update_xaxes(rangemode="tozero", tickformat=",.0f")
        target.plotly_chart(polish(fig), width="stretch")
    monthly = summarize(data, "monthly")
    monthly["amount_eur"] = monthly["amount_cents"] / 100
    if len(monthly) > 1:
        st.plotly_chart(
            polish(
                px.line(
                    monthly,
                    x="month",
                    y="amount_eur",
                    markers=True,
                    title="Monthly expense movement — investigate timing and mix",
                    labels={"month": "Invoice month", "amount_eur": "Expense (EUR)"},
                    color_discrete_sequence=[GREEN],
                    hover_data={"amount_eur": ":,.2f"},
                )
            ),
            width="stretch",
        )
    comparison = pd.DataFrame(budget["departments"])
    if not comparison.empty:
        comparison["actual_eur"] = comparison["actual_cents"] / 100
        comparison["budget_eur"] = comparison["budget_cents"] / 100
        st.plotly_chart(
            polish(
                px.bar(
                    comparison,
                    x="department",
                    y=["actual_eur", "budget_eur"],
                    barmode="group",
                    title="Department budgets versus recorded expense",
                    labels={"value": "EUR", "variable": "Measure"},
                    color_discrete_sequence=[GREEN, "#AACBB7"],
                )
            ),
            width="stretch",
        )
        known = comparison[comparison["variance_cents"].notna()].copy()
        known["variance_eur"] = known["variance_cents"] / 100
        known["direction"] = known["variance_eur"].map(
            lambda x: "Above budget" if x > 0 else "Below budget"
        )
        st.plotly_chart(
            polish(
                px.bar(
                    known,
                    x="department",
                    y="variance_eur",
                    color="direction",
                    title="Which departments contribute to budget variance?",
                    labels={"variance_eur": "Actual − budget (EUR)"},
                    color_discrete_map={"Above budget": "#B7791F", "Below budget": GREEN},
                )
            ),
            width="stretch",
        )
    with st.expander("Planning scenarios and investigation priorities"):
        reduction = st.slider("Discretionary expense reduction scenario (%)", 0, 50, 10) / 100
        complete = st.checkbox("Assume uploaded elapsed months are complete for run-rate scenario")
        scenario = planning_insights(data, reduction, complete_months=complete)
        st.metric(
            "Illustrative savings on Travel / Meals / Hotel · EUR",
            f"{scenario['scenario_savings_cents'] / 100:,.2f}",
        )
        st.caption(scenario["scenario_assumption"])
        if scenario["year_end"]:
            st.write("Year-end scenario:", scenario["year_end"])
        else:
            st.info(
                "Year-end run rate not shown: insufficient complete elapsed-month coverage or year already complete."
            )
        st.write(scenario["next_action"])
        st.dataframe(pd.DataFrame(scenario["monthly_changes"]), hide_index=True)
