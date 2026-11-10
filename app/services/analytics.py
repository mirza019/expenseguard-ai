"""Tool registry and strict evidence validation."""
import math

from app.services.validation import ToolResult, ValidatedData
from app.tools.anomalies import detect_anomalies
from app.tools.budget import check_budget
from app.tools.duplicates import detect_duplicates
from app.tools.missing_data import check_missing

TOOLS = {'duplicates': detect_duplicates, 'budget': check_budget,
         'anomalies': detect_anomalies, 'missing_data': check_missing}


def validate_result(result: ToolResult, data: ValidatedData, expected_tool: str) -> None:
    """Validate status, references, finite numerics and independent financial totals."""
    if result.tool != expected_tool or result.status != 'success':
        raise ValueError('Invalid tool execution status or tool identity.')
    by_row = dict(zip(data.cleaned['source_row'].astype(int), data.cleaned['transaction_id']))
    for finding in result.findings:
        if not finding.rows or not finding.evidence or len(finding.rows) != len(finding.transaction_ids):
            raise ValueError('Finding lacks evidence or aligned transaction references.')
        if any(row not in by_row or by_row[row] != tid for row, tid in
               zip(finding.rows, finding.transaction_ids)):
            raise ValueError('Finding references an unknown transaction or source row.')

    def finite(value: object) -> None:
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError('Nonfinite result.')
        if isinstance(value, dict):
            for item in value.values():
                finite(item)
        if isinstance(value, list):
            for item in value:
                finite(item)
    finite(result.model_dump())
    if expected_tool == 'budget':
        metrics = result.metrics
        if metrics.get('total_actual_cents') != int(data.eligible['amount_cents'].sum()):
            raise ValueError('Budget actual total failed reconciliation.')
        for group in metrics.get('groups', []):
            actual, budget = group['actual_cents'], group['budget_cents']
            if budget is not None and group['variance_cents'] != actual - budget:
                raise ValueError('Budget variance failed reconciliation.')
        if metrics.get('budget_complete'):
            total = sum(g['budget_cents'] for g in metrics['groups'])
            if metrics['total_budget_cents'] != total or metrics['variance_cents'] != (
                    metrics['total_actual_cents'] - total):
                raise ValueError('Total budget failed reconciliation.')


def execute_tool(name: str, data: ValidatedData) -> ToolResult:
    """Execute only a registered analytical function and validate its output."""
    if name not in TOOLS:
        raise ValueError('Unknown analytical tool.')
    result = TOOLS[name](data)
    validate_result(result, data, name)
    return result
