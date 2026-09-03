# Remote harnesses — Hermes, OpenMousBot, Rakazo

Open Swarm can sit **in front of** other agent harnesses: configure them, check
they are up, and send work through **their** APIs. This is not a concurrent
Grok / OpenMousBot / Rakazo seat clone, and **Grok-Bot chrome is not claimed live**.

**Team vocabulary (REQ-11):** a Team is how you wire API agents, CLI agents, and
**remote** agents (Hermes / OpenMousBot / Rakazo) so they can see and talk to each
other via openai-agents **handoff / as_tool**. Hermes, OpenMousBot, and Rakazo are
Team *members* (`consult_hermes`, `consult_omb`, `consult_rakazo`).

That is **not** the Django `/teams/` JSON registry. `/teams/` today is
LLM-profile aliases (`DynamicTeamBlueprint`). New copy should not call those
aliases “teams”; prefer **Profiles**. `GET /v1/remotes/` and
`GET /v1/agent-team/` repeat this collision in `vocabulary` + `team_members`.

Place or unplace remotes in that Team (`agent_team.members` in
`swarm_config.json`; missing key = all three placed; `[]` = empty Team):

```bash
swarm-cli remotes team
swarm-cli remotes unplace rakazo
swarm-cli remotes place rakazo
```

REST: `GET /v1/agent-team/` · `PATCH /v1/agent-team/` `{"members":["hermes","omb"]}`
or `{"place":"rakazo"}` / `{"unplace":"hermes"}`. `remote_harness` only attaches
`consult_*` as_tool specialists for **placed** members.

LAN LLM for *this* swarm: `http://10.0.0.30:8000/v1`. Do **not** point remotes
at Fly open-litellm.

This environment could not TCP-reach `10.0.0.36` / `10.0.0.32` (cloud VM, no
LAN). Defaults below are operator facts already present in `harness_fleet`
plus the published APIs for those products. Health fails honestly when the
box is down.

## Configure (persist)

Defaults (override anytime):

| Remote | Host | Default base URL | Auth env |
|---|---|---|---|
| **hermes** | ubuntu-gtx | `http://10.0.0.36:8642` (UI `:9119`) | `HERMES_API_KEY` (Hermes `API_SERVER_KEY`) |
| **omb** | Windows2 | `http://10.0.0.32:8802` | `OMB_API_KEY` (optional Bearer) |
| **rakazo** | Windows2 | API `http://10.0.0.32:3100`, UI `:5173`, tree `C:\rakazo` | `RAKAZO_API_KEY` and/or `RAKAZO_SESSION_COOKIE` |

```bash
swarm-cli remotes set hermes --base-url http://10.0.0.36:8642 --api-key-env HERMES_API_KEY
swarm-cli remotes set omb --base-url http://10.0.0.32:8802 --api-key-env OMB_API_KEY
swarm-cli remotes set rakazo --base-url http://10.0.0.32:3100 --ui-url http://10.0.0.32:5173 --api-key-env RAKAZO_API_KEY
```

Equivalent persist:

* `PATCH /v1/remotes/hermes/` `{"base_url":"http://10.0.0.36:8642","api_key":"${HERMES_API_KEY}"}`
* `swarm-cli config add --section remotes --name hermes --json '{...}'`
* Edit `~/.config/swarm/swarm_config.json` → `"remotes"` (or `SWARM_CONFIG_PATH`)

Env overrides win over the file: `HERMES_BASE_URL`, `OMB_BASE_URL`, `RAKAZO_BASE_URL`.

Settings → **Remote Harnesses** shows the same values with secrets redacted.
`swarm-cli remotes get hermes` prints the redacted view.

## Health

```bash
swarm-cli remotes health
curl -X POST http://127.0.0.1:8000/v1/remotes/hermes/health/
```

One TCP connect + one HTTP GET. **No retries, no crash-loop.** DOWN is a
report, not an exception. Auth-gated 401/403 on a live port counts as **UP**
(endpoint is alive).

| Remote | Probe |
|---|---|
| Hermes | `GET /health` → `{"status":"ok"}`; version via `GET /v1/models` |
| OpenMousBot (`omb`) | `GET /api/health` → `{"app":"openmausbot",...}` |
| Rakazo | `GET /health` → `{"ok":true,"runtime":"pi",...}` |

## Operate today vs not

| Remote | List | Send / start a job | Gap |
|---|---|---|---|
| **Hermes** | `GET /v1/models`, `GET /api/sessions`, `GET /api/jobs` | `POST /v1/runs` `{"input":"..."}` | Needs Bearer `API_SERVER_KEY`. Do not bounce Hermes to read config; do not delete `SKILL.md`. Dashboard `:9119` is not the operate API. |
| **OpenMousBot** | `GET /api/bots` | `POST /api/bots/{id}/messages` `{"text":"..."}` (202). Creates a bot if none exist. | HTTP only — no OpenMousBot source clone. Upstream default bind is `127.0.0.1:8799`; this LAN install is `:8802`. |
| **Rakazo** | `POST /rpc/bots/list` | `POST /rpc/threads/send` `{botId,text}` | **Better Auth session required** for RPC. Public `GET /health` works without auth. Set `RAKAZO_SESSION_COOKIE` from a signed-in UI session. No unauthenticated job API in upstream. |

```bash
swarm-cli remotes operate hermes --op list
swarm-cli remotes operate hermes --op send --prompt "status"
swarm-cli remotes operate omb --op list
swarm-cli remotes operate omb --op send --prompt "hello" --target <botId>
swarm-cli remotes operate rakazo --op list
```

REST: `POST /v1/remotes/<id>/operate/` `{"op":"list"}` or `{"op":"send","prompt":"…","target":"…"}`.

Blueprint `remote_harness` (chat `model: remote_harness`): grammar `health`, `list omb`, `send hermes …`. Coordinator uses openai-agents **as_tool** specialists (`consult_hermes` / `consult_omb` / `consult_rakazo`).

`harness_fleet` inventory now names `rakazo-32:3100` and `omb-32:8802` (legacy `rakoza-32` / `openmousbot-32` aliases kept).

## Out of scope (this change)

* Do not enable `open-swarm-oracle`.
* Do not change Neon.
* Do not POST to Qwen/Comfy as a prove.
* Do not set `SWARM_ALLOW_ANONYMOUS`.
* Do not point remotes at Fly open-litellm (`persist_remote` refuses those URLs).
