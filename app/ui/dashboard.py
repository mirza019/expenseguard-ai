"""Professional financial overview; every visual reconciles to validated expense facts."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from app.database.duckdb_service import summarize
from app.services.planning import planning_insights
from app.services.validation import ValidatedData
from app.tools.budget import check_budget

EMERALD = "#167D61"
DARK_EMERALD = "#105C48"
SAGE = "#AACBB7"
AMBER = "#B7791F"
GRID = "#E6EEE9"
PLOT_CONFIG = {"displayModeBar": False, "responsive": True, "scrollZoom": False}


def _eur(cents: int | None) -> str:
    return "Not available" if cents is None else f"€{cents / 100:,.2f}"


def polish(fig: go.Figure, height: int = 360) -> go.Figure:
    fig.update_layout(
        height=height,
        font={"family": "Inter, system-ui, sans-serif", "color": "#172B24"},
        title={"font": {"size": 17, "color": DARK_EMERALD}, "x": 0.02, "xanchor": "left"},
        paper_bgcolor="white",
        plot_bgcolor="white",
        margin={"l": 30, "r": 20, "t": 70, "b": 45},
        legend={"orientation": "h", "y": 1.13, "x": 0},
        hoverlabel={"font_size": 12},
    )
    fig.update_xaxes(gridcolor=GRID, zerolinecolor=GRID)
    fig.update_yaxes(gridcolor=GRID, zerolinecolor=GRID)
    return fig


def _chart(target, figure: go.Figure) -> None:
    target.plotly_chart(figure, config=PLOT_CONFIG)


def _horizontal_panels(widths: tuple[int, ...]):
    """Create fixed desktop panels; unlike st.columns these do not enter mobile stacking mode."""
    row = st.container(horizontal=True, gap="medium", vertical_alignment="top")
    return tuple(row.container(width=width) for width in widths)


def _summary_strip(data: ValidatedData, budget: dict, monthly: pd.DataFrame) -> None:
    departments = int(data.eligible["department"].replace("", pd.NA).nunique())
    categories = int(data.eligible["category"].replace("", pd.NA).nunique())
    months = len(monthly)
    latest = monthly["month"].max() if months else "Not available"
    st.markdown(
        f"""
        <div style="display:flex;gap:24px;flex-wrap:wrap;padding:14px 18px;margin:6px 0 20px 0;
        background:#EAF4EE;border:1px solid #DCE8DF;border-radius:12px;color:#40554C">
          <span><b style="color:#105C48">Latest period</b><br>{latest}</span>
          <span><b style="color:#105C48">Periods</b><br>{months}</span>
          <span><b style="color:#105C48">Departments</b><br>{departments}</span>
          <span><b style="color:#105C48">Categories</b><br>{categories}</span>
          <span><b style="color:#105C48">Budget coverage</b><br>{'Complete' if budget['budget_complete'] else 'Incomplete'}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def dashboard(data: ValidatedData, report: dict | None) -> None:
    budget = check_budget(data).metrics
    monthly = summarize(data, "monthly")
    monthly["amount_eur"] = monthly["amount_cents"] / 100

    st.markdown("### Management overview")
    if data.cleaned["date"].notna().any():
        start = data.cleaned["date"].min().date()
        end = data.cleaned["date"].max().date()
        st.caption(f"Validated reporting scope · {start}–{end} · EUR · {len(data.cleaned):,} source rows")
    _summary_strip(data, budget, monthly)

    actual = budget["total_actual_cents"]
    represented_budget = budget["total_budget_cents"]
    variance = budget["variance_cents"]
    variance_percent = budget["variance_percent"]
    flagged = report["flagged_rows"] if report else None

    kpis = _horizontal_panels((320, 320, 320, 320))
    kpis[0].metric("Recorded expense", _eur(actual), help="Total eligible expense in the validated dataset.")
    kpis[1].metric(
        "Represented budget",
        _eur(represented_budget),
        help="Shown only when every represented allocation is known and consistent.",
    )
    kpis[2].metric(
        "Budget variance",
        _eur(variance),
        delta=f"{variance_percent:+.1f}%" if variance_percent is not None else None,
        delta_color="inverse",
        help="Actual minus budget. Positive values indicate expense above budget.",
    )
    kpis[3].metric(
        "Rows requiring review",
        f"{flagged:,}" if flagged is not None else "Audit not run",
        help="Unique source rows referenced by completed audit findings.",
    )
    st.caption(
        "Unknown or conflicting budgets are not treated as zero. Potential duplicates remain in recorded expense until reviewed."
    )

    overview, budget_tab, mix_tab, scenario_tab = st.tabs(
        ["Overview", "Budget performance", "Expense mix", "Scenarios"]
    )

    with overview:
        trend_col, review_col = _horizontal_panels((860, 400))
        with trend_col:
            if len(monthly) > 1:
                trend = px.line(
                    monthly,
                    x="month",
                    y="amount_eur",
                    markers=True,
                    title="Expense trend by month",
                    labels={"month": "Reporting month", "amount_eur": "Expense (EUR)"},
                    color_discrete_sequence=[EMERALD],
                    hover_data={"amount_eur": ":,.2f"},
                )
                trend.update_traces(line={"width": 3}, marker={"size": 8})
                trend.update_yaxes(tickprefix="€", tickformat=",.0f", rangemode="tozero")
                _chart(st, polish(trend, 380))
            else:
                st.info("At least two reporting periods are required for a trend chart.")
        with review_col:
            st.markdown("#### Review status")
            duplicate_rows = (
                len(
                    {
                        row
                        for finding in report["findings"]
                        if finding["tool"] == "duplicates"
                        for row in finding["rows"]
                    }
                )
                if report
                else None
            )
            st.metric("Data-quality issues", len(data.issues))
            st.metric(
                "Potential duplicate rows",
                duplicate_rows if duplicate_rows is not None else "Audit not run",
            )
            if report:
                st.success("Audit results are available for management review.")
            else:
                st.info("Run an audit to populate risk indicators and findings.")

        st.markdown("#### Where expense is concentrated")
        department_col, category_col = _horizontal_panels((630, 630))
        for target, dimension, title in [
            (department_col, "department", "Expense by department"),
            (category_col, "category", "Expense by category"),
        ]:
            frame = summarize(data, dimension)
            frame["amount_eur"] = frame["amount_cents"] / 100
            frame = frame.nlargest(10, "amount_eur").sort_values("amount_eur")
            figure = px.bar(
                frame,
                x="amount_eur",
                y=dimension,
                orientation="h",
                title=title,
                labels={"amount_eur": "Expense (EUR)", dimension: ""},
                color_discrete_sequence=[EMERALD],
                hover_data={"amount_eur": ":,.2f", "amount_cents": False},
            )
            figure.update_xaxes(tickprefix="€", tickformat=",.0f", rangemode="tozero")
            _chart(target, polish(figure, 390))

    with budget_tab:
        comparison = pd.DataFrame(budget["departments"])
        if comparison.empty:
            st.info("No department-level budget allocations are available.")
        else:
            comparison["actual_eur"] = comparison["actual_cents"] / 100
            comparison["budget_eur"] = comparison["budget_cents"] / 100
            comparison["variance_eur"] = comparison["variance_cents"] / 100
            known = comparison[comparison["variance_cents"].notna()].copy()
            budget_left, budget_right = _horizontal_panels((630, 630))
            grouped = px.bar(
                comparison,
                x="department",
                y=["actual_eur", "budget_eur"],
                barmode="group",
                title="Actual expense compared with budget",
                labels={"value": "EUR", "variable": "Measure", "department": "Department"},
                color_discrete_sequence=[EMERALD, SAGE],
            )
            grouped.update_yaxes(tickprefix="€", tickformat=",.0f")
            _chart(budget_left, polish(grouped, 410))

            known["direction"] = known["variance_eur"].map(
                lambda value: "Above budget" if value > 0 else "At or below budget"
            )
            variance_chart = px.bar(
                known.sort_values("variance_eur"),
                x="variance_eur",
                y="department",
                orientation="h",
                color="direction",
                title="Department contribution to variance",
                labels={"variance_eur": "Actual − budget (EUR)", "department": ""},
                color_discrete_map={"Above budget": AMBER, "At or below budget": EMERALD},
            )
            variance_chart.update_xaxes(tickprefix="€", tickformat=",.0f")
            _chart(budget_right, polish(variance_chart, 410))

            st.markdown("#### Department detail")
            display = comparison[
                ["department", "actual_eur", "budget_eur", "variance_eur", "variance_percent"]
            ].rename(
                columns={
                    "department": "Department",
                    "actual_eur": "Actual (EUR)",
                    "budget_eur": "Budget (EUR)",
                    "variance_eur": "Variance (EUR)",
                    "variance_percent": "Variance (%)",
                }
            )
            st.dataframe(
                display,
                hide_index=True,
                column_config={
                    "Actual (EUR)": st.column_config.NumberColumn(format="€ %.2f"),
                    "Budget (EUR)": st.column_config.NumberColumn(format="€ %.2f"),
                    "Variance (EUR)": st.column_config.NumberColumn(format="€ %.2f"),
                    "Variance (%)": st.column_config.NumberColumn(format="%.1f%%"),
                },
            )

    with mix_tab:
        category = summarize(data, "category")
        category["amount_eur"] = category["amount_cents"] / 100
        mix_left, mix_right = _horizontal_panels((520, 740))
        donut = px.pie(
            category,
            names="category",
            values="amount_eur",
            hole=0.58,
            title="Share of recorded expense",
            color_discrete_sequence=[EMERALD, DARK_EMERALD, SAGE, "#6F9B82", AMBER, "#D8B56A"],
        )
        donut.update_traces(
            textposition="inside",
            textinfo="percent",
            hovertemplate="%{label}<br>€%{value:,.2f}<extra></extra>",
        )
        _chart(mix_left, polish(donut, 420))

        category = category.sort_values("amount_eur", ascending=False)
        category["share"] = category["amount_eur"] / category["amount_eur"].sum() * 100
        mix_table = category[["category", "amount_eur", "share"]].rename(
            columns={"category": "Category", "amount_eur": "Expense (EUR)", "share": "Share (%)"}
        )
        with mix_right:
            st.markdown("#### Category detail")
            st.dataframe(
                mix_table,
                hide_index=True,
                column_config={
                    "Expense (EUR)": st.column_config.NumberColumn(format="€ %.2f"),
                    "Share (%)": st.column_config.ProgressColumn(
                        format="%.1f%%", min_value=0, max_value=100
                    ),
                },
            )
            st.caption(
                "Concentration indicates where expense is recorded; it does not establish an operational cause."
            )

    with scenario_tab:
        st.markdown("#### Controlled expense scenario")
        st.caption("Illustrative calculation on recorded data—not a statistical forecast or committed saving.")
        reduction = st.slider("Discretionary expense reduction (%)", 0, 50, 10) / 100
        complete = st.checkbox("Assume uploaded elapsed months are complete for run-rate scenario")
        scenario = planning_insights(data, reduction, complete_months=complete)
        scenario_cols = _horizontal_panels((420, 420, 420))
        scenario_cols[0].metric(
            "Recorded discretionary expense", _eur(scenario["discretionary_actual_cents"])
        )
        scenario_cols[1].metric("Illustrative saving", _eur(scenario["scenario_savings_cents"]))
        scenario_cols[2].metric("Remaining expense", _eur(scenario["scenario_remaining_cents"]))
        st.caption(scenario["scenario_assumption"])
        if scenario["year_end"]:
            st.write("Year-end scenario", scenario["year_end"])
        else:
            st.info("A year-end run rate requires at least three complete, contiguous elapsed months.")
        st.write("**Recommended next step:**", scenario["next_action"])
        if scenario["monthly_changes"]:
            st.dataframe(pd.DataFrame(scenario["monthly_changes"]), hide_index=True)
