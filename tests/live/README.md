# Optional live remote integrations

Unlike the simulated-server tests in `tests/core`, this suite exercises the
installed adapters against real services. No URL means three skipped checks;
an explicit URL opts that instance in. Configured failures fail the run.
Nothing loads your Swarm config or `.env` automatically. Ordinary CI has no
`SWARM_LIVE_*` settings and therefore makes no external calls.

Install the development/test extras, then run only this suite:

```bash
uv run pytest tests/live -m live_remote --no-cov -q --tb=no --show-capture=no
```

Provide these through the host's private environment or secret manager. Never
commit an environment file containing real URLs or credentials.

| Variable | Meaning |
|---|---|
| `SWARM_LIVE_TRUEFORGE_URL` | Base URL; required to opt in TrueForge |
| `SWARM_LIVE_TRUEFORGE_API_KEY` | Optional bearer credential, according to server policy |
| `SWARM_LIVE_TRUEFORGE_COOKIE` | Optional session cookie |
| `SWARM_LIVE_TRUEFORGE_TARGET` | Optional agent ID |
| `SWARM_LIVE_TRUEFORGE_TIMEOUT` | Turn deadline in seconds, default 90, range 1–300 |
| `SWARM_LIVE_TRUEFORGE_HEALTH_PATH` | Override adapter's default health route |

Replace `TRUEFORGE` with `OMB` (OpenMousBot), `RAKAZO`, `HERMES`,
`ANYTHINGLLM`, `OPENWEBUI`, `FLOWISE`, `N8N`, `SWARM`, `OCTOP` or `OPENMUSE`.
Herdr uses SSH/CLI and is outside this HTTP suite; its unconfigured entry skips.
No credential is required for services deliberately configured without auth.
Credentials are taken **only** from these variables, never inherited from
the normal kind-level secrets.

For multiple servers of one kind, set `SWARM_LIVE_INSTANCES=trueforge_second`
and `SWARM_LIVE_TRUEFORGE_SECOND_KIND=trueforge`, then define its `_URL`,
`_API_KEY`, etc. Instance names contain lowercase letters, digits and underscores;
the environment prefix is uppercase. Comma-separate additional instance names.

Each instance has independent health, discovery and inference checks. Inference
requires an actual correct answer to a randomized arithmetic question, with
the answer absent from the request. An accepted job or echoed prompt is not
success. A service counts as **working** only when all three checks pass. This
does not certify tools, streaming, computer control, handoffs or every model.
The terminal summary gives counts and per-instance results without printing
URLs, credentials, replies or raw service errors.

Turns may consume model quota and create server-side history. The prompt asks
for no tools or changes. `session_id=None` avoids resuming an operator thread
where the adapter supports fresh sessions. OMB, Rakazo and AnythingLLM require
`_TARGET` pointing to a **dedicated test bot/workspace**, because their adapters
otherwise select existing operator conversations. The suite does not guess a
target, create bots, delete history, or claim an adapter can cancel/delete jobs
without that API. Provision test resources on the development host and retain
or remove them through the service's documented administration interface.

For private diagnosis, inspect server logs rather than enabling HTTP debug
logging in shared test reports. Do not use `--showlocals` with live credentials.
The offline contract tests are `tests/unit/test_live_remote_contract.py`.
