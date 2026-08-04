---
name: conventional-commit
description: Writes a single Conventional Commits message from a description of changes or a git diff. Use when the user asks for a commit message, or mentions committing, staging, or a diff.
---

# Conventional Commit

Output exactly one Conventional Commits message and nothing else — no backticks,
no code fences, no commentary.

## Format

```
<type>(<optional scope>): <summary>

<optional body explaining WHY, wrapped at 72 columns>
```

- `<type>`: one of `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`,
  `build`, `ci`, `chore`, `revert`.
- Summary: imperative mood, lower-case, no trailing period, ≤ 72 characters.
- Add a `!` after the type/scope (or a `BREAKING CHANGE:` body footer) for a
  breaking change.

## Examples

Input: Added user authentication with JWT tokens
Output:
feat(auth): add JWT-based login and token validation

Input: Fixed dates rendering in the wrong timezone on reports
Output:
fix(reports): use UTC timestamps in date formatting

Input: Upgraded deps and standardized error responses (drops Node 16)
Output:
chore!: upgrade dependencies and unify error responses

BREAKING CHANGE: drops support for Node 16.
