# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added
- **REQ-66 scale-out rail:** An agent with more than one session stays **one** sidepane row. Stacked hop-style avatars (max 3 + remainder). Every face pulses with a start-time stagger (not lockstep). Click opens a search-palette popup of that agent’s running and finished sessions; picking a row opens `?session=` in the still-mounted chat. v1: picker only when session count > 1. (#394)
- **REQ-37 nested conversation compact:** Composer `+` menu Compact summarises the backlog into a Django/sqlite `ConversationSummary` (`span`, `parent_summary_id`, `body`). Raw JSON + `ChatMessage` rows stay. Later compacts nest. UI renders bordered `.chat-summary` blocks. Model context walks the summary tree. No Neon.
- **REQ-25 hover-edit on role agents:** Rail rows for the example roles (support, gate, skeptic) reveal a focusable edit icon on hover. Enter/click opens a DaisyUI `modal-end` Settings sheet scrolled to the Blueprint editor, which shows that agent's Python (`highlightPython` / `os-code-python`). Live `blueprint_support.py` / `tool_gate` / `skeptic` files are linked when `/v1/blueprints/<id>/source` lists them. Does not open the Teams drop-zone and does not rewrite role runtime.

### Changed
- **REQ-26 first-load Hidden seed:** First visit (no `localStorage.swarm_hidden_agents`) hides gate and skeptic (`gate` / `tool_gate` / `skeptic` — whatever ids the catalog ships). Support stays visible and highlighted. An existing hidden list, including `[]` after Unhide, is not re-seeded. Hidden drop zone + N hidden popup still work; role agents remain hideable.
- **REQ-24 Hidden drop zone:** Any left-rail conversation row (including role agents support / gate / skeptic) can be dragged onto an always-visible Hidden drop zone (`os-drop-target`, `data-drag-over`; empty hint “drop here to hide”). Hide writes `localStorage.swarm_hidden_agents` and removes the row from the list **and** the favourite pin grid. Unhide is still the **N hidden** dialog (no Hide-all). Context-menu Hide remains for a11y.
- **Grok-Bot SPA chrome:** Product UI is left rail + the selected agent's chat (no Home/Chat/Blueprints/Teams/Settings top nav). Rail: Search command palette, unlabeled favourite tiles, Support-first conversations, hidden-agents Unhide popup, Plugins, editable hostname. Composer is a `[+] [ Message … ] [mic]` pill; theme is an icon toggle; footer is tokens / who+how-long; errors toast. Operator Django pages stay on the composer + menu.
- **SPA + Django dark chrome (REQ-5 / REQ-5c):** DaisyUI cupcake/rainbow operator skin replaced with near-black Grok-like chrome. Home dashboard four quick actions are large cards. Django Blueprints / Teams / Sessions / Settings share the same nav + AGENTS sidepane (right-click Hide from sidebar, Hidden + Unhide, `localStorage.swarm_hidden_agents`). Settings purple gradient header removed. Primary actions on those pages are large cards, not tiny rainbow buttons.
- **Mobile dock PNG honesty:** GUIDED_TOUR / SCREENSHOTS admit journey capture parks fixed bottom navs as `position:static` so full-page mobile PNGs show the tab bar after scrolled content (not a live viewport overlay) — locked by `tests/unit/test_screenshot_registry.py`
- **Journey screenshots (2026-08-19):** regenerated desktop + mobile via `capture_user_journey.py`; captions/registry now match **Connected** `spa-chat`, **`fs_introspect`** launcher default, sticky **Redirected:** banners on `spa-*`, dashboard 0/45/45 + library 12 of 38, ADR-001 nav honesty (`tests/unit/test_screenshot_registry.py`)

### Fixed
- **REQ-5d Django operator chrome:** login styles in `operator.css` no longer flex-center every `body`. Teams / Sessions / Settings / Blueprint Library keep `.os-header` in the first viewport and dock AGENTS flush left (no ~35% leftover gutter). Session card previews wrap long error strings; agent row text truncates inside the pane; SPA `html`/`body` paint near-black so Chat has no light leftover strip.
- **REQ-5d `/chat` stays Chat:** first-class Django `/chat` (+ `/chat/`) serves the SPA shell; `/agents` and `/agents/` 302 to `/chat` (query preserved). SPA router aliases `/agents` → `/chat` and keeps `/chat/` on ChatPage (composer + Connected). Chat nav stays `href="/chat"` / `to="/chat"`.
- **Screenshot honesty (library MCP + my-blueprints + spa-chat Connected):** GUIDED_TOUR / USER_JOURNEY / SCREENSHOTS match checked-in PNGs — blueprint-library MCP badges are ready green checkmarks (not a checking spinner); my-blueprints shows Custom Created **3** (**Agent A**/**B**/**C**), not an empty library; Agent Creator captions name **1 Identity** / optional Persona+Tags; desktop + mobile `spa-chat.png` hardclaim **Connected** (recaptured mobile off Connecting…). Capture hard-fails spa-chat on non-terminal badge unless `--allow-connecting`, supports `--only STEM`, and isolates `SWARM_USER_DATA_DIR` so future regenerations ignore host customs. Locked by `tests/unit/test_screenshot_registry.py`
- **Screenshot honesty (settings empty meter):** GUIDED_TOUR / USER_JOURNEY / SCREENSHOTS captions match checked-in `settings.png` — **No settings configured** / **0 of 0** (not populated local config); keep `session-detail` as seeded `hybrid_team` fixture distinct from `fs_introspect` launcher; registry tests lock both (`tests/unit/test_screenshot_registry.py`)
- **Screenshot count honesty:** USER_JOURNEY / GUIDED_TOUR / SCREENSHOTS bridge `swarm-cli list` (**31** package dirs, incl. non-runnable `common`) vs library `discover_blueprints()` (**38**, Showing **12 of 38**) vs SPA `/v1/blueprints`+`/v1/models` (**45** after `swarm_*` aliases on `landing.png` 0/45/45); refresh stale CLI list transcript (drop deleted husks). Locked by `tests/unit/test_screenshot_registry.py`
- **Journey capture ADR-001 defects:** require built SPA `dist/`; wait 20s for word-bounded Connected/Unavailable (not Connecting…); inject Redirected banners at `body` start for spa-* redirect stems; park only visible mobile docks; seed `resp_journey_seed` only after empty `sessions` capture — locked by `tests/unit/test_screenshot_registry.py`
- **Agent Creator echo-only codegen:** `AgentPersonaGenerator` no longer emits nonexistent `model.chat_completion_stream`; uses `AsyncOpenAI` + `chat.completions.create(stream=True)` with warned echo fallback (same fix as library `generate_blueprint_code`) — `tests/unit/test_agent_creator_codegen.py`
- **Blueprint source/tools URL slash twins:** `/v1/blueprints/<id>/source/` and `/tools/` no longer 404; `/v1/cli-agents` and `/v1/config-options` gain no-slash twins (same pattern as `/v1/responses` and `/v1/chat/completions`)
- **FEATURE_STATUS / AUTH CSP honesty:** SPA mobile dock row no longer lists Settings (five tabs: Home·Chat·Blueprints·Teams·Sessions; Settings is desktop/gear); AUTH overview drops stale “style residual” — prod CSP is `script-src`/`style-src` `'self'` only. Locked by `tests/unit/test_screenshot_registry.py`
- **MCP blueprint→tool bridge silent no-op:** `register_blueprints_with_mcp()` now `logger.error`s when `mcp_server` ≥0.5 lacks flat `registry.register_tool` (or registration fails). `FEATURE_STATUS` + `docs/mcp_server_mode.md` state clearly: flag mounts `/mcp/`, blueprints are NOT tools until the MCPToolset port.
- **Screenshot/docs ADR-001 alignment:** tour captions name SPA desktop **Home · Chat · …**; `spa-*` embeds describe redirect landings with sticky “Redirected” banners in checked-in PNGs; SPA mobile dock drops Settings tab to match five-tab PNGs / SCREENSHOTS.md
- **WS anonymous receive race:** `DjangoChatConsumer.receive` re-checks session auth so a frame that lands after accept-but-before 4401 close cannot crash the consumer or reach blueprint/LLM paths
- **MoA `--act` phantom write:** `run_moa_cli` with `--act` and no `--act-write` now actually creates `moa_determination.md` (previously only `RecordingWriteSurface` + `ActResult` claimed the write)
- **Fly HTTP health check:** re-enable `[[http_service.checks]]` GET `/health` in `fly.toml` (was disabled 2026-06-20 while the image lacked the route); live `open-swarm.fly.dev/health` returns 200 `{"status":"ok"}`
- **SPA Chat Send honesty:** composer Send no longer shows a loading spinner while an assistant reply streams (progress stays on the bubble); avoids a false busy state on an enabled control
- **Library-generated blueprints echo-only run:** `generate_blueprint_code` no longer calls nonexistent `model.chat_completion_stream`; uses `AsyncOpenAI` + `chat.completions.create(stream=True)` (DjangoChat/DynamicTeam pattern) with an explicit warned echo fallback
- **Silent LLM profile fallback:** honor `blueprints[].default_model` / `settings.default_llm_profile`; **warn** (never silent) when a requested profile is missing, then fall back. `get_llm_profile` and Stewie warn on named misses; `llm_profile` stays fail-loud. Docs aligned in CONFIGURATION.md.

### Security
- **Prod CSP `style-src 'self'`:** operator template `style=""` moved to `operator.css` (`.os-hide` + `data-pct="N"` widths); ship missing `static/js/htmx_csp.js` referenced by `base.html` (HTMX indicator `<style>` inject off without inline script); session-detail graph uses `.sd-graph-svg` instead of `element.style` (AUTH.md §7)
- **Filesystem toolset secret dump:** default roots no longer include `~/open-swarm`; reads/lists/grep/find refuse credential files (`.env*`, private keys, `.pem`/`.key`, `.ssh`/`.aws`) even under an allow-listed root so `fs_introspect` cannot return live API keys via `/v1/chat/completions`
- **MCP stdio env leak:** MCP client/provider no longer pass the full parent `os.environ` into stdio MCP children (that exposed ambient API keys/tokens). Children get essentials (`PATH`/`HOME`/…) plus only vars declared in the server's `env` block.


### Added
- **REQ-47 Pinokio launcher (local sideload):** root `pinokio.js` menu (Install / Start+Update / Open App) plus `install.js`, `start.js`, and `update.js`. Start is `docker compose up` with REQ-45 `SWARM_RUNTIME=sandbox-home`. Not listed on pinokio.computer; add via git URL only.
- **REQ-27b Computer-control UI stub:** Grok chat header **Chat tools** toolbar (top-right) Monitor icon labeled Computer control opens a DaisyUI WIP modal (“computer control will use a placed OMB or Rakazo remote; not implemented here”). Icon visible by default (may look muted); clickable; not attached to agent tools; no driver/E2B/CUA/xdotool/CDP/sandbox. `ComputerControlStub` + ChatPage/e2e chrome tests.
- **REQ-28 Chief of Staff + team isolation + teams-of-teams:** role
  `chief_of_staff` (aliases `cos`, `chief`) with an ice-steel rail badge
  (not support/gate/skeptic colors). Composition rosters persist
  `{id, kind: api|cli|remote|team|herdr, role, source}` in
  `team_rosters.json` (`/v1/team-rosters/`). Default: no cross-team consult
  tools; CoS gets consult/handoff to every team id; a parent may send-to-all
  to a nested child team as one member, not every grandchild.
- **SPA DaisyUI settings sheet (REQ-19):** gear opens a right-docked `modal` + `modal-end` `<dialog>` over chat (Esc / backdrop close, `showModal()` focus lock). Inner DaisyUI `menu` + `menu-dropdown` (Remotes → Hermes / OMB / Rakazo placeholders; Retention; Hostname; LLM profiles). Retention uses `join` radios (Count / Disk / Archive / Trash) persisted in localStorage with a save toast; hostname override same. Settings is not a top-nav or mobile-dock destination. Django `/settings/` stays the operator dump (REQ-14 chat count / disk / trash).
- **Remote harnesses (REQ-11):** persist `remotes.hermes|omb|rakazo` (base URL + auth), honest health/version, and operate via each product's real API. CLI `swarm-cli remotes`, REST `/v1/remotes/`, Settings group, blueprint `remote_harness` (openai-agents as_tool — not a Grok/OMB/Rakazo seat clone). Rakazo RPC remains Better-Auth-gated. **Team** = API/CLI/remote members that see/talk via handoff/as_tool (`agent_team.members`, `GET/PATCH /v1/agent-team/`); `/teams/` is **Profiles** (LLM-profile aliases). Docs: [docs/REMOTE_HARNESSES.md](docs/REMOTE_HARNESSES.md).
- **REQ-14 per-agent chat persistence:** each agent thread is a JSON file under `$SWARM_USER_DATA_DIR/chats` (override `SWARM_CHAT_DIR`). Chat restores that thread after reload or agent switch. Settings shows chat count + disk use, can move chats to trash / empty trash, and auto-archives after `SWARM_CHAT_MAX_AGE_DAYS` (default 90; `0` disables). Not in the Chat chrome.
- **Herdr connectivity (REQ-21):** `swarm.herdr.HerdrClient` wraps the official `herdr` CLI (no invented socket protocol). Default is localhost (no `--remote`); optional agent `remote` prefixes `herdr --remote <value>`. `herdr agent prompt <TARGET> <TEXT>` passes TEXT as one argv (proven `w3:p1` / `HERDR_PING_OK` → `type: agent_prompted`). Persist members (`kind=herdr`) via Django ORM + `/v1/herdr-agents/` (SQLite default; no Neon). Discover live `agent list` / `workspace list` as addable members for Teams + sidepane. Cloud CI mocks `herdr`. Docs: [docs/HERDR.md](docs/HERDR.md).
- **SPA ChatPage markdown + auto-reconnect:** bubbles render GFM via `marked` then allowlist-sanitize (`htmlSafe`, same model as rest_mode); unexpected WS closes retry with exponential backoff (skip **4401** auth gate)
- **Responses store prune:** `swarm.core.responses_store.prune_expired` deletes terminal records older than `max_age_days` / `SWARM_RESPONSES_MAX_AGE_DAYS` (skips `queued`/`in_progress`; not automatic — operator/cron); notes in CONFIGURATION.md, ASYNC_RESPONSES.md, ORACLE_DEPLOY.md
- **SPA build wiring (ADR-001):** `make frontend` → `scripts/build_frontend.sh` (`npm ci` + verify `dist/index.html`); multi-stage `Dockerfile` bakes `webui/frontend/dist` for Docker/Fly; CI `frontend` job in `python-pytest.yml` runs the same script. After pull: `make frontend` (DEPLOYMENT.md / webui/README)
- **Settings credential checklist:** compact AUTH.md callout on `/settings/` (Chat/WS = session; `/v1/*` = Bearer or session; Explorer token bridge when API auth on; link to repo `docs/AUTH.md` — not served in-app)
- **Auth operator golden path:** `tests/api/test_auth_operator_golden_path.py` — with `ENABLE_API_AUTH`, session + Bearer `POST /v1/responses` stamp owners; Session Explorer bridge lists both for the web login; REST IDOR stays same-principal (bridge ≠ API privilege). Library create→run→sessions closer: exec `generate_blueprint_code` proves live `AsyncOpenAI` streaming (not echo-only), My Blueprints runner POSTs `/v1/chat/completions`, session/Bearer chat background stamps `owner`, Explorer list/detail shows those records (token bridge; foreign `user:` hidden)
- **Pure MoA team path (no openai-agents):** `run_moa_consensus` / `run_moa_then_team` / `TeamTask` in `swarm.core.moa.team`; INFO logs on `moa.collect` / `moa.team` (champagne trace)
- **`swarm-cli moa --team --workdir`**: consensus then scripted specialists (`--team-tasks`, `-v` INFO logs); mutually exclusive with `--act`
- **Examples:** `docs/examples/moa-consensus-vs-team/`, `docs/examples/moa-orchestrator/`; demos `scripts/demo_moa_consensus_vs_team.py`, `scripts/trace_moa_champagne.py`
- **`moa_orchestrator` blueprint**: scripted MoA→team via `run_moa_agents_orchestrator` → `run_moa_then_team` (`implementer`/`tester`/`docs`/`researcher` writes; no live openai-agents Runner by default; optional `build_moa_orchestrator_agents` for real Agents)
- **Skip-to-main:** skip links on Django `base.html` + SPA `App`; decorative mobile dock icons `aria-hidden`
- **`swarm-cli config init`:** writes default `swarm_config.json` (`--force` to overwrite); aligns config-loader error hints that already recommended it

### Changed
- **Docs honesty (ADR-001 / AUTH):** VISION version → v0.5.4 + AUTH/ADR see-also; QUICKSTART leads with Django-canonical UI + Bearer≠WS, fixes Docker boot trio vs `OPENAI_API_KEY`, renumbers sections, drops false `~/.swarm/swarm.log`; DEPLOYMENT WS 4401 points at `/login/` per AUTH.md. USERGUIDE already matched.
- **Blueprints README honesty:** inventory lists only discoverable dirs + GLOSSARY links; remove stale EchoCraft/Nebula/MissionImprobable/WhingeSurf/… rows
- **CSP prep — library/session pages:** extract `blueprint_library` (+ `blueprint_card`), `my_blueprints`, `blueprint_creator`, and `session_detail` inline scripts to `static/js/` (`{% static %}`); AUTH.md extraction progress updated
- **CSP prep — creator pages:** extract `agent_creator` / `team_creator` inline scripts to `static/js/` (`{% static %}`); team profiles via `json_script` island; AUTH.md extraction progress updated
- **ADR-001 SPA finish:** delete `webui/frontend/src/pages/_quarantine/` (no remount bait); drop Builder/Settings e2e stubs; VISION/FEATURE_STATUS/ROADMAP align — SPA stays `/` + `/chat` only. Rebuild `dist/` after pull (`npm run build` — gitignored).
- **ADR-001 SPA route cut:** React SPA mounts only `/` + `/chat`; Teams/Blueprints/Settings/Builder/AgentCreator pages were first quarantined then deleted; e2e/a11y/shots limited to live stems; nav/dock link out to Django for operator chrome.
- **v1 product vocabulary:** [docs/GLOSSARY.md](docs/GLOSSARY.md) + honesty sweeps (Blueprint vs `/v1/teams` LLM-profile alias; Operator UI vs SPA Chat); confirm `blueprint_audit_status.json` gone; ROADMAP v1 cut → ADR-001 + glossary
- **Settings dashboard dead-end honesty:** Validate Config / env Export use “(not available)” (not “(soon)”); unwired path-check buttons removed
- **MoA CLI P1 UX:** soft `--team` failure still prints payload then exits 1; `-v` scopes INFO to `swarm.core.moa` (no root `basicConfig`); seeds `notes.txt` only if missing; `--trace` creates parent dirs
- **MoA soft-fail honesty:** `format_team_text` no longer labels empty `--team` specialists as “consensus only”; CLI prints a `MoA team soft-fail:…` stderr line after the payload; USERGUIDE / TROUBLESHOOTING exit-1 wording aligned
- **Docs polish:** journey screenshots regenerated (2026-08-18) + caption/registry honesty; MoA troubleshooting; FEATURE_STATUS MoA team-path row; `cli-and-api.gif` refreshed from `SWARM_TEST_MODE` captures (optional `moa --team` scene)
- **Session detail journey capture:** mid-run seed of `resp_journey_seed` so `session-detail.png` shows Graph/timeline; embeds in USER_JOURNEY / GUIDED_TOUR / SESSION_EXPLORER with seeded-fixture honesty (synthetic JSON, not a live hybrid_team run)
- **SPA vs Django mobile docks:** recapture after Chat dock; docs distinguish SPA **Home · Chat · Blueprints · Teams · Sessions** from Django **… · Settings**; journey `spa-chat.png` is Connected post-login
- **Session Explorer empty state:** recapture `sessions.png` (+ mobile) for owner-scoped copy (“only sessions you own”)
- **`/v1/teams/` honesty:** OpenAPI + module docs label teams as LLM-profile aliases (not a multi-agent team builder)

### Removed
- **Empty `swarm.extensions.config` package:** delete leftover `__init__.py` after config_loader shim sunset; tests lock `ModuleNotFoundError`
- **Empty blueprint husks:** delete non-discoverable dirs with no `blueprint_*.py` (`flock`, `digitalbutlers`, `echocraft`, `mcp_demo`, `mission_improbable`, `monkai_magic`, `nebula_shellz`, `omniplex`); FEATURE_STATUS §9 curated to match live discovery (chatbot stays ✅)
- **Remaining consolidation deprecation shims (ROADMAP §2.1):** delete `extensions/config/config_loader`, `blueprints/common/spinner`, `ux/spinner`, `utils/ansi_box`, and `extensions/launchers/swarm_api`; import `swarm.core.config_loader`, `swarm.core.spinner`, `swarm.ux.ansi_box` / `swarm.core.output_utils.ansi_box`, and `swarm.core.swarm_api` instead. `tests/unit/test_deprecation_shims.py` now asserts `ModuleNotFoundError`.
- **Orphan SPA Builder panels:** delete unused Inference/Skills/Trait/ToolCapabilities/BlueprintToolsBadges/CodeViewer/ApiAccess/ConfigSnippet/InfoTip + AuthContext; move `buildCandidates` into `lib/inferenceProfile.ts`; drop `@uiw/react-codemirror` / `@codemirror/lang-python`
- **`swarm.extensions.blueprint` deprecation shim:** delete the package (`__init__` / `spinner` / `slash_commands`); import `swarm.core.blueprint_base`, `swarm.core.spinner`, and `swarm.core.slash_commands` instead.
- **Orphan argparse CLI trees:** delete `src/swarm/extensions/cli/` and unused `src/swarm/core/cli/` (dead-alias warning source); drop non-shipped `extensions.launchers.swarm_cli` / `swarm_wrapper`; relocate `AsyncInputHandler` → `swarm.core.async_input`, `prompt_user` → `swarm.core.config_manager`. `swarm-api` / `swarm-cli` both enter via `swarm.core.*` in pyproject. Tests that only covered the orphan trees removed.
- **Agent Creator Pro leftovers:** delete unused `agent_creator_pro` view/template/JS/CSS; `/agent-creator-pro/` redirect to `/agent-creator/` retained
- **SPA leftover pages:** TeamsPage / BlueprintsPage / SettingsPage / BuilderPage / AgentCreatorPage deleted from the SPA tree (ADR-001); `App.tsx` mounts `/` + `/chat` only
- **Orphaned rest_mode templates:** delete unrouted `templates/rest_mode/` (`slackbot.html`, `message_ui.html`, components); static `rest_mode/js` retained for XSS regressions
- **Stewie nested Django leftovers:** delete broken `apps`/`models`/`serializers`/`views`/`urls`/`settings` that imported nonexistent `blueprints.chc` and were never on `INSTALLED_APPS`; keep `blueprint_stewie.py`
- **Empty blueprint husks:** remove `family_ties/` and `whinge_surf/` directories that contained only `__pycache__` (not discoverable)

### Fixed
- **Stewie docs/tests honesty:** FEATURE_STATUS no longer claims nested Django / `blueprint_family_ties.py`; dedicated `tests/blueprints/test_stewie.py` covers `SWARM_TEST_MODE`
- **Library create→run path:** `generate_blueprint_code` emits a BlueprintBase `AsyncGenerator` `run` (yields message chunks; no invalid `__main__`/`asyncio.run`); My Blueprints runner POSTs `/v1/chat/completions` and links to `/chat?blueprint=` + `/teams/launch/` (replaces client-side “Simulate run” demo)
- **`swarm-cli config remove` missing target:** exits **1** (stderr) when the profile/server name is absent (was exit **0** after printing “not found”), matching `delete`/`uninstall`
- **Custom blueprint DELETE missing-id:** `DELETE /v1/blueprints/custom/<id>/` now returns **404** when the id is absent (was **204**), matching GET/PATCH on the same resource and DELETE on `/v1/library/` + `/v1/teams/`
- **Blueprint discovery model-id pollution:** `metadata["name"]` display/class labels (e.g. `Chuck's Angels`, `ChatbotBlueprint`) are no longer registered as `/v1/models` ids; only programmatic slugs (`^[a-z0-9]+(?:[_-][a-z0-9]+)*$`) and explicit slug `aliases` become keys
- **Agent Creator Pro retired:** `/agent-creator-pro/` redirects to `/agent-creator/`; dropdown nav link removed (was unwired clickware)
- **Blueprint AST sandbox Path.open write escape:** `Path(...).open('w')` / `p.open('wb')` put mode in the first positional arg (unlike builtin `open(file, mode)`), so write modes bypassed the open-ban; detect Path.open-style modes and reject them (keyword `mode=` was already caught)
- **CLI blueprint name path traversal:** `swarm-cli add`/`delete`/`uninstall`/`install-executable`/`launch` reject `../` and multi-segment names so library/bin joins cannot `rmtree`/`unlink`/exec outside XDG roots; `add`/`delete` also use `get_user_blueprints_dir()` instead of a hardcoded `~/.local/share/swarm/blueprints`
- **Blueprint AST sandbox getattr/runpy escapes:** reject `getattr(os, "system")` / `getattr(asyncio, "create_subprocess_*")` constant reflection that bypassed Attribute bans; ban `runpy` (code-loading peer of `importlib`)
- **Workdir confinement:** `params.workdir` / `params.cwd` (hybrid_moa, moa_orchestrator, cli_fusion_support consumers) and `swarm-cli moa --workdir`/`--cwd` resolve under `SWARM_WORKSPACES_DIR` / XDG `workspaces/`; absolute escapes rejected unless `ALLOW_UNRESTRICTED_WORKDIR=true`. Unset write workdirs get a per-run temp under that root.
- **Library blueprint_creator XDG save:** POST writes `blueprint_<id>.py` under `get_user_blueprints_dir()` (slug-safe) in addition to the JSON catalog, with the same discovery-opt-in message as Agent Creator
- **Filesystem toolset read cap:** `read(..., start_line/end_line)`, `head`, and `tail` now honor `max_read_bytes` (previously only full-file `read` was capped, so line-range peeks could return unbounded content)
- **QUICKSTART install wording:** `swarm-cli install` compiles via PyInstaller (does not download a package)
- **Fake Django UI actions honesty:** My Blueprints “Simulate run (demo)” + banner; Settings Validate/path-check/env Export disabled as not implemented; Team Creator Validate marked demo-only
- **`/v1/chat/completions` trailing slash:** slash twin so `…/completions/` no longer 404s
- **Agent Creator Pro preview XSS:** escape personality/style/expertise/template (and template tooltip) before capability `innerHTML` (static leftovers; route now redirects)
- **SPA DaisyUI Toast a11y:** `role="status"` + `aria-live` (assertive for error/warning); dismiss `type="button"`
- **Chat WS streaming XSS:** HTMX OOB append chunks now `django.utils.html.escape` model/user text (blueprint + LiteLLM paths and TEST-MODE echo); final template swap was already escaped
- **GitHub marketplace allowlist bypass:** client `org`/`topic` no longer replace configured allowlists; unknown values return **400** when lists are set (empty org allowlist remains intentionally unscoped)
- **Session Explorer attribute XSS:** live-poll `esc()` now escapes `"`/`'` used in `data-status`/`title`/`class` (status/role breakout)
- **rest_mode blueprintManager XSS:** escape API `id`/`title`/`description` via `htmlSafe.js` before dialog/dropdown/metadata `innerHTML`
- **`/v1/responses` trailing slash:** slash twins for create/detail/cancel (no more 404 on `…/responses/`)
- **MoA `--act` human output:** `run_moa_cli` stamps `mode=consensus_then_act` (not false `consensus_only`); CLI routes act payloads to `format_moa_text` so `## Act` appears; consensus/team still use `format_team_text`
- **Community blueprint namespace:** `merge_community_blueprints` now passes `namespace=swarm_community_{index}` into discovery so external packs (e.g. user `…/swarm/blueprints`) do not collide with real `swarm.blueprints` in `sys.modules`
- **Chat WS history duplication:** `save_conversation` deletes existing `ChatMessage` rows before `bulk_create` so reconnect → disconnect does not double the transcript
- **`make dev` live-reload:** `docker-compose.dev.yml` now overrides CMD to `uvicorn --reload` (workers=1) instead of claiming Django runserver autoreload; drop stale hatchling-irrelevant `open_swarm.egg-info` anonymous volume
- **Chat websocket auth messaging:** anonymous connects accept-then-close with code **4401**; SPA distinguishes session-required vs ASGI/unreachable and clarifies session cookie ≠ Settings API token; journey capture waits for the Connected/Unavailable badge
- **rest_mode chatLogic ESM:** export `initializeChatLogic` for `ui.js` (was a broken import); demo chat helpers append via `textContent`
- **CLI stream cleanup:** `CliAdapter.stream_run` terminates the process group on generator `aclose`/cancel (SSE client disconnect); chat/responses streaming views `aclose` blueprint generators in `finally`
- **rest_mode debug/settings XSS:** escape debug pane role/sender/content/metadata and LLM settings field values via `htmlSafe.js`
- **SPA honesty:** Teams/Blueprints pages no longer invent demo rows on API failure — empty + alert with Django deep-links; Launch is a real `/chat?blueprint=…` link (not a simulated timeout)
- **Mobile dock:** Chat tab + `aria-current` for SPA routes; Settings remains on the top-bar icon
- **Chat Unavailable CTA layout:** Sign-in/Reconnect alert uses `shrink-0` so the fixed-height chat column cannot collapse it
- **GitHub marketplace errors:** upstream GitHub failures are **429/502** JSON (`GitHubAPIError`), not empty HTTP 200; library UI surfaces non-OK as an error empty-state; repo “View” links allow only `http:`/`https:` hrefs
- **rest_mode / creator DOM XSS:** escape toast/creator messages; sanitize marked HTML via `htmlSafe.js` allowlist; gate profiles `base_url` href to http(s); slackbot `slackLogic.js` uses `textContent`; static regression tests
- **CLI import on broken XDG cache:** `ensure_swarm_directories_exist` in `swarm.core.paths` is best-effort per root (`_safe_mkdir`) so a broken `~/.cache` symlink no longer crashes `swarm-cli` import
- **CLI MoA test XDG isolation:** `swarm-cli moa` subprocess dogfood tests pin `HOME` / `XDG_*` / `SWARM_USER_DATA_DIR` under a temp tree so host broken-cache layouts cannot break CI
- **LoadingOverlay a11y:** `role="status"` instead of a fake modal without a focus trap
- **Template XSS residual:** `onclick="fn('{{ … }}')"` JS-string breakout → `data-*` handlers (settings dashboard, blueprint cards / my blueprints)

### Security
- **Operator session gates:** require login for teams admin/export and blueprint library browse + mutators (aligned with Settings/Sessions)
- **Session Explorer operator bridge:** with API auth on, logged-in Django users also see sessions owned by configured Bearer token principals (curl/API creates); foreign `user:…` owners stay hidden; REST IDOR unchanged
- **CSRF on login:** `custom_login` POST is no longer `@csrf_exempt`
- **Login open redirect:** post-login `next` accepts only rooted same-origin paths; rejects `//evil`, backslash tricks, absolute/external URLs

### Removed
- **Leftover `@csrf_exempt` on GET-only WebUI views:** `index`, `team_launcher`, `teams_export`, and unrouted `serve_swarm_config` in `web_views.py` (decorator was pointless on GET; token-auth chat/responses APIs unchanged)
- **Dead `swarm.views.github_views`:** unrouted legacy marketplace helpers including `csrf_exempt` POST “install” stubs; live GitHub discovery remains `MarketplaceGitHub*` in `api_views` + `github_topics_service`

## [0.5.4] — 2026-06-19

### Fixed — `django_chat` actually resolves its LLM profile
- Follow-up to 0.5.2: `django_chat` returned "not configured" at runtime even with a valid `llm` profile, because its `__init__` re-assigned `self._config = config if config is not None else None` (and nulled `_llm_profile_name`) *after* the base `__init__` had already loaded the config — clobbering it. Removed those redundant overrides; verified live (real answer over the local backend). Regression tests added.

## [0.5.3] — 2026-06-19

### Fixed — SPA loading buttons show a spinner (DaisyUI 5)
- `Button` used the bare `loading` class, which DaisyUI 5 no longer renders as a spinner — so every mutating action (save/delete/create) across Teams/Blueprints/Agent-Creator showed a disabled button with **no visible feedback**. Now renders an explicit `loading loading-spinner` element (with `aria-busy`/SR text retained). Tests added.


### Removed — test cruft + orphan CLI
- Deleted ~15 low-quality tests (tautological dict/`isinstance` checks, import-only smokes, over-mocked tests that only verify their own mock, and a suite testing an orphan root `swarm_cli.py`). Removed that orphan `swarm_cli.py` (a stale `click` CLI superseded by `swarm.core.swarm_cli:app`). Net: leaner, higher-signal suite (1293 passing).

## [0.5.2] — 2026-06-19

### Fixed — `django_chat` now calls a real LLM
- The `django_chat` blueprint shipped as a stub that only yielded a simulated `"[DjangoChat LLM] Would respond to: …"` box — it never called a model. It now proxies the conversation to the configured `llm` profile (OpenAI-compatible, mirroring `dynamic_team`), degrading to a clear "not configured" message when no profile is set.

### Security — settings dashboard XSS
- `templates/settings_dashboard.html` injected server settings into a `<script>` via `{{ settings_groups|safe }}` — an XSS vector (any value containing `</script>` could break out) that also emitted invalid JS (a raw Python dict). Replaced with Django's `json_script` (auto-escapes `<`/`>`/`&`) read via `JSON.parse`. Sensitive values were already masked server-side. Regression tests added.

### Fixed — index page silently listed zero blueprints
- `web_views.py` called `discover_blueprints(directories=[BLUEPRINT_DIRECTORY])` — a wrong kwarg that raised `TypeError`, swallowed by a `try/except`, so the Django index page showed **no** blueprints and the team-name collision check never fired against existing blueprints. Fixed to the real positional signature.

### Removed — dead view + templates
- Deleted the unrouted, broken `blueprint_webpage` view (and its 4 tests that exercised it directly) plus its only template `simple_blueprint_page.html`, and the never-rendered `chat.html`. (From the critique audit, ROADMAP §4.4.)

### Fixed — MCP server mode module name
- `ENABLE_MCP_SERVER` mode was dead on a clean install: the code imported `django_mcp_server` while the `django-mcp-server` distribution actually installs the module **`mcp_server`**. Corrected the module name in `settings.py`/`urls.py`/`mcp/integration.py`, so the `/mcp/` mount loads cleanly once the package is present (verified: Django check passes, mount present). It's installed manually — `pip install django-mcp-server` — not as an extra, because its transitive `mcp` SDK dep needs pre-releases that would break `uv lock`. Note: the blueprint→tool *bridge* (`register_blueprints_with_mcp`) targets a flat `registry.register_tool` API that `mcp_server` ≥0.5 replaced with an `MCPToolset` paradigm — a no-op until ported (ROADMAP §3.3).

### Changed — orchestration patterns published as `swarm_*` (aliases; `cli_*` kept)
- The multi-agent *pattern* blueprints now have canonical `swarm_*` names — `swarm_ensemble`, `swarm_map`, `swarm_recurse`, `swarm_pipeline`, `swarm_roundtable`, `swarm_planner`, `swarm_orchestrator` — registered via a central alias map (same classes, canonical name advertised in metadata). They're Swarm primitives, not CLI wrappers, so `swarm_` is the honest brand. The `cli_*` names (and `cli_fusion`) keep working as back-compat aliases; `cli_agent` stays `cli_` (it runs one CLI). New `apply_blueprint_aliases()` / `BLUEPRINT_ALIASES` in `swarm.core.blueprint_discovery`.

## [0.5.1] — 2026-06-19

### Added — Docker
- API-only base `docker-compose.yml` (the gateway serving the REST surface; CLIs are host-bound and opt-in) plus a rewritten `docker-compose.override.example.yml` catalog of per-CLI mount blocks.

### Added — `cli_recurse` (recursive divide & conquer)
- New blueprint that breaks a problem down to **any depth**: each node decides to solve directly or split into sub-problems, and every sub-problem is handed to a **freshly-instantiated child of the same blueprint** — recursing until each leaf is atomic, then synthesizing back up. Three limiters keep it finite: `max_depth`, `max_subproblems` (fan-out width), and `max_nodes` (a shared global budget; once spent, remaining nodes solve directly). Config block `cli_recurse` (decomposer/solver/synthesizer + limits), falls back to `cli_fusion`. The recursive generalization of `cli_map`'s single-level decompose.

### Changed — `cli_fusion` → `cli_ensemble` (canonical rename, alias kept)
- The multi-CLI deliberation blueprint is now published as **`cli_ensemble`** (ML-standard "ensemble" / Mixture-of-Agents terminology). **`cli_fusion` still works** as a back-compat model alias with identical behavior, and the shared `cli_fusion` config block / `cli_fusion_support` internals are unchanged (used family-wide). Renamed to avoid colliding with OpenRouter's "Fusion" — which is a *tool a model invokes*, the inverse of ours (the panel *is* the endpoint).

### Added — Community blueprints (discovery foundation)
- Blueprint discovery now scans **external roots** in addition to the bundled set: the user data dir `$XDG_DATA_HOME/swarm/blueprints` (where community packs install) plus any paths in `SWARM_BLUEPRINT_PATHS`. External roots load under a synthetic module namespace so they can't shadow or collide with `swarm.blueprints`; the bundled set always wins on name collisions. New `merge_community_blueprints()` / `discover_all_blueprints()` in `swarm.core.blueprint_discovery`. This is the foundation for installing community blueprint packs from GitHub (explicit opt-in; running third-party blueprint code is a code-execution trust decision).

## [0.5.0] — 2026-06-19

### Removed — Dead code cleanup (pre-release)
- Deleted the non-functional `digitalbutlers` and `flock` blueprint stubs (empty placeholder classes, superseded by `jeeves`) and the orphaned `services/monitor.py` fixture, along with their trivial import/shell tests. No functional blueprint or production path referenced them.

### Added — Persona councils (diverse-lens consensus)
- **`persona_council`** blueprint: examine one question through a council of distinct **expert lenses** (each a system-prompt persona) in parallel, then a judge reconciles agreement, tensions, and a synthesized position. Consensus from *perspective diversity*, not redundant runs. Built-in councils — `ethics` (Utilitarian/Kantian/Virtue/Rawlsian/Care), `science`, `psych`, `decision`, `red_team` — work with zero config; select via `params.council`, pass an explicit `personas` roster, or define your own in a `persona_council` config block. The published persona names stay generic but the lens prompts **channel the actual thinkers** (Mill, Kant, Rawls, Feynman, Munger, Schneier, …) for sharper, more distinct voices. Verified live. The bundled persona blueprints are reframed as *examples* of this composition system.

### Added — Docs (deployment-ready)
- **[docs/EXAMPLES.md](docs/EXAMPLES.md)** — every recipe in two sections: **Team examples** (consensus blueprints + persona councils, curl for each) and **CLI + REST config** (wiring `cli_agents`, `llm` profiles, and the mix). README gains an **Architecture** section with two diagrams (the dispatch flow and the consensus-invocation spectrum) linking out to the examples + [ORCHESTRATION_PATTERNS.md](docs/ORCHESTRATION_PATTERNS.md).

### Added — Async tasking (`/v1/responses` background mode)
- Fire-and-forget for long-running agent work: `POST /v1/responses` with `"background": true` returns **202** immediately with a `resp_<id>` and `status: "queued"`; the blueprint runs in a daemon worker that updates the file-backed store `queued → in_progress → completed/failed` with `execution_ms`/`started_at`. Poll via `GET /v1/responses/{id}`; completed results carry `output_text`/`system_fingerprint`/`usage` and are chainable via `previous_response_id`. Sync behavior unchanged when `background` is absent. Also wired per-request `params` into `/v1/responses`. See **[docs/ASYNC_RESPONSES.md](docs/ASYNC_RESPONSES.md)**.
- **Cancellation:** `POST /v1/responses/{id}/cancel` — cooperative cancel, `status → cancelled` (idempotent on finished tasks).
- **Restart durability:** queued/in-progress tasks persist a spec and **resume** on server startup (at-least-once).
- **No-auth opt-out:** `SWARM_ALLOW_NO_AUTH=true` lets the server boot in production without `API_AUTH_TOKEN` (for when an external OAuth/gateway layer gates access) — warns loudly instead of refusing.
- **Fast-path sync vs queued (auto-escalation):** `max_wait_seconds` (per request) or `SWARM_RESPONSES_SYNC_TIMEOUT` (server default) make `/v1/responses` return the result inline if it beats the deadline, else a queued handle to poll — the task keeps running either way. No deadline = classic blocking sync.

### Added — Orchestration patterns (MAF-class, over CLIs)
- Three new orchestration blueprints complete the field-standard pattern set over heterogeneous agentic CLIs: **`cli_pipeline`** (sequential — each stage refines the prior stage's output, draft → review → polish), **`cli_roundtable`** (group-chat — debaters react to each other in a shared transcript across bounded rounds, a moderator concludes and synthesizes), and **`cli_planner`** (Magentic-One — a planner keeps a task ledger, delegates to workers, and re-plans on stall until the goal is met). All follow the existing `BlueprintBase` + `cli_fusion_support` conventions, degrade gracefully on a dead backend, and are auto-discovered at `/v1/models`. 20 new tests.
- New docs: **[docs/VISION.md](docs/VISION.md)** (front-and-centre vision + honest built-vs-remaining) and **[docs/ORCHESTRATION_PATTERNS.md](docs/ORCHESTRATION_PATTERNS.md)** (GitHub Mermaid sequence diagrams for all seven patterns). Live cross-CLI transcripts (consensus, routing, tool calling) under `docs/proofs/`.

### Added — Skills
- Reusable **skills**: `SKILL.md` directories (Anthropic [Agent Skills](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview) open standard) discoverable via `swarm-cli skills` (`--show`/`--json`) and applied to any CLI with the `cli_agent` `skill=<name>` param. Applying a skill prepends its instructions and stages any bundled assets into the workdir so a write-mode CLI can execute them.
- Bundled skills: `conventional-commit`, `reviewing-code`, `writing-changelog`, and `counting-lines` (ships an executable `count.py`).
- Verified live across gemini + `claude -p` + grok: skill portability (3/3) and bundled-asset tool calling (2/2). See `docs/examples/`.

### Added — Inference profiles (decouple blueprints from models)
- A blueprint can declare *what kind of thinking it wants* — `intelligence`, `speed`, `cost` as 0–1 targets (`inference_profile`) — instead of naming a CLI. Backends carry capability traits, **per-provider** (`cli_catalog.CLI_TRAITS`) and **per-model** (`MODEL_TRAITS`, overridable via a config `models` block); the closest backend is chosen by **distance-from-ideal** over only the axes the blueprint specifies. Opt-in `profile=` param resolving to a `cli` or `cli@model`; precedence: explicit `cli` > `default_cli` > `profile`. Live routing verified (deep-reasoning → claude, fast&cheap → gemini, balanced → opencode). See `docs/examples/inference-profile-routing.md`.

### Added — Tool capabilities endpoint + playwright-mcp
- `GET /v1/blueprints/<id>/tools` resolves a blueprint's `tool_requirements` to concrete MCP providers. Official **microsoft/playwright-mcp** added to the catalog (non-auth `browser`), auto-provisioned for blueprints needing it (jeeves, whiskeytango_foxtrot); verified live (23 browser tools).

### Added — Web UI Builder config panels
- The Builder gained four config panels bound to `GET /v1/config-options/`: **inference profile** (live resolve preview), **per-model trait editor**, **tool capabilities/MCP** (non-auth preferred), and a **skills picker** (with SKILL.md preview). Each snippet has Copy/Download; selected blueprints show a "resolved MCP" badge; accessible header tooltips. 0 axe violations; Playwright e2e. See `docs/examples/webui-config-panels.md`.

### Added — Tool capabilities (decouple blueprints from MCP providers)
- A blueprint can declare an abstract tool capability and whether it's mandatory/optional (`tool_requirements`) instead of naming a server. `swarm.core.tool_capabilities` resolves each capability to a configured MCP provider, **preferring non-auth providers**; unmet optional needs never block. `suggest_mcp_config()` emits a ready-to-paste, keyless `mcpServers` block (duckduckgo/fetch/filesystem/…). See `docs/examples/tool-capabilities.md`.

### Added — Docs
- Illustrated [Skills & Consensus walkthrough](docs/SKILLS_AND_CONSENSUS_WALKTHROUGH.md) with regenerable terminal screenshots; `docs/CLI_FUSION.md` Skills + Inference-profiles sections; README Core Concepts bullets.

## [0.4.11] - 2026-06-17

### Fixed — accessibility best-practice (web UI)
- A deeper axe pass with the **full** ruleset (not just WCAG2 A/AA) surfaced best-practice violations the scoped run missed, now all fixed:
  - `landmark-one-main` / `region`: page content is wrapped in a single `<main>` so every region sits inside a landmark.
  - `page-has-heading-one`: the Dashboard had no `<h1>` — added one.
  - `heading-order`: Blueprints/Teams card titles jumped from `<h1>` to `<h3>`; demoted to `<h2>`.
- Adds reusable `webui/frontend/scripts/a11y-audit.mjs` (full ruleset, 7 routes × light/dark × desktop/mobile). **0 violations across all 28 combinations.**

### Added — CLI permutation proof
- `scripts/prove_cli_permutations.py` exercises every installed CLI through every framework mode (cli_agent, cli_fusion panel, cli_orchestrator, cli_map, self-consensus ×2, native best-of-n). Verified live: **12/12 permutations PASS** across claude + gemini + grok + opencode.

## [0.4.10] - 2026-06-17

### Changed — Builder visual polish
- The source file-browser is shown only when a blueprint has more than one file; single-file blueprints get a full-width editor instead of a lonely 1-item list. Verified: tap targets all >=24px across pages; axe stays at 0 (mobile+desktop, light+dark).

## [0.4.9] - 2026-06-17

### Fixed — responsive / mobile (web UI)
- Builder: the blueprint list (a desktop sidebar) buried the config + editor on mobile; below `lg` it's now a compact blueprint **dropdown**, so the agent/model config and source editor are immediately reachable.
- Mobile a11y: the API Access snippet `<pre>` blocks and the chat message list became scrollable-region-focusable violations at narrow widths — made keyboard-focusable + labeled. **0 axe WCAG2 A/AA violations across mobile (light+dark) and desktop.**

## [0.4.8] - 2026-06-17

### Fixed — accessibility (web UI)
- Pedantic a11y pass (axe-core, WCAG 2 A/AA): **0 violations across all pages in both light and dark mode** (was several "serious"). Fixes: CodeMirror editor/scroller given an accessible name + keyboard focus (read-only, not editable=false); the config `<pre>` made focusable + labeled; the Settings icon-link labeled; `aria-current` on active list items; replaced fixed `text-gray-*`/low-opacity text with theme-adaptive `text-base-content` tokens (fixed dark-mode contrast); fixed a low-contrast stat color and the CodeMirror dark gutter.

## [0.4.7] - 2026-06-17

### Changed — Blueprint Builder polish
- Builder added to the mobile dock nav; agent/model config gains a **Download** button (client-side JSON); CodeMirror editor follows the app **dark/light theme**; dark mode verified across the page.

## [0.4.6] - 2026-06-17

### Added — Blueprint Builder web UI
- New **/builder** page (React + TanStack Query + DaisyUI): lists all blueprints, shows their source in a lazy-loaded **CodeMirror** editor with a file browser, and an **editable agent/model config builder** — pick a CLI + consensus mode (single / self-consensus N / native best-of-N / panel) + N and get a live, copy-pasteable `cli_agents` JSON block.
- Backend endpoints: `GET /v1/blueprints/<id>/source` (read-only source, path-traversal guarded) and `GET /v1/cli-agents/` (CLI catalog + `native_consensus` map). 4 API tests.

## [0.4.5] - 2026-06-17

### Added — more consensus modes
- **Self-consensus:** `consensus: N` (int) runs the **same persona N times** and synthesizes — self-consistency sampling. Verified live (grok ×3 → "operational/distributed complexity… no material disagreement on substance").
- **Call-time consensus flag:** a per-request `params.consensus` (bool/int/list/dict) overrides the agent's config designation; falsy forces a single call.
- **Native (built-in) consensus catalog:** `cli_catalog.NATIVE_CONSENSUS` records CLIs whose *own* flag fans out (grok `--best-of-n N`, verified live), with `has_native_consensus()` / `native_consensus_flags()` / `with_native_consensus()`. `swarm-cli cli-agents --json` now emits a `native_consensus` map so a UI can offer a "use this CLI's built-in consensus" toggle only where available. Framework and native consensus compose (N framework samples × M native candidates).

## [0.4.4] - 2026-06-16

### Added
- **Consensus agents:** designate any agent as a consensus agent via `consensus` in its `cli_agents` config — calling it runs a *panel* instead of a single inference. `true` => all available CLIs; a list => a preferred whitelist that falls back to all-available if it matches nothing; `{panel, judge}` => explicit. The default panel is real CLIs (other consensus *designations* are excluded). Verified live with grok (whitelist `[grok, claude]` and a no-match whitelist that fell back to the full panel — both returned "Tokyo").
- `docs/BLUEPRINT_LIBRARY.md` gains a **Consensus modes** taxonomy (single / agent-designated / self-consensus / call-time flag / orchestrated multi-persona) — a roadmap of permutations on the shared `run_consensus` engine.

## [0.4.3] - 2026-06-16

### Added — Blueprint library (permutation matrix)
- **`chatbot`** — minimal single-agent REST blueprint (the simplest template).
- **`hybrid_team`** / **`hybrid_swarm`** — the Mixed column: a REST coordinator/orchestrator that reaches for **grok CLI personas** and a **consensus panel** mid-run (`swarm.core.cli_tools`). REST half wired to a real openai-agents Agent that degrades gracefully without an LLM key; CLI half verified live with grok ("Rome", unanimous consensus).
- `docs/BLUEPRINT_LIBRARY.md` — a feature-tagged menu organized as an agents × backend matrix (1→many × REST/CLI/mixed); every cell now has a working, tested demonstrator.

### Changed
- **Laconic CLI:** `swarm-cli cli-agents` gains short flags (`-c/-a/-S/-s/-j/-i/-w`) and an `agents` alias, so `swarm-cli agents -iw` == `cli-agents --init --write`.

## [0.4.2] - 2026-06-16

### Added
- **grok** (xAI's CLI, also installed as `agent`) added to the catalog: `grok -p {prompt} --output-format json --always-approve` → `json:.text`. Verified live.
- `grok` is now the **preferred** single-agent CLI: `--init` (and the example config) make it the `cli_agent` default and the orchestrator router / map planner+reducer / fusion judge, while panels still include every installed CLI — so the other agents are only engaged for the multi-agent paths.

## [0.4.1] - 2026-06-16

### Added
- **One-command setup:** `swarm-cli cli-agents --init [--write]` autodiscovers the CLIs installed on the host and emits a complete, ready-to-run `swarm_config.json` wiring every mode (`cli_fusion` / `cli_orchestrator` / `cli_map`) over them, with per-CLI gotchas baked in. `--write` saves it (backing up any existing file).
- Example config now includes `cli_orchestrator` and `cli_map` blocks; docs gain a 60-second quick start.

### Fixed
- Removed a dead `[tool.hatch.version]` block in `pyproject.toml` (ignored, since the version is static).

## [0.4.0] - 2026-06-16

### Added — CLI Agent Fusion

Turn the agentic CLIs you already have installed (`claude`, `gemini`, `codex`,
`opencode`, …) into one-shot, OpenAI-API-addressable subagents — single
(`cli_agent`) or a parallel panel a judge synthesizes (`cli_fusion`). See
[docs/CLI_FUSION.md](docs/CLI_FUSION.md).

- `CliAdapter` one-shot layer + `cli_agent`/`cli_fusion` blueprints (panel → judge → synthesize, bounded master plan) (#116, #117)
- Autodiscovery: `swarm-cli cli-agents` reports install status; `--check-auth` probes each CLI's `auth_check`
- Full-capability (auto-approve) example adapters, replacing the read-only defaults
- Per-panelist workdir isolation (`cli_fusion.isolate_workdir` / per-request `isolate`): each write-capable panelist gets a throwaway `git worktree` (or temp dir) so parallel fan-out can't corrupt the source tree
- Built-in adapter catalog + `swarm-cli cli-agents --suggest`: paste-ready config for supported CLIs installed but not yet configured
- Catalog defaults encode known per-CLI gotchas so they run non-interactively out of the box: `gemini --skip-trust` (untrusted-dir gate), `opencode --model` (no usable built-in default) — verified live
- Non-interactive smoke probe + `swarm-cli cli-agents --smoke`: catches a misconfigured `cmd` that hangs instead of returning (ok/hang/error/not_installed)
- Machine-readable `swarm-cli cli-agents --json` (agents/smoke/suggestions) for CI and scripting
- `cli_agent` streams CLI stdout incrementally for `parse: "text"` adapters when `stream: true` (json-parse adapters fall back to one-shot)
- Failover & graceful degradation: `cli_agent` fails over down a candidate chain (`params.fallback`, or auto to other installed adapters; `failover: false` for strict) when a CLI is missing/broken/hung; `cli_fusion` drops failed panelists and reaches consensus from the survivors
- Reusable consensus service (`swarm.core.consensus.run_consensus`) extracted from the `cli_fusion` blueprint; consensus-first synthesis (no-judge fallback now picks the **most-corroborated** panel answer, not the longest)
- New `cli_orchestrator` blueprint — granular consensus: a cheap router CLI answers directly and escalates only high-stakes questions to a consensus panel (fusion as an on-demand tool, not a whole-request mode)
- Cleanup: removed dead `progress_text()` and `CliResult.as_dict()`
- Agent-tool layer (`swarm.core.cli_tools`): `cli_persona(adapter)` and `consensus_fn(panel, judge)` callables, `as_function_tool()` to hand either to an openai-agents `Agent` — so a real agent can call `consensus()` granularly mid-reasoning
- New `cli_map` blueprint — decompose → distribute → reduce: a planner CLI splits one task into subtasks, workers run them in parallel (round-robin), a reducer combines (complements `cli_fusion`'s consensus)
- Web UI **API Access** panel (Settings) — surfaces the live base URL, token, model list, and copy-paste snippets (curl / OpenAI SDK / Open WebUI) to plug any OpenAI client into the server
- End-to-end API coverage: real panel→synthesize and `params`-driven selection over `/v1/chat/completions`

## [0.3.3] - 2026-06-12

### Added
- Websocket chat honors blueprint selection (per-message field or ?blueprint= param); Teams page Launch buttons into preselected chat (#103)
- /v1/library/ API + SPA Add-to-Library / My Library filter (#104)
- Guided tour and all 26 screenshots refreshed to current UI

## [0.3.2] - 2026-06-11

### Fixed
- SPA shipped unstyled (Tailwind v4/v3 config mismatch emitted ~2kB CSS); DaisyUI 5 `card-bordered` removal made card borders invisible app-wide
- Django navbar dropdowns rendered as empty white boxes; duplicate element id
- Non-streaming `/v1/chat/completions` returned spinner text in test mode; all 14 blueprints now answer on both API surfaces (smoke matrix added)
- Mobile: SPA bottom nav never rendered (DaisyUI 4 class); viewport overflows fixed

### Added
- Guided tour + screenshot registry + README demo GIF; CI visual-regression workflow (golden journey, computed-style guards)
- SPA: agent-creator and settings pages, token auth UX, websocket ChatPage; theme-token dark mode toggle
- Mobile captures (13 pages); capture harness authenticates and migrates fresh DBs

### Changed
- Branding: project name is "Open Swarm" (dropped stale "MCP" suffix)

## [0.3.1] - 2026-06-11

### Added
- SPA: agent-creator and settings pages on live APIs (#80); websocket ChatPage + token auth UX
- ASGI routing — websocket chat now functional (channels/daphne wired)
- JSON Teams API (/v1/teams/); NOTICE file; opt-in mem0 e2e harness (#85)
- uv.lock tracked; CI lock-check now meaningful (#81)

### Changed
- vite 5 -> 8; npm audit clean (#84)
- Absorbed 18 community/agent branches (perf, security shlex hardening, UX, tests) (#83)

### Removed
- Wagtail marketplace and SAML IdP scaffolding (-716 lines; GitHub-topics discovery retained) (#82)

### Security / hygiene
- Hardened .dockerignore: image no longer ships .git history, dev database (auth_user hashes), .letta/.claude local state, pycache with local absolute paths, or test artifacts

## [0.3.0] - 2026-06-11

### Repository cleanup wave (June 2026)

- **Added** `ROADMAP.md` — nested-checkbox roadmap consolidating project status; `TODO.md` slimmed to point at it.
- **Removed** tracked `node_modules` from the repository (now untracked/ignored).
- **Removed** dead code identified during the sweep; deleted the automated `CODE_SWEEP_REPORT.md`; archived `IMPLEMENTATION_SUMMARY.md` to `docs/archive/`.
- **Security** hardened defaults: command/SQL injection fixes, open redirect fixes, removal of hardcoded passwords.
- **Fixed** packaging issues (`uv sync`, frontend lockfile regeneration).
- **Docs** README attribution section (OpenAI Swarm derivative, built on openai-agents SDK) and explicit prerequisites (Python >= 3.10, Node >= 22 for optional frontend); React web UI marked experimental with the Django UI as the supported interface.

### Added
- **Dual workflow taxonomy** (`docs/SWARM_WORKFLOWS.md`): **A** MoA consensus (read-only subagents + orchestrator) vs **B** openai-agents persona swarm (read/write specialists).
- **Mixture of Agents (MoA)** (`swarm.core.moa`): read-only multi-CLI consensus participants; orchestrator-only determination and optional act/writes. Injectable fake backend for CI; production `AcpxParticipantBackend` defaults to `--approve-reads` + `exec` (never `--approve-all`). See `docs/MOA.md`.
- Blueprint `moa` with legacy aliases `cli_fusion` / `cli_ensemble` / `mixture_of_agents` (discoverable model ids).
- **`swarm-cli moa`** dogfood command: `--backend fake|acpx|grok`, orchestrator `--act` / `--act-write`; `GrokParticipantBackend` for local grok CLI as a read-only panelist.
- **HTTP**: `/v1/chat/completions` model `moa` with `system_fingerprint` (`moa:p1+p2`); chat_views `backend_fingerprint`.
- **Resilience**: participant failover chain, per-participant timeout budget, vote weights on determination.
- **Model B**: `persona_swarm.run_persona_swarm_with_runner` (live Runner when available, scripted R/W fallback).
- TDD: `tests/core/test_moa*.py`, `tests/cli/test_moa_command.py`, `tests/api/test_moa_api.py`, `tests/api/test_moa_http_e2e.py`, `tests/core/test_persona_swarm_runner.py`, `tests/integration/test_swarm_workflows_proof.py`.
- Fixed Django 4 SPA `re_path` import; chat non-streaming generator `aclose`; discovery skip of same-class alias re-exports.
- **Grok first-class MoA participant** (`GrokParticipantBackend` in `backends.py`); multi-seat labels; CLI defaults no longer Codex-centric (`analyst,critic` / fake); docs state Codex not required.
- **Hybrid A←B:** `run_hybrid_scripted` + coordinator `consult_moa_panel` tool (read-only MoA then implementer write).
- **`swarm-cli moa-init`**, `docs/examples/moa.swarm_config.json`, Open WebUI preset (`docs/OPENWEBUI_MOA.md`), blueprint **`hybrid_moa`**, multi-seat demo script.
- Comprehensive unit tests for low-coverage modules: `audit.py`, `progress.py`, `output_formatters.py`, and `ansi_box.py`
- Test coverage for `ChucksAngelsBlueprint` class
- Test coverage for `DiffFormatter` and `StatusFormatter` classes
- Test coverage for `ProgressRenderer` class
- Test coverage for `ansi_box` function with various parameters and edge cases

### Changed
- Improved test coverage from ~26% to ~30% for core modules
- Enhanced code quality with comprehensive test cases for utility functions
- Fixed test failures in `test_audit_logger_log_with_args` and `test_chucks_angels_blueprint_init`

### Fixed
- Syntax error in test file (async for outside async function)
- Incorrect assertion in audit logger test (format args mismatch)
- Incorrect assertion in ChucksAngelsBlueprint test (description content)

### Performance
- Identified performance bottleneck in blueprint creation (test currently disabled due to 5.4s > 2.0s limit)
- Added comprehensive performance test suite for future optimization work

## [0.1.0] - 2024-01-01

### Added
- Initial project structure
- Core blueprint architecture
- CLI interface
- Basic test suite

## Style Compliance

### Linting Issues Identified
- **C0301 (line-too-long)**: 126 occurrences - Lines exceeding 100 character limit
- **C0114 (missing-module-docstring)**: Multiple modules missing docstrings
- **C0115 (missing-class-docstring)**: Multiple classes missing docstrings
- **C0116 (missing-function-docstring)**: Multiple functions missing docstrings
- **W0611 (unused-import)**: Several unused imports detected

### Top Violations by Line Number
- Line 1: 126 occurrences (missing module docstrings)
- Line 24: 12 occurrences
- Line 8: 11 occurrences
- Line 7: 11 occurrences
- Line 60: 11 occurrences

### Recommendations
- Add module-level docstrings to all Python files
- Add class and function docstrings following Google or NumPy style
- Break long lines (>100 characters) into multiple lines
- Remove unused imports
- Consider increasing line length limit or reformatting long lines
