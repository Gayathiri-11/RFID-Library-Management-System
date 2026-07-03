from flask import Blueprint, render_template, request
from database.db import get_connection
from datetime import datetime, timedelta

transactions_bp = Blueprint("transactions", __name__)
@transactions_bp.route("/transactions")
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

        # Default values
        t["is_overdue"] = False
        t["fine"] = 0

        if t["due_date"]:

            # Convert datetime to date if required
            if hasattr(t["due_date"], "date"):
                due_date = t["due_date"].date()
            else:
                due_date = t["due_date"]

            # Calculate fine only for issued books
            if t["status"] == "Issued":

                overdue_days = (today - due_date).days

                if overdue_days > 0:
                    t["is_overdue"] = True
                    t["fine"] = overdue_days * 5

            # Returned books
            elif t["status"] == "Returned":

                # Show stored fine from database
                t["fine"] = t["fine"] if t["fine"] else 0

    conn.close()

    return render_template(
        "transactions.html",
        transactions=transactions
    )
@transactions_bp.route("/export_transactions")
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

@transactions_bp.route("/issue_book", methods=["GET", "POST"])
def issue_book():

    if request.method == "POST":

        uid = request.form.get("uid")
        roll_number = request.form.get("roll_number")

        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        # Check Book
        cursor.execute(
            "SELECT * FROM books WHERE uid=%s",
            (uid,)
        )
        book = cursor.fetchone()

        if not book:
            conn.close()
            return render_template(
                "issue_book.html",
                message="Book not found"
            )

        if book["status"] != "Available":
            conn.close()
            return render_template(
                "issue_book.html",
                message="Book is already issued"
            )

        # Check Student
        cursor.execute(
            "SELECT * FROM students WHERE roll_number=%s AND status='Active'",
            (roll_number,)
        )
        student = cursor.fetchone()

        if not student:
            conn.close()
            return render_template(
                "issue_book.html",
                message="Student not found"
            )

        try:

            issue_date = datetime.now()
            due_date = issue_date + timedelta(days=15)

            cursor.execute("""
                INSERT INTO transactions
                (uid, roll_number, issue_date, due_date, status, fine)
                VALUES (%s,%s,%s,%s,%s,%s)
            """,(
                uid,
                roll_number,
                issue_date,
                due_date,
                "Issued",
                0
            ))

            cursor.execute("""
                UPDATE books
                SET
                    status='Issued',
                    issue_count=issue_count+1
                WHERE uid=%s
            """,(uid,))

            conn.commit()

            conn.close()

            return render_template(
                "issue_book.html",
                message="Book Issued Successfully",
                redirect="/dashboard"
            )

        except Exception as e:

            conn.rollback()
            conn.close()

            return f"Error : {e}"

    return render_template("issue_book.html")
@transactions_bp.route("/return_book", methods=["GET", "POST"])
def return_book():

    if request.method == "POST":

        uid = request.form["uid"].strip()

        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        try:

            # Get latest issued transaction
            cursor.execute("""
                SELECT
                    t.*,
                    b.book_name,
                    s.student_name
                FROM transactions t
                JOIN books b
                    ON t.uid = b.uid
                JOIN students s
                    ON t.roll_number = s.roll_number
                WHERE t.uid=%s
                AND t.status='Issued'
                ORDER BY t.issue_date DESC
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

            today = datetime.now().date()
            due_date = transaction["due_date"]

            # Calculate Fine (₹5/day)
            fine = 0

            if due_date:

                if hasattr(due_date, "date"):
                    due_date = due_date.date()

                overdue_days = (today - due_date).days

                if overdue_days > 0:
                    fine = overdue_days * 5

            # Update Transaction
            cursor.execute("""
                UPDATE transactions
                SET
                    status='Returned',
                    return_date=%s,
                    fine=%s
                WHERE id=%s
            """,(
                datetime.now(),
                fine,
                transaction["id"]
            ))

            # Update Book Status
            cursor.execute("""
                UPDATE books
                SET status='Available'
                WHERE uid=%s
            """,(uid,))

            conn.commit()

            conn.close()

            return render_template(
                "return_book.html",
                message=f"Book Returned Successfully. Fine Collected : ₹{fine}",
                redirect="/dashboard"
            )

        except Exception as e:

            conn.rollback()
            conn.close()

            return f"Error : {e}"

    return render_template("return_book.html")