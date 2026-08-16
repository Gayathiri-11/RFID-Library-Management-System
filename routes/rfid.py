from flask import Blueprint, render_template, jsonify, request
from database.db import get_connection

rfid_bp = Blueprint("rfid", __name__)

# Stores the latest RFID UID received from the Windows PC
latest_rfid_uid = ""


# -----------------------------
# Receive RFID UID from PC bridge
# -----------------------------
@rfid_bp.route("/api/rfid/update", methods=["POST"])
def update_rfid():
    global latest_rfid_uid

    try:
        data = request.get_json(silent=True)

        if not data or "uid" not in data:
            return jsonify({
                "success": False,
                "message": "UID missing"
            }), 400

        uid = str(data["uid"]).strip()

        if not uid:
            return jsonify({
                "success": False,
                "message": "Empty UID"
            }), 400

        latest_rfid_uid = uid

        print("RFID UID received from PC:", latest_rfid_uid)

        return jsonify({
            "success": True,
            "uid": latest_rfid_uid
        })

    except Exception as e:
        print("RFID update error:", e)

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# -----------------------------
# Scan RFID
# Used by Add Book / other pages
# -----------------------------
@rfid_bp.route("/scan_uid")
def scan_uid_route():
    try:
        print("RFID UID:", latest_rfid_uid)

        return jsonify({
            "uid": latest_rfid_uid
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
        print("Get UID:", latest_rfid_uid)

        return jsonify({
            "uid": latest_rfid_uid
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
        print("API RFID UID:", latest_rfid_uid)

        return jsonify({
            "uid": latest_rfid_uid
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