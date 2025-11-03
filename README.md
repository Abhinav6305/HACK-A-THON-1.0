# HACK-A-THON 1.0 Interface

A complete dynamic web interface for the international hackathon event HACK-A-THON 1.0, modeled after Denovate.org's style and functionality.

## Features

- **Landing Page**: Event introduction, stages, schedule, prizes, registration button.
- **Registration**: Team registration with abstract upload and AI evaluation.
- **Login**: For participants, admins, and judges.
- **Participant Dashboard**: Progress tracking across 3 stages, submissions, results.
- **Admin Dashboard**: Manage teams, stages, reviews, export data.
- **Judge Panel**: Evaluate teams on innovation, feasibility, clarity.
- **Results & Leaderboard**: Automatically generated from scores.
- **AI Abstract Reviewer**: Uses Ollama with Llama3 for local AI evaluation.
- **Multi-Stage Event**: Ideathon (20 Nov), Coding Contest (1-2 Dec), Hackathon (5-6 Dec).

## Setup

1. Clone or download the project.
2. Install dependencies: `pip install -r requirements.txt`
3. Install Ollama: Download from https://ollama.ai/ and run `ollama pull llama3:latest`
4. Run the app: `python app.py`
5. Open http://127.0.0.1:5000 in your browser.

## Deployment

- For deployment, ensure Ollama is installed on the server.
- Use a production WSGI server like Gunicorn: `gunicorn app:app`
- Set environment variables as needed.

## Database

Uses SQLite (`database.db`) with tables for users, teams, submissions, judges, evaluations, problem_statements.

## Technologies

- Backend: Flask (Python)
- Frontend: HTML5, CSS3, JavaScript
- Database: SQLAlchemy (SQLite)
- AI: Ollama (Llama3)
- Styling: Denovate-inspired dark theme with gradients and animations

## Organization Plan

- **Budget**: ~14 lakhs
- **Stages**:
  - Stage 1: Virtual Ideathon (20 Nov 2025) - PPT upload, AI evaluation
  - Stage 2: Virtual Coding Contest (1-2 Dec 2025) - Link to external platform
  - Stage 3: Offline Hackathon (5-6 Dec 2025) - Judging and final results
- **Sponsorship**: Seek sponsors for prizes, logistics, promotion.
- **Logistics**: Online platforms for virtual stages, venue for offline.
- **Promotion**: Social media, university networks, international outreach.
- **Extras**: Email/WhatsApp notifications, certificate generation, data export.

## Testing

- Registration: Submit form, check database entry and AI score.
- Login: Authenticate and redirect to appropriate dashboard.
- Stages: Upload PPT for Ideathon, access coding contest link.
- Admin: Approve teams, update stages.
- Judge: Evaluate teams.
- Results: View leaderboard with combined scores.
