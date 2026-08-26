# DOCS-HONESTY - documentation honesty audit and architecture deep dive

Date: 2026-08-26. Audited at main commit `eca6a0de`.
Review branch only. Do not merge. Nothing in this document is a code change.

## Scope and method

Everything scored below was verified empirically on a clean review VM, not
inferred from reading docs. What was actually run:

- Full test suite (`uv run pytest -q --timeout=120`), plus isolation reruns.
- PR #295's own unit tests, in a worktree of its branch.
- Functional fail-fast probes: ASGI import, `manage.py runserver`, and a live
  uvicorn server, each against an unreachable `DATABASE_URL`, on main and on
  the PR #295 branch.
- Live HTTP probes of `open-swarm.fly.dev` (IPv4 and IPv6, with control
  requests to other Fly-hosted apps to rule out local network artifacts).
- Every documented `swarm-cli` subcommand.

Limits of this environment: no Docker daemon on the review VM (the compose
path was analyzed from source, not executed) and no Fly/Neon credentials
(intentionally - live facts below are taken as given).

**Live facts taken as given, not re-tested:** the host systemd unit
`open-swarm-oracle.service` (teamstinky) was stopped and disabled because a
Neon Postgres compute quota was exhausted; draft PR
[#295](https://github.com/matthewhand/open-swarm/pull/295) is the fail-fast /
local-DB response; Neon must not be resumed. No secrets were accessed or are
reproduced here.

---

## TL;DR - what is partially done, and the smallest step to complete it

**Partially done:** the Neon crash-loop remediation. The bleeding is stopped
(unit stopped and disabled), and PR #295 contains a working fail-fast
(verified: exit 78 in about 10 seconds with an actionable message). But the
PR as written does not actually end the crash-loop class of incident:

1. It never touches `deploy/oracle/open-swarm-oracle.service`, which still has
   `Restart=always` / `RestartSec=3`. Under `Restart=always`, systemd restarts
   on **any** exit code - exit 78 included. The PR's claim that exit 78
   "signals a configuration error to systemd" and stops the restart churn is
   incorrect as configured. The loop would continue, just at a ~13s cadence
   (10s connect timeout + 3s RestartSec) instead of instantly.
2. Its health check is not wired into the one boot path that provably crashes
   on a dead DB in this repo: the container CMD runs `manage.py migrate`
   before uvicorn (`Dockerfile` lines 63-77), and `migrate` is deliberately
   excluded from the PR's `manage.py` gate. Docker and Fly boots remain
   unprotected.
3. 4 of its 9 new unit tests fail (details in the PR review section). The
   tests were never run against the shipped code.

**Smallest completing step:** one line in
`deploy/oracle/open-swarm-oracle.service`:

```ini
RestartPreventExitStatus=78
```

(optionally plus `StartLimitIntervalSec=60` / `StartLimitBurst=5` as a
backstop for other boot failures), and the matching correction in the PR's
runbook. That single line is what makes exit 78 mean what the PR already
claims it means. Everything else in PR #295 is polish on top of that.

---

## Works-as-documented scorecard

Verdicts: **yes** = claim verified true, **partial** = true with material
caveats or stale in places, **no** = claim contradicted by observed reality,
**unverified** = could not be tested from this environment.

| Documented surface | Claim location | Verdict | Evidence |
|---|---|---|---|
| `swarm-cli` command set "available today" | README | **yes** | All 12 documented subcommands (`list`, `launch`, `install`, `uninstall`, `add`, `delete`, `config`, `cli-agents`, `skills`, `wizard`, `moa`, `moa-init`) respond to `--help` with exit 0; `list` works |
| Test suite "1100+ tests, no API keys needed" | README (2 places) | **yes** (understated) | Measured: **2143 passed, 1 failed, 8 skipped** in 3m59s, keyless. The one failure (`tests/blueprints/test_stewie.py::test_unknown_llm_profile_warns_then_falls_back`) is order-dependent: passes in isolation |
| OpenAI-compatible API works locally | README quickstart | **yes** | uvicorn on main serves `/health` 200 and `/v1/models` 200 (39 blueprints discovered) in a live smoke run |
| "verified in Docker" | README status line | **unverified** | No Docker on review VM. Partial corroboration: the Docker Hub image build succeeded in CI on 2026-08-24 |
| Fly deployment "Verified live ... 200" | `fly.toml` comment, CHANGELOG | **no** | `open-swarm.fly.dev` is dead as of 2026-08-26: TCP+TLS complete at Fly's edge, then zero response bytes until timeout, on both IPv4 and IPv6. Control apps on fly.dev respond normally from the same VM. Last deploy workflow run succeeded 2026-08-24 |
| Oracle systemd runbook produces a durable service | `docs/ORACLE_DEPLOY.md` | **partial** | Unit template as shipped (SQLite, uvicorn) is safe: verified that ASGI boots in 0.6s and stays up even with a dead `DATABASE_URL`. But the runbook's `Restart=always`/`RestartSec=3` + any boot-time crasher = restart storm, which is exactly what happened on the real host (with a host-side `DATABASE_URL` overlay the repo never documents) |
| FEATURE_STATUS.md is a "live status board" | FEATURE_STATUS.md header | **partial** | Test count badly stale (says "673 passed / 2 skipped"; reality 2143 passed). Its evidence commits `4c7e1b28` and `f1fa20b1` do not exist in this repo's history (full clone, not shallow) - the anchors are dangling |
| ROADMAP is "the single source of truth for project status" | ROADMAP.md | **partial** | Understates in places: "only `list`/`wizard`/`install` work cleanly" is stale (all 12 commands work). Header says last updated 2026-06-19 |
| `.env.example` documents database config | `.env.example` | **no** | Documents `DJANGO_DATABASE` and `POSTGRES_*` variables that `settings.py` never reads. The variable that actually switches backends - `DATABASE_URL` - appears nowhere in `.env.example`, README, CONFIGURATION.md, DEVELOPMENT.md, or docs/DEPLOYMENT.md |
| "CI enforces blueprint metadata and UX standards" | README Contributing | **no** | `check_ux_compliance.py` / `lint_blueprints.py` run via pre-commit and manually only; no GitHub Actions workflow invokes them |
| MCP server mode / memory backends honestly flagged unfinished | README roadmap section | **yes** | Flags match code (langmem/papr are placeholder files with commented-out imports) |
| PR #295 as described in its own body | PR #295 | **partial** | Fail-fast works (verified). Testing claims false (4/9 tests fail). systemd claim wrong (see TL;DR). Root-cause analysis attributes the crash to the wrong layer (see below) |

---

## Overstated claims, quoted

Each quote is followed by the measured reality.

**1. `fly.toml` (comment above the health check):**

> "Liveness via AllowAny /health (urls.py HealthCheckView). Verified live on
> open-swarm.fly.dev (200 {"status":"ok"}); re-enabled after the 2026-06-20
> disable that avoided fly-proxy blackholing /v1 while the image lacked /health."

Reality: as of 2026-08-26 the endpoint returns nothing. The TLS handshake
completes at Fly's edge (so the app and cert still exist), then the request
hangs with zero bytes until client timeout - the signature of fly-proxy having
no healthy machine to route to. "Verified live" was a snapshot, not a
continuously-enforced property, and it is false today. CHANGELOG carries the
same claim ("live `open-swarm.fly.dev/health` returns 200").

**2. `docker-compose.yml` (header comment):**

> "Native (systemd-on-host) deployment avoids all of this - the CLIs are
> already installed and authed. See docs/ORACLE_DEPLOY.md."

Reality: the recommended native deployment is currently stopped and disabled
after crash-looping approximately 37,500 times. "Avoids all of this" trades
the CLI-mapping pain for an undocumented database coupling hazard that took
the deployment down. The recommendation is not wrong, but stated without its
operative risk.

**3. README status line:**

> "Core framework, CLI, OpenAI-compatible REST API, websocket chat, and both
> web UIs are working, covered by an 1100+ test suite and verified in Docker."

Reality: mostly true, and the test count is understated (2143 passed), which
is its own honesty defect - the number was written down once and never
re-measured. One order-dependent failure means a fresh clone does not get a
green run. "Verified in Docker" is unverifiable from the repo and not
re-verified here.

**4. `FEATURE_STATUS.md` ("Test suite health" row):**

> "673 passed / 2 skipped as of `4c7e1b28`."

Reality: 2143 passed / 1 failed / 8 skipped on current main, and commit
`4c7e1b28` does not exist in the repository history. A status board whose
evidence pointers dangle cannot serve its stated purpose.

**5. `.env.example` (database section):**

> `DJANGO_DATABASE="sqlite"` ... `# POSTGRES_DB="swarm"` (etc.)

Reality: `settings.py` reads none of these. It reads `DATABASE_URL` (Postgres
via dj-database-url) or `DJANGO_DB_NAME`/`SQLITE_DB_PATH` (SQLite, defaulting
to ephemeral `/tmp/db.sqlite3`). The production incident ran through a
variable the docs never mention.

**6. README (Contributing):**

> "CI enforces blueprint metadata and UX standards."

Reality: no GitHub Actions workflow runs the compliance scripts. PR gates are
pytest (3 Python versions), a frontend build, and the visual-regression job.

**7. PR #295 body and runbook:**

> "Failing fast with exit code 78 (EX_CONFIG) to signal a configuration error
> to systemd" / "Prevents systemd restart churn"

Reality: false under the unit's `Restart=always`, which the PR does not
change. Also from the runbook's root-cause analysis:

> "Django ASGI/WSGI application initialization attempted to connect to the
> database ... Process exited with code 1"

Reality: measured false. On main, `import swarm.asgi` (which calls
`get_asgi_application()`) completes in 0.6s with a dead `DATABASE_URL`, and
the served app returns 200 on `/health` and `/v1/models`. Django's DB access
is lazy. The boot-time crashers are elsewhere: `manage.py runserver`'s
startup migration check (verified: exit 1 on unreachable DB) and the
container CMD's `migrate` step. The runbook's remediation steps are still
correct; its mechanism is not.

---

## Architecture as it is

Condensed to what matters for direction. File/line specifics are from a full
source walk on `eca6a0de`.

### Core runtime

One Django/DRF app serving an OpenAI-compatible surface. `POST
/v1/chat/completions` flows: twin routes in `urls.py` -> `ChatCompletionsView`
(csrf-exempt, bearer-or-session auth; auth enabled iff any token env is set)
-> serializer -> `model` name looked up in a filesystem blueprint-discovery
cache (directory names + aliases; `validate_model_access` is an existence
check, not an ACL) -> fresh `BlueprintBase` subclass instance -> `run()`
async generator, streamed as SSE or aggregated. 39 blueprints discover on
main (32 directories, plus aliases like `swarm_*` -> `cli_*`; `cli_fusion` is
a thin re-export of the MoA blueprint - product name and implementation have
drifted apart).

### State model (the load-bearing fact for the Neon question)

The Django ORM holds: chat/websocket transcripts, GitHub-marketplace catalog
tables, Django auth/sessions/admin. That is all. The async `/v1/responses`
store - the thing the Oracle deployment exists to serve - is **filesystem**
(one JSON file per response id under `SWARM_RESPONSES_DIR`, atomic writes,
file-flag cancellation, boot-time resume in a daemon thread). Dynamic teams
live in `teams.json`. Blueprint discovery is filesystem.

**Consequence: nothing in this system needs Postgres.** The DB is a
transcript-and-catalog store that SQLite on a durable volume serves fine at
this scale (single VM, single uvicorn worker enforced by
`SWARM_ENFORCE_SINGLE_WORKER`). The Neon dependency was pure operational
liability: an external quota-metered service wired into the boot path of a
system whose actual durable state lives in local files.

### Database coupling by deployment path (all verified empirically)

| Boot path | Touches DB at boot? | Dead `DATABASE_URL` on main | With PR #295 as written |
|---|---|---|---|
| Container CMD (Docker and Fly): `migrate` then uvicorn | **Yes** - migrate connects | migrate fails -> process exits -> restart loop (compose `restart: unless-stopped`; Fly machine never becomes ready) | **Unchanged** - the health check is not wired in front of `migrate` |
| Oracle unit as shipped: uvicorn `swarm.asgi` directly, no migrate | **No** - verified: boots 0.6s, `/health` 200, `/v1/models` 200 | Stays up; DB-backed routes (sessions, websocket chat, marketplace) fail per-request | Exits 78 in ~10s -> `Restart=always` restarts anyway -> ~13s-cadence loop |
| `manage.py runserver` | **Yes** - startup migration check connects (verified: exit 1) | Crash-loop under `Restart=always`/`RestartSec=3` - matches the ~37,500 restarts on the real host | Gated: exits 78 pre-Django with a clear message; still loops without the unit change |

Two direction-relevant observations fall out of this table:

- **The three deployment paths have three different failure behaviors** for
  the same misconfiguration. That is the deeper problem behind the incident;
  the docs describe three runbooks but not this asymmetry.
- **PR #295's ASGI-time check converts graceful degradation into refusal to
  boot.** On main, a uvicorn deployment with a dead DB keeps serving
  everything that does not need the ORM (including `/health` and, for
  bearer-token clients, much of `/v1/*`). With the PR, the whole API goes
  down. Combined with the unchanged `Restart=always`, the PR arguably makes
  the uvicorn path *worse* until the unit file is fixed. Fail-fast is a
  defensible choice - silent partial service hides misconfiguration - but it
  is a trade-off the PR does not acknowledge, and it should ship together
  with the systemd policy that gives exit 78 meaning.

### The Fly outage, honestly bounded

What is known: the endpoint stopped responding sometime after the successful
2026-08-24 deploy; the edge accepts connections but no machine answers. What
the repo alone cannot determine: whether the Fly app has a `DATABASE_URL`
secret set. If it does, the container's migrate-before-listen chain would
crash-loop the machine on Neon quota exhaustion - the same incident in a
second costume, and fully consistent with the observed signature. If it does
not, the cause is Fly-side (stopped/suspended machines, volume, billing).
`fly status` / `fly secrets list` (names only) answers this in one command.
Note also `fly.toml` sets `min_machines_running = 1` (an always-on machine)
and a `release_command_timeout` comment implying migrations run as a release
command, but no `release_command` is defined - migrations run in the CMD,
inside request-serving boot, which is the fragile place.

### Test infrastructure

The keyless suite is real: `SWARM_TEST_MODE` swaps deterministic canned
outputs for LLM calls, with a production guard that refuses the flag when
`DJANGO_DEBUG` is off (verified - the guard fired during this audit's own
probing, which is good evidence it works). 2143 tests in ~4 minutes with
coverage measured at 70% by the suite's own run. One order-dependent failure
(`test_stewie.py`) indicates residual test pollution, a known historical
problem here (FEATURE_STATUS records a previous 59-failure ordering bug).

---

## PR #295 review (draft: "Fix: Prevent crash-looping when Neon Postgres quota exceeded")

Branch `cursor/fix-neon-quota-crash-loop-d671`, one commit, based on current
main tip, +615/-3 across 7 files. Not merged; should not be merged as-is.

**What holds up (verified):**

- The core mechanism works. With an unreachable `DATABASE_URL`, importing
  `swarm.asgi` on the PR branch exits 78 in ~10.5s printing correct,
  actionable remediation. With no `DATABASE_URL` it is a no-op (SQLite path
  untouched). `SKIP_DB_HEALTH_CHECK` escape hatch works.
- `docker-compose.postgres.yml` is a reasonable local-Postgres alternative
  (dev-grade password, correctly labeled as such; healthcheck-gated
  `depends_on`).
- The runbook's remediation *steps* (stop/disable unit, switch to SQLite or
  local Postgres, do not resume Neon) are correct and match what was done.

**What does not hold up:**

1. **Tests fail: 4 of 9.** `TestDatabaseHealthCheck` patches
   `swarm.utils.db_health.psycopg2` as a module attribute, but the
   implementation imports psycopg2 *inside* the function, so the patch target
   does not exist (`AttributeError: module ... does not have the attribute
   'psycopg2'`). The tests were written against a different implementation
   shape and never run against the shipped code. The PR body's "Run the new
   unit tests" instruction fails for anyone who follows it. TDD status of
   this PR: claimed, not practiced.
2. **The systemd claim is wrong** (see TL;DR): exit 78 does not stop
   `Restart=always`. The unit file is the missing half of the fix and the PR
   does not touch it. The runbook even cites `man systemd.service` without
   drawing the conclusion.
3. **Wrong-layer root-cause analysis**: ASGI init does not connect to the DB
   (measured). The check added to `asgi.py` guards a path that was not
   crashing; the `migrate` step that does crash the container boot is
   explicitly excluded from the `manage.py` gate.
4. **DSN handling divergence**: the check re-parses `DATABASE_URL` by hand
   and drops query parameters (`sslmode`, `options`, etc.) that
   `dj_database_url` preserves for Django's real connection. Neon URLs
   commonly carry `sslmode=require`. The probe can therefore disagree with
   the connection Django would actually make. Passing the DSN string directly
   to `psycopg2.connect(database_url, connect_timeout=10)` removes the
   divergence and ~40 lines of code.
5. Minor: the quota-vs-generic error classification only changes the printed
   message (both paths exit 78), so its broad substring matching ("exceeded",
   "suspended") is cosmetic rather than harmful; the psycopg2 ImportError
   fallback is dead code since psycopg2-binary is a hard dependency.

**Verdict: right instinct, half-landed.** Keep the intent, fix the four
items above, and ship it together with the one-line unit change that makes
the whole design coherent.

---

## Three next moves

**1. Finish the crash-loop fix properly (smallest real step first).**
Add `RestartPreventExitStatus=78` (plus start-limit backstop) to
`deploy/oracle/open-swarm-oracle.service` and correct the runbook's RCA and
systemd claims. Then repair PR #295: fix the 4 failing tests, pass the DSN
straight to psycopg2, and either wire the health check in front of the
container's `migrate` step (a guard line in the Dockerfile CMD or a
`release_command` on Fly) or explicitly document that the container path is
out of scope. Land it. Do not resume Neon - the state model does not justify
any external Postgres.

**2. Close the database documentation hole and settle the Fly question.**
Document `DATABASE_URL` (and the deliberate SQLite default) in `.env.example`
and CONFIGURATION.md; delete the dead `DJANGO_DATABASE`/`POSTGRES_*` knobs;
consider making the SQLite fallback default somewhere durable instead of
`/tmp/db.sqlite3`. Then spend two minutes with `fly status` and `fly secrets
list` (names only): if a `DATABASE_URL` secret exists there, remove it (same
incident, second deployment); if Fly is not worth an always-on 256mb machine
(`min_machines_running = 1`) given the cost-cutting posture that shut Neon
down, decommission it and delete `fly.toml` + the deploy job rather than
leaving a dead "verified live" endpoint in CI.

**3. Make status claims either measured or dated.**
Fix the specific stale numbers found here (README test count, FEATURE_STATUS
row and its dangling commit hashes, ROADMAP's stale CLI-cruft note, the
fly.toml/CHANGELOG "verified live" comments, the README CI-enforcement
claim). Cheap structural guard: a tiny CI step that greps README's claimed
test count against the actual collected count, and a rule that any "verified
live" claim in a config comment carries a date. This repo's docs fail in an
unusual way - they understate as often as they overstate - which means the
defect is *currency*, not spin; date-stamping fixes currency.

---

## Direction briefing

**The honest headline: this project is in better shape than its
documentation.** The test suite is nearly twice the size the README claims,
runs keyless in four minutes, and has real production guards (secret-key
refusal, test-mode refusal in prod, single-worker enforcement) that fired
correctly during this audit's own probing. The failure pattern is not
vaporware claims - it is *unrefreshed snapshots*: numbers and "verified live"
notes written down once, true at the time, and never re-measured. That is
fixable with process (dated claims, one CI grep), not rewrites.

**The incident's real lesson is about the state model, not about Neon.**
Everything durable that matters here is filesystem or SQLite; the ORM stores
transcripts and catalog rows. An external quota-metered Postgres was wired
into the boot path of three deployment shapes, each of which failed
differently - crash-loop (runserver), boot-death (container migrate), silent
degradation (uvicorn). No document described any of the three because the
variable itself was undocumented. The decision to fall back to local DB is
correct, and PR #295 points the right direction, but it currently hardens
the one layer that was already safe and skips the two that were not. Land it
completed (unit line + tests + migrate-path decision), not as-is.

**Strategic simplification worth considering:** three deployment stories
(compose, Fly, Oracle-systemd) is a lot of surface for a project whose
flagship value - wrapping host-authenticated agentic CLIs - only actually
works on the systemd-on-host path, as `docker-compose.yml`'s own header
admits at length. The Fly app serves the REST-only slice, is down right now,
costs an always-on machine, and its "verified live" claim is the single most
falsified line in the repo. Either give Fly a real job (status page, demo
endpoint, with a dated uptime claim) or retire it. One honest deployment
story beats three partially-true ones - which is the same principle this
audit applies to documentation, applied to infrastructure.
