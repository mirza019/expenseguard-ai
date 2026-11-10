import pytest

from app.agents.graph import run_audit
from app.agents.state import Decision, Recommendation
from app.config import Settings
from app.services.analytics import execute_tool, validate_result
from app.services.validation import Finding, ToolResult, validate
from scripts.generate_data import generate


@pytest.fixture
def data():
    frame, _ = generate()
    return validate(frame)


def test_deterministic(data):
    state = run_audit(data)
    assert state["calls"] == 4
    assert len(state["results"]) == 4
    assert state["report"]["mode"] == "deterministic"
    assert not state["errors"]


def test_dynamic_selection_and_explanation(data):
    def planner(context):
        if "duplicates" in context["remaining_tools"]:
            return Decision(tool="duplicates")
        assert context["findings"][0]["finding_id"] == "duplicates:0"
        return Decision(
            tool="finish",
            recommendations=[Recommendation(finding_id="duplicates:0", action="review_invoice")],
        )

    state = run_audit(data, mode="agent", planner=planner)
    assert state["calls"] == 1
    assert state["report"]["recommendations"][0]["finding_id"] == "duplicates:0"
    assert state["trace"][0] == "Model selected duplicates"


def test_unavailable_model_and_retry_limit(data):
    def unavailable(_):
        raise ConnectionError("Sensitive details must not be exposed")

    state = run_audit(data, mode="agent", planner=unavailable, config=Settings(max_retries=1))
    assert state["retries"] == 2
    assert state["report"]["mode"] == "deterministic"
    assert state["calls"] == 4
    assert "Sensitive" not in str(state["errors"])


def test_unknown_reference_rejected(data):
    def planner(_):
        return Decision(
            tool="finish",
            recommendations=[Recommendation(finding_id="invented:99", action="review_invoice")],
        )

    state = run_audit(data, mode="agent", planner=planner, config=Settings(max_retries=0))
    assert state["mode"] == "deterministic"
    assert not state["recommendations"]


def test_repeat_and_max_calls(data):
    state = run_audit(
        data,
        mode="agent",
        planner=lambda _: Decision(tool="budget"),
        config=Settings(max_calls=1, max_retries=0),
    )
    assert state["mode"] == "deterministic"
    assert state["calls"] == 4  # fallback completes remaining tools once each
    assert list(state["results"]).count("budget") == 1


def test_validator_rejects_bad_numbers_and_refs(data):
    result = execute_tool("budget", data)
    result.metrics["total_actual_cents"] += 1
    with pytest.raises(ValueError, match="reconciliation"):
        validate_result(result, data, "budget")
    result = ToolResult(
        tool="duplicates",
        findings=[
            Finding(
                rule="x",
                severity="high",
                rows=[2],
                transaction_ids=["nonexistent"],
                evidence={"x": 1},
            )
        ],
    )
    with pytest.raises(ValueError, match="unknown"):
        validate_result(result, data, "duplicates")


def test_invalid_modes_and_goal(data):
    with pytest.raises(ValueError):
        run_audit(data, mode="fake")
    with pytest.raises(ValueError):
        run_audit(data, goal="")
    with pytest.raises(ValueError):
        execute_tool("shell", data)
