# REQ-95 Scope C — Docs layout (look-only)

**Audit only. No moves, deletes, or rewrites of existing docs.**

> **REQ-95** (GitHub [#452](https://github.com/matthewhand/open-swarm/issues/452)):
> look-only folder / file structure audit. Scope **C** is `docs/` vs root
> guides (README / USERGUIDE / DEVELOPMENT / CONTRIBUTING / ROADMAP / TODO /
> FEATURE_STATUS / CONFIGURATION), plus `docs/debt/` and leftover
> `docs/requirements/` pointers.
>
> Standing rule: **GitHub Issues are the REQ source of truth.**
> `docs/requirements/` should be **pointers only** if present.
>
> Success: inventory table (path, role, load-bearing Y/N/?, proposed action:
> keep / move / merge / delete / archive) and a short “do not do yet” list.
> Cite `#452`. No product-code changes. No secret dumps. No live host.

Audited at `origin/main` @ `dfd72eef` (2026-09-04 tree). Counts on this
snapshot: **81** markdown files under `docs/`, **188** files under `docs/`
including PNGs/captures, **9** root narrative `*.md` (plus `CHANGELOG.md`),
**21** files in `docs/requirements/`, **4** existing `docs/debt/` audits
(do **not** rewrite — reference only).

Sibling look-only scopes (out of this file): **A** root sprawl, **B** app
packages, **D** deploy/CI. Product-code debt already filed:

| Existing debt file | REQ | Do not rewrite |
|--------------------|-----|----------------|
| [`docs/debt/core.md`](./core.md) | REQ-22c | Docs honesty is **P0-4** there (GLOSSARY / VISION still teach Blueprint-as-composition). |
| [`docs/debt/webui.md`](./webui.md) | REQ-22a | Caption/IA locks on GUIDED_TOUR / SCREENSHOTS / FEATURE_STATUS. Starting tree was older (`91dabd64`). |
| [`docs/debt/tests-ci.md`](./tests-ci.md) | REQ-22d | **D-01 / D-02 / D-14**: screenshot goldens + caption lockfile freeze 2026-08-19 chrome. |
| [`docs/debt/django-spa-overlap.md`](./django-spa-overlap.md) | REQ-22b | **D-19**: stale ADR / ROADMAP / websocket / GLOSSARY HTMX overclaim. Starting tree `4d554ea5`. |

---

## How to read this

| Load-bearing | Meaning |
|--------------|---------|
| **Y** | Linked from README / CONTRIBUTING / tests / capture registry, or is the current operator map. Do not delete without a replacement. |
| **N** | Historical, stub, or superseded. Safe to archive/delete in a later implementer PR. |
| **?** | Useful content, but duplicated or partially stale — decide after CoS review. |

| Proposed action | Meaning (later implementer — **not this PR**) |
|-----------------|-----------------------------------------------|
| **keep** | Canonical location. Fix honesty in a dedicated docs PR if stale. |
| **merge** | Fold into a named canonical file, then pointer or delete the loser. |
| **pointer-to-Issue** | Replace body with a link to the GitHub Issue (REQ SoT). |
| **archive** | Move under `docs/archive/` (already the historical bin). |
| **delete** | Remove after inbound links are retargeted. No mass-delete in this wave. |
| **leave** | Keep on disk; do not promote; do not enable (Oracle / Neon). |

---

## 1. Inventory

### 1.1 Root narrative guides

| Path | Role | Load-bearing | Proposed action |
|------|------|--------------|-----------------|
| `README.md` | Product front door: install, API, vocabulary, doc map | **Y** | **keep** — honesty pass later (still says `/` is SPA **dashboard**; live `App.tsx` mounts `ChatPage` at `/` and `/chat`) |
| `USERGUIDE.md` | `swarm-cli` task reference; documents the four-file doc map | **Y** | **keep** — CLI SoT |
| `DEVELOPMENT.md` | Internal architecture / layout / testing | **Y** (linked) | **merge** into a rewritten `docs/DEVELOPER_GUIDE.md` — tree listing is fiction (`setup.py`, `extensions/blueprint`, `echocraft/`, `swarm_config.json.example`) |
| `CONTRIBUTING.md` | Clone, test, ruff, conventional commits | **Y** | **keep** — fix “alpha-stage” vs README “beta” |
| `ROADMAP.md` | Claims “single source of truth for project status”; last updated **2026-06-19** (v0.5.1) | **Y** | **keep** as *future* checklist only; **demote** status-SoT claim (Issues + FEATURE_STATUS win) |
| `TODO.md` | Fine-grained leftovers; says ROADMAP is status SoT | **?** | **merge** remaining open bullets into ROADMAP or Issues; several “Docs” bullets already done |
| `FEATURE_STATUS.md` | Live evidence board; last updated **2026-08-18** | **Y** | **keep** — closest honest status file; not a REQ SoT |
| `CONFIGURATION.md` | `swarm_config.json` + env vars | **Y** | **keep** — config SoT (`docs/SWARM_CONFIG.md` already points here) |
| `CHANGELOG.md` | Release notes (out of Scope C “guides” list; listed for completeness) | **Y** | **keep** — not a getting-started guide |

`docs/TODO.md` already points at root `ROADMAP.md` + `TODO.md`. That pattern
is the model for other duplicates.

### 1.2 `docs/` top-level narrative

| Path | Role | Load-bearing | Proposed action |
|------|------|--------------|-----------------|
| `docs/VISION.md` | North-star: adapt + orchestrate CLIs as `model` ids | **Y** | **keep** — later honesty: still teaches Blueprint-as-composition ([`core.md` P0-4](./core.md)) |
| `docs/GLOSSARY.md` | v1 vocabulary (Blueprint / Team / Profiles / roster / MoA / Session) | **Y** | **keep** — most current noun map |
| `docs/ADR-001-primary-ui.md` | Django operator chrome; SPA `/` + `/chat` | **Y** | **keep** — addendum later: `/` is now Chat, not Dashboard; leftover-SPA sentence is stale |
| `docs/AUTH.md` | Bearer vs session, WS 4401, Explorer, sandbox | **Y** | **keep** |
| `docs/QUICKSTART.md` | Third install path (`pip install --user`, wizard) | **?** | **merge** into README + USERGUIDE |
| `docs/DEVELOPER_GUIDE.md` | 62-line stub (empty “Project Structure”) | **N** | **merge** (absorb DEVELOPMENT.md) or **delete** after rewrite |
| `docs/TODO.md` | Pointer to root ROADMAP / TODO | **Y** (inbound links) | **keep** as pointer |
| `docs/SWARM_CONFIG.md` | Pointer to `CONFIGURATION.md` | **Y** | **keep** as pointer |
| `docs/USER_JOURNEY.md` | Install → CLI → web → API story; 2026-08-19 captures | **Y** | **keep** — recapture after chrome honesty ([`tests-ci.md` D-01](./tests-ci.md)) |
| `docs/GUIDED_TOUR.md` | Screenshot-per-page tour; still describes Home · Chat top-nav | **Y** | **keep** — same recapture; conflicts with live Grok-Bot chrome |
| `docs/SCREENSHOTS.md` | Capture registry; locked by `tests/unit/test_screenshot_registry.py` | **Y** | **keep** — registry SoT for PNGs |
| `docs/DEPLOYMENT.md` | Generic CLI-wrapping server runbook | **Y** | **keep** |
| `docs/TROUBLESHOOTING.md` | Common CLI/API/config failures | **Y** | **keep** |
| `docs/EXAMPLES.md` | Copy-paste `model:` recipes | **Y** | **keep** — overlap with ORCHESTRATION_PATTERNS / CLI_FUSION |
| `docs/ORCHESTRATION_PATTERNS.md` | Mermaid sequence diagrams per `cli_*` | **Y** | **keep** — mechanics SoT |
| `docs/SWARM_WORKFLOWS.md` | MoA vs Persona (who may write) | **Y** | **keep** — conceptual SoT; pointer from MOA / GLOSSARY |
| `docs/MOA.md` | `swarm-cli moa` + Python API | **Y** | **keep** |
| `docs/CLI_FUSION.md` | Wrap installed CLIs; 469 lines | **Y** | **keep** — overlap with MOA / VISION / EXAMPLES |
| `docs/OPENWEBUI_MOA.md` | Client preset for `model: moa` | **?** | **merge** into MOA.md |
| `docs/BLUEPRINT_LIBRARY.md` | Permutation-matrix catalog of shipped blueprints | **Y** | **keep** |
| `docs/BLUEPRINT_SPLASH.md` | CLI splash from metadata | **?** | **merge** into blueprint_guide / DEVELOPER_GUIDE |
| `docs/blueprint_test_mode_ux.md` | `SWARM_TEST_MODE` spinner/box rules | **Y** (CONTRIBUTING) | **keep** |
| `docs/technical/blueprint_guide.md` | Live `BlueprintBase` / discovery / sandbox | **Y** | **keep** — technical SoT (beats DEVELOPMENT.md) |
| `docs/blueprints_api.md` | `/v1/blueprints` CRUD; stale XDG path `~/.config/OpenSwarm/` | **?** | **merge** into FEATURE_STATUS / AUTH or fix path |
| `docs/TOOLS.md` | Filesystem toolset + skills/MCP | **Y** | **keep** |
| `docs/framework_builtin_tools.md` | Older ToolRegistry catalog (Codey-centric) | **?** | **merge** into TOOLS.md |
| `docs/ASYNC_RESPONSES.md` | `/v1/responses` `background:true` | **Y** | **keep** |
| `docs/websocket_chat.md` | ASGI / Channels; still names `templates/chat.html` | **Y** | **keep** — honesty fix ([`django-spa-overlap.md` D-19](./django-spa-overlap.md)) |
| `docs/SESSION_EXPLORER.md` | `/sessions/` operator guide | **Y** | **keep** |
| `docs/REMOTE_HARNESSES.md` | Hermes / OMB / Rakazo; says Grok-Bot chrome **not** live | **Y** | **keep** — one-line honesty vs FEATURE_STATUS |
| `docs/HERDR.md` | `kind=herdr` (REQ-21) | **Y** | **keep** |
| `docs/TEAM_ISOLATION.md` | REQ-28 parent/child / CoS rules | **Y** | **keep** |
| `docs/SKILLS_AND_CONSENSUS_WALKTHROUGH.md` | Illustrated skills + 3-CLI consensus | **Y** | **keep** |
| `docs/github_marketplace.md` | GitHub-topics marketplace design | **?** | **archive** — FEATURE_STATUS says discovery ✅; marketplace CMS 🗑 |
| `docs/architecture_marketplace_to_mcp.md` | Marketplace → MCP flow (pre-CLI-fusion) | **N** | **archive** — already labeled historical in `docs/archive/README.md` |
| `docs/mcp_server_mode.md` | Honest: flag mounts `/mcp/`; blueprints are **not** tools | **Y** | **keep** |
| `docs/mcp_blueprints_adapter.md` | Aspirational “register blueprints as MCP tools” | **N** | **archive** or **merge** caveat into `mcp_server_mode.md` (contradicts it) |
| `docs/ORACLE_DEPLOY.md` | Public HTTPS + systemd on a CLI host | **?** | **leave** — do **not** enable Oracle ([`core.md` P2-1](./core.md)) |
| `docs/RUNBOOK_NEON_QUOTA_CRASH_LOOP.md` | Neon quota crash-loop | **?** | **leave** — do **not** enable Neon |
| `docs/COMFYUI_SETUP.md` | Avatar generation via ComfyUI | **?** | **keep** if avatars stay; else **archive** |
| `docs/BASELINE_REPORT.md` | Milestone 0 uv/README check, **2025-08-03** | **N** | **archive** |

### 1.3 `docs/requirements/` leftovers

Standing rule (also in `src/swarm/blueprints/software_dev/roles.py`): **Issues
are REQ SoT; do not invent a parallel `docs/requirements/` SoT.**

What is on disk today is **not** pointers. Each `REQ-*.md` is a full Intent /
Success / Constraints / Owner transcript. The index
(`docs/requirements/README.md`) still says most items are “PR N — in flight”
against starting tree `91dabd64`, hard-codes a guest live-preview host, and
omits REQ-22 / REQ-5 / REQ-95 / later REQs.

| Path | Role | Load-bearing | Proposed action |
|------|------|--------------|-----------------|
| `docs/requirements/README.md` | Backlog index + honesty table | **N** as SoT | **pointer-to-Issue** (index of Issue URLs only) or **archive** |
| `docs/requirements/REQ-7.md` … `REQ-37.md` (20 pages) | Full REQ transcripts | **N** as SoT | **pointer-to-Issue** each (`https://github.com/matthewhand/open-swarm/issues/<n>`) |
| Notable stale statuses | REQ-16 “PR 322 in flight” / “Grok chrome not on :8001 yet”; REQ-28 “this PR”; REQ-14 merged `4d554ea5` | **N** | Do not refresh bodies — **pointers** so Issues can move |

Issue numbers for the leftover pages were **not** all verified in this look-only
pass (several pages cite PR numbers, not Issue numbers). Implementer must map
REQ → Issue before rewriting.

### 1.4 `docs/debt/` (existing + this file)

| Path | Role | Load-bearing | Proposed action |
|------|------|--------------|-----------------|
| `docs/debt/core.md` | REQ-22c core/teams/blueprint audit | **Y** | **keep** — do not rewrite |
| `docs/debt/webui.md` | REQ-22a SPA audit | **Y** | **keep** — describes pre–Grok-Bot top-nav tree |
| `docs/debt/django-spa-overlap.md` | REQ-22b Django vs SPA | **Y** | **keep** |
| `docs/debt/tests-ci.md` | REQ-22d tests/CI | **Y** | **keep** |
| `docs/debt/qa-wave3-structure-docs.md` | This file (REQ-95 C) | **Y** | **keep** |
| *(expected siblings)* `qa-wave3-structure-{root,packages,deploy}.md` | Scopes A / B / D | — | **keep** when filed; do not merge scopes in one file |

### 1.5 `docs/archive/`, `docs/steering/`, proofs / demo / examples / screenshots

| Path | Role | Load-bearing | Proposed action |
|------|------|--------------|-----------------|
| `docs/archive/README.md` | Historical bin index | **Y** | **keep** |
| `docs/archive/FEATURE_STATUS_2026-06-10.md` | Point-in-time audit | **N** | **keep** (already archived) |
| `docs/archive/IMPLEMENTATION_SUMMARY.md` | 2026-06 FOSS-cleanup snapshot (title still says “MCP - Static Node.js WebUI”) | **N** | **keep** in archive |
| `docs/archive/2026-06-cleanup-commit-log.txt` | Raw commit log | **N** | **keep** in archive |
| `docs/steering/open-swarm-responses-fix.md` | One-line “Steering prompt…” | **N** | **delete** or **archive** |
| `docs/proofs/` | Live cross-CLI transcripts (2026-06-17) | **Y** | **keep** — evidence, not a guide |
| `docs/demo/cli-and-api.gif` + `docs/demo/captures/` | README GIF + raw scene dumps | **Y** (GIF) | **keep** GIF; captures **archive** if unused |
| `docs/examples/*.md` + `moa-*` walkthroughs | Worked examples + assets | **Y** | **keep** |
| `docs/examples/webui-config-panels.md` | Historical Builder panels (already labeled orphaned) | **N** | **archive** with `docs/screenshots/webui/` |
| `docs/screenshots/README.md` | Pointer to SCREENSHOTS.md | **Y** | **keep** |
| `docs/screenshots/*.png` + `mobile/` | Journey goldens (2026-08-19) | **Y** (registry + tests) | **keep** until recapture ([`tests-ci.md` D-01](./tests-ci.md)) |
| `docs/screenshots/webui/` | Deleted SPA Builder panels | **N** | **archive** |
| `docs/screenshots/archive/` | Older explorer / a11y shots | **N** | **keep** (already archived) |
| `docs/screenshots/skills/` | Skills walkthrough PNGs | **Y** | **keep** |

---

## 2. Duplicates / stale / conflicting guidance

Grouped by topic. “Canonical” is the file a later IA should point at.

### 2.1 Who is the status source of truth?

| File | Claim | Reality on this tree |
|------|-------|----------------------|
| GitHub Issues | REQ SoT (standing rule + software-dev CoS instructions) | **Intended** SoT. `#452` is this audit. |
| `docs/requirements/*` | Transcribed backlog; many “in flight” | Parallel SoT. Status lines disagree with FEATURE_STATUS / CHANGELOG (REQ-16 / REQ-19 / REQ-25 / REQ-37 described as shipped). |
| `ROADMAP.md` L10 | “single source of truth for project status”; last updated 2026-06-19 | Still says only `list`/`wizard`/`install` work cleanly (L53–54) — **false** vs README / USERGUIDE (`remotes`, `moa`, `skills`, `cli-agents`). |
| `FEATURE_STATUS.md` | Live evidence board (2026-08-18) | Closest honest **shipped** board. Not a REQ. |
| `TODO.md` | Fine-grained tasks; Docs section still asks to document XDG in USERGUIDE | USERGUIDE already has XDG + full command table. |
| `CONTRIBUTING.md` | “alpha-stage” | README: “Status: **beta**.” |

**Conflict:** three files claim status SoT (Issues, ROADMAP, FEATURE_STATUS).
`docs/requirements/` is a fourth, stale copy.

### 2.2 Getting started (four install stories)

| File | Install story |
|------|----------------|
| `README.md` | `git clone` + `uv sync --all-extras` + `swarm-cli list/launch` |
| `docs/QUICKSTART.md` | `pip install --user open-swarm` + `swarm-cli install codey` (compile) |
| `USERGUIDE.md` | Assumes already installed; CLI reference |
| `docs/USER_JOURNEY.md` | Fresh checkout + real transcripts + PNGs |

Not contradictory on purpose, but a newcomer hits four front doors. QUICKSTART
is the weakest (no `uv`, implies `install` downloads a package).

### 2.3 Developer / layout docs (stale tree)

`DEVELOPMENT.md` “Project Layout” still lists `setup.py` (**gone**),
`src/swarm/extensions/blueprint/` (**gone** — only `extensions/mcp/` remains),
`echocraft/` (**deleted husk** per FEATURE_STATUS), and
`swarm_config.json.example` (**not at repo root**). `docs/DEVELOPER_GUIDE.md`
is an unfinished outline that points at `SWARM_CONFIG.md` (now a pointer).
`docs/technical/blueprint_guide.md` is the only layout-accurate Blueprint
write-up.

### 2.4 Chrome honesty (largest user-facing conflict)

Live SPA (`webui/frontend/src/App.tsx`): Grok-Bot shell — left rail +
`ChatPage` at **`/` and `/chat`**. `Dashboard.tsx` is **not routed** (tests
only). FEATURE_STATUS §5 and CHANGELOG describe that chrome.

Still teaching the 2026-08-19 **catalog Home + six-link top-nav**:

- `docs/GUIDED_TOUR.md` / `docs/SCREENSHOTS.md` / `docs/USER_JOURNEY.md`
  (explicit “Home · Chat · Blueprints · Teams · Sessions · Settings”)
- `README.md` hero `docs/screenshots/landing.png` captioned as “the dashboard”
- `README.md` Web UI paragraph: “`/` prefers that React SPA **dashboard**”
- `docs/ADR-001-primary-ui.md` context: Teams/Blueprints SPA pages are
  “leftovers” (they were **deleted**); decision still says `/` is dashboard
- `docs/REMOTE_HARNESSES.md` L5: “Grok-Bot chrome is **not** claimed live”
- `docs/requirements/REQ-16.md`: “Grok chrome is **not on `:8001` yet**”

Existing debt files (`webui.md`, `django-spa-overlap.md`, `tests-ci.md`)
were written against the **top-nav** tree. They remain valid as historical
audits; do not “fix” them in place. A later chrome-docs PR should recapture
PNGs ([`tests-ci.md` D-01 / D-02](./tests-ci.md)) and update the tour trio +
README + ADR addendum.

### 2.5 Team / Blueprint vocabulary

`docs/GLOSSARY.md` is the honest map: **Team** = handoff members (REQ-11);
**Profiles** = `/v1/teams` aliases; **team roster** = `team_rosters.json`
(REQ-28). USERGUIDE and README mostly follow it.

Still Blueprint-as-composition (see [`core.md` P0-4](./core.md)):

- `docs/VISION.md` — patterns “exposed as **blueprints** (each is a `model` id)”
- `docs/ORCHESTRATION_PATTERNS.md` / `docs/EXAMPLES.md` — same
- `docs/QUICKSTART.md` — `wizard` “Create Your Own **Team**” scaffolds a Blueprint

`/v1/teams` vs `/v1/team-rosters` vs `/v1/agent-team/` remains a noun pile;
GLOSSARY is the resolver, not FEATURE_STATUS section titles.

### 2.6 MoA / Fusion / workflow cluster

Overlapping but not identical:

| File | Job |
|------|-----|
| `SWARM_WORKFLOWS.md` | Model A (MoA, read-only) vs Model B (Persona, write) |
| `MOA.md` | CLI + Python how-to |
| `CLI_FUSION.md` | Wrap host CLIs; GLOSSARY calls “fusion” a **legacy** name |
| `ORCHESTRATION_PATTERNS.md` | Per-blueprint sequence diagrams |
| `EXAMPLES.md` | curl recipes (`cli_*` names, `swarm_*` aliases) |
| `OPENWEBUI_MOA.md` | Client preset (subset of MOA.md) |
| `docs/examples/moa-*` | Captured runs |

Keep the cluster; collapse only OPENWEBUI_MOA into MOA. Do not rewrite
CLI_FUSION in this wave.

### 2.7 MCP / marketplace

- `mcp_server_mode.md` — honest: mount only; `register_blueprints_with_mcp` is a no-op on `mcp_server` ≥0.5.
- `mcp_blueprints_adapter.md` — still describes registering blueprints as tools.
- `architecture_marketplace_to_mcp.md` — archive-worthy (archive README already says so).
- `github_marketplace.md` — design doc; GitHub-topics discovery shipped, Wagtail CMS removed.

### 2.8 Tools cluster

`TOOLS.md` (filesystem toolset + skills/MCP) vs
`framework_builtin_tools.md` (older `ToolRegistry` / Codey list). Merge later.

### 2.9 Oracle / Neon

`ORACLE_DEPLOY.md` and `RUNBOOK_NEON_QUOTA_CRASH_LOOP.md` are operator
memory. [`core.md` P2-1](./core.md): no callers in core/blueprints; **do not
enable**. Scope C does not recommend deleting them.

### 2.10 Screenshot / Builder fossils

Already scored in [`tests-ci.md`](./tests-ci.md) (goldens vs captions) and
`docs/examples/webui-config-panels.md` (self-labeled historical).
`docs/screenshots/webui/*` are Builder museum PNGs.

---

## 3. Proposed docs IA (later implementer)

Target shape after CoS picks resolutions. **Do not execute in this PR.**

```
README.md                    front door (install + link map only)
USERGUIDE.md                 swarm-cli reference
CONTRIBUTING.md              how to PR
CONFIGURATION.md             config + env
FEATURE_STATUS.md            shipped evidence (not REQ)
ROADMAP.md                   future work only (no “SoT for status”)
CHANGELOG.md                 releases
TODO.md                      optional short pointer → ROADMAP / Issues

docs/
  GLOSSARY.md                nouns
  ADR-*.md                   decisions
  AUTH.md                    trust model
  VISION.md                  north star
  GUIDED_TOUR.md             UI tour (after recapture)
  USER_JOURNEY.md            E2E story (after recapture)
  SCREENSHOTS.md             PNG registry
  DEVELOPER_GUIDE.md         replace DEVELOPMENT.md + stub
  technical/                 BlueprintBase, test-mode UX
  MOA.md + CLI_FUSION.md + ORCHESTRATION_PATTERNS.md + SWARM_WORKFLOWS.md
  REMOTE_HARNESSES.md + HERDR.md + TEAM_ISOLATION.md
  DEPLOYMENT.md + TROUBLESHOOTING.md
  examples/  proofs/  screenshots/  demo/
  debt/                      audits only (this convention)
  archive/                   historical
  requirements/              POINTER FILES ONLY (or delete the dir)
```

### 3.1 Keep (canonical)

README, USERGUIDE, CONTRIBUTING, CONFIGURATION, FEATURE_STATUS, CHANGELOG,
GLOSSARY, ADR-001, AUTH, VISION, SCREENSHOTS, GUIDED_TOUR, USER_JOURNEY,
DEPLOYMENT, TROUBLESHOOTING, MOA, CLI_FUSION, ORCHESTRATION_PATTERNS,
SWARM_WORKFLOWS, BLUEPRINT_LIBRARY, technical/blueprint_guide,
blueprint_test_mode_ux, TOOLS, ASYNC_RESPONSES, websocket_chat,
SESSION_EXPLORER, REMOTE_HARNESSES, HERDR, TEAM_ISOLATION,
SKILLS_AND_CONSENSUS_WALKTHROUGH, mcp_server_mode, EXAMPLES,
docs/TODO.md (pointer), docs/SWARM_CONFIG.md (pointer), docs/debt/*,
docs/archive/*, docs/proofs/*, docs/examples/ (except Builder log),
docs/screenshots/ journey + skills PNGs.

### 3.2 Merge

| Loser | Into |
|-------|------|
| `docs/QUICKSTART.md` | README (uv path) + USERGUIDE (wizard / XDG) |
| `DEVELOPMENT.md` + stub `docs/DEVELOPER_GUIDE.md` | one `docs/DEVELOPER_GUIDE.md`; root file becomes a pointer |
| `docs/OPENWEBUI_MOA.md` | `docs/MOA.md` |
| `docs/framework_builtin_tools.md` | `docs/TOOLS.md` |
| `docs/BLUEPRINT_SPLASH.md` | `docs/technical/blueprint_guide.md` |
| `docs/blueprints_api.md` | FEATURE_STATUS API rows + AUTH (fix XDG path) |
| `docs/mcp_blueprints_adapter.md` | short “not shipped” note in `mcp_server_mode.md` |
| Root `TODO.md` leftover bullets | ROADMAP or Issues |

### 3.3 Pointer-to-Issue

Every `docs/requirements/REQ-*.md` and the index: one heading + link to the
GitHub Issue. No Intent/Success copy. If a REQ has no Issue yet, file one
or omit the page — do not keep a transcript.

### 3.4 Archive

`docs/BASELINE_REPORT.md`, `docs/architecture_marketplace_to_mcp.md`,
`docs/github_marketplace.md` (if not rewritten as a short “topics discovery”
page), `docs/examples/webui-config-panels.md` + `docs/screenshots/webui/`,
`docs/steering/` if anything else lands there.

### 3.5 Delete (after link retarget)

`docs/steering/open-swarm-responses-fix.md` (49 bytes). Stub
`docs/DEVELOPER_GUIDE.md` only after the merge rewrite exists.

### 3.6 Leave (do not enable)

`docs/ORACLE_DEPLOY.md`, `docs/RUNBOOK_NEON_QUOTA_CRASH_LOOP.md`.

---

## 4. How new `docs/debt/` files should be named

Existing names are a mix:

| Pattern | Examples | When |
|---------|----------|------|
| Short area slug | `core.md`, `webui.md`, `tests-ci.md` | REQ-22 area audits (already shipped — do not rename) |
| Collision slug | `django-spa-overlap.md` | Same |
| Wave + scope | `qa-wave3-structure-docs.md` (this file) | REQ-95 look-only wave |

**Going forward (additive; never overwrite):**

```
docs/debt/<kind>-<wave-or-req>-<scope>.md
```

1. **Look-only structure / hygiene waves:**
   `qa-wave<N>-structure-<scope>.md`
   — scopes already reserved: `root` (A), `packages` (B), `docs` (C),
   `deploy` (D). One file per scope. No `qa-wave3-structure.md` catch-all.
2. **Feature / area debt audits (REQ-22 style):**
   `<area>.md` or `<area>-<facet>.md` (kebab-case, no spaces).
   Quote the REQ at the top. Do not reuse `core.md` / `webui.md` /
   `tests-ci.md` / `django-spa-overlap.md`.
3. **Follow-ups that only add findings:** new file
   `qa-wave<N>-<topic>.md` or `req-<N>-<slug>.md`.
   Append a one-line “see also” in the older file **only** if CoS asks;
   default is **do not edit** prior debt files.
4. **Forbidden:** rewriting an existing debt file “to bring it current,”
   putting secrets, host IPs as if they were public SoT, or `Fixes #<req>`
   on a look-only docs PR.

---

## Do not do yet

CoS reviews this file (and sibling Scope A/B/D reports) before any
reorganisation Issue is filed. Until then:

1. **No file moves, mass-deletes, or IA execution.** Smash / squash is
   Matthew’s agy; these docs PRs are not that priority.
2. **Do not rewrite** `docs/debt/core.md`, `webui.md`, `tests-ci.md`,
   `django-spa-overlap.md`.
3. **Do not convert `docs/requirements/` in the same PR as a feature.**
   Pointer pass is its own implementer Issue after CoS maps REQ → Issue.
4. **Do not recapture screenshots** here. That is [`tests-ci.md` D-01](./tests-ci.md)
   plus `scripts/capture_user_journey.py` — it will fail the caption lockfile
   until FEATURE_STATUS / GUIDED_TOUR / SCREENSHOTS move together.
5. **Do not enable Oracle or Neon.** Do not treat those runbooks as a
   deploy invitation.
6. **Do not remount** deleted SPA Builder / Teams / Settings pages to “make
   the tour PNGs true.” ADR-001 still stands; chrome moved *toward* Grok-Bot,
   not back to a catalog Home.
7. **Do not fan implementers** off `#452` until Matthew picks resolutions.
   DaisyUI product chrome is out of this wave.

---

## Method / out of scope

- Static read of every `docs/**/*.md` title + root guides listed in REQ-95.
- Cross-check against live `webui/frontend/src/App.tsx` (chrome),
  `src/swarm/extensions/` (only `mcp/` remains), and standing Issue-SoT
  comment in `software_dev/roles.py`.
- Did **not** open `:8001`, Neon, or Oracle. Did **not** dump `.env`.
- Did **not** inventory Scope A root `*.patch` / Pinokio / `assets/` (Scope A)
  or Django vs SPA packages (Scope B) or Docker/CI (Scope D), except where
  a doc file’s honesty depends on them.
