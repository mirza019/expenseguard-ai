from app.services.validation import validate
from app.tools.budget import check_budget
from scripts.generate_data import generate


def sample():
    frame, _ = generate()
    frame = frame.iloc[20:22].copy()
    frame['invoice_date'] = '2025-01-01'
    frame['department'] = 'Sales'
    frame['cost_center'] = 'CC1'
    frame['amount'] = ['60', '70']
    frame['budget_amount'] = '100'
    return frame


def test_budget_not_double_counted():
    result = check_budget(validate(sample()))
    assert result.metrics['total_actual_cents'] == 13000
    assert result.metrics['total_budget_cents'] == 10000
    assert result.metrics['variance_cents'] == 3000
    assert result.metrics['variance_percent'] == 30
    assert result.metrics['departments'][0]['variance_cents'] == 3000
    assert result.findings[0].rule == 'budget_overrun'


def test_conflict_and_zero():
    frame = sample()
    frame['budget_amount'] = ['100', '200']
    result = check_budget(validate(frame))
    assert result.metrics['variance_cents'] is None
    assert result.findings[0].rule == 'unknown_or_conflicting_budget'
    frame['budget_amount'] = '0'
    assert check_budget(validate(frame)).metrics['variance_percent'] is None


def test_injected_overrun():
    frame, _ = generate()
    result = check_budget(validate(frame))
    assert any('TX00003' in f.transaction_ids for f in result.findings if f.rule == 'budget_overrun')
