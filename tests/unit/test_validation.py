import pandas as pd
import pytest

from app.services.validation import cents, validate
from app.tools.missing_data import check_missing
from scripts.generate_data import generate


@pytest.mark.parametrize(
    "value,expected",
    [
        ("12.30", 1230),
        ("0", 0),
        ("-1", None),
        ("NaN", None),
        ("inf", None),
        ("1.001", None),
        ("bad", None),
    ],
)
def test_cents(value, expected):
    assert cents(value) == expected


def test_validation_preserves_source():
    source, _ = generate()
    before = source.copy(deep=True)
    data = validate(source)
    pd.testing.assert_frame_equal(source, before)
    pd.testing.assert_frame_equal(data.original, before)
    assert not data.cleaned.loc[5, "eligible"]
    assert not data.cleaned.loc[6, "eligible"]
    assert not data.cleaned.loc[7, "eligible"]
    result = check_missing(data)
    assert result.metrics["excluded_rows"] == 4
    assert {
        "invalid_date",
        "invalid_amount",
        "unsupported_currency",
        "missing_value",
        "duplicate_transaction_id",
    } <= {f.rule for f in result.findings}


def test_bad_schema_and_empty():
    with pytest.raises(ValueError, match="Missing required"):
        validate(pd.DataFrame({"x": [1]}))
    frame, _ = generate()
    with pytest.raises(ValueError, match="No transactions"):
        validate(frame.iloc[:0])


def test_generator_reproducible():
    a, manifest = generate()
    b, _ = generate()
    pd.testing.assert_frame_equal(a, b)
    assert len(a) == 1200
    assert manifest["large_expense_id"] == "TX00003"
