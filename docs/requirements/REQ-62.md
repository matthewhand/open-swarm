# REQ-62 — OpenMousBot remote — add, list, send (kind complete)

**Status:** in flight (#388)

## Intent

OpenMousBot is a complete remote kind: after the user + adds it, Settings can
health / list / send. UI label is OpenMousBot, never OMB.

## Success

1. Kind id may stay `omb`. User-facing string is **OpenMousBot** everywhere.
2. After add (base URL + optional api-key-env), Settings shows that remote:
   health, list bots, send message to a bot id.
3. DOWN is a report, not a crash.
4. Tests: stub `/api/health`, `/api/bots`, send; no live LAN; no tokens in repo.
5. HTTP adapter only — no OpenMousBot source clone.

## Constraints

- Compatible with #384 and #380. Reuse remotes / Herdr stack.
- GitHub-only. No `:8001`. No Neon. No secrets.
- One Cursor cloud. `Fixes` this issue. Do not fold into 344.

## Owner

- CoS transcribes
- cloud implements
- engineer GitHub-merge after skeptic
