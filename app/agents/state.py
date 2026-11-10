"""Explicit state and constrained model decisions."""

from typing import Literal, TypedDict

from pydantic import BaseModel, ConfigDict, Field

from app.services.validation import ToolResult, ValidatedData

ACTIONS = {
    "review_invoice": "Check the invoice and approval evidence.",
    "review_budget": "Review allocation ownership and the expense approvals.",
    "request_details": "Request missing details from the record owner.",
    "review_business_purpose": "Confirm business purpose and supporting documentation.",
}


class Recommendation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    finding_id: str
    action: Literal["review_invoice", "review_budget", "request_details", "review_business_purpose"]


class Decision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tool: Literal["duplicates", "budget", "anomalies", "missing_data", "finish", "generate_report"]
    recommendations: list[Recommendation] = Field(default_factory=list, max_length=8)


class AuditState(TypedDict, total=False):
    data: ValidatedData
    goal: str
    mode: str
    results: dict[str, ToolResult]
    pending: str
    retries: int
    calls: int
    errors: list[str]
    trace: list[str]
    recommendations: list[dict]
    done: bool
    report: dict
    pdf_requested: bool
    pdf_bytes: bytes
    pdf_error: str
    policies: tuple
