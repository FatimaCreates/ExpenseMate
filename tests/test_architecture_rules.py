"""
Guards the required dependency direction: Controller -> Services -> Repository -> Database.
Fails if SQL or sqlite3 leaks into controllers/services, or if the upper
layers are reached 'upwards' from a lower layer.
"""

import os
import re

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SQL = re.compile(r"\b(SELECT|INSERT\s+INTO|UPDATE\s+\w+\s+SET|DELETE\s+FROM)\b")  # uppercase SQL only


def _sources(folder):
    base = os.path.join(ROOT, folder)
    for name in sorted(os.listdir(base)):
        if name.endswith(".py"):
            path = os.path.join(base, name)
            yield name, open(path, encoding="utf-8").read()


def test_controllers_and_services_contain_no_sql_or_sqlite():
    for folder in ("controllers", "services"):
        for name, text in _sources(folder):
            assert "sqlite3" not in text, f"{folder}/{name} imports sqlite3"
            assert not SQL.search(text), f"{folder}/{name} contains SQL"
            assert ".execute(" not in text, f"{folder}/{name} executes statements"


def test_repositories_contain_no_business_calculations():
    for name, text in _sources("repositories"):
        assert "sum(" not in text and "defaultdict" not in text, f"{name} does calculations"


def test_dependency_direction_is_downwards_only():
    for name, text in _sources("repositories"):
        assert not re.search(r"^\s*(from|import)\s+(services|controllers)\b", text, re.M), name
    for name, text in _sources("services"):
        assert not re.search(r"^\s*(from|import)\s+controllers\b", text, re.M), name
    for name, text in _sources("controllers"):
        assert not re.search(r"^\s*(from|import)\s+repositories\b", text, re.M), name


def test_app_py_goes_through_controllers_only():
    text = open(os.path.join(ROOT, "app.py"), encoding="utf-8").read()
    forbidden = [f"db.{name}" for name in (
        "add_transaction", "get_transactions", "delete_transaction", "get_budgets", "set_budget",
        "register_user", "verify_user", "set_user_currency", "get_categories", "add_category",
        "ensure_default_categories", "add_savings_goal", "update_savings_progress",
        "get_savings_goals")] + ["logic."]
    for call in forbidden:
        assert call not in text, f"app.py still calls {call}"
    assert text.count("db.") == 1 and "db.init_db()" in text   # only schema start-up


def test_import_export_uses_services_not_database():
    text = open(os.path.join(ROOT, "import_export.py"), encoding="utf-8").read()
    assert "import database" not in text
