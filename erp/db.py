import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "erp.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def init_db():
    conn = get_db()
    conn.executescript(SCHEMA)
    _seed_chart_of_accounts(conn)
    conn.commit()
    conn.close()


SCHEMA = """
-- Users / Auth
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name TEXT NOT NULL,
    email TEXT,
    role TEXT DEFAULT 'user',
    active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Contacts (customers & suppliers)
CREATE TABLE IF NOT EXISTS contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    contact_type TEXT NOT NULL CHECK(contact_type IN ('customer','supplier','both')),
    email TEXT,
    phone TEXT,
    address TEXT,
    city TEXT,
    country TEXT,
    tax_id TEXT,
    notes TEXT,
    active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Product categories
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT
);

-- Products
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sku TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    category_id INTEGER REFERENCES categories(id),
    unit_price REAL DEFAULT 0,
    cost_price REAL DEFAULT 0,
    stock_qty REAL DEFAULT 0,
    reorder_level REAL DEFAULT 0,
    unit TEXT DEFAULT 'unit',
    active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Stock movements
CREATE TABLE IF NOT EXISTS stock_movements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL REFERENCES products(id),
    movement_type TEXT NOT NULL CHECK(movement_type IN ('in','out','adjustment')),
    quantity REAL NOT NULL,
    reference TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Sales orders
CREATE TABLE IF NOT EXISTS sales_orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_number TEXT UNIQUE NOT NULL,
    customer_id INTEGER NOT NULL REFERENCES contacts(id),
    order_date DATE NOT NULL,
    status TEXT DEFAULT 'draft' CHECK(status IN ('draft','confirmed','shipped','invoiced','cancelled')),
    subtotal REAL DEFAULT 0,
    tax_amount REAL DEFAULT 0,
    total REAL DEFAULT 0,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sales_order_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL REFERENCES sales_orders(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(id),
    description TEXT,
    quantity REAL NOT NULL,
    unit_price REAL NOT NULL,
    tax_rate REAL DEFAULT 0,
    line_total REAL NOT NULL
);

-- Invoices
CREATE TABLE IF NOT EXISTS invoices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_number TEXT UNIQUE NOT NULL,
    sales_order_id INTEGER REFERENCES sales_orders(id),
    customer_id INTEGER NOT NULL REFERENCES contacts(id),
    invoice_date DATE NOT NULL,
    due_date DATE,
    status TEXT DEFAULT 'draft' CHECK(status IN ('draft','sent','paid','overdue','cancelled')),
    subtotal REAL DEFAULT 0,
    tax_amount REAL DEFAULT 0,
    total REAL DEFAULT 0,
    amount_paid REAL DEFAULT 0,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS invoice_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id INTEGER NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    product_id INTEGER REFERENCES products(id),
    description TEXT,
    quantity REAL NOT NULL,
    unit_price REAL NOT NULL,
    tax_rate REAL DEFAULT 0,
    line_total REAL NOT NULL
);

-- Purchase orders
CREATE TABLE IF NOT EXISTS purchase_orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    po_number TEXT UNIQUE NOT NULL,
    supplier_id INTEGER NOT NULL REFERENCES contacts(id),
    order_date DATE NOT NULL,
    expected_date DATE,
    status TEXT DEFAULT 'draft' CHECK(status IN ('draft','confirmed','received','invoiced','cancelled')),
    subtotal REAL DEFAULT 0,
    tax_amount REAL DEFAULT 0,
    total REAL DEFAULT 0,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS purchase_order_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    po_id INTEGER NOT NULL REFERENCES purchase_orders(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(id),
    description TEXT,
    quantity REAL NOT NULL,
    unit_price REAL NOT NULL,
    tax_rate REAL DEFAULT 0,
    line_total REAL NOT NULL
);

-- Chart of Accounts
CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    account_type TEXT NOT NULL CHECK(account_type IN ('asset','liability','equity','revenue','expense')),
    parent_id INTEGER REFERENCES accounts(id),
    balance REAL DEFAULT 0,
    active INTEGER DEFAULT 1
);

-- Journal entries
CREATE TABLE IF NOT EXISTS journal_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_date DATE NOT NULL,
    reference TEXT,
    description TEXT,
    posted INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS journal_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_id INTEGER NOT NULL REFERENCES journal_entries(id) ON DELETE CASCADE,
    account_id INTEGER NOT NULL REFERENCES accounts(id),
    debit REAL DEFAULT 0,
    credit REAL DEFAULT 0,
    description TEXT
);

-- Departments
CREATE TABLE IF NOT EXISTS departments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    manager_id INTEGER REFERENCES employees(id)
);

-- Employees
CREATE TABLE IF NOT EXISTS employees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_number TEXT UNIQUE NOT NULL,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email TEXT,
    phone TEXT,
    department_id INTEGER REFERENCES departments(id),
    job_title TEXT,
    hire_date DATE,
    salary REAL DEFAULT 0,
    active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Leave requests
CREATE TABLE IF NOT EXISTS leave_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL REFERENCES employees(id),
    leave_type TEXT NOT NULL CHECK(leave_type IN ('annual','sick','personal','unpaid')),
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    status TEXT DEFAULT 'pending' CHECK(status IN ('pending','approved','rejected','cancelled')),
    reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


def _seed_chart_of_accounts(conn):
    existing = conn.execute("SELECT COUNT(*) FROM accounts").fetchone()[0]
    if existing > 0:
        return
    accounts = [
        ("1000", "Cash", "asset"),
        ("1100", "Accounts Receivable", "asset"),
        ("1200", "Inventory", "asset"),
        ("1300", "Prepaid Expenses", "asset"),
        ("1500", "Fixed Assets", "asset"),
        ("2000", "Accounts Payable", "liability"),
        ("2100", "Accrued Liabilities", "liability"),
        ("2200", "Tax Payable", "liability"),
        ("2500", "Long-term Debt", "liability"),
        ("3000", "Owner's Equity", "equity"),
        ("3100", "Retained Earnings", "equity"),
        ("4000", "Sales Revenue", "revenue"),
        ("4100", "Service Revenue", "revenue"),
        ("4200", "Other Income", "revenue"),
        ("5000", "Cost of Goods Sold", "expense"),
        ("5100", "Salaries & Wages", "expense"),
        ("5200", "Rent Expense", "expense"),
        ("5300", "Utilities Expense", "expense"),
        ("5400", "Office Supplies", "expense"),
        ("5500", "Depreciation", "expense"),
        ("5600", "Marketing Expense", "expense"),
        ("5900", "Other Expenses", "expense"),
    ]
    conn.executemany(
        "INSERT INTO accounts (code, name, account_type) VALUES (?, ?, ?)", accounts
    )
