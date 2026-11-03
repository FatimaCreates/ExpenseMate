"""
conftest.py
------------
Shared pytest fixtures for the ExpenseMate test suite.

Putting fixtures here means every test_*.py file in this folder can use
`temp_db` and `user_id` without re-defining them — pytest auto-discovers
this file.
"""

import os
import sys
import tempfile
import pytest

# Make sure the project root (one level up from tests/) is importable,
# since app.py / logic.py / database.py / import_export.py live there.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import database as db


@pytest.fixture(autouse=True)
def temp_db(monkeypatch):
    """
    Point database.py at a brand-new temporary SQLite file for every test,
    so tests never touch the real expensemate.db and never leak state
    between tests.
    """
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    monkeypatch.setattr(db, "DB_NAME", path)
    db.init_db()
    yield
    os.remove(path)


@pytest.fixture
def user_id():
    """A ready-to-use registered user for tests that need one."""
    _, uid = db.register_user("alice", "password123")
    return uid
