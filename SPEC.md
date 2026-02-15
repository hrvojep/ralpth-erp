# ERP System Specification

## Overview

A full-featured Enterprise Resource Planning system built with Python Flask and SQLite. Server-side rendered with Jinja2 templates. Designed for small-to-medium business operations.

- **Stack**: Python 3.9+, Flask 3.x, SQLite, Jinja2, vanilla CSS
- **Auth**: Flask-Login with session-based cookies, pbkdf2:sha256 password hashing
- **Database**: 16 tables, SQLite with WAL mode and foreign keys enabled
- **Deployment**: Local (`python3 run.py`) or Vercel (serverless, ephemeral `/tmp` DB)

## Architecture

```
erp/
  app.py              # Flask app factory, blueprint registration
  auth.py             # Login/logout, User model (UserMixin)
  db.py               # SQLite connection, schema, chart of accounts seed
  modules/
    dashboard.py      # KPI stats, recent orders
    contacts.py       # Customer/supplier CRUD
    products.py       # Product catalog, categories, stock management
    sales.py          # Sales orders, invoicing, payments
    purchasing.py     # Purchase orders, receiving, stock updates
    accounting.py     # Double-entry accounting, reports
    hr.py             # Employees, departments, leave management
  templates/          # Jinja2 templates (base.html + per-module dirs)
  static/css/         # Single stylesheet
app.py                # Vercel entrypoint
run.py                # Local dev server entrypoint
seed_data.py          # Sample data loader
vercel.json           # Vercel routing config
```

## Modules

### 1. Authentication

| Route | Method | Description |
|-------|--------|-------------|
| `/login` | GET, POST | Login form and handler |
| `/logout` | GET | End session, redirect to login |

- Default credentials: `admin` / `admin`
- All other routes require `@login_required`
- User roles: `admin`, `user`

### 2. Dashboard

| Route | Method | Description |
|-------|--------|-------------|
| `/` | GET | KPI dashboard |

Displays:
- Total contacts, products, sales orders, purchase orders
- Pending invoices count
- Total revenue (paid invoices)
- 5 most recent sales orders
- 5 most recent purchase orders

### 3. Contacts

| Route | Method | Description |
|-------|--------|-------------|
| `/contacts/` | GET | List contacts (supports `?search=` and `?type=` filters) |
| `/contacts/new` | GET, POST | Create contact |
| `/contacts/<id>` | GET | Contact detail |
| `/contacts/<id>/edit` | GET, POST | Edit contact |
| `/contacts/<id>/delete` | POST | Soft-delete (sets `active=0`) |

Contact types: `customer`, `supplier`, `both`

Fields: name, contact_type, email, phone, address, city, country, tax_id, notes

### 4. Products

| Route | Method | Description |
|-------|--------|-------------|
| `/products/` | GET | List products (highlights low stock) |
| `/products/new` | GET, POST | Create product |
| `/products/<id>` | GET | Product detail + stock movement history |
| `/products/<id>/edit` | GET, POST | Edit product |
| `/products/<id>/adjust-stock` | POST | Stock in/out/adjustment |
| `/products/categories` | GET, POST | Manage categories |

Stock adjustment types:
- `in` — adds to current stock
- `out` — subtracts from current stock
- `adjustment` — sets stock to given quantity (records delta)

Fields: sku (unique), name, description, category_id, unit_price, cost_price, stock_qty, reorder_level, unit

### 5. Sales

| Route | Method | Description |
|-------|--------|-------------|
| `/sales/` | GET | List sales orders |
| `/sales/new` | GET, POST | Create sales order with line items |
| `/sales/<id>` | GET | Order detail |
| `/sales/<id>/edit` | GET, POST | Edit order (draft only) |
| `/sales/<id>/confirm` | POST | draft -> confirmed |
| `/sales/<id>/cancel` | POST | Cancel order (not if invoiced) |
| `/sales/<id>/create-invoice` | POST | Generate invoice from confirmed/shipped order |
| `/sales/invoices` | GET | List invoices |
| `/sales/invoices/<id>` | GET | Invoice detail |
| `/sales/invoices/<id>/mark-paid` | POST | Mark invoice as paid |

Order status flow: `draft` -> `confirmed` -> `shipped` -> `invoiced` -> (or `cancelled`)

Invoice status flow: `draft` -> `sent` -> `paid` (or `overdue`, `cancelled`)

Auto-generated numbers: `SO-0001`, `SO-0002`, ... / `INV-0001`, `INV-0002`, ...

Tax: 10% flat rate on subtotal

Line items: product_id, quantity, unit_price, line_total (with JS auto-fill from product price)

### 6. Purchasing

| Route | Method | Description |
|-------|--------|-------------|
| `/purchasing/` | GET | List purchase orders |
| `/purchasing/new` | GET, POST | Create PO with line items |
| `/purchasing/<id>` | GET | PO detail |
| `/purchasing/<id>/edit` | GET, POST | Edit PO (draft only) |
| `/purchasing/<id>/confirm` | POST | draft -> confirmed |
| `/purchasing/<id>/receive` | POST | Receive goods (updates stock + creates stock movements) |
| `/purchasing/<id>/cancel` | POST | Cancel PO (not if received/invoiced) |

PO status flow: `draft` -> `confirmed` -> `received` -> `invoiced` (or `cancelled`)

Auto-generated numbers: `PO-0001`, `PO-0002`, ...

Receiving: automatically increases product `stock_qty` and inserts `stock_movements` records with `movement_type='in'`

Line items: product_id, quantity, unit_price, line_total (JS auto-fills cost_price)

### 7. Accounting

| Route | Method | Description |
|-------|--------|-------------|
| `/accounting/` | GET | Chart of accounts grouped by type |
| `/accounting/accounts/new` | GET, POST | Create account |
| `/accounting/journal` | GET | List journal entries |
| `/accounting/journal/new` | GET, POST | Create journal entry with debit/credit lines |
| `/accounting/journal/<id>` | GET | Journal entry detail |
| `/accounting/journal/<id>/post` | POST | Post entry (updates account balances) |
| `/accounting/trial-balance` | GET | Trial balance report |
| `/accounting/profit-loss` | GET | P&L report (supports `?date_from=` and `?date_to=`) |
| `/accounting/balance-sheet` | GET | Balance sheet report |

Account types: `asset`, `liability`, `equity`, `revenue`, `expense`

Double-entry rules:
- Total debits must equal total credits (validated server-side and client-side)
- Posting updates account balances:
  - Asset/Expense: balance += (debit - credit)
  - Liability/Equity/Revenue: balance += (credit - debit)

Pre-seeded chart of accounts (22 accounts):
- 1000-1500: Assets (Cash, AR, Inventory, Prepaid, Fixed Assets)
- 2000-2500: Liabilities (AP, Accrued, Tax Payable, Long-term Debt)
- 3000-3100: Equity (Owner's Equity, Retained Earnings)
- 4000-4200: Revenue (Sales, Service, Other Income)
- 5000-5900: Expenses (COGS, Salaries, Rent, Utilities, Supplies, Depreciation, Marketing, Other)

Reports:
- **Trial Balance**: All accounts with non-zero balances, debit/credit columns
- **P&L**: Revenue vs expenses with net income, filterable by date range
- **Balance Sheet**: Assets, Liabilities, Equity sections with equation check

### 8. HR

| Route | Method | Description |
|-------|--------|-------------|
| `/hr/` | GET | Employee list |
| `/hr/new` | GET, POST | Create employee |
| `/hr/<id>` | GET | Employee detail + leave history |
| `/hr/<id>/edit` | GET, POST | Edit employee |
| `/hr/<id>/deactivate` | POST | Deactivate employee |
| `/hr/departments` | GET, POST | Manage departments |
| `/hr/leaves` | GET | All leave requests |
| `/hr/<id>/leave/new` | GET, POST | Create leave request |
| `/hr/leave/<id>/approve` | POST | Approve leave request |
| `/hr/leave/<id>/reject` | POST | Reject leave request |

Auto-generated numbers: `EMP-0001`, `EMP-0002`, ...

Leave types: `annual`, `sick`, `personal`, `unpaid`

Leave status flow: `pending` -> `approved` or `rejected` (or `cancelled`)

Fields: employee_number, first_name, last_name, email, phone, department_id, job_title, hire_date, salary

## Database Schema

### Tables (16 total)

| Table | Description | Key relationships |
|-------|-------------|-------------------|
| `users` | Auth users | - |
| `contacts` | Customers and suppliers | Referenced by sales_orders, purchase_orders, invoices |
| `categories` | Product categories | Referenced by products |
| `products` | Product catalog | Referenced by order lines, stock_movements |
| `stock_movements` | Inventory audit trail | -> products |
| `sales_orders` | Sales order headers | -> contacts |
| `sales_order_lines` | Sales order line items | -> sales_orders, products |
| `invoices` | Customer invoices | -> sales_orders, contacts |
| `invoice_lines` | Invoice line items | -> invoices, products |
| `purchase_orders` | Purchase order headers | -> contacts |
| `purchase_order_lines` | PO line items | -> purchase_orders, products |
| `accounts` | Chart of accounts | Self-referencing parent_id |
| `journal_entries` | Journal entry headers | - |
| `journal_lines` | Journal entry lines | -> journal_entries, accounts |
| `departments` | Company departments | -> employees (manager) |
| `employees` | Employee records | -> departments |
| `leave_requests` | Leave/PTO requests | -> employees |

### Constraints

- Foreign keys enforced via `PRAGMA foreign_keys = ON`
- Status fields use CHECK constraints with allowed values
- SKU, order numbers, PO numbers, invoice numbers, employee numbers are UNIQUE
- Cascade deletes on line items (order_lines, invoice_lines, journal_lines)

## Deployment

### Local

```bash
pip3 install -r requirements.txt
python3 run.py
# -> http://0.0.0.0:8080
# Login: admin / admin
```

Optional: seed sample data:
```bash
python3 -c "from seed_data import seed; seed()"
```

### Vercel

- Entrypoint: `app.py` (top-level, exports `app`)
- Config: `vercel.json` routes all requests through Flask
- DB: SQLite in `/tmp/erp.db` (ephemeral, recreated on cold start)
- Demo data auto-seeded on cold starts via `VERCEL` env var detection
- Set `SECRET_KEY` env var in Vercel dashboard for stable sessions

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | Random 32-byte hex | Flask session signing key |
| `VERCEL` | (set by Vercel) | Detected automatically; switches DB to `/tmp` |

## Dependencies

```
flask>=3.0
flask-login>=0.6
flask-wtf>=1.2
wtforms>=3.1
werkzeug>=3.0
```

## Limitations

- No REST/JSON API (all routes return server-rendered HTML)
- Single-user SQLite (no concurrent write scaling)
- No CSRF protection on forms (flask-wtf imported but not enforced)
- Tax rate hardcoded at 10%
- No file uploads or document attachments
- No email notifications
- No audit logging beyond stock movements
- Vercel deployment: data does not persist between cold starts
