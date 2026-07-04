from database.db import get_connection
from datetime import datetime, timedelta
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    jsonify
)

import pandas as pd

students_bp = Blueprint("students", __name__)
@students_bp.route("/students")
def students():

    search = request.args.get("search", "")
    department = request.args.get("department", "")
    year = request.args.get("year", "")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT *
        FROM students
        WHERE status='Active'
    """

    params = []

    if search:
        query += """
        AND (
            roll_number LIKE %s
            OR student_name LIKE %s
        )
        """
        keyword = "%" + search + "%"
        params.extend([keyword, keyword])

    if department:
        query += " AND department=%s"
        params.append(department)

    if year:
        query += " AND year=%s"
        params.append(year)

    query += " ORDER BY student_name"

    cursor.execute(query, tuple(params))

    students = cursor.fetchall()

    conn.close()

    return render_template(
        "students.html",
        students=students,
        search=search,
        department=department,
        year=year
    )
@students_bp.route("/add_student", methods=["GET", "POST"])
def add_student():

    if request.method == "POST":

        roll_number = request.form["roll_number"]
        student_name = request.form["student_name"]
        department = request.form["department"]
        year = request.form["year"]

        conn = get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO students
                (roll_number, student_name, department, year)
                VALUES (%s, %s, %s, %s)
            """, (
                roll_number,
                student_name,
                department,
                year
            ))

            conn.commit()
            conn.close()

            return render_template("add_student.html", success=True)

        except Exception as e:
            conn.rollback()
            conn.close()
            return f"Error Adding Student: {e}"

    return render_template("add_student.html")
@students_bp.route("/edit_student/<roll_number>", methods=["GET", "POST"])
def edit_student(roll_number):

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM students WHERE roll_number=%s", (roll_number,))
    student = cursor.fetchone()

    if not student:
        conn.close()
        return "Student not found"

    if request.method == "POST":

        student_name = request.form["student_name"]
        department = request.form["department"]
        year = request.form["year"]

        try:
            cursor.execute("""
                UPDATE students
                SET student_name=%s,
                    department=%s,
                    year=%s
                WHERE roll_number=%s
            """, (student_name, department, year, roll_number))

            conn.commit()

            return "Student updated successfully"

        except Exception as e:
            conn.rollback()
            return f"Error: {str(e)}"

        finally:
            conn.close()

    conn.close()
    return render_template("edit_student.html", student=student)
@students_bp.route("/bulk_student_management")
def bulk_student_management():
    return render_template("bulk_student_management.html")

@students_bp.route("/bulk_import_students", methods=["POST"])
def bulk_import_students():

    if "excel_file" not in request.files:
        return "No file uploaded"

    file = request.files["excel_file"]

    if file.filename == "":
        return "Please select a file"

    df = pd.read_excel(file)

    # Convert column names to lowercase
    df.columns = df.columns.str.strip().str.lower()

    print("Columns:", df.columns.tolist())

    conn = get_connection()
    cursor = conn.cursor()

    updated_count = 0

    try:

        for _, row in df.iterrows():

            cursor.execute("""
                INSERT INTO students
                (roll_number, student_name, department, year, status)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                str(row["roll_number"]).strip(),
                str(row["student_name"]).strip(),
                str(row["department"]).strip(),
                int(row["year"]),
                "Active"
            ))

            updated_count += 1

        conn.commit()

        return f"Students Imported Successfully. Rows Imported = {updated_count}"

    except Exception as e:

        conn.rollback()
        return f"Error Importing Students: {e}"

    finally:

        conn.close()
@students_bp.route("/bulk_deactivate_students", methods=["POST"])
def bulk_deactivate_students():

    if "excel_file" not in request.files:
        return "No file uploaded"

    file = request.files["excel_file"]

    if file.filename == "":
        return "Please select a file"

    df = pd.read_excel(file)

    conn = get_connection()
    cursor = conn.cursor()

    updated_count = 0

    try:

        for _, row in df.iterrows():

            roll_number = str(row["roll_number"]).strip()

            cursor.execute("""
                UPDATE students
                SET status='Inactive'
                WHERE roll_number=%s
            """, (roll_number,))

            print("Roll Number:", roll_number)
            print("Rows Updated:", cursor.rowcount)

            updated_count += cursor.rowcount

        conn.commit()
        return f"Students Deactivated Successfully. Updated Rows = {updated_count}"

    except Exception as e:

        conn.rollback()
        return f"Error Deactivating Students: {e}"

    finally:

        conn.close()
@students_bp.route("/inactive_students")
def inactive_students():

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT *
        FROM students
        WHERE status='Inactive'
    """)

    students = cursor.fetchall()

    conn.close()

    return render_template(
        "inactive_students.html",
        students=students
    )
