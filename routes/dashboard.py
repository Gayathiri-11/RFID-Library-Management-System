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

dashboard_bp = Blueprint("dashboard", __name__)

@dashboard_bp.route("/dashboard")
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
@dashboard_bp.route("/reports")
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