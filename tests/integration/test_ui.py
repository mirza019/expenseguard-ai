from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_sample_and_complete_audit(monkeypatch):
    from app.services.model_manager import ModelStatus

    monkeypatch.setattr(
        "app.ui.model_setup.get_status",
        lambda _: ModelStatus("unavailable", False, "qwen3:4b-q4_K_M", "Ollama Unavailable"),
    )
    app = AppTest.from_file(
        Path(__file__).resolve().parents[2] / "app/main.py", default_timeout=60
    ).run()
    assert not app.exception
    next(x for x in app.radio if x.label == "Workspace").set_value("Data & Context").run()
    next(b for b in app.button if b.label == "Try fictional sample").click().run()
    assert not app.exception
    next(x for x in app.radio if x.label == "Workspace").set_value("Dashboard").run()
    assert app.metric[0].value != "0.00"
    next(x for x in app.radio if x.label == "Workspace").set_value("Agent Workflows").run()
    next(b for b in app.button if b.label == "Run complete deterministic audit").click().run()
    assert not app.exception
    assert app.session_state["audit"]["report"]["mode"] == "deterministic"
    assert len(app.session_state["audit"]["results"]) == 4


def test_local_demo_loaders_bypass_browser_upload(monkeypatch):
    from app.services.model_manager import ModelStatus

    monkeypatch.setattr(
        "app.ui.model_setup.get_status",
        lambda _: ModelStatus("unavailable", False, "qwen3:4b-q4_K_M", "Ollama Unavailable"),
    )
    app = AppTest.from_file(
        Path(__file__).resolve().parents[2] / "app/main.py", default_timeout=90
    ).run()
    next(b for b in app.button if b.label == "Load transactions.csv").click().run()
    assert not app.exception
    assert app.session_state["data_source"]["name"] == "transactions.csv"
    next(b for b in app.button if b.label == "Load 60,000-row workbook").click().run()
    assert not app.exception
    assert app.session_state["data_source"]["rows"] == 60_000


def test_every_financial_action_after_data_load(monkeypatch):
    """Exercise every calculation button that is available after loading financial data."""
    from app.services.analytics import TOOLS
    from app.services.model_manager import ModelStatus

    monkeypatch.setattr(
        "app.ui.model_setup.get_status",
        lambda _: ModelStatus("unavailable", False, "qwen3:4b-q4_K_M", "Ollama Unavailable"),
    )
    app = AppTest.from_file(
        Path(__file__).resolve().parents[2] / "app/main.py", default_timeout=120
    ).run()
    next(b for b in app.button if b.label == "Load transactions.csv").click().run()
    next(x for x in app.radio if x.label == "Workspace").set_value("Agent Workflows").run()

    next(b for b in app.button if b.label == "Run monthly financial review").click().run()
    assert not app.exception
    assert app.session_state["monthly_close"].status == "completed"

    tool_select = next(x for x in app.selectbox if x.label == "Individual analytical check")
    for tool in TOOLS:
        tool_select.set_value(tool).run()
        next(b for b in app.button if b.label == "Run selected check").click().run()
        assert not app.exception
        assert app.session_state["individual"]["tool"] == tool

    next(b for b in app.button if b.label == "Run complete deterministic audit").click().run()
    assert not app.exception
    assert len(app.session_state["audit"]["results"]) == 4

    next(x for x in app.radio if x.label == "Workspace").set_value("Reports & Governance").run()
    next(b for b in app.button if b.label == "Generate PDF Audit Report").click().run()
    assert not app.exception
    assert app.session_state["pdf_artifact"]["bytes"].startswith(b"%PDF")


def test_stale_numeric_widget_values_do_not_crash(monkeypatch):
    from app.services.model_manager import ModelStatus

    monkeypatch.setattr(
        "app.ui.model_setup.get_status",
        lambda _: ModelStatus("unavailable", False, "qwen3:4b-q4_K_M", "Ollama unavailable"),
    )
    app = AppTest.from_file(
        Path(__file__).resolve().parents[2] / "app/main.py", default_timeout=60
    ).run()
    next(b for b in app.button if b.label == "Load transactions.csv").click().run()
    app.session_state["individual_audit_tool_v2"] = 0
    app.session_state["ai_audit_focus_v2"] = 0
    next(x for x in app.radio if x.label == "Workspace").set_value("Agent Workflows").run()
    assert not app.exception
