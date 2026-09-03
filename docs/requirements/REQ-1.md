# REQ-1

Intent: operators pick how an agent talks — API (coded team / LiteLLM), host CLI, or remote team — not a single undifferentiated roster.

Success:
1. Public agent types are `api`, `cli`, and `remote` (`swarm.core.agent_types`, SPA `agent-types.ts`).
2. Agent Router header extras are type-gated: CLI model (catalog + custom string), API blueprint, remote member.
3. Backend select options are gated the same way (no LiteLLM on a CLI agent, no CLI binary on an API agent).
4. CLI agents can consume OMB-style MCP servers via the CLI adapter (`swarm.core.cli_mcp`).
5. Persist type + params on the agent record (`params.backend`).

Constraints: Do not invent TBD Rakazo/OMB ports. No extra UI frameworks.

Owner: open-swarm engineer.
