# QA wave 1 — leftover SPA / webui debt (look-only)

> **Look-only.** This file re-reads [`docs/debt/webui.md`](webui.md) (REQ-22a,
> merged as #325) against **today’s** SPA. It does not rewrite the app, edit
> existing debt docs, or file new Issues. No product diffs live in the PR that
> added this file.

**As-of:** `origin/main` @ `841e953c` (`feat(pinokio): REQ-47 local sideload launcher (#375)`).

**Starting audit:** [`docs/debt/webui.md`](webui.md) scored the tree at
`91dabd64` (REQ-5 dark chrome, #307). Later chrome / settings / Teams work
landed on `main` after that audit: Grok left-rail (#322), DaisyUI `modal-end`
settings sheet (#320), teams in the AGENTS rail (#331), hover-edit Blueprint
(#334), Hidden seed/drag (#335 / #342), computer-control stub (#341), CoS +
teams-of-teams (#345), nested Compact (#365).

**Method:** static re-read of `webui/frontend/src/**/*.{ts,tsx,css}`, e2e
locks, and open Issues **#336–#416**. No host bounce. No Neon. No secrets.
No live LAN URLs.

**How to read**

| Rank | Meaning here |
|------|----------------|
| **must-fix** | Still true on today’s Grok chrome, and it fights the live IA (overlays, URL selection, or CI locking a dead catalog). |
| **nice** | Still true, but dead weight / polish. Safe to leave until a cleanup slice. |
| **obsolete** | No longer true: shipped by a later merged PR, or the original path/behavior is gone. |

Severity inside a rank reuses the original P0/P1/P2 scale from
[`webui.md`](webui.md).

**Do not fold this into PR 344.** PR 344 is a product chrome PR
(`REQ-29–41`). This file is documentation only.

---

## Today’s SPA snapshot (what #325 described vs what shipped)

| Surface | #325 tree (`91dabd64`) | Today (`841e953c`) |
|---------|------------------------|--------------------|
| Shell | `App.tsx` sticky Primary top-nav + five-tab dock | Left rail + chat-only main. No Primary nav, no dock. Gear / Search / Settings are **overlays** on `App`. |
| Home | Routed `Dashboard.tsx` (four action cards) | `/` and `/chat` both mount `ChatPage`. `Dashboard.tsx` is **unmounted**. |
| Chat | Header `<select>` wrote local `selectedBlueprint` | Selection is `?blueprint=` / `?team=` via `useSearchParams`. Header select is the **team-member** dropdown only. |
| Agents | Sidepane + hide/unhide | Rail: Search, pins, Support-first list, teams (#331/#345), Hidden drop (#342), Plugins, hostname. |
| Settings | Full-page hop to Django | DaisyUI `modal` + `modal-end` sheet (#320). Hover-edit opens Blueprint section (#334). |
| Launchers | Experimental ⌘K `CommandPalette` only | **Two** launchers: default-ON experimental ⌘K **and** product `SearchPalette`. |
| DaisyUI | 6 live primitives; Modal unused | Settings sheet mounts `Modal` / `Input` / `Alert` / `Button` / `Toast`. Kit museum remains. |

Live DaisyUI imports **today** (pages/components, not tests, not the kit itself):

- `App.tsx` → `ToastProvider`
- `ChatPage.tsx` → `LoadingDots`, `useToast`
- `SettingsSheet.tsx` → `Alert`, `Button`, `Input`, `Modal`, `useToast`
- `Dashboard.tsx` → `Badge`, `Card` (**unmounted**)

---

## Must-fix (still true)

### M1 — Two command palettes; the experimental one is still an operator catalog

| Field | Value |
|-------|--------|
| **Rank / sev** | must-fix / P1 (was [`webui.md`](webui.md) P1-6 + P1-7) |
| **Still-true?** | **Yes — worse.** Product Search shipped; the experimental catalog was not deleted. |
| **Path** | `webui/frontend/src/experimental/CommandPalette.tsx`; `webui/frontend/src/experimental/flags.ts`; `webui/frontend/src/App.tsx` (mounts both); `webui/frontend/src/components/SearchPalette.tsx` |
| **Why** | `isExperimentalEnabled` still defaults **ON** and is read once at module load. `App` mounts `CommandPalette` **and** `SearchPalette`. Rail Search opens the product overlay (`e2e/chrome.spec.ts`). ⌘K still opens the experimental catalog whose items are Home / Chat / Blueprints / My Blueprints / Launch / Teams / Sessions — leftover operator IA. `choose()` SPA-navigates only paths starting `/chat`; **Home (`/`)** still does `window.location.assign('/')` (full reload of the chat SPA). Search Actions also hop to `/blueprint-library/`, `/teams/launch/`, `/settings/` via `window.location.assign`. |
| **Later PRs** | #322 shipped the rail Search overlay. It did **not** promote-or-delete `experimental/`. |
| **Open Issue** | **Do not re-file.** Overlaps **#364** (REQ-48: chat stays the main view; manage/settings are popups). Open PR **#383** already targets #364. The leftover dual-launcher + default-ON flag is **not** its own ticket in #336–#416. |

### M2 — Search / Manage Teams still eject the operator out of chat

| Field | Value |
|-------|--------|
| **Rank / sev** | must-fix / P0 (new leftover after #320/#322/#331; original P0-2 chrome is gone) |
| **Still-true?** | **Yes** for those entry points. Settings **gear** and hover-edit are overlays. |
| **Path** | `webui/frontend/src/pages/ChatPage.tsx` (`MANAGE_TEAMS_HREF = '/teams/'`, `window.location.assign`); `webui/frontend/src/lib/teamRosters.ts` L15; `webui/frontend/src/components/SearchPalette.tsx` L91–110, L147–148; `webui/frontend/src/experimental/CommandPalette.tsx` L67–77, L131–134 |
| **Why** | Today’s intended IA is “chat always mounted; manage/settings are overlays” (`App.tsx` comment; Settings sheet; Search overlay; Hidden/Plugins dialogs). The **gear** dispatches `swarm:open-settings`. Search’s Settings row still assigns Django `/settings/`. The team-member `<select>` “Manage Teams” option assigns `/teams/`. Those are full-page hops that unmount the React tree. |
| **Later PRs** | #320 sheet + #322 chrome + #331 member dropdown shipped the overlay path **and** left the Django ejects. |
| **Open Issue** | **Do not re-file.** This **is** **#364** / PR **#383**. Related product tickets (do not file as debt): **#382** / PR **#404** (agent editor scoped), **#377** / PR **#397** (Settings System section). |

### M3 — Unmounted Dashboard + a Vitest lock that still treats Home as a catalog

| Field | Value |
|-------|--------|
| **Rank / sev** | must-fix / P1 (was P0-1 + P1-5) |
| **Still-true?** | **Partly.** The *e2e* sacred-catalog lock is **gone**. The *page + unit test* remain and will fight delete/rewrite. |
| **Path** | `webui/frontend/src/pages/Dashboard.tsx`; `webui/frontend/src/pages/__tests__/Dashboard.test.tsx`; `webui/frontend/src/index.css` `.os-action-card*`; `webui/frontend/src/experimental/README.md` (still documents 30s Dashboard polling) |
| **Why** | `App.tsx` routes `/`, `/chat`, `/chat/*` → `ChatPage`. `Dashboard` is imported **only** by its own test. That test still asserts four `os-action-card` links (Launch Team / Browse Blueprints / Manage Teams / Settings) with Django hrefs. Dashboard still raw-fetches `/v1/blueprints` + `/v1/models` + `/v1/teams/` on a distinct `['dashboard-stats']` key every 30s — dead, but CI-sacred. Meanwhile `e2e/chrome.spec.ts` and `e2e/nav.spec.ts` correctly assert **no** Primary nav, **no** Home/Chat links, **no** Dashboard heading on unknown paths. |
| **Later PRs** | #322 inverted the e2e IA lock. It did not delete `Dashboard.tsx`. |
| **Open Issue** | **None in #336–#416.** Do not file a “restore Home catalog” ticket. A later debt slice can delete the unmounted page + test. |

### M4 — Three Team-roster clients after REQ-23 / REQ-28

| Field | Value |
|-------|--------|
| **Rank / sev** | must-fix / P1 (new leftover; evolved from P1-3 / P1-5) |
| **Still-true?** | **Yes.** Live rail + chat share `teamRosters.ts`. Two other copies sit beside it. |
| **Path** | `webui/frontend/src/lib/teamRosters.ts` (AgentSidebar + ChatPage); `webui/frontend/src/lib/teamRoster.ts` (REQ-28 nest/parse, tests only from pages); `webui/frontend/src/lib/api.ts` `fetchTeamRosters` / `TeamRosterRecord` (no page import) |
| **Why** | Sidepane and the member dropdown load via `teamRosters.fetchTeamRosters` (`/team_rosters.json` then `/v1/team-rosters/`, demo stub fallback, raw `fetch`, no auth-error path). `api.ts` also exports a typed `GET /v1/team-rosters/` that nobody calls. `teamRoster.ts` is a third `TeamRoster` shape (`kind` union, `wires`, `source`). Counts and member kinds can disagree with a future Settings/Teams overlay that uses the typed client. |
| **Later PRs** | #331 / #345 added the extra copies; they did not collapse them. |
| **Open Issue** | **None in #336–#416** as a debt ticket. Do not re-file as a Teams product REQ. Composition product work is #345 (merged) and remotes/scale-out Issues (#380, #387–#390, #393–#394, #398) which are **not** this cleanup. |

---

## Nice (still true, not blocking chrome)

### N1 — DaisyUI museum is smaller, not gone

| Field | Value |
|-------|--------|
| **Rank / sev** | nice / P1 (was P1-1, P1-2, P2-6, P2-8) |
| **Still-true?** | **Yes, narrowed.** Modal / Input / Toast / Alert / Button are live. Tabs / Pagination / Select / Textarea / FormValidation / Card (except unmounted Dashboard) / ConfirmModal / extra Loading* are still tests-only. |
| **Path** | `webui/frontend/src/components/DaisyUI/*` (~2,630 lines); `__tests__/{A11y,Modal,Tabs,Pagination,Button}.test.tsx`; `index.ts` barrel + `FormValidation.tsx` `'./'` cycle |
| **Why** | #320 mounted the sheet on `Modal`. FEATURE_STATUS still lists the 13-component kit as 🔲. Deleting Tabs/Pagination still fails CI. `Button` `variant`/`color` overlap and dead `active`/`disabled` aliases are unchanged. |
| **Open Issue** | **None in #336–#416.** Do not file “add Tabs to chat.” |

### N2 — `api.ts` is still mostly the deleted Builder/operator client

| Field | Value |
|-------|--------|
| **Rank / sev** | nice / P1 (was P1-3) |
| **Still-true?** | **Yes, narrowed.** Live callers now also include Settings + Herdr. |
| **Path** | `webui/frontend/src/lib/api.ts` (543 lines) |
| **Why** | Live: `fetchBlueprints`, `fetchModels`, `fetchBlueprintSource`, `fetchHerdrAgents`, `apiGet`/`apiPost` (via `agentChat.ts`). Unused by any page: `fetchTeams` / `createTeam` / `deleteTeam`, library CRUD, `generateAgentCode` / `validateAgentCode` / `ensureCsrfCookie`, custom-blueprint CRUD, `fetchServerSettings` / `fetchEnvironmentVariables`, `fetchCliAgents` / `fetchConfigOptions` / `fetchBlueprintTools`, plus unused `fetchTeamRosters` (see M4). `AUTH_ERROR_EVENT` is still dispatched with **no listener** (ChatPage auth toast is WS `4401`, not this event). Comment still says “SPA Settings token UI was deleted.” Herdr comment still says the DaisyUI sheet “is not in this tree.” |
| **Open Issue** | **None in #336–#416.** Remotes Issues (#384, #387–#390) are product add/list/send, not `api.ts` trim. |

### N3 — Builder leftover pure libs (ADR-001 still says panels are gone)

| Field | Value |
|-------|--------|
| **Rank / sev** | nice / P1 (was P1-4) |
| **Still-true?** | **Yes.** |
| **Path** | `webui/frontend/src/lib/{inferenceProfile,toolCapabilities,skills}.ts` + matching `__tests__` |
| **Why** | Still no page import. Vitest-only JS copies of Python `swarm.core.*`. |
| **Open Issue** | **None in #336–#416.** |

### N4 — Experimental Copy/Retry is default-ON with no ChatPage test

| Field | Value |
|-------|--------|
| **Rank / sev** | nice / P2 (was P1-6 + P2-10) |
| **Still-true?** | **Yes.** |
| **Path** | `webui/frontend/src/experimental/ChatMessageActions.tsx`; `ChatPage.tsx` `SHOW_MESSAGE_ACTIONS`; `pages/__tests__/ChatPage.test.tsx` (no Copy/Retry cases) |
| **Why** | Same theater as M1’s flag wrapper. **#366** (REQ-49: edit any API-agent message) is a **different** product surface (edit, not Copy/Retry). Do not treat N4 as #366. |
| **Open Issue** | Do not re-file as #366. No debt Issue in range. |

### N5 — Dual lockfiles + stale frontend README

| Field | Value |
|-------|--------|
| **Rank / sev** | nice / P2 (was P2-3) |
| **Still-true?** | **Yes.** |
| **Path** | `webui/frontend/package-lock.json` + `pnpm-lock.yaml`; `webui/README.md` (`tailwind.config.js` still listed; “`/` (dashboard) and `/chat`”; “All DaisyUI components are available”) |
| **Why** | CI/build still uses `npm ci` (`scripts/build_frontend.sh`). README still describes the pre-#322 tree. |
| **Open Issue** | **None in #336–#416.** |

### N6 — Unused toolchain leftovers (narrowed)

| Field | Value |
|-------|--------|
| **Rank / sev** | nice / P2 (was P2-4) |
| **Still-true?** | **Partly.** |
| **Path** | `webui/frontend/package.json` (`@types/jest`); `vite.config.ts` `/marketplace`, `/team-creator` |
| **Why** | `@types/jest` still unused (Vitest). `/marketplace` and `/team-creator` proxies remain; SPA has no those routes. **`axe-core` is no longer unused** — `webui/frontend/scripts/a11y-audit.mjs` resolves it. Vite comment still says `/health` is “fetched by the Dashboard status card.” |
| **Open Issue** | **None in #336–#416.** |

### N7 — `agentMarkColor` still unused in the UI

| Field | Value |
|-------|--------|
| **Rank / sev** | nice / P2 (was P2-5) |
| **Still-true?** | **Yes.** |
| **Path** | `webui/frontend/src/lib/hiddenAgents.ts` L119–137; `index.css` `.os-agent-dot[data-mark]` / `.os-search-row__icon[data-mark]` |
| **Why** | Rail and Search still use `agentMarkIndex` + CSS. `agentMarkColor` is only asserted in `hiddenAgents.test.ts`. Hex tables remain duplicated (TS vs CSS). |
| **Open Issue** | **None.** Avatar product work is **#346** / **#386** / **#398** / **#355** — do not file a color-helper ticket as those. |

### N8 — Single-line composer remains

| Field | Value |
|-------|--------|
| **Rank / sev** | nice / P2 (was P2-7) |
| **Still-true?** | **Yes** (product gap, not unused code). |
| **Path** | `webui/frontend/src/pages/ChatPage.tsx` (`<input type="text" className="os-composer__input">`); unused `DaisyUI/Textarea.tsx` |
| **Why** | Composer is now the Compact pill (`+` / Compact / Message / mic, #365) but still a single-line `<input>`. Do **not** wire unused `Textarea` “just because.” |
| **Open Issue** | **#351** is **attach files** via `+` and drag-drop — not “multiline composer.” Do not re-file P2-7 as #351. |

### N9 — Theme / drawer state still lives on `App`

| Field | Value |
|-------|--------|
| **Rank / sev** | nice / P2 (was P2-2) |
| **Still-true?** | **Yes**, and `App` now also holds Search + Settings overlay state. |
| **Path** | `webui/frontend/src/App.tsx` (`darkMode`, `sidebarOpen`, `searchOpen`, `settingsOpen`); `AgentSidebar.tsx` `renderAgentRow` (not memo) |
| **Why** | Toggling theme or opening Search/Settings re-renders `ChatPage`. WS state is still refs (no reconnect). Not a correctness bug. |
| **Open Issue** | **None.** **#374** is mobile rail tuck/swipe — product, not this extract. |

### N10 — DaisyUI v4 leftover `:root` tokens

| Field | Value |
|-------|--------|
| **Rank / sev** | nice / P2 (was P2-1) |
| **Still-true?** | **Yes.** |
| **Path** | `webui/frontend/src/index.css` L73–80 (`--animation-btn`, `--btn-text-case`, `--tab-border`, …) |
| **Why** | DaisyUI 5 themes above already set `--color-*` / `--radius-*`. No live Tabs. `--os-chrome-sidebar` **is** used — keep it. `.os-action-card*` is now only needed by the unmounted Dashboard (see M3). |
| **Open Issue** | **None in #336–#416.** |

### N11 — `/` and `/chat` are two `ChatPage` route elements (remount on hop)

| Field | Value |
|-------|--------|
| **Rank / sev** | nice / P2 (new leftover after #322) |
| **Still-true?** | **Yes.** Overlays stay mounted; the chat **route** is not a single keep-alive. |
| **Path** | `webui/frontend/src/App.tsx` L132–138 |
| **Why** | Settings / Search / experimental palette are siblings of `<Routes>`, so they do not unmount chat when opened. Navigating `/` ↔ `/chat` still matches two different `<Route element={<ChatPage />}>` nodes and remounts the page. Sidebar links go to `/chat?blueprint=…`, so the common path is fine. CommandPalette Home’s full reload (M1) is the sharp edge. |
| **Open Issue** | Covered by **#364** if someone treats remount-on-`/` as the bug. Do not file a third “keep-alive” ticket. |

---

## Obsolete (shipped or no longer true)

### O1 — Leftover top-nav + mobile dock vs intended Grok chrome

| Field | Value |
|-------|--------|
| **Was** | [`webui.md`](webui.md) P0-2 |
| **Status** | **Obsolete — shipped.** |
| **Evidence** | `App.tsx` L48–54, L114–139: left rail + `ChatPage` only. `e2e/chrome.spec.ts` L62–80 asserts `navigation[name=Primary]` count 0, no Home/Chat links. Merged **#322**. |
| **Do not re-file** | **#364** is the *remaining* overlay contract, not “put the top-nav back.” |

### O2 — Chat blueprint `<select>` and AgentSidebar did not share a source of truth

| Field | Value |
|-------|--------|
| **Was** | P0-3 |
| **Status** | **Obsolete — shipped.** |
| **Evidence** | `ChatPage.tsx` L97–102 derives `selectedBlueprint` / `teamFromUrl` from `useSearchParams` every render (not a one-shot `useState`). AgentSidebar L96–101 reads the same params. Header `<select>` is team members (#331), not a second blueprint picker. Default Support is written **into the URL** (`setSearchParams`). |
| **Residual** | Member target is still local state (`memberTarget`), not a search param. That is a Teams UX leftover, not the original P0-3 bug. Do not re-file P0-3. Related product: **#362** (bubble-less line when a dropdown changes). |

### O3 — e2e / nav tests treat Home + Agents catalog as sacred

| Field | Value |
|-------|--------|
| **Was** | P0-1 (e2e half) |
| **Status** | **Obsolete for e2e.** The unit-test half remains as M3. |
| **Evidence** | `e2e/chrome.spec.ts` L78–80, L132; `e2e/nav.spec.ts` L16–31; `App.routes.test.tsx` L74–75; `AppSettingsChrome.test.tsx` all assert **against** Primary / Home / Chat catalog chrome. `AgentSidebar.test.tsx` now locks rail / Hidden / teams, not a six-item top-nav. |
| **Later PRs** | #322, #331, #335, #342, #345. |

### O4 — Sidebar footer duplicates Teams/Settings already in top-nav

| Field | Value |
|-------|--------|
| **Was** | P2-9 |
| **Status** | **Obsolete.** Top-nav is gone; footer is Plugins + hostname. |
| **Evidence** | `AgentSidebar.tsx` L733–763. Hostname product leftover is **#372** (bland vs red on WS drop), not a Teams/Settings duplicate. |

### O5 — `focus-trap-react` exists only for unmounted Modal

| Field | Value |
|-------|--------|
| **Was** | P1-8 |
| **Status** | **Obsolete.** Modal is mounted by SettingsSheet (#320). Computer-control stub (#341) uses a native `<dialog>`, not this wrapper. |
| **Evidence** | `SettingsSheet.tsx` imports `Modal`; `DaisyUI/Modal.tsx` imports `focus-trap-react`. Do not delete the dep with the museum until Modal itself is replaced. |

### O6 — Dashboard re-fetches the live catalog the sidebar already loads

| Field | Value |
|-------|--------|
| **Was** | P1-5 as a *live* dual-stack bug |
| **Status** | **Obsolete as a live bug** (Home is not routed). **Still true as museum** — see M3. |
| **Evidence** | No `import Dashboard` outside `Dashboard.test.tsx`. Sidebar + Chat + Search share `queryKey: ['blueprints']` + `fetchBlueprints`. |

### O7 — Settings is only a Django full-page hop (from REQ-22b, not 22a)

| Field | Value |
|-------|--------|
| **Was** | [`django-spa-overlap.md`](django-spa-overlap.md) Settings noun / “no sheet” |
| **Status** | **Obsolete for the SPA gear.** Sheet shipped **#320**; Blueprint hover-edit **#334**. |
| **Residual** | Search/CommandPalette Settings rows still hop (M2). Django `/settings/` remains the operator dump by design. **#377** / **#382** / **#384** are product Settings sections, not “the sheet is missing.” |

---

## Original `webui.md` scorecard

| ID | Original one-liner | Today | Rank here |
|----|-------------------|-------|-----------|
| P0-1 | Tests treat Home + Agents catalog as sacred | e2e inverted; Dashboard unit test remains | M3 + O3 |
| P0-2 | Leftover top-nav + mobile dock | Grok rail shipped (#322) | O1 |
| P0-3 | Blueprint select vs sidebar URL desync | URL is the source of truth | O2 |
| P1-1 / P1-2 / P2-6 / P2-8 | DaisyUI museum + sacred tests | Modal/Input/Toast live; rest museum | N1 |
| P1-3 | `api.ts` Builder/operator client | Narrowed; still mostly unused | N2 |
| P1-4 | Builder leftover pure libs | Unchanged | N3 |
| P1-5 | Dashboard dual catalog fetch | Unmounted; test still locks it | M3 + O6 |
| P1-6 | Experimental flags default ON | Still true; now two palettes | M1 + N4 |
| P1-7 | CommandPalette operator catalog + broken Home | Still true next to SearchPalette | M1 |
| P1-8 | `focus-trap-react` only for dead Modal | Modal live | O5 |
| P2-1 | DaisyUI v4 `:root` tokens | Unchanged | N10 |
| P2-2 | Theme/drawer on App re-renders chat | Unchanged (+ overlay state) | N9 |
| P2-3 | Dual lockfiles + stale README | Unchanged (README *more* stale) | N5 |
| P2-4 | axe-core / `@types/jest` / dead proxies | axe-core now used; rest remains | N6 |
| P2-5 | `agentMarkColor` unused | Unchanged | N7 |
| P2-7 | Single-line composer | Unchanged (Compact pill still `<input>`) | N8 |
| P2-9 | Sidebar footer Teams/Settings | Replaced by Plugins + hostname | O4 |
| P2-10 | Copy/Retry has no page test | Unchanged | N4 |

---

## Open Issues #336–#416 — do not re-file as this debt

These are **product REQs**, not a second copy of [`webui.md`](webui.md). Cite them so a cleanup PR does not open duplicates.

| Issue | Title (short) | Relation to leftover debt |
|-------|----------------|---------------------------|
| **#336** | streaming bubble tail, quiet role chrome, last-message sidebar | Product chrome. Not P0-2. Open PR 344 — do not fold debt into it. |
| **#337** | Hidden-agents popup fits the display | Hidden dialog in `AgentSidebar.tsx` is still a short centered card (`w-[20rem]`, no max-height/scroll). **Product**, not DaisyUI-museum. |
| **#338** | token count in the top navbar | Footer already has a token meter (`ChatPage` `os-chat-footer`). Product move, not “restore top-nav.” |
| **#339** | click-to-rename agent in the chat header | Product. Header is a `<h1>`, not an input. |
| **#340** | selected hidden agent appears in the rail until you leave | Product Hidden behavior. |
| **#346** | avatar theme sets | Product. Not N7. |
| **#347** | Hidden Bots row at list bottom + Grok-style popup | Product restyle of the existing `{n} hidden` control. Pair with #337. |
| **#351** | attach files via + and drag-drop | Product. **Not** N8 multiline composer. |
| **#353–#356** | timestamps / jump / working avatar / role-badge pane | Product. In PR 344’s stated range. |
| **#358 / #360** | default LLM + auto-list models | Settings product. Sheet already fetches `fetchModels`. |
| **#361** | Computer control bare-metal default | Stub shipped #341. Product follow-on. |
| **#362** | bubble-less transcript line when a dropdown changes | Touches the team-member `<select>` residual in O2. Product. |
| **#364** | chat stays the main view; manage/settings are popups | **Duplicates M1/M2/N11.** Open PR **#383**. |
| **#366** | edit any API-agent message | **Not** N4 Copy/Retry. Open PR **#391**. |
| **#367** | Support skill constraints | Product Support. |
| **#368** | persist CLI session ids | Not SPA debt. |
| **#369** | drag-reorder rail + bump-on-complete | Product. Open PR **#392**. |
| **#372** | hostname rail icon bland vs red on WS drop | Product on the hostname footer (O4). |
| **#374** | mobile rail tucks after select; swipe to reopen | Product. Open PR **#395**. Not N9. |
| **#377** | Settings System section — local store size | Product on the **existing** sheet. Open PR **#397**. |
| **#378** | Safety role tool-status badges | Product. |
| **#380** | nest open-swarm as a remote type | Product remotes. |
| **#382** | Agent editor is agent-scoped; Blueprint is a picker | Product split of hover-edit vs Settings. Open PR **#404**. |
| **#384** | Remotes are opt-in; OpenMousBot not OMB | Product. Open PR **#409**. |
| **#386** | selected-agent avatar in the header | Product. Open PR **#401**. |
| **#387–#390** | Hermes / OMB / Rakazo / Herdr remotes complete | Product remotes. |
| **#393–#394** | new chat per task; scale-out rail | Product. |
| **#396** | Role chrome is the badge only | Product restyle. Open PR **#403**. |
| **#398** | Stacked avatars for teams and remotes | Product. Open PR **#413**. |
| **#405** | Per-agent ordered inference list | Product. |
| **#407** | Info/status lines are UI-only | Product. |
| **#416** | PR-opened card | Product. |

Closed in-range (already shipped — do not reopen as debt): **#350** REQ-37 Compact (#365), **#348** REQ-36 software-dev (#357), **#363** REQ-47 Pinokio (#375).

---

## Suggested later slices (not this file, not PR 344)

Look-only. If someone files follow-up work, keep slices small and **prefer existing Issues**:

1. **Overlays over chat** — already **#364** / PR **#383**. Includes M1 Home full-reload, M2 Django ejects, N11 remount. Do not open a fourth PR.
2. **Delete unmounted Dashboard + its unit test** — M3. No existing Issue; file only if CoS wants a debt ticket.
3. **One roster client** — M4. Collapse `teamRosters.ts` / `teamRoster.ts` / unused `api.fetchTeamRosters`.
4. **Delete DaisyUI museum** — N1. Keep Modal/Input/Toast/Alert/Button/LoadingDots until a raw-class pass.
5. **Trim `api.ts` + Builder libs** — N2 + N3.
6. **Promote or delete `experimental/`** — M1 + N4. If Search stays, delete ⌘K catalog or point ⌘K at `SearchPalette`.

---

## What this audit did not do

- No app, test, CI, or existing `docs/debt/*.md` edits.
- No rebase, squash, or fold into PR 344 / #383 / other open chrome PRs.
- No host bounce, no Neon, no secrets, no live LAN URLs.
- No new GitHub Issues.
- Django operator templates / `agent_sidebar.js` were not re-scored (that remains [`django-spa-overlap.md`](django-spa-overlap.md) + [`core.md`](core.md) / [`tests-ci.md`](tests-ci.md)).
