"""
logic.py
---------
Backward-compatible facade over the service layer. The budget / summary
calculations now live in services/budget_service.py; these functions keep the
Assignment 01 call signatures so existing callers and tests keep working.
"""

from services.budget_service import BudgetService
from services.savings_service import SavingsService

_budget_service = BudgetService()
_savings_service = SavingsService()


def get_monthly_summary(user_id, year_month=None):
    return _budget_service.monthly_summary(user_id, year_month)


def get_category_summary(user_id, year_month=None, type_="expense"):
    return _budget_service.category_summary(user_id, year_month, type_)


def check_budget_alerts(user_id, year_month=None):
    return _budget_service.budget_alerts(user_id, year_month)


def would_exceed_budget(user_id, category, amount, year_month=None):
    return _budget_service.would_exceed_budget(user_id, category, amount, year_month)


def get_budget_progress(user_id, year_month=None):
    return _budget_service.budget_progress(user_id, year_month)


def get_savings_progress(user_id):
    return _savings_service.goals_progress(user_id)
