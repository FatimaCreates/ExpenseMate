"""
test_logic.py
--------------
Unit tests for logic.py (Business Logic Layer).

Seeds a temporary database with known transactions/budgets, then verifies
that logic.py's calculations (summaries, category totals, budget alerts,
progress percentages) are mathematically correct.
"""

import database as db
import logic


# ---------------------------------------------------------------------------
# MONTHLY SUMMARY
# ---------------------------------------------------------------------------

def test_monthly_summary_totals_income_and_expense(user_id):
    db.add_transaction(user_id, "2026-09-01", "income", "Salary", 50000)
    db.add_transaction(user_id, "2026-09-05", "expense", "Food", 2000)
    db.add_transaction(user_id, "2026-09-10", "expense", "Transport", 1000)

    summary = logic.get_monthly_summary(user_id, "2026-09")

    assert summary["total_income"] == 50000
    assert summary["total_expense"] == 3000
    assert summary["net_balance"] == 47000


def test_monthly_summary_ignores_other_months(user_id):
    db.add_transaction(user_id, "2026-08-20", "expense", "Food", 999)  # August, not September
    db.add_transaction(user_id, "2026-09-05", "expense", "Food", 500)

    summary = logic.get_monthly_summary(user_id, "2026-09")

    assert summary["total_expense"] == 500  # August transaction must be excluded


def test_monthly_summary_with_no_transactions(user_id):
    summary = logic.get_monthly_summary(user_id, "2026-09")
    assert summary == {"total_income": 0, "total_expense": 0, "net_balance": 0}


# ---------------------------------------------------------------------------
# CATEGORY SUMMARY
# ---------------------------------------------------------------------------

def test_category_summary_groups_correctly(user_id):
    db.add_transaction(user_id, "2026-09-01", "expense", "Food", 500)
    db.add_transaction(user_id, "2026-09-02", "expense", "Food", 300)
    db.add_transaction(user_id, "2026-09-03", "expense", "Transport", 200)

    result = logic.get_category_summary(user_id, "2026-09", type_="expense")

    assert result == {"Food": 800, "Transport": 200}


def test_category_summary_filters_by_type(user_id):
    db.add_transaction(user_id, "2026-09-01", "income", "Salary", 50000)
    db.add_transaction(user_id, "2026-09-02", "expense", "Food", 500)

    expense_only = logic.get_category_summary(user_id, "2026-09", type_="expense")
    income_only = logic.get_category_summary(user_id, "2026-09", type_="income")

    assert expense_only == {"Food": 500}
    assert income_only == {"Salary": 50000}


# ---------------------------------------------------------------------------
# BUDGET ALERTS  (the "challenging part" of the project)
# ---------------------------------------------------------------------------

def test_budget_alert_triggers_when_over_limit(user_id):
    db.set_budget(user_id, "Food", 1000)
    db.add_transaction(user_id, "2026-09-01", "expense", "Food", 700)
    db.add_transaction(user_id, "2026-09-02", "expense", "Food", 500)  # total 1200 > 1000

    alerts = logic.check_budget_alerts(user_id, "2026-09")

    assert len(alerts) == 1
    assert alerts[0]["category"] == "Food"
    assert alerts[0]["spent"] == 1200
    assert alerts[0]["limit"] == 1000
    assert alerts[0]["over_by"] == 200


def test_no_alert_when_under_limit(user_id):
    db.set_budget(user_id, "Food", 1000)
    db.add_transaction(user_id, "2026-09-01", "expense", "Food", 500)

    alerts = logic.check_budget_alerts(user_id, "2026-09")

    assert alerts == []


def test_no_alert_when_exactly_at_limit(user_id):
    db.set_budget(user_id, "Food", 1000)
    db.add_transaction(user_id, "2026-09-01", "expense", "Food", 1000)

    alerts = logic.check_budget_alerts(user_id, "2026-09")

    assert alerts == []  # code uses strict ">" so exactly-at-limit is not an alert


def test_multiple_category_alerts(user_id):
    db.set_budget(user_id, "Food", 1000)
    db.set_budget(user_id, "Transport", 500)
    db.add_transaction(user_id, "2026-09-01", "expense", "Food", 1500)
    db.add_transaction(user_id, "2026-09-02", "expense", "Transport", 800)

    alerts = logic.check_budget_alerts(user_id, "2026-09")
    categories_alerted = {a["category"] for a in alerts}

    assert categories_alerted == {"Food", "Transport"}


# ---------------------------------------------------------------------------
# BUDGET PROGRESS
# ---------------------------------------------------------------------------

def test_budget_progress_percentage(user_id):
    db.set_budget(user_id, "Food", 2000)
    db.add_transaction(user_id, "2026-09-01", "expense", "Food", 500)

    progress = logic.get_budget_progress(user_id, "2026-09")

    assert len(progress) == 1
    assert progress[0]["percent"] == 25.0  # 500 / 2000 * 100


def test_budget_progress_with_zero_limit_does_not_crash(user_id):
    db.set_budget(user_id, "Food", 0)
    progress = logic.get_budget_progress(user_id, "2026-09")
    assert progress[0]["percent"] == 0  # avoids division by zero


# ---------------------------------------------------------------------------
# SAVINGS PROGRESS
# ---------------------------------------------------------------------------

def test_savings_progress_percentage(user_id):
    db.add_savings_goal(user_id, "Emergency Fund", 10000)
    goal_id = db.get_savings_goals(user_id)[0]["id"]
    db.update_savings_progress(goal_id, 2500)

    result = logic.get_savings_progress(user_id)

    assert result[0]["percent"] == 25.0


def test_savings_progress_caps_at_100_percent(user_id):
    db.add_savings_goal(user_id, "Emergency Fund", 10000)
    goal_id = db.get_savings_goals(user_id)[0]["id"]
    db.update_savings_progress(goal_id, 15000)  # saved more than target

    result = logic.get_savings_progress(user_id)

    assert result[0]["percent"] == 100  # should be capped, not 150%
