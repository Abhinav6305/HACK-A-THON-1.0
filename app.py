import os
import io
import csv
import datetime
from flask import (
    Flask, request, render_template, redirect, url_for,
    flash, session, send_file, abort
)
from flask_sqlalchemy import SQLAlchemy
from email_validator import validate_email, EmailNotValidError
from ai_reviewer import evaluate_abstract

# ------------------ App Config ------------------
app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = os.getenv("SECRET_KEY", "supersecretkey")

# ------------------ Database Config ------------------
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("⚠️ DATABASE_URL not found — using SQLite fallback.")
    DATABASE_URL = "sqlite:///database.db"

# PostgreSQL fix for Render
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ------------------ Database Model ------------------
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
    transaction_id = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    status = db.Column(db.String(50), default="submitted")
    abstract_score = db.Column(db.Integer, nullable=True)

# ------------------ Routes ------------------

@app.route("/")
def home():
    return render_template("home.html")


# ------------------ Register ------------------

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        try:
            team_name = request.form["team_name"]
            leader_name = request.form["leader_name"]
            leader_email = request.form["leader_email"]
            leader_phone = request.form["leader_phone"]
            leader_company = request.form["leader_company"]
            team_size = int(request.form["team_size"])
            transaction_id = request.form["transaction_id"]

            # Email validation
            try:
                validate_email(leader_email)
            except EmailNotValidError:
                flash("Invalid email address.", "error")
                return redirect(url_for("register"))

            # File uploads
            abstract_file = request.files["abstract"]
            payment_photo = request.files["transaction_photo"]

            upload_folder = os.path.join(app.static_folder, "uploads")
            os.makedirs(upload_folder, exist_ok=True)

            abstract_filename = f"{team_name}_abstract.pdf"
            payment_filename = f"{team_name}_payment.jpg"

            abstract_path = os.path.join(upload_folder, abstract_filename)
            payment_path = os.path.join(upload_folder, payment_filename)

            abstract_file.save(abstract_path)
            payment_photo.save(payment_path)

            abstract_rel = f"uploads/{abstract_filename}"
            payment_rel = f"uploads/{payment_filename}"

            # Save to DB
            team = Team(
                team_name=team_name,
                leader_name=leader_name,
                leader_email=leader_email,
                leader_phone=leader_phone,
                leader_company=leader_company,
                team_size=team_size,
                transaction_id=transaction_id,
                abstract_path=abstract_rel,
                payment_path=payment_rel
            )
            db.session.add(team)
            db.session.commit()

            # AI abstract evaluation
            try:
                with open(os.path.join("static", abstract_rel), "rb") as f:
                    text = f.read().decode("utf-8", errors="ignore")
                    team.abstract_score = evaluate_abstract(text)
                    db.session.commit()
            except Exception as e:
                print("AI evaluation failed:", e)

            flash("Registration successful!", "success")
            return redirect(url_for("registration_success"))

        except Exception as e:
            print("Registration error:", e)
            flash("An error occurred during registration. Please try again.", "error")
            return redirect(url_for("register"))

    return render_template("register.html")


@app.route("/registration_success")
def registration_success():
    return render_template("registration_success.html")


# ------------------ Admin ------------------

@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        if email == "origin@stpetershyd.com" and password == "#C0re0r!g!n":
            session["admin"] = True
            return redirect(url_for("admin_dashboard"))
        else:
            flash("Invalid credentials", "error")

    return render_template("admin_login.html")


@app.route("/admin_dashboard")
def admin_dashboard():
    if not session.get("admin"):
        return redirect(url_for("admin_login"))

    # FIX: If table doesn’t exist, create it
    try:
        teams = Team.query.order_by(Team.created_at.desc()).all()
    except Exception as e:
        print("Teams table missing — creating...")
        with app.app_context():
            db.create_all()
        teams = []

    total = len(teams)
    return render_template("admin_dashboard.html", teams=teams, total=total)


@app.route("/download_csv")
def download_csv():
    if not session.get("admin"):
        abort(403)

    teams = Team.query.all()

    proxy = io.StringIO()
    writer = csv.writer(proxy)
    writer.writerow([
        "Team Name", "Leader Name", "Email", "Phone", "College",
        "Team Size", "Transaction ID", "Abstract Path", "Payment Path", "Score", "Created At"
    ])

    for t in teams:
        writer.writerow([
            t.team_name, t.leader_name, t.leader_email, t.leader_phone,
            t.leader_company, t.team_size, t.transaction_id,
            t.abstract_path, t.payment_path, t.abstract_score, t.created_at
        ])

    mem = io.BytesIO(proxy.getvalue().encode("utf-8"))
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


# ------------------ Main ------------------

if __name__ == "__main__":
    with app.app_context():
        try:
            db.create_all()
            print("Database tables ensured.")
        except Exception as e:
            print("DB init error:", e)

    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
