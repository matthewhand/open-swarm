# REQ-170 — Blueprints are not rail agents

Implements [#595](https://github.com/matthewhand/open-swarm/issues/595). Coordinates [#419](https://github.com/matthewhand/open-swarm/issues/419) / [#828](https://github.com/matthewhand/open-swarm/pull/828) (`django_chat` package already gone). Look-only audit: [REQ-171-surface-b-rail-agents.md](./REQ-171-surface-b-rail-agents.md).

## Diagnosis (why recipes appeared as agents)

There is **no** Django “one Agent row per blueprint” seed. Live `:8001` (2026-09-04) had `GET /v1/blueprints/` ≈ 54 `object=blueprint` rows and `marketplace_blueprint` count **0**.

The Grok AGENTS rail and Search Bots mapped that **filesystem catalog** (`get_available_blueprints()` under `src/swarm/blueprints/*`, plus aliases) through `exampleRoleAgents`. Display name is `metadata.name`, often the same as the id (39/54 on that sample) — so Name and Blueprint looked like clones.

Archiving Django seed agents does nothing on that host. Deleting recipe packages would break `?blueprint=` and `/v1/models`. **Filter + optional leftover archive** is the fix. `#419` already retired `django_chat`; leftover ids stay denied on the rail if they reappear.

## SoT: `metadata.rail` (default deny)

`GET /v1/blueprints/` now includes `rail: true|false`. Missing metadata = **false** (catalog-only).

**On the rail:** Support; hide-seeded gate / skeptic; CLI verify rows from `/v1/cli-agents/`; teams / remotes / Herdr / CoS from their own lists; any recipe that sets `rail: true`.

**Off the rail (catalog only):** demo pack (`poets`, `chucks_angels`, MoA / `cli_fusion` aliases, `software_dev`, `codey`, …) and retired `django_chat`. Deep links and `/v1/models` still resolve.

## Cleanup (idempotent, dry-run default)

```bash
# Report leftover marketplace / custom-library demo clones. No writes.
uv run python manage.py cleanup_blueprint_as_agents
uv run python manage.py cleanup_blueprint_as_agents --json

# Archive leftovers only (never deletes user-created seats or recipe packages).
uv run python manage.py cleanup_blueprint_as_agents --apply
```

User-created customs (id not in the demo denylist, `source=wizard|user|custom`, or `rail: true`) are kept. Already-inactive / `archived` rows are skipped.

## Editor rule

When the seat **display name** equals the assigned blueprint **id or name** (case-insensitive), hide the labeled “Blueprint” heading and show `Recipe: {id}` as secondary meta. The picker stays (accessible name still “Blueprint”) so the recipe can change. When the name differs from the recipe, keep the labeled Blueprint picker.

Do not rename catalog slugs so name ≠ id.
