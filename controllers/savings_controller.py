from controllers.result import Result
from services.savings_service import SavingsService


class SavingsController:

    def __init__(self, service=None):
        self._service = service or SavingsService()

    def add_goal(self, user_id, name, target):
        if not (name or "").strip() or target is None or target <= 0:
            return Result(False, "Please enter a valid goal name and target amount.",
                          error="validation")
        self._service.add_goal(user_id, name.strip(), target)
        return Result(True, f"Savings goal '{name.strip()}' added!")

    def update_progress(self, goal_id, saved_amount):
        self._service.update_progress(goal_id, saved_amount)
        return Result(True, "Progress updated!")

    def list_goals(self, user_id):
        return Result(True, data=self._service.list_goals(user_id))

    def goals_progress(self, user_id):
        return Result(True, data=self._service.goals_progress(user_id))
