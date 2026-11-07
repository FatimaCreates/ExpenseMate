"""Business validation rules (kept out of the database and UI layers)."""

import re
from datetime import date as _date


def validate_amount(amount):
    if amount is None or amount < 0:
        raise ValueError("Amount must be zero or greater.")
    return amount


def validate_monthly_limit(limit):
    if limit is None or limit < 0:
        raise ValueError("Monthly limit must be zero or greater.")
    return limit


def validate_date(value, today=None):
    """Validate and normalise a transaction date.

    Accepts 'YYYY-M-D' / 'YYYY-MM-DD' and returns zero-padded 'YYYY-MM-DD'.
    Raises ValueError for malformed/impossible dates and for future dates.
    `today` can be injected so the rule is testable without the real clock.
    """
    today = today or _date.today()
    text = str(value).strip() if value is not None else ""
    if not re.fullmatch(r"\d{4}-\d{1,2}-\d{1,2}", text):
        raise ValueError(f"Invalid date '{value}'. Use YYYY-MM-DD.")
    year, month, day = (int(part) for part in text.split("-"))
    try:
        parsed = _date(year, month, day)
    except ValueError:
        raise ValueError(f"Invalid date '{value}'. Use YYYY-MM-DD.")
    if parsed > today:
        raise ValueError(f"Date '{parsed.isoformat()}' is in the future.")
    return parsed.isoformat()
