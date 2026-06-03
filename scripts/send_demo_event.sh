#!/usr/bin/env bash
set -euo pipefail

curl -sS \
  -X POST http://localhost:8080/demo/events/issue \
  -H 'Content-Type: application/json' \
  --data @scripts/demo_issue.json
echo
