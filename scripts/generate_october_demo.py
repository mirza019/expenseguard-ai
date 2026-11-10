"""Reproducible finance interview scenario; never reads evaluation labels."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.agents.graph import run_audit  # noqa: E402
from app.rag.datasets import DEFAULT_ROOT, write_json  # noqa: E402
from app.rag.index import PolicyIndex  # noqa: E402
from app.services.ingestion import read_upload  # noqa: E402
from app.services.planning import planning_insights  # noqa: E402
from app.services.reporting import pdf_report  # noqa: E402
from app.services.validation import validate  # noqa: E402


def main():
    frame = read_upload(
        (DEFAULT_ROOT / "expenses/transactions.csv").read_bytes(), "transactions.csv"
    )
    index = PolicyIndex.load(ROOT / ".local/rag")
    state = run_audit(
        validate(frame),
        goal="Audit October 2025 expenses",
        policy_index=index,
        policy_root=DEFAULT_ROOT / "policies",
    )
    data = state["data"]
    metrics = state["report"]["metrics"]["budget"]
    review_rows = {row for f in state["report"]["findings"] for row in f["rows"]}
    review_rows |= {
        f["source_row"]
        for f in state["policy_findings"]
        if f["status"] not in {"within_limit", "within_exception"}
    }
    affected = data.eligible[data.eligible["source_row"].isin(review_rows)]
    from collections import Counter

    summary = {
        "period": "October 2025 (invoice date scope; policies use incurred transaction date)",
        "source_rows": len(data.cleaned),
        "currency": "EUR",
        "actual_cents": metrics["total_actual_cents"],
        "budget_cents": metrics["total_budget_cents"],
        "variance_cents": metrics["variance_cents"],
        "financial_findings": len(state["report"]["findings"]),
        "policy_status_counts": dict(Counter(f["status"] for f in state["policy_findings"])),
        "recorded_review_exposure_cents": int(affected["amount_cents"].sum()),
        "exposure_definition": "Unique affected recorded rows, including unresolved evidence. Not a loss estimate.",
        "departments": metrics["departments"],
        "scenario": planning_insights(data, 0.10),
        "historical_case": next(
            f for f in state["policy_findings"] if f["transaction_id"] == "RAG-TX-00007"
        ),
        "trace": state["trace"],
        "ai_generation": "not_run; deterministic mode does not require Ollama",
    }
    write_json(ROOT / "docs/release/OCTOBER_2025_DEMO.json", summary)
    days = data.cleaned["date"].dropna()
    report, pdf = pdf_report(data, state, days.min().date(), days.max().date())
    target = ROOT / "docs/examples/ExpenseGuard_October_2025_RAG_Audit.pdf"
    target.write_bytes(pdf)
    print(
        {
            k: v
            for k, v in summary.items()
            if k not in ["historical_case", "scenario", "trace", "departments"]
        }
    )


if __name__ == "__main__":
    main()
