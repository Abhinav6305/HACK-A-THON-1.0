import os
from flask import Flask, render_template, request, redirect, session, send_from_directory, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "supersecretkey"  # Change this

# -----------------------------
# DATABASE CONFIG
# -----------------------------
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://")

    app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///local.db"

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# -----------------------------
# UPLOAD FOLDER
# -----------------------------
UPLOAD_FOLDER = "uploads/abstracts"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# -----------------------------
# DATABASE MODEL
# -----------------------------
class Registration(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    team_name = db.Column(db.String(100), nullable=False)
    leader_name = db.Column(db.String(100), nullable=False)
    leader_email = db.Column(db.String(100), nullable=False)
    leader_phone = db.Column(db.String(20), nullable=False)
    leader_company = db.Column(db.String(200), nullable=False)

    team_size = db.Column(db.Integer, nullable=False)

    member_1_name = db.Column(db.String(100))
    member_1_email = db.Column(db.String(100))
    member_1_phone = db.Column(db.String(20))
    member_1_company = db.Column(db.String(200))

    member_2_name = db.Column(db.String(100))
    member_2_email = db.Column(db.String(100))
    member_2_phone = db.Column(db.String(20))
    member_2_company = db.Column(db.String(200))

    member_3_name = db.Column(db.String(100))
    member_3_email = db.Column(db.String(100))
    member_3_phone = db.Column(db.String(20))
    member_3_company = db.Column(db.String(200))

    member_4_name = db.Column(db.String(100))
    member_4_email = db.Column(db.String(100))
    member_4_phone = db.Column(db.String(20))
    member_4_company = db.Column(db.String(200))

    abstract_filename = db.Column(db.String(200), nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# -----------------------------
# INIT DB (only run once)
# -----------------------------
@app.route("/init_db")
def init_db():
    db.create_all()
    return "Database initialized successfully!"


# -----------------------------
# ROUTES
# -----------------------------
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":

        team_name = request.form["team_name"]
        leader_name = request.form["leader_name"]
        leader_email = request.form["leader_email"]
        leader_phone = request.form["leader_phone"]
        leader_company = request.form["leader_company"]
        team_size = int(request.form["team_size"])

        # Abstract upload
        abstract = request.files["abstract"]
        abstract_filename = secure_filename(abstract.filename)
        abstract.save(os.path.join(app.config["UPLOAD_FOLDER"], abstract_filename))

        # Create DB entry
        reg = Registration(
            team_name=team_name,
            leader_name=leader_name,
            leader_email=leader_email,
            leader_phone=leader_phone,
            leader_company=leader_company,
            team_size=team_size,
            abstract_filename=abstract_filename
        )

        # Add Member Details
        for i in range(1, team_size):
            setattr(reg, f"member_{i}_name", request.form.get(f"member_{i}_name"))
            setattr(reg, f"member_{i}_email", request.form.get(f"member_{i}_email"))
            setattr(reg, f"member_{i}_phone", request.form.get(f"member_{i}_phone"))
            setattr(reg, f"member_{i}_company", request.form.get(f"member_{i}_company"))

        db.session.add(reg)
        db.session.commit()

        return redirect("/registration_success")

    return render_template("register.html")


@app.route("/registration_success")
def success():
    return render_template("registration_success.html")


# -----------------------------
# ADMIN LOGIN
# -----------------------------
ADMIN_EMAIL = "origin@gmail.com"
ADMIN_PASSWORD = "origin@123"

@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
            session["admin_logged_in"] = True
            return redirect("/admin_dashboard")
        else:
            flash("Invalid credentials")

    return render_template("admin_login.html")


@app.route("/admin_logout")
def admin_logout():
    session.clear()
    return redirect("/admin_login")


# -----------------------------
# ADMIN DASHBOARD
# -----------------------------
@app.route("/admin_dashboard")
def admin_dashboard():
    if not session.get("admin_logged_in"):
        return redirect("/admin_login")

    registrations = Registration.query.order_by(Registration.id.desc()).all()

    formatted = []
    for reg in registrations:
        members = []
        for i in range(1, reg.team_size):
            m = {
                "name": getattr(reg, f"member_{i}_name"),
                "email": getattr(reg, f"member_{i}_email"),
                "phone": getattr(reg, f"member_{i}_phone"),
                "college": getattr(reg, f"member_{i}_company"),
            }
            if m["name"]:
                members.append(m)

        formatted.append({
            "id": reg.id,
            "team_name": reg.team_name,
            "leader_name": reg.leader_name,
            "leader_email": reg.leader_email,
            "leader_phone": reg.leader_phone,
            "leader_company": reg.leader_company,
            "team_size": reg.team_size,
            "members": members,
            "abstract": reg.abstract_filename,
            "created": reg.created_at.strftime("%d-%m-%Y %I:%M %p")
        })

    return render_template("admin_dashboard.html", registrations=formatted)


# -----------------------------
# DOWNLOAD ABSTRACT
# -----------------------------
@app.route("/download/<filename>")
def download_file(filename):
    return send_from_directory("uploads/abstracts", filename, as_attachment=True)


# -----------------------------
# MAIN
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True)
