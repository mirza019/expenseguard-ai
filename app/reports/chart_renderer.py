"""Headless static charts from exactly the report's tabulated series."""

from io import BytesIO
from threading import RLock

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from app.reports.report_schema import AuditPDFReport, FinancialRow

_LOCK = RLock()


def render_chart(rows: list[FinancialRow], title: str, budget: bool = False) -> bytes:
    """Use Agg without browser/Kaleido; no external services or GUI required."""
    with _LOCK:
        fig = Figure(figsize=(7.1, 3.6), dpi=130, layout="constrained")
        FigureCanvasAgg(fig)
        axes = fig.add_subplot()
        # Chart labels shortened only visually; complete values appear in the accompanying table.
        chosen = rows[:12]
        labels = [r.label[:28] + ("…" if len(r.label) > 28 else "") for r in chosen]
        x = list(range(len(chosen)))
        axes.bar(
            x,
            [r.actual_cents / 100 for r in chosen],
            width=0.38 if budget else 0.65,
            color="#167D61",
            label="Actual",
        )
        if budget:
            known = [
                (index, row) for index, row in enumerate(chosen) if row.budget_cents is not None
            ]
            axes.bar(
                [index + 0.4 for index, _ in known],
                [row.budget_cents / 100 for _, row in known],
                width=0.38,
                color="#AACBB7",
                label="Known budget",
            )
            axes.legend(frameon=False, fontsize=8)
        axes.set_xticks(x, labels, rotation=25, ha="right", fontsize=8)
        axes.set_ylabel("EUR", fontsize=9)
        axes.set_title(title, fontsize=11, loc="left", pad=14)
        axes.spines[["top", "right"]].set_visible(False)
        axes.grid(axis="y", alpha=0.15)
        axes.set_axisbelow(True)
        if not chosen:
            axes.text(0.5, 0.5, "No eligible values", transform=axes.transAxes, ha="center")
        out = BytesIO()
        fig.savefig(out, format="png", facecolor="white")
        fig.clear()
        return out.getvalue()


def charts(report: AuditPDFReport) -> dict[str, bytes]:
    """Shared series guarantee chart values and report tables come from the same facts."""
    return {
        "budget": render_chart(report.departments, "Department budget versus actual", True),
        "department": render_chart(report.departments, "Expenses by department"),
        "category": render_chart(report.categories, "Expenses by category"),
        **(
            {"monthly": render_chart(report.monthly, "Monthly spending trend")}
            if len(report.monthly) >= 2
            else {}
        ),
    }
