"""AI-backed report text with a rule-based fallback."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
DEFAULT_OPENAI_MODEL = "gpt-5.2"
GEMINI_GENERATE_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
AI_REPORT_JSON_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "ai_summary": {"type": "string"},
        "improvement_plan": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": ["ai_summary", "improvement_plan"],
}


def generate_fallback_summary(report_data: dict[str, Any]) -> str:
    username = report_data.get("username", "developer")
    score = report_data.get("builder_score", 0)
    identity = report_data.get("main_identity", "Builder")
    repos = report_data.get("repos", [])
    strong = report_data.get("strong_areas", [])
    weak = report_data.get("weak_areas", [])
    skill_map = report_data.get("skill_map", {})

    repo_count = len(repos)
    named = ", ".join(r.get("name", "project") for r in repos[:3]) if repos else "no public repos in this scan"

    if score >= 75:
        tone = f"Public GitHub evidence for **{username}** shows a solid builder profile centered on **{identity}**."
    elif score >= 55:
        tone = f"Public GitHub evidence for **{username}** suggests an emerging **{identity}** with room to deepen portfolio signals."
    else:
        tone = (
            f"Public project evidence for **{username}** is limited in this MVP scan; "
            f"the profile is oriented toward **{identity}**, but more documented repos would strengthen the proof."
        )

    strong_text = (
        f"Strongest signals appear in: {', '.join(strong)}."
        if strong
        else "No category reached a strong threshold yet; focus on README quality and deployment links."
    )

    weak_text = (
        f"Areas with thinner public evidence: {', '.join(weak[:3])}."
        if weak
        else "Weak-area signals are balanced; continue shipping visible artifacts."
    )

    top_skills = sorted(skill_map.items(), key=lambda x: x[1], reverse=True)[:3]
    skills_line = ", ".join(f"{k} ({v})" for k, v in top_skills) if top_skills else "n/a"

    return (
        f"{tone} This report analyzed {repo_count} representative public project(s) "
        f"({named}). Builder Score: **{score}/100**. "
        f"{strong_text} {weak_text} "
        f"Top skill-map signals: {skills_line}. "
        "Scores are derived from public repo metadata and file signals only, not from private code or employer data."
    )


def generate_improvement_plan(report_data: dict[str, Any]) -> list[str]:
    weak = set(report_data.get("weak_areas", []))
    repos = report_data.get("repos", [])
    plan: list[str] = []

    if "Documentation" in weak or not all(r.get("has_readme") for r in repos):
        plan.append("Add or expand README files with setup, architecture, and demo links on top repos.")
    if "Deployment" in weak or not any(r.get("has_live_demo") for r in repos):
        plan.append("Publish a live demo (Vercel, Render, or similar) for at least one flagship project.")
    if not any(r.get("has_tests") for r in repos):
        plan.append("Expose test folders or CI badges so public evidence shows quality discipline.")
    if "Cybersecurity" in weak:
        plan.append("Document security tooling, dependency scans, or defensive review notes in one repo.")
    if "AI / ML" in weak and any(r.get("has_ai") for r in repos):
        plan.append("Add model cards, dataset notes, or inference examples to AI repos for clearer skill proof.")
    if "Consistency" in weak:
        plan.append("Commit regularly for 30 days on one primary repo to improve activity signals.")
    if "Backend" in weak:
        plan.append("Ship a small API project with OpenAPI docs and a clear requirements.txt or package.json.")
    if "Frontend" in weak:
        plan.append("Showcase one responsive UI with screenshots and component structure in the README.")

    defaults = [
        "Pin your best 3 repositories on GitHub and align their README narratives with your target role.",
        "Add LICENSE and .gitignore to every public repo you want recruiters to see.",
        "Link this SkillProof report in your profile README once the full GitHub scanner is live.",
    ]
    for item in defaults:
        if item not in plan:
            plan.append(item)
        if len(plan) >= 6:
            break

    return plan[:6]


def _compact_report_context(report_data: dict[str, Any]) -> dict[str, Any]:
    repos = report_data.get("repos", [])
    compact_repos = []
    for repo in repos[:12]:
        compact_repos.append(
            {
                "name": repo.get("name"),
                "description": repo.get("description"),
                "language": repo.get("language"),
                "score": repo.get("score"),
                "project_types": repo.get("project_types", []),
                "signals": {
                    "readme": repo.get("has_readme"),
                    "demo": repo.get("has_live_demo"),
                    "backend": repo.get("has_backend"),
                    "frontend": repo.get("has_frontend"),
                    "ai": repo.get("has_ai"),
                    "security": repo.get("has_security"),
                    "tests": repo.get("has_tests"),
                    "docker": repo.get("has_docker"),
                    "fork": repo.get("is_fork"),
                },
            }
        )

    return {
        "username": report_data.get("username"),
        "builder_score": report_data.get("builder_score"),
        "main_identity": report_data.get("main_identity"),
        "skill_map": report_data.get("skill_map", {}),
        "strong_areas": report_data.get("strong_areas", []),
        "weak_areas": report_data.get("weak_areas", []),
        "suggested_roles": report_data.get("suggested_roles", []),
        "repos": compact_repos,
    }


def _extract_response_text(payload: dict[str, Any]) -> str:
    direct = payload.get("output_text")
    if isinstance(direct, str) and direct.strip():
        return direct.strip()

    chunks: list[str] = []
    for item in payload.get("output", []):
        if not isinstance(item, dict):
            continue
        for content in item.get("content", []):
            if isinstance(content, dict):
                text = content.get("text")
                if isinstance(text, str):
                    chunks.append(text)
    return "\n".join(chunks).strip()


def _parse_ai_json(text: str) -> dict[str, Any] | None:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        cleaned = cleaned[start : end + 1]
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    return data


def _generate_openai_report(report_data: dict[str, Any]) -> dict[str, Any] | None:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    provider = os.getenv("AI_PROVIDER", "auto").strip().lower()
    if not api_key or provider not in {"auto", "openai"}:
        return None

    model = os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL).strip() or DEFAULT_OPENAI_MODEL
    prompt = {
        "task": "Generate an honest proof-of-skill report from public GitHub evidence.",
        "rules": [
            "Use only the supplied evidence.",
            "Do not exaggerate ability.",
            "Do not insult or judge the person.",
            "Focus on projects, public signals, and next practical improvements.",
            "Return valid JSON only.",
        ],
        "required_json_shape": {
            "ai_summary": "One concise paragraph, 90-140 words.",
            "improvement_plan": [
                "Six concrete 30-day improvement steps as strings.",
            ],
        },
        "report_context": _compact_report_context(report_data),
    }
    payload = {
        "model": model,
        "instructions": (
            "You are SkillProof AI, a careful proof-of-skill analyzer for young developers. "
            "You write clear, evidence-based portfolio feedback."
        ),
        "input": json.dumps(prompt, ensure_ascii=False),
        "text": {
            "format": {
                "type": "json_schema",
                "name": "skillproof_ai_report",
                "strict": True,
                "schema": AI_REPORT_JSON_SCHEMA,
            },
            "verbosity": "medium",
        },
        "max_output_tokens": 900,
    }
    request = urllib.request.Request(
        OPENAI_RESPONSES_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=18) as response:
            raw = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError):
        return None

    parsed = _parse_ai_json(_extract_response_text(raw))
    if not parsed:
        return None

    summary = parsed.get("ai_summary")
    plan = parsed.get("improvement_plan")
    if not isinstance(summary, str) or not isinstance(plan, list):
        return None
    clean_plan = [str(item).strip() for item in plan if str(item).strip()]
    if not summary.strip() or not clean_plan:
        return None
    return {
        "ai_summary": summary.strip(),
        "improvement_plan": clean_plan[:6],
    }


def _generate_gemini_report(report_data: dict[str, Any]) -> dict[str, Any] | None:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    provider = os.getenv("AI_PROVIDER", "auto").strip().lower()
    if not api_key or provider not in {"auto", "gemini"}:
        return None

    model = os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL).strip() or DEFAULT_GEMINI_MODEL
    prompt = {
        "task": "Generate an honest proof-of-skill report from public GitHub evidence.",
        "rules": [
            "Use only the supplied evidence.",
            "Do not exaggerate ability.",
            "Do not insult or judge the person.",
            "Focus on projects, public signals, and next practical improvements.",
            "Return valid JSON only.",
        ],
        "required_json_shape": {
            "ai_summary": "One concise paragraph, 90-140 words.",
            "improvement_plan": [
                "Six concrete 30-day improvement steps as strings.",
            ],
        },
        "report_context": _compact_report_context(report_data),
    }
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "text": (
                            "You are SkillProof AI, a careful proof-of-skill analyzer for young developers. "
                            "Return only valid JSON.\n\n"
                            + json.dumps(prompt, ensure_ascii=False)
                        )
                    }
                ],
            }
        ],
        "generationConfig": {
            "temperature": 0.4,
            "maxOutputTokens": 900,
            "responseMimeType": "application/json",
        },
    }
    request = urllib.request.Request(
        GEMINI_GENERATE_URL.format(model=model),
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=18) as response:
            raw = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError):
        return None

    parts = (
        raw.get("candidates", [{}])[0]
        .get("content", {})
        .get("parts", [])
    )
    text = "\n".join(part.get("text", "") for part in parts if isinstance(part, dict)).strip()
    parsed = _parse_ai_json(text)
    if not parsed:
        return None

    summary = parsed.get("ai_summary")
    plan = parsed.get("improvement_plan")
    if not isinstance(summary, str) or not isinstance(plan, list):
        return None
    clean_plan = [str(item).strip() for item in plan if str(item).strip()]
    if not summary.strip() or not clean_plan:
        return None
    return {
        "ai_summary": summary.strip(),
        "improvement_plan": clean_plan[:6],
    }


def generate_ai_report(report_data: dict[str, Any]) -> dict[str, Any]:
    openai_report = _generate_openai_report(report_data)
    if openai_report:
        return openai_report

    gemini_report = _generate_gemini_report(report_data)
    if gemini_report:
        return gemini_report

    return {
        "ai_summary": generate_fallback_summary(report_data),
        "improvement_plan": generate_improvement_plan(report_data),
    }
