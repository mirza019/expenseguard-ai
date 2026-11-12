from pathlib import Path
from unittest.mock import MagicMock, patch

import pymupdf
import pytest
from streamlit.testing.v1 import AppTest

from app.agents.graph import run_audit
from app.agents.request import interpret_request
from app.agents.state import Decision
from app.rag.datasets import generate_expenses, generate_policies
from app.rag.index import build_index
from app.services.model_manager import ModelStatus
from app.services.reporting import pdf_report
from app.services.validation import validate


@pytest.fixture(scope="module")
def intelligence(tmp_path_factory):
    root = tmp_path_factory.mktemp("intelligence")
    generate_policies(root)
    frame, _ = generate_expenses(root)
    index = build_index(root / "policies", root / "index")
    return root, frame, index


def test_october_end_to_end_financial_policy_agent_pdf(intelligence):
    root, frame, index = intelligence
    data = validate(frame)
    state = run_audit(
        data, goal="Audit October 2025 expenses", policy_index=index, policy_root=root / "policies"
    )
    assert set(state["data"].eligible["month"]) == {"2025-10"}
    assert state["calls"] == 4 and state["policy_checked"]
    historical = next(f for f in state["policy_findings"] if f["transaction_id"] == "RAG-TX-00007")
    assert historical["threshold_cents"] == 4000 and historical["status"] == "potential_violation"
    assert all(c["version"] == "1" for c in historical["citations"])
    dates = state["data"].cleaned["date"].dropna()
    report, pdf = pdf_report(state["data"], state, dates.min().date(), dates.max().date())
    assert report.total_actual_cents == int(state["data"].eligible["amount_cents"].sum())
    assert report.potential_policy_rows == sum(
        f["status"] == "potential_violation" for f in state["policy_findings"]
    )
    with pymupdf.open(stream=pdf, filetype="pdf") as doc:
        text = "\n".join(p.get_text() for p in doc)
        assert "RAG-TX-00007" in text and "Indexed policy review" in text
        assert "meals-policy-v2" not in text

    def planner(context):
        return (
            Decision(tool=context["remaining_tools"][0])
            if context["remaining_tools"]
            else Decision(tool="finish")
        )

    assisted = run_audit(
        data,
        goal="Audit October 2025 expenses",
        mode="agent",
        planner=planner,
        policy_index=index,
        policy_root=root / "policies",
    )
    assert assisted["policy_checked"]
    assert any("Retrieved and verified" in event for event in assisted["trace"])
    assert assisted["report"]["total_actual_cents"] == state["report"]["total_actual_cents"]


def test_policy_source_failure_and_request_validation(intelligence, tmp_path):
    root, frame, index = intelligence
    state = run_audit(validate(frame.iloc[:20]), policy_index=index, policy_root=tmp_path)
    assert state["report"].get("policy_error")
    assert len(state["results"]) == 4
    request = interpret_request("Investigate Engineering expenses in France in October 2025")
    assert (
        request.country == "FR"
        and request.department == "Engineering"
        and request.period_start.month == 10
    )
    with pytest.raises(ValueError):
        run_audit(validate(frame), goal="Audit October 2035")


def test_mocked_neural_and_live_generation_without_network(intelligence):
    import sys

    import numpy as np

    from app.rag.answers import evaluate_live
    from app.rag.index import SentenceEmbedding

    root, frame, index = intelligence
    fake = MagicMock()
    fake.SentenceTransformer.return_value.get_sentence_embedding_dimension.return_value = 3
    fake.SentenceTransformer.return_value.encode.return_value = np.ones((1, 3), dtype="float32")
    with patch.dict(sys.modules, {"sentence_transformers": fake}):
        embed = SentenceEmbedding("test-model")
        assert embed.encode(["test"]).shape == (1, 3)
        assert fake.SentenceTransformer.call_args.kwargs["local_files_only"] is True
    from app.rag.datasets import generate_ground_truth

    questions = generate_ground_truth(root)[:1]
    hit = index.search(questions[0]["question"], questions[0]["transaction_date"])[0]
    with (
        patch("app.services.model_manager.ModelManager") as manager,
        patch("langchain_ollama.ChatOllama") as model,
    ):
        manager.return_value.status.return_value.state = "ready"
        model.return_value.with_structured_output.return_value.invoke.return_value.model_dump.return_value = {
            "behavior": "answer_with_citation",
            "answer": hit.chunk.parent_text,
            "citations": [hit.chunk.reference],
        }
        result = evaluate_live(index, questions)
        assert result["status"] == "completed" and "metrics" in result["results"][0]
        model.return_value.with_structured_output.return_value.invoke.side_effect = ValueError
        assert "error" in evaluate_live(index, questions)["results"][0]


def test_ui_knowledge_audit_findings_and_evaluation(monkeypatch):
    monkeypatch.setattr(
        "app.ui.model_setup.get_status",
        lambda _: ModelStatus("unavailable", False, "test", "Ollama unavailable"),
    )
    app = AppTest.from_file(
        Path(__file__).resolve().parents[2] / "app/main.py", default_timeout=120
    ).run()
    next(x for x in app.radio if x.label == "Workspace").set_value("Data & Context").run()
    next(b for b in app.button if b.label == "Load 2,400-transaction policy demo").click().run()
    next(b for b in app.button if b.label == "Load fictional policy demo").click().run()
    assert any(expander.label == "View policy PDF" for expander in app.expander)
    assert any(control.label == "Page" for control in app.number_input)
    next(x for x in app.radio if x.label == "Workspace").set_value("Agent Workflows").run()
    next(b for b in app.button if b.label == "Run complete deterministic audit").click().run()
    assert not app.exception
    assert app.session_state["audit"]["policy_checked"]
    assert len(app.session_state["audit"]["policy_findings"]) == 2400
    next(x for x in app.radio if x.label == "Workspace").set_value("Reports & Governance").run()
    assert any(tab.label == "Evaluation" for tab in app.tabs)
