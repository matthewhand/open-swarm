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
    "default_timeout": 300
  }
}
```

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

## Tests

```bash
pytest tests/core/test_moa*.py tests/cli/test_moa_command.py \
  tests/api/test_moa*.py tests/integration/test_swarm_workflows_proof.py -q --no-cov
```
