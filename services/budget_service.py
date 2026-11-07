"""Budget and monthly-summary business logic (Services layer).

All calculations live here. Data comes from repositories, which are injected
so the rules can be unit-tested with fakes (no database needed).
"""

from collections import defaultdict
from datetime import datetime

from repositories.transaction_repository import TransactionRepository
from repositories.budget_repository import BudgetRepository
from services.validators import validate_monthly_limit


class BudgetService:

    def __init__(self, transaction_repo=None, budget_repo=None, clock=None):
        self._transactions = transaction_repo or TransactionRepository()
        self._budgets = budget_repo or BudgetRepository()
        self._clock = clock or datetime.now

    # -- helpers -----------------------------------------------------------
    def _month(self, year_month):
        return year_month or self._clock().strftime("%Y-%m")

    @staticmethod
    def _totals(month_txns):
        income = sum(t["amount"] for t in month_txns if t["type"] == "income")
        expense = sum(t["amount"] for t in month_txns if t["type"] == "expense")
        return {"total_income": income, "total_expense": expense,
                "net_balance": income - expense}

    @staticmethod
    def _by_category(month_txns, type_):
        totals = defaultdict(float)
        for t in month_txns:
            if t["type"] == type_:
                totals[t["category"]] += t["amount"]
        return dict(totals)

    @staticmethod
    def _progress(budgets, spent_by_category):
        rows = []
        for b in budgets:
            spent = spent_by_category.get(b["category"], 0)
            limit = b["monthly_limit"]
            percent = round((spent / limit) * 100, 1) if limit > 0 else 0
            rows.append({"category": b["category"], "spent": spent,
                         "limit": limit, "percent": percent})
        return rows

    @staticmethod
    def _alerts(budgets, spent_by_category):
        alerts = []
        for b in budgets:
            spent = spent_by_category.get(b["category"], 0)
            if spent > b["monthly_limit"]:
                alerts.append({"category": b["category"], "spent": spent,
                               "limit": b["monthly_limit"],
                               "over_by": spent - b["monthly_limit"]})
        return alerts

    # -- public API --------------------------------------------------------
    def monthly_summary(self, user_id, year_month=None):
        month = self._month(year_month)
        return self._totals(self._transactions.list_for_month(user_id, month))

    def category_summary(self, user_id, year_month=None, type_="expense"):
        month = self._month(year_month)
        return self._by_category(self._transactions.list_for_month(user_id, month), type_)

    def budget_progress(self, user_id, year_month=None):
        spent = self.category_summary(user_id, year_month, "expense")
        return self._progress(self._budgets.list_for_user(user_id), spent)

    def budget_alerts(self, user_id, year_month=None):
        spent = self.category_summary(user_id, year_month, "expense")
        return self._alerts(self._budgets.list_for_user(user_id), spent)

    def would_exceed_budget(self, user_id, category, amount, year_month=None):
        """None if fine (or no budget for the category), else a dict describing the overshoot."""
        limits = {b["category"]: b["monthly_limit"]
                  for b in self._budgets.list_for_user(user_id)}
        if category not in limits:
            return None
        limit = limits[category]
        spent = self.category_summary(user_id, year_month, "expense").get(category, 0)
        total_after = spent + amount
        if total_after > limit:
            return {"category": category, "spent": spent, "amount": amount,
                    "limit": limit, "over_by": total_after - limit}
        return None

    def monthly_budget_report(self, user_id, year_month=None):
        """Everything the dashboard needs for one month from ONE read of the
        month's transactions and ONE read of the budgets."""
        month = self._month(year_month)
        month_txns = self._transactions.list_for_month(user_id, month)
        budgets = self._budgets.list_for_user(user_id)
        spent = self._by_category(month_txns, "expense")
        return {
            "month": month,
            "summary": self._totals(month_txns),
            "category_totals": spent,
            "progress": self._progress(budgets, spent),
            "alerts": self._alerts(budgets, spent),
        }

    def set_budget(self, user_id, category, monthly_limit):
        validate_monthly_limit(monthly_limit)
        self._budgets.upsert(user_id, category, monthly_limit)

    def list_budgets(self, user_id):
        return self._budgets.list_for_user(user_id)
