import os
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from datetime import datetime

# ---------------------------------------------------------
# Flask Setup
# ---------------------------------------------------------
app = Flask(__name__)
app.secret_key = "supersecretkey"

# ---------------------------------------------------------
# SECURE SQLITE PATH FOR RENDER
# ---------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")   # inside project folder
os.makedirs(DATA_DIR, exist_ok=True)

DB_PATH = os.path.join(DATA_DIR, "registrations.db")

app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_PATH}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


# ---------------------------------------------------------
# DATABASE MODEL
# ---------------------------------------------------------
class Registration(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    team_name = db.Column(db.String(200), nullable=False)
    team_leader = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    college = db.Column(db.String(200), nullable=False)
    members = db.Column(db.String(500), nullable=False)
    idea = db.Column(db.String(500), nullable=False)
    abstract_filename = db.Column(db.String(300))
    payment_screenshot = db.Column(db.String(300))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


# ---------------------------------------------------------
# Initialize DB
# ---------------------------------------------------------
with app.app_context():
    db.create_all()


# ---------------------------------------------------------
# ROUTES
# ---------------------------------------------------------

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        team_name = request.form["team_name"]
        team_leader = request.form["team_leader"]
        email = request.form["email"]
        phone = request.form["phone"]
        college = request.form["college"]
        members = request.form["members"]
        idea = request.form["idea"]

        # File Upload Path
        upload_folder = os.path.join(BASE_DIR, "uploads")
        os.makedirs(upload_folder, exist_ok=True)

        abstract_file = request.files.get("abstract")
        payment_file = request.files.get("payment")

        abstract_filename = None
        payment_filename = None

        if abstract_file:
            abstract_filename = secure_filename(abstract_file.filename)
            abstract_file.save(os.path.join(upload_folder, abstract_filename))

        if payment_file:
            payment_filename = secure_filename(payment_file.filename)
            payment_file.save(os.path.join(upload_folder, payment_filename))

        entry = Registration(
            team_name=team_name,
            team_leader=team_leader,
            email=email,
            phone=phone,
            college=college,
            members=members,
            idea=idea,
            abstract_filename=abstract_filename,
            payment_screenshot=payment_filename,
        )
        db.session.add(entry)
        db.session.commit()
        return render_template("registration_success.html")

    return render_template("register.html")


# ---------------------------------------------------------
# ADMIN LOGIN
# ---------------------------------------------------------
ADMIN_USER = "admin"
ADMIN_PASS = "admin123"

@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if username == ADMIN_USER and password == ADMIN_PASS:
            session["admin"] = True
            return redirect(url_for("admin_dashboard"))
        else:
            flash("Invalid credentials!")

    return render_template("admin_login.html")


# ---------------------------------------------------------
# ADMIN DASHBOARD
# ---------------------------------------------------------
@app.route("/admin_dashboard")
def admin_dashboard():
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    all_regs = Registration.query.all()
    count = len(all_regs)

    return render_template("admin_dashboard.html", registrations=all_regs, count=count)


# ---------------------------------------------------------
# CSV EXPORT
# ---------------------------------------------------------
import csv

@app.route("/export_csv")
def export_csv():
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    export_path = os.path.join(BASE_DIR, "registrations_export.csv")

    all_regs = Registration.query.all()

    with open(export_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "ID", "Team Name", "Leader", "Email", "Phone",
            "College", "Members", "Idea", "Abstract", "Payment", "Timestamp"
        ])

        for r in all_regs:
            writer.writerow([
                r.id, r.team_name, r.team_leader, r.email, r.phone,
                r.college, r.members, r.idea, r.abstract_filename,
                r.payment_screenshot, r.timestamp
            ])

    return send_file(export_path, as_attachment=True)


# ---------------------------------------------------------
# LOGOUT
# ---------------------------------------------------------
@app.route("/logout")
def logout():
    session.pop("admin", None)
    return redirect(url_for("admin_login"))


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)
