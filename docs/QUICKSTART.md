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
# Set OPENAI_API_KEY and, for gateways, OPENAI_BASE_URL.
# Production-like boots also require API_AUTH_TOKEN, DJANGO_SECRET_KEY,
# and DJANGO_ALLOWED_HOSTS; see .env.example.
```

2) Start the API
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

Named profiles in `swarm_config.json` are the canonical configuration. For the
simple env-only bootstrap, set:

```bash
export OPENAI_API_KEY=sk-...
export OPENAI_BASE_URL=https://api.openai.com/v1  # required for gateways; explicit is safest
```

With no config file, these synthesize a named `default` profile. `LITELLM_API_KEY`
and `LITELLM_BASE_URL` remain compatibility aliases only. `DEFAULT_LLM` and
`LITELLM_MODEL` do not select models; set the profile's `model` and route by
profile name in JSON.

For persistent or multi-provider setup, copy the portable example and edit its
named profiles:

```bash
mkdir -p ~/.config/swarm
cp swarm_config.json.example ~/.config/swarm/swarm_config.json
python -m json.tool ~/.config/swarm/swarm_config.json >/dev/null
swarm-cli config list --section llm
```

You can also add a profile with the implemented `config` command:

```bash
swarm-cli config add --section llm --name local --json \
  '{"provider":"openai","model":"gpt-5.5","base_url":"https://api.your-endpoint.com/v1","api_key":"${OPENAI_API_KEY}"}'
```

Select it with `settings.default_llm_profile` or a per-blueprint
`blueprints.<id>.llm_profile` entry. See [CONFIGURATION.md](../CONFIGURATION.md).

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

- The canonical file is `~/.config/swarm/swarm_config.json` (XDG compliant).
- Keep secrets in the environment and reference them as `${ENV_VAR}` in JSON.
- The compact portable starting point is
  [swarm_config.json.example](../swarm_config.json.example); profile names drive
  bootstrap and per-blueprint routing.
- For agentic CLIs, generate the `cli_agents` block from installed tools with
  `swarm-cli cli-agents --init --write`.
- For MoA defaults, run `swarm-cli moa-init`; use `swarm-cli moa --team
  --workdir ...` only when you want post-consensus scripted specialists.
- Docker ships the REST/API path, not host-authenticated agentic CLIs. To use
  those in a container, copy and adapt `docker-compose.override.example.yml`, or
  run natively so the installed CLI binaries and auth state are available.
- See [CONFIGURATION.md](../CONFIGURATION.md) for the full schema.

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
- See [CONFIGURATION.md](../CONFIGURATION.md) and [BLUEPRINT_SPLASH.md](./BLUEPRINT_SPLASH.md) for in-depth config and blueprint info.

---

**Happy hacking with Open Swarm!**
