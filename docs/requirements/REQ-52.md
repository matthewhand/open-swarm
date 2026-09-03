# REQ-52 — Persist CLI session ids and resume them

**Status:** in flight (Fixes [#369](https://github.com/matthewhand/open-swarm/issues/369))

## Intent

CLI tools own their sessions. Open Swarm tracks each CLI **session id** so when
the user comes back to that CLI agent, we pass the id back and the CLI restores
context. (API threads we own and persist ourselves; remotes are the remote’s
session.)

## Success

- For each catalogued CLI (grok, claude, gemini, codex, opencode; antigravity
  documented but not wired): resume flags live in `cli_catalog.SESSION_RESUME`.
  Swarm stores the id in the REQ-14 chat JSON as `cli_sessions`.
- Resume: the next send to that CLI includes the stored id. Missing/expired id
  starts a new session and we store the new id.
- Honest UI: if a CLI cannot resume, no fake “restored” — a bubble-less status
  line says we started a new session.
- Tests: fixture CLI that echoes `--resume ID`; second turn passes the stored
  id. No secrets in stored records.

## Constraints

- Distinct from #366 (API edit).
- No live preview. No secrets. No Neon.

## Owner

- CoS transcribes
- cloud implements
- engineer GitHub-merge after skeptic
- live preview `10.0.0.30:8001` guest dirty only
