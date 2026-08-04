# Proofs — live cross-CLI transcripts

Raw, re-runnable evidence that the orchestration patterns work over **real**
heterogeneous agentic CLIs (not mocks). Captured 2026-06-17 against
`gemini` (gemini-2.5-flash-lite), `claude -p`, and `grok` on this machine.

| File | Pattern | What it shows |
|---|---|---|
| [tri_cli_fusion_run.txt](./tri_cli_fusion_run.txt) | `cli_fusion` (concurrent) | One prompt fanned to gemini + claude + grok in parallel; a claude judge synthesizes; analysis surfaces consensus, contradictions, gaps, and per-model unique insights. ~27 s. |
| [orchestrator_escalation_run.txt](./orchestrator_escalation_run.txt) | `cli_orchestrator` (handoff) | A gemini router answers directly and states whether to escalate, reserving the panel for contested questions. |
| [pipeline_run.txt](./pipeline_run.txt) | `cli_pipeline` (sequential) | gemini drafts, claude reviews and tightens — the refined paragraph is the output of the chain. ~18 s. |
| [roundtable_run.txt](./roundtable_run.txt) | `cli_roundtable` (group chat) | gemini + grok debate trunk-based vs feature branches; a claude moderator concludes after one round and synthesizes a sided answer. ~22 s. |
| [planner_run.txt](./planner_run.txt) | `cli_planner` (Magentic-One) | claude plans a ledger, a worker executes, the planner reviews and concludes — yielding a 12-point production-safety checklist. ~35 s. |
| [tool_calling_run.txt](./tool_calling_run.txt) | tool use | gemini and claude each read a real file (`pyproject.toml`) via their own tools and return the exact version string. |

## Re-running

The fusion and orchestrator transcripts were produced by driving the blueprints
directly with a config that maps the three CLIs (`gemini`/`claude`/`grok`) as
`cli_agents`. For the full installed-CLI-by-framework-mode matrix (12/12 pass),
see [`scripts/prove_cli_permutations.py`](../../scripts/prove_cli_permutations.py).

> Note on gemini quota (free tier, 2026-06): `gemini-2.5-flash-lite` was reliable;
> `gemini-2.5-flash` was intermittently rate-limited (HTTP 429); `gemini-2.5-pro`
> reported capacity exhausted. The transcripts use flash-lite for stability.
