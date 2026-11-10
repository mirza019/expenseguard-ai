// Strictly bounded static-report viewer. No financial analysis or LLM inference here.
export function validateReport(value) {
  if (!value || typeof value !== 'object' || value.currency !== 'EUR' ||
      !['agent', 'deterministic'].includes(value.mode) || !Array.isArray(value.findings) ||
      value.findings.length > 100000 || !Array.isArray(value.tools_run) ||
      !value.tools_run.every(x => ['duplicates', 'budget', 'anomalies', 'missing_data'].includes(x))) {
    throw new Error('Open a valid ExpenseGuard EUR audit JSON report.');
  }
  for (const key of ['total_actual_cents', 'total_source_rows', 'eligible_rows', 'excluded_rows', 'flagged_rows']) {
    if (!Number.isSafeInteger(value[key]) || value[key] < 0) throw new Error('Invalid report totals.');
  }
  for (const f of value.findings) {
    if (!f || typeof f.finding_id !== 'string' || typeof f.rule !== 'string' ||
        !['high', 'medium'].includes(f.severity) || !Array.isArray(f.transaction_ids) ||
        !f.transaction_ids.every(x => typeof x === 'string') || !Array.isArray(f.rows) ||
        !f.rows.every(Number.isSafeInteger) || typeof f.evidence !== 'object' || !f.evidence ||
        typeof f.action !== 'string') throw new Error('Invalid finding structure.');
  }
  return value;
}
export function filteredFindings(report, severity, search) {
  const term = search.toLowerCase();
  return report.findings.filter(f => (severity === 'all' || f.severity === severity) &&
    `${f.finding_id} ${f.rule} ${f.transaction_ids.join(' ')}`.toLowerCase().includes(term));
}
export function euros(cents) {
  return new Intl.NumberFormat('en-IE', { style: 'currency', currency: 'EUR' }).format(cents / 100);
}
