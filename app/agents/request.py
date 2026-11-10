"""Conservative, deterministic request parameters; unrecognized scope stays unset."""

import calendar
import re
from datetime import date

from pydantic import BaseModel, ConfigDict

from app.services.validation import ValidatedData, validate


class AuditRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    period_start: date | None = None
    period_end: date | None = None
    department: str | None = None
    country: str | None = None
    currency: str = "EUR"


def interpret_request(goal: str) -> AuditRequest:
    months = {name.lower(): i for i, name in enumerate(calendar.month_name) if name}
    match = re.search(r"\b(" + "|".join(months) + r")\s+(20\d{2})\b", goal, re.I)
    start = end = None
    if match:
        month = months[match.group(1).lower()]
        year = int(match.group(2))
        start = date(year, month, 1)
        end = date(year, month, calendar.monthrange(year, month)[1])
    department = next(
        (
            d
            for d in ["Engineering", "Finance", "Operations", "Sales"]
            if re.search(r"\b" + d + r"\b", goal, re.I)
        ),
        None,
    )
    country = (
        "DE"
        if re.search(r"\b(Germany|DE)\b", goal, re.I)
        else "FR"
        if re.search(r"\b(France|FR)\b", goal, re.I)
        else None
    )
    return AuditRequest(period_start=start, period_end=end, department=department, country=country)


def apply_request(data: ValidatedData, request: AuditRequest) -> ValidatedData:
    mask = data.cleaned["eligible"] | ~data.cleaned["eligible"]
    if request.period_start:
        import pandas as pd

        mask &= data.cleaned["date"].between(
            pd.Timestamp(request.period_start), pd.Timestamp(request.period_end)
        )
    for field, value in [("department", request.department), ("country", request.country)]:
        if value:
            if field not in data.cleaned:
                raise ValueError(f"Request needs a {field} column; scope cannot be assumed.")
            mask &= data.cleaned[field].eq(value)
    if mask.all():
        return data
    if not mask.any():
        raise ValueError("No transactions match the requested date/department/country scope.")
    original = data.original.iloc[mask.to_numpy()].copy()
    fresh = validate(original.reset_index(drop=True))
    mapping = dict(zip(fresh.cleaned["source_row"], data.cleaned.loc[mask, "source_row"]))
    fresh.cleaned["source_row"] = fresh.cleaned["source_row"].map(mapping)
    fresh.issues = [
        f.model_copy(update={"rows": [int(mapping[r]) for r in f.rows]}) for f in fresh.issues
    ]
    fresh.original = original
    fresh.transformations.append(
        "Explicit natural-language request scope applied; source-row references preserved."
    )
    return fresh
