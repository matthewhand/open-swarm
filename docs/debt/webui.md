# REQ-22a — React SPA technical debt (audit only)

> **Quoted REQ (do not treat this file as a rewrite ticket):**
>
> REQ-22a technical debt AUDIT ONLY. Do not rewrite the app. Do not open a
> feature PR unless you must; prefer a draft docs PR `docs/debt/webui.md` OR
> put the FULL ranked list in your final report (CoS will relay).
>
> Scope: `webui/frontend` React SPA only (ChatPage, Dashboard, AgentSidebar,
> DaisyUI wrappers, experimental CommandPalette).
> Look for: stale/unused components, duplicate chat/sidebar logic, dead
> experimental flags, inefficient re-renders, leftover top-nav vs intended
> Grok chrome, unused CSS, tests that assert the old Home+Agents catalog as
> sacred.
>
> For each finding: severity (P0/P1/P2), path, one-line why, suggested
> action (delete / extract / leave).
> Do not enable Neon/oracle. Do not deploy. starting tree is this ref.
> Quote this REQ.

**Starting tree:** `91dabd645d289ee539aa00bbe0721e1dc916b116`
(`feat(webui): REQ-5 dark chrome, large home cards, hide-from-sidebar (#307)`)

**Scope honored:** `webui/frontend` only. Django `agent_sidebar.js` / operator
templates are cited only as the *other half* of a duplicated contract — not
scored as in-scope work. Neon/oracle not touched. No app rewrite.

**Method:** static read of every `webui/frontend/src/**/*.{ts,tsx,css}` file,
import graphs (who imports DaisyUI / `api.ts` / Builder leftovers), e2e +
Vitest assertions that lock chrome, and the REQ-5 / ADR-001 comments already
in tree.

**Severity:**

| Sev | Meaning here |
|-----|----------------|
| **P0** | Blocks a Grok-chrome rewrite, or is a live source-of-truth bug on `/chat`. |
| **P1** | Dead weight / duplication that will fight the next chrome pass. |
| **P2** | Polish, unused CSS tokens, unused deps, inefficient but bounded re-renders. |

**Actions:** `delete` = safe to remove in a later debt PR · `extract` = pull
shared logic out before rewriting chrome · `leave` = keep until product
decides (or the lock is the intended contract).

---

## Ranked findings

### P0-1 — Tests treat the Home + Agents catalog as sacred

| Field | Value |
|-------|--------|
| **Sev** | P0 |
| **Path** | `webui/frontend/src/pages/__tests__/Dashboard.test.tsx`; `webui/frontend/e2e/chrome.spec.ts`; `webui/frontend/e2e/nav.spec.ts`; `webui/frontend/e2e/smoke.spec.ts`; `webui/frontend/src/components/__tests__/AgentSidebar.test.tsx` |
| **Why** | These tests hard-lock four Home action cards (Launch Team / Browse Blueprints / Manage Teams / Settings), `os-action-card` (not rainbow buttons), a visible `Primary` top-nav, “Blueprints\|Settings” chrome text, and a always-on Agents sidepane with hide/unhide. A Grok-first shell (chat as `/`, no catalog Home, no operator top-nav) fails this suite before any pixel changes. |
| **Action** | **extract** the *behavior* locks (hide persistence, theme, WS honesty) from the *IA* locks (four cards, six-item nav). Do not delete until a chrome ADR says Home is no longer a catalog. Out-of-scope but related: `tests/unit/test_screenshot_registry.py` (`Home · Chat · Blueprints · Teams · Sessions · Settings`) and FEATURE_STATUS / GUIDED_TOUR / SCREENSHOTS captions will also fail a rewrite. |

### P0-2 — Leftover top-nav + mobile dock vs intended Grok chrome

| Field | Value |
|-------|--------|
| **Sev** | P0 |
| **Path** | `webui/frontend/src/App.tsx` (sticky `<nav aria-label="Primary">` L67–113; five-tab dock L128–138); `webui/frontend/src/index.css` L6–10 (“Grok/OMB-like dark metal”) |
| **Why** | REQ-5 painted DaisyUI dark metal and added an Agents sidepane, but the **IA is still operator chrome**: desktop Home · Chat · Blueprints · Teams · Sessions · Settings, plus a mobile catalog dock. Grok chrome is sidebar + conversation, not a six-link top bar over a Dashboard catalog. Triple chrome (top-nav + Agents pane + dock) fights the comment in `index.css`. |
| **Action** | **leave** until a chrome decision; then **delete** the catalog top-nav/dock (Settings gear can stay). Do not “fix” by adding more nav. `Dashboard.tsx` QUICK_ACTIONS is the same leftover catalog in card form. |

### P0-3 — Chat blueprint select and AgentSidebar do not share a source of truth

| Field | Value |
|-------|--------|
| **Sev** | P0 |
| **Path** | `webui/frontend/src/pages/ChatPage.tsx` L71–77, L357–360; `webui/frontend/src/components/AgentSidebar.tsx` L32–34, L117–122 |
| **Why** | ChatPage initializes `selectedBlueprint` from `?blueprint=` **once** (`useState(() => searchParams.get('blueprint'))`) and never syncs. The header `<select>` writes local state only — not the URL. AgentSidebar highlights `searchParams.get('blueprint')` and navigates to `/chat?blueprint=<id>`. Same-route search-param changes do **not** remount ChatPage, so: (1) picking a blueprint in the header leaves the sidebar stale; (2) clicking an agent while already on `/chat` updates the URL but **not** the header/send payload. Duplicate picker + broken highlight. |
| **Action** | **extract** one `blueprint` search-param hook used by both ChatPage and AgentSidebar; delete the header `<select>` *or* the sidebar-as-picker (not both forever). |

---

### P1-1 — DaisyUI wrappers are a scaffold library, not the live UI

| Field | Value |
|-------|--------|
| **Sev** | P1 |
| **Path** | `webui/frontend/src/components/DaisyUI/*` (~2,602 lines); `webui/frontend/src/components/DaisyUI/index.ts` |
| **Why** | Live pages import only `Alert`, `Badge`, `Button`, `Card`, `LoadingSpinner`, `LoadingDots`. Unused in app (tests-only): `Modal`/`ConfirmModal`, `Input`, `Select`/`SmartSelect`, `Textarea`, `Tabs`/`Accordion`/`Stepper`/`VerticalTabs`/`ContentTabs`, `Pagination`/`SimplePagination`/`AdvancedPagination`/`useInfiniteScroll`, `Toast`/`ToastProvider`, `FormValidation`, `ImageCard`, named Alert/Badge wrappers, `LoadingRing`/`Ball`/`Bars`/`Infinity`, Skeletons, `LoadingOverlay`/`LoadingButton`. FEATURE_STATUS already marks the kit 🔲. ROADMAP §4.6 Modal triple-focus is moot — Modal is unmounted. |
| **Action** | **delete** unused modules + their `__tests__` in a later debt PR; **leave** the six live primitives (or replace with raw DaisyUI classes). Do not grow the kit. |

### P1-2 — DaisyUI tests keep the unused kit sacred

| Field | Value |
|-------|--------|
| **Sev** | P1 |
| **Path** | `webui/frontend/src/components/DaisyUI/__tests__/{A11y,Modal,Tabs,Pagination,Button}.test.tsx` |
| **Why** | A11y/Modal/Tabs/Pagination tests instantiate wrappers no page mounts. Deleting dead Modal/Tabs/Pagination fails CI even though `/` and `/chat` never render them. Same “sacred catalog” pattern as P0-1, for a component museum. |
| **Action** | **delete** with P1-1. Keep Button loading + Alert a11y only if those primitives stay. |

### P1-3 — `api.ts` is still the deleted Builder/operator client

| Field | Value |
|-------|--------|
| **Sev** | P1 |
| **Path** | `webui/frontend/src/lib/api.ts` (458 lines) |
| **Why** | Live callers: `fetchBlueprints`, `isAuthError` (ChatPage, AgentSidebar). Everything else is leftover from deleted SPA pages: `fetchModels`/`fetchTeams`/`createTeam`/`deleteTeam`, library CRUD, `generateAgentCode`/`validateAgentCode`/`ensureCsrfCookie`, custom-blueprint CRUD, `fetchServerSettings`/`fetchEnvironmentVariables`, `fetchBlueprintSource`/`fetchCliAgents`/`fetchConfigOptions`/`fetchBlueprintTools`. `AUTH_ERROR_EVENT` is dispatched; **no listener**. Comment still says “SPA Settings token UI was deleted”. |
| **Action** | **delete** unused exports + types; **leave** `apiGet`/`ApiError`/`fetchBlueprints`. |

### P1-4 — Builder leftover pure libs (ADR-001 already said panels are gone)

| Field | Value |
|-------|--------|
| **Sev** | P1 |
| **Path** | `webui/frontend/src/lib/inferenceProfile.ts` (112); `toolCapabilities.ts` (62); `skills.ts` (13); plus `src/lib/__tests__/{inferenceProfile,toolCapabilities,skills}.test.ts` |
| **Why** | Comments admit “SPA Builder UI deleted per ADR-001; logic kept for tests.” No page imports them. FEATURE_STATUS: “Orphan Builder React panels 🗑; pure helpers remain.” They are a second, JS copy of Python `swarm.core.*` kept alive by Vitest. |
| **Action** | **delete** helpers + tests (Python remains source of truth). **leave** only if a future SPA Builder is an accepted milestone — ADR-001 rejected remounts. |

### P1-5 — Dashboard re-fetches the same catalog the sidebar already loads

| Field | Value |
|-------|--------|
| **Sev** | P1 |
| **Path** | `webui/frontend/src/pages/Dashboard.tsx` L34–59; `AgentSidebar.tsx` L42–46; `ChatPage.tsx` L95–98 |
| **Why** | Sidebar + Chat share `queryKey: ['blueprints']` + `fetchBlueprints`. Dashboard uses a **different** key (`dashboard-stats`) and raw `fetch('/v1/blueprints')` + `/v1/models` + `/v1/teams/` (fallback `/teams/export?format=json`) + `/health`, polling every 30s, **without** the typed client / auth-error path. Same catalog, two stacks, counts can disagree with the sidepane on 401. |
| **Action** | **extract** dashboard counts onto `['blueprints']` / `['models']` / `['teams']` via `api.ts` (after P1-3 trim). **leave** the 30s poll if Home stays a stats catalog. |

### P1-6 — Experimental flags are not experimental (default ON, module-load freeze)

| Field | Value |
|-------|--------|
| **Sev** | P1 |
| **Path** | `webui/frontend/src/experimental/flags.ts`; `App.tsx` L10–11, L56; `ChatPage.tsx` L37–38; `experimental/README.md` |
| **Why** | No *dead unused flag names*. Both `command_palette` and `chat_message_actions` are wired and **default ON** (`isExperimentalEnabled` → `true` unless `off`/`false`). Values are read **once at module load**, so console `localStorage.setItem` does nothing until full reload. Reviewers get ⌘K + Copy/Retry in “production” SPA. Not dead — **theater**. |
| **Action** | **leave** the two features if they stay; **delete** the flag wrapper and `experimental/` folder (promote to `components/`) *or* flip default to OFF. Do not add more default-ON flags. |

### P1-7 — CommandPalette is a third copy of the operator catalog + broken Home nav

| Field | Value |
|-------|--------|
| **Sev** | P1 |
| **Path** | `webui/frontend/src/experimental/CommandPalette.tsx` L65–84, L118–127 |
| **Why** | Palette items duplicate App top-nav + Dashboard cards + sidebar footer (Home, Chat, Blueprints, My Blueprints, Launch, Teams, Sessions, Settings, theme). `choose()` SPA-`navigate`s only paths starting `/chat`; **Home (`/`)** does `window.location.assign('/')` — full reload of the SPA. No CommandPalette unit/e2e test (only `flags.test.ts`). |
| **Action** | **extract** a single destinations table if palette stays; fix `/` to `navigate('/')`. **delete** the palette if Grok chrome has no catalog launcher. |

### P1-8 — `focus-trap-react` exists only for unmounted Modal

| Field | Value |
|-------|--------|
| **Sev** | P1 |
| **Path** | `webui/frontend/package.json` (`focus-trap-react`); `src/components/DaisyUI/Modal.tsx` |
| **Why** | ROADMAP §4.6 already flags native `<dialog>` + FocusTrap + backdrop math. Modal is unused (P1-1), so the dependency is dead weight in the lockfile. |
| **Action** | **delete** with Modal. |

---

### P2-1 — DaisyUI v4 leftover CSS tokens in `:root`

| Field | Value |
|-------|--------|
| **Sev** | P2 |
| **Path** | `webui/frontend/src/index.css` L73–81 (`--animation-btn`, `--animation-input`, `--btn-text-case`, `--btn-focus-scale`, `--border-btn`, `--tab-border`, `--tab-radius`) |
| **Why** | DaisyUI 5 themes above already set `--color-*` / `--radius-*`. These v4-era `:root` knobs are unused by the Grok theme plugins and by live markup (no Tabs in app). `os-action-card*` and `os-agent-*` **are** used — do not delete those. |
| **Action** | **delete** the v4 `:root` block in a CSS tidy PR. **leave** `--os-chrome-sidebar` + agent-dot + action-card rules while Home/Agents exist. |

### P2-2 — Theme / drawer state at App root re-renders Chat + Dashboard + sidebar

| Field | Value |
|-------|--------|
| **Sev** | P2 |
| **Path** | `webui/frontend/src/App.tsx` L35–36, L38–52; `AgentSidebar.tsx` `renderAgentLink` L117–147 |
| **Why** | `darkMode` and `sidebarOpen` live on `App`. Toggling theme or opening the mobile drawer re-renders ChatPage (WS state is refs, so no reconnect — good) and rebuilds every agent row (`renderAgentLink` is not `memo`). ChatPage already memoizes `ChatBubbleBody` (good). Not a correctness bug. |
| **Action** | **extract** theme + drawer into a small context/store if chrome is rewritten; **leave** until then. Memoizing `renderAgentLink` is optional. |

### P2-3 — Dual lockfiles + stale frontend README

| Field | Value |
|-------|--------|
| **Sev** | P2 |
| **Path** | `webui/frontend/package-lock.json` + `pnpm-lock.yaml`; `webui/README.md` L57 (`tailwind.config.js` — **file does not exist**; Vite + `@tailwindcss/vite`); L90 (“All DaisyUI components are available”) |
| **Why** | Two package managers recorded; README still describes the pre-ADR-001 tree and advertises the unused DaisyUI museum. |
| **Action** | **delete** one lockfile (keep whichever CI uses — `npm ci` in `scripts/build_frontend.sh`). **leave** README until the next docs pass; then drop `tailwind.config.js` and the “all components” line. |

### P2-4 — Unused / leftover tooling in the frontend package

| Field | Value |
|-------|--------|
| **Sev** | P2 |
| **Path** | `webui/frontend/package.json` (`axe-core`, `@types/jest`); `vite.config.ts` L24–26 `/marketplace`, L60–63 `/team-creator` |
| **Why** | `axe-core` is never imported (a11y tests are RTL, not axe). `@types/jest` is unused (Vitest). Vite still proxies Wagtail-era `/marketplace` and `/team-creator` (SPA has no those routes; marketplace was removed). |
| **Action** | **delete** unused deps and dead proxy entries when touching the toolchain. **leave** `/v1`, `/ws`, `/sessions`, `/blueprint-library`, `/settings`, `/accounts`, `/login`, `/health`. |

### P2-5 — `agentMarkColor` is unused in the UI (CSS dots are the live path)

| Field | Value |
|-------|--------|
| **Sev** | P2 |
| **Path** | `webui/frontend/src/lib/hiddenAgents.ts` L45–64; `index.css` L147–159 `.os-agent-dot[data-mark]` |
| **Why** | Sidebar uses `agentMarkIndex` + CSS `data-mark`. `agentMarkColor` is only asserted in `hiddenAgents.test.ts`. Color tables are duplicated (TS hex list vs CSS). |
| **Action** | **delete** `agentMarkColor` + the TS color array; **leave** CSS marks. |

### P2-6 — Button `variant`/`color` overlap and dead `active`/`disabled` aliases

| Field | Value |
|-------|--------|
| **Sev** | P2 |
| **Path** | `webui/frontend/src/components/DaisyUI/Button.tsx` L8–40 |
| **Why** | ROADMAP §4.2 already notes dead `active`/`disabled` variant aliases. `variant` and `color` both emit `btn-*` and can fight. Live ChatPage only uses `primary` / `ghost` / `lg` / `sm`. |
| **Action** | **leave** until P1-1; then shrink the prop surface or **delete** the wrapper and use `btn` classes. |

### P2-7 — ChatPage still a single-line composer (known gap)

| Field | Value |
|-------|--------|
| **Sev** | P2 |
| **Path** | `webui/frontend/src/pages/ChatPage.tsx` L561–571 (`<input type="text">`) |
| **Why** | ROADMAP §4.6: “single-line composer remains.” Unused DaisyUI `Textarea` sits next door. Not unused code — missing product surface. |
| **Action** | **leave** (product). Do not wire unused `Textarea` “just because”. |

### P2-8 — Barrel `DaisyUI/index.ts` re-exports the museum

| Field | Value |
|-------|--------|
| **Sev** | P2 |
| **Path** | `webui/frontend/src/components/DaisyUI/index.ts`; `FormValidation.tsx` imports from `'./'` (cycle) |
| **Why** | Pages import from the barrel. Rollup can tree-shake, but the barrel + `FormValidation` → `'./'` cycle makes shake fragile and advertises 13 components as public API. |
| **Action** | **extract** live primitives to a thin barrel (or direct files) when deleting P1-1. |

### P2-9 — Sidebar footer duplicates Teams/Settings already in top-nav

| Field | Value |
|-------|--------|
| **Sev** | P2 |
| **Path** | `webui/frontend/src/components/AgentSidebar.tsx` L247–256 |
| **Why** | Grok-like pane ends with operator links that App.tsx already shows. Fine as a shortcut; more catalog chrome. |
| **Action** | **leave** until P0-2. |

### P2-10 — Experimental Copy/Retry has no page-level test

| Field | Value |
|-------|--------|
| **Sev** | P2 |
| **Path** | `webui/frontend/src/experimental/ChatMessageActions.tsx`; `ChatPage.test.tsx` (no Copy/Retry cases) |
| **Why** | Feature is default-ON (P1-6) but ChatPage tests never enable/assert it. Regression risk if promoted. |
| **Action** | **leave** until promote/delete decision; then add one test or delete with the flag. |

---

## What is *not* a finding (checked, leave)

| Item | Why leave |
|------|-----------|
| `ChatBubbleBody` memo + `htmlSafe`/`markdown.ts` | Live, tested, correct for streaming. |
| WS reconnect / 4401 skip (`chatReconnect.ts`, ChatPage tests) | Honest and covered. |
| `hiddenAgents` persist key `swarm_hidden_agents` | Shared contract with Django JS; do not rename casually. |
| Theme key `swarm_theme` + dark default | Matches Django; e2e `interaction.spec.ts` locks it. |
| ADR-001 route cut (`/` + `/chat` only, `*` → `/`) | Already done; do not remount Builder. |
| Unused CSS for `os-action-card` / `os-agent-sidebar` | Used. Only v4 `:root` tokens are unused (P2-1). |
| Extra experimental **flag names** | None. Two flags, both wired. The debt is default-ON theater (P1-6), not orphans. |

---

## Suggested later-PR slices (not this audit)

Do **not** do these in REQ-22a. If a follow-up is filed, keep slices small:

1. **Unlock tests** — split IA assertions (P0-1) from behavior assertions so a chrome rewrite can land.
2. **One blueprint selection** — search-param hook (P0-3).
3. **Delete DaisyUI museum** — P1-1, P1-2, P1-8, P2-6, P2-8.
4. **Trim `api.ts` + Builder libs** — P1-3, P1-4, P1-5.
5. **Promote or delete `experimental/`** — P1-6, P1-7, P2-10.
6. **Chrome IA** — P0-2 (needs a product/ADR decision, not a drive-by).

---

## Inventory (starting tree)

| Surface | Files | Role |
|---------|-------|------|
| Shell | `App.tsx` (195) | Top-nav + dock + theme + palette mount |
| Home | `Dashboard.tsx` (188) | Four action cards + raw-fetch stats |
| Chat | `ChatPage.tsx` (659) | WS, header blueprint `<select>`, markdown bubbles |
| Agents | `AgentSidebar.tsx` (292) | `/v1/blueprints` list, hide/unhide |
| Experimental | `CommandPalette.tsx` (224), `ChatMessageActions.tsx` (64), `flags.ts` | Default-ON |
| DaisyUI | 13 modules, ~2.6k lines | 6 used, rest museum |
| Live libs | `api.ts`, `chatWs.ts`, `chatReconnect.ts`, `markdown.ts`, `htmlSafe.ts`, `hiddenAgents.ts` | Mixed live / leftover |
| Orphan libs | `inferenceProfile.ts`, `skills.ts`, `toolCapabilities.ts` | Tests only |

Live DaisyUI imports:

- `Dashboard.tsx` → `Badge`, `Card`
- `ChatPage.tsx` → `Alert`, `Badge`, `Button`, `LoadingDots`, `LoadingSpinner`
