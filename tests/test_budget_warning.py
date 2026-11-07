from streamlit.testing.v1 import AppTest
import database as db


def _add_expense(user_id, category, amount):
    at = AppTest.from_file("../app.py")
    at.session_state["user"] = db.get_user(user_id)
    at.run()
    at.radio(key="nav_radio").set_value("➕ Add Transaction").run()
    next(s for s in at.selectbox if s.label == "Category").set_value(category)
    at.number_input[0].set_value(amount)
    next(b for b in at.button if b.label == "Add Transaction").click().run()
    return at

def test_no_warning_within_budget(user_id):
    db.set_budget(user_id, "Food", 1000)
    at = _add_expense(user_id, "Food", 200.0)
    assert len(db.get_transactions(user_id)) == 1
    assert not at.warning


def test_no_warning_for_other_category(user_id):
    db.set_budget(user_id, "Food", 100)
    at = _add_expense(user_id, "Transport", 5000.0)
    assert not at.warning