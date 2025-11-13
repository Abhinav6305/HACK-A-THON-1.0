from flask import Flask, render_template, request, redirect, send_from_directory, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)

# ============================
# Render-Compatible Database
# ============================
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///hackathon.db")

if app.config["SQLALCHEMY_DATABASE_URI"].startswith("postgres://"):
    app.config["SQLALCHEMY_DATABASE_URI"] = app.config["SQLALCHEMY_DATABASE_URI"].replace("postgres://", "postgresql://")

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ============================
# Upload folder
# ============================
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


# ============================
# Database Model (No Payment)
# ============================
class Registration(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    team_name = db.Column(db.String(200))
    leader_name = db.Column(db.String(200))
    leader_email = db.Column(db.String(200))
    leader_phone = db.Column(db.String(200))
    leader_company = db.Column(db.String(200))
    team_size = db.Column(db.Integer)
    members = db.Column(db.JSON)  # list of members
    abstract_filename = db.Column(db.String(300))


# ============================
# Init DB Route (DEV ONLY)
# ============================
@app.route("/init_db")
def init_db():
    with app.app_context():
        db.create_all()
    return "Database initialized successfully!"


# ============================
# HOME PAGE
# ============================
@app.route("/")
def home():
    return render_template("index.html")


# ============================
# SHOW REGISTER PAGE
# ============================
@app.route("/register", methods=["GET"])
def show_register():
    return render_template("register.html")


# ============================
# HANDLE FORM SUBMISSION
# ============================
@app.route("/register", methods=["POST"])
def register_team():

    # STEP-1 – Team lead
    team_name = request.form.get("team_name")
    leader_name = request.form.get("leader_name")
    leader_email = request.form.get("leader_email")
    leader_phone = request.form.get("leader_phone")
    leader_company = request.form.get("leader_company")

    # STEP-2 – Team members
    team_size = int(request.form.get("team_size"))
    members = []

    for i in range(1, team_size):
        members.append({
            "name": request.form.get(f"member_{i}_name"),
            "email": request.form.get(f"member_{i}_email"),
            "phone": request.form.get(f"member_{i}_phone"),
            "college": request.form.get(f"member_{i}_company"),
        })

    # STEP-3 – Abstract upload
    abstract_file = request.files["abstract"]
    abstract_filename = secure_filename(abstract_file.filename)
    abstract_path = os.path.join(app.config["UPLOAD_FOLDER"], abstract_filename)
    abstract_file.save(abstract_path)

    # Save to DB
    new_reg = Registration(
        team_name=team_name,
        leader_name=leader_name,
        leader_email=leader_email,
        leader_phone=leader_phone,
        leader_company=leader_company,
        team_size=team_size,
        members=members,
        abstract_filename=abstract_filename,
    )

    db.session.add(new_reg)
    db.session.commit()

    return redirect("/registration_success")


# ============================
# SUCCESS PAGE
# ============================
@app.route("/registration_success")
def success():
    return render_template("success.html")


# ============================
# ADMIN LOGIN PAGE
# ============================
@app.route("/admin_login")
def admin_login():
    return render_template("admin_login.html")


# ============================
# ADMIN LOGIN AUTH
# ============================
@app.route("/admin_auth", methods=["POST"])
def admin_auth():
    username = request.form.get("username")
    password = request.form.get("password")

    if username == "admin" and password == "origin123":
        return redirect("/admin_dashboard")
    else:
        return "Invalid credentials. Try again."


# ============================
# ADMIN DASHBOARD
# ============================
@app.route("/admin_dashboard")
def admin_dashboard():
    registrations = Registration.query.all()
    total_count = Registration.query.count()
    return render_template("admin_dashboard.html", registrations=registrations, count=total_count)


# ============================
# DOWNLOAD ABSTRACT
# ============================
@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory("uploads", filename, as_attachment=True)


# ============================
# HEALTH CHECK
# ============================
@app.route("/healthz")
def health():
    return "ok"


# ============================
# RUN APP (LOCAL)
# ============================
if __name__ == "__main__":
    app.run(debug=True)
