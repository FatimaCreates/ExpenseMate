"""Savings-goal rules and progress calculation (Services layer)."""

from repositories.savings_goal_repository import SavingsGoalRepository


class SavingsService:

    def __init__(self, goal_repo=None):
        self._goals = goal_repo or SavingsGoalRepository()

    def add_goal(self, user_id, name, target_amount):
        self._goals.add(user_id, name, target_amount)

    def update_progress(self, goal_id, saved_amount):
        self._goals.update_saved(goal_id, saved_amount)

    def list_goals(self, user_id):
        return self._goals.list_for_user(user_id)

    def goals_progress(self, user_id):
        result = []
        for g in self._goals.list_for_user(user_id):
            percent = (round((g["saved_amount"] / g["target_amount"]) * 100, 1)
                       if g["target_amount"] > 0 else 0)
            result.append({
                "id": g["id"], "name": g["name"],
                "saved_amount": g["saved_amount"], "target_amount": g["target_amount"],
                "percent": min(percent, 100),
            })
        return result
