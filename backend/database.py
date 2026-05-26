"""SQLite persistence for SkillProof reports."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from models import HistoryItem, ReportResponse

DB_PATH = Path(__file__).resolve().parent / "skillproof.db"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reports (
                id TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                builder_score INTEGER NOT NULL,
                main_identity TEXT NOT NULL,
                report_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


def save_report(report: ReportResponse) -> None:
    payload = report.model_dump()
    with _connect() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO reports
            (id, username, builder_score, main_identity, report_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                report.id,
                report.username,
                report.builder_score,
                report.main_identity,
                json.dumps(payload),
                report.created_at,
            ),
        )
        conn.commit()


def get_report(report_id: str) -> ReportResponse | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT report_json FROM reports WHERE id = ?",
            (report_id,),
        ).fetchone()
    if not row:
        return None
    data: dict[str, Any] = json.loads(row["report_json"])
    return ReportResponse(**data)


def get_history(limit: int = 20) -> list[HistoryItem]:
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT id, username, builder_score, main_identity, created_at
            FROM reports
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [
        HistoryItem(
            id=row["id"],
            username=row["username"],
            builder_score=row["builder_score"],
            main_identity=row["main_identity"],
            created_at=row["created_at"],
        )
        for row in rows
    ]
