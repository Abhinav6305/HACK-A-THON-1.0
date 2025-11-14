import os
from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory, send_file
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import csv
from io import StringIO
from datetime import datetime


# --------------------------
# Flask Setup
# --------------------------
app = Flask(__name__)
app.secret_key = "supersecretkey"

# --------------------------
# Database (PostgreSQL)
# --------------------------
# Reads DATABASE_URL from Render environment
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL")

# Required for PostgreSQL SSL in Render
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    "connect_args": {"sslmode": "require"}
}

db = SQLAlchemy(app)


# --------------------------
# File Upload Setup
# --------------------------
UPLOAD_FOLDER = "abstracts"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Ensure payment upload directory exists
os.makedirs("static/uploads", exist_ok=True)


# --------------------------
# Database Model
# --------------------------
class Registration(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    team_name = db.Column(db.String(100), nullable=False)
    leader_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    members = db.Column(db.String(300))
    payment_screenshot = db.Column(db.String(300))
    abstract_file = db.Column(db.String(300))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


with app.app_context():
    db.create_all()


# --------------------------
# Home Page
# --------------------------
@app.route("/")
def home():
    return render_template("index.html")


# --------------------------
# Registration Page
# --------------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":

        team_name = request.form["team_name"]
        leader_name = request.form["leader_name"]
        email = request.form["email"]
        phone = request.form["phone"]
        members = request.form["members"]

        # Upload payment screenshot
        payment_file = request.files["payment_screenshot"]
        payment_filename = None
        if payment_file and payment_file.filename != "":
            payment_filename = secure_filename(payment_file.filename)
            payment_file.save(os.path.join("static/uploads", payment_filename))

        # Upload abstract PDF
        abstract_file = request.files.get("abstract_file")
        abstract_filename = None
        if abstract_file and abstract_file.filename != "":
            abstract_filename = secure_filename(abstract_file.filename)
            abstract_file.save(os.path.join(app.config["UPLOAD_FOLDER"], abstract_filename))

        reg = Registration(
            team_name=team_name,
            leader_name=leader_name,
            email=email,
            phone=phone,
            members=members,
            payment_screenshot=payment_filename,
            abstract_file=abstract_filename
        )
        db.session.add(reg)
        db.session.commit()

        return redirect(url_for("success"))

    return render_template("registration.html")


@app.route("/success")
def success():
    return render_template("success.html")


# --------------------------
# Admin Login
# --------------------------
@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        if request.form["username"] == "admin" and request.form["password"] == "admin123":
            session["admin"] = True
            return redirect("/admin_dashboard")

    return render_template("admin_login.html")


# --------------------------
# Admin Logout
# --------------------------
@app.route("/admin_logout")
def admin_logout():
    session.pop("admin", None)
    return redirect("/admin_login")


# --------------------------
# Admin Dashboard
# --------------------------
@app.route("/admin_dashboard")
def admin_dashboard():
    if "admin" not in session:
        return redirect("/admin_login")

    search_query = request.args.get("search", "")

    if search_query:
        registrations = Registration.query.filter(
            Registration.team_name.ilike(f"%{search_query}%")
        ).all()
    else:
        registrations = Registration.query.order_by(Registration.timestamp.desc()).all()

    return render_template("admin_dashboard.html",
                           registrations=registrations,
                           search_query=search_query)


# --------------------------
# Download Abstract
# --------------------------
@app.route("/download/<filename>")
def download_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename, as_attachment=True)


# --------------------------
# Export CSV
# --------------------------
@app.route("/export_csv")
def export_csv():
    if "admin" not in session:
        return redirect("/admin_login")

    registrations = Registration.query.all()

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["Team Name", "Leader", "Email", "Phone", "Members", "Abstract File", "Timestamp"])

    for r in registrations:
        writer.writerow([
            r.team_name,
            r.leader_name,
            r.email,
            r.phone,
            r.members,
            r.abstract_file,
            r.timestamp
        ])

    output.seek(0)
    return send_file(
        StringIO(output.getvalue()),
        mimetype="text/csv",
        as_attachment=True,
        download_name="registrations.csv"
    )


# --------------------------
# Run App
# --------------------------
if __name__ == "__main__":
    app.run(debug=True)
