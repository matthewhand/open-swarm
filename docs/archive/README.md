# Archive — superseded architectures and plans

This folder is the project's memory of paths we have taken and moved past. It is
kept deliberately: it explains *why* the current design looks the way it does.
Nothing here describes the current system — for that, start at
[../VISION.md](../VISION.md).

> Status of everything in this folder: **historical**. Do not treat any document
> here as current guidance.

## What lives here

| Document | Era | What it captured | Superseded by |
|---|---|---|---|
| [IMPLEMENTATION_SUMMARY.md](./IMPLEMENTATION_SUMMARY.md) | 2026-06 | Snapshot of the FOSS-cleanup implementation wave | [ROADMAP.md](../../ROADMAP.md), [FEATURE_STATUS.md](../../FEATURE_STATUS.md) |
| [2026-06-cleanup-commit-log.txt](./2026-06-cleanup-commit-log.txt) | 2026-06 | Raw commit log of the cleanup wave (PRs #80–#85) | git history |

## Related historical documents kept in place

These still live under `docs/` for their inbound links, but describe earlier
architectures rather than the current one:

- [../architecture_marketplace_to_mcp.md](../architecture_marketplace_to_mcp.md)
  — the marketplace → local config → secure MCP → clients flow. A blueprint
  *distribution* design that predates the CLI-fusion direction. The MCP-provider
  resolution idea survives in `swarm.core.tool_capabilities`; the marketplace
  framing does not.
- [../TODO.md](../TODO.md) — the original phase-based "make it run as in the
  README" milestone plan. Superseded as the source of truth by
  [ROADMAP.md](../../ROADMAP.md); retained as history.

## Lineage in one paragraph

Open Swarm began as a derivative of OpenAI's experimental
[Swarm](https://github.com/openai/swarm), then migrated its runtime to the
[openai-agents SDK](https://github.com/openai/openai-agents-python). An early
emphasis on a blueprint **marketplace** and MCP distribution (the
marketplace-to-MCP doc above) gave way, after a 2026 FOSS-cleanup wave, to the
current focus: an **OpenAI-compatible gateway that adapts and orchestrates
agentic CLIs** (see [../VISION.md](../VISION.md)). The MCP work did not vanish —
it became the tool-capabilities layer — but it is no longer the headline.
