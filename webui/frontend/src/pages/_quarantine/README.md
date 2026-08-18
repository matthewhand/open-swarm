# Quarantined SPA pages (not mounted)

Per [ADR-001](../../../../../docs/ADR-001-primary-ui.md): the React SPA only
mounts **Dashboard (`/`)** and **Chat (`/chat`)**. These sources are kept for
history / possible future remount — they are **not** imported by `App.tsx`.

| File | Former route | Canonical replacement |
| --- | --- | --- |
| `TeamsPage.tsx` | `/teams` | Django `/teams/` · `/teams/launch/` |
| `BlueprintsPage.tsx` | `/blueprints` | Django `/blueprint-library/` |
| `SettingsPage.tsx` | `/settings` | Django `/settings/` |
| `BuilderPage.tsx` | `/builder` | Django `/agent-creator/` |
| `AgentCreatorPage.tsx` | `/agent-creator` | Django `/agent-creator/` |

Bare paths still **redirect** to Django via `urls.py` when served behind the API.
Do **not** remount these without an explicit product decision.

Vitest / `tsc` exclude this directory (see `vite.config.ts`, `tsconfig.json`).
