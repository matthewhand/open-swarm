# CLI Fusion — your installed agentic CLIs, behind one OpenAI endpoint

Most agentic CLIs (`claude`, `gemini`, `codex`, `opencode`, …) are powerful but
**not** OpenAI-compatible, and each only orchestrates its own model's subagents.
Open Swarm's CLI-fusion blueprints turn whatever CLIs you already have installed
into composable, API-addressable subagents:

- **`cli_agent`** — expose a *single* CLI over `/v1/chat/completions`.
- **`cli_fusion`** — fan a prompt to a *panel* of CLIs in parallel, have a
  *judge* compare their answers, *synthesize* a single best answer, and
  optionally iterate a bounded **master plan** (the judge decides the next step).

Inspired by [OpenRouter Fusion](https://openrouter.ai/docs/guides/features/plugins/fusion),
except the panelists are *your local toolbox*, not a fixed hosted set — and they
can use any tools their own CLI provides (MCP servers, file access, web, …).

Any OpenAI client (Open WebUI, Cursor, the OpenAI SDK, a shell script) talks to
them with no changes — just point at the Open Swarm API and pick the model name.

---

## Quick start

1. Add a `cli_agents` block (and optionally `cli_fusion`) to your
   `~/.config/swarm/swarm_config.json` — see [the example](#full-example) below.
2. Make sure the CLIs are installed and **logged in** on the host (each CLI
   authenticates itself; Open Swarm does not proxy their credentials).
3. Call the API:

```bash
# Single CLI:
curl -sf http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer ${API_AUTH_TOKEN}" -H "Content-Type: application/json" \
  -d '{"model":"cli_agent","messages":[{"role":"user","content":"Explain this repo"}],
       "params":{"cli":"claude"}}' | jq -r '.choices[0].message.content'

# Fusion panel:
curl -sf http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer ${API_AUTH_TOKEN}" -H "Content-Type: application/json" \
  -d '{"model":"cli_fusion","messages":[{"role":"user","content":"Design a rate limiter"}],
       "params":{"preset":"general-high","show_analysis":true}}' | jq -r '.choices[0].message.content'
```

`params` is the standard Open Swarm per-request field; OpenAI SDKs send it via
`extra_body={"params": {...}}`.

### Autodiscovery

See which of your configured CLIs are actually installed on the host:

```bash
swarm-cli cli-agents               # install status only (fast)
swarm-cli cli-agents --check-auth  # also probe each CLI's auth_check
swarm-cli cli-agents --suggest     # propose config for installed-but-unconfigured CLIs
swarm-cli cli-agents --smoke       # run one trivial one-shot per CLI to confirm it returns
swarm-cli cli-agents --config ./swarm_config.json
```

`--smoke` is the counterpart to `--check-auth`: auth tells you the CLI is logged
in; smoke tells you its configured `cmd` actually **returns** in non-interactive
mode instead of hanging on a prompt. Each probe runs one trivial one-shot
(`status` of `ok` / `hang` / `error` / `not_installed`) — a `hang` almost always
means a missing or wrong non-interactive/auto-approve flag. Unlike auth, the
smoke probe invokes the model once per CLI, so it costs a little quota; it's
opt-in for that reason.

`--suggest` checks a built-in catalog of known-good adapter configs against your
host and prints a ready-to-paste `cli_agents` block for every supported CLI
(`claude`, `gemini`, `codex`, `opencode`) that is installed but not yet in your
config — so getting started is "install the CLI, run `--suggest`, paste". The
suggested flags track each CLI's non-interactive + auto-approve mode; verify them
against the CLI's own `--help`, since flags drift by version.

```
AGENT            STATUS     MODE       EXECUTABLE
claude           installed  write      /home/you/.local/bin/claude
codex            missing    write      -
gemini           installed  write      /home/you/.nvm/.../gemini
3/4 configured CLI agents installed on this host.
```

---

## Config: `cli_agents`

Each entry declares how to run one CLI **one-shot**. The command is an argv list
executed directly (no shell), so the prompt is never interpolated into a shell
string.

| Key | Type | Meaning |
|---|---|---|
| `cmd` | list[str] | argv. Put `{prompt}` where the prompt goes; `{workdir}` for the working dir. |
| `prompt_mode` | `"arg"` \| `"stdin"` | `arg` (default) substitutes `{prompt}` into `cmd`; `stdin` pipes it to stdin. |
| `parse` | `"text"` \| `"json:<dotpath>"` | `text` (default) = trimmed stdout. `json:.result` parses JSON and extracts a dotted path (list indices allowed, e.g. `json:.choices.0.message.content`). |
| `cwd` | str | Working directory template (`{workdir}` allowed). Defaults to the per-request `workdir` or the server CWD. |
| `env` | dict | Extra env vars merged onto the child's environment. |
| `env_allowlist` | list[str] \| null | **null (default):** child inherits the full environment (convenient, but every panelist sees every API key). **Set it:** child gets only these vars plus essentials (`PATH`, `HOME`, …) — isolates each CLI's secrets. |
| `timeout` | number | Seconds before the CLI (and its whole process group) is killed. Default 180. |
| `mode` | str | Free-text label documenting safety posture (`"readonly"`, `"write"`). Advisory. |
| `auth_check` | list[str] | Optional argv probe for `swarm-cli cli-agents --check-auth`. Exit 0 ⇒ authenticated. Should be cheap and not consume quota (capped at 30s). |

> ⚠️ **Exact flags and JSON shapes vary by CLI version.** The snippets below are
> starting points — run the CLI's `--help` and confirm its non-interactive flag,
> its auto-approve flag, and (if using `json:` parse) the actual key in its JSON
> output. When in doubt, use `parse: "text"`.

### Non-interactive mode is the whole game

The adapter runs each CLI with stdin closed and a timeout. The flag that makes or
breaks a run is the **auto-approve** one: in non-interactive mode an agentic CLI
will otherwise stop mid-task to ask "may I write this file / run this command?",
and since there's no one to answer, it blocks until the timeout kills it. So to
get a panelist that actually *does work*, pin down two flags from its `--help`:

1. its **print/exec/run** flag (one-shot, non-interactive), and
2. its **auto-approve / skip-permissions** flag (so it never waits on a prompt).

| CLI | Print/exec | Auto-approve (full-capability) | Structured output → `parse` |
|---|---|---|---|
| `claude` | `-p` | `--dangerously-skip-permissions` | `--output-format json` → `json:.result` |
| `gemini` | `-p` | `--yolo` | `-o json` → `json:.response` |
| `codex` | `exec` | `--dangerously-bypass-approvals-and-sandbox` (or `--full-auto`) | text |
| `opencode` | `run` | (none needed — `run` acts without an approval gate) | text |

### Example adapters

```jsonc
"cli_agents": {
  "claude": {
    "cmd": ["claude", "-p", "{prompt}", "--output-format", "json",
            "--dangerously-skip-permissions"],
    "parse": "json:.result",
    "mode": "write",
    "timeout": 240
  },
  "gemini": {
    "cmd": ["gemini", "-p", "{prompt}", "-o", "json", "--yolo"],
    "parse": "json:.response",
    "mode": "write"
  },
  "codex": {
    "cmd": ["codex", "exec", "{prompt}", "--dangerously-bypass-approvals-and-sandbox"],
    "parse": "text",
    "mode": "write"
  },
  "opencode": {
    "cmd": ["opencode", "run", "{prompt}"],
    "parse": "text",
    "mode": "write"
  }
}
```

These panelists run at **full capability** — they can read, write, and run
commands. The one real hazard of fanning several write-capable agents out in
parallel is that they stomp each other's edits in a shared tree; `cli_fusion`
solves that by giving each panelist its own working copy — see
[Workdir isolation](#workdir-isolation).

---

## Config: `cli_fusion`

| Key | Type | Meaning |
|---|---|---|
| `default_cli` | str | Which adapter the `cli_agent` blueprint uses when the request doesn't name one. |
| `presets` | dict | Named panels. Each preset: `{ "panel": [names], "judge": name }`. |
| `default_preset` | str | Preset used by `cli_fusion` when the request doesn't specify a panel/preset. |
| `max_rounds` | int | Master-plan rounds (default 1, hard-capped at 5). |
| `max_concurrency` | int | Max CLI subprocesses launched at once per round (default 8). |
| `isolate_workdir` | bool \| null | Give each panelist its own working copy so parallel writes don't collide. **null (default):** auto — isolate when the request's `workdir` is a git repo and the panel has >1 member. **true:** always isolate. **false:** never (all panelists share one workdir). See [Workdir isolation](#workdir-isolation). |
| `show_analysis` | bool | Append the judge's consensus/contradictions/gaps footer to the answer. |

```jsonc
"cli_fusion": {
  "default_cli": "claude",
  "default_preset": "general-high",
  "max_rounds": 1,
  "isolate_workdir": true,
  "show_analysis": false,
  "presets": {
    "general-high":   { "panel": ["claude", "gemini", "codex"], "judge": "claude" },
    "general-budget": { "panel": ["gemini"],                    "judge": "gemini" }
  }
}
```

### Per-request `params`

| Param | Applies to | Meaning |
|---|---|---|
| `cli` | cli_agent | Which adapter to run. |
| `panel` | cli_fusion | Explicit list of adapter names (overrides preset). |
| `preset` | cli_fusion | Named preset to use. |
| `judge` | cli_fusion | Judge adapter (overrides preset's). |
| `max_rounds` | cli_fusion | Override master-plan rounds (capped at 5). |
| `isolate` | cli_fusion | Override `isolate_workdir` for this request (`true`/`false`). |
| `show_analysis` | cli_fusion | Override the analysis footer. |
| `timeout` | both | Override every adapter's timeout for this request. |
| `workdir` | both | Working directory for the CLI(s). |

---

## How fusion works

```
prompt ─► panel: N CLIs run in PARALLEL (asyncio.gather), each one-shot
            │
            ▼
        judge CLI: compares (not concatenates) the answers → structured JSON
            { consensus, contradictions, gaps, unique_insights, answer, done, next_step }
            │
            ▼
        synthesize: judge's "answer" (or longest panel answer if no judge)
            │
       done? ──no──► feed answer + next_step back as the next round's prompt
            │
           yes ─► final answer (the only chunk marked final)
```

- **No judge configured?** Fusion still works — it falls back to the longest
  successful panel answer.
- **Master plan:** when `max_rounds > 1` and the judge returns `"done": false`,
  its `"next_step"` becomes the next round's instruction. The loop stops on
  `done`, at `max_rounds`, or if every panelist fails.
- **Progress** (per-round panel/judge status) streams as a side-channel chunk
  (`{"type":"fusion_progress"}`) that vanilla OpenAI clients ignore, so it never
  pollutes the synthesized answer.

---

## Workdir isolation

Panelists run at full capability, so a panel of N write-capable agents fanned out
over the *same* `workdir` will stomp each other's edits. `cli_fusion` defuses this
by giving each panelist its own working copy for the duration of a round:

- **git repo (the common case):** each panelist gets a throwaway
  `git worktree` checked out at `HEAD`, so it sees the full repo cheaply and its
  edits never touch the source tree or the other panelists. The worktrees are
  removed (`--force`, discarding scratch edits) when the round ends.
- **non-repo `workdir` (or none):** each panelist gets a fresh empty temp
  directory as scratch space.

Controlled by `cli_fusion.isolate_workdir` (config) or the per-request `isolate`
param. The default (`null`) auto-isolates when `workdir` is a git repo and the
panel has more than one member; set it `true` to always isolate or `false` to
share one workdir. The **judge** always runs in the base `workdir` (it only reads
and compares the panel's text answers). Fusion synthesizes a single *text* answer
— it does not merge the panelists' divergent trees, so the isolated edits are
treated as scratch work, not a deliverable.

## Safety

CLI agents can read files, run commands, and reach the network. Treat them as
untrusted, side-effecting processes:

- **Workdir isolation.** Keep `isolate_workdir` on (the default auto-isolates git
  repos) so parallel write-capable panelists can't corrupt the source tree or
  collide — see above.
- **Timeouts always.** Interactive CLIs hang waiting for input if you get the
  non-interactive or auto-approve flag wrong. Every adapter has a `timeout`; on
  expiry the whole process group is killed (SIGTERM → SIGKILL).
- **Secret isolation.** By default every panelist inherits the full environment.
  Set `env_allowlist` per adapter so each CLI sees only the keys it needs.
- **Recursion guard.** If a panelist CLI is itself pointed back at this Open
  Swarm endpoint with `model: "cli_fusion"`, the `SWARM_CLI_FUSION_DEPTH` env var
  (injected into children) makes nested fusion degrade to a single agent — no
  fan-out explosion.
- **Cost.** A panel of N agents over R rounds is ~N×R completions. Keep
  `max_rounds` small and panels focused; use `general-budget` for cheap runs.

---

## Full example

A complete, copy-pasteable config lives at
[`docs/examples/cli_fusion.swarm_config.json`](examples/cli_fusion.swarm_config.json).
