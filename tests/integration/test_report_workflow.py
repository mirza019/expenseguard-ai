from pathlib import Path
from unittest.mock import MagicMock

import pymupdf
from streamlit.testing.v1 import AppTest

from app.agents.graph import run_audit
from app.agents.state import Decision
from app.config import Settings
from app.services.ingestion import read_upload
from app.services.model_manager import ModelStatus
from app.services.reporting import pdf_report
from app.services.validation import validate
from tests.fixtures.pdf_helpers import audit_fixture


def test_csv_to_audit_to_pdf():
    source, _, _, _ = audit_fixture()
    data = validate(read_upload(source.original.to_csv(index=False).encode(), "report.csv"))
    audit = run_audit(data)
    days = data.cleaned["date"].dropna()
    verified, pdf = pdf_report(data, audit, days.min().date(), days.max().date(), include_ai=True)
    assert verified.analysis_mode == "deterministic"
    assert verified.total_actual_cents == audit["report"]["total_actual_cents"]
    with pymupdf.open(stream=pdf, filetype="pdf") as doc:
        assert len(doc) > 1


def test_agent_optional_report_action_and_early_request_rejected():
    data, _, _, _ = audit_fixture()

    def planner(context):
        if context["remaining_tools"]:
            return Decision(tool=context["remaining_tools"][0])
        return Decision(tool="generate_report")

    state = run_audit(data, mode="agent", planner=planner)
    assert state["pdf_bytes"].startswith(b"%PDF-")
    assert not state.get("pdf_error")
    assert state["calls"] == 4
    assert "Validated and generated PDF report" in state["trace"]
    state = run_audit(
        data,
        mode="agent",
        planner=lambda _: Decision(tool="generate_report"),
        config=Settings(max_retries=0),
    )
    assert state["mode"] == "deterministic"
    assert not state.get("pdf_bytes")


def test_report_failure_is_not_issued(monkeypatch):
    data, _, _, _ = audit_fixture()
    monkeypatch.setattr("app.services.reporting.pdf_report", MagicMock(side_effect=ValueError))
    state = run_audit(data, generate_pdf=True)
    assert state.get("pdf_error")
    assert not state.get("pdf_bytes")


def test_streamlit_generation_download_and_no_rerun_render(monkeypatch):
    monkeypatch.setattr(
        "app.ui.model_setup.get_status",
        lambda _: ModelStatus("unavailable", False, Settings().ollama_model, "Ollama Unavailable"),
    )
    app = AppTest.from_file(
        Path(__file__).resolve().parents[2] / "app/main.py", default_timeout=90
    ).run()
    next(x for x in app.radio if x.label == "Workspace").set_value("Data & Context").run()
    next(b for b in app.button if b.label == "Try fictional sample").click().run()
    next(x for x in app.radio if x.label == "Workspace").set_value("Agent Workflows").run()
    next(b for b in app.button if b.label == "Run complete deterministic audit").click().run()
    assert not app.exception
    next(x for x in app.radio if x.label == "Workspace").set_value("Reports & Governance").run()
    next(b for b in app.button if b.label == "Generate PDF Audit Report").click().run()
    assert not app.exception
    artifact = app.session_state["pdf_artifact"]
    assert artifact["bytes"].startswith(b"%PDF-")
    downloads = app.get("download_button")
    assert any("Download PDF Audit Report" == item.proto.label for item in downloads)
    first = artifact["bytes"]
    blocked = MagicMock(side_effect=AssertionError("Unnecessary rerender"))
    monkeypatch.setattr("app.ui.report_panel.pdf_report", blocked)
    app.run()
    assert not app.exception
    assert app.session_state["pdf_artifact"]["bytes"] == first
    blocked.assert_not_called()
    next(
        c for c in app.checkbox if c.label == "Include verified AI-selected investigation actions"
    ).check().run()
    assert "pdf_artifact" not in app.session_state


def test_selected_period_audit_is_displayed_and_reused_across_options(monkeypatch):
    from datetime import date

    monkeypatch.setattr(
        "app.ui.model_setup.get_status",
        lambda _: ModelStatus("unavailable", False, Settings().ollama_model, "Ollama Unavailable"),
    )
    app = AppTest.from_file(
        Path(__file__).resolve().parents[2] / "app/main.py", default_timeout=90
    ).run()
    next(x for x in app.radio if x.label == "Workspace").set_value("Data & Context").run()
    next(b for b in app.button if b.label == "Try fictional sample").click().run()
    next(x for x in app.radio if x.label == "Workspace").set_value("Agent Workflows").run()
    next(b for b in app.button if b.label == "Run complete deterministic audit").click().run()
    next(x for x in app.radio if x.label == "Workspace").set_value("Reports & Governance").run()
    next(w for w in app.date_input if w.label == "Reporting period end").set_value(
        date(2025, 1, 28)
    ).run()
    next(b for b in app.button if b.label == "Prepare selected-period audit").click().run()
    assert not app.exception
    scoped = app.session_state["pdf_scoped_audit"]
    assert set(scoped["data"].eligible["month"]) == {"2025-01"}
    next(
        c for c in app.checkbox if c.label == "Include verified AI-selected investigation actions"
    ).check().run()
    assert app.session_state["pdf_scoped_audit"]["key"] == scoped["key"]
    next(b for b in app.button if b.label == "Generate PDF Audit Report").click().run()
    assert not app.exception
    assert (
        app.session_state["pdf_artifact"]["report"].total_actual_cents
        == scoped["audit"]["report"]["total_actual_cents"]
    )
