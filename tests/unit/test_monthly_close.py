from pathlib import Path

from app.services.ingestion import read_upload
from app.services.validation import validate
from app.workflows.monthly_close import run_monthly_close


def test_monthly_close_reconciles_and_is_idempotent():
    path = Path(__file__).resolve().parents[2] / "data" / "synthetic_expenses.csv"
    data = validate(read_upload(path.read_bytes(), path.name))
    first = run_monthly_close(data)
    second = run_monthly_close(data)
    assert first.idempotency_key == second.idempotency_key
    assert first.actual_cents >= 0
    if first.budget_complete:
        assert first.variance_cents == first.actual_cents - first.budget_cents
    assert first.approval_status == "awaiting_human_review"
    assert all("cause" in item.interpretation for item in first.drivers if item.variance_cents)
