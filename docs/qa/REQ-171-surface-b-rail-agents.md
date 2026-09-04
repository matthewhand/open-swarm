# REQ-171 surface B — Left rail / agents / favourites / hidden / blueprints-as-agents

Look-only audit for [#596](https://github.com/matthewhand/open-swarm/issues/596) (REQ-171) surface **B**, coordinating [#595](https://github.com/matthewhand/open-swarm/issues/595) (REQ-170: stop listing blueprints as agents; redundant name/blueprint pairing).

**As-of:** `origin/main` @ `f21d24ea` (CLI/API dropdowns #593). No SPA, Django, tests, or CI files were changed in this PR.

**Method:** Static read of Grok `AgentSidebar.tsx`, Search, Add-agent wizard, agent editor/edits, rail order / pins / hide helpers, `/v1/blueprints/` + discovery + custom library, leftover Django `agent_sidebar.js`, Agent Router sidebar + zustand store, and the tests that lock current behaviour. GitHub: #595, #596, #419; open PRs #576–#579, #582, #597. **No Neon. No secrets. No live `:8001` dump** (this cloud has no host bind to that sample). Expected `:8001` rail is inferred from the same code path the sample runs.

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

**Recommended later path: FILTER the rail + Search first. Do not delete shipped recipes.** Cleanup is a dry-run inventory of *ids treated as seats*, not a wipe of `src/swarm/blueprints/`. A real Agent instance store is the durable fix if Add-agent must create seats; it does not exist on the Grok rail today.

---

## Root cause (#595) — why recipes appear as Agent rows

### 1. Catalog API is discovery, not seats

`BlueprintsListView` (`src/swarm/views/api_views.py`) lists `get_available_blueprints()`:

- `discover_blueprints(BLUEPRINT_DIRECTORY)` — every `blueprint_*.py` under `src/swarm/blueprints/` (**37** shipped packages on this tip, including `django_chat`, `software_dev`, `codey`, `cli_*`, MoA/hybrid family).
- `merge_community_blueprints` — extra / user dirs.
- `apply_blueprint_aliases`.
- **`teams.json` dynamic-team aliases** merged as `DynamicTeamBlueprint` with `metadata.name = team_id` (name === id by construction).

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

### 7. What `:8001` should show (inferred)

On a default discovery catalog, the Grok rail lists Support (and CLI verify rows), then **every remaining discovered recipe** that is not hide-seeded — typically dozens of snake_case names that match `?blueprint=` and the Blueprint picker. Favourites show Support. Hidden Bots starts at 2 (gate + skeptic) unless localStorage was customized. This matches the live report on #595 without needing a LAN dump.

---

## Cleanup vs filter (CoS decision)

| Option | What it does | Use? |
|--------|----------------|------|
| **Filter (recommended first)** | SPA rail + Search Bots + leftover Django sidebar list **seats only**: Support (and other explicit role seats), host CLI verify rows, team/remote/Herdr rows, CoS from rosters, and *user-created instances once a store exists*. Catalog stays under Settings / Blueprints sheet / Add-agent kind flows / `GET /v1/blueprints/`. | **Yes.** Matches #595 success 3. SPA-only is allowed. |
| **Cleanup / migrate** | Idempotent dry-run that **lists** catalog ids currently treated as seats; optional archive of *custom library* JSON that was created as a fake agent; **do not delete** shipped `blueprint_*.py` or `/v1/models` ids. | **Secondary.** There is no Agent table to vacuum. Deleting recipes breaks CLI/API. |
| **Seat-store (durable)** | First-class agent instance (id ≠ recipe id) with Blueprint as a picker (REQ-58). Add-agent writes a seat, not `blueprint_library.json`. | **After filter**, if CoS wants “create agent” to stick. |
| **Editor rule (pick one)** | When display name equals assigned blueprint name/id: hide Blueprint control, or show “Recipe: codey” as secondary meta, or default new-seat names to “New agent” / “Copy of {recipe}”. | **Yes**, with the filter. Do not rename every recipe. |

**Do not** prefer “cleanup the seed” as the main fix. The seed **is** discovery. **Do not** hide recipes from `/v1/blueprints/` unless #419-style retirement (e.g. `django_chat`) is in scope.

Suggested filter predicate (later implementer, not this PR):

```text
rail agent row if:
  isSupportAgent OR kind === 'cli' OR kind === 'herdr'
  OR explicit user-seat flag (does not exist yet)
else:
  catalog recipe → Settings / picker only
teams/remotes stay their own row kinds
```

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
| **What** | `AgentSidebar` `agents` memo starts from `exampleRoleAgents(catalog)` where `catalog` is `GET /v1/blueprints/`. Search Bots is the same. |
| **Not** | A fixture that inserted one Django `HerdrAgent` / ORM row per recipe. |
| **Later** | **filter** (SPA + Search + leftover JS). Keep recipes on `/v1/blueprints/` and Settings. |

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
| **#595 success tests** | **Missing** | Need: rail/Search exclude recipe ids; cleanup dry-run; editor pairing rule. |

**Asserts that do not bite:** Python `assert "bumpRailIdToTop" in content`; Search “No results” on Messages; Add-agent `onCreated` without querying the rail.

---

## HIGH items for CoS (file as Issues)

`gh` is read-only on this agent. Copy-paste these. Do not implement in the look-only PR.

### Issue 1 — Filter catalog recipes out of Grok rail + Search (implements #595)

- **Intent:** Rail and Search Bots show chat seats, not `BlueprintBase` recipes.
- **Success:** Support + CLI verify + teams/remotes/Herdr/CoS remain; `codey` / `django_chat` / `software_dev` / `cli_fusion` are not peer rows; Settings / Blueprints sheet still lists recipes; tests for “catalog not in rail”; `Fixes #595`.
- **Constraints:** **Filter, not delete recipes.** SPA (+ leftover `agent_sidebar.js`) OK. Coordinate #419 (id still in catalog), #579 (do not persist recipe ids as favourites). No Neon. No secrets.
- **Owner:** Cursor implementer after CoS queues a 2–3 fix wave.

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

## Out of scope / coordination

- Surfaces **A** (chat/composer/session) and **C** (CLI/API/remote harness) — sibling #596 reports.
- [#419](https://github.com/matthewhand/open-swarm/issues/419) — still retire `django_chat` as a catalog id; filter hides it from the rail even if the package stays.
- [#579](https://github.com/matthewhand/open-swarm/pull/579) — persist Grok hide/pins; recipe ids in those lists are leftover after a filter.
- [#597](https://github.com/matthewhand/open-swarm/pull/597) — wizard manage/folder; same wrong create store (B-04).
- [#576](https://github.com/matthewhand/open-swarm/pull/576) / [#578](https://github.com/matthewhand/open-swarm/pull/578) / [#582](https://github.com/matthewhand/open-swarm/pull/582) — docs ADRs; no conflict.
- [#577](https://github.com/matthewhand/open-swarm/pull/577) — keybinding tips chrome; no rail-list conflict.
- Drafts #297 / #537 — not reopened.
- No Neon. No secrets. No runtime change in this PR.
