"""
test_edge_cases.py
--------------------
Boundary/edge-case integration tests written for Phase 4 to actively probe
for faults that the Phase 3 unit tests did not target.

History: these tests originally *documented* faults (negative amounts, bad
dates, blank usernames were all silently accepted). Each fault has since been
fixed in the code, so the tests now assert the corrected behaviour.
"""

import csv
import datetime

import pytest
from streamlit.testing.v1 import AppTest

import database as db
import logic
import import_export as ie


def _write_csv(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=ie.CSV_HEADERS)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)


# ---------------------------------------------------------------------------
# Negative / invalid amounts  (fixed: bug1)
# ---------------------------------------------------------------------------

def test_negative_amount_transaction_is_rejected_by_db_layer(user_id):
    with pytest.raises(ValueError):
        db.add_transaction(user_id, "2026-09-15", "expense", "Food", -500)
    assert db.get_transactions(user_id) == []


def test_negative_amount_via_csv_import_is_skipped(user_id, tmp_path):
    path = tmp_path / "import.csv"
    _write_csv(path, [{"date": "2026-09-15", "type": "expense", "category": "Food", "amount": "-200", "note": ""}])

    result = ie.import_transactions_from_csv(user_id, str(path))
    assert result["imported"] == 0
    assert result["skipped"] == 1


# ---------------------------------------------------------------------------
# Budget with negative limit
# ---------------------------------------------------------------------------

def test_negative_budget_limit_is_rejected_by_db_layer(user_id):
    with pytest.raises(ValueError):
        db.set_budget(user_id, "Food", -100)
    assert db.get_budgets(user_id) == []


def test_budget_progress_with_zero_limit_does_not_crash(user_id):
    """get_budget_progress() guards with `if limit > 0 else 0` (no divide by zero)."""
    db.set_budget(user_id, "Food", 0)
    db.add_transaction(user_id, "2026-09-01", "expense", "Food", 50)
    progress = logic.get_budget_progress(user_id, "2026-09")
    assert progress[0]["percent"] == 0


# ---------------------------------------------------------------------------
# Future-dated / malformed dates  (fixed: database.validate_date)
# ---------------------------------------------------------------------------

def test_far_future_dated_transaction_is_rejected(user_id):
    with pytest.raises(ValueError, match="future"):
        db.add_transaction(user_id, "2099-01-01", "expense", "Food", 100)
    assert db.get_transactions(user_id) == []


def test_tomorrow_is_rejected_but_today_is_allowed(user_id):
    today = datetime.date.today()
    db.add_transaction(user_id, today.isoformat(), "expense", "Food", 10)
    with pytest.raises(ValueError):
        db.add_transaction(user_id, (today + datetime.timedelta(days=1)).isoformat(), "expense", "Food", 10)
    assert len(db.get_transactions(user_id)) == 1


@pytest.mark.parametrize("bad_date", [
    "not-a-real-date",   # nonsense
    "2026-13-01",        # month 13
    "2026-02-30",        # day doesn't exist
    "01/10/2026",        # wrong format
    "",                  # empty
])
def test_malformed_date_is_rejected_by_db_layer(user_id, bad_date):
    with pytest.raises(ValueError, match="Invalid date"):
        db.add_transaction(user_id, bad_date, "expense", "Food", 100)
    assert db.get_transactions(user_id) == []


def test_date_is_normalised_so_monthly_filter_still_matches(user_id):
    """'2026-9-5' would never match startswith('2026-09'); it is stored as '2026-09-05'."""
    db.add_transaction(user_id, "2026-9-5", "expense", "Food", 300)
    assert db.get_transactions(user_id)[0]["date"] == "2026-09-05"
    assert logic.get_monthly_summary(user_id, "2026-09")["total_expense"] == 300


def test_rejected_date_never_corrupts_monthly_totals(user_id):
    """Before the fix, a bad date silently vanished from every summary."""
    db.add_transaction(user_id, "2026-09-05", "expense", "Food", 100)
    with pytest.raises(ValueError):
        db.add_transaction(user_id, "not-a-real-date", "expense", "Food", 999)
    assert logic.get_monthly_summary(user_id, "2026-09")["total_expense"] == 100


def test_update_transaction_also_validates_date(user_id):
    db.add_transaction(user_id, "2026-09-05", "expense", "Food", 100)
    txn_id = db.get_transactions(user_id)[0]["id"]
    with pytest.raises(ValueError):
        db.update_transaction(txn_id, "2099-01-01", "expense", "Food", 100)
    assert db.get_transactions(user_id)[0]["date"] == "2026-09-05"


def test_csv_import_skips_bad_and_future_dates_with_clear_errors(user_id, tmp_path):
    path = tmp_path / "dates.csv"
    _write_csv(path, [
        {"date": "2026-09-05", "type": "expense", "category": "Food", "amount": "100", "note": ""},
        {"date": "garbage",    "type": "expense", "category": "Food", "amount": "100", "note": ""},
        {"date": "2099-01-01", "type": "expense", "category": "Food", "amount": "100", "note": ""},
    ])
    result = ie.import_transactions_from_csv(user_id, str(path))
    assert result["imported"] == 1
    assert result["skipped"] == 2
    assert "Invalid date" in result["errors"][0]
    assert "future" in result["errors"][1]


# ---------------------------------------------------------------------------
# Empty / header-only CSV import
# ---------------------------------------------------------------------------

def test_import_header_only_csv_reports_zero_imported(user_id, tmp_path):
    path = tmp_path / "empty.csv"
    _write_csv(path, [])

    result = ie.import_transactions_from_csv(user_id, str(path))
    assert result["imported"] == 0
    assert result["skipped"] == 0
    assert result["errors"] == []


def test_import_completely_empty_file_does_not_crash(user_id, tmp_path):
    """A truly empty file (no header row at all)."""
    path = tmp_path / "truly_empty.csv"
    path.write_text("")

    result = ie.import_transactions_from_csv(user_id, str(path))
    assert result["imported"] == 0
    assert result["skipped"] == 0


# ---------------------------------------------------------------------------
# Category deletion while in use
# ---------------------------------------------------------------------------

def test_category_in_use_cannot_be_deleted(user_id):
    """
    Migration 001 made transactions.category_id a foreign key. A category that
    transactions still point to can no longer be deleted (before the migration
    this silently left transactions pointing at a name missing from the
    dropdown). The transaction must be untouched.
    """
    db.add_transaction(user_id, "2026-09-01", "expense", "Gym", 100)
    with pytest.raises(ValueError, match="used by"):
        db.delete_category(user_id, "Gym")
    txns = db.get_transactions(user_id)
    assert txns[0]["category"] == "Gym"
    assert "Gym" in db.get_categories(user_id)


# ---------------------------------------------------------------------------
# Username / password validation  (fixed: register_user)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("blank", ["", "   ", "\t\n"])
def test_blank_username_is_rejected(blank):
    ok, message = db.register_user(blank, "password123")
    assert ok is False
    assert "Username" in message


def test_empty_password_is_rejected():
    ok, message = db.register_user("alice", "")
    assert ok is False
    assert "Password" in message


def test_username_is_stripped_so_login_works():
    ok, uid = db.register_user("  bob  ", "password123")
    assert ok is True
    assert db.get_user(uid)["username"] == "bob"
    assert db.verify_user("bob", "password123") is not None


def test_padded_duplicate_username_is_still_a_duplicate():
    db.register_user("carol", "password123")
    ok, _ = db.register_user(" carol ", "password123")
    assert ok is False


def test_register_form_rejects_whitespace_only_username_in_ui():
    at = AppTest.from_file("../app.py")
    at.run()
    at.button(key="btn_register_toggle").click().run()
    at.text_input[0].set_value("     ")
    at.text_input[1].set_value("securepass123")
    at.text_input[2].set_value("securepass123")
    at.button(key="FormSubmitter:register_form-Register").click().run()
    assert not at.exception
    assert any("fill in all fields" in e.value for e in at.error)
    assert db.verify_user("", "securepass123") is None