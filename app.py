import os, io, csv, datetime, re
from flask import Flask, request, render_template, redirect, url_for, flash, session, send_file, jsonify, abort
from flask_sqlalchemy import SQLAlchemy
from email_validator import validate_email, EmailNotValidError
from ai_reviewer import evaluate_abstract  # 🤖 AI evaluation

# ------------------ Config ------------------
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "hackathon_secret_key")

# Database setup
db_url = os.getenv("DATABASE_URL", "sqlite:///database.db")
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ------------------ Database Models ------------------
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
    abstract_score = db.Column(db.Integer, nullable=True)  # 🧠 AI score field


# ------------------ Helpers ------------------
def allowed_file(filename, exts):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in exts


# ------------------ Routes ------------------
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        try:
            team_name = request.form["team_name"].strip()
            leader_name = request.form["leader_name"].strip()
            leader_email = request.form["leader_email"].strip()
            leader_phone = request.form["leader_phone"].strip()
            leader_company = request.form["leader_company"].strip()
            team_size = int(request.form["team_size"])
            transaction_id = request.form["transaction_id"].strip()

            # Validate email
            validate_email(leader_email)

            # Save abstract PDF
            abstract_file = request.files.get("abstract")
            abstract_rel, abs_path = None, None
            if abstract_file and allowed_file(abstract_file.filename, {"pdf"}):
                abs_filename = f"{team_name}_abstract.pdf"
                abs_path = os.path.join("static/uploads/abstracts", abs_filename)
                os.makedirs(os.path.dirname(abs_path), exist_ok=True)
                abstract_file.save(abs_path)
                abstract_rel = f"uploads/abstracts/{abs_filename}"

            # Save payment screenshot
            txn_file = request.files.get("transaction_photo")
            txn_rel = None
            if txn_file and allowed_file(txn_file.filename, {"png", "jpg", "jpeg"}):
                txn_filename = f"{team_name}_txn.png"
                txn_path = os.path.join("static/uploads/payments", txn_filename)
                os.makedirs(os.path.dirname(txn_path), exist_ok=True)
                txn_file.save(txn_path)
                txn_rel = f"uploads/payments/{txn_filename}"

            # Create team entry
            team = Team(
                team_name=team_name,
                leader_name=leader_name,
                leader_email=leader_email,
                leader_phone=leader_phone,
                leader_company=leader_company,
                team_size=team_size,
                abstract_path=abstract_rel,
                payment_path=txn_rel,
                transaction_id=transaction_id,
            )

            db.session.add(team)
            db.session.commit()

            # ------------------ AI Abstract Evaluation ------------------
            if abs_path:
                with open(abs_path, "rb") as f:
                    text = f.read().decode("utf-8", errors="ignore")
                score = evaluate_abstract(text)
                team.abstract_score = score
                db.session.commit()

            flash("Registration successful!", "success")
            return redirect(url_for("registration_success"))

        except EmailNotValidError:
            flash("Invalid email address. Please check again.", "danger")
        except Exception as e:
            print("❌ Error during registration:", e)
            flash("Registration failed. Please try again.", "danger")

    return render_template("register.html")


@app.route("/registration_success")
def registration_success():
    return render_template("success.html")


# ------------------ Admin Login ------------------
@app.route("/admin", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        if email == "origin@stpetershyd.com" and password == "#C0re0r!g!n":
            session["admin"] = True
            return redirect(url_for("admin_dashboard"))
        else:
            flash("Invalid credentials", "danger")

    return render_template("admin_login.html")


# ------------------ Admin Dashboard ------------------
@app.route("/admin_dashboard")
def admin_dashboard():
    if not session.get("admin"):
        return redirect(url_for("admin_login"))
    teams = Team.query.order_by(Team.created_at.desc()).all()
    return render_template("admin_dashboard.html", teams=teams)


# ------------------ Download CSV ------------------
@app.route("/download_csv")
def download_csv():
    if not session.get("admin"):
        abort(403)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Team Name", "Leader", "Email", "Phone", "College", "Transaction ID", "Abstract Score", "Submitted On"])

    for t in Team.query.all():
        writer.writerow([t.team_name, t.leader_name, t.leader_email, t.leader_phone, t.leader_company, t.transaction_id, t.abstract_score or "-", t.created_at])

    output.seek(0)
    return send_file(io.BytesIO(output.getvalue().encode()), mimetype="text/csv", as_attachment=True, download_name="registrations.csv")


# ------------------ Run App ------------------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=True)
