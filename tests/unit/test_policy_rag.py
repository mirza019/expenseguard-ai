from dataclasses import replace
from datetime import date

import pytest

from app.services.policy_rag import extract_policy, policy_evidence, retrieve, verify_citation
from tests.fixtures.pdf_helpers import audit_fixture, policy_pdf


def test_verified_policy_citation_and_effective_date():
    data, _, _, _ = audit_fixture()
    policy = policy_pdf("Travel expenses must not exceed EUR 100.00 per transaction.")
    citations, evaluations = policy_evidence(data, (policy,))
    assert evaluations > 0
    assert citations
    assert citations[0].page == 1
    assert citations[0].section == "1. Travel expense limits"
    verify_citation(citations[0], data, (policy,))
    future = policy_pdf(effective=date(2030, 1, 1))
    assert policy_evidence(data, (future,)) == ([], None)
    assert retrieve((policy,), "unrelated terminology", date(2025, 2, 1)) == []


@pytest.mark.parametrize(
    "change",
    [
        {"page": 99},
        {"version": "fabricated"},
        {"quote": "Invented policy"},
        {"document_id": "fake"},
        {"chunk_id": "fake"},
        {"transaction_id": "fake"},
        {"threshold_cents": 1},
        {"assessment": "confirmed_fraud"},
    ],
)
def test_fabricated_citations_fail(change):
    data, _, _, _ = audit_fixture()
    policy = policy_pdf("Travel expenses must not exceed EUR 100.00 per transaction.")
    citations, _ = policy_evidence(data, (policy,))
    bad = citations[0].model_copy(update=change)
    with pytest.raises(ValueError):
        verify_citation(bad, data, (policy,))


def test_missing_policy_unsupported_language_and_latest_version():
    data, _, _, _ = audit_fixture()
    assert policy_evidence(data, ()) == ([], None)
    unsupported = policy_pdf("Travel requires approval under local rules.")
    citations, evaluations = policy_evidence(data, (unsupported,))
    assert evaluations is None
    assert citations[0].assessment == "related_guidance"
    verify_citation(citations[0], data, (unsupported,))
    older = policy_pdf("Travel expenses must not exceed EUR 1.00 per transaction.", version="1")
    newer = policy_pdf(
        "Travel expenses must not exceed EUR 1000000.00 per transaction.",
        version="2",
        effective=date(2025, 1, 1),
    )
    with pytest.raises(ValueError, match="Ambiguous"):
        policy_evidence(data, (older, newer))
    newer = replace(newer, effective_date=date(2025, 1, 2))
    chosen = retrieve((older, newer), "Travel expenses", date(2025, 3, 1))
    assert {doc.version for doc, _ in chosen} == {"2"}


def test_bad_pdf_and_metadata():
    for source in [b"", b"not a pdf"]:
        with pytest.raises(ValueError):
            extract_policy(source, "Title", "1", date(2025, 1, 1))
    with pytest.raises(ValueError):
        extract_policy(b"x", "", "1", date(2025, 1, 1))
    policy = policy_pdf()
    with pytest.raises(ValueError):
        extract_policy(policy.source, policy.title, "", policy.effective_date)


def test_source_bytes_and_guidance_explanations_cannot_be_forged():
    data, _, _, _ = audit_fixture()
    policy = policy_pdf("Travel requires approval under local rules.")
    citations, _ = policy_evidence(data, (policy,))
    with pytest.raises(ValueError, match="explanation|conclusion"):
        verify_citation(
            citations[0].model_copy(update={"explanation": "Confirmed fraud"}), data, (policy,)
        )
    with pytest.raises(ValueError, match="document"):
        verify_citation(citations[0], data, (replace(policy, source=b"forged"),))
    with pytest.raises(ValueError, match="amount"):
        verify_citation(citations[0].model_copy(update={"observed_cents": 1}), data, (policy,))
