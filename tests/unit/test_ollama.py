from unittest.mock import patch

import pytest

from app.agents.finance_agent import OllamaPlanner
from app.agents.state import Decision
from app.config import Settings, settings


def test_chatollama_selection_and_lazy_initialization():
    with patch("app.agents.finance_agent.ChatOllama") as factory:
        structured = factory.return_value.with_structured_output.return_value
        structured.invoke.return_value = Decision(tool="budget")
        planner = OllamaPlanner(Settings())
        factory.assert_not_called()
        assert planner({"goal": "Check budget"}).tool == "budget"
        assert planner({"goal": "Check again"}).tool == "budget"
        factory.assert_called_once()
        assert factory.call_args.kwargs["model"] == "qwen3:4b-q4_K_M"
        assert factory.call_args.kwargs["validate_model_on_init"] is True
        assert factory.call_args.kwargs["temperature"] == 0
        factory.return_value.with_structured_output.assert_called_once_with(
            Decision, method="json_schema"
        )
        assert structured.invoke.call_args.args[0][1].content == '{"goal": "Check again"}'


def test_reject_oversize_and_malformed_responses():
    with patch("app.agents.finance_agent.ChatOllama") as factory:
        planner = OllamaPlanner(Settings())
        with pytest.raises(ValueError, match="safe size"):
            planner({"goal": "x" * 32000})
        factory.assert_not_called()
        factory.return_value.with_structured_output.return_value.invoke.return_value = {
            "tool": "shell"
        }
        with pytest.raises(ValueError):
            planner({})


def test_initialization_failure_reaches_fallback():
    from app.agents.graph import run_audit
    from app.services.validation import validate
    from scripts.generate_data import generate

    frame, _ = generate()
    with patch("app.agents.finance_agent.ChatOllama", side_effect=ConnectionError):
        state = run_audit(validate(frame), mode="agent", config=Settings(max_retries=0))
    assert state["mode"] == "deterministic"
    assert len(state["results"]) == 4


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com",
        "http://10.0.0.1",
        "http://user:password@localhost",
        "http://localhost?secret=x",
        "http://localhost/api",
    ],
)
def test_reject_nonlocal_ollama(url):
    with pytest.raises(ValueError):
        Settings(ollama_url=url)


def test_config_limits_and_environment(monkeypatch):
    for kwargs in [{"max_calls": 5}, {"timeout": 0}, {"ollama_model": ""}]:
        with pytest.raises(ValueError):
            Settings(**kwargs)
    monkeypatch.setenv("OLLAMA_MODEL", "local-test")
    assert settings().ollama_model == "local-test"


def test_langchain_tools_are_registered_and_constrained():
    from app.agents.tools import build_tools
    from app.services.validation import validate
    from scripts.generate_data import generate

    frame, _ = generate()
    tools = build_tools(validate(frame))
    assert set(tools) == {"duplicates", "budget", "anomalies", "missing_data"}
    assert tools["budget"].invoke({})["metrics"]["total_actual_cents"] > 0
    with pytest.raises(ValueError):
        tools["budget"].invoke({"sql": "DROP TABLE expenses"})


def test_chatollama_inference_drives_langgraph_and_verified_tool():
    from app.agents.graph import run_audit
    from app.agents.state import Recommendation
    from app.services.validation import validate
    from scripts.generate_data import generate

    frame, _ = generate()
    with patch("app.agents.finance_agent.ChatOllama") as factory:
        structured = factory.return_value.with_structured_output.return_value
        structured.invoke.side_effect = [
            Decision(tool="budget"),
            Decision(
                tool="finish",
                recommendations=[Recommendation(finding_id="budget:0", action="review_budget")],
            ),
        ]
        state = run_audit(validate(frame), mode="agent")
    assert state["mode"] == "agent"
    assert state["calls"] == 1
    assert state["results"]["budget"].metrics["total_actual_cents"] > 0
    assert state["recommendations"][0]["finding_id"] == "budget:0"
    assert structured.invoke.call_count == 2
