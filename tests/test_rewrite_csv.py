"""
test_rewrite_csv.py  (Assignment 02, Part C - rewritten import_export.py)
Unit tests for TransactionCsvParser / Importer / Exporter. Most tests use a fake
service, so they need no database; the last ones check the old public API.
"""
import csv
import math

import pytest

import database as db
import import_export as ie
from import_export import (ParsedRow, TransactionCsvExporter, TransactionCsvImporter,
                           TransactionCsvParser)


class FakeService:
    """Stands in for TransactionService: records saves, can reject chosen amounts."""

    def __init__(self, transactions=None, reject_amount=None):
        self.saved, self._transactions, self._reject = [], transactions or [], reject_amount

    def add_transaction(self, user_id, date, type_, category, amount, note=""):
        if amount == self._reject:
            raise ValueError("Amount must be zero or greater.")
        self.saved.append((user_id, date, type_, category, amount, note))

    def list_transactions(self, user_id):
        return self._transactions


def row(**over):
    base = {"date": "2026-01-05", "type": "expense", "category": "Food", "amount": "12.5", "note": "lunch"}
    base.update(over)
    return base


# ----------------------------------------------------------------- parser
def test_parser_returns_clean_parsed_row():
    assert TransactionCsvParser().parse(row()) == ParsedRow("2026-01-05", "expense", "Food", 12.5, "lunch")


def test_parser_strips_spaces_and_lowercases_type():
    parsed = TransactionCsvParser().parse(row(date=" 2026-01-05 ", type=" EXPENSE ", category=" Food ", note=" hi "))
    assert (parsed.date, parsed.type_, parsed.category, parsed.note) == ("2026-01-05", "expense", "Food", "hi")


def test_parser_accepts_short_row_where_note_is_none():
    parsed = TransactionCsvParser().parse(row(note=None))      # csv.DictReader gives None for a missing last column
    assert parsed.note == ""


@pytest.mark.parametrize("column", ["date", "type", "category", "amount"])
def test_parser_reports_a_missing_column_by_name(column):
    bad = row(); del bad[column]
    with pytest.raises(ValueError, match=f"missing column '{column}'"):
        TransactionCsvParser().parse(bad)


@pytest.mark.parametrize("field", ["date", "category"])
def test_parser_rejects_blank_date_or_category(field):
    with pytest.raises(ValueError, match="missing date or category"):
        TransactionCsvParser().parse(row(**{field: "  "}))


def test_parser_rejects_unknown_type():
    with pytest.raises(ValueError, match="invalid type 'transfer'"):
        TransactionCsvParser().parse(row(type="Transfer"))


@pytest.mark.parametrize("bad_amount", ["", "abc", "nan", "inf", "-inf", None])
def test_parser_rejects_non_numeric_and_non_finite_amounts(bad_amount):
    with pytest.raises(ValueError, match="invalid amount"):
        TransactionCsvParser().parse(row(amount=bad_amount))


def test_parser_leaves_negative_amounts_to_the_service():
    assert TransactionCsvParser().parse(row(amount="-5")).amount == -5.0


# --------------------------------------------------------------- importer
def test_importer_saves_valid_rows_through_the_service():
    service = FakeService()
    result = TransactionCsvImporter(service).import_rows(7, [row(), row(type="income", amount="100", note="")])
    assert result == {"imported": 2, "skipped": 0, "errors": []}
    assert service.saved == [(7, "2026-01-05", "expense", "Food", 12.5, "lunch"),
                             (7, "2026-01-05", "income", "Food", 100.0, "")]


def test_importer_numbers_error_rows_from_line_2_and_keeps_going():
    service = FakeService(reject_amount=-1.0)
    rows = [row(), row(type="gift"), row(amount="-1"), row(amount="3")]
    result = TransactionCsvImporter(service).import_rows(1, rows)
    assert (result["imported"], result["skipped"]) == (2, 2)
    assert result["errors"][0].startswith("Row 3: invalid type")
    assert result["errors"][1] == "Row 4: Amount must be zero or greater."


def test_importer_uses_the_injected_parser():
    class AlwaysFails:
        def parse(self, r):
            raise ValueError("nope")
    result = TransactionCsvImporter(FakeService(), AlwaysFails()).import_rows(1, [row()])
    assert result["errors"] == ["Row 2: nope"]


def test_importer_reads_a_file(tmp_path):
    path = tmp_path / "in.csv"
    path.write_text("date,type,category,amount,note\n2026-01-05,expense,Food,10,a\n2026-01-06,income,Salary,50\n",
                    encoding="utf-8")                          # 2nd line is short: no note column
    service = FakeService()
    result = TransactionCsvImporter(service).import_file(3, str(path))
    assert result["imported"] == 2 and result["errors"] == []
    assert service.saved[1][-1] == ""


def test_importer_is_not_created_with_a_service_until_needed():
    # old module built a TransactionService at import time; now nothing is built until a class is used
    assert not hasattr(ie, "_transactions")


# --------------------------------------------------------------- exporter
def test_exporter_writes_header_and_rows_and_returns_count(tmp_path):
    txns = [{"date": "2026-01-05", "type": "expense", "category": "Food", "amount": 12.5, "note": None},
            {"date": "2026-01-06", "type": "income", "category": "Salary", "amount": 100.0, "note": "jan"}]
    path = tmp_path / "out.csv"
    count = TransactionCsvExporter(FakeService(txns)).export(1, str(path))
    rows = list(csv.DictReader(open(path, newline="", encoding="utf-8")))
    assert count == 2
    assert list(rows[0].keys()) == ie.CSV_HEADERS
    assert rows[0]["note"] == "" and rows[1]["note"] == "jan"


def test_exporter_with_no_transactions_writes_only_the_header(tmp_path):
    path = tmp_path / "out.csv"
    assert TransactionCsvExporter(FakeService([])).export(1, str(path)) == 0
    assert path.read_text(encoding="utf-8").strip() == ",".join(ie.CSV_HEADERS)


# --------------------------------- defects of the old function, now fixed
def test_short_row_no_longer_crashes_the_whole_import(user_id, tmp_path):
    path = tmp_path / "in.csv"
    path.write_text("date,type,category,amount,note\n2026-01-01,expense,Food,10\n", encoding="utf-8")
    assert ie.import_transactions_from_csv(user_id, str(path))["imported"] == 1   # old code: AttributeError


@pytest.mark.parametrize("bad", ["nan", "inf"])
def test_nan_and_inf_amounts_are_skipped_not_saved_or_crashing(user_id, tmp_path, bad):
    path = tmp_path / "in.csv"
    path.write_text(f"date,type,category,amount,note\n2026-01-01,expense,Food,{bad},x\n", encoding="utf-8")
    result = ie.import_transactions_from_csv(user_id, str(path))                  # old: IntegrityError / saved inf
    assert result["imported"] == 0 and result["skipped"] == 1
    assert db.get_transactions(user_id) == []


# --------------------------------------------- round trip through the real DB
def test_export_then_import_round_trip(user_id, tmp_path):
    db.add_transaction(user_id, "2026-01-05", "expense", "Food", 12.5, "lunch")
    db.add_transaction(user_id, "2026-01-06", "income", "Salary", 100, "")
    path = tmp_path / "rt.csv"
    assert ie.export_transactions_to_csv(user_id, str(path)) == 2
    _, other = db.register_user("bob", "pw")
    assert ie.import_transactions_from_csv(other, str(path))["imported"] == 2
    got = sorted((t["date"], t["type"], t["category"], t["amount"]) for t in db.get_transactions(other))
    assert got == [("2026-01-05", "expense", "Food", 12.5), ("2026-01-06", "income", "Salary", 100.0)]
