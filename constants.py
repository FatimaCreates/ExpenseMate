"""Shared constants (kept out of database.py so services can use them
without depending on the Database layer)."""

DEFAULT_CATEGORIES = [
    "Food", "Transport", "Salary", "Bills", "Rent",
    "Entertainment", "Health", "Shopping", "Education", "Other",
]

SUPPORTED_CURRENCIES = {
    "PKR": "Rs.",
    "USD": "$",
    "EUR": "€",
    "GBP": "£",
}
