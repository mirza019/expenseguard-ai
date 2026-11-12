"""Financial decision support with explicit assumptions, never causal/forecast certainty."""

from app.database.duckdb_service import summarize
from app.services.validation import ValidatedData


def planning_insights(
    data: ValidatedData,
    reduction: float = 0.10,
    categories: tuple[str, ...] = ("Travel", "Meals", "Hotel"),
    complete_months: bool = False,
) -> dict:
    if not 0 <= reduction <= 1:
        raise ValueError("Reduction must be between 0 and 100%.")
    frame = data.eligible
    discretionary = int(frame.loc[frame["category"].isin(categories), "amount_cents"].sum())
    monthly = summarize(data, "monthly")
    monthly_values = [
        {"month": r["month"], "actual_cents": int(r["amount_cents"])} for _, r in monthly.iterrows()
    ]
    changes = []
    for prior, current in zip(monthly_values, monthly_values[1:]):
        # Only adjacent calendar months are valid month-over-month comparisons.
        import pandas as pd

        if pd.Period(current["month"], "M") - pd.Period(prior["month"], "M") != pd.offsets.MonthEnd(
            1
        ):
            continue
        old = frame[frame["month"].eq(prior["month"])].groupby("category")["amount_cents"].sum()
        new = frame[frame["month"].eq(current["month"])].groupby("category")["amount_cents"].sum()
        contributions = {
            category: int(new.get(category, 0)) - int(old.get(category, 0))
            for category in set(old.index) | set(new.index)
        }
        largest = max(contributions, key=contributions.get) if contributions else "None"
        changes.append(
            {
                "month": current["month"],
                "prior_month": prior["month"],
                "change_cents": current["actual_cents"] - prior["actual_cents"],
                "largest_increase_category": largest,
                "largest_category_change_cents": contributions.get(largest, 0),
                "category_contributions_cents": contributions,
                "interpretation": "Arithmetic category contributions explain the recorded movement, not its operational cause; review timing, scope and invoices.",
            }
        )
    projection = None
    if complete_months and len(monthly_values) >= 3:
        latest = monthly_values[-1]["month"]
        year = int(latest[:4])
        month = int(latest[-2:])
        year_rows = [r for r in monthly_values if r["month"].startswith(str(year))]
        if len(year_rows) == month and month < 12:
            projection = {
                "year": year,
                "actual_ytd_cents": sum(r["actual_cents"] for r in year_rows),
                "estimate_year_end_cents": round(
                    sum(r["actual_cents"] for r in year_rows) / month * 12
                ),
                "assumption": "Simple YTD average run rate; assumes complete elapsed months, no seasonality or scope changes.",
                "kind": "scenario estimate, not a validated statistical forecast",
            }
    return {
        "currency": "EUR",
        "discretionary_actual_cents": discretionary,
        "reduction_fraction": reduction,
        "scenario_savings_cents": round(discretionary * reduction),
        "scenario_remaining_cents": discretionary - round(discretionary * reduction),
        "scenario_assumption": "Apply reduction only to selected recorded categories; no behavioral or contractual effects modeled.",
        "monthly_changes": changes,
        "year_end": projection,
        "next_action": "Review largest variances with cost-center owners and verify invoice timing and policy exceptions.",
    }
