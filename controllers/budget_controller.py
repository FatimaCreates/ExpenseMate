from controllers.result import Result
from services.budget_service import BudgetService


class BudgetController:

    def __init__(self, service=None):
        self._service = service or BudgetService()

    def monthly_summary(self, user_id, year_month=None):
        """Monthly Budget Summary: totals, category spending, progress and alerts."""
        return Result(True, data=self._service.monthly_budget_report(user_id, year_month))

    def set_budget(self, user_id, category, limit):
        if not category or limit is None or limit <= 0:
            return Result(False, "Please select a category and enter a limit greater than 0.",
                          error="validation")
        try:
            self._service.set_budget(user_id, category, limit)
        except ValueError as exc:
            return Result(False, str(exc), error="validation")
        return Result(True, f"Budget for {category} set.")

    def list_budgets(self, user_id):
        return Result(True, data=self._service.list_budgets(user_id))
