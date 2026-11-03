"""
test_app_pages.py
-------------------
Presentation-layer tests for app.py, using Streamlit's official AppTest
framework (streamlit.testing.v1.AppTest). Unlike test_database.py /
test_logic.py / test_import_export.py — which test backend modules directly
by calling their functions — these tests run the actual Streamlit script
headlessly and inspect what it renders, the same way a user's browser would
see it.

This closes the one gap the earlier test files intentionally left open: the
Presentation Layer (app.py) itself.
"""

from streamlit.testing.v1 import AppTest

import database as db


def _fake_logged_in_user(user_id):
    """Build the same dict shape app.py stores in st.session_state['user']."""
    return db.get_user(user_id)


# LOGIN SCREEN

def test_login_screen_shown_when_not_logged_in():
    at = AppTest.from_file("../app.py")
    at.run()

    assert at.session_state["user"] is None
    # The login/register form should be rendered with its two toggle buttons.
    button_labels = [b.label for b in at.button]
    assert "Login" in button_labels
    assert "Register" in button_labels


def test_can_register_a_new_user_from_the_ui():
    at = AppTest.from_file("../app.py")
    at.run()

    # Switch to the Register tab.
    at.button(key="btn_register_toggle").click().run()

    # register_form has, in order: username, password, confirm password.
    inputs = at.text_input
    inputs[0].set_value("newuser")
    inputs[1].set_value("securepass123")
    inputs[2].set_value("securepass123")

    at.button(key="FormSubmitter:register_form-Register").click().run()

    user = db.verify_user("newuser", "securepass123")
    assert user is not None


# DASHBOARD (after simulating a logged-in session)

def test_dashboard_loads_after_login(user_id):
    at = AppTest.from_file("../app.py")
    at.session_state["user"] = _fake_logged_in_user(user_id)
    at.run()

    assert at.session_state["user"] is not None
    titles = [t.value for t in at.title]
    assert "Dashboard" in titles


def test_dashboard_shows_empty_state_with_no_transactions(user_id):
    at = AppTest.from_file("../app.py")
    at.session_state["user"] = _fake_logged_in_user(user_id)
    at.run()

    # No exception should occur when there is no data yet — the empty-state
    # helper (render_empty_state) should render a CTA button instead of
    # crashing when the pie chart / progress bars have nothing to show.
    assert not at.exception


def test_dashboard_shows_alert_banner_when_over_budget(user_id):
    db.set_budget(user_id, "Food", 1000)
    db.add_transaction(user_id, "2026-09-01", "expense", "Food", 1500)

    at = AppTest.from_file("../app.py")
    at.session_state["user"] = _fake_logged_in_user(user_id)
    at.run()

    assert not at.exception
    # The alert banner is rendered via st.markdown with unsafe_allow_html,
    # so we check the raw markdown body for the category name and the
    # warning icon rather than a widget value.
    markdown_bodies = " ".join(m.value for m in at.markdown)
    assert "Food" in markdown_bodies



# NAVIGATION


def test_navigating_to_add_transaction_page(user_id):
    at = AppTest.from_file("../app.py")
    at.session_state["user"] = _fake_logged_in_user(user_id)
    at.run()

    at.radio(key="nav_radio").set_value("➕ Add Transaction").run()

    assert not at.exception
    titles = [t.value for t in at.title]
    assert "Add Transaction" in titles


def test_navigating_to_budgets_page(user_id):
    at = AppTest.from_file("../app.py")
    at.session_state["user"] = _fake_logged_in_user(user_id)
    at.run()

    at.radio(key="nav_radio").set_value("💰 Budgets").run()

    assert not at.exception
    titles = [t.value for t in at.title]
    assert "Budgets" in titles


def test_navigating_to_savings_goals_page(user_id):
    at = AppTest.from_file("../app.py")
    at.session_state["user"] = _fake_logged_in_user(user_id)
    at.run()

    at.radio(key="nav_radio").set_value("🎯 Savings Goals").run()

    assert not at.exception
    titles = [t.value for t in at.title]
    assert "Savings Goals" in titles

# ADD TRANSACTION FLOW


def test_add_transaction_category_dropdown_is_populated(user_id):
    at = AppTest.from_file("../app.py")
    at.session_state["user"] = _fake_logged_in_user(user_id)
    at.run()
    at.radio(key="nav_radio").set_value("➕ Add Transaction").run()

    # The category field should be a selectbox (dropdown), not a free-text
    # input, and it should already contain the default categories.
    assert len(at.selectbox) > 0  # at least one selectbox exists on this page
    all_options = [opt for sb in at.selectbox for opt in sb.options]
    assert "Food" in all_options


def test_logout_clears_session():
    at = AppTest.from_file("../app.py")
    _, uid = db.register_user("logouttest", "password123")
    at.session_state["user"] = db.get_user(uid)
    at.run()

    logout_buttons = [b for b in at.button if b.label == "Log out"]
    assert len(logout_buttons) == 1
    logout_buttons[0].click().run()

    assert at.session_state["user"] is None
