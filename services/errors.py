class BudgetExceededError(ValueError):
    """Raised when an expense would push a category over its monthly budget.
    `.details` holds category / spent / amount / limit / over_by."""

    def __init__(self, details):
        self.details = details
        super().__init__(
            f"Transaction would exceed the {details['category']} budget "
            f"(over by {details['over_by']})."
        )
