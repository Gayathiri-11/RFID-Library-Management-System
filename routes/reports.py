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

reports_bp = Blueprint("reports", __name__)
@reports_bp.route("/overdue_report")
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
@reports_bp.route("/export_overdue_report")
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
