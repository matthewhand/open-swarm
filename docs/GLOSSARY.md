# Glossary (v1 product vocabulary)

Short definitions that match the code and APIs. Prefer these names in docs and UI copy.

Related: [ADR-001 — Primary UI is Django; SPA Chat only](./ADR-001-primary-ui.md);
[ADR-003 — Desktop packaging](./adr/003-desktop-packaging.md) (planned Windows pane of glass).

## Blueprint

A discoverable `BlueprintBase` subclass (`swarm.core.blueprint_base`) that defines a runnable agent workflow: agents, tools/MCP requirements, coordination, and optional config. Selected by OpenAI-compatible `model` id on `/v1/chat/completions` and `/v1/responses`. Live discovery lives in `swarm.core.blueprint_discovery` (the old `swarm.extensions.blueprint` path was removed).

## Team (handoff members — REQ-11)

A **Team** wires API agents, CLI agents, and **remote** agents (Hermes, OpenMausBot, Rakazo, nested open-swarm) so they can **see and talk** to each other via openai-agents **handoff / as_tool**. Remotes are Team *members* (`consult_hermes`, `consult_omb`, `consult_rakazo`, `consult_swarm`). Place or unplace them with `swarm-cli remotes place|unplace` / `PATCH /v1/agent-team/` (`agent_team.members` in `swarm_config.json`). Blueprint: `remote_harness`. Nested swarm is a network remote (own process, own DB); do not auto-add this instance as its own remote.

This is **not** the Django `/teams/` + `/v1/teams/` JSON registry.

## Profiles (`/teams/` — name collision)

`/v1/teams/` and the Django `/teams/` admin store **LLM-profile aliases** (`id`, `description`, `llm_profile`) in `teams.json`. They run through `DynamicTeamBlueprint` — a thin chat proxy to a profile. Prefer calling that surface **Profiles** in new copy. Do not call those aliases a Team.

## Team roster (composition) / Chief of Staff

A **team roster** (`team_rosters.json`, `/v1/team-rosters/`) is a composition
of members `{id, kind: api\|cli\|remote\|team\|herdr, role, source}`. This is
**not** the `/v1/teams` alias. `kind=team` + `team_id` nests a child roster.

**Isolation (REQ-28):** members of Team A cannot `handoff` / `as_tool` to Team B
unless B is a **direct child** of A or the caller is `chief_of_staff` (`cos`,
`chief`). Parent talks to the child team as one member (send-to-all on the
child), not automatically every grandchild. See [TEAM_ISOLATION.md](./TEAM_ISOLATION.md).

## Persona / MoA

Two primary multi-agent styles ([SWARM_WORKFLOWS.md](./SWARM_WORKFLOWS.md)):

| Name | Meaning |
|------|---------|
| **MoA** (Mixture of Agents) | Read-only participant seats → orchestrator determination → optional act / scripted `--team` specialists (`swarm.core.moa`, `swarm-cli moa`). |
| **Persona** (agent-as-tool swarm) | A coordinator switches specialists via the `openai-agents` SDK (handoffs / `as_tool()`). Includes blueprints such as `persona_council` (diverse-lens consensus). |

Do not call `/v1/teams` aliases “MoA teams” or “persona teams.”

## Agent role (support / gate / skeptic / default)

First-class field on an agent spec (`AgentConfig.role`, team `AGENT_SPECS`, `/v1/blueprints/` `role` + `agents[]`). Visual CSS: `os-agent-role-<role>` and `data-role`. Wiring (openai-agents `as_tool` / handoff only — not extra Grok seats):

* **default** — ordinary worker / coordinator
* **support** — Support seat (REQ-7). Talk about gate/skeptic; this repo wires them.
* **gate** (`tool_gate`) — classifies a pending tool call YES/NO (dangerous). Wired → elicit on dangerous. **Unwired → all approved, never prompt.**
* **skeptic** — reviews whether the original prompt was accomplished; on NO, findings go back to the original agent (bounded retries, default 2). On YES, stop — do not nag.

See [AGENT_ROLES.md](./AGENT_ROLES.md).

## CLI Fusion

Wrapping installed agentic CLIs (`grok` / `claude` / `gemini` / …) behind the OpenAI API and composing them (`cli_agent`, `cli_fusion` panel+judge, `cli_orchestrator`, `cli_map`, …). Config: `cli_agents` (+ fusion blocks) in `swarm_config.json`. Docs: [CLI_FUSION.md](./CLI_FUSION.md). Legacy product phrasing; MoA is the preferred name for read-only consensus.

## Session

A stateful `/v1/responses` record (and related conversation/delegation data) owned by an operator or API-token principal. The Django **Session Explorer** at `/sessions/` is a read-only observability UI over those records — not a chat composer.

**Scale-out chat sessions (REQ-66)** are per-agent websocket conversations (`?session=` on SPA Chat). They are not Session Explorer rows. An agent with more than one of these stays one rail row with stacked avatars.
## CLI session

An id **owned by an agentic CLI** (`--resume` / `--session` / `exec resume` / id file). Open Swarm stores it next to the chat thread (`cli_sessions`) and passes it back so the CLI restores its own context (REQ-52). Not a Django `conversation_id`, not a `/v1/responses` Session, and not OS `start_new_session` (process-group kill). Remotes keep the remote’s session.

## Herdr member (`kind=herdr`)

A persisted connection to a [Herdr](https://herdr.dev/) pane/agent that Open Swarm drives via the official `herdr` CLI (not a socket protocol). Empty `remote` means localhost (unix sockets, typically `~/.config/herdr/`). Optional `remote` becomes `herdr --remote <user@host>`. **Remotes kind** (REQ-64): add `herdr` in Settings (base URL + api-key-env); CLI `--remote` uses that configured base; missing config is an error, not a silent other-host. **Not** Hermes, OMB, or Rakazo. Docs: [HERDR.md](./HERDR.md).

## Operator UI vs SPA Chat

| Surface | Role (v1) |
|---------|-----------|
| **Operator UI** | Canonical Django/HTMx trailing-slash chrome: `/teams/launch/`, `/teams/`, `/blueprint-library/`, `/agent-creator/`, `/settings/`, `/sessions/`, … ([ADR-001](./ADR-001-primary-ui.md)). |
| **SPA Chat** | React SPA retains `/` (dashboard) and `/chat` (websocket chat) only. Bare `/teams`, `/blueprints`, `/settings`, `/agent-creator` redirect to Django. Do not remount Builder / AgentCreator SPA pages. |
