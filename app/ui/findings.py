"""Searchable review register and transaction-level evidence inspection."""

import pandas as pd
import streamlit as st

from app.services.validation import ValidatedData


def findings_panel(data: ValidatedData, audit: dict | None) -> None:
    st.subheader("Audit Findings")
    if not audit:
        st.info("Run a full audit to build the evidence register.")
        return
    rows = []
    for f in audit["report"]["findings"]:
        affected = data.cleaned[data.cleaned["source_row"].isin(f["rows"])]
        rows.append(
            {
                "finding_id": f["finding_id"],
                "type": f["tool"],
                "severity": f["severity"],
                "department": ", ".join(sorted(set(affected["department"]))),
                "amount_eur": int(affected.loc[affected["eligible"], "amount_cents"].sum()) / 100,
                "transactions": ", ".join(f["transaction_ids"]),
                "status": "Verified data issue"
                if f["tool"] == "missing_data"
                else "Potential duplicate"
                if f["tool"] == "duplicates"
                else "Needs review",
                "evidence": f["evidence"],
                "action": f["action"],
                "source_rows": f["rows"],
            }
        )
    for i, f in enumerate(audit["report"].get("indexed_policy_findings", [])):
        if f["status"] in {"within_limit", "within_exception"}:
            continue
        rows.append(
            {
                "finding_id": f"POL-{i:04d}",
                "type": "policy",
                "severity": "high" if f["status"] == "potential_violation" else "medium",
                "department": f["department"],
                "amount_eur": f["amount_cents"] / 100,
                "transactions": f["transaction_id"],
                "status": f["status"].replace("_", " ").title(),
                "evidence": f["citations"],
                "action": f["action"],
                "source_rows": [f["source_row"]],
            }
        )
    frame = pd.DataFrame(rows)
    if frame.empty:
        st.success("No flags in the executed checks; this is not an assurance of compliance.")
        return
    text = st.text_input("Search findings", "")
    severity = st.multiselect("Severity filter", ["high", "medium"], default=["high", "medium"])
    shown = frame[frame["severity"].isin(severity)]
    if text:
        shown = shown[
            shown[["finding_id", "transactions", "department", "type"]]
            .astype(str)
            .agg(" ".join, axis=1)
            .str.contains(text, case=False, regex=False)
        ]
    st.dataframe(
        shown.drop(columns=["evidence", "source_rows"]),
        hide_index=True,
        column_config={
            "amount_eur": st.column_config.NumberColumn("Affected expense (EUR)", format="%.2f")
        },
    )
    if not shown.empty:
        finding_ids = shown["finding_id"].tolist()
        chosen = st.selectbox(
            "Investigate finding", finding_ids, key="finding_investigation_v2"
        )
        if chosen not in finding_ids:
            chosen = finding_ids[0]
        row = shown.loc[shown["finding_id"] == chosen].iloc[0]
        st.write("What happened:", row["status"])
        st.write("Next action:", row["action"])
        st.json(row["evidence"], expanded=False)
        affected = data.cleaned[data.cleaned["source_row"].isin(row["source_rows"])]
        st.dataframe(affected, hide_index=True)
    flagged = data.original.iloc[
        [
            i
            for i, r in enumerate(data.cleaned["source_row"])
            if r in {r for entry in rows for r in entry["source_rows"]}
        ]
    ].copy()
    safe = flagged.astype(str).map(lambda s: "'" + s if s.startswith(("=", "+", "-", "@")) else s)
    st.download_button(
        "Export flagged transactions CSV",
        safe.to_csv(index=False),
        "flagged-transactions.csv",
        mime="text/csv",
    )
