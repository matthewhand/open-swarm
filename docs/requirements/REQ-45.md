# REQ-45 — Browser control (Playwright / this-machine first)

**Status:** in flight — Fixes [#361](https://github.com/matthewhand/open-swarm/issues/361)

## Intent

Agents can drive a **bare-metal browser** on the machine (Antigravity-style
Chrome control). Playwright is the expected driver. OMB/Rakazo-style sandboxed
Docker or SaaS browsers are desirable later, not v1. Desktop OS control stays
out of v1 (keep the existing #341 WIP stub).

## Success

1. **Research** — table of options (Playwright vs Antigravity Chrome vs
   OMB/Rakazo sandbox/Docker/SaaS) with adopt/adapt/skip for a
   harness-of-harnesses. No secrets.
2. **UI** — computer/browser control pane: **Browser (this machine)** is the
   default. **Sandbox / Docker** and **SaaS** rows exist and are **greyed TODO**
   (clickable WIP, not wired). Do not pretend they work.
3. **Driver** (same PR if small) — Playwright launches/attaches local
   Chrome/Chromium and can navigate + snapshot. Tests use a fake/stub browser.
   Missing Chrome → visible error, no crash.
4. Chrome stays Grok-Bot-style and **agnostic** to CLI / API / remote.

### Addendum — runtime banner

Compose (dev sandbox) passes `SWARM_RUNTIME_MODE` into the app.

| Mode | Meaning | Banner |
|---|---|---|
| `bare-metal` | Dedicated harness machine, no container | warning |
| `sandbox-home` | Compose with `$HOME` (or `SWARM_SANDBOX_ROOT`) mapped | warning |
| `sandbox-isolated` | Compose *without* that tree mapped | green/info |
| unset / junk | Honest unknown | never fake green |

Dismissible; persist dismissed (localStorage like hostname). Re-show if mode
changes. Copy uses `$HOME` / `SWARM_SANDBOX_ROOT` placeholders only. This
banner is where the **app** is running; Playwright-on-this-machine stays the
default browser-control choice.

## Constraints

React 18 + Vite + Tailwind 4 + DaisyUI 5. Do not fold into chrome PR #344.
Distinct from #341 stub. No live preview checkout. No secrets. Do not enable
Neon/oracle. Desktop/OS automation is out of scope (grey if shown).

## Owner

Cursor cloud investigates + UI grey-out; engineer quotes this Issue +
feasibility before a driver merge.
