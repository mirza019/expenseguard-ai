import pytest

from app.services.planning import planning_insights
from app.services.validation import validate
from scripts.generate_data import generate


def test_scenario_exact_financials_and_forecast_assumptions():
    frame, _ = generate()
    frame = frame.iloc[20:23].copy().reset_index(drop=True)
    frame["amount"] = ["100", "200", "300"]
    frame["category"] = "Travel"
    frame["invoice_date"] = ["2025-01-01", "2025-02-01", "2025-03-01"]
    data = validate(frame)
    result = planning_insights(data, 0.10, complete_months=True)
    assert result["scenario_savings_cents"] == 6000
    assert result["year_end"]["estimate_year_end_cents"] == 240000
    assert result["monthly_changes"][0]["change_cents"] == 10000
    assert planning_insights(data)["year_end"] is None
    with pytest.raises(ValueError):
        planning_insights(data, 2)


def test_column_aliases_and_ambiguous_columns():
    frame, _ = generate()
    frame = frame.iloc[20:21].copy()
    frame = frame.drop(columns=["invoice_date", "category"]).assign(
        transaction_date="2025-01-01", expense_category="Meals"
    )
    data = validate(frame)
    assert data.eligible.iloc[0]["category"] == "Meals"
    assert "transaction_date" in data.original
    bad = frame.copy()
    bad["Amount"] = bad["amount"]
    with pytest.raises(ValueError, match="Ambiguous"):
        validate(bad)
