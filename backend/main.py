"""SkillProof AI — FastAPI backend MVP."""

from __future__ import annotations

import importlib.util
import uuid
from datetime import datetime, timezone
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from ai_report import generate_ai_report
from database import get_history, get_report, init_db, save_report
from models import (
    AnalyzeGithubRequest,
    ErrorResponse,
    Finding,
    HistoryItem,
    RepoAnalysis,
    ReportResponse,
)
from score_engine import (
    calculate_builder_score,
    calculate_repo_score,
    calculate_skill_map,
    determine_main_identity,
    get_strong_areas,
    get_weak_areas,
    suggest_roles,
)

load_dotenv()

app = FastAPI(title="SkillProof AI API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    _request: Request, exc: RequestValidationError
) -> JSONResponse:
    errors = exc.errors()
    message = errors[0].get("msg", "Validation error") if errors else "Validation error"
    if "ctx" in (errors[0] if errors else {}):
        message = str(errors[0].get("msg", message))
    return JSONResponse(status_code=422, content={"detail": message})


@app.exception_handler(HTTPException)
async def http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(Exception)
async def generic_exception_handler(_request: Request, _exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal error occurred. Please try again later."},
    )


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _github_analyzer_available() -> bool:
    spec = importlib.util.find_spec("github_analyzer")
    return spec is not None


def _fetch_via_analyzer(username: str) -> dict[str, Any] | None:
    if not _github_analyzer_available():
        return None
    try:
        import github_analyzer  # type: ignore

        result = github_analyzer.analyze_user(username)
        if isinstance(result, dict):
            return result
        if isinstance(result, list):
            return {"username": username, "repos": result}
    except Exception as exc:
        message = str(exc)
        if "not found" in message.lower():
            raise HTTPException(status_code=404, detail=message) from exc
        return None
    return None


def _mock_profile(username: str) -> dict[str, Any]:
    return {
        "username": username,
        "avatar_url": f"https://github.com/{username}.png",
        "github_url": f"https://github.com/{username}",
        "repos": _mock_repos(username),
    }


def _normalize_profile(username: str, raw: Any) -> dict[str, Any]:
    if raw is None:
        return _mock_profile(username)
    if isinstance(raw, list):
        return {
            "username": username,
            "avatar_url": f"https://github.com/{username}.png",
            "github_url": f"https://github.com/{username}",
            "repos": raw,
        }
    if isinstance(raw, dict):
        repos = raw.get("repos")
        if not isinstance(repos, list):
            repos = []
        return {
            "username": raw.get("username") or username,
            "avatar_url": raw.get("avatar_url") or f"https://github.com/{username}.png",
            "github_url": raw.get("github_url") or f"https://github.com/{username}",
            "repos": repos,
        }
    return _mock_profile(username)


def _fetch_profile(username: str) -> dict[str, Any]:
    profile = _fetch_via_analyzer(username)
    if profile is not None:
        return _normalize_profile(username, profile)
    return _mock_profile(username)


def _fetch_repos_via_analyzer(username: str) -> list[dict[str, Any]] | None:
    try:
        profile = _fetch_via_analyzer(username)
        if profile is None:
            return None
        return _normalize_profile(username, profile)["repos"]
    except HTTPException:
        return None


def _mock_repos(username: str) -> list[dict[str, Any]]:
    """Three realistic public-style repos for MVP when scanner is unavailable."""
    base = f"https://github.com/{username}"
    return [
        {
            "name": "skillproof-ml-api",
            "url": f"{base}/skillproof-ml-api",
            "description": "FastAPI service with embeddings pipeline and batch inference endpoints.",
            "language": "Python",
            "stars": 24,
            "forks": 5,
            "updated_at": "2026-04-12T10:00:00Z",
            "created_at": "2025-08-01T09:00:00Z",
            "has_readme": True,
            "readme_length": 1200,
            "has_live_demo": True,
            "has_backend": True,
            "has_frontend": False,
            "has_ai": True,
            "has_security": False,
            "has_tests": True,
            "has_docker": True,
            "has_deps_file": True,
            "has_license": True,
            "has_gitignore": True,
            "is_fork": False,
            "file_count": 42,
            "recently_updated": True,
            "project_types": ["AI / ML", "Backend", "API"],
        },
        {
            "name": "secure-audit-kit",
            "url": f"{base}/secure-audit-kit",
            "description": "CLI toolkit for dependency scanning and basic SAST-style checks.",
            "language": "Python",
            "stars": 18,
            "forks": 3,
            "updated_at": "2026-03-20T14:30:00Z",
            "created_at": "2025-11-10T12:00:00Z",
            "has_readme": True,
            "readme_length": 800,
            "has_live_demo": False,
            "has_backend": True,
            "has_frontend": False,
            "has_ai": False,
            "has_security": True,
            "has_tests": True,
            "has_docker": False,
            "has_deps_file": True,
            "has_license": True,
            "has_gitignore": True,
            "is_fork": False,
            "file_count": 28,
            "recently_updated": True,
            "project_types": ["Cybersecurity", "Tooling"],
        },
        {
            "name": "portfolio-dashboard-ui",
            "url": f"{base}/portfolio-dashboard-ui",
            "description": "React dashboard for visualizing open-source activity and project metrics.",
            "language": "TypeScript",
            "stars": 31,
            "forks": 7,
            "updated_at": "2026-05-01T08:15:00Z",
            "created_at": "2025-06-15T16:00:00Z",
            "has_readme": True,
            "readme_length": 650,
            "has_live_demo": True,
            "has_backend": False,
            "has_frontend": True,
            "has_ai": False,
            "has_security": False,
            "has_tests": False,
            "has_docker": False,
            "has_deps_file": True,
            "has_license": False,
            "has_gitignore": True,
            "is_fork": False,
            "file_count": 55,
            "recently_updated": True,
            "project_types": ["Frontend", "Dashboard"],
        },
    ]


def _build_findings(repo: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    for item in repo.get("security_findings", []):
        if isinstance(item, dict):
            findings.append(Finding(**item))
    if repo.get("has_readme"):
        findings.append(
            Finding(
                category="Documentation",
                signal="README present",
                impact="positive",
                detail="Repository includes a README for onboarding.",
            )
        )
    if repo.get("has_live_demo"):
        findings.append(
            Finding(
                category="Deployment",
                signal="Live demo linked",
                impact="positive",
                detail="Public demo URL detected or declared in README.",
            )
        )
    if repo.get("has_ai"):
        findings.append(
            Finding(
                category="AI / ML",
                signal="AI/ML artifacts",
                impact="positive",
                detail="Model, inference, or ML-related structure detected.",
            )
        )
    if repo.get("has_security"):
        findings.append(
            Finding(
                category="Cybersecurity",
                signal="Security tooling",
                impact="positive",
                detail="Security-oriented scripts or configs found.",
            )
        )
    if repo.get("is_fork"):
        findings.append(
            Finding(
                category="Project Complexity",
                signal="Fork",
                impact="negative",
                detail="Forked repo; originality signals are discounted.",
            )
        )
    if not repo.get("has_tests"):
        findings.append(
            Finding(
                category="Project Complexity",
                signal="No test signals",
                impact="neutral",
                detail="No public test folder or CI badge detected.",
            )
        )
    return findings


def _enrich_repos(raw_repos: list[dict[str, Any]]) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    for repo in raw_repos:
        data = dict(repo)
        data["score"] = calculate_repo_score(data)
        enriched.append(data)
    return enriched


def _repos_to_models(repos: list[dict[str, Any]]) -> list[RepoAnalysis]:
    models: list[RepoAnalysis] = []
    for repo in repos:
        models.append(
            RepoAnalysis(
                name=repo["name"],
                url=repo["url"],
                description=repo.get("description"),
                language=repo.get("language"),
                stars=repo.get("stars", 0),
                forks=repo.get("forks", 0),
                updated_at=repo.get("updated_at"),
                created_at=repo.get("created_at"),
                has_readme=repo.get("has_readme", False),
                has_live_demo=repo.get("has_live_demo", False),
                has_backend=repo.get("has_backend", False),
                has_frontend=repo.get("has_frontend", False),
                has_ai=repo.get("has_ai", False),
                has_security=repo.get("has_security", False),
                has_tests=repo.get("has_tests", False),
                has_docker=repo.get("has_docker", False),
                is_fork=repo.get("is_fork", False),
                project_types=repo.get("project_types", []),
                score=repo.get("score", 0),
                findings=_build_findings(repo),
            )
        )
    return models


def build_report(username: str, raw_repos: list[dict[str, Any]] | None = None) -> ReportResponse:
    profile = _normalize_profile(username, raw_repos) if raw_repos is not None else _fetch_profile(username)
    username = profile["username"]
    repos_data = profile["repos"]
    repos_data = _enrich_repos(repos_data)
    skill_map = calculate_skill_map(repos_data)
    builder_score = calculate_builder_score(repos_data, skill_map)
    main_identity = determine_main_identity(skill_map)
    strong_areas = get_strong_areas(skill_map, repos_data)
    weak_areas = get_weak_areas(skill_map, repos_data)
    suggested = suggest_roles(skill_map, main_identity)
    repo_models = _repos_to_models(repos_data)

    report_id = str(uuid.uuid4())
    created_at = _utc_now_iso()
    partial: dict[str, Any] = {
        "username": username,
        "builder_score": builder_score,
        "main_identity": main_identity,
        "skill_map": skill_map,
        "strong_areas": strong_areas,
        "weak_areas": weak_areas,
        "suggested_roles": suggested,
        "repos": [r.model_dump() for r in repo_models],
    }
    ai = generate_ai_report(partial)

    report = ReportResponse(
        id=report_id,
        username=username,
        avatar_url=profile["avatar_url"],
        github_url=profile["github_url"],
        builder_score=builder_score,
        main_identity=main_identity,
        skill_map=skill_map,
        strong_areas=strong_areas,
        weak_areas=weak_areas,
        suggested_roles=suggested,
        repos=repo_models,
        ai_summary=ai["ai_summary"],
        improvement_plan=ai["improvement_plan"],
        created_at=created_at,
    )
    return report


def report_to_markdown(report: ReportResponse) -> str:
    lines = [
        f"# SkillProof Report — {report.username}",
        "",
        f"**Builder Score:** {report.builder_score}/100",
        f"**Main Identity:** {report.main_identity}",
        f"**GitHub:** {report.github_url}",
        f"**Generated:** {report.created_at}",
        "",
        "## Skill Map",
        "",
    ]
    for category, value in sorted(report.skill_map.items(), key=lambda x: -x[1]):
        lines.append(f"- {category}: {value}/100")
    lines.extend(["", "## Strong Areas", ""])
    if report.strong_areas:
        for area in report.strong_areas:
            lines.append(f"- {area}")
    else:
        lines.append("- (none above threshold)")
    lines.extend(["", "## Weak Areas", ""])
    if report.weak_areas:
        for area in report.weak_areas:
            lines.append(f"- {area}")
    else:
        lines.append("- (none flagged)")
    lines.extend(["", "## Suggested Roles", ""])
    for role in report.suggested_roles:
        lines.append(f"- {role}")
    lines.extend(["", "## Repo Analysis", ""])
    for repo in report.repos:
        lines.append(f"### {repo.name} (score: {repo.score}/100)")
        lines.append(f"- URL: {repo.url}")
        lines.append(f"- Language: {repo.language or 'n/a'}")
        lines.append(f"- Stars: {repo.stars} | Forks: {repo.forks}")
        if repo.description:
            lines.append(f"- {repo.description}")
        types = ", ".join(repo.project_types) if repo.project_types else "n/a"
        lines.append(f"- Types: {types}")
        if repo.findings:
            lines.append("- Findings:")
            for f in repo.findings:
                lines.append(f"  - [{f.impact}] {f.category}: {f.detail}")
        lines.append("")
    lines.extend(["## AI Summary", "", report.ai_summary, "", "## 30-Day Improvement Plan", ""])
    for i, step in enumerate(report.improvement_plan, 1):
        lines.append(f"{i}. {step}")
    lines.extend(
        [
            "",
            "## Disclaimer",
            "",
            "This report is generated from public GitHub signals only (MVP). "
            "It is not a hiring decision, certification, or guarantee of skill. "
            "Private repositories and employer work are not analyzed.",
        ]
    )
    return "\n".join(lines)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "name": "SkillProof AI API",
        "status": "running",
        "version": "0.1.0",
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/analyze/github", response_model=ReportResponse)
def analyze_github(body: AnalyzeGithubRequest) -> ReportResponse:
    report = build_report(body.username)
    save_report(report)
    return report


@app.get("/report/{report_id}", response_model=ReportResponse)
def get_report_by_id(report_id: str) -> ReportResponse:
    report = get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@app.get("/history", response_model=list[HistoryItem])
def history(limit: int = 20) -> list[HistoryItem]:
    return get_history(limit=min(limit, 100))


@app.get("/report/{report_id}/markdown")
def report_markdown(report_id: str) -> PlainTextResponse:
    report = get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return PlainTextResponse(report_to_markdown(report), media_type="text/markdown")


@app.get("/demo/report", response_model=ReportResponse)
def demo_report() -> ReportResponse:
    report = build_report("SkillProofDemo")
    save_report(report)
    return report
