# app.py
import os
import io
import csv
import datetime
from flask import (
    Flask, request, render_template, redirect, url_for,
    flash, session, send_file, abort
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from email_validator import validate_email, EmailNotValidError
from sqlalchemy.exc import ProgrammingError, OperationalError

# ------------------ Config ------------------
app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = os.getenv("SECRET_KEY", "supersecretkey")  # set SECRET_KEY in environment in production

# ------------------ Database Configuration ------------------
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    app.logger.warning("⚠️ DATABASE_URL not found, using local SQLite fallback.")
    DATABASE_URL = "sqlite:///database.db"

# Some providers give DATABASE_URL starting with postgres:// which SQLAlchemy dislikes
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Uploads config
UPLOAD_FOLDER = os.path.join(app.static_folder, "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024  # 20 MB limit

ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "webp"}

db = SQLAlchemy(app)


# ------------------ Models ------------------
class Team(db.Model):
    __tablename__ = "teams"
    id = db.Column(db.Integer, primary_key=True)
    team_name = db.Column(db.String(200), nullable=False)
    leader_name = db.Column(db.String(200), nullable=False)
    leader_email = db.Column(db.String(200), nullable=False, index=True)
    leader_phone = db.Column(db.String(50), nullable=False)
    leader_company = db.Column(db.String(200), nullable=True)
    team_size = db.Column(db.Integer, nullable=False, default=3)
    abstract_path = db.Column(db.String(500), nullable=True)
    payment_path = db.Column(db.String(500), nullable=True)
    transaction_id = db.Column(db.String(120), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    status = db.Column(db.String(50), default="submitted")


# ------------------ Helpers ------------------
def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def ensure_tables():
    """Create tables if they don't exist."""
    with app.app_context():
        try:
            db.create_all()
        except Exception as e:
            app.logger.exception("Failed to create DB tables: %s", e)


# ------------------ Routes ------------------
@app.route("/")
def home():
    # render home.html (you said you'll switch to home.html)
    return render_template("home.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        try:
            # basic form fields (make sure your form uses these field names)
            team_name = request.form.get("team_name", "").strip()
            leader_name = request.form.get("leader_name", "").strip()
            leader_email = request.form.get("leader_email", "").strip()
            leader_phone = request.form.get("leader_phone", "").strip()
            leader_company = request.form.get("leader_company", "").strip()
            team_size = int(request.form.get("team_size", 3))
            transaction_id = request.form.get("transaction_id", "").strip()

            # validate required
            if not (team_name and leader_name and leader_email and leader_phone):
                flash("Please fill in all required fields.", "error")
                return redirect(url_for("register"))

            # Email validation
            try:
                validate_email(leader_email)
            except EmailNotValidError:
                flash("Invalid email address.", "error")
                return redirect(url_for("register"))

            # File uploads
            abstract_file = request.files.get("abstract")
            payment_photo = request.files.get("transaction_photo")

            abstract_rel = None
            payment_rel = None

            # Save abstract (optional but recommended)
            if abstract_file and abstract_file.filename:
                if not allowed_file(abstract_file.filename):
                    flash("Abstract file type not allowed. Use PDF (or allowed images).", "error")
                    return redirect(url_for("register"))
                safe_name = secure_filename(f"{team_name}_abstract.{abstract_file.filename.rsplit('.',1)[1]}")
                abs_path = os.path.join(app.config["UPLOAD_FOLDER"], safe_name)
                abstract_file.save(abs_path)
                abstract_rel = f"uploads/{safe_name}"

            # Save payment image (optional)
            if payment_photo and payment_photo.filename:
                if not allowed_file(payment_photo.filename):
                    flash("Payment file type not allowed. Use JPG/PNG.", "error")
                    return redirect(url_for("register"))
                safe_name = secure_filename(f"{team_name}_payment.{payment_photo.filename.rsplit('.',1)[1]}")
                pay_path = os.path.join(app.config["UPLOAD_FOLDER"], safe_name)
                payment_photo.save(pay_path)
                payment_rel = f"uploads/{safe_name}"

            # Save into DB
            team = Team(
                team_name=team_name,
                leader_name=leader_name,
                leader_email=leader_email,
                leader_phone=leader_phone,
                leader_company=leader_company,
                team_size=team_size,
                transaction_id=transaction_id,
                abstract_path=abstract_rel,
                payment_path=payment_rel,
            )
            db.session.add(team)
            db.session.commit()

            flash("Registration successful! We'll review your abstract and confirm shortly.", "success")
            return redirect(url_for("registration_success"))

        except Exception as e:
            app.logger.exception("Registration error: %s", e)
            flash("An error occurred during registration. Please try again.", "error")
            return redirect(url_for("register"))

    return render_template("register.html")


@app.route("/registration_success")
def registration_success():
    return render_template("registration_success.html")


# ------------------ Admin Routes ------------------
@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    # Remains /admin_login per your preference
    if request.method == "POST":
        email = request.form.get("email", "")
        password = request.form.get("password", "")

        # change these credentials as required and store securely in env in production
        admin_email = os.getenv("ADMIN_EMAIL", "origin@stpetershyd.com")
        admin_pass = os.getenv("ADMIN_PASSWORD", "#C0re0r!g!n")

        if email == admin_email and password == admin_pass:
            session["admin"] = True
            return redirect(url_for("admin_dashboard"))
        else:
            flash("Invalid credentials", "error")
    return render_template("admin_login.html")


@app.route("/refresh")
def refresh():
    if not session.get("admin"):
        return redirect(url_for("admin_login"))
    return redirect(url_for("admin_dashboard"))


@app.route("/admin_dashboard")
def admin_dashboard():
    if not session.get("admin"):
        return redirect(url_for("admin_login"))

    try:
        teams = Team.query.order_by(Team.created_at.desc()).all()
    except (ProgrammingError, OperationalError) as e:
        # If tables don't exist or DB error, try creating tables and retry once
        app.logger.warning("DB access error when querying teams: %s — attempting to create tables and retry", e)
        ensure_tables()
        try:
            teams = Team.query.order_by(Team.created_at.desc()).all()
        except Exception as e2:
            app.logger.exception("Failed to query teams after create_all: %s", e2)
            flash("Database error. Admin dashboard temporarily unavailable.", "error")
            teams = []

    total = len(teams)
    return render_template("admin_dashboard.html", teams=teams, total=total)


@app.route("/download_csv")
def download_csv():
    if not session.get("admin"):
        abort(403)

    try:
        teams = Team.query.order_by(Team.created_at.desc()).all()
    except Exception:
        teams = []

    proxy = io.StringIO()
    writer = csv.writer(proxy)
    writer.writerow([
        "Team Name", "Leader Name", "Email", "Phone", "College",
        "Team Size", "Transaction ID", "Abstract Path", "Payment Path", "Created At"
    ])

    for t in teams:
        writer.writerow([
            t.team_name, t.leader_name, t.leader_email, t.leader_phone,
            t.leader_company or "", t.team_size, t.transaction_id or "",
            t.abstract_path or "", t.payment_path or "", t.created_at
        ])

    mem = io.BytesIO()
    mem.write(proxy.getvalue().encode("utf-8"))
    mem.seek(0)
    proxy.close()
    return send_file(
        mem,
        mimetype="text/csv",
        download_name="registrations.csv",
        as_attachment=True
    )


@app.route("/logout")
def logout():
    session.pop("admin", None)
    flash("Logged out successfully.", "success")
    return redirect(url_for("admin_login"))


# ------------------ Dev / Admin helpers ------------------
@app.route("/init_db")
def init_db():
    # Be careful: this only creates the tables (safe). Use DB migrations for production.
    with app.app_context():
        try:
            db.create_all()
            return "Database initialized successfully!"
        except Exception as e:
            app.logger.exception("init_db failed: %s", e)
            return f"Failed to initialize database: {e}", 500


# ------------------ Error handlers ------------------
@app.errorhandler(403)
def forbidden(e):
    return render_template("403.html") if os.path.exists(os.path.join(app.template_folder, "403.html")) else ("Forbidden", 403)


@app.errorhandler(404)
def not_found(e):
    return render_template("404.html") if os.path.exists(os.path.join(app.template_folder, "404.html")) else ("Not Found", 404)


@app.errorhandler(413)
def too_large(e):
    flash("Uploaded file is too large (max 20MB).", "error")
    return redirect(request.referrer or url_for("register"))


# ------------------ Start App ------------------
if __name__ == "__main__":
    # Create tables on startup to avoid race condition on first admin access
    ensure_tables()
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
