from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)

# Get Postgres DB from environment
DATABASE_URL = os.getenv("DATABASE_URL")

# Fix for postgres:// → postgresql:// (SQLAlchemy requirement)
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

if DATABASE_URL:
    app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
else:
    # Fallback to SQLite for local development
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# Registration Model
class Registration(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    team_name = db.Column(db.String(200))
    leader_name = db.Column(db.String(200))
    leader_email = db.Column(db.String(200))
    leader_phone = db.Column(db.String(200))
    college = db.Column(db.String(300))
    team_size = db.Column(db.Integer)
    transaction_id = db.Column(db.String(200))

# Create tables ONCE after deployment
with app.app_context():
    db.create_all()

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        data = Registration(
            team_name=request.form.get("team_name"),
            leader_name=request.form.get("leader_name"),
            leader_email=request.form.get("leader_email"),
            leader_phone=request.form.get("leader_phone"),
            college=request.form.get("leader_company"),
            team_size=request.form.get("team_size"),
            transaction_id=request.form.get("transaction_id")
        )
        db.session.add(data)
        db.session.commit()
        return redirect(url_for("home"))
    return render_template("register.html")

# Admin Dashboard
@app.route("/admin")
def admin():
    registrations = Registration.query.all()
    return render_template("admin.html", registrations=registrations)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
