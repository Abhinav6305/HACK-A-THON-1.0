import os
import csv
from datetime import datetime
from pathlib import Path

from flask import (
    Flask, render_template, request, redirect, url_for,
    send_file, flash
)
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.utils import secure_filename

from sqlalchemy import (
    create_engine, Column, Integer, String, DateTime
)
from sqlalchemy.orm import sessionmaker, declarative_base, scoped_session

# Cloudinary for file persistence
import cloudinary
import cloudinary.uploader

# Configure Cloudinary (set these in Render env vars)
cloudinary.config(
    cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"),
    api_key=os.environ.get("CLOUDINARY_API_KEY"),
    api_secret=os.environ.get("CLOUDINARY_API_SECRET")
)

# ----------------------------
# Flask + Config
# ----------------------------
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret")

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "static" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_PDF = {"pdf"}
ALLOWED_IMG = {"png", "jpg", "jpeg", "webp", "gif"}

# File size limit: 10MB
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024

# ----------------------------
# Database (Render Postgres -> local SQLite fallback)
# ----------------------------
db_url = os.environ.get("DATABASE_URL")
if db_url:
    # Render/Heroku style needs fix: postgres:// -> postgresql+psycopg2://
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql+psycopg2://", 1)
else:
    db_url = f"sqlite:///{BASE_DIR/'registrations.db'}"

engine = create_engine(db_url, pool_pre_ping=True)
SessionLocal = scoped_session(sessionmaker(bind=engine))
Base = declarative_base()

# ----------------------------
# Models
# ----------------------------
class Team(Base):
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True)
    team_name = Column(String(200), nullable=False)
    leader_name = Column(String(200), nullable=False)
    leader_email = Column(String(200), nullable=False)
    leader_phone = Column(String(50), nullable=False)
    leader_company = Column(String(200), nullable=False)

    team_size = Column(Integer, nullable=False, default=3)

    # uploaded file URLs from Cloudinary
    abstract_url = Column(String(500))
    payment_url = Column(String(500))

    transaction_id = Column(String(120))
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(engine)

# ----------------------------
# Helpers
# ----------------------------
def _allowed(filename, allowed_set):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_set

def _save_upload(file_storage, prefix):
    """
    Save uploaded file to Cloudinary for persistence.
    Returns public URL from Cloudinary.
    """
    if not file_storage:
        return None
    filename = secure_filename(file_storage.filename or "")
    if not filename:
        return None

    try:
        # Upload to Cloudinary
        result = cloudinary.uploader.upload(
            file_storage,
            public_id=f"{prefix}_{int(datetime.utcnow().timestamp())}",
            resource_type="auto"
        )
        return result['secure_url']
    except Exception:
        app.logger.exception("Cloudinary upload failed")
        return None

# ----------------------------
# Error Handlers
# ----------------------------
@app.errorhandler(RequestEntityTooLarge)
def handle_file_too_large(e):
    return "File too large. Maximum 10 MB allowed.", 413

# ----------------------------
# Routes
# ----------------------------
@app.route("/")
def home():
    return render_template("home.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    # --- POST: create a team record
    form = request.form
    files = request.files

    # Required leader fields
    team_name = form.get("team_name", "").strip()
    leader_name = form.get("leader_name", "").strip()
    leader_email = form.get("leader_email", "").strip()
    leader_phone = form.get("leader_phone", "").strip()
    leader_company = form.get("leader_company", "").strip()
    team_size = int(form.get("team_size", "3") or 3)

    # Validate minimal fields
    if not all([team_name, leader_name, leader_email, leader_phone, leader_company]):
        flash("Please fill all required fields.", "error")
        return redirect(url_for("register"))

    # Files
    abstract_file = files.get("abstract")
    pay_file = files.get("transaction_photo")
    transaction_id = form.get("transaction_id", "").strip()

    # Validate file types and upload to Cloudinary
    abstract_url = None
    if abstract_file and _allowed(abstract_file.filename, ALLOWED_PDF):
        abstract_url = _save_upload(abstract_file, prefix="abstract")
    elif abstract_file:
        flash("Abstract must be a .pdf file", "error")
        return redirect(url_for("register"))

    payment_url = None
    if pay_file and _allowed(pay_file.filename, ALLOWED_IMG):
        payment_url = _save_upload(pay_file, prefix="payment")
    elif pay_file:
        flash("Payment screenshot must be an image", "error")
        return redirect(url_for("register"))

    # Persist to DB
    db = SessionLocal()
    try:
        team = Team(
            team_name=team_name,
            leader_name=leader_name,
            leader_email=leader_email,
            leader_phone=leader_phone,
            leader_company=leader_company,
            team_size=team_size,
            abstract_url=abstract_url,
            payment_url=payment_url,
            transaction_id=transaction_id
        )
        db.add(team)
        db.commit()
        flash("Registration successful!", "success")
        return redirect(url_for("registration_success"))
    except Exception:
        db.rollback()
        app.logger.exception("Registration error")
        flash("Something went wrong while saving. Please try again.", "error")
        return redirect(url_for("register"))
    finally:
        db.close()

@app.route("/registration_success")
def registration_success():
    return render_template("registration_success.html")

@app.route("/admin_dashboard")
def admin_dashboard():
    db = SessionLocal()
    try:
        teams = db.query(Team).order_by(Team.created_at.desc()).all()
        total = db.query(Team).count()
        return render_template("admin_dashboard.html", teams=teams, total=total)
    finally:
        db.close()

@app.route("/download_csv")
def download_csv():
    """Download all registrations as CSV."""
    db = SessionLocal()
    try:
        teams = db.query(Team).order_by(Team.created_at.desc()).all()
    finally:
        db.close()

    tmp = BASE_DIR / "registrations_export.csv"
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "Team Name", "Leader Name", "Leader Email", "Leader Phone",
            "College/Company", "Team Size", "Transaction ID",
            "Abstract URL", "Payment Screenshot URL", "Registered At (UTC)"
        ])
        for t in teams:
            w.writerow([
                t.team_name, t.leader_name, t.leader_email, t.leader_phone,
                t.leader_company, t.team_size, t.transaction_id,
                t.abstract_url or "", t.payment_url or "", t.created_at.isoformat()
            ])

    return send_file(tmp, as_attachment=True, download_name="registrations.csv")

@app.route("/refresh")
def refresh():
    return redirect(url_for("admin_dashboard"))

# ----------------------------
# Render needs this
# ----------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
