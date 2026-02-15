from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from erp.db import get_db
import json
from datetime import date

sales_bp = Blueprint("sales", __name__, template_folder="../templates")


def _next_order_number(db):
    row = db.execute(
        "SELECT order_number FROM sales_orders ORDER BY id DESC LIMIT 1"
    ).fetchone()
    if row:
        seq = int(row["order_number"].split("-")[1]) + 1
    else:
        seq = 1
    return f"SO-{seq:04d}"


def _next_invoice_number(db):
    row = db.execute(
        "SELECT invoice_number FROM invoices ORDER BY id DESC LIMIT 1"
    ).fetchone()
    if row:
        seq = int(row["invoice_number"].split("-")[1]) + 1
    else:
        seq = 1
    return f"INV-{seq:04d}"


def _get_customers(db):
    return db.execute(
        "SELECT id, name FROM contacts WHERE active = 1 "
        "AND contact_type IN ('customer', 'both') ORDER BY name"
    ).fetchall()


def _get_products(db):
    return db.execute(
        "SELECT id, name, unit_price FROM products WHERE active = 1 ORDER BY name"
    ).fetchall()


def _save_order_lines(db, order_id, form):
    """Parse line item arrays from form and insert into sales_order_lines."""
    product_ids = form.getlist("product_id[]")
    quantities = form.getlist("quantity[]")
    unit_prices = form.getlist("unit_price[]")

    subtotal = 0.0
    for i in range(len(product_ids)):
        pid = product_ids[i]
        qty = quantities[i]
        price = unit_prices[i]

        if not pid or not qty or not price:
            continue

        pid = int(pid)
        qty = float(qty)
        price = float(price)
        line_total = qty * price
        subtotal += line_total

        db.execute(
            """INSERT INTO sales_order_lines
               (order_id, product_id, quantity, unit_price, line_total)
               VALUES (?, ?, ?, ?, ?)""",
            (order_id, pid, qty, price, line_total),
        )

    tax_amount = round(subtotal * 0.1, 2)
    total = round(subtotal + tax_amount, 2)
    subtotal = round(subtotal, 2)

    db.execute(
        "UPDATE sales_orders SET subtotal = ?, tax_amount = ?, total = ? WHERE id = ?",
        (subtotal, tax_amount, total, order_id),
    )

    return subtotal, tax_amount, total


# ---------------------------------------------------------------------------
# Sales Orders
# ---------------------------------------------------------------------------

@sales_bp.route("/")
@login_required
def index():
    db = get_db()
    orders = db.execute(
        "SELECT so.*, c.name AS customer_name "
        "FROM sales_orders so "
        "JOIN contacts c ON so.customer_id = c.id "
        "ORDER BY so.created_at DESC"
    ).fetchall()
    db.close()
    return render_template("sales/index.html", orders=orders)


@sales_bp.route("/new", methods=["GET", "POST"])
@login_required
def new():
    db = get_db()

    if request.method == "POST":
        customer_id = request.form.get("customer_id")
        order_date = request.form.get("order_date", "")
        notes = request.form.get("notes", "").strip()

        if not customer_id:
            flash("Customer is required.", "error")
            customers = _get_customers(db)
            products = _get_products(db)
            db.close()
            return render_template(
                "sales/form.html",
                order=None,
                customers=customers,
                products=products,
                products_json=json.dumps([dict(p) for p in products]),
                editing=False,
            )

        order_number = _next_order_number(db)

        db.execute(
            """INSERT INTO sales_orders
               (order_number, customer_id, order_date, status, notes)
               VALUES (?, ?, ?, 'draft', ?)""",
            (order_number, int(customer_id), order_date or date.today().isoformat(), notes),
        )
        order_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]

        _save_order_lines(db, order_id, request.form)

        db.commit()
        db.close()

        flash("Sales order created successfully.", "success")
        return redirect(url_for("sales.detail", id=order_id))

    customers = _get_customers(db)
    products = _get_products(db)
    db.close()

    return render_template(
        "sales/form.html",
        order=None,
        customers=customers,
        products=products,
        products_json=json.dumps([dict(p) for p in products]),
        editing=False,
    )


@sales_bp.route("/<int:id>")
@login_required
def detail(id):
    db = get_db()
    order = db.execute(
        "SELECT so.*, c.name AS customer_name "
        "FROM sales_orders so "
        "JOIN contacts c ON so.customer_id = c.id "
        "WHERE so.id = ?",
        (id,),
    ).fetchone()

    if not order:
        db.close()
        flash("Sales order not found.", "error")
        return redirect(url_for("sales.index"))

    lines = db.execute(
        "SELECT sol.*, p.name AS product_name "
        "FROM sales_order_lines sol "
        "JOIN products p ON sol.product_id = p.id "
        "WHERE sol.order_id = ?",
        (id,),
    ).fetchall()
    db.close()

    return render_template("sales/detail.html", order=order, lines=lines)


@sales_bp.route("/<int:id>/edit", methods=["GET", "POST"])
@login_required
def edit(id):
    db = get_db()
    order = db.execute("SELECT * FROM sales_orders WHERE id = ?", (id,)).fetchone()

    if not order:
        db.close()
        flash("Sales order not found.", "error")
        return redirect(url_for("sales.index"))

    if order["status"] != "draft":
        db.close()
        flash("Only draft orders can be edited.", "error")
        return redirect(url_for("sales.detail", id=id))

    if request.method == "POST":
        customer_id = request.form.get("customer_id")
        order_date = request.form.get("order_date", "")
        notes = request.form.get("notes", "").strip()

        if not customer_id:
            flash("Customer is required.", "error")
            customers = _get_customers(db)
            products = _get_products(db)
            lines = db.execute(
                "SELECT sol.*, p.name AS product_name "
                "FROM sales_order_lines sol "
                "JOIN products p ON sol.product_id = p.id "
                "WHERE sol.order_id = ?",
                (id,),
            ).fetchall()
            db.close()
            return render_template(
                "sales/form.html",
                order=order,
                customers=customers,
                products=products,
                products_json=json.dumps([dict(p) for p in products]),
                lines=lines,
                editing=True,
            )

        db.execute(
            "UPDATE sales_orders SET customer_id = ?, order_date = ?, notes = ? WHERE id = ?",
            (int(customer_id), order_date or date.today().isoformat(), notes, id),
        )

        # Remove old lines and re-insert
        db.execute("DELETE FROM sales_order_lines WHERE order_id = ?", (id,))
        _save_order_lines(db, id, request.form)

        db.commit()
        db.close()

        flash("Sales order updated successfully.", "success")
        return redirect(url_for("sales.detail", id=id))

    customers = _get_customers(db)
    products = _get_products(db)
    lines = db.execute(
        "SELECT sol.*, p.name AS product_name "
        "FROM sales_order_lines sol "
        "JOIN products p ON sol.product_id = p.id "
        "WHERE sol.order_id = ?",
        (id,),
    ).fetchall()
    db.close()

    return render_template(
        "sales/form.html",
        order=order,
        customers=customers,
        products=products,
        products_json=json.dumps([dict(p) for p in products]),
        lines=lines,
        editing=True,
    )


@sales_bp.route("/<int:id>/confirm", methods=["POST"])
@login_required
def confirm(id):
    db = get_db()
    order = db.execute("SELECT * FROM sales_orders WHERE id = ?", (id,)).fetchone()

    if not order:
        db.close()
        flash("Sales order not found.", "error")
        return redirect(url_for("sales.index"))

    if order["status"] != "draft":
        db.close()
        flash("Only draft orders can be confirmed.", "error")
        return redirect(url_for("sales.detail", id=id))

    db.execute(
        "UPDATE sales_orders SET status = 'confirmed' WHERE id = ?", (id,)
    )
    db.commit()
    db.close()

    flash("Sales order confirmed.", "success")
    return redirect(url_for("sales.detail", id=id))


@sales_bp.route("/<int:id>/cancel", methods=["POST"])
@login_required
def cancel(id):
    db = get_db()
    order = db.execute("SELECT * FROM sales_orders WHERE id = ?", (id,)).fetchone()

    if not order:
        db.close()
        flash("Sales order not found.", "error")
        return redirect(url_for("sales.index"))

    if order["status"] in ("invoiced", "cancelled"):
        db.close()
        flash("This order cannot be cancelled.", "error")
        return redirect(url_for("sales.detail", id=id))

    db.execute(
        "UPDATE sales_orders SET status = 'cancelled' WHERE id = ?", (id,)
    )
    db.commit()
    db.close()

    flash("Sales order cancelled.", "success")
    return redirect(url_for("sales.detail", id=id))


# ---------------------------------------------------------------------------
# Invoices
# ---------------------------------------------------------------------------

@sales_bp.route("/invoices")
@login_required
def invoices():
    db = get_db()
    invoice_list = db.execute(
        "SELECT inv.*, c.name AS customer_name "
        "FROM invoices inv "
        "JOIN contacts c ON inv.customer_id = c.id "
        "ORDER BY inv.created_at DESC"
    ).fetchall()
    db.close()
    return render_template("sales/invoices.html", invoices=invoice_list)


@sales_bp.route("/<int:id>/create-invoice", methods=["POST"])
@login_required
def create_invoice(id):
    db = get_db()
    order = db.execute("SELECT * FROM sales_orders WHERE id = ?", (id,)).fetchone()

    if not order:
        db.close()
        flash("Sales order not found.", "error")
        return redirect(url_for("sales.index"))

    if order["status"] not in ("confirmed", "shipped"):
        db.close()
        flash("Only confirmed or shipped orders can be invoiced.", "error")
        return redirect(url_for("sales.detail", id=id))

    invoice_number = _next_invoice_number(db)

    db.execute(
        """INSERT INTO invoices
           (invoice_number, sales_order_id, customer_id, invoice_date,
            status, subtotal, tax_amount, total, notes)
           VALUES (?, ?, ?, ?, 'draft', ?, ?, ?, ?)""",
        (
            invoice_number,
            id,
            order["customer_id"],
            date.today().isoformat(),
            order["subtotal"],
            order["tax_amount"],
            order["total"],
            order["notes"],
        ),
    )
    invoice_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]

    # Copy lines from sales order to invoice
    lines = db.execute(
        "SELECT * FROM sales_order_lines WHERE order_id = ?", (id,)
    ).fetchall()
    for line in lines:
        db.execute(
            """INSERT INTO invoice_lines
               (invoice_id, product_id, description, quantity, unit_price, tax_rate, line_total)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                invoice_id,
                line["product_id"],
                line["description"],
                line["quantity"],
                line["unit_price"],
                line["tax_rate"],
                line["line_total"],
            ),
        )

    # Update sales order status
    db.execute(
        "UPDATE sales_orders SET status = 'invoiced' WHERE id = ?", (id,)
    )

    db.commit()
    db.close()

    flash("Invoice created successfully.", "success")
    return redirect(url_for("sales.invoice_detail", id=invoice_id))


@sales_bp.route("/invoices/<int:id>")
@login_required
def invoice_detail(id):
    db = get_db()
    invoice = db.execute(
        "SELECT inv.*, c.name AS customer_name "
        "FROM invoices inv "
        "JOIN contacts c ON inv.customer_id = c.id "
        "WHERE inv.id = ?",
        (id,),
    ).fetchone()

    if not invoice:
        db.close()
        flash("Invoice not found.", "error")
        return redirect(url_for("sales.invoices"))

    lines = db.execute(
        "SELECT il.*, p.name AS product_name "
        "FROM invoice_lines il "
        "LEFT JOIN products p ON il.product_id = p.id "
        "WHERE il.invoice_id = ?",
        (id,),
    ).fetchall()
    db.close()

    return render_template("sales/invoice_detail.html", invoice=invoice, lines=lines)


@sales_bp.route("/invoices/<int:id>/mark-paid", methods=["POST"])
@login_required
def mark_paid(id):
    db = get_db()
    invoice = db.execute("SELECT * FROM invoices WHERE id = ?", (id,)).fetchone()

    if not invoice:
        db.close()
        flash("Invoice not found.", "error")
        return redirect(url_for("sales.invoices"))

    if invoice["status"] == "paid":
        db.close()
        flash("Invoice is already paid.", "error")
        return redirect(url_for("sales.invoice_detail", id=id))

    db.execute(
        "UPDATE invoices SET status = 'paid', amount_paid = total WHERE id = ?",
        (id,),
    )
    db.commit()
    db.close()

    flash("Invoice marked as paid.", "success")
    return redirect(url_for("sales.invoice_detail", id=id))
