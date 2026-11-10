"""Session-local in-memory SQL analytics with a fixed query allowlist."""

import duckdb
import pandas as pd

from app.services.validation import ValidatedData

QUERIES = {
    "department": "SELECT department, SUM(amount_cents)::BIGINT AS amount_cents "
    "FROM expenses GROUP BY department ORDER BY amount_cents DESC",
    "category": "SELECT category, SUM(amount_cents)::BIGINT AS amount_cents "
    "FROM expenses GROUP BY category ORDER BY amount_cents DESC",
    "monthly": "SELECT month, SUM(amount_cents)::BIGINT AS amount_cents "
    "FROM expenses GROUP BY month ORDER BY month",
}


def summarize(data: ValidatedData, dimension: str) -> pd.DataFrame:
    """Execute a predefined query; no user/model SQL and no persistent shared state."""
    if dimension not in QUERIES:
        raise ValueError("Unsupported analytics dimension.")
    with duckdb.connect(":memory:") as connection:
        connection.register("expenses", data.eligible)
        return connection.execute(QUERIES[dimension]).df()
