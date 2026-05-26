# SkillProof AI

**Your projects speak louder than your resume.**

SkillProof AI analyzes a developer's **public GitHub projects** and generates a **proof-of-skill report** based on visible project evidence—not claims on a CV.

## What it does

- Accepts a GitHub username
- Evaluates public repo signals (README, stack hints, demos, tests, etc.)
- Computes a **Builder Score** and **skill map**
- Produces an evidence-based summary and **30-day improvement plan**
- Saves reports to SQLite and exports **Markdown**

## Why it exists

Resumes list skills; repositories **prove** them. SkillProof AI helps students and early-career developers show recruiters and hackathon judges what their public work actually demonstrates.

## Features (MVP)

- `POST /analyze/github` — analyze username and return full report
- Rule-based **score engine** (no paid AI API)
- Fallback **mock repos** until the GitHub scanner is integrated
- SQLite **history**
- **Markdown** export per report
- Demo endpoint for presentations

## Tech stack

| Layer | Stack |
|-------|--------|
| API | FastAPI, Uvicorn, Pydantic |
| Storage | SQLite (`backend/skillproof.db`) |
| Scoring | Python rule engine (`score_engine.py`) |
| Reports | Template logic (`ai_report.py`) |

## Backend setup

```bash
cd backend
python -m venv .venv
```

**macOS / Linux:**

```bash
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

**Windows:**

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Or double-click **`backend/run.bat`** (uses `.venv\Scripts\python.exe`, port **8080**).

> **Windows — `uvicorn is not recognized`:** use `python -m uvicorn` or `.venv\Scripts\python.exe -m uvicorn`.
>
> **Windows — `Activate.ps1 cannot be loaded`:** skip activate; run:
> `.\.venv\Scripts\python.exe -m pip install -r requirements.txt`
> then `.\.venv\Scripts\python.exe -m uvicorn main:app --reload --host 127.0.0.1 --port 8080`
> Or in **CMD**: `\.venv\Scripts\activate.bat` (works without changing execution policy).
>
> **Windows — `[WinError 10013]` on port 8000:** port blocked or in use. Use **8080**: `--port 8080` and open http://127.0.0.1:8080/docs

API: [http://127.0.0.1:8000](http://127.0.0.1:8000)  
Interactive docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

Optional env (copy `.env.example` → `.env`):

```bash
cp .env.example .env   # macOS/Linux
copy .env.example .env # Windows
```

AI API keys are **not required** for MVP.

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | API info |
| GET | `/health` | Health check |
| POST | `/analyze/github` | Analyze GitHub username |
| GET | `/report/{id}` | Fetch saved report |
| GET | `/history` | Recent reports |
| GET | `/report/{id}/markdown` | Markdown export |
| GET | `/demo/report` | Demo report (saved) |

See [docs/API_SPEC.md](docs/API_SPEC.md) for request/response examples.

## Team roles

| Person | Responsibility |
|--------|----------------|
| **Nero / BeBe** | Backend API, score engine, AI/fallback reports, SQLite, Markdown |
| **Khuslen** | `github_analyzer.py`, `repo_scanner.py` — real GitHub scanning |
| **Frontend** | (separate) UI consuming this API |

## Disclaimer

Reports are based on **public GitHub metadata and file signals only**. They are not certifications, hiring decisions, or guarantees. Private repos and employer work are not analyzed.
