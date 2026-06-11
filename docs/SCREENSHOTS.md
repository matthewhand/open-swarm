# Screenshot Registry

Master registry of every screenshot in the repository. All current captures
live in [`docs/screenshots/`](./screenshots/) and were taken from a live local
dev server (fresh database) by
[`scripts/capture_user_journey.py`](../scripts/capture_user_journey.py) —
headless Chromium, 1280x800 viewport, full-page PNGs.

> **Documentation map:** [USERGUIDE.md](../USERGUIDE.md) is the `swarm-cli`
> reference, [USER_JOURNEY.md](./USER_JOURNEY.md) is the end-to-end story,
> [GUIDED_TOUR.md](./GUIDED_TOUR.md) is the visual tour, and this file is the
> capture registry.

## Current captures (`docs/screenshots/`)

| File | Page / URL | What it shows | Used in | Captured | Status |
| --- | --- | --- | --- | --- | --- |
| `landing.png` | `/` (React SPA dashboard) | Styled SPA landing: live blueprint/model counts, quick actions, backend health | USER_JOURNEY.md, GUIDED_TOUR.md | 2026-06-11 | current |
| `spa-chat.png` | `/chat` (React SPA) | Websocket chat, authenticated session showing "Connected", empty conversation | GUIDED_TOUR.md | 2026-06-11 | current |
| `spa-teams.png` | `/teams` (React SPA) | Team management wired to `/v1/teams/`, fresh-db "No teams yet" empty state | GUIDED_TOUR.md | 2026-06-11 | current |
| `spa-blueprints.png` | `/blueprints` (React SPA) | Blueprint library from `/v1/blueprints/` with per-card MCP requirements | GUIDED_TOUR.md | 2026-06-11 | current |
| `spa-agent-creator.png` | `/agent-creator` (React SPA) | Persona form + blueprint-code panel; empty custom-blueprints list | GUIDED_TOUR.md | 2026-06-11 | current |
| `spa-settings.png` | `/settings` (React SPA) | API-token form, read-only server settings by category, masked env vars | GUIDED_TOUR.md | 2026-06-11 | current |
| `login.png` | `/accounts/login/` (Django) | Minimal unstyled login form with dev test-credentials hint | USER_JOURNEY.md, GUIDED_TOUR.md | 2026-06-11 | current |
| `teams.png` | `/teams/` (Django) | Teams Admin registration form; empty Registered Teams table (fresh db) | USER_JOURNEY.md, GUIDED_TOUR.md | 2026-06-11 | current |
| `teams-launch.png` | `/teams/launch/` (Django) | Team Launcher with bundled `django_chat` pre-selected; empty output panel | USER_JOURNEY.md, GUIDED_TOUR.md | 2026-06-11 | current |
| `blueprint-library.png` | `/blueprint-library/` (Django) | Bundled blueprint catalog with requirement badges; 5/0/0/5 summary tiles | USER_JOURNEY.md, GUIDED_TOUR.md | 2026-06-11 | current |
| `my-blueprints.png` | `/blueprint-library/my-blueprints/` (Django) | Personal library, empty state (all counters 0) | USER_JOURNEY.md, GUIDED_TOUR.md | 2026-06-11 | current |
| `agent-creator.png` | `/agent-creator/` (Django) | Agent persona form + empty Generated Code panel | USER_JOURNEY.md, GUIDED_TOUR.md | 2026-06-11 | current |
| `settings.png` | `/settings/` (Django) | Settings dashboard with config-progress meter and category sections | USER_JOURNEY.md, GUIDED_TOUR.md | 2026-06-11 | current |

The "Used in" column is verified by grepping the docs for
`screenshots/<file>`; README.md and USERGUIDE.md embed no screenshots.

## Mobile captures (`docs/screenshots/mobile/`)

Same 13 pages captured with `--mobile`: iPhone-14-class emulation
(390x844 viewport, device-scale-factor 2, touch enabled), full-page PNGs.
The SPA shows the DaisyUI `dock` bottom navigation below the `lg`
breakpoint; Django pages collapse into the Bootstrap burger menu.

| File | Page / URL | Mobile-specific notes | Captured | Status |
| --- | --- | --- | --- | --- |
| `mobile/landing.png` | `/` (React SPA dashboard) | Stat cards and quick actions stack; bottom dock with active-tab indicator | 2026-06-11 | current |
| `mobile/spa-chat.png` | `/chat` (React SPA) | Header stacks (title above blueprint selector); composer clears the fixed dock | 2026-06-11 | current |
| `mobile/spa-teams.png` | `/teams` (React SPA) | Single-column empty state; dock highlights Teams | 2026-06-11 | current |
| `mobile/spa-blueprints.png` | `/blueprints` (React SPA) | Single-column cards; long blueprint names wrap instead of overflowing | 2026-06-11 | current |
| `mobile/spa-agent-creator.png` | `/agent-creator` (React SPA) | Form fields full-width, single column | 2026-06-11 | current |
| `mobile/spa-settings.png` | `/settings` (React SPA) | Settings categories and env-var table fit the narrow viewport | 2026-06-11 | current |
| `mobile/login.png` | `/accounts/login/` (Django) | Login card fills the width with comfortable margins | 2026-06-11 | current |
| `mobile/teams.png` | `/teams/` (Django) | Bootstrap navbar collapsed to burger; form and buttons wrap | 2026-06-11 | current |
| `mobile/teams-launch.png` | `/teams/launch/` (Django) | Launcher form full-width; output panel below | 2026-06-11 | current |
| `mobile/blueprint-library.png` | `/blueprint-library/` (Django) | Summary tiles and blueprint cards stack single-column | 2026-06-11 | current |
| `mobile/my-blueprints.png` | `/blueprint-library/my-blueprints/` (Django) | Stat tiles stack; empty-state actions wrap | 2026-06-11 | current |
| `mobile/agent-creator.png` | `/agent-creator/` (Django) | Persona form single-column; Validate/Save buttons wrap in the panel header | 2026-06-11 | current |
| `mobile/settings.png` | `/settings/` (Django) | Dashboard header tiles wrap; category accordions full-width | 2026-06-11 | current |

Regenerate with:

```bash
.venv/bin/python scripts/capture_user_journey.py --mobile
```

## Other images in the repo

| File | What it shows | Used in | Captured | Status |
| --- | --- | --- | --- | --- |
| `assets/images/20250105-Open-Swarm-HTML-Page.png` | Old HTML landing page from an earlier iteration of the project | unused (no doc references) | 2025-01-05 | legacy |

(`assets/images/openswarm-project-image.jpg` is the project logo embedded in
README.md, not a screenshot.)

## Regenerating

```bash
.venv/bin/pip install playwright
.venv/bin/playwright install chromium
.venv/bin/python scripts/capture_user_journey.py            # desktop (1280x800)
.venv/bin/python scripts/capture_user_journey.py --mobile   # mobile (390x844, dpr 2)
```

The script is idempotent: it starts its own dev server on port 8321
(`DJANGO_DEBUG=true ENABLE_WEBUI=true`), runs migrations, creates a throwaway
superuser and logs in (so authenticated pages like the SPA chat render
realistically), captures every page in its `PAGES` list, overwrites the PNGs
here, skips (never fakes) any page that returns 4xx/5xx, then kills the server
and prints a captured/skipped summary. The SPA pages require a built
`webui/frontend/dist/`.

After regenerating, update the captions in
[USER_JOURNEY.md](./USER_JOURNEY.md) and [GUIDED_TOUR.md](./GUIDED_TOUR.md) if
the pages changed, and update this registry's "Captured" dates.

## Convention

* The **current** capture of each page lives in `docs/screenshots/` under a
  stable kebab-case filename (matching the `PAGES` slug in the capture
  script).
* When a screenshot is **superseded** but worth keeping for history, move the
  old file to `docs/screenshots/archive/` under the **same filename** before
  regenerating, and note it here with status "archived".
* Every screenshot added to the repo gets a row in this registry.
