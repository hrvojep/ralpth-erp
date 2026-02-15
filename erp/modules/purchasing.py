import json
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from erp.db import get_db

purchasing_bp = Blueprint("purchasing", __name__, template_folder="../templates")


def _next_po_number(db):
    row = db.execute(
        "SELECT po_number FROM purchase_orders ORDER BY id DESC LIMIT 1"
    ).fetchone()
    if row:
        last_num = int(row["po_number"].split("-")[1])
        return f"PO-{last_num + 1:04d}"
    return "PO-0001"


def _get_suppliers(db):
    return db.execute(
        "SELECT id, name FROM contacts "
        "WHERE contact_type IN ('supplier','both') AND active = 1 "
        "ORDER BY name"
    ).fetchall()


def _get_products(db):
    return db.execute(
        "SELECT id, name, sku, cost_price FROM products WHERE active = 1 ORDER BY name"
    ).fetchall()


def _products_json(products):
    return json.dumps(
        {str(p["id"]): {"name": p["name"], "sku": p["sku"], "cost_price": p["cost_price"]} for p in products}
    )


def _save_po(db, po_id, supplier_id, order_date, expected_date, notes, form):
    product_ids = form.getlist("product_id[]")
    quantities = form.getlist("quantity[]")
    unit_prices = form.getlist("unit_price[]")

    # Delete old lines if editing
    db.execute("DELETE FROM purchase_order_lines WHERE po_id = ?", (po_id,))

    subtotal = 0.0
    for pid, qty, price in zip(product_ids, quantities, unit_prices):
        if not pid:
            continue
        qty = float(qty or 0)
        price = float(price or 0)
        line_total = round(qty * price, 2)
        subtotal += line_total
        db.execute(
            "INSERT INTO purchase_order_lines (po_id, product_id, quantity, unit_price, line_total) "
            "VALUES (?, ?, ?, ?, ?)",
            (po_id, int(pid), qty, price, line_total),
        )

    subtotal = round(subtotal, 2)
    tax_amount = round(subtotal * 0.10, 2)
    total = round(subtotal + tax_amount, 2)

    db.execute(
        "UPDATE purchase_orders SET supplier_id = ?, order_date = ?, expected_date = ?, "
        "notes = ?, subtotal = ?, tax_amount = ?, total = ? WHERE id = ?",
        (supplier_id, order_date, expected_date or None, notes, subtotal, tax_amount, total, po_id),
    )
    db.commit()


@purchasing_bp.route("/")
@login_required
def index():
    db = get_db()
    orders = db.execute(
        "SELECT po.*, c.name AS supplier_name "
        "FROM purchase_orders po "
        "JOIN contacts c ON po.supplier_id = c.id "
        "ORDER BY po.created_at DESC"
    ).fetchall()
    db.close()
    return render_template("purchasing/index.html", orders=orders)


@purchasing_bp.route("/new", methods=["GET", "POST"])
@login_required
def new():
    db = get_db()
    suppliers = _get_suppliers(db)
    products = _get_products(db)

    if request.method == "POST":
        supplier_id = request.form.get("supplier_id", "").strip()
        order_date = request.form.get("order_date", "").strip()

        if not supplier_id or not order_date:
            flash("Supplier and order date are required.", "error")
            db.close()
            return render_template(
                "purchasing/form.html",
                po=None,
                suppliers=suppliers,
                products=products,
                products_json=_products_json(products),
                editing=False,
            )

        po_number = _next_po_number(db)
        expected_date = request.form.get("expected_date", "").strip() or None
        notes = request.form.get("notes", "").strip()

        db.execute(
            "INSERT INTO purchase_orders (po_number, supplier_id, order_date, expected_date, notes) "
            "VALUES (?, ?, ?, ?, ?)",
            (po_number, int(supplier_id), order_date, expected_date, notes),
        )
        po_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]

        _save_po(db, po_id, int(supplier_id), order_date, expected_date, notes, request.form)
        db.close()

        flash("Purchase order created successfully.", "success")
        return redirect(url_for("purchasing.detail", id=po_id))

    db.close()
    return render_template(
        "purchasing/form.html",
        po=None,
        suppliers=suppliers,
        products=products,
        products_json=_products_json(products),
        editing=False,
    )


@purchasing_bp.route("/<int:id>")
@login_required
def detail(id):
    db = get_db()
    po = db.execute(
        "SELECT po.*, c.name AS supplier_name "
        "FROM purchase_orders po "
        "JOIN contacts c ON po.supplier_id = c.id "
        "WHERE po.id = ?",
        (id,),
    ).fetchone()

    if not po:
        db.close()
        flash("Purchase order not found.", "error")
        return redirect(url_for("purchasing.index"))

    lines = db.execute(
        "SELECT pol.*, p.name AS product_name, p.sku "
        "FROM purchase_order_lines pol "
        "JOIN products p ON pol.product_id = p.id "
        "WHERE pol.po_id = ? "
        "ORDER BY pol.id",
        (id,),
    ).fetchall()
    db.close()

    return render_template("purchasing/detail.html", po=po, lines=lines)


@purchasing_bp.route("/<int:id>/edit", methods=["GET", "POST"])
@login_required
def edit(id):
    db = get_db()
    po = db.execute("SELECT * FROM purchase_orders WHERE id = ?", (id,)).fetchone()

    if not po:
        db.close()
        flash("Purchase order not found.", "error")
        return redirect(url_for("purchasing.index"))

    if po["status"] != "draft":
        db.close()
        flash("Only draft purchase orders can be edited.", "error")
        return redirect(url_for("purchasing.detail", id=id))

    suppliers = _get_suppliers(db)
    products = _get_products(db)

    if request.method == "POST":
        supplier_id = request.form.get("supplier_id", "").strip()
        order_date = request.form.get("order_date", "").strip()

        if not supplier_id or not order_date:
            flash("Supplier and order date are required.", "error")
            lines = db.execute(
                "SELECT pol.*, p.name AS product_name "
                "FROM purchase_order_lines pol "
                "JOIN products p ON pol.product_id = p.id "
                "WHERE pol.po_id = ? ORDER BY pol.id",
                (id,),
            ).fetchall()
            db.close()
            return render_template(
                "purchasing/form.html",
                po=po,
                lines=lines,
                suppliers=suppliers,
                products=products,
                products_json=_products_json(products),
                editing=True,
            )

        expected_date = request.form.get("expected_date", "").strip() or None
        notes = request.form.get("notes", "").strip()

        _save_po(db, id, int(supplier_id), order_date, expected_date, notes, request.form)
        db.close()

        flash("Purchase order updated successfully.", "success")
        return redirect(url_for("purchasing.detail", id=id))

    lines = db.execute(
        "SELECT pol.*, p.name AS product_name "
        "FROM purchase_order_lines pol "
        "JOIN products p ON pol.product_id = p.id "
        "WHERE pol.po_id = ? ORDER BY pol.id",
        (id,),
    ).fetchall()
    db.close()

    return render_template(
        "purchasing/form.html",
        po=po,
        lines=lines,
        suppliers=suppliers,
        products=products,
        products_json=_products_json(products),
        editing=True,
    )


@purchasing_bp.route("/<int:id>/confirm", methods=["POST"])
@login_required
def confirm(id):
    db = get_db()
    po = db.execute("SELECT * FROM purchase_orders WHERE id = ?", (id,)).fetchone()

    if not po:
        db.close()
        flash("Purchase order not found.", "error")
        return redirect(url_for("purchasing.index"))

    if po["status"] != "draft":
        db.close()
        flash("Only draft purchase orders can be confirmed.", "error")
        return redirect(url_for("purchasing.detail", id=id))

    db.execute("UPDATE purchase_orders SET status = 'confirmed' WHERE id = ?", (id,))
    db.commit()
    db.close()

    flash("Purchase order confirmed.", "success")
    return redirect(url_for("purchasing.detail", id=id))


@purchasing_bp.route("/<int:id>/receive", methods=["POST"])
@login_required
def receive(id):
    db = get_db()
    po = db.execute("SELECT * FROM purchase_orders WHERE id = ?", (id,)).fetchone()

    if not po:
        db.close()
        flash("Purchase order not found.", "error")
        return redirect(url_for("purchasing.index"))

    if po["status"] != "confirmed":
        db.close()
        flash("Only confirmed purchase orders can be received.", "error")
        return redirect(url_for("purchasing.detail", id=id))

    lines = db.execute(
        "SELECT * FROM purchase_order_lines WHERE po_id = ?", (id,)
    ).fetchall()

    for line in lines:
        # Increase product stock
        db.execute(
            "UPDATE products SET stock_qty = stock_qty + ? WHERE id = ?",
            (line["quantity"], line["product_id"]),
        )
        # Insert stock movement
        db.execute(
            "INSERT INTO stock_movements (product_id, movement_type, quantity, reference, notes) "
            "VALUES (?, 'in', ?, ?, ?)",
            (line["product_id"], line["quantity"], po["po_number"], f"Received from PO {po['po_number']}"),
        )

    db.execute("UPDATE purchase_orders SET status = 'received' WHERE id = ?", (id,))
    db.commit()
    db.close()

    flash("Purchase order received. Stock quantities updated.", "success")
    return redirect(url_for("purchasing.detail", id=id))


@purchasing_bp.route("/<int:id>/cancel", methods=["POST"])
@login_required
def cancel(id):
    db = get_db()
    po = db.execute("SELECT * FROM purchase_orders WHERE id = ?", (id,)).fetchone()

    if not po:
        db.close()
        flash("Purchase order not found.", "error")
        return redirect(url_for("purchasing.index"))

    if po["status"] in ("received", "invoiced"):
        db.close()
        flash("Cannot cancel a received or invoiced purchase order.", "error")
        return redirect(url_for("purchasing.detail", id=id))

    db.execute("UPDATE purchase_orders SET status = 'cancelled' WHERE id = ?", (id,))
    db.commit()
    db.close()

    flash("Purchase order cancelled.", "success")
    return redirect(url_for("purchasing.detail", id=id))
