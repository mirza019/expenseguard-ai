from datetime import datetime, timezone
from io import BytesIO

import pandas as pd
import pymupdf
import pytest

from app.agents.graph import run_audit
from app.reports.chart_renderer import charts
from app.reports.pdf_generator import generate_pdf
from app.reports.templates.audit_report import money
from app.services.report_validation import prepare_report
from app.services.validation import validate
from tests.fixtures.pdf_helpers import audit_fixture, policy_pdf


@pytest.fixture(scope="module")
def generated():
    data, audit, start, end = audit_fixture()
    report = prepare_report(
        data, audit, start, end, generated_at=datetime(2026, 11, 10, tzinfo=timezone.utc)
    )
    return report, generate_pdf(report)


def text_of(content):
    with pymupdf.open(stream=content, filetype="pdf") as doc:
        return "\n".join(page.get_text() for page in doc)


def test_pdf_signature_readable_sections_totals_and_counts(generated):
    report, content = generated
    assert content.startswith(b"%PDF-")
    text = text_of(content)
    for heading in [
        "Financial Expense",
        "Executive Summary",
        "Financial Performance",
        "Audit Findings",
        "Policy Compliance",
        "Investigation Summary",
        "Methodology and Limitations",
    ]:
        assert heading in text
    assert str(report.period_start) in text and str(report.period_end) in text
    assert money(report.total_actual_cents) in text
    assert money(report.variance_cents) in text
    assert "duplicates:0" in text
    assert "TX00003" in text
    assert "missing_data:" in text
    assert "compliance could not be evaluated" in text
    assert len(report.findings) == 12


def test_chart_images_from_same_series(generated):
    report, _ = generated
    images = charts(report)
    assert set(images) == {"budget", "department", "category", "monthly"}
    assert all(image.startswith(b"\x89PNG") for image in images.values())
    assert sum(row.actual_cents for row in report.departments) == report.total_actual_cents
    from PIL import Image

    for content in images.values():
        assert Image.open(BytesIO(content)).size[0] >= 800


def test_pdf_rendering_and_content_bounds(generated, tmp_path):
    _, content = generated
    with pymupdf.open(stream=content, filetype="pdf") as doc:
        assert len(doc) >= 8
        for page in doc:
            assert abs(page.rect.width - 595.276) < 1
            assert abs(page.rect.height - 841.89) < 1
            for block in page.get_text("dict")["blocks"]:
                if block["type"] == 0:
                    for line in block["lines"]:
                        x0, y0, x1, y1 = line["bbox"]
                        assert x0 >= 45, (page.number, line)
                        assert x1 <= page.rect.width - 45, (page.number, line)
                        assert 15 <= y0 < y1 <= page.rect.height - 15
                        text = "".join(s["text"] for s in line["spans"])
                        if not any(
                            token in text
                            for token in ["FinContext AI |", "Human review required |", "Page "]
                        ):
                            assert y0 >= 55 and y1 < page.rect.height - 48, (page.number, text)
            words = page.get_text("words")
            for index, word in enumerate(words):
                rect = pymupdf.Rect(word[:4])
                for other in words[index + 1 :]:
                    intersection = rect & pymupdf.Rect(other[:4])
                    assert intersection.is_empty or intersection.get_area() < 2.0, (
                        page.number,
                        word[4],
                        other[4],
                    )
            assert f"Page {page.number + 1}" in page.get_text()
        image = doc[1].get_pixmap(matrix=pymupdf.Matrix(1, 1))
        image.save(tmp_path / "layout.png")
        assert image.width > 500 and image.height > 800


def test_valid_policy_in_pdf():
    data, audit, start, end = audit_fixture()
    policy = policy_pdf("Travel expenses must not exceed EUR 100.00 per transaction.")
    report = prepare_report(data, audit, start, end, policies=(policy,))
    assert report.potential_policy_rows > 0
    text = text_of(generate_pdf(report))
    assert "Fictional Expense Policy" in text
    assert "version 1.0" in text
    assert "page 1" in text
    assert "Travel expenses must not exceed EUR 100.00" in text


def test_empty_findings_and_single_month():
    data, _, _, _ = audit_fixture()
    frame = data.original.iloc[20:28].copy()
    frame["amount"] = "100"
    frame["budget_amount"] = "1000"
    frame["department"] = "Sales"
    frame["cost_center"] = "CC1"
    frame["invoice_date"] = "2025-01-01"
    frame["category"] = "Travel"
    frame["vendor"] = [f"Vendor {i}" for i in range(len(frame))]
    clean = validate(frame.reset_index(drop=True))
    audit = run_audit(clean)
    day = clean.cleaned["date"].min().date()
    report = prepare_report(clean, audit, day, day)
    assert not report.findings
    assert set(charts(report)) == {"budget", "department", "category"}
    assert "No findings from the four checks" in text_of(generate_pdf(report))


def test_long_unicode_and_multi_page_tables():
    data, _, _, _ = audit_fixture()
    frame = pd.concat([data.original.iloc[20:21]] * 100, ignore_index=True)
    frame["transaction_id"] = [f"LONG{i}" for i in range(len(frame))]
    frame["invoice_id"] = [f"LONG-INV{i}" for i in range(len(frame))]
    frame["vendor"] = [f"Long vendor {i}" for i in range(len(frame))]
    frame["department"] = [f"Department {i:03d}" for i in range(len(frame))]
    frame["amount"] = "100"
    frame["budget_amount"] = "1"
    frame["description"] = "München — Αθήνα — Москва — 采购 <untrusted>& text " * 35
    clean = validate(frame)
    audit = run_audit(clean)
    start = clean.cleaned["date"].min().date()
    report = prepare_report(clean, audit, start, start)
    content = generate_pdf(report)
    text = text_of(content)
    assert "München" in text and "Москва" in text and "Αθήνα" in text and "采购" in text
    assert "<untrusted>" in text
    assert "Department 099" in text
    assert text.count("Department\nActual") >= 2
    with pymupdf.open(stream=content, filetype="pdf") as pdf:
        assert len(pdf) > 10
        assert pdf[-1].get_pixmap().width > 500
