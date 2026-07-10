# Open Swarm workflow models

Open Swarm has **two primary multi-agent workflow styles**. They differ in
*who may change the world* and *how specialization is expressed*.

| | **A. Orchestrated consensus (MoA)** | **B. Persona / agent-as-tool swarm** |
|---|---|---|
| **Primary name** | Mixture of Agents (MoA) | openai-agents team / persona swarm |
| **Core idea** | Many **independent** subagents opine; **one orchestrator** decides and acts | **One coordinating agent** (or small graph) **switches personas** / delegates to specialists via the `openai-agents` SDK |
| **Subagents** | Encouraged **read-only** (consultants) | Encouraged **read/write** (doers with tools) |
| **Consensus** | Explicit: collect → **orchestrator determine** → optional **act** | Implicit: coordinator chooses next persona/tool; no formal multi-model vote required |
| **Typical backends** | **fake** (CI), **grok** (live consensus), optional acpx (`swarm.core.moa`). Codex not required. | In-process `Agent`, handoffs, `as_tool()`, MCP, `@function_tool` |
| **Write authority** | **Orchestrator only** after determination | **Specialists + coordinator** (tools: write_file, shell, git, …) |
| **When to use** | Cross-model judgment, review, high-stakes “what should we do?” | Implementation, multi-step coding, domain teams that *execute* |

```
A. Consensus (read-only subagents)
──────────────────────────────────
  User task
      │
      ▼
  Orchestrator ──consult──► Subagent₁ (read-only opinion)
              ├──consult──► Subagent₂ (read-only opinion)
              └──consult──► Subagentₙ (read-only opinion)
      │
      ▼
  Orchestrator.determine()   ← sole consensus owner
      │
      ▼
  Orchestrator.act()         ← sole write / impact path (optional)

B. Persona swarm (read/write specialists)
─────────────────────────────────────────
  User task
      │
      ▼
  Coordinator Agent (openai-agents)
      │  handoff / agent-as-tool / tool call
      ├──► Persona: Researcher  (read + tools)
      ├──► Persona: Implementer (read/write)
      └──► Persona: Reviewer    (read/write as allowed)
      │
      ▼
  Continues until coordinator ends the turn
```

## A — Orchestrated consensus (Mixture of Agents)

**Policy:** subagents are **consultants**. They may inspect and argue; they
must not be the path that mutates the workspace as part of the consensus round.

| Layer | Responsibility |
|-------|----------------|
| Participants | Text (or structured) opinions only; permission `approve-reads` / `deny-all` |
| Orchestrator | Frame question, call `collect` / `consult_moa`, **determine**, optional **act** |
| Act tools | File/shell/git — owned by orchestrator (or a deliberate post-consensus delegate), not by panelists |

**Code surfaces**

- `swarm.core.moa` — `MoAOrchestrator`, backends, policy, schema
- `swarm.core.moa.tools.consult_moa` — orchestrator tool entry
- `swarm-cli moa` — CLI dogfood
- Blueprint `moa` (legacy names: `cli_fusion` / `cli_ensemble` → read-only MoA only)

**Docs:** [MOA.md](./MOA.md)

## B — Persona / agent-as-tool swarm (openai-agents)

**Policy:** specialists are **operators**. They are encouraged to use the full
tool surface (read *and* write) appropriate to their role. The “switch” is not
a formal vote; the coordinator (or graph) selects the next persona via:

- multiple `Agent` instances + handoffs  
- agent-as-tool (`specialist.as_tool(...)`)  
- shared `@function_tool` / MCP tools  

**Code surfaces**

- `openai-agents` dependency: `Agent`, `Runner`, `@function_tool`, handoffs  
- `BlueprintBase` blueprints under `src/swarm/blueprints/`  
  (e.g. codey, rue_code, geese, zeus, digitalbutlers, …)  
- Built-in tools: [framework_builtin_tools.md](./framework_builtin_tools.md)

Here “subagent” often means **another Agent in the same process** with a
different system prompt and tool set—not an external CLI panelist.

## Choosing A vs B

| Situation | Prefer |
|-----------|--------|
| “What should we do?” / design review / multi-vendor judgment | **A (MoA)** |
| “Do the work” / implement / refactor / operate systems | **B (persona swarm)** |
| High-stakes decision *then* implement | **A then B**: MoA determine → orchestrator (or a B team) acts |
| Cheap single-model coding agent | **B** alone |

## Hybrid (supported pattern)

The orchestrator in **B** can call **A** as a tool:

```text
Persona swarm coordinator
    └── consult_moa(question, participants=…)   # read-only panel
    └── write_file / shell / …                  # after it accepts the determination
```

That keeps champagne consistent: **opinions from the panel, impact from the owner**.

### Code

```python
from swarm.core.persona_swarm import run_hybrid_scripted

result = await run_hybrid_scripted(
    "./workspace",
    "Should we enable edge rate limiting?",
    seed_files={"notes.txt": "API is public."},
    moa_backend="fake",  # or "grok" for live
)
# result.steps[0] == consult_moa (read-only)
# result.steps[1] == implementer write decision.md
```

### openai-agents orchestrator mode (recommended)

The orchestrator is an openai-agents **coordinator**. It:

1. Calls **MoA** for read-only multi-seat consensus (`consult_moa`, never `act`)
2. Tasks **purpose-specific R/W agents**: `implementer`, `tester`, `docs`, `researcher`

```python
from swarm.core.moa.agents_orchestrator import (
    SpecialistTask,
    run_moa_agents_orchestrator,
)

result = await run_moa_agents_orchestrator(
    "./workspace",
    "Should we enable edge rate limiting?",
    specialist_tasks=[
        SpecialistTask("implementer", "Apply decision", "decision.md"),
        SpecialistTask("tester", "Write verification notes", "test_notes.md"),
        SpecialistTask("docs", "Write ADR", "docs/ADR.md"),
    ],
    moa_backend="fake",  # or "grok"
)
# Panel never writes; specialists do.
```

API model ids:

| Model | Behavior |
|-------|----------|
| `moa` | Consensus only (read-only panel + determination) |
| `hybrid_moa` | MoA then single implementer write |
| `moa_orchestrator` | MoA then multi-specialist R/W tasks (`params.tasks`) |

```json
{
  "model": "moa_orchestrator",
  "messages": [{"role": "user", "content": "Ship feature X?"}],
  "params": {
    "backend": "grok",
    "participants": ["analyst", "critic"],
    "workdir": "/tmp/orch",
    "tasks": "implementer:apply|tester:verify|docs:adr"
  }
}
```

**Enforcement:** MoA path always `act=False` + read-only permissions. Specialist
agents alone get `write_file` / shell-class tools. Coordinator instructions
require consult-before-write for high-stakes work.

## Naming

| Use | Avoid as primary |
|-----|------------------|
| Mixture of Agents / MoA / orchestrated consensus | fusion, ensemble (legacy aliases only) |
| Persona swarm / agent-as-tool / openai-agents team | calling MoA panelists “writers” |

## Prove it

```bash
# Full MoA + dual-workflow + leftovers suite
pytest tests/core/test_moa*.py tests/cli/test_moa_command.py \
  tests/api/test_moa_api.py tests/integration/test_swarm_workflows_proof.py -v --no-cov

# Live artifact-producing run
python scripts/prove_swarm_workflows.py

# OpenAI-compatible HTTP (model id)
# POST /v1/chat/completions
# {"model":"moa","messages":[...],
#  "params":{"backend":"fake","participants":["analyst","critic"],
#            "fake_responses":{"analyst":"...","critic":"..."}}}
# system_fingerprint → "moa:analyst+critic"
# Live: "params":{"backend":"grok","participants":["analyst","critic"]}
```

| Path | What is proven |
|------|----------------|
| **A** | Multi-participant MoA via `run_moa_cli` / `swarm-cli moa`; `approve-reads` only; orchestrator `act` writes; participant write denied |
| **A live** | Grok first-class backend (`GrokParticipantBackend`); multi-seat one-shots; Codex not required |
| **B** | Real `agents.Agent` personas with R/W `function_tool`s; coordinator switches researcher → implementer; implementer writes `summary.md` |
| **API** | Discoverable model ids `moa` / `mixture_of_agents` / legacy aliases; fingerprint from meta |
| **Resilience** | Failover chain, per-participant timeout, vote weights |

Code: `swarm.core.moa`, `swarm.core.persona_swarm`, `scripts/prove_swarm_workflows.py`.

## Related

- [MOA.md](./MOA.md) — consensus path details  
- [blueprints/README.md](../src/swarm/blueprints/README.md) — persona-swarm examples  
- [framework_builtin_tools.md](./framework_builtin_tools.md) — default R/W tools for B  
