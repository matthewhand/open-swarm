# Blueprint Library

A menu of the multi-agent workflows ("blueprints") Open Swarm ships, each chosen
to demonstrate a specific framework feature. Pick one by its `model` name over
the OpenAI API, run it with `swarm-cli launch <name>`, or use it as a starting
point for your own.

**Status legend**

| Mark | Meaning |
|------|---------|
| ✅ | Deep tests + verified live (incl. grok where CLI-backed) |
| 🟢 | Discovered and answers over the API (smoke-matrix verified) — dedicated feature test pending |
| 🔧 | Present in-tree but **not discovered** (needs a fix to join the library) |
| 📋 | Removed in the FOSS cleanup — reintroduction candidate (resurrect, modernize, test) |

This is a living document: the build-out loop adds a dedicated feature test (and
grok verification for CLI-backed ones) to each 🟢 row, fixes the 🔧 rows, and
reintroduces 📋 rows that demonstrate a feature not already covered.

---

## CLI Agent Fusion — drive your installed CLIs (claude / grok / gemini / …)

| Blueprint | Feature it demonstrates | Status |
|---|---|---|
| `cli_agent` | One external CLI behind the OpenAI API; streaming; failover | ✅ |
| `cli_fusion` | Multi-CLI **consensus** (panel → judge → synthesize) | ✅ |
| `cli_orchestrator` | **Granular** consensus — cheap router escalates only hard questions | ✅ |
| `cli_map` | **Decompose → distribute → reduce** (map-reduce across CLIs) | ✅ |

All four verified live with **grok** driving every role (panelist, judge, router, planner, worker, reducer).

## Coding & developer workflows

| Blueprint | Feature it demonstrates | Status |
|---|---|---|
| `codey` | Code generation + semantic code search/analysis; approval-mode | 🟢 |
| `rue_code` | Code execution + filesystem interaction | 🟢 |
| `whinge_surf` | Async subprocess job management (launch / poll / review) | 🟢 |

## Multi-agent coordination & delegation

| Blueprint | Feature it demonstrates | Status |
|---|---|---|
| `geese` | Researcher/coordinator pattern with memory | 🟢 |
| `zeus` | General-purpose team launcher (agent-as-tool delegation) | 🟢 |
| `dynamic_team` | Dynamically-registered team from a configured LLM profile | 🟢 |
| `chucks_angels` | Themed task coordination | 🟢 |
| `digitalbutlers` | Butler-style delegation | 🔧 present, not discovered |
| `flock` | Agent flock/swarm coordination | 🔧 present, not discovered |

## Structured output, tools & integrations

| Blueprint | Feature it demonstrates | Status |
|---|---|---|
| `suggestion` | **Structured output** via `Agent(output_type=…)` | 🟢 |
| `jeeves` | Private web search (DuckDuckGo) + home automation delegation | 🟢 |
| `stewie` | **MCP** integration (WordPress CMS via MCP tools) | 🟢 |
| `whiskeytango_foxtrot` | Hierarchical multi-agent + SQLite + web scraping | 🟢 |
| `poets` | SQLite-backed collaborative creative writing | 🟢 |
| `django_chat` | Web chat with conversation-history management | 🟢 |

## Reintroduction candidates (removed in the FOSS cleanup)

Each is a 📋 candidate — resurrect from git history, modernize to current
`BlueprintBase`, add a feature test. Ordered by the feature they'd add:

| Blueprint | Feature it would demonstrate |
|---|---|
| `echocraft` | Minimal "hello world" blueprint (the simplest template) |
| `chatbot` | Bare single-agent chat |
| `mcp_demo` | Focused MCP-server usage demo |
| `nebula_shellz` | Agent-as-tool + `@function_tool` for shell/code |
| `monkai_magic` | External-CLI function tools (AWS/Fly/Vercel cloud ops) |
| `mission_improbable` · `burnt_noodles` · `dilbot_universe` · `gaggle` · `gotchaman` · `omniplex` · `unapologetic_press` | Misc themed multi-agent demos — triage each for a unique feature before resurrecting |

> `family_ties` was **renamed** to `stewie` (already in the library), not removed.
