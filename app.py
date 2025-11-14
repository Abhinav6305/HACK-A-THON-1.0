import os
from flask import Flask, render_template, request, redirect, url_for, send_file, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "supersecretkey"

# ============================================================
# 🟦 Persistent SQLite Database (Render survives restart)
# ============================================================
DB_PATH = "/data/registrations.db"      # Persistent directory
os.makedirs("/data", exist_ok=True)     # Ensure directory exists

app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_PATH}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ============================================================
# 🟦 Database Model
# ============================================================
class Registration(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    team_name = db.Column(db.String(100))
    leader_name = db.Column(db.String(100))
    leader_email = db.Column(db.String(100))
    leader_phone = db.Column(db.String(20))
    leader_company = db.Column(db.String(200))

    team_size = db.Column(db.Integer)

    # Members stored as a simple combined text (easy + flexible)
    members = db.Column(db.Text)

    abstract_path = db.Column(db.String(200))
    agree_terms = db.Column(db.Boolean, default=False)

# Create DB if not exists
with app.app_context():
    db.create_all()

# ============================================================
# 🟦 ROUTES
# ============================================================

@app.route("/")
def home():
    return render_template("home.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":

        team_name = request.form.get("team_name")
        leader_name = request.form.get("leader_name")
        leader_email = request.form.get("leader_email")
        leader_phone = request.form.get("leader_phone")
        leader_company = request.form.get("leader_company")
        team_size = int(request.form.get("team_size"))
        agree_terms = request.form.get("agree_terms") == "on"

        # Collect members dynamically
        members_list = []
        for i in range(1, team_size):
            members_list.append({
                "name": request.form.get(f"member_{i}_name"),
                "email": request.form.get(f"member_{i}_email"),
                "phone": request.form.get(f"member_{i}_phone"),
                "company": request.form.get(f"member_{i}_company")
            })

        # Abstract file
        abstract_file = request.files["abstract"]
        abstract_filename = secure_filename(abstract_file.filename)

        upload_folder = "uploads"
        os.makedirs(upload_folder, exist_ok=True)

        abstract_path = os.path.join(upload_folder, abstract_filename)
        abstract_file.save(abstract_path)

        registration = Registration(
            team_name=team_name,
            leader_name=leader_name,
            leader_email=leader_email,
            leader_phone=leader_phone,
            leader_company=leader_company,
            team_size=team_size,
            members=str(members_list),
            abstract_path=abstract_path,
            agree_terms=agree_terms
        )

        db.session.add(registration)
        db.session.commit()

        return redirect(url_for("registration_success"))

    return render_template("register.html")


@app.route("/registration_success")
def registration_success():
    return render_template("registration_success.html")


# ============================================================
# 🟦 ADMIN LOGIN
# ============================================================
ADMIN_EMAIL = "admin@origin.com"
ADMIN_PASSWORD = "admin123"

@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
            session["admin_logged_in"] = True
            return redirect(url_for("admin_dashboard"))

        flash("Invalid admin credentials", "error")

    return render_template("admin_login.html")


# ============================================================
# 🟦 ADMIN DASHBOARD
# ============================================================
@app.route("/admin_dashboard")
def admin_dashboard():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    registrations = Registration.query.all()
    total = len(registrations)

    return render_template("admin_dashboard.html",
                           registrations=registrations,
                           total=total)


# ============================================================
# 🟦 DOWNLOAD CSV EXPORT
# ============================================================
@app.route("/download_csv")
def download_csv():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    filepath = "registrations_export.csv"

    with open(filepath, "w") as f:
        f.write("Team Name,Leader Name,Leader Email,Leader Phone,Team Size,Members,Abstract\n")
        for r in Registration.query.all():
            f.write(f"{r.team_name},{r.leader_name},{r.leader_email},"
                    f"{r.leader_phone},{r.team_size},"
                    f"\"{r.members}\",{r.abstract_path}\n")

    return send_file(filepath, as_attachment=True)


# ============================================================
# 🟦 LOGOUT
# ============================================================
@app.route("/logout")
def logout():
    session.pop("admin_logged_in", None)
    return redirect(url_for("admin_login"))


# ============================================================
# RUN
# ============================================================
if __name__ == "__main__":
    app.run(debug=True)
