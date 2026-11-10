"""Scaffold import check; behavioral tests will accompany implementation."""


def test_budget_module_imports():
    from app.tools import budget

    assert budget.__doc__
