#!/usr/bin/env python3
"""Populate the ERP database with realistic sample data."""
import sqlite3
import os

from erp.db import DB_PATH

def seed():
    db = sqlite3.connect(DB_PATH)
    db.execute("PRAGMA foreign_keys = ON")

    # --- Contacts ---
    contacts = [
        ("Acme Corporation", "customer", "sales@acme.com", "+1-555-0101", "123 Industrial Blvd", "Chicago", "US", "US-12-3456789"),
        ("TechParts Global", "supplier", "orders@techparts.com", "+1-555-0202", "456 Supply Chain Dr", "Houston", "US", "US-98-7654321"),
        ("Green Valley Foods", "customer", "info@greenvalley.com", "+1-555-0303", "789 Harvest Lane", "Portland", "US", "US-45-1234567"),
        ("Pacific Trading Co", "both", "contact@pacifictrading.com", "+1-555-0404", "321 Harbor Way", "San Francisco", "US", "US-67-8901234"),
        ("Nordic Electronics AB", "supplier", "procurement@nordic-elec.se", "+46-8-555-0505", "Teknikvägen 12", "Stockholm", "SE", "SE-556789-0123"),
        ("Bright Future LLC", "customer", "hello@brightfuture.com", "+1-555-0606", "55 Innovation Park", "Austin", "US", "US-33-4567890"),
        ("Atlas Machinery", "supplier", "sales@atlasmachinery.de", "+49-30-555-0707", "Industriestr. 88", "Berlin", "DE", "DE-123456789"),
        ("Summit Retail Group", "customer", "purchasing@summitretail.com", "+1-555-0808", "900 Commerce St", "Denver", "US", "US-78-9012345"),
        ("Oceanic Imports Ltd", "both", "trade@oceanic.co.uk", "+44-20-555-0909", "14 Docklands Road", "London", "GB", "GB-987654321"),
        ("Sunrise Manufacturing", "supplier", "supply@sunrisemfg.cn", "+86-21-555-1010", "88 Pudong Ave", "Shanghai", "CN", "CN-310115678"),
        ("Mountain View Services", "customer", "info@mountainview.com", "+1-555-1111", "2200 Tech Rd", "Seattle", "US", "US-22-3456789"),
        ("Delta Wholesale", "both", "orders@deltawholesale.com", "+1-555-1212", "430 Distribution Ave", "Atlanta", "US", "US-11-2345678"),
    ]
    db.executemany(
        "INSERT INTO contacts (name, contact_type, email, phone, address, city, country, tax_id) VALUES (?,?,?,?,?,?,?,?)",
        contacts,
    )

    # --- Categories ---
    categories = [
        ("Electronics", "Electronic components and devices"),
        ("Office Supplies", "General office and stationery items"),
        ("Furniture", "Office and warehouse furniture"),
        ("Raw Materials", "Manufacturing raw materials"),
        ("Software", "Software licenses and subscriptions"),
    ]
    db.executemany("INSERT INTO categories (name, description) VALUES (?,?)", categories)

    # --- Products ---
    products = [
        ("SKU-1001", "Laptop Pro 15", "15-inch professional laptop, 16GB RAM, 512GB SSD", 1, 1299.99, 850.00, 45, 10, "unit"),
        ("SKU-1002", "Wireless Mouse", "Ergonomic wireless mouse with USB receiver", 1, 29.99, 12.50, 200, 50, "unit"),
        ("SKU-1003", "USB-C Hub 7-port", "7-port USB-C hub with HDMI and Ethernet", 1, 59.99, 28.00, 120, 30, "unit"),
        ("SKU-1004", "Mechanical Keyboard", "Cherry MX Blue switches, full-size", 1, 89.99, 42.00, 85, 20, "unit"),
        ("SKU-2001", "A4 Copy Paper", "80gsm white A4 paper, 500 sheets per ream", 2, 8.99, 4.50, 500, 100, "ream"),
        ("SKU-2002", "Ballpoint Pens (12pk)", "Blue ink ballpoint pens, medium point", 2, 6.49, 2.80, 300, 60, "pack"),
        ("SKU-2003", "Sticky Notes Assorted", "3x3 inch sticky notes, 12 pads", 2, 11.99, 5.20, 150, 30, "pack"),
        ("SKU-3001", "Standing Desk", "Electric height-adjustable standing desk, 60x30", 3, 549.99, 320.00, 15, 5, "unit"),
        ("SKU-3002", "Ergonomic Chair", "Mesh back ergonomic office chair with lumbar support", 3, 399.99, 210.00, 22, 5, "unit"),
        ("SKU-3003", "Filing Cabinet 3-Drawer", "Steel 3-drawer filing cabinet, lockable", 3, 179.99, 95.00, 18, 5, "unit"),
        ("SKU-4001", "Steel Sheet 4x8", "Cold-rolled steel sheet, 4ft x 8ft, 16 gauge", 4, 89.00, 62.00, 75, 20, "sheet"),
        ("SKU-4002", "Aluminum Rod 1in", "6061 aluminum rod, 1 inch diameter, 6ft length", 4, 24.50, 15.00, 200, 40, "piece"),
        ("SKU-5001", "Office Suite License", "Annual office productivity suite license", 5, 149.99, 95.00, 999, 10, "license"),
        ("SKU-5002", "Antivirus Pro", "Annual antivirus subscription, 5 devices", 5, 79.99, 45.00, 999, 10, "license"),
    ]
    db.executemany(
        "INSERT INTO products (sku, name, description, category_id, unit_price, cost_price, stock_qty, reorder_level, unit) VALUES (?,?,?,?,?,?,?,?,?)",
        products,
    )

    # Stock movements for initial inventory
    for i, p in enumerate(products, 1):
        db.execute(
            "INSERT INTO stock_movements (product_id, movement_type, quantity, reference, notes) VALUES (?,?,?,?,?)",
            (i, "in", p[6], "INIT", "Initial inventory load"),
        )

    # --- Sales Orders ---
    sales_orders = [
        ("SO-0001", 1, "2025-11-15", "invoiced", "First big order from Acme"),
        ("SO-0002", 3, "2025-12-01", "confirmed", "Green Valley holiday order"),
        ("SO-0003", 6, "2025-12-10", "shipped", "Bright Future office setup"),
        ("SO-0004", 8, "2026-01-05", "confirmed", "Summit Retail Q1 order"),
        ("SO-0005", 11, "2026-01-20", "draft", "Mountain View initial inquiry"),
        ("SO-0006", 1, "2026-02-01", "draft", "Acme February restock"),
        ("SO-0007", 4, "2026-02-05", "confirmed", "Pacific Trading mixed order"),
        ("SO-0008", 9, "2026-02-10", "draft", "Oceanic Imports bulk request"),
    ]
    so_lines = [
        # SO-0001: Acme - laptops and accessories
        (1, 1, "", 10, 1299.99, 12999.90),
        (1, 2, "", 20, 29.99, 599.80),
        (1, 4, "", 10, 89.99, 899.90),
        # SO-0002: Green Valley - office supplies
        (2, 5, "", 50, 8.99, 449.50),
        (2, 6, "", 30, 6.49, 194.70),
        (2, 7, "", 20, 11.99, 239.80),
        # SO-0003: Bright Future - office setup
        (3, 8, "", 5, 549.99, 2749.95),
        (3, 9, "", 5, 399.99, 1999.95),
        (3, 1, "", 5, 1299.99, 6499.95),
        (3, 2, "", 5, 29.99, 149.95),
        # SO-0004: Summit Retail
        (4, 1, "", 8, 1299.99, 10399.92),
        (4, 3, "", 15, 59.99, 899.85),
        (4, 13, "", 20, 149.99, 2999.80),
        # SO-0005: Mountain View
        (5, 9, "", 10, 399.99, 3999.90),
        (5, 8, "", 10, 549.99, 5499.90),
        # SO-0006: Acme restock
        (6, 2, "", 50, 29.99, 1499.50),
        (6, 3, "", 25, 59.99, 1499.75),
        (6, 4, "", 15, 89.99, 1349.85),
        # SO-0007: Pacific Trading
        (7, 11, "", 20, 89.00, 1780.00),
        (7, 12, "", 40, 24.50, 980.00),
        (7, 5, "", 25, 8.99, 224.75),
        # SO-0008: Oceanic Imports
        (8, 1, "", 15, 1299.99, 19499.85),
        (8, 4, "", 30, 89.99, 2699.70),
        (8, 14, "", 50, 79.99, 3999.50),
    ]
    for so in sales_orders:
        lines = [l for l in so_lines if l[0] == sales_orders.index(so) + 1]
        subtotal = sum(l[5] for l in lines)
        tax = round(subtotal * 0.10, 2)
        total = round(subtotal + tax, 2)
        db.execute(
            "INSERT INTO sales_orders (order_number, customer_id, order_date, status, subtotal, tax_amount, total, notes) VALUES (?,?,?,?,?,?,?,?)",
            (so[0], so[1], so[2], so[3], round(subtotal, 2), tax, total, so[4]),
        )
    for line in so_lines:
        db.execute(
            "INSERT INTO sales_order_lines (order_id, product_id, description, quantity, unit_price, line_total) VALUES (?,?,?,?,?,?)",
            (line[0], line[1], line[2], line[3], line[4], line[5]),
        )

    # --- Invoices (from SO-0001 which is invoiced) ---
    so1_subtotal = 12999.90 + 599.80 + 899.90
    so1_tax = round(so1_subtotal * 0.10, 2)
    so1_total = round(so1_subtotal + so1_tax, 2)
    db.execute(
        "INSERT INTO invoices (invoice_number, sales_order_id, customer_id, invoice_date, due_date, status, subtotal, tax_amount, total, amount_paid, notes) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        ("INV-0001", 1, 1, "2025-11-20", "2025-12-20", "paid", round(so1_subtotal, 2), so1_tax, so1_total, so1_total, "Payment received in full"),
    )
    db.execute("INSERT INTO invoice_lines (invoice_id, product_id, description, quantity, unit_price, line_total) VALUES (?,?,?,?,?,?)", (1, 1, "Laptop Pro 15", 10, 1299.99, 12999.90))
    db.execute("INSERT INTO invoice_lines (invoice_id, product_id, description, quantity, unit_price, line_total) VALUES (?,?,?,?,?,?)", (1, 2, "Wireless Mouse", 20, 29.99, 599.80))
    db.execute("INSERT INTO invoice_lines (invoice_id, product_id, description, quantity, unit_price, line_total) VALUES (?,?,?,?,?,?)", (1, 4, "Mechanical Keyboard", 10, 89.99, 899.90))

    # Second invoice - sent but unpaid
    so3_subtotal = 2749.95 + 1999.95 + 6499.95 + 149.95
    so3_tax = round(so3_subtotal * 0.10, 2)
    so3_total = round(so3_subtotal + so3_tax, 2)
    db.execute(
        "INSERT INTO invoices (invoice_number, sales_order_id, customer_id, invoice_date, due_date, status, subtotal, tax_amount, total, amount_paid) VALUES (?,?,?,?,?,?,?,?,?,?)",
        ("INV-0002", 3, 6, "2025-12-15", "2026-01-15", "sent", round(so3_subtotal, 2), so3_tax, so3_total, 0),
    )
    db.execute("INSERT INTO invoice_lines (invoice_id, product_id, description, quantity, unit_price, line_total) VALUES (?,?,?,?,?,?)", (2, 8, "Standing Desk", 5, 549.99, 2749.95))
    db.execute("INSERT INTO invoice_lines (invoice_id, product_id, description, quantity, unit_price, line_total) VALUES (?,?,?,?,?,?)", (2, 9, "Ergonomic Chair", 5, 399.99, 1999.95))
    db.execute("INSERT INTO invoice_lines (invoice_id, product_id, description, quantity, unit_price, line_total) VALUES (?,?,?,?,?,?)", (2, 1, "Laptop Pro 15", 5, 1299.99, 6499.95))
    db.execute("INSERT INTO invoice_lines (invoice_id, product_id, description, quantity, unit_price, line_total) VALUES (?,?,?,?,?,?)", (2, 2, "Wireless Mouse", 5, 29.99, 149.95))

    # --- Purchase Orders ---
    purchase_orders = [
        ("PO-0001", 2, "2025-11-01", "2025-11-15", "received", "Restock electronics from TechParts"),
        ("PO-0002", 5, "2025-12-05", "2025-12-20", "received", "Nordic Electronics shipment"),
        ("PO-0003", 7, "2026-01-10", "2026-01-25", "confirmed", "Atlas Machinery furniture order"),
        ("PO-0004", 10, "2026-01-28", "2026-02-15", "confirmed", "Raw materials from Sunrise"),
        ("PO-0005", 2, "2026-02-05", "2026-02-20", "draft", "TechParts Q1 restock"),
    ]
    po_lines = [
        # PO-0001: TechParts - electronics
        (1, 1, "", 20, 850.00, 17000.00),
        (1, 2, "", 100, 12.50, 1250.00),
        (1, 3, "", 50, 28.00, 1400.00),
        # PO-0002: Nordic - keyboards + mice
        (2, 4, "", 50, 42.00, 2100.00),
        (2, 2, "", 80, 12.50, 1000.00),
        # PO-0003: Atlas - furniture
        (3, 8, "", 10, 320.00, 3200.00),
        (3, 9, "", 10, 210.00, 2100.00),
        (3, 10, "", 8, 95.00, 760.00),
        # PO-0004: Sunrise - raw materials
        (4, 11, "", 50, 62.00, 3100.00),
        (4, 12, "", 100, 15.00, 1500.00),
        # PO-0005: TechParts - restock
        (5, 1, "", 15, 850.00, 12750.00),
        (5, 3, "", 40, 28.00, 1120.00),
    ]
    for po in purchase_orders:
        idx = purchase_orders.index(po) + 1
        lines = [l for l in po_lines if l[0] == idx]
        subtotal = sum(l[5] for l in lines)
        tax = round(subtotal * 0.10, 2)
        total = round(subtotal + tax, 2)
        db.execute(
            "INSERT INTO purchase_orders (po_number, supplier_id, order_date, expected_date, status, subtotal, tax_amount, total, notes) VALUES (?,?,?,?,?,?,?,?,?)",
            (po[0], po[1], po[2], po[3], po[4], round(subtotal, 2), tax, total, po[5]),
        )
    for line in po_lines:
        db.execute(
            "INSERT INTO purchase_order_lines (po_id, product_id, description, quantity, unit_price, line_total) VALUES (?,?,?,?,?,?)",
            (line[0], line[1], line[2], line[3], line[4], line[5]),
        )

    # --- Journal Entries ---
    # JE1: Record initial capital investment
    db.execute("INSERT INTO journal_entries (entry_date, reference, description, posted) VALUES (?,?,?,?)",
               ("2025-10-01", "JE-001", "Initial capital investment", 1))
    db.execute("INSERT INTO journal_lines (entry_id, account_id, debit, credit) VALUES (?,?,?,?)", (1, 1, 100000.00, 0))  # Debit Cash
    db.execute("INSERT INTO journal_lines (entry_id, account_id, debit, credit) VALUES (?,?,?,?)", (1, 10, 0, 100000.00))  # Credit Owner's Equity

    # JE2: Record inventory purchase (PO-0001 received)
    db.execute("INSERT INTO journal_entries (entry_date, reference, description, posted) VALUES (?,?,?,?)",
               ("2025-11-15", "JE-002", "Inventory from PO-0001 - TechParts", 1))
    db.execute("INSERT INTO journal_lines (entry_id, account_id, debit, credit) VALUES (?,?,?,?)", (2, 3, 19650.00, 0))   # Debit Inventory
    db.execute("INSERT INTO journal_lines (entry_id, account_id, debit, credit) VALUES (?,?,?,?)", (2, 6, 0, 19650.00))   # Credit Accounts Payable

    # JE3: Record revenue from INV-0001 (paid)
    db.execute("INSERT INTO journal_entries (entry_date, reference, description, posted) VALUES (?,?,?,?)",
               ("2025-11-20", "JE-003", "Revenue from INV-0001 - Acme Corporation", 1))
    db.execute("INSERT INTO journal_lines (entry_id, account_id, debit, credit) VALUES (?,?,?,?)", (3, 2, 15949.56, 0))   # Debit AR
    db.execute("INSERT INTO journal_lines (entry_id, account_id, debit, credit) VALUES (?,?,?,?)", (3, 12, 0, 14499.60, ))  # Credit Sales Revenue
    db.execute("INSERT INTO journal_lines (entry_id, account_id, debit, credit) VALUES (?,?,?,?)", (3, 8, 0, 1449.96))    # Credit Tax Payable

    # JE4: Record payment received from Acme
    db.execute("INSERT INTO journal_entries (entry_date, reference, description, posted) VALUES (?,?,?,?)",
               ("2025-12-05", "JE-004", "Payment received for INV-0001", 1))
    db.execute("INSERT INTO journal_lines (entry_id, account_id, debit, credit) VALUES (?,?,?,?)", (4, 1, 15949.56, 0))   # Debit Cash
    db.execute("INSERT INTO journal_lines (entry_id, account_id, debit, credit) VALUES (?,?,?,?)", (4, 2, 0, 15949.56))   # Credit AR

    # JE5: Record COGS for SO-0001
    db.execute("INSERT INTO journal_entries (entry_date, reference, description, posted) VALUES (?,?,?,?)",
               ("2025-11-20", "JE-005", "COGS for SO-0001", 1))
    cogs = (10 * 850) + (20 * 12.50) + (10 * 42.00)  # 8500 + 250 + 420 = 9170
    db.execute("INSERT INTO journal_lines (entry_id, account_id, debit, credit) VALUES (?,?,?,?)", (5, 15, cogs, 0))      # Debit COGS
    db.execute("INSERT INTO journal_lines (entry_id, account_id, debit, credit) VALUES (?,?,?,?)", (5, 3, 0, cogs))       # Credit Inventory

    # JE6: Monthly rent
    db.execute("INSERT INTO journal_entries (entry_date, reference, description, posted) VALUES (?,?,?,?)",
               ("2026-01-01", "JE-006", "January rent payment", 1))
    db.execute("INSERT INTO journal_lines (entry_id, account_id, debit, credit) VALUES (?,?,?,?)", (6, 17, 3500.00, 0))   # Debit Rent Expense
    db.execute("INSERT INTO journal_lines (entry_id, account_id, debit, credit) VALUES (?,?,?,?)", (6, 1, 0, 3500.00))    # Credit Cash

    # JE7: Salary expense
    db.execute("INSERT INTO journal_entries (entry_date, reference, description, posted) VALUES (?,?,?,?)",
               ("2026-01-31", "JE-007", "January salaries", 1))
    db.execute("INSERT INTO journal_lines (entry_id, account_id, debit, credit) VALUES (?,?,?,?)", (7, 16, 28500.00, 0))  # Debit Salaries
    db.execute("INSERT INTO journal_lines (entry_id, account_id, debit, credit) VALUES (?,?,?,?)", (7, 1, 0, 28500.00))   # Credit Cash

    # JE8: Unposted draft entry
    db.execute("INSERT INTO journal_entries (entry_date, reference, description, posted) VALUES (?,?,?,?)",
               ("2026-02-10", "JE-008", "February rent accrual", 0))
    db.execute("INSERT INTO journal_lines (entry_id, account_id, debit, credit) VALUES (?,?,?,?)", (8, 17, 3500.00, 0))
    db.execute("INSERT INTO journal_lines (entry_id, account_id, debit, credit) VALUES (?,?,?,?)", (8, 7, 0, 3500.00))

    # Update account balances for posted entries
    db.execute("UPDATE accounts SET balance = 83949.56 WHERE code = '1000'")   # Cash: 100000 + 15949.56 - 3500 - 28500
    db.execute("UPDATE accounts SET balance = 0 WHERE code = '1100'")          # AR: 15949.56 - 15949.56
    db.execute("UPDATE accounts SET balance = 10480.00 WHERE code = '1200'")   # Inventory: 19650 - 9170
    db.execute("UPDATE accounts SET balance = 19650.00 WHERE code = '2000'")   # AP
    db.execute("UPDATE accounts SET balance = 1449.96 WHERE code = '2200'")    # Tax Payable
    db.execute("UPDATE accounts SET balance = 100000.00 WHERE code = '3000'")  # Owner's Equity
    db.execute("UPDATE accounts SET balance = 14499.60 WHERE code = '4000'")   # Sales Revenue
    db.execute("UPDATE accounts SET balance = 9170.00 WHERE code = '5000'")    # COGS
    db.execute("UPDATE accounts SET balance = 28500.00 WHERE code = '5100'")   # Salaries
    db.execute("UPDATE accounts SET balance = 3500.00 WHERE code = '5200'")    # Rent

    # --- Departments ---
    departments = [
        ("Engineering",),
        ("Sales",),
        ("Operations",),
        ("Finance",),
        ("Human Resources",),
    ]
    db.executemany("INSERT INTO departments (name) VALUES (?)", departments)

    # --- Employees ---
    employees = [
        ("EMP-0001", "Sarah", "Chen", "sarah.chen@erp.local", "+1-555-2001", 1, "VP of Engineering", "2023-03-15", 145000),
        ("EMP-0002", "James", "Rodriguez", "james.r@erp.local", "+1-555-2002", 2, "Sales Director", "2023-06-01", 125000),
        ("EMP-0003", "Emily", "Thompson", "emily.t@erp.local", "+1-555-2003", 1, "Senior Developer", "2023-09-01", 120000),
        ("EMP-0004", "Michael", "Park", "michael.p@erp.local", "+1-555-2004", 3, "Operations Manager", "2024-01-15", 95000),
        ("EMP-0005", "Lisa", "Nguyen", "lisa.n@erp.local", "+1-555-2005", 4, "Financial Analyst", "2024-03-01", 88000),
        ("EMP-0006", "David", "Williams", "david.w@erp.local", "+1-555-2006", 1, "Full Stack Developer", "2024-04-15", 105000),
        ("EMP-0007", "Anna", "Kowalski", "anna.k@erp.local", "+1-555-2007", 2, "Account Executive", "2024-06-01", 78000),
        ("EMP-0008", "Robert", "Singh", "robert.s@erp.local", "+1-555-2008", 5, "HR Coordinator", "2024-07-01", 72000),
        ("EMP-0009", "Maria", "Garcia", "maria.g@erp.local", "+1-555-2009", 3, "Warehouse Supervisor", "2024-09-01", 68000),
        ("EMP-0010", "Kevin", "O'Brien", "kevin.ob@erp.local", "+1-555-2010", 1, "Junior Developer", "2025-01-15", 75000),
    ]
    db.executemany(
        "INSERT INTO employees (employee_number, first_name, last_name, email, phone, department_id, job_title, hire_date, salary) VALUES (?,?,?,?,?,?,?,?,?)",
        employees,
    )

    # --- Leave Requests ---
    leave_requests = [
        (1, "annual", "2026-02-17", "2026-02-21", "approved", "Family vacation"),
        (3, "sick", "2026-01-13", "2026-01-14", "approved", "Flu"),
        (5, "annual", "2026-03-03", "2026-03-07", "pending", "Spring break trip"),
        (7, "personal", "2026-02-14", "2026-02-14", "approved", "Personal appointment"),
        (2, "annual", "2026-04-07", "2026-04-11", "pending", "Holiday planned"),
        (9, "sick", "2026-02-03", "2026-02-04", "approved", "Back pain"),
        (10, "unpaid", "2026-03-15", "2026-03-20", "pending", "Moving to new apartment"),
        (4, "annual", "2026-01-27", "2026-01-31", "rejected", "Insufficient leave balance"),
    ]
    db.executemany(
        "INSERT INTO leave_requests (employee_id, leave_type, start_date, end_date, status, reason) VALUES (?,?,?,?,?,?)",
        leave_requests,
    )

    db.commit()
    db.close()
    print("Sample data seeded successfully!")
    print(f"  12 contacts, 5 categories, 14 products")
    print(f"  8 sales orders, 2 invoices, 5 purchase orders")
    print(f"  8 journal entries (7 posted, 1 draft)")
    print(f"  5 departments, 10 employees, 8 leave requests")


if __name__ == "__main__":
    seed()
