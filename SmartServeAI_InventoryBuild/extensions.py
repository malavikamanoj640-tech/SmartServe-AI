"""Persistent operational extensions for SmartServe AI (SQLite local store)."""
import os, sqlite3
from contextlib import contextmanager
from datetime import date

DB_PATH = os.environ.get('SMARTSERVE_LOCAL_DB', os.path.join(os.path.dirname(__file__), 'database', 'smartserve_local.sqlite3'))

@contextmanager
def connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def init_store():
    with connection() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS inventory(id INTEGER PRIMARY KEY AUTOINCREMENT, ingredient TEXT NOT NULL UNIQUE, quantity REAL NOT NULL DEFAULT 0, unit TEXT NOT NULL, unit_cost REAL NOT NULL DEFAULT 0, updated_at TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS suppliers(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, contact TEXT, email TEXT, category TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS purchase_orders(id INTEGER PRIMARY KEY AUTOINCREMENT, supplier_id INTEGER, ingredient TEXT NOT NULL, quantity REAL NOT NULL, unit_price REAL NOT NULL, total REAL NOT NULL, status TEXT NOT NULL DEFAULT 'DRAFT', created_at TEXT DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(supplier_id) REFERENCES suppliers(id));
        CREATE TABLE IF NOT EXISTS sales_records(id INTEGER PRIMARY KEY AUTOINCREMENT, sale_date TEXT NOT NULL, item TEXT NOT NULL, quantity INTEGER NOT NULL, selling_price REAL NOT NULL, unit_cost REAL NOT NULL, revenue REAL NOT NULL, cost REAL NOT NULL, gross_profit REAL NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
        ''')
        seeds = [('Rice',25,'kg',55),('Paneer',8,'kg',280),('Chicken',12,'kg',220),('Potato',15,'kg',35),('Onion',10,'kg',32),('Dal',8,'kg',120),('Vegetables',14,'kg',70),('Roti Flour',10,'kg',55),('Bread',10,'pack',45),('Cheese',3,'kg',360),('Urad Dal',7,'kg',145),('Oil',12,'L',140),('Spices',3,'kg',260)]
        c.executemany('INSERT OR IGNORE INTO inventory(ingredient,quantity,unit,unit_cost) VALUES(?,?,?,?)', seeds)

def rows(c, query, args=()): return [dict(r) for r in c.execute(query,args).fetchall()]
