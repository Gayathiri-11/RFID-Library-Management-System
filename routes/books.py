from flask import Blueprint, render_template, request, redirect, url_for
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

books_bp = Blueprint("books", __name__)
@books_bp.route("/books")
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
@books_bp.route("/edit_book/<uid>", methods=["GET", "POST"])
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
@books_bp.route("/assign_rfid")
def assign_rfid():
    return render_template("assign_rfid.html")
@books_bp.route("/assign_book_uid", methods=["POST"])
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

@books_bp.route("/replace_uid/<old_uid>", methods=["GET", "POST"])
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

        return redirect(url_for("books.books"))
    return render_template(
        "replace_uid.html",
        old_uid=old_uid
    )
@books_bp.route("/deactivate_book/<uid>")
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
    return redirect(url_for("books.books"))
@books_bp.route("/add_book", methods=["GET", "POST"])
def add_book():

    if request.method == "POST":

        uid = request.form["uid"].strip()
        book_number = request.form["book_number"].strip()
        book_name = request.form["book_name"].strip()
        author = request.form["author"].strip()
        
        conn = get_connection()
        cursor = conn.cursor()

        try:

            # Check duplicate UID
            cursor.execute(
                "SELECT uid FROM books WHERE uid=%s",
                (uid,)
            )

            if cursor.fetchone():
                conn.close()
                return "Book already exists with this RFID UID."

            # Check duplicate Book Number
            cursor.execute(
                "SELECT book_number FROM books WHERE book_number=%s",
                (book_number,)
            )

            if cursor.fetchone():
                conn.close()
                return "Book Number already exists."

            # Insert Book
            cursor.execute("""
                INSERT INTO books
                (
                    uid,
                    book_number,
                    book_name,
                    author,
                    status,
                    active,
                    issue_count
                )
                VALUES
                (
                    %s,%s,%s,%s,%s,%s,%s,
                )
            """,(
                uid,
                book_number,
                book_name,
                author,
                "Available",
                1,
                0
            ))

            conn.commit()
            conn.close()

            return render_template(
                "add_book.html",
                success=True
            )

        except Exception as e:

            conn.rollback()
            conn.close()

            return f"Error Adding Book : {e}"

    return render_template("add_book.html")
@books_bp.route("/check_book/<uid>")
def check_book_status(uid):

    conn = get_connection()
    cursor = conn.cursor(dictionary=True, buffered=True)

    cursor.execute("SELECT status FROM books WHERE uid=%s", (uid,))
    book = cursor.fetchone()

    conn.close()

    if not book:
        return {"status": "NOT_FOUND"}

    return {"status": book["status"]}
@books_bp.route("/check_book", methods=["GET", "POST"])
def check_book():

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    book = None

    if request.method == "POST":

        keyword = request.form["keyword"]

        cursor.execute("""
            SELECT *
            FROM books
            WHERE uid=%s
               OR book_number=%s
               OR book_name=%s
        """, (keyword, keyword, keyword))

        book = cursor.fetchone()

    cursor.execute("""
        SELECT
            book_name,
            COUNT(*) AS total_books,
            SUM(CASE WHEN status='Available' THEN 1 ELSE 0 END) AS available_books
        FROM books
        GROUP BY book_name
        ORDER BY book_name
    """)

    book_summary = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "check_book.html",
        book=book,
        book_summary=book_summary
    )
@books_bp.route("/get_book/<uid>")
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
@books_bp.route("/book_statistics")
def book_statistics():

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            book_number,
            book_name,
            author,
            issue_count
        FROM books
        ORDER BY issue_count DESC
    """)

    books = cursor.fetchall()

    conn.close()

    return render_template(
        "book_statistics.html",
        books=books
    )
@books_bp.route("/bulk_book_management")
def bulk_book_management():
    return render_template("bulk_book_management.html")
@books_bp.route("/bulk_import_books", methods=["POST"])
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
@books_bp.route("/bulk_delete_books", methods=["POST"])
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
