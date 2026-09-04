# Wave 1 QA — leftover Django-vs-SPA overlap

Look-only re-read of [django-spa-overlap.md](./django-spa-overlap.md) against
**today’s tree**. No templates, JS, views, SPA pages, tests, or CI were
changed. Existing `docs/debt/*.md` files were not edited.

**As-of:** `origin/main` @ `841e953c` (includes Grok-Bot chrome, REQ-19
settings sheet, REQ-28 team rosters / CoS, REQ-37 compact). Prior overlap
audit was frozen at `4d554ea5` and still describes a mirrored six-tab SPA.

**Method:** static read of `src/swarm/templates/`, operator JS, `urls.py`,
`webui/frontend/src/{App,pages,components,lib,experimental}`, Vite proxy,
FEATURE_STATUS / ADR-001 / GLOSSARY. No Neon. No secrets. No live LAN
URLs or tokens.

**How to read the ranks**

| Rank | Meaning here |
|------|----------------|
| **must-fix** | Two sources of truth for the same screen/behavior, or an operator can mutate / land on the wrong noun. Still true today. |
| **nice** | Dual implementation, dead weight, or chrome tax. Real, but not a wrong-store lie. |
| **obsolete** | Prior D-item is no longer true after Grok chrome / REQ-19 / REQ-28. |
| **intentional** | CLI vs API vs remote (or REST vs operator UI). Must stay even if Django HTML is deleted. |

Prior IDs `D-01`…`D-26` are mapped, not rewritten. New collisions since
that audit use `N-` ids.

---

## Snapshot vs the leftover notes

| Surface | Prior audit (`4d554ea5`) | Today (`841e953c`) |
|---------|--------------------------|--------------------|
| SPA routes | `/` = `Dashboard`, `/chat` = Chat | `/` and `/chat` both mount `ChatPage`. `Dashboard.tsx` is **unrouted**. |
| SPA chrome | Six-link top-nav + five-tab dock mirroring Django | **Gone.** Left rail + chat. E2E `chrome.spec.ts` asserts no `Primary` nav. |
| Settings | Intended DaisyUI `modal-end` unused | `SettingsSheet.tsx` **is** the sheet (REQ-19). Django `/settings/` **also** remains. |
| Teams in SPA nav | Top-nav → `/teams/launch/`; sidebar foot → `/teams/` | No SPA top-nav. Split moved to Search / Command / Chat dropdown. |
| Team noun | Alias **or** launcher **or** Swarm Creator | **Plus** composition rosters (`/v1/team-rosters/`, rail + `?team=`). |
| Auth | Agent Creator GET public; `/profiles/` public | Both `@login_required`. Launcher still public; admin still gated. |
| ADR-001 text | SPA retains `/` (dashboard) + `/chat` | Code: `/` is chat. Doc line is stale. |

Django `base.html` is **unchanged IA**: Home · Chat · Blueprints · Teams ·
Sessions · Settings, plus a five-tab dock that still claims it “matches SPA.”
The comment at `base.html` is now false.

---

## Ranked index

| ID | Rank | Sev | Status | One-line |
|----|------|-----|--------|----------|
| Q-01 | must-fix | P0 | still-true (worse) | “Team” is four products; nav word is still one |
| Q-02 | must-fix | P0 | still-true | Same label “Teams” → `/teams/launch/` **or** `/teams/` |
| Q-03 | must-fix | P0 | still-true (inverted) | Settings sheet **and** Django dump; retention writes two stores |
| Q-04 | must-fix | P1 | new | Hostname: rail `swarm_hostname` vs sheet `swarm_hostname_override` |
| Q-05 | must-fix | P1 | new | Roster “Manage Teams” hops to LLM-alias admin, not rosters |
| Q-06 | nice | P1 | changed | Chrome is **asymmetric**, not mirrored (D-04) |
| Q-07 | nice | P1 | still-true | “Session” is still five meanings (D-05) |
| Q-08 | nice | P1 | changed | Two Homes: live Chat vs Django fallback `index.html` + orphan Dashboard |
| Q-09 | nice | P1 | still-true | Swarm Creator vs alias admin vs Blueprint Library (D-07) |
| Q-10 | nice | P1 | still-true | Full-page hops; Vite `/agent-creator/` page still unproxied (D-08) |
| Q-11 | nice | P1 | still-true | SPA Chat parses HTMX HTML; HTMX loaded unused on operator pages (D-09) |
| Q-12 | nice | P1 | still-true | SPA-parity APIs + unused `api.ts` CRUD; `fetchTeamRosters` duplicated (D-10) |
| Q-13 | nice | P1 | still-true | Dual agent sidebars, now both load rosters/CoS (D-11) |
| Q-14 | nice | P1 | changed | Settings vs `/profiles/` — both login-gated, still two UIs (D-12) |
| Q-15 | nice | P1 | changed | Public launcher vs gated admin/settings/chat restore (D-13) |
| Q-16 | nice | P2 | still-true | Dead `account/signup.html` (D-14) |
| Q-17 | nice | P2 | still-true | Dead `core_views.py` (D-15) |
| Q-18 | nice | P2 | still-true | Dead `dropdown.js`; `dropdown.css` still linked (D-16) |
| Q-19 | nice | P2 | still-true | `django_chat` third chat page (D-18) |
| Q-20 | nice | P2 | still-true (worse) | Stale ADR/GLOSSARY/`base.html` comment (D-19) |
| Q-21 | nice | P2 | still-true | Duplicated `os-action-card` CSS (D-20) |
| Q-22 | nice | P2 | still-true | Bare `/team-creator` missing redirect + fallback exclusion (D-21) |
| Q-23 | nice | P2 | still-true (Django) | Settings missing from Django mobile dock (D-22) |
| Q-24 | nice | P2 | still-true | Login mini-shell (D-23) |
| Q-25 | nice | P2 | still-true | `rest_mode` static fossil (D-24) |
| Q-26 | nice | P2 | changed | Command palette vs Search palette disagree on Settings/Teams (D-25) |
| Q-27 | nice | P2 | still-true | Theme attributes: `data-theme` vs `data-bs-theme` (D-26) |
| Q-28 | obsolete | — | obsolete | SPA six-tab top-nav + dock mirroring Django (D-04 SPA half, D-22 SPA) |
| Q-29 | obsolete | — | obsolete | Settings `modal-end` unused / DaisyUI Modal unused (D-03, D-17) |
| Q-30 | obsolete | — | obsolete | Agent Creator GET + Profiles were public (part of D-13) |
| I-01 | intentional | — | keep | `/v1/teams` aliases ≠ `/v1/team-rosters` composition |
| I-02 | intentional | — | keep | CLI vs API vs remote vs `herdr` members |
| I-03 | intentional | — | keep | Session Explorer (`/v1/responses`) ≠ Chat threads |
| I-04 | intentional | — | keep | Django `/admin/`, login, REST, WS transport |

---

## Must-fix

### Q-01 — “Team” is four products under one word (D-01, worse)

| | |
|--|--|
| **Rank / sev** | must-fix / P0 |
| **Status** | **still-true**, worse after REQ-28 |
| **Django** | `/teams/` + `/v1/teams/` = LLM-profile aliases (`teams_admin.html`, `teams_api.py`, `teams.json`). `/teams/launch/` runs a **blueprint** as “Team Blueprint.” `/team-creator/` Swarm Creator writes a multi-bot Python blueprint. |
| **SPA** | Left rail loads **composition rosters** from `/team_rosters.json` + `/v1/team-rosters/` (`teamRosters.ts`, `AgentSidebar.tsx`). Team chat is `/chat?team=`. Orphan `Dashboard.tsx` still says “Stand up a blueprint team and expose it as an API model.” |
| **Evidence** | `docs/GLOSSARY.md` already splits Team (handoff) / Profiles (`/teams/`) / Team roster. `teamRosters.ts` comment: “never the Django LLM-alias `/v1/teams/` admin registry.” `base.html` top-nav label is still **Teams** → launcher. |
| **Why this is still a lie** | Four stores, one word. REQ-28 added the composition object the glossary wanted, but chrome still says Teams and still points at launcher or alias admin. |

### Q-02 — Same chrome label “Teams” points at two Django URLs (D-02)

| | |
|--|--|
| **Rank / sev** | must-fix / P0 |
| **Status** | **still-true** on Django; **moved** on SPA (nav gone, palettes re-split) |
| **Django** | Top-nav + mobile dock **Teams** → `/teams/launch/`. Sidebar foot **Teams** → `/teams/`. Bare `/teams` RedirectView → `/teams/launch/` (`spa_teams_to_django`). |
| **SPA** | SearchPalette Actions **Teams** → `/teams/launch/`. CommandPalette **Launch a Team** → `/teams/launch/` and **Manage Teams** → `/teams/`. Chat team `<select>` **Manage Teams** → `/teams/` (`MANAGE_TEAMS_HREF`). Herdr rows → `/teams/#herdr-members`. |
| **Evidence** | `src/swarm/templates/base.html` (nav vs `os-agent-sidebar__foot`). `SearchPalette.tsx` Actions. `CommandPalette.tsx`. `teamRosters.ts` `MANAGE_TEAMS_HREF`. `urls.py` `spa_teams_to_django`. |
| **Why** | Operators following “Teams” still cannot predict alias registry vs launcher. SPA no longer has a competing top-nav, but Search vs Command vs Chat dropdown recreate the same fork. |

### Q-03 — Settings is now two products that both write “retention” (D-03 inverted)

| | |
|--|--|
| **Rank / sev** | must-fix / P0 |
| **Status** | **still-true as overlap**; prior “sheet unused” claim is **obsolete** |
| **Django** | Login-gated Bootstrap dashboard `/settings/` (`settings_dashboard.html` + `settings_dashboard.js`). REQ-14 **server** chat persistence: archive / trash / disk / `SWARM_CHAT_MAX_AGE_DAYS`. Gear in operator chrome is a full-page hop. |
| **SPA** | Gear opens DaisyUI `Modal` `placement="end"` `size="sheet"` (`SettingsSheet.tsx`, REQ-19). Retention pane writes **`localStorage.swarm_retention_mode` only** (`settingsPrefs.ts`: “until a remotes / settings API lands”). Footer link **Operator dump** → `/settings/`. |
| **Evidence** | `SettingsSheet.tsx` file comment: “Django `/settings/` stays the operator dump.” FEATURE_STATUS: sheet exists **and** Django dump remains. Sheet save toast: “stored in this browser.” Django section id `chat-retention-title` posts to `/settings/chats/action/`. |
| **Why** | Prior action was “sheet **or** dashboard, not both.” Today both shipped. Same noun (Settings / Retention); two stores (server files vs localStorage). Operators can think the sheet archived chats when only the dashboard does. |

### Q-04 — Dual hostname keys (new)

| | |
|--|--|
| **Rank / sev** | must-fix / P1 |
| **Status** | **new** (post–Grok chrome) |
| **Django** | No hostname editor in operator chrome. |
| **SPA** | Rail footer uses `hostname.ts` key **`swarm_hostname`**. Settings sheet Hostname pane uses `settingsPrefs.ts` key **`swarm_hostname_override`**. |
| **Evidence** | `AgentSidebar.tsx` `loadHostname` / `saveHostname`. `SettingsSheet.tsx` `loadHostnameOverride` / `saveHostnameOverride`. Two modules, two keys, one label. |
| **Why** | Two writable sources of truth for the same chrome field. Saving in the sheet does not update the rail, and vice versa. |

### Q-05 — Roster chrome “Manage Teams” opens the alias registry (new)

| | |
|--|--|
| **Rank / sev** | must-fix / P1 |
| **Status** | **new** (REQ-28) |
| **Django** | `/teams/` is alias CRUD (`teams_admin.html`). There is **no** Django roster editor page or nav item. Rosters are API + JSON only (`team_rosters_api.py`, `web_views.team_rosters_json`). |
| **SPA** | Team-thread member `<select>` last option “Manage Teams” assigns `window.location` to `/teams/`. Rail herdr links go to `/teams/#herdr-members` (alias admin fragment). |
| **Evidence** | `teamRosters.ts` (`MANAGE_TEAMS_HREF = '/teams/'` + “Never reads `/v1/teams/`”). `ChatPage.tsx` option. `AgentSidebar.tsx` herdr href. |
| **Why** | The rail’s Team is a roster. The manage href is the other Team. Same class of wrong-store hop as D-01/D-02, now on the new object. |

---

## Nice (still real, not a wrong-noun P0)

### Q-06 — Duplicate chrome, now asymmetric (D-04 changed)

| | |
|--|--|
| **Rank / sev** | nice / P1 |
| **Status** | **changed** — no longer “mirrored IA”; still two shells |
| **Django** | `base.html` + `chrome_theme.js` + `agent_sidebar.js` + `operator.css` / `rest_mode_style.css`. Bootstrap `data-bs-theme` / `data-os-theme`. Font Awesome. Six-tab Primary nav + five-tab dock. |
| **SPA** | `App.tsx` Grok rail + `index.css` DaisyUI `data-theme`. Lucide. No top-nav, no dock. Search palette + settings sheet. |
| **Evidence** | `App.tsx` comment: “Product chrome is Grok-Bot.” `base.html` comment still says “Primary IA matches SPA Home: Home · Chat · …”. Shared keys only: `swarm_theme`, `swarm_hidden_agents`. |
| **Why** | Every chrome tweak still lands twice **or** the hop Home ↔ Teams/Settings looks like a different product. That is now the intended ADR-001 split plus an outdated Django comment. Not two sources for the same screen — two products. |

### Q-07 — “Session” still five meanings (D-05)

| | |
|--|--|
| **Rank / sev** | nice / P1 |
| **Status** | **still-true** |
| **Django** | Login cookie (WS 4401). Session Explorer `/sessions/` over `/v1/responses`. REQ-14 file store + ORM `ChatConversation` mirror. |
| **SPA** | Per-agent WS id in `localStorage` (`swarm_agent_chat:`). Hydrate via `GET /chat/thread/`. Nav **Sessions** (Django) is Explorer only. |
| **Evidence** | Unchanged stores vs prior audit. FEATURE_STATUS still says retention is Settings-only (now ambiguous: which Settings). |
| **Why** | Intentional store split (see I-03) plus missing glossary row for Chat thread vs Explorer. Not two UIs for Explorer. |

### Q-08 — Two Homes + orphan Dashboard (D-06 changed)

| | |
|--|--|
| **Rank / sev** | nice / P1 |
| **Status** | **changed** |
| **Django** | `web_views.index` prefers `dist/index.html`; else `templates/index.html` catalog (Launch Team / Browse / Manage Teams / Settings + recent sessions). |
| **SPA** | Live `/` is `ChatPage`. `Dashboard.tsx` + `Dashboard.test.tsx` still implement the old catalog and hrefs; **no route**. CommandPalette Home hint still says “SPA dashboard.” Vite comment still says catch-all dumps users “on the dashboard.” |
| **Evidence** | `App.tsx` routes; `nav.spec.ts` unknown path → chat; `index.html` cards; `Dashboard.tsx` `QUICK_ACTIONS`. |
| **Why** | Live product is one Home (chat). Fallback + orphan page are still a second catalog if `dist/` is missing or someone remounts Dashboard. |

### Q-09 — Three factories + two libraries (D-07)

| | |
|--|--|
| **Rank / sev** | nice / P1 |
| **Status** | **still-true** (Django-only screens) |
| **Django** | Library `/blueprint-library/`, My Library, Blueprint Creator, Agent Creator `/agent-creator/`, Swarm Creator `/team-creator/`, alias admin `/teams/`. Creators still have **no** nav `href` in `base.html` (Blueprints active-state only). |
| **SPA** | No creator pages (ADR-001). Search/Command hop to library/launch only; still omit Agent/Swarm/Blueprint Creator. |
| **Evidence** | Template inventory unchanged. `team_creator.html` / `agent_creator.html` live routes. |
| **Why** | Same-app factory sprawl, not SPA remount. |

### Q-10 — Full-page hops; Vite `/agent-creator/` page gap (D-08)

| | |
|--|--|
| **Rank / sev** | nice / P1 |
| **Status** | **still-true**; `/team-creator` Vite proxy **fixed** |
| **Django** | Trailing-slash operator pages. |
| **SPA** | React `<Link>` only for `/` and `/chat`. Search/Command/sheet/herdr use `<a href>` or `location.assign`. |
| **Evidence** | `vite.config.ts`: `/team-creator` proxied; `/agent-creator/` **page** not (only `generate` / `validate`). `urls.py` fallback comment still warns about dual-mount. |
| **Why** | ADR-001 accepted the hop. Destaging `/agent-creator/` in Vite still lies (SPA catch-all → Chat). |

### Q-11 — HTMX HTML frames for SPA Chat (D-09)

| | |
|--|--|
| **Rank / sev** | nice / P1 |
| **Status** | **still-true** |
| **Django** | `consumers.py` still `render_to_string("websocket_partials/…")` with `hx-swap-oob`. `base.html` loads `htmx.min.js` + `htmx_csp.js` on every operator page. **No** `hx-` on routable operator templates (only the three partials). |
| **SPA** | Only live Chat UI. `chatWs.ts` DOMParses those frames. |
| **Evidence** | `src/swarm/templates/websocket_partials/*.html`; `consumers.py`; `base.html` script tags. |
| **Why** | Two stacks for one socket. Deleting Django **operator pages** would not fix Chat; deleting **partials** would. |

### Q-12 — Unused SPA client + parity APIs (D-10)

| | |
|--|--|
| **Rank / sev** | nice / P1 |
| **Status** | **still-true**; extra dead `api.ts` `fetchTeamRosters` |
| **Django** | `/v1/teams/`, `/v1/library/`, `/settings/api/`, `/v1/team-rosters/` are real HTTP. |
| **SPA** | Live imports: `fetchBlueprints`, `fetchHerdrAgents`, `fetchBlueprintSource`, `fetchModels`. Unused in `src/`: `fetchTeams` / `createTeam` / `deleteTeam` / `fetchLibrary` / `generateAgentCode` / `fetchServerSettings` / … plus **`api.ts` `fetchTeamRosters`** (live path is `lib/teamRosters.ts`). |
| **Evidence** | Import graph of `webui/frontend/src`. Dashboard (orphan) uses raw `fetch('/v1/teams/')`. |
| **Why** | Remount bait. Public REST must stay (I-01). Unused typed wrappers need not. |

### Q-13 — Dual agent sidebars (D-11)

| | |
|--|--|
| **Rank / sev** | nice / P1 |
| **Status** | **still-true**, both now load rosters/CoS |
| **Django** | `agent_sidebar.js`: `swarm_hidden_agents`, `/v1/blueprints`, `/team_rosters.json` + `/v1/team-rosters/`, CoS role badges. Footer Teams/Settings stay in `base.html`. |
| **SPA** | `AgentSidebar.tsx` + `hiddenAgents.ts` + `teamRosters.ts`. Footer is Plugins + hostname (no Teams/Settings). |
| **Evidence** | Parallel URL lists and hide key. `test_req28_cos_chrome.py` locks both CSS ports. |
| **Why** | Same contract, two UIs. Feature-parity improved; maintenance tax did not shrink. |

### Q-14 — Settings dashboard vs `/profiles/` (D-12)

| | |
|--|--|
| **Rank / sev** | nice / P1 |
| **Status** | **changed** — Profiles now `@login_required`; still two pages |
| **Django** | `/settings/` card → `/profiles/` Bootstrap table. |
| **SPA** | Sheet LLM pane lists `/v1/models/` and links out to `/profiles/` + `/settings/`. |
| **Evidence** | `web_views.profiles_page` decorator; `SettingsSheet.tsx` `LlmProfilesPane`. |
| **Why** | Two operator UIs for profiles; SPA is read-only + hop. |

### Q-15 — Auth split across the same nouns (D-13)

| | |
|--|--|
| **Rank / sev** | nice / P1 |
| **Status** | **changed** (creators + profiles gated); launcher/admin split **still-true** |
| **Django** | `team_launcher` public; `team_admin`, settings, sessions, library, both creators, profiles **login_required**. |
| **SPA** | Chat WS still session-cookie; bearer works for `/v1/*` not `/chat`. |
| **Evidence** | View decorators in `web_views.py`, `agent_creator_views.py`, `settings_views.py`, `session_explorer.py`. |
| **Why** | Correct AUTH.md rules. Hybrid chrome still makes “Teams” feel like two apps. |

### Q-16 — Dead `account/signup.html` (D-14)

| | |
|--|--|
| **Rank / sev** | nice / P2 |
| **Status** | **still-true** |
| **Django** | `src/swarm/templates/account/signup.html` — no URL; `{% block head %}` missing on `base.html`; `{% url 'account_login' %}` missing; `css/custom.css` missing. |
| **SPA** | n/a |
| **Evidence** | Template exists; `urls.py` has `login` / `custom_login` only. |

### Q-17 — Dead `core_views.py` (D-15)

| | |
|--|--|
| **Rank / sev** | nice / P2 |
| **Status** | **still-true** |
| **Django** | Renders missing `swarm/index.html` / `swarm/login.html`. Not in `urls.py`. Optional import in `views/__init__.py`. Live login is `web_views.custom_login`. |
| **SPA** | n/a |

### Q-18 — Dead `dropdown.js` + leftover `dropdown.css` (D-16)

| | |
|--|--|
| **Rank / sev** | nice / P2 |
| **Status** | **still-true**; CSS now looks fully orphaned |
| **Django** | `dropdown.js` has zero `<script>` refs (redirects to deleted `/django_chat/<blueprint>/new/`). `base.html` still links `dropdown.css`. No `#blueprintDropdown` in templates. |
| **SPA** | n/a |

### Q-19 — `django_chat` third chat UI (D-18)

| | |
|--|--|
| **Rank / sev** | nice / P2 |
| **Status** | **still-true** |
| **Django** | Blueprint webpage `blueprints/django_chat/templates/django_chat/django_chat_webpage.html` at `/django_chat/`. |
| **SPA** | Product Chat is `/` + `/chat` only. |
| **Why** | Discoverable demo, not operator chrome. Keep as a blueprint unless labeled. |

### Q-20 — Stale docs after Grok chrome (D-19, worse)

| | |
|--|--|
| **Rank / sev** | nice / P2 |
| **Status** | **still-true**, and the leftover overlap doc itself is stale |
| **Django / SPA** | `docs/ADR-001-primary-ui.md`: “SPA retains `/` (dashboard)”. `docs/GLOSSARY.md` Operator UI table: same. `base.html` “Primary IA matches SPA Home”. `django-spa-overlap.md` as-of `4d554ea5`. `chatWs.ts` / `websocket_chat.md` still mention `chat.html`. Vite comment: catch-all → dashboard. CommandPalette Home hint: “SPA dashboard.” |
| **Why** | Docs describe a dual-mount world ADR-001 ended, then Grok chrome ended the mirrored nav. This file is the QA pass; do not edit those docs here. |

### Q-21 — Duplicated `os-action-card` CSS (D-20)

| | |
|--|--|
| **Rank / sev** | nice / P2 |
| **Status** | **still-true**; live SPA usage dropped (Dashboard unmounted) |
| **Django** | `rest_mode_style.css` (also fallback Home cards). |
| **SPA** | `index.css` (orphan Dashboard + tests). Slight drift (`11rem` vs `11.5rem`). |
| **Evidence** | `tests/unit/test_req5_chrome_shell.py` still locks both. |

### Q-22 — `team-creator` fallback / redirect gap (D-21)

| | |
|--|--|
| **Rank / sev** | nice / P2 |
| **Status** | **still-true** in production URLconf; Vite **fixed** |
| **Django** | `/team-creator/` registered. Bare `/team-creator` has **no** RedirectView twin. SPA fallback negative lookahead **omits** `team-creator/`. |
| **SPA** | Catch-all → Chat. Vite proxies `/team-creator`. |
| **Evidence** | `urls.py` redirect list vs fallback regex. |

### Q-23 — Settings missing from Django mobile dock (D-22)

| | |
|--|--|
| **Rank / sev** | nice / P2 |
| **Status** | **still-true** for Django; **obsolete** for SPA (no dock) |
| **Django** | Five tabs: Home, Chat, Blueprints, Teams, Sessions. REQ-14 retention is dashboard-only. |
| **SPA** | Gear → sheet. No dock. |

### Q-24 — Login mini-shell (D-23)

| | |
|--|--|
| **Rank / sev** | nice / P2 |
| **Status** | **still-true** |
| **Django** | `account/login.html` standalone (`operator.css` only). No AGENTS rail, no IA, no theme toggle. |
| **SPA** | Sign-in links hop to `/accounts/login/`. |

### Q-25 — `rest_mode` static fossil (D-24)

| | |
|--|--|
| **Rank / sev** | nice / P2 |
| **Status** | **still-true** |
| **Django** | `src/swarm/static/rest_mode/**` not linked from `base.html`. Kept for XSS tests. |
| **SPA** | n/a |

### Q-26 — Two palettes, disagreeing destinations (D-25 changed)

| | |
|--|--|
| **Rank / sev** | nice / P2 |
| **Status** | **changed** — Settings in CommandPalette opens the sheet; Search still hops to Django |
| **Django** | n/a (destinations are Django URLs) |
| **SPA** | `SearchPalette.tsx` (product) vs `CommandPalette.tsx` (experimental, default-ON). Search: Teams → launch, Settings → `/settings/`. Command: Launch vs Manage Teams; Settings → `swarm:open-settings`; Home hint “SPA dashboard.” Both omit creators + Profiles. |
| **Why** | Third copy of the operator catalog, and the two copies disagree. |

### Q-27 — Theme attribute split (D-26)

| | |
|--|--|
| **Rank / sev** | nice / P2 |
| **Status** | **still-true** |
| **Django** | `chrome_theme.js` sets `data-bs-theme` + `data-os-theme`. |
| **SPA** | `applyDocumentTheme` sets `data-theme` + inline `backgroundColor`. |
| **Shared** | `localStorage.swarm_theme` / `THEME_STORAGE_KEY`. |
| **Why** | Harmless while shells never coexist in one document. |

---

## Obsolete (do not plan cleanup as if these were still true)

### Q-28 — SPA six-tab top-nav + mobile dock (D-04 SPA half, D-22 SPA)

| | |
|--|--|
| **Status** | **obsolete** |
| **Django** | Still has Primary nav + dock. |
| **SPA** | Removed. `App.tsx` is rail + chat. `chrome.spec.ts`: `navigation[name="Primary"]` count 0. |
| **Why listed** | Prior overlap treated mirrored IA as the tax. SPA half is gone. Remaining tax is Q-06 (asymmetric shells), not a second six-tab bar. |

### Q-29 — Settings sheet / DaisyUI Modal unused (D-03 as written, D-17)

| | |
|--|--|
| **Status** | **obsolete** |
| **Django** | Dashboard never used DaisyUI Modal (unchanged). |
| **SPA** | `SettingsSheet` mounts `Modal` `placement="end"`. Input / Button / Alert used. Tabs / Pagination / FormValidation / ConfirmModal remain test-only (that leftover is webui-debt P1-1, not “sheet missing”). |
| **Why listed** | Prior action “build the sheet or drop the story” — sheet shipped. Overlap **moved** to Q-03 (two Settings products). |

### Q-30 — Agent Creator GET + Profiles were public (part of D-13)

| | |
|--|--|
| **Status** | **obsolete** |
| **Django** | `agent_creator_page`, `team_creator_page`, `profiles_page` are `@login_required`. |
| **SPA** | n/a |
| **Why listed** | Leftover notes overstate the public surface. Launcher-vs-admin (Q-15) remains. |

Also obsolete as *live product* claims (see Q-08): “SPA Home is the Dashboard catalog.” Live `/` is Chat. Dashboard is remount bait only.

---

## Intentional splits (must stay)

These are **not** two UIs for the same screen. Deleting Django HTML must not delete them.

### I-01 — `/v1/teams` aliases vs `/v1/team-rosters` composition

| | |
|--|--|
| **Django HTML** | Alias admin at `/teams/` is a UI over `teams.json`. No roster HTML page. |
| **SPA** | Rail/chat consume rosters only (`teamRosters.ts`). |
| **Keep** | `GET/POST/DELETE /v1/teams/`, `GET /v1/team-rosters/`, `team_rosters.json`, CLI/API that write those files. Different nouns (GLOSSARY). The **bug** is chrome labels (Q-01/Q-02/Q-05), not the two APIs. |

### I-02 — CLI vs API vs remote vs `herdr` members

| | |
|--|--|
| **Django HTML** | Herdr blocks on `teams_admin.html` / settings group. |
| **SPA** | Rail herdr rows; remotes panes in the sheet are stubs. |
| **Keep** | Member kinds `api|cli|remote|team|herdr` in roster JSON, `swarm-cli remotes`, Herdr CLI wiring. This is composition, not a duplicate Teams screen. |

### I-03 — Session Explorer vs Chat threads

| | |
|--|--|
| **Django HTML** | `/sessions/` observability over `/v1/responses`. |
| **SPA** | Per-agent / per-team websocket threads + REQ-14 JSON. |
| **Keep** | `/v1/responses`, Explorer APIs, `GET /chat/thread/`, `POST /settings/chats/action/`, `POST /chat/compact/`. Do not merge stores to “clean overlap.” |

### I-04 — Admin, auth, REST, WS transport

| | |
|--|--|
| **Keep** | Django `/admin/`. `custom_login` (some login template). OpenAI-style `/v1/*`. WS consumer + routing. Settings/environment JSON used by tests and operator dump. MCP / marketplace URL prefixes if still served. |
| **Not optional HTML** | `websocket_partials/*` are the live Chat protocol until a JSON-frame REQ. Deleting them **is** deleting SPA Chat, not leftover operator UI. |

---

## If we deleted the Django path tomorrow

“Django path” here means operator **templates + `base.html` chrome + page JS**,
not Django-the-process (REST, admin, auth, WS).

### Breaks immediately (do not delete)

| What | Why |
|------|-----|
| `/teams/`, `/teams/launch/`, `/blueprint-library/**`, `/agent-creator/`, `/team-creator/`, `/settings/`, `/profiles/`, `/sessions/**` | Only Django templates render these screens. SPA hops 404 or hit Chat catch-all. |
| SearchPalette / CommandPalette / sheet “Operator dump” / herdr `/teams/#herdr-members` / Chat “Manage Teams” | All are full-page hrefs into those templates. |
| REQ-14 archive/trash/disk **UI** | Server endpoints can stay; the only operator surface that POSTs them is `settings_dashboard.js`. The SPA sheet does **not** call them. |
| Login page | `account/login.html` is the gate for admin/settings/chat restore. |
| Fallback Home | `templates/index.html` when `dist/` is missing. |
| **`websocket_partials/*`** | SPA Chat parsing. This is not optional chrome. |
| `base.html` + operator static if those pages stay | No shell for leftover Django routes. |

### Must stay even if operator HTML dies

| What | Paths |
|------|--------|
| REST / OpenAI-style | `/v1/teams/`, `/v1/library/`, `/v1/team-rosters/`, `/v1/blueprints`, `/v1/models/`, `/v1/chat/completions`, `/v1/responses`, … |
| Chat persist / compact | `/settings/chats/action/`, `GET /chat/thread/`, `/chat/compact/` |
| Settings JSON (tests + future sheet) | `/settings/api/`, `/settings/environment/` |
| Django admin | `/admin/` |
| Auth | `web_views.custom_login` + **a** login template |
| WS transport | `consumers.py` + routing (**plus** partials or a JSON replacement) |
| File stores | `teams.json`, `team_rosters.json`, `SWARM_CHAT_DIR` |
| SPA shell | `webui/frontend` `dist/` for `/` + `/chat` |
| Blueprint-local UIs | `django_chat` lives under `blueprints/`, not `templates/` |

### Safe to delete later (does not serve REST/admin)

| Item | Notes |
|------|--------|
| `account/signup.html` | No URL (Q-16) |
| `core_views.py` + optional import | Dead (Q-17) |
| `dropdown.js` (+ likely `dropdown.css` link) | Dead (Q-18) |
| Orphan `Dashboard.tsx` + its unit test | Not routed (Q-08) |
| Unused `api.ts` wrappers | Keep `/v1/teams` **server**; drop unused client (Q-12) |
| `rest_mode` static | Runtime-safe; update XSS tests first (Q-25) |
| Unused DaisyUI Tabs/Pagination/FormValidation | Sheet uses Modal; museum remains (Q-29 leftover) |

Deleting **all** Django operator HTML without replacing hops would break
Search/Settings-dump/Herdr-admin/launcher/library. That is not “SPA already
owns it.” SPA owns Chat + a **partial** settings sheet. ADR-001 still makes
Django canonical for operator back-office.

---

## Inventory (today, evidence only)

### Django templates (`src/swarm/templates/`)

| File | Role | Live? |
|------|------|-------|
| `base.html` | Operator shell (6-nav + dock + sidebar foot) | Yes |
| `index.html` | Home if SPA `dist/` absent | Fallback only |
| `teams_launch.html` | Launcher | Yes |
| `teams_admin.html` | Alias registry (+ herdr fragment) | Yes |
| `team_creator.html` | Swarm Creator | Yes, **no nav href** |
| `agent_creator.html` | Agent Creator | Yes, **no nav href** |
| `blueprint_library.html` / `_card` / `_creator` / `my_blueprints.html` | Catalog | Yes |
| `settings_dashboard.html` | Settings + REQ-14 retention | Yes |
| `profiles.html` | LLM profile table (now login-gated) | Yes |
| `session_explorer.html` / `session_detail.html` | Explorer | Yes |
| `account/login.html` | Login | Yes |
| `account/signup.html` | Signup | **Dead** |
| `websocket_partials/*` | WS HTML frames | Used by consumer |

Still gone: `chat.html`, `simple_blueprint_page.html`, `swarm/index.html`,
`swarm/login.html`. **No** new roster template after REQ-28.

### SPA (`webui/frontend`)

| Route | Page |
|-------|------|
| `/`, `/chat`, `/chat/*` | `ChatPage.tsx` |
| `/agents`, `/agents/*` | Navigate → `/chat` |
| `*` | Navigate → `/` (chat) |

Unrouted: `Dashboard.tsx`. Deleted pages still gone: TeamsPage,
BlueprintsPage, SettingsPage, BuilderPage, AgentCreatorPage.

Overlays (not routes): `SettingsSheet`, `SearchPalette`, experimental
`CommandPalette`, computer-control stub.

### Live SPA → Django exits

```
/teams/launch/          SearchPalette Actions “Teams”; CommandPalette Launch
/teams/                 CommandPalette Manage; Chat “Manage Teams”
/teams/#herdr-members   AgentSidebar herdr rows
/settings/              SearchPalette Settings; SettingsSheet “Operator dump”
/profiles/              SettingsSheet LLM pane links
/blueprint-library/     Search / Command
/sessions/              CommandPalette only
/accounts/login/        Chat sign-in gate
/agent-creator/         no SPA chrome href (Vite page proxy still missing)
```

---

## Suggested follow-up order (not this PR)

1. **Honesty (Q-01, Q-02, Q-05)** — one label per href; stop sending roster
   “Manage” to `/v1/teams` admin. Keep both APIs (I-01).
2. **Settings destination (Q-03, Q-04)** — one retention store; one hostname
   key. Sheet **or** dump for chat-adjacent prefs, not two writers.
3. **Dead deletion (Q-16, Q-17, Q-18, Q-08 orphan Dashboard, Q-12 unused
   client)** — small, safe, does not require an ADR.
4. **Doc pass (Q-20)** — ADR-001 `/` is chat; strike `base.html` “matches SPA
   Home”; glossary Chat-thread row. Separate PR; do not fold into product.
5. **Chrome freeze (Q-06, Q-13, Q-27)** — contract tests only. Do not remount
   a six-tab SPA to match Django.

Do **not** remount deleted SPA operator pages. Do **not** delete Django
operator HTML until hops in Search/sheet/herdr have a home. Do **not**
delete `websocket_partials` without a Chat protocol REQ.

---

## Out of scope (this wave)

- No rewrite of templates, SPA, views, tests, or CI.
- No edit of existing `docs/debt/*.md`.
- No rebase / squash / fold into other PRs.
- No Neon. No host bounce. No secrets or live LAN URLs.
- No SPA-primary alternative (already rejected in ADR-001).
