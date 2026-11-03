# ExpenseMate — Personal Expense Manager

A personal finance app to record income and expenses, set monthly budgets, track savings goals and get a warning when spending goes over budget. Built for the **Software Construction** course.

**Team:** Fatima Javaid (24k-3036), Umama Khan (24k-3089)

## Features

- User accounts; each user only sees their own data
- Add, view and delete income and expense transactions
- Category dropdown with defaults (Food, Transport, Salary, Bills, etc.) plus custom categories
- Monthly budgets per category with progress bars and a red over-budget alert
- Savings goals with progress tracking
- Dashboard with income, expense and net balance cards and a category-wise pie chart
- CSV import and export; invalid rows are skipped and reported

## Tech Stack

Python 3, Streamlit, SQLite (`sqlite3`), Matplotlib, `hashlib` (SHA-256), pytest, pytest-cov, radon

## Architecture

A local client–server app with a layered design. The browser is the client; Streamlit and SQLite run on the user's machine.

| Layer | File | Responsibility |
|---|---|---|
| Presentation | `app.py` | Streamlit pages, forms, charts, login |
| Business logic | `logic.py` | Summaries, budget alerts, progress |
| Data access | `database.py` | Schema and SQLite CRUD, scoped by `user_id` |
| Utility | `import_export.py` | CSV import and export |

**Tables:** `users`, `transactions`, `budgets`, `savings_goals`, `categories`

## Getting Started

Requires Python 3.10 or newer.

```bash
git clone <your-repo-url>
cd ExpenseMate
pip install -r requirements.txt
streamlit run app.py
```

The app opens at `http://localhost:8501`. The database file is created on first run. Register an account, then log in.

**CSV format:** header row `date,type,category,amount,note`, where `type` is `income` or `expense`.

## Testing

```bash
pip install pytest pytest-cov pytest-html
pytest tests/ -v
```

Tests cover unit, UI (Streamlit `AppTest`), performance, integration and system levels, and run on a temporary database.

**Result:** 55 tests passed, 96% statement coverage. Average cyclomatic complexity is A (3.09); the most complex function is `login_screen()` (grade C, 14).

## Known Issues

- `delete_transaction` and `update_transaction` do not check that the transaction belongs to the logged-in user.
- Transaction notes are inserted into the HTML table without escaping.
- CSV import does not validate that a date is a real date.
- Passwords use plain SHA-256 with no salt; `bcrypt` or `argon2` would be safer.

## License

Academic project, not intended for production use.
