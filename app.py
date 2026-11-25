import os
import sqlite3
from datetime import datetime
from flask import Flask, flash, redirect, render_template, request, url_for

app = Flask(__name__)
app.secret_key = "wpp-lab17-employee-secret-key"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "employees.db")


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                department TEXT NOT NULL,
                role TEXT NOT NULL,
                email TEXT NOT NULL,
                salary REAL NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


def parse_salary(raw_salary):
    try:
        val = float(raw_salary)
        if val < 0:
            return None
        return val
    except (ValueError, TypeError):
        return None


# VIEW + SEARCH (by Name or ID) + ADD EMPLOYEE
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        department = request.form.get("department", "").strip()
        role = request.form.get("role", "").strip()
        email = request.form.get("email", "").strip().lower()
        salary = parse_salary(request.form.get("salary", ""))

        if not name or not department or not role or not email or salary is None:
            flash("Please provide valid values for all employee fields (including a non-negative salary).", "error")
            return redirect(url_for("index"))

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

        try:
            with get_db_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO employees (name, department, role, email, salary, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (name, department, role, email, salary, timestamp),
                )
                conn.commit()
            flash(f"Added employee '{name}'.", "success")
        except sqlite3.Error as exc:
            flash(f"Database error while adding employee: {exc}", "error")

        return redirect(url_for("index"))

    search_query = request.args.get("q", "").strip()
    search_by = request.args.get("search_by", "all").strip().lower()

    with get_db_connection() as conn:
        if search_query:
            if search_by == "id":
                clean_id = search_query.lstrip("#")
                if clean_id.isdigit():
                    employees = conn.execute(
                        "SELECT * FROM employees WHERE id = ? ORDER BY id DESC",
                        (int(clean_id),),
                    ).fetchall()
                else:
                    employees = []
            elif search_by == "name":
                employees = conn.execute(
                    "SELECT * FROM employees WHERE LOWER(name) LIKE ? ORDER BY id DESC",
                    (f"%{search_query.lower()}%",),
                ).fetchall()
            else:
                clean_id = search_query.lstrip("#")
                if clean_id.isdigit():
                    employees = conn.execute(
                        """
                        SELECT * FROM employees
                        WHERE id = ? OR LOWER(name) LIKE ?
                        ORDER BY id DESC
                        """,
                        (int(clean_id), f"%{search_query.lower()}%"),
                    ).fetchall()
                else:
                    employees = conn.execute(
                        "SELECT * FROM employees WHERE LOWER(name) LIKE ? ORDER BY id DESC",
                        (f"%{search_query.lower()}%",),
                    ).fetchall()
        else:
            employees = conn.execute("SELECT * FROM employees ORDER BY id DESC").fetchall()

    return render_template(
        "index.html",
        employees=employees,
        search_query=search_query,
        search_by=search_by,
    )


# UPDATE EMPLOYEE
@app.route("/edit/<int:emp_id>", methods=["GET", "POST"])
def edit_employee(emp_id):
    with get_db_connection() as conn:
        employee = conn.execute("SELECT * FROM employees WHERE id = ?", (emp_id,)).fetchone()

        if not employee:
            flash("Employee record not found.", "error")
            return redirect(url_for("index"))

        if request.method == "POST":
            name = request.form.get("name", "").strip()
            department = request.form.get("department", "").strip()
            role = request.form.get("role", "").strip()
            email = request.form.get("email", "").strip().lower()
            salary = parse_salary(request.form.get("salary", ""))

            if not name or not department or not role or not email or salary is None:
                flash("Please fill in all fields with a valid non-negative salary.", "error")
                return render_template("edit.html", employee=employee)

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            conn.execute(
                """
                UPDATE employees
                SET name = ?, department = ?, role = ?, email = ?, salary = ?, updated_at = ?
                WHERE id = ?
                """,
                (name, department, role, email, salary, timestamp, emp_id),
            )
            conn.commit()
            flash(f"Updated details for '{name}'.", "success")
            return redirect(url_for("index"))

    return render_template("edit.html", employee=employee)


# DELETE EMPLOYEE
@app.route("/delete/<int:emp_id>", methods=["POST"])
def delete_employee(emp_id):
    try:
        with get_db_connection() as conn:
            cursor = conn.execute("DELETE FROM employees WHERE id = ?", (emp_id,))
            conn.commit()

        if cursor.rowcount > 0:
            flash("Employee record deleted.", "success")
        else:
            flash("Employee record was already deleted.", "error")
    except sqlite3.Error as exc:
        flash(f"Error deleting employee: {exc}", "error")

    return redirect(url_for("index"))


if __name__ == "__main__":
    init_db()
    app.run(debug=True)