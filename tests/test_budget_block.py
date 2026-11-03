"""
Tests for the budget guard: an expense that would push a category over its
monthly budget must NOT be saved.
"""

from streamlit.testing.v1 import AppTest

import database as db
import logic


# ---------------------------------------------------------------------------
# logic.would_exceed_budget (unit tests)
# ---------------------------------------------------------------------------

def test_no_budget_means_no_block(user_id):
    assert logic.would_exceed_budget(user_id, "Food", 99999, "2026-10") is None


def test_within_budget_is_allowed(user_id):
    db.set_budget(user_id, "Food", 1000)
    assert logic.would_exceed_budget(user_id, "Food", 400, "2026-10") is None


def test_exactly_at_limit_is_allowed(user_id):
    db.set_budget(user_id, "Food", 1000)
    assert logic.would_exceed_budget(user_id, "Food", 1000, "2026-10") is None


def test_over_limit_is_blocked_with_details(user_id):
    db.set_budget(user_id, "Food", 1000)
    result = logic.would_exceed_budget(user_id, "Food", 1500, "2026-10")
    assert result["over_by"] == 500
    assert result["limit"] == 1000


def test_counts_existing_spending_in_same_month(user_id):
    db.set_budget(user_id, "Food", 1000)
    db.add_transaction(user_id, "2026-10-02", "expense", "Food", 800)
    assert logic.would_exceed_budget(user_id, "Food", 300, "2026-10")["over_by"] == 100


def test_other_months_spending_is_ignored(user_id):
    db.set_budget(user_id, "Food", 1000)
    db.add_transaction(user_id, "2026-09-02", "expense", "Food", 900)
    assert logic.would_exceed_budget(user_id, "Food", 500, "2026-10") is None


def test_income_does_not_count_as_spending(user_id):
    db.set_budget(user_id, "Food", 1000)
    db.add_transaction(user_id, "2026-10-02", "income", "Food", 5000)
    assert logic.would_exceed_budget(user_id, "Food", 500, "2026-10") is None


# ---------------------------------------------------------------------------
# UI (Streamlit AppTest)
# ---------------------------------------------------------------------------

def _submit(user_id, category, amount, type_="expense"):
    at = AppTest.from_file("../app.py")
    at.session_state["user"] = db.get_user(user_id)
    at.run()
    at.radio(key="nav_radio").set_value("➕ Add Transaction").run()
    next(s for s in at.selectbox if s.label == "Type").set_value(type_)
    next(s for s in at.selectbox if s.label == "Category").set_value(category)
    at.number_input[0].set_value(amount)
    next(b for b in at.button if b.label == "Add Transaction").click().run()
    return at


def test_over_budget_expense_is_not_saved(user_id):
    db.set_budget(user_id, "Food", 1000)
    at = _submit(user_id, "Food", 1500.0)
    assert not at.exception
    assert db.get_transactions(user_id) == []
    assert any("not added" in e.value for e in at.error)


def test_within_budget_expense_is_saved(user_id):
    db.set_budget(user_id, "Food", 1000)
    at = _submit(user_id, "Food", 200.0)
    assert len(db.get_transactions(user_id)) == 1
    assert not at.error


def test_income_is_never_blocked(user_id):
    db.set_budget(user_id, "Food", 100)
    _submit(user_id, "Food", 5000.0, type_="income")
    assert len(db.get_transactions(user_id)) == 1


def test_category_without_budget_is_not_blocked(user_id):
    db.set_budget(user_id, "Food", 100)
    _submit(user_id, "Transport", 5000.0)
    assert len(db.get_transactions(user_id)) == 1