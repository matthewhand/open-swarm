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

- **If missing:** A minimal `default` profile is synthesized from `OPENAI_API_KEY` (+ `OPENAI_BASE_URL`); full profiles live in `swarm_config.json`. `LITELLM_*` aliases work for compatibility.

> Paths and all environment variables (`SWARM_CONFIG_PATH`, `SWARM_RESPONSES_DIR`,
> server/auth/feature flags, provider keys) are consolidated in one place:
> **[Environment Variables](#environment-variables)** below.

---

## Migration Note (from legacy env selectors)

**LLM setup is now driven by named profiles in `swarm_config.json`** (the `llm` block), including complex multi-provider mappings, trait tags for inference profiles, etc.

- **Simple case:** just `export OPENAI_API_KEY=...` (and `OPENAI_BASE_URL=...` for gateways). No `swarm_config.json` needed — a `default` profile using the `gpt-5.5` family is synthesized.
- `LITELLM_*` env vars continue to work as aliases for compatibility.
- **Removed as selectors/overrides:** `DEFAULT_LLM` and `LITELLM_MODEL` env vars. Use `llm_profile: "foo"` (or `settings.default_llm_profile`) and profile definitions instead.
- Per-blueprint: prefer `"llm_profile": "name"` in the `blueprints` section.

Old code using env model selectors will now use the configured profiles (or synthesized default). See "How Loading Works" below.

## 2. Example Config Structure

```json
{
  "llm": {
    "default": {
      "provider": "openai",
      "model": "gpt-5.5",
      "api_key": "${OPENAI_API_KEY}",
      "base_url": "${OPENAI_BASE_URL}",
      "intelligence": 0.6,
      "speed": 0.6,
      "cost": 0.6
    },
    "reason": {
      "provider": "openai",
      "model": "gpt-5.5",
      "api_key": "${OPENAI_API_KEY}",
      "base_url": "${OPENAI_BASE_URL}",
      "intelligence": 0.95,
      "reasoning_effort": "high"
    },
    "classify": {
      "provider": "openai",
      "model": "gpt-5.4-mini",
      "api_key": "${OPENAI_API_KEY}",
      "base_url": "${OPENAI_BASE_URL}",
      "temperature": 0.0,
      "speed": 0.8,
      "cost": 0.8
    },
    "openrouter-example": {
      "provider": "openrouter",
      "model": "minimax-m3",
      "api_key": "${OPENROUTER_API_KEY}",
      "base_url": "https://openrouter.ai/api/v1"
    }
  },
  "settings": {
    "default_llm_profile": "default"
  },
  "blueprints": {
    "rue_code": { "llm_profile": "reason" },
    "geese": { "llm_profile": "default" }
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

- **Model Profiles by Name:** Each key under `llm` is a named profile (e.g. `default`, `reason`, `classify`). Profiles support any OpenAI-compatible model (prefer `gpt-5.5` family for examples).
- **Cost Tracking:** `pricing` section per model, used for cost estimation/reporting.
- **Environment Variables:** Use `${ENVVAR}` for any value.
- **Per-Blueprint Overrides:** `blueprints` section allows each blueprint to specify `"llm_profile": "..."` (preferred) or legacy `"default_model"`.
- **Agent/Task Overrides:** Blueprints themselves can choose models per agent/task.
- **MCP Servers:** The `mcpServers` section defines available MCP servers, their endpoints, and credentials.
- **CLI Agent Fusion:** A `cli_agents` section wraps your installed agentic CLIs (grok/claude/gemini/codex/opencode) as subagents, with `cli_fusion` / `cli_map` / `cli_orchestrator` blocks composing them. Calling the API with `model: "cli_fusion"` (consensus across CLIs) or `model: "cli_map"` (many agents, each one CLI) runs them. Generate this block with `swarm-cli cli-agents --init --write`; full reference in **[docs/CLI_FUSION.md](docs/CLI_FUSION.md)** and the deploy runbook **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)**.
- **Fallbacks:**
  - If a requested model is not configured, the system falls back to the default and prints a warning.
  - If config is missing, a default config is generated (uses the configured gateway).

---

## 4. How Loading Works

**Config profiles (under the top-level `llm` key) are the primary and recommended way to set up LLMs**, including complex mappings (different providers, models, base URLs, reasoning params, traits for inference_profile routing, per-profile pricing, etc.).

1. **Locate and load** `swarm_config.json` (prefer XDG, fallback to cwd/project).
2. **Substitute environment variables** for any `${...}` values.
3. **Select the active LLM profile** by name (e.g. via `llm_profile` key, `settings.default_llm_profile`, per-blueprint `llm_profile`, or explicit override). Falls back to the `default` profile.
4. **Blueprints:**
    - Use explicit `llm_profile` (preferred; also in `settings.default_llm_profile`) or legacy `default_model` if set in the `blueprints` section of config.
    - May specify per-agent/task via their logic or inference_profile intent.
5. **Simple env-only case (no/full swarm_config.json):** if `OPENAI_API_KEY` (+ optional `OPENAI_BASE_URL`) are present, a minimal `default` profile using `gpt-5.5` is synthesized automatically. `LITELLM_API_KEY` / `LITELLM_BASE_URL` are accepted as compatibility aliases.
6. **If a requested profile is missing,** fall back to the default (with warning).

**Deprecated/legacy:** `DEFAULT_LLM` and `LITELLM_MODEL` env vars no longer act as model selectors or overrides — profile names in config are authoritative.

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

`swarm.utils.redact.redact_sensitive_data` walks dicts/lists recursively and
masks any value whose **key** matches a sensitive name (e.g. `api_key`,
`password`, `token`, `secret`). Details:

- **Case-insensitive** key matching (`API_KEY`, `Password` are caught).
- **Type-agnostic** — a sensitive value is masked even if it isn't a string
  (ints, bools, or a nested dict/list stored under a secret key are masked
  wholesale, never passed through).
- By default the value is replaced with `[REDACTED]`. Pass `reveal_chars=N` to
  keep the first/last `N` characters for debugging (`abc…hij`); values too short
  to reveal safely are fully masked.

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
    "llm":      {"provider": "openai", "config": {"model": "gpt-5.5", "openai_base_url": "${OPENAI_BASE_URL}", "api_key": "${OPENAI_API_KEY}"}},
    "embedder": {"provider": "openai", "config": {"model": "text-embedding-3-small", "openai_base_url": "${OPENAI_BASE_URL}", "api_key": "${OPENAI_API_KEY}"}}
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
| `SWARM_RESPONSES_SYNC_TIMEOUT` | Default seconds a `/v1/responses` request waits inline before auto-escalating to a queued handle (per-request override: `max_wait_seconds`). Unset = fully-blocking sync. | unset |
| `XDG_DATA_HOME` | Base for state data (responses store). | `~/.local/share` |
| `SWARM_BLUEPRINT_PATHS` | Extra blueprint roots scanned **in addition** to the bundled set (os.pathsep-separated). The user data blueprints dir (`$XDG_DATA_HOME/swarm/blueprints`) is always scanned too. Bundled blueprints win on name collision. | unset |

### Server, security & auth

| Variable | Purpose | Default |
|---|---|---|
| `DJANGO_SECRET_KEY` | Django secret. **Required in production** (server refuses to start without it). | dev only: fixed insecure fallback |
| `DJANGO_DEBUG` | Debug mode (verbose errors, DEBUG logging, relaxed auth). Keep **off** in prod. | `false` |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated allowed hosts (whitespace-trimmed, empties dropped). **Required in production.** | dev: `localhost,127.0.0.1` |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Comma-separated trusted origins for CSRF on mutating routes (whitespace-trimmed, empties dropped). | `http://localhost:8000,http://127.0.0.1:8000` |
| `API_AUTH_TOKEN` | Bearer token OpenAI clients present to the API. | none |
| `ENABLE_API_AUTH` | Require auth on `/v1/*`. Auto-on when `API_AUTH_TOKEN` is set. | prod: on |
| `SWARM_ALLOW_NO_AUTH` | Allow booting in production **without** a token (warns) — for when an external OAuth proxy / API gateway already gates access. | `false` |
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
| `STATEFUL_CHAT_ID_PATH` | `\|\|`-separated JMESPath expressions used to extract the chat/session id from an incoming request payload (first non-empty match wins). | `metadata.channelInfo.channelId`, `metadata.userInfo.userId`, … |
| `SWARM_TRUNCATION_MODE` | Context truncation strategy when trimming message history to fit the token budget: `pairs` (sophisticated — keeps assistant/tool call pairs intact) or `simple` (most-recent only). Unknown values fall back to `simple`. | `pairs` |

### Provider credentials & integrations

Model/provider keys and service endpoints use OpenAI-compatible names preferentially:

- Simple case: `OPENAI_API_KEY` + `OPENAI_BASE_URL` (synthesizes a `default` profile using `gpt-5.5`).
- `LITELLM_API_KEY` / `LITELLM_BASE_URL` are accepted as compatibility aliases.
- Others: `ANTHROPIC_API_KEY`, `GEMINI_API_KEY` / `GOOGLE_API_KEY`, `OPENROUTER_API_KEY`, `OLLAMA_BASE_URL`, etc.

Reference via `${VAR}` in `swarm_config.json`. Full list in [`.env.example`](./.env.example). `DEFAULT_LLM` and `LITELLM_MODEL` envs are deprecated for selection/override.

> **Note for CLI agents:** wrapped CLIs (`claude`, `gemini`, `grok`, …) carry
> **their own** authentication — Open Swarm never reads or stores it. These
> provider keys are only for `llm` profiles and MCP tool servers.

---

For more, see the main [README.md](./README.md) or run `swarm-cli --help`.
