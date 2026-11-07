"""
Tests for migration 001 (category TEXT -> category_id FK) and the new
category-aware database functions.

Each migration test builds a database in the OLD (Assignment 01) schema, runs
the migration, and checks that data is preserved and the new rules hold.
"""

import os
import sqlite3

import pytest

import database as db
from migrations import m001_category_fk as m001

OLD_SCHEMA = """
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    currency TEXT NOT NULL DEFAULT 'PKR'
);
CREATE TABLE transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    type TEXT NOT NULL CHECK(type IN ('income', 'expense')),
    category TEXT NOT NULL,
    amount REAL NOT NULL,
    note TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
CREATE TABLE budgets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    category TEXT NOT NULL,
    monthly_limit REAL NOT NULL,
    UNIQUE(user_id, category),
    FOREIGN KEY (user_id) REFERENCES users(id)
);
CREATE TABLE savings_goals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    target_amount REAL NOT NULL,
    saved_amount REAL NOT NULL DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
CREATE TABLE categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    UNIQUE(user_id, name),
    FOREIGN KEY (user_id) REFERENCES users(id)
);
"""


@pytest.fixture
def old_db(tmp_path):
    """An old-schema database with the exact problems found in Assignment 01."""
    path = str(tmp_path / "old.db")
    conn = sqlite3.connect(path)
    conn.executescript(OLD_SCHEMA)
    conn.execute("INSERT INTO users (id, username, password_hash) VALUES (1, 'a', 'x'), (2, 'b', 'x')")
    for uid in (1, 2):
        for name in ("Food", "Education", "Salary", "Transport"):
            conn.execute("INSERT INTO categories (user_id, name) VALUES (?, ?)", (uid, name))
    rows = [
        # user 1: same category in different spellings
        (1, "2026-09-01", "expense", "Education", 100.0),
        (1, "2026-09-02", "expense", "education", 50.0),
        (1, "2026-09-03", "income", "salary", 2000.0),
        (1, "2026-09-04", "expense", "transport", 30.0),
        # category that is NOT in the categories table (deleted earlier)
        (1, "2026-09-05", "expense", "Gym", 70.0),
        # user 2 has its own data
        (2, "2026-09-01", "expense", "Food", 10.0),
        (2, "2026-09-02", "expense", "FOOD", 5.0),
    ]
    conn.executemany(
        "INSERT INTO transactions (user_id, date, type, category, amount) VALUES (?, ?, ?, ?, ?)", rows)
    conn.execute("INSERT INTO budgets (user_id, category, monthly_limit) VALUES (1, 'Food', 500)")
    conn.execute("INSERT INTO budgets (user_id, category, monthly_limit) VALUES (1, 'education', 300)")
    conn.commit()
    conn.close()
    return path


def _query(path, sql, params=()):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        return conn.execute(sql, params).fetchall()
    finally:
        conn.close()


def _run(path, tmp_path):
    return m001.migrate(path, backup_dir=str(tmp_path / "bk"), log=lambda *_: None)


# ---------------------------------------------------------------------------
# migration behaviour
# ---------------------------------------------------------------------------

def test_old_schema_is_detected(old_db):
    conn = sqlite3.connect(old_db)
    assert m001.is_old_schema(conn) is True
    assert m001.current_version(conn) == 0
    conn.close()


def test_migration_preserves_row_counts_and_totals(old_db, tmp_path):
    before_sum = _query(old_db, "SELECT SUM(amount) s FROM transactions")[0]["s"]
    report = _run(old_db, tmp_path)
    assert report["status"] == "migrated"
    assert _query(old_db, "SELECT COUNT(*) c FROM transactions")[0]["c"] == 7
    assert _query(old_db, "SELECT SUM(amount) s FROM transactions")[0]["s"] == before_sum
    assert _query(old_db, "PRAGMA foreign_key_check") == []


def test_case_duplicates_are_merged_into_one_category(old_db, tmp_path):
    _run(old_db, tmp_path)
    rows = _query(old_db, """
        SELECT c.name AS name, SUM(t.amount) AS total
        FROM transactions t JOIN categories c ON c.id = t.category_id
        WHERE t.user_id = 1 GROUP BY c.id""")
    totals = {r["name"]: r["total"] for r in rows}
    assert totals["Education"] == 150.0      # 'Education' + 'education'
    assert totals["Salary"] == 2000.0        # 'salary' -> existing 'Salary'
    assert totals["Transport"] == 30.0
    assert not any(name.islower() for name in totals)   # no stray lowercase copies


def test_user2_food_spellings_merge_too(old_db, tmp_path):
    _run(old_db, tmp_path)
    rows = _query(old_db, """
        SELECT c.name AS name, SUM(t.amount) AS total FROM transactions t
        JOIN categories c ON c.id = t.category_id WHERE t.user_id = 2 GROUP BY c.id""")
    assert [(r["name"], r["total"]) for r in rows] == [("Food", 15.0)]


def test_missing_category_is_created_not_lost(old_db, tmp_path):
    report = _run(old_db, tmp_path)
    assert report["categories_created"] == 1
    names = [r["name"] for r in _query(old_db, "SELECT name FROM categories WHERE user_id=1")]
    assert "Gym" in names
    gym = _query(old_db, """SELECT t.amount FROM transactions t JOIN categories c
                            ON c.id=t.category_id WHERE c.name='Gym'""")
    assert gym[0]["amount"] == 70.0


def test_budgets_follow_their_category(old_db, tmp_path):
    _run(old_db, tmp_path)
    rows = _query(old_db, """SELECT c.name AS name, b.monthly_limit AS lim FROM budgets b
                             JOIN categories c ON c.id=b.category_id WHERE b.user_id=1""")
    assert {r["name"]: r["lim"] for r in rows} == {"Food": 500.0, "Education": 300.0}


def test_duplicate_budgets_for_same_category_are_merged(old_db, tmp_path):
    conn = sqlite3.connect(old_db)
    conn.execute("INSERT INTO budgets (user_id, category, monthly_limit) VALUES (1, 'EDUCATION', 999)")
    conn.commit()
    conn.close()
    report = _run(old_db, tmp_path)
    assert report["budgets_merged"] == 1
    rows = _query(old_db, """SELECT b.monthly_limit AS lim FROM budgets b
                             JOIN categories c ON c.id=b.category_id
                             WHERE b.user_id=1 AND c.name='Education'""")
    assert [r["lim"] for r in rows] == [999.0]       # most recent row wins


def test_schema_version_is_recorded(old_db, tmp_path):
    _run(old_db, tmp_path)
    conn = sqlite3.connect(old_db)
    assert m001.current_version(conn) == 1
    assert m001.is_old_schema(conn) is False
    conn.close()


def test_backup_is_created_and_contains_old_data(old_db, tmp_path):
    report = _run(old_db, tmp_path)
    assert os.path.exists(report["backup"])
    old_cols = [r["name"] for r in _query(report["backup"], "PRAGMA table_info(transactions)")]
    assert "category" in old_cols and "category_id" not in old_cols


def test_migration_is_idempotent(old_db, tmp_path):
    _run(old_db, tmp_path)
    snapshot = [dict(r) for r in _query(old_db, "SELECT * FROM transactions ORDER BY id")]
    second = _run(old_db, tmp_path)
    assert second["status"] == "already_applied"
    assert [dict(r) for r in _query(old_db, "SELECT * FROM transactions ORDER BY id")] == snapshot


def test_transaction_ids_are_preserved(old_db, tmp_path):
    ids_before = [r["id"] for r in _query(old_db, "SELECT id FROM transactions ORDER BY id")]
    _run(old_db, tmp_path)
    assert [r["id"] for r in _query(old_db, "SELECT id FROM transactions ORDER BY id")] == ids_before


def test_failed_migration_rolls_back_and_leaves_old_data(old_db, tmp_path, monkeypatch):
    def boom(conn, log):
        conn.execute("DROP TABLE transactions")      # destructive step ...
        raise RuntimeError("simulated failure")      # ... then a failure
    monkeypatch.setattr(m001, "_apply", boom)
    with pytest.raises(RuntimeError):
        _run(old_db, tmp_path)
    conn = sqlite3.connect(old_db)
    assert m001.is_old_schema(conn) is True           # still the old schema
    assert conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0] == 7
    conn.close()


def test_empty_database_is_a_noop(tmp_path):
    path = str(tmp_path / "empty.db")
    sqlite3.connect(path).close()
    assert _run(path, tmp_path)["status"] == "empty"


# ---------------------------------------------------------------------------
# app code on the new schema
# ---------------------------------------------------------------------------

def test_fresh_database_is_created_on_latest_schema(user_id):
    conn = sqlite3.connect(db.DB_NAME)
    assert m001.current_version(conn) == 1
    assert m001.is_old_schema(conn) is False
    conn.close()


def test_init_db_refuses_an_unmigrated_database(old_db, monkeypatch):
    monkeypatch.setattr(db, "DB_NAME", old_db)
    with pytest.raises(RuntimeError, match="m001_category_fk"):
        db.init_db()


def test_init_db_works_on_a_migrated_database(old_db, tmp_path, monkeypatch):
    _run(old_db, tmp_path)
    monkeypatch.setattr(db, "DB_NAME", old_db)
    db.init_db()                                      # must not raise
    assert len(db.get_transactions(1)) == 5
    assert {t["category"] for t in db.get_transactions(1)} == {
        "Education", "Salary", "Transport", "Gym"}


def test_add_transaction_reuses_category_case_insensitively(user_id):
    db.add_transaction(user_id, "2026-09-01", "expense", "food", 10)
    db.add_transaction(user_id, "2026-09-02", "expense", "FOOD", 20)
    cats = [c for c in db.get_categories(user_id) if c.lower() == "food"]
    assert cats == ["Food"]                           # still exactly one 'Food'
    assert {t["category"] for t in db.get_transactions(user_id)} == {"Food"}


def test_new_category_from_transaction_is_created_once(user_id):
    db.add_transaction(user_id, "2026-09-01", "expense", "Gym", 10)
    db.add_transaction(user_id, "2026-09-02", "expense", "gym", 20)
    assert [c for c in db.get_categories(user_id) if c.lower() == "gym"] == ["Gym"]


def test_set_budget_matches_category_case_insensitively(user_id):
    db.set_budget(user_id, "food", 500)
    db.set_budget(user_id, "FOOD", 800)
    budgets = db.get_budgets(user_id)
    assert len(budgets) == 1
    assert budgets[0]["category"] == "Food" and budgets[0]["monthly_limit"] == 800


def test_empty_category_is_rejected(user_id):
    with pytest.raises(ValueError, match="Category"):
        db.add_transaction(user_id, "2026-09-01", "expense", "   ", 10)


def test_foreign_keys_are_enforced(user_id):
    conn = db.get_connection()
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO transactions (user_id, date, type, category_id, amount) "
            "VALUES (?, '2026-09-01', 'expense', 99999, 1)", (user_id,))
    conn.close()


def test_unused_category_can_still_be_deleted(user_id):
    db.add_category(user_id, "Hobby")
    db.delete_category(user_id, "Hobby")
    assert "Hobby" not in db.get_categories(user_id)
