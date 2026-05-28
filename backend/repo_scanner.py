"""Repository evidence scanner for SkillProof AI.

This module converts GitHub repo metadata, README text, and file-tree paths into
the boolean evidence flags expected by the scoring engine.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

AI_KEYWORDS = {
    "ai",
    "ml",
    "machine-learning",
    "deep-learning",
    "model",
    "inference",
    "training",
    "dataset",
    "sklearn",
    "scikit",
    "torch",
    "pytorch",
    "tensorflow",
    "keras",
    "opencv",
    "nlp",
    "llm",
    "rag",
    "embedding",
}

SECURITY_KEYWORDS = {
    "security",
    "cyber",
    "ctf",
    "crypto",
    "pwn",
    "rev",
    "reverse",
    "forensics",
    "exploit",
    "scanner",
    "vulnerability",
    "sast",
    "audit",
    "writeup",
    "owasp",
}

FRONTEND_KEYWORDS = {
    "react",
    "vite",
    "next",
    "vue",
    "svelte",
    "tailwind",
    "bootstrap",
    "component",
    "responsive",
}

BACKEND_KEYWORDS = {
    "fastapi",
    "flask",
    "django",
    "express",
    "api",
    "router",
    "endpoint",
    "server",
    "database",
    "sqlite",
    "postgres",
    "mongodb",
}

RISK_PATTERNS: dict[str, re.Pattern[str]] = {
    "Possible API key": re.compile(r"(?i)(api_key|apikey|api-key)\s*[:=]\s*['\"][^'\"]{8,}['\"]"),
    "Possible secret": re.compile(r"(?i)(secret|secret_key)\s*[:=]\s*['\"][^'\"]{8,}['\"]"),
    "Possible password": re.compile(r"(?i)(password|passwd|pwd)\s*[:=]\s*['\"][^'\"]{4,}['\"]"),
    "Debug mode enabled": re.compile(r"(?i)\bdebug\s*=\s*true\b"),
    "eval usage": re.compile(r"\beval\s*\("),
    "exec usage": re.compile(r"\bexec\s*\("),
}


def _lower_paths(paths: list[str]) -> list[str]:
    return [path.replace("\\", "/").lower() for path in paths]


def _contains_any(text: str, words: set[str]) -> bool:
    lowered = text.lower()
    return any(word in lowered for word in words)


def _recently_updated(updated_at: str | None) -> bool:
    if not updated_at:
        return False
    try:
        parsed = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
    except ValueError:
        return False
    age_days = (datetime.now(timezone.utc) - parsed.astimezone(timezone.utc)).days
    return age_days <= 180


def detect_project_types(repo: dict[str, Any], paths: list[str], readme: str) -> list[str]:
    lower_paths = _lower_paths(paths)
    text = " ".join(
        [
            repo.get("name") or "",
            repo.get("description") or "",
            repo.get("language") or "",
            " ".join(repo.get("topics") or []),
            readme[:5000],
            " ".join(lower_paths[:300]),
        ]
    ).lower()

    types: list[str] = []
    has_package = "package.json" in lower_paths
    has_python_deps = "requirements.txt" in lower_paths or "pyproject.toml" in lower_paths

    if _contains_any(text, AI_KEYWORDS) or any(path.endswith(".ipynb") for path in lower_paths):
        types.append("AI / ML")
    if _contains_any(text, SECURITY_KEYWORDS):
        types.append("Cybersecurity / CTF")
    if has_package or any(path.endswith((".html", ".css", ".jsx", ".tsx")) for path in lower_paths):
        types.append("Frontend")
    if has_python_deps or _contains_any(text, BACKEND_KEYWORDS) or any(
        part in lower_paths for part in ("app.py", "main.py", "server.js", "index.js")
    ):
        types.append("Backend")
    if "Frontend" in types and "Backend" in types:
        types.append("Full-stack App")
    if any(path.endswith(".ipynb") for path in lower_paths):
        types.append("Data Science Notebook")
    if any(path.endswith(".ino") or "arduino" in path or "esp32" in path for path in lower_paths):
        types.append("Hardware / Arduino")
    if _contains_any(text, {"game", "unity", "pygame", "godot"}):
        types.append("Game")
    if _contains_any(text, {"cli", "command-line", "terminal"}) or any(path.startswith("bin/") for path in lower_paths):
        types.append("Utility / CLI")
    if not types and repo.get("language") is None:
        types.append("Documentation-only Repo")
    if not types:
        types.append("General Software Project")

    return list(dict.fromkeys(types))


def scan_security_risks(readme: str, important_file_text: dict[str, str]) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    searchable = {"README": readme, **important_file_text}
    for file_name, text in searchable.items():
        for label, pattern in RISK_PATTERNS.items():
            if pattern.search(text):
                findings.append(
                    {
                        "category": "Security Hygiene",
                        "signal": label,
                        "impact": "negative",
                        "detail": f"{label} pattern detected in {file_name}. Review and remove sensitive or risky code.",
                    }
                )
    return findings[:8]


def scan_repo(
    repo: dict[str, Any],
    paths: list[str],
    readme: str = "",
    important_file_text: dict[str, str] | None = None,
) -> dict[str, Any]:
    important_file_text = important_file_text or {}
    lower_paths = _lower_paths(paths)
    path_blob = " ".join(lower_paths)
    text_blob = " ".join(
        [
            repo.get("name") or "",
            repo.get("description") or "",
            repo.get("language") or "",
            " ".join(repo.get("topics") or []),
            readme,
            path_blob,
            " ".join(important_file_text.values()),
        ]
    )

    has_package_json = "package.json" in lower_paths
    has_requirements = "requirements.txt" in lower_paths or "pyproject.toml" in lower_paths
    has_readme = bool(readme.strip())
    homepage = (repo.get("homepage") or "").strip()

    data = {
        "name": repo.get("name", ""),
        "url": repo.get("html_url") or repo.get("url") or "",
        "description": repo.get("description"),
        "language": repo.get("language"),
        "stars": repo.get("stargazers_count", repo.get("stars", 0)) or 0,
        "forks": repo.get("forks_count", repo.get("forks", 0)) or 0,
        "updated_at": repo.get("updated_at"),
        "created_at": repo.get("created_at"),
        "topics": repo.get("topics") or [],
        "has_readme": has_readme,
        "readme_length": len(readme),
        "has_live_demo": bool(homepage) or _contains_any(readme, {"vercel.app", "netlify.app", "github.io", "render.com", "railway.app"}),
        "has_backend": _contains_any(text_blob, BACKEND_KEYWORDS) or has_requirements,
        "has_frontend": _contains_any(text_blob, FRONTEND_KEYWORDS) or has_package_json or any(path.endswith((".html", ".css", ".jsx", ".tsx")) for path in lower_paths),
        "has_ai": _contains_any(text_blob, AI_KEYWORDS) or any(path.endswith((".ipynb", ".pkl", ".pt", ".h5", ".onnx")) for path in lower_paths),
        "has_security": _contains_any(text_blob, SECURITY_KEYWORDS),
        "has_tests": any(path.startswith(("tests/", "test/")) or "/tests/" in path or path.startswith(".github/workflows/") for path in lower_paths),
        "has_docker": "dockerfile" in lower_paths or "docker-compose.yml" in lower_paths,
        "has_deps_file": has_package_json or has_requirements,
        "has_package_json": has_package_json,
        "has_requirements": has_requirements,
        "has_license": any(path.startswith("license") for path in lower_paths),
        "has_gitignore": ".gitignore" in lower_paths,
        "is_fork": bool(repo.get("fork") or repo.get("is_fork")),
        "file_count": len(lower_paths),
        "folder_count": len({path.split("/")[0] for path in lower_paths if "/" in path}),
        "recently_updated": _recently_updated(repo.get("updated_at")),
    }
    data["project_types"] = detect_project_types(repo, paths, readme)
    data["security_findings"] = scan_security_risks(readme, important_file_text)
    return data
