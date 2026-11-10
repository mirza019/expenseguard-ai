import assert from 'node:assert/strict';
import test from 'node:test';
import { validateReport, filteredFindings, euros } from '../../site/report.mjs';
const valid = () => ({ mode: 'deterministic', currency: 'EUR', total_actual_cents: 10000,
  total_source_rows: 2, eligible_rows: 2, excluded_rows: 0, flagged_rows: 1, tools_run: ['budget'],
  findings: [{ finding_id: 'budget:0', rule: 'budget_overrun', severity: 'high', rows: [2],
    transaction_ids: ['TX001'], evidence: { actual_cents: 10000 }, action: 'Review allocation.' }] });
test('accepts structured reports and formats cents', () => {
  assert.equal(validateReport(valid()).currency, 'EUR');
  assert.ok(euros(12345).includes('123.45'));
});
test('rejects missing or unsafe totals and malformed findings', () => {
  for (const value of [null, {}, { ...valid(), currency: 'USD' },
    { ...valid(), total_actual_cents: Infinity }, { ...valid(), findings: [{}] },
    { ...valid(), tools_run: ['shell'] }]) assert.throws(() => validateReport(value));
});
test('filters by severity and transaction reference', () => {
  assert.equal(filteredFindings(valid(), 'high', 'tx001').length, 1);
  assert.equal(filteredFindings(valid(), 'medium', '').length, 0);
  assert.equal(filteredFindings(valid(), 'all', 'missing').length, 0);
});
