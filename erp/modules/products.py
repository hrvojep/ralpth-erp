import sqlite3

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from erp.db import get_db

products_bp = Blueprint("products", __name__, template_folder="../templates")


@products_bp.route("/")
@login_required
def index():
    db = get_db()
    products = db.execute(
        """SELECT p.*, c.name AS category_name
           FROM products p
           LEFT JOIN categories c ON p.category_id = c.id
           ORDER BY p.name"""
    ).fetchall()
    db.close()
    return render_template("products/index.html", products=products)


@products_bp.route("/new", methods=["GET", "POST"])
@login_required
def new():
    db = get_db()
    if request.method == "POST":
        try:
            db.execute(
                """INSERT INTO products
                   (sku, name, description, category_id, unit_price, cost_price,
                    stock_qty, reorder_level, unit)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    request.form["sku"].strip(),
                    request.form["name"].strip(),
                    request.form.get("description", "").strip(),
                    request.form.get("category_id") or None,
                    float(request.form.get("unit_price") or 0),
                    float(request.form.get("cost_price") or 0),
                    float(request.form.get("stock_qty") or 0),
                    float(request.form.get("reorder_level") or 0),
                    request.form.get("unit", "unit").strip() or "unit",
                ),
            )
            db.commit()
            flash("Product created successfully.", "success")
            db.close()
            return redirect(url_for("products.index"))
        except sqlite3.IntegrityError:
            flash("A product with that SKU already exists.", "error")

    categories = db.execute(
        "SELECT * FROM categories ORDER BY name"
    ).fetchall()
    db.close()
    return render_template("products/form.html", product=None, categories=categories)


@products_bp.route("/<int:id>")
@login_required
def detail(id):
    db = get_db()
    product = db.execute(
        """SELECT p.*, c.name AS category_name
           FROM products p
           LEFT JOIN categories c ON p.category_id = c.id
           WHERE p.id = ?""",
        (id,),
    ).fetchone()
    if not product:
        db.close()
        flash("Product not found.", "error")
        return redirect(url_for("products.index"))

    movements = db.execute(
        """SELECT * FROM stock_movements
           WHERE product_id = ?
           ORDER BY created_at DESC""",
        (id,),
    ).fetchall()
    db.close()
    return render_template(
        "products/detail.html", product=product, movements=movements
    )


@products_bp.route("/<int:id>/edit", methods=["GET", "POST"])
@login_required
def edit(id):
    db = get_db()
    product = db.execute("SELECT * FROM products WHERE id = ?", (id,)).fetchone()
    if not product:
        db.close()
        flash("Product not found.", "error")
        return redirect(url_for("products.index"))

    if request.method == "POST":
        try:
            db.execute(
                """UPDATE products
                   SET sku = ?, name = ?, description = ?, category_id = ?,
                       unit_price = ?, cost_price = ?, stock_qty = ?,
                       reorder_level = ?, unit = ?
                   WHERE id = ?""",
                (
                    request.form["sku"].strip(),
                    request.form["name"].strip(),
                    request.form.get("description", "").strip(),
                    request.form.get("category_id") or None,
                    float(request.form.get("unit_price") or 0),
                    float(request.form.get("cost_price") or 0),
                    float(request.form.get("stock_qty") or 0),
                    float(request.form.get("reorder_level") or 0),
                    request.form.get("unit", "unit").strip() or "unit",
                    id,
                ),
            )
            db.commit()
            flash("Product updated successfully.", "success")
            db.close()
            return redirect(url_for("products.detail", id=id))
        except sqlite3.IntegrityError:
            flash("A product with that SKU already exists.", "error")

    categories = db.execute(
        "SELECT * FROM categories ORDER BY name"
    ).fetchall()
    db.close()
    return render_template("products/form.html", product=product, categories=categories)


@products_bp.route("/<int:id>/adjust-stock", methods=["POST"])
@login_required
def adjust_stock(id):
    db = get_db()
    product = db.execute("SELECT * FROM products WHERE id = ?", (id,)).fetchone()
    if not product:
        db.close()
        flash("Product not found.", "error")
        return redirect(url_for("products.index"))

    movement_type = request.form["movement_type"]
    quantity = float(request.form["quantity"])
    reference = request.form.get("reference", "").strip()
    notes = request.form.get("notes", "").strip()

    if quantity <= 0:
        flash("Quantity must be greater than zero.", "error")
        db.close()
        return redirect(url_for("products.detail", id=id))

    # Calculate new stock level
    if movement_type == "in":
        new_qty = product["stock_qty"] + quantity
    elif movement_type == "out":
        new_qty = product["stock_qty"] - quantity
    elif movement_type == "adjustment":
        # Adjustment sets stock to the given quantity
        new_qty = quantity
        quantity = quantity - product["stock_qty"]
    else:
        flash("Invalid movement type.", "error")
        db.close()
        return redirect(url_for("products.detail", id=id))

    db.execute(
        """INSERT INTO stock_movements
           (product_id, movement_type, quantity, reference, notes)
           VALUES (?, ?, ?, ?, ?)""",
        (id, movement_type, quantity, reference or None, notes or None),
    )
    db.execute(
        "UPDATE products SET stock_qty = ? WHERE id = ?",
        (new_qty, id),
    )
    db.commit()
    db.close()

    flash(f"Stock adjusted. New quantity: {new_qty}", "success")
    return redirect(url_for("products.detail", id=id))


@products_bp.route("/categories", methods=["GET", "POST"])
@login_required
def categories():
    db = get_db()
    if request.method == "POST":
        name = request.form["name"].strip()
        description = request.form.get("description", "").strip()
        if not name:
            flash("Category name is required.", "error")
        else:
            try:
                db.execute(
                    "INSERT INTO categories (name, description) VALUES (?, ?)",
                    (name, description or None),
                )
                db.commit()
                flash("Category added.", "success")
            except sqlite3.IntegrityError:
                flash("A category with that name already exists.", "error")

    cats = db.execute("SELECT * FROM categories ORDER BY name").fetchall()
    db.close()
    return render_template("products/categories.html", categories=cats)
