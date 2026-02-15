from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from erp.db import get_db

accounting_bp = Blueprint("accounting", __name__, template_folder="../templates")


@accounting_bp.route("/")
@login_required
def index():
    db = get_db()
    accounts = db.execute(
        "SELECT * FROM accounts WHERE active = 1 ORDER BY code"
    ).fetchall()
    db.close()

    grouped = {}
    for acct_type in ("asset", "liability", "equity", "revenue", "expense"):
        grouped[acct_type] = [a for a in accounts if a["account_type"] == acct_type]

    return render_template("accounting/index.html", grouped=grouped)


@accounting_bp.route("/accounts/new", methods=["GET", "POST"])
@login_required
def account_new():
    if request.method == "POST":
        code = request.form.get("code", "").strip()
        name = request.form.get("name", "").strip()
        account_type = request.form.get("account_type", "").strip()

        if not code or not name:
            flash("Account code and name are required.", "error")
            return render_template(
                "accounting/account_form.html", account=request.form
            )

        if account_type not in ("asset", "liability", "equity", "revenue", "expense"):
            flash("Invalid account type.", "error")
            return render_template(
                "accounting/account_form.html", account=request.form
            )

        db = get_db()
        existing = db.execute(
            "SELECT id FROM accounts WHERE code = ?", (code,)
        ).fetchone()
        if existing:
            db.close()
            flash("An account with that code already exists.", "error")
            return render_template(
                "accounting/account_form.html", account=request.form
            )

        db.execute(
            "INSERT INTO accounts (code, name, account_type) VALUES (?, ?, ?)",
            (code, name, account_type),
        )
        db.commit()
        db.close()

        flash("Account created successfully.", "success")
        return redirect(url_for("accounting.index"))

    return render_template("accounting/account_form.html", account={})


@accounting_bp.route("/journal")
@login_required
def journal():
    db = get_db()
    entries = db.execute(
        """SELECT je.*,
                  COALESCE(SUM(jl.debit), 0) AS total_debit,
                  COALESCE(SUM(jl.credit), 0) AS total_credit
           FROM journal_entries je
           LEFT JOIN journal_lines jl ON jl.entry_id = je.id
           GROUP BY je.id
           ORDER BY je.entry_date DESC, je.id DESC"""
    ).fetchall()
    db.close()

    return render_template("accounting/journal.html", entries=entries)


@accounting_bp.route("/journal/new", methods=["GET", "POST"])
@login_required
def journal_new():
    db = get_db()

    if request.method == "POST":
        entry_date = request.form.get("entry_date", "").strip()
        reference = request.form.get("reference", "").strip()
        description = request.form.get("description", "").strip()

        if not entry_date:
            flash("Entry date is required.", "error")
            accounts = db.execute(
                "SELECT * FROM accounts WHERE active = 1 ORDER BY code"
            ).fetchall()
            db.close()
            return render_template(
                "accounting/journal_form.html",
                accounts=accounts,
                form=request.form,
            )

        account_ids = request.form.getlist("account_id[]")
        debits = request.form.getlist("debit[]")
        credits = request.form.getlist("credit[]")

        lines = []
        total_debit = 0.0
        total_credit = 0.0

        for i in range(len(account_ids)):
            acct_id = account_ids[i].strip()
            debit_val = debits[i].strip() if i < len(debits) else ""
            credit_val = credits[i].strip() if i < len(credits) else ""

            if not acct_id:
                continue

            d = float(debit_val) if debit_val else 0.0
            c = float(credit_val) if credit_val else 0.0

            if d == 0.0 and c == 0.0:
                continue

            lines.append((int(acct_id), d, c))
            total_debit += d
            total_credit += c

        if not lines:
            flash("At least one journal line is required.", "error")
            accounts = db.execute(
                "SELECT * FROM accounts WHERE active = 1 ORDER BY code"
            ).fetchall()
            db.close()
            return render_template(
                "accounting/journal_form.html",
                accounts=accounts,
                form=request.form,
            )

        if round(total_debit, 2) != round(total_credit, 2):
            flash(
                f"Total debits ({total_debit:.2f}) must equal total credits ({total_credit:.2f}).",
                "error",
            )
            accounts = db.execute(
                "SELECT * FROM accounts WHERE active = 1 ORDER BY code"
            ).fetchall()
            db.close()
            return render_template(
                "accounting/journal_form.html",
                accounts=accounts,
                form=request.form,
            )

        db.execute(
            "INSERT INTO journal_entries (entry_date, reference, description) VALUES (?, ?, ?)",
            (entry_date, reference, description),
        )
        entry_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]

        for acct_id, d, c in lines:
            db.execute(
                "INSERT INTO journal_lines (entry_id, account_id, debit, credit) VALUES (?, ?, ?, ?)",
                (entry_id, acct_id, d, c),
            )

        db.commit()
        db.close()

        flash("Journal entry created successfully.", "success")
        return redirect(url_for("accounting.journal_detail", id=entry_id))

    accounts = db.execute(
        "SELECT * FROM accounts WHERE active = 1 ORDER BY code"
    ).fetchall()
    db.close()
    return render_template(
        "accounting/journal_form.html", accounts=accounts, form={}
    )


@accounting_bp.route("/journal/<int:id>")
@login_required
def journal_detail(id):
    db = get_db()
    entry = db.execute(
        "SELECT * FROM journal_entries WHERE id = ?", (id,)
    ).fetchone()

    if not entry:
        db.close()
        flash("Journal entry not found.", "error")
        return redirect(url_for("accounting.journal"))

    lines = db.execute(
        """SELECT jl.*, a.code AS account_code, a.name AS account_name
           FROM journal_lines jl
           JOIN accounts a ON a.id = jl.account_id
           WHERE jl.entry_id = ?
           ORDER BY jl.id""",
        (id,),
    ).fetchall()
    db.close()

    return render_template(
        "accounting/journal_detail.html", entry=entry, lines=lines
    )


@accounting_bp.route("/journal/<int:id>/post", methods=["POST"])
@login_required
def journal_post(id):
    db = get_db()
    entry = db.execute(
        "SELECT * FROM journal_entries WHERE id = ?", (id,)
    ).fetchone()

    if not entry:
        db.close()
        flash("Journal entry not found.", "error")
        return redirect(url_for("accounting.journal"))

    if entry["posted"]:
        db.close()
        flash("Journal entry is already posted.", "error")
        return redirect(url_for("accounting.journal_detail", id=id))

    lines = db.execute(
        """SELECT jl.*, a.account_type
           FROM journal_lines jl
           JOIN accounts a ON a.id = jl.account_id
           WHERE jl.entry_id = ?""",
        (id,),
    ).fetchall()

    for line in lines:
        acct_type = line["account_type"]
        debit = line["debit"]
        credit = line["credit"]

        # Assets and expenses increase with debits, decrease with credits
        # Liabilities, equity, and revenue increase with credits, decrease with debits
        if acct_type in ("asset", "expense"):
            change = debit - credit
        else:
            change = credit - debit

        db.execute(
            "UPDATE accounts SET balance = balance + ? WHERE id = ?",
            (change, line["account_id"]),
        )

    db.execute(
        "UPDATE journal_entries SET posted = 1 WHERE id = ?", (id,)
    )
    db.commit()
    db.close()

    flash("Journal entry posted successfully.", "success")
    return redirect(url_for("accounting.journal_detail", id=id))


@accounting_bp.route("/trial-balance")
@login_required
def trial_balance():
    db = get_db()
    accounts = db.execute(
        "SELECT * FROM accounts WHERE active = 1 ORDER BY code"
    ).fetchall()
    db.close()

    rows = []
    total_debit = 0.0
    total_credit = 0.0

    for acct in accounts:
        balance = acct["balance"]
        acct_type = acct["account_type"]

        # Assets and expenses: positive balance is a debit balance
        # Liabilities, equity, revenue: positive balance is a credit balance
        if acct_type in ("asset", "expense"):
            if balance >= 0:
                debit_bal = balance
                credit_bal = 0.0
            else:
                debit_bal = 0.0
                credit_bal = abs(balance)
        else:
            if balance >= 0:
                debit_bal = 0.0
                credit_bal = balance
            else:
                debit_bal = abs(balance)
                credit_bal = 0.0

        if debit_bal == 0.0 and credit_bal == 0.0:
            continue

        rows.append({
            "code": acct["code"],
            "name": acct["name"],
            "debit": debit_bal,
            "credit": credit_bal,
        })
        total_debit += debit_bal
        total_credit += credit_bal

    return render_template(
        "accounting/trial_balance.html",
        rows=rows,
        total_debit=total_debit,
        total_credit=total_credit,
    )


@accounting_bp.route("/profit-loss")
@login_required
def profit_loss():
    date_from = request.args.get("date_from", "")
    date_to = request.args.get("date_to", "")

    db = get_db()

    # Build a query that sums posted journal line amounts per account
    # filtered by date range if provided
    query = """
        SELECT a.id, a.code, a.name, a.account_type,
               COALESCE(SUM(jl.debit), 0) AS total_debit,
               COALESCE(SUM(jl.credit), 0) AS total_credit
        FROM accounts a
        LEFT JOIN journal_lines jl ON jl.account_id = a.id
        LEFT JOIN journal_entries je ON je.id = jl.entry_id AND je.posted = 1
    """
    conditions = ["a.account_type IN ('revenue', 'expense')", "a.active = 1"]
    params = []

    if date_from:
        conditions.append("(je.entry_date >= ? OR je.entry_date IS NULL)")
        params.append(date_from)
    if date_to:
        conditions.append("(je.entry_date <= ? OR je.entry_date IS NULL)")
        params.append(date_to)

    query += " WHERE " + " AND ".join(conditions)
    query += " GROUP BY a.id ORDER BY a.code"

    accounts = db.execute(query, params).fetchall()
    db.close()

    revenue_accounts = []
    expense_accounts = []
    total_revenue = 0.0
    total_expense = 0.0

    for acct in accounts:
        # Revenue: credits - debits
        # Expense: debits - credits
        if acct["account_type"] == "revenue":
            amount = acct["total_credit"] - acct["total_debit"]
            if amount != 0:
                revenue_accounts.append({
                    "code": acct["code"],
                    "name": acct["name"],
                    "amount": amount,
                })
                total_revenue += amount
        else:
            amount = acct["total_debit"] - acct["total_credit"]
            if amount != 0:
                expense_accounts.append({
                    "code": acct["code"],
                    "name": acct["name"],
                    "amount": amount,
                })
                total_expense += amount

    net_income = total_revenue - total_expense

    return render_template(
        "accounting/profit_loss.html",
        revenue_accounts=revenue_accounts,
        expense_accounts=expense_accounts,
        total_revenue=total_revenue,
        total_expense=total_expense,
        net_income=net_income,
        date_from=date_from,
        date_to=date_to,
    )


@accounting_bp.route("/balance-sheet")
@login_required
def balance_sheet():
    db = get_db()
    accounts = db.execute(
        """SELECT * FROM accounts
           WHERE active = 1 AND account_type IN ('asset', 'liability', 'equity')
           ORDER BY code"""
    ).fetchall()
    db.close()

    asset_accounts = []
    liability_accounts = []
    equity_accounts = []
    total_assets = 0.0
    total_liabilities = 0.0
    total_equity = 0.0

    for acct in accounts:
        balance = acct["balance"]
        if acct["account_type"] == "asset":
            asset_accounts.append({
                "code": acct["code"],
                "name": acct["name"],
                "balance": balance,
            })
            total_assets += balance
        elif acct["account_type"] == "liability":
            liability_accounts.append({
                "code": acct["code"],
                "name": acct["name"],
                "balance": balance,
            })
            total_liabilities += balance
        else:
            equity_accounts.append({
                "code": acct["code"],
                "name": acct["name"],
                "balance": balance,
            })
            total_equity += balance

    return render_template(
        "accounting/balance_sheet.html",
        asset_accounts=asset_accounts,
        liability_accounts=liability_accounts,
        equity_accounts=equity_accounts,
        total_assets=total_assets,
        total_liabilities=total_liabilities,
        total_equity=total_equity,
    )
