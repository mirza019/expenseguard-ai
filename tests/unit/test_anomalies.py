import pytest

from app.services.validation import validate
from app.tools.anomalies import detect_anomalies
from scripts.generate_data import generate


def test_extreme_expense_has_evidence():
    frame, _ = generate()
    result = detect_anomalies(validate(frame))
    finding = next(f for f in result.findings if "TX00003" in f.transaction_ids)
    assert finding.evidence["observed_cents"] > finding.evidence["threshold_cents"]
    assert "not proof of fraud" in finding.action


def test_small_cohort_and_invalid_config():
    frame, _ = generate()
    data = validate(frame.iloc[20:22])
    assert not detect_anomalies(data).findings
    assert detect_anomalies(data).metrics["skipped_small_categories"]
    with pytest.raises(ValueError):
        detect_anomalies(data, 0)
