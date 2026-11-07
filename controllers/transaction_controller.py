from controllers.result import Result
from services.errors import BudgetExceededError
from services.transaction_service import TransactionService


class TransactionController:

    def __init__(self, service=None):
        self._service = service or TransactionService()

    def add_transaction(self, user_id, date, type_, category, amount, note=""):
        """Basic input check -> service -> Result. The budget guard is enforced."""
        if not category or amount is None or amount <= 0:
            return Result(False, "Please select a category and enter an amount greater than 0.",
                          error="validation")
        try:
            self._service.add_transaction(user_id, str(date), type_, category, amount, note,
                                          enforce_budget=True)
        except BudgetExceededError as exc:
            return Result(False, str(exc), data=exc.details, error="budget_exceeded")
        except ValueError as exc:
            return Result(False, str(exc), error="validation")
        return Result(True, f"{type_.capitalize()} added to {category}.")

    def list_transactions(self, user_id):
        return Result(True, data=self._service.list_transactions(user_id))

    def delete_transaction(self, txn_id):
        if not txn_id or txn_id <= 0:
            return Result(False, "Enter a valid transaction ID.", error="validation")
        self._service.delete_transaction(int(txn_id))
        return Result(True, f"Transaction #{int(txn_id)} deleted.")
