from flask import Blueprint, render_template, jsonify, request
from database.db import get_connection
from rfid import scan_uid

rfid_bp = Blueprint("rfid", __name__)


# -----------------------------
# Scan RFID
# -----------------------------
@rfid_bp.route("/scan_uid")
def scan_uid_route():

    uid = scan_uid()
    print("returning: ",uid)
    
    return jsonify({
        "uid": uid
    })


# -----------------------------
# Get UID (Used for Auto Scan)
# -----------------------------
@rfid_bp.route("/get_uid")
def get_uid():

    uid = scan_uid()

    if uid == "RFID_NOT_CONNECTED":
        return ""

    return uid


# -----------------------------
# Assign RFID Page
# -----------------------------
@rfid_bp.route("/assign_rfid")
def assign_rfid():

    return render_template("assign_rfid.html")


# -----------------------------
# Get Book Details
# -----------------------------
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