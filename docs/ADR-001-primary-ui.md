# ADR-001: Primary UI is Django; SPA Chat only

- **Status:** Accepted (2026-08-18)
- **Context:** Open Swarm grew a Django/HTMx operator UI and a React SPA in parallel. Builder/AgentCreator SPA routes were unmounted; Teams/Blueprints SPA pages are leftovers while bare paths redirect to Django. Dual maintenance and confused docs were flagged as a senior-review P0.

## Decision
1. **Canonical operator chrome** = Django trailing-slash routes (`/teams/launch/`, `/blueprint-library/`, `/agent-creator/`, `/settings/`, `/sessions/`, …).
2. **SPA retains** `/` (dashboard) and `/chat` (websocket chat) only.
3. **Do not remount** `BuilderPage` / `AgentCreatorPage`. Quarantine or delete leftover SPA pages (`TeamsPage`, `BlueprintsPage`, `SettingsPage`, Builder, AgentCreator).
4. Bare `/teams`, `/blueprints`, `/settings`, `/agent-creator` continue to **redirect to Django**.

## Consequences
- Update FEATURE_STATUS, ROADMAP, GUIDED_TOUR, SCREENSHOTS, a11y/shots/e2e to match.
- Rebuild SPA after route cuts (`dist/` is gitignored).
- Future “Builder” work, if any, belongs on Django or a new intentional SPA milestone — not silent remounts.

## Rejected alternative
SPA-primary rewrite — too large for incremental finish; contradicts current verified Django operator path.
