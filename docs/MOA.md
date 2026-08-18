# Mixture of Agents (MoA)

**Primary product name:** Mixture of Agents / MoA  
**Workflow family:** [Orchestrated consensus (model A)](./SWARM_WORKFLOWS.md) — subagents **read-only**; orchestrator owns consensus and writes.  
**Sibling model:** [Persona / agent-as-tool swarm (model B)](./SWARM_WORKFLOWS.md) — openai-agents specialists **read/write**.  
**Legacy names (do not use as primary):** `cli_fusion`, `cli_ensemble`, “fusion panel”

**Live consensus participant:** local **Grok** CLI (`--backend grok`).  
**Not required:** Codex (deferred). acpx multi-vendor is optional when other agents are available.

## Model

| Role | Allowed | Forbidden |
|------|---------|-----------|
| **Participant** (fake / grok / optional acpx) | Read context, reason, propose patches as text | File mutation, commits, mutating shell, package install |
| **Orchestrator** (`MoAOrchestrator`) | Collect opinions, **determine** consensus, optional **act** | Delegating determination or writes to participants |

```
User question
    → MoAOrchestrator.collect_opinions (N read-only seats)
    → MoAOrchestrator.determine      (orchestrator only)
    → MoAOrchestrator.act            (optional; orchestrator write tools only)
```

## Python API

```python
from swarm.core.moa import MoAOrchestrator, GrokParticipantBackend, FakeParticipantBackend

# CI / demos (no live CLI):
backend = FakeParticipantBackend({
    "analyst": "Prefer token bucket at the edge.",
    "critic": "Prefer token bucket with metrics.",
})
orch = MoAOrchestrator(backend=backend)
result = await orch.run("How should we rate-limit?", participants=["analyst", "critic"])
print(result.determination.answer)

# Live consensus via Grok (first-class path; multi-seat = multiple grok -p):
backend = GrokParticipantBackend()
orch = MoAOrchestrator(backend=backend)
result = await orch.run(
    "Review auth middleware risks",
    participants=["analyst", "critic"],  # two one-shots with seat labels
    cwd="/path/to/repo",
    act=False,
)
```

## Backends

| Backend | When | Notes |
|---------|------|--------|
| **fake** | CI, demos (default CLI) | Injectable opinions; no network |
| **grok** | Live consensus | `grok -p`, write tools disallowed; multi-seat supported |
| **acpx** | Optional multi-vendor | `--approve-reads` + `exec`; **Codex not required** |

Grok command shape (built by `GrokParticipantBackend.build_command`):

```bash
grok -p '<read-only framed prompt>' \
  --disallowed-tools Write,Edit,MultiEdit,NotebookEdit \
  --output-format plain --max-turns 4 --no-subagents --no-plan
```

## Configuration sketch

```json
{
  "moa": {
    "backend": "grok",
    "participants": ["analyst", "critic"],
    "permission": "approve-reads",
    "default_timeout": 300,
    "presets": {
      "default": { "backend": "grok", "participants": ["analyst", "critic"] },
      "ci": {
        "backend": "fake",
        "participants": ["analyst", "critic"],
        "fake_responses": { "analyst": "…", "critic": "…" }
      },
      "single-grok": { "backend": "grok", "participants": ["grok"] }
    }
  }
}
```

**Presets** overlay panel fields only (`backend`, `participants`, `fake_responses`,
optional `permission` / `timeout`). They are **not** where you select team mode.

| Want | How (not a `moa.presets` field) |
|------|----------------------------------|
| Consensus only | `swarm-cli moa …` or model `moa` |
| Consensus → scripted team | `swarm-cli moa … --team --workdir …` |
| Consensus → one implementer write | model `hybrid_moa` |
| Consensus → multi specialist | model `moa_orchestrator` + `params.tasks` |

Install/merge the default block with `swarm-cli moa-init` (see below).

## Dogfood: `swarm-cli moa`

```bash
# Demo / CI — default backend fake
swarm-cli moa "How should we rate-limit the API?" --json

# Explicit fake multi-seat
swarm-cli moa "Pick a cache" --backend fake --participants a,b \
  --fake-responses 'a=Use redis.||b=Use redis with TTL.'

# Live Grok consensus (first-class)
swarm-cli moa "Summarize risks in auth/" --backend grok \
  --participants analyst,critic --cwd .

# Optional acpx (any installed ACP agent except we do not depend on Codex)
swarm-cli moa "Review the design" --backend acpx \
  --participants claude,gemini --cwd .

# Orchestrator-only write after determination
swarm-cli moa "Document the decision" --backend fake --act \
  --act-write ./moa_decision.md

# Consensus then scripted team (no openai-agents; specialists write under --workdir)
swarm-cli moa "Ship rate limiting?" --backend fake --team \
  --workdir /tmp/moa-team \
  --team-tasks 'implementer:Apply|tester:Verify|docs:ADR' \
  --json -v
```

### Orchestrator tool: `consult_moa`

```python
from swarm.core.moa.tools import consult_moa

result = await consult_moa(
    "Should we enable feature flags?",
    ["analyst", "critic"],
    backend="fake",  # or "grok"
    fake_responses={"analyst": '{"claim":"yes","confidence":0.9}', ...},
)
# result["determination"] is orchestrator-owned; never writes
```

Participants may emit free text **or** structured JSON:

```json
{"claim": "use redis with TTL", "confidence": 0.9, "evidence": ["shared cache"]}
```

## Config init

```bash
swarm-cli moa-init              # dry-run print default moa block
swarm-cli moa-init --write      # merge into XDG / discovered swarm_config.json
swarm-cli moa-init --show-openwebui
```

Example file: `docs/examples/moa.swarm_config.json`.  
Open WebUI setup: `docs/OPENWEBUI_MOA.md`.

## Hybrid: consensus → optional specialists

After read-only MoA consensus, impact is **never** delegated to panel seats.
Post-consensus work is almost always **scripted** (`WorkspaceTools` writers).
A live openai-agents `Runner` is **not** the default for `moa_orchestrator`.

| Model id | Behavior (what actually runs) |
|----------|-------------------------------|
| `moa` | Panel opinions + determination only |
| `hybrid_moa` | MoA then one implementer-style write (persona/hybrid path) |
| **`moa_orchestrator`** | MoA then multi-specialist **scripted** team via `run_moa_agents_orchestrator` → `run_moa_then_team` |

### Pure team path (no openai-agents)

`TeamTask` is the canonical task type. CLI: `swarm-cli moa … --team --workdir …`
(`--team-tasks`, mutually exclusive with `--act`). Without `--team`,
`swarm-cli moa --json` is `mode=consensus_only` (same serializer family).

```python
from swarm.core.moa.team import TeamTask, run_moa_consensus, run_moa_then_team

# Consensus only — judgment, no specialist writes
await run_moa_consensus("Ship rate limiting?", moa_backend="fake")

# Consensus then purpose files (implementer/tester/docs/…)
await run_moa_then_team(
    "./ws",
    "Ship rate limiting?",
    specialist_tasks=[TeamTask("implementer", "Apply", "decision.md")],
    moa_backend="fake",
)
```

If the panel returns no usable opinions, the team path **does not** schedule
specialists or write determination artifacts (soft-fail, not silent fake writes).

### Agents-shaped wrapper (still scripted by default)

`run_moa_agents_orchestrator` is a thin result-shape wrapper around
`run_moa_then_team`. It does **not** construct openai-agents `Agent` objects or
call `Runner.run`. Prefer pure `run_moa_then_team` unless you want the
agents-mode result shape / blueprint id. `SpecialistTask` is a **back-compat
alias** of `TeamTask`. For optional live Agent construction only, use
`build_moa_orchestrator_agents` (separate from the dogfood path).

```python
from swarm.core.moa.agents_orchestrator import SpecialistTask, run_moa_agents_orchestrator
# or: from swarm.core.moa.team import TeamTask as SpecialistTask

await run_moa_agents_orchestrator(
    "./ws",
    "Ship rate limiting?",
    specialist_tasks=[
        SpecialistTask("implementer", "Apply", "decision.md"),
        SpecialistTask("tester", "Verify", "test_notes.md"),
    ],
    moa_backend="fake",  # or "grok" for live panel seats
)
```

**Enforcement:** `consult_moa` has no `act` parameter (always no-act). Panel
permission is only `approve-reads` / `deny-all`. Specialists write via sandboxed
`WorkspaceTools`, not panel seats. See `docs/SWARM_WORKFLOWS.md`.

### First-class walkthroughs (diagrams + captured runs)

| Example | Path | Live openai-agents Runner? |
|---------|------|----------------------------|
| **Consensus vs consensus→team** | [`docs/examples/moa-consensus-vs-team/`](./examples/moa-consensus-vs-team/) | **No** — pure `run_moa_consensus` / `run_moa_then_team` / `swarm-cli moa --team` |
| **MoA orchestrator surface** | [`docs/examples/moa-orchestrator/`](./examples/moa-orchestrator/) | **No by default** — same scripted team; optional `build_moa_orchestrator_agents` for live Agents |

```bash
python scripts/demo_moa_grok_multiseat.py   # live multi-seat grok or fake fallback
bash docs/examples/moa-consensus-vs-team/scripts/capture_example_runs.sh
bash docs/examples/moa-orchestrator/scripts/capture_example_runs.sh
```

## Troubleshooting

Common CLI failures (Grok not signed in, `--team` / `--workdir`, `approve-all`
rejected, soft panel exit 1, broken XDG cache): [TROUBLESHOOTING.md §8](./TROUBLESHOOTING.md#8-moa--swarm-cli-moa-common-failures).

## Tests

```bash
pytest tests/core/test_moa*.py tests/cli/test_moa_command.py \
  tests/api/test_moa*.py tests/integration/test_swarm_workflows_proof.py \
  tests/integration/test_hybrid_moa_persona.py tests/core/test_moa_config.py -q --no-cov
```
