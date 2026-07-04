from flask import Blueprint, render_template, request
from database.db import get_connection
from datetime import datetime, timedelta

auth_bp = Blueprint("auth", __name__)
@auth_bp.route("/login", methods=["GET", "POST"])
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

@auth_bp.route("/logout")
def logout():
    return redirect("/login")
