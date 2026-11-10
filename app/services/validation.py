"""Explicit normalization, exclusions and row-level quality evidence."""
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field

REQUIRED = ['transaction_id', 'invoice_id', 'invoice_date', 'vendor', 'department',
            'cost_center', 'category', 'amount', 'currency', 'budget_amount',
            'description', 'payment_status']


class Finding(BaseModel):
    model_config = ConfigDict(extra='forbid')
    rule: str
    severity: str
    rows: list[int] = Field(default_factory=list)
    transaction_ids: list[str] = Field(default_factory=list)
    evidence: dict = Field(default_factory=dict)
    action: str = 'Review supporting records; do not assume fraud.'


class ToolResult(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)
    tool: str
    status: str = 'success'
    findings: list[Finding] = Field(default_factory=list)
    metrics: dict = Field(default_factory=dict)


@dataclass
class ValidatedData:
    original: pd.DataFrame
    cleaned: pd.DataFrame
    issues: list[Finding]
    transformations: list[str]

    @property
    def eligible(self) -> pd.DataFrame:
        return self.cleaned.loc[self.cleaned['eligible']].copy()


def cents(value: object) -> int | None:
    """Parse exact cents; reject nonfinite, negative and sub-cent amounts."""
    try:
        number = Decimal(str(value))
        if not number.is_finite() or number < 0 or number > Decimal('1000000000'):
            return None
        scaled = number * 100
        return int(scaled) if scaled == scaled.to_integral_value() else None
    except (InvalidOperation, ValueError, TypeError):
        return None


def validate(frame: pd.DataFrame) -> ValidatedData:
    """Preserve source; normalize separately and record every validation failure."""
    missing = sorted(set(REQUIRED) - set(frame.columns))
    if missing:
        raise ValueError('Missing required columns: ' + ', '.join(missing))
    if frame.empty:
        raise ValueError('No transactions to validate.')
    clean = frame[REQUIRED].copy(deep=True).reset_index(drop=True)
    for column in REQUIRED:
        clean[column] = clean[column].fillna('').astype(str).str.strip()
    clean['source_row'] = range(2, len(clean) + 2)
    clean['currency'] = clean['currency'].str.upper()
    clean['amount_cents'] = pd.array(clean['amount'].map(cents), dtype='Int64')
    clean['budget_cents'] = pd.array(clean['budget_amount'].map(cents), dtype='Int64')
    clean['date'] = pd.to_datetime(clean['invoice_date'], format='%Y-%m-%d', errors='coerce')
    clean['month'] = clean['date'].dt.strftime('%Y-%m')
    clean['eligible'] = True
    issues = []

    def issue(mask: pd.Series, rule: str, column: str, exclude: bool) -> None:
        for _, row in clean.loc[mask].iterrows():
            issues.append(Finding(rule=rule, severity='high' if exclude else 'medium',
                rows=[int(row['source_row'])], transaction_ids=[row['transaction_id']],
                evidence={'column': column, 'excluded_from_financials': exclude}))
        if exclude:
            clean.loc[mask, 'eligible'] = False

    for column in REQUIRED:
        issue(clean[column].eq(''), 'missing_value', column,
              column not in {'budget_amount', 'description', 'payment_status', 'invoice_id'})
    issue(clean['amount_cents'].isna() & clean['amount'].ne(''), 'invalid_amount', 'amount', True)
    issue(clean['date'].isna() & clean['invoice_date'].ne(''), 'invalid_date', 'invoice_date', True)
    issue(~clean['currency'].isin(['EUR']) & clean['currency'].ne(''),
          'unsupported_currency', 'currency', True)
    issue(clean['budget_cents'].isna() & clean['budget_amount'].ne(''),
          'invalid_budget', 'budget_amount', False)
    issue(clean['transaction_id'].duplicated(keep=False) & clean['transaction_id'].ne(''),
          'duplicate_transaction_id', 'transaction_id', False)
    issue(~clean['payment_status'].isin(['paid', 'pending', 'overdue']) &
          clean['payment_status'].ne(''), 'invalid_payment_status', 'payment_status', False)
    return ValidatedData(frame.copy(deep=True), clean, issues, [
        'Trimmed surrounding whitespace in analytical fields; source retained unchanged.',
        'Normalized currency to uppercase; only EUR is supported; no FX conversion.',
        'Parsed ISO dates and exact nonnegative cents; invalid financial rows excluded explicitly.',
        'Retained duplicate records for audit; no automatic deduplication.',
        'Budget allocation grain: month, department, cost_center; conflicts reported, not summed.'
    ])
