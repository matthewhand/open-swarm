# Swarm Configuration Guide

## Quickstart: Configuring Swarm

Swarm supports both interactive and manual configuration. The recommended way to set up and manage your config is via the `swarm-cli`, which provides commands to initialize, edit, and validate your configuration interactively. However, you can also hand-edit the config JSON if you prefer full control or need to automate deployment.

- **Interactive:**
  - Run `swarm-cli configure` to launch guided setup for LLMs, MCP servers, blueprints, and more.
  - Use `swarm-cli list-config` to view your current configuration.
  - Use `swarm-cli set <section> <key> <value>` to update specific values.
- **Manual:**
  - Edit `~/.config/swarm/swarm_config.json` directly (or wherever your config is located).

---

## 1. Config File Location and Discovery

**Recommended location:** `~/.config/swarm/swarm_config.json` (XDG Base Directory
Spec — overridable with `XDG_CONFIG_HOME`).

Config is resolved in this order:

1. `SWARM_CONFIG_PATH` (explicit absolute path) — wins if set and the file exists.
2. **XDG**: `~/.config/swarm/swarm_config.json` (or `$XDG_CONFIG_HOME/swarm/…`).
3. `./swarm_config.json` in the current working directory.

So dropping a config at `~/.config/swarm/swarm_config.json` is enough — both
`swarm-cli` and the API server (`swarm-api` / `manage.py runserver`) pick it up
with no environment variable. Set `SWARM_CONFIG_PATH` only when you want to point
at a non-standard path explicitly. (`swarm-cli` additionally does an upward
directory search for a project-local `swarm_config.json`.)

- **If missing:** Swarm generates a default config using `OPENAI_API_KEY` and the official OpenAI endpoint (with a warning).

> Paths and all environment variables (`SWARM_CONFIG_PATH`, `SWARM_RESPONSES_DIR`,
> server/auth/feature flags, provider keys) are consolidated in one place:
> **[Environment Variables](#environment-variables)** below.

---

## 2. Example Config Structure

```json
{
  "llm": {
    "gpt-4o": {
      "provider": "openai",
      "model": "gpt-4o",
      "api_key": "${OPENAI_API_KEY}",
      "base_url": "https://api.openai.com/v1",
      "pricing": { "prompt": 0.000005, "completion": 0.000015, "unit": "per_token" }
    },
    "o3-mini": {
      "provider": "openrouter",
      "model": "openrouter/o3-mini",
      "api_key": "${OPENROUTER_API_KEY}",
      "base_url": "https://openrouter.ai/api/v1",
      "pricing": { "prompt": 0.000001, "completion": 0.000002, "unit": "per_token" }
    },
    "envvars_only": {
      "provider": "${LLM_PROVIDER}",
      "model": "${LLM_MODEL}",
      "api_key": "${LLM_API_KEY}",
      "base_url": "${LLM_BASE_URL}",
      "pricing": {
        "prompt": "${LLM_PROMPT_COST}",
        "completion": "${LLM_COMPLETION_COST}",
        "unit": "${LLM_COST_UNIT}"
      }
    }
  },
  "settings": {
    "default_llm_profile": "gpt-4o"
  },
  "blueprints": {
    "rue_code": { "default_model": "o3-mini" },
    "geese": { "default_model": "gpt-4o" }
  },
  "mcpServers": {
    "main": {
      "url": "http://localhost:8001",
      "api_key": "${MCP_API_KEY}",
      "description": "Primary local MCP server"
    },
    "cloud": {
      "url": "https://mcp.example.com",
      "api_key": "${MCP_CLOUD_KEY}",
      "description": "Cloud backup MCP server"
    }
  }
}
```

---

## 3. Key Features

- **Model Profiles by Name:** Each key under `llm` matches a model (e.g., `gpt-4o`, `o3-mini`).
- **Cost Tracking:** `pricing` section per model, used for cost estimation/reporting.
- **Environment Variables:** Use `${ENVVAR}` for any value.
- **Per-Blueprint Model Overrides:** `blueprints` section allows each blueprint to specify a `default_model`.
- **Agent/Task Overrides:** Blueprints themselves can choose models per agent/task.
- **MCP Servers:** The `mcpServers` section defines available MCP servers, their endpoints, and credentials.
- **CLI Agent Fusion:** A `cli_agents` section wraps your installed agentic CLIs (grok/claude/gemini/codex/opencode) as subagents, with `cli_fusion` / `cli_map` / `cli_orchestrator` blocks composing them. Calling the API with `model: "cli_fusion"` (consensus across CLIs) or `model: "cli_map"` (many agents, each one CLI) runs them. Generate this block with `swarm-cli cli-agents --init --write`; full reference in **[docs/CLI_FUSION.md](docs/CLI_FUSION.md)** and the deploy runbook **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)**.
- **Fallbacks:**
  - If a requested model is not configured, the system falls back to the default and prints a warning.
  - If config is missing, a default config is generated (uses OpenAI endpoint).

---

## 4. How Loading Works

1. **Locate and load** `swarm_config.json` (prefer XDG, fallback to cwd/project).
2. **Substitute environment variables** for any `${...}` values.
3. **Select the active LLM profile** from `settings.default_llm_profile`, unless overridden by a blueprint or CLI argument.
4. **Blueprints:**
    - Use their own `default_model` if set in config.
    - May specify a model per agent/task within their own logic.
5. **If a requested model/profile is missing,** fall back to the default and print a warning.

---

## 5. CLI vs Manual Configuration

- The `swarm-cli` is the recommended tool for all config tasks:
  - `swarm-cli configure` (guided interactive setup)
  - `swarm-cli list-config` (view config)
  - `swarm-cli set ...` (update values)
- Manual editing is fully supported for power users and automation.

---

## 6. Security & Redaction

- All sensitive config values (API keys, tokens) are redacted in logs.
- Never log full secrets.

---

## 7. Troubleshooting

- **Missing config:** Default file is generated, warning printed.
- **Missing model:** Fallback to default, warning printed.
- **Missing API key:** Error raised if not found after env substitution.
- **Cost not shown:** Add `pricing` section to the model profile.

---

## 8. Extending & Testing

- Add new models/providers by updating the `llm` section.
- Use envvars for secrets and endpoints.
- Add/override MCP servers as needed.
- Tests should cover config loading, env substitution, fallback logic, and cost reporting.

---

## 9. Memory (experimental)

Blueprints can opt in to persistent, cross-conversation memory. **mem0 is the default and currently the only working backend.** Install its dependency via the `memory` extra:

```sh
pip install open-swarm[memory]   # or: uv sync --extra memory
```

### Config Shape

Add a `memory` block either per blueprint (under `blueprints.<id>`, checked first) or at the top level of the config (applies to all blueprints):

```json
{
  "blueprints": {
    "my_blueprint": {
      "memory": {
        "backend": "mem0",
        "user_id": "alice",
        "limit": 5,
        "config": { "vector_store": { "provider": "qdrant" } }
      }
    }
  }
}
```

Keys (all optional except `backend`):

| Key       | Description |
|-----------|-------------|
| `backend` | `"mem0"` is the only implemented backend. Empty/`"none"` disables memory; unknown names log a warning and disable. **Required** — without it the block is ignored. |
| `user_id` | Default user id for memory search/storage when a run doesn't pass one (default: `"default"`). |
| `limit`   | Max memory snippets returned per search (default: `5`). |
| `config`  | Dict passed verbatim to `mem0.Memory.from_config(...)` (vector store, LLM, etc. — see mem0 docs). Omit to use mem0's defaults. |

**Custom OpenAI-compatible endpoint (e.g. LiteLLM):** mem0 accepts a base-URL
override per component via the `config` block (forwarded verbatim):

```json
"memory": {
  "backend": "mem0",
  "config": {
    "llm":      {"provider": "openai", "config": {"model": "gpt-4o-mini", "openai_base_url": "${LITELLM_BASE_URL}", "api_key": "${LITELLM_API_KEY}"}},
    "embedder": {"provider": "openai", "config": {"model": "text-embedding-3-small", "openai_base_url": "${LITELLM_BASE_URL}", "api_key": "${LITELLM_API_KEY}"}}
  }
}
```

Note: the endpoint must also proxy an **embeddings** model — mem0 needs one
for its vector store, not just a chat model.

### Behavior

- **Pre-run retrieval:** before each `run()`, the latest user message is used to search memory; any hits are prepended as a single system message (`"Relevant memories from previous conversations: ..."`).
- **Post-run storage:** after the run, the input messages plus the assistant's output are stored under `user_id`. The injected memory system message is not re-stored.
- **Strict no-op when unconfigured:** with no `memory` block (or no `backend` key), `run()` is untouched and behavior is byte-for-byte identical to before.
- **Graceful degradation:** if `backend: "mem0"` is set but the `mem0ai` package is not installed, a warning is logged and the blueprint continues without memory — nothing raises.
- **Error isolation:** memory search/storage failures are logged as warnings and never break a run.

### Status

This integration is covered by unit tests using fake in-memory backends; it has **not yet been validated end-to-end against a live mem0 instance**. The `langmem` and `papr` backends are placeholders: selecting them in config logs a warning and disables memory, and instantiating their classes directly raises `NotImplementedError`.

---

## Environment Variables

The canonical reference. [`.env.example`](./.env.example) is the copy-paste
template; this table explains what each variable does. Secrets belong in the
environment / `.env`, never in `swarm_config.json` (reference them with
`${VAR}`).

### Config & state paths

| Variable | Purpose | Default |
|---|---|---|
| `SWARM_CONFIG_PATH` | Explicit path to `swarm_config.json` (wins over discovery). | unset → XDG-first discovery (see [§1](#1-config-file-location-and-discovery)) |
| `XDG_CONFIG_HOME` | Base for the config dir (`…/swarm/swarm_config.json`, `teams.json`). | `~/.config` |
| `SWARM_RESPONSES_DIR` | Where `/v1/responses` stores records for `previous_response_id` chaining and `GET`/`DELETE`. | `$XDG_DATA_HOME/swarm/responses` (i.e. `~/.local/share/swarm/responses`) |
| `XDG_DATA_HOME` | Base for state data (responses store). | `~/.local/share` |

### Server, security & auth

| Variable | Purpose | Default |
|---|---|---|
| `DJANGO_SECRET_KEY` | Django secret. **Required in production** (server refuses to start without it). | none (dev random) |
| `DJANGO_DEBUG` | Debug mode (verbose errors, DEBUG logging, relaxed auth). Keep **off** in prod. | `false` |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated allowed hosts. **Required in production.** | dev: localhost |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Comma-separated trusted origins for CSRF on mutating routes. | none |
| `API_AUTH_TOKEN` | Bearer token OpenAI clients present to the API. | none |
| `ENABLE_API_AUTH` | Require auth on `/v1/*`. Forced on in production. | prod: on |
| `ALLOW_TESTUSER_AUTOLOGIN` | Dev-only auto-login (debug only, random password). | `false` |
| `HOST` / `PORT` | Bind address/port for the server. | `0.0.0.0` / `8000` |

### Feature flags

| Variable | Purpose | Default |
|---|---|---|
| `ENABLE_WEBUI` | Serve the web UI at `/`. | on |
| `ENABLE_ADMIN` | Mount the Django admin. | off |
| `ENABLE_GITHUB_MARKETPLACE` | GitHub-topics blueprint discovery. | off |
| `ENABLE_MCP_SERVER` | Aspirational MCP-server mode — warns loudly; see [docs/mcp_server_mode.md](./docs/mcp_server_mode.md). | off |

### Behavior & diagnostics

| Variable | Purpose | Default |
|---|---|---|
| `SWARM_TEST_MODE` | Deterministic, network-free blueprint output (testing). | off |
| `DJANGO_LOG_LEVEL` / `LOGLEVEL` | Log verbosity. | `INFO` |

### Provider credentials & integrations

Model/provider keys and service endpoints — `OPENAI_API_KEY`, `OPENAI_BASE_URL`,
`ANTHROPIC_API_KEY`, `GEMINI_API_KEY` / `GOOGLE_API_KEY`, `OPENROUTER_API_KEY`,
`LITELLM_*`, `OLLAMA_BASE_URL`, plus MCP/tool keys (`BRAVE_API_KEY`,
`GITHUB_TOKEN`, `QDRANT_*`, …) — are listed with inline guidance in
[`.env.example`](./.env.example). Reference them in `swarm_config.json` via
`${VAR}`.

> **Note for CLI agents:** wrapped CLIs (`claude`, `gemini`, `grok`, …) carry
> **their own** authentication — Open Swarm never reads or stores it. These
> provider keys are only for `llm` profiles and MCP tool servers.

---

For more, see the main [README.md](./README.md) or run `swarm-cli --help`.
