# Open Swarm: A User Journey

A walkthrough of Open Swarm from a fresh checkout to running agent teams —
on the command line, in the web UI, and over the OpenAI-compatible API.

Every terminal block below is real output captured on a development machine,
and every screenshot in [`docs/screenshots/`](./screenshots/) was captured from
a live local server by [`scripts/capture_user_journey.py`](../scripts/capture_user_journey.py).
Where a page shows demo, placeholder, or empty-state data, the caption says so.

> Screenshots last regenerated **2026-08-18** with Playwright
> (`scripts/capture_user_journey.py`) against a live local server. Captures
> reflect that environment’s data (empty states and login-gated chat are
> called out in captions). Terminal transcripts below were captured
> 2026-06-10 on `main`.

> **Documentation map:** [USERGUIDE.md](../USERGUIDE.md) is the `swarm-cli`
> reference, this file is the end-to-end story,
> [GUIDED_TOUR.md](./GUIDED_TOUR.md) is the screenshot-per-page visual tour of
> the web UI (Django operator shell + lightweight SPA dashboard/chat), and
> [SCREENSHOTS.md](./SCREENSHOTS.md) is the capture registry.

---

## 1. Install

```bash
git clone https://github.com/matthewhand/open-swarm.git
cd open-swarm
uv sync --all-extras          # or: pip install -e .[dev]

# Configure an LLM key for real agent runs (not needed for the tour below)
export OPENAI_API_KEY="sk-..."
```

This guide uses the project virtualenv directly (`.venv/bin/...`); if you use
`uv`, prefix the same commands with `uv run` instead.

## 2. Meet the CLI

Open Swarm ships agent teams as **blueprints**. `swarm-cli list` shows what is
bundled and what you have installed:

```text
$ .venv/bin/swarm-cli list
--- Installed Blueprint Executables (in /home/user/.local/share/swarm/bin) ---
(No installed blueprint executables found in /home/user/.local/share/swarm/bin)
Try 'swarm-cli install-executable <blueprint_name>' or see 'swarm-cli list --available'.

--- Bundled Blueprints (available from package) ---
- django_chat (entry: apps.py)
- gawd (entry: apps.py)
- family_ties (entry: blueprint_family_ties.py)
- geese (entry: geese_memory_objects.py)
- dynamic_team (entry: blueprint_dynamic_team.py)
- poets (entry: poets_cli.py)
- flock (entry: blueprint_flock.py)
- stewie (entry: apps.py)
- rue_code (entry: blueprint_rue_code.py)
- chucks_angels (entry: blueprint_chucks_angels.py)
- digitalbutlers (entry: blueprint_digitalbutlers.py)
- jeeves (entry: blueprint_jeeves.py)
- zeus (entry: apps.py)
- common (entry: progress.py)
- whiskeytango_foxtrot (entry: apps.py)
- suggestion (entry: suggestion_cli.py)
- codey (entry: blueprint_codey.py)
- whinge_surf (entry: blueprint_whinge_surf.py)

--- User Blueprint Sources (in /home/user/.local/share/swarm/blueprints) ---
(No user blueprint sources found in /home/user/.local/share/swarm/blueprints)
You can add blueprints by copying their source folders to this directory.
```

### Try a blueprint without an API key (`SWARM_TEST_MODE`)

`SWARM_TEST_MODE=1` makes blueprints emit deterministic, canned output — the
same mechanism the 600+ test suite uses to run keyless. It also makes
`swarm-cli install` write a fast shell shim instead of compiling a PyInstaller
binary:

```text
$ SWARM_TEST_MODE=1 .venv/bin/swarm-cli install jeeves
Installing blueprint 'jeeves' as executable...
  Source: /home/user/open-swarm/src/swarm/blueprints/jeeves
  Entry Point: blueprint_jeeves.py
  Output Executable: /home/user/.local/share/swarm/bin/jeeves
Test-mode shim installed at: /home/user/.local/share/swarm/bin/jeeves

$ SWARM_TEST_MODE=1 .venv/bin/swarm-cli launch jeeves --message "What time is it?"
Launching 'jeeves' with: /home/user/.local/share/swarm/bin/jeeves --message What time is it?
--- jeeves Output ---
[SWARM_CONFIG_DEBUG] Trying: /home/user/open-swarm/swarm_config.json
[SWARM_CONFIG_DEBUG] Loaded: /home/user/open-swarm/swarm_config.json

--- 'jeeves' finished (Return Code: 0) ---
```

Each blueprint also has a direct CLI entry point. In test mode Jeeves renders
its full spinner-and-result-box UX (this is the canned test output, not a real
LLM answer):

```text
$ SWARM_TEST_MODE=1 .venv/bin/python -m swarm.blueprints.jeeves.jeeves_cli --message "What time is it?"
[SPINNER] Polishing the silver
╭──────────────────────────── Searching Filesystem ────────────────────────────╮
│ 🔍 Matches so far: 1                                                         │
│ [SPINNER] Polishing the silver                                               │
│                                                                              │
╰──────────────────────────────────────────────────────────────────────────────╯
[SPINNER] Generating.
╭──────────────────────────── Searching Filesystem ────────────────────────────╮
│ 🔍 Matches so far: 2                                                         │
│ [SPINNER] Generating.                                                        │
│                                                                              │
╰──────────────────────────────────────────────────────────────────────────────╯
[SPINNER] Generating..
╭──────────────────────────── Searching Filesystem ────────────────────────────╮
│ 🔍 Matches so far: 3                                                         │
│ [SPINNER] Generating..                                                       │
│                                                                              │
╰──────────────────────────────────────────────────────────────────────────────╯
[SPINNER] Generating...
╭──────────────────────────── Searching Filesystem ────────────────────────────╮
│ 🔍 Matches so far: 4                                                         │
│ [SPINNER] Generating...                                                      │
│                                                                              │
╰──────────────────────────────────────────────────────────────────────────────╯
[SPINNER] Running...
╭──────────────────────────── Searching Filesystem ────────────────────────────╮
│ 🔍 Matches so far: 5                                                         │
│ [SPINNER] Running...                                                         │
│                                                                              │
╰──────────────────────────────────────────────────────────────────────────────╯
```

With a real key configured (`OPENAI_API_KEY` plus `swarm_config.json` LLM
profiles), drop `SWARM_TEST_MODE` and the same commands run real agents.

## 3. Tour the web UI

Start the Django server in development mode. `ENABLE_WEBUI=true` enables the
template-rendered pages (teams, launcher, library, creator, settings):

```bash
ENABLE_WEBUI=true DJANGO_DEBUG=true .venv/bin/python manage.py runserver 8000
```

> With `DJANGO_DEBUG=true` and no `API_AUTH_TOKEN`, API auth stays **off**
> (server warns). Production is the opposite: leave `DJANGO_DEBUG` unset/false
> and set `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, and `API_AUTH_TOKEN`
> (or `SWARM_ALLOW_NO_AUTH=true` if an external layer gates access) — see
> [CONFIGURATION.md](../CONFIGURATION.md).

### Landing page — `/`

![Landing page](./screenshots/landing.png)

When the React frontend has been built (`webui/frontend/dist/` exists), `/`
serves a **lightweight SPA dashboard** (DaisyUI / Tailwind). Live
teams/blueprints/models counts come from the API (this capture: 0 / 53 / 53).
Quick Actions on the capture read **Launch Team**, **Manage Teams**,
**Settings** (current `App.tsx` also includes Browse Blueprints and
Django-aligned nav Home · Blueprints · Teams · Sessions · Settings — rebuild
`dist` and recapture to align). Bare `/teams`, `/blueprints`, `/settings`, and
`/agent-creator` **redirect** to Django (`/teams/launch/`,
`/blueprint-library/`, `/settings/`, `/agent-creator/`) — `spa-*.png`
captures document those redirect landings. Experimental SPA chat remains at
`/chat` (login required for the websocket consumer). See the page-by-page
[guided tour](./GUIDED_TOUR.md). Without `webui/frontend/dist/`, `/` falls
back to Django templates; the Django pages below are the supported admin
surface either way.

### Teams admin — `/teams/`

![Teams admin](./screenshots/teams.png)

Register named teams that become OpenAI-compatible *models*. The "Registered
Teams" table is empty here because this is a fresh development database. Once
added, a team appears in `/v1/models` and can be used as the `model` field
with any OpenAI client.

### Team launcher — `/teams/launch/`

![Team launcher](./screenshots/teams-launch.png)

Pick a team blueprint (the launcher lists bundled options such as
`fs_introspect`, `hybrid_team`, `django_chat`, `persona_council`, … — the
capture shows **`fs_introspect`** selected), type a task, and stream the
team's output in the browser. The output panel is empty until you launch.

### Blueprint library — `/blueprint-library/`

![Blueprint library](./screenshots/blueprint-library.png)

Browse discoverable blueprints with per-blueprint MCP status badges (async
check; this capture still shows the checking spinner labeled **MCP** on each
card). The grid is **paginated** on first paint (Show more — e.g. 12 of 55)
so the catalog does not dump every card at once; summary tiles reflect
available / installed / custom / category counts for this environment.

### My blueprints — `/blueprint-library/my-blueprints/`

![My blueprints](./screenshots/my-blueprints.png)

Your personal collection of installed and custom blueprints. Shown in its
empty state — a fresh environment with nothing added to the library yet.

### Agent creator — `/agent-creator/`

![Agent creator](./screenshots/agent-creator.png)

Build a custom agent persona with **progressive disclosure**: essentials
(name, description, special instructions) open by default; Persona and Tags
are optional collapsed sections. The right-hand panel generates, validates,
and saves the resulting Python blueprint code.

### Settings dashboard — `/settings/`

![Settings dashboard](./screenshots/settings.png)

Configuration management grouped by category (Django, Swarm core, auth, LLM
providers, blueprints/agents, MCP servers, database, logging, performance, UI
features), with a configuration-progress meter and import/export of the
environment. Values shown are this dev machine's local configuration.

### Login page — `/accounts/login/`

![Login page](./screenshots/login.png)

The login form. Both `/accounts/login/` and `/login/` are wired to the
`custom_login` view. Logging in enables authenticated operator pages and the
SPA chat websocket session — the chat consumer rejects anonymous connections.

### Session explorer — `/sessions/`

![Session explorer: empty list, 0 sessions, live toggle](./screenshots/sessions.png)

Fresh-db empty state: **0 sessions**, a **live** auto-refresh toggle, and
“No sessions yet. Make a `POST /v1/responses` request and they'll appear
here.” Status filter chips and the newest-N truncation banner show once
sessions exist (and when the list is truncated to the default limit of 50).
See also [GUIDED_TOUR.md](./GUIDED_TOUR.md) and
[SESSION_EXPLORER.md](./SESSION_EXPLORER.md).

### LLM profiles — `/profiles/`

![LLM profiles table: provider, model, source, enabled](./screenshots/profiles.png)

Detected LLM profiles from project and user config (openai, anthropic,
google, ollama, lmstudio, openrouter, …) with Provider / Model / Base URL /
Source / Enabled columns. Nested under **Settings → LLM profiles** in the
primary nav (Settings dropdown active in this capture). Enable or disable
providers under Settings → LLM Providers.

### Pages not captured as distinct products

* **Bare SPA dual routes** (`/teams`, `/blueprints`, `/settings`,
  `/agent-creator`) — they redirect to Django; covered by `spa-*.png`
  redirect captures, not separate products.
* **`/webui/`** — legacy template; redirects to `/` for old bookmarks.


## 4. Use it as an OpenAI-compatible API

Everything in the web UI is also an API. List blueprints as *models*
(output truncated; real capture from a local `DJANGO_DEBUG=true` server —
no `API_AUTH_TOKEN`, so no Bearer header):

```text
$ curl -s http://localhost:8000/v1/models | python -m json.tool
{
    "object": "list",
    "data": [
        {
            "id": "django_chat",
            "object": "model",
            "created": 1781045533,
            "owned_by": "open-swarm"
        },
        {
            "id": "gawd",
            "object": "model",
            "created": 1781045533,
            "owned_by": "open-swarm"
        },
        ...
    ]
}
```

Chat with a blueprint using any OpenAI client — the `model` field selects the
blueprint. Same open-auth local setup as above (no Bearer). When
`API_AUTH_TOKEN` *is* set, `ENABLE_API_AUTH` turns on and every `/v1/*` call
needs `Authorization: Bearer ${API_AUTH_TOKEN}` (missing/wrong → 403):

```bash
# Local debug, no token configured (matches the /v1/models capture above):
curl -s http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "suggestion", "messages": [{"role":"user","content":"Say hello"}]}'

# When API_AUTH_TOKEN is set on the server:
curl -s http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${API_AUTH_TOKEN}" \
  -d '{"model": "suggestion", "messages": [{"role":"user","content":"Say hello"}]}'
```

The response is a standard OpenAI chat-completion envelope. Captured on this
dev machine *without* a valid upstream LLM key, so the assistant content is an
error string — shown here to illustrate the envelope honestly:

```json
{
  "id": "chatcmpl-76e9038c-616e-45fd-930e-a1abf5448b1e",
  "object": "chat.completion",
  "created": 1781045545,
  "model": "suggestion",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "An error occurred: Error code: 401 - {'error': {'message': 'Incorrect API key provided: ...'}}"
      },
      "logprobs": null,
      "finish_reason": "stop"
    }
  ],
  "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
  "system_fingerprint": null
}
```

Configure a working LLM profile (`OPENAI_API_KEY` or a local Ollama profile in
`swarm_config.json`) and the same request returns real agent output.
Streaming (`"stream": true`) is supported.

## 5. Regenerating this guide

The screenshots are maintained by a self-contained, re-runnable script:

```bash
.venv/bin/pip install playwright
.venv/bin/playwright install chromium
.venv/bin/python scripts/capture_user_journey.py
```

[`scripts/capture_user_journey.py`](../scripts/capture_user_journey.py):

1. starts its own Django dev server on port **8321**
   (`DJANGO_DEBUG=true ENABLE_WEBUI=true manage.py runserver 8321 --noreload`)
   and waits for readiness;
2. runs migrations, creates a throwaway superuser via `manage.py shell -c`,
   and logs in up front — the chat websocket consumer only accepts
   authenticated sessions, and logged-in pages render more realistically;
3. visits each page in its `PAGES` list (the React SPA routes plus the Django
   template pages) in headless Chromium at **1280x800** and writes full-page
   PNGs to `docs/screenshots/<kebab-name>.png`, overwriting the previous
   capture (SPA pages require a built `webui/frontend/dist/`);
4. skips (never fakes) any page that returns 4xx/5xx, then kills the server
   and prints a `captured/skipped` summary.

After re-running it, update the captions in this file and in
[`GUIDED_TOUR.md`](./GUIDED_TOUR.md) if pages changed, and move superseded
screenshots to `docs/screenshots/archive/` (same filename) per the convention
in the [screenshot registry](./SCREENSHOTS.md).
The terminal transcripts in section 2 and 4 can be refreshed by re-running the
commands shown and pasting the new output.
