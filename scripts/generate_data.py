"""Generate fictional expenses and an explicit injected-condition manifest."""
import argparse
import json
import random
from pathlib import Path

import pandas as pd


def generate(count: int = 1200, seed: int = 42) -> tuple[pd.DataFrame, dict]:
    """Generate fixed-budget monthly cohorts and deliberately dirty records."""
    if count < 1000:
        raise ValueError('Generate at least 1,000 transactions.')
    rng = random.Random(seed)
    rows = []
    departments = ['Engineering', 'Sales', 'Operations', 'Finance']
    for i in range(count):
        department = departments[i % 4]
        month = (i // 4) % 12 + 1
        rows.append(dict(transaction_id=f'TX{i:05d}', invoice_id=f'INV{i:05d}',
            invoice_date=f'2025-{month:02d}-{rng.randint(1,28):02d}',
            vendor=f'Fictional Vendor {rng.randrange(25):02d}', department=department,
            cost_center=f'CC-{i % 4 + 1}', category=['Travel', 'Software', 'Supplies'][i % 3],
            amount=round(rng.lognormvariate(5.2, .5), 2), currency='EUR',
            budget_amount=4500 if department == 'Sales' else 9000,
            description='Fictional business expense', payment_status=rng.choice(['paid','pending'])))
    # Same business fields and new transaction ID: an exact invoice duplicate.
    rows[1] = dict(rows[0], transaction_id='TX00001')
    # Same vendor/amount/date but different invoice: possible duplicate.
    rows[2] = dict(rows[0], transaction_id='TX00002', invoice_id='INV-ALTERNATE')
    rows[3]['amount'] = 125000.0
    rows[4]['vendor'] = ''
    rows[5]['invoice_date'] = 'invalid-date'
    rows[6]['amount'] = 'not-a-number'
    rows[7]['currency'] = 'USD'
    rows[8]['transaction_id'] = rows[9]['transaction_id']
    manifest = {'seed': seed, 'rows': count, 'exact_duplicate_ids': ['TX00000', 'TX00001'],
        'possible_duplicate_id': 'TX00002', 'large_expense_id': 'TX00003',
        'missing_vendor_id': 'TX00004', 'invalid_date_id': 'TX00005',
        'invalid_amount_id': 'TX00006', 'unsupported_currency_id': 'TX00007',
        'duplicate_transaction_id': 'TX00009',
        'budget_overrun': 'TX00003 exceeds its monthly cost-center allocation on its own'}
    return pd.DataFrame(rows), manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--rows', type=int, default=1200)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--output', type=Path, default=Path('data/synthetic_expenses.csv'))
    args = parser.parse_args()
    frame, manifest = generate(args.rows, args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(args.output, index=False)
    args.output.with_suffix('.manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
