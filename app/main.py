from __future__ import annotations

import json

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from . import db
from .github import parse_issue_event, verify_signature
from .service import AutomationService


app = FastAPI(title="Devin Superset Automation")
templates = Jinja2Templates(directory="app/templates")
service = AutomationService()


@app.on_event("startup")
async def startup() -> None:
    db.init_db()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request) -> HTMLResponse:
    stats = db.get_stats()
    jobs = db.list_jobs(limit=25)
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "stats": stats, "jobs": jobs},
    )


@app.get("/api/jobs")
async def api_jobs() -> dict[str, object]:
    return {"jobs": db.list_jobs(limit=100), "stats": db.get_stats()}


@app.get("/api/jobs/{job_id}")
async def api_job(job_id: int) -> dict[str, object]:
    job = db.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    events = db.list_job_events(job_id)
    return {"job": job, "events": events}


@app.post("/webhooks/github")
async def github_webhook(request: Request) -> JSONResponse:
    raw = await request.body()
    signature = request.headers.get("X-Hub-Signature-256")
    event_name = request.headers.get("X-GitHub-Event")
    if event_name != "issues":
        return JSONResponse({"accepted": False, "reason": "unsupported_event"}, status_code=202)
    if not verify_signature(raw, signature):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    payload = json.loads(raw.decode("utf-8"))
    issue_payload = parse_issue_event(payload)
    if not issue_payload:
        return JSONResponse({"accepted": False, "reason": "ignored"}, status_code=202)

    job = await service.enqueue_issue(issue_payload)
    return JSONResponse({"accepted": True, "job_id": job["id"]}, status_code=202)


@app.post("/demo/events/issue")
async def demo_issue(payload: dict[str, object]) -> JSONResponse:
    issue_payload = {
        "external_id": f"{payload['repo_full_name']}#{payload['issue_number']}",
        "repo_full_name": payload["repo_full_name"],
        "issue_number": payload["issue_number"],
        "issue_title": payload["issue_title"],
        "issue_url": payload["issue_url"],
        "issue_body": payload.get("issue_body", ""),
        "trigger_label": payload.get("trigger_label", "devin-remediate"),
        "raw_event": payload,
    }
    job = await service.enqueue_issue(issue_payload)
    return JSONResponse({"accepted": True, "job_id": job["id"]}, status_code=202)
