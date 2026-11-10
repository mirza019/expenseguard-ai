# expenseguard-ai

Starter scaffold for expense duplicate detection, budget checks, and anomaly analysis.

## Status

Project structure only: analysis tools and AI orchestration are not implemented yet. Tests currently verify module imports, not expense-analysis behavior. Sample records are fictional and contain an intentional duplicate.

## Setup

Requires Python 3.11.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m app.main
python -m pytest -q
```

## Structure

- `app/main.py`: application entry point.
- `app/agent.py`: future orchestration.
- `app/tools/`: duplicate, budget, and anomaly modules.
- `tests/`: starter import checks.
- `data/sample_expenses.csv`: fictional sample expenses in EUR.
- `.github/workflows/ci.yml`: compilation and pytest checks on pushes and pull requests.

Never commit API keys or real employee financial information. Local `.env` files are ignored.
