from unittest.mock import patch

import pandas as pd
import pytest

from app.agents.graph import run_audit
from app.services.analytics import execute_tool, validate_result
from app.services.ingestion import IngestionError, read_upload
from app.services.validation import Finding, ToolResult, validate
from scripts.generate_data import generate


def test_invalid_all_financial_rows():
    frame, _ = generate()
    frame["currency"] = "USD"
    data = validate(frame)
    report = run_audit(data)["report"]
    assert report["total_actual_cents"] == 0
    assert report["eligible_rows"] == 0
    assert len(report["tools_run"]) == 4


def test_validation_other_failures():
    frame, _ = generate()
    frame.loc[0, "budget_amount"] = "invalid"
    frame.loc[1, "payment_status"] = "mystery"
    rules = {f.rule for f in validate(frame).issues}
    assert {"invalid_budget", "invalid_payment_status"} <= rules
    with pytest.raises(ValueError):
        generate(10)


def test_ingestion_row_limit_and_workbook_bomb(monkeypatch):
    import io
    from zipfile import ZipFile

    monkeypatch.setattr("app.services.ingestion.MAX_ROWS", 1)
    with pytest.raises(IngestionError, match="100,000"):
        read_upload(b"a\n1\n2\n", "a.csv")
    out = io.BytesIO()
    with ZipFile(out, "w") as archive:
        archive.writestr("sheet.xml", "x" * 6000)
    monkeypatch.setattr("app.services.ingestion.MAX_BYTES", 1000)
    # compressed bytes stay within the upload limit while expanded bytes do not
    out = io.BytesIO()
    from zipfile import ZIP_DEFLATED

    with ZipFile(out, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("sheet.xml", "x" * 60000)
    with pytest.raises(IngestionError, match="decompressed"):
        read_upload(out.getvalue(), "a.xlsx")


def test_missing_evidence_status_and_infinity():
    frame, _ = generate()
    data = validate(frame)
    with pytest.raises(ValueError, match="status"):
        validate_result(ToolResult(tool="budget", status="error"), data, "budget")
    with pytest.raises(ValueError, match="lacks evidence"):
        validate_result(
            ToolResult(tool="duplicates", findings=[Finding(rule="x", severity="high")]),
            data,
            "duplicates",
        )
    with pytest.raises(ValueError, match="Nonfinite"):
        validate_result(
            ToolResult(tool="duplicates", metrics={"x": float("inf")}), data, "duplicates"
        )
    result = execute_tool("budget", data)
    result.metrics["groups"][0]["variance_cents"] += 1
    with pytest.raises(ValueError, match="variance"):
        validate_result(result, data, "budget")
    result = execute_tool("budget", data)
    result.metrics["total_budget_cents"] += 1
    with pytest.raises(ValueError, match="Total budget"):
        validate_result(result, data, "budget")


def test_tool_failure_is_explicit():
    frame, _ = generate()
    with patch("app.agents.graph.execute_tool", side_effect=ValueError("failed")):
        state = run_audit(validate(frame))
    assert state["errors"]
    assert not state["report"]["tools_run"]


def test_default_model_unavailable():
    frame, _ = generate()
    with patch("app.agents.finance_agent.requests.post", side_effect=ConnectionError):
        state = run_audit(validate(frame), mode="agent")
    assert state["mode"] == "deterministic"
    assert len(state["results"]) == 4


def test_refunds_subcents_and_all_missing():
    frame, _ = generate()
    frame = frame.iloc[20:23].copy()
    frame["amount"] = ["-10", "1.001", ""]
    data = validate(frame)
    assert data.eligible.empty
    assert len(data.issues) >= 3
    with pytest.raises(ValueError):
        validate(pd.DataFrame())
