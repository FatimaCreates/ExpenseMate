"""Transaction business rules (Services layer)."""

from repositories.transaction_repository import TransactionRepository
from services.budget_service import BudgetService
from services.errors import BudgetExceededError
from services.validators import validate_amount, validate_date


class TransactionService:

    def __init__(self, transaction_repo=None, budget_service=None):
        self._transactions = transaction_repo or TransactionRepository()
        self._budgets = budget_service or BudgetService()

    def add_transaction(self, user_id, date, type_, category, amount, note="",
                        enforce_budget=False):
        """Validate and save a transaction.

        With enforce_budget=True an expense that would push its category over
        the monthly budget is rejected with BudgetExceededError (nothing saved).
        """
        validate_amount(amount)
        date = validate_date(date)
        if enforce_budget and type_ == "expense":
            blocked = self._budgets.would_exceed_budget(user_id, category, amount, date[:7])
            if blocked:
                raise BudgetExceededError(blocked)
        self._transactions.add(user_id, date, type_, category, amount, note)

    def list_transactions(self, user_id):
        return self._transactions.list_for_user(user_id)

    def update_transaction(self, txn_id, date, type_, category, amount, note=""):
        self._transactions.update(txn_id, validate_date(date), type_, category, amount, note)

    def delete_transaction(self, txn_id):
        self._transactions.delete(txn_id)
