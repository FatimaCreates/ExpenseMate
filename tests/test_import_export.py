"""
test_import_export.py
-----------------------
Unit tests for import_export.py (Support / Utility Layer).

Covers:
    - Exporting a user's transactions to a CSV file, with correct headers
      and row counts.
    - Importing valid rows from a CSV file into the database.
    - Skipping and reporting invalid rows (bad type, missing fields, bad
      amount) without crashing the whole import.
"""

import os
import csv
import tempfile

import database as db
import import_export as ie


def _read_csv_rows(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))



# EXPORT


def test_export_creates_csv_with_correct_headers(user_id, tmp_path):
    db.add_transaction(user_id, "2026-09-15", "expense", "Food", 500, "Lunch")
    out_path = tmp_path / "export.csv"

    count = ie.export_transactions_to_csv(user_id, str(out_path))

    assert count == 1
    assert out_path.exists()
    rows = _read_csv_rows(str(out_path))
    assert rows[0]["category"] == "Food"
    assert rows[0]["amount"] == "500.0"


def test_export_with_no_transactions_still_writes_header_only(user_id, tmp_path):
    out_path = tmp_path / "export.csv"

    count = ie.export_transactions_to_csv(user_id, str(out_path))

    assert count == 0
    rows = _read_csv_rows(str(out_path))
    assert rows == []


def test_export_only_includes_the_given_users_transactions(tmp_path):
    _, alice_id = db.register_user("alice", "pw1")
    _, bob_id = db.register_user("bob", "pw2")
    db.add_transaction(alice_id, "2026-09-15", "expense", "Food", 500)
    db.add_transaction(bob_id, "2026-09-15", "expense", "Transport", 300)

    out_path = tmp_path / "alice_export.csv"
    count = ie.export_transactions_to_csv(alice_id, str(out_path))

    assert count == 1
    rows = _read_csv_rows(str(out_path))
    assert rows[0]["category"] == "Food"


# IMPORT — valid data


def test_import_valid_rows(user_id, tmp_path):
    csv_path = tmp_path / "import.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=ie.CSV_HEADERS)
        writer.writeheader()
        writer.writerow({"date": "2026-09-15", "type": "expense", "category": "Food", "amount": "500", "note": "Lunch"})
        writer.writerow({"date": "2026-09-16", "type": "income", "category": "Salary", "amount": "50000", "note": ""})

    result = ie.import_transactions_from_csv(user_id, str(csv_path))

    assert result["imported"] == 2
    assert result["skipped"] == 0
    assert len(db.get_transactions(user_id)) == 2


# IMPORT — invalid data should be skipped, not crash the whole import


def test_import_skips_invalid_type(user_id, tmp_path):
    csv_path = tmp_path / "import.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=ie.CSV_HEADERS)
        writer.writeheader()
        writer.writerow({"date": "2026-09-15", "type": "refund", "category": "Food", "amount": "500", "note": ""})

    result = ie.import_transactions_from_csv(user_id, str(csv_path))

    assert result["imported"] == 0
    assert result["skipped"] == 1
    assert "invalid type" in result["errors"][0]


def test_import_skips_missing_category(user_id, tmp_path):
    csv_path = tmp_path / "import.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=ie.CSV_HEADERS)
        writer.writeheader()
        writer.writerow({"date": "2026-09-15", "type": "expense", "category": "", "amount": "500", "note": ""})

    result = ie.import_transactions_from_csv(user_id, str(csv_path))

    assert result["imported"] == 0
    assert result["skipped"] == 1


def test_import_skips_non_numeric_amount(user_id, tmp_path):
    csv_path = tmp_path / "import.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=ie.CSV_HEADERS)
        writer.writeheader()
        writer.writerow({"date": "2026-09-15", "type": "expense", "category": "Food", "amount": "not_a_number", "note": ""})

    result = ie.import_transactions_from_csv(user_id, str(csv_path))

    assert result["imported"] == 0
    assert result["skipped"] == 1


def test_import_continues_after_a_bad_row(user_id, tmp_path):
    """One bad row in the middle should not stop the good rows around it."""
    csv_path = tmp_path / "import.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=ie.CSV_HEADERS)
        writer.writeheader()
        writer.writerow({"date": "2026-09-15", "type": "expense", "category": "Food", "amount": "500", "note": ""})
        writer.writerow({"date": "2026-09-16", "type": "invalid_type", "category": "Food", "amount": "200", "note": ""})
        writer.writerow({"date": "2026-09-17", "type": "income", "category": "Salary", "amount": "1000", "note": ""})

    result = ie.import_transactions_from_csv(user_id, str(csv_path))

    assert result["imported"] == 2
    assert result["skipped"] == 1
    assert len(db.get_transactions(user_id)) == 2
