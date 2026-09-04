# Architecture decision records

| ADR | Title |
|-----|--------|
| [ADR-001](../ADR-001-primary-ui.md) | Primary UI is Django; SPA Chat only |
| [ADR-002](./002-config-ownership.md) | Config ownership — `.env` vs XDG `swarm_config.json` vs Django DB |
| [ADR-003](./003-kind-bases.md) | Three kind bases (API / CLI / remote) — Support subclasses these |
| [ADR-003](./003-desktop-packaging.md) | Desktop packaging — local server + pywebview (Windows first) |
| [ADR-004](./004-virtualized-chat-history.md) | Virtualized infinite chat history — `@tanstack/react-virtual` ≥ 3.14 (REQ-163) |

Related research (not an ADR): [Grok Bot keybinding parity](../GROK_KEYBINDING_PARITY.md) (REQ-150 / #552).
