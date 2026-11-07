"""Helpers shared by the repositories (connection access + category lookup)."""

import database


def connect():
    """Open a connection through the Database layer.

    database.get_connection is looked up on every call (not imported by
    name) so a changed database.DB_NAME - e.g. the temp DB used by the tests -
    is always respected.
    """
    return database.get_connection()


def resolve_category_id(cur, user_id, name):
    """Return the id of this user's category `name` (case-insensitive),
    creating it if it does not exist yet, so 'food' and 'Food' stay ONE category."""
    name = (name or "").strip()
    if not name:
        raise ValueError("Category cannot be empty.")
    row = cur.execute(
        "SELECT id FROM categories WHERE user_id = ? AND name = ? COLLATE NOCASE",
        (user_id, name),
    ).fetchone()
    if row:
        return row["id"]
    cur.execute("INSERT INTO categories (user_id, name) VALUES (?, ?)", (user_id, name))
    return cur.lastrowid
