from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any

import httpx

from .config import settings


STRUCTURED_OUTPUT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["outcome", "summary"],
    "properties": {
        "outcome": {"type": "string", "enum": ["success", "failed", "needs_human"]},
        "summary": {"type": "string"},
        "branch_name": {"type": "string"},
        "pr_url": {"type": "string"},
        "files_changed": {"type": "array", "items": {"type": "string"}},
        "test_evidence": {"type": "string"},
        "failure_reason": {"type": "string"},
        "next_action": {"type": "string"},
    },
}


def build_prompt(job: dict[str, Any]) -> str:
    repo_url = settings.devin_repo_url or f"https://github.com/{job['repo_full_name']}.git"
    return f"""
You are remediating a GitHub issue in Apache Superset.

Repository:
- Repo: {repo_url}
- Target issue: #{job['issue_number']} - {job['issue_title']}
- Issue URL: {job['issue_url']}

Issue body:
{job['issue_body'] or "(no body provided)"}

Execution requirements:
1. Reproduce or inspect the issue.
2. Implement the smallest credible fix.
3. Run the most targeted validation available.
4. Commit changes to a dedicated branch.
5. Open a pull request if repository permissions allow it.
6. Return final structured output with outcome, summary, branch_name, pr_url, files_changed, and test_evidence.

Business context:
- This session is part of an automated remediation pipeline.
- Prefer high-confidence, low-blast-radius changes.
- If blocked by missing permissions, missing secrets, or inability to reproduce, say so explicitly in structured output.
""".strip()


@dataclass
class DevinSession:
    session_id: str
    status: str
    status_detail: str | None
    structured_output: dict[str, Any] | None
    pull_requests: list[dict[str, Any]]
    acus_consumed: float | None


class DevinClient:
    def __init__(self) -> None:
        self.mock = settings.mock_devin or not (settings.devin_api_key and settings.devin_org_id)

    async def create_session(self, job: dict[str, Any]) -> DevinSession:
        if self.mock:
            return DevinSession(
                session_id=f"mock-devin-{job['id']}",
                status="running",
                status_detail="working",
                structured_output=None,
                pull_requests=[],
                acus_consumed=0.0,
            )

        payload = {
            "prompt": build_prompt(job),
            "repos": [settings.devin_repo_url or f"https://github.com/{job['repo_full_name']}.git"],
            "devin_mode": settings.devin_mode,
            "max_acu_limit": settings.devin_max_acu_limit,
            "tags": ["superset", "automation", "take-home"],
            "structured_output_required": True,
            "structured_output_schema": STRUCTURED_OUTPUT_SCHEMA,
        }
        headers = {"Authorization": f"Bearer {settings.devin_api_key}"}
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{settings.devin_api_base}/v3/organizations/{settings.devin_org_id}/sessions",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            body = response.json()
        return self._to_session(body)

    async def get_session(self, session_id: str) -> DevinSession:
        if self.mock:
            await asyncio.sleep(1)
            structured = {
                "outcome": "success",
                "summary": "Mock run completed. Replace MOCK_DEVIN with a real API key to create a PR.",
                "branch_name": f"devin/mock-fix-{session_id.split('-')[-1]}",
                "pr_url": "https://github.com/example/apache-superset/pull/123",
                "files_changed": ["superset/config.py", "tests/unit/mock_test.py"],
                "test_evidence": "Simulated pytest pass.",
                "next_action": "Swap in real Devin credentials and re-run against your fork.",
            }
            return DevinSession(
                session_id=session_id,
                status="running",
                status_detail="finished",
                structured_output=structured,
                pull_requests=[{"url": structured["pr_url"]}],
                acus_consumed=1.2,
            )

        headers = {"Authorization": f"Bearer {settings.devin_api_key}"}
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.get(
                f"{settings.devin_api_base}/v3/organizations/{settings.devin_org_id}/sessions/{session_id}",
                headers=headers,
            )
            response.raise_for_status()
            body = response.json()
        return self._to_session(body)

    def _to_session(self, body: dict[str, Any]) -> DevinSession:
        return DevinSession(
            session_id=body["session_id"],
            status=body["status"],
            status_detail=body.get("status_detail"),
            structured_output=body.get("structured_output"),
            pull_requests=body.get("pull_requests", []),
            acus_consumed=body.get("acus_consumed"),
        )
