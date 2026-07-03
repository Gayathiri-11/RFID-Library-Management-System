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

rfid_bp = Blueprint("rfid", __name__)
@rfid_bp.route("/assign_rfid")
def assign_rfid():

    return render_template("assign_rfid.html")
@rfid_bp.route("/get_book_details/<book_number>")
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
@rfid_bp.route("/get_uid")
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
@rfid_bp.route("/assign_book_uid", methods=["POST"])
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
@rfid_bp.route("/scan_uid")
def scan_uid():

    if arduino is None:
        return {"uid": "RFID_NOT_CONNECTED"}

    uid = arduino.readline().decode().strip()

    return {"uid": uid}
