import os
import secrets
from flask import Flask
from flask_login import LoginManager
from erp.db import get_db, init_db, DB_PATH
from erp.auth import auth_bp, User
from erp.modules.dashboard import dashboard_bp
from erp.modules.contacts import contacts_bp
from erp.modules.products import products_bp
from erp.modules.sales import sales_bp
from erp.modules.purchasing import purchasing_bp
from erp.modules.accounting import accounting_bp
from erp.modules.hr import hr_bp


def create_app():
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", secrets.token_hex(32))

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    @login_manager.user_loader
    def load_user(user_id):
        db = get_db()
        row = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        db.close()
        if row:
            return User(row)
        return None

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(contacts_bp, url_prefix="/contacts")
    app.register_blueprint(products_bp, url_prefix="/products")
    app.register_blueprint(sales_bp, url_prefix="/sales")
    app.register_blueprint(purchasing_bp, url_prefix="/purchasing")
    app.register_blueprint(accounting_bp, url_prefix="/accounting")
    app.register_blueprint(hr_bp, url_prefix="/hr")

    init_db()
    _ensure_admin()

    # On Vercel, /tmp is ephemeral — auto-seed demo data on cold starts
    if os.environ.get("VERCEL") and not os.path.exists(DB_PATH + ".seeded"):
        _seed_demo_data()
        open(DB_PATH + ".seeded", "w").close()

    return app


def _seed_demo_data():
    """Seed sample data on Vercel cold starts."""
    import importlib.util
    import sys
    spec = importlib.util.spec_from_file_location(
        "seed_data",
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "seed_data.py"),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.seed()


def _ensure_admin():
    from werkzeug.security import generate_password_hash

    db = get_db()
    existing = db.execute(
        "SELECT id FROM users WHERE username = 'admin'"
    ).fetchone()
    if not existing:
        db.execute(
            "INSERT INTO users (username, password_hash, full_name, email, role) VALUES (?, ?, ?, ?, ?)",
            ("admin", generate_password_hash("admin", method="pbkdf2:sha256"), "Administrator", "admin@erp.local", "admin"),
        )
        db.commit()
    db.close()
