# REQ-188 Surface A — look-only Settings audit

> Settings sections **`definition`**, **`blueprint`**, **`remotes`** in the live
> SPA sheet (`webui/frontend/src/components/SettingsSheet.tsx`) plus
> `DefinitionPane`, `BlueprintsListPane` / `BlueprintEditorPane`,
> `RemotesCatalogPane` / `RemoteOperatePane`.
> **Look-only.** This file is a findings list for CoS triage. It does not
> change runtime product code, close [#644](https://github.com/matthewhand/open-swarm/issues/644),
> or implement fixes.

**As-of:** `origin/main` @ `781db565` (`feat(webui): remove You and agent name labels above chat bubbles (Fixes #507) (#625)`).

**Umbrella:** [#644](https://github.com/matthewhand/open-swarm/issues/644) (REQ-188). This report is **audit partial** for **surface A only** (Definition / Blueprints / Remotes). Other Settings nav items (`retention`, `hostname`, `llm-profiles`, `rail`, `system`) are out of scope here except where a surface-A control jumps to them.

**Method:** static read of the live sheet, the three panes, remotes / definition / blueprint APIs, and the tests that claim to lock this surface. No host bounce. No Neon. No secrets. No live LAN URLs. No product edits.

**How to read**

| Sev | Meaning here |
|-----|----------------|
| **HIGH** | Wrong behaviour a user can hit from Settings today: empty untitled pane, Save that does not persist, “Editing” that cannot edit, or a catalog that lies empty / invites a live token. File a child Issue. |
| **MEDIUM** | Real hole, but bounded (no PATCH after add, silent fallback, dead sibling form, test that locks the buggy success). Fix after HIGH waves. |
| **LOW** | Dead overlay tree, unused exports, copy nits, or intentional inspect-only chrome. Do not file unless a later REQ needs it. |

**Test column:** `missing` = no test would fail if the bug shipped. `weak` = a test exists but asserts a mock, a happy path, or the buggy fallback itself.

**Do not treat this PR as Fixes #644.** Fixes belong on child Issues, queued in waves of 2–3.

---

## Skipped open Cursor surfaces

REQ-188 asked look-only agents not to fight in-flight Cursor PRs unless the defect is critical. On this snapshot:

| Open PR | Surface | This audit |
|---------|---------|------------|
| [#576](https://github.com/matthewhand/open-swarm/pull/576) | Desktop packaging ADR (REQ-151) | **Skip.** Docs/ADR only. No Settings sheet overlap. |
| [#577](https://github.com/matthewhand/open-swarm/pull/577) | First-load keybinding tips under composer (#571) | **Skip.** Composer / Search chips. No Settings pane overlap. |
| [#578](https://github.com/matthewhand/open-swarm/pull/578) | Kind bases + handoff-graph docs (#564 / #570) | **Skip.** README / ADR-005 / examples. Wizard still emits `BlueprintBase`; this audit does not touch that. |
| [#579](https://github.com/matthewhand/open-swarm/pull/579) | Persist favourites / Hidden / hostname prefs | **Skip.** Hostname hydrate/save is a later Settings section, not surface A. Do not “fix” hostname keys here. |
| [#599](https://github.com/matthewhand/open-swarm/pull/599) / [#600](https://github.com/matthewhand/open-swarm/pull/600) / [#609](https://github.com/matthewhand/open-swarm/pull/609) | REQ-171 look-only `docs/qa/` | **Skip.** Different umbrella. This file is a sibling under `docs/qa/`; do not edit those reports. Rail “blueprints-as-agents” (surface B) is a **catalog-as-rail** problem, not this sheet’s inspect pane. |

Related open / archived product docs (do **not** re-file as new product REQs):

- [REQ-42](../archive/requirements/REQ-42.md) — role badge → explained Definition pane. Success #4 (“Edit code … After save, Re-summarise”) is what H2 shows is unwired for shipped seats.
- FEATURE_STATUS “Settings → Blueprints list (REQ-58)” — honest that the list **inspects** a recipe. The in-pane heading still says **Editing** (H3).
- FEATURE_STATUS Grok chrome line still lists gear as Remotes / Retention / Hostname / LLM / System — **Definition** and **Blueprints** are first-class nav items today and are omitted from that sentence.

---

## Surface map (what Settings A is today)

Two `SettingsSheet` trees exist. **Only one is mounted.**

| Piece | Role | Mounted? |
|-------|------|----------|
| `webui/frontend/src/components/SettingsSheet.tsx` | Live DaisyUI `modal-end` sheet. Nav: Definition, Blueprints, Remotes, Retention, Hostname, Show LLM profiles, Rail, System. | **Yes.** `App.tsx` listens for `swarm:open-settings` and passes `section` / `blueprintId` / `teamId` / `definitionKind` / `definitionId`. |
| `webui/frontend/src/components/overlays/SettingsSheet.tsx` | Older REQ-48 sheet. Remotes are a Hermes / OMB / Rakazo dropdown of **placeholder** panes (“the remotes API has not landed”). | **No.** Only `overlays/ChatOverlays.tsx` imports it; `ChatOverlays` is never imported. |
| `webui/frontend/src/components/DefinitionPane.tsx` | Definition section. Static brief + optional LLM summary + Edit code / Re-summarise. | Yes, when `section === 'definition'`. |
| `BlueprintsListPane` + `BlueprintEditorPane` (same file as the live sheet) | Catalog listbox + highlighted Python `<pre>`. | Yes, when `section === 'blueprint'`. |
| `RemotesCatalogPane` (live sheet) + `RemoteOperatePane` (`RemotesSettings.tsx`) | Opt-in catalog, Add / Remove, Health / List / Send. | Yes, when `section === 'remotes'`. |
| `EmptyRemotesPane` / `AddRemoteForm` (`RemotesSettings.tsx`) | Alternate empty + add UI (“never paste a token”). | **No** importer. |

How the live sheet gets a target:

```
Gear (ChatPage)          → OPEN_SETTINGS_EVENT with no detail
                           default section = retention
                           Definition/Blueprints/Remotes are nav clicks only

Role badge / team badge  → openSettingsSheet({ section: 'definition', definitionId, … })
Chat header identity     → same, kind role|blueprint|team from the current seat
Agent editor “Edit blueprint…” → section: 'blueprint' + blueprintId
RemoteSelect “Add remote” / rail server popup → section: 'remotes'
```

`SettingsSheet` resolves Definition as:

```text
resolvedDefinitionId = definitionId || teamId || blueprintId || ''
resolvedKind         = definitionKind || (teamId ? 'team' : blueprintId ? 'role' : 'blueprint')
```

Gear → Definition therefore opens **`kind=blueprint`, `id=''`**.

---

## Ranked index

| ID | Sev | Section | One-line |
|----|-----|---------|----------|
| H1 | HIGH | definition | Gear / nav Definition with no identity is an empty untitled pane |
| H2 | HIGH | definition | Save swallows 404 / wrong store and still claims the draft is stored |
| H3 | HIGH | blueprint | Copy says “Editing {label}”; the control is a read-only `<pre>` with no Save |
| H4 | HIGH | remotes | GET failure and pending look like “No remotes configured yet” |
| H5 | HIGH | remotes | Add form posts a live `api_key` despite the “env name only” contract |
| M1 | MEDIUM | definition | GET `/v1/definitions/…` failure silently uses `localDefinitionContext` |
| M2 | MEDIUM | definition | Team / shipped-role Edit code always `PATCH /v1/blueprints/custom/<id>/` |
| M3 | MEDIUM | definition | Sheet `useEffect` ignores `definitionId` / `definitionKind` / `teamId` |
| M4 | MEDIUM | definition | Injected tools / metadata / handoff are never shown except via LLM summary |
| M5 | MEDIUM | blueprint | `ModuleLink` opens raw `/v1/blueprints/<id>/source?file=` JSON in a new tab |
| M6 | MEDIUM | blueprint | File-tab `aria-selected` follows `live.selected`, not the click (`selectedFile`) |
| M7 | MEDIUM | remotes | No PATCH / edit URL after add (backend `PATCH /v1/remotes/<id>/` exists) |
| M8 | MEDIUM | remotes | Dead sibling `AddRemoteForm` contradicts the live Add form |
| M9 | MEDIUM | tests | E2E / Vitest never open Definition or Blueprints from the gear; they lock H2’s fake save |
| L1 | LOW | chrome | Orphan `overlays/SettingsSheet` still has placeholder remotes + its own test file |
| L2 | LOW | remotes | `EmptyRemotesPane` / `AddRemoteForm` unused exports |
| L3 | LOW | remotes | Duplicate RemoteSelect + Remove list; Cancel only clears the password field |
| L4 | LOW | blueprint | “Catalog recipes this instance can assign” — select inspects, does not assign |
| L5 | LOW | remotes | Two `remoteKindLabel` helpers (`lib/remotes.ts` vs `lib/remoteKinds.ts`) |

Suggested first fix wave (2–3): **H1, H2, H3**. That is the “empty / can’t edit / Save lies” cluster #644 asked about. H4 + H5 are the Remotes honesty wave.

---

## Section: `definition` (`DefinitionPane`)

### What the UI claims

- Nav label: **Definition**.
- Heading: `agentLabel` of the current id / API title (role name, team name, or blueprint id).
- Eyebrow: `{kind}` and optional `· {role}`.
- **How it works** — static brief from `staticExplanation` (gate YES/NO, skeptic retry, Support Socratic, CoS talk-to-any-team, generic worker / team copy).
- **Source summary** — default LLM summarises live source + injections, or `MISSING_MODEL_HINT` + **Show LLM profiles**.
- **Edit code** / **Save** / **Cancel** — operator can change the definition source.
- **Re-summarise** — refresh the LLM against the new source (disabled without a default model).

REQ-42 success #4 is explicit: after Save, Re-summarise uses the new source. The pane is not advertised as inspect-only.

### What actually renders

| Control | Editable? | Wired? |
|---------|-----------|--------|
| Static brief | No (copy) | Yes — `ROLE_BRIEFS` / `TEAM_BRIEF` / `BLUEPRINT_BRIEF`. Does not use the API `explanation` field. |
| Source summary | No | Yes when `definitionId` is set **and** GET succeeds with `default_llm.configured`. Auto-summarise once per load. |
| Show LLM profiles | Button | Yes — `openSettingsSheet({ section: 'llm-profiles' })`. Works even while this sheet is already open (`initialSection` changes). |
| Re-summarise | Button | Disabled + present when no model; live POST `/v1/definitions/<kind>/<id>/summarize` when configured. |
| Edit code | Textarea | Local `draft` only. |
| Save | Button | Calls `updateCustomBlueprint(definitionId, { code })` → `PATCH /v1/blueprints/custom/<id>/`. On throw, still keeps `savedSource` and tells the user the draft is stored. |
| Cancel | Button | Drops edit mode; does not revert `savedSource`. |

Empty / broken:

- **No identity** (H1): heading is blank (`editedAgentLabel({ id: '', name: '' })` → `''`). Eyebrow is `blueprint`. Brief is `BLUEPRINT_BRIEF`. Fetch is `enabled: Boolean(definitionId)` so it never runs. Source is `fallbackBlueprintSource('', 'default')` (`# Blueprint \n# No source is published…`).
- **GET error** (M1): `contextQuery.data ?? fallback` — no error Alert. The pane looks like a live definition.
- **Injected context** (M4): tools / metadata / handoff / extra are sent to the summariser only. The human never sees them unless the LLM mentions them.
- Closing the sheet and reopening the gear while `section` was `definition` resets to **Retention** (`useEffect` treats `definition` like a contextual pane). That is intentional-ish; the nav still has no picker.

### Findings

#### H1 — Settings → Definition with no selected identity is an empty untitled pane

| Field | Value |
|-------|--------|
| **Severity** | HIGH |
| **File / area** | `SettingsSheet.tsx` (`resolvedDefinitionId` / `resolvedKind`); `DefinitionPane.tsx` heading; `App.tsx` / `ChatPage.tsx` gear (`OPEN_SETTINGS_EVENT` with no detail) |
| **Evidence** | Gear does not pass `definitionId`. Nav **Definition** only `setSection('definition')`. Resolver falls through to `id=''`, `kind='blueprint'`. `fetchDefinition` is disabled. `agentLabel` of an empty id is empty, so the `<h4>` is blank. Edit/Save still render against the empty fallback. This is the path #644 called “show nothing / empty controls” for the first menu item. Badge / header identity paths **do** pass an id (those work). |
| **Suggested fix Issue title** | Settings → Definition needs a selected identity or an honest empty state (REQ-188 / #644) |
| **Test** | **Missing.** `SettingsSheet.test.tsx` “definition pane (REQ-42)” only opens with `definitionId: 'gate'`. `DefinitionPane.test.tsx` always passes `'gate'` / `'support'`. `e2e/settings-sheet.spec.ts` never clicks Definition. `e2e/definition-pane.spec.ts` opens via **Open support settings** (badge), not the gear. |

#### H2 — Save claims success when persistence fails or hits the wrong store

| Field | Value |
|-------|--------|
| **Severity** | HIGH |
| **File / area** | `DefinitionPane.tsx` `handleSave`; `lib/api.ts` `updateCustomBlueprint`; `src/swarm/views/api_views.py` `CustomBlueprintDetailView.patch` (404 if not in the custom library) |
| **Evidence** | Save **always** `setSavedSource(next)` then `PATCH /v1/blueprints/custom/<id>/`. Shipped seats (`gate`, `support`, `skeptic`, catalog recipes) and **teams** are not custom-library rows — PATCH 404s. Catch sets `saveHint` to “Draft stored for this pane…” (same user-visible success class as the 200 path’s “Saved.”). No toast. No revert. Re-summarise then summarises the **local** draft, so the pane looks saved. Custom-library agents are the only ids this Save can actually persist. |
| **Suggested fix Issue title** | Definition Save must persist or fail honestly — do not swallow 404 as “draft stored” (REQ-188 / #644) |
| **Test** | **Weak (locks the lie).** `DefinitionPane.test.tsx` “edit + re-summarise” stubs `/blueprints/custom/` as **404** and still asserts the summary updates. `e2e/definition-pane.spec.ts` stubs `**/v1/blueprints**` as 200 list JSON, so a real PATCH is fulfilled as success without writing a custom row. Neither asserts a persist call for `gate` / a team. |

#### M1 — Definition GET failure is indistinguishable from a local recipe

`contextQuery.isError` is unused. Operators cannot tell a down `/v1/definitions/` from “this is the live source.”

**Test:** missing. Happy-path GET only.

#### M2 — Team and shipped-role Edit code share the custom-blueprint PATCH

Even on 200, a team roster JSON would be written as `code` on a custom blueprint id, not `_team_roster` / disk recipe. Backend `load_source('team', …)` reads roster JSON, not that PATCH.

**Test:** missing.

#### M3 — Re-open while the sheet is already open can keep a stale definition

`useEffect` deps are `[isOpen, blueprintId, initialSection]`. `definitionId` / `definitionKind` / `teamId` are omitted. A second `openSettingsSheet({ section: 'definition', definitionId: 'other' })` with the same `blueprintId` and `initialSection` does not re-resolve.

**Test:** missing.

#### M4 — Injected runtime context is invisible

REQ-42 promised source **plus** injections. The human brief is static; the textarea is source only. If the LLM is off, injections never appear.

**Test:** weak. Tests assert the fixture string inside the **summary**, not a visible injected block.

---

## Section: `blueprint` (`BlueprintsListPane` / `BlueprintEditorPane`)

### What the UI claims

- Nav label: **Blueprints**.
- List blurb: “Catalog recipes this instance can assign to an agent. Select one to inspect its Python — this is not Remotes or other instance Settings.”
- Editor heading: **Blueprint**.
- Editor blurb when an id is set: “**Editing** {label} (role). This editor opens the Python/API recipe … — not the Teams roster.”
- Editor blurb when empty: “Select a roled agent in the rail to open its blueprint.”
- File tabs when the API returns multiple files.
- Runtime module names (`tool_gate`, …) as links “open when present on this checkout.”
- 404 Alert: “No live `/v1/blueprints/{id}/source` file. Showing the design recipe…”

FEATURE_STATUS REQ-58 is closer to the truth (**inspect**). The heading **Editing** is not.

### What actually renders

| Control | Editable? | Wired? |
|---------|-----------|--------|
| Catalog listbox | Select only | Yes — `GET /v1/blueprints/` via `exampleRoleAgents` (full catalog **plus** synthetic support/gate/skeptic). Click sets `selectedBlueprintId`. |
| Python body | **No** | `<pre><code dangerouslySetInnerHTML=highlightPython>` — not a textarea, no onChange, no Save. |
| File tabs | Click | Yes — `setSelectedFile` refetches `GET /v1/blueprints/<id>/source?file=`. Active tab uses `live.selected \|\| live.primary`, not `selectedFile` (M6). |
| Module links | Link or `<code>` | If the filename is in `source.files`, an `<a target=_blank>` to the **raw API JSON**. Otherwise a dead `<code title=path>`. |
| Fallback recipe | Read-only | Yes on 404 — honest Alert + `fallbackBlueprintSource`. |

Empty / broken:

- Gear → Blueprints with no `blueprintId`: list can load; editor is omitted until a row is clicked. That empty editor path is OK. The “Select a roled agent in the rail…” sentence is **dead** inside `BlueprintEditorPane` because the pane is only mounted when `selectedId` is truthy.
- Catalog fetch pending: “Loading blueprints…”. Empty catalog: “No blueprints in the catalog.” (synthetics from `exampleRoleAgents` mean this is rare).
- Selecting a row does **not** assign a recipe to an agent (L4). Assignment lives in `AgentEditor`.

### Findings

#### H3 — “Editing {label}” is a read-only highlighted dump

| Field | Value |
|-------|--------|
| **Severity** | HIGH |
| **File / area** | `SettingsSheet.tsx` `BlueprintEditorPane` |
| **Evidence** | The only body control is a `<pre className={PYTHON_CODE_CLASS}>`. There is no `<textarea>`, no `contentEditable`, no Save, no PATCH to `/v1/blueprints/<id>/source` (that endpoint is GET-only). Users who open **Edit blueprint…** from the agent editor, or Blueprints from Settings, are told they are **Editing** Support/Safety/…. They cannot change a character. This is the “can’t edit” report for the second menu item. Definition’s Edit code is a different pane and does not write this view. |
| **Suggested fix Issue title** | Settings → Blueprints must not claim Editing on a read-only `<pre>` (REQ-188 / #644) |
| **Test** | **Missing for editability.** `SettingsSheet.test.tsx` “blueprint editor” asserts highlighted YES/NO / live `ask_user` / file tabs. It never looks for a textarea or Save, and never asserts the word “Editing” is absent. Would pass forever on a read-only dump. |

#### M5 — Runtime module “links” open raw API JSON

`ModuleLink` `href=/v1/blueprints/${id}/source?file=` in a new tab. That is the JSON envelope (`id`, `files`, `content`, …), not the checkout file and not the in-pane tab switch.

**Test:** `SettingsSheet.test.tsx` **requires** that href for `blueprint_support.py`. Weak — locks the raw-API tab.

#### M6 — File tab selected state can lag or stick

`aria-selected` is `(live?.selected \|\| live?.primary) === name`. Until the refetch returns a matching `selected`, the previous tab stays active (or both look wrong).

**Test:** weak. The tab test stubs the API to echo `selected` from the query string, so it cannot fail this.

#### L4 — “can assign” vs inspect-only

List copy says recipes “this instance can assign.” Select does not call `saveAgentEdit` / the agent-editor picker. Low — FEATURE_STATUS already says inspect.

---

## Section: `remotes` (`RemotesCatalogPane` / `RemoteOperatePane`)

### What the UI claims

- Nav label: **Remotes** (single item, not a Hermes/OMB/Rakazo submenu).
- Blurb: “Only remotes you add appear here and in remote dropdowns. Unused kinds stay off the list.”
- Empty: “No remotes configured yet.” + **Add remote**.
- Add form: Kind, URL, API key env (optional), **API key** (password), **Save remote** / Cancel.
- Swarm kind note: “Nested open-swarm is another process (own DB). Do not add this instance as its own remote.”
- Configured row: kind label + `base_url` or `localhost` + **Remove**.
- Operate pane: Health, List / List bots, Target / Bot id, Message, **Send**.
- `lib/api.ts` contract comment: “Auth is an env-var *name* only; never send a live token.”

The **live** sheet is not the overlay placeholder. `test_req72_chrome_contracts.py` already forbids `"remotes API has not landed"` in the live file.

### What actually renders

| Control | Editable? | Wired? |
|---------|-----------|--------|
| Kind / URL / api_key_env | Yes, add-only | Yes — `POST /v1/remotes/` via `createRemote` → `addRemote`. |
| API key password | Yes, add-only | Yes — included in the POST body when non-empty (H5). Backend `persist_remote` will write a raw key into `swarm_config.json` if it is not a `${ENV}` placeholder. |
| Save remote | Button | Disabled when `!kind` or pending. Toast on success/error. |
| Cancel | Button | Sets `adding=false` and clears **only** `apiKey`. URL / env / kind stay. |
| Remove | Button | `DELETE /v1/remotes/<id>/`. |
| RemoteSelect | Select | Filters the operate pane; includes an “Add remote” option that re-dispatches Settings → remotes. |
| Health / List / Send | Buttons | `POST /v1/remotes/<id>/health/` and `/operate/`. Failures become Alerts (honest). List timeout bounded (REQ-131). |
| Existing URL / env | **No** | Backend `PATCH /v1/remotes/<id>/` exists. The sheet has no edit fields (M7). Change = Remove + Add. |
| GET catalog | — | `configuredRemotes(data)`. **No** `isPending` / `isError` UI (H4). |

Empty / broken:

- `remotesQuery.data` undefined (pending **or** error) → `configured = []` → info Alert “No remotes configured yet.” Same copy as a true empty catalog.
- Unused `AddRemoteForm` (M8) still says “never paste a token” and has no password field — not what the user sees.
- Overlay sheet (L1) still teaches Hermes/OMB/Rakazo placeholders if someone mounts `ChatOverlays`.

### Findings

#### H4 — Remotes GET failure (and the loading gap) look like an empty catalog

| Field | Value |
|-------|--------|
| **Severity** | HIGH |
| **File / area** | `SettingsSheet.tsx` `RemotesCatalogPane` (`remotesQuery` → `configuredRemotes`) |
| **Evidence** | There is no `remotesQuery.isPending` or `isError` branch. `configuredRemotes(undefined)` is `[]`. The pane then paints the same “No remotes configured yet.” Alert used for a healthy empty list, plus **Add remote**. An auth/5xx/offline GET is indistinguishable from “you have never added a remote.” Re-adding a kind that still exists on disk can 400 from the server; the sheet has already told the user the catalog is empty. |
| **Suggested fix Issue title** | Settings → Remotes must not treat a failed GET as an empty catalog (REQ-188 / #644) |
| **Test** | **Missing.** `SettingsSheet.test.tsx` remotes cases stub GET 200 with `configured: []` or a row. No 500/network test. `e2e/settings-sheet.spec.ts` stubs remotes 200 empty and asserts the empty copy. `lib/__tests__/remotes.test.ts` only covers helper math on fixtures. |

#### H5 — Add remote posts a live API key contrary to the published contract

| Field | Value |
|-------|--------|
| **Severity** | HIGH |
| **File / area** | `RemotesCatalogPane` API key `<Input type="password">`; `lib/api.ts` `AddRemoteRequest.api_key` + “never send a live token”; `src/swarm/core/remotes.py` `persist_remote` |
| **Evidence** | The live form label is **API key**, placeholder `${API_KEY}`, and the mutation sends `api_key: apiKey.trim()` whenever the box is non-empty. That is a live secret in the JSON body and, unless it looks like `${ENV}`, a live secret on disk. The module comment and the unused `AddRemoteForm` both say env-name / placeholder only. #644 is a usability audit; a Settings field that invites pasting a token is both a broken affordance (users think this is how auth works) and a secrets foot-gun. |
| **Suggested fix Issue title** | Settings → Remotes Add must not accept or persist a pasted API token (REQ-188 / #644) |
| **Test** | **Missing / opposite.** Add-remote Vitest fills Kind + URL and submits; it does not assert the POST body omits `api_key`. No test that the password field is absent. |

#### M7 — No edit after add

`RemoteDetailView.patch` already persists `base_url` / `api_key_env` / … The sheet only Remove + Add. Changing a URL means delete (and drop team placement) then recreate.

**Test:** missing.

#### M8 — Two Add UIs, one dead, conflicting copy

`AddRemoteForm` is the honest “env name only” form. Nothing imports it. Operators only see `RemotesCatalogPane`.

**Test:** `RemotesSettings.test.tsx` covers `RemoteOperatePane` only.

#### L1 / L2 / L3 — Dead overlay + unused exports + duplicate picker

Do not delete the overlay tree in a settings-usability fix wave unless a dedicated cleanup Issue wants it. `test_req72_chrome_contracts.py` already pins the **live** file to the opt-in catalog. Overlay tests still require Hermes / OMB / Rakazo **placeholder** copy — they do not run against `App.tsx`.

---

## Test gaps (surface A)

| Area | What exists | Gap |
|------|-------------|-----|
| Definition (Vitest) | Brief without LLM; Show LLM profiles event; stub summary includes fixture; edit + re-summarise on 404 custom PATCH | No empty-id / gear path. No persist assertion. 404 treated as success. |
| Definition (e2e) | Badge → pane → edit → re-summarise | Gear / nav Definition never opened. Custom PATCH swallowed by `**/v1/blueprints**` stub. |
| SettingsSheet (Vitest) | Menu labels; remotes add/operate happy path; blueprint highlight + file tabs; one Definition-with-id case | No click Definition without props. No “Editing” vs textarea. No remotes GET error. |
| Settings e2e | Gear → Remotes empty, Retention, Hostname, Rail, System | **Does not click Definition or Blueprints.** |
| RemotesSettings | List bots spinner stop / timeout Alert | Add/Remove/error-empty not covered here. |
| Chrome contracts (pytest) | Live sheet is opt-in remotes, not placeholders | Does not lock Definition empty-state or read-only Blueprint copy. |
| Overlay SettingsSheet.test.tsx | Placeholder remotes still required | Tests a component `App.tsx` does not mount. |

---

## HIGH child Issue drafts (for CoS to file)

`gh` for this agent is read-only. CoS should file these as **sub-issues of [#644](https://github.com/matthewhand/open-swarm/issues/644)**. Do not put `Fixes #644` on the implement PRs until triage says the umbrella can close.

### Issue 1 — Settings → Definition needs a selected identity or an honest empty state (REQ-188 / #644)

**Intent:** Opening Settings → Definition from the gear (or any path without a role / team / blueprint id) must not show a blank heading and a fake worker recipe. Either pick a current chat identity, show a chooser, or show an honest “select an agent or team” empty state with Edit/Save hidden.

**Success:**

1. Gear → Settings → Definition never renders `data-definition-id=""` with an empty `<h4>`.
2. Empty state copy tells the operator how to open a real definition (rail badge, chat header, or a picker).
3. Edit code / Save / Re-summarise are hidden or disabled until an id exists.
4. Tests: open sheet with no `definitionId` and click Definition; assert the empty state (and that Save is not offered). Existing badge / header paths still open `gate` / `support` / a team.

**Constraints:** Look-only audit is this file. Implement is a later PR. DaisyUI / React 18. Do not fold into #579 hostname prefs or #577 keybindings. No secrets. No Neon. Parent #644.

**Owner:** CoS files. Cursor implement. Engineer merge after skeptic.

### Issue 2 — Definition Save must persist or fail honestly — do not swallow 404 as “draft stored” (REQ-188 / #644)

**Intent:** **Save** on Definition either writes the store that `load_source` actually reads, or fails with a visible error. A 404 / network error must not keep a local draft that Re-summarise then treats as canonical.

**Success:**

1. Save for a shipped role / catalog blueprint / team either hits a real write path those kinds use, or returns an error Alert/toast and does **not** set `savedSource`.
2. Custom-library blueprints still PATCH `/v1/blueprints/custom/<id>/` and show Saved only on 2xx.
3. Tests: `gate` (or `support`) Save with 404 does **not** claim stored; a custom id 200 does. Drop the current test that treats custom 404 as the happy path.

**Constraints:** Do not invent a second blueprint store. Teams must not be written as custom `code` unless product agrees that is the store. No secrets in fixtures. Parent #644. Sibling of Issue 1.

**Owner:** CoS files. Cursor implement. Engineer merge after skeptic.

### Issue 3 — Settings → Blueprints must not claim Editing on a read-only `<pre>` (REQ-188 / #644)

**Intent:** The Blueprints pane must match what the control can do. Today that is **inspect**. Either say Inspect / View recipe, or ship a real editor with Save against a write API.

**Success:**

1. Visible copy does not say “Editing {name}” unless a textarea (or equivalent) and a working Save exist.
2. If inspect-only (recommended first wave): heading / blurb say View / Inspect; no Save; 404 fallback Alert stays.
3. If edit is in scope: a write API + tests that a change survives reload. Do not pretend the highlighted `<pre>` is that editor.
4. Tests: assert the inspect copy (or, if edit ships, assert Save + persist). Current highlight / file-tab tests remain.

**Constraints:** Do not fight AgentEditor assignment (REQ-58). This pane is catalog inspect, not “assign to seat.” No Neon. Parent #644.

**Owner:** CoS files. Cursor implement. Engineer merge after skeptic.

### Issue 4 — Settings → Remotes must not treat a failed GET as an empty catalog (REQ-188 / #644)

**Intent:** Loading and error states for `GET /v1/remotes/` are distinct from “you have not added a remote.”

**Success:**

1. Pending shows a loading line (same pattern as Blueprints “Loading blueprints…”).
2. Error shows a warning Alert (request failed) — not “No remotes configured yet.”
3. True empty (`configured: []` on 200) keeps the current empty + Add remote.
4. Tests: stub GET 500 / rejected fetch; assert the error copy and that Add is not the only story.

**Constraints:** Keep opt-in catalog (REQ-59): unused kinds stay off the list. Do not revive overlay Hermes/OMB/Rakazo cards. Parent #644.

**Owner:** CoS files. Cursor implement. Engineer merge after skeptic.

### Issue 5 — Settings → Remotes Add must not accept or persist a pasted API token (REQ-188 / #644)

**Intent:** Settings Add remote matches the published contract: auth is an env-var **name** (or `${ENV}` placeholder), never a live token in the POST body or in `swarm_config.json`.

**Success:**

1. The live Add form has no password **API key** field (or it is removed / replaced with env-name only, matching unused `AddRemoteForm`).
2. `createRemote` / `addRemote` from this pane does not send `api_key` unless it is a `${NAME}` placeholder.
3. Tests: submit Add; POST body has `kind` / optional `base_url` / `api_key_env` only.

**Constraints:** No secrets in repo or screenshots. Do not log keys. Backend may keep PATCH `api_key` for CLI/operator dump; the SPA Settings form must not invite a paste. Parent #644. Can ship in the same wave as Issue 4.

**Owner:** CoS files. Cursor implement. Engineer merge after skeptic.

---

## Out of scope (do not fix in this audit)

- Retention / Hostname / LLM profiles / Rail / System panes (later REQ-188 surfaces).
- #579 server-backed hostname / favourites (will touch Settings hydrate — not these three sections).
- Deleting `overlays/SettingsSheet.tsx` / `ChatOverlays.tsx` (L1) — cleanup, not usability of the live gear.
- Rail “every blueprint is an agent” (#595 / REQ-171 surface B).
- Product implementation of any HIGH draft above.
