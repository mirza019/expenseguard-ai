import json

import pytest

from app.agents.graph import run_audit
from app.database.duckdb_service import summarize
from app.services.ingestion import read_upload
from app.services.reporting import json_report, markdown_report
from app.services.validation import validate
from scripts.generate_data import generate


def test_complete_workflow():
    source, _ = generate()
    loaded = read_upload(source.to_csv(index=False).encode(), "expenses.csv")
    data = validate(loaded)
    state = run_audit(data)
    report = json.loads(json_report(state["report"]))
    assert report["total_actual_cents"] == int(data.eligible["amount_cents"].sum())
    assert report["flagged_rows"] > 0
    assert len(report["tools_run"]) == 4
    assert any(
        f["rule"] == "high_amount_iqr" and "TX00003" in f["transaction_ids"]
        for f in report["findings"]
    )
    for dimension in ["department", "monthly", "category"]:
        assert int(summarize(data, dimension)["amount_cents"].sum()) == report["total_actual_cents"]
    assert "ExpenseGuard AI" in markdown_report(report)
    with pytest.raises(ValueError):
        summarize(data, "DROP TABLE expenses")
