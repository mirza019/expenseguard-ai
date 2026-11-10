"""Invoice-based duplicate detection with transparent matching rules."""

from app.services.validation import Finding, ToolResult, ValidatedData


def detect_duplicates(data: ValidatedData, date_tolerance_days: int = 3) -> ToolResult:
    """Group exact invoice matches; find possible matches within a bounded date window."""
    if not 0 <= date_tolerance_days <= 31:
        raise ValueError("Date tolerance must be between 0 and 31 days.")
    frame = data.eligible.copy()
    frame["vendor_key"] = frame["vendor"].str.casefold()
    frame["invoice_key"] = frame["invoice_id"].str.casefold()
    findings = []
    exact_groups = {}
    for key, group in frame[frame["invoice_key"].ne("")].groupby(
        ["invoice_key", "vendor_key", "amount_cents", "date"], dropna=False
    ):
        if len(group) > 1:
            group_id = len(exact_groups) + 1
            for row in group["source_row"]:
                exact_groups[int(row)] = group_id
            findings.append(
                Finding(
                    rule="exact_invoice_duplicate",
                    severity="high",
                    rows=group["source_row"].astype(int).tolist(),
                    transaction_ids=group["transaction_id"].tolist(),
                    evidence={
                        "invoice_id": str(key[0]),
                        "vendor": str(key[1]),
                        "amount_cents": int(key[2]),
                        "date": str(key[3].date()),
                        "record_count": len(group),
                    },
                )
            )
    # Anchor each possible duplicate to its most recent qualifying predecessor.
    # This bounds evidence size and avoids a quadratic list of all possible pairs.
    for _, group in frame.groupby(["vendor_key", "amount_cents"]):
        previous = None
        for _, row in group.sort_values(["date", "source_row"]).iterrows():
            if previous is not None:
                distance = int((row["date"] - previous["date"]).days)
                same_exact = int(row["source_row"]) in exact_groups and exact_groups.get(
                    int(row["source_row"])
                ) == exact_groups.get(int(previous["source_row"]))
                if distance <= date_tolerance_days and not same_exact:
                    findings.append(
                        Finding(
                            rule="possible_duplicate",
                            severity="medium",
                            rows=[int(previous["source_row"]), int(row["source_row"])],
                            transaction_ids=[previous["transaction_id"], row["transaction_id"]],
                            evidence={
                                "vendor": row["vendor"],
                                "amount_cents": int(row["amount_cents"]),
                                "days_apart": distance,
                                "tolerance_days": date_tolerance_days,
                            },
                        )
                    )
            previous = row
    return ToolResult(
        tool="duplicates",
        findings=findings,
        metrics={
            "duplicate_groups": len(findings),
            "flagged_rows": len({r for f in findings for r in f.rows}),
        },
    )
