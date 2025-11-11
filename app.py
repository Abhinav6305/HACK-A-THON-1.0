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

# ------------------ Config ------------------
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# folders for uploads
ABSTRACT_DIR = os.path.join(BASE_DIR, "static", "uploads", "abstracts")
PAYMENT_DIR  = os.path.join(BASE_DIR, "static", "uploads", "payments")
os.makedirs(ABSTRACT_DIR, exist_ok=True)
os.makedirs(PAYMENT_DIR,  exist_ok=True)

# env (with safe defaults for local)
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "origin@stpetershyd.com")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "#C0re0r!g!n")

# DATABASE_URL from Render (supports postgres:// or postgresql://)
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# fallback to local sqlite if not set (local dev)
if not DATABASE_URL:
    DATABASE_URL = "sqlite:///" + os.path.join(BASE_DIR, "app.db")

# flask
app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = os.getenv("SECRET_KEY", "super-secret-key-change-me")
app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024  # 20MB hard cap

db = SQLAlchemy(app)

# ------------------ Models ------------------
class Team(db.Model):
    __tablename__ = "teams"
    id = db.Column(db.Integer, primary_key=True)

    team_name     = db.Column(db.String(200), nullable=False)
    leader_name   = db.Column(db.String(200), nullable=False)
    leader_email  = db.Column(db.String(200), nullable=False, index=True)
    leader_phone  = db.Column(db.String(50),  nullable=False)
    leader_company= db.Column(db.String(200), nullable=False)

    team_size     = db.Column(db.Integer, nullable=False, default=3)

    # stored relative to /static for easy serving
    abstract_path = db.Column(db.String(500), nullable=True)
    payment_path  = db.Column(db.String(500), nullable=True)

    transaction_id= db.Column(db.String(120), nullable=False)

    created_at    = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    # simple status field if you want (pending/approved/rejected)
    status        = db.Column(db.String(50), default="submitted")

    members = db.relationship("Member", backref="team", cascade="all, delete-orphan")

class Member(db.Model):
    __tablename__ = "members"
    id = db.Column(db.Integer, primary_key=True)

    team_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=False)

    name    = db.Column(db.String(200), nullable=False)
    email   = db.Column(db.String(200), nullable=False)
    phone   = db.Column(db.String(50),  nullable=False)
    company = db.Column(db.String(200), nullable=False)

# ------------------ Helpers ------------------
ALLOWED_ABSTRACT = {".pdf"}
ALLOWED_IMAGES   = {".png", ".jpg", ".jpeg", ".webp", ".gif"}

def _ext_ok(filename, allowed):
    ext = os.path.splitext(filename.lower())[1]
    return ext in allowed

def _validate_email(email: str) -> bool:
    # simple validation; keeps dependencies minimal
    pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    return bool(re.match(pattern, email or ""))

def _save_file(file_storage, folder_abs):
    """
    Save safely into folder_abs, return relative path under /static (for <a href>).
    """
    if not file_storage:
        return None
    filename = secure_filename(file_storage.filename or "")
    if not filename:
        return None
    # add timestamp to avoid collisions
    stamp = datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
    filename = f"{stamp}_{filename}"
    abs_path = os.path.join(folder_abs, filename)
    file_storage.save(abs_path)

    # return path relative to static (e.g., 'uploads/abstracts/....pdf')
    rel = os.path.relpath(abs_path, os.path.join(BASE_DIR, "static")).replace("\\", "/")
    return rel

def _file_len(file_storage):
    # some servers provide stream length; if not, read temporarily (small cap)
    file_storage.stream.seek(0, 2)
    size = file_storage.stream.tell()
    file_storage.stream.seek(0)
    return size

# ------------------ Routes ------------------
@app.before_first_request
def init_db():
    db.create_all()

@app.route("/")
def home():
    # your existing template
    return render_template("home.html")

# ----- Registration -----
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    # POST
    form = request.form
    files = request.files

    team_name      = (form.get("team_name") or "").strip()
    leader_name    = (form.get("leader_name") or "").strip()
    leader_email   = (form.get("leader_email") or "").strip()
    leader_phone   = (form.get("leader_phone") or "").strip()
    leader_company = (form.get("leader_company") or "").strip()
    team_size_raw  = (form.get("team_size") or "").strip()
    transaction_id = (form.get("transaction_id") or "").strip()

    # basic validations
    if not team_name or not leader_name or not leader_email or not leader_phone or not leader_company:
        flash("Please fill all required leader fields.", "error")
        return redirect(url_for("register"))

    if not _validate_email(leader_email):
        flash("Please enter a valid email address.", "error")
        return redirect(url_for("register"))

    try:
        team_size = int(team_size_raw)
    except ValueError:
        team_size = 0

    if team_size not in (3, 4, 5):
        flash("Team size must be 3, 4, or 5.", "error")
        return redirect(url_for("register"))

    if not transaction_id:
        flash("Transaction ID is required.", "error")
        return redirect(url_for("register"))

    # files
    abstract = files.get("abstract")
    payment  = files.get("transaction_photo")

    # abstract validation (<=10MB, .pdf only)
    if not abstract or not abstract.filename:
        flash("Abstract PDF is required.", "error")
        return redirect(url_for("register"))

    if not _ext_ok(abstract.filename, ALLOWED_ABSTRACT):
        flash("Abstract must be a .pdf file.", "error")
        return redirect(url_for("register"))

    if _file_len(abstract) > 10 * 1024 * 1024:
        flash("Abstract file exceeds 10MB limit.", "error")
        return redirect(url_for("register"))

    # payment screenshot validation (<=10MB, image only)
    if not payment or not payment.filename:
        flash("Payment screenshot is required.", "error")
        return redirect(url_for("register"))

    if not _ext_ok(payment.filename, ALLOWED_IMAGES):
        flash("Payment screenshot must be an image (png/jpg/jpeg/webp/gif).", "error")
        return redirect(url_for("register"))

    if _file_len(payment) > 10 * 1024 * 1024:
        flash("Payment screenshot exceeds 10MB limit.", "error")
        return redirect(url_for("register"))

    # build team
    team = Team(
        team_name=team_name,
        leader_name=leader_name,
        leader_email=leader_email,
        leader_phone=leader_phone,
        leader_company=leader_company,
        team_size=team_size,
        transaction_id=transaction_id,
    )

    # member fields: member_1..member_4 (because team_size max=5 → 4 members)
    max_members = team_size - 1  # excluding leader
    for i in range(1, max_members + 1):
        m_name = (form.get(f"member_{i}_name") or "").strip()
        m_email = (form.get(f"member_{i}_email") or "").strip()
        m_phone = (form.get(f"member_{i}_phone") or "").strip()
        m_comp  = (form.get(f"member_{i}_company") or "").strip()

        if not (m_name and m_email and m_phone and m_comp):
            flash(f"Please fill all fields for Member {i}.", "error")
            return redirect(url_for("register"))

        if not _validate_email(m_email):
            flash(f"Member {i} email is invalid.", "error")
            return redirect(url_for("register"))

        team.members.append(Member(
            name=m_name, email=m_email, phone=m_phone, company=m_comp
        ))

    # save files
    try:
        abstract_rel = _save_file(abstract, ABSTRACT_DIR)
        payment_rel  = _save_file(payment,  PAYMENT_DIR)
        team.abstract_path = abstract_rel
        team.payment_path  = payment_rel

        db.session.add(team)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        app.logger.exception("Error saving registration")
        flash("Server error while saving your registration. Please try again.", "error")
        return redirect(url_for("register"))

    # success
    return redirect(url_for("registration_success"))

@app.route("/registration_success")
def registration_success():
    return render_template("registration_success.html")

# ----- Admin Auth -----
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "GET":
        return render_template("admin_login.html")

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

# ----- Admin Dashboard -----
@app.route("/admin/dashboard")
def admin_dashboard():
    _require_admin()
    teams = (Team.query
             .order_by(Team.created_at.desc())
             .all())
    count = Team.query.count()
    return render_template("admin_dashboard.html", teams=teams, registration_count=count)

# CSV export
@app.route("/admin/download_csv")
def download_csv():
    _require_admin()

    # build csv in memory
    from io import StringIO, BytesIO
    si = StringIO()
    writer = csv.writer(si)
    writer.writerow([
        "Team Name", "Leader Name", "Leader Email", "Leader Phone", "Leader College/School",
        "Team Size", "Transaction ID", "Abstract Path", "Payment Path",
        "Member 1 Name", "Member 1 Email", "Member 1 Phone", "Member 1 College/School",
        "Member 2 Name", "Member 2 Email", "Member 2 Phone", "Member 2 College/School",
        "Member 3 Name", "Member 3 Email", "Member 3 Phone", "Member 3 College/School",
        "Member 4 Name", "Member 4 Email", "Member 4 Phone", "Member 4 College/School",
        "Submitted At (UTC)"
    ])

    for t in Team.query.order_by(Team.created_at.desc()).all():
        # pad members to 4 rows
        mems = t.members[:4] + [None] * (4 - len(t.members))
        row = [
            t.team_name, t.leader_name, t.leader_email, t.leader_phone, t.leader_company,
            t.team_size, t.transaction_id,
            (t.abstract_path or ""), (t.payment_path or "")
        ]
        for m in mems:
            if m:
                row.extend([m.name, m.email, m.phone, m.company])
            else:
                row.extend(["", "", "", ""])
        row.append(t.created_at.strftime("%Y-%m-%d %H:%M:%S"))
        writer.writerow(row)

    mem = BytesIO()
    mem.write(si.getvalue().encode("utf-8"))
    mem.seek(0)
    filename = f"registrations_{datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    return send_file(mem, mimetype="text/csv", as_attachment=True, download_name=filename)

# health
@app.route("/healthz")
def healthz():
    return "ok", 200

# ------------- Error handlers -------------
@app.errorhandler(403)
def forbidden(_):
    return "Forbidden", 403

@app.errorhandler(413)
def too_large(_):
    # triggered if MAX_CONTENT_LENGTH exceeded
    flash("Uploaded file too large.", "error")
    return redirect(url_for("register"))

# ------------- Main -------------
if __name__ == "__main__":
    # For local dev
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=True)
