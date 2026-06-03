# Submission Runbook

## 1. Fork Superset

Create a GitHub fork of:

`https://github.com/apache/superset`

Then point the automation at your fork in `.env`:

`DEVIN_REPO_URL=https://github.com/<your-user>/superset.git`

## 2. Create issues in your fork

Use the issue ideas from [superset-issue-seeds.md](/Users/scarqin/devin-superset-automation/docs/superset-issue-seeds.md:1).

For each issue:

1. Create the issue in your fork
2. Add the label `devin-remediate`
3. Keep the scope bounded and testable

## 3. Expose your local webhook receiver

If GitHub cannot reach your local machine directly, use a tunnel:

```bash
ngrok http 8080
```

Then configure the GitHub webhook payload URL as:

`https://<ngrok-id>.ngrok.app/webhooks/github`

## 4. Switch from mock to real Devin

Update `.env`:

```bash
MOCK_DEVIN=false
DEVIN_API_KEY=...
DEVIN_ORG_ID=org-...
DEVIN_REPO_URL=https://github.com/<your-user>/superset.git
```

Important:
- The service user needs org permissions to create and view sessions.
- Devin must have repo access to your Superset fork or be able to authenticate inside the session.

## 5. Run the service

```bash
docker compose up --build
```

## 6. Validate the flow

Expected path:

1. New labeled issue appears in your Superset fork
2. GitHub sends webhook
3. Dashboard shows a new queued job
4. Job transitions to running with a Devin session ID
5. Job finishes with success/failure and, ideally, a PR URL

## 7. Record Loom

Suggested recording sequence:

1. Show the labeled issue in your Superset fork
2. Show the webhook configuration
3. Trigger or relabel the issue
4. Show the dashboard updating
5. Open the Devin session
6. Show the generated PR or structured failure state
7. Close with the operating model and next-step roadmap
