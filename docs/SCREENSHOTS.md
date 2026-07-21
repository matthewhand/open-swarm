# Screenshot Registry

Master registry of every screenshot in the repository. All current captures
live in [`docs/screenshots/`](./screenshots/) and were taken from a live local
dev server by
[`scripts/capture_user_journey.py`](../scripts/capture_user_journey.py) —
headless Chromium, 1280×800 viewport (desktop) or 390×844 dpr2 (mobile),
full-page PNGs.

> **Documentation map:** [USERGUIDE.md](../USERGUIDE.md) is the `swarm-cli`
> reference, [USER_JOURNEY.md](./USER_JOURNEY.md) is the end-to-end story,
> [GUIDED_TOUR.md](./GUIDED_TOUR.md) is the visual tour, and this file is the
> capture registry.

## Current captures (`docs/screenshots/`)

| File | Page / URL | What it shows | Used in | Captured | Status |
| --- | --- | --- | --- | --- | --- |
| `landing.png` | `/` (React SPA dashboard) | Lightweight dashboard: live teams/blueprints/models counts, Django Quick Actions, API reachable | USER_JOURNEY.md, GUIDED_TOUR.md, README.md | 2026-07-21 | current |
| `spa-chat.png` | `/chat` (React SPA) | Websocket chat shell with blueprint selector (login required for consumer) | GUIDED_TOUR.md | 2026-07-21 | current |
| `spa-teams.png` | `/teams` → **`/teams/launch/`** | Redirect capture: Django Team Launcher (not a separate SPA product) | GUIDED_TOUR.md | 2026-07-21 | current |
| `spa-blueprints.png` | `/blueprints` → **`/blueprint-library/`** | Redirect capture: Django Blueprint Library | GUIDED_TOUR.md | 2026-07-21 | current |
| `spa-settings.png` | `/settings` → **`/settings/`** | Redirect capture: Django Settings Dashboard | GUIDED_TOUR.md | 2026-07-21 | current |
| `spa-agent-creator.png` | `/agent-creator` → **`/agent-creator/`** | Redirect capture: Django Agent Creator | GUIDED_TOUR.md | 2026-07-21 | current |
| `login.png` | `/accounts/login/` (Django) | Sign-in form | USER_JOURNEY.md, GUIDED_TOUR.md | 2026-07-21 | current |
| `teams.png` | `/teams/` (Django) | Teams Admin registration form + table | USER_JOURNEY.md, GUIDED_TOUR.md | 2026-07-21 | current |
| `teams-launch.png` | `/teams/launch/` (Django) | Team Launcher with blueprint select + task box | USER_JOURNEY.md, GUIDED_TOUR.md | 2026-07-21 | current |
| `blueprint-library.png` | `/blueprint-library/` (Django) | Catalog with search, pagination (Show more), MCP badges | USER_JOURNEY.md, GUIDED_TOUR.md | 2026-07-21 | current |
| `my-blueprints.png` | `/blueprint-library/my-blueprints/` (Django) | Personal library (often empty on fresh db) | USER_JOURNEY.md, GUIDED_TOUR.md | 2026-07-21 | current |
| `agent-creator.png` | `/agent-creator/` (Django) | Progressive-disclosure persona form + code panel | USER_JOURNEY.md, GUIDED_TOUR.md | 2026-07-21 | current |
| `settings.png` | `/settings/` (Django) | Settings dashboard with progress meter | USER_JOURNEY.md, GUIDED_TOUR.md | 2026-07-21 | current |
| `sessions.png` | `/sessions/` (Django) | Session Explorer, limit=50 banner, status chips | GUIDED_TOUR.md | 2026-07-21 | current |
| `profiles.png` | `/profiles/` (Django) | LLM profiles table (Teams nav active) | GUIDED_TOUR.md | 2026-07-21 | current |

The "Used in" column is verified by grepping the docs for
`screenshots/<file>`. USERGUIDE.md embeds no PNG files (CLI reference only)
but points readers at this tour.

## Mobile captures (`docs/screenshots/mobile/`)

Same stems as desktop with `--mobile` (iPhone-14-class: 390×844, dpr 2, touch).
Django pages use the five-item bottom primary bar; SPA dashboard uses five
tabs linking to Django destinations.

| File | Page / URL | Mobile-specific notes | Captured | Status |
| --- | --- | --- | --- | --- |
| `mobile/landing.png` | `/` | Stat cards stack; bottom tabs → Django hrefs | 2026-07-21 | current |
| `mobile/spa-chat.png` | `/chat` | Chat composer + dock clearance | 2026-07-21 | current |
| `mobile/spa-teams.png` | `/teams` → launch | Redirect to Django launcher + bottom nav | 2026-07-21 | current |
| `mobile/spa-blueprints.png` | `/blueprints` → library | Redirect to library; single-column cards | 2026-07-21 | current |
| `mobile/spa-settings.png` | `/settings` → settings/ | Redirect to Django settings | 2026-07-21 | current |
| `mobile/spa-agent-creator.png` | `/agent-creator` → creator/ | Redirect to Django agent creator | 2026-07-21 | current |
| `mobile/login.png` | `/accounts/login/` | Full-width login card | 2026-07-21 | current |
| `mobile/teams.png` | `/teams/` | Bottom primary tabs; form wraps | 2026-07-21 | current |
| `mobile/teams-launch.png` | `/teams/launch/` | Launcher full-width | 2026-07-21 | current |
| `mobile/blueprint-library.png` | `/blueprint-library/` | Paginated cards stack | 2026-07-21 | current |
| `mobile/my-blueprints.png` | `/my-blueprints/` | Empty-state CTAs | 2026-07-21 | current |
| `mobile/agent-creator.png` | `/agent-creator/` | Essentials accordion; bottom tabs | 2026-07-21 | current |
| `mobile/settings.png` | `/settings/` | Dashboard tiles wrap | 2026-07-21 | current |
| `mobile/sessions.png` | `/sessions/` | Session list + limit banner | 2026-07-21 | current |
| `mobile/profiles.png` | `/profiles/` | Profiles table; Teams tab active | 2026-07-21 | current |

Regenerate with:

```bash
.venv/bin/python scripts/capture_user_journey.py --mobile
```

## Demo animations (`docs/demo/`)

| File | What it shows | Used in | Captured | Status |
| --- | --- | --- | --- | --- |
| `demo/cli-and-api.gif` | Animated terminal demo (~18s loop): `swarm-cli list`, blueprint CLI, curl API | README.md | 2026-06-12 | current |

## Other images in the repo

| File | What it shows | Used in | Captured | Status |
| --- | --- | --- | --- | --- |
| `assets/images/20250105-Open-Swarm-HTML-Page.png` | Old HTML landing | unused | 2025-01-05 | legacy |
| `docs/screenshots/webui/*` | Themed WebUI component captures | various | mixed | current |
| `docs/screenshots/skills/*` | Skills walkthrough stills | SKILLS docs | mixed | current |

## Regenerating

```bash
.venv/bin/pip install playwright
.venv/bin/playwright install chromium
.venv/bin/python scripts/capture_user_journey.py            # desktop
.venv/bin/python scripts/capture_user_journey.py --mobile   # mobile
# optional manifest:
CAPTURE_MANIFEST=/tmp/capture-manifest.json .venv/bin/python scripts/capture_user_journey.py
```

The script starts its own dev server on port 8321
(`DJANGO_DEBUG=true ENABLE_WEBUI=true`), migrates, logs in a throwaway
superuser, captures every page in `PAGES`, overwrites PNGs, skips (never
fakes) 4xx/5xx, then stops the server. SPA routes need `webui/frontend/dist/`.

After regenerating, update captions in
[USER_JOURNEY.md](./USER_JOURNEY.md) and [GUIDED_TOUR.md](./GUIDED_TOUR.md) if
pages changed, and refresh this registry's "Captured" dates.

## Convention

* The **current** capture of each page lives in `docs/screenshots/` under a
  stable kebab-case filename (matching the `PAGES` slug in the capture
  script).
* When a screenshot is **superseded** but worth keeping for history, move the
  old file to `docs/screenshots/archive/` under the **same filename** before
  regenerating, and note it here with status "archived".
* Every screenshot added to the repo gets a row in this registry.
