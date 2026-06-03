# Suggested Superset Issue Seeds

Use these as the issues you create in your Superset fork. They are deliberately scoped for a 2-3 hour take-home and fit a "high-confidence autonomous remediation" story.

## Issue 1: Config validation hardening

Title:
`Validate cache-related config before bootstrap to avoid unsafe defaults`

Body:
`Some cache/bootstrap configuration paths accept loosely typed values and fail late. Add targeted validation near the entry point plus a regression test so invalid config is rejected early with a clear error. Keep the blast radius minimal.`

Why it works:
- Small, bounded fix
- Easy for Devin to inspect, patch, and test
- VP-friendly story: prevent misconfiguration incidents before runtime

## Issue 2: Lintable cleanup with regression test

Title:
`Refactor duplicated parsing helper in Superset and add regression coverage`

Body:
`There is a narrow helper path with duplicated parsing logic. Consolidate it into one function, preserve behavior, and add regression coverage for the branch that previously relied on duplicated logic. Prefer a minimal refactor without changing public APIs.`

Why it works:
- Good code-quality remediation example
- Lets you show Devin doing repo exploration, patching, and test execution

## Recommended labeling

Add the label:
`devin-remediate`

That label is the event trigger this automation listens for.
