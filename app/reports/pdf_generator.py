"""Deterministic PDF rendering from an already reconciled typed report."""

from io import BytesIO
from threading import RLock

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate

from app.reports.chart_renderer import charts
from app.reports.report_schema import AuditPDFReport
from app.reports.templates.audit_report import page_chrome, register_fonts, story

_RENDER_LOCK = RLock()


def generate_pdf(report: AuditPDFReport) -> bytes:
    """Revalidate structure and invariants before creating a paginated in-memory PDF."""
    report = AuditPDFReport.model_validate(report.model_dump())
    with _RENDER_LOCK:
        register_fonts()
        output = BytesIO()
        document = SimpleDocTemplate(
            output,
            pagesize=A4,
            leftMargin=18 * mm,
            rightMargin=18 * mm,
            topMargin=23 * mm,
            bottomMargin=21 * mm,
            title="Financial Expense Audit Report",
            author="FinContext AI",
            subject=f"{report.period_start} to {report.period_end}; {report.analysis_mode}",
        )
        document.build(
            story(report, charts(report)), onFirstPage=page_chrome, onLaterPages=page_chrome
        )
        return output.getvalue()
