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

> ⚠️ **Exact flags and JSON shapes vary by CLI version.** The snippets below are
> starting points — run the CLI's `--help` and confirm its non-interactive flag,
> its read-only/approval mode, and (if using `json:` parse) the actual key in its
> JSON output. When in doubt, use `parse: "text"`.

### Example adapters

```jsonc
"cli_agents": {
  "claude": {
    "cmd": ["claude", "-p", "{prompt}", "--output-format", "json",
            "--allowedTools", "Read,Grep,Glob"],
    "parse": "json:.result",
    "mode": "readonly",
    "timeout": 240
  },
  "gemini": {
    "cmd": ["gemini", "-p", "{prompt}", "-o", "json", "--approval-mode", "plan"],
    "parse": "json:.response",
    "mode": "readonly"
  },
  "codex": {
    "cmd": ["codex", "exec", "{prompt}"],
    "parse": "text"
  },
  "opencode": {
    "cmd": ["opencode", "run", "{prompt}"],
    "parse": "text"
  }
}
```

`--allowedTools Read,Grep,Glob` (claude) and `--approval-mode plan` (gemini) keep
panelists **read-only** — strongly recommended when fanning out in parallel (see
[Safety](#safety)).

---

## Config: `cli_fusion`

| Key | Type | Meaning |
|---|---|---|
| `default_cli` | str | Which adapter the `cli_agent` blueprint uses when the request doesn't name one. |
| `presets` | dict | Named panels. Each preset: `{ "panel": [names], "judge": name }`. |
| `default_preset` | str | Preset used by `cli_fusion` when the request doesn't specify a panel/preset. |
| `max_rounds` | int | Master-plan rounds (default 1, hard-capped at 5). |
| `show_analysis` | bool | Append the judge's consensus/contradictions/gaps footer to the answer. |

```jsonc
"cli_fusion": {
  "default_cli": "claude",
  "default_preset": "general-high",
  "max_rounds": 1,
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

## Safety

CLI agents can read files, run commands, and reach the network. Treat them as
untrusted, side-effecting processes:

- **Read-only panelists by default.** Use each CLI's plan/read-only mode
  (`--approval-mode plan`, `--allowedTools Read,Grep,…`). Only opt specific
  adapters into write mode, and avoid running several write-mode CLIs in the same
  `workdir` in parallel — give them separate `workdir`s.
- **Timeouts always.** Interactive CLIs hang waiting for input if you get the
  non-interactive flag wrong. Every adapter has a `timeout`; on expiry the whole
  process group is killed (SIGTERM → SIGKILL).
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
