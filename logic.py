"""
logic.py
---------
Contains the business logic of ExpenseMate — calculations and rules that sit
on top of the raw database data.

Every function takes a user_id so results are always scoped to the
currently logged-in user.
"""

from datetime import datetime
from collections import defaultdict

import database as db


def _current_month_transactions(transactions, year_month=None):
    if year_month is None:
        year_month = datetime.now().strftime("%Y-%m")
    return [t for t in transactions if t["date"].startswith(year_month)]


def get_monthly_summary(user_id, year_month=None):
    transactions = db.get_transactions(user_id)
    month_txns = _current_month_transactions(transactions, year_month)

    total_income = sum(t["amount"] for t in month_txns if t["type"] == "income")
    total_expense = sum(t["amount"] for t in month_txns if t["type"] == "expense")

    return {
        "total_income": total_income,
        "total_expense": total_expense,
        "net_balance": total_income - total_expense,
    }


def get_category_summary(user_id, year_month=None, type_="expense"):
    transactions = db.get_transactions(user_id)
    month_txns = _current_month_transactions(transactions, year_month)

    totals = defaultdict(float)
    for t in month_txns:
        if t["type"] == type_:
            totals[t["category"]] += t["amount"]

    return dict(totals)


def check_budget_alerts(user_id, year_month=None):
    spent_by_category = get_category_summary(user_id, year_month, type_="expense")
    budgets = {b["category"]: b["monthly_limit"] for b in db.get_budgets(user_id)}

    alerts = []
    for category, limit in budgets.items():
        spent = spent_by_category.get(category, 0)
        if spent > limit:
            alerts.append({
                "category": category,
                "spent": spent,
                "limit": limit,
                "over_by": spent - limit,
            })
    return alerts


def would_exceed_budget(user_id, category, amount, year_month=None):
    """
    Check BEFORE saving an expense: would adding `amount` push this category
    over its monthly budget?

    Returns None if it is fine (or if the category has no budget), otherwise a
    dict describing the overshoot so the UI can explain why it was blocked.
    """
    budgets = {b["category"]: b["monthly_limit"] for b in db.get_budgets(user_id)}
    if category not in budgets:
        return None

    limit = budgets[category]
    spent = get_category_summary(user_id, year_month, type_="expense").get(category, 0)
    total_after = spent + amount

    if total_after > limit:
        return {
            "category": category,
            "spent": spent,
            "amount": amount,
            "limit": limit,
            "over_by": total_after - limit,
        }
    return None


def get_budget_progress(user_id, year_month=None):
    spent_by_category = get_category_summary(user_id, year_month, type_="expense")
    budgets = db.get_budgets(user_id)

    progress = []
    for b in budgets:
        category = b["category"]
        limit = b["monthly_limit"]
        spent = spent_by_category.get(category, 0)
        percent = round((spent / limit) * 100, 1) if limit > 0 else 0
        progress.append({
            "category": category,
            "spent": spent,
            "limit": limit,
            "percent": percent,
        })
    return progress


def get_savings_progress(user_id):
    goals = db.get_savings_goals(user_id)
    result = []
    for g in goals:
        percent = round((g["saved_amount"] / g["target_amount"]) * 100, 1) \
            if g["target_amount"] > 0 else 0
        result.append({
            "id": g["id"],
            "name": g["name"],
            "saved_amount": g["saved_amount"],
            "target_amount": g["target_amount"],
            "percent": min(percent, 100),
        })
    return result