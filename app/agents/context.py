"""Versioned instructions, separated from untrusted financial/policy context."""

from pathlib import Path

NAMES = [
    "request_interpretation",
    "tool_selection",
    "policy_retrieval_planning",
    "policy_grounded_explanation",
    "violation_classification",
    "evidence_verification",
    "final_audit_summary",
    "human_review_escalation",
]


def system_prompts() -> str:
    root = Path(__file__).resolve().parents[1] / "prompts"
    return "\n\n".join((root / (name + ".txt")).read_text(encoding="utf-8") for name in NAMES)
