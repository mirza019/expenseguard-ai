from pathlib import Path
from unittest.mock import MagicMock

from streamlit.testing.v1 import AppTest

from app.config import Settings
from app.services.model_manager import DownloadProgress, ModelSetupError, ModelStatus

APP = Path(__file__).resolve().parents[2] / "app/main.py"


def status(state):
    return ModelStatus(state, True, Settings().ollama_model, state)


def setup_ui(monkeypatch, state):
    getter = MagicMock(return_value=status(state))
    monkeypatch.setattr("app.ui.model_setup.get_status", getter)
    manager = MagicMock()
    monkeypatch.setattr("app.ui.model_setup.ModelManager", manager)
    app = AppTest.from_file(APP, default_timeout=60).run()
    assert not app.exception
    return app, getter, manager


def load_sample(app):
    next(x for x in app.radio if x.label == "Workspace").set_value("Data & Context").run()
    next(b for b in app.button if b.label == "Try fictional sample").click().run()
    next(x for x in app.radio if x.label == "Workspace").set_value("Agent Workflows").run()
    return app


def test_ready_enables_agent_without_download(monkeypatch):
    app, _, manager = setup_ui(monkeypatch, "ready")
    assert not any(b.label == "Download & Enable AI" for b in app.button)
    load_sample(app)
    assert not next(b for b in app.button if b.label == "Run AI-guided audit").disabled
    manager.return_value.download.assert_not_called()


def test_missing_model_button_success(monkeypatch):
    app, getter, manager = setup_ui(monkeypatch, "missing")

    def download(callback):
        callback(DownloadProgress("pulling", 50, 100))
        getter.return_value = status("ready")
        return status("ready")

    manager.return_value.download.side_effect = download
    next(b for b in app.button if b.label == "Download & Enable AI").click().run()
    assert not app.exception
    manager.return_value.download.assert_called_once()
    getter.clear.assert_called_once()
    assert any("AI Ready" in message.value for message in app.success)


def test_failed_download_remains_usable(monkeypatch):
    app, _, manager = setup_ui(monkeypatch, "missing")
    manager.return_value.download.side_effect = ModelSetupError("Model download failed.")
    next(b for b in app.button if b.label == "Download & Enable AI").click().run()
    assert not app.exception
    assert any("failed" in error.value for error in app.error)
    load_sample(app)
    assert next(b for b in app.button if b.label == "Run AI-guided audit").disabled
    next(b for b in app.button if b.label == "Run complete deterministic audit").click().run()
    assert len(app.session_state["audit"]["results"]) == 4


def test_unavailable_has_instructions_and_disabled_agent(monkeypatch):
    app, _, _ = setup_ui(monkeypatch, "unavailable")
    assert any("Ollama" in item.value for item in app.markdown)
    load_sample(app)
    assert next(b for b in app.button if b.label == "Run AI-guided audit").disabled
