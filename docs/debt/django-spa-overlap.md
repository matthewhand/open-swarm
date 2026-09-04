# REQ-22b — Django operator UI vs SPA overlap (audit only)

> **Quoted requirement (do not rewrite; audit only):**
>
> REQ-22b technical debt AUDIT ONLY. Do not rewrite. Full ranked list in
> final report and/or draft `docs/debt/django-spa-overlap.md`.
>
> Scope: Django operator UI vs SPA overlap. Templates under
> `src/swarm/templates/`, static JS (`teams_*.js`, settings, chrome), views,
> vs `webui/frontend`.
> Known collision: `/teams/` is LLM-profile aliases; SPA has no Teams page;
> top-nav Teams hrefs out to Django. Also settings dashboard vs intended
> DaisyUI modal-end sheet. Swarm Creator vs Teams Admin vs blueprint library.
>
> Look for: duplicate chrome (theme, nav), dead templates, two sources of
> truth for the same noun (Team, Session, Settings), Bootstrap vs DaisyUI,
> inefficient server render + SPA.
>
> Each finding: P0/P1/P2, path, why, action. No Neon. No deploy. Quote this REQ.

**Status:** audit only. No templates, JS, views, or SPA pages were rewritten.
No Neon work. No deploy.

**As-of:** `origin/main` @ `4d554ea5` (includes REQ-5d chrome + REQ-14 chat
retention). Governing product decision remains
[ADR-001](../ADR-001-primary-ui.md): Django trailing-slash routes own operator
chrome; the SPA mounts `/` + `/chat` only.

---

## How to read this list

| Priority | Meaning in this audit |
|----------|------------------------|
| **P0** | Operator can hit the wrong noun / mutate the wrong store, or two writable sources of truth already diverge. |
| **P1** | Dual implementation or IA split that will keep costing every chrome/settings/session change. |
| **P2** | Dead weight, stale docs, or polish. Safe to delete or ignore until a cleanup pulse. |

**Action** is a recommended next slice, not work done here. ADR-001 already
**rejected** an SPA-primary rewrite; actions assume Django stays canonical
unless a later ADR reverses that.

---

## Architecture snapshot

| Surface | Stack | Owns |
|---------|-------|------|
| SPA `webui/frontend` | React 18 + Tailwind 4 + DaisyUI 5 | `/` dashboard, `/chat` (+ `/chat/*`, `/agents` → `/chat`) |
| Django operator | Bootstrap 5 + `operator.css` + HTMX (loaded, barely used) | `/teams/`, `/teams/launch/`, `/blueprint-library/`, `/agent-creator/`, `/team-creator/`, `/settings/`, `/sessions/`, `/profiles/` |
| Hybrid serve | `web_views.index` + `spa_chat` + SPA fallback regex | Built `dist/index.html` when present; Django `index.html` only if `dist/` is missing |

Chrome is **mirrored, not shared**: same IA labels (Home · Chat · Blueprints ·
Teams · Sessions · Settings), two implementations, full-page `<a href>` hops
from SPA → Django.

---

## Noun collision map

| Noun | Store A | Store B | Store C+ | Operator-visible lie |
|------|---------|---------|----------|----------------------|
| **Team** | `/teams/` + `/v1/teams/` + `teams.json` = **LLM-profile aliases** ([GLOSSARY](../GLOSSARY.md)) | `/teams/launch/` runs a **blueprint** as “Team Blueprint” | `/team-creator/` **Swarm Creator** writes a multi-bot Python blueprint | Top-nav **Teams** → launcher, not admin. Sidebar **Teams** → admin. SPA has no Teams page. |
| **Session** | Django **login cookie** (WS auth, 4401) | Session Explorer `/sessions/` over `/v1/responses` | REQ-14 **per-agent JSON** (`chat_store`) + `ChatConversation` DB mirror + `localStorage swarm_agent_chat:*` | Nav **Sessions** is Explorer only. Chat persistence is Settings-only. None of these is the other. |
| **Settings** | Full-page Bootstrap dashboard `/settings/` (now also REQ-14 retention) | Intended DaisyUI **`modal-end` sheet** (component exists, unused) | `/profiles/` + `/settings/api/` + unused SPA `fetchServerSettings` | Gear / nav always full-page hops to Django. No sheet. |
| **Blueprint / swarm** | Catalog `/blueprint-library/` | My Library + Blueprint Creator | Agent Creator + Swarm Creator (no nav hrefs) | “Create a team” has three factories and two libraries. |
| **Chrome / theme** | `base.html` + `chrome_theme.js` (`data-bs-theme` / `data-os-theme`) | `App.tsx` (`data-theme`) | Shared key `localStorage.swarm_theme` only | Theme survives hops; everything else reloads. |

---

## Ranked findings

### P0

#### D-01 — “Team” is three products under one nav word

| | |
|--|--|
| **Priority** | P0 |
| **Path** | `src/swarm/templates/base.html` (Teams → `/teams/launch/`); `src/swarm/templates/teams_admin.html`; `src/swarm/templates/teams_launch.html`; `src/swarm/templates/team_creator.html`; `src/swarm/views/teams_api.py`; `src/swarm/views/web_views.py`; `docs/GLOSSARY.md`; `webui/frontend/src/App.tsx`; `webui/frontend/src/pages/Dashboard.tsx` |
| **Why** | GLOSSARY and `teams_api.py` are honest: a `/v1/teams` “team” is `id` + `description` + `llm_profile` in `teams.json`, **not** a multi-agent builder. The launcher copy says “Team Blueprint” and streams `/v1/chat/completions` against **discoverable blueprints**. Swarm Creator (`/team-creator/`) is the actual multi-bot codegen. SPA Dashboard **Launch Team** text (“Stand up a blueprint team and expose it as an API model”) conflates launcher (run a blueprint) with admin (register an alias). Operators following **Teams** will not land on the alias registry they think they are managing, and may create the wrong object. |
| **Action** | Rename in IA before any rewrite: **Launch** (blueprints), **Aliases** (`/teams/` / `/v1/teams`), **Swarm Creator** (codegen). Keep `/v1/teams` contract; change labels and dashboard copy. Do not remount a SPA Teams page (ADR-001). |

#### D-02 — Same chrome label “Teams” points at two Django URLs

| | |
|--|--|
| **Priority** | P0 |
| **Path** | `src/swarm/templates/base.html` L54–57 (top-nav + mobile dock → `/teams/launch/`) vs L116 (sidebar foot → `/teams/`); `webui/frontend/src/App.tsx` L116–117 (nav → launch) vs `webui/frontend/src/components/AgentSidebar.tsx` (footer → `/teams/`); `webui/frontend/src/pages/Dashboard.tsx` (`Launch Team` vs `Manage Teams`); `webui/frontend/src/experimental/CommandPalette.tsx` |
| **Why** | Known collision in the REQ. SPA has **no** Teams route. Every Teams control is a full-page href out to Django, but **which** Django page depends on which chrome widget you click. Sidebar “Teams” and top-nav “Teams” are not the same destination. Bare `/teams` (no slash) RedirectView goes to **`/teams/launch/`**, not `/teams/` (`src/swarm/urls.py` `spa_teams_to_django`). |
| **Action** | One label, one href. Recommend: nav/dock **Launch**; sidebar/admin **Aliases** or **Manage aliases**. Align the `/teams` redirect with that choice. |

---

### P1

#### D-03 — Settings is a Bootstrap dashboard; intended UX is a DaisyUI `modal-end` sheet

| | |
|--|--|
| **Priority** | P1 |
| **Path** | `src/swarm/templates/settings_dashboard.html` + `src/swarm/static/js/settings_dashboard.js` + `src/swarm/views/settings_views.py`; Bootstrap `#objectModal` / `#envModal`; REQ-14 block “Chat persistence” on the same page; `webui/frontend/src/components/DaisyUI/Modal.tsx` (unused by any page); `webui/frontend/src/App.tsx` Settings `<a href="/settings/">` |
| **Why** | Current Settings is a login-gated, server-rendered **dashboard**: stats meter, AUTH checklist, REQ-14 chat retention (archive / trash / disk), accordion groups, JSON export, env modal. The SPA Settings page was **deleted** (ADR-001). DaisyUI already has a Modal primitive (and DaisyUI’s `modal-end` is the end-sheet pattern) but nothing in `pages/` imports it. Gear / nav always tears down Chat/Home and loads a different CSS stack. REQ-14 **increased** the dashboard’s job (retention “not in the Chat chrome”) instead of moving settings into a sheet over Chat. Two intended products: overlay sheet vs operator back-office. Only the back-office exists. |
| **Action** | Decide in a short ADR addendum: (a) keep `/settings/` as the canonical back-office and drop the sheet story, or (b) extract a DaisyUI `modal-end` for **Chat-adjacent** prefs (theme already in chrome; retention/trash) and leave the dashboard for env/profiles. Do not build both. |

#### D-04 — Duplicate chrome: theme, top-nav, AGENTS sidebar, mobile dock

| | |
|--|--|
| **Priority** | P1 |
| **Path** | `src/swarm/templates/base.html` + `src/swarm/static/js/chrome_theme.js` + `src/swarm/static/js/agent_sidebar.js` + `src/swarm/static/css/operator.css` + `rest_mode_style.css`; `webui/frontend/src/App.tsx` + `webui/frontend/src/index.css` + `webui/frontend/src/components/AgentSidebar.tsx` + `webui/frontend/src/lib/hiddenAgents.ts` |
| **Why** | REQ-5 / REQ-5c / REQ-5d already spent pulses making the two shells **look** alike (shared IA, `swarm_theme`, `swarm_hidden_agents`, large action cards). They are still two codepaths: Bootstrap `data-bs-theme`/`data-os-theme` vs DaisyUI `data-theme`; Font Awesome vs Lucide; vanilla JS sidebar vs React Query sidebar. Every chrome tweak must land twice or the hop Home ↔ Teams/Settings looks broken (REQ-5d was exactly that class of bug). |
| **Action** | Freeze a chrome contract test (already started in `tests/unit/test_req5_chrome_shell.py`) and treat `base.html` as the operator source of truth. Do not “fix” by remounting SPA chrome on Django routes. |

#### D-05 — “Session” has four (now five) meanings

| | |
|--|--|
| **Priority** | P1 |
| **Path** | `src/swarm/templates/session_explorer.html` + `src/swarm/views/session_explorer.py`; `webui/frontend/src/lib/chatWs.ts` + `agentChat.ts`; `src/swarm/core/chat_store.py`; `src/swarm/views/chat_persist_views.py`; `src/swarm/consumers.py`; Django `ChatConversation` / `ChatMessage` |
| **Why** | **(1)** Login session cookie — required for WS; bearer does not work. **(2)** Session Explorer — `/v1/responses` observability. **(3)** Per-agent WS conversation id in `localStorage` (`swarm_agent_chat:`). **(4)** REQ-14 file store `active/<user>/<agent>.json` — documented as **the** restore/stats source of truth. **(5)** ORM `ChatConversation` — “mirror used by the websocket consumer.” Nav **Sessions** is only (2). Chat restore is (3)+(4)+`GET /chat/thread/`. Operators looking for “that chat” in Session Explorer will not find REQ-14 threads. |
| **Action** | Glossary row: **Auth session** / **API session (Explorer)** / **Agent thread (Chat)**. Optional Explorer link from Settings retention rows (read-only). Do not merge stores without a dedicated REQ. |

#### D-06 — Two Home pages (SPA dashboard vs Django `index.html`)

| | |
|--|--|
| **Priority** | P1 |
| **Path** | `webui/frontend/src/pages/Dashboard.tsx`; `src/swarm/templates/index.html`; `src/swarm/views/web_views.py` `index` |
| **Why** | `/` prefers built SPA. If `dist/` is missing (fresh clone, skipped `make frontend`), operators get a **different** Home: Django cards + **recent sessions** list (SPA Home has stats + API status, no session list). Two sources of “what Home is.” |
| **Action** | Either always bake `dist/` in the images operators run, or make Django `index.html` a thin “build the frontend” stub so the fallback is not a second product. |

#### D-07 — Swarm Creator vs Teams Admin vs Blueprint Library (three factories)

| | |
|--|--|
| **Priority** | P1 |
| **Path** | `src/swarm/templates/team_creator.html` + `team_creator.js` + `agent_creator_views.team_creator_page` (`/team-creator/`); `teams_admin.html` + `teams_admin.js` + `web_views.team_admin` (`/teams/`); `blueprint_library.html` + `blueprint_creator.html` + `my_blueprints.html` + `agent_creator.html` |
| **Why** | Library: browse/install **existing** blueprints, launch via `/teams/launch/?blueprint=`. Admin: CRUD **aliases**. Swarm Creator: generate a **new multi-bot** blueprint (Validate marked unavailable/demo). Agent Creator: generate a **single-agent** blueprint. Blueprint Creator: yet another custom-blueprint form. None of Agent Creator / Swarm Creator appear as `href` in any other operator template (only Blueprints **active-state** highlighting in `base.html`). Library cards do not link to either creator. |
| **Action** | Put **one** “Create” entry on the library page (choose single-agent vs swarm). Leave alias CRUD on `/teams/` under a non-Team name (see D-01). Hide or tombstone Swarm Creator Validate until it is real. |

#### D-08 — Full-page SPA ↔ Django hops (no shared shell)

| | |
|--|--|
| **Priority** | P1 |
| **Path** | `webui/frontend/src/App.tsx` (React `<Link>` only for `/` and `/chat`; everything else `<a href>`); `src/swarm/urls.py` RedirectViews + `spa_fallback`; `webui/frontend/vite.config.ts` |
| **Why** | Leaving Chat for Settings/Teams/Blueprints/Sessions unloads the React tree, loses in-memory Chat UI state (disk persist is REQ-14, not chrome), and reloads Bootstrap. Returning Home reloads DaisyUI. Inefficient by construction: server-render **plus** SPA, never one document. Vite proxies most Django prefixes so `npm run dev` works, but **`/agent-creator/` the page is not proxied** (only `generate`/`validate`) — local Vite silently dumps that URL onto the SPA dashboard (`App.tsx` `*`). |
| **Action** | Accept the hop (ADR-001) and document it. Fix the Vite `/agent-creator` page proxy so destaging does not lie. Do not embed Django pages in an iframe. |

#### D-09 — Chat protocol is HTMX HTML fragments; Django `chat.html` is gone

| | |
|--|--|
| **Priority** | P1 |
| **Path** | `src/swarm/templates/websocket_partials/*.html`; `src/swarm/consumers.py`; `webui/frontend/src/lib/chatWs.ts`; `docs/websocket_chat.md` (still mentions `templates/chat.html`) |
| **Why** | The only live Chat UI is the SPA. The consumer still emits HTMX `hx-swap-oob` HTML for a deleted Django chat page. The SPA `DOMParser`s those frames. HTMX is loaded on **every** operator page (`base.html`) even though **no** operator template uses `hx-` attributes (only the partials). Two stacks for one socket. |
| **Action** | Later REQ: JSON frames for SPA; keep HTML partials only if a Django chat returns. Until then, stop loading `htmx.min.js` on operator pages that never swap. |

#### D-10 — “SPA parity” JSON APIs + unused SPA client (remount bait)

| | |
|--|--|
| **Priority** | P1 |
| **Path** | `src/swarm/views/teams_api.py`, `library_api.py` (“JSON … (SPA parity)”); `src/swarm/views/settings_views.py` `settings_api`; `webui/frontend/src/lib/api.ts` (`fetchTeams` / `createTeam` / `deleteTeam` / `fetchLibrary` / `generateAgentCode` / `fetchServerSettings` / `fetchCustomBlueprints` / …) — **no page imports** |
| **Why** | ADR-001: delete leftover SPA pages; do not keep remount bait. Pages are gone; the typed client and the “parity” APIs remain. External OpenAI-style `/v1/teams` is a real API (keep). `/settings/api/` is only consumed by tests + the unused client (dashboard uses `json_script`). Easy to accidentally remount Settings/Teams in React. |
| **Action** | Keep `/v1/teams` and `/v1/library` as public REST. Delete or quarantine unused SPA wrappers. Mark `/settings/api/` as test/operator JSON, not SPA. |

#### D-11 — Dual agent-sidebar implementations

| | |
|--|--|
| **Priority** | P1 |
| **Path** | `src/swarm/static/js/agent_sidebar.js`; `webui/frontend/src/components/AgentSidebar.tsx` + `lib/hiddenAgents.ts` |
| **Why** | Same hide contract (`localStorage.swarm_hidden_agents`), same `/v1/blueprints` list, two UIs. Sidebar foot **Teams** href differs (D-02). Hash-to-color mark logic is duplicated. |
| **Action** | Treat JS as the Django port of the React contract; add a shared fixture test for hide/unhide JSON shape only. No third implementation. |

#### D-12 — Settings + Profiles are two config UIs

| | |
|--|--|
| **Priority** | P1 |
| **Path** | `settings_dashboard.html` (link card → profiles); `src/swarm/templates/profiles.html`; `web_views.profiles_page` |
| **Why** | LLM profiles are a Settings concern (aliases in Teams Admin **select** a profile). Profiles is a separate Bootstrap table at `/profiles/`, public (FEATURE_STATUS), while Settings is login-gated. ROADMAP §4.6 still claims “`profiles.html` DaisyUI classes on a Bootstrap base” — **false today** (file is Bootstrap + `prof-*` in `operator.css`). Two pages, stale debt note. |
| **Action** | Fold the table into Settings or keep Profiles as a deep-link section. Strike the DaisyUI-on-Bootstrap ROADMAP line. |

#### D-13 — Auth split across the same nouns

| | |
|--|--|
| **Priority** | P1 |
| **Path** | FEATURE_STATUS / `docs/AUTH.md`; `team_launcher` public vs `team_admin` `@login_required`; Chat WS session-only; Settings/Sessions login; Agent Creator GET public / POST login |
| **Why** | “Teams” launcher is usable logged-out; “Teams” admin is not. Chat needs a cookie the Settings dashboard talks about in a checklist the operator already left Chat to read. Bearer works for `/v1/*` and not for `/chat`. Correct, but the hybrid UI makes it feel like two apps. |
| **Action** | Keep the AUTH.md rules. Surface a one-line “sign in for admin/settings/chat restore” on the public launcher. No new auth system. |

---

### P2

#### D-14 — Dead template `account/signup.html`

| | |
|--|--|
| **Priority** | P2 |
| **Path** | `src/swarm/templates/account/signup.html` |
| **Why** | No URL. `{% block head %}` is not defined on `base.html`. `{% url 'account_login' %}` does not exist (`login` / `custom_login` do). References missing `css/custom.css`. |
| **Action** | Delete. |

#### D-15 — Dead views `core_views.py`

| | |
|--|--|
| **Priority** | P2 |
| **Path** | `src/swarm/views/core_views.py`; imported optionally in `src/swarm/views/__init__.py` |
| **Why** | `index` renders missing `swarm/index.html`; `custom_login` renders missing `swarm/login.html`. Not in `urls.py`. Live login is `web_views.custom_login`. |
| **Action** | Delete module + `__init__` import. |

#### D-16 — Dead `dropdown.js`; leftover `dropdown.css`

| | |
|--|--|
| **Priority** | P2 |
| **Path** | `src/swarm/static/js/dropdown.js` (zero `<script>` refs); `src/swarm/static/css/dropdown.css` still in `base.html` L10 |
| **Why** | JS redirects to `/django_chat/<blueprint>/new/` after an HTMX swap on `#blueprintDropdown` — leftover of deleted `chat.html`. CSS may still style something; JS is dead. |
| **Action** | Delete JS. Grep CSS usage; drop the link if unused. |

#### D-17 — Unused DaisyUI library (the sheet primitives)

| | |
|--|--|
| **Priority** | P2 |
| **Path** | `webui/frontend/src/components/DaisyUI/*` — Modal, Toast, Tabs, Pagination, Input, Select, Textarea, FormValidation unused by `pages/` (Dashboard/Chat use Badge, Card, Alert, Button, Loading*) |
| **Why** | FEATURE_STATUS: 🔲 “13 components built”. The intended Settings `modal-end` sheet would use Modal. Today it is test-only weight. ROADMAP §4.6 also flags Modal triple focus/dismiss. |
| **Action** | If D-03 chooses “no sheet”, delete unused components + tests. If sheet, implement **one** Modal path. |

#### D-18 — `django_chat` is a third chat UI

| | |
|--|--|
| **Priority** | P2 |
| **Path** | `src/swarm/blueprints/django_chat/templates/django_chat/django_chat_webpage.html` + views |
| **Why** | Discoverable blueprint with its own webpage, separate from SPA `/chat` and the deleted operator `chat.html`. Operators can think it is the product Chat. |
| **Action** | Label it a blueprint demo, or link to `/chat?blueprint=django_chat`. |

#### D-19 — Stale docs after ADR-001 / REQ-5 / REQ-14

| | |
|--|--|
| **Priority** | P2 |
| **Path** | `docs/ADR-001-primary-ui.md` (context still says Teams/Blueprints SPA pages are leftovers; they are deleted); `docs/websocket_chat.md` + `chatWs.ts` (`chat.html`); `ROADMAP.md` L306–309 (DaisyUI-on-Bootstrap `profiles.html`); GLOSSARY “HTMx operator UI” overstates HTMX |
| **Why** | Docs describe a dual-mount world that ADR-001 already ended, then REQ-14 added a fifth session store without a glossary row. |
| **Action** | Doc-only pass; no product change. |

#### D-20 — Duplicated `os-action-card` CSS

| | |
|--|--|
| **Priority** | P2 |
| **Path** | `src/swarm/static/css/rest_mode_style.css`; `webui/frontend/src/index.css` |
| **Why** | Same class names on Django and SPA so REQ-5 cards match. Two copies will drift (already the usual chrome tax). |
| **Action** | Comment a “keep in sync with …” pointer in both files. No shared build. |

#### D-21 — SPA fallback / redirect gaps for Swarm Creator

| | |
|--|--|
| **Priority** | P2 |
| **Path** | `src/swarm/urls.py` SPA fallback negative lookahead omits `team-creator/`; no bare `/team-creator` RedirectView (unlike `/agent-creator`) |
| **Why** | `/team-creator/` is registered earlier so production still hits Django. Bare `/team-creator` can fall through to the SPA catch-all → Home. Easy to break if route order changes. |
| **Action** | Add `team-creator/` to the exclusion and a slash redirect twin. |

#### D-22 — Settings missing from the five-tab mobile dock

| | |
|--|--|
| **Priority** | P2 |
| **Path** | `base.html` L127–153; `App.tsx` L163–168 |
| **Why** | Intentional (ADR-001 / FEATURE_STATUS): Settings is desktop/gear only. After REQ-14, **retention is Settings-only**, so mobile operators have no dock path to trash chats. Gear exists only in the top bar (easy to miss under the hamburger). |
| **Action** | If D-03 stays dashboard, add Settings to the dock **or** a Chat overflow → `/settings/#chat-retention-title`. |

#### D-23 — Login is outside operator chrome

| | |
|--|--|
| **Priority** | P2 |
| **Path** | `src/swarm/templates/account/login.html` (standalone; `operator.css` only) |
| **Why** | No AGENTS sidebar, no IA, no theme toggle. Fine for a gate; after REQ-5d, login CSS was special-cased so it would not flex-center every `body`. Another mini-shell. |
| **Action** | Leave unless login theming drifts again. |

#### D-24 — `rest_mode` static tree is a fourth UI fossil

| | |
|--|--|
| **Priority** | P2 |
| **Path** | `src/swarm/static/rest_mode/js/*`, `css/chat.css`, `settings.css`, … |
| **Why** | ROADMAP §4.4 deleted `templates/rest_mode/*`; static JS kept for XSS tests. Not operator chrome, but another Settings/Chat implementation on disk. |
| **Action** | Keep tests; do not wire into `base.html`. |

#### D-25 — Command palette incomplete (experimental)

| | |
|--|--|
| **Priority** | P2 |
| **Path** | `webui/frontend/src/experimental/CommandPalette.tsx` |
| **Why** | Jumps to Launch + Manage Teams + Settings dashboard + library; omits Agent Creator, Swarm Creator, Blueprint Creator, Profiles. Flag-gated. |
| **Action** | If the palette stays, add the hidden creators or drop it. |

#### D-26 — Theme attributes are not the same DOM contract

| | |
|--|--|
| **Priority** | P2 |
| **Path** | `chrome_theme.js` sets `data-bs-theme` + `data-os-theme`; `App.tsx` `applyDocumentTheme` sets `data-theme` + inline `backgroundColor` on `html`/`body` |
| **Why** | Shared **storage** key, not shared **attributes**. Harmless while shells never coexist in one document; any future in-place embed would fight. REQ-5d already paints `html`/`body` so Chat has no light strip — Django does the Bootstrap equivalent separately. |
| **Action** | Document the two attribute sets next to `THEME_STORAGE_KEY`. No merge. |

---

## Ranked index (full list)

| ID | Pri | One-line |
|----|-----|----------|
| D-01 | P0 | Team = alias **or** launched blueprint **or** Swarm Creator |
| D-02 | P0 | Chrome “Teams” → `/teams/launch/` **or** `/teams/` depending on widget |
| D-03 | P1 | Settings dashboard vs intended DaisyUI `modal-end` sheet |
| D-04 | P1 | Duplicate chrome (theme / nav / sidebar / dock); Bootstrap vs DaisyUI |
| D-05 | P1 | Session / chat thread: cookie, Explorer, localStorage, JSON store, ORM |
| D-06 | P1 | Two Home UIs (SPA `Dashboard` vs Django `index.html`) |
| D-07 | P1 | Swarm Creator vs Teams Admin vs Blueprint Library (+ Agent/Blueprint creators) |
| D-08 | P1 | Full-page hops; Vite `/agent-creator/` page not proxied |
| D-09 | P1 | SPA Chat parses HTMX HTML; HTMX loaded unused on operator pages |
| D-10 | P1 | SPA-parity APIs + unused `api.ts` CRUD (remount bait) |
| D-11 | P1 | Two agent sidebars |
| D-12 | P1 | Settings dashboard vs `/profiles/` |
| D-13 | P1 | Public launcher vs login-gated admin/settings/chat restore |
| D-14 | P2 | Dead `account/signup.html` |
| D-15 | P2 | Dead `core_views.py` |
| D-16 | P2 | Dead `dropdown.js` + leftover `dropdown.css` |
| D-17 | P2 | Unused DaisyUI Modal/Toast/… (sheet primitives) |
| D-18 | P2 | `django_chat` third chat page |
| D-19 | P2 | Stale ADR/ROADMAP/websocket docs |
| D-20 | P2 | Duplicated `os-action-card` CSS |
| D-21 | P2 | `team-creator` missing from fallback/redirect twins |
| D-22 | P2 | Settings (and REQ-14 retention) not in mobile dock |
| D-23 | P2 | Login mini-shell |
| D-24 | P2 | `rest_mode` static fossil |
| D-25 | P2 | Command palette misses creators |
| D-26 | P2 | Theme attribute split (`data-theme` vs `data-bs-theme`) |

---

## Inventory (evidence, not extra findings)

### Django templates (`src/swarm/templates/`)

| File | Role | Live? |
|------|------|-------|
| `base.html` | Operator shell | Yes |
| `index.html` | Home if SPA `dist/` absent | Fallback only |
| `teams_launch.html` | Team Launcher | Yes |
| `teams_admin.html` | Alias registry admin | Yes |
| `team_creator.html` | Swarm Creator | Yes, **no nav href** |
| `agent_creator.html` | Agent Creator | Yes, **no nav href** |
| `blueprint_library.html` | Catalog | Yes |
| `blueprint_card.html` | Card partial | Yes |
| `blueprint_creator.html` | Custom blueprint form | Yes |
| `my_blueprints.html` | Installed/custom | Yes |
| `settings_dashboard.html` | Settings + REQ-14 retention | Yes |
| `profiles.html` | LLM profile table | Yes |
| `session_explorer.html` / `session_detail.html` | Explorer | Yes |
| `account/login.html` | Login | Yes |
| `account/signup.html` | Signup | **Dead** |
| `websocket_partials/*` | WS HTML frames | Used by consumer, not by operator pages |

Removed earlier (do not restore): `chat.html`, `simple_blueprint_page.html`, `swarm/index.html`, `swarm/login.html`.

### Operator JS (chrome / teams / settings)

| File | Role |
|------|------|
| `chrome_theme.js` | Light/dark; `swarm_theme` |
| `agent_sidebar.js` | AGENTS pane |
| `teams_launch.js` | Blueprint pick + stream |
| `teams_admin.js` | Delete modal wiring |
| `team_creator.js` | Swarm Creator |
| `settings_dashboard.js` | Accordion, export, env modal, REQ-14 retention POSTs |
| `htmx.min.js` + `htmx_csp.js` | Loaded globally; no `hx-` on operator pages |
| `dropdown.js` | **Unreferenced** |

### SPA (`webui/frontend`)

| Route | Page |
|-------|------|
| `/` | `Dashboard.tsx` — cards href out to Django |
| `/chat`, `/chat/*` | `ChatPage.tsx` |
| `/agents`, `/agents/*` | Navigate → `/chat` (REQ-5d) |
| `*` | Navigate → `/` |

Deleted (do not remount): TeamsPage, BlueprintsPage, SettingsPage, BuilderPage, AgentCreatorPage.

### Parallel REST (same nouns)

| HTTP | Mirrors |
|------|---------|
| `/v1/teams/` | `teams.json` / Teams Admin |
| `/v1/library/` | installed list / Blueprint Library |
| `/settings/api/`, `/settings/environment/` | dashboard data |
| `/settings/chats/action/`, `GET /chat/thread/` | REQ-14 |
| `/api/sessions/` | Explorer poll |

---

## Suggested follow-up order (still not this PR)

1. **Honesty (D-01, D-02)** — rename Teams chrome; one href per label.
2. **Settings destination (D-03)** — sheet **or** dashboard, not both; then D-17/D-22.
3. **Session glossary (D-05, D-19)** — name the stores; no merge.
4. **Dead deletion (D-14, D-15, D-16, D-10 unused client)** — small, safe.
5. **Chrome freeze (D-04, D-11, D-20, D-26)** — contract tests only.

Do **not** remount deleted SPA operator pages. Do **not** start a DaisyUI rewrite of `/teams/` until D-01 is named.

---

## Out of scope (per REQ)

- No rewrite of templates, SPA, or views.
- No Neon.
- No deploy.
- No SPA-primary alternative (already rejected in ADR-001).
