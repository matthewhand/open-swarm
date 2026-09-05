# Wave 2 QA — django_chat / webui-in-blueprint map

> **Implemented (#419):** the `django_chat` package, catalog id, logger, and
> leftover tests were deleted. Blueprints are CLI/API only. This file stays a
> look-only snapshot of the pre-delete map.

Look-only inventory for later **#419** (REQ-74: blueprints are CLI/API only;
retire webui blueprints / django-chat). No templates, views, SPA, tests, CI,
or existing `docs/debt/*.md` were changed.

**As-of:** `origin/main` @ `dfd72eef`. django_chat sources match that tip.
Wave 1 leftover notes are [qa-wave1-django-spa.md](./qa-wave1-django-spa.md)
on PR 429 (unmerged at this audit). Core finding is [core.md](./core.md)
index row 16 / section **P1-12**.

**Method:** static read of `src/swarm/blueprints/django_chat/`,
`src/swarm/urls.py`, discovery, Settings / catalog / launcher pickers,
other blueprint `apps.py` / `templates/`, and the docs that still name
`django_chat`. No Neon. No host bounce. No `:8001`. No secrets or live
LAN URLs.

**How to read the ranks**

| Rank | Meaning here |
|------|----------------|
| **must-fix** | Still offered as a webui-shaped blueprint, or import-time Django boot, or docs that teach the old model. Blocks #419 success. |
| **nice** | Dead files, duplicate helpers, or naming leftovers. Real, but the second chat shell is already unmounted. |
| **obsolete** | Prior note is no longer true (live `/django_chat/` page, explicit `kind=webui` enum). |
| **intentional** | CLI/API recipes, product Grok chrome, chat stores, REST. Must stay when webui-as-blueprint dies. |

Action vocabulary (for a **later** ticket, not this PR): **leave** / **wrap** /
**delete**.

**#420** (roles in blueprint metadata) is out of scope except one line:
nothing in the role story blocks retiring webui blueprints.

---

## Verdict

The only blueprint that ships a webpage is `django_chat`. That webpage is
**already unmounted**: `urls.py` never includes it, the Django app is not
installed, and `urls_module` / `url_prefix` are not consumed. Wave 1 Q-19
overstated a live third chat page at `/django_chat/`.

What remains is worse for #419 than a dead template: the package is still a
discoverable `/v1/models` + launcher + library + sidebar id, its **module
import calls `django.setup()`**, docs still say “web chat”, and `run()` is a
thin LLM proxy that duplicates `dynamic_team` while advertising HTTP-only.

**Product decision vs core.md:** [core.md](./core.md) P1-12 said **wrap**
(move views out; keep a thin recipe). #419 prefers **delete** if nothing
else depends on it. This map agrees with #419: nothing unique depends on
the webpage, and the API `run()` is not a distinct recipe.

---

## Cross-walk

| Prior note | This pass |
|------------|-----------|
| Wave 1 **Q-19** / leftover **D-18** — `django_chat` third chat UI at `/django_chat/`, rank nice/P2, “keep as a blueprint unless labeled” | **Corrected.** Files exist; **route is not mounted**. Product Chat is `/` + `/chat`. Rank for a *live* third page: **obsolete**. Rank for leftover identity + import: **must-fix** (W-01, W-02). Wave 1 “must stay if operator HTML dies” listed blueprint-local UIs — that was “do not delete with Django chrome,” not “keep as a WebUI.” #419 inverts the keep. |
| Wave 1 **Q-18** / **D-16** — dead `dropdown.js` → `/django_chat/<blueprint>/new/` | **Still-true.** Zero `<script>` refs. Same later-delete as wave 1. |
| Wave 1 **Q-16** — dead `account/signup.html` title “Sign Up - django_chat” | **Still-true.** Cosmetic leftover on a dead page. |
| Wave 1 “If Django HTML deleted / must stay” — `django_chat` lives under `blueprints/` | **Re-rank.** Stay-as-operator-HTML: n/a (not operator chrome). Stay-as-CLI/API: only if #419 chooses wrap. Prefer **delete**. |
| [core.md](./core.md) index **#16 / P1** — `django.setup()` at import; section heading **P1-12** | **Still-true.** Numbering drift: table row 16 vs section P1-12. Trigger is `discover_blueprints()` (`exec_module`), **not** `swarm-cli list` (directory scan only). |
| [core.md](./core.md) inventory — `django_chat` “rejects CLI / wrap out of default discovery” | **Still-true** as behavior; #419 prefer-remove supersedes wrap-as-the-goal. |
| #419 success: no blueprint webpage; catalog/picker/Settings offer no webui kind; creating an agent never mounts a second chat UI | Webpage already unmounted. Catalog still offers the **id**. No `kind=webui` enum exists. Creating an agent already opens product Chat / `/v1/chat/completions`, not `/django_chat/`. |
| #420 roles/workflows in blueprint metadata | `software_dev` already declares seats/roles. `django_chat` has no role. **Does not block #419.** |

---

## Ranked index

| ID | Rank | Sev | Status | Action later | One-line |
|----|------|-----|--------|--------------|----------|
| W-01 | must-fix | P1 | still-true | delete (or wrap) | `django_chat` still a catalog / `/v1/models` / launcher / sidebar id |
| W-02 | must-fix | P1 | still-true (core P1-12) | delete or wrap | `django.setup()` at import on discovery |
| W-03 | must-fix | P2 | still-true | delete rows | Docs teach “web chat” / HTTP-only blueprint |
| W-04 | nice | P2 | still-true | delete | Unmounted package: views/urls/templates/`apps.py` |
| W-05 | nice | P2 | still-true | delete | Dead `__main__` / spinner; duplicate class view |
| W-06 | nice | P2 | still-true | delete | Tests that only exist for this package / default-user |
| W-07 | nice | P2 | still-true | delete | `dropdown.js` `/django_chat/…/new/` (wave 1 Q-18) |
| W-08 | nice | P2 | still-true | delete | Dead signup title “django_chat” (wave 1 Q-16) |
| W-09 | nice | P2 | still-true | wrap/delete tag | Swarm Creator stamps `tags: ["swarm", "webui"]` |
| W-10 | nice | P2 | still-true | delete | Settings logger `blueprint_django_chat` |
| W-11 | nice | P2 | still-true | leave | Stewie comment only (django_chat-style config bug) |
| W-12 | nice | P2 | historical | leave or archive | `docs/examples/webui-config-panels.md` is deleted SPA Builder, not django_chat |
| W-13 | obsolete | — | obsolete | — | Live mounted `/django_chat/` webpage (wave 1 Q-19 as written) |
| W-14 | obsolete | — | obsolete | — | Settings / picker `kind=webui` enum |
| W-15 | obsolete | — | obsolete | — | Other leftover `apps.py` (gawd / zeus / whiskeytango) as webpages |
| W-16 | obsolete | — | obsolete | — | `messenger` stub UI (already deleted) |
| I-01 | intentional | — | keep | leave | `ChatConversation` / `ChatMessage` (WS + REQ-14 mirror) |
| I-02 | intentional | — | keep | leave | Product Grok chrome `/` + `/chat`; `/webui/` redirect; `ENABLE_WEBUI` |
| I-03 | intentional | — | keep | leave | `/v1/blueprints`, `/v1/models`, `/v1/chat/completions` machinery |
| I-04 | intentional | — | keep | leave | Other blueprints as CLI/API recipes (`software_dev` roles = #420) |
| I-05 | intentional | — | keep | leave | `django.setup()` in `scripts/demo_*.py` / `prove_*.py` (not a blueprint) |
| I-06 | intentional | — | keep | leave | Settings sheet Blueprint **editor** (role-agent source) — #420, not a webui kind |
| I-07 | intentional | — | keep | leave | `harness_fleet` host label `kind: "hermes webui"` — remote, not a blueprint kind |

---

## Must-fix

### W-01 — Catalog still offers `django_chat` as a blueprint id

| | |
|--|--|
| **Rank / sev** | must-fix / P1 |
| **#419** | Success 2: catalog / picker / Settings must not offer a webui / django-chat kind. |
| **What it is** | There is **no** `kind=webui` field anywhere. The leftover is the **id** itself. |
| **Surfaces** | `discover_blueprints()` registers the directory. `/v1/blueprints` and `/v1/models` list it. Team launcher `teams_launch.js` fills `<select>` from those APIs (no kind filter). Blueprint library cards it with fallback copy “Blueprint for django_chat” (`BLUEPRINT_METADATA` has no dedicated row). Django operator `agent_sidebar.js` concatenates `/v1/blueprints` into the agent list. Library **Launch** → `/teams/launch/?blueprint=django_chat`. Runner **Open in Chat** → `/chat?blueprint=django_chat`. `swarm-cli list` prints the directory (entry `blueprint_django_chat.py`) without importing it. Settings group **Blueprints & Agents** is a config dump (`ENABLED_BLUEPRINTS` / defaults / timeout), not a kind picker — it does not add a webui kind, and it does not hide this id from discovery. |
| **Creating an agent** | Does **not** mount a second chat shell. Completions + SPA Chat use `model: "django_chat"`. That already matches “never mounts a second UI.” The lie is offering a webui-shaped recipe in the same list as CLI/API recipes. |
| **Action later** | **delete** the package (preferred). If wrap: drop from default discovery / `/v1/models` and stop HTTP-only copy. |

### W-02 — `django.setup()` at import (core.md P1-12)

| | |
|--|--|
| **Rank / sev** | must-fix / P1 |
| **Path** | `src/swarm/blueprints/django_chat/blueprint_django_chat.py` (sets `DJANGO_SETTINGS_MODULE`, then `django.setup()` before any class). |
| **Why** | `discover_blueprints()` `exec_module`s that file. `/v1/models`, `/v1/blueprints`, blueprint library, fallback Home, and instance load therefore boot Django as a side effect of *finding* the recipe. In an already-configured Django process `setup()` is mostly idempotent; from a non-server importer it is a hidden ASGI/ORM boot. |
| **Correction to core.md** | `swarm-cli list` does **not** import modules (directory + `find_entry_point` only). The import-time setup fires on **discovery**, not on the list command. |
| **Metadata wrinkle** | `metadata` is an instance `@property`, not a class dict. Discovery `getattr(cls, "metadata")` sees a `property`, discards it, and registers `name=django_chat` with empty description. `urls_module` / `url_prefix` never reach `/v1/blueprints`. Import still runs `django.setup()`. |
| **Action later** | **delete** the module, or **wrap** to a recipe that does not call `django.setup()` and uses a class-level `metadata` dict like every other blueprint. |

### W-03 — Docs still teach web-chat-as-blueprint

| | |
|--|--|
| **Rank / sev** | must-fix / P2 |
| **#419** | Success 3: BLUEPRINT_* / USERGUIDE / README say blueprints = CLI/API; web UI is Grok chrome. |
| **Paths** | `docs/BLUEPRINT_LIBRARY.md` (“Web chat with conversation-history management”, green). `FEATURE_STATUS.md` §9 (views/urls/templates). `src/swarm/blueprints/README.md`. `docs/technical/blueprint_guide.md`. `docs/USER_JOURNEY.md` (bundled list, launcher example, `/v1/models` sample id). `ROADMAP.md` / `CHANGELOG.md` historical LLM-stub rows (leave as history or one-line strike). Archive `FEATURE_STATUS_2026-06-10.md` is already archive. |
| **Not this** | `docs/examples/webui-config-panels.md` is the **deleted SPA Builder** capture log (W-12). It does not teach django_chat. #419’s “delete or redirect if it teaches blueprint-as-builder-UI” is already marked historical; do not treat it as a live webui blueprint. |
| **Action later** | **delete** live catalog rows; one sentence in BLUEPRINT / README / FEATURE_STATUS: blueprints are CLI/API only. Do not rewrite USERGUIDE in the same PR as code delete unless the id is gone. |

---

## Nice

### W-04 — Unmounted package (views / urls / templates / apps.py)

| File | What it thinks it is | Reality |
|------|----------------------|---------|
| `blueprint_django_chat.py` | HTTP-only service at `/django_chat/` | `run()` is an OpenAI-compatible LLM proxy (`dynamic_team` shape). CLI `__main__` exits 1. |
| `views.py` | `login_required` + `csrf_exempt` page; lists `ChatConversation` | Never included from `swarm.urls`. Template ignores `conversations`. |
| `urls.py` | `app_name = django_chat`, `path('', views.django_chat)` | No `include()`. Prefix `django_chat/` is metadata-only. |
| `apps.py` | `name = "blueprints.django_chat"` | Not in `INSTALLED_APPS`. Real package is `swarm.blueprints.django_chat`. No `__init__.py`. |
| `templates/django_chat/django_chat_webpage.html` | “third chat UI” (D-18) | Alpine/HTMX **model dropdown fragment** (`hx-get="/v1/models"`). Not a chat shell. `APP_DIRS` would not see it anyway (app not installed; `TEMPLATES['DIRS']` is not this tree). |

`urls_module` value `"blueprints.django_chat.urls"` is the old import path. Nothing reads it.

**Action later:** **delete** with the package.

### W-05 — Dead CLI / duplicate view

First `if __name__ == "__main__"` prints HTTP-only and `sys.exit(1)`. The second `__main__` block and `DjangoChatSpinner` are **unreachable**. Class method `django_chat()` duplicates `views.py` and is not wired.

`run_with_context` returns a canned “UI active at `/django_chat/`” string.

**Action later:** **delete**.

### W-06 — Tests that exist only for this leftover

| Path | Keep if package deleted? |
|------|--------------------------|
| `tests/blueprints/test_django_chat_config.py` | **delete** (config-clobber regression for this class). Pattern already copied as a comment in `stewie`. |
| `tests/unit/test_auth_hardening.py` `TestDjangoChatDefaultUserGuard` | **delete** with views (debug `testuser` is webpage-only). |
| `tests/system/test_django_chat.sh` | **delete**. Path is `python blueprints/django_chat/…` (pre-`src/swarm` layout). Would hit the exit-1 `__main__` even if the path existed. |
| `tests/views/test_spa_django_canonical_routes.py` `test_django_chat_nav_href_is_chat_not_agents` | **leave**. Name collision only: asserts Django `base.html` Chat href is `/chat`, not `/agents`. Not this blueprint. |

#419 success 4 (listing has no webui kind; leftover URL 404) needs **new** tests on the later ticket. Do not add them here.

### W-07 — Dead `dropdown.js` (wave 1 Q-18)

`src/swarm/static/js/dropdown.js` redirects to `/django_chat/${blueprintName}/new/` after HTMX swap on `#blueprintDropdown`. No template still has that id. Zero script tags. **delete** with Q-18 (can share a dead-JS PR; not required to wait for #419).

### W-08 — Dead signup title (wave 1 Q-16)

`src/swarm/templates/account/signup.html` heading still says “Sign Up - django_chat (open-swarm edition)”. Page has no URL. **delete** with Q-16.

### W-09 — Swarm Creator `tags: ["swarm", "webui"]`

`agent_creator_views.py` generated team metadata stamps `"author": "Web UI"` and `"tags": ["swarm", "webui"]`. That is a **tag**, not a kind, and it does not mount a page. Closest “Settings / creator offers a webui kind” leftover.

**Action later:** **wrap** — stamp `["swarm"]` or omit. Distinct from #420 roles.

### W-10 — Logger leftover

`src/swarm/settings.py` `LOGGING['loggers']['blueprint_django_chat']`. **delete** with the package.

### W-11 — Stewie comment

`blueprint_stewie.py`: “Do not clobber a config the base already loaded (django_chat-style bug).” **leave** the guard; optional comment reword after delete.

### W-12 — Historical SPA Builder doc

`docs/examples/webui-config-panels.md` is already “Orphaned / historical.” It documents deleted Builder panels, not django_chat. **leave** or move under `docs/archive/` on a docs pass. Do not treat as a live webui-blueprint.

---

## Obsolete (do not plan cleanup as if these were still true)

### W-13 — Live `/django_chat/` webpage (wave 1 Q-19 as written)

`src/swarm/urls.py` has no `django_chat` include. `INSTALLED_APPS` is daphne / Django / DRF / channels / `swarm` / optional `mcp_server` — not this app.

If `webui/frontend/dist/` exists, the SPA catch-all **does not** exclude `django_chat/`, so `/django_chat/` would serve **product Chat**, not the blueprint template. That is a confusing bookmark, not a second shell.

**Do not** file a “delete the live third chat page” task. Delete the unused files (W-04) and the id (W-01).

### W-14 — Settings Blueprints list `kind=webui`

Grep finds **no** `kind=webui` / `webui/django-chat` kind. Settings **Blueprints & Agents** = `ENABLED_BLUEPRINTS` list + defaults. Settings sheet **Blueprint** pane = Python source for a rail agent (#420 / #382 picker). Marketplace `kind` is `'blueprint' | 'mcp'`. Member `kind` is `agent` / `herdr` / remotes.

#419’s “do not offer a webui kind” is already true as an enum. Remaining work is W-01 (the id) and W-09 (the tag).

### W-15 — Other leftover `apps.py` are not webpages

| Package | `apps.py` | HTML / urls / views |
|---------|-----------|---------------------|
| `gawd` | `name = 'blueprints.gawd'` | none |
| `zeus` | `name = "swarm.blueprints.zeus"` | none |
| `whiskeytango_foxtrot` | `name = 'blueprints.whiskeytango_foxtrot'` | none |

#419: out of scope unless they render a webpage. They do not. core.md P2-10 can delete those `apps.py` later without #419.

Only `render(` / Django templates under `src/swarm/blueprints/` are django_chat.

### W-16 — `messenger` stub UI

Discovery still has a special-case stub if a `messenger/` dir exists. `blueprints/README.md` says the dir is **gone**. Do not restore.

---

## Intentional (must stay)

These are **not** webui-as-blueprint. Deleting `django_chat` must not delete them.

### I-01 — `ChatConversation` / `ChatMessage`

ORM in `src/swarm/models/`. Websocket consumer, REQ-14 persist/compact, and tests use them. django_chat only **reads** conversations for a context the template ignores. **leave** the models. **delete** only the blueprint queries.

### I-02 — Product Grok chrome

`/`, `/chat`, `/webui/` → `/`, `ENABLE_WEBUI`, `webui/frontend`. That **is** the web UI (#419). Not a blueprint.

### I-03 — Blueprint REST / completions

`/v1/blueprints`, `/v1/models`, `/v1/chat/completions`, `/v1/blueprints/<id>/source`. Keep the machinery; drop this id from the list.

### I-04 — Other recipes (CLI/API)

`software_dev` (roles/seats, #420), `codey`, MoA / `cli_*` / hybrid family, `dynamic_team` (the real thin LLM proxy), remotes, `harness_fleet`. **leave**. Do not drive-by delete gawd here (core.md P1-13, separate).

### I-05 — Script-level `django.setup()`

`scripts/demo_*.py`, `scripts/prove_*.py` call `django.setup()` after setting settings. That is script bootstrap, not blueprint import. **leave**.

### I-06 — Settings Blueprint editor

Sheet section `blueprint` loads `/v1/blueprints/<id>/source` for a roled rail agent. #382 / #420. Not a webui kind. **leave**.

### I-07 — `harness_fleet` `"kind": "hermes webui"`

Remote host descriptor, not a blueprint kind. **leave**.

---

## Delete vs stay (CLI/API)

| Item | Delete in #419? | Stay as CLI/API? |
|------|-----------------|------------------|
| `src/swarm/blueprints/django_chat/` (whole package) | **Yes, prefer** | Only if wrap: keep `run()` without Django/HTML. Not unique vs `dynamic_team` / `chatbot`. |
| Webpage half (`views` / `urls` / `templates` / `apps.py` / class `django_chat()`) | **Yes** | No |
| `django.setup()` at import | **Yes** (remove with package or wrap) | No |
| Discoverable model id `django_chat` | **Yes** (drop from lists) | No unless wrap + honest “thin proxy” docs |
| `run()` LLM proxy | Delete with package | Wrap only if someone still POSTs `model: "django_chat"` |
| Config regression test | Delete with class | Keep only if wrap |
| Default-user guard tests | **Yes** | No |
| `tests/system/test_django_chat.sh` | **Yes** | No |
| `ChatConversation` / WS / REQ-14 | **No** | **Yes** |
| Product `/chat` + SPA | **No** | n/a (chrome, not a blueprint) |
| `/v1/*` blueprint + completions | **No** | **Yes** |
| Other blueprints | **No** | **Yes** |
| `software_dev` roles | **No** (#420) | **Yes** |
| Wave 1 dead JS / signup | Optional same PR or Q-16/Q-18 | n/a |
| `webui-config-panels.md` | No (already historical) | n/a |

**Wrap recipe (only if delete is deferred):** strip Django imports and HTML; class-level metadata; no `urls_module`; allow CLI; do not call `django.setup()`; describe it as a completions proxy. #419 text prefers skip this and remove.

---

## Route / mount map

| Path / claim | Mounted? | What happens |
|--------------|----------|--------------|
| `django_chat` metadata `url_prefix: "django_chat/"` | No consumer | Dead field (and not in discovered metadata because `@property`) |
| `blueprints.django_chat.urls` | No | Wrong module path; not in `urlpatterns` |
| Operator `/chat` | Yes | Product SPA Chat |
| `/webui/` | Yes | Redirect to `/` (`WebUIView`) |
| `/django_chat/` | **No** dedicated view | SPA catch-all → product Chat if `dist/` exists; otherwise 404 |
| `/django_chat/<blueprint>/new/` | **No** | Only dead `dropdown.js` |
| Library / launcher / sidebar pick `django_chat` | Yes as **id** | Completions or `/chat?blueprint=django_chat` — product chrome |

No other blueprint registers `urls_module` / `url_prefix`.

---

## `django.setup()` map (blueprint vs scripts)

| Location | At import? | In #419 scope? |
|----------|------------|----------------|
| `blueprints/django_chat/blueprint_django_chat.py` | **Yes** | **Yes** — only blueprint that does this |
| `scripts/demo_inference_profile.py` and other `scripts/demo_*.py` / `prove_*.py` | Yes (script main) | **No** |
| `tests/views/test_settings_dashboard_xss.py` | Test bootstrap | **No** |
| Django process `apps.populate()` | Framework | **No** |

---

## Role gaps (#420) — only if they block #419

They do not.

- `django_chat` declares no `role` / seats.
- `software_dev` already has `roles.py` + metadata `agents` / `gate_agent` / `skeptic_agent` (CLI/API recipe, no webpage).
- Settings sheet Blueprint editor is role-agent source, not a django_chat page.
- Retiring webui-as-blueprint does not require role-on-create, handoff metadata, or picker badges.

Do not fold #420 into #419.

---

## If #419 deleted `django_chat` tomorrow

**Breaks**

- `model: "django_chat"` on completions / Responses (use `dynamic_team` / `chatbot` / a team alias).
- Library / launcher / sidebar row for that id.
- The three tests in W-06 (must go with the package).
- Docs rows in W-03 (stale until edited).

**Does not break**

- Product Chat, WS partials, REQ-14, `ChatConversation`.
- `/v1/blueprints` for every other id.
- Settings sheet, Teams, rosters, remotes, `software_dev`.
- `swarm-cli list` (loses one directory line).
- gawd / zeus / whiskeytango (still discoverable recipes).

**Safe later deletes (not this PR):** the package, W-06 tests, W-10 logger, W-03 live catalog sentences, W-07/W-08 if bundled with wave 1 dead-file cleanup.

---

## Suggested later ticket (not this PR)

One #419 implementation cloud, after feature-freeze unblock, `Fixes #419`, from stable main:

1. **delete** `src/swarm/blueprints/django_chat/` and W-06 tests / W-10 logger.
2. **delete** W-03 live “web chat” rows (BLUEPRINT_LIBRARY, FEATURE_STATUS, blueprints README, blueprint_guide, USER_JOURNEY samples).
3. Optional same PR: W-09 drop `webui` tag; W-07/W-08 if still present.
4. Tests: `/v1/models` + `/v1/blueprints` have no `django_chat`; `discover_blueprints` has no that key; leftover `/django_chat/` is 404 or SPA Chat, not a blueprint template; no new blueprint Django app.
5. Do **not** rebase / squash / fold #420, #382, or wave 1 Django-vs-SPA PRs.

**Do not** remount a django_chat page. **Do not** add a `kind=webui`. **Do not** touch `:8001` or Neon.

---

## Out of scope (this wave)

- No rewrite of app, SPA, Django, tests, or CI.
- No edit of existing `docs/debt/*.md`.
- No rebase / squash / fold into other PRs.
- No Neon. No host bounce. No secrets or live LAN URLs.
- No role metadata (#420).
- No gawd / zeus / whiskeytango deletes.
