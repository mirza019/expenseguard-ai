"""Budget reconciliation at a declared allocation grain."""
from app.services.validation import Finding, ToolResult, ValidatedData


def check_budget(data: ValidatedData) -> ToolResult:
    """Variance = actual minus budget; positive means overspend. Amounts are cents."""
    frame = data.eligible
    groups = []
    findings = []
    # Read allocations from all identifiable rows, including excluded financial rows.
    allocations = data.cleaned.dropna(subset=['month'])
    allocations = allocations[allocations['department'].ne('') & allocations['cost_center'].ne('')]
    for (month, department, center), group in allocations.groupby(
            ['month', 'department', 'cost_center']):
        valid = frame[(frame['month'] == month) & (frame['department'] == department) &
                      (frame['cost_center'] == center)]
        actual = int(valid['amount_cents'].sum())
        budgets = group['budget_cents'].dropna().unique()
        budget = int(budgets[0]) if len(budgets) == 1 else None
        rows = group['source_row'].astype(int).tolist()
        ids = group['transaction_id'].tolist()
        evidence = {'month': month, 'department': department, 'cost_center': center,
                    'actual_cents': actual, 'budget_cents': budget}
        if budget is None:
            findings.append(Finding(rule='unknown_or_conflicting_budget', severity='high',
                rows=rows, transaction_ids=ids, evidence=evidence,
                action='Supply one consistent allocation for this month/department/cost center.'))
        variance = actual - budget if budget is not None else None
        percent = 100 * variance / budget if budget else None
        record = dict(evidence, variance_cents=variance, variance_percent=percent)
        groups.append(record)
        if variance is not None and variance > 0:
            findings.append(Finding(rule='budget_overrun', severity='high', rows=rows,
                transaction_ids=ids, evidence=record,
                action='Review the allocation and supporting expense approvals.'))
    known = [g for g in groups if g['budget_cents'] is not None]
    total_actual = int(frame['amount_cents'].sum())
    known_actual = sum(g['actual_cents'] for g in known)
    total_budget = sum(g['budget_cents'] for g in known)
    complete = len(known) == len(groups) and bool(groups)
    variance = total_actual - total_budget if complete else None

    def aggregate(key: str) -> list[dict]:
        output = []
        for name in sorted({g[key] for g in groups}):
            items = [g for g in groups if g[key] == name]
            actual = sum(g['actual_cents'] for g in items)
            budget = sum(g['budget_cents'] for g in items) if all(
                g['budget_cents'] is not None for g in items) else None
            output.append({key: name, 'actual_cents': actual, 'budget_cents': budget,
                'variance_cents': actual - budget if budget is not None else None,
                'variance_percent': 100 * (actual - budget) / budget if budget else None})
        return output

    return ToolResult(tool='budget', findings=findings, metrics={
        'total_actual_cents': total_actual, 'total_budget_cents': total_budget if complete else None,
        'known_budget_cents': total_budget, 'known_actual_cents': known_actual,
        'variance_cents': variance, 'variance_percent': 100 * variance / total_budget
        if variance is not None and total_budget else None,
        'budget_complete': complete, 'groups': groups,
        'departments': aggregate('department'), 'cost_centers': aggregate('cost_center')})
