# QA wave 2 — leftover core P1 MoA / consensus / unsafe loops (look-only)

> **Look-only.** This file re-reads the **P1** slice of
> [`docs/debt/core.md`](core.md) (REQ-22c, merged as #327) against **today’s**
> `main`. It does not rewrite product code, edit existing debt docs, rebase
> other PRs, or file new Issues. No product diffs live in the PR that added
> this file.

**As-of:** `origin/main` @ `dfd72eef`
(`fix(webui): buffer SPA HTML/assets on ASGI so Daphne does not hang (#428)`).

**Starting audit:** [`docs/debt/core.md`](core.md) scored the tree at
`91dabd64` (REQ-22c / #327). Later `main` landings that touch this slice:
software-dev as-tool (#357 / REQ-36), remotes + `remote_harness` (#318),
CoS / teams-of-teams (#345 / REQ-28), nested Compact (#365 / REQ-37).
Those add **new** unbounded `Runner.run` sites and a third specialist roster.
They do **not** collapse the P1 engines.

**Method:** static re-read of `src/swarm/core/{consensus,persona_swarm,cli_*,blueprint_base,blueprint_discovery,swarm_cli}.py`,
`src/swarm/core/moa/**`, and the hybrid / cli / gawd / django_chat /
software_dev / remote_harness blueprint packages. No host bounce. No `:8001`.
No Neon. No secrets. No live LAN URLs.

**Out of scope (wave2 core-P0 Teams audit).** Do **not** re-file or re-argue
[`core.md`](core.md) **P0-1…P0-4** here: `/v1/teams` as a profile alias,
CLI-has-no-Teams-command, multi-agent composition registered as Blueprint
`model` ids, docs/API honesty that still teach Blueprint-as-composition.
This file is engines, loops, stubs, and discovery schema only.

**How to read**

| Rank | Meaning here |
|------|----------------|
| **still-true** | The leftover is still in today’s tree, same shape as #327. |
| **obsolete** | No longer true: shipped, deleted, or the cited caller/path is gone. |
| **intentional** | Still present, but the *product split* is deliberate (keep the policy; wrap the stacks). |
| **new** | Appeared on `main` after `91dabd64` and is the same *kind* of P1 (dupe engine / unsafe loop / schema drift). |

| Severity | Meaning here |
|----------|----------------|
| **must-fix** | Unsafe loop or import-time side effect that can hang / re-enter / boot Django on discovery. |
| **nice** | Real duplication or husk. Safe to leave until a dedicated cleanup ticket. |

Action vocabulary is unchanged from [`core.md`](core.md): **leave** / **wrap** /
**delete** — for a **later** ticket, not this PR.

---

## Today’s engine snapshot (what #327 described vs what shipped)

| Cluster | #327 tree (`91dabd64`) | Today (`dfd72eef`) |
|---------|------------------------|--------------------|
| Consensus | `run_consensus` vs `MoAOrchestrator.default_synthesize` | **Same two engines.** `persona_council` no longer calls `run_consensus` (own judge). |
| Orchestrator name | `moa/orchestrator.py` + facade `agents_orchestrator.py` | **Same.** Facade still wraps `run_moa_then_team`. |
| `swarm-cli moa` | `--team` / `--act` / default = three runners | **Still three `asyncio.run` entrypoints.** Default + `--team` now share `team_result_to_payload`. |
| Specialists | `persona_swarm` vs `moa.team` | **Same two**, plus **new** `software_dev` CoS/engineer/skeptic as-tool roster. |
| grok argv | catalog `--always-approve` vs MoA `--disallowed-tools` | **Same opposite policies.** |
| hybrid loops | ThreadPool + nested `asyncio.run`, no `max_turns` | **Unchanged.** |
| `Runner.run` | unbounded on API blueprints; only `persona_swarm` caps at 4 | **Worse:** `software_dev` + `remote_harness` added two more uncapped sites. |
| `django_chat` | `django.setup()` at import | **Unchanged.** |
| `gawd` | deprecated comment, still discovered | **Unchanged.** No `metadata.deprecated`. |
| Metadata | no `category`; zeus `get_metadata()` unused | **Same**, plus `software_dev` extra keys the TypedDict does not list. |

Nothing in this slice enables Oracle deploy or Neon.

---

## Ranked index (P1 leftovers + new)

| # | Orig | Status | Sev | Finding | Later action |
|---|------|--------|-----|---------|--------------|
| 1 | P1-1 | still-true | nice | Dual consensus engines | wrap |
| 2 | P1-2 | still-true | nice | Dual “orchestrator” modules; agents one is a facade | wrap |
| 3 | P1-3 | still-true (narrowed) | nice | Triple `swarm-cli moa` backends | wrap |
| 4 | P1-4 | still-true + intentional split | nice | `persona_swarm` vs `moa.team` | wrap |
| 5 | P1-5 | intentional policy + still-true stacks | nice | catalog grok vs MoA grok argv | wrap |
| 6 | P1-6 | still-true | **must-fix** | `hybrid_team` ThreadPool + nested `asyncio.run` | wrap |
| 7 | P1-7 | still-true | nice | `hybrid_team` ≈ `hybrid_swarm` | wrap |
| 8 | P1-8 | still-true + intentional aliases | nice | Nine `cli_*` + two MoA alias packages | wrap |
| 9 | P1-9 | still-true | nice | `wizard` stub; `--role` never written | delete stub / wrap later |
| 10 | P1-10 | still-true | nice | `BlueprintBase` god module | wrap |
| 11 | P1-11 | still-true (**worse**) | **must-fix** | `Runner.run` without `max_turns` | wrap |
| 12 | P1-12 | still-true | **must-fix** | `django_chat` `django.setup()` at import | wrap |
| 13 | P1-13 | still-true | nice | Deprecated `gawd` still a model id | delete |
| 14 | P1-14 | still-true (**worse**) | nice | Metadata / discovery schema drift | wrap |
| 15 | — | **new** | **must-fix** | `software_dev` + `remote_harness` uncapped `Runner.run` | wrap |
| 16 | — | **new** | nice | Third specialist roster (`software_dev` as-tool) | wrap |
| 17 | P1-1 caller | **obsolete** | — | `persona_council` “uses `run_consensus`” | leave (own judge) |

---

## Must-fix (still true)

### M1 — `hybrid_team` farms async `Runner.run` through threads + nested loops

| Field | Value |
|-------|--------|
| **Rank / sev** | still-true / must-fix (was [`core.md`](core.md) P1-6) |
| **Still-true?** | **Yes.** Same `_execute_delegations` / `_run_delegation` shape. |
| **Path** | `src/swarm/blueprints/hybrid_team/blueprint_hybrid_team.py` (`_execute_delegations`, `_run_delegation`, `_rest_reason`, `_synthesize`) |
| **Why** | Outer `run()` is already async. Delegations go to a `ThreadPoolExecutor`; each worker does `asyncio.run(asyncio.wait_for(self._run_delegation(...)))`, and `_run_delegation` calls `Runner.run` with **no `max_turns`**. New event loop per sub-task; rate-limit `time.sleep` holds a thread. Same nested-loop pattern still lives in `persona_swarm._consult_moa_sync` and `moa/agents_orchestrator._consult_configured` (`ThreadPoolExecutor` + `asyncio.run` when a loop is running). `persona_council` / `cli_map` already use `asyncio.gather` + a semaphore. |
| **Later PRs** | None on `main` touched this file after #327. |
| **Later ticket** | **wrap** — native `asyncio.gather` + semaphore; cap `max_turns`. Do not add more thread-pool Runner hops. **Not this PR.** |

### M2 — Unbounded openai-agents loops on the API path (worse after #318 / #357)

| Field | Value |
|-------|--------|
| **Rank / sev** | still-true + new sites / must-fix (was P1-11) |
| **Still-true?** | **Yes — worse.** `grep max_turns src/swarm/blueprints` is still **zero**. |
| **Path** | Uncapped `Runner.run(...)` today in `hybrid_team` (×3), `hybrid_swarm`, `geese`, `jeeves`, `codey`, `chatbot`, `suggestion`, `gawd`, `zeus`, `whiskeytango_foxtrot`, `stewie`, **plus new** `software_dev` and `remote_harness`. Only core `persona_swarm.run_persona_swarm_with_runner` passes `max_turns=4`. |
| **Why** | Tool-using agents can loop until the gateway times out. `/v1/chat/completions` has no per-blueprint turn cap. `zeus` / `whiskeytango_foxtrot` / `stewie` still treat `Runner.run` as a **sync generator** (`for chunk in Runner.run` / `while True` over the gen) — a second, older SDK shape. New `software_dev` and `remote_harness` fall back to a status/health string on exception, but the live path is still uncapped. |
| **Later PRs** | #357 and #318 **added** sites. They did not add a shared cap. |
| **Later ticket** | **wrap** — default `max_turns` on `BlueprintBase.make_agent` / a shared `run_agent` helper. Fix zeus/WTF/stewie to `await Runner.run`. **Not this PR.** |

### M3 — `django_chat` calls `django.setup()` at import

| Field | Value |
|-------|--------|
| **Rank / sev** | still-true / must-fix (was P1-12) |
| **Still-true?** | **Yes.** |
| **Path** | `src/swarm/blueprints/django_chat/blueprint_django_chat.py` (module top: `DJANGO_SETTINGS_MODULE` + `django.setup()`); pulled in by `discover_blueprints` from `views/utils.py`, `library_api.py`, `core_views.py`, `blueprint_library_views.py`, `web_views.py`, `teams_api.py`. |
| **Why** | Docstring still says “HTTP-only; not intended for CLI use.” The package is **not** in `INSTALLED_APPS` (only a logger name in `settings.py`). API discovery `exec_module`s every blueprint dir, so listing models/library **re-enters** Django setup from inside a recipe. `swarm-cli list` itself only walks directories (does **not** import) — the original “CLI list boots Django” line is slightly overstated; the API/discovery path is the real one. `__main__` still `sys.exit(1)`. |
| **Later ticket** | **wrap** — move views/urls/templates out of `blueprints/`; drop from default discovery or keep a thin recipe that does not `django.setup()`. **Not this PR.** |

---

## Nice (still true, not an unsafe loop)

### N1 — Two consensus engines (`run_consensus` vs `MoAOrchestrator`)

| Field | Value |
|-------|--------|
| **Rank / sev** | still-true / nice (was P1-1) |
| **Still-true?** | **Yes** for the two engines. One cited caller moved (see O1). |
| **Path** | `src/swarm/core/consensus.py` (`run_consensus`, `most_corroborated`, `_tokens`); `src/swarm/core/moa/orchestrator.py` (`default_synthesize`, its own `_tokens`, structured `parse_proposal` / `score_proposals`) |
| **Why** | Same product idea (panel → corroborate → one answer), two policies. CLI-fusion family (`hybrid_team`, `hybrid_swarm`, `cli_agent`, `cli_orchestrator`, `cli_tools.consensus_fn`) uses the first. `moa` / `hybrid_moa` / `swarm-cli moa` use the second. Duplicate `re.findall(r"[a-z0-9]+", …)` tokenizers. Operators can get different “consensus” for the same prompt depending on model id. |
| **Later ticket** | **wrap** — one synthesizer; CLI-fusion and MoA become backends. Do not blend the read-only MoA policy into write-mode fusion. |

### N2 — Two modules named “orchestrator”; the agents one is a facade

| Field | Value |
|-------|--------|
| **Rank / sev** | still-true / nice (was P1-2) |
| **Still-true?** | **Yes.** |
| **Path** | `src/swarm/core/moa/orchestrator.py` (`MoAOrchestrator`); `src/swarm/core/moa/agents_orchestrator.py` (`run_moa_agents_orchestrator`); consumer `src/swarm/blueprints/moa_orchestrator/blueprint_moa_orchestrator.py` |
| **Why** | The agents module docstring still says it is **not** a live openai-agents `Runner` path; it wraps `run_moa_then_team` and returns a name roster (`SCRIPTED_ORCHESTRATOR_ROSTER`). `build_moa_orchestrator_agents` exists for optional live Agents and is unused by the default dogfood path. Naming still implies a third SDK. |
| **Later ticket** | **wrap** — merge the facade into `moa/team.py` or rename it to a team runner. Reserve “orchestrator” for a later Teams layer (P0 owns that rename; this ticket only folds the facade). |

### N3 — Triple `swarm-cli moa` internals (serialization narrowed, runners not)

| Field | Value |
|-------|--------|
| **Rank / sev** | still-true (narrowed) / nice (was P1-3) |
| **Still-true?** | **Yes** for three `asyncio.run` entrypoints. Payload shape is closer than #327 claimed. |
| **Path** | `src/swarm/core/swarm_cli.py` `moa` (`--team` → `run_moa_then_team`; `--act` → `run_moa_cli`; default → `run_moa_consensus`) |
| **Why** | Product modes (`consensus_only` / `consensus_then_act` / `consensus_then_team`) are a **deliberate** CLI. The leftover is three Python runners plus two serializers. Default and `--team` now share `team_result_to_payload`. `run_moa_cli` stamps `mode` / `specialists` / `panel_wrote` for parity, but `--act` still constructs `MoAOrchestrator` directly instead of going through `moa.team`. Soft `--team` failure still prints then exits 1 (that UX is fine; not debt). |
| **Later ticket** | **wrap** — one `run_moa(mode=…)` used by CLI and API. Keep the three flags. |

### N4 — `persona_swarm` vs `moa.team` — two specialist runners

| Field | Value |
|-------|--------|
| **Rank / sev** | still-true + intentional workflow split / nice (was P1-4) |
| **Still-true?** | **Yes.** Documented as Model B vs consensus-then-team in `docs/SWARM_WORKFLOWS.md`. |
| **Path** | `src/swarm/core/persona_swarm.py`; `src/swarm/core/moa/team.py`; callers `hybrid_moa` (`run_hybrid_scripted`) and `moa_orchestrator` (`run_moa_then_team`) |
| **Why** | Both script researcher/implementer-style writes on `WorkspaceTools` (`team.py` imports that class and `PersonaResult` from `persona_swarm`). `run_persona_swarm_with_runner` is still the only core `Runner.run` (`max_turns=4`) and **falls back silently** to the scripted swarm. The workflow split is intentional; the leftover is two schedulers + a silent live-path fallback. A **new** third roster sits beside them (N-new-2). |
| **Later ticket** | **wrap** — one post-consensus specialist scheduler. Persona module keeps optional live Runner + `consult_moa` tool only. Do not re-argue Teams-vs-Blueprint here. |

### N5 — Two grok CLIs: catalog write vs MoA read-only

| Field | Value |
|-------|--------|
| **Rank / sev** | intentional policy + still-true stacks / nice (was P1-5) |
| **Still-true?** | **Yes.** Do **not** “fix” by enabling write on MoA panelists. |
| **Path** | `src/swarm/core/cli_catalog.py` `CATALOG["grok"]`; `src/swarm/core/cli_adapter.py`; `src/swarm/core/moa/backends.py` `GrokParticipantBackend.build_command` |
| **Why** | Fusion catalog: `grok -p … --output-format json --always-approve` (`mode: "write"`). MoA backend: `grok -p … --disallowed-tools Write,Edit,… --max-turns 4 --no-subagents --no-plan` (`--output-format plain`). Same binary, opposite policy — **intentional**. `swarm-cli moa --backend grok` still bypasses `CliAdapterRegistry`; `swarm-cli cli-agents` still bypasses MoA backends. Two subprocess stacks for one CLI is the leftover. |
| **Later ticket** | **wrap** — `ParticipantBackend` on top of `CliAdapter` + catalog, with a readonly override. Leave the deny-write MoA flags. |

### N6 — `hybrid_team` and `hybrid_swarm` share one pipeline

| Field | Value |
|-------|--------|
| **Rank / sev** | still-true / nice (was P1-7) |
| **Still-true?** | **Yes.** |
| **Path** | `src/swarm/blueprints/hybrid_team/blueprint_hybrid_team.py` (504 lines); `src/swarm/blueprints/hybrid_swarm/blueprint_hybrid_swarm.py` (184 lines) |
| **Why** | Both: REST plan → grok CLI persona → `run_consensus` / `consensus_fn` → concatenate. Team adds Claude-orchestrated delegations (the unsafe loop in M1) + optional auxiliary synthesis. Swarm stops at step 4. Two discoverable model ids for one hybrid recipe. Both still fall back to the `cli_fusion` preset. |
| **Later ticket** | **wrap** — one recipe, `params.mode=team\|swarm`, or one shared helper. Do not add a third `hybrid_*` id. |

### N7 — Nine `cli_*` strategy packages + two MoA aliases + `swarm_*` aliases

| Field | Value |
|-------|--------|
| **Rank / sev** | still-true + intentional back-compat aliases / nice (was P1-8) |
| **Still-true?** | **Yes.** ROADMAP §4.5 still open. |
| **Path** | `src/swarm/blueprints/cli_{agent,map,orchestrator,pipeline,planner,recurse,roundtable}/`; alias packages `cli_fusion/` (31 lines) and `cli_ensemble/` (24 lines) — both `MoABlueprint` subclasses; `src/swarm/core/blueprint_discovery.py` `BLUEPRINT_ALIASES` (`swarm_ensemble` → `cli_fusion`, plus six `swarm_*` → `cli_*`) |
| **Why** | The seven strategy packages all import `blueprints.common.cli_fusion_support` and differ by orchestration template. `cli_fusion` / `cli_ensemble` are **intentional** legacy model ids (API tests lock `model: "cli_fusion"`). ROADMAP §4.5: “consider one blueprint + `strategy` param.” |
| **Later ticket** | **wrap** — collapse aliases into discovery metadata; one strategy enum later. Keep packages as thin recipes until then. Do not add more `cli_*` / `swarm_*` ids. |

### N8 — `wizard` is labeled “team” and emits a dead Blueprint

| Field | Value |
|-------|--------|
| **Rank / sev** | still-true / nice (was P1-9) |
| **Still-true?** | **Yes.** |
| **Path** | `src/swarm/core/swarm_cli.py` `wizard_cmd` |
| **Why** | Help: “Scaffold a new team blueprint.” `--role` builds `agents_code` (`Agent(name=…)`) that is **never written**. Output is an inert `BlueprintBase.run` that yields `"Team {name} ready."` It does not write `teams.json`, MoA tasks, or a composition object. (P0 owns what “team” should mean; this leftover is the stub generator.) |
| **Later ticket** | **delete** the stub generator, or **wrap** it to emit a real template once a composition object exists. **Not this PR.** |

### N9 — `BlueprintBase` is still a god module

| Field | Value |
|-------|--------|
| **Rank / sev** | still-true / nice (was P1-10) |
| **Still-true?** | **Yes.** 921 lines (ROADMAP §4.5 still says 919 / 35 methods). |
| **Path** | `src/swarm/core/blueprint_base.py` |
| **Why** | Import-time `configure_openai_client_from_env()` + `set_tracing_disabled`; Django `apps` import; LLM profile resolution; memory wrap; `make_agent`; inline `Spinner`; interactive `request_approval` / `execute_tool_with_approval` (`input()` — **no callers** outside this file); session logger; CLI `print_help`. Stale header comment still names `src/swarm/extensions/blueprint/blueprint_base.py`. ROADMAP §4.5 still asks for `MemoryMixin` / `ApprovalMixin` / `ConfigResolver`. |
| **Later ticket** | **wrap** — thin recipe base; lazy client; no stdin approval on the API path. Approval helpers are **delete**-candidates (unused). |

### N10 — Deprecated `gawd` is still a `/v1/models` id

| Field | Value |
|-------|--------|
| **Rank / sev** | still-true / nice (was P1-13) |
| **Still-true?** | **Yes.** |
| **Path** | `src/swarm/blueprints/gawd/blueprint_gawd.py` (line 1: “DEPRECATED: superseded by Zeus”); `gawd/__init__.py`; `gawd/apps.py`; locked in `tests/blueprints/test_discoverable_gap_test_mode.py` `GAP_BLUEPRINTS` and library-view fixtures |
| **Why** | Still discovered. No `metadata["deprecated"] = True` (discovery supports the field but **never skips** it — comment says “future: skip”). Only consumer of `common/progress.py` and `common/output_formatters.py`. Duplicates zeus UX (`ProgressRenderer`, uncapped `Runner.run`). FEATURE_STATUS still lists it as discoverable. |
| **Later ticket** | **delete** (with gap-test row + gawd-only formatters), or mark `deprecated: true` and actually exclude from prod lists. Do not migrate new work here. |

### N11 — Discovery metadata is inconsistent and Blueprint-only

| Field | Value |
|-------|--------|
| **Rank / sev** | still-true (worse) / nice (was P1-14) |
| **Still-true?** | **Yes.** ROADMAP §4.5 still open. |
| **Path** | `src/swarm/core/blueprint_discovery.py` (`BlueprintMetadata` TypedDict); worst offenders `gawd` (no `metadata` dict), `geese` (no `metadata` dict), `zeus` (`get_metadata()` that discovery **does not call**); `chucks_angels` display name `"Chuck's Angels"` vs dir key (slug check now skips it as a model id — good); zero blueprints set `category`. Comment still mentions deleted `audit_status.json` (file **absent**). |
| **Why** | `software_dev` added `aliases`, `agents`, `gate_agent`, `skeptic_agent` — discovery copies `aliases` ad hoc; the TypedDict does not list those keys. `deprecated` / `status` are extracted and then ignored. Library grouping and slug checks cannot work without a schema + CI validator. |
| **Later ticket** | **wrap** — schema + CI validator. Do not add more `swarm_*` aliases. (A `discover_teams()` belongs to the P0 composition ticket, not this one.) |

---

## New leftovers (after `91dabd64`, same P1 kind)

### N-new-1 — `software_dev` and `remote_harness` are new uncapped Runner sites

| Field | Value |
|-------|--------|
| **Rank / sev** | new / must-fix (extends M2 / P1-11) |
| **Path** | `src/swarm/blueprints/software_dev/blueprint_software_dev.py` (`await Runner.run(coordinator, text)`); `src/swarm/blueprints/remote_harness/blueprint_remote_harness.py` (same) |
| **Why** | #357 and #318 shipped deterministic grammar fallbacks (good) and a live coordinator path with **no `max_turns`**. Same API hang risk as the older recipe family. Count these with M2; do not open a second “add max_turns” ticket. |
| **Later ticket** | **wrap** with M2. |

### N-new-2 — Third specialist roster (as-tool CoS / engineer / skeptic)

| Field | Value |
|-------|--------|
| **Rank / sev** | new / nice (extends N4 / P1-4) |
| **Path** | `src/swarm/blueprints/software_dev/blueprint_software_dev.py`; `src/swarm/blueprints/software_dev/roles.py` |
| **Why** | Scripted seats + optional `Runner` on a coordinator that `as_tool()`s engineer/skeptic. Parallel to `persona_swarm.build_persona_agents` (coordinator / researcher / implementer) and `moa.team` (`implementer` / `tester` / `docs` / `researcher`). This is a **duplicate specialist engine**, not a Teams-honesty finding — leave P0 composition to that audit. |
| **Later ticket** | **wrap** with N4 (one specialist scheduler). **leave** the deterministic grammar (`quote` / `implement` / `review`) as a recipe. |

---

## Obsolete / narrowed (do not re-state as if #327 were frozen)

### O1 — `persona_council` no longer calls `run_consensus`

| Field | Value |
|-------|--------|
| **Rank / sev** | obsolete (caller claim only) |
| **Path** | `src/swarm/blueprints/persona_council/blueprint_persona_council.py` |
| **Why** | #327 P1-1 listed `persona_council` as a `run_consensus` consumer. Today it fans out lenses with `asyncio.gather` + `CliAdapter.run`, then runs its **own** `JUDGE_TEMPLATE` on the judge adapter. That is a **third** panel synthesizer, not a `consensus.py` caller. The dual-engine leftover (N1) still stands; this caller line does not. |
| **Later ticket** | **leave** the council recipe. If a wrap ticket unifies synthesizers, fold this judge into the same helper. |

### O2 — `swarm-cli moa` JSON shape is no longer “three different serializers”

| Field | Value |
|-------|--------|
| **Rank / sev** | obsolete as stated; leftover is the three runners (N3) |
| **Why** | `team_result_to_payload` and `run_moa_cli` now share `determination` / `opinions` / `mode` / `specialists` / `panel_wrote` keys. The original “serialize slightly differently” sentence is stale. Three `asyncio.run` hops remain. |

### O3 — `swarm-cli list` does not import `django_chat`

| Field | Value |
|-------|--------|
| **Rank / sev** | obsolete as stated; leftover is API discovery (M3) |
| **Why** | `list_blueprints` walks package dirs for an entry file. It does not call `discover_blueprints`. The import-time `django.setup()` fires when API/library/views discover, and when tests import the module. |

---

## Later-ticket actions (not this PR)

| ID | Action | Do | Do not |
|----|--------|----|--------|
| M1 | wrap | `asyncio.gather` + semaphore in `hybrid_team`; cap turns | Add another thread-pool Runner hop |
| M2 / N-new-1 | wrap | Shared `max_turns` default; `await Runner.run` on zeus/WTF/stewie | Per-blueprint one-off caps that drift |
| M3 | wrap | Thin recipe or drop from default discovery | Keep `django.setup()` in a discoverable package |
| N1 | wrap | One synthesizer, two backends | Blend MoA read-only with fusion write |
| N2 | wrap | Fold `agents_orchestrator` into `moa.team` | Add a third module named orchestrator |
| N3 | wrap | One `run_moa(mode=…)` | Remove `--team` / `--act` product flags |
| N4 / N-new-2 | wrap | One specialist scheduler | Re-file as Teams composition honesty |
| N5 | wrap | Backend on `CliAdapter` + readonly override | `--always-approve` on MoA panelists |
| N6 | wrap | One hybrid recipe + mode | New `hybrid_*` model id |
| N7 | wrap | Discovery aliases + strategy enum later | New `cli_*` / `swarm_*` packages |
| N8 | delete or wrap | Delete stub, or emit a real template later | Teach `wizard` as a Teams builder in this slice |
| N9 | wrap | Split mixins; delete unused approval | Rewrite all blueprints in one PR |
| N10 | delete | Remove package + gap-test row + gawd-only formatters | Migrate features into gawd |
| N11 | wrap | Schema + CI validator | More `swarm_*` aliases |
| O1 | leave | Council recipe as-is until synthesizer wrap | Claim it still uses `run_consensus` |

---

## Do not re-file

- **P0-1…P0-4** composition honesty — wave2 core-P0 Teams audit. This file does not repeat them.
- Open product REQs (software-dev, remotes, CoS, Compact) are **not** this cleanup. #357 / #318 / #345 / #365 shipped features; they left the P1 loops in place.
- ROADMAP §4.5 already lists god-module / metadata / nine `cli_*`. Do not open a parallel “structure” Issue that restates that section.
- No Neon. No Oracle. No live host. No `:8001`.
- Do not fold this into a product PR. Do not squash. Do not rebase other PRs.

---

## What this audit does **not** recommend implementing here

- Collapsing packages, deleting `gawd`, moving `django_chat`, or adding `max_turns`.
- Turning `DynamicTeamBlueprint` into a graph (P0).
- Enabling write on MoA panelists.
- Adding more `cli_*` / `hybrid_*` / `swarm_*` model ids.
