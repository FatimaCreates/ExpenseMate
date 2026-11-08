# ExpenseMate (Assignment 02)

ExpenseMate is a personal expense manager: record income and expenses, set monthly
budgets with alerts, track savings goals, see category charts, and import/export CSV.
Stack: **Python + Streamlit + SQLite**, running locally.

Assignment 02 evolves the Assignment 01 code through three concepts:

| Part | Concept | Where to look |
|------|---------|---------------|
| A | Migration: category text -> `category_id` foreign key, `schema_version` table | `migrations/m001_category_fk.py`, `snapshot_db.py`, `snapshots/` |
| B | Layered architecture: Controller -> Services -> Repository -> Database | `controllers/`, `services/`, `repositories/`, `database.py` |
| C | Rewritten classes: CSV import/export, `init_db()` -> `SchemaManager` | `import_export.py`, `schema.py`, `tools/part_c_schema_equivalence.py` |

Team: Fatima Javaid (24k-3036), Umama Khan (24k-3089)

## 1. Requirements

- Python 3.10 or newer
- The packages in `requirements.txt` (streamlit, matplotlib, pytest, pytest-cov; radon is optional)

## 2. Setup

From the project folder (the one containing `app.py`):

```bat
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

On macOS/Linux use `source venv/bin/activate` instead of `venv\Scripts\activate`.

## 3. Run the app

```bat
streamlit run app.py
```

The app opens in the browser (default http://localhost:8501). Register a new user on the
first screen, or log in with an existing one.

### Database

- The SQLite file is `expensemate.db` in the project folder.
- If the file does not exist, the app creates a new database in the current schema
  (schema version 1) on first start.
- The submitted `expensemate.db` is already migrated to schema version 1.
- An old Assignment 01 database (free-text categories) is **refused** on start-up with a
  message. Migrate it first (section 5).

## 4. Run the tests

```bat
pytest -q
```

Expected: 194 tests. On a fresh clone they all passed in our run (Linux, Python 3.12,
streamlit 1.67). On the team's Windows machine, 193 of 194 passed: the performance test
`test_bulk_insert_500_transactions_completes_quickly` has a 2.0 s limit and took 2.96 s;
it failed the same way in the Assignment 01 baseline, so it is machine-speed related.

Test groups:

| Group | Files |
|-------|-------|
| Assignment 01 regression (login, transactions, budgets, summaries, import/export, UI pages) | `test_database.py`, `test_logic.py`, `test_budget_block.py`, `test_budget_warning.py`, `test_edge_cases.py`, `test_import_export.py`, `test_app_pages.py`, `test_performance.py` |
| Part A migration | `test_migration_001.py` |
| Part B layers | `test_layers_unit.py` (fake repositories, no database), `test_architecture_rules.py` |
| Integration / system | `test_layers_integration.py` (11 cases, 3 through the Streamlit UI) |
| Part C rewrites | `test_rewrite_csv.py`, `test_rewrite_schema.py` |

Coverage of the new layers (as quoted in the reports):

```bat
pytest --cov=services --cov=controllers --cov=repositories
```

## 5. Migration (Part A)

Migrate an old database (makes its own backup first, runs in one transaction, safe to run twice):

```bat
python migrations\m001_category_fk.py
python migrations\m001_category_fk.py --db other.db --backup-dir backups
```

Verify that no data changed (row counts, totals per user/category/budget):

```bat
python snapshot_db.py before
python migrations\m001_category_fk.py
python snapshot_db.py after
python snapshot_db.py compare
```

Rollback: copy the backup file printed by the migration over `expensemate.db`.
The Assignment 01 database from before the migration is kept in `backups\expensemate_before_migration.db`.

## 6. Part C equivalence check

Compares the old `init_db()` (Git commit `057bb2b`) with the new `SchemaManager` on the same
starting databases. Needs Git and the repository history (`.git`):

```bat
python tools\part_c_schema_equivalence.py
```

Saved output: `snapshots\part_c_schema_equivalence.txt`.

## 7. Architecture

```
app.py  (Streamlit pages, calls controllers only)
   |
controllers/   basic input checks, call one service, return Result(ok, message, data, error)
   |
services/      business rules: budget guard, totals, progress, login, category rules
   |
repositories/  all data SQL, no calculations
   |
database.py + schema.py + expensemate.db   connection and schema
```

`database.py` and `logic.py` also keep thin wrappers for Assignment 01 callers and tests.
New code does not use them.

## 8. Project layout

```
app.py                  Streamlit UI
controllers/            Transaction, Budget, User, Category, Savings controllers + Result
services/               services, validators.py, security.py, errors.py
repositories/           Transaction, Budget, User, Category, SavingsGoal repositories
database.py, schema.py  connection, SchemaManager (Part C)
import_export.py        CSV parser / importer / exporter (Part C)
logic.py                legacy wrappers over services
constants.py            default categories, supported currencies
migrations/             m001_category_fk.py (Part A)
snapshot_db.py          before/after data snapshots for the migration
tools/                  part_c_schema_equivalence.py
tests/                  pytest suite
snapshots/              migration and test evidence
backups/                database backups taken before the migration
.streamlit/config.toml  theme
```

## 9. Version control

- Tag `assignment01-baseline` on `main`: the Assignment 01 code.
- Branch `assignment02`: all Assignment 02 work.
- Commits: Part A `3b7ad21`; Part B `441696d`, `0d0a503`, `2d4fc95`, `d702f41`, `057bb2b`;
  Part C `02f5fbd`, `28f46f6`, `77a9753`.

## 10. Known limitations

- Legacy wrappers in `database.py` and `logic.py` remain for the old tests.
- `app.py` is still long (about 770 lines) because it holds the Streamlit UI and CSS.
- Import page was not screenshotted with real data; CSV import is covered by automated tests.
- One performance test can fail on slower machines (see section 4).
