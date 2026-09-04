# Wave 2 QA — leftover core.md P0 (Teams vs Blueprint)

Look-only re-read of leftover [core.md](./core.md) **P0** items against
**today’s tree**. No app, SPA, Django, tests, CI, or golden-journey files
were changed. Existing `docs/debt/*.md` files were not edited.

**As-of:** `origin/main` @ `dfd72eef` (includes Grok-Bot chrome #322,
REQ-36 software-dev team #357 / Issue #348, REQ-28 rosters + CoS #345,
REQ-37 compact, Pinokio #375, ASGI SPA buffer #428). Prior core audit
([PR 327](https://github.com/matthewhand/open-swarm/pull/327)) was frozen
at `91dabd64`.

**Method:** static re-read of `src/swarm/core/{swarm_cli,team_rosters,agent_roles,blueprint_discovery,remotes}.py`,
`src/swarm/views/{teams_api,team_rosters_api}.py`,
`src/swarm/blueprints/{dynamic_team,software_dev,hybrid_*,cli_*,moa_*}/`,
`docs/{GLOSSARY,VISION,DEVELOPER_GUIDE,ORCHESTRATION_PATTERNS,TEAM_ISOLATION}.md`,
`README.md`, `FEATURE_STATUS.md`, `CHANGELOG.md`. GitHub: Issues #348 /
#382 / #420; PRs 357 (merged), 404 (open), 429 (open wave1). No Neon.
No secrets. No live LAN / Fly URLs. No `:8001`. No second cloud.

**How to read the ranks**

| Rank | Meaning here |
|------|----------------|
| **must-fix** | An operator or new contributor still lands on the wrong noun (alias vs roster vs Blueprint `model` id). Still true today. |
| **nice** | Docs inventory gap, chrome teaching, or role-metadata mismatch. Real, not a wrong-store lie. |
| **obsolete** | Prior P0 claim is no longer the whole truth after REQ-28 / GLOSSARY honesty / software-dev. |
| **intentional** | Split that must stay (alias API ≠ roster API; Blueprint as Python recipe). |
| **new** | Collision that did not exist (or was not named) at the `91dabd64` audit. |

Prior P0 ids `P0-1`…`P0-4` are mapped as `C-01`…`C-04`. New collisions
continue the `C-` series. Wave1 sibling (Django/SPA chrome) is [PR 429](https://github.com/matthewhand/open-swarm/pull/429)
`docs/debt/qa-wave1-django-spa.md` — **not on `main`**; this file uses that
PR body + the fetched branch file. Do not edit wave1.

**Assumptions this pass does *not* make**

| Item | Today |
|------|--------|
| Agent-editor picker (Issue [#382](https://github.com/matthewhand/open-swarm/issues/382)) | **Not on `main`.** Implementation is open [PR 404](https://github.com/matthewhand/open-swarm/pull/404). `main` still has REQ-25 hover-edit → Settings **Blueprint Python** (`SettingsSheet.tsx` `BlueprintEditorPane`). |
| Blueprint role metadata (Issue [#420](https://github.com/matthewhand/open-swarm/issues/420)) | **Unmerged.** No PR. `agent_roles.py` is rail/roster roles only. Do not treat `metadata.role` as a shipped apply-on-create contract. |
| Wave1 file | Open PR 429 only. “Team is four products” is taken from that note. |

---

## Snapshot vs the leftover P0 notes

| Leftover (`core.md` @ `91dabd64`) | Today (`dfd72eef`) |
|-----------------------------------|--------------------|
| `/v1/teams` + `DynamicTeamBlueprint` = profile alias, not composition | **Still true.** Honesty docstring still says alias. Composition now also exists **beside** it (`team_rosters.json`, `/v1/team-rosters/`). |
| “Team” means three things (alias / MoA `--team` / future composition) | **Worse.** Wave1 Q-01: **four** products (alias / launcher / Swarm Creator / **rosters**). Core also still has REQ-11 `agent_team` in `swarm_config.json`. |
| CLI is Blueprint-only; no `teams` command | **Still true.** `remotes place\|unplace` talks to `agent_team`, not rosters. Zero `swarm-cli` roster/teams command. `wizard` still “Scaffold a new team blueprint.” |
| Multi-agent composition = Blueprint `model` ids | **Still true, plus one.** `software_dev` (REQ-36 / #348) is another as-tool team shipped as a discoverable blueprint id. It does **not** write `team_rosters.json`. |
| GLOSSARY: “For multi-agent workflows, use a **Blueprint**.” | **Quote gone.** GLOSSARY now splits Team (handoff) / Profiles (`/teams/`) / Team roster. VISION / README / ORCHESTRATION / DEVELOPER_GUIDE still teach Blueprint-as-composition. |
| No composition store | **Obsolete as a vacuum.** Rosters shipped (REQ-28). The P0 is now *naming + CLI + recipe-as-id*, not “composition does not exist.” |

---

## Ranked index

| ID | Rank | Sev | Status | One-line |
|----|------|-----|--------|----------|
| C-01 (P0-1) | must-fix | P0 | still-true (worse) | `/v1/teams` is still the alias; composition is a *different* object |
| C-02 (P0-2) | must-fix | P0 | still-true | CLI composition is still Blueprint `launch` / `wizard`; no roster command |
| C-03 (P0-3) | must-fix | P0 | still-true (worse) | Hybrid / MoA / `cli_*` **and** `software_dev` are still `model` ids |
| C-04 (P0-4) | must-fix | P0 | still-true (split) | Front-door docs still teach Blueprint-as-team; GLOSSARY is only half-fixed |
| C-05 | must-fix | P0 | new | `software_dev` is a Team-shaped workflow that is not a roster |
| C-06 | must-fix | P1 | new | Two composition stores: `agent_team` vs `team_rosters` |
| C-07 | nice | P1 | new | Hover-edit on `main` opens Settings Python, not a picker ( #382 unmerged ) |
| C-08 | nice | P1 | new | `software_dev` stamps `role=engineer`; canonical roles have no `engineer` (#420 unmerged) |
| C-09 | nice | P1 | still-true | `wizard --role` still unused; help still says “team blueprint” (was P1-9) |
| C-10 | nice | P2 | new | FEATURE_STATUS / README table / CHANGELOG omit `software_dev` |
| C-11 | nice | P2 | still-true | GLOSSARY SPA line still says `/` is dashboard (wave1 Q-20 sibling) |
| O-01 | obsolete | — | obsolete | “GLOSSARY defines Team as the `teams.json` alias only” |
| O-02 | obsolete | — | obsolete | “No Teams composition object exists in the tree” |
| I-01 | intentional | — | keep | `/v1/teams` aliases ≠ `/v1/team-rosters` composition (wave1 I-01) |
| I-02 | intentional | — | keep | Do **not** grow `DynamicTeamBlueprint` into a graph |
| I-03 | intentional | — | keep | Blueprint stays a Python recipe / OpenAI `model` id |
| I-04 | intentional | — | keep | `swarm-cli remotes` + `/v1/agent-team/` for Hermes/OMB/Rakazo placement |
| I-05 | intentional | — | keep | #420 role-on-blueprint apply-on-create is **not** shipped |

---

## Must-fix

### C-01 — `/v1/teams` + `DynamicTeamBlueprint` is still a profile alias (P0-1, worse)

| | |
|--|--|
| **Rank / sev** | must-fix / P0 |
| **Status** | **still-true**, worse after REQ-28 + wave1 “four products” |
| **Paths** | `src/swarm/blueprints/dynamic_team/blueprint_dynamic_team.py`, `src/swarm/views/teams_api.py`, `src/swarm/views/utils.py` (`teams.json`), `src/swarm/core/team_rosters.py`, `src/swarm/views/team_rosters_api.py`, Django `/teams/` + `/teams/launch/` + `/team-creator/` |
| **Why** | `DynamicTeamBlueprint.run()` is still a thin `AsyncOpenAI` Chat Completions proxy to one `llm_profile`. `teams_api.py` honesty: a “team” here is `id` + `description` + `llm_profile` — “not a multi-agent Team.” That object was never a foundation for composition, and it still is not. What changed: REQ-28 shipped the composition store **beside** it (`team_rosters.json`, `/v1/team-rosters/`). Wave1 Q-01: the chrome word “Team” now covers **alias / launcher / Swarm Creator / rosters**. Core adds a fifth sibling store (`agent_team` — see C-06). Expanding the alias stub would still be wrong. |
| **Later-ticket action** | **wrap** — keep the alias registry; stop calling it a Team in new API/CLI/docs. Do **not** grow `DynamicTeamBlueprint`. Real composition stays on rosters (I-01). Wave1 Q-02 / Q-05 (hrefs that hop roster chrome to `/teams/`) are the UI twin; not this file. |

### C-02 — CLI still treats Blueprint as the composition layer (P0-2)

| | |
|--|--|
| **Rank / sev** | must-fix / P0 |
| **Status** | **still-true** |
| **Paths** | `src/swarm/core/swarm_cli.py` (`launch`, `list`, `wizard`, `install`, `moa`, `cli-agents`, `remotes`); `README.md` CLI paragraph; `docs/DEVELOPER_GUIDE.md` |
| **Why** | Shipped commands are still blueprint lifecycle (`list` / `launch` / `install` / `wizard` / `add` / `delete`) plus `moa` (third meaning of “team”) and `cli-agents`. There is **no** `teams` or `rosters` Typer command. `remotes place\|unplace` persists `agent_team.members` in `swarm_config.json` (REQ-11 handoff Team), not `team_rosters.json`. `wizard_cmd` help: “Scaffold a new team blueprint.” `launch` is still PyInstaller / blueprint-executable only. API + rail can share a roster; CLI cannot. |
| **Later-ticket action** | **wrap** — add a roster CLI that reads/writes the same `team_rosters.json` the API and rail use. Demote `launch` to “run a Blueprint recipe.” Keep `moa` as a strategy, not a third product. Keep `remotes` for harness placement (I-04). **delete** the unused `wizard --role` stub in the same later pulse (C-09), or wrap wizard to emit a roster entry. |

### C-03 — Multi-agent composition is still a pile of Blueprint `model` ids (P0-3)

| | |
|--|--|
| **Rank / sev** | must-fix / P0 |
| **Status** | **still-true**, worse (`software_dev` added) |
| **Paths** | `src/swarm/blueprints/hybrid_team/`, `hybrid_swarm/`, `hybrid_moa/`, `moa_orchestrator/`, `persona_council/`, `cli_{agent,map,orchestrator,pipeline,planner,recurse,roundtable}/`, aliases `cli_fusion` / `cli_ensemble`, **plus** `src/swarm/blueprints/software_dev/` |
| **Why** | Same family as the leftover audit: REST + CLI adapters + consensus / specialists, consumed as OpenAI `model:` ids on `/v1/chat/completions`. Discovery still registers `swarm_*` aliases (`blueprint_discovery.py` `BLUEPRINT_ALIASES`). `pyproject.toml` scripts are still `swarm-cli` / `swarm-api` / `codey` / `suggestion` — no Teams binary. REQ-36 then shipped the software-dev **team** the same way (C-05). Team Launcher still picks blueprint ids. |
| **Later-ticket action** | **wrap** — keep implementations as recipes / strategies; expose one Teams (roster) surface for API + CLI + remote. Do **not** add more `cli_*` / `hybrid_*` / `swarm_*` ids. Do **not** delete `software_dev` (it is a valid recipe). Deprecate extra model ids rather than growing the pile. |

### C-04 — Front-door docs still teach Blueprint-as-composition (P0-4, split)

| | |
|--|--|
| **Rank / sev** | must-fix / P0 |
| **Status** | **still-true** for README / VISION / ORCHESTRATION / DEVELOPER_GUIDE; GLOSSARY honesty **changed** (O-01) |
| **Paths** | `README.md` (L7–14, L112 “Blueprint = team or strategy”, L151–153), `docs/VISION.md` (L33–44, mermaid L141), `docs/ORCHESTRATION_PATTERNS.md` (L3–18), `docs/DEVELOPER_GUIDE.md` (L37–44), `docs/GLOSSARY.md`, `src/swarm/views/teams_api.py` (OpenAPI text) |
| **Why** | Leftover quote “For multi-agent workflows, use a **Blueprint**” is **gone** from GLOSSARY (O-01). GLOSSARY now names Profiles vs Team vs Team roster. The front door did not follow: README still opens “Agent teams are defined as **Blueprints**”; VISION still “compose … *teams* … exposed as **blueprints** (each is a `model` id)”; ORCHESTRATION_PATTERNS still “each multi-agent orchestration pattern as a **blueprint**”; DEVELOPER_GUIDE CLI surface is still `list` / `install` / `launch` blueprints. Until those change, a contributor will still add another blueprint id (C-03 / C-05). |
| **Later-ticket action** | **wrap** — later docs-only PR (not this audit). Align README / VISION / ORCHESTRATION / DEVELOPER_GUIDE: Team roster = composition (API+CLI+remote); Blueprint = Python recipe / `model` id; `/v1/teams` = legacy **Profiles**. Keep `teams_api.py` honesty as a **legacy** caveat until the alias registry is renamed. |

### C-05 — `software_dev` is a Team-shaped workflow that is not a roster (new)

| | |
|--|--|
| **Rank / sev** | must-fix / P0 |
| **Status** | **new** after Issue #348 / PR 357 |
| **Paths** | `src/swarm/blueprints/software_dev/blueprint_software_dev.py`, `src/swarm/blueprints/software_dev/roles.py`, `src/swarm/blueprints/README.md` (only inventory that lists it), `tests/blueprints/test_software_dev.py` |
| **Why** | REQ-36 asked for “one custom team/blueprint” (CoS / engineer / skeptic, openai-agents `as_tool` + handoff). That landed as `SoftwareDevBlueprint` with `metadata.aliases` `software-dev` / `software_dev_team` and `metadata.agents[].role` stamps. It is composition. It is **not** a `team_rosters` row, not an `/v1/teams` alias, and not `agent_team`. Talk-to is the CoS seat inside the recipe. This is the leftover P0-3 pattern applied to the one team the product just invested in. FEATURE_STATUS / README bundled table / CHANGELOG Unreleased do not mention it (C-10). |
| **Later-ticket action** | **wrap** — keep the recipe; optionally *project* its three seats onto a roster so rail / CLI / isolation see the same Team. **leave** the Python as-tool wiring. Do not clone it into extra Grok seats. Do not assume #420 will stamp these roles on create. |

### C-06 — Two composition stores: `agent_team` vs `team_rosters` (new)

| | |
|--|--|
| **Rank / sev** | must-fix / P1 |
| **Status** | **new** as a named leftover (both stores existed by REQ-28; CLI only talks to one) |
| **Paths** | `src/swarm/core/remotes.py` (`agent_team.members`, `persist_agent_team`), `src/swarm/views/remotes_api.py` (`/v1/agent-team/`), `src/swarm/core/team_rosters.py`, `src/swarm/views/team_rosters_api.py`, `docs/GLOSSARY.md` (Team vs Team roster), `docs/TEAM_ISOLATION.md` |
| **Why** | GLOSSARY **Team** (REQ-11) is remotes placed via `swarm-cli remotes place` / `PATCH /v1/agent-team/` into `swarm_config.json`. GLOSSARY **Team roster** (REQ-28) is `team_rosters.json` with `kind: api\|cli\|remote\|team\|herdr`. `team_rosters.py` comments that member *shape* is shared; the files are not. CLI has a Team command for the older store only. Isolation / CoS consult tools attach to rosters. An operator can “place” Hermes in a Team and never appear on the rail roster. |
| **Later-ticket action** | **wrap** — one composition object the API, CLI, and remotes write. Until then **leave** both stores (do not merge in a drive-by). Document `agent_team` as “remote placement,” not a second Team product. Wave1 I-02 (CLI vs API vs remote vs herdr *members*) stays intentional; this finding is the *store* split. |

---

## Nice

### C-07 — Hover-edit on `main` opens Settings Blueprint Python (#382 unmerged)

| | |
|--|--|
| **Rank / sev** | nice / P1 |
| **Status** | **new** relative to the leftover P0s; **do not treat the picker as shipped** |
| **Paths** | `webui/frontend/src/components/AgentSidebar.tsx` (`openSettingsSheet({ section: 'blueprint', blueprintId })`), `webui/frontend/src/components/SettingsSheet.tsx` (`BlueprintEditorPane`), `webui/frontend/src/lib/agentRoles.ts` (`showsBlueprintEdit` = support/gate/skeptic only), FEATURE_STATUS “Role hover-edit → Blueprint settings (REQ-25)” |
| **Why** | Issue #382 wants an agent-scoped editor whose Blueprint control is a **selector** of existing recipes. That PR (404) is open. On today’s `main`, pencil → Settings sheet **Python** for that id, with Remotes / Retention / Hostname / LLM still in the same sheet nav. That teaches “edit agent = edit Blueprint source,” which is the leftover P0-4 story in chrome. If 404 lands later, Blueprint-as-**picker** actually matches I-03 (recipe assigned to a seat) and does **not** by itself fix C-01…C-05. |
| **Later-ticket action** | **leave** on this audit. Do not fold #382 / #420 into a core P0 ticket. Re-rank after 404 merges. |

### C-08 — `software_dev` `role=engineer` is not a canonical role (#420 unmerged)

| | |
|--|--|
| **Rank / sev** | nice / P1 |
| **Status** | **new**; **do not assume #420 landed** |
| **Paths** | `src/swarm/blueprints/software_dev/blueprint_software_dev.py` `metadata.agents` (`chief_of_staff` / `engineer` / `skeptic`), `src/swarm/blueprints/software_dev/roles.py` `seat_tool_policy` (`role: "engineer"`), `src/swarm/core/agent_roles.py` `CANONICAL_ROLES` / `ROLE_ALIASES` (default, support, gate, skeptic, chief_of_staff — **no engineer**), `webui/frontend/src/lib/agentRoles.ts` (same set) |
| **Why** | `normalize_agent_role("engineer")` → `default`. Roster validation rejects unknown roles (`team_rosters.normalize_member`). A later “put software_dev seats on a roster” wrap would drop engineer to default unless #420 (or a roster-role add) lands first. #420’s success (“blueprint declares default role; create assigns it”) is **not** true today. |
| **Later-ticket action** | **leave** until #420 or an explicit roster-role ticket. Do not invent `engineer` in chrome here. |

### C-09 — `wizard` is still labeled “team” and emits a dead Blueprint (was P1-9)

| | |
|--|--|
| **Rank / sev** | nice / P1 |
| **Status** | **still-true** (same code) |
| **Paths** | `src/swarm/core/swarm_cli.py` `wizard_cmd` (~L1216–1247) |
| **Why** | `--role` still builds `agents_code` that is **never written**. Output is `yield "Team {name} ready."`. It does not write `teams.json`, `team_rosters.json`, or `software_dev`-style as-tool seats. Help still says “team blueprint.” Same leftover; more misleading now that rosters exist. |
| **Later-ticket action** | **delete** the stub generator, or **wrap** it to emit a roster / recipe template. Same later CLI ticket as C-02. |

### C-10 — Inventory docs omit `software_dev`

| | |
|--|--|
| **Rank / sev** | nice / P2 |
| **Status** | **new** |
| **Paths** | `FEATURE_STATUS.md` (no REQ-36 / `software_dev` row), `README.md` bundled-blueprint tables (still lists removed `whinge_surf`; no `software_dev`), `CHANGELOG.md` Unreleased (REQ-28 / REQ-37 / Pinokio present; REQ-36 absent), `docs/technical/blueprint_guide.md` (zeus only). Counter-example: `src/swarm/blueprints/README.md` **does** list it. |
| **Why** | Contributors using FEATURE_STATUS / README will not find the new team recipe. Not a wrong-store lie; inventory drift after #357. |
| **Later-ticket action** | **wrap** in the same later docs PR as C-04. Do not treat CHANGELOG silence as “the blueprint is unofficial.” |

### C-11 — GLOSSARY still says SPA `/` is dashboard

| | |
|--|--|
| **Rank / sev** | nice / P2 |
| **Status** | **still-true** (wave1 Q-20 sibling; in scope because P0-4 named GLOSSARY) |
| **Paths** | `docs/GLOSSARY.md` “Operator UI vs SPA Chat” table |
| **Why** | Line still: “React SPA retains `/` (dashboard) and `/chat`.” After Grok chrome, `/` and `/chat` both mount Chat. The leftover P0-4 GLOSSARY work started; this stale IA line was not part of that honesty pass. |
| **Later-ticket action** | **wrap** with C-04. Wave1 already filed the same line; one docs PR can fix both. |

---

## Obsolete (prior P0 claim no longer the whole truth)

### O-01 — “GLOSSARY defines Team as the `teams.json` alias only”

Leftover P0-4 evidence quoted GLOSSARY as “Team = `teams.json` LLM-profile alias … For multi-agent workflows, use a **Blueprint**.” That sentence is **gone**. Today GLOSSARY has **Team (handoff members — REQ-11)**, **Profiles (`/teams/` — name collision)**, and **Team roster (composition) / Chief of Staff**. Honesty exists. The remaining lie is the *other* front-door docs (C-04) and the chrome word (wave1 Q-01), not a missing glossary split.

**Later-ticket action:** **leave** the three GLOSSARY headings. Do not revert them to “Team = alias.”

### O-02 — “No Teams composition object exists”

Leftover product lens treated composition as future. REQ-28 shipped `team_rosters.json` + `/v1/team-rosters/` + isolation + CoS. The leftover P0 is no longer “build the object.” It is “stop calling four other objects Team, and put CLI/docs on the one that is composition.”

**Later-ticket action:** **leave** the roster store. Do not invent a third composition JSON.

---

## Intentional (must stay)

### I-01 — `/v1/teams` ≠ `/v1/team-rosters`

Same keep as wave1 I-01. Alias registry (`teams.json`, `DynamicTeamBlueprint`, Django `/teams/` admin) is a **profile** product. Roster registry is composition. Collapsing them would re-expand the stub `core.md` warned against.

**Action:** **leave** both endpoints. Rename in copy / OpenAPI only (C-01 wrap).

### I-02 — Do not grow `DynamicTeamBlueprint`

Leftover action is still correct. The class is a chat proxy. Graph / as-tool / isolation do not belong here.

**Action:** **leave** the implementation. **wrap** the name.

### I-03 — Blueprint stays a Python recipe / `model` id

REQ-22c direction is unchanged: Teams (rosters) own composition for API+CLI+remote; Blueprint is the recipe you can POST as `model`. `software_dev` as a *recipe* is allowed (C-05 wrap, not delete). #382’s picker (if it lands) assigns that recipe to a seat — still I-03, not a Teams replacement.

**Action:** **leave** discovery + `/v1/blueprints/` + `/v1/models`. Stop teaching recipe = Team (C-04).

### I-04 — `swarm-cli remotes` / `/v1/agent-team/` for harness placement

Hermes / OMB / Rakazo placement is a real CLI/API. It is not a roster editor. Deleting it to “have one Team command” would break REQ-11.

**Action:** **leave** remotes. **wrap** later so place/unplace can also add `kind=remote` on a named roster (C-06).

### I-05 — #420 is not a product fact

Issue #420 (blueprint default `role` / workflow hint, apply-on-create) is open and unmerged. `agent_roles.py` is the rail/roster contract only. Tests and docs must not pretend picker-create assigns `gate` from blueprint metadata.

**Action:** **leave**. Re-rank C-08 after that issue ships.

---

## Duplicate-path map (today, P0 slice only)

```
stores named "Team"
  teams.json            → /v1/teams/ + Django /teams/     → DynamicTeamBlueprint (alias)
  team_rosters.json     → /v1/team-rosters/ + rail ?team= → composition + isolation
  swarm_config.json     → agent_team.members              → remotes place / /v1/agent-team/
  launcher / creator    → /teams/launch/ , /team-creator/ → run or write a Blueprint (wave1)

recipes named "team" (API model ids)
  hybrid_team / hybrid_swarm / hybrid_moa / moa_orchestrator
  persona_council / cli_* / cli_fusion / cli_ensemble
  software_dev          → CoS/engineer/skeptic as_tool     (new; not a roster)

CLI
  swarm-cli launch / wizard / list / install   (blueprint)
  swarm-cli moa [--team|--act]                 (third "team")
  swarm-cli remotes place|unplace|team         (agent_team only)
  (no swarm-cli rosters / teams)
```

---

## What this audit does **not** recommend

- Product code, SPA/Django chrome, tests, CI, or golden-journey edits (wave1 owns chrome hrefs).
- Rebasing, squashing, or folding into PRs 404 / 420 / 429 / 357 follow-ups.
- Enabling Oracle or Neon. No dead callers were re-opened in this pass.
- Growing `DynamicTeamBlueprint` into a graph, or deleting `software_dev`.
- Assuming the agent-editor picker (#382 / PR 404) or role metadata (#420) shipped.
- Touching `:8001` or any live host.

---

## Suggested later ticket (not this PR)

One **docs + naming** wrap, then one **CLI roster** wrap. Do not start a composition rewrite.

1. **Docs honesty (C-04, C-10, C-11, O-01 leave):** README / VISION / ORCHESTRATION / DEVELOPER_GUIDE / FEATURE_STATUS / CHANGELOG / GLOSSARY SPA line. Team roster = composition; `/v1/teams` = Profiles; Blueprint = recipe. Add `software_dev` to inventories.
2. **CLI roster surface (C-02, C-06, C-09):** `swarm-cli` list/get/upsert against `team_rosters.json`. Demote `wizard` (delete stub or emit a roster). Keep `remotes` (I-04).
3. **Recipe wrap, not delete (C-03, C-05, C-08):** keep `software_dev` / `hybrid_*` / `cli_*` as recipes; optional roster projection for software-dev seats **after** #420 or an explicit `engineer` role decision.

Wave1 must-fix Q-01 / Q-02 / Q-05 (chrome word + hrefs) is the UI twin of C-01. Same later naming pulse; different files. Do not implement either in this PR.
