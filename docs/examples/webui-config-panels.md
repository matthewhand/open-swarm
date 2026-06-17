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
