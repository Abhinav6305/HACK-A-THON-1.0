import os
import re
import csv
import datetime
from urllib.parse import urlparse

from flask import (
    Flask, request, render_template, redirect, url_for,
    flash, session, send_file, abort
)
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
from ai_reviewer import evaluate_abstract  # 🤖 AI Evaluation

# ------------------ Config ------------------
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# folders for uploads
ABSTRACT_DIR = os.path.join(BASE_DIR, "static", "uploads", "abstracts")
PAYMENT_DIR = os.path.join(BASE_DIR, "static", "uploads", "payments")
os.makedirs(ABSTRACT_DIR, exist_ok=True)
os.makedirs(PAYMENT_DIR, exist_ok=True)

# Admin credentials
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "origin@stpetershyd.com")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "#C0re0r!g!n")

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL")

# Render gives PostgreSQL URL; local dev will fallback to SQLite automatically
if not DATABASE_URL:
    DATABASE_URL = "sqlite:///" + os.path.join(BASE_DIR, "app.db")
elif DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = os.getenv("SECRET_KEY", "super-secret-key-change-me")
app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024  # 20MB max file size

db = SQLAlchemy(app)

# ------------------ Models ------------------
class Team(db.Model):
    __tablename__ = "teams"
    id = db.Column(db.Integer, primary_key=True)

    team_name = db.Column(db.String(200), nullable=False)
    leader_name = db.Column(db.String(200), nullable=False)
    leader_email = db.Column(db.String(200), nullable=False, index=True)
    leader_phone = db.Column(db.String(50), nullable=False)
    leader_company = db.Column(db.String(200), nullable=False)
    team_size = db.Column(db.Integer, nullable=False, default=3)

    abstract_path = db.Column(db.String(500), nullable=True)
    payment_path = db.Column(db.String(500), nullable=True)
    abstract_score = db.Column(db.Integer, nullable=True)  # 🧠 AI Score

    transaction_id = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    status = db.Column(db.String(50), default="submitted")

    members = db.relationship("Member", backref="team", cascade="all, delete-orphan")


class Member(db.Model):
    __tablename__ = "members"
    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(50), nullable=False)
    company = db.Column(db.String(200), nullable=False)

# ------------------ Helpers ------------------
ALLOWED_ABSTRACT = {".pdf"}
ALLOWED_IMAGES = {".png", ".jpg", ".jpeg", ".webp", ".gif"}

def _ext_ok(filename, allowed):
    ext = os.path.splitext(filename.lower())[1]
    return ext in allowed

def _validate_email(email: str) -> bool:
    pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    return bool(re.match(pattern, email or ""))

def _save_file(file_storage, folder_abs):
    if not file_storage:
        return None
    filename = secure_filename(file_storage.filename or "")
    if not filename:
        return None
    stamp = datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
    filename = f"{stamp}_{filename}"
    abs_path = os.path.join(folder_abs, filename)
    file_storage.save(abs_path)
    rel = os.path.relpath(abs_path, os.path.join(BASE_DIR, "static")).replace("\\", "/")
    return rel

def _file_len(file_storage):
    file_storage.stream.seek(0, 2)
    size = file_storage.stream.tell()
    file_storage.stream.seek(0)
    return size

# ------------------ Routes ------------------

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    form = request.form
    files = request.files

    team_name = (form.get("team_name") or "").strip()
    leader_name = (form.get("leader_name") or "").strip()
    leader_email = (form.get("leader_email") or "").strip()
    leader_phone = (form.get("leader_phone") or "").strip()
    leader_company = (form.get("leader_company") or "").strip()
    team_size_raw = (form.get("team_size") or "").strip()
    transaction_id = (form.get("transaction_id") or "").strip()

    # Validation
    if not team_name or not leader_name or not leader_email or not leader_phone or not leader_company:
        flash("Please fill all required fields.", "error")
        return redirect(url_for("register"))

    if not _validate_email(leader_email):
        flash("Invalid email address.", "error")
        return redirect(url_for("register"))

    try:
        team_size = int(team_size_raw)
    except ValueError:
        team_size = 0

    if team_size not in (3, 4, 5):
        flash("Team size must be 3, 4, or 5.", "error")
        return redirect(url_for("register"))

    abstract = files.get("abstract")
    payment = files.get("transaction_photo")

    # Abstract checks
    if not abstract or not abstract.filename:
        flash("Abstract PDF required.", "error")
        return redirect(url_for("register"))

    if not _ext_ok(abstract.filename, ALLOWED_ABSTRACT):
        flash("Abstract must be a PDF.", "error")
        return redirect(url_for("register"))

    if _file_len(abstract) > 10 * 1024 * 1024:
        flash("Abstract exceeds 10MB limit.", "error")
        return redirect(url_for("register"))

    # Payment checks
    if not payment or not payment.filename:
        flash("Payment screenshot required.", "error")
        return redirect(url_for("register"))

    if not _ext_ok(payment.filename, ALLOWED_IMAGES):
        flash("Payment must be an image file.", "error")
        return redirect(url_for("register"))

    if _file_len(payment) > 10 * 1024 * 1024:
        flash("Payment screenshot exceeds 10MB limit.", "error")
        return redirect(url_for("register"))

    # Team creation
    team = Team(
        team_name=team_name,
        leader_name=leader_name,
        leader_email=leader_email,
        leader_phone=leader_phone,
        leader_company=leader_company,
        team_size=team_size,
        transaction_id=transaction_id,
    )

    max_members = team_size - 1
    for i in range(1, max_members + 1):
        m_name = (form.get(f"member_{i}_name") or "").strip()
        m_email = (form.get(f"member_{i}_email") or "").strip()
        m_phone = (form.get(f"member_{i}_phone") or "").strip()
        m_comp = (form.get(f"member_{i}_company") or "").strip()

        if not (m_name and m_email and m_phone and m_comp):
            flash(f"Fill all fields for Member {i}.", "error")
            return redirect(url_for("register"))

        if not _validate_email(m_email):
            flash(f"Invalid email for Member {i}.", "error")
            return redirect(url_for("register"))

        team.members.append(Member(
            name=m_name, email=m_email, phone=m_phone, company=m_comp
        ))

    try:
        abstract_rel = _save_file(abstract, ABSTRACT_DIR)
        payment_rel = _save_file(payment, PAYMENT_DIR)
        team.abstract_path = abstract_rel
        team.payment_path = payment_rel

        db.session.add(team)
        db.session.commit()

        # === AI Evaluation ===
        abs_file_path = os.path.join("static", abstract_rel)
        with open(abs_file_path, "rb") as f:
            text = f.read().decode("utf-8", errors="ignore")

        ai_score = evaluate_abstract(text)
        team.abstract_score = ai_score
        db.session.commit()
        app.logger.info(f"AI evaluated abstract score: {ai_score}")
    except Exception as e:
        db.session.rollback()
        app.logger.exception("Error saving registration or evaluating AI.")
        flash("Server error during registration.", "error")
        return redirect(url_for("register"))

    return redirect(url_for("registration_success"))

@app.route("/registration_success")
def registration_success():
    return render_template("registration_success.html")

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "GET":
        return render_template("login.html")

    email = (request.form.get("email") or "").strip()
    password = (request.form.get("password") or "").strip()

    if email.lower() == ADMIN_EMAIL.lower() and password == ADMIN_PASSWORD:
        session["admin"] = True
        session.permanent = True
        return redirect(url_for("admin_dashboard"))

    flash("Invalid credentials.", "error")
    return redirect(url_for("admin_login"))

@app.route("/admin/logout")
def admin_logout():
    session.pop("admin", None)
    return redirect(url_for("admin_login"))

def _require_admin():
    if not session.get("admin"):
        abort(403)

@app.route("/admin/dashboard")
def admin_dashboard():
    _require_admin()
    teams = Team.query.order_by(Team.created_at.desc()).all()
    count = Team.query.count()
    return render_template("admin_dashboard.html", teams=teams, total=count)

@app.route("/admin/download_csv")
def download_csv():
    _require_admin()
    from io import StringIO, BytesIO
    si = StringIO()
    writer = csv.writer(si)
    writer.writerow([
        "Team Name", "Leader Name", "Leader Email", "Leader Phone", "Leader Company",
        "Team Size", "Transaction ID", "Abstract Path", "Payment Path",
        "AI Score", "Submitted At (UTC)"
    ])
    for t in Team.query.order_by(Team.created_at.desc()).all():
        writer.writerow([
            t.team_name, t.leader_name, t.leader_email, t.leader_phone, t.leader_company,
            t.team_size, t.transaction_id, t.abstract_path or "", t.payment_path or "",
            t.abstract_score or "N/A", t.created_at.strftime("%Y-%m-%d %H:%M:%S")
        ])
    mem = BytesIO()
    mem.write(si.getvalue().encode("utf-8"))
    mem.seek(0)
    filename = f"registrations_{datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    return send_file(mem, mimetype="text/csv", as_attachment=True, download_name=filename)

@app.route("/healthz")
def healthz():
    return "ok", 200

@app.errorhandler(403)
def forbidden(_):
    return "Forbidden", 403

@app.errorhandler(413)
def too_large(_):
    flash("Uploaded file too large.", "error")
    return redirect(url_for("register"))

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        print("✅ Database tables ready and app running!")
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=True)
