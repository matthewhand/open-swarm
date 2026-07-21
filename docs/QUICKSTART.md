# Open Swarm Quickstart

This guide will help you get started with Open Swarm, install and configure blueprints (like Codey), and run your first LLM-powered agent.

---

## 1. Install Open Swarm

Install the Open Swarm framework and CLI globally:
```bash
pip install --user open-swarm
```
- This provides the `swarm-cli` tool and core libraries.
- Make sure `~/.local/bin` is in your `$PATH` so CLI tools are discoverable.

---

## 2. Install a Blueprint (e.g., Codey)

Blueprints are modular agents or tools. To install Codey (a coding assistant):
```bash
swarm-cli install codey
```
- This downloads and registers the Codey blueprint.
- The `codey` command will be installed to your local bin directory.

To list available blueprints:
```bash
swarm-cli list
```

---

## 2b. Create Your Own Team (Wizard)

Use the built-in wizard to scaffold a new team blueprint and optionally install a CLI shortcut.

- Interactive:
```bash
swarm-cli wizard
```

- Non-interactive example:
```bash
swarm-cli wizard --non-interactive \
  -n "Demo Team" \
  -r "Coordinator:lead" \
  -r "Engineer:code" \
  --output-dir ./my_blueprints
```

Flags (see `swarm-cli wizard --help`):
- `--name/-n`: Team name
- `--role/-r`: Role:description pairs (repeatable)
- `--no-shortcut`: Skip creating the CLI shortcut
- `--output-dir`: Where to write the blueprint

Outputs:
- Python file at `<output-dir>/<slug>/blueprint_<slug>.py`
- Optional CLI shortcut at `<bin-dir>/<abbreviation>`

Tip: If you are new or don’t have keys yet, the CLI can hint `swarm-cli wizard` at startup.

---

## 3. Deploy swarm-api via Docker (Optional)

If you want to expose blueprints over an OpenAI-compatible REST API:

1) Prepare environment
```bash
cp .env.example .env
# Ensure OPENAI_API_KEY (and optional SWARM_API_KEY) are set in .env
```

2) Start the API (set `API_AUTH_TOKEN` and `DJANGO_SECRET_KEY` in `.env` for
production-like boots; see `.env.example`)
```bash
docker compose up -d
# wait for the healthcheck to pass (or tail the logs)
# docker compose logs -f swarm
```

3) Smoke-check the API
```bash
# Models
curl -sf http://localhost:8000/v1/models | jq .

# Chat (non-streaming) — use a bundled model id from /v1/models
curl -sf http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${API_AUTH_TOKEN}" \
  -d '{
    "model": "suggestion",
    "messages": [{"role":"user","content":"ping"}]
  }' | jq .
```

Notes:
- docker-compose healthcheck probes `/health` (service name: `swarm`)
- PORT defaults to 8000
- Auth is **on** by default; set `SWARM_ALLOW_NO_AUTH=true` only for local demos

---

## 3. Configure Your LLM Provider

Before using LLM-powered agents, you must provide credentials.

### a. Add an OpenAI API Key (simplest case)

```bash
export OPENAI_API_KEY=sk-...
# or put OPENAI_API_KEY in .env / ~/.config/swarm/.env
```

Register an LLM profile with the real CLI (`config`, not `llm add`):

```bash
swarm-cli config add --section llm --name default --json \
  '{"provider":"openai","model":"gpt-4o-mini","api_key":"${OPENAI_API_KEY}"}'
```

### b. Use a Custom Endpoint or Model

```bash
swarm-cli config add --section llm --name local --json \
  '{"provider":"openai","model":"gpt-4o","base_url":"https://api.your-endpoint.com/v1","api_key":"${OPENAI_API_KEY}"}'
```

### c. Check or Edit LLM Config

```bash
swarm-cli config list --section llm
# or edit the JSON file:
# nano ~/.config/swarm/swarm_config.json
```

---

## 4. Run a Blueprint (e.g., Codey)

To start Codey interactively (installed executable):
```bash
codey
```
- If you see "command not found", try:
  - `~/.local/bin/codey`
  - Or add `~/.local/bin` to your `$PATH`.

To run a one-off instruction (non-interactive) via installed executable:
```bash
codey --message "Write a Python function to add two numbers"
```

To launch without installing the executable:
```bash
swarm-cli launch codey --message "Write a Python function to add two numbers"
```

---

## 5. Managing Blueprints

- **List known and installed blueprints:**
  ```bash
  swarm-cli list
  ```
- **Install a blueprint executable:**
  ```bash
  swarm-cli install codey
  ```
- **Launch an installed blueprint executable:**
  ```bash
  swarm-cli launch codey --message "Hello from Codey"
  ```

---

## 6. Advanced: Configure swarm_config.json

- The main config file is at `~/.config/swarm/swarm_config.json` (XDG compliant).
- Secrets are stored in `~/.config/swarm/.env` and referenced as `${ENV_VAR}` in JSON.
- Edit it directly (it's plain JSON), then add an `llm` profile like:
  ```jsonc
  {"llm": {"openai_default": {"provider": "openai", "model": "gpt-4o",
    "base_url": "https://api.openai.com/v1", "api_key": "${OPENAI_API_KEY}"}}}
  ```
- For the agentic CLIs, generate the `cli_agents` block from what's installed:
  `swarm-cli cli-agents --init --write`.
- See [docs/SWARM_CONFIG.md](./SWARM_CONFIG.md) and [CONFIGURATION.md](../CONFIGURATION.md) for the full schema.

---

## 7. Troubleshooting

- **Blueprint/command not found:** Ensure `~/.local/bin` is in your `$PATH`.
- **API errors:** Check your API key and network connectivity.
- **Config issues:** The config is plain JSON — check it parses (`python -m json.tool ~/.config/swarm/swarm_config.json`); for CLI auth, run `swarm-cli cli-agents --check-auth`.
- **Logs:** Check `~/.swarm/swarm.log` or run with increased verbosity if supported.

---

## 8. Next Steps & Resources

- Run `swarm-cli --help` and `codey --help` for usage info.
- Explore more blueprints: `swarm-cli list`
- Read the [Developer Guide](./DEVELOPER_GUIDE.md) for advanced usage, customization, and contribution tips.
- See [docs/SWARM_CONFIG.md](./SWARM_CONFIG.md) and [docs/BLUEPRINT_SPLASH.md](./BLUEPRINT_SPLASH.md) for in-depth config and blueprint info.

---

**Happy hacking with Open Swarm!**
