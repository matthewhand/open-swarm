# REQ-95 / #452 — Wave 3 Scope A: root-folder sprawl (look-only)

> **Look-only inventory** landed first (`#458`). A later implementer PR
> applied **only** the safe **N** delete / gitignore list below. No Pinokio
> moves, no root-guide merges, no `swarm_config.json` / remotes, no
> `build_all_blueprints.py` (Makefile still calls it), no fly/compose/oracle
> / Neon / golden-journey, no package reorg. **Do not `git apply` the leftover
> patches** — they were deleted unread.

**Safe N landed (implementer):**

| Path | Action |
|------|--------|
| `diff-commandpalette.patch`, `tabs-diff.patch` | **deleted** (not applied) |
| `build_blueprint_executables.py` | **deleted** (broken `blueprints/codey` path) |
| `pyinstaller_specs/codey.spec`, `pyinstaller_specs/geese.spec` | **deleted** |
| `scripts/codey_py_entry.py`, `scripts/aggregate_feedback.py` | **deleted** (still no callers) |
| `.grok/workflows/moa-team-megafan-report.md` | **deleted** (accidental scratch dump; not re-homed) |
| `.grok/`, `.Jules/` | **gitignored** and untracked (`.cursor/` stays) |

**Skipped (still load-bearing or out of this PR):**

- `assets/images/favicon.ico` — REQ-106 (`#487`) now copies the bee ICO here
  (`scripts/export_brand_icons.py`) and
  `tests/unit/test_req106_brand_mark.py` asserts byte-equality with
  `assets/brand/favicon.ico`. SPA/Django hrefs are `/favicon.ico` and
  `brand/favicon.ico`, not this path, but deleting it would fail that test.
- Large `assets/images/20250105-Swarm-Openwebui-Voice-Demo.mp4` — skipped
  (blob risk).
- `scripts/delete_stale_branches.sh` — not run; not deleted here.
- `build_all_blueprints.py`, `swarm_cli_hook.py` — Makefile still calls the
  builder.

**Issue:** [#452](https://github.com/matthewhand/open-swarm/issues/452) (REQ-95).
**As-of:** `origin/main` @ `ccc1b33e`
(`feat(webui): show selected-agent avatar next to the header name (REQ-60) (#401)`).

**Method:** `git ls-files` of root + scoped dirs; static read of each listed
file; ripgrep for inbound references (tests, Makefile, `pyproject.toml`,
docs, Pinokio). No Neon. No secrets dumped. No live host. Golden-journey /
unrelated CI ignored.

**Load-bearing column**

| Mark | Meaning |
|------|---------|
| **Y** | Something in-tree (code, test, Makefile, Pinokio, packaging, README embed) will break or lie if this path vanishes or moves without a follow-up edit. |
| **N** | No inbound reference found. Safe *in principle* to archive/delete later — still do not do it in this wave. |
| **?** | Referenced in docs or a Makefile help line, but the file itself is stale, broken, or superseded. |

**Action column** is a *proposal for a later implementer Issue* (keep /
move-to / merge-into / delete / archive / gitignore). Not work done here.

---

## 1. Inventory

### 1.1 Root markdown + NOTICE + LICENSE

| Path | Apparent role | Load-bearing | Proposed action |
|------|---------------|--------------|-----------------|
| `README.md` | GitHub + PyPI landing (`pyproject.toml` `readme =`). Quickstarts, screenshot embeds, doc map. | **Y** — packaging, `tests/unit/test_pinokio_scripts.py`, `tests/unit/test_screenshot_registry.py` (scans `README.md` + `docs/**/*.md`) | **keep** at root (GitHub/PyPI convention) |
| `USERGUIDE.md` | Task-oriented `swarm-cli` reference; `<!-- from-scratch: -->` fences | **Y** — `tests/unit/test_screenshot_registry.py` opens `REPO / "USERGUIDE.md"`; `tests/core/test_userguide_captures.py` opens cwd `USERGUIDE.md`; `scripts/paste_userguide_from_scratch.py` writes it | **keep** for now; later **move-to** `docs/USERGUIDE.md` *only* with those three callers + README links (Scope C) |
| `DEVELOPMENT.md` | Architecture / tech-stack / (stale) tree diagram | **Y** — README + CONTRIBUTING point here; tree still shows `swarm_config.json.example` (file **does not exist**) and a `./swarm_config.json` Docker mount that `docker-compose.yml` no longer does | **merge-into** `docs/DEVELOPER_GUIDE.md` (that file is still a stub) after Scope C; do not delete inbound links first |
| `CONTRIBUTING.md` | Dev setup, pytest, ruff, PR rules | **Y** — README, `docs/DEVELOPER_GUIDE.md`, GitHub convention | **keep** at root |
| `ROADMAP.md` | Claimed “single source of truth” for status (last updated 2026-06-19) | **Y** — README, CONTRIBUTING, `docs/TODO.md` stub, `docs/VISION.md`; `src/swarm/mcp/provider.py` cites `ROADMAP.md §3.3` | **keep** or later **move-to** `docs/ROADMAP.md` with link updates; honesty vs `FEATURE_STATUS.md` is Scope C |
| `TODO.md` | Slim leftover task list; points at `ROADMAP.md` | **?** — `docs/TODO.md` is a redirect *to this file*; DEVELOPMENT.md still describes a coordinator that reads root `TODO.md` | **merge-into** `ROADMAP.md` (or a `docs/debt/` punch-list) then leave `docs/TODO.md` as the only stub |
| `FEATURE_STATUS.md` | Live evidence board (header: 2026-08-18) | **Y** — `tests/unit/test_screenshot_registry.py` reads `REPO / "FEATURE_STATUS.md"`; README / ROADMAP / AUTH / VISION link it | **keep** for now; later **move-to** `docs/FEATURE_STATUS.md` only with the registry test |
| `CONFIGURATION.md` | Canonical `swarm_config.json` + env reference | **Y** — `docs/SWARM_CONFIG.md` is already a redirect here; README, USERGUIDE, `blueprint_base.py` / `stewie` comments cite it | **keep** or later **move-to** `docs/CONFIGURATION.md` (update the stub + comments). Do **not** also keep a second full copy |
| `CHANGELOG.md` | Keep-a-Changelog; `pyproject.toml` `[project.urls] Changelog` | **Y** | **keep** at root |
| `NOTICE` | Attribution + vendored-asset licenses (Bootstrap, Prism, FA, marked, Tabler, htmx) | **Y** — legal | **keep** at root |
| `LICENSE` | MIT | **Y** — `pyproject.toml` `license`, hatch `include` | **keep** at root |

Root-guide sprawl is real: eight human docs at `/` plus `docs/QUICKSTART.md`,
`docs/DEVELOPER_GUIDE.md` (stub), `docs/SWARM_CONFIG.md` (redirect),
`docs/TODO.md` (redirect), `docs/VISION.md`. **Scope C** should pick one map;
this table only flags what a move would break.

### 1.2 Leftover patches

| Path | Apparent role | Load-bearing | Proposed action |
|------|---------------|--------------|-----------------|
| `diff-commandpalette.patch` | Unapplied `git diff` that **deletes** `webui/frontend/src/experimental/CommandPalette.tsx` | **N** — zero references. File still exists and is mounted from `App.tsx` (wave1 debt: dual palettes) | **delete** or **archive** under `docs/archive/patches/`. **Do not apply** — it would delete a live (if experimental) module |
| `tabs-diff.patch` | Unapplied diff that **reverts** DaisyUI v5 class names (`tabs-box` → `tabs-boxed`, etc.) | **N** — zero references. Current `Tabs.tsx` already has the v5 names the patch would undo | **delete**. Applying it is a product regression |

### 1.3 Pinokio / root `*.js`

Pinokio sideload contract: `pinokio.js` must live at the **clone root** and
`href` sibling scripts by basename. `tests/unit/test_pinokio_scripts.py`
hard-codes those four paths.

| Path | Apparent role | Load-bearing | Proposed action |
|------|---------------|--------------|-----------------|
| `pinokio.js` | Local-only Pinokio menu (Install / Start+Update / Open App). REQ-47 | **Y** — Pinokio + unit test | **keep** at root |
| `install.js` | `docker compose build` + `.pinokio/installed` marker | **Y** | **keep** at root |
| `start.js` | `docker compose up`, `SWARM_RUNTIME=sandbox-home` | **Y** — also mentioned in `docker-compose.yml` comments | **keep** at root |
| `update.js` | `git pull --ff-only` then `install.js` | **Y** | **keep** at root |

`.pinokio/` (created at install time) is already gitignored. Correct.

### 1.4 Legacy PyInstaller helpers

Canonical compile path today is `swarm-cli install-executable` in
`src/swarm/core/swarm_cli.py`: it generates a spec under the **user cache**
(`~/.cache/swarm/specs`), does **not** read `pyinstaller_specs/`, and does
**not** pass `swarm_cli_hook.py`.

| Path | Apparent role | Load-bearing | Proposed action |
|------|---------------|--------------|-----------------|
| `build_all_blueprints.py` | Walks `src/swarm/blueprints/**/blueprint_*.py`, `pyinstaller --onefile` + `--runtime-hook swarm_cli_hook.py` → `bin/` | **?** — only caller is `make build-all-pyinstaller` (Makefile help labels it **LEGACY**). `.gitignore` already ignores `bin/*` | **archive** or **delete** after Makefile drops the target (Scope D). Do not delete while the target still calls it |
| `build_blueprint_executables.py` | Builds **only** `blueprints/codey` (path has **no** `src/swarm/` prefix) | **N** — that directory does not exist; script prints “Codey blueprint directory not found.” No Makefile / test / doc caller | **delete** |
| `swarm_cli_hook.py` | PyInstaller runtime hook: `SWARM_CLI=1`, stderr → `SWARM_STDERR_LOG` or `os.devnull` | **?** — only referenced by the two root `build_*.py` files, not by `swarm_cli.py` | **delete** with the legacy builders, or **move-to** `scripts/packaging/` if hook behavior is still wanted |
| `pyinstaller_specs/codey.spec` | Checked-in spec: entry `src/swarm/blueprints/codey/blueprint_codey.py` | **N** — not passed to any current command. `.gitignore` has `*.spec` (these two are already-tracked exceptions). `.dockerignore` excludes `pyinstaller_specs/` | **delete** or **archive** |
| `pyinstaller_specs/geese.spec` | Same, for `geese` | **N** | **delete** or **archive** |

### 1.5 `swarm_config.json`

| Path | Apparent role | Load-bearing | Proposed action |
|------|---------------|--------------|-----------------|
| `swarm_config.json` | Committed **sample** (LLM profiles, MCP catalog, `agent_team`, remotes). Keys are `${ENV}` placeholders — no raw secrets in the file | **Y** — discovery order is `SWARM_CONFIG_PATH` → XDG `~/.config/swarm/swarm_config.json` → **cwd `./swarm_config.json`**. `src/swarm/utils/env_utils.py` defaults `SWARM_CONFIG_PATH` to repo-root `swarm_config.json`. A developer running from the clone **will** load this file. Docker compose now bind-mounts **XDG**, not this path (DEVELOPMENT.md is stale) | **keep** as the in-repo example **or** **move-to** `docs/examples/swarm_config.example.json` and add the missing `swarm_config.json.example` DEVELOPMENT.md already documents. Either way, later strip **operator-LAN remotes** (RFC1918 `base_url`s) into an override example so the committed default is generic |

`docs/examples/cli_fusion.swarm_config.json` and
`docs/examples/moa.swarm_config.json` already exist as topic examples.

### 1.6 `assets/`

Four tracked files, ~7.4 MB. Journey PNGs live under `docs/screenshots/`
(out of this scope).

| Path | Apparent role | Load-bearing | Proposed action |
|------|---------------|--------------|-----------------|
| `assets/images/openswarm-project-image.jpg` | README hero (~580 KB) | **Y** — `README.md` `<img src="assets/images/openswarm-project-image.jpg">` | **keep** or later **move-to** `docs/assets/` with one README edit |
| `assets/images/favicon.ico` | Old favicon (~244 KB) | **N** — no href / Django / SPA reference | **delete** or **archive** |
| `assets/images/20250105-Open-Swarm-HTML-Page.png` | 2025-01-05 HTML landing | **N** — `docs/SCREENSHOTS.md` already lists it as **unused / legacy** | **archive** (e.g. `docs/screenshots/archive/`) or **delete** |
| `assets/images/20250105-Swarm-Openwebui-Voice-Demo.mp4` | ~6.4 MB voice-demo video | **N** — no markdown embed found | **archive** or **delete** (largest single root-adjacent blob) |

### 1.7 `scripts/` entrypoints only

`scripts/` stays as the repo’s extra-entry bin. Several scripts are CI / Make
/ pre-commit load-bearing; several are live-proof demos; a few look one-shot
or path-broken. **Do not relocate the load-bearing ones** without Makefile /
workflow / pre-commit edits (Scope D).

| Path | Apparent role | Load-bearing | Proposed action |
|------|---------------|--------------|-----------------|
| `scripts/build_frontend.sh` | `npm ci` + Vite `dist/` | **Y** — `make frontend`, `.github/workflows/python-pytest.yml`, `.cursor/install.sh`, CONTRIBUTING / DEPLOYMENT | **keep** |
| `scripts/run_tests.py` | Pytest wrapper (`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`) | **Y** — `make test`. CI itself calls `uv run pytest` (known dual-suite, `docs/debt/tests-ci.md` D-08) | **keep** |
| `scripts/lint_blueprints.py` | Static blueprint UX lint | **Y** — `.pre-commit-config.yaml`, CONTRIBUTING | **keep** |
| `scripts/check_ux_compliance.py` | Runtime `SWARM_TEST_MODE` UX scan | **Y** — CONTRIBUTING / README | **keep** |
| `scripts/capture_user_journey.py` | Playwright journey PNGs | **Y** — SCREENSHOTS / GUIDED_TOUR / USER_JOURNEY. (Golden-journey honesty is **out of this wave**.) | **keep** |
| `scripts/render_demo_gif.py` | README `docs/demo/cli-and-api.gif` | **Y** — `docs/SCREENSHOTS.md` | **keep** |
| `scripts/paste_userguide_from_scratch.py` | Pastes `$SCRATCH/*.txt` into USERGUIDE / README fences | **Y** — paired with `tests/core/test_userguide_captures.py`. Default `SCRATCH=/tmp/grok-goal-4567a1afab94/implementer` is a **dead agent path** | **keep** the mechanism; later stop hard-coding a vanished scratch dir |
| `scripts/demo_moa_consensus_vs_team.py` | MoA contrast demo | **Y** — `docs/examples/moa-consensus-vs-team/` | **keep** |
| `scripts/trace_moa_champagne.py` | MoA invariant trace | **Y** — same example README | **keep** |
| `scripts/demo_moa_grok_multiseat.py` | Live/fake multi-seat MoA | **Y** — `docs/MOA.md` | **keep** |
| `scripts/prove_cli_permutations.py` | Live CLI×mode matrix | **Y** — `docs/VISION.md`, `docs/proofs/` | **keep** (opt-in live; not CI) |
| `scripts/prove_swarm_workflows.py` | Workflow A/B proof | **Y** — `docs/SWARM_WORKFLOWS.md` | **keep** |
| `scripts/prove_mcp_live.py` | Live MCP resolve+stdio | **Y** — `docs/examples/mcp-live-proof.md` | **keep** |
| `scripts/prove_skill_across_clis.py` | Skill portability proof | **Y** — `docs/SKILLS_AND_CONSENSUS_WALKTHROUGH.md` | **keep** |
| `scripts/prove_skill_asset_toolcall.py` | Bundled-asset toolcall proof | **Y** — same + `docs/examples/skill-bundled-asset-toolcall.md` | **keep** |
| `scripts/prove_gemini_toolcalling.py` | Live tool-use proof | **?** — sibling of the prove_* family; thinner inbound docs | **keep** with proofs |
| `scripts/demo_consensus.py` | 3-CLI consensus artifact | **Y** — walkthrough doc | **keep** |
| `scripts/demo_inference_profile.py` | Intent→CLI routing demo | **Y** — `docs/examples/inference-profile-routing.md` | **keep** |
| `scripts/smoke_api.sh` | `/v1/models` + one completion | **?** — useful operator smoke; no CI caller found | **keep** |
| `scripts/gen_blueprint_table.py` | Rewrites a README blueprint table | **?** — README comment points at it; not CI | **keep** or fold into a docs Makefile target |
| `scripts/codey_py_entry.py` | Test-mode wrapper that execs `codey_cli.py` | **N** — no callers | **delete** |
| `scripts/aggregate_feedback.py` | Regex-harvest `*.md` surveys | **N** — no callers, no `feedback/` tree | **delete** |
| `scripts/delete_stale_branches.sh` | One-shot 2026-06 origin cleanup (`git push --delete`) | **N** for product; **dangerous** if re-run (hard-coded branch list + `--merged`) | **archive** then **delete** from default branch |
| `scripts/stress_test_suite.py` | Parallel pytest hammer | **N** — optional; writes `swarm_stress_*` at cwd | **keep** as opt-in or **move-to** `scripts/dev/` |
| `scripts/capture_cli_evidence.sh` | Writes `$SCRATCH` CLI transcripts | **?** — pairs with paste_userguide; requires `SCRATCH` | **keep** with the paste pipeline |
| `scripts/capture_prod_evidence.sh` | Local “prod-like” server + curl into `$SCRATCH` | **?** — starts `src/manage.py runserver` (path may be stale vs root `manage.py`); contains `pkill -f` | **keep** only after a later audit of the pkill / path; do not run from a cloud agent |

### 1.8 Agent-tooling dirs: `.cursor/` vs `.Jules/` vs `.grok/`

| Path | Apparent role | Load-bearing | Proposed action |
|------|---------------|--------------|-----------------|
| `.cursor/environment.json` | Cursor **Cloud Agent** env: install/start/ports | **Y** — Cloud Agents bootstrap this file | **keep** in repo |
| `.cursor/install.sh` | Idempotent `uv sync --all-extras` + `scripts/build_frontend.sh` | **Y** — referenced by `environment.json` | **keep** in repo |
| `.Jules/hone.md` | Jules “architectural audit” protocol notes (DaisyUI modal / a11y) | **N** — personal agent memory; not imported by product or CI | **gitignore** (or **move-to** a private gist). Does not belong on the default branch |
| `.grok/workflows/architecture-finish.rhai` | Grok megafan: hardcoded `/home/matthewh/open-swarm` | **N** — operator machine path | **gitignore** (local) |
| `.grok/workflows/polish-loop.rhai` | Recurring Grok polish pulse | **N** | **gitignore** |
| `.grok/workflows/moa-team-megafan.rhai` | MoA megafan workflow | **N** | **gitignore** |
| `.grok/workflows/moa-team-megafan-report.md` | Huge dumped JSON report from a past Grok run | **N** — scratch output committed by accident | **delete** (or **archive** off `main`) |

**Repo vs local**

| Keep in git | Treat as local |
|-------------|----------------|
| `.cursor/` (shared Cloud Agent bootstrap; no secrets) | `.Jules/`, `.grok/` (operator-specific agent transcripts / host paths) |
| Pinokio `*.js` at root | `.pinokio/` (already ignored) |
| `.env.example` | `.env`, `docker-compose.override.yml` (already ignored) |

`.gitignore` does **not** currently mention `.Jules/` or `.grok/`. Adding
those patterns is a later implementer change, not this wave.

### 1.9 Adjacent root items (observed, not scored)

Not in Scope A’s required list; listed so Scope B/D do not rediscover them
as “mystery root”:

| Path | Note |
|------|------|
| `avatars/` | Empty, **untracked** directory on this checkout. REQ-60 avatar work lives under product trees, not here. Safe to leave untracked / not commit |
| `manage.py`, `Makefile`, `Dockerfile*`, `docker-compose*`, `fly.toml`, `pytest.ini`, `pyproject.toml`, `uv.lock`, `.env.example`, `.github/` | Scope D / B. **keep** at root in the target layout below |
| `src/`, `webui/`, `tests/`, `docs/`, `skills/`, `deploy/` | Other scopes |

---

## 2. Do not do yet (risks)

1. **Do not move Pinokio `*.js` off the repo root.** Pinokio resolves
   `href: "install.js"` from the clone root; `tests/unit/test_pinokio_scripts.py`
   asserts those exact paths.
2. **Do not move `USERGUIDE.md` or `FEATURE_STATUS.md` without a test +
   script pass.** `test_screenshot_registry.py`, `test_userguide_captures.py`,
   and `scripts/paste_userguide_from_scratch.py` open them at repo root / cwd.
3. **Do not `git apply` the two leftover patches.**
   `tabs-diff.patch` reverts live DaisyUI v5 class names.
   `diff-commandpalette.patch` deletes a file `App.tsx` still imports.
   Command-palette product work is already tracked as SPA debt (wave1), not
   as a root-file apply.
4. **Do not delete `swarm_config.json` until discovery + example story is
   decided.** Cwd fallback and `env_utils.get_swarm_config_path()` will load
   *something* from the repo root today. A missing file is a behavior change
   for anyone who `cd`s the clone and runs `swarm-cli` / `swarm-api`.
5. **Do not gitignore `.cursor/`.** That is the Cloud Agent install/start
   contract, not local IDE junk (`.serena/` / `.letta/` are the local ones).
6. **Do not delete `build_all_blueprints.py` while `make build-all-pyinstaller`
   still calls it.** Retarget or drop the Makefile target in the same PR
   (Scope D).
7. **Do not merge/move root guides in this wave.** Scope C owns
   README / USERGUIDE / DEVELOPMENT / CONFIGURATION / ROADMAP / TODO /
   FEATURE_STATUS vs `docs/*` stubs. Dual copies will drift if A moves and C
   has not picked a canonical map.
8. **Do not run `scripts/delete_stale_branches.sh` or
   `scripts/capture_prod_evidence.sh` from a look-only / cloud agent.**
   The first force-deletes origin branches; the second `pkill`s by pattern.
9. **Do not treat committed remotes in `swarm_config.json` as a public
   template.** Keys are placeholders; host URLs are operator-LAN. A later
   cleanup should example-ize them — do not paste live LAN details into
   Issues/PRs.
10. **Do not enable Neon, touch golden-journey, or “fix” CI** as part of
    implementing this inventory.

---

## 3. Proposed target layout (root)

A later implementer PR (after CoS + Matthew pick resolutions) should aim
for a **thin root**: legal + landing + packaging + Pinokio + compose +
source trees. Everything else is `docs/`, `scripts/`, or gitignored.

**Stay at repository root**

- `README.md`
- `LICENSE`, `NOTICE`
- `CHANGELOG.md`
- `CONTRIBUTING.md`
- `pyproject.toml`, `uv.lock`, `pytest.ini`, `.pre-commit-config.yaml`
- `Makefile`, `manage.py`
- `Dockerfile`, `docker-entrypoint.sh`, `docker-compose.yml`,
  `docker-compose.dev.yml`, `docker-compose.override.example.yml`,
  `.dockerignore`, `fly.toml`
- `.env.example`, `.gitignore`
- `pinokio.js`, `install.js`, `start.js`, `update.js`
- `.cursor/` (Cloud Agent bootstrap)
- Trees: `src/`, `tests/`, `docs/`, `webui/`, `scripts/`, `skills/`,
  `deploy/`, `.github/`

**Move (later; not this PR)**

- `USERGUIDE.md` → `docs/USERGUIDE.md` (update three test/script lock-ins)
- `DEVELOPMENT.md` → merge into `docs/DEVELOPER_GUIDE.md`
- `CONFIGURATION.md` → `docs/CONFIGURATION.md` (keep `docs/SWARM_CONFIG.md` as the redirect)
- `ROADMAP.md`, `FEATURE_STATUS.md` → `docs/` (or keep **one** status file at root if GitHub browsing prefers it — pick in Scope C)
- `TODO.md` → merge into `ROADMAP.md`; keep only `docs/TODO.md` redirect
- `swarm_config.json` → `docs/examples/swarm_config.example.json` **or**
  root `swarm_config.json.example` (match DEVELOPMENT.md); generic remotes only
- `assets/images/openswarm-project-image.jpg` → `docs/assets/` (or keep a
  one-file `assets/` if README-at-root hero is preferred)
- Legacy PyInstaller trio + `pyinstaller_specs/` → `docs/archive/packaging/`
  then delete once Makefile no longer calls them
- Proof/demo scripts may stay in `scripts/` (already the right home); optional
  later buckets `scripts/proofs/` and `scripts/dev/` — only if inbound docs
  are updated in the same PR

**Delete / archive (later)**

- `diff-commandpalette.patch`, `tabs-diff.patch`
- `build_blueprint_executables.py` (broken path)
- `scripts/codey_py_entry.py`, `scripts/aggregate_feedback.py`
- `scripts/delete_stale_branches.sh` (after archive)
- `assets/images/favicon.ico`, `20250105-Open-Swarm-HTML-Page.png`,
  `20250105-Swarm-Openwebui-Voice-Demo.mp4`
- `.grok/workflows/moa-team-megafan-report.md`

**Gitignore (later)**

- `.Jules/`
- `.grok/`
- (already): `.pinokio/`, `.env*`, `docker-compose.override.yml`, `bin/*`,
  `*.spec`, `.venv/`, `.serena/`, `.letta/`

**Do not add to git**

- `avatars/` (empty local dir on this checkout)
