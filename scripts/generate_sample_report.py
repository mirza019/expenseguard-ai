"""Generate small, reproducible PDF examples from exclusively fictional records/policies."""

import sys
from datetime import date, datetime, timezone
from io import BytesIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from reportlab.pdfgen.canvas import Canvas  # noqa: E402

from app.agents.graph import run_audit  # noqa: E402
from app.reports.pdf_generator import generate_pdf  # noqa: E402
from app.services.policy_rag import extract_policy  # noqa: E402
from app.services.report_validation import prepare_report  # noqa: E402
from app.services.validation import validate  # noqa: E402
from scripts.generate_data import generate  # noqa: E402


def main() -> None:
    target = ROOT / "docs" / "examples"
    target.mkdir(parents=True, exist_ok=True)
    source, _ = generate(1200, 42)
    data = validate(source.iloc[:100])
    output = BytesIO()
    canvas = Canvas(output, invariant=1)
    canvas.drawString(50, 790, "Fictional Expense Policy - version 1.0")
    canvas.drawString(50, 765, "1. Travel expense limits")
    canvas.drawString(50, 740, "Travel expenses must not exceed EUR 500.00 per transaction.")
    canvas.drawString(50, 715, "Exceptions and approvals require human review.")
    canvas.save()
    policy = extract_policy(output.getvalue(), "Fictional Expense Policy", "1.0", date(2025, 1, 1))
    (target / "fictional_expense_policy.pdf").write_bytes(policy.source)
    audit = run_audit(data)
    days = data.cleaned["date"].dropna()
    report = prepare_report(
        data,
        audit,
        days.min().date(),
        days.max().date(),
        policies=(policy,),
        generated_at=datetime(2026, 11, 10, tzinfo=timezone.utc),
    )
    (target / "ExpenseGuard_Synthetic_Audit_Report.pdf").write_bytes(generate_pdf(report))
    print(
        f"Example report generated: {len(report.findings)} financial findings; "
        f"{report.potential_policy_rows} potential policy-exception rows. No AI or private data."
    )


if __name__ == "__main__":
    main()
