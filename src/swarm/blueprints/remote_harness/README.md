# remote_harness

Open Swarm as a **harness for other harnesses**: Hermes, OpenMausBot (OMB), and Rakazo.

This blueprint does **not** clone Grok / OMB / Rakazo seats. It configures remotes,
probes health, and (when the remote exposes an API) lists or sends a job through
`swarm.core.remotes`. Specialists are openai-agents **agent-as-tool** wrappers.

Grok-Bot chrome is **not** claimed live.

## Configure

```bash
swarm-cli remotes set hermes --base-url http://10.0.0.36:8642 --api-key-env HERMES_API_KEY
swarm-cli remotes set omb --base-url http://10.0.0.32:8802 --api-key-env OMB_API_KEY
swarm-cli remotes set rakazo --base-url http://10.0.0.32:3100 --ui-url http://10.0.0.32:5173 --api-key-env RAKAZO_API_KEY
```

Or `PATCH /v1/remotes/<id>/`. See [docs/REMOTE_HARNESSES.md](../../../docs/REMOTE_HARNESSES.md).

## Grammar

```
health
health hermes
list
list omb
send hermes summarize systemd units
```

LAN LLM for *this* swarm (not a remote harness): `http://10.0.0.30:8000/v1`.
Do not point remotes at Fly open-litellm.
