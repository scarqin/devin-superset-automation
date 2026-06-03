from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import settings


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(settings.database_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def get_conn() -> sqlite3.Connection:
    conn = _connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    Path(settings.database_path).parent.mkdir(parents=True, exist_ok=True)
    with get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                external_id TEXT UNIQUE NOT NULL,
                repo_full_name TEXT NOT NULL,
                issue_number INTEGER NOT NULL,
                issue_title TEXT NOT NULL,
                issue_url TEXT NOT NULL,
                issue_body TEXT,
                trigger_label TEXT,
                mode TEXT NOT NULL,
                status TEXT NOT NULL,
                success INTEGER,
                devin_session_id TEXT,
                devin_status TEXT,
                devin_status_detail TEXT,
                devin_url TEXT,
                pr_url TEXT,
                branch_name TEXT,
                summary TEXT,
                failure_reason TEXT,
                raw_event_json TEXT NOT NULL,
                structured_output_json TEXT,
                created_at TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS job_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER NOT NULL,
                level TEXT NOT NULL,
                message TEXT NOT NULL,
                payload_json TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(job_id) REFERENCES jobs(id)
            );
            """
        )


def create_job(payload: dict[str, Any], mode: str) -> int:
    now = utc_now()
    with get_conn() as conn:
        cursor = conn.execute(
            """
            INSERT INTO jobs (
                external_id, repo_full_name, issue_number, issue_title, issue_url, issue_body,
                trigger_label, mode, status, raw_event_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload["external_id"],
                payload["repo_full_name"],
                payload["issue_number"],
                payload["issue_title"],
                payload["issue_url"],
                payload.get("issue_body", ""),
                payload.get("trigger_label"),
                mode,
                "queued",
                json.dumps(payload["raw_event"]),
                now,
                now,
            ),
        )
        return int(cursor.lastrowid)


def log_event(job_id: int, level: str, message: str, payload: dict[str, Any] | None = None) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO job_events (job_id, level, message, payload_json, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (job_id, level, message, json.dumps(payload) if payload else None, utc_now()),
        )


def update_job(job_id: int, **fields: Any) -> None:
    if not fields:
        return
    fields["updated_at"] = utc_now()
    assignments = ", ".join(f"{key} = ?" for key in fields)
    values = list(fields.values()) + [job_id]
    with get_conn() as conn:
        conn.execute(f"UPDATE jobs SET {assignments} WHERE id = ?", values)


def get_job(job_id: int) -> dict[str, Any] | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    return dict(row) if row else None


def get_job_by_external_id(external_id: str) -> dict[str, Any] | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM jobs WHERE external_id = ?", (external_id,)).fetchone()
    return dict(row) if row else None


def list_jobs(limit: int = 50) -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(row) for row in rows]


def list_job_events(job_id: int) -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM job_events WHERE job_id = ? ORDER BY created_at ASC", (job_id,)
        ).fetchall()
    return [dict(row) for row in rows]


def get_stats() -> dict[str, Any]:
    with get_conn() as conn:
        totals = conn.execute(
            """
            SELECT
                COUNT(*) AS total_jobs,
                SUM(CASE WHEN status IN ('completed', 'failed') THEN 1 ELSE 0 END) AS finished_jobs,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) AS successful_jobs,
                SUM(CASE WHEN status IN ('queued', 'running') THEN 1 ELSE 0 END) AS active_jobs
            FROM jobs
            """
        ).fetchone()
        statuses = conn.execute(
            "SELECT status, COUNT(*) AS count FROM jobs GROUP BY status ORDER BY count DESC"
        ).fetchall()
    total_jobs = int(totals["total_jobs"] or 0)
    successful_jobs = int(totals["successful_jobs"] or 0)
    return {
        "total_jobs": total_jobs,
        "finished_jobs": int(totals["finished_jobs"] or 0),
        "successful_jobs": successful_jobs,
        "active_jobs": int(totals["active_jobs"] or 0),
        "success_rate": round((successful_jobs / total_jobs) * 100, 1) if total_jobs else 0.0,
        "status_breakdown": [dict(row) for row in statuses],
    }
