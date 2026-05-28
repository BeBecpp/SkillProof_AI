"""GitHub API analyzer for SkillProof AI.

The scanner uses public GitHub endpoints and an optional GITHUB_TOKEN for higher
rate limits. It intentionally reads public metadata and small text files only.
"""

from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from repo_scanner import scan_repo

GITHUB_API = "https://api.github.com"
MAX_REPOS = int(os.getenv("MAX_REPOS", "5"))
MAX_FILES_PER_REPO = int(os.getenv("MAX_FILES_PER_REPO", "500"))
FETCH_IMPORTANT_FILES = os.getenv("FETCH_IMPORTANT_FILES", "false").strip().lower() == "true"
IMPORTANT_TEXT_FILES = {
    "requirements.txt",
    "pyproject.toml",
    "package.json",
    "dockerfile",
    "docker-compose.yml",
    "render.yaml",
    "procfile",
    ".env.example",
    "app.py",
    "main.py",
    "server.js",
    "index.js",
}


class GitHubAPIError(RuntimeError):
    """Raised when GitHub cannot return public profile data."""


def _headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "SkillProof-AI-MVP",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.getenv("GITHUB_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _request_json(path_or_url: str) -> Any:
    url = path_or_url if path_or_url.startswith("http") else f"{GITHUB_API}{path_or_url}"
    req = urllib.request.Request(url, headers=_headers())
    try:
        with urllib.request.urlopen(req, timeout=8) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise GitHubAPIError("GitHub user or repository was not found.") from exc
        if exc.code in {403, 429}:
            raise GitHubAPIError("GitHub API rate limit reached. Add GITHUB_TOKEN in backend/.env.") from exc
        raise GitHubAPIError(f"GitHub API request failed with status {exc.code}.") from exc
    except urllib.error.URLError as exc:
        raise GitHubAPIError("Could not connect to GitHub API.") from exc


def _fetch_user(username: str) -> dict[str, Any]:
    return _request_json(f"/users/{urllib.parse.quote(username)}")


def _fetch_repositories(username: str) -> list[dict[str, Any]]:
    repos = _request_json(
        f"/users/{urllib.parse.quote(username)}/repos?per_page=100&sort=updated&type=owner"
    )
    if not isinstance(repos, list):
        return []
    public_repos = [repo for repo in repos if not repo.get("private")]
    return public_repos[:MAX_REPOS]


def _fetch_tree(owner: str, repo: str, branch: str) -> list[str]:
    encoded_owner = urllib.parse.quote(owner)
    encoded_repo = urllib.parse.quote(repo)
    encoded_branch = urllib.parse.quote(branch)
    tree = _request_json(f"/repos/{encoded_owner}/{encoded_repo}/git/trees/{encoded_branch}?recursive=1")
    items = tree.get("tree", []) if isinstance(tree, dict) else []
    paths = [item.get("path", "") for item in items if item.get("type") == "blob" and item.get("path")]
    return paths[:MAX_FILES_PER_REPO]


def _fetch_readme(owner: str, repo: str) -> str:
    encoded_owner = urllib.parse.quote(owner)
    encoded_repo = urllib.parse.quote(repo)
    try:
        payload = _request_json(f"/repos/{encoded_owner}/{encoded_repo}/readme")
    except GitHubAPIError:
        return ""
    if not isinstance(payload, dict):
        return ""
    content = payload.get("content", "")
    if payload.get("encoding") == "base64" and content:
        try:
            return base64.b64decode(content).decode("utf-8", errors="replace")
        except ValueError:
            return ""
    return ""


def _fetch_file_text(owner: str, repo: str, path: str) -> str:
    encoded_owner = urllib.parse.quote(owner)
    encoded_repo = urllib.parse.quote(repo)
    encoded_path = urllib.parse.quote(path)
    try:
        payload = _request_json(f"/repos/{encoded_owner}/{encoded_repo}/contents/{encoded_path}")
    except GitHubAPIError:
        return ""
    if not isinstance(payload, dict) or payload.get("encoding") != "base64":
        return ""
    try:
        raw = base64.b64decode(payload.get("content", ""))
    except ValueError:
        return ""
    if len(raw) > 120_000:
        return ""
    return raw.decode("utf-8", errors="replace")


def _important_text(owner: str, repo: str, paths: list[str]) -> dict[str, str]:
    if not FETCH_IMPORTANT_FILES:
        return {}
    selected: dict[str, str] = {}
    for path in paths:
        normalized = path.lower().split("/")[-1]
        if normalized in IMPORTANT_TEXT_FILES or path.lower() in IMPORTANT_TEXT_FILES:
            text = _fetch_file_text(owner, repo, path)
            if text:
                selected[path] = text[:20_000]
        if len(selected) >= 4:
            break
    return selected


def analyze_user(username: str) -> dict[str, Any]:
    user = _fetch_user(username)
    owner = user.get("login") or username
    repos: list[dict[str, Any]] = []

    for repo in _fetch_repositories(owner):
        name = repo.get("name")
        if not name:
            continue
        default_branch = repo.get("default_branch") or "main"
        try:
            paths = _fetch_tree(owner, name, default_branch)
        except GitHubAPIError:
            paths = []
        readme = _fetch_readme(owner, name)
        important_text = _important_text(owner, name, paths)
        scanned = scan_repo(repo, paths, readme, important_text)
        repos.append(scanned)

    return {
        "username": owner,
        "avatar_url": user.get("avatar_url") or f"https://github.com/{owner}.png",
        "github_url": user.get("html_url") or f"https://github.com/{owner}",
        "repos": repos,
    }


def analyze_github_user(username: str) -> dict[str, Any]:
    return analyze_user(username)
