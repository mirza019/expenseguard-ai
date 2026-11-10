from copy import deepcopy
from datetime import date

import pytest
from pydantic import ValidationError

from app.agents.graph import run_audit
from app.reports.report_schema import AuditPDFReport
from app.services.report_validation import (
    ReportValidationError,
    prepare_report,
    report_key,
    select_period,
)
from tests.fixtures.pdf_helpers import audit_fixture


@pytest.fixture
def source():
    return audit_fixture()


def test_reconciliation_counts_and_references(source):
    data, audit, start, end = source
    report = prepare_report(data, audit, start, end)
    metrics = audit["report"]["metrics"]["budget"]
    assert report.total_actual_cents == audit["report"]["total_actual_cents"]
    assert report.total_budget_cents == metrics["total_budget_cents"]
    assert report.variance_cents == metrics["variance_cents"]
    assert len(report.findings) == len(audit["report"]["findings"])
    assert report.duplicate_rows == 3
    assert any("TX00003" in f.transaction_ids for f in report.findings if f.tool == "anomalies")
    assert report.quality_issues > 0
    assert report.potential_policy_rows is None
    assert report.analysis_mode == "deterministic"


@pytest.mark.parametrize(
    "field,value",
    [
        ("total_actual_cents", 9),
        ("total_actual_cents", float("nan")),
        ("total_actual_cents", float("inf")),
        ("mode", "invented"),
    ],
)
def test_reject_altered_summary(source, field, value):
    data, audit, start, end = source
    bad = deepcopy(audit)
    bad["report"][field] = value
    with pytest.raises(ValueError):
        prepare_report(data, bad, start, end)


def test_reject_altered_tool_and_fabricated_reference(source):
    data, audit, start, end = source
    bad = deepcopy(audit)
    bad["results"]["budget"].metrics["total_actual_cents"] += 1
    with pytest.raises(ReportValidationError, match="stale or altered"):
        prepare_report(data, bad, start, end)
    bad = deepcopy(audit)
    bad["report"]["findings"][0]["transaction_ids"] = ["INVENTED"]
    with pytest.raises(ReportValidationError):
        prepare_report(data, bad, start, end)
    bad = deepcopy(audit)
    bad["report"]["recommendations"] = [{"finding_id": "invented", "action": "approve payment"}]
    with pytest.raises(ReportValidationError, match="recommendation"):
        prepare_report(data, bad, start, end, True)


def test_partial_and_bad_period(source):
    data, audit, start, end = source
    partial = deepcopy(audit)
    partial["results"].pop("budget")
    with pytest.raises(ReportValidationError, match="all four"):
        prepare_report(data, partial, start, end)
    with pytest.raises(ReportValidationError):
        prepare_report(data, audit, end, start)
    with pytest.raises(ReportValidationError, match="cover"):
        prepare_report(data, audit, start, date(2025, 2, 1))


def test_period_subset_keeps_source_rows(source):
    data, audit, start, end = source
    scoped = select_period(data, start, date(2025, 1, 28))
    assert scoped.cleaned["source_row"].min() == 2
    assert not scoped.cleaned["date"].isna().any()
    audit2 = run_audit(scoped)
    report = prepare_report(scoped, audit2, start, date(2025, 1, 28))
    assert report.total_actual_cents == int(scoped.eligible["amount_cents"].sum())
    assert report_key(data, audit, start, end, False) != report_key(data, audit, start, end, True)
    with pytest.raises(ReportValidationError):
        select_period(data, date(2024, 1, 1), end)
    with pytest.raises(ReportValidationError):
        select_period(data, end, start)


def test_schema_rejects_nan_bad_totals_and_chart_mismatch(source):
    data, audit, start, end = source
    report = prepare_report(data, audit, start, end)
    for key, value in [
        ("variance_percent", float("nan")),
        ("total_actual_cents", 123),
        ("source_rows", 0),
        ("period_end", date(2020, 1, 1)),
    ]:
        values = report.model_dump()
        values[key] = value
        with pytest.raises(ValidationError):
            AuditPDFReport.model_validate(values)
    values = report.model_dump()
    values["categories"][0]["actual_cents"] += 1
    with pytest.raises(ValidationError, match="series"):
        AuditPDFReport.model_validate(values)


def test_ai_actions_are_labeled_and_no_ai_fallback(source):
    from app.agents.state import Decision, Recommendation

    data, audit, start, end = source
    assert prepare_report(data, audit, start, end, include_ai=True).analysis_mode == "deterministic"

    def planner(context):
        if context["remaining_tools"]:
            return Decision(tool=context["remaining_tools"][0])
        return Decision(
            tool="finish",
            recommendations=[Recommendation(finding_id="duplicates:0", action="review_invoice")],
        )

    assisted = run_audit(data, mode="agent", planner=planner)
    report = prepare_report(data, assisted, start, end, include_ai=True)
    assert report.analysis_mode == "AI-assisted"
    assert any(
        n.origin == "ai_selected_action" and n.finding_id == "duplicates:0"
        for n in report.investigation
    )


def test_empty_source_and_missing_required_fields(source):
    from app.services.validation import ValidatedData

    data, audit, start, end = source
    empty = ValidatedData(data.original.iloc[:0], data.cleaned.iloc[:0], [], [])
    with pytest.raises(ReportValidationError):
        prepare_report(empty, audit, start, end)
    with pytest.raises(ReportValidationError):
        prepare_report(data, {}, start, end)
    values = prepare_report(data, audit, start, end).model_dump()
    del values["total_actual_cents"]
    with pytest.raises(ValidationError):
        AuditPDFReport.model_validate(values)


def test_cached_key_changes_with_tool_results_and_policy_source(source):
    from tests.fixtures.pdf_helpers import policy_pdf

    data, audit, start, end = source
    old = report_key(data, audit, start, end, False)
    changed = deepcopy(audit)
    changed["results"]["budget"].metrics["total_actual_cents"] += 1
    assert report_key(data, changed, start, end, False) != old
    assert report_key(data, audit, start, end, False, (policy_pdf(),)) != old


def test_selected_period_revalidates_cross_period_duplicate_ids():
    from app.services.validation import validate
    from scripts.generate_data import generate

    frame, _ = generate()
    frame = frame.iloc[20:22].copy().reset_index(drop=True)
    frame["transaction_id"] = "SAME-ID"
    frame["invoice_date"] = ["2025-01-01", "2025-02-01"]
    full = validate(frame)
    assert any(f.rule == "duplicate_transaction_id" for f in full.issues)
    scoped = select_period(full, date(2025, 1, 1), date(2025, 1, 1))
    assert not any(f.rule == "duplicate_transaction_id" for f in scoped.issues)
    assert scoped.cleaned["source_row"].tolist() == [2]
