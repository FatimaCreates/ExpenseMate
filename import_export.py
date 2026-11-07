"""
import_export.py
------------------
Handles CSV import and export of transactions for ExpenseMate, scoped to a
specific logged-in user.
"""

import csv

from services.transaction_service import TransactionService

_transactions = TransactionService()

CSV_HEADERS = ["date", "type", "category", "amount", "note"]


def export_transactions_to_csv(user_id, filepath):
    transactions = _transactions.list_transactions(user_id)

    with open(filepath, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        writer.writeheader()
        for t in transactions:
            writer.writerow({
                "date": t["date"],
                "type": t["type"],
                "category": t["category"],
                "amount": t["amount"],
                "note": t.get("note", ""),
            })

    return len(transactions)


def import_transactions_from_csv(user_id, filepath):
    imported = 0
    skipped = 0
    errors = []

    with open(filepath, mode="r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for i, row in enumerate(reader, start=2):
            try:
                date = row["date"].strip()
                type_ = row["type"].strip().lower()
                category = row["category"].strip()
                amount = float(row["amount"])
                note = row.get("note", "").strip()

                if type_ not in ("income", "expense"):
                    raise ValueError(f"invalid type '{type_}'")
                if not date or not category:
                    raise ValueError("missing date or category")

                _transactions.add_transaction(user_id, date, type_, category, amount, note)
                imported += 1

            except (KeyError, ValueError, TypeError) as e:
                skipped += 1
                errors.append(f"Row {i}: {e}")

    return {"imported": imported, "skipped": skipped, "errors": errors}