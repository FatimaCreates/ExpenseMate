"""
Integration / system tests for Part B: they drive the real chain
Controller -> Service -> Repository -> (temporary SQLite) Database,
plus two through the real Streamlit UI.
"""

from datetime import datetime

from streamlit.testing.v1 import AppTest

import database as db
from controllers import TransactionController, BudgetController

MONTH = datetime.now().strftime("%Y-%m")
TODAY = datetime.now().strftime("%Y-%m-%d")


def test_it1_add_expense_flows_to_database_with_category_fk(user_id):
    result = TransactionController().add_transaction(user_id, TODAY, "expense", "food", 250, "lunch")
    assert result.ok
    conn = db.get_connection()
    row = conn.execute(
        "SELECT t.amount, c.name FROM transactions t JOIN categories c ON c.id = t.category_id"
    ).fetchone()
    conn.close()
    assert (row["amount"], row["name"]) == (250, "Food")      # 'food' resolved to the one 'Food' row


def test_it2_budget_guard_blocks_and_nothing_is_saved(user_id):
    BudgetController().set_budget(user_id, "Food", 1000)
    ctl = TransactionController()
    assert ctl.add_transaction(user_id, TODAY, "expense", "Food", 800).ok
    blocked = ctl.add_transaction(user_id, TODAY, "expense", "Food", 300)
    assert blocked.error == "budget_exceeded" and blocked.data["over_by"] == 100
    assert len(ctl.list_transactions(user_id).data) == 1


def test_it3_monthly_summary_after_income_expense_and_budget(user_id):
    tc, bc = TransactionController(), BudgetController()
    bc.set_budget(user_id, "Food", 500)
    tc.add_transaction(user_id, TODAY, "income", "Salary", 3000)
    tc.add_transaction(user_id, TODAY, "expense", "Food", 400)
    report = bc.monthly_summary(user_id, MONTH).data
    assert report["summary"] == {"total_income": 3000, "total_expense": 400, "net_balance": 2600}
    assert report["category_totals"] == {"Food": 400}
    assert report["progress"][0]["percent"] == 80.0 and report["alerts"] == []


def test_it4_users_cannot_see_each_others_data():
    _, a = db.register_user("alice", "pw")
    _, b = db.register_user("bob", "pw")
    TransactionController().add_transaction(a, TODAY, "expense", "Food", 10)
    assert BudgetController().monthly_summary(b, MONTH).data["summary"]["total_expense"] == 0


def test_it5_legacy_api_and_new_layers_see_the_same_data(user_id):
    db.add_transaction(user_id, TODAY, "expense", "Bills", 70)               # old entry point
    seen = TransactionController().list_transactions(user_id).data           # new entry point
    assert [(t["category"], t["amount"]) for t in seen] == [("Bills", 70)]


def _open_app(user_id):
    at = AppTest.from_file("../app.py")
    at.session_state["user"] = db.get_user(user_id)
    at.run()
    return at


def test_it6_ui_add_transaction_goes_through_controller(user_id):
    at = _open_app(user_id)
    at.radio(key="nav_radio").set_value("➕ Add Transaction").run()
    next(s for s in at.selectbox if s.label == "Category").set_value("Food")
    at.number_input[0].set_value(120.0)
    next(b for b in at.button if b.label == "Add Transaction").click().run()
    assert not at.exception
    assert [t["amount"] for t in db.get_transactions(user_id)] == [120.0]


def test_it7_ui_dashboard_renders_budget_summary(user_id):
    BudgetController().set_budget(user_id, "Food", 100)
    db.add_transaction(user_id, TODAY, "expense", "Food", 60)
    at = _open_app(user_id)
    assert not at.exception
    assert any("Budget Progress" in s.value for s in at.subheader)


# ---- users / categories / savings through the real chain --------------------
from controllers import UserController, CategoryController, SavingsController


def test_it8_register_then_login_through_layers():
    uc = UserController()
    assert uc.register("zainab", "pw123", "pw123", "USD").ok
    result = uc.login("zainab", "pw123")
    assert result.ok and result.data["currency"] == "USD"
    assert uc.register("zainab", "x", "x").message == "Username already exists."
    assert "Food" in CategoryController().list_names(result.data["id"]).data    # seeded


def test_it9_category_rules_against_real_database(user_id):
    cc, tc = CategoryController(), TransactionController()
    assert cc.add_category(user_id, "food").ok is False                         # duplicate of Food
    assert cc.add_category(user_id, "Gym").ok
    tc.add_transaction(user_id, TODAY, "expense", "Gym", 30)
    from services import CategoryService
    import pytest
    with pytest.raises(ValueError, match="used by"):
        CategoryService().delete_category(user_id, "Gym")


def test_it10_savings_goal_progress_end_to_end(user_id):
    sc = SavingsController()
    assert sc.add_goal(user_id, "Laptop", 1000).ok
    goal_id = sc.list_goals(user_id).data[0]["id"]
    sc.update_progress(goal_id, 250)
    assert sc.goals_progress(user_id).data[0]["percent"] == 25.0


def test_it11_ui_savings_page_adds_goal_via_controller(user_id):
    at = _open_app(user_id)
    at.radio(key="nav_radio").set_value("🎯 Savings Goals").run()
    at.text_input[0].set_value("Holiday")
    at.number_input[0].set_value(900.0)
    next(b for b in at.button if b.label == "Add Goal").click().run()
    assert not at.exception
    assert [g["name"] for g in db.get_savings_goals(user_id)] == ["Holiday"]
