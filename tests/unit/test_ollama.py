import json
from unittest.mock import MagicMock, patch

import pytest

from app.agents.finance_agent import OllamaPlanner
from app.agents.state import Decision
from app.config import Settings, settings


def test_ollama_json_selection():
    response = MagicMock()
    response.__enter__.return_value = response
    response.iter_content.return_value = [
        json.dumps({"message": {"content": Decision(tool="budget").model_dump_json()}}).encode()
    ]
    with patch("app.agents.finance_agent.requests.post", return_value=response) as post:
        assert OllamaPlanner(Settings())({"goal": "Check budget"}).tool == "budget"
        assert post.call_args.kwargs["json"]["format"]["type"] == "object"
        assert post.call_args.kwargs["timeout"] == 60
        assert post.call_args.args[0] == "http://localhost:11434/api/chat"


def test_ollama_oversize_and_malformed():
    response = MagicMock()
    response.__enter__.return_value = response
    with patch("app.agents.finance_agent.requests.post", return_value=response):
        response.iter_content.return_value = [b"x" * 256001]
        with pytest.raises(ValueError, match="safe size"):
            OllamaPlanner(Settings())({})
        response.iter_content.return_value = [b"not json"]
        with pytest.raises(ValueError):
            OllamaPlanner(Settings())({})


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com",
        "http://10.0.0.1",
        "http://user:password@localhost",
        "http://localhost?secret=x",
    ],
)
def test_reject_nonlocal_ollama(url):
    with pytest.raises(ValueError):
        Settings(ollama_url=url)


def test_config_limits_and_environment(monkeypatch):
    with pytest.raises(ValueError):
        Settings(max_calls=5)
    monkeypatch.setenv("OLLAMA_MODEL", "local-test")
    assert settings().ollama_model == "local-test"
