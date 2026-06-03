# Devin Superset Automation

Event-driven automation that turns labeled GitHub issues in an Apache Superset fork into Devin remediation sessions, then surfaces status and outcomes in a lightweight engineering dashboard.

## What this solves

This project pitches Devin as an autonomous remediation layer for repetitive engineering work:

- A GitHub issue is created for a bounded remediation task.
- A webhook triggers the automation service.
- The service creates and monitors a Devin session via the Devin API.
- Engineering leaders can see throughput, active work, success/failure signals, and generated outputs like PRs.

The target repository for the take-home is Apache Superset:

- Upstream: `https://github.com/apache/superset`
- Your fork: `https://github.com/scarqin/superset`

## Proven Outcome

This repository has been validated against a real Superset fork and a real Devin enterprise org.

- Trigger issue: `https://github.com/scarqin/superset/issues/4`
- Devin session: `https://app.devin.ai/sessions/6eeb7d1340384f08b2248c09a8f1371e`
- Generated PR: `https://github.com/scarqin/superset/pull/5`

Observed result:

- GitHub issue webhook triggered the automation service
- The service created a Devin session via the v3 API
- Devin implemented a bounded code fix in Superset
- Devin ran targeted validation and returned structured output
- Devin pushed a branch and opened a PR automatically

## Architecture

1. `GitHub Issues webhook`
   Sends `issues` events to the automation service.
2. `FastAPI orchestration service`
   Verifies webhook signatures, filters for the `devin-remediate` label, creates remediation jobs, and polls Devin.
3. `Devin API client`
   Creates a session in your enterprise org using a repo-scoped prompt and structured output schema.
4. `SQLite + dashboard`
   Tracks job lifecycle, logs, success rate, and outputs for a technical audience.

## Why Devin is the core primitive

This system is not just calling an LLM for advice. It delegates the actual software engineering loop to Devin:

- repo inspection
- implementation
- targeted validation
- branch + PR creation
- structured completion output

Without an autonomous coding agent, you would still need glue code plus a human to do the actual repository work. Here, the automation system only decides when to invoke Devin, what context to provide, and how to observe outcomes.

## Run locally

### 1. Configure env

```bash
cd /Users/scarqin/devin-superset-automation
cp .env.example .env
```

For a local demo without Devin credentials, keep:

```bash
MOCK_DEVIN=true
```

For a real run, set:

```bash
MOCK_DEVIN=false
DEVIN_API_KEY=...
DEVIN_ORG_ID=org-...
DEVIN_REPO_URL=https://github.com/<your-user>/superset.git
GITHUB_WEBHOOK_SECRET=...
```

### 2. Start with Docker

```bash
docker compose up --build
```

Open:

`http://localhost:8080`

### 3. Simulate an issue event

```bash
./scripts/send_demo_event.sh
```

The dashboard will show a remediation job and, in mock mode, a simulated PR/result.

## GitHub webhook setup

In your Superset fork:

1. Go to `Settings -> Webhooks`
2. Add payload URL: `http://<your-host>:8080/webhooks/github`
3. Content type: `application/json`
4. Secret: match `GITHUB_WEBHOOK_SECRET`
5. Subscribe to `Issues`

Trigger the workflow by creating or labeling an issue with:

`devin-remediate`

## Real Devin behavior

When not in mock mode, the service calls:

- `POST /v3/organizations/{org_id}/sessions`
- `GET /v3/organizations/{org_id}/sessions/{devin_id}`

The session prompt instructs Devin to:

- inspect the Superset issue
- implement the smallest credible fix
- run targeted validation
- create a branch and PR if permissions allow
- return structured output for observability

## Observability

The dashboard and `/api/jobs` answer the core leadership question: "How do I know this is working?"

- active vs completed jobs
- success rate
- per-job status and Devin session links
- PR URLs when produced
- failure reasons when blocked

For this take-home, the automation recorded both:

- blocked runs caused by missing GitHub write permission
- a successful end-to-end run after repository access was granted

## Suggested issues for your fork

See [docs/superset-issue-seeds.md](/Users/scarqin/devin-superset-automation/docs/superset-issue-seeds.md:1) for two bounded issue ideas that fit the take-home scope.

## Submission helpers

- [docs/runbook.md](/Users/scarqin/devin-superset-automation/docs/runbook.md:1)
- [docs/loom-outline.md](/Users/scarqin/devin-superset-automation/docs/loom-outline.md:1)

## Recommended Loom structure

### What

Show the manual pain:
- triaging small repo issues
- assigning engineers
- waiting for fixes and PRs

### How

Demo:
- labeled GitHub issue
- webhook arriving
- Devin session being created
- dashboard updating
- PR/result attached back to the workflow

### Why

Argue that Devin is uniquely useful because it closes the loop from event to code change, not just classification or summarization.

### When

Extensions:
- multiple issue classes
- scheduled backlog sweeps
- Jira/Linear ingestion
- automatic issue comments and Slack notifications
- policy-based routing to fast vs normal Devin mode

## Known gaps

- GitHub issue comments/status updates are only posted back when `GITHUB_TOKEN` is configured.
- Duplicate issue events are intentionally ignored by `external_id`; if you want to re-run the same issue, create a new issue or add a rerun endpoint/override.
- The service currently treats `waiting_for_user` plus structured output as terminal so leadership reporting stays accurate, but a richer production workflow would branch into explicit approval / remediation states.

## Devin API references

- Overview: `https://docs.devin.ai/api-reference/overview`
- Create Session: `https://docs.devin.ai/api-reference/v3/sessions/post-organizations-sessions`
- Get Session: `https://docs.devin.ai/api-reference/v3/sessions/get-organizations-session`
- Send Session Message: `https://docs.devin.ai/api-reference/v3/sessions/post-organizations-sessions-messages`
