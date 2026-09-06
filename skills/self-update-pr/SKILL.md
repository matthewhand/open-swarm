---
name: self-update-pr
description: Open a real GitHub pull request on matthewhand/open-swarm from an in-app coding CLI. Use when the operator asks open-swarm to update itself, prove self-update, or open a trivial docs/test PR on this repo.
---

# Self-update PR (REQ-79 / #424)

You are running **inside open-swarm SPA chat** as a catalogued coding CLI
(claude / codex / agy / opencode / grok). You are **not** Cursor cloud and
**not** Grok Bot. Your job is to open a **real** pull request on
`matthewhand/open-swarm`.

## Working directory

Use the agent's **Folder** (the open-swarm checkout). Do not invent a LAN
host or a preview listen port. Do not write secrets or tokens into the PR,
the Issue, or the chat.

## Allowed change

Smallest honest prove is enough:

- a docs sentence, or
- a test comment / assertion name,

on `matthewhand/open-swarm`. Keep the diff own-diff. No Neon.

## Git / gh

1. Confirm `git remote -v` points at `matthewhand/open-swarm`.
2. Create a branch (`cursor/self-update-prove-…` or similar).
3. Commit the trivial change (Conventional Commits).
4. Push the branch.
5. Open the PR with JSON so Chat can show the View PR card:

```bash
gh pr create --repo matthewhand/open-swarm --title "…" --body "…" --json url,number,title
```

If `--json` is unavailable, print the PR URL on its own line:

`https://github.com/matthewhand/open-swarm/pull/N`

## Honesty

- If `gh` is missing, auth cannot write, or the Folder is not this repo:
  say so in one bubble-less-honest sentence. **Do not invent a PR URL.**
- Do not claim a session was restored unless the CLI actually resumed.
- Record the real PR URL on Issue #424 only after `gh` printed it.

## Out of scope

Chrome polish, remotes, STT/TTS, stacked avatars, Hermes bounce, Neon,
feature-squash of unrelated work.
