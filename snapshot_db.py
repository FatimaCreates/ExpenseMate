import json
import os
import sqlite3
import sys
from collections import defaultdict

DB_PATH = "expensemate.db"
SNAP_DIR = "snapshots"


def _columns(cur, table):
    return [r[1] for r in cur.execute(f"PRAGMA table_info({table})")]


def take_snapshot(db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    tables = [r[0] for r in cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]

    snap = {
        "row_counts": {t: cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in tables},
        "totals_per_user": {},
        "category_totals_per_user": {},
        "budgets_per_user": {},
    }

    txn_cols = _columns(cur, "transactions")
    if "category_id" in txn_cols:
        # new schema: resolve the name through the categories table
        txn_sql = """SELECT t.user_id, t.type, c.name AS category, t.amount
                     FROM transactions t JOIN categories c ON c.id = t.category_id"""
    else:
        txn_sql = "SELECT user_id, type, category, amount FROM transactions"

    totals = defaultdict(lambda: {"income": 0.0, "expense": 0.0})
    cat_totals = defaultdict(lambda: defaultdict(float))
    for r in cur.execute(txn_sql):
        uid = str(r["user_id"])
        totals[uid][r["type"]] += r["amount"]
        # case-insensitive key so before/after are comparable
        cat_totals[uid][f'{r["type"]}:{r["category"].strip().lower()}'] += r["amount"]
    snap["totals_per_user"] = {u: dict(v) for u, v in totals.items()}
    snap["category_totals_per_user"] = {u: dict(v) for u, v in cat_totals.items()}

    bud_cols = _columns(cur, "budgets")
    if "category_id" in bud_cols:
        bud_sql = """SELECT b.user_id, c.name AS category, b.monthly_limit
                     FROM budgets b JOIN categories c ON c.id = b.category_id"""
    else:
        bud_sql = "SELECT user_id, category, monthly_limit FROM budgets"
    budgets = defaultdict(dict)
    for r in cur.execute(bud_sql):
        budgets[str(r["user_id"])][r["category"].strip().lower()] = r["monthly_limit"]
    snap["budgets_per_user"] = dict(budgets)

    # distinct raw category spellings in transactions (shows the duplicates)
    if "category_id" not in txn_cols:
        snap["raw_distinct_txn_categories"] = sorted(
            r[0] for r in cur.execute("SELECT DISTINCT category FROM transactions"))
    conn.close()
    return snap


def save(name):
    os.makedirs(SNAP_DIR, exist_ok=True)
    snap = take_snapshot()
    path = os.path.join(SNAP_DIR, f"{name}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(snap, f, indent=2, sort_keys=True)
    print(f"Snapshot saved to {path}")
    print(json.dumps(snap, indent=2, sort_keys=True))


def compare():
    with open(os.path.join(SNAP_DIR, "before.json"), encoding="utf-8") as f:
        before = json.load(f)
    with open(os.path.join(SNAP_DIR, "after.json"), encoding="utf-8") as f:
        after = json.load(f)

    ok = True
    for key in ("totals_per_user", "category_totals_per_user", "budgets_per_user"):
        same = before[key] == after[key]
        ok &= same
        print(f"{key:28s}: {'MATCH' if same else 'MISMATCH'}")

    for t in ("users", "transactions", "budgets", "savings_goals"):
        b, a = before["row_counts"].get(t), after["row_counts"].get(t)
        same = b == a
        ok &= same
        print(f"row count {t:20s}: before={b} after={a} {'OK' if same else 'MISMATCH'}")

    print("\nOVERALL:", "PASS - data preserved" if ok else "FAIL - investigate")
    return ok


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd in ("before", "after"):
        save(cmd)
    elif cmd == "compare":
        sys.exit(0 if compare() else 1)
    else:
        print(__doc__)