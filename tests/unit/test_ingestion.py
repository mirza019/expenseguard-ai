from io import BytesIO

import pandas as pd
import pytest

from app.services.ingestion import IngestionError, read_upload


def test_csv_preserves_values():
    frame = read_upload(b"transaction_id,amount\n001,10.00\n", "a.csv")
    assert frame.iloc[0].to_dict() == {"transaction_id": "001", "amount": "10.00"}


def test_xlsx():
    out = BytesIO()
    pd.DataFrame({"amount": ["12"]}).to_excel(out, index=False)
    assert read_upload(out.getvalue(), "a.xlsx").iloc[0]["amount"] == "12"


@pytest.mark.parametrize(
    "content,name",
    [
        (b"", "a.csv"),
        (b"x", "a.exe"),
        (b"amount\n", "a.csv"),
        (b"garbage", "a.xlsx"),
        (b"\xff\xfe", "a.csv"),
    ],
)
def test_invalid(content, name):
    with pytest.raises(IngestionError):
        read_upload(content, name)


def test_size(monkeypatch):
    monkeypatch.setattr("app.services.ingestion.MAX_BYTES", 2)
    with pytest.raises(IngestionError, match="10 MB"):
        read_upload(b"123", "a.csv")


def test_native_excel_dates_validate():
    from datetime import datetime

    from app.services.validation import validate
    from scripts.generate_data import generate

    frame, _ = generate()
    frame = frame.iloc[20:21].copy()
    frame["invoice_date"] = datetime(2025, 1, 2)
    out = BytesIO()
    frame.to_excel(out, index=False)
    data = validate(read_upload(out.getvalue(), "native.xlsx"))
    assert len(data.eligible) == 1
    assert data.eligible.iloc[0]["month"] == "2025-01"
