# Screenshots

Captured by [`scripts/capture_user_journey.py`](../../scripts/capture_user_journey.py)
(headless Chromium, 1280x800, full-page) against a local dev server; embedded
in [`docs/USER_JOURNEY.md`](../USER_JOURNEY.md).

**Convention:** the current capture of each page lives here under a stable
kebab-case filename; when a screenshot is superseded but worth keeping for
history, move the old file to `docs/screenshots/archive/` under the **same
filename** before regenerating.

| File | Page | Notes |
| --- | --- | --- |
| `landing.png` | `/` | React SPA dashboard (experimental, minimally styled in this build) |
| `teams.png` | `/teams/` | Teams admin, empty fresh-db state |
| `teams-launch.png` | `/teams/launch/` | Team launcher with bundled `django_chat` selected |
| `blueprint-library.png` | `/blueprint-library/` | Bundled blueprint catalog with requirement badges |
| `my-blueprints.png` | `/blueprint-library/my-blueprints/` | Personal library, empty state |
| `agent-creator.png` | `/agent-creator/` | Custom agent persona form + code generation panel |
| `settings.png` | `/settings/` | Settings dashboard with config-progress meter |
