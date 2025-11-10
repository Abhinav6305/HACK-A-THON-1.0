# HACK-A-THON 1.0 Interface

A complete dynamic web interface for the HACK-A-THON 1.0 international hackathon event, modeled after Denovate.org's style and functionality.

## Features

- **Landing Page**: Event introduction, stages, schedule, prizes, registration button.
- **Registration**: Team registration with abstract upload, AI evaluation.
- **Admin Dashboard**: Manage teams, view registrations, export data.
- **AI Abstract Reviewer**: Uses OpenAI GPT-4 to score abstracts on Innovation, Relevance, Feasibility, Clarity.
- **Database**: SQLite for local development, PostgreSQL for production.
- **Modern UI**: Denovate-style design with gradients, animations, neon-tech theme.

## Setup

1. Clone the repository.
2. Install dependencies: `pip install -r requirements.txt`
3. Set environment variables:
   - `OPENAI_API_KEY`: Your OpenAI API key for AI evaluation.
   - `DATABASE_URL`: PostgreSQL URL for production (optional, defaults to SQLite).
   - `SECRET_KEY`: Flask secret key.
   - `ADMIN_PASSWORD`: Password for admin access.
4. Run the app: `python app.py`
5. Access at `http://127.0.0.1:5000/`

## Project Structure

```
hackathon_interface/
├── static/
│   ├── css/styles.css
│   ├── js/scripts.js
│   └── uploads/
├── templates/
│   ├── home.html
│   ├── register.html
│   ├── admin.html
│   └── results.html
├── app.py
├── models.py
├── ai_reviewer.py
├── requirements.txt
├── README.md
└── database.db (created automatically)
```

## Routes

- `/`: Home page
- `/register`: Team registration
- `/admin`: Admin dashboard
- `/results`: Leaderboard

## Technologies

- **Backend**: Flask (Python)
- **Database**: SQLAlchemy (SQLite/PostgreSQL)
- **AI**: OpenAI GPT-4 API
- **Frontend**: HTML5, CSS3, JavaScript
- **Styling**: Custom CSS with animations

## Deployment

Deploy to Heroku, Render, or similar platform. Set environment variables in the platform's settings.
