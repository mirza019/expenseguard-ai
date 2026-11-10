"""Reconcile report inputs to deterministic tools and retained source evidence."""

import hashlib
import json
from datetime import date, datetime, timezone
from decimal import Decimal

import pandas as pd

from app.agents.state import ACTIONS
from app.database.duckdb_service import summarize
from app.reports.report_schema import (
    AuditPDFReport,
    FinancialRow,
    InvestigationNote,
    PolicySource,
    ReportFinding,
)
from app.services.analytics import TOOLS, execute_tool
from app.services.policy_rag import PolicyDocument, policy_evidence, verify_citation
from app.services.reporting import build_report, json_report
from app.services.validation import ValidatedData, validate


class ReportValidationError(ValueError):
    """User-actionable failure; do not generate misleading PDFs."""


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def report_key(
    data: ValidatedData,
    audit: dict,
    start: date,
    end: date,
    include_ai: bool,
    policies: tuple[PolicyDocument, ...] = (),
) -> str:
    """Fingerprint full source, audit, policy metadata and presentation options."""
    metadata = [
        (
            p.document_id,
            hashlib.sha256(p.source).hexdigest(),
            p.title,
            p.version,
            p.effective_date.isoformat(),
        )
        for p in policies
    ]
    return digest(
        data.original.to_json(date_format="iso")
        + data.cleaned.to_json(date_format="iso")
        + json_report(audit["report"])
        + json.dumps(
            {
                name: result.model_dump(mode="json")
                for name, result in audit.get("results", {}).items()
            },
            sort_keys=True,
            allow_nan=False,
        )
        + str(start)
        + str(end)
        + str(include_ai)
        + json.dumps(metadata)
    )


def select_period(data: ValidatedData, start: date, end: date) -> ValidatedData:
    """Keep stable original row references. Undated rows are retained only for full coverage."""
    if start > end:
        raise ReportValidationError("Reporting period start must not follow its end.")
    dates = data.cleaned["date"].dropna()
    if dates.empty:
        raise ReportValidationError("No dated transactions are available for a reporting period.")
    low, high = dates.min().date(), dates.max().date()
    if start < low or end > high:
        raise ReportValidationError("Select a period within the source transaction date range.")
    mask = data.cleaned["date"].between(pd.Timestamp(start), pd.Timestamp(end))
    if (start, end) == (low, high):
        mask |= data.cleaned["date"].isna()
    if not mask.any():
        raise ReportValidationError("The selected period contains no transactions.")
    original = data.original.iloc[mask.to_numpy()].copy()
    fresh = validate(original.reset_index(drop=True))
    mapping = dict(zip(fresh.cleaned["source_row"], data.cleaned.loc[mask, "source_row"]))
    fresh.cleaned["source_row"] = fresh.cleaned["source_row"].map(mapping)
    issues = [
        finding.model_copy(update={"rows": [int(mapping[row]) for row in finding.rows]})
        for finding in fresh.issues
    ]
    return ValidatedData(
        original,
        fresh.cleaned,
        issues,
        [
            *data.transformations,
            f"Report scope {start} to {end}; original source-row references retained. "
            "Undated records are retained only for a full-source reporting period.",
        ],
    )


def prepare_report(
    data: ValidatedData,
    audit: dict,
    start: date,
    end: date,
    include_ai: bool = False,
    policies: tuple[PolicyDocument, ...] = (),
    generated_at: datetime | None = None,
) -> AuditPDFReport:
    """Fail closed on partial, stale, altered or unverified audit snapshots."""
    if start > end or data.cleaned.empty:
        raise ReportValidationError("Use a valid period with at least one source transaction.")
    dates = data.cleaned["date"].dropna()
    if dates.empty or dates.min().date() < start or dates.max().date() > end:
        raise ReportValidationError("Reporting period does not cover the audited transactions.")
    report = audit.get("report", {})
    if set(report.get("tools_run", [])) != set(TOOLS) or set(audit.get("results", {})) != set(
        TOOLS
    ):
        raise ReportValidationError("Run all four audit checks before generating the PDF.")
    canonical = {name: execute_tool(name, data) for name in TOOLS}
    for name, result in canonical.items():
        supplied = audit["results"][name]
        if supplied.model_dump() != result.model_dump():
            raise ReportValidationError(
                "Audit tool results are stale or altered. Run the audit again."
            )
    all_ids = {
        f"{name}:{i}" for name, result in canonical.items() for i in range(len(result.findings))
    }
    recommendations = report.get("recommendations", [])
    if any(
        set(r) != {"finding_id", "action"}
        or r["finding_id"] not in all_ids
        or r["action"] not in ACTIONS.values()
        for r in recommendations
    ):
        raise ReportValidationError(
            "AI recommendation lacks verified evidence or an approved action."
        )
    mode = report.get("mode")
    if mode not in {"agent", "deterministic"}:
        raise ReportValidationError("Unknown audit mode.")
    expected = build_report(data, canonical, mode, audit.get("errors", []), recommendations)
    if audit.get("policy_index") is not None:
        from app.rag.compliance import evaluate_compliance, verify_index_citations

        verified_policies = evaluate_compliance(data, audit["policy_index"])
        if audit.get("policy_root") is None:
            raise ReportValidationError(
                "Policy source directory is required for indexed citations."
            )
        verify_index_citations(verified_policies, audit["policy_index"], audit["policy_root"])
        expected["indexed_policy_findings"] = verified_policies
    try:
        if json_report(expected) != json_report(report):
            raise ReportValidationError(
                "Audit summary does not reconcile with its underlying results."
            )
    except (TypeError, ValueError) as exc:
        raise ReportValidationError(
            "Audit contains invalid values or unreconciled findings."
        ) from exc
    metrics = canonical["budget"].metrics
    financial = {}
    for dimension in ["department", "category", "monthly"]:
        frame = summarize(data, dimension)
        label = "month" if dimension == "monthly" else dimension
        financial[dimension] = [
            FinancialRow(label=str(row[label]), actual_cents=int(row["amount_cents"]))
            for _, row in frame.iterrows()
        ]
    departments = [
        FinancialRow(
            label=r["department"],
            actual_cents=r["actual_cents"],
            budget_cents=r["budget_cents"],
            variance_cents=r["variance_cents"],
        )
        for r in metrics["departments"]
    ]
    by_department = {row.label: row.actual_cents for row in financial["department"]}
    if any(row.actual_cents != by_department.get(row.label, 0) for row in departments):
        raise ReportValidationError("Department totals do not reconcile with transaction SQL.")
    centers = [
        FinancialRow(
            label=r["cost_center"],
            actual_cents=r["actual_cents"],
            budget_cents=r["budget_cents"],
            variance_cents=r["variance_cents"],
        )
        for r in metrics["cost_centers"]
    ]
    findings = []
    for finding in report["findings"]:
        affected = data.cleaned[data.cleaned["source_row"].isin(finding["rows"])]
        eligible = affected[affected["eligible"]]
        findings.append(
            ReportFinding(
                **{
                    key: finding[key]
                    for key in [
                        "finding_id",
                        "tool",
                        "rule",
                        "severity",
                        "rows",
                        "transaction_ids",
                        "action",
                        "explanation",
                    ]
                },
                departments=sorted(set(affected["department"]) - {""}),
                cost_centers=sorted(set(affected["cost_center"]) - {""}),
                amount_cents=int(eligible["amount_cents"].sum()) if len(eligible) else None,
                evidence_text=json.dumps(finding["evidence"], ensure_ascii=False, allow_nan=False),
                descriptions=affected["description"].drop_duplicates().tolist(),
            )
        )
    citations, evaluations = policy_evidence(data, policies)
    for citation in citations:
        verify_citation(citation, data, policies)
    indexed = expected.get("indexed_policy_findings", [])
    indexed_comparisons = sum(
        1 for f in indexed for c in f["citations"] if c["section_id"] in {"2.1", "2.2"}
    )
    if indexed_comparisons:
        evaluations = (evaluations or 0) + indexed_comparisons
    notes = [
        InvestigationNote(
            origin="calculated",
            text=f"{len(findings)} verified review findings; {report['excluded_rows']} source rows excluded "
            "from financial calculations. Flags require investigation, not automatic payment decisions.",
        )
    ]
    if metrics["variance_cents"] is not None:
        notes.append(
            InvestigationNote(
                origin="calculated",
                text="The expense-minus-budget variance is calculated from represented monthly allocations. "
                "Review the unfavorable cost centers listed in Financial Performance; "
                "the dataset alone does not establish causal explanations.",
            )
        )
    if departments:
        largest = max(departments, key=lambda row: row.actual_cents)
        notes.append(
            InvestigationNote(
                origin="calculated",
                text=f"Largest recorded department expense: {largest.label}, "
                f"EUR {Decimal(largest.actual_cents) / 100:,.2f}. "
                "This is a spending concentration, not evidence of its underlying cause.",
            )
        )
    unfavorable = [
        row for row in centers if row.variance_cents is not None and row.variance_cents > 0
    ]
    if unfavorable:
        largest = max(unfavorable, key=lambda row: row.variance_cents)
        notes.append(
            InvestigationNote(
                origin="calculated",
                text=f"Largest unfavorable cost-center variance: {largest.label}, "
                f"EUR {Decimal(largest.variance_cents) / 100:,.2f} above its represented allocation. "
                "Review invoice scope, approvals and allocation ownership before attributing a cause.",
            )
        )
    use_ai = include_ai and mode == "agent" and bool(recommendations)
    if use_ai:
        notes.extend(
            InvestigationNote(
                origin="ai_selected_action", text=r["action"], finding_id=r["finding_id"]
            )
            for r in recommendations
        )
    else:
        notes.append(
            InvestigationNote(
                origin="calculated",
                text="Deterministic summary: prioritize high-severity findings, missing approvals, "
                "budget conflicts and supporting invoice checks. No live AI explanation was used.",
            )
        )
    duplicate_rows = {r for f in findings if f.tool == "duplicates" for r in f.rows}
    anomaly_rows = {r for f in findings if f.tool == "anomalies" for r in f.rows}
    return AuditPDFReport(
        generated_at=generated_at or datetime.now(timezone.utc),
        period_start=start,
        period_end=end,
        analysis_mode="AI-assisted" if use_ai else "deterministic",
        source_summary="Validated CSV/XLSX transaction export; source rows retained in session.",
        source_digest=digest(data.original.to_json(date_format="iso")),
        audit_digest=digest(json_report(report)),
        source_rows=len(data.cleaned),
        eligible_rows=len(data.eligible),
        excluded_rows=report["excluded_rows"],
        undated_rows=int(data.cleaned["date"].isna().sum()),
        total_actual_cents=metrics["total_actual_cents"],
        total_budget_cents=metrics["total_budget_cents"],
        variance_cents=metrics["variance_cents"],
        variance_percent=metrics["variance_percent"],
        duplicate_rows=len(duplicate_rows),
        anomaly_rows=len(anomaly_rows),
        quality_issues=canonical["missing_data"].metrics["issue_count"],
        potential_policy_rows=len(
            {c.source_row for c in citations if c.assessment == "potential_violation"}
            | {f["source_row"] for f in indexed if f["status"] == "potential_violation"}
        )
        if evaluations is not None
        else None,
        policy_evaluations=evaluations,
        status="Review required"
        if findings or any(c.assessment == "potential_violation" for c in citations)
        else "No flags in the executed checks",
        departments=departments,
        categories=financial["category"],
        monthly=financial["monthly"],
        cost_centers=centers,
        findings=findings,
        policy_sources=[
            PolicySource(
                document_id=p.document_id,
                title=p.title,
                version=p.version,
                effective_date=p.effective_date,
                pages=p.page_count,
            )
            for p in policies
        ],
        policies=citations,
        indexed_policies=expected.get("indexed_policy_findings", []),
        investigation=notes,
        methodology=[
            *data.transformations,
            "Duplicates: invoice/vendor/exact cents/date; possible matches within three days.",
            "Outliers: category Q3 + 1.5 × IQR, minimum eight eligible observations; not fraud proof.",
            "Variance = actual − budget; positive is unfavorable. Percent undefined for zero/unknown budget.",
            "Budgets are counted once per month/department/cost center; unknown/conflicting groups "
            "withhold overall variance. All payment statuses and potential duplicates remain in actuals.",
            "Policy PDFs: PyMuPDF extraction; same-page/section chunks, lexical retrieval, exact "
            "quotes and retained-byte hashes. Title/version/effective date are uploader-declared.",
            "Only exact supported category-limit sentences are automatically evaluated; "
            "other policy language and exceptions require human review.",
        ],
        limitations=[
            *report["limitations"],
            *report["errors"],
            "This report supports human review and is not a certified financial audit.",
            "Financial amounts attached to findings are affected recorded expenses, not proven losses; "
            "overlapping findings must not be summed.",
            "Undated records cannot be assigned to a narrower reporting period.",
            "No applicable machine-evaluable policy: compliance could not be evaluated."
            if evaluations is None
            else "Policy checks are limited to supported retrieved rules; "
            "they are not an exhaustive compliance assessment.",
        ],
    )
