from flask import Flask, render_template
import os

app = Flask(__name__)
app.secret_key = "library_rfid_secret_key"

from routes.books import books_bp
from routes.students import students_bp
from routes.transactions import transactions_bp
from routes.dashboard import dashboard_bp
from routes.reports import reports_bp
from routes.rfid import rfid_bp   
from routes.auth import auth_bp

app.register_blueprint(auth_bp)
app.register_blueprint(books_bp)
app.register_blueprint(students_bp)
app.register_blueprint(transactions_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(reports_bp)
app.register_blueprint(rfid_bp)  


@app.route("/")
def home():
    return render_template("dashboard.html")
@app.route("/issue")
def issue_book():
    return render_template("issue_book.html")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)