"""Data access for the `transactions` table. SQL only - no business rules,
no totals, no validation."""

from repositories._common import connect, resolve_category_id

_SELECT = """SELECT t.id, t.user_id, t.date, t.type, c.name AS category,
                    t.category_id, t.amount, t.note
             FROM transactions t
             JOIN categories c ON c.id = t.category_id"""


class TransactionRepository:

    def add(self, user_id, date, type_, category, amount, note=""):
        conn = connect()
        try:
            cur = conn.cursor()
            category_id = resolve_category_id(cur, user_id, category)
            cur.execute(
                "INSERT INTO transactions (user_id, date, type, category_id, amount, note) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, date, type_, category_id, amount, note),
            )
            conn.commit()
        finally:
            conn.close()

    def list_for_user(self, user_id):
        conn = connect()
        try:
            rows = conn.execute(
                _SELECT + " WHERE t.user_id = ? ORDER BY t.date DESC, t.id DESC",
                (user_id,),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def list_for_month(self, user_id, year_month):
        """Raw rows whose date starts with 'YYYY-MM' (filtered in SQL, not in Python)."""
        conn = connect()
        try:
            rows = conn.execute(
                _SELECT + " WHERE t.user_id = ? AND substr(t.date, 1, ?) = ?"
                          " ORDER BY t.date DESC, t.id DESC",
                (user_id, len(year_month), year_month),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def update(self, txn_id, date, type_, category, amount, note=""):
        conn = connect()
        try:
            cur = conn.cursor()
            owner = cur.execute(
                "SELECT user_id FROM transactions WHERE id = ?", (txn_id,)
            ).fetchone()
            if owner is None:
                return
            category_id = resolve_category_id(cur, owner["user_id"], category)
            cur.execute(
                "UPDATE transactions SET date=?, type=?, category_id=?, amount=?, note=? "
                "WHERE id=?",
                (date, type_, category_id, amount, note, txn_id),
            )
            conn.commit()
        finally:
            conn.close()

    def delete(self, txn_id):
        conn = connect()
        try:
            conn.execute("DELETE FROM transactions WHERE id = ?", (txn_id,))
            conn.commit()
        finally:
            conn.close()
