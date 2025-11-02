from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    user_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=True)
    role = db.Column(db.String(20), nullable=False)  # participant, judge, admin
    phone = db.Column(db.String(20))
    company = db.Column(db.String(100))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Team(db.Model):
    __tablename__ = 'teams'
    team_id = db.Column(db.Integer, primary_key=True)
    team_name = db.Column(db.String(100), unique=True, nullable=False)
    leader_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    members = db.Column(db.Text, nullable=False)  # JSON string of member details
    email = db.Column(db.String(100), nullable=False)
    contact = db.Column(db.String(20), nullable=False)
    stage = db.Column(db.Integer, default=1)  # 1: Ideathon, 2: Coding Contest, 3: Hackathon
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    transaction_id = db.Column(db.String(100))
    transaction_photo = db.Column(db.String(200))
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())

class Submission(db.Model):
    __tablename__ = 'submissions'
    submission_id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.team_id'), nullable=False)
    abstract_path = db.Column(db.String(200), nullable=False)
    ai_score = db.Column(db.Float, nullable=True)
    feedback = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())

class Judge(db.Model):
    __tablename__ = 'judges'
    judge_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    assigned_teams = db.Column(db.Text, nullable=True)  # JSON string of team_ids

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Evaluation(db.Model):
    __tablename__ = 'evaluations'
    evaluation_id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.team_id'), nullable=False)
    judge_id = db.Column(db.Integer, db.ForeignKey('judges.judge_id'), nullable=False)
    innovation = db.Column(db.Float, nullable=False)
    feasibility = db.Column(db.Float, nullable=False)
    clarity = db.Column(db.Float, nullable=False)
    final_score = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())

class ProblemStatement(db.Model):
    __tablename__ = 'problem_statements'
    ps_id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    domain = db.Column(db.String(100), nullable=False)
    level = db.Column(db.String(20), nullable=False)  # beginner, intermediate, advanced
