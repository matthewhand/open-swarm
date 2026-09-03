# Glossary (v1 product vocabulary)

Short definitions that match the code and APIs. Prefer these names in docs and UI copy.

Related: [ADR-001 — Primary UI is Django; SPA Chat only](./ADR-001-primary-ui.md).

## Blueprint

A discoverable `BlueprintBase` subclass (`swarm.core.blueprint_base`) that defines a runnable agent workflow: agents, tools/MCP requirements, coordination, and optional config. Selected by OpenAI-compatible `model` id on `/v1/chat/completions` and `/v1/responses`. Live discovery lives in `swarm.core.blueprint_discovery` (the old `swarm.extensions.blueprint` path was removed).

## Team (live vs intended)

| | Meaning |
|---|---|
| **Live today** (`/teams/`, `/v1/teams`) | A named **LLM-profile alias** in `teams.json` (`id`, `description`, `llm_profile`). CRUD via the JSON API and Django `/teams/` admin/launcher. Surfaces as a model id and proxies chat through `DynamicTeamBlueprint` — one profile, no graph. |
| **Intended** | A Team **wires** API / CLI / remote agents so they can **see and talk to each other** (openai-agents handoff / `as_tool`). Same composition axis as the [VISION](./VISION.md) harness-of-harnesses turn. |

**Do not claim Teams Admin already does inter-agent talk.** Multi-agent talk that works today is a **Blueprint** or **MoA** / persona pattern — not `/teams/`. Do not call `/v1/teams` aliases “MoA teams” or “persona teams.”

## Persona / MoA

Two primary multi-agent styles ([SWARM_WORKFLOWS.md](./SWARM_WORKFLOWS.md)):

| Name | Meaning |
|------|---------|
| **MoA** (Mixture of Agents) | Read-only participant seats → orchestrator determination → optional act / scripted `--team` specialists (`swarm.core.moa`, `swarm-cli moa`). |
| **Persona** (agent-as-tool swarm) | A coordinator switches specialists via the `openai-agents` SDK (handoffs / `as_tool()`). Includes blueprints such as `persona_council` (diverse-lens consensus). |

## Harness / Remote / Role (direction)

Intended vocabulary for the harness-of-harnesses turn. See [VISION.md](./VISION.md).

| Name | Meaning | Honesty |
|------|---------|---------|
| **Harness** | An agent runtime you already run (Hermes, OpenMausBot, Rakazo, or an agentic CLI). Open Swarm's intended job is to *compose* those. | Live today: wrap **CLIs** (`cli_agent` / fusion) and in-process openai-agents specialists. `/teams/` is not that composition. |
| **Remote** (REQ-11) | A first-class connection to another harness, invoked by handoff / `as_tool` — not another concurrent Grok/OMB/Rakazo seat. | **Not landed.** Chat has no Remote selector. `harness_fleet` is LAN health probes only. Do not claim remotes work. |
| **Role** (`support` / `gate` / `skeptic`) | Seats in an openai-agents graph (`as_tool` / handoff). Support talks about the roster; gate classifies a pending tool call; skeptic reviews then bounded retry. | **In flight.** Not on `main`. Assigning a role is not an extra concurrent worker. |

**Grok-Bot-like UI** (roster + remotes + Bot chrome) is intended, **not live**. REQ-5 dark chrome on `main` is colour/shell only.

## CLI Fusion

Wrapping installed agentic CLIs (`grok` / `claude` / `gemini` / …) behind the OpenAI API and composing them (`cli_agent`, `cli_fusion` panel+judge, `cli_orchestrator`, `cli_map`, …). Config: `cli_agents` (+ fusion blocks) in `swarm_config.json`. Docs: [CLI_FUSION.md](./CLI_FUSION.md). Legacy product phrasing; MoA is the preferred name for read-only consensus.

## Session

A stateful `/v1/responses` record (and related conversation/delegation data) owned by an operator or API-token principal. The Django **Session Explorer** at `/sessions/` is a read-only observability UI over those records — not a chat composer.

## Operator UI vs SPA Chat

| Surface | Role (v1) |
|---------|-----------|
| **Operator UI** | Canonical Django/HTMx trailing-slash chrome: `/teams/launch/`, `/teams/`, `/blueprint-library/`, `/agent-creator/`, `/settings/`, `/sessions/`, … ([ADR-001](./ADR-001-primary-ui.md)). |
| **SPA Chat** | React SPA retains `/` (dashboard) and `/chat` (websocket chat) only. Bare `/teams`, `/blueprints`, `/settings`, `/agent-creator` redirect to Django. Do not remount Builder / AgentCreator SPA pages. |
