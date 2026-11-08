"""
Database layer for ExpenseMate (SQLite).
Responsibilities:
    - connection settings (get_connection) and schema creation (init_db)

All SQL for reading/writing data now lives in repositories/, and the rules in
services/. The functions below this point are thin BACKWARD-COMPATIBLE
wrappers kept so Assignment 01 callers and tests keep working
(see Assignment 02, Part B). New code uses controllers -> services -> repositories.

"""

import sqlite3

DB_NAME = "expensemate.db"
SCHEMA_VERSION = 1   # 1 = category_id foreign keys (migration m001)

from constants import DEFAULT_CATEGORIES, SUPPORTED_CURRENCIES  # noqa: F401 (re-exported)
from schema import SchemaManager


def validate_date(value):
    """Kept for backward compatibility; the rule now lives in services.validators."""
    from services.validators import validate_date as _validate
    return _validate(value)


def get_connection():
    """Create and return a new SQLite connection."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row  # lets us access columns by name
    #bug3 fix
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")   # enforce the foreign keys
    return conn


def init_db():
    """Create all required tables if they do not already exist (see schema.py)."""
    SchemaManager(get_connection, DB_NAME, SCHEMA_VERSION).apply()


# ---------------------------------------------------------------------------
# Legacy API (thin wrappers; lazy imports avoid an import cycle with repositories)
# ---------------------------------------------------------------------------

def _services():
    import services
    return services


# USERS / AUTH

def register_user(username, password, currency="PKR"):
    try:
        return True, _services().UserService().register(username, password, currency)
    except ValueError as exc:
        return False, str(exc)


def verify_user(username, password):
    return _services().UserService().verify(username, password)


def get_user(user_id):
    return _services().UserService().get_user(user_id)


def set_user_currency(user_id, currency):
    _services().UserService().set_currency(user_id, currency)


# TRANSACTIONS

def add_transaction(user_id, date, type_, category, amount, note=""):
    _services().TransactionService().add_transaction(user_id, date, type_, category, amount, note)


def get_transactions(user_id):
    return _services().TransactionService().list_transactions(user_id)


def update_transaction(txn_id, date, type_, category, amount, note=""):
    _services().TransactionService().update_transaction(txn_id, date, type_, category, amount, note)


def delete_transaction(txn_id):
    _services().TransactionService().delete_transaction(txn_id)


# BUDGETS

def set_budget(user_id, category, monthly_limit):
    _services().BudgetService().set_budget(user_id, category, monthly_limit)


def get_budgets(user_id):
    return _services().BudgetService().list_budgets(user_id)


# SAVINGS GOALS

def add_savings_goal(user_id, name, target_amount):
    _services().SavingsService().add_goal(user_id, name, target_amount)


def update_savings_progress(goal_id, saved_amount):
    _services().SavingsService().update_progress(goal_id, saved_amount)


def get_savings_goals(user_id):
    return _services().SavingsService().list_goals(user_id)


# CATEGORIES

def get_categories(user_id):
    return _services().CategoryService().list_names(user_id)


def add_category(user_id, name):
    try:
        return True, _services().CategoryService().add_category(user_id, name)
    except ValueError as exc:
        return False, str(exc)


def delete_category(user_id, name):
    _services().CategoryService().delete_category(user_id, name)


def ensure_default_categories(user_id):
    _services().CategoryService().ensure_defaults(user_id)
