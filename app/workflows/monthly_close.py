"""Deterministic monthly financial review and variance investigation workflow."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field

from app.services.validation import ValidatedData
from app.tools.anomalies import detect_anomalies
from app.tools.budget import check_budget


class VarianceDriver(BaseModel):
    model_config = ConfigDict(extra="forbid")
    department: str
    actual_cents: int
    budget_cents: int | None
    variance_cents: int | None
    variance_percent: float | None
    observed_contributors: list[str] = Field(default_factory=list)
    interpretation: str


class MonthlyCloseResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    run_id: str
    idempotency_key: str
    workflow: str = "monthly_fp_and_a_close"
    status: str
    reporting_period: str
    started_at: datetime
    completed_at: datetime
    actual_cents: int
    budget_cents: int | None
    variance_cents: int | None
    variance_percent: float | None
    budget_complete: bool
    drivers: list[VarianceDriver]
    unusual_expense_count: int
    limitations: list[str]
    approval_status: str = "awaiting_human_review"
    trace: list[str]


def run_monthly_close(
    data: ValidatedData,
    period: str | None = None,
    context_version: str = "unapproved-built-in",
    threshold_percent: float = 10.0,
) -> MonthlyCloseResult:
    """Run bounded calculations; contributors are observations, never invented causes."""
    started = datetime.now(timezone.utc)
    available = sorted(data.eligible["month"].dropna().unique())
    if not available:
        raise ValueError("Monthly analysis requires at least one valid dated expense.")
    period = period or available[-1]
    if period not in available:
        raise ValueError("Selected reporting period is not present in the dataset.")
    scoped_clean = data.cleaned.loc[data.cleaned["month"] == period].copy()
    scoped_original = data.original.iloc[(scoped_clean["source_row"] - 2).astype(int)].copy()
    scoped_clean = scoped_clean.reset_index(drop=True)
    scoped_original = scoped_original.reset_index(drop=True)
    scoped = ValidatedData(scoped_original, scoped_clean, [], data.transformations)
    budget = check_budget(scoped).metrics
    anomalies = detect_anomalies(scoped)
    contributors = (
        scoped.eligible.groupby(["department", "category"], dropna=False)["amount_cents"]
        .sum()
        .reset_index()
    )
    drivers = []
    for row in budget["departments"]:
        variance_percent = row["variance_percent"]
        if variance_percent is not None and abs(variance_percent) < threshold_percent:
            continue
        top = (
            contributors.loc[contributors["department"] == row["department"]]
            .sort_values("amount_cents", ascending=False)
            .head(3)
        )
        observed = [
            f"{item.category}: EUR {int(item.amount_cents) / 100:,.2f}"
            for item in top.itertuples()
        ]
        interpretation = (
            "Recorded expense is above represented budget. Contributors describe arithmetic "
            "composition; the underlying business cause requires human confirmation."
            if row["variance_cents"] is not None and row["variance_cents"] > 0
            else "Recorded expense is below represented budget; the cause and completeness require human confirmation."
            if row["variance_cents"] is not None
            else "Variance cannot be calculated because budget evidence is missing or conflicting."
        )
        drivers.append(VarianceDriver(**row, observed_contributors=observed, interpretation=interpretation))
    fingerprint = pd.util.hash_pandas_object(scoped.original, index=True).values.tobytes()
    key = hashlib.sha256(
        fingerprint + period.encode() + context_version.encode() + str(threshold_percent).encode()
    ).hexdigest()
    completed = datetime.now(timezone.utc)
    return MonthlyCloseResult(
        run_id=key[:16],
        idempotency_key=key,
        status="completed",
        reporting_period=period,
        started_at=started,
        completed_at=completed,
        actual_cents=budget["total_actual_cents"],
        budget_cents=budget["total_budget_cents"],
        variance_cents=budget["variance_cents"],
        variance_percent=budget["variance_percent"],
        budget_complete=budget["budget_complete"],
        drivers=drivers,
        unusual_expense_count=len(anomalies.findings),
        limitations=[
            "Observed contributors are not confirmed operational causes.",
            "Unknown or conflicting budgets are never treated as zero.",
            "The draft remains subject to human review and approval.",
        ],
        trace=[
            "Validated source rows and reporting period",
            "Resolved deterministic budget-variance calculation",
            "Ranked material department variances",
            "Identified arithmetic category contributors",
            "Reconciled totals and prepared human-review draft",
        ],
    )
