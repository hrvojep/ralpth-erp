from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from erp.db import get_db

contacts_bp = Blueprint("contacts", __name__, template_folder="../templates")


@contacts_bp.route("/")
@login_required
def index():
    search = request.args.get("search", "").strip()
    contact_type = request.args.get("type", "").strip()

    query = "SELECT * FROM contacts WHERE active = 1"
    params = []

    if search:
        query += " AND (name LIKE ? OR email LIKE ? OR phone LIKE ?)"
        like = f"%{search}%"
        params.extend([like, like, like])

    if contact_type in ("customer", "supplier", "both"):
        query += " AND contact_type = ?"
        params.append(contact_type)

    query += " ORDER BY name"

    db = get_db()
    contacts = db.execute(query, params).fetchall()
    db.close()

    return render_template(
        "contacts/index.html",
        contacts=contacts,
        search=search,
        contact_type=contact_type,
    )


@contacts_bp.route("/new", methods=["GET", "POST"])
@login_required
def new():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("Name is required.", "error")
            return render_template("contacts/form.html", contact=request.form, editing=False)

        contact_type = request.form.get("contact_type", "customer")
        if contact_type not in ("customer", "supplier", "both"):
            contact_type = "customer"

        db = get_db()
        db.execute(
            """INSERT INTO contacts (name, contact_type, email, phone, address, city, country, tax_id, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                name,
                contact_type,
                request.form.get("email", "").strip(),
                request.form.get("phone", "").strip(),
                request.form.get("address", "").strip(),
                request.form.get("city", "").strip(),
                request.form.get("country", "").strip(),
                request.form.get("tax_id", "").strip(),
                request.form.get("notes", "").strip(),
            ),
        )
        db.commit()
        new_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        db.close()

        flash("Contact created successfully.", "success")
        return redirect(url_for("contacts.detail", id=new_id))

    return render_template("contacts/form.html", contact={}, editing=False)


@contacts_bp.route("/<int:id>")
@login_required
def detail(id):
    db = get_db()
    contact = db.execute("SELECT * FROM contacts WHERE id = ? AND active = 1", (id,)).fetchone()
    db.close()

    if not contact:
        flash("Contact not found.", "error")
        return redirect(url_for("contacts.index"))

    return render_template("contacts/detail.html", contact=contact)


@contacts_bp.route("/<int:id>/edit", methods=["GET", "POST"])
@login_required
def edit(id):
    db = get_db()
    contact = db.execute("SELECT * FROM contacts WHERE id = ? AND active = 1", (id,)).fetchone()

    if not contact:
        db.close()
        flash("Contact not found.", "error")
        return redirect(url_for("contacts.index"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("Name is required.", "error")
            db.close()
            return render_template("contacts/form.html", contact=request.form, editing=True, id=id)

        contact_type = request.form.get("contact_type", "customer")
        if contact_type not in ("customer", "supplier", "both"):
            contact_type = "customer"

        db.execute(
            """UPDATE contacts
               SET name = ?, contact_type = ?, email = ?, phone = ?,
                   address = ?, city = ?, country = ?, tax_id = ?, notes = ?
               WHERE id = ?""",
            (
                name,
                contact_type,
                request.form.get("email", "").strip(),
                request.form.get("phone", "").strip(),
                request.form.get("address", "").strip(),
                request.form.get("city", "").strip(),
                request.form.get("country", "").strip(),
                request.form.get("tax_id", "").strip(),
                request.form.get("notes", "").strip(),
                id,
            ),
        )
        db.commit()
        db.close()

        flash("Contact updated successfully.", "success")
        return redirect(url_for("contacts.detail", id=id))

    db.close()
    return render_template("contacts/form.html", contact=contact, editing=True, id=id)


@contacts_bp.route("/<int:id>/delete", methods=["POST"])
@login_required
def delete(id):
    db = get_db()
    db.execute("UPDATE contacts SET active = 0 WHERE id = ?", (id,))
    db.commit()
    db.close()

    flash("Contact deleted.", "success")
    return redirect(url_for("contacts.index"))
