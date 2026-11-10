"""Small, entirely fictional report fixtures."""

from datetime import date
from io import BytesIO

from reportlab.pdfgen.canvas import Canvas

from app.agents.graph import run_audit
from app.services.policy_rag import extract_policy
from app.services.validation import validate
from scripts.generate_data import generate


def audit_fixture(count=100):
    frame, _ = generate()
    data = validate(frame.iloc[:count].copy())
    audit = run_audit(data)
    dates = data.cleaned["date"].dropna()
    return data, audit, dates.min().date(), dates.max().date()


def policy_pdf(
    text="Travel expenses must not exceed EUR 500.00 per transaction.",
    version="1.0",
    effective=date(2025, 1, 1),
    title="Fictional Expense Policy",
):
    output = BytesIO()
    canvas = Canvas(output)
    canvas.drawString(50, 790, "1. Travel expense limits")
    y = 765
    for line in text.splitlines():
        canvas.drawString(50, y, line)
        y -= 18
    canvas.save()
    return extract_policy(output.getvalue(), title, version, effective)
