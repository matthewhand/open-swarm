# REQ-24 — Drag any agent incl. roles into Hidden drop zone

**Status:** in flight (no PR number in this backlog slice)

## Intent

Hide is a **drop zone**, not only a context-menu. Any agent — including
**role** seats (support / gate / skeptic / default) — can be dragged there.

## Success

- Drag any AGENTS / conversation row onto a Hidden drop zone → that id joins `localStorage.swarm_hidden_agents`.
- Role-badged rows (REQ-9) are eligible. Support can be hidden if the user does it (first-load default is REQ-26).
- Unhide remains per-row from the `N hidden` popup (REQ-8). **No Hide-all.**
- Pin / favourite (REQ-10) is a copy; hide does not have to unpin unless the implementer proves that is clearer.

## Constraints

- Native HTML5 drag. No `@dnd-kit`.
- Do not hide-all. Do not re-seed hide on every load (REQ-26).
- No Neon. No oracle. Docs-only on this filing PR — do not implement here.

## Owner

- CoS transcribes
- cloud implements
- engineer GitHub-merge after skeptic
- live preview `10.0.0.30:8001` guest dirty only
