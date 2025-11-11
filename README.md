# HACK-A-THON 1.0 Interface

A complete dynamic web interface for the HACK-A-THON 1.0 international hackathon event, modeled after Denovate.org's style and functionality.

## Features

- **Landing Page**: Event introduction, stages, schedule, prizes, registration button
- **Registration**: Team registration with abstract upload and AI evaluation
- **Login System**: For participants, judges, and admins
- **Dashboards**: Participant progress, admin controls, judge evaluation panel
- **AI Abstract Reviewer**: Uses OpenAI GPT-4 to score abstracts on Innovation, Relevance, Feasibility, Clarity
- **Judging System**: Judges evaluate teams on multiple criteria
- **Leaderboard**: Automatically generated results from AI and judge scores
- **Modern UI**: Denovate-style design with gradients, animations, and mobile responsiveness

## Tech Stack

- **Backend**: Flask (Python)
- **Database**: SQLite (local) / PostgreSQL (production)
- **AI**: OpenAI GPT-4 API
- **Frontend**: HTML5, CSS3, JavaScript
- **File Storage**: Local / Cloudinary (for persistence)

## Setup

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd hack-a-thon-1.0
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables:
   - `OPENAI_API_KEY`: Your OpenAI API key
   - `SECRET_KEY`: Flask secret key
   - `DATABASE_URL`: Database URL (optional, defaults to SQLite)
   - `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET`: For file uploads (optional)

4. Run the application:
   ```bash
   python app.py
   ```

5. Open your browser and navigate to `http://localhost:10000`

## Project Structure

```
hackathon_interface/
├── static/
│   ├── css/
│   │   └── styles.css
│   ├── js/
│   │   └── scripts.js
│   └── uploads/
├── templates/
│   ├── home.html
│   ├── register.html
│   ├── login.html
│   ├── dashboard.html
│   ├── admin.html
│   ├── judge.html
│   └── results.html
├── app.py
├── models.py
├── ai_reviewer.py
├── requirements.txt
└── README.md
```

## Database Schema

- **users**: User accounts (participants, judges, admins)
- **teams**: Team information and status
- **submissions**: Abstract uploads and AI scores
- **judges**: Judge accounts and assignments
- **evaluations**: Judge scores for teams
- **problem_statements**: Hackathon challenges

## AI Evaluation

The AI reviewer evaluates abstracts on:
- Innovation (0-10)
- Relevance (0-10)
- Feasibility (0-10)
- Clarity (0-10)

Total score = 0.4*Innovation + 0.3*Feasibility + 0.2*Relevance + 0.1*Clarity

## Deployment

This app is configured for deployment on Render.com with:
- PostgreSQL database
- Cloudinary for file storage
- Environment variables for secrets

## License

MIT License
