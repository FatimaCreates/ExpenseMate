"""Data access for the `budgets` table. SQL only."""

from repositories._common import connect, resolve_category_id


class BudgetRepository:

    def upsert(self, user_id, category, monthly_limit):
        conn = connect()
        try:
            cur = conn.cursor()
            category_id = resolve_category_id(cur, user_id, category)
            cur.execute(
                """INSERT INTO budgets (user_id, category_id, monthly_limit)
                   VALUES (?, ?, ?)
                   ON CONFLICT(user_id, category_id)
                   DO UPDATE SET monthly_limit = excluded.monthly_limit""",
                (user_id, category_id, monthly_limit),
            )
            conn.commit()
        finally:
            conn.close()

    def list_for_user(self, user_id):
        conn = connect()
        try:
            rows = conn.execute(
                """SELECT b.id, b.user_id, c.name AS category, b.category_id, b.monthly_limit
                   FROM budgets b
                   JOIN categories c ON c.id = b.category_id
                   WHERE b.user_id = ?""",
                (user_id,),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()
