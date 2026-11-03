"""
test_performance.py
---------------------
Basic performance / non-functional tests for ExpenseMate.

Unlike the correctness-focused tests in test_database.py / test_logic.py /
test_import_export.py, these tests answer a different question: "does the
system stay fast enough as data grows?" This matters for ExpenseMate
because a user's transaction history grows every day they use the app.

These are deliberately simple wall-clock timing tests (not a full
benchmarking suite) — appropriate for an assignment-scale project, and
still meaningful: if a future change accidentally turns an O(n) function
into an O(n^2) one, these tests will start failing.
"""

import time
import database as db
import logic
import import_export as ie


PERFORMANCE_LIMIT_SECONDS = 2.0
BULK_TRANSACTION_COUNT = 500


def _seed_bulk_transactions(user_id, count):
    categories = ["Food", "Transport", "Bills", "Entertainment", "Health"]
    for i in range(count):
        db.add_transaction(
            user_id,
            f"2026-09-{(i % 28) + 1:02d}",
            "expense" if i % 3 else "income",
            categories[i % len(categories)],
            100 + i,
            f"txn {i}",
        )


# DATABASE LAYER PERFORMANCE


def test_bulk_insert_500_transactions_completes_quickly(user_id):
    start = time.perf_counter()
    _seed_bulk_transactions(user_id, BULK_TRANSACTION_COUNT)
    elapsed = time.perf_counter() - start

    assert len(db.get_transactions(user_id)) == BULK_TRANSACTION_COUNT
    assert elapsed < PERFORMANCE_LIMIT_SECONDS, (
        f"Inserting {BULK_TRANSACTION_COUNT} transactions took {elapsed:.2f}s, "
        f"expected under {PERFORMANCE_LIMIT_SECONDS}s"
    )


def test_reading_500_transactions_completes_quickly(user_id):
    _seed_bulk_transactions(user_id, BULK_TRANSACTION_COUNT)

    start = time.perf_counter()
    transactions = db.get_transactions(user_id)
    elapsed = time.perf_counter() - start

    assert len(transactions) == BULK_TRANSACTION_COUNT
    assert elapsed < PERFORMANCE_LIMIT_SECONDS


# BUSINESS LOGIC LAYER PERFORMANCE


def test_monthly_summary_on_large_dataset_is_fast(user_id):
    _seed_bulk_transactions(user_id, BULK_TRANSACTION_COUNT)

    start = time.perf_counter()
    summary = logic.get_monthly_summary(user_id, "2026-09")
    elapsed = time.perf_counter() - start

    assert summary["total_expense"] > 0 or summary["total_income"] > 0
    assert elapsed < PERFORMANCE_LIMIT_SECONDS


def test_budget_alert_check_on_large_dataset_is_fast(user_id):
    db.set_budget(user_id, "Food", 5000)
    db.set_budget(user_id, "Transport", 5000)
    _seed_bulk_transactions(user_id, BULK_TRANSACTION_COUNT)

    start = time.perf_counter()
    alerts = logic.check_budget_alerts(user_id, "2026-09")
    elapsed = time.perf_counter() - start

    assert isinstance(alerts, list)
    assert elapsed < PERFORMANCE_LIMIT_SECONDS


# CSV EXPORT/IMPORT PERFORMANCE


def test_csv_export_of_large_dataset_is_fast(user_id, tmp_path):
    _seed_bulk_transactions(user_id, BULK_TRANSACTION_COUNT)
    out_path = tmp_path / "bulk_export.csv"

    start = time.perf_counter()
    count = ie.export_transactions_to_csv(user_id, str(out_path))
    elapsed = time.perf_counter() - start

    assert count == BULK_TRANSACTION_COUNT
    assert elapsed < PERFORMANCE_LIMIT_SECONDS
