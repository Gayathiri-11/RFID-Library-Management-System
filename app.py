from flask import Flask
import os
import serial
import time

app = Flask(__name__)
app.secret_key = "library_rfid_secret_key"

# Arduino Connection
if os.environ.get("RENDER"):
    arduino = None
else:
    try:
        arduino = serial.Serial("COM5", 9600, timeout=1)
        time.sleep(2)
        print("Arduino Connected")
    except Exception as e:
        print(e)
        arduino = None

from routes.books import books_bp
from routes.students import students_bp
from routes.transactions import transactions_bp
from routes.dashboard import dashboard_bp
from routes.reports import reports_bp

app.register_blueprint(books_bp)
app.register_blueprint(students_bp)
app.register_blueprint(transactions_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(reports_bp)


@app.route("/")
def home():
    return render_template("dashboard.html")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)