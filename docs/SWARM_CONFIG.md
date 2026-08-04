# `swarm_config.json`

> **This page has moved.** The configuration reference now lives in one place to
> avoid drift:
>
> ### → [CONFIGURATION.md](../CONFIGURATION.md)

That canonical guide covers everything `swarm_config.json`:

- **File location, discovery precedence, and environment variables** (XDG path,
  `SWARM_CONFIG_PATH`, `SWARM_RESPONSES_DIR`) — [§1](../CONFIGURATION.md#1-config-file-location-and-discovery)
- **The real config schema** — `llm` profiles, `settings`, `blueprints`,
  `mcpServers` — with a full example ([§2](../CONFIGURATION.md#2-example-config-structure))
- Env-var substitution, per-blueprint model overrides, memory, security/redaction,
  and troubleshooting.

For wrapping agentic CLIs (`cli_agents` / `cli_fusion` blocks) see
[CLI_FUSION.md](./CLI_FUSION.md).
