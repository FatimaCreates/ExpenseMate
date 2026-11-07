"""
Migration 001 - category TEXT  ->  category_id FOREIGN KEY
===========================================================

BEFORE (schema version 0, Assignment 01)
    transactions.category  TEXT      (free text, e.g. 'education' and 'Education')
    budgets.category       TEXT      (free text)
    -> the database cannot tell that 'education' and 'Education' are the same
       category, so summaries and budget checks can silently disagree.

AFTER (schema version 1)
    transactions.category_id  INTEGER NOT NULL  REFERENCES categories(id)
    budgets.category_id       INTEGER NOT NULL  REFERENCES categories(id)
    categories: one row per (user, case-insensitive name)
    schema_version table records which migrations have been applied.

HOW IT WORKS
    1. Back up the database (sqlite3 backup API, safe with WAL).
    2. Inside ONE transaction:
         - collapse case-duplicate rows in `categories`
         - create a category row for any text used by transactions/budgets that
           has no matching category (e.g. a category deleted earlier)
         - rebuild `transactions` and `budgets` with category_id (SQLite cannot
           add a foreign key to an existing table, so the table is rebuilt;
           row ids are preserved)
         - record the migration in `schema_version`
         - verify: row counts, total amount, PRAGMA foreign_key_check
       Any failure rolls everything back; the original data is untouched.
    3. Running it again is a no-op (idempotent).

USAGE
    python migrations/m001_category_fk.py                 # uses expensemate.db
    python migrations/m001_category_fk.py --db other.db
    python migrations/m001_category_fk.py --backup-dir backups

ROLLBACK
    Copy the backup file printed by the script back over the database file.
"""

import argparse
import os
import sqlite3
import sys
from datetime import datetime

VERSION = 1
DESCRIPTION = "category TEXT -> category_id FK on transactions and budgets"


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def _tables(conn):
    return {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}


def _columns(conn, table):
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}


def current_version(conn):
    """Highest applied migration version (0 if none recorded)."""
    if "schema_version" not in _tables(conn):
        return 0
    row = conn.execute("SELECT MAX(version) FROM schema_version").fetchone()
    return row[0] or 0


def is_old_schema(conn):
    """True if `transactions` exists but still uses the free-text category."""
    return ("transactions" in _tables(conn)
            and "category_id" not in _columns(conn, "transactions"))


def backup(db_path, backup_dir):
    """Copy the database using SQLite's backup API; returns the backup path."""
    os.makedirs(backup_dir, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = os.path.splitext(os.path.basename(db_path))[0]
    dest_path = os.path.join(backup_dir, f"{base}_pre_m001_{stamp}.db")
    src = sqlite3.connect(db_path)
    dest = sqlite3.connect(dest_path)
    try:
        src.backup(dest)
    finally:
        dest.close()
        src.close()
    return dest_path


# --------------------------------------------------------------------------
# the migration
# --------------------------------------------------------------------------

def migrate(db_path, backup_dir="backups", log=print):
    """
    Apply migration 001 to `db_path`.

    Returns a report dict. report["status"] is one of:
        "migrated"       - migration applied
        "already_applied" - nothing to do
        "empty"          - database has no transactions table yet
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.isolation_level = None            # we control BEGIN/COMMIT ourselves
    try:
        if "transactions" not in _tables(conn):
            log("Database has no transactions table yet; init_db() will create "
                "the new schema. Nothing to migrate.")
            return {"status": "empty"}

        if not is_old_schema(conn):
            log("Already on the new schema (category_id present). Nothing to do.")
            if current_version(conn) < VERSION:
                _ensure_version_table(conn)
                conn.execute(
                    "INSERT OR IGNORE INTO schema_version (version, description, applied_at) "
                    "VALUES (?, ?, ?)", (VERSION, DESCRIPTION, _now()))
            return {"status": "already_applied"}

        backup_path = backup(db_path, backup_dir)
        log(f"Backup written to {backup_path}")

        conn.execute("PRAGMA foreign_keys=OFF")   # must be outside a transaction
        conn.execute("BEGIN")
        try:
            report = _apply(conn, log)
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            log("Migration FAILED and was rolled back. Database unchanged. "
                f"Backup is at {backup_path}")
            raise
        conn.execute("PRAGMA foreign_keys=ON")

        report["status"] = "migrated"
        report["backup"] = backup_path
        log("Migration 001 applied successfully.")
        return report
    finally:
        conn.close()


def _now():
    return datetime.now().isoformat(timespec="seconds")


def _ensure_version_table(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY,
            description TEXT NOT NULL,
            applied_at TEXT NOT NULL
        )""")


def _apply(conn, log):
    report = {}

    # ---- snapshot of "before" numbers used for verification ---------------
    old_txn_count = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
    old_txn_sum = conn.execute("SELECT COALESCE(SUM(amount),0) FROM transactions").fetchone()[0]
    old_bud_count = conn.execute("SELECT COUNT(*) FROM budgets").fetchone()[0]
    old_txn_seq = conn.execute(
        "SELECT seq FROM sqlite_sequence WHERE name='transactions'").fetchone()
    old_bud_seq = conn.execute(
        "SELECT seq FROM sqlite_sequence WHERE name='budgets'").fetchone()

    # ---- 1. collapse case-duplicate rows in categories --------------------
    canonical = {}          # (user_id, lower(name)) -> category id
    duplicate_ids = []
    for r in conn.execute("SELECT id, user_id, name FROM categories ORDER BY id").fetchall():
        key = (r["user_id"], r["name"].strip().lower())
        if key in canonical:
            duplicate_ids.append(r["id"])
        else:
            canonical[key] = r["id"]
    for cid in duplicate_ids:
        conn.execute("DELETE FROM categories WHERE id=?", (cid,))
    report["duplicate_categories_removed"] = len(duplicate_ids)

    created = []

    def resolve(user_id, text):
        """category text -> category id, creating the category if needed."""
        clean = (text or "").strip() or "Uncategorized"
        key = (user_id, clean.lower())
        if key not in canonical:
            cur = conn.execute(
                "INSERT INTO categories (user_id, name) VALUES (?, ?)", (user_id, clean))
            canonical[key] = cur.lastrowid
            created.append((user_id, clean))
        return canonical[key]

    # ---- 2. rebuild transactions with category_id -------------------------
    conn.execute("""
        CREATE TABLE transactions_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            type TEXT NOT NULL CHECK(type IN ('income', 'expense')),
            category_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            note TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (category_id) REFERENCES categories(id)
        )""")
    spellings_merged = set()
    for t in conn.execute("SELECT * FROM transactions ORDER BY id").fetchall():
        cid = resolve(t["user_id"], t["category"])
        if (t["category"] or "").strip() != conn.execute(
                "SELECT name FROM categories WHERE id=?", (cid,)).fetchone()[0]:
            spellings_merged.add((t["category"], cid))
        conn.execute(
            "INSERT INTO transactions_new (id, user_id, date, type, category_id, amount, note) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (t["id"], t["user_id"], t["date"], t["type"], cid, t["amount"], t["note"]))
    conn.execute("DROP TABLE transactions")
    conn.execute("ALTER TABLE transactions_new RENAME TO transactions")
    report["transaction_spellings_normalised"] = len(spellings_merged)

    # ---- 3. rebuild budgets with category_id ------------------------------
    conn.execute("""
        CREATE TABLE budgets_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            category_id INTEGER NOT NULL,
            monthly_limit REAL NOT NULL,
            UNIQUE(user_id, category_id),
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (category_id) REFERENCES categories(id)
        )""")
    winners = {}            # (user_id, category_id) -> (budget id, limit); last row wins
    for b in conn.execute("SELECT * FROM budgets ORDER BY id").fetchall():
        winners[(b["user_id"], resolve(b["user_id"], b["category"]))] = (
            b["id"], b["monthly_limit"])
    for (user_id, cid), (bid, limit) in winners.items():
        conn.execute(
            "INSERT INTO budgets_new (id, user_id, category_id, monthly_limit) VALUES (?, ?, ?, ?)",
            (bid, user_id, cid, limit))
    conn.execute("DROP TABLE budgets")
    conn.execute("ALTER TABLE budgets_new RENAME TO budgets")
    report["budgets_merged"] = old_bud_count - len(winners)
    report["categories_created"] = len(created)

    # keep AUTOINCREMENT from reusing ids that were handed out before
    for table, old_seq in (("transactions", old_txn_seq), ("budgets", old_bud_seq)):
        if old_seq is not None:
            updated = conn.execute(
                "UPDATE sqlite_sequence SET seq=MAX(seq, ?) WHERE name=?",
                (old_seq[0], table)).rowcount
            if not updated:
                conn.execute("INSERT INTO sqlite_sequence (name, seq) VALUES (?, ?)",
                             (table, old_seq[0]))

    conn.execute("CREATE INDEX IF NOT EXISTS idx_transactions_category ON transactions(category_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_budgets_category ON budgets(category_id)")

    # ---- 4. record the migration ------------------------------------------
    _ensure_version_table(conn)
    conn.execute(
        "INSERT INTO schema_version (version, description, applied_at) VALUES (?, ?, ?)",
        (VERSION, DESCRIPTION, _now()))

    # ---- 5. verify BEFORE committing --------------------------------------
    new_txn_count = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
    new_txn_sum = conn.execute("SELECT COALESCE(SUM(amount),0) FROM transactions").fetchone()[0]
    if new_txn_count != old_txn_count:
        raise RuntimeError(f"transaction count changed: {old_txn_count} -> {new_txn_count}")
    if abs(new_txn_sum - old_txn_sum) > 1e-9:
        raise RuntimeError(f"transaction amount total changed: {old_txn_sum} -> {new_txn_sum}")
    violations = conn.execute("PRAGMA foreign_key_check").fetchall()
    if violations:
        raise RuntimeError(f"foreign key violations after migration: {len(violations)}")

    report.update({
        "transactions": new_txn_count,
        "budgets": len(winners),
        "total_amount": new_txn_sum,
    })
    log(f"  transactions kept        : {new_txn_count}")
    log(f"  budgets kept             : {len(winners)} (merged {report['budgets_merged']})")
    log(f"  duplicate categories gone: {report['duplicate_categories_removed']}")
    log(f"  categories created       : {report['categories_created']}")
    log(f"  spellings normalised     : {report['transaction_spellings_normalised']}")
    log("  foreign_key_check        : clean")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description="ExpenseMate migration 001 (category_id FK)")
    parser.add_argument("--db", default="expensemate.db", help="path to the SQLite database")
    parser.add_argument("--backup-dir", default="backups", help="where the backup is written")
    args = parser.parse_args(argv)

    if not os.path.exists(args.db):
        print(f"Database '{args.db}' not found.")
        return 1
    migrate(args.db, args.backup_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
