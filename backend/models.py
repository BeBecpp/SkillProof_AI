"""Pydantic models for SkillProof AI API."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

GITHUB_USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,37}[a-zA-Z0-9])?$")


class AnalyzeGithubRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=39)

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        username = value.strip()
        if not username:
            raise ValueError("Username cannot be empty")
        if len(username) > 39:
            raise ValueError("Username must be at most 39 characters")
        if not GITHUB_USERNAME_PATTERN.match(username):
            raise ValueError(
                "Username may only contain letters, numbers, and hyphens, "
                "and cannot start or end with a hyphen"
            )
        return username


class Finding(BaseModel):
    category: str
    signal: str
    impact: str  # positive | neutral | negative
    detail: str


class RepoAnalysis(BaseModel):
    name: str
    url: str
    description: str | None = None
    language: str | None = None
    stars: int = 0
    forks: int = 0
    updated_at: str | None = None
    created_at: str | None = None
    has_readme: bool = False
    has_live_demo: bool = False
    has_backend: bool = False
    has_frontend: bool = False
    has_ai: bool = False
    has_security: bool = False
    has_tests: bool = False
    has_docker: bool = False
    is_fork: bool = False
    project_types: list[str] = Field(default_factory=list)
    score: int = 0
    findings: list[Finding] = Field(default_factory=list)


class ReportResponse(BaseModel):
    id: str
    username: str
    avatar_url: str
    github_url: str
    builder_score: int
    main_identity: str
    skill_map: dict[str, int]
    strong_areas: list[str]
    weak_areas: list[str]
    suggested_roles: list[str]
    repos: list[RepoAnalysis]
    ai_summary: str
    improvement_plan: list[str]
    created_at: str


class HistoryItem(BaseModel):
    id: str
    username: str
    builder_score: int
    main_identity: str
    created_at: str


class ErrorResponse(BaseModel):
    detail: str


def report_to_dict(report: ReportResponse) -> dict[str, Any]:
    return report.model_dump()
