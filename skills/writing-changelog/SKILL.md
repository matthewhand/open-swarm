---
name: writing-changelog
description: Writes a Keep a Changelog entry from a description of changes or a git log. Use when the user asks for a changelog entry, release notes, or mentions updating CHANGELOG.md.
---

# Writing a Changelog Entry

Produce a [Keep a Changelog](https://keepachangelog.com) entry for the changes
described. Write for a human reader deciding whether to upgrade — lead with
impact, not implementation.

## Rules

- Group items under these headings only, in this order, omitting empty ones:
  `Added`, `Changed`, `Deprecated`, `Removed`, `Fixed`, `Security`.
- One bullet per user-visible change, imperative mood, present tense
  ("Add X", "Fix Y") — not "Added"/"Fixed" in the bullet itself.
- Describe the effect on the user; mention internals only when they change
  behavior. Collapse purely internal refactors into one line or omit them.
- Reference issues/PRs as `(#123)` when given. No author handles, no dates
  inside bullets.

## Output template

```
## [<version>] - <YYYY-MM-DD>

### Added
- <new capability and why it matters> (#NN)

### Fixed
- <the bug, stated as the symptom the user saw> (#NN)
```

Output only the entry. If a version or date is unknown, use `[Unreleased]` and
omit the date.
