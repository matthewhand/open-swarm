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
# Set OPENAI_API_KEY. Compose defaults DJANGO_DEBUG=false, so also set
# API_AUTH_TOKEN (or SWARM_API_KEY), DJANGO_SECRET_KEY, and DJANGO_ALLOWED_HOSTS
# or the container will refuse to start — see .env.example.
```

2) Start the API
```bash
docker compose up -d
# wait for the healthcheck to pass (or tail the logs)
# docker compose logs -f swarm
```

3) Smoke-check the API (Bearer required whenever `API_AUTH_TOKEN` is set —
`ENABLE_API_AUTH` is derived from the token, not a separate switch)
```bash
# Models
curl -sf http://localhost:8000/v1/models \
  -H "Authorization: Bearer ${API_AUTH_TOKEN}" | jq .

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
- Auth is **not** “on by default”: it is on only when a token is configured.
  With compose’s `DJANGO_DEBUG=false`, a missing token refuses boot unless you
  set `SWARM_ALLOW_NO_AUTH=true` (local/demo / external-gateway opt-out only).
  Local `DJANGO_DEBUG=true` with no token leaves the API open (warns).

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

For a local OpenAI-compatible gateway that advertises role model slugs
(`orchestration` / `delegation` / `auxiliary`) — for example
`http://127.0.0.1:4000/v1` (adjust host/port) — put the host and a placeholder
key in the environment, then register one profile per slug. Full JSON example,
trait tags for `inference_profile` routing, and the `hybrid_team` role vs
gateway-slug distinction live in
[USERGUIDE.md — Local OpenAI-compatible gateway](../USERGUIDE.md#local-openai-compatible-gateway-role-model-slugs):

```bash
export LITELLM_BASE_URL=http://127.0.0.1:4000/v1
export LITELLM_API_KEY=sk-local-placeholder   # any non-empty value if keyless
# Do not set LITELLM_MODEL — that overrides every profile's model.

swarm-cli config add --section llm --name orchestration --json \
  '{"provider":"openai","model":"orchestration","base_url":"${LITELLM_BASE_URL}","api_key":"${LITELLM_API_KEY}","intelligence":0.95}'
swarm-cli config add --section llm --name delegation --json \
  '{"provider":"openai","model":"delegation","base_url":"${LITELLM_BASE_URL}","api_key":"${LITELLM_API_KEY}","intelligence":0.7,"cost":0.4}'
swarm-cli config add --section llm --name auxiliary --json \
  '{"provider":"openai","model":"auxiliary","base_url":"${LITELLM_BASE_URL}","api_key":"${LITELLM_API_KEY}","speed":0.9,"cost":0.9}'

export DEFAULT_LLM=orchestration
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

**MoA (optional):** multi-seat consensus, or consensus then a scripted team:

```bash
swarm-cli moa "Ship rate limiting?" --backend fake --team \
  --workdir /tmp/moa-team \
  --team-tasks 'implementer:Apply|tester:Verify|docs:ADR'
```

See [MOA.md](./MOA.md).

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
- Role-slug gateway example (`orchestration` / `delegation` / `auxiliary` on
  `LITELLM_BASE_URL`): see [§3b](#b-use-a-custom-endpoint-or-model) and
  [USERGUIDE.md](../USERGUIDE.md#local-openai-compatible-gateway-role-model-slugs).
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
