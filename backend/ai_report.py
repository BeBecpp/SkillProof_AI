"""Rule-based report text — no external AI API."""

from __future__ import annotations

from typing import Any


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
        "Scores are derived from public repo metadata and file signals only—not from private code or employer data."
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
        plan.append("Document security tooling (linters, dependency scans) in a dedicated security-oriented repo.")
    if "AI / ML" in weak and any(r.get("has_ai") for r in repos):
        plan.append("Add model cards or inference examples to AI repos for clearer skill proof.")
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


def generate_ai_report(report_data: dict[str, Any]) -> dict[str, Any]:
    return {
        "ai_summary": generate_fallback_summary(report_data),
        "improvement_plan": generate_improvement_plan(report_data),
    }
