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
| `landing.png` | `/` (React SPA dashboard) | Counts 0/53/53; Quick Actions **Launch Team / Browse Blueprints / Manage Teams / Settings**; nav Home·Blueprints·Teams·Sessions·Settings (matches App.tsx) | USER_JOURNEY.md, GUIDED_TOUR.md, README.md | 2026-08-18 | current |
| `spa-chat.png` | `/chat` (React SPA) | **Unavailable** / websocket failed gate + Sign in CTA; blueprint selector **not** in frame — same gate as `mobile/spa-chat.png` | GUIDED_TOUR.md | 2026-08-18 | current |
| `spa-teams.png` | `/teams` → **`/teams/launch/`** | Redirect capture + sticky “Redirected: …” banner over Team Launcher | GUIDED_TOUR.md | 2026-08-18 | current |
| `spa-blueprints.png` | `/blueprints` → **`/blueprint-library/`** | Redirect capture + banner over Blueprint Library | GUIDED_TOUR.md | 2026-08-18 | current |
| `spa-settings.png` | `/settings` → **`/settings/`** | Redirect capture + banner over Settings Dashboard | GUIDED_TOUR.md | 2026-08-18 | current |
| `spa-agent-creator.png` | `/agent-creator` → **`/agent-creator/`** | Redirect capture + banner over Agent Creator | GUIDED_TOUR.md | 2026-08-18 | current |
| `login.png` | `/accounts/login/` (Django) | Sign-in form | USER_JOURNEY.md, GUIDED_TOUR.md | 2026-08-18 | current |
| `teams.png` | `/teams/` (Django) | Teams Admin registration form + table | USER_JOURNEY.md, GUIDED_TOUR.md | 2026-08-18 | current |
| `teams-launch.png` | `/teams/launch/` (Django) | Team Launcher; **`hybrid_team`** selected (first dropdown option); empty output | USER_JOURNEY.md, GUIDED_TOUR.md | 2026-08-18 | current |
| `blueprint-library.png` | `/blueprint-library/` (Django) | Catalog with search, pagination (Show more, 12 of 55), MCP badges (checking spinner) | USER_JOURNEY.md, GUIDED_TOUR.md | 2026-08-18 | current |
| `my-blueprints.png` | `/blueprint-library/my-blueprints/` (Django) | Personal library (often empty on fresh db) | USER_JOURNEY.md, GUIDED_TOUR.md | 2026-08-18 | current |
| `agent-creator.png` | `/agent-creator/` (Django) | Progressive-disclosure persona form + code panel | USER_JOURNEY.md, GUIDED_TOUR.md | 2026-08-18 | current |
| `settings.png` | `/settings/` (Django) | Settings dashboard with progress meter | USER_JOURNEY.md, GUIDED_TOUR.md | 2026-08-18 | current |
| `sessions.png` | `/sessions/` (Django) | Session Explorer empty state: 0 sessions, live toggle, POST /v1/responses CTA (captured before mid-run seed) | USER_JOURNEY.md, GUIDED_TOUR.md, SESSION_EXPLORER.md | 2026-08-18 | current |
| `session-detail.png` | `/sessions/resp_journey_seed/` (Django) | Session detail Graph tab: seeded `hybrid_team` fixture (`resp_journey_seed`) with orchestration/agent/auxiliary nodes — real template, synthetic JSON (**not** a live hybrid_team run) | USER_JOURNEY.md, GUIDED_TOUR.md, SESSION_EXPLORER.md | 2026-08-18 | current |
| `profiles.png` | `/profiles/` (Django) | LLM profiles table (provider/model/source/enabled; Settings → LLM profiles active) | USER_JOURNEY.md, GUIDED_TOUR.md | 2026-08-18 | current |

The "Used in" column is verified by grepping the docs for
`screenshots/<file>`. USERGUIDE.md embeds no PNG files (CLI reference only)
but points readers at this tour.

## Mobile captures (`docs/screenshots/mobile/`)

Same stems as desktop with `--mobile` (iPhone-14-class: 390×844, dpr 2, touch).

**Bottom nav honesty (as of these PNGs):**

* **Django** operator pages and the **SPA** shell (`mobile/landing.png`,
  `mobile/spa-chat.png`) use the same five-tab bar
  **Home · Blueprints · Teams · Sessions · Settings** (matches App.tsx).
* Bare SPA paths still **redirect** to Django; `spa-*` redirect captures keep
  the sticky “Redirected: …” banner over the Django landing (five-tab bar).
* Desktop and mobile `spa-chat.png` both show the **Unavailable** /
  websocket-failed gate with a Sign in link (`/accounts/login/`). A prior
  mobile frame sometimes showed **Connected** when an older session cookie
  survived; the current journey capture authenticates up front but the chat
  WS still fails closed in this env, so both viewports match.

| File | Page / URL | Mobile-specific notes | Captured | Status |
| --- | --- | --- | --- | --- |
| `mobile/landing.png` | `/` | Stat cards stack; Quick Actions **Launch Team / Browse Blueprints / Manage Teams / Settings**; **5-tab dock** Home · Blueprints · Teams · Sessions · Settings (Home active; matches App.tsx). Embedded in GUIDED_TOUR.md | 2026-08-18 | current |
| `mobile/spa-chat.png` | `/chat` | **Unavailable** / websocket-failed gate + Sign in CTA (matches desktop); **5-tab dock** (Chat is SPA-only, not a dock tab) | 2026-08-18 | current |
| `mobile/spa-teams.png` | `/teams` → **`/teams/launch/`** | Redirect banner + Team Launcher; Django **5-tab** bar (Teams active) | 2026-08-18 | current |
| `mobile/spa-blueprints.png` | `/blueprints` → **`/blueprint-library/`** | Redirect banner + single-column cards; Django **5-tab** (Blueprints active) | 2026-08-18 | current |
| `mobile/spa-settings.png` | `/settings` → **`/settings/`** | Redirect banner over Settings dashboard; Django **5-tab** (Settings active) | 2026-08-18 | current |
| `mobile/spa-agent-creator.png` | `/agent-creator` → **`/agent-creator/`** | Redirect banner over Agent Creator; Django **5-tab** (Blueprints active) | 2026-08-18 | current |
| `mobile/login.png` | `/accounts/login/` | Full-width login card (no bottom primary bar) | 2026-08-18 | current |
| `mobile/teams.png` | `/teams/` | Django **5-tab** bar (Teams active); form wraps | 2026-08-18 | current |
| `mobile/teams-launch.png` | `/teams/launch/` | Launcher full-width; **`hybrid_team`** selected (first dropdown option); Django **5-tab** (Teams active) | 2026-08-18 | current |
| `mobile/blueprint-library.png` | `/blueprint-library/` | Paginated cards stack; Django **5-tab** (Blueprints active) | 2026-08-18 | current |
| `mobile/my-blueprints.png` | `/blueprint-library/my-blueprints/` | Empty-state CTAs; Django **5-tab** (Blueprints active) | 2026-08-18 | current |
| `mobile/agent-creator.png` | `/agent-creator/` | Essentials accordion; Django **5-tab** (Blueprints active) | 2026-08-18 | current |
| `mobile/settings.png` | `/settings/` | Dashboard tiles wrap; Django **5-tab** (Settings active) | 2026-08-18 | current |
| `mobile/sessions.png` | `/sessions/` | Empty state (0 sessions + live toggle); Django **5-tab** (Sessions active). Embedded in GUIDED_TOUR.md | 2026-08-18 | current |
| `mobile/session-detail.png` | `/sessions/resp_journey_seed/` | Seeded `hybrid_team` fixture Graph tab (same honesty as desktop — not a live run); Django **5-tab** (Sessions active) | 2026-08-18 | current |
| `mobile/profiles.png` | `/profiles/` | Profiles table; Django **5-tab** (Settings active — profiles nest under Settings) | 2026-08-18 | current |

Regenerate with:

```bash
.venv/bin/python scripts/capture_user_journey.py --mobile
```

## Demo animations (`docs/demo/`)

| File | What it shows | Used in | Captured | Status |
| --- | --- | --- | --- | --- |
| `demo/cli-and-api.gif` | Animated terminal demo (~25s loop): `swarm-cli list`, `launch zeus`, curl `/v1/*`, optional `moa --team` (fake) | README.md | 2026-08-18 | current |

Four scenes from real `SWARM_TEST_MODE` / curl / `--backend fake` captures under
`docs/demo/captures/` (see `raw_*.txt`). Scene 2 uses documented
`swarm-cli launch zeus` (after `install-executable zeus`). Scene 4 is
`swarm-cli moa --backend fake --team --workdir /tmp/moa-demo`.

Regenerate (real captures only) via
[`scripts/render_demo_gif.py`](../scripts/render_demo_gif.py) after updating
`docs/demo/captures/scene{1,2,3,4}.txt` (and `raw_*.txt`) from live commands —
see [Regenerating](#regenerating) below.

## Other images in the repo

| File | What it shows | Used in | Captured | Status |
| --- | --- | --- | --- | --- |
| `assets/images/20250105-Open-Swarm-HTML-Page.png` | Old HTML landing | unused | 2025-01-05 | legacy |
| `webui/blueprint-tools-badge-dark.png` | SPA builder / themed component capture | webui-config-panels.md | mixed | current |
| `webui/builder-all-panels-dark.png` | SPA builder / themed component capture | webui-config-panels.md | mixed | current |
| `webui/builder-dark.png` | SPA builder / themed component capture | webui-config-panels.md | mixed | current |
| `webui/builder-light.png` | SPA builder light twin (a11y pair; dark embed used) | none (pair of builder-dark) | mixed | current |
| `webui/inference-profile-dark.png` | SPA builder / themed component capture | webui-config-panels.md | mixed | current |
| `webui/inference-profile-light.png` | SPA builder light twin (a11y pair; dark embed used) | none (pair of inference-profile-dark) | mixed | current |
| `webui/skills-dark.png` | SPA builder / themed component capture | webui-config-panels.md | mixed | current |
| `webui/skills-light.png` | SPA builder light twin (a11y pair; dark embed used) | none (pair of skills-dark) | mixed | current |
| `webui/skills-preview-dark.png` | SPA builder / themed component capture | webui-config-panels.md | mixed | current |
| `webui/tool-capabilities-dark.png` | SPA builder / themed component capture | webui-config-panels.md | mixed | current |
| `webui/tool-capabilities-light.png` | SPA builder light twin (a11y pair; dark embed used) | none (pair of tool-capabilities-dark) | mixed | current |
| `webui/trait-editor-dark.png` | SPA builder / themed component capture | webui-config-panels.md | mixed | current |
| `docs/screenshots/skills/*` | Skills walkthrough stills | SKILLS docs | mixed | current |
| `docs/screenshots/archive/session-explorer-detail.png` | Older Session detail still (superseded by current `session-detail.png`) | none (historical) | archived | archived |
| `docs/screenshots/archive/session-explorer-list.png` | Superseded list still (replaced by `sessions.png`) | none | archived | archived |
| `docs/screenshots/archive/a11y-focus-ring.png` | Old a11y focus-ring still | none | archived | archived |

## Regenerating

### WebUI / journey screenshots

```bash
.venv/bin/pip install playwright
.venv/bin/playwright install chromium
.venv/bin/python scripts/capture_user_journey.py            # desktop
.venv/bin/python scripts/capture_user_journey.py --mobile   # mobile
# optional manifest:
CAPTURE_MANIFEST=/tmp/capture-manifest.json .venv/bin/python scripts/capture_user_journey.py
```

The script starts its own dev server on port 8321
(`DJANGO_DEBUG=true ENABLE_WEBUI=true`), uses an isolated
`SWARM_RESPONSES_DIR` (empty for `sessions.png`), migrates, logs in a
throwaway superuser, captures every page in `PAGES`, mid-run seeds
`resp_journey_seed` before `session-detail.png`, overwrites PNGs, skips
(never fakes) 4xx/5xx, then stops the server. SPA routes need
`webui/frontend/dist/`.

After regenerating, update captions in
[USER_JOURNEY.md](./USER_JOURNEY.md) and [GUIDED_TOUR.md](./GUIDED_TOUR.md) if
pages changed, and refresh this registry's "Captured" dates.

### Demo GIF (`docs/demo/cli-and-api.gif`)

Honesty rule (from the render script): every output line must come from a
real capture under `docs/demo/captures/` — type-animation only; elide with a
single `…` line when trimming a contiguous block. Scene format: `$ ` lines are
typed; other lines are output blocks. `scene*.txt` are picked up in sorted
order (`scene1`…`scene4`).

```bash
# 1) Refresh raw captures (trim into scene{1,2,3,4}.txt afterward)
SWARM_TEST_MODE=1 uv run swarm-cli list
# prefer documented launch path (install once if needed):
#   uv run swarm-cli install-executable zeus
SWARM_TEST_MODE=1 uv run swarm-cli launch zeus --message "Plan a release: tests, changelog, tag"
# or module path still works:
# SWARM_TEST_MODE=1 uv run python -m swarm.blueprints.zeus.zeus_cli \
#     --message "Plan a release: tests, changelog, tag"
SWARM_TEST_MODE=1 DJANGO_DEBUG=true uv run python manage.py runserver 8447 --noreload &
curl -s localhost:8447/v1/models | jq -c '[.data[].id]'
curl -s localhost:8447/v1/chat/completions -H 'Content-Type: application/json' \
    -d '{"model":"zeus","stream":true,"messages":[{"role":"user","content":"Plan a release: tests, changelog, tag"}]}'
# optional scene4 — real fake-backend MoA team only (do not invent frames):
mkdir -p /tmp/moa-demo
SWARM_TEST_MODE=1 uv run swarm-cli moa --backend fake --team --workdir /tmp/moa-demo \
    "Should we ship the release?"

# 2) Render from scene files
uv run python scripts/render_demo_gif.py
# Requires Pillow + DejaVu Sans Mono (fonts-dejavu on Linux).
```

Then set this registry row’s Captured date and Status back to `current`.

## Convention

* The **current** capture of each page lives in `docs/screenshots/` under a
  stable kebab-case filename (matching the `PAGES` slug in the capture
  script).
* When a screenshot is **superseded** but worth keeping for history, move the
  old file to `docs/screenshots/archive/` under the **same filename** before
  regenerating, and note it here with status "archived".
* Every screenshot added to the repo gets a row in this registry.
