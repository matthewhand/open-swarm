# Glossary (v1 product vocabulary)

Short definitions that match the code and APIs. Prefer these names in docs and UI copy.

Related: [ADR-001 — Primary UI is Django; SPA Chat only](./ADR-001-primary-ui.md).

## Blueprint

A discoverable `BlueprintBase` subclass (`swarm.core.blueprint_base`) that defines a runnable agent workflow: agents, tools/MCP requirements, coordination, and optional config. Selected by OpenAI-compatible `model` id on `/v1/chat/completions` and `/v1/responses`. Live discovery lives in `swarm.core.blueprint_discovery` (the old `swarm.extensions.blueprint` path was removed).

## Team (handoff members — REQ-11)

A **Team** wires API agents, CLI agents, and **remote** agents (Hermes, OpenMausBot, Rakazo) so they can **see and talk** to each other via openai-agents **handoff / as_tool**. Remotes are Team *members* (`consult_hermes`, `consult_omb`, `consult_rakazo`). Place or unplace them with `swarm-cli remotes place|unplace` / `PATCH /v1/agent-team/` (`agent_team.members` in `swarm_config.json`). Blueprint: `remote_harness`.

This is **not** the Django `/teams/` + `/v1/teams/` JSON registry.

## Profiles (`/teams/` — name collision)

`/v1/teams/` and the Django `/teams/` admin store **LLM-profile aliases** (`id`, `description`, `llm_profile`) in `teams.json`. They run through `DynamicTeamBlueprint` — a thin chat proxy to a profile. Prefer calling that surface **Profiles** in new copy. Do not call those aliases a Team.

## Team roster (composition / `team_rosters.json`)

A named **roster of members** (API from a blueprint, CLI, or remote harness) plus per-team openai-agents wire toggles (`handoff`, `as_tool`; both default on). Stored in `team_rosters.json` (`members[{id, kind, role, source}]`). CRUD via `/v1/team-rosters/`. SPA entry is the chat-header **Compose team** `+` overlay (not a top-nav Teams tab). Remotes/CLIs may be placeholders; they are not Blueprint classes.

Docs: [TEAM_ROSTERS.md](./TEAM_ROSTERS.md). Do not call a `/v1/teams` alias a roster. This store does not write `teams.json` or `/v1/agent-team/` config.

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

## Herdr member (`kind=herdr`)

A persisted connection to a [Herdr](https://herdr.dev/) pane/agent that Open Swarm drives via the official `herdr` CLI (not a socket protocol). Empty `remote` means localhost (unix sockets, typically `~/.config/herdr/`). Optional `remote` becomes `herdr --remote <user@host>`. **Not** Hermes, OMB, or Rakazo. Docs: [HERDR.md](./HERDR.md).

## Operator UI vs SPA Chat

| Surface | Role (v1) |
|---------|-----------|
| **Operator UI** | Canonical Django/HTMx trailing-slash chrome: `/teams/launch/`, `/teams/`, `/blueprint-library/`, `/agent-creator/`, `/settings/`, `/sessions/`, … ([ADR-001](./ADR-001-primary-ui.md)). |
| **SPA Chat** | React SPA retains `/` (dashboard) and `/chat` (websocket chat) only. Bare `/teams`, `/blueprints`, `/settings`, `/agent-creator` redirect to Django. Do not remount Builder / AgentCreator SPA pages. |
