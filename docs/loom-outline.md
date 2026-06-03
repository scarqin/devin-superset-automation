# 5 Minute Loom Outline

## 0:00-0:45 What

I built an event-driven remediation system for Apache Superset issues. When a scoped issue is labeled `devin-remediate`, the system creates a Devin session that inspects the repo, implements a fix, runs targeted validation, and produces a PR or an explicit blocked result.

## 0:45-2:15 How

Walk through:

- GitHub issues webhook as the event source
- FastAPI orchestration service
- Devin API session creation with a repo-scoped prompt
- polling loop and structured output
- SQLite-backed dashboard for observability

Show the live flow:

- issue
- dashboard
- Devin session
- PR/output

## 2:15-3:45 Why Devin

The unique value is that Devin is not a classifier in the loop. It is the software engineer in the loop.

This automation can:

- inspect a large codebase
- decide where to patch
- edit code
- run validation
- create a branch and PR

Traditional automation could route tickets, label issues, or summarize findings, but it would still hand the real engineering work back to humans.

## 3:45-5:00 When

Next steps in a real deployment:

- route issue classes to different playbooks
- ingest scan results or Jira/Linear tickets, not just GitHub issues
- add Slack notifications and auto-comments
- enforce policy gates before PR creation
- use session metrics to tune cost, throughput, and success rate by issue class
