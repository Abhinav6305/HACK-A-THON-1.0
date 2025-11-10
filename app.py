import os
from datetime import datetime
from urllib.parse import urlparse
from flask import Flask, render_template, request, redirect, url_for, abort
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base, Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, DateTime, ForeignKey

# --- Flask setup ---
app = Flask(__name__, static_folder="static", template_folder="templates")
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev")
# Render's ephemeral disk: use /tmp for any temp uploads
app.config["UPLOAD_FOLDER"] = os.getenv("UPLOAD_FOLDER", "/tmp/uploads")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB

os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# --- Database setup (Render Postgres) ---
def _normalize_db_url(raw):
    # Render may give postgres:// — SQLAlchemy needs postgresql://
    if raw and raw.startswith("postgres://"):
        return raw.replace("postgres://", "postgresql://", 1)
    return raw

DB_URL = _normalize_db_url(os.getenv("DATABASE_URL"))
if not DB_URL:
    # allow local dev fallback to sqlite
    DB_URL = "sqlite:///local.db"

engine = create_engine(DB_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
Base = declarative_base()

# --- Models ---
class Team(Base):
    __tablename__ = "teams"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    team_name: Mapped[str] = mapped_column(String(120))
    leader_name: Mapped[str] = mapped_column(String(120))
    leader_email: Mapped[str] = mapped_column(String(120))
    leader_phone: Mapped[str] = mapped_column(String(32))
    leader_company: Mapped[str] = mapped_column(String(160))
    team_size: Mapped[int] = mapped_column(Integer)
    abstract_filename: Mapped[str] = mapped_column(String(200), default="")
    payment_screenshot_url: Mapped[str] = mapped_column(String(500), default="")  # store a link (Drive/OneDrive) or empty
    transaction_id: Mapped[str] = mapped_column(String(120), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    members = relationship("Member", back_populates="team", cascade="all, delete-orphan")

class Member(Base):
    __tablename__ = "members"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str] = mapped_column(String(32))
    company: Mapped[str] = mapped_column(String(160))
    team = relationship("Team", back_populates="members")

# Create tables automatically on first boot
with engine.begin() as conn:
    Base.metadata.create_all(conn)

# --- Routes ---
@app.route("/")
def home():
    return render_template("home.html")  # your existing home

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")  # your existing template
    # POST
    form = request.form
    size = int(form.get("team_size", "3") or 3)

    # optional file save (abstract PDF) → place on ephemeral /tmp so request doesn't crash
    abstract_file = request.files.get("abstract")
    abstract_path = ""
    if abstract_file and abstract_file.filename:
        abstract_path = os.path.join(app.config["UPLOAD_FOLDER"], f"{datetime.utcnow().timestamp()}_{abstract_file.filename}")
        abstract_file.save(abstract_path)

    # if you're using a cloud link for screenshot, capture it as text
    payment_url = form.get("transaction_photo_url", "").strip()  # <input name="transaction_photo_url"> on your form

    team = Team(
        team_name=form.get("team_name","").strip(),
        leader_name=form.get("leader_name","").strip(),
        leader_email=form.get("leader_email","").strip(),
        leader_phone=form.get("leader_phone","").strip(),
        leader_company=form.get("leader_company","").strip(),
        team_size=size,
        abstract_filename=os.path.basename(abstract_path) if abstract_path else "",
        transaction_id=form.get("transaction_id","").strip(),
        payment_screenshot_url=payment_url
    )
    # members
    for i in range(1, size):  # members apart from leader
        team.members.append(Member(
            name=form.get(f"member_{i}_name","").strip(),
            email=form.get(f"member_{i}_email","").strip(),
            phone=form.get(f"member_{i}_phone","").strip(),
            company=form.get(f"member_{i}_company","").strip(),
        ))

    db = SessionLocal()
    try:
        db.add(team)
        db.commit()
    except Exception as e:
        db.rollback()
        # log the error to stdout so Render logs show it
        print("REGISTER ERROR:", e, flush=True)
        abort(500)
    finally:
        db.close()

    return redirect(url_for("registration_success"))

@app.route("/registration_success")
def registration_success():
    return render_template("registration_success.html")

# exact path requested by you
@app.route("/admin_dashboard")
def admin_dashboard():
    db = SessionLocal()
    try:
        teams = db.query(Team).order_by(Team.created_at.desc()).all()
        # Shape data for your template
        data = []
        for t in teams:
            data.append({
                "team": t,
                "leader": {
                    "name": t.leader_name,
                    "email": t.leader_email,
                    "phone": t.leader_phone,
                    "company": t.leader_company,
                },
                "members": [{"name": m.name, "email": m.email, "phone": m.phone, "company": m.company} for m in t.members],
            })
    finally:
        db.close()
    return render_template("admin_dashboard.html", teams=data, registration_count=len(data))

# health check (useful on Render)
@app.route("/healthz")
def healthz():
    try:
        with engine.connect() as conn:
            conn.execute(text("select 1"))
        return "ok", 200
    except Exception as e:
        print("HEALTH ERROR:", e, flush=True)
        return "db error", 500

if __name__ == "__main__":
    app.run(debug=True)
