from flask import Blueprint, render_template, jsonify, request
from database.db import get_connection
from rfid import scan_uid

rfid_bp = Blueprint("rfid", __name__)


# -----------------------------
# Scan RFID
# -----------------------------
@rfid_bp.route("/scan_uid")
def scan_uid_route():
    try:
        uid = scan_uid()

        print("RFID UID:", uid)

        return jsonify({
            "uid": uid
        })

    except Exception as e:
        print("RFID scan error:", e)

        return jsonify({
            "uid": "",
            "error": str(e)
        }), 500


# -----------------------------
# Get UID
# -----------------------------
@rfid_bp.route("/get_uid")
def get_uid():
    try:
        uid = scan_uid()

        if not uid or uid == "RFID_NOT_CONNECTED":
            return jsonify({
                "uid": ""
            })

        return jsonify({
            "uid": uid
        })

    except Exception as e:
        print("Get UID error:", e)

        return jsonify({
            "uid": "",
            "error": str(e)
        }), 500


# -----------------------------
# RFID API
# Used by Issue Book page
# -----------------------------
@rfid_bp.route("/api/rfid")
def api_rfid():
    try:
        uid = scan_uid()

        print("API RFID UID:", uid)

        if not uid or uid == "RFID_NOT_CONNECTED":
            return jsonify({
                "uid": ""
            })

        return jsonify({
            "uid": uid
        })

    except Exception as e:
        print("RFID API error:", e)

        return jsonify({
            "uid": "",
            "error": str(e)
        }), 500


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

    conn = None
    cursor = None

    try:
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
            WHERE book_number = %s
        """, (book_number,))

        book = cursor.fetchone()

        if book:
            return jsonify(book)

        return jsonify({})

    except Exception as e:
        print("Get book details error:", e)

        return jsonify({
            "error": str(e)
        }), 500

    finally:
        if cursor:
            cursor.close()

        if conn:
            conn.close()
