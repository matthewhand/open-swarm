# Herdr connectivity (REQ-21)

Open Swarm can drive **Herdr** as a member `kind=herdr` without owning the TUI.

This is **NOT Hermes**, **NOT OMB**, and **NOT Rakazo**. Those are different
products. Herdr is the pane session server + CLI at [herdr.dev](https://herdr.dev/).

## Same-host default

The default remote is **localhost**. Invoke the official CLI with **no**
`--remote`:

```bash
herdr workspace list
herdr agent list
herdr agent read w3:p1
herdr agent prompt w3:p1 HERDR_PING_OK
herdr agent wait w3:p1 --until idle
```

That talks to the Herdr already on this host (local server + unix sockets,
typically `~/.config/herdr/`). Live `.30` (ubuntu-max) runs `herdr server` plus
the remote-client-bridge. This cloud agent does **not** SSH there.

## Settings Remotes kind (REQ-64)

Herdr is an **addable remotes kind** (`kind=herdr`), same persist shape as
Hermes / OpenMousBot / Rakazo: base URL + api-key-env name. It is **opt-in**
(compatible with REQ-59): it does not appear in Settings Remotes until you add
it. There is **no baked LAN host**.

```bash
swarm-cli remotes set herdr --base-url http://127.0.0.1:9 --api-key-env HERDR_API_KEY
```

Settings → Remotes → **+ Add remote** (or Django `/settings/` **Add Herdr remote**)
does the same `PATCH /v1/remotes/herdr/`. After add, Herdr shows in the Remotes
list like the other kinds.

`herdr --remote` and `HerdrClient.from_remote_config()` use that configured
base. A **localhost / loopback** base omits `--remote` (the documented default)
only when **you set** that URL. Missing config is a clear error — Open Swarm
will not guess another host.

HTTP health/list (stubbed in tests; no live LAN in CI):

| Op | Request |
|---|---|
| Health | `GET {base}/health` |
| List | `GET {base}/agents` |

```bash
swarm-cli remotes health herdr
swarm-cli remotes operate herdr --op list
```

Do not commit tokens. Placeholders only (`${HERDR_API_KEY}`).

## Optional `--remote`

A persisted Herdr row may set `remote` to a string such as
`matthewh@10.0.0.36`, `workbox`, or `ssh://you@server:2222`. Empty/omitted
means localhost. When set, **every** CLI call is prefixed:

```bash
herdr --remote matthewh@10.0.0.36 agent prompt w3:p1 HERDR_PING_OK
```

See [How to work with Herdr](https://herdr.dev/docs/how-to-work/) and the
[CLI reference](https://herdr.dev/docs/cli-reference/). Open Swarm does **not**
invent flags or a socket protocol; it wraps `herdr`.

## Proven prompt shape

Engineer proof on ubuntu-max `10.0.0.30`:

```bash
herdr agent prompt w3:p1 HERDR_PING_OK
```

`TEXT` is **one** argv argument. The CLI returned `type: agent_prompted`. The
pane showed user `HERDR_PING_OK` and grok replied that the ping was OK.

Unquoted TEXT is a quoting bug: herdr then reports `unknown option: with`.
The Python wrapper always passes TEXT as a single `argv` element (spaces stay
inside that one argument).

## Blocked and `--wait`

- If the agent is **blocked**, submit is rejected (`HerdrBlockedError` /
  Herdr `agent_blocked`). Input is not sent.
- If the agent is already **working**, `herdr agent prompt --wait` may match
  **that in-flight turn finishing**, not a newly submitted turn. Do not assume
  `--wait` observed your prompt.
- Tests must **mock** `herdr`. Do **not** target a WORKING grok pane in CI.

## Addable members

`GET /v1/herdr-agents/discover/` runs `herdr agent list` and
`herdr workspace list` and returns addable members (`kind=herdr`,
`remote=""` = localhost). `POST /v1/herdr-agents/` persists a row
(`name`, optional `remote`). Teams (`/teams/#herdr-members`) and the AGENTS
sidepane list persisted rows so an operator can pick them.

Cloud CI must mock `herdr` (no live TUI). SQLite is the default DB; this
feature does not set `DATABASE_URL` or enable Neon.

## API

| Method | Path | Role |
|--------|------|------|
| GET | `/v1/herdr-agents/` | List persisted members |
| POST | `/v1/herdr-agents/` | Add `{name, remote?}` |
| GET | `/v1/herdr-agents/discover/` | Live agent + workspace list |
| GET/DELETE | `/v1/herdr-agents/<id>/` | Read / remove (id or name) |

Operator UI: `/settings/#group-herdr` and Django admin. The DaisyUI SPA
settings sheet is not in this tree (ADR-001); the SPA sidepane still fetches
`/v1/herdr-agents/` so members appear next to blueprints.

## Python wrapper

```python
from swarm.herdr import HerdrClient, extract_prompt_type

client = HerdrClient()  # localhost, no --remote
payload = client.agent_prompt("w3:p1", "HERDR_PING_OK")
assert extract_prompt_type(payload) == "agent_prompted"

client = HerdrClient(remote="matthewh@10.0.0.36")
client.agent_list()  # herdr --remote matthewh@10.0.0.36 agent list
```
