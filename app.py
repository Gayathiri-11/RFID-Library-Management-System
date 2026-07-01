from flask import Flask, render_template, request, redirect, flash, jsonify, url_for, session, send_file
import mysql.connector
from datetime import datetime, timedelta
import serial
import os
import time
import pandas as pd
from database.db import get_connection
from flask import url_for

app = Flask(__name__)
app.secret_key = "library_rfid_secret_key"

if os.environ.get("RENDER"):
    arduino = None
else:
    try:
        arduino = serial.Serial("COM5", 9600, timeout=1)
        time.sleep(2)
        print("Arduino Connected")
    except Exception as e:
        print(e)
        arduino = None

@app.route("/")
def home():
    return render_template("dashboard.html")
@app.route("/scan_uid")
def scan_uid():

    if arduino is None:
        return {"uid": "RFID_NOT_CONNECTED"}

    uid = arduino.readline().decode().strip()

    return {"uid": uid}

def get_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="Nanmai@2006",
        database="RFID_LIBRARY"
    )
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        try:
            conn = get_connection()
            cursor = conn.cursor(dictionary=True)

            cursor.execute(
                "SELECT * FROM users WHERE username=%s",
                (username,)
            )

            user = cursor.fetchone()
            conn.close()

            if user and user["password"] == password:
                return redirect("/dashboard")

            return "Invalid username or password"

        except Exception as e:
            return f"Database Error: {e}"

    return render_template("login.html")

@app.route("/logout")
def logout():
    return redirect("/login")
@app.route("/dashboard")
def dashboard():

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # Total Books
    cursor.execute("SELECT COUNT(*) AS total FROM books")
    total_books = cursor.fetchone()["total"]

    # Available Books
    cursor.execute("SELECT COUNT(*) AS total FROM books WHERE status='Available'")
    available_books = cursor.fetchone()["total"]

    # Issued Books
    cursor.execute("SELECT COUNT(*) AS total FROM books WHERE status='Issued'")
    issued_books = cursor.fetchone()["total"]

    # Students
    cursor.execute("SELECT COUNT(*) AS total FROM students")
    total_students = cursor.fetchone()["total"]

    # Overdue Books
    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM transactions
        WHERE status='Issued'
        AND due_date < CURDATE()
    """)
    overdue_books = cursor.fetchone()["total"]

    # Total Fine (₹5 per overdue day)
    cursor.execute("""
        SELECT
        IFNULL(SUM(GREATEST(DATEDIFF(CURDATE(), due_date),0)*5),0) AS total_fine
        FROM transactions
        WHERE status='Issued'
        AND due_date < CURDATE()
    """)
    total_fine = cursor.fetchone()["total_fine"]

    # Recent Transactions
    cursor.execute("""
        SELECT

            b.book_name,

            s.student_name,

            t.status,

            t.issue_date,

            t.due_date

        FROM transactions t

        JOIN books b
        ON t.uid=b.uid

        JOIN students s
        ON t.roll_number=s.roll_number

        ORDER BY t.issue_date DESC

        LIMIT 10
    """)

    recent_transactions = cursor.fetchall()

    conn.close()

    return render_template(
        "dashboard.html",
        total_books=total_books,
        available_books=available_books,
        issued_books=issued_books,
        total_students=total_students,
        overdue_books=overdue_books,
        total_fine=total_fine,
        recent_transactions=recent_transactions
    )
@app.route("/export_transactions")
def export_transactions():

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT *
        FROM transactions
        ORDER BY issue_date DESC
    """)

    data = cursor.fetchall()

    df = pd.DataFrame(data)

    file_name = "transactions.xlsx"

    df.to_excel(file_name, index=False)

    conn.close()

    return send_file(
        file_name,
        as_attachment=True
    )
@app.route("/books")
def books():

    search = request.args.get("search", "")
    category = request.args.get("category", "")
    status = request.args.get("status", "")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT *
        FROM books
        WHERE 1=1
    """

    params = []

    if search:
        query += """
        AND (
            uid LIKE %s
            OR book_number LIKE %s
            OR book_name LIKE %s
            OR author LIKE %s
        )
        """
        keyword = "%" + search + "%"
        params.extend([keyword, keyword, keyword, keyword])

    if category:
        query += " AND category=%s"
        params.append(category)

    if status:
        query += " AND status=%s"
        params.append(status)

    query += " ORDER BY book_name"

    cursor.execute(query, tuple(params))

    books = cursor.fetchall()

    conn.close()

    return render_template(
        "books.html",
        books=books,
        search=search,
        category=category,
        status=status
    )
@app.route("/edit_book/<uid>", methods=["GET", "POST"])
def edit_book(uid):

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM books WHERE uid=%s",
        (uid,)
    )

    book = cursor.fetchone()

    if not book:
        conn.close()
        return "Book not found"

    if book["status"] == "Issued":
        conn.close()
        return "Issued books cannot be edited"

    if request.method == "POST":

        book_number = request.form["book_number"]
        book_name = request.form["book_name"]
        author = request.form["author"]

        try:
            cursor.execute("""
                UPDATE books
                SET book_number=%s,
                    book_name=%s,
                    author=%s
                WHERE uid=%s
            """, (
                book_number,
                book_name,
                author,
                uid
            ))

            conn.commit()

        except Exception as e:

            conn.rollback()
            return f"Error Updating Book: {e}"

        finally:

            conn.close()

        return redirect("/books")

    conn.close()

    return render_template(
        "edit_book.html",
        book=book
    )
@app.route("/replace_uid/<old_uid>", methods=["GET", "POST"])
def replace_uid(old_uid):

    if request.method == "POST":

        new_uid = request.form["new_uid"]

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "UPDATE books SET uid=%s WHERE uid=%s",
            (new_uid, old_uid)
        )

        conn.commit()
        conn.close()

        return redirect(url_for("books"))
    return render_template(
        "replace_uid.html",
        old_uid=old_uid
    )
@app.route("/deactivate_book/<uid>")
def deactivate_book(uid):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT status FROM books WHERE uid=%s",
        (uid,)
    )

    book = cursor.fetchone()

    if book and book[0] == "Issued":
        conn.close()
        return "Issued books cannot be deactivated"

    cursor.execute(
        "UPDATE books SET status='Inactive' WHERE uid=%s",
        (uid,)
    )

    conn.commit()
    conn.close()
    return redirect(url_for("books"))
@app.route("/edit_student/<roll_number>", methods=["GET", "POST"])
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
@app.route("/add_book", methods=["GET", "POST"])
def add_book():

    if request.method == "POST":

        uid = request.form["uid"]
        book_number = request.form["book_number"]
        book_name = request.form["book_name"]
        author = request.form["author"]

        conn = get_connection()
        cursor = conn.cursor()

        try:
            # CHECK DUPLICATE
            cursor.execute("SELECT * FROM books WHERE uid=%s", (uid,))
            existing = cursor.fetchone()

            if existing:
                conn.close()
                return "❌ Book already exists with this UID"

            # INSERT BOOK
            cursor.execute("""
                INSERT INTO books
                (uid, book_number, book_name, author, status)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                uid,
                book_number,
                book_name,
                author,
                "Available"
            ))

            conn.commit()
            conn.close()

            return render_template("add_book.html", success=True)

        except Exception as e:
            conn.rollback()
            conn.close()
            return f"Error Adding Book: {e}"

    return render_template("add_book.html")
@app.route("/add_student", methods=["GET", "POST"])
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
@app.route("/students")
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
@app.route("/issue_book", methods=["GET", "POST"])
def issue_book():

    if request.method == "POST":

        uid = request.form.get("uid")
        roll_number = request.form.get("roll_number")

        if not uid:
            return "UID Required"

        conn = get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO transactions
                (uid, roll_number, issue_date, due_date, status)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                uid,
                roll_number,
                datetime.now(),
                datetime.now() + timedelta(days=15),
                "Issued"
            ))

            cursor.execute("""
                UPDATE books
                SET status='Issued'
                WHERE uid=%s
            """, (uid,))

            conn.commit()
            conn.close()

            return render_template(
                "issue_book.html",
                message="Book issued successfully",
                redirect="/dashboard"
            )

        except Exception as e:
            conn.rollback()
            conn.close()
            return f"Error Issuing Book: {e}"

    return render_template("issue_book.html")
@app.route("/return_book", methods=["GET", "POST"])
def return_book():

    if request.method == "POST":

        uid = request.form["uid"]

        conn = get_connection()
        cursor = conn.cursor(dictionary=True, buffered=True)

        try:
            # Find latest issued transaction
            cursor.execute("""
                SELECT *
                FROM transactions
                WHERE uid=%s AND status='Issued'
                ORDER BY issue_date DESC
                LIMIT 1
            """, (uid,))

            transaction = cursor.fetchone()

            if not transaction:
                conn.close()
                return render_template(
                    "return_book.html",
                    message="Book not found or already returned",
                    redirect="/return_book"
                )

            due_date = transaction["due_date"]
            today = datetime.now().date()

            fine = 0

            if due_date and today > due_date:
                fine = (today - due_date).days * 2

            # Update transaction
            cursor.execute("""
                UPDATE transactions
                SET status='Returned',
                    return_date=%s,
                    fine=%s
                WHERE id=%s
            """, (
                datetime.now(),
                fine,
                transaction["id"]
            ))

            # Update book status
            cursor.execute("""
                UPDATE books
                SET status='Available'
                WHERE uid=%s
            """, (uid,))

            conn.commit()
            conn.close()

            return render_template(
                "return_book.html",
                message=f"Book Returned Successfully. Fine = ₹{fine}",
                redirect="/dashboard"
            )

        except Exception as e:
            conn.rollback()
            conn.close()

            import traceback
            print(traceback.format_exc())

            return f"Error Returning Book: {e}"

    return render_template("return_book.html")
@app.route("/check_book/<uid>")
def check_book_status(uid):

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT status FROM books WHERE uid=%s", (uid,))
    book = cursor.fetchone()

    conn.close()

    if not book:
        return {"status": "NOT_FOUND"}

    return {"status": book["status"]}
@app.route("/check_book", methods=["GET","POST"])
def check_book():

    conn=get_connection()
    cursor=conn.cursor(dictionary=True)

    book=None

    if request.method=="POST":

        keyword=request.form["keyword"]

        cursor.execute("""
        SELECT *
        FROM books
        WHERE uid=%s
        OR book_number=%s
        OR book_name=%s
        """,(keyword,keyword,keyword))

        book=cursor.fetchone()
    cursor.execute("""
        SELECT
        book_name,
        author,
        category,
        COUNT(*) AS total_books,
        SUM(CASE WHEN status='Available' THEN 1 ELSE 0 END) AS available_books
        FROM books
        GROUP BY book_name, author, category
        ORDER BY book_name
        """)

    book_summary = cursor.fetchall()

    conn.close()

    return render_template(
        "check_book.html",
        book=book,
        book_summary=book_summary
    )
@app.route("/get_book/<uid>")
def get_book(uid):

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM books WHERE uid=%s",
        (uid,)
    )

    book = cursor.fetchone()

    conn.close()

    return jsonify(book)
@app.route("/transactions")
def transactions():

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            t.*,
            b.book_name,
            s.student_name,
            s.department
        FROM transactions t
        JOIN books b
            ON t.uid = b.uid
        JOIN students s
            ON t.roll_number = s.roll_number
        ORDER BY t.issue_date DESC
    """)

    transactions = cursor.fetchall()

    today = datetime.now().date()

    for t in transactions:

        t["is_overdue"] = False

        if (
            t["status"] == "Issued"
            and t["due_date"]
            and today > t["due_date"]
        ):
            t["is_overdue"] = True

    conn.close()

    return render_template(
        "transactions.html",
        transactions=transactions
    )
@app.route("/bulk_student_management")
def bulk_student_management():
    return render_template("bulk_student_management.html")

@app.route("/bulk_import_students", methods=["POST"])
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
                (roll_number, student_name, category, year, status)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                str(row["roll_number"]).strip(),
                str(row["student_name"]).strip(),
                str(row["category"]).strip(),
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
@app.route("/bulk_deactivate_students", methods=["POST"])
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
@app.route("/inactive_students")
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
@app.route("/overdue_report")
def overdue_report():

    department = request.args.get("department", "")
    from_date = request.args.get("from_date", "")
    to_date = request.args.get("to_date", "")
    min_fine = request.args.get("min_fine", "")
    max_fine = request.args.get("max_fine", "")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT
            t.uid,
            t.roll_number,
            s.student_name,
            s.department,
            t.issue_date,
            t.due_date,
            t.status,

            GREATEST(DATEDIFF(CURDATE(), t.due_date),0) AS overdue_days,

            GREATEST(DATEDIFF(CURDATE(), t.due_date),0) * 5 AS fine

        FROM transactions t

        JOIN students s
        ON t.roll_number = s.roll_number

        WHERE t.status='Issued'
        AND t.due_date < CURDATE()
    """

    params = []

    if department:
        query += " AND s.department=%s"
        params.append(department)

    if from_date:
        query += " AND t.due_date >= %s"
        params.append(from_date)

    if to_date:
        query += " AND t.due_date <= %s"
        params.append(to_date)

    if min_fine:
        query += " AND (GREATEST(DATEDIFF(CURDATE(), t.due_date),0)*5) >= %s"
        params.append(min_fine)

    if max_fine:
        query += " AND (GREATEST(DATEDIFF(CURDATE(), t.due_date),0)*5) <= %s"
        params.append(max_fine)

    query += " ORDER BY t.due_date ASC"

    cursor.execute(query, tuple(params))

    books = cursor.fetchall()

    conn.close()

    return render_template(
        "overdue_report.html",
        books=books
    )
@app.route("/export_overdue_report")
def export_overdue_report():

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT

            t.uid,
            t.roll_number,
            s.student_name,
            s.department,
            t.issue_date,
            t.due_date,

            GREATEST(DATEDIFF(CURDATE(), t.due_date),0) AS overdue_days,

            GREATEST(DATEDIFF(CURDATE(), t.due_date),0) * 5 AS fine,

            t.status

        FROM transactions t

        JOIN students s
        ON t.roll_number=s.roll_number

        WHERE t.status='Issued'
        AND t.due_date<CURDATE()

        ORDER BY t.due_date
    """)

    books = cursor.fetchall()

    conn.close()

    df = pd.DataFrame(books)

    filename = "Overdue_Report.xlsx"

    df.to_excel(filename,index=False)

    return send_file(filename,as_attachment=True)
@app.route("/bulk_book_management")
def bulk_book_management():
    return render_template("bulk_book_management.html")
@app.route("/bulk_import_books", methods=["POST"])
def bulk_import_books():

    if "excel_file" not in request.files:
        flash("No file selected", "error")
        return redirect("/bulk_book_management")

    file = request.files["excel_file"]

    conn = get_connection()
    cursor = conn.cursor()

    try:

        df = pd.read_excel(file)
        df.columns = df.columns.str.strip().str.lower()

        required = [
            "book_number",
            "book_name",
            "author",
            "category"
        ]

        for col in required:
            if col not in df.columns:
                flash(f"Missing column : {col}", "error")
                return redirect("/bulk_book_management")

        count = 0

        for _, row in df.iterrows():

            cursor.execute(
                "SELECT * FROM books WHERE book_number=%s",
                (str(row["book_number"]).strip(),)
            )

            if cursor.fetchone():
                continue

            cursor.execute("""
            INSERT INTO books
            (book_number,book_name,author,category)
            VALUES(%s,%s,%s,%s)
            """,(

                str(row["book_number"]).strip(),
                str(row["book_name"]).strip(),
                str(row["author"]).strip(),
                str(row["category"]).strip()

            ))

            count += 1

        conn.commit()

        flash(f"{count} Books Imported Successfully","success")

    except Exception as e:

        conn.rollback()
        flash(str(e),"error")

    finally:

        cursor.close()
        conn.close()

    return redirect("/bulk_book_management")
@app.route("/assign_rfid")
def assign_rfid():

    return render_template("assign_rfid.html")
@app.route("/get_book_details/<book_number>")
def get_book_details(book_number):

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            book_number,
            book_name,
            author,
            category,
            uid
        FROM books
        WHERE book_number=%s
    """, (book_number,))

    book = cursor.fetchone()

    cursor.close()
    conn.close()

    if book:
        return jsonify(book)

    return jsonify({})
@app.route("/get_uid")
def get_uid():

    try:

        if arduino is None:
            return ""

        if arduino.in_waiting > 0:

            uid = arduino.readline().decode("utf-8").strip()

            print(uid)

            return uid

        return ""

    except Exception as e:

        print(e)

        return ""
@app.route("/assign_book_uid", methods=["POST"])
def assign_book_uid():

    data = request.get_json()

    uid = data["uid"].strip()
    book_number = data["book_number"].strip()

    conn = get_connection()
    cursor = conn.cursor()

    try:

        # Check book exists

        cursor.execute("""
            SELECT uid
            FROM books
            WHERE book_number=%s
        """, (book_number,))

        book = cursor.fetchone()

        if not book:

            return jsonify({
                "success": False,
                "message": "Book Number not found."
            })

        # Check RFID already used

        cursor.execute("""
            SELECT book_number
            FROM books
            WHERE uid=%s
        """, (uid,))

        existing = cursor.fetchone()

        if existing:

            return jsonify({
                "success": False,
                "message": "RFID already assigned to another book."
            })

        # Save RFID

        cursor.execute("""
            UPDATE books
            SET uid=%s
            WHERE book_number=%s
        """, (uid, book_number))

        conn.commit()

        return jsonify({
            "success": True
        })

    except Exception as e:

        conn.rollback()

        return jsonify({
            "success": False,
            "message": str(e)
        })

    finally:

        cursor.close()
        conn.close()
@app.route("/bulk_delete_books", methods=["POST"])
def bulk_delete_books():

    if "excel_file" not in request.files:
        flash("Please upload an Excel file.", "error")
        return redirect("/bulk_book_management")

    file = request.files["excel_file"]

    if file.filename == "":
        flash("Please select an Excel file.", "error")
        return redirect("/bulk_book_management")

    conn = get_connection()
    cursor = conn.cursor()

    deleted = 0
    skipped = 0

    try:

        df = pd.read_excel(file)
        df.columns = df.columns.str.strip().str.lower()

        if "book_number" not in df.columns:
            flash("Excel must contain 'book_number' column.", "error")
            return redirect("/bulk_book_management")

        for _, row in df.iterrows():

            book_number = str(row["book_number"]).strip()

            cursor.execute(
                "SELECT book_number FROM books WHERE book_number=%s",
                (book_number,)
            )

            if not cursor.fetchone():
                skipped += 1
                continue

            cursor.execute(
                "DELETE FROM books WHERE book_number=%s",
                (book_number,)
            )

            deleted += 1

        conn.commit()

        flash(
            f"{deleted} books deleted successfully. {skipped} books were not found.",
            "success"
        )

    except Exception as e:

        conn.rollback()
        flash(f"Error: {e}", "error")

    finally:

        cursor.close()
        conn.close()

    return redirect("/bulk_book_management")
@app.route("/reports")
def reports():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM books")
    total_books = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM books
        WHERE status='Available'
    """)
    available_books = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM books
        WHERE status='Issued'
    """)
    issued_books = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM students
    """)
    total_students = cursor.fetchone()[0]

    cursor.execute("""
       SELECT IFNULL(SUM(fine),0)
       FROM transactions
     """)
    total_fine = cursor.fetchone()[0]
    cursor.execute("""
        SELECT COUNT(*)
        FROM transactions
        WHERE status='Issued'
        AND due_date < CURDATE()
    """)
    overdue_books = cursor.fetchone()[0]
    conn.close()
    return render_template(
    "reports.html",
    total_books=total_books,
    available_books=available_books,
    issued_books=issued_books,
    total_students=total_students,
    overdue_books=overdue_books,
    total_fine=total_fine
)
 
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)