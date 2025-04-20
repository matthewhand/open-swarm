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

- **Preferred:** `~/.config/swarm/swarm_config.json` (XDG Base Directory Spec)
- **Fallbacks:** Current working directory, project root, blueprint directories
- **If missing:** Swarm generates a default config using `OPENAI_API_KEY` and the official OpenAI endpoint (with a warning).

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

For more, see the main [README.md](./README.md) or run `swarm-cli --help`.
