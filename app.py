from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
from models import db, User, Team, Submission, Evaluation
from ai_reviewer import ai_review
from onedrive_services import upload_to_onedrive
import os
from werkzeug.utils import secure_filename
import pandas as pd
from datetime import datetime
import json
import functools

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
db.init_app(app)

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Add default admin user
with app.app_context():
    db.create_all()
    # Create admin user if not exists
    admin = User.query.filter_by(email='admin@example.com').first()
    if not admin:
        admin = User(name='Admin', email='admin@example.com', role='admin')
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()

    # Create additional admin user
    admin2 = User.query.filter_by(email='abhinavrishisaka@gmail.com').first()
    if not admin2:
        admin2 = User(name='Abhinav', email='abhinavrishisaka@gmail.com', role='admin')
        admin2.set_password('Aishnav@6305')
        db.session.add(admin2)
        db.session.commit()

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            team_name = request.form['team_name']
            leader_name = request.form['leader_name']
            leader_email = request.form['leader_email']
            leader_phone = request.form['leader_phone']
            leader_company = request.form['leader_company']
            team_size = int(request.form['team_size'])
            members = []
            for i in range(1, team_size):
                member_name = request.form.get(f'member_{i}_name')
                member_email = request.form.get(f'member_{i}_email')
                member_phone = request.form.get(f'member_{i}_phone')
                member_company = request.form.get(f'member_{i}_company')
                if member_name:
                    members.append({
                        'name': member_name,
                        'email': member_email,
                        'phone': member_phone,
                        'company': member_company
                    })

            # Check unique email
            all_emails = [leader_email] + [m['email'] for m in members]
            for email in all_emails:
                if User.query.filter_by(email=email).first():
                    flash(f'Email {email} is already registered.')
                    return redirect(url_for('register'))

            # Check unique team name
            if Team.query.filter_by(team_name=team_name).first():
                flash(f'Team name "{team_name}" is already taken. Please choose a different name.')
                return redirect(url_for('register'))

            abstract = request.files['abstract']
            if not abstract or abstract.filename == '':
                flash('Abstract file is required.')
                return redirect(url_for('register'))

            # Check file type and size
            allowed_extensions = {'pdf'}
            if '.' not in abstract.filename or abstract.filename.rsplit('.', 1)[1].lower() not in allowed_extensions:
                flash('Only PDF files are allowed.')
                return redirect(url_for('register'))
            if abstract.content_length > 10 * 1024 * 1024:  # 10MB
                flash('File size must be less than 10MB.')
                return redirect(url_for('register'))

            filename = secure_filename(abstract.filename)
            abstract.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

            # Create user for leader (no password since no password registration)
            leader = User(name=leader_name, email=leader_email, phone=leader_phone, company=leader_company, role='participant')
            db.session.add(leader)
            db.session.commit()
            leader_id = leader.user_id

            # Handle payment details
            transaction_id = request.form['transaction_id']
            transaction_photo = request.files['transaction_photo']
            # Upload to OneDrive and get link
            transaction_photo_link = upload_to_onedrive(transaction_photo)
            if not transaction_photo_link:
                # Fallback: save locally and provide local link
                transaction_photo_filename = secure_filename(transaction_photo.filename)
                transaction_photo.save(os.path.join(app.config['UPLOAD_FOLDER'], transaction_photo_filename))
                transaction_photo_link = url_for('static', filename=f'uploads/{transaction_photo_filename}', _external=True)

            # Create team
            team = Team(team_name=team_name, leader_id=leader_id, members=json.dumps(members), email=leader_email, contact=leader_phone, transaction_id=transaction_id, transaction_photo=transaction_photo_link)
            db.session.add(team)
            db.session.commit()
            team_id = team.team_id

            # Submit abstract
            if filename.lower().endswith('.pdf'):
                try:
                    from PyPDF2 import PdfReader
                    reader = PdfReader(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    abstract_text = ''
                    for page in reader.pages:
                        abstract_text += page.extract_text()
                except Exception:
                    # Fallback to reading as text if PDF parsing fails
                    with open(os.path.join(app.config['UPLOAD_FOLDER'], filename), 'r', encoding='utf-8', errors='ignore') as f:
                        abstract_text = f.read()
            else:
                with open(os.path.join(app.config['UPLOAD_FOLDER'], filename), 'r', encoding='utf-8', errors='ignore') as f:
                    abstract_text = f.read()
            try:
                review = ai_review(abstract_text)
            except Exception:
                review = {'total_score': 0, 'feedback': 'AI review failed'}
            submission = Submission(team_id=team_id, abstract_path=filename, ai_score=review['total_score'], feedback=review['feedback'])
            db.session.add(submission)
            db.session.commit()

            # Submit to Google Form
            import requests
            GOOGLE_FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSdBJdjl0uAP9kI3i1zmm2V6osWx7vqGDYCmqVSGHXSJTpnFmw/formResponse"
            form_data = {
                "entry.1652384628": team_name,
                "entry.745041484": leader_name,
                "entry.991783448": leader_email,
                "entry.140739757": leader_phone,
                "entry.73918322": leader_company,
                "entry.816675560": members[0]['name'] if members else '',
                "entry.449064233": members[0]['email'] if members else '',
                "entry.1447071560": members[0]['phone'] if members else '',
                "entry.1601113014": members[1]['name'] if len(members) > 1 else '',
                "entry.1347895140": members[1]['email'] if len(members) > 1 else '',
                "entry.1624551232": members[1]['phone'] if len(members) > 1 else '',
                "entry.913869574": url_for('static', filename=f'uploads/{filename}', _external=True),
                "entry.492840252": transaction_photo_link,
                "entry.1036318918": transaction_id
            }
            try:
                response = requests.post(GOOGLE_FORM_URL, data=form_data)
                print(f"Google Form submission: {response.status_code}")
            except Exception:
                print("Error submitting to Google Form")

            # Save to local Excel file (fallback since Google services are blocked)
            member_details = '; '.join([f"{m['name']} ({m['email']}, {m['phone']}, {m['company']})" for m in members])
            data = {
                'Team Name': team_name,
                'Leader Name': leader_name,
                'Leader Email': leader_email,
                'Leader Phone': leader_phone,
                'Leader Company': leader_company,
                'Team Size': team_size,
                'Members': member_details,
                'Abstract Path': filename,
                'Transaction ID': transaction_id,
                'Transaction Photo': transaction_photo_link,
                'AI Score': review['total_score'],
                'Feedback': review['feedback'],
                'Timestamp': datetime.utcnow()
            }
            df = pd.DataFrame([data])
            if os.path.exists('registrations.xlsx'):
                existing_df = pd.read_excel('registrations.xlsx')
                df = pd.concat([existing_df, df], ignore_index=True)
            df.to_excel('registrations.xlsx', index=False)

            import time
            time.sleep(3)  # Simulate processing time to show loader
            flash('Registration successful! Your abstract has been evaluated. We will get back to you shortly.')
            return redirect(url_for('registration_success'))
        except Exception as e:
            # Pass error message to success page to show error
            return redirect(url_for('registration_success', error=str(e)))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            session['user_id'] = str(user.user_id)
            session['role'] = user.role
            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                flash('Access denied. Admin login required.')
                return redirect(url_for('login'))
        flash('Invalid credentials')
    return render_template('login.html')

def admin_required(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'admin':
            flash('Access denied. Admin login required.')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/admin_dashboard')
@admin_required
def admin_dashboard():
    teams = Team.query.all()
    teams_data = []
    for team in teams:
        leader = User.query.filter_by(user_id=team.leader_id).first()
        members_list = json.loads(team.members) if team.members else []
        submission = Submission.query.filter_by(team_id=team.team_id).first()
        teams_data.append({
            'team': team,
            'leader': leader,
            'members': members_list,
            'submission': submission
        })
    registration_count = len(teams_data)
    return render_template('admin.html', teams=teams_data, registration_count=registration_count)

@app.route('/ideathon', methods=['GET', 'POST'])
def ideathon():
    if request.method == 'POST':
        ppt = request.files['ppt']
        filename = secure_filename(ppt.filename)
        ppt.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        # For simplicity, treat PPT as text or extract text; here assume it's a text file
        with open(os.path.join(app.config['UPLOAD_FOLDER'], filename), 'r') as f:
            idea_text = f.read()
        review = ai_review(idea_text)
        # For now, just save to Excel without team association
        data = {
            'Idea Text': idea_text[:500],  # Truncate for Excel
            'AI Score': review['total_score'],
            'Feedback': review['feedback'],
            'Timestamp': datetime.utcnow()
        }
        df = pd.DataFrame([data])
        if os.path.exists('ideathon.xlsx'):
            existing_df = pd.read_excel('ideathon.xlsx')
            df = pd.concat([existing_df, df], ignore_index=True)
        df.to_excel('ideathon.xlsx', index=False)
        flash('Idea submitted and evaluated by AI.')
        return redirect(url_for('home'))
    return render_template('ideathon.html')



@app.route('/update_stage', methods=['POST'])
@admin_required
def update_stage():
    team_id = request.form['team_id']
    new_stage = int(request.form['stage'])
    team = Team.query.filter_by(team_id=int(team_id)).first()
    if team:
        team.stage = new_stage
        db.session.commit()
        flash('Stage updated')
    else:
        flash('Team not found')
    return redirect(url_for('admin_dashboard'))

@app.route('/download_registrations')
@admin_required
def download_registrations():
    teams = Team.query.all()
    if not teams:
        flash('No registrations found.')
        return redirect(url_for('admin_dashboard'))

    data_list = []
    for team in teams:
        submissions = Submission.query.filter_by(team_id=team.team_id).all()
        ai_score = submissions[0].ai_score if submissions else 0
        feedback = submissions[0].feedback if submissions else ''
        members = json.loads(team.members) if team.members else []
        member_details = '; '.join([f"{m['name']} ({m['email']}, {m['phone']}, {m['company']})" for m in members])
        leader = User.query.filter_by(user_id=team.leader_id).first()
        leader_name = leader.name if leader else ''
        leader_company = leader.company if leader else ''
        data_list.append({
            'Team Name': team.team_name,
            'Leader Name': leader_name,
            'Leader Email': team.email,
            'Leader Phone': team.contact,
            'Leader Company': leader_company,
            'Team Size': len(members) + 1,
            'Members': member_details,
            'Abstract Path': submissions[0].abstract_path if submissions else '',
            'Transaction ID': team.transaction_id,
            'Transaction Photo': team.transaction_photo,
            'AI Score': ai_score,
            'Feedback': feedback,
            'Timestamp': team.timestamp
        })

    df = pd.DataFrame(data_list)
    df.to_excel('registrations.xlsx', index=False)
    return send_file('registrations.xlsx', as_attachment=True)

@app.route('/registration_success')
def registration_success():
    error = request.args.get('error')
    return render_template('registration_success.html', error=error)

@app.route('/results')
def results():
    # Calculate leaderboard based on evaluations and AI scores
    teams = Team.query.all()  # Show all teams for now, or filter as needed
    leaderboard = []
    for team in teams:
        evaluations = Evaluation.query.filter_by(team_id=team.team_id).all()
        ai_score = Submission.query.filter_by(team_id=team.team_id).first().ai_score or 0
        avg_judge_score = sum(e.final_score for e in evaluations) / len(evaluations) if evaluations else 0
        total_score = (ai_score + avg_judge_score) / 2
        leaderboard.append({'team': team, 'score': total_score})
    leaderboard.sort(key=lambda x: x['score'], reverse=True)
    return render_template('results.html', leaderboard=leaderboard)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
