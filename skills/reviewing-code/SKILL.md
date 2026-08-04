---
name: reviewing-code
description: Reviews a diff or file for bugs, security issues, and missing tests, returning prioritized findings. Use when the user asks for a code review, a PR review, or "what's wrong with this code".
---

# Reviewing Code

Review the supplied diff or file and report concrete, actionable findings.
Prefer a few high-signal issues over an exhaustive list of nitpicks.

## Process

1. Read the change and infer its intent.
2. Look, in priority order, for:
   - **Correctness** — logic errors, off-by-one, wrong/missing error handling,
     unhandled `None`/null, race conditions, resource leaks.
   - **Security** — injection, path traversal, secrets in code, unsafe
     deserialization, missing authz/authn checks.
   - **Tests** — untested new behavior; the specific case that would catch a bug.
   - **Clarity** — naming, dead code, or duplication that will mislead the next
     reader. Only if it materially hurts maintainability.
3. Skip style a linter/formatter already enforces.

## Output

For each finding, one bullet:

`- [severity] file:line — problem, then the fix in one clause.`

Use severity `blocker`, `major`, or `minor`. End with a one-line verdict:
`APPROVE`, `APPROVE WITH NITS`, or `REQUEST CHANGES`. If you find nothing
substantive, say so plainly rather than inventing issues.
