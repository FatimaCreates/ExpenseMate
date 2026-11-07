"""Data access for the `categories` table. SQL only."""

import sqlite3

from repositories._common import connect
from repositories.errors import DuplicateRecordError


class CategoryRepository:

    def list_names(self, user_id):
        conn = connect()
        try:
            rows = conn.execute(
                "SELECT name FROM categories WHERE user_id = ? ORDER BY name COLLATE NOCASE",
                (user_id,),
            ).fetchall()
            return [r["name"] for r in rows]
        finally:
            conn.close()

    def add(self, user_id, name):
        conn = connect()
        try:
            conn.execute("INSERT INTO categories (user_id, name) VALUES (?, ?)", (user_id, name))
            conn.commit()
        except sqlite3.IntegrityError:
            raise DuplicateRecordError(name)
        finally:
            conn.close()

    def add_many_ignoring_duplicates(self, user_id, names):
        conn = connect()
        try:
            for name in names:
                try:
                    conn.execute("INSERT INTO categories (user_id, name) VALUES (?, ?)",
                                 (user_id, name))
                except sqlite3.IntegrityError:
                    pass
            conn.commit()
        finally:
            conn.close()

    def find_id(self, user_id, name):
        conn = connect()
        try:
            row = conn.execute("SELECT id FROM categories WHERE user_id = ? AND name = ?",
                               (user_id, name)).fetchone()
            return row["id"] if row else None
        finally:
            conn.close()

    def usage_count(self, category_id):
        """How many transactions + budgets still point at this category."""
        conn = connect()
        try:
            return conn.execute(
                "SELECT (SELECT COUNT(*) FROM transactions WHERE category_id = ?) "
                "     + (SELECT COUNT(*) FROM budgets WHERE category_id = ?)",
                (category_id, category_id),
            ).fetchone()[0]
        finally:
            conn.close()

    def delete(self, user_id, name):
        conn = connect()
        try:
            conn.execute("DELETE FROM categories WHERE user_id = ? AND name = ?", (user_id, name))
            conn.commit()
        finally:
            conn.close()
