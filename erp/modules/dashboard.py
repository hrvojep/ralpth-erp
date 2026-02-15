from flask import Blueprint, render_template
from flask_login import login_required
from erp.db import get_db

dashboard_bp = Blueprint("dashboard", __name__, template_folder="../templates")


@dashboard_bp.route("/")
@login_required
def index():
    db = get_db()

    # Key stats
    total_contacts = db.execute("SELECT COUNT(*) FROM contacts").fetchone()[0]
    total_products = db.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    total_sales_orders = db.execute("SELECT COUNT(*) FROM sales_orders").fetchone()[0]
    total_purchase_orders = db.execute("SELECT COUNT(*) FROM purchase_orders").fetchone()[0]
    pending_invoices = db.execute(
        "SELECT COUNT(*) FROM invoices WHERE status IN ('draft', 'sent')"
    ).fetchone()[0]
    total_revenue = db.execute(
        "SELECT COALESCE(SUM(total), 0) FROM invoices WHERE status = 'paid'"
    ).fetchone()[0]

    # Recent sales orders (last 5)
    recent_sales = db.execute(
        "SELECT so.id, so.order_number, c.name AS customer_name, "
        "so.order_date, so.status, so.total "
        "FROM sales_orders so "
        "JOIN contacts c ON so.customer_id = c.id "
        "ORDER BY so.created_at DESC LIMIT 5"
    ).fetchall()

    # Recent purchase orders (last 5)
    recent_purchases = db.execute(
        "SELECT po.id, po.po_number, c.name AS supplier_name, "
        "po.order_date, po.status, po.total "
        "FROM purchase_orders po "
        "JOIN contacts c ON po.supplier_id = c.id "
        "ORDER BY po.created_at DESC LIMIT 5"
    ).fetchall()

    db.close()

    return render_template(
        "dashboard/index.html",
        total_contacts=total_contacts,
        total_products=total_products,
        total_sales_orders=total_sales_orders,
        total_purchase_orders=total_purchase_orders,
        pending_invoices=pending_invoices,
        total_revenue=total_revenue,
        recent_sales=recent_sales,
        recent_purchases=recent_purchases,
    )
