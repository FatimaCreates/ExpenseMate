"""Data access for the `users` table. SQL only (no hashing, no validation)."""

import sqlite3

from repositories._common import connect
from repositories.errors import DuplicateRecordError


class UserRepository:

    def create(self, username, password_hash, currency):
        conn = connect()
        try:
            cur = conn.execute(
                "INSERT INTO users (username, password_hash, currency) VALUES (?, ?, ?)",
                (username, password_hash, currency),
            )
            conn.commit()
            return cur.lastrowid
        except sqlite3.IntegrityError:
            raise DuplicateRecordError(username)
        finally:
            conn.close()

    def find_by_username(self, username):
        conn = connect()
        try:
            row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def find_by_id(self, user_id):
        conn = connect()
        try:
            row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def update_currency(self, user_id, currency):
        conn = connect()
        try:
            conn.execute("UPDATE users SET currency = ? WHERE id = ?", (currency, user_id))
            conn.commit()
        finally:
            conn.close()
