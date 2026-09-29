# FitBuddy – AI Fitness Plan Generator

A complete FastAPI + Jinja2 + SQLite + Google Gemini application based on the supplied FitBuddy project documentation.

## Features

- Collects name, user ID, age, weight, fitness goal and workout intensity.
- Generates a structured 7-day workout plan with Gemini.
- Generates a concise nutrition/recovery tip with a fast Gemini model.
- Accepts feedback and regenerates the plan while preserving the original plan.
- Stores users and plans in SQLite using SQLAlchemy.
- Admin dashboard protected by an admin token.
- JSON REST API plus browser/Jinja2 interface.
- Health endpoint and automated tests.
- Uses Google's current `google-genai` SDK rather than the older `google-generativeai` package referenced by the original document.

## Safety note

FitBuddy is a wellness-planning demo, not a medical diagnosis or treatment system. AI output should be reviewed by a qualified professional when appropriate. Users with injuries, medical conditions, pregnancy, eating disorders, or other health concerns should seek professional guidance before following a workout or nutrition plan.

## Quick start

### Windows PowerShell

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Open `.env` and set `GEMINI_API_KEY` and `ADMIN_TOKEN`.

Run:

```powershell
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000

API docs: http://127.0.0.1:8000/docs

Admin: http://127.0.0.1:8000/admin?token=YOUR_ADMIN_TOKEN

## Linux/macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

## Testing

The test suite uses a fake AI service, so tests do not consume Gemini API quota:

```bash
pytest -q
```

## API examples

Generate a plan:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/plans \
  -H "Content-Type: application/json" \
  -d '{"name":"Arun","user_id":"FB001","age":21,"weight":68,"goal":"muscle gain","intensity":"medium"}'
```

Get a plan:

```bash
curl http://127.0.0.1:8000/api/v1/plans/FB001
```

Submit feedback:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/plans/FB001/feedback \
  -H "Content-Type: application/json" \
  -d '{"feedback":"Add more cardio and one extra rest day."}'
```

## Project structure

```text
FitBuddy/
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── database.py
│   ├── main.py
│   ├── models.py
│   ├── schemas.py
│   ├── gemini_service.py
│   ├── routes.py
│   └── seed.py
├── static/
│   ├── css/style.css
│   └── js/app.js
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── result.html
│   ├── admin_login.html
│   └── all_users.html
├── tests/
│   └── test_app.py
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```
