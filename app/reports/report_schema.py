"""Typed report contract; monetary facts are exact cents, never model prose."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator

from app.services.policy_rag import PolicyCitation


class ReportModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, frozen=True)


class FinancialRow(ReportModel):
    label: str
    actual_cents: StrictInt = Field(ge=0)
    budget_cents: StrictInt | None = Field(default=None, ge=0)
    variance_cents: StrictInt | None = None

    @model_validator(mode="after")
    def reconcile(self):
        expected = self.actual_cents - self.budget_cents if self.budget_cents is not None else None
        if self.variance_cents != expected:
            raise ValueError("Financial row variance does not reconcile.")
        return self


class ReportFinding(ReportModel):
    finding_id: str
    tool: str
    rule: str
    severity: Literal["high", "medium"]
    rows: list[StrictInt]
    transaction_ids: list[str]
    departments: list[str]
    cost_centers: list[str]
    amount_cents: StrictInt | None = Field(default=None, ge=0)
    evidence_text: str
    descriptions: list[str]
    action: str
    explanation: str


class InvestigationNote(ReportModel):
    origin: Literal["calculated", "ai_selected_action"]
    text: str
    finding_id: str | None = None


class PolicySource(ReportModel):
    document_id: str
    title: str
    version: str
    effective_date: date
    pages: StrictInt = Field(ge=1)


class AuditPDFReport(ReportModel):
    schema_version: str = "1.0"
    generated_at: datetime
    period_start: date
    period_end: date
    analysis_mode: Literal["AI-assisted", "deterministic"]
    source_summary: str
    source_digest: str
    audit_digest: str
    source_rows: StrictInt = Field(ge=1)
    eligible_rows: StrictInt = Field(ge=0)
    excluded_rows: StrictInt = Field(ge=0)
    undated_rows: StrictInt = Field(ge=0)
    total_actual_cents: StrictInt = Field(ge=0)
    total_budget_cents: StrictInt | None = Field(default=None, ge=0)
    variance_cents: StrictInt | None = None
    variance_percent: float | None = None
    duplicate_rows: StrictInt = Field(ge=0)
    anomaly_rows: StrictInt = Field(ge=0)
    quality_issues: StrictInt = Field(ge=0)
    potential_policy_rows: StrictInt | None = Field(default=None, ge=0)
    policy_evaluations: StrictInt | None = Field(default=None, ge=0)
    status: str
    departments: list[FinancialRow]
    categories: list[FinancialRow]
    monthly: list[FinancialRow]
    cost_centers: list[FinancialRow]
    findings: list[ReportFinding]
    policy_sources: list[PolicySource]
    indexed_policies: list[dict] = Field(default_factory=list)
    policies: list[PolicyCitation]
    investigation: list[InvestigationNote]
    methodology: list[str]
    limitations: list[str]

    @model_validator(mode="after")
    def consistent_facts(self):
        if self.period_start > self.period_end:
            raise ValueError("Reporting period start must not follow its end.")
        if self.source_rows != self.eligible_rows + self.excluded_rows:
            raise ValueError("Source/eligible/excluded row counts do not reconcile.")
        for series in [self.departments, self.categories, self.monthly, self.cost_centers]:
            if sum(row.actual_cents for row in series) != self.total_actual_cents:
                raise ValueError("Chart/table series does not reconcile with total expenses.")
        variance = (
            self.total_actual_cents - self.total_budget_cents
            if self.total_budget_cents is not None
            else None
        )
        if self.variance_cents != variance:
            raise ValueError("Report variance does not reconcile.")
        percent = 100 * variance / self.total_budget_cents if self.total_budget_cents else None
        if self.variance_percent != percent:
            raise ValueError("Report percentage variance does not reconcile.")
        if len({f.finding_id for f in self.findings}) != len(self.findings):
            raise ValueError("Duplicate finding IDs.")
        if self.potential_policy_rows != (
            len(
                {c.source_row for c in self.policies if c.assessment == "potential_violation"}
                | {
                    f["source_row"]
                    for f in self.indexed_policies
                    if f["status"] == "potential_violation"
                }
            )
            if self.policy_evaluations is not None
            else None
        ):
            raise ValueError("Policy summary does not reconcile.")
        return self
