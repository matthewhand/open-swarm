# REQ-188 Surface C — look-only Settings audit

> Settings sections **`rail`**, **`system`**, plus Settings **chrome**
> (nav, open/close, section deep-link). Includes `RailPane` (avatar theme
> etc.) and `SystemPane`.
> **Look-only.** Findings list for CoS triage. This file does not change
> runtime product code, close [#644](https://github.com/matthewhand/open-swarm/issues/644),
> or implement fixes.

**As-of:** `origin/main` @ `781db565` (`feat(webui): remove You and agent name labels above chat bubbles (Fixes #507) (#625)`).

**Umbrella:** [#644](https://github.com/matthewhand/open-swarm/issues/644) (REQ-188). This report is **audit partial** for surface **C** only. Sibling look-only agents cover `definition` / `blueprint` / `remotes` / `retention` / `hostname` / `llm-profiles`. Do not re-file their HIGHs here.

**Bar (same as #644):** unusable / empty / uneditable. A control that saves and a peer surface reads it is **not** HIGH. A pane that looks populated while hiding failure, or a Settings write that nothing in the product reads, **is**.

**Method:** static read of `webui/frontend/src/components/SettingsSheet.tsx` (`RailPane`, `SystemPane`, sheet chrome), `webui/frontend/src/App.tsx` (live host), `webui/frontend/src/components/overlays/{SettingsSheet,ChatOverlays}.tsx` (unmounted twin), `AvatarThemePicker.tsx`, `lib/{settingsPrefs,avatarTheme,useAvatarTheme,railResize,hostname,chromeOverlay,api}.ts`, `SearchPalette.tsx`, `AgentAvatar.tsx`, `AgentSidebar.tsx` (rail hostname + bump consumer), `src/swarm/views/system_views.py`, `src/swarm/core/local_store.py`, Vitest (`SettingsSheet.test.tsx`, `AppSettingsChrome.test.tsx`, `App.overlays.test.tsx`, overlays twin tests), and Playwright `e2e/settings-sheet.spec.ts` / `e2e/overlays.spec.ts` / `e2e/chrome.spec.ts`. No host bounce. No Neon. No secrets. No live LAN URLs.

**How to read**

| Sev | Meaning here |
|-----|----------------|
| **HIGH** | Unusable, empty, or uneditable *today* on this surface — or chrome that makes Rail/System unreachable / a failed System fetch look empty. File a child Issue. |
| **MEDIUM** | Real hole, bounded (thin Rail pane vs copy, no URL hash, write-only Hostname key). Fix after HIGH waves. Hostname itself is a sibling section — listed only as overlap. |
| **LOW** | Dead helpers, naming, mobile stack. Do not file unless a later REQ needs it. |

**Test column:** `missing` = no test would fail if the bug shipped. `weak` = a test exists but asserts the buggy fallback or a stub. `theatre` = locks an unmounted Settings IA or a Compact menu that no longer has Settings.

**Do not treat this PR as Fixes #644.** Fixes belong on child Issues, queued in waves of 2–3.

---

## Skipped open Cursor surfaces

REQ-188 asked look-only agents not to fight in-flight Cursor PRs unless the defect is critical. On this snapshot:

| Open PR | Surface | This audit |
|---------|---------|------------|
| [#576](https://github.com/matthewhand/open-swarm/pull/576) | ADR-003 desktop packaging (REQ-151) | **Skip.** |
| [#577](https://github.com/matthewhand/open-swarm/pull/577) | First-load keybinding tips (#571) | **Skip.** Composer chrome only. |
| [#578](https://github.com/matthewhand/open-swarm/pull/578) | REQ-156 graphs + REQ-159 kind bases | **Skip.** |
| [#579](https://github.com/matthewhand/open-swarm/pull/579) | Persist favourites / Hidden / hostname | **Skip.** Prefs persist — coordinate if an implementer touches `swarm_hostname` vs `swarm_hostname_override`. Do not rewrite prefs in a Settings-pane fix. |
| [#599](https://github.com/matthewhand/open-swarm/pull/599) / [#600](https://github.com/matthewhand/open-swarm/pull/600) / [#609](https://github.com/matthewhand/open-swarm/pull/609) | REQ-171 surfaces B / A / C | **Skip.** Do not re-file rail-catalog, WS, or CLI/API HIGHs. Surface B is *rail-as-agent-list*, not Settings → Rail. |

Related closed / product Issues (do **not** re-file as new product REQs; coordinate):

- [#377](https://github.com/matthewhand/open-swarm/issues/377) (REQ-56, **closed**) — System section shipped as read-only local-store facts. Missing/empty store → `0` / “not created yet” is **Success #4**. C-H2 is the *over-apply*: transport/auth failure uses the same empty paint.
- [#563](https://github.com/matthewhand/open-swarm/issues/563) / [#619](https://github.com/matthewhand/open-swarm/pull/619) — Blobs vs Bland on the **chat** rail (`swarm_avatar_theme`). That picker works. The second store (`agent_avatar_theme` / ten packs) is C-H3.
- [#497](https://github.com/matthewhand/open-swarm/issues/497) / [#624](https://github.com/matthewhand/open-swarm/pull/624) — Rail resize / avatar-only. Lives on the rail handle, not Settings → Rail.
- [#364](https://github.com/matthewhand/open-swarm/issues/364) (REQ-48) — Settings is a sheet over chat. Still true on the live host. The unmounted `overlays/` twin is leftover from that wave.

---

## Surface map (what “C” is today)

| Piece | Role | Live? |
|-------|------|--------|
| `webui/frontend/src/components/SettingsSheet.tsx` | Product sheet. Nav: Definition, Blueprints, Remotes, Retention, Hostname, Show LLM profiles, **Rail**, **System**. | **Yes.** `App.tsx` mounts it. |
| `RailPane` (same file) | “Bump completed” toggle + `AvatarThemePicker` (blobs / bland). | **Yes.** |
| `SystemPane` (same file) | Read-only `GET /v1/system/` facts (size, path, conversation/message counts). | **Yes.** |
| `AvatarThemePicker.tsx` + `lib/avatarTheme.ts` | Chat-rail face theme. Key `swarm_avatar_theme`. | **Yes** for `components/AgentAvatar.tsx`. |
| `App.tsx` | `swarm:open-settings` + `swarm:open-llm-profiles` → `settingsOpen` / `settingsDetail`. Close only flips `settingsOpen`. | **Yes.** |
| `openSettingsSheet({ section })` | Event deep-link. Type includes `'rail' \| 'system'`. | **API yes; product callers for rail/system: none.** |
| `SearchPalette` Actions | “Settings” → `openChromeOverlay('settings')` (no section). “Show LLM profiles” → `openSettingsSheet({ section: 'llm-profiles' })`. No Rail / System rows. | **Yes.** |
| Chat gear (`ChatPage`) | `new CustomEvent(OPEN_SETTINGS_EVENT)` — no `detail`. Compact `+` menu is **Compact only**. | **Yes.** |
| `components/overlays/SettingsSheet.tsx` | Older IA: Remotes▸Hermes/OMB/Rakazo placeholders, Retention, Hostname, LLM profiles, Computer control, Role. **No Rail. No System.** `ChatOverlays` always opens section `retention` and **drops event detail**. | **Unmounted.** `ChatOverlays` has zero importers. |
| `lib/chromeOverlay.ts` | Overlay bus. `OPEN_SETTINGS_EVENT` string matches the live sheet. App does **not** listen for teams / blueprints / hidden / role / computer-control. | Half-wired. |
| `GET /v1/system/` (`LocalStoreView`) | Read-only facts. Exceptions → empty payload (REQ-56). Never says Django. | **Yes.** |

BrowserControl is **not** a live Settings section. Computer control is a chat-header WIP stub (`ComputerControlStub`), plus an unmounted overlays pane. Out of this surface except as chrome leftover.

---

## Section inventory

### Settings chrome (nav, open/close, section deep-link)

| Claim | What code actually does |
|-------|-------------------------|
| Gear / Search opens a right-docked sheet over chat | **True** on the live host. `Modal` `placement="end"` `size="sheet"`. Chat stays mounted. |
| Nav lists every Settings section | **True** on the live sheet (8 buttons, `aria-current="page"`). Twin sheet lists a different set. |
| Close via Close / Escape / backdrop | **True.** Live `onClose` is `setSettingsOpen(false)` only. It does **not** call `notifyOverlayClosed()` (only the unmounted twin does; nothing in Chat listens anyway). |
| Section deep-link | **Event-only, incomplete.** `OpenSettingsDetail.section` works when `App` sets `initialSection` and the **live** sheet’s `useEffect` runs. No `?settings=` / hash. Refresh loses the sheet. **Zero** product callers pass `section: 'rail'` or `section: 'system'`. |
| Compact `+` still has Settings | **False.** Menu is Compact only. `ChatPage.test.tsx` and `e2e/chrome.spec.ts` lock that. `App.overlays.test.tsx` and `e2e/overlays.spec.ts` still click Add → Settings / Teams. |

Editability: nav is clickable. Deep-link into Rail/System from Search, URL, or any in-app launcher: **missing**.

### Rail (`RailPane`)

| Claim | What code actually does |
|-------|-------------------------|
| “Drag conversation rows… Hidden stays its own list. Favourite tiles keep their own order.” | Caption only. No drag / Hidden / Favourites controls in this pane. Those live on the rail. |
| Bump completed agents to top | **Works.** Toggle persists `swarm_bump_completed` and dispatches `swarm:bump-completed-changed`. `AgentSidebar` listens and reorders. Default on. Editable. |
| Avatar theme (Blobs / Bland) | **Works on the Grok chat rail** (`components/AgentAvatar` via `useAvatarTheme`). Immediate persist (no Save). Custom uploaded faces win. |
| Same control on `/agents` | **No-op.** Agent Router + `AgentSidebar/SidebarHeader` use `useAgentStore` packs (`chassis` / `pixel` / … + eyes) in `agent_avatar_theme`. Settings does not write that store. |
| Rail width / avatar-only | **Not in this pane.** `lib/railResize.ts` (`swarm_rail_width`, min 68 / max 420 / avatar-only ≤ 96) is the hover handle only. No reset. |
| Rail hostname | **Not in this pane.** Footer input writes `swarm_hostname`. Settings → Hostname writes `swarm_hostname_override`, which **nothing else reads** (sibling section; see MEDIUM). |

Empty/uneditable: the two controls that exist are editable and wired to chat chrome. The pane still *presents* as the Rail settings surface while most rail prefs are elsewhere or in a second store.

### System (`SystemPane`)

| Claim | What code actually does |
|-------|-------------------------|
| Local database facts, refresh on open | `useQuery` `['settings-local-store']`, `staleTime: 0`, `refetchOnMount: 'always'`, `retry: false`. |
| Size / location / conversations / messages | Rendered in a `<dl>`. Path is home-relative; copy avoids Django / sqlite / ORM (REQ-56). |
| Missing store | `0` / “not created yet” — **intended** (#377 Success #4). Backend `local_store_facts()` never raises into the client. |
| Failed `GET /v1/system/` (network, 5xx, 401) | `storeQuery.isError \|\| !storeQuery.data ? EMPTY_LOCAL_STORE`. **Same paint as missing store.** No alert, no retry. Vitest **locks** this (`shows 0 and not created yet when the local store is missing` uses `fetch` reject). |
| Edit / export / vacuum / open folder | **None.** Read-only by REQ-56. Not HIGH by itself. |

Empty/uneditable: on a healthy API the facts are visible and honestly read-only. On any fetch failure the pane is **empty-looking and unrecoverable**.

---

## HIGH findings

Three child Issues for CoS (drafts at the bottom). Suggested first wave (2–3): **all three** (chrome host + System empty-on-error + Rail avatar split). They do not overlap sibling Settings sections.

### C-H1 — Two Settings sheets; the unmounted one has no Rail/System and drops section deep-link

| Field | Value |
|-------|--------|
| **Severity** | HIGH |
| **File / area** | `webui/frontend/src/App.tsx`; `components/SettingsSheet.tsx`; `components/overlays/SettingsSheet.tsx`; `components/overlays/ChatOverlays.tsx`; `lib/chromeOverlay.ts`; `SearchPalette.tsx`; `App.overlays.test.tsx`; `e2e/overlays.spec.ts`; `overlays/__tests__/SettingsSheet.test.tsx` |
| **Evidence** | Live product: `App` mounts `components/SettingsSheet` and listens for `swarm:open-settings` **with** `detail.section`. Search “Settings” calls `openChromeOverlay('settings')` — same event string, **no section**. Compact `+` is Compact-only; the gear is the in-chat opener. `ChatOverlays` is **never imported**. If it were mounted (tests and leftover docs still assume it), `onSettings = () => openSettings('retention')` **ignores** `OpenSettingsDetail`, and the twin sheet has **no Rail / System nav**. Twin tests still assert Hermes / OMB / Rakazo placeholders and “Computer control”. `App.overlays.test.tsx` clicks Add → Settings / Teams and `openChromeOverlay('hidden' \| 'role' \| 'computer-control')` — App does not host those sheets. `e2e/overlays.spec.ts` same Compact path. Live e2e that *does* match product: `e2e/settings-sheet.spec.ts` (gear) and `e2e/chrome.spec.ts` (no Settings menuitem). Deep-link: `rg` finds **no** `section: 'rail'` or `section: 'system'` in `*.{ts,tsx}`. Type allows it; nothing launches it. |
| **Suggested fix Issue title** | One Settings host; deep-link Rail/System; stop testing the unmounted sheet (REQ-188 / #644) |
| **Test** | **Theatre / missing.** Twin Vitest + `overlays.spec.ts` + `App.overlays.test.tsx` lock a dead IA. No App-level test that `openSettingsSheet({ section: 'rail' \| 'system' })` activates those nav buttons. Gear e2e clicks Rail/System only *after* opening the sheet. |
| **Coordinate** | #364 leftover. Do not remount `ChatOverlays` as the fix. Delete or quarantine the twin. |

### C-H2 — System paints fetch/auth failure as an empty store

| Field | Value |
|-------|--------|
| **Severity** | HIGH |
| **File / area** | `SystemPane` in `components/SettingsSheet.tsx`; `EMPTY_LOCAL_STORE` / `fetchLocalStore` in `lib/api.ts`; locked by `components/__tests__/SettingsSheet.test.tsx`; backend already maps *collection* exceptions to empty in `system_views.py` |
| **Evidence** | `#377` Success #4 is **missing/empty store**, not “any error”. `SystemPane` uses `facts = storeQuery.isError \|\| !storeQuery.data ? EMPTY_LOCAL_STORE : storeQuery.data`. `apiGet` throws on non-OK (including 401/403 via `ApiAuthError`). The pane then shows Size/Location “not created yet” and Conversations/Messages `0`, with no alert and no retry. Operators cannot tell “fresh machine” from “API down / logged out”. The Vitest case named “when the local store is missing” **rejects** `fetch` and asserts the empty copy — it encodes the hole. e2e only stubs a happy `GET /v1/system`. |
| **Suggested fix Issue title** | Settings System must not look empty when /v1/system/ fails (REQ-188 / #644) |
| **Test** | **Weak.** Happy-path Vitest + e2e. Error path asserts empty paint. No test that 500/401 shows a warning and keeps retry. |
| **Coordinate** | Closed #377 — do **not** reopen “say Django” or add connection strings. Keep missing-store empty. Split **error** from **not created**. |

### C-H3 — Settings → Rail avatar theme unified with /agents (RESOLVED)

| Field | Value |
|-------|--------|
| **Severity** | HIGH (Resolved in #662) |
| **File / area** | `AvatarThemePicker.tsx`; `lib/avatarTheme.ts` (`swarm_avatar_theme`, blobs/bland/default); `components/AgentAvatar.tsx`; `types/agent.ts`; `lib/agent-store.ts` (`swarm_avatar_theme`); `components/AgentSidebar/AgentAvatar.tsx`; `pages/AgentRouterPage.tsx` |
| **Resolution** | Unified on `swarm_avatar_theme` as the single store of truth. `agent_avatar_theme` eliminated. Settings Rail theme changes synchronize live with Agent Router and rail faces via `AVATAR_THEME_SET_EVENT`. When Bland is chosen, both chat and `/agents` faces fall back to bland static circles. Custom uploaded faces always win. |
| **Test** | `agent-store.test.ts`, `avatarTheme.test.ts`, `components/AgentSidebar/__tests__/AgentSidebar.test.tsx`. |

---

## MEDIUM (do not file unless CoS wants them)

### C-M1 — RailPane is a caption plus two prefs; width/order/Hidden are not here

Copy promises drag / Hidden / Favourites. Those work on the rail, not in Settings. `swarm_rail_width` has no Settings reset. Bump + Bland **are** wired (not empty). Incomplete surface, not a broken toggle.

### C-M2 — No URL / hash deep-link; refresh closes Settings

`/chat?settings=rail` does not exist. Event deep-link is the only API. Search has no Rail/System actions. Survives if C-H1 adds Search rows + optional query.

### C-M3 — Settings → Hostname is write-only (sibling section; overlap)

`saveHostnameOverride` → `swarm_hostname_override`. `rg` consumers are the Hostname pane, its tests, and a REQ-72 source lock that **asserts the keys stay different**. Rail footer uses `swarm_hostname`. Saving Settings → Hostname does not change the visible rail label. Out of Rail/System nav, but the same “Settings write, product ignores” smell. Coordinate #579; let the hostname-section agent own the Issue if they also flag it.

### C-M4 — Live close does not notify `swarm:overlay-closed`

Only the unmounted twin notifies. No Chat listener today. Harmless until someone remounts the twin or wires composer restore to that event.

---

## LOW

- Nav label “Show LLM profiles” vs pane heading “LLM profiles”.
- Eight nav buttons stack above the pane on narrow viewports (`flex-col` + `border-b`); content can sit below the fold. Buttons still work.
- `definitionKind` / `definitionId` omitted from the live sheet `useEffect` deps (sibling Definition surface).
- `overlays/` Computer control / Role / placeholder remotes — dead IA, covered by C-H1.
- Operator dump `<a href="/settings/">` still ejects to Django (by design).

---

## Test quality scorecard

| Check | Verdict |
|-------|---------|
| Live sheet lists Rail + System | **Good.** Vitest + `e2e/settings-sheet.spec.ts`. |
| Bump toggle persist | **Good.** Vitest + `settingsPrefs.test.ts`. Sidebar listens (own tests). |
| Avatar Bland persist on chat rail | **Good.** `avatarTheme.test.ts` + e2e select `bland` → `swarm_avatar_theme`. |
| System happy path + no “Django” | **Good.** Vitest + e2e stub + Django view tests. |
| System error ≠ empty | **Theatre.** Vitest locks empty-on-reject. |
| `openSettingsSheet({ section: 'rail' \| 'system' })` | **Missing.** |
| Twin `overlays/SettingsSheet` | **Theatre.** Still in the Vitest tree; IA is not mounted. |
| Compact `+` → Settings / Teams | **Theatre.** `App.overlays.test.tsx`, `e2e/overlays.spec.ts` vs live Compact-only menu. |
| Overlay bus hidden / role / computer-control via `App` | **Missing / would fail.** `ChatOverlays` unmounted; App does not listen. |

Frontend CI on this repo often does not gate Vitest (REQ-171 C-H9). Do not treat a green visual job as coverage of this file.

---

## HIGH Issue drafts (CoS to file)

`gh` is read-only on this agent. File as children of [#644](https://github.com/matthewhand/open-swarm/issues/644). No `Fixes #644` from implementer PRs until triage is done.

### Issue 1 — One Settings host + Rail/System deep-link (C-H1)

**Title:** One Settings host; deep-link Rail/System; stop testing the unmounted sheet (REQ-188 / #644)

**Intent:** There is one Settings sheet. Every section in its nav, including Rail and System, can be opened from Search and from `openSettingsSheet({ section })`. Tests lock that sheet, not the leftover twin.

**Success:**

1. `App` remains the only Settings host (`components/SettingsSheet`). `ChatOverlays` / `overlays/SettingsSheet` are deleted or quarantined so they cannot remount and steal `swarm:open-settings`.
2. `openSettingsSheet({ section: 'rail' })` and `{ section: 'system' }` open the sheet with that nav `aria-current="page"` and the matching heading. Same for existing sections (do not regress definition / blueprint / remotes / llm-profiles).
3. Search Actions includes Rail and System rows (or a Settings row that accepts a section). Compact `+` stays Compact-only unless product explicitly puts Settings back.
4. Tests that click Add → Settings / Teams, or that assert Hermes/OMB/Rakazo placeholders / Computer control **as Settings nav**, are updated or removed. Add an App-level test for rail + system deep-link.
5. Optional: `/chat?settings=rail` (and `system`) opens the sheet; closing clears the query. Not required if Search + event cover it.

**Constraints:** Look-only audit already landed — this is the implementer ticket. Do not remount `ChatOverlays`. Do not fight #576–#579. No Neon. No secrets. Chat stays mounted (sheet overlay).

**Owner:** CoS assigns (wave 1).

**Parent:** #644. Evidence: C-H1.

---

### Issue 2 — System error ≠ empty store (C-H2)

**Title:** Settings System must not look empty when /v1/system/ fails (REQ-188 / #644)

**Intent:** Operators can tell a missing local store from a failed System fetch. Missing store stays `0` / “not created yet”. Errors are visible and retryable.

**Success:**

1. `SystemPane` does **not** map `storeQuery.isError` to `EMPTY_LOCAL_STORE`.
2. Failed `GET /v1/system/` (5xx, network, 401/403) shows a warning (no Django / sqlite / ORM / connection strings) and a retry. Counts/path are omitted or clearly “unavailable”, not `0` / “not created yet”.
3. Happy missing store (`created: false`, 200) still shows `0` / “not created yet” (#377 Success #4).
4. Tests: reject/500/401 ≠ empty copy; 200 + `created: false` still empty; copy still has no “Django”.

**Constraints:** Keep the pane read-only (no vacuum/export in this ticket). No secrets in the path. Do not reopen #377’s “do not say Django” as a new REQ. Coordinate backend empty-on-exception only if the implementer wants a 5xx instead of a 200 empty body — frontend must still handle both.

**Owner:** CoS assigns (wave 1 with Issue 1 if capacity).

**Parent:** #644. Evidence: C-H2.

---

### Issue 3 — One avatar-theme store (C-H3)

**Title:** One avatar-theme store for Settings → Rail and /agents (REQ-188 / #644)

**Intent:** Settings → Rail → Avatar theme is the avatar theme the user sees on every rail that Settings can reach. One persist key. One picker.

**Success:**

1. Chat rail (`components/AgentAvatar`) and Agent Router faces read the **same** preference Settings → Rail writes.
2. Either (a) Settings exposes the ten packs + Bland/Blobs in one control, or (b) `/agents` drops the ten-pack picker and uses Blobs/Bland only — pick one IA, document it in the pane copy.
3. Legacy `default` → bland migration stays.
4. Tests: change Settings → Rail, assert both chat rail and `/agents` default face follow; no second silent key.

**Constraints:** Do not persist two keys in #579. Custom uploaded faces still win. No Neon.

**Owner:** CoS assigns (wave 1 or 2).

**Parent:** #644. Evidence: C-H3.

---

## Out of scope / honesty

- No runtime product change in this PR.
- No `Fixes` / `Closes` on #644.
- No secrets, no Neon, no live LAN, no host bounce.
- Did not audit Definition / Blueprints / Remotes / Retention / Hostname / LLM profiles except where they share chrome or a write-only key (C-M3).
- Did not recapture screenshots or run Playwright.
- Did not re-file REQ-171 rail-catalog HIGHs (#599 / #606–#608).
- BrowserControl is not linked from the live Settings nav.
