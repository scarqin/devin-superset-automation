from __future__ import annotations

import asyncio
import json
from typing import Any

from . import db
from .config import settings
from .devin import DevinClient
from .github import post_issue_comment


class AutomationService:
    def __init__(self) -> None:
        self.devin = DevinClient()

    async def enqueue_issue(self, issue_payload: dict[str, Any]) -> dict[str, Any]:
        existing = db.get_job_by_external_id(issue_payload["external_id"])
        if existing:
            db.log_event(existing["id"], "info", "Duplicate webhook ignored", issue_payload)
            return existing

        mode = "mock" if self.devin.mock else "live"
        job_id = db.create_job(issue_payload, mode=mode)
        db.log_event(job_id, "info", "Job created from webhook", issue_payload)
        asyncio.create_task(self._run_job(job_id))
        return db.get_job(job_id) or {"id": job_id}

    async def _run_job(self, job_id: int) -> None:
        job = db.get_job(job_id)
        if not job:
            return

        db.update_job(job_id, status="running", started_at=db.utc_now())
        db.log_event(job_id, "info", "Starting Devin remediation session")

        try:
            session = await self.devin.create_session(job)
            devin_url = f"https://app.devin.ai/sessions/{session.session_id}"
            db.update_job(
                job_id,
                devin_session_id=session.session_id,
                devin_status=session.status,
                devin_status_detail=session.status_detail,
                devin_url=devin_url,
            )
            db.log_event(job_id, "info", "Devin session created", {"session_id": session.session_id})

            while True:
                latest = await self.devin.get_session(session.session_id)
                db.update_job(
                    job_id,
                    devin_status=latest.status,
                    devin_status_detail=latest.status_detail,
                    structured_output_json=(
                        None if latest.structured_output is None else json.dumps(latest.structured_output)
                    ),
                )
                terminal = self._is_terminal_session(latest)
                if terminal:
                    self._finalize_job(job_id, latest)
                    return
                await asyncio.sleep(settings.devin_poll_interval_seconds)
        except Exception as exc:
            db.update_job(
                job_id,
                status="failed",
                success=0,
                failure_reason=str(exc),
                completed_at=db.utc_now(),
            )
            db.log_event(job_id, "error", "Job failed before completion", {"error": str(exc)})

    def _is_terminal_session(self, latest: Any) -> bool:
        if latest.status in {"exit", "error"}:
            return True
        if latest.status_detail in {
            "finished",
            "error",
            "out_of_credits",
            "payment_declined",
            "usage_limit_exceeded",
        }:
            return True
        # Treat structured handoff as terminal for automation observability.
        if latest.status_detail == "waiting_for_user" and latest.structured_output:
            return True
        return False

    def _finalize_job(self, job_id: int, latest: Any) -> None:
        output = latest.structured_output or {}
        pr_url = output.get("pr_url")
        if not pr_url and latest.pull_requests:
            pr_url = latest.pull_requests[0].get("url")

        outcome = output.get("outcome", "failed")
        success = 1 if outcome == "success" else 0
        status = "completed" if success else "failed"
        db.update_job(
            job_id,
            status=status,
            success=success,
            completed_at=db.utc_now(),
            summary=output.get("summary"),
            branch_name=output.get("branch_name"),
            pr_url=pr_url,
            failure_reason=output.get("failure_reason"),
            structured_output_json=(
                None if latest.structured_output is None else json.dumps(latest.structured_output)
            ),
        )
        db.log_event(
            job_id,
            "info" if success else "error",
            "Devin session reached terminal state",
            {
                "status": latest.status,
                "status_detail": latest.status_detail,
                "outcome": outcome,
                "pr_url": pr_url,
                "acus_consumed": latest.acus_consumed,
            },
        )
        job = db.get_job(job_id)
        if job:
            asyncio.create_task(post_issue_comment(job))

    async def reconcile_job(self, job_id: int) -> dict[str, Any] | None:
        job = db.get_job(job_id)
        if not job or not job.get("devin_session_id"):
            return job
        latest = await self.devin.get_session(job["devin_session_id"])
        db.update_job(
            job_id,
            devin_status=latest.status,
            devin_status_detail=latest.status_detail,
            structured_output_json=(
                None if latest.structured_output is None else json.dumps(latest.structured_output)
            ),
        )
        if self._is_terminal_session(latest):
            self._finalize_job(job_id, latest)
        return db.get_job(job_id)
