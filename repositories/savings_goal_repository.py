"""Data access for the `savings_goals` table. SQL only."""

from repositories._common import connect


class SavingsGoalRepository:

    def add(self, user_id, name, target_amount):
        conn = connect()
        try:
            conn.execute(
                "INSERT INTO savings_goals (user_id, name, target_amount, saved_amount) "
                "VALUES (?, ?, ?, 0)",
                (user_id, name, target_amount),
            )
            conn.commit()
        finally:
            conn.close()

    def update_saved(self, goal_id, saved_amount):
        conn = connect()
        try:
            conn.execute("UPDATE savings_goals SET saved_amount = ? WHERE id = ?",
                         (saved_amount, goal_id))
            conn.commit()
        finally:
            conn.close()

    def list_for_user(self, user_id):
        conn = connect()
        try:
            rows = conn.execute("SELECT * FROM savings_goals WHERE user_id = ?",
                                (user_id,)).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()
