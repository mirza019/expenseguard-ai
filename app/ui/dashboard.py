"""Calculated KPIs and financial charts."""
import pandas as pd
import plotly.express as px
import streamlit as st

from app.database.duckdb_service import summarize
from app.services.validation import ValidatedData
from app.tools.budget import check_budget

BURGUNDY = '#711D3C'


def dashboard(data: ValidatedData, report: dict | None) -> None:
    """Present all-data metrics with explicit audit and allocation scope."""
    budget = check_budget(data).metrics
    columns = st.columns(4)
    columns[0].metric('Eligible expenses · EUR', f"{budget['total_actual_cents']/100:,.2f}")
    variance = budget['variance_cents']
    columns[1].metric('Expense − budget · EUR', f'{variance/100:,.2f}'
                      if variance is not None else 'Budget incomplete')
    columns[2].metric('Audit-flagged source rows', report['flagged_rows'] if report else 'Run audit')
    columns[3].metric('Data quality issues', len(data.issues))
    st.caption('Totals include paid, pending and overdue expenses and retain potential duplicates. '
               'Invalid financial rows are excluded. Budgets cover represented allocation groups only.')
    left, right = st.columns(2)
    for target, dimension in [(left, 'department'), (right, 'category')]:
        frame = summarize(data, dimension)
        frame['amount_eur'] = frame['amount_cents'] / 100
        chart = px.bar(frame, x=dimension, y='amount_eur',
            title=f'Expenses by {dimension}', color_discrete_sequence=[BURGUNDY],
            labels={'amount_eur': 'EUR'})
        target.plotly_chart(chart, width='stretch')
    monthly = summarize(data, 'monthly')
    monthly['amount_eur'] = monthly['amount_cents'] / 100
    st.plotly_chart(px.line(monthly, x='month', y='amount_eur', markers=True,
        title='Monthly expense trend', labels={'amount_eur': 'EUR'},
        color_discrete_sequence=[BURGUNDY]), width='stretch')
    comparison = pd.DataFrame(budget['departments'])
    if not comparison.empty:
        for column in ['actual_cents', 'budget_cents']:
            comparison[column.removesuffix('_cents') + '_eur'] = comparison[column] / 100
        st.plotly_chart(px.bar(comparison, x='department', y=['actual_eur', 'budget_eur'],
            barmode='group', title='Department budget versus actual',
            color_discrete_sequence=[BURGUNDY, '#B9A0AB']), width='stretch')
