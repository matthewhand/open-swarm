# Self-update (REQ-79 / #424)

Prove that **open-swarm can continue without Grok CoS**: SPA chat works with
CLI and/or API agents, and an **in-app** coding CLI can open a real GitHub PR
on [`matthewhand/open-swarm`](https://github.com/matthewhand/open-swarm).

Issue: [#424](https://github.com/matthewhand/open-swarm/issues/424).
Chrome for a printed PR URL: REQ-71 View PR card (`swarm.core.pr_opened`).
Wiring: `swarm.core.self_update`, skill `self-update-pr`, harness
`scripts/prove_self_update.py`.

This page is the operator path. It does **not** invent a PR URL.

## 1. SPA must hydrate

`dist/` is gitignored. Without a build, Django may serve the template index
(no React `#root` mount).

```bash
make frontend
# or: ./scripts/build_frontend.sh
```

`/` and `/chat` must serve `webui/frontend/dist/index.html` with
`<div id="root">` and the baked JS. A blank `#root` is a fail. Preview-down
blocks this REQ — do not fake the prove from GitHub-only.

## 2. API chat (already on main)

1. Select or create an API seat (Add-agent API → rail-visible).
2. Send a message. The websocket streams the reply.
3. Reload: `GET /chat/thread/` keeps the thread.
4. Unused tools must not crash (`make_agent(..., tools=None)` → `[]`).

Do not re-stack session persist/hydrate — that shipped under REQ-171A.

## 3. CLI chat + resume (already on main)

1. Catalogue a CLI (`grok` / `agy` / `claude` / `gemini` / `codex` / `opencode` / `pi`).
2. Send from SPA. First turn stores the CLI session id on the thread
   (`cli_sessions`).
3. Second send resumes that id (`--resume` / `--session` per catalog).
4. If the CLI cannot resume: a **bubble-less** line
   `Started a new {cli} session.` — never “Restored” / fake restore.

## 4. Self-update prove (in-app CLI)

Preferred seat: a **coding** catalog CLI with Folder bound to this checkout
(REQ-167 Folder is process cwd; unset Folder mints a temp under
`SWARM_WORKSPACES_DIR` and **cannot** write this repo).

1. Attach skill [`self-update-pr`](../skills/self-update-pr/SKILL.md)
   (`/skill self-update-pr` or the agent-editor checkbox).
2. Send: open a trivial docs or test PR on `matthewhand/open-swarm`.
3. The CLI commits, pushes, and runs:

   ```bash
   gh pr create --repo matthewhand/open-swarm --json url,number,title
   ```

4. Chat parses a real `https://github.com/matthewhand/open-swarm/pull/N`
   from stdout and emits REQ-71 **View PR**. No URL in stdout → no card.
5. Paste that URL on [#424](https://github.com/matthewhand/open-swarm/issues/424).

The PR must be opened **by the in-app agent**, not by Cursor cloud / Grok Bot.

## 5. Cursor cloud / CI deviation

Cloud VMs and CI run the **fixture harness**, not a live in-app PR:

```bash
uv run python scripts/prove_self_update.py
```

The script parses sample `gh` JSON / URL lines, prints this checklist, and
reports `live_pr_url: null` plus an honest deviation when
`SWARM_SELF_UPDATE_LIVE` is unset or the process is not the SPA CLI.

**Do not** write a placeholder PR URL into the Issue or this file.

Live create (operator laptop only):

```bash
SWARM_SELF_UPDATE_LIVE=1 uv run python scripts/prove_self_update.py
```

That flag still does not invent a URL; it only allows the probe to say
`can_live` when `gh` is on PATH and this is not a Cursor cloud VM. Opening
the PR remains the in-app CLI's job.

## Constraints

- Own-diff. No Neon. No secrets / tokens in Issues or PRs.
- No guessed LAN hosts. No feature-flag `:8001`.
- Do not bounce Hermes. Do not fold into #344.
- Chat/session resume work already on `main` is reused, not rewritten.
