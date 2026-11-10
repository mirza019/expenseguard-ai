"""Deterministic, scope-aware controls over actual PDF-derived limits and approval conditions."""

import re
from pathlib import Path

from app.rag.index import PolicyIndex, applicable
from app.services.validation import ValidatedData


def extract_rules(index: PolicyIndex) -> list[dict]:
    rules = []
    seen = set()
    for c in index.chunks:
        if c.reference in seen or c.section_id not in {"2.1", "2.2"}:
            continue
        seen.add(c.reference)
        text = " ".join(c.parent_text.split())
        match = re.search(
            r"(?:limited to EUR|have a EUR) (\d+(?:\.\d+)?) (per day|per transaction)", text
        )
        if not match:
            continue
        limit = round(float(match.group(1)) * 100)
        exception = next(
            (x for x in index.chunks if x.document_id == c.document_id and x.section_id == "3.1"),
            None,
        )
        exception_match = (
            re.search(r"use a EUR (\d+(?:\.\d+)?) limit", " ".join(exception.parent_text.split()))
            if exception
            else None
        )
        rules.append(
            {
                "chunk": c,
                "limit_cents": limit,
                "unit": match.group(2),
                "approval": c.approval_requirements,
                "exception": exception,
                "exception_limit_cents": round(float(exception_match.group(1)) * 100)
                if exception_match
                else None,
            }
        )
    return rules


def evaluate_compliance(data: ValidatedData, index: PolicyIndex) -> list[dict]:
    rules = extract_rules(index)
    output = []
    frame = data.eligible
    daily = {}
    for _, row in frame.iterrows():
        import pandas as pd

        policy_day = row.get("policy_date", row["date"])
        if pd.isna(policy_day):
            continue
        key = (row.get("employee_id", ""), policy_day.date().isoformat(), row["category"])
        daily[key] = daily.get(key, 0) + int(row["amount_cents"])
    for _, row in frame.iterrows():
        policy_day = row.get("policy_date", row["date"])
        if pd.isna(policy_day):
            output.append(
                {
                    "source_row": int(row["source_row"]),
                    "transaction_id": row["transaction_id"],
                    "department": row["department"],
                    "cost_center": row["cost_center"],
                    "amount_cents": int(row["amount_cents"]),
                    "date": "UNKNOWN",
                    "country": row.get("country", "UNKNOWN"),
                    "category": row["category"],
                    "citations": [],
                    "threshold_cents": None,
                    "status": "evidence_incomplete",
                    "reason": "Incurred transaction date is missing or invalid.",
                    "action": "Supply the incurred date before applying a policy version.",
                }
            )
            continue
        day = policy_day.date().isoformat()
        country = row.get("country", "UNKNOWN")
        found = [
            r
            for r in rules
            if r["chunk"].category.casefold() == row["category"].casefold()
            and applicable(r["chunk"], day, country, row["department"])
        ]
        # Specific departmental scope overrides generic scope within each document only.
        grouped = {}
        for rule in found:
            c = rule["chunk"]
            key = c.document_id
            if key not in grouped or c.department == row["department"]:
                grouped[key] = rule
        found = list(grouped.values())
        base = {
            "source_row": int(row["source_row"]),
            "transaction_id": row["transaction_id"],
            "department": row["department"],
            "cost_center": row["cost_center"],
            "amount_cents": int(row["amount_cents"]),
            "date": day,
            "country": country,
            "category": row["category"],
            "citations": [],
            "threshold_cents": None,
        }
        if not found:
            output.append(
                dict(
                    base,
                    status="evidence_incomplete",
                    reason="No applicable documented category rule.",
                    action="Supply an applicable policy and missing scope evidence.",
                )
            )
            continue
        limits = {(r["limit_cents"], r["unit"]) for r in found}
        citations = [
            {
                "document_id": r["chunk"].document_id,
                "document_hash": r["chunk"].document_hash,
                "title": r["chunk"].title,
                "version": r["chunk"].version,
                "section_id": r["chunk"].section_id,
                "page": r["chunk"].page_start,
                "page_end": r["chunk"].page_end,
                "quote": r["chunk"].parent_text,
                "content_hash": r["chunk"].content_hash,
                "reference": r["chunk"].reference,
            }
            for r in found
        ]
        base["citations"] = citations
        if len(limits) > 1:
            output.append(
                dict(
                    base,
                    status="human_review_required",
                    reason="Applicable policies have conflicting limits.",
                    action="Resolve policy precedence with the policy owner; do not choose a larger limit.",
                )
            )
            continue
        rule = found[0]
        limit = rule["limit_cents"]
        observed = int(row["amount_cents"])
        if rule["unit"] == "per day":
            if not row.get("employee_id"):
                output.append(
                    dict(
                        base,
                        status="evidence_incomplete",
                        reason="Daily limit requires employee identity.",
                        action="Supply employee/day evidence.",
                    )
                )
                continue
            observed = daily[(row["employee_id"], day, row["category"])]
        base.update(threshold_cents=limit, observed_cents=observed, unit=rule["unit"])
        exception = (
            row["department"] == "Engineering"
            and country == "DE"
            and row.get("emergency") == "yes"
            and row.get("exception_evidence") == "yes"
            and row.get("approver_role") == "director"
            and rule["exception_limit_cents"] is not None
        )
        if exception:
            limit = rule["exception_limit_cents"]
            base["threshold_cents"] = limit
            c = rule["exception"]
            base["citations"].append(
                {
                    "document_id": c.document_id,
                    "document_hash": c.document_hash,
                    "title": c.title,
                    "version": c.version,
                    "section_id": c.section_id,
                    "page": c.page_start,
                    "page_end": c.page_end,
                    "quote": c.parent_text,
                    "content_hash": c.content_hash,
                    "reference": c.reference,
                }
            )
        role = row.get("approver_role", "UNKNOWN")
        approval = row.get("approval_status", "UNKNOWN")
        receipt = row.get("receipt_available", "UNKNOWN")
        if (
            row["department"] == "Engineering"
            and country == "DE"
            and row.get("emergency") == "yes"
            and observed > rule["limit_cents"]
            and not exception
        ):
            status, reason = (
                "evidence_incomplete",
                "A higher emergency limit was claimed without complete director/exception evidence.",
            )
        elif (
            rule["approval"] == "UNKNOWN"
            or role not in {"manager", "director"}
            or any(v in {"UNKNOWN", "", None} for v in [role, approval, receipt])
        ):
            status, reason = "evidence_incomplete", "Receipt or approval evidence is incomplete."
        elif receipt != "yes" or approval != "approved":
            status, reason = "potential_violation", "Required receipt or approval is absent."
        elif rule["approval"] == "director" and role != "director":
            status, reason = (
                "potential_violation",
                "Approval authority is below the documented requirement.",
            )
        elif observed > limit:
            status, reason = (
                "potential_violation",
                "Observed amount exceeds the applicable documented limit.",
            )
        else:
            status, reason = (
                ("within_exception", "Documented emergency exception applied.")
                if exception
                else (
                    "within_limit",
                    "Within the supported amount/receipt/approval controls; not a complete compliance verdict.",
                )
            )
        output.append(
            dict(
                base,
                status=status,
                reason=reason,
                action="Review invoice, scope, approvals and applicable exceptions before any payment decision.",
            )
        )
    return output


def verify_index_citations(findings: list[dict], index: PolicyIndex, policies: Path) -> None:
    """Verify provenance against real policy bytes and extracted section/page snapshots."""
    import hashlib

    for finding in findings:
        for citation in finding["citations"]:
            chunk = next((c for c in index.chunks if c.reference == citation["reference"]), None)
            if (
                chunk is None
                or citation["quote"] != chunk.parent_text
                or citation["page"] != chunk.page_start
            ):
                raise ValueError("Unverified indexed policy citation.")
            path = Path(policies) / (chunk.document_id + ".pdf")
            if (
                not path.is_file()
                or hashlib.sha256(path.read_bytes()).hexdigest() != chunk.document_hash
            ):
                raise ValueError("Policy source changed; rebuild the index before citing it.")
