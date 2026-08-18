# Glossary (v1 product vocabulary)

Short definitions that match the code and APIs. Prefer these names in docs and UI copy.

Related: [ADR-001 — Primary UI is Django; SPA Chat only](./ADR-001-primary-ui.md).

## Blueprint

A discoverable `BlueprintBase` subclass (`swarm.core.blueprint_base`) that defines a runnable agent workflow: agents, tools/MCP requirements, coordination, and optional config. Selected by OpenAI-compatible `model` id on `/v1/chat/completions` and `/v1/responses`. Live discovery lives in `swarm.core.blueprint_discovery` (not the deprecated `swarm.extensions.blueprint` shim).

## Team (dynamic / `/v1/teams`)

A named **LLM-profile alias** stored in `teams.json` (`id`, `description`, `llm_profile`). CRUD via `/v1/teams/` and the Django `/teams/` admin/launcher. Entries surface as model ids and run through `DynamicTeamBlueprint` — a thin chat proxy to the configured profile.

**Not** a multi-agent team builder or graph editor. For multi-agent workflows, use a **Blueprint** (or MoA / persona patterns below).

## Persona / MoA

Two primary multi-agent styles ([SWARM_WORKFLOWS.md](./SWARM_WORKFLOWS.md)):

| Name | Meaning |
|------|---------|
| **MoA** (Mixture of Agents) | Read-only participant seats → orchestrator determination → optional act / scripted `--team` specialists (`swarm.core.moa`, `swarm-cli moa`). |
| **Persona** (agent-as-tool swarm) | A coordinator switches specialists via the `openai-agents` SDK (handoffs / `as_tool()`). Includes blueprints such as `persona_council` (diverse-lens consensus). |

Do not call `/v1/teams` aliases “MoA teams” or “persona teams.”

## CLI Fusion

Wrapping installed agentic CLIs (`grok` / `claude` / `gemini` / …) behind the OpenAI API and composing them (`cli_agent`, `cli_fusion` panel+judge, `cli_orchestrator`, `cli_map`, …). Config: `cli_agents` (+ fusion blocks) in `swarm_config.json`. Docs: [CLI_FUSION.md](./CLI_FUSION.md). Legacy product phrasing; MoA is the preferred name for read-only consensus.

## Session

A stateful `/v1/responses` record (and related conversation/delegation data) owned by an operator or API-token principal. The Django **Session Explorer** at `/sessions/` is a read-only observability UI over those records — not a chat composer.

## Operator UI vs SPA Chat

| Surface | Role (v1) |
|---------|-----------|
| **Operator UI** | Canonical Django/HTMx trailing-slash chrome: `/teams/launch/`, `/teams/`, `/blueprint-library/`, `/agent-creator/`, `/settings/`, `/sessions/`, … ([ADR-001](./ADR-001-primary-ui.md)). |
| **SPA Chat** | React SPA retains `/` (dashboard) and `/chat` (websocket chat) only. Bare `/teams`, `/blueprints`, `/settings`, `/agent-creator` redirect to Django. Do not remount Builder / AgentCreator SPA pages. |
