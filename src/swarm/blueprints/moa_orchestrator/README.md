# moa_orchestrator

**openai-agents mode orchestrator** for Mixture of Agents:

1. Collect **read-only** MoA consensus (`consult_moa`, never act)
2. Task purpose-specific **R/W** specialists: `implementer`, `tester`, `docs`, `researcher`

```bash
# Default: MoA panel → implementer writes decision.md
# model: moa_orchestrator
# params: { "backend": "fake", "workdir": "/tmp/orch", "tasks": "implementer:apply|tester:verify" }
```

See `docs/SWARM_WORKFLOWS.md` and `docs/MOA.md`.
