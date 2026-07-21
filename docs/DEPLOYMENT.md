# Deploying a CLI-wrapping OpenAI-compatible server

A runbook for standing up Open Swarm so it exposes an **OpenAI-compatible API**
(`/v1/chat/completions`, `/v1/responses`, `/v1/models`, OpenAPI at `/api/schema/`)
that wraps your installed agentic CLIs (grok, claude, gemini, codex, opencode).

## 0. Prerequisites — the CLIs must be installed *where the server runs*

The fusion blueprints shell out to the CLIs as subprocesses, so each CLI you
want to use must be **installed and authenticated on the same host/container as
the server** (not just on your laptop). In Docker, that means baking the CLIs
into the image (or mounting them) and providing their auth.

Auth, per CLI:

| CLI | Auth |
|---|---|
| `gemini` | `GEMINI_API_KEY` / `GOOGLE_API_KEY`, or `gemini` oauth login |
| `claude` | `ANTHROPIC_API_KEY`, or `claude` login |
| `grok` (a.k.a. `agent`) | file-based login via the `grok` CLI (no single env var) |
| `codex` | `OPENAI_API_KEY` |
| `opencode` | per its own config (`opencode models`) |

## 1. Update

```bash
git checkout main && git pull --ff-only
```

## 2. Configure

```bash
cp .env.example .env   # set DJANGO_SECRET_KEY, DJANGO_ALLOWED_HOSTS, API_AUTH_TOKEN
                       # (production refuses to start without all three)

# which CLIs are installed AND authenticated on this host?
swarm-cli cli-agents --check-auth

# generate a swarm_config.json wiring cli_agent/cli_fusion/cli_map/cli_orchestrator
# over the installed CLIs (writes to ~/.config/swarm/swarm_config.json):
swarm-cli cli-agents --init --write
```

Then open the written `swarm_config.json` and confirm the **judge / router /
planner** roles (in the `cli_fusion` / `cli_orchestrator` / `cli_map` blocks)
point only at CLIs that showed as authenticated — `--init` prefers `grok` then
`claude` by default; change them to match your host.

The server and `swarm-cli` both find this XDG file automatically — no extra
step. Set `SWARM_CONFIG_PATH` only to point at a non-standard path. See
[CONFIGURATION.md §1](../CONFIGURATION.md#1-config-file-location-and-discovery)
for the full resolution rules.

## 3. Run

```bash
swarm-api                 # ASGI server on :8000 (also powers websocket chat)
# or:
docker compose up -d
```

Point any OpenAI client at `http://<host>:8000/v1` with
`Authorization: Bearer $API_AUTH_TOKEN`.

> **Single worker until a shared queue exists.** Async `/v1/responses` cancel
> and in-flight limits are **process-local**. Compose/Dockerfile default
> `SWARM_UVICORN_WORKERS=1`. Setting workers > 1 is refused by default
> (`SWARM_ENFORCE_SINGLE_WORKER=true`); only override if you accept broken
> cross-worker cancel. Oracle systemd unit already uses `--workers 1`.

> **Persist Responses state.** `/v1/responses` is stateful: stored responses (for
> `previous_response_id` chaining and `GET`/`DELETE`) live under
> `SWARM_RESPONSES_DIR` (default `~/.local/share/swarm/responses`). In Docker,
> mount a volume there — or set `SWARM_RESPONSES_DIR` to a mounted path — or
> chained responses won't survive a container restart.

## 4. Prove it works

```bash
H="-H 'Authorization: Bearer $API_AUTH_TOKEN' -H 'Content-Type: application/json'"

curl -sf http://localhost:8000/v1/models | jq .          # lists cli_fusion, cli_map, …
curl -sf http://localhost:8000/api/schema/ | head        # OpenAPI spec (200)

# one agent, consensus across your CLIs:
curl -sf http://localhost:8000/v1/chat/completions -H "Authorization: Bearer $API_AUTH_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"model":"cli_fusion","messages":[{"role":"user","content":"In one word, capital of France?"}]}' | jq .

# many agents, each one CLI:
curl -sf http://localhost:8000/v1/chat/completions -H "Authorization: Bearer $API_AUTH_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"model":"cli_map","messages":[{"role":"user","content":"In one word, capital of France?"}]}' | jq .

# Responses API:
curl -sf http://localhost:8000/v1/responses -H "Authorization: Bearer $API_AUTH_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"model":"cli_fusion","input":"In one word, capital of France?"}' | jq .
```

PASS = HTTP 200 and a non-empty answer naming Paris.

## Which blueprint?

| You want | `model:` |
|---|---|
| One agent, consensus across many CLIs | `cli_fusion` |
| Many agents, each using one CLI | `cli_map` |
| Cheap router that escalates hard questions to a panel | `cli_orchestrator` |
| A single named CLI, no consensus | `cli_agent` |

See [CLI_FUSION.md](CLI_FUSION.md) for the full config reference (panels, judges,
presets, per-request `params`, failover, workdir isolation, native best-of-N).

## Common gotchas

- **`All CLI panelists failed` / empty answers** → the CLI isn't installed or not
  authenticated *in the server's environment*. Re-run `swarm-cli cli-agents
  --check-auth` on the host.
- **Server refuses to start** → in production (`DJANGO_DEBUG` not true) you must
  set `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, and `API_AUTH_TOKEN`.
- **401/403** → missing/wrong `Authorization: Bearer $API_AUTH_TOKEN`.
- **gemini slow / stalls** → the free `oauth-personal` tier throttles the pro
  model heavily; the flash default answers in seconds. Use a paid `GEMINI_API_KEY`
  for the pro tier.
