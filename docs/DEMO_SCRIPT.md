# SkillProof AI — Hackathon Demo Script (~3 minutes)

## Before you start

1. Terminal: `cd backend` → activate venv → `uvicorn main:app --reload`
2. Browser tabs: Swagger `http://127.0.0.1:8000/docs`, optional frontend `localhost:5173`
3. One GitHub username ready (e.g. `BeBecpp`)

## 1. Hook (20 sec)

> "Resumes say what people *claim*. SkillProof shows what their **public GitHub projects prove**—with a Builder Score and a skill map."

## 2. Health check (15 sec)

Open `http://127.0.0.1:8000/` — show API name and version.  
Open `/health` — `status: ok`.

## 3. Demo report (30 sec)

`GET /demo/report` in Swagger.

Point out:

- **builder_score**
- **main_identity**
- **skill_map** (9 categories)
- Three **repos** (AI, security, frontend mock)

## 4. Live analyze (45 sec)

`POST /analyze/github`:

```json
{ "username": "BeBecpp" }
```

Explain: MVP uses mock repos until Khuslen's scanner ships; scores are **rule-based**, no OpenAI bill.

Highlight **ai_summary** and **improvement_plan**.

## 5. History + Markdown (30 sec)

`GET /history` — last reports from SQLite.  
Copy `id` → `GET /report/{id}/markdown` — show export for README or portfolio.

## 6. Team split (20 sec)

- **Nero**: API, scoring, reports, DB  
- **Khuslen**: real GitHub analyzer  
- **Frontend**: calls these endpoints  

## 7. Close (20 sec)

> "SkillProof AI—your projects speak louder than your resume. Public evidence only; not a hiring guarantee."

## Backup if network fails

Everything runs offline with mock data. Use `/demo/report` only.
