# REQ-171 surface B — Left rail / agents / favourites / hidden / blueprints-as-agents

Look-only audit for [#596](https://github.com/matthewhand/open-swarm/issues/596) (REQ-171) surface **B**, coordinating [#595](https://github.com/matthewhand/open-swarm/issues/595) (REQ-170: stop listing blueprints as agents; redundant name/blueprint pairing).

**As-of:** `origin/main` @ `f21d24ea` (CLI/API dropdowns #593). No SPA, Django, tests, or CI files were changed in this PR.

**Method:** Static read of Grok `AgentSidebar.tsx`, Search, Add-agent wizard, agent editor/edits, rail order / pins / hide helpers, `/v1/blueprints/` + discovery + custom library, leftover Django `agent_sidebar.js`, Agent Router sidebar + zustand store, and the tests that lock current behaviour. GitHub: #595, #596, #419; open PRs #576–#579, #582, #597.

**Live confirm (folded 2026-09-04):** Engineer look-only on `:8001` — [comment on #595](https://github.com/matthewhand/open-swarm/issues/595#issuecomment-5537343790). Agrees with this report: rail = filesystem catalog, not Django Agent rows. **No Neon. No secrets.** This cloud did not re-hit `:8001`; numbers below are that sample.

**How to read the ranks**

| Rank | Meaning here |
|------|----------------|
| **HIGH** | Wrong noun on the rail (recipe listed as a chat seat), crash, or create-agent that never becomes a seat. Blocks #595 success. |
| **MEDIUM** | Real rail/Search/wizard/hide/pin logic defect or tests that encode the wrong contract. |
| **LOW** | Naming leftovers, duplicate describes, source-scan “contract” tests. |
| **intentional** | Split that must stay (blueprint catalog API ≠ rail seats; CLI verify rows). |

Action vocabulary (for a **later** ticket, not this PR): **filter** / **cleanup** / **seat-store** / **leave**.

Do not fight [#579](https://github.com/matthewhand/open-swarm/pull/579) (persist favourites/hidden) or [#597](https://github.com/matthewhand/open-swarm/pull/597) (wizard manage + folder) unless CoS treats a finding as critical. #419 (`django_chat` catalog id) stays a filter/delete later, not this audit.

---

## Verdict

There is **no** seed table of “one agent row per blueprint.” The Grok left rail **is** `GET /v1/blueprints/` plus three injected role seats, host CLI verify rows, team rosters, remotes, and Herdr members. Chat identity is `?blueprint=<catalog-id>`. The editor then defaults **Name** and **Blueprint** to that same id. That is why `:8001` looks like “every recipe is an agent, and the name equals the blueprint.”

**`:8001` engineer sample (2026-09-04)** — [comment](https://github.com/matthewhand/open-swarm/issues/595#issuecomment-5537343790):

| Fact | Live |
|------|------|
| `GET /v1/blueprints/` | **~54** `object=blueprint` rows |
| Django `marketplace_blueprint` count | **0** |
| Name === id | **39 / 54** |
| `exampleRoleAgents` | injects/sorts support/gate/skeptic only; **does not hide demos** |
| Demos on the rail | `poets`, `chucks_angels`, `django_chat`, MoA aliases, etc. |
| Seed script → Django Agent | **None.** Discovery *is* the seed. |

**Recommended later path: FILTER (rail allowlist or discovery metadata flag). Do not archive Django seed agents (there are none). Do not delete recipe packages.** See [Implement Issue — concrete Success](#implement-issue--concrete-success-595).

---

## Root cause (#595) — why recipes appear as Agent rows

### 1. Catalog API is discovery, not seats

`BlueprintsListView` (`src/swarm/views/api_views.py`) lists `get_available_blueprints()`:

- `discover_blueprints(BLUEPRINT_DIRECTORY)` — every `blueprint_*.py` under `src/swarm/blueprints/` (**37** shipped packages on this tip: `django_chat`, `software_dev`, `codey`, `poets`, `chucks_angels`, `cli_*`, MoA/hybrid family, …).
- `merge_community_blueprints` — extra / user dirs.
- Metadata `aliases` (e.g. `moa` → `mixture_of_agents`, `cli_fusion`; `software_dev` → `software-dev`) **plus** `BLUEPRINT_ALIASES` (`swarm_ensemble` → `cli_fusion`, …). That is why live `:8001` lists **~54** API rows from 37 packages.
- **`teams.json` dynamic-team aliases** merged as `DynamicTeamBlueprint` with `metadata.name = team_id` (name === id by construction).

`GET /v1/blueprints/` already emits `"installed": null` / `"compiled": null` placeholders — not a rail flag. Django `marketplace_blueprint` is unused on `:8001` (count **0**).

Each row is `{ object: "blueprint", id, name, … }` where `name = meta.get("name", blueprint_id)`. Most recipes set `"name": "<same-as-id>"` (e.g. `codey`, `gate`, `support`, `cli_fusion`). Display names that differ (`Chuck's Angels`) are the exception.

Custom library JSON (`POST /v1/blueprints/custom/` → `blueprint_library.json`) is a **different** store. It is **not** merged into `GET /v1/blueprints/`.

### 2. Grok rail treats that list as agents

`webui/frontend/src/components/AgentSidebar.tsx` (mounted from `App.tsx` on `/` and `/chat`):

```text
fetchBlueprints() → catalog
exampleRoleAgents(catalog)  // injects support/gate/skeptic, KEEPS every recipe
  + CoS from team rosters
  + Herdr members (object still "blueprint")
  + CLI rail from /v1/cli-agents/
→ RailRow kind "agent" → /chat?blueprint=<id>
```

`exampleRoleAgents` is a **misnomer**. It does not filter to example roles. It calls `ensureExampleRoleAgents` (unshift Support / push Safety / Skeptic if missing) then `sortExampleRolesFirst`. Tests lock this in: `exampleRoleAgents([codey])` must equal `['support', 'gate', 'skeptic', 'codey']`.

`SidebarAgent` is typed as `Blueprint & { kind?, remote?, cli? }`. CLI/Herdr adapters set `object: 'blueprint'`.

First-load hide seeds `gate` / `tool_gate` / `skeptic` (`hiddenAgents.ts`). That only *hides* two role recipes. It does **not** hide `codey`, `stewie`, `software_dev`, `django_chat`, `cli_fusion`, …

First-load favourite seeds `{ id: 'support', name: 'Support' }`.

### 3. Search is the same catalog

`SearchPalette.tsx` fetches `/v1/blueprints/`, runs `exampleRoleAgents`, maps every row to tab **Bots** with `href: /chat?blueprint=<id>`. Tests require Codey on Bots and navigation to `?blueprint=codey`.

### 4. Chat + editor identity is the catalog id

- `ChatPage` resolves the selected seat from `exampleRoleAgents(blueprints)` and `assignedBlueprintId(selectedBlueprint)` (defaults to the URL id).
- `agentEdits.ts`: “Chat identity stays the agent id (`?blueprint=<agentId>`). The assigned blueprint is what the websocket / run uses.” Self-assignment is deleted: if `blueprintId === agentId`, the field is omitted. So a catalog row is both seat and recipe.
- `AgentEditor.tsx` hydrates `setName(edit.name || catalogAgent?.name || id)` and `setBlueprintId(edit.blueprintId || id)`. For `codey`, both controls show **codey**. That is the “stupid pairing,” not a stray seed clone.

### 5. Leftover Django rail does the same

`src/swarm/static/js/agent_sidebar.js` `fetch("/v1/blueprints/")` then `agents = blueprints.concat(herdrAgents)` and `href = /chat?blueprint=`. Same noun collision if operator HTML is still hit.

### 6. Agent Router is a second, different rail

`/agents` uses `AgentSidebar/AgentSidebar.tsx` + `useAgentStore` + `GET /v1/agents/` (`agent_router` blueprint members) + `mergeStarters` / `hideAllExceptStarters`. Persistence keys are `agent_hidden_ids` / `agent_favourite_ids`, **not** `swarm_hidden_agents` / `swarm_pinned_agents`. Out of Grok-chrome success for #595, but dual stores will confuse #579 and testers.

### 7. What `:8001` shows (engineer live, not inferred)

Confirmed on the host sample and in [#595 comment](https://github.com/matthewhand/open-swarm/issues/595#issuecomment-5537343790):

- Rail lists the **filesystem** catalog via `GET /v1/blueprints/` (~54 rows). **Not** Django Agent / `marketplace_blueprint` rows (count **0**).
- Chat is `?blueprint=<id>`. Display name is `metadata.name`; **39/54** have `name == id`.
- `exampleRoleAgents` only special-cases support / gate / skeptic (inject + sort + hide-seed gate/skeptic). **Demos all show:** `poets`, `chucks_angels`, `django_chat`, MoA / `swarm_*` aliases, and the rest of the pack.
- Archiving “seed agents” in Django does **nothing**. Deleting blueprint packages would break `?blueprint=` chat / `/v1/models`.

`swarm_hidden_agents` only seeds gate+skeptic and is per-browser (later #540 / #579 prefs). It is not a catalog filter.

---

## Cleanup vs filter (CoS decision)

Live `:8001` closed this: **there is nothing to archive in Django.** `marketplace_blueprint` = 0. No Agent-per-blueprint rows. Discovery *is* the seed.

| Option | What it does | Use? |
|--------|----------------|------|
| **Filter (required)** | Rail + Search Bots list **seats only**. Catalog stays on `GET /v1/blueprints/` + Settings / Blueprints sheet. | **Yes.** Code filter and/or discovery metadata flag. |
| **DB archive of seed agents** | Delete/hide Django Agent / marketplace rows. | **No.** Count is already 0. Does nothing on `:8001`. |
| **Delete recipe packages** | Remove `poets`, `django_chat`, MoA, … from disk. | **No.** Breaks `?blueprint=` and `/v1/models`. #419 may still retire `django_chat` later as its own ticket. |
| **Seat-store (later)** | First-class agent instance (id ≠ recipe id). | After filter, if Add-agent must stick. |
| **Editor pairing rule** | When name === blueprint id/name, hide or demote the Blueprint control. | Yes, same implement Issue or a one-line follow-up. |

**Do not** ship a migrate/archive script as the #595 fix.

---

## Ranked index

| ID | Rank | Sev | Surface | One-line |
|----|------|-----|---------|----------|
| B-01 | HIGH | P0 | rail + Search + Django leftover | Entire `/v1/blueprints` catalog rendered as Agent rows (`exampleRoleAgents` does not filter) |
| B-02 | HIGH | P0 | editor + chat URL | Seat id === recipe id; Name and Blueprint default to the same string |
| B-03 | HIGH | P1 | rail | Scale-out hover-edit calls undefined `openBlueprintEditor` → runtime `ReferenceError` |
| B-04 | HIGH | P1 | Add-agent wizard | CLI/API create writes custom library JSON (not discovery); rail never lists it; CLI command is a comment |
| B-05 | HIGH | P1 | favourites | Pin / Alt+1–9 always `?blueprint=` — team/remote pins navigate to a bogus recipe id |
| B-06 | MEDIUM | P1 | hide | CLI verify rows cannot be hidden (conflicts with REQ-24 “any row”) |
| B-07 | MEDIUM | P1 | Search | Messages / Groups / Files / Links / Routines are empty stubs; tests treat that as success |
| B-08 | MEDIUM | P1 | dual chrome | Grok `swarm_*` keys vs Agent Router `agent_*` keys; #579 only helps one |
| B-09 | MEDIUM | P2 | rail | Remote rows refuse reorder (`dropEffect: none`) except unpin-on-self |
| B-10 | MEDIUM | P2 | context menu | Edit / pin on team/remote uses `team:` / `remote:` hide ids as agent ids |
| B-11 | MEDIUM | P2 | rail | `loadingList` / `loadFailed` require **both** blueprint and team queries |
| B-12 | MEDIUM | P2 | leftover | Django `agent_sidebar.js` still concatenates `/v1/blueprints/` into agents |
| B-13 | MEDIUM | P2 | tests | Existing tests **lock in** catalog-as-rail and catalog-as-Search-Bots |
| B-14 | LOW | P2 | tests | Duplicate `describe('AgentSidebar special roles')`; Python REQ-128/164 are source greps |
| I-01 | intentional | — | API | `GET /v1/blueprints/` remains the recipe catalog |
| I-02 | intentional | — | rail | Host CLI verify rows (`grok_agent`, …) are seats, not recipes |
| I-03 | intentional | — | hide seed | First-visit hide of gate/skeptic is product, not the #595 bug |

---

## HIGH findings

### B-01 — Catalog recipes are Agent rail rows

| | |
|--|--|
| **Rank / sev** | HIGH / P0 |
| **#595** | Success 3: rail + Search agents only. |
| **What** | `AgentSidebar` `agents` memo starts from `exampleRoleAgents(catalog)` where `catalog` is `GET /v1/blueprints/` (~54 on `:8001`). Search Bots is the same. Demos (`poets`, `chucks_angels`, `django_chat`, MoA aliases) all show. |
| **Not** | Django Agent / `marketplace_blueprint` seed rows (live count **0**). |
| **Later** | [Implement Issue](#implement-issue--concrete-success-595) — allowlist or `metadata.rail` flag. |

### B-02 — Redundant name / blueprint pairing

| | |
|--|--|
| **Rank / sev** | HIGH / P0 |
| **What** | Recipe metadata `name` ≈ `id`. Editor defaults both fields to that id. `assignedBlueprintId(id)` returns `id` until the user picks a *different* recipe. `saveAgentEdit` drops `blueprintId` when it equals `agentId`. |
| **Later** | Filter so the rail row is a seat; editor rule above. Do not rename `codey`’s metadata. |

### B-03 — `openBlueprintEditor` is not defined

| | |
|--|--|
| **Rank / sev** | HIGH / P1 |
| **Path** | `AgentSidebar.tsx` scale-out branch (`shouldOpenSessionPicker`): hover pencil calls `openBlueprintEditor(agent)`. Non-scale-out branch correctly calls `openEditor` → `openAgentEditor`. |
| **Later** | One-line fix to `openEditor` (own Issue). Tests must click scale-out + edit. |

### B-04 — Add-agent wizard does not create a rail seat

| | |
|--|--|
| **Rank / sev** | HIGH / P1 |
| **What** | CLI/API steps `POST /v1/blueprints/custom/` (`createCustomBlueprint`). Id is `name.lower().replace(" ", "_")`. Code for CLI is `# CLI agent: …` / `# Command: …` only. Invalidates `['blueprints']` which still **cannot** see custom JSON. Navigates to `/chat?blueprint=<id>` (ghost seat). Remote step is the only path that hits a list the rail actually fetches (`configured-remotes`). |
| **#597** | That PR manages existing CLI/API from the wizard — still the wrong store unless they also add a seat list. Coordinate; do not race a third create API in a drive-by. |
| **Later** | Seat-store or, as a stopgap, merge marked custom entries into the rail **after** the catalog filter exists. Tests must assert the new row appears (they do not today). |

### B-05 — Favourite / shortcut href ignores row kind

| | |
|--|--|
| **Rank / sev** | HIGH / P1 |
| **What** | Visible pins always `<Link to={/chat?blueprint=${pin.id}}>`. Alt+1–9 same. Pinning `team:demo` or `remote:omb` yields `?blueprint=team%3Ademo`. Herdr is the only special case (`/teams/#herdr-members`). |
| **Later** | Href from pin id prefix / stored kind. Tests for team/remote pins (missing). |

---

## MEDIUM findings (rail logic)

### B-06 — CLI hide exemption

`hideFromRail` no-ops `isCliRailAgent`. Visible list always includes `kind === 'cli'` even if the id is in `swarm_hidden_agents`. Tests require this. REQ-24 / comments say hide is not role-exempt; CLI is a second exemption. CoS: keep (PATH verify always visible) or honour hide.

### B-07 — Search stub tabs

`SEARCH_PALETTE_TABS` includes Messages, Groups, Files, Links, Routines. `rows` only builds Bots + Actions. Tests click Messages and expect “No results.” Quality: asserts the stub, not a product.

### B-08 — Dual persistence

| Grok chrome | Agent Router (`/agents`) |
|-------------|--------------------------|
| `swarm_hidden_agents` | `agent_hidden_ids` |
| `swarm_pinned_agents` | `agent_favourite_ids` |
| `swarm_rail_order` | `agent_custom_order` |
| per-agent hide, no hide-all | `hideAllExceptStarters` |

[#579](https://github.com/matthewhand/open-swarm/pull/579) persists Grok keys via Django prefs. Do not invent a third key. Call out Router keys as out of scope for that PR.

### B-09 — Remotes not in list reorder

`renderRemoteRow` `onDragOver` only allows drop when the drag is already pinned (unpin). Non-favourite remotes cannot change `swarm_rail_order` relative to agents/teams.

### B-10 — Context menu on team/remote

`openMenu(..., hideId, ...)` then “Edit agent” → `openAgentEditor({ agentId: menu.agentId })` with `team:…` / `remote:…`. Pin uses the same id. Hide/unhide is correct for those prefixes.

### B-11 — Load / error gates

`loadingList = blueprintsQuery.isPending && teamsQuery.isPending` — if teams return first, the list paints without blueprints. `loadFailed` requires both queries in error **and** `visibleCount === 0` (synthetics + CLI can hide a real catalog failure).

### B-12 — Django leftover

Same catalog-as-agents as B-01. Filter must include `agent_sidebar.js` or the operator page will regress #595.

### B-13 — Tests encode the defect

See [Test coverage / quality](#test-coverage--quality). A later filter PR **will fail** current AgentSidebar + SearchPalette + `exampleRoleAgents` tests unless those asserts flip.

---

## LOW / quality

- **B-14:** `AgentSidebar.test.tsx` repeats `describe('AgentSidebar special roles')` (two nearly identical Support-first cases). `tests/unit/test_req128_bump_order.py` and `test_req164_add_agent_search_row.py` are `Path.read_text` substring checks, not browser/RTL behaviour (RTL *does* cover bump + Add-agent placement separately).
- Plugins dialog is honest-empty (already tested).
- `openBlueprintEditor` vs `openEditor` is the only confirmed crash in this surface.

---

## Test coverage / quality

| Area | What exists | Gap / quality |
|------|-------------|---------------|
| **AgentSidebar (Grok)** | Large RTL file: hide/unhide, pin move-not-copy, bump, CLI always-visible, Search opens palette, Add-agent `+` placement, teams/remotes, scale-out picker | **Locks in** Codey/Stewie on the rail. No “catalog excluded.” No team/remote pin href. No scale-out edit (would catch B-03). Duplicate special-roles describe. |
| **SearchPalette** | Open/focus, Bots lists Support+Codey, Actions, filter, Ctrl+1, Enter → `?blueprint=` | **Locks in** catalog Bots. Empty-tab test is a stub lock. No hidden-filter. No teams/remotes as Bots. |
| **AddAgentWizard** | Kind copy, Cancel, happy-path CLI/API/remote mocks | No validation fail, no 409, no Esc/backdrop, **no rail appearance**, no “custom JSON ≠ `/v1/blueprints`”. |
| **AgentEditor / agentEdits** | Picker persist; self-assignment cleared | **Locks in** `assignedBlueprintId(id) === id`. No “hide Blueprint when name === recipe.” |
| **hiddenAgents / pinnedAgents / railOrder** | Persistence, seed, bump stability | Solid helpers. Do not prove catalog filter. |
| **Python REQ-128 / 129 / 164** | Source greps + some RTL | Greps do not bite if a second sidebar copy regresses. |
| **Agent Router sidebar** | Separate `AgentSidebar/__tests__` + `agent-store.test.ts` hide-all/starters | Different product. Easy to “fix” the wrong rail. |
| **e2e** | Chrome specs mock `object: 'blueprint'` as rail data | Will keep teaching catalog-as-agents until rewritten. |
| **#595 success tests** | **Missing** | Need the [Implement Issue](#implement-issue--concrete-success-595) asserts (allowlist/flag + denylist fixtures). No DB-archive test — there is nothing to archive. |

**Asserts that do not bite:** Python `assert "bumpRailIdToTop" in content`; Search “No results” on Messages; Add-agent `onCreated` without querying the rail.

---

## HIGH items for CoS (file as Issues)

`gh` is read-only on this agent. Copy-paste these. Do not implement in the look-only PR.

### Issue 1 — Rail seat filter (implements #595)

Copy the [Implement Issue](#implement-issue--concrete-success-595) block. `Fixes #595`. **Filter / metadata flag, not DB archive.**

### Issue 2 — Add-agent must create a seat the rail can list

- **Intent:** Wizard CLI/API (and later manage in #597) produce a visible seat, not a library JSON ghost.
- **Success:** After create, a row appears (or an honest error). CLI command is wired or the kind is rejected. Tests include rail appearance + failure paths.
- **Constraints:** Prefer seat-store or an explicit seat flag. Do not merge the entire custom library onto the rail (that recreates B-01). Coordinate #597.
- **Owner:** Same wave or next.

### Issue 3 — Scale-out hover-edit `ReferenceError`

- **Intent:** Pencil on a multi-session row opens the same agent editor as a normal row.
- **Success:** `openBlueprintEditor` gone or aliased; RTL clicks scale-out + edit; no console error.
- **Constraints:** Tiny PR. Own-diff CI only.
- **Owner:** Cursor; can ride with Issue 1 if wave capacity allows.

### Issue 4 — Favourite / Alt+digit hrefs honour team/remote/herdr

- **Intent:** A pinned team opens `?team=`; remote opens `?remote=`.
- **Success:** Tests pin each kind and assert href / Alt+1. Herdr unchanged.
- **Constraints:** Do not fight #579 schema; store kind or parse prefixes.
- **Owner:** Cursor; good pair with Issue 1.

---

## Implement Issue — concrete Success (#595)

CoS files one implement Issue (or reuses #595). **Not this PR.** Pick **one** filter SoT (A, B, or C). Do not combine three sources of truth.

### Recommended SoT: **B** (metadata `rail` flag) + SPA apply

`installed` / `compiled` on `/v1/blueprints/` are already `null` placeholders. Do **not** overload `installed` (that word is the library “installed recipes” list). Add an explicit seat flag.

| Option | Mechanism | When |
|--------|-----------|------|
| **A — SPA allowlist** | Shared helper `isRailSeat(row)` in SPA (+ leftover `agent_sidebar.js`). Catalog API unchanged. | Fastest. Fragile when new recipes land (they show on the rail until someone updates the list). |
| **B — discovery metadata flag (preferred)** | `metadata.rail: true` (or `seat: true`) on recipes that **may** be a chat seat. Missing/false = catalog-only. `BlueprintsListView` passes `rail` through. SPA + Search + leftover JS: `row.rail === true` **or** `kind` in `cli`/`herdr`. Teams/remotes unchanged. | Durable. New demos default off. `/v1/models` and `?blueprint=<id>` still work. |
| **C — SPA denylist of the demo pack** | Hard-coded exclude of today’s `:8001` demo ids. | Stopgap only. New `blueprint_*` packages leak onto the rail again. |

**Default for unknown recipes: deny on the rail** (B with missing=`false`, or A as a closed allowlist). That matches “exclude demo recipe pack.”

### Allowlist (must remain on the Grok rail)

These are **seats**, not the demo pack:

- Role seats: `support` (visible). `gate` / `tool_gate` / `skeptic` stay **hide-seeded** (Hidden Bots), not deleted.
- Host CLI verify rows from `/v1/cli-agents/` (`grok_agent`, `agy_agent`, `opencode_agent`, `pi_agent`, …).
- Team roster rows (`?team=`), remotes (`?remote=`), Herdr members, CoS from rosters.
- User-created seats **once they exist** (Add-agent today does not create these — B-04). Do not treat `POST /v1/blueprints/custom/` as a seat unless the implement Issue also adds a seat flag.

Favourites: a pin of a **denied** catalog id may remain as a favourite (migration) **or** drop on next load. Pick one and test it. Do not re-insert denied ids into the list below the grid.

### Denylist (must **not** be peer Agent rows)

Minimum fixtures from the `:8001` / #595 comment — all must fail `isRailSeat` / `rail !== true`:

| Class | Example ids (not exhaustive) |
|-------|------------------------------|
| Demo / persona packs | `poets`, `chucks_angels` |
| Webui leftover recipe | `django_chat` (#419 may delete the package later; filter still required until then) |
| MoA / hybrid + aliases | `moa`, `mixture_of_agents`, `moa_orchestrator`, `moa-orch`, `hybrid_moa`, `moa_hybrid`, `hybrid-consensus`, `hybrid_team`, `hybrid_swarm` |
| CLI-fusion recipes + `swarm_*` aliases | `cli_fusion`, `cli_ensemble`, `cli_map`, `cli_recurse`, `cli_pipeline`, `cli_roundtable`, `cli_planner`, `cli_orchestrator`, `swarm_ensemble`, `swarm_map`, `swarm_recurse`, `swarm_pipeline`, `swarm_roundtable`, `swarm_planner`, `swarm_orchestrator` |
| Other catalog recipes | `software_dev`, `software-dev`, `codey`, `stewie`, `geese`, `zeus`, `gawd`, `suggestion`, `fs_introspect`, `remote_harness`, `harness_fleet`, `persona_council`, `dynamic_team`, `agent_router`, `jeeves`, `rue_code`, `whiskeytango_foxtrot`, `cli_agent`, `chatbot`, `gate` *as a visible list row if un-hidden only via user Unhide* |

`codey` is a recipe, not a user seat. Today’s tests **require** Codey on the rail — the implement PR **must flip those asserts.**

### Success checklist (implement PR)

1. **`:8001` / local rail** after filter: Agent list does **not** contain `poets`, `chucks_angels`, `django_chat`, `moa` / `mixture_of_agents`, `cli_fusion` / `swarm_ensemble`, `software_dev`. Support + CLI verify + teams/remotes/Herdr/CoS still present.
2. **Search Bots** uses the same `isRailSeat` / `rail` predicate. Those demo ids do not appear as Bots. Actions “Blueprints” still opens the catalog sheet.
3. **`GET /v1/blueprints/` still lists recipes** (~54 on this sample, or the same discovery set). Catalog is not deleted. If option B: each row has `rail: true|false`; demos are `false`.
4. **`GET /v1/models/`** and `?blueprint=poets` (deep link / completions) still resolve. Filter is **display**, not discovery removal. (Optional: Settings copy “recipe, not a rail agent.”)
5. **Django `marketplace_blueprint`** remains unused. **No** migrate/archive script. **No** Neon.
6. **Name === blueprint UX** (same PR or listed follow-up): when a remaining seat’s display name equals its assigned blueprint id/name, hide the Blueprint `<select>` label or show “Recipe: {id}” as secondary meta. Do not rename 39 recipe slugs.
7. **Leftover** `agent_sidebar.js` uses the same predicate (or operator rail is documented as out of scope in the Issue — pick one).
8. **Tests (must bite):**
   - RTL: catalog fixture includes `poets`, `chucks_angels`, `django_chat`, `moa`, `cli_fusion`, `codey` → **none** in `[data-testid=os-agent-rail]` agent rows or Search Bots.
   - RTL: `support` + a CLI verify row **are** listed.
   - Unit: `isRailSeat` / metadata default-deny for unknown ids.
   - If option B: API serializer test that `rail` is present and `poets` is false.
   - Flip existing AgentSidebar / SearchPalette / `exampleRoleAgents([codey])` expects that **lock in** catalog-as-rail.
9. **`Fixes #595`.** Coordinate #419 (do not delete `django_chat` in the filter PR unless CoS folds it), #579 (pins of denied ids), #597 (wizard still not a seat).

### Out of this implement Issue

B-03 (`openBlueprintEditor`), B-04 (wizard seat-store), B-05 (pin href kinds) — separate Issues in the list above. Do not block #595 filter on those.

---

## Out of scope / coordination

- Surfaces **A** (chat/composer/session) and **C** (CLI/API/remote harness) — sibling #596 reports.
- [#419](https://github.com/matthewhand/open-swarm/issues/419) — still retire `django_chat` as a catalog id; filter hides it from the rail even if the package stays.
- [#579](https://github.com/matthewhand/open-swarm/pull/579) — persist Grok hide/pins; recipe ids in those lists are leftover after a filter.
- [#597](https://github.com/matthewhand/open-swarm/pull/597) — wizard manage/folder; same wrong create store (B-04).
- [#576](https://github.com/matthewhand/open-swarm/pull/576) / [#578](https://github.com/matthewhand/open-swarm/pull/578) / [#582](https://github.com/matthewhand/open-swarm/pull/582) — docs ADRs; no conflict.
- [#577](https://github.com/matthewhand/open-swarm/pull/577) — keybinding tips chrome; no rail-list conflict.
- Drafts #297 / #537 — not reopened.
- No Neon. No secrets. No runtime change in this PR.
