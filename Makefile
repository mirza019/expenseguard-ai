.PHONY: run test lint data
run:
	python -m streamlit run app/main.py

test:
	python -m pytest --cov --cov-report=term-missing

lint:
	python -m ruff check .
	python -m ruff format --check .

data:
	python scripts/generate_data.py --rows 1200 --seed 42
