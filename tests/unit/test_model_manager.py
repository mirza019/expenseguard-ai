from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from ollama import ProgressResponse

from app.config import Settings
from app.services.model_manager import DownloadProgress, ModelManager, ModelSetupError

MODEL = Settings().ollama_model


def listing(*names):
    return SimpleNamespace(models=[SimpleNamespace(model=name) for name in names])


def test_unavailable_and_cli_detection():
    client = MagicMock()
    client.list.side_effect = ConnectionError
    with patch("app.services.model_manager.shutil.which", return_value=None):
        state = ModelManager(Settings(), client).status()
    assert state.state == "unavailable"
    assert state.cli_installed is False
    client.pull.assert_not_called()


def test_installed_model_no_download_even_without_cli():
    client = MagicMock()
    client.list.return_value = listing(MODEL)
    manager = ModelManager(Settings(), client)
    with patch("app.services.model_manager.shutil.which", return_value=None):
        assert manager.status().state == "ready"
    assert manager.download().state == "ready"
    client.pull.assert_not_called()
    client.show.assert_called_with(MODEL)


def test_missing_exact_tag_not_alias():
    client = MagicMock()
    client.list.return_value = listing("qwen3:4b")
    assert ModelManager(Settings(), client).status().state == "missing"
    client.show.assert_not_called()
    client.pull.assert_not_called()


def test_download_progress_and_post_verification():
    client = MagicMock()
    client.list.side_effect = [listing(), listing(MODEL)]
    client.pull.return_value = iter(
        [
            ProgressResponse(status="pulling manifest"),
            ProgressResponse(status="pulling layer", total=100, completed=50),
            ProgressResponse(status="success"),
        ]
    )
    updates = []
    result = ModelManager(Settings(), client).download(updates.append)
    assert result.state == "ready"
    assert updates[1].fraction == 0.5
    assert updates[0].fraction is None
    client.pull.assert_called_once_with(MODEL, stream=True)
    client.show.assert_called_once_with(MODEL)


@pytest.mark.parametrize("failure", [ConnectionError, KeyboardInterrupt])
def test_download_failure_or_interrupt(failure):
    client = MagicMock()
    client.list.return_value = listing()

    def broken_stream():
        yield ProgressResponse(status="pulling")
        raise failure()

    client.pull.return_value = broken_stream()
    with pytest.raises(ModelSetupError, match="failed|interrupted"):
        ModelManager(Settings(), client).download()


def test_unavailable_never_pulls_and_unverified_model_never_ready():
    client = MagicMock()
    client.list.side_effect = ConnectionError
    with pytest.raises(ModelSetupError, match="Start Ollama"):
        ModelManager(Settings(), client).download()
    client.pull.assert_not_called()
    client.list.side_effect = None
    client.list.return_value = listing()
    client.pull.return_value = iter([])
    with pytest.raises(ModelSetupError, match="could not be verified"):
        ModelManager(Settings(), client).download()
    client.list.return_value = listing(MODEL)
    client.show.side_effect = RuntimeError
    assert ModelManager(Settings(), client).status().state == "unavailable"


def test_no_io_on_construction_and_progress_bounds():
    with patch("app.services.model_manager.Client") as client:
        ModelManager(Settings())
        client.return_value.list.assert_not_called()
        client.return_value.pull.assert_not_called()
    assert DownloadProgress("x", 200, 100).fraction == 1
    assert DownloadProgress("x", -1, 100).fraction == 0
