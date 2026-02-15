from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from erp.db import get_db

hr_bp = Blueprint("hr", __name__, template_folder="../templates")


def _generate_employee_number(db):
    """Auto-generate the next employee number like EMP-0001."""
    row = db.execute(
        "SELECT employee_number FROM employees ORDER BY id DESC LIMIT 1"
    ).fetchone()
    if row:
        last_num = int(row["employee_number"].split("-")[1])
        return f"EMP-{last_num + 1:04d}"
    return "EMP-0001"


@hr_bp.route("/")
@login_required
def index():
    db = get_db()
    employees = db.execute(
        """SELECT e.*, d.name AS department_name
           FROM employees e
           LEFT JOIN departments d ON e.department_id = d.id
           ORDER BY e.last_name, e.first_name"""
    ).fetchall()
    db.close()
    return render_template("hr/index.html", employees=employees)


@hr_bp.route("/new", methods=["GET", "POST"])
@login_required
def new():
    db = get_db()

    if request.method == "POST":
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()

        if not first_name or not last_name:
            flash("First name and last name are required.", "error")
            departments = db.execute(
                "SELECT * FROM departments ORDER BY name"
            ).fetchall()
            db.close()
            return render_template(
                "hr/form.html",
                employee=request.form,
                departments=departments,
                editing=False,
            )

        employee_number = _generate_employee_number(db)

        db.execute(
            """INSERT INTO employees
               (employee_number, first_name, last_name, email, phone,
                department_id, job_title, hire_date, salary)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                employee_number,
                first_name,
                last_name,
                request.form.get("email", "").strip(),
                request.form.get("phone", "").strip(),
                request.form.get("department_id") or None,
                request.form.get("job_title", "").strip(),
                request.form.get("hire_date", "").strip() or None,
                float(request.form.get("salary") or 0),
            ),
        )
        db.commit()
        new_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        db.close()

        flash(f"Employee {employee_number} created successfully.", "success")
        return redirect(url_for("hr.detail", id=new_id))

    departments = db.execute(
        "SELECT * FROM departments ORDER BY name"
    ).fetchall()
    db.close()
    return render_template(
        "hr/form.html", employee={}, departments=departments, editing=False
    )


@hr_bp.route("/<int:id>")
@login_required
def detail(id):
    db = get_db()
    employee = db.execute(
        """SELECT e.*, d.name AS department_name
           FROM employees e
           LEFT JOIN departments d ON e.department_id = d.id
           WHERE e.id = ?""",
        (id,),
    ).fetchone()

    if not employee:
        db.close()
        flash("Employee not found.", "error")
        return redirect(url_for("hr.index"))

    leave_requests = db.execute(
        """SELECT * FROM leave_requests
           WHERE employee_id = ?
           ORDER BY created_at DESC""",
        (id,),
    ).fetchall()
    db.close()

    return render_template(
        "hr/detail.html", employee=employee, leave_requests=leave_requests
    )


@hr_bp.route("/<int:id>/edit", methods=["GET", "POST"])
@login_required
def edit(id):
    db = get_db()
    employee = db.execute(
        "SELECT * FROM employees WHERE id = ?", (id,)
    ).fetchone()

    if not employee:
        db.close()
        flash("Employee not found.", "error")
        return redirect(url_for("hr.index"))

    if request.method == "POST":
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()

        if not first_name or not last_name:
            flash("First name and last name are required.", "error")
            departments = db.execute(
                "SELECT * FROM departments ORDER BY name"
            ).fetchall()
            db.close()
            return render_template(
                "hr/form.html",
                employee=request.form,
                departments=departments,
                editing=True,
                id=id,
            )

        db.execute(
            """UPDATE employees
               SET first_name = ?, last_name = ?, email = ?, phone = ?,
                   department_id = ?, job_title = ?, hire_date = ?, salary = ?
               WHERE id = ?""",
            (
                first_name,
                last_name,
                request.form.get("email", "").strip(),
                request.form.get("phone", "").strip(),
                request.form.get("department_id") or None,
                request.form.get("job_title", "").strip(),
                request.form.get("hire_date", "").strip() or None,
                float(request.form.get("salary") or 0),
                id,
            ),
        )
        db.commit()
        db.close()

        flash("Employee updated successfully.", "success")
        return redirect(url_for("hr.detail", id=id))

    departments = db.execute(
        "SELECT * FROM departments ORDER BY name"
    ).fetchall()
    db.close()
    return render_template(
        "hr/form.html",
        employee=employee,
        departments=departments,
        editing=True,
        id=id,
    )


@hr_bp.route("/<int:id>/deactivate", methods=["POST"])
@login_required
def deactivate(id):
    db = get_db()
    db.execute("UPDATE employees SET active = 0 WHERE id = ?", (id,))
    db.commit()
    db.close()

    flash("Employee deactivated.", "success")
    return redirect(url_for("hr.index"))


@hr_bp.route("/departments", methods=["GET", "POST"])
@login_required
def departments():
    db = get_db()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("Department name is required.", "error")
        else:
            try:
                db.execute(
                    "INSERT INTO departments (name) VALUES (?)", (name,)
                )
                db.commit()
                flash("Department added.", "success")
            except db.IntegrityError:
                flash("A department with that name already exists.", "error")

    depts = db.execute(
        """SELECT d.*, COUNT(e.id) AS employee_count
           FROM departments d
           LEFT JOIN employees e ON e.department_id = d.id AND e.active = 1
           GROUP BY d.id
           ORDER BY d.name"""
    ).fetchall()
    db.close()
    return render_template("hr/departments.html", departments=depts)


@hr_bp.route("/leaves")
@login_required
def leaves():
    db = get_db()
    leave_requests = db.execute(
        """SELECT lr.*, e.first_name, e.last_name, e.employee_number
           FROM leave_requests lr
           JOIN employees e ON lr.employee_id = e.id
           ORDER BY lr.created_at DESC"""
    ).fetchall()
    db.close()
    return render_template("hr/leaves.html", leave_requests=leave_requests)


@hr_bp.route("/<int:id>/leave/new", methods=["GET", "POST"])
@login_required
def leave_new(id):
    db = get_db()
    employee = db.execute(
        "SELECT * FROM employees WHERE id = ?", (id,)
    ).fetchone()

    if not employee:
        db.close()
        flash("Employee not found.", "error")
        return redirect(url_for("hr.index"))

    if request.method == "POST":
        leave_type = request.form.get("leave_type", "").strip()
        start_date = request.form.get("start_date", "").strip()
        end_date = request.form.get("end_date", "").strip()
        reason = request.form.get("reason", "").strip()

        if not leave_type or not start_date or not end_date:
            flash("Leave type, start date, and end date are required.", "error")
            db.close()
            return render_template(
                "hr/leave_form.html",
                employee=employee,
                leave=request.form,
            )

        if leave_type not in ("annual", "sick", "personal", "unpaid"):
            flash("Invalid leave type.", "error")
            db.close()
            return render_template(
                "hr/leave_form.html",
                employee=employee,
                leave=request.form,
            )

        db.execute(
            """INSERT INTO leave_requests
               (employee_id, leave_type, start_date, end_date, reason)
               VALUES (?, ?, ?, ?, ?)""",
            (id, leave_type, start_date, end_date, reason or None),
        )
        db.commit()
        db.close()

        flash("Leave request created.", "success")
        return redirect(url_for("hr.detail", id=id))

    db.close()
    return render_template(
        "hr/leave_form.html", employee=employee, leave={}
    )


@hr_bp.route("/leave/<int:id>/approve", methods=["POST"])
@login_required
def leave_approve(id):
    db = get_db()
    leave = db.execute(
        "SELECT * FROM leave_requests WHERE id = ?", (id,)
    ).fetchone()

    if not leave:
        db.close()
        flash("Leave request not found.", "error")
        return redirect(url_for("hr.leaves"))

    db.execute(
        "UPDATE leave_requests SET status = 'approved' WHERE id = ?", (id,)
    )
    db.commit()
    db.close()

    flash("Leave request approved.", "success")
    return redirect(url_for("hr.leaves"))


@hr_bp.route("/leave/<int:id>/reject", methods=["POST"])
@login_required
def leave_reject(id):
    db = get_db()
    leave = db.execute(
        "SELECT * FROM leave_requests WHERE id = ?", (id,)
    ).fetchone()

    if not leave:
        db.close()
        flash("Leave request not found.", "error")
        return redirect(url_for("hr.leaves"))

    db.execute(
        "UPDATE leave_requests SET status = 'rejected' WHERE id = ?", (id,)
    )
    db.commit()
    db.close()

    flash("Leave request rejected.", "success")
    return redirect(url_for("hr.leaves"))
