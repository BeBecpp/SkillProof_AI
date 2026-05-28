# SkillProof AI — API Specification (MVP v0.1.0)

Local base URL: `http://127.0.0.1:8000`

Production backend: `https://skillproof-ai-9u61.onrender.com`

## GET /

**Response 200**

Serves the static frontend `index.html` when the backend is running from the repo.

---

## GET /api

**Response 200**

```json
{
  "name": "SkillProof AI API",
  "status": "running",
  "version": "0.1.0"
}
```

---

## GET /health

**Response 200**

```json
{
  "status": "ok"
}
```

---

## POST /analyze/github

Analyze a GitHub username. Uses `github_analyzer` when available; otherwise MVP mock repos.

**Request body**

```json
{
  "username": "BeBecpp"
}
```

**Validation**

- Non-empty, max 39 characters
- Letters, numbers, hyphen only
- Cannot start or end with hyphen

**Response 200** — `ReportResponse`

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "BeBecpp",
  "avatar_url": "https://github.com/BeBecpp.png",
  "github_url": "https://github.com/BeBecpp",
  "builder_score": 72,
  "main_identity": "AI Builder",
  "skill_map": {
    "AI / ML": 68,
    "Cybersecurity": 55,
    "Frontend": 60,
    "Backend": 70,
    "Data Science": 40,
    "Documentation": 75,
    "Deployment": 65,
    "Project Complexity": 70,
    "Consistency": 80
  },
  "strong_areas": ["Documentation", "Consistency"],
  "weak_areas": ["Data Science"],
  "suggested_roles": ["AI Builder", "Backend Developer"],
  "repos": [
    {
      "name": "skillproof-ml-api",
      "url": "https://github.com/BeBecpp/skillproof-ml-api",
      "description": "FastAPI service with embeddings pipeline...",
      "language": "Python",
      "stars": 24,
      "forks": 5,
      "updated_at": "2026-04-12T10:00:00Z",
      "created_at": "2025-08-01T09:00:00Z",
      "has_readme": true,
      "has_live_demo": true,
      "has_backend": true,
      "has_frontend": false,
      "has_ai": true,
      "has_security": false,
      "has_tests": true,
      "has_docker": true,
      "is_fork": false,
      "project_types": ["AI / ML", "Backend", "API"],
      "score": 85,
      "findings": []
    }
  ],
  "ai_summary": "Public GitHub evidence for **BeBecpp** shows...",
  "improvement_plan": [
    "Add or expand README files...",
    "Publish a live demo..."
  ],
  "created_at": "2026-05-26T12:00:00+00:00"
}
```

**Response 422** — invalid username

```json
{
  "detail": "Username may only contain letters, numbers, and hyphens..."
}
```

---

## GET /report/{report_id}

**Response 200** — full `ReportResponse` (same shape as analyze)

**Response 404**

```json
{
  "detail": "Report not found"
}
```

---

## GET /history

Query: `limit` (optional, default 20, max 100)

**Response 200**

```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "username": "BeBecpp",
    "builder_score": 72,
    "main_identity": "AI Builder",
    "created_at": "2026-05-26T12:00:00+00:00"
  }
]
```

---

## GET /report/{report_id}/markdown

**Response 200** — `text/markdown`

```markdown
# SkillProof Report — BeBecpp

**Builder Score:** 72/100
...
```

**Response 404** — report not found

---

## GET /demo/report

Returns a full report for username `SkillProofDemo` using mock data and **saves** it to SQLite.

**Response 200** — `ReportResponse`

---

## Error format

```json
{
  "detail": "Human-readable message"
}
```

Internal errors return 500 without stack traces.
