"""Evidence-based reports; all figures originate from verified tools."""
import json

from app.services.validation import ToolResult, ValidatedData


RULE_EXPLANATIONS = {
    'exact_invoice_duplicate': 'Multiple records share invoice, vendor, amount and date.',
    'possible_duplicate': 'Records share vendor and amount within the configured date window.',
    'budget_overrun': 'Recorded expense exceeds the monthly allocation.',
    'unknown_or_conflicting_budget': 'A unique budget allocation could not be established.',
    'high_amount_iqr': 'The amount exceeds its category’s statistical upper fence.',
}


def build_report(data: ValidatedData, results: dict[str, ToolResult], mode: str,
                 errors: list[str], recommendations: list[dict]) -> dict:
    """Build a serializable audit with stable finding IDs and explicit scope."""
    findings = []
    for tool, result in results.items():
        for i, finding in enumerate(result.findings):
            findings.append(dict(finding.model_dump(), finding_id=f'{tool}:{i}', tool=tool,
                explanation=RULE_EXPLANATIONS.get(finding.rule,
                    'The record failed the stated data-quality rule.')))
    return {'mode': mode, 'currency': 'EUR', 'tools_run': list(results),
        'total_source_rows': len(data.cleaned), 'eligible_rows': len(data.eligible),
        'excluded_rows': int((~data.cleaned['eligible']).sum()),
        'total_actual_cents': int(data.eligible['amount_cents'].sum()),
        'flagged_rows': len({r for f in findings for r in f['rows']}),
        'findings': findings, 'metrics': {k: v.metrics for k, v in results.items()},
        'transformations': data.transformations, 'errors': errors,
        'recommendations': recommendations,
        'limitations': ['Review flags are not findings of fraud.',
            'Totals retain possible duplicate entries until human review.',
            'Budgets cover represented month/department/cost-center allocations only.',
            'EUR-only, nonnegative expenses; refunds and FX conversion are not supported.']}


def markdown_report(report: dict) -> str:
    """Export safe plain Markdown; source fields are kept in JSON evidence instead."""
    lines = ['# ExpenseGuard AI — Audit report', '', f"Mode: {report['mode']}",
        f"Eligible expense: EUR {report['total_actual_cents'] / 100:,.2f}",
        f"Source rows: {report['total_source_rows']}; excluded rows: {report['excluded_rows']}",
        f"Tools executed: {', '.join(report['tools_run'])}", '', '## Findings']
    for finding in report['findings']:
        lines.extend(['', f"### {finding['finding_id']} — {finding['rule']}",
            f"Severity: {finding['severity']}",
            'Source rows: ' + ', '.join(map(str, finding['rows'])),
            finding['explanation'], finding['action']])
    lines.extend(['', '## Limitations', *['- ' + x for x in report['limitations']]])
    return '\n'.join(lines)


def json_report(report: dict) -> str:
    """Export complete structured evidence."""
    return json.dumps(report, indent=2, allow_nan=False)
