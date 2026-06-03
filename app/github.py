from __future__ import annotations

import hashlib
import hmac
from typing import Any

import httpx

from .config import settings


def verify_signature(raw_body: bytes, signature: str | None) -> bool:
    if not signature:
        return False
    expected = "sha256=" + hmac.new(
        settings.github_webhook_secret.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def parse_issue_event(event: dict[str, Any]) -> dict[str, Any] | None:
    action = event.get("action")
    if action not in {"opened", "labeled", "edited", "reopened"}:
        return None

    issue = event.get("issue") or {}
    repo = event.get("repository") or {}
    labels = {label["name"] for label in issue.get("labels", []) if "name" in label}
    if settings.github_label not in labels:
        return None

    repo_full_name = repo.get("full_name")
    issue_number = issue.get("number")
    if not repo_full_name or issue_number is None:
        return None

    external_id = f"{repo_full_name}#{issue_number}"
    return {
        "external_id": external_id,
        "repo_full_name": repo_full_name,
        "issue_number": issue_number,
        "issue_title": issue.get("title", ""),
        "issue_url": issue.get("html_url", ""),
        "issue_body": issue.get("body", ""),
        "trigger_label": settings.github_label,
        "raw_event": event,
        "labels": sorted(labels),
        "action": action,
    }


def build_issue_comment(job: dict[str, Any]) -> str:
    lines = [
        "### Devin remediation job",
        f"- Job status: `{job['status']}`",
        f"- Mode: `{job['mode']}`",
    ]
    if job.get("devin_session_id"):
        lines.append(f"- Devin session: `{job['devin_session_id']}`")
    if job.get("devin_url"):
        lines.append(f"- Devin URL: {job['devin_url']}")
    if job.get("pr_url"):
        lines.append(f"- PR: {job['pr_url']}")
    if job.get("summary"):
        lines.append(f"- Summary: {job['summary']}")
    if job.get("failure_reason"):
        lines.append(f"- Failure: {job['failure_reason']}")
    return "\n".join(lines)


async def post_issue_comment(job: dict[str, Any]) -> None:
    token = settings.github_issue_comment_token
    if not token:
        return

    url = f"https://api.github.com/repos/{job['repo_full_name']}/issues/{job['issue_number']}/comments"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(url, headers=headers, json={"body": build_issue_comment(job)})
        response.raise_for_status()
