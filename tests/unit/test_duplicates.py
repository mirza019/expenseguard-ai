import pytest

from app.services.validation import validate
from app.tools.duplicates import detect_duplicates
from scripts.generate_data import generate


def test_injected_duplicates():
    frame, _ = generate()
    result = detect_duplicates(validate(frame))
    assert any(
        {"TX00000", "TX00001"} <= set(f.transaction_ids)
        for f in result.findings
        if f.rule == "exact_invoice_duplicate"
    )
    assert any(
        "TX00002" in f.transaction_ids for f in result.findings if f.rule == "possible_duplicate"
    )
    assert all(f.rows and "amount_cents" in f.evidence for f in result.findings)


def test_invalid_tolerance():
    frame, _ = generate()
    with pytest.raises(ValueError):
        detect_duplicates(validate(frame), -1)


def test_no_duplicate():
    frame, _ = generate()
    assert not detect_duplicates(validate(frame.iloc[20:21])).findings
