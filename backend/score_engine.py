"""Rule-based scoring for SkillProof AI."""

from __future__ import annotations

from typing import Any

SKILL_CATEGORIES = [
    "AI / ML",
    "Cybersecurity",
    "Frontend",
    "Backend",
    "Data Science",
    "Documentation",
    "Deployment",
    "Project Complexity",
    "Consistency",
]


def clamp_score(value: float | int) -> int:
    return max(0, min(100, int(round(value))))


def calculate_repo_score(repo: dict[str, Any]) -> int:
    score = 40
    readme_len = repo.get("readme_length", 0)

    if repo.get("has_readme"):
        score += 15
    if readme_len >= 500:
        score += 10
    if repo.get("has_live_demo"):
        score += 10
    if repo.get("has_deps_file"):
        score += 10
    if repo.get("file_count", 0) >= 8:
        score += 10
    if repo.get("has_backend") or repo.get("has_frontend"):
        score += 15
    if repo.get("has_ai") or repo.get("has_security"):
        score += 15
    if repo.get("recently_updated"):
        score += 10
    if repo.get("has_license") or repo.get("has_gitignore"):
        score += 5
    if repo.get("is_fork"):
        score -= 15

    return clamp_score(score)


def _repo_skill_signals(repo: dict[str, Any]) -> dict[str, int]:
    signals: dict[str, int] = {cat: 0 for cat in SKILL_CATEGORIES}
    score = repo.get("score", calculate_repo_score(repo))

    if repo.get("has_ai"):
        signals["AI / ML"] += 25
    if repo.get("has_security"):
        signals["Cybersecurity"] += 25
    if repo.get("has_frontend"):
        signals["Frontend"] += 22
    if repo.get("has_backend"):
        signals["Backend"] += 22
    if repo.get("language", "").lower() in ("python", "r", "julia") and repo.get("has_tests"):
        signals["Data Science"] += 12
    if repo.get("has_readme"):
        signals["Documentation"] += 15
    if readme_len := repo.get("readme_length", 0):
        if readme_len >= 500:
            signals["Documentation"] += 10
    if repo.get("has_docker") or repo.get("has_live_demo"):
        signals["Deployment"] += 18
    if repo.get("file_count", 0) >= 10:
        signals["Project Complexity"] += 15
    signals["Project Complexity"] += min(20, score // 5)
    if repo.get("recently_updated"):
        signals["Consistency"] += 12
    if not repo.get("is_fork"):
        signals["Consistency"] += 5

    return signals


def calculate_skill_map(repos: list[dict[str, Any]]) -> dict[str, int]:
    totals: dict[str, float] = {cat: 0.0 for cat in SKILL_CATEGORIES}
    if not repos:
        return {cat: 0 for cat in SKILL_CATEGORIES}

    for repo in repos:
        signals = _repo_skill_signals(repo)
        for cat, value in signals.items():
            totals[cat] += value

    count = len(repos)
    return {cat: clamp_score(totals[cat] / count) for cat in SKILL_CATEGORIES}


def calculate_builder_score(
    repos: list[dict[str, Any]], skill_map: dict[str, int]
) -> int:
    if not repos:
        return 0

    avg_quality = sum(r.get("score", 0) for r in repos) / len(repos)
    skill_depth = (
        skill_map.get("Backend", 0)
        + skill_map.get("Frontend", 0)
        + skill_map.get("AI / ML", 0)
        + skill_map.get("Cybersecurity", 0)
    ) / 4
    documentation = skill_map.get("Documentation", 0)
    deployment = skill_map.get("Deployment", 0)
    activity = sum(1 for r in repos if r.get("recently_updated")) / len(repos) * 100
    consistency = skill_map.get("Consistency", 0)

    raw = (
        avg_quality * 0.35
        + skill_depth * 0.25
        + documentation * 0.15
        + deployment * 0.10
        + activity * 0.10
        + consistency * 0.05
    )
    return clamp_score(raw)


def determine_main_identity(skill_map: dict[str, int]) -> str:
    identity_keys = [
        ("AI / ML", "AI Builder"),
        ("Cybersecurity", "Security Engineer"),
        ("Frontend", "Frontend Developer"),
        ("Backend", "Backend Developer"),
        ("Data Science", "Data Builder"),
    ]
    best = max(identity_keys, key=lambda item: skill_map.get(item[0], 0))
    if skill_map.get(best[0], 0) < 35:
        return "Full-Stack Builder"
    return best[1]


def get_strong_areas(
    skill_map: dict[str, int], repos: list[dict[str, Any]]
) -> list[str]:
    areas: list[str] = []
    for cat, value in sorted(skill_map.items(), key=lambda x: x[1], reverse=True):
        if value >= 60:
            areas.append(cat)
    if repos and any(r.get("has_ai") for r in repos) and "AI / ML" not in areas:
        if skill_map.get("AI / ML", 0) >= 50:
            areas.append("AI / ML")
    return areas[:5] if areas else [
        k for k, v in sorted(skill_map.items(), key=lambda x: x[1], reverse=True)[:2]
        if v >= 40
    ]


def get_weak_areas(
    skill_map: dict[str, int], repos: list[dict[str, Any]]
) -> list[str]:
    weak: list[str] = []
    for cat, value in skill_map.items():
        if value < 40:
            weak.append(cat)
    if repos:
        if not any(r.get("has_tests") for r in repos) and "Project Complexity" not in weak:
            weak.append("Automated Testing (limited public signals)")
        if not any(r.get("has_docker") for r in repos) and "Deployment" in weak:
            pass
    return weak[:5]


def suggest_roles(skill_map: dict[str, int], main_identity: str) -> list[str]:
    roles: list[str] = [main_identity]
    mapping = [
        (55, "Backend", "Backend Developer"),
        (55, "Frontend", "Frontend Developer"),
        (50, "AI / ML", "ML Engineer (Junior)"),
        (50, "Cybersecurity", "Security Analyst"),
        (50, "Deployment", "DevOps-minded Developer"),
        (50, "Documentation", "Technical Writer / Developer Advocate"),
    ]
    for threshold, key, role in mapping:
        if skill_map.get(key, 0) >= threshold and role not in roles:
            roles.append(role)
    if len(roles) < 3:
        roles.append("Junior Full-Stack Developer")
    return list(dict.fromkeys(roles))[:5]
