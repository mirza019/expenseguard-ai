"""Explainable category-level IQR outlier screening, not fraud classification."""
from app.services.validation import Finding, ToolResult, ValidatedData


def detect_anomalies(data: ValidatedData, multiplier: float = 1.5) -> ToolResult:
    """Flag high amounts above Q3 + multiplier × IQR for cohorts of at least 8."""
    if not 0.5 <= multiplier <= 10:
        raise ValueError('IQR multiplier must be between 0.5 and 10.')
    findings = []
    skipped = []
    for category, group in data.eligible.groupby('category'):
        if len(group) < 8:
            skipped.append(str(category))
            continue
        values = group['amount_cents'].astype(float)
        q1, q3 = values.quantile([.25, .75])
        threshold = float(q3 + multiplier * (q3 - q1))
        for _, row in group.loc[values > threshold].iterrows():
            findings.append(Finding(rule='high_amount_iqr', severity='medium',
                rows=[int(row['source_row'])], transaction_ids=[row['transaction_id']],
                evidence={'category': str(category), 'observed_cents': int(row['amount_cents']),
                    'threshold_cents': threshold, 'q1_cents': float(q1), 'q3_cents': float(q3),
                    'multiplier': multiplier, 'cohort_size': len(group)},
                action='Review business purpose and approval; an outlier is not proof of fraud.'))
    return ToolResult(tool='anomalies', findings=findings,
        metrics={'outlier_rows': len(findings), 'skipped_small_categories': skipped})
