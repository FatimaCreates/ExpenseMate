"""
Handles all interaction with the SQLite database for ExpenseMate.
Responsibilities:
    - Creating the database and tables (schema) if they don't exist
    - CRUD operations for users (register / login)
    - CRUD operations for transactions, budgets, savings goals, and categories

"""

import sqlite3
import hashlib

DB_NAME = "expensemate.db"

DEFAULT_CATEGORIES = [
    "Food",
    "Transport",
    "Salary",
    "Bills",
    "Rent",
    "Entertainment",
    "Health",
    "Shopping",
    "Education",
    "Other",
]

SUPPORTED_CURRENCIES = {
    "PKR": "Rs.",
    "USD": "$",
    "EUR": "€",
    "GBP": "£",
}


def get_connection():
    """Create and return a new SQLite connection."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row  # lets us access columns by name
    #bug3 fix
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def init_db():
    """Create all required tables if they do not already exist."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            currency TEXT NOT NULL DEFAULT 'PKR'
        )
    """)

    # Migration: add the currency column for databases created before
    # multi-currency support existed (CREATE TABLE IF NOT EXISTS above
    # won't add it to an already-existing users table).
    try:
        cur.execute("ALTER TABLE users ADD COLUMN currency TEXT NOT NULL DEFAULT 'PKR'")
    except sqlite3.OperationalError:
        pass  # column already exists

    cur.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            type TEXT NOT NULL CHECK(type IN ('income', 'expense')),
            category TEXT NOT NULL,
            amount REAL NOT NULL,
            note TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS budgets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            category TEXT NOT NULL,
            monthly_limit REAL NOT NULL,
            UNIQUE(user_id, category),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS savings_goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            target_amount REAL NOT NULL,
            saved_amount REAL NOT NULL DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # NEW: categories table. Each user has their own list of categories
    # (starting from DEFAULT_CATEGORIES) so Add Transaction / Budgets can use
    # a dropdown instead of free text, avoiding duplicate categories that
    # differ only by capitalization or spelling (e.g. "Food" vs "food").
    cur.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            UNIQUE(user_id, name),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    conn.commit()
    conn.close()



# USERS / AUTH

def _hash_password(password):
    """Return a SHA-256 hash of the password. We never store plain text."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def register_user(username, password, currency="PKR"):
    if currency not in SUPPORTED_CURRENCIES:
        currency = "PKR"

    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO users (username, password_hash, currency) VALUES (?, ?, ?)",
            (username, _hash_password(password), currency),
        )
        conn.commit()
        user_id = cur.lastrowid

        # Seed default categories for this brand-new user.
        for name in DEFAULT_CATEGORIES:
            try:
                cur.execute(
                    "INSERT INTO categories (user_id, name) VALUES (?, ?)",
                    (user_id, name),
                )
            except sqlite3.IntegrityError:
                pass
        conn.commit()

        return True, user_id
    except sqlite3.IntegrityError:
        return False, "Username already exists."
    finally:
        conn.close()


def verify_user(username, password):
    """
    Check username/password against the database.
    Returns the user's dict if valid, otherwise None.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username = ?", (username,))
    row = cur.fetchone()
    conn.close()

    if row and row["password_hash"] == _hash_password(password):
        return dict(row)
    return None


def get_user(user_id):
    """Fetch a single user's info by id."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None

def set_user_currency(user_id, currency):
    """Update a user's display currency (no conversion of existing amounts)."""
    if currency not in SUPPORTED_CURRENCIES:
        raise ValueError(f"Unsupported currency '{currency}'.")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE users SET currency=? WHERE id=?", (currency, user_id))
    conn.commit()
    conn.close()

# ---------------------------------------------------------------------------
# TRANSACTIONS
# ---------------------------------------------------------------------------

def add_transaction(user_id, date, type_, category, amount, note=""):
    if amount is None or amount < 0:
        raise ValueError("Amount must be zero or greater.") #bug1 fix
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO transactions (user_id, date, type, category, amount, note) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, date, type_, category, amount, note),
    )
    conn.commit()
    conn.close()


def get_transactions(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM transactions WHERE user_id = ? ORDER BY date DESC, id DESC",
        (user_id,),
    )
    rows = cur.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def update_transaction(txn_id, date, type_, category, amount, note=""):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """UPDATE transactions
           SET date=?, type=?, category=?, amount=?, note=?
           WHERE id=?""",
        (date, type_, category, amount, note, txn_id),
    )
    conn.commit()
    conn.close()


def delete_transaction(txn_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM transactions WHERE id=?", (txn_id,))
    conn.commit()
    conn.close()


# BUDGETS


def set_budget(user_id, category, monthly_limit):
    if monthly_limit is None or monthly_limit < 0:
        raise ValueError("Monthly limit must be zero or greater.")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO budgets (user_id, category, monthly_limit)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id, category) DO UPDATE SET monthly_limit=excluded.monthly_limit
    """, (user_id, category, monthly_limit))
    conn.commit()
    conn.close()


def get_budgets(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM budgets WHERE user_id = ?", (user_id,))
    rows = cur.fetchall()
    conn.close()
    return [dict(row) for row in rows]


# SAVINGS GOALS


def add_savings_goal(user_id, name, target_amount):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO savings_goals (user_id, name, target_amount, saved_amount) VALUES (?, ?, ?, 0)",
        (user_id, name, target_amount),
    )
    conn.commit()
    conn.close()


def update_savings_progress(goal_id, saved_amount):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE savings_goals SET saved_amount=? WHERE id=?",
        (saved_amount, goal_id),
    )
    conn.commit()
    conn.close()


def get_savings_goals(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM savings_goals WHERE user_id = ?", (user_id,))
    rows = cur.fetchall()
    conn.close()
    return [dict(row) for row in rows]


# CATEGORIES


def get_categories(user_id):
    """Return a sorted list of category names (strings) that belong to this user."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT name FROM categories WHERE user_id = ? ORDER BY name COLLATE NOCASE", (user_id,))
    rows = cur.fetchall()
    conn.close()
    return [row["name"] for row in rows]


def add_category(user_id, name):
    """
    Add a new category for this user. Returns (True, name) on success,
    or (False, error_message) if it already exists (case-insensitively).
    """
    name = name.strip()
    if not name:
        return False, "Category name cannot be empty."

    existing = {c.lower() for c in get_categories(user_id)}
    if name.lower() in existing:
        return False, f"Category '{name}' already exists."

    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO categories (user_id, name) VALUES (?, ?)",
            (user_id, name),
        )
        conn.commit()
        return True, name
    except sqlite3.IntegrityError:
        return False, f"Category '{name}' already exists."
    finally:
        conn.close()


def delete_category(user_id, name):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM categories WHERE user_id = ? AND name = ?", (user_id, name))
    conn.commit()
    conn.close()


def ensure_default_categories(user_id):
    """
    Make sure this user has at least the default categories. Useful for
    users who registered before the categories table existed.
    """
    existing = {c.lower() for c in get_categories(user_id)}
    conn = get_connection()
    cur = conn.cursor()
    for name in DEFAULT_CATEGORIES:
        if name.lower() not in existing:
            try:
                cur.execute(
                    "INSERT INTO categories (user_id, name) VALUES (?, ?)",
                    (user_id, name),
                )
            except sqlite3.IntegrityError:
                pass
    conn.commit()
    conn.close()