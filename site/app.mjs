import { validateReport, filteredFindings, euros } from './report.mjs';
const $ = id => document.getElementById(id);
let report = null;
function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}
function renderFindings() {
  if (!report) return;
  const visible = filteredFindings(report, $('severity').value, $('search').value);
  $('finding-count').textContent = `${visible.length.toLocaleString()} findings`;
  $('finding-body').replaceChildren();
  for (const f of visible.slice(0, 300)) {
    const row = element('tr');
    row.append(element('td', f.finding_id));
    const severity = element('td'); severity.append(element('span', f.severity, `severity ${f.severity}`));
    row.append(severity, element('td', f.rule.replaceAll('_', ' ')),
      element('td', f.transaction_ids.slice(0, 8).join(', ') + (f.transaction_ids.length > 8 ? ' …' : '')));
    const cell = element('td'), details = element('details');
    details.append(element('summary', 'Inspect evidence'), element('p', f.action),
      element('p', `Source rows: ${f.rows.slice(0, 30).join(', ')}`),
      element('pre', JSON.stringify(f.evidence, null, 2)));
    cell.append(details); row.append(cell); $('finding-body').append(row);
  }
  if (visible.length > 300) $('message').textContent = 'Showing the first 300 matching findings. Refine the filter or download the complete report.';
}
function showReport(value, source) {
  const checked = validateReport(value);
  report = checked;
  $('source-label').textContent = source;
  $('message').textContent = 'Report loaded. Review scope and evidence before drawing conclusions.';
  $('kpis').replaceChildren();
  const cards = [
    ['Eligible expenses', euros(report.total_actual_cents), 'EUR · potential duplicates retained'],
    ['Flagged source rows', report.flagged_rows.toLocaleString(), 'Across the checks executed'],
    ['High-severity findings', report.findings.filter(f => f.severity === 'high').length.toLocaleString(), 'Investigation required'],
    ['Excluded rows', report.excluded_rows.toLocaleString(), 'Not included in financial totals']
  ];
  for (const [label, value, note] of cards) {
    const card = element('article', undefined, 'kpi');
    card.append(element('p', label), element('strong', value), element('small', note)); $('kpis').append(card);
  }
  $('scope').replaceChildren(element('p', `Mode: ${report.mode}. Source: ${report.total_source_rows.toLocaleString()} rows. Eligible: ${report.eligible_rows.toLocaleString()} rows.`),
    element('p', `Tools executed: ${report.tools_run.join(', ')}.`));
  if (report.tools_run.length < 4) $('scope').append(element('p', 'Partial audit: not all checks were executed.'));
  if (Array.isArray(report.errors) && report.errors.length) $('scope').append(element('p', 'This report includes errors or fallback events. Inspect the complete JSON.'));
  $('department-chart').replaceChildren();
  const groups = report.metrics?.budget?.departments;
  if (Array.isArray(groups) && groups.length <= 1000 && groups.every(g => typeof g.department === 'string' && Number.isSafeInteger(g.actual_cents) && g.actual_cents >= 0)) {
    const maximum = Math.max(1, ...groups.map(g => g.actual_cents));
    for (const group of groups) {
      const label = element('div', undefined, 'bar-label');
      label.append(element('span', group.department), element('span', euros(group.actual_cents)));
      const track = element('div', undefined, 'bar-track'), fill = element('div', undefined, 'bar-fill');
      fill.style.width = `${100 * group.actual_cents / maximum}%`;
      track.append(fill); $('department-chart').append(label, track);
    }
  } else $('department-chart').append(element('p', 'Department metrics are not available in this report.'));
  $('download').disabled = false;
  renderFindings();
}
$('demo').addEventListener('click', async () => {
  try {
    $('message').textContent = 'Loading fictional report…';
    const response = await fetch('./demo-report.json', { cache: 'no-store' });
    if (!response.ok) throw new Error('Demo report unavailable. Build it with scripts/build_pages_demo.py.');
    showReport(await response.json(), 'Fictional demo · seed 42');
  } catch (error) { $('message').textContent = error.message; }
});
$('report-file').addEventListener('change', async event => {
  const file = event.target.files[0]; if (!file) return;
  try {
    if (file.size > 10 * 1024 * 1024) throw new Error('Report exceeds the 10 MB limit.');
    showReport(JSON.parse(await file.text()), 'Your report · processed in this browser only');
  } catch (error) { $('message').textContent = `Cannot load report: ${error.message}`; }
});
$('severity').addEventListener('change', renderFindings);
$('search').addEventListener('input', renderFindings);
$('download').addEventListener('click', () => {
  if (!report) return;
  const url = URL.createObjectURL(new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' }));
  const link = element('a'); link.href = url; link.download = 'expenseguard-report.json'; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
});
