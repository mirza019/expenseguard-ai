"""White-background A4 report layout with safe, Unicode-aware flowable content."""

from decimal import Decimal
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, LongTable, PageBreak, Paragraph, Spacer, TableStyle

from app.reports.report_schema import AuditPDFReport

WINE = colors.HexColor("#167D61")
WIDTH = 174 * mm


def register_fonts() -> None:
    """Bundle licensed fonts so macOS/Linux produce the same Latin/Greek/Cyrillic layout."""
    root = Path(__file__).resolve().parents[1] / "assets" / "fonts"
    if "EG" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont("EG", str(root / "DejaVuSans.ttf")))
        pdfmetrics.registerFont(TTFont("EG-Bold", str(root / "DejaVuSans-Bold.ttf")))
        pdfmetrics.registerFontFamily(
            "EG", normal="EG", bold="EG-Bold", italic="EG", boldItalic="EG-Bold"
        )
        pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))


def safe_text(value: object) -> str:
    """Escape XML, retain supported Unicode, and visibly label unsupported glyphs."""
    text = str(value)
    text = "".join(c for c in text if c in "\n\t" or ord(c) >= 32)
    font = pdfmetrics.getFont("EG")
    output = []
    for character in text:
        code = ord(character)
        if 0x2E80 <= code <= 0x9FFF or 0xF900 <= code <= 0xFAFF:
            output.append(f'<font name="STSong-Light">{escape(character)}</font>')
        elif code not in font.face.charToGlyph and character not in "\n\t":
            output.append(f"[U+{code:04X}]")
        else:
            output.append(escape(character))
    return "".join(output).replace("\n", "<br/>")


def money(value: int | None) -> str:
    return "Not evaluable" if value is None else f"EUR {Decimal(value) / 100:,.2f}"


def story(report: AuditPDFReport, images: dict[str, bytes]) -> list:
    """Build fully flowable sections; long cells/paragraphs split rather than clip."""
    register_fonts()
    styles = getSampleStyleSheet()
    for name in ["Normal", "BodyText", "Heading1", "Heading2", "Heading3", "Title"]:
        styles[name].fontName = "EG-Bold" if name.startswith("Heading") or name == "Title" else "EG"
        styles[name].textColor = colors.HexColor("#29222A")
    styles["BodyText"].fontSize = 8
    styles["BodyText"].leading = 12
    styles["BodyText"].spaceAfter = 6
    for name in ["Heading1", "Heading2", "Heading3"]:
        styles[name].keepWithNext = True
    styles["Heading1"].fontSize = 19
    styles["Heading1"].leading = 24
    styles["Heading1"].textColor = WINE
    styles["Heading2"].fontSize = 12
    styles["Heading2"].leading = 17
    styles["Heading2"].textColor = WINE
    styles["Title"].fontSize = 28
    styles["Title"].leading = 36
    styles.add(
        ParagraphStyle(
            "Cell", fontName="EG", fontSize=7, leading=10, splitLongWords=True, spaceAfter=0
        )
    )
    styles.add(ParagraphStyle("Number", parent=styles["Cell"], alignment=TA_RIGHT))
    items = []

    def p(text: object, style: str = "BodyText") -> Paragraph:
        return Paragraph(safe_text(text), styles[style])

    def paragraphs(text: str) -> None:
        # Individual bounded flowables prevent unbreakable evidence cells.
        for offset in range(0, len(text), 700):
            items.append(p(text[offset : offset + 700]))

    def table(headers: list[str], rows: list[list], widths: list[float], numeric=()) -> None:
        values = [[p(v, "Cell") for v in headers]]
        values.extend(
            [
                [p(v, "Number" if index in numeric else "Cell") for index, v in enumerate(row)]
                for row in rows
            ]
        )
        tab = LongTable(
            values, colWidths=widths, repeatRows=1, hAlign="LEFT", splitByRow=1, splitInRow=1
        )
        tab.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EAF4EE")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LINEBELOW", (0, 0), (-1, 0), 0.7, WINE),
                    ("LINEBELOW", (0, 1), (-1, -1), 0.25, colors.HexColor("#E4DEE1")),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 7),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ]
            )
        )
        items.extend([tab, Spacer(1, 5 * mm)])

    items.extend(
        [
            Spacer(1, 24 * mm),
            p("EXPENSEGUARD AI", "Heading2"),
            p("Financial Expense\nAudit Report", "Title"),
            Spacer(1, 9 * mm),
        ]
    )
    table(
        ["REPORT INFORMATION", "DETAIL"],
        [
            ["Reporting period", f"{report.period_start} to {report.period_end}"],
            ["Generated date (UTC)", report.generated_at.isoformat(timespec="seconds")],
            ["Analysis mode", report.analysis_mode],
            ["Audit scope", "All four financial checks; EUR only"],
            ["Data source", report.source_summary],
            [
                "Data coverage",
                f"{report.source_rows} source rows; {report.eligible_rows} eligible; "
                f"{report.excluded_rows} excluded; {report.undated_rows} undated",
            ],
            ["Audit status", report.status],
        ],
        [52 * mm, 122 * mm],
    )
    items.extend(
        [
            p(
                "Confidential when populated with real records. Independent portfolio application; "
                "this report supports human review and is not a certified financial audit."
            ),
            PageBreak(),
        ]
    )
    items.append(p("Executive Summary", "Heading1"))
    summary = [
        ["Total expenses", money(report.total_actual_cents)],
        ["Total budget", money(report.total_budget_cents)],
        ["Absolute variance (actual − budget)", money(report.variance_cents)],
        [
            "Percentage variance",
            "Not evaluable"
            if report.variance_percent is None
            else f"{report.variance_percent:,.2f}%",
        ],
        ["Potentially duplicate transactions (unique source rows)", report.duplicate_rows],
        ["Statistical anomalies (unique source rows)", report.anomaly_rows],
        ["Missing/invalid data issues", report.quality_issues],
        [
            "Potential policy exceptions (unique source rows)",
            report.potential_policy_rows
            if report.potential_policy_rows is not None
            else "Not evaluated",
        ],
        ["Verified financial findings", len(report.findings)],
        ["Overall audit status", report.status],
    ]
    table(["MEASURE", "VERIFIED RESULT"], summary, [112 * mm, 62 * mm], numeric=(1,))
    items.append(
        p(
            "Amounts include potential duplicate records pending human review. "
            "An unknown budget is not zero. Finding amounts overlap and are not proven losses."
        )
    )
    items.append(p("Financial Performance", "Heading1"))
    for key, title, rows in [
        ("budget", "Budget versus actual by department", report.departments),
        ("department", "Expenses by department", report.departments),
        ("category", "Expenses by category", report.categories),
        ("monthly", "Monthly spending trends", report.monthly),
    ]:
        items.append(p(title, "Heading2"))
        if key == "monthly" and len(rows) < 2:
            items.append(p("Fewer than two months: no trend chart is presented."))
        elif key in images:
            items.append(Image(BytesIO(images[key]), width=WIDTH, height=88 * mm))
        if key == "budget":
            table(
                ["Department", "Actual", "Budget", "Variance"],
                [
                    [r.label, money(r.actual_cents), money(r.budget_cents), money(r.variance_cents)]
                    for r in rows
                ],
                [54 * mm, 40 * mm, 40 * mm, 40 * mm],
                numeric=(1, 2, 3),
            )
        else:
            table(
                ["Scope", "Actual expenses"],
                [[r.label, money(r.actual_cents)] for r in rows],
                [114 * mm, 60 * mm],
                numeric=(1,),
            )
        if len(rows) > 12:
            items.append(p("Chart shows the first 12 series; the table contains every series."))
    items.append(p("Cost centers contributing to unfavorable variance", "Heading2"))
    unfavorable = sorted(
        [r for r in report.cost_centers if r.variance_cents is not None and r.variance_cents > 0],
        key=lambda r: r.variance_cents,
        reverse=True,
    )
    if unfavorable:
        table(
            ["Cost center", "Actual", "Budget", "Unfavorable variance"],
            [
                [r.label, money(r.actual_cents), money(r.budget_cents), money(r.variance_cents)]
                for r in unfavorable
            ],
            [54 * mm, 40 * mm, 40 * mm, 40 * mm],
            numeric=(1, 2, 3),
        )
    else:
        items.append(
            p(
                "No unfavorable variance among cost centers with known budgets. Unknown "
                "budgets cannot be interpreted as favorable performance."
            )
        )
    items.extend([PageBreak(), p("Audit Findings", "Heading1")])
    if not report.findings:
        items.append(
            p("No findings from the four checks. This does not establish the absence of errors.")
        )
    for finding in report.findings:
        items.append(
            p(f"{finding.finding_id} | {finding.severity.upper()} | {finding.rule}", "Heading2")
        )
        items.append(
            p(
                f"Type: {finding.tool}. Department: {', '.join(finding.departments) or 'Unknown'}. "
                f"Cost center: {', '.join(finding.cost_centers) or 'Unknown'}."
            )
        )
        items.append(
            p("Affected recorded expense (not proven loss): " + money(finding.amount_cents))
        )
        references = list(zip(finding.rows, finding.transaction_ids))
        table(
            ["Source row", "Transaction ID"],
            [[r, tid or "(missing)"] for r, tid in references],
            [34 * mm, 140 * mm],
        )
        paragraphs("Detection rule: " + finding.explanation)
        paragraphs("Supporting evidence: " + finding.evidence_text)
        for description in finding.descriptions:
            paragraphs("Source description: " + description)
        paragraphs("Recommended investigation: " + finding.action)
    items.extend([PageBreak(), p("Policy Compliance", "Heading1")])
    if report.policy_evaluations is None:
        items.append(
            p(
                "No applicable machine-evaluable policy evidence was available. "
                "Policy compliance could not be evaluated. No compliant verdict is implied."
            )
        )
    else:
        items.append(
            p(
                f"{report.policy_evaluations} supported rule/transaction comparisons were evaluated. "
                f"{report.potential_policy_rows} unique source rows exceeded a cited limit. "
                "Applicability and exceptions require human confirmation."
            )
        )
    if report.policy_sources:
        table(
            ["Policy title", "Version", "Effective date", "Pages"],
            [[d.title, d.version, str(d.effective_date), d.pages] for d in report.policy_sources],
            [90 * mm, 27 * mm, 37 * mm, 20 * mm],
        )
        items.append(
            p(
                "Source metadata is uploader-declared; citations are checked against retained PDF bytes."
            )
        )
    for index, citation in enumerate(report.policies, 1):
        items.append(p(f"Policy evidence {index} — {citation.transaction_id}", "Heading2"))
        paragraphs(
            f"{citation.title}; version {citation.version}; effective {citation.effective_date}; "
            f"section {citation.section}; page {citation.page}; source row {citation.source_row}."
        )
        paragraphs("Verified source passage: " + citation.quote)
        paragraphs(
            "Assessment: "
            + citation.assessment
            + "; observed expense: "
            + money(citation.observed_cents)
            + "; limit: "
            + money(citation.threshold_cents)
        )
        paragraphs(citation.explanation)
        paragraphs("Document SHA-256: " + citation.document_id + "; chunk: " + citation.chunk_id)
    for finding in report.indexed_policies:
        if finding["status"] in {"within_limit", "within_exception"}:
            continue
        items.append(p("Indexed policy review — " + finding["transaction_id"], "Heading2"))
        paragraphs("Evidence status: " + finding["status"] + ". " + finding["reason"])
        paragraphs(
            "Affected expense: "
            + money(finding["amount_cents"])
            + ". Recommended action: "
            + finding["action"]
        )
        for citation in finding["citations"]:
            paragraphs(
                f"{citation['title']}; version {citation['version']}; section {citation['section_id']}; pages {citation['page']}–{citation.get('page_end', citation['page'])}. "
                + citation["quote"]
            )
    items.extend([PageBreak(), p("Investigation Summary", "Heading1")])
    items.append(
        p(
            "AI-selected priorities are explicitly labeled and cannot introduce new financial "
            "facts. Other explanations are deterministic summaries of verified results."
        )
    )
    for note in report.investigation:
        label = (
            "AI-selected investigation action"
            if note.origin == "ai_selected_action"
            else "Calculated summary"
        )
        paragraphs(f"{label}{' (' + note.finding_id + ')' if note.finding_id else ''}: {note.text}")
    items.extend([p("Methodology and Limitations", "Heading1")])
    for text in [*report.methodology, *report.limitations]:
        paragraphs("• " + text)
    paragraphs(
        "Reconciliation identifiers: source "
        + report.source_digest
        + "; audit "
        + report.audit_digest
    )
    return items


def page_chrome(canvas, doc) -> None:
    """Fixed header/footer outside the content frame on every page."""
    canvas.saveState()
    canvas.setStrokeColor(WINE)
    canvas.setLineWidth(0.7)
    canvas.line(18 * mm, 281 * mm, 192 * mm, 281 * mm)
    canvas.setFont("EG", 8)
    canvas.setFillColor(WINE)
    canvas.drawString(18 * mm, 285 * mm, "ExpenseGuard AI | Financial Expense Audit Report")
    canvas.setFillColor(colors.HexColor("#706773"))
    canvas.drawString(18 * mm, 12 * mm, "Human review required | Not a certified financial audit")
    canvas.drawRightString(192 * mm, 12 * mm, f"Page {doc.page}")
    canvas.restoreState()
