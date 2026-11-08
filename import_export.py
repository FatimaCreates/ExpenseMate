"""
import_export.py  (rewritten in Assignment 02, Part C)
------------------------------------------------------
CSV import and export of one user's transactions.

The old module was a single 30-line import function that opened the file,
parsed every field, validated the values and saved the row, using a service
object created at import time. It is now four small classes, each with one job:

    TransactionCsvParser    one CSV row (dict)  -> ParsedRow, or ValueError  (pure)
    TransactionCsvImporter  reads rows, parses them, saves them via the service
    TransactionCsvExporter  writes a user's transactions to a CSV file
    ParsedRow               the clean result of parsing one row

The two module-level functions at the bottom keep the old public API, so
app.py and the Assignment 01 tests are unchanged. This module still reaches
data only through TransactionService (Controller -> Services -> Repository).
"""

import csv
import math
from dataclasses import dataclass

from services.transaction_service import TransactionService

CSV_HEADERS = ["date", "type", "category", "amount", "note"]
TRANSACTION_TYPES = ("income", "expense")
_REQUIRED_COLUMNS = ("date", "type", "category", "amount")
_FIRST_DATA_LINE = 2          # line 1 of the file is the header


@dataclass(frozen=True)
class ParsedRow:
    date: str
    type_: str
    category: str
    amount: float
    note: str = ""


class TransactionCsvParser:
    """Turns one CSV row (a dict) into a ParsedRow. No file and no database
    are involved, so every rule can be unit-tested with plain dicts."""

    def parse(self, row):
        """Raises ValueError with a readable message if the row is unusable.
        Business rules (future dates, negative amounts) stay in the service."""
        values = {name: self._text(row, name) for name in _REQUIRED_COLUMNS}
        if not values["date"] or not values["category"]:
            raise ValueError("missing date or category")
        return ParsedRow(
            date=values["date"],
            type_=self._parse_type(values["type"]),
            category=values["category"],
            amount=self._parse_amount(values["amount"]),
            note=(row.get("note") or "").strip(),
        )

    @staticmethod
    def _text(row, column):
        if column not in row:
            raise ValueError(f"missing column '{column}'")
        return (row[column] or "").strip()      # a short row gives None, not ""

    @staticmethod
    def _parse_type(text):
        type_ = text.lower()
        if type_ not in TRANSACTION_TYPES:
            raise ValueError(f"invalid type '{type_}'")
        return type_

    @staticmethod
    def _parse_amount(text):
        try:
            amount = float(text)
        except ValueError:
            raise ValueError(f"invalid amount '{text}'")
        if not math.isfinite(amount):
            raise ValueError(f"invalid amount '{text}'")
        return amount


class TransactionCsvImporter:
    """Reads a CSV file and saves each valid row; bad rows are skipped and reported."""

    def __init__(self, service=None, parser=None):
        self._transactions = service or TransactionService()
        self._parser = parser or TransactionCsvParser()

    def import_file(self, user_id, filepath):
        with open(filepath, mode="r", newline="", encoding="utf-8") as f:
            return self.import_rows(user_id, csv.DictReader(f))

    def import_rows(self, user_id, rows):
        """rows: any iterable of dicts. Returns {"imported", "skipped", "errors"}."""
        imported, errors = 0, []
        for line_no, row in enumerate(rows, start=_FIRST_DATA_LINE):
            try:
                parsed = self._parser.parse(row)
                self._transactions.add_transaction(
                    user_id, parsed.date, parsed.type_, parsed.category,
                    parsed.amount, parsed.note)
                imported += 1
            except ValueError as exc:
                errors.append(f"Row {line_no}: {exc}")
        return {"imported": imported, "skipped": len(errors), "errors": errors}


class TransactionCsvExporter:
    """Writes all of one user's transactions to a CSV file."""

    def __init__(self, service=None):
        self._transactions = service or TransactionService()

    def export(self, user_id, filepath):
        """Returns the number of transactions written."""
        transactions = self._transactions.list_transactions(user_id)
        with open(filepath, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
            writer.writeheader()
            for t in transactions:
                writer.writerow({
                    "date": t["date"], "type": t["type"], "category": t["category"],
                    "amount": t["amount"], "note": t.get("note") or "",
                })
        return len(transactions)


# ---------------------------------------------------------------------------
# Public API kept from Assignment 01 (used by app.py and the existing tests)
# ---------------------------------------------------------------------------

def export_transactions_to_csv(user_id, filepath):
    return TransactionCsvExporter().export(user_id, filepath)


def import_transactions_from_csv(user_id, filepath):
    return TransactionCsvImporter().import_file(user_id, filepath)
