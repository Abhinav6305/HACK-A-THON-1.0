# app.py
import os
import io
import csv
import datetime
import re
from werkzeug.utils import secure_filename
from flask import (
    Flask, request, render_template, redirect, url_for,
    flash, session, send_file, abort, current_app
)
from flask_sqlalchemy import SQLAlchemy

# ------------------ Minimal / defensive AI import ------------------
# We intentionally don't `from ai_reviewer import evaluate_abstract` at top-level
# because transformers/torch are heavy and cause memory/time issues on small hosts.
# We'll try a lazy import only when needed, and allow disabling via env var.
def get_ai_reviewer():
    """Try to import evaluate_abstract lazily. Return None if unavailable."""
    if os.getenv("ENABLE_AI", "true").lower() in ("0", "false", "no"):
        return None
    try:
        from ai_reviewer import evaluate_abstract
        return evaluate_abstract
    except Exception as e:
        # fail gracefully, log to console
        print("AI reviewer unavailable:", e)
        return None

# ------------------ Flask app ------------------
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

app = Flask(__name__, template_folder=TEMPLATES_DIR, static_folder=STATIC_DIR)
app.secret_key = os.getenv("SECRET_KEY", "super-secret-key-change-me")

# ------------------ Database config (safe fallback) ------------------
DATABASE_URL = os.getenv("DATABASE_URL", "").strip() or None
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# If DATABASE_URL references postgres but psycopg2 import fails (common on mismatched Python),
# fallback to a local sqlite file so the app still runs.
def _choose_database_url(candidate):
    if not candidate:
        return "sqlite:///" + os.path.join(BASE_DIR, "app.db")
    if candidate.startswith("postgres") or "postgresql" in candidate:
        try:
            import psycopg2  # just to test availability
            return candidate
        except Exception as e:
            print("WARNING: psycopg2 not available or incompatible:", e)
            print("Falling back to local sqlite database to avoid import errors.")
            return "sqlite:///" + os.path.join(BASE_DIR, "app.db")
    return candidate

DATABASE_URL = _choose_database_url(DATABASE_URL)
app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
# hard cap on uploads (20MB)
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024

db = SQLAlchemy(app)

# ------------------ Upload folders ------------------
ABSTRACT_DIR = os.path.join(STATIC_DIR, "uploads", "abstracts")
PAYMENT_DIR = os.path.join(STATIC_DIR, "uploads", "payments")
os.makedirs(ABSTRACT_DIR, exist_ok=True)
os.makedirs(PAYMENT_DIR, exist_ok=True)

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
    status        = db.Column(db.String(50), default="submitted")

    # NEW: abstract score saved by ai_reviewer (nullable)
    abstract_score = db.Column(db.Integer, nullable=True)

# simple Member model if you keep members table (optional earlier)
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
    rel = os.path.relpath(abs_path, STATIC_DIR).replace("\\", "/")
    return rel

def _file_len(file_storage):
    # read length safely
    file_storage.stream.seek(0, 2)
    size = file_storage.stream.tell()
    file_storage.stream.seek(0)
    return size

def _validate_email_simple(email: str) -> bool:
    # avoid extra dependency in critical path; small regex for sanity
    pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    return bool(re.match(pattern, email or ""))

# ------------------ Routes ------------------
@app.before_request
def ensure_db():
    # create tables lazily for dev (harmless if they exist)
    try:
        db.create_all()
    except Exception as e:
        # log but don't crash the server on every request
        print("DB create_all warning:", e)

@app.route("/")
def home():
    # your template file is `home.html` in templates/ — use that consistently.
    return render_template("home.html")

# Registration endpoint
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

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

    if not _validate_email_simple(leader_email):
        flash("Please enter a valid email address.", "error")
        return redirect(url_for("register"))

    try:
        team_size = int(team_size_raw)
    except ValueError:
        team_size = 0
    if team_size not in (3,4,5):
        flash("Team size must be 3, 4, or 5.", "error")
        return redirect(url_for("register"))

    if not transaction_id:
        flash("Transaction ID is required.", "error")
        return redirect(url_for("register"))

    # files
    abstract = files.get("abstract")
    payment  = files.get("transaction_photo")

    if not abstract or not abstract.filename:
        flash("Abstract PDF is required.", "error")
        return redirect(url_for("register"))
    if not _ext_ok(abstract.filename, ALLOWED_ABSTRACT):
        flash("Abstract must be a .pdf file.", "error")
        return redirect(url_for("register"))
    if _file_len(abstract) > 10 * 1024 * 1024:
        flash("Abstract file exceeds 10MB limit.", "error")
        return redirect(url_for("register"))

    if not payment or not payment.filename:
        flash("Payment screenshot is required.", "error")
        return redirect(url_for("register"))
    if not _ext_ok(payment.filename, ALLOWED_IMAGES):
        flash("Payment screenshot must be an image.", "error")
        return redirect(url_for("register"))
    if _file_len(payment) > 10 * 1024 * 1024:
        flash("Payment screenshot exceeds 10MB limit.", "error")
        return redirect(url_for("register"))

    # create team and members
    team = Team(
        team_name=team_name,
        leader_name=leader_name,
        leader_email=leader_email,
        leader_phone=leader_phone,
        leader_company=leader_company,
        team_size=team_size,
        transaction_id=transaction_id,
    )

    # members (member_1..)
    max_members = team_size - 1
    for i in range(1, max_members+1):
        m_name = (form.get(f"member_{i}_name") or "").strip()
        m_email = (form.get(f"member_{i}_email") or "").strip()
        m_phone = (form.get(f"member_{i}_phone") or "").strip()
        m_comp = (form.get(f"member_{i}_company") or "").strip()
        if not (m_name and m_email and m_phone and m_comp):
            flash(f"Please fill all fields for Member {i}.", "error")
            return redirect(url_for("register"))
        if not _validate_email_simple(m_email):
            flash(f"Member {i} email is invalid.", "error")
            return redirect(url_for("register"))
        team.members.append(Member(name=m_name, email=m_email, phone=m_phone, company=m_comp))

    # save files safely
    try:
        abstract_rel = _save_file(abstract, ABSTRACT_DIR)
        payment_rel  = _save_file(payment, PAYMENT_DIR)
        team.abstract_path = abstract_rel
        team.payment_path = payment_rel

        db.session.add(team)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print("Error saving registration:", e)
        flash("Server error while saving your registration. Please try again.", "error")
        return redirect(url_for("register"))

    # AI scoring (lazy, optional)
    evaluate_fn = get_ai_reviewer()
    if evaluate_fn:
        try:
            # read small piece (avoid huge reads); provide text for model
            abs_file_path = os.path.join(STATIC_DIR, abstract_rel)
            with open(abs_file_path, "rb") as f:
                raw = f.read()
            # best-effort decode; if pdf, may be binary text; still attempt
            text = raw.decode("utf-8", errors="ignore")
            score = evaluate_fn(text[:8192])  # pass a reasonable slice
            try:
                team.abstract_score = int(score)
            except Exception:
                team.abstract_score = None
            db.session.commit()
        except Exception as e:
            print("AI evaluation failed (non-fatal):", e)

    flash("Registration successful!", "success")
    return redirect(url_for("registration_success"))

@app.route("/registration_success")
def registration_success():
    return render_template("registration_success.html")

# ----- admin -----
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "origin@stpetershyd.com")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "#C0re0r!g!n")

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

@app.route("/admin/dashboard")
def admin_dashboard():
    if not session.get("admin"):
        return redirect(url_for("admin_login"))
    teams = Team.query.order_by(Team.created_at.desc()).all()
    count = Team.query.count()
    return render_template("admin_dashboard.html", teams=teams, total=count, registration_count=count)

@app.route("/admin/download_csv")
def download_csv():
    if not session.get("admin"):
        abort(403)
    si = io.StringIO()
    writer = csv.writer(si)
    writer.writerow([
        "Team Name", "Leader Name", "Leader Email", "Leader Phone", "Leader Company",
        "Team Size", "Transaction ID", "Abstract Path", "Payment Path", "AI Score", "Submitted At (UTC)"
    ])
    for t in Team.query.order_by(Team.created_at.desc()).all():
        writer.writerow([
            t.team_name, t.leader_name, t.leader_email, t.leader_phone, t.leader_company,
            t.team_size, t.transaction_id, (t.abstract_path or ""), (t.payment_path or ""),
            (t.abstract_score if t.abstract_score is not None else ""), t.created_at
        ])
    mem = io.BytesIO()
    mem.write(si.getvalue().encode("utf-8"))
    mem.seek(0)
    return send_file(mem, mimetype="text/csv", as_attachment=True, download_name="registrations.csv")

@app.route("/admin/logout")
def admin_logout():
    session.pop("admin", None)
    flash("Logged out", "success")
    return redirect(url_for("admin_login"))

# error handlers
@app.errorhandler(413)
def too_large(_):
    flash("Uploaded file too large.", "error")
    return redirect(url_for("register"))

# ------------------ Run ------------------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=True)
