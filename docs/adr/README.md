# Architecture decision records

| ADR | Title |
|-----|--------|
| [ADR-001](../ADR-001-primary-ui.md) | Primary UI is Django; SPA Chat only |
| [ADR-002](./002-config-ownership.md) | Config ownership — `.env` vs XDG `swarm_config.json` vs Django DB |
| [ADR-006](./006-api-vs-blueprint-kinds.md) | Separate API (inference seat) from Blueprint (programmatic) — REQ-193 |

ADR-003 (desktop packaging, #576), ADR-004 (virtualized chat, #582), and ADR-005 (three kind bases, [PR #578](https://github.com/matthewhand/open-swarm/pull/578)) are claimed on other branches and are not in this tree yet. ADR-006 **amends** ADR-005’s `ApiKindBase` slot: user-facing kinds become CLI \| API \| Blueprint \| Remote.
| [ADR-003](./003-desktop-packaging.md) | Desktop packaging — local server + pywebview (Windows first) |
| [ADR-004](./004-virtualized-chat-history.md) | Virtualized infinite chat history — `@tanstack/react-virtual` ≥ 3.14 (REQ-163) |
| [ADR-005](./005-kind-bases.md) | Three kind bases (API / CLI / remote) — Support subclasses these |

Related research (not an ADR): [Grok Bot keybinding parity](../GROK_KEYBINDING_PARITY.md) (REQ-150 / #552).
