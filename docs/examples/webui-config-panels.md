# Builder config panels (web UI)

Proof of the Builder UI panels that configure the decoupling features, each
bound to `GET /v1/config-options/`. Built on the existing React + TanStack Query
+ DaisyUI stack. 0 axe violations (full ruleset, light/dark, desktop/mobile).

## Panel 1 — Inference profile (+ per-model traits)

Declare what kind of inference you want (intelligence / speed / cost, each an
optional 0–1 target) and the Builder live-previews which CLI/model it resolves
to — mirroring `swarm.core.inference_profile` (distance-from-ideal over only the
axes you enable). Per-model candidates (`<cli>@<model>`) are included, so e.g.
asking for intelligence 0.90 resolves to `claude` model `claude-sonnet-4-6`
(its 0.90 is closer than opus's 0.98).

![Inference profile panel](../screenshots/webui/inference-profile-dark.png)

It emits a request snippet (`{"params": {"profile": {...}}}`) you can paste into
any OpenAI-compatible call.

**Verification**
- Pure resolver mirror `src/lib/inferenceProfile.ts` unit-tested (6 cases:
  single-axis, fast+cheap, balanced→all-rounder, tie-break, empty) + a
  `buildCandidates` test. 26 vitest tests pass.
- `npx tsc --noEmit` clean; `npm run build` succeeds.
- axe full-ruleset audit: **0 violations** across builder light/dark, desktop/mobile.

_(Panels 2 (tool capabilities/MCP) and 3 (skills picker) follow.)_

## Panel 2 — Tool capabilities / MCP

Declare abstract capabilities (off / optional / mandatory) and pick MCP
providers. Non-auth servers are surfaced first with a green "no key" badge;
`brave-search` is opt-in with a key badge. The panel live-resolves each required
capability to a provider (non-auth preferred) and emits `mcpServers` +
`tool_requirements`.

![Tool capabilities panel](../screenshots/webui/tool-capabilities-dark.png)

Example above: `web_search` (mandatory) → `duckduckgo`, `browser` (optional) →
`playwright` — both non-auth, runnable with no API key.

**Verification**
- Pure resolver `src/lib/toolCapabilities.ts` unit-tested (6 cases: non-auth
  preference, missing mandatory, optional skip, auth-key gating, suggestion,
  config emission). 32 vitest tests pass; `tsc` clean; build OK.
- axe full-ruleset audit: **0 violations**, now stable across runs.

### Fixed: a11y-audit theme-forcing (item 4)

The audit set `data-theme` only on existing `[data-theme]` nodes, leaving a
white `<body>`; axe then saw dark text on white and reported false
`color-contrast` failures that flaked between desktop/mobile dark. Fixed by
seeding the theme via `addInitScript` before load and setting `data-theme` on
`<html>`, plus waiting for a real selector instead of `networkidle`. Result: 0
violations, deterministic across repeated runs.
