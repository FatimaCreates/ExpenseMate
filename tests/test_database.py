"""
test_database.py
------------------
Unit tests for database.py (Data Access Layer).

Uses the `temp_db` fixture from conftest.py, so every test runs against a
fresh, temporary SQLite file — never the real expensemate.db.
"""

import database as db


# USERS / AUTH


def test_register_user_success():
    ok, user_id = db.register_user("alice", "password123")
    assert ok is True
    assert isinstance(user_id, int)


def test_register_duplicate_username_fails():
    db.register_user("alice", "password123")
    ok, msg = db.register_user("alice", "differentpassword")
    assert ok is False
    assert "already exists" in msg.lower()


def test_register_seeds_default_categories():
    ok, user_id = db.register_user("alice", "password123")
    categories = db.get_categories(user_id)
    for expected in db.DEFAULT_CATEGORIES:
        assert expected in categories


def test_verify_user_correct_password():
    db.register_user("alice", "password123")
    user = db.verify_user("alice", "password123")
    assert user is not None
    assert user["username"] == "alice"


def test_verify_user_wrong_password_returns_none():
    db.register_user("alice", "password123")
    user = db.verify_user("alice", "wrongpassword")
    assert user is None


def test_verify_user_nonexistent_username_returns_none():
    user = db.verify_user("nobody", "whatever")
    assert user is None


def test_password_is_hashed_not_plaintext():
    db.register_user("alice", "password123")
    user = db.verify_user("alice", "password123")
    assert user["password_hash"] != "password123"
    assert len(user["password_hash"]) == 64  # SHA-256 hex digest length


# TRANSACTIONS


def test_add_and_get_transaction(user_id):
    db.add_transaction(user_id, "2026-09-15", "expense", "Food", 500, "Lunch")

    txns = db.get_transactions(user_id)
    assert len(txns) == 1
    assert txns[0]["category"] == "Food"
    assert txns[0]["amount"] == 500


def test_transactions_are_scoped_per_user():
    _, alice_id = db.register_user("alice", "pw1")
    _, bob_id = db.register_user("bob", "pw2")

    db.add_transaction(alice_id, "2026-09-15", "expense", "Food", 500)
    db.add_transaction(bob_id, "2026-09-15", "expense", "Transport", 300)

    alice_txns = db.get_transactions(alice_id)
    bob_txns = db.get_transactions(bob_id)

    assert len(alice_txns) == 1
    assert len(bob_txns) == 1
    assert alice_txns[0]["category"] == "Food"
    assert bob_txns[0]["category"] == "Transport"


def test_update_transaction(user_id):
    db.add_transaction(user_id, "2026-09-15", "expense", "Food", 500)
    txn_id = db.get_transactions(user_id)[0]["id"]

    db.update_transaction(txn_id, "2026-09-16", "expense", "Transport", 750, "Bus fare")

    updated = db.get_transactions(user_id)[0]
    assert updated["category"] == "Transport"
    assert updated["amount"] == 750
    assert updated["note"] == "Bus fare"


def test_delete_transaction(user_id):
    db.add_transaction(user_id, "2026-09-15", "expense", "Food", 500)
    txn_id = db.get_transactions(user_id)[0]["id"]

    db.delete_transaction(txn_id)

    assert db.get_transactions(user_id) == []


# BUDGETS


def test_set_and_get_budget(user_id):
    db.set_budget(user_id, "Food", 5000)

    budgets = db.get_budgets(user_id)
    assert len(budgets) == 1
    assert budgets[0]["category"] == "Food"
    assert budgets[0]["monthly_limit"] == 5000


def test_set_budget_updates_existing_limit(user_id):
    db.set_budget(user_id, "Food", 5000)
    db.set_budget(user_id, "Food", 8000)  # same category -> should update, not duplicate

    budgets = db.get_budgets(user_id)
    assert len(budgets) == 1
    assert budgets[0]["monthly_limit"] == 8000



# SAVINGS GOALS


def test_add_and_get_savings_goal(user_id):
    db.add_savings_goal(user_id, "Emergency Fund", 10000)

    goals = db.get_savings_goals(user_id)
    assert len(goals) == 1
    assert goals[0]["name"] == "Emergency Fund"
    assert goals[0]["saved_amount"] == 0


def test_update_savings_progress(user_id):
    db.add_savings_goal(user_id, "Emergency Fund", 10000)
    goal_id = db.get_savings_goals(user_id)[0]["id"]

    db.update_savings_progress(goal_id, 2500)

    updated = db.get_savings_goals(user_id)[0]
    assert updated["saved_amount"] == 2500



# CATEGORIES


def test_add_category_success(user_id):
    ok, name = db.add_category(user_id, "Gym")
    assert ok is True
    assert name == "Gym"
    assert "Gym" in db.get_categories(user_id)


def test_add_duplicate_category_case_insensitive_fails(user_id):
    db.add_category(user_id, "Gym")
    ok, msg = db.add_category(user_id, "gym")  # same name, different case
    assert ok is False
    assert "already exists" in msg.lower()


def test_add_empty_category_fails(user_id):
    ok, msg = db.add_category(user_id, "   ")
    assert ok is False


def test_delete_category(user_id):
    db.add_category(user_id, "Gym")
    db.delete_category(user_id, "Gym")
    assert "Gym" not in db.get_categories(user_id)
