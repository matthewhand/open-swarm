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
  -r "Coordinator:lead, Engineer:code" \
  --output-dir ./my_blueprints \
  --bin-dir ./my_bin
```

Flags:
- `--name/-n`: Team name
- `--description/-d`: One-line description
- `--abbreviation/-a`: CLI shortcut name (defaults to slugified name)
- `--agents/-r`: Comma-separated `Name:role` entries
- `--use-llm [--model]`: Use LLM with constrained JSON to refine the spec (requires API key)
- `--no-shortcut`: Skip creating the CLI shortcut
- `--output-dir`, `--bin-dir`: Control output locations (useful in sandboxes/CI)

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

2) Start the API
```bash
docker compose up -d
# wait for the healthcheck to pass (or tail the logs)
# docker compose logs -f open-swarm
```

3) Smoke-check the API
```bash
# Models
curl -sf http://localhost:8000/v1/models | jq .

# Chat (non-streaming)
curl -sf http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${SWARM_API_KEY:-dev}" \
  -d '{
    "model": "echocraft",
    "messages": [{"role":"user","content":"ping"}]
  }' | jq .
```

Notes:
- docker-compose includes a healthcheck for /v1/models
- PORT defaults to 8000; SWARM_BLUEPRINTS defaults to echocraft
- Adjust volumes in docker-compose.yaml to mount your blueprints and config

---

## 3. Configure Your LLM Provider

Before using LLM-powered agents, you must provide credentials.

### a. Add an OpenAI API Key (simplest case)
```bash
swarm-cli llm add --provider openai --api-key sk-... 
```
- This saves your API key to `~/.config/swarm/.env` as `OPENAI_API_KEY`.

### b. Use a Custom Endpoint or Model
```bash
swarm-cli llm add --provider openai --api-key sk-... --base-url https://api.your-endpoint.com/v1 --model gpt-4
```
- Supports local models and other providers (see `swarm-cli llm add --help`).

### c. Check or Edit LLM Config
- View config: `swarm-cli llm list`
- Edit config manually: `nano ~/.config/swarm/.env`

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
- Manage via CLI:
  ```bash
  swarm-cli config add --section llm --name openai_default --json '{"provider":"openai","model":"gpt-4o","base_url":"https://api.openai.com/v1","api_key":"${OPENAI_API_KEY}"}'
  ```
- See [docs/SWARM_CONFIG.md](./SWARM_CONFIG.md) for details.

---

## 7. Troubleshooting

- **Blueprint/command not found:** Ensure `~/.local/bin` is in your `$PATH`.
- **API errors:** Check your API key and network connectivity.
- **Config issues:** Validate your config with `swarm-cli config validate` (if available).
- **Logs:** Check `~/.swarm/swarm.log` or run with increased verbosity if supported.

---

## 8. Next Steps & Resources

- Run `swarm-cli --help` and `codey --help` for usage info.
- Explore more blueprints: `swarm-cli list`
- Read the [Developer Guide](./DEVELOPER_GUIDE.md) for advanced usage, customization, and contribution tips.
- See [docs/SWARM_CONFIG.md](./SWARM_CONFIG.md) and [docs/BLUEPRINT_SPLASH.md](./BLUEPRINT_SPLASH.md) for in-depth config and blueprint info.

---

**Happy hacking with Open Swarm!**
