import os
from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.utils import secure_filename
from huggingface_hub import InferenceClient

app = Flask(__name__)
app.secret_key = "supersecretkey123"

# DATABASE CONFIG
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# -------------------------------
# DATABASE MODEL
# -------------------------------
class Team(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    team_name = db.Column(db.String(200), nullable=False)
    leader_name = db.Column(db.String(200), nullable=False)
    leader_email = db.Column(db.String(200), nullable=False)
    leader_phone = db.Column(db.String(20), nullable=False)
    leader_company = db.Column(db.String(200), nullable=True)
    team_size = db.Column(db.Integer, nullable=False)

    abstract_path = db.Column(db.String(300))
    payment_path = db.Column(db.String(300))
    transaction_id = db.Column(db.String(200))

    abstract_score = db.Column(db.Float, default=0)
    status = db.Column(db.String(50), default="Pending")

    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# -------------------------------
# ADMIN LOGIN PAGE
# -------------------------------
@app.route("/admin", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if username == "admin" and password == "admin123":
            session["admin"] = True
            return redirect(url_for("admin_dashboard"))
        else:
            return render_template("admin_login.html", error="Invalid credentials")

    return render_template("admin_login.html")


# -------------------------------
# ADMIN DASHBOARD
# -------------------------------
@app.route("/admin_dashboard")
def admin_dashboard():
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    teams = Team.query.order_by(Team.created_at.desc()).all()
    total = Team.query.count()

    return render_template("admin_dashboard.html", teams=teams, total=total)


# -------------------------------
# USER REGISTRATION
# -------------------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":

        # Save files
        abstract_file = request.files["abstract"]
        payment_file = request.files["payment"]

        abstract_filename = secure_filename(abstract_file.filename)
        payment_filename = secure_filename(payment_file.filename)

        abstract_path = os.path.join("uploads", abstract_filename)
        payment_path = os.path.join("uploads", payment_filename)

        abstract_file.save(abstract_path)
        payment_file.save(payment_path)

        # Save to DB
        team = Team(
            team_name=request.form["team_name"],
            leader_name=request.form["leader_name"],
            leader_email=request.form["leader_email"],
            leader_phone=request.form["leader_phone"],
            leader_company=request.form["leader_company"],
            team_size=request.form["team_size"],
            abstract_path=abstract_path,
            payment_path=payment_path,
            transaction_id=request.form["transaction_id"]
        )

        db.session.add(team)
        db.session.commit()

        return redirect(url_for("registration_success"))

    return render_template("register.html")


@app.route("/registration_success")
def registration_success():
    return render_template("registration_success.html")


# -------------------------------
# AI EVALUATION USING HUGGINGFACE
# -------------------------------
@app.route("/evaluate/<int:team_id>")
def evaluate(team_id):
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    team = Team.query.get_or_404(team_id)

    # Read the abstract file
    with open(team.abstract_path, "r", errors="ignore") as f:
        abstract_text = f.read()

    # HuggingFace inference
    HF_TOKEN = os.getenv("HF_TOKEN")
    client = InferenceClient(api_key=HF_TOKEN, model="google/gemma-2-9b-it")

    prompt = f"Evaluate this project abstract on a scale of 1 to 10:\n\n{abstract_text}"

    response = client.text_generation(
        prompt,
        max_new_tokens=30,
        temperature=0.3
    )

    try:
        score = float(response.strip().split()[0])
    except:
        score = 5.0

    team.abstract_score = score
    db.session.commit()

    return redirect(url_for("admin_dashboard"))


# -------------------------------
# TEMP ROUTE TO CREATE TABLES
# DELETE AFTER ONE USE
# -------------------------------
@app.route("/init_db")
def init_db():
    try:
        db.create_all()
        return "Database tables created successfully!"
    except Exception as e:
        return str(e)


# -------------------------------
# HOME PAGE
# -------------------------------
@app.route("/")
def home():
    return render_template("home.html")


# -------------------------------
# MAIN
# -------------------------------
if __name__ == "__main__":
    app.run()
