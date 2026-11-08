"""Old init_db (assignment02 commit 057bb2b) vs new SchemaManager on the same starting databases."""
import importlib.util, os, sqlite3, sys, tempfile
sys.path.insert(0, '.')
import database as new
import subprocess; _src = subprocess.check_output(['git', 'show', '057bb2b:database.py'], text=True); open(os.path.join(tempfile.gettempdir(), 'database_old_057bb2b.py'), 'w', encoding='utf8').write(_src)
spec = importlib.util.spec_from_file_location('database_old', os.path.join(tempfile.gettempdir(), 'database_old_057bb2b.py'))
old = importlib.util.module_from_spec(spec); spec.loader.exec_module(old)

def norm(sql): return ' '.join((sql or '').split())
def dump(path):
    c = sqlite3.connect(path)
    schema = sorted((r[0], norm(r[1])) for r in c.execute("SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"))
    ver = [(r[0], r[1]) for r in c.execute("SELECT version, description FROM schema_version")]
    c.close(); return schema, ver

def run(mod, setup):
    fd, p = tempfile.mkstemp(suffix='.db'); os.close(fd); os.remove(p)
    if setup:
        c = sqlite3.connect(p); c.executescript(setup); c.commit(); c.close()
    mod.DB_NAME = p
    try:
        mod.init_db(); out = ('ok', dump(p))
    except Exception as e:
        out = (type(e).__name__, str(e).replace(p, '<DB>'))
    for ext in ('', '-wal', '-shm'):
        if os.path.exists(p + ext): os.remove(p + ext)
    return out

LEGACY = "CREATE TABLE users(id INTEGER PRIMARY KEY, username TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL);" \
         "CREATE TABLE transactions(id INTEGER PRIMARY KEY, user_id INTEGER, date TEXT, type TEXT, category TEXT, amount REAL, note TEXT);"
NO_CURRENCY = "CREATE TABLE users(id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL);"
cases = {'fresh database': '', 'users table without currency column': NO_CURRENCY, 'old free-text schema (must refuse)': LEGACY}
bad = 0
for name, setup in cases.items():
    a, b = run(old, setup), run(new, setup)
    same = a == b; bad += (not same)
    print(f"{'SAME' if same else 'DIFF'}  {name}: old={a[0]} new={b[0]}")
# idempotence: run new twice on the same file, compare with once
fd, p = tempfile.mkstemp(suffix='.db'); os.close(fd); os.remove(p)
new.DB_NAME = p; new.init_db(); first = dump(p); new.init_db(); second = dump(p)
print(f"{'SAME' if first == second else 'DIFF'}  second init_db() changes nothing")
bad += first != second
print('RESULT:', 'all equivalent' if not bad else f'{bad} difference(s)')
