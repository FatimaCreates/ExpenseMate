"""
schema.py  (Database layer, rewritten in Assignment 02, Part C)
----------------------------------------------------------------
Creates and checks the SQLite schema.

This replaces the old 85-line init_db() function, which mixed five jobs
(legacy-schema detection, five CREATE TABLEs, an ALTER TABLE used as a
try/except probe, schema_version stamping, connection handling) and could
leave a connection open if something failed half-way. SchemaManager gives
each job its own small method and always closes the connection.

database.init_db() still exists and simply calls SchemaManager.apply().
"""

# Order matters only for readability: SQLite does not check foreign keys at CREATE time.
TABLE_DDL = {
    "users": """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            currency TEXT NOT NULL DEFAULT 'PKR'
        )
    """,
    "transactions": """
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            type TEXT NOT NULL CHECK(type IN ('income', 'expense')),
            category_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            note TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (category_id) REFERENCES categories(id)
        )
    """,
    "budgets": """
        CREATE TABLE IF NOT EXISTS budgets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            category_id INTEGER NOT NULL,
            monthly_limit REAL NOT NULL,
            UNIQUE(user_id, category_id),
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (category_id) REFERENCES categories(id)
        )
    """,
    "savings_goals": """
        CREATE TABLE IF NOT EXISTS savings_goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            target_amount REAL NOT NULL,
            saved_amount REAL NOT NULL DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """,
    # Each user has their own category list, so the UI can use a dropdown and
    # "Food" / "food" cannot become two categories.
    "categories": """
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            UNIQUE(user_id, name),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """,
    # Records which schema migrations have been applied (see migrations/).
    "schema_version": """
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY,
            description TEXT NOT NULL,
            applied_at TEXT NOT NULL
        )
    """,
}

# Columns added after the first release: (table, column, definition).
# Databases created before multi-currency support lack users.currency.
LATER_COLUMNS = [
    ("users", "currency", "TEXT NOT NULL DEFAULT 'PKR'"),
]


class SchemaManager:

    def __init__(self, connect, db_name, schema_version):
        """connect: a function returning a new sqlite3 connection (database.get_connection)."""
        self._connect = connect
        self._db_name = db_name
        self._schema_version = schema_version

    def apply(self):
        """Create missing tables/columns; refuse a database that still has the
        pre-migration schema. Safe to run on every start-up."""
        conn = self._connect()
        try:
            cur = conn.cursor()
            fresh = "transactions" not in self._table_names(cur)
            if not fresh:
                self._refuse_legacy_schema(cur)
            self._create_tables(cur)
            self._add_missing_columns(cur)
            if fresh:
                self._stamp_version(cur)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # -- steps -------------------------------------------------------------
    @staticmethod
    def _table_names(cur):
        return {r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")}

    @staticmethod
    def _column_names(cur, table):
        return {r[1] for r in cur.execute(f"PRAGMA table_info({table})")}

    def _refuse_legacy_schema(self, cur):
        if "category_id" not in self._column_names(cur, "transactions"):
            raise RuntimeError(
                f"'{self._db_name}' still uses the old schema (free-text categories). "
                f"Run:  python migrations/m001_category_fk.py --db {self._db_name}"
            )

    @staticmethod
    def _create_tables(cur):
        for ddl in TABLE_DDL.values():
            cur.execute(ddl)

    def _add_missing_columns(self, cur):
        for table, column, definition in LATER_COLUMNS:
            if column not in self._column_names(cur, table):
                cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def _stamp_version(self, cur):
        """A brand-new database is created directly in the latest schema."""
        cur.execute(
            "INSERT OR IGNORE INTO schema_version (version, description, applied_at) "
            "VALUES (?, 'created with latest schema', datetime('now'))",
            (self._schema_version,),
        )
