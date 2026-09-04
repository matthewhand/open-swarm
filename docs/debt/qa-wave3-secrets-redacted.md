# REQ-96 — Look-only secrets / credentials / env-detail scan (redacted)

**Audit only. No scrub, rotate, or history rewrite in this PR.**

> **REQ-96:** hunt for credentials, tokens, private keys, connection strings,
> and identifying / dev-environment details that should not live in a
> publishable tree. Decide **scrub-in-place** vs **repo tainted**. Never write
> real secrets into the Issue, PR, or this file.

Audited at `dfd72eefd616d2038a2f8376d87d177ee968a2df` (branch point: `main`).
This file is the inventory. Values are **REDACTED**: at most 2–4 prefix/suffix
characters, or the word `REDACTED`. No `.env` bodies, private keys, live
connection strings, or full tokens appear here.

**Owner follow-up (outside this PR):** Matthew decides rotate / BFG / nuke.

---

## How to read this

| Severity | Meaning here |
|----------|----------------|
| **critical** | Live credential or private key in the tracked tree |
| **high** | Likely-valid secret or passworded connection string |
| **medium** | Identifying home-LAN / SSH / home-path detail beyond hostname+role |
| **low** | Placeholder, test fixture, public package metadata, or debug fallback |

| `in_git_history?` | Meaning |
|-------------------|---------|
| **likely current-tree-only** | Present at HEAD; history grep did not show a deleted extra leak |
| **history checked** | `git log -S` / light `-p` classify ran; same class of string, or test-only |
| **unknown** | Not grepped |

**Action vocabulary** (proposed only — not done here):

| Action | Meaning |
|--------|---------|
| **scrub file** | Replace identifying defaults/docs in a later PR |
| **rotate credential** | Invalidate the leaked secret (Matthew) |
| **gitignore + remove** | Stop tracking a secrets file |
| **BFG or history rewrite** | Erase from git history (Matthew) |
| **leave-as-placeholder** | Keep; not a live secret |

---

## Method (what was scanned)

Tracked tree (`git ls-files`) under repo root, `docs/`, `src/`, `webui/`,
`scripts/`, `deploy/`, `.github/`, `*.md`, `*.yml`/`*.yaml`/`*.json`/`*.env*`,
`docker-compose*`, example configs, tests/fixtures, Pinokio/JS entrypoints.

Pattern classes: `.env` (non-example), `*.pem` / `id_rsa` / private-key PEM
headers, `sk-` / `ghp_` / `gho_` / `xoxb-` / `AKIA` / `github_pat_`,
passworded `postgres://` / `mysql://` / `mongodb://` / `redis://`, Neon hosts
with userinfo, webhook `whsec_`, SSH material, RFC1918 inventories beyond
hostname/role, personal home-path dumps.

History (light, values not copied): `git log --all -S '<needle>' --max-count=20`
plus a classify pass on `-p` that records path/commit/category only, for
`sk-`, `ghp_`, `BEGIN PRIVATE KEY`, `.env`, `AKIA`, `xoxb-`, `postgres://`,
`sk-proj-`, `github_pat_`, `gho_`, `-----BEGIN RSA PRIVATE KEY-----`,
`-----BEGIN OPENSSH PRIVATE KEY-----`. Also `git rev-list --all -- .env`
and add/delete name lists for `*.pem` / `id_rsa`.

Ignored this wave: golden-journey / unrelated CI, Neon enablement, live hosts.

---

## Clean / not found (credentials)

| Check | Result |
|-------|--------|
| Tracked `.env` (non-example) | **none** (`.gitignore` has `.env` / `.env.*`; only `.env.example` is tracked) |
| Tracked `*.pem` / `id_rsa` / `id_ed25519` / `*.ppk` | **none** |
| Live `sk-` / `sk-proj-` API keys in current tree | **none** (hits are test fixtures or word false positives such as `skill-`) |
| Live `ghp_` / `gho_` / `github_pat_` | **none** (test placeholders + detector regexes) |
| Live `xoxb-` / Slack webhook | **none** (history: 0 commits) |
| Live `AKIA` / `ASIA` | **none** (AWS example key in redact tests only) |
| Passworded Neon / Postgres / Mongo / Redis URLs | **none** in current tree (comment example `pos…ss@` in `src/swarm/settings.py`; test fakes) |
| `whsec_` webhook secrets | **none** |
| SSH private key blobs | **none** (one test writes a header-only stub into a sandbox) |
| `swarm_config.json` raw `api_key` literals | **none** at HEAD; history classify: env-or-empty lines only, **0** raw literals |
| GitHub Actions token values | **none** (workflows reference `${{ secrets.* }}` only) |
| Pinokio `install.js` / `start.js` / `pinokio.js` | no host secrets; `install.js` copies `.env.example` → local `.env` (untracked) |
| `.env` ever committed | **0** commits (`git rev-list --all -- .env`); only `.env.example` added |

---

## Inventory

| # | Path | Lines (approx) | Category | Severity | in_git_history? | Proposed action | Redaction |
|---|------|----------------|----------|----------|-----------------|-----------------|-----------|
| 1 | `src/swarm/blueprints/harness_fleet/blueprint_harness_fleet.py` | 48–96 | home_lan_inventory | medium | history checked (current tree + many commits; same facts) | scrub file — replace built-in fleet with example/empty defaults | RFC1918 `10.…` hosts + ports + kinds; notes include systemd/docker, `C:\…zo`, home-automation role. Beyond hostname/role. |
| 2 | `swarm_config.json` | 393–409 | home_lan_inventory | medium | history checked | scrub file — keep `${…}` auth; drop real LAN URLs from the published default | remotes `base_url`/`ui_url` on `10.…36` / `10.…32`; auth is `${HER…}` / `${OMB…}` / `${RAK…}` |
| 3 | `src/swarm/core/remotes.py` | 10–12, 60–99 | home_lan_inventory | medium | history checked | scrub file — defaults to example hosts; keep env-key names | operator labels + `10.…` URLs + Windows tree `C:\…zo` |
| 4 | `src/swarm/core/config_loader.py` | 198–213, 523–531 | home_lan_inventory | medium | history checked | scrub file — default-config writer should not bake operator LAN | same remotes URLs as #2; keys still `${…}` |
| 5 | `docs/REMOTE_HARNESSES.md` | 30–56 | home_lan_inventory | medium | history checked | scrub file — hostname/role only, or fictional examples | table: host labels + `10.…` + UI ports + `C:\…zo` |
| 6 | `.env.example` | 183–194 | home_lan_inventory | medium | history checked (`.env` itself never committed) | scrub comments — keep empty key slots; drop live LAN map | comment “LAN facts” with host labels + `10.…`; values are `""` / `your-…` |
| 7 | `docs/HERDR.md` + Herdr code/tests/UI | see cluster below | personal_identity + ssh | medium | history checked | scrub file — example `user@host` only | SSH-style `matt…@10.…36` (also `workbox`, `ssh://you@…`) |
| 8 | `docs/requirements/*` live-preview line + `CONFIGURATION.md` + `docs/DEPLOYMENT.md` + `docs/EXAMPLES.md` + `docs/ASYNC_RESPONSES.md` + blueprint READMEs | various | home_lan_inventory | low | history checked | scrub file — `localhost` / example host; REQ-11 table is the densest | repeated preview `10.…30:8001`; EXAMPLES extra host `10.…107`; ASYNC curl `10.…36:8000` |
| 9 | `docs/demo/captures/raw_list.txt`, `scene2.txt`, `raw_zeus_cli.txt` | 1–38 / 3 / 1 | personal_identity | low | history checked | scrub file — anonymize home path in captures | `/hom…wh/.local/share/swarm/…` |
| 10 | `pyproject.toml` | 13 | personal_identity | low | history checked | leave-as-placeholder (intentional public PyPI author metadata) | maintainer email `matt…com` |
| 11 | `src/swarm/utils/env_utils.py` | 28 | other | low | history checked | leave-as-placeholder (debug-only well-known fallback; prod refuses unset key) | `djan…-dev` |
| 12 | `tests/unit/test_redact*.py`, `tests/core/test_redact*.py`, `tests/core/test_tool_executor.py`, `tests/unit/test_prod_p0_secrets_creator_workers.py`, `tests/utils/test_env_utils.py`, `tests/test_consumers.py` | various | api_key / token / connection_string | low | history checked | leave-as-placeholder | `sk-…def`, `ghp…eak`, `AKI…PLE`, `pos…r2@` |
| 13 | `tests/core/test_filesystem_toolset.py` | 197–198 | private_key | low | history checked | leave-as-placeholder | sandbox write of header-only `---…KEY` / `---…ATE` (no key body) |
| 14 | `deploy/oracle/open-swarm-oracle.service` | 14, 21 | token / other | low | history checked | leave-as-placeholder | `CHAN…RET`, `CHAN…KEN`, path `/hom…SER/…` |
| 15 | `.github/workflows/docker-io-fly-deploy.yml`, `publish.yml` | 27–28, 57, 68, 88 | token | low | history checked | leave-as-placeholder | `${{ secr… }}` refs only |

### Finding 7 — Herdr identity cluster (same string)

| Path | Lines (approx) |
|------|----------------|
| `docs/HERDR.md` | 22–32, 41, 96–97 |
| `src/swarm/herdr/client.py` | 11 |
| `src/swarm/models/herdr.py` | 24 |
| `src/swarm/views/herdr_api.py` | 88, 109 |
| `src/swarm/migrations/0012_herdragent.py` | 33 |
| `src/swarm/templates/settings_dashboard.html` | 192–193 |
| `tests/herdr/test_herdr_client.py` | 3, 88–97 |
| `tests/views/test_herdr_api.py` | 51–55 |

### Finding 8 — docs LAN cluster (hostname/role + IP, not a full fleet dump)

Primary extra-beyond-role docs (besides #5–#7):

| Path | Lines (approx) | Extra beyond hostname/role |
|------|----------------|----------------------------|
| `docs/requirements/REQ-11.md` | 15–21 | remotes table with `10.…` + ports |
| `docs/requirements/README.md` and REQ-7, 8, 9, 10, 12–21, 23, 24, 26, 28, 37, 18-25 | one line each | live preview `10.…30:8001` |
| `CONFIGURATION.md` | 109, 280 | LAN LLM `10.…30`; CSRF example |
| `docs/DEPLOYMENT.md` | 44 | CSRF origin `10.…30` |
| `docs/EXAMPLES.md` | 158 | LLM `base_url` `10.…107` + `${LIT…}` |
| `docs/ASYNC_RESPONSES.md` | 29, 72, 81, 86 | curl examples `10.…36:8000` |
| `src/swarm/blueprints/remote_harness/README.md` | 16–33 | same remotes URLs as #5 |
| `tests/blueprints/test_harness_fleet.py`, `tests/blueprints/test_remote_harness.py`, `tests/cli/test_remotes_command.py`, `tests/core/test_remotes.py`, `tests/views/test_remotes_api.py` | various | assert the published LAN defaults |

---

## History taint (light)

Commands run (subjects/paths only; patch bodies not copied into this file):

- `git log --all -S 'sk-' --max-count=20` — 20 commits, almost all tests / session / `skill-` wording.
- `git log --all -S 'ghp_' --max-count=20` — 4 commits, all tests or detector regex.
- `git log --all -S 'BEGIN PRIVATE KEY' --max-count=20` — 1 commit, `tests/core/test_filesystem_toolset.py` header stub.
- `git log --all -S '.env' --max-count=20` — 20 commits, product/docs mentions; **no** `.env` file.
- `git log --all -S 'AKIA'` — 1 commit, redact tests + AWS example key.
- `git log --all -S 'xoxb-'` — 0 commits.
- `git log --all -S 'postgres://'` — 6 commits, settings comment + redact/local-store tests.
- `git rev-list --all -- .env` — **0**.
- Add-name search for `*.pem` / `id_rsa` / `id_ed25519` — **empty**.
- `swarm_config.json` `-p` classify of `api_key` / `password` / `token` assignments — **0** raw literals.

Ambiguous `sk-` `-p` hits were reclassified by shape (no values recorded):

| Commit (short) | Path | Class |
|----------------|------|--------|
| `887b4b1d53aa` | `src/swarm/urls.py` | word false positive (`skill-…`) |
| `fba9e8567e6f` | `tests/core/test_cli_sessions.py` (deleted since) | test asserts / short placeholder assign (`rhs` length 16) |
| `fba9e8567e6f` | `src/swarm/core/cli_sessions.py` (deleted since) | detector regex |
| `6e3219ecd837` | `tests/core/test_filesystem_toolset.py` | header-only private-key stub |
| `ba567b7ec945` | `tests/core/test_local_store.py` (deleted since) | test URI fakes (`pos…r2@`) |
| `139ef9309dde` | `src/swarm/settings.py` | comment example `pos…ss@` |

**No history hit looked like a live provider token, GitHub PAT, Slack bot token, AWS key, or PEM body.** This was a light pass (`--max-count=20` per needle), not a full `git filter-repo` audit.

Identifying LAN IPs and the `matt…@10.…` example **do** exist in many historical commits (they are still at HEAD). That is the same published map, not a deleted extra secret.

---

## Taint assessment

**A — scrub current tree enough** (for credentials).

- No live API keys, tokens, private keys, webhook secrets, or passworded
  database URLs were found in the tracked tree.
- Light history grep did **not** show a deleted `.env`, PEM, or raw
  `swarm_config.json` key that would require rotate + rewrite.
- Do **not** treat this PR as a clean bill for a full forensic rewrite; it
  is enough to say history is **unlikely** to be credential-tainted.

**Not B:** no rotate-worthy secret was identified. Matthew should still
rotate anything that was *ever* pasted into a chat/CI log outside this repo;
that is out of scope.

**LAN / identity caveat (still A, not B):** findings 1–9 are identifying
operator facts (RFC1918 map, SSH user@host, home path), not credentials.
Scrubbing HEAD in a later PR leaves the same strings in git history. A
history rewrite would only be for **privacy unpublished**, not because a
key leaked. Matthew decides; this PR does not rewrite.

**C** is not selected: the credential scan was conclusive enough at the
requested depth.

---

## Proposed later work (not this PR)

1. Replace `harness_fleet` built-ins and remotes defaults with fictional
   or empty inventory; load real hosts from untracked local config.
2. Redact docs/REQ/`.env.example` comments to hostname/role or
   `203.0.113.x` examples; drop `C:\…` and `matt…@10.…`.
3. Anonymize `docs/demo/captures/*` home paths.
4. Leave test fixtures and the debug Django fallback as placeholders.
5. No BFG / `git filter-repo` unless Matthew wants the LAN map erased from
   history after the tree scrub.

Refs #453.
