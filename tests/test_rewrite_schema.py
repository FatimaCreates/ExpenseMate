"""
test_rewrite_schema.py  (Assignment 02, Part C - rewritten init_db -> SchemaManager)
Tests the new class on throw-away SQLite files, and that database.init_db() delegates to it.
"""
import sqlite3

import pytest

import database as db
from schema import LATER_COLUMNS, TABLE_DDL, SchemaManager

ALL_TABLES = {"users", "transactions", "budgets", "savings_goals", "categories", "schema_version"}


def manager(path, version=1):
    return SchemaManager(lambda: sqlite3.connect(path), str(path), version)


def tables(path):
    c = sqlite3.connect(path)
    try:
        return {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")} - {"sqlite_sequence"}
    finally:
        c.close()


def columns(path, table):
    c = sqlite3.connect(path)
    try:
        return {r[1] for r in c.execute(f"PRAGMA table_info({table})")}
    finally:
        c.close()


def test_fresh_database_gets_every_table_and_a_version_row(tmp_path):
    path = tmp_path / "a.db"
    manager(path).apply()
    assert tables(path) == ALL_TABLES == set(TABLE_DDL)
    c = sqlite3.connect(path)
    assert c.execute("SELECT version, description FROM schema_version").fetchall() == [(1, "created with latest schema")]
    c.close()


def test_apply_twice_changes_nothing(tmp_path):
    path = tmp_path / "a.db"
    manager(path).apply()
    c = sqlite3.connect(path)
    c.execute("INSERT INTO users (username, password_hash) VALUES ('u', 'h')")
    c.commit(); c.close()
    manager(path).apply()
    c = sqlite3.connect(path)
    assert c.execute("SELECT username FROM users").fetchall() == [("u",)]
    assert c.execute("SELECT COUNT(*) FROM schema_version").fetchone()[0] == 1
    c.close()


def test_users_table_without_currency_gets_the_column_and_keeps_its_rows(tmp_path):
    path = tmp_path / "a.db"
    c = sqlite3.connect(path)
    c.execute("CREATE TABLE users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL)")
    c.execute("INSERT INTO users (username, password_hash) VALUES ('old', 'hash')")
    c.commit(); c.close()
    manager(path).apply()
    assert "currency" in columns(path, "users")
    c = sqlite3.connect(path)
    assert c.execute("SELECT username, currency FROM users").fetchall() == [("old", "PKR")]
    c.close()


def test_old_free_text_schema_is_refused_with_the_migration_command(tmp_path):
    path = tmp_path / "a.db"
    c = sqlite3.connect(path)
    c.execute("CREATE TABLE transactions (id INTEGER PRIMARY KEY, user_id INTEGER, date TEXT, type TEXT, category TEXT, amount REAL)")
    c.commit(); c.close()
    with pytest.raises(RuntimeError) as err:
        manager(path).apply()
    assert "old schema" in str(err.value)
    assert f"python migrations/m001_category_fk.py --db {path}" in str(err.value)
    assert tables(path) == {"transactions"}                    # nothing else was created


def test_existing_current_database_is_not_stamped_again(tmp_path):
    path = tmp_path / "a.db"
    manager(path).apply()
    c = sqlite3.connect(path)
    c.execute("DELETE FROM schema_version"); c.commit(); c.close()
    manager(path, version=99).apply()                          # not fresh -> no new version row
    c = sqlite3.connect(path)
    assert c.execute("SELECT COUNT(*) FROM schema_version").fetchone()[0] == 0
    c.close()


def test_connection_is_closed_and_rolled_back_when_something_fails():
    events = []

    class Cur:
        def execute(self, sql, *a):
            raise sqlite3.OperationalError("disk full")

    class Conn:
        def cursor(self): return Cur()
        def commit(self): events.append("commit")
        def rollback(self): events.append("rollback")
        def close(self): events.append("close")

    with pytest.raises(sqlite3.OperationalError):
        SchemaManager(lambda: Conn(), "x.db", 1).apply()
    assert events == ["rollback", "close"]


def test_connection_is_closed_after_a_successful_run(tmp_path):
    events = []
    real = sqlite3.connect(tmp_path / "a.db")

    class Spy:
        def __getattr__(self, name): return getattr(real, name)
        def close(self): events.append("close"); real.close()

    SchemaManager(lambda: Spy(), "a.db", 1).apply()
    assert events == ["close"]


def test_database_init_db_delegates_and_uses_the_current_db_name(tmp_path, monkeypatch):
    path = str(tmp_path / "other.db")
    monkeypatch.setattr(db, "DB_NAME", path)
    db.init_db()
    assert tables(path) == ALL_TABLES


def test_ddl_matches_what_the_repositories_expect():
    assert {"id", "user_id", "date", "type", "category_id", "amount", "note"} <= set(
        c.split()[0] for c in [l.strip() for l in TABLE_DDL["transactions"].splitlines()] if c and c[0].islower())
    assert LATER_COLUMNS == [("users", "currency", "TEXT NOT NULL DEFAULT 'PKR'")]
