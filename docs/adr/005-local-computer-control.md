# ADR-005: Local computer control — adapt OMB + Rakazo; do not invent a third stack

- **Status:** Proposed (look-only; no runtime change in this PR)
- **Date:** 2026-09-04
- **Programme:** [#645](https://github.com/matthewhand/open-swarm/issues/645) (REQ-189)
- **Related:** [#361](https://github.com/matthewhand/open-swarm/issues/361) (REQ-45 browser this-machine), [#378](https://github.com/matthewhand/open-swarm/issues/378) (REQ-55 Safety approval), [#388](https://github.com/matthewhand/open-swarm/issues/388) (REQ-62 OpenMousBot remote), [ADR-001](../ADR-001-primary-ui.md) (SPA `/` + `/chat`), [ADR-002](./002-config-ownership.md) (config SoT), open [ADR-003](https://github.com/matthewhand/open-swarm/pull/576) (desktop packaging)
- **Sources (public GitHub, 2026-09-04):** [matthewhand/OpenMausBot](https://github.com/matthewhand/OpenMausBot) `main`, [matthewhand/rakazo](https://github.com/matthewhand/rakazo) `main`
- **Sibling look-only PRs:** none open on those forks for REQ-189. Closest drafts are architecture reviews ([OMB #18](https://github.com/matthewhand/OpenMausBot/pull/18), [rakazo #13](https://github.com/matthewhand/rakazo/pull/13)), not computer-control reports.
- **Supersedes:** none. Complements REQ-45 (browser default) and the REQ-27b chrome stub. Does **not** close #645.

**Decision:** stay a **harness-of-harnesses**. Do not embed CUA-driver, xdotool, or a third desktop stack in Django/uvicorn.

1. **Browser (this machine)** stays the native default (Playwright). Already catalogued.
2. **Isolated computer** = Docker sibling sandbox. Copy **Rakazo’s `SandboxProvider` contract** (supervisor owns the Docker socket). Do not give the swarm API process an unrestricted socket.
3. **Host desktop (“This computer”)** = **placed OpenMousBot or Rakazo remote**, not a swarm-owned driver. Global enable ≠ per-agent assign. Auto never selects the host.
4. **SaaS** (E2B, Daytona, Box, hosted browsers) stays greyed TODO.

This ADR is **feasibility-first**. It records what OMB, Rakazo, and open-swarm do today, then picks one adaptation. It does **not** wire a driver, provision a sandbox, or change chrome.

No secrets are documented here. Use `${VAR}` names only.

---

## Issue quote (REQ-189)

**Intent:** Reuse proven local computer-control patterns; don’t invent a third stack blind.

**Success (this Issue):**

1. Look-only report on OMB: entry points, host vs Docker, permissions/approvals, API surface, SPA affordances.
2. Same for Rakazo.
3. open-swarm ADR/proposal: recommended architecture (what to copy, what to drop, bare-metal vs compose sandbox), phased Issues. No runtime product change in this pass.
4. SaaS explicitly deferred.

**Constraints:** Look-only. No secrets in reports. Prefer Cursor clouds on each fork + synthesis PR on open-swarm. No Neon.

Owner / CoS: implement later after Matthew picks. This PR does **not** `Fixes` #645.

---

## 1. Feasibility (what exists today)

Open-swarm already has **chrome and a browser catalog**. It does **not** have a computer driver, a sandbox supervisor, or remotes `operate` ops beyond `list` / `send`.

The expensive parts are not “pick an icon.” They are:

1. **Three overlapping UIs** that tell different stories (header stub vs Settings pane vs unused Globe pane).
2. **App runtime mode ≠ computer provider.** `SWARM_RUNTIME_MODE` describes where *this process* runs. Playwright “this machine” is a different axis.
3. **Host control from inside Compose is a lie** unless a sibling sandbox or a LAN remote owns the desktop.
4. **Approval is API-agent only** (REQ-55). CLI/remote keep their own brokers. Computer tools must not invent a second card stack.

A third CUA/xdotool implementation inside Django would paper over (1)–(4) and fight OMB’s TCC/Electron rules. This ADR rejects that.

---

## 2. Evidence: OpenMausBot (local only)

Upstream is the Grok-Bot-shaped chat app (Electron + harness on `127.0.0.1:8799`). Matthew’s fork is [matthewhand/OpenMausBot](https://github.com/matthewhand/OpenMausBot). SaaS/cloud boxes and BYO-VPS are noted only to mark them **out of scope**.

### 2.1 Entry points

| Surface | Role | Evidence |
|---|---|---|
| SPA **Computer panel** (right slot) | Per-bot destination, live preview, take/release | `src/components/ComputerPanel.tsx` |
| **This computer** / Local VM / Cloud / VPS pickers | Explicit per-bot assign | `apps/docs/content/docs/computers/index.mdx` |
| Settings **Enable local control** | Global opt-in; does **not** assign a bot | `docs/linux-desktop.md`, `local-computer.mdx` |
| **Preview this computer** | View-only; never grants control | `docs/linux-desktop.md` |
| Inline **approval cards** | Allow / Deny / Always; Inspector for detail | `docs/features/approvals-and-inspector.mdx`, `src/components/ApprovalCard.tsx` |
| Harness HTTP | Bot CRUD + computer lifecycle | `server/index.ts` |

### 2.2 Host vs Docker

| Backend | Isolation | How it runs | Notes |
|---|---|---|---|
| **This computer** | None | Bundled **CUA-driver** spawned from **Electron main**, MCP proxy over a private socket | macOS + Ubuntu Xorg after explicit opt-in. Wayland **fail-closed** (upstream #345). Auto **never** routes to the user desktop. |
| **Local VM** | Container desktop | Docker / Podman. Image `localhost/openmausbot/cua-local-vm` from pinned `trycua/xfce-cua`. Agent talks `cua-driver mcp` **inside** the container | Shared or per-bot. Durable mount is `/home/cua/workspace` only. Viewer loopback `:6080`. |
| Cloud Box / VPS | Remote | Out of scope (SaaS / self-host remote) | Listed so we do not pretend they are local |

`deploy/docker-compose.yml` is the **app tenant** (harness + Caddy). It is **not** the Local VM. Host control requires the Electron (or equivalent) process on a real desktop session.

CUA policy (`docs/computer-use-integration.md`): **CUA is the only host-control provider.** No cliclick / robotjs / Python computer-server. Spawn from Electron main so OS permissions attach to OpenMausBot, not a Node gateway.

### 2.3 Permissions / approvals

`server/auto-approve.ts` + `server/permission-proxy.ts` + `server/computer-control.ts`:

- Default: human cards every risky tool.
- **Always allow** is keyed `Tool:program` for shells (`Bash:git`), not a bare `Bash` grant.
- **Guards outrank grants:** destructive (`rm -rf`, `mkfs`, …) and sensitive (`.env`, `.ssh`, keychain) still card. Regex is a backstop, **not** a security boundary.
- **`local-computer` scope:** Always-allow does **not** cover host GUI. Unattended / webhook turns never inherit Auto.
- **Take / release:** only the person takes the wheel. While held, proxies **refuse** bot actions (do not queue). `requestHelp` is a plea, not a grant. Hold is in-memory per boot.
- Linux: global enable + per-bot **This computer** + per-action cards. Preview ≠ control.

### 2.4 API surface (local, no secrets)

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/health` | `{"app":"openmausbot",…}` — swarm remotes already probe this |
| `GET` | `/api/bots` | List bots (operate `list` today) |
| `POST` | `/api/bots/{id}/messages` | Send (operate `send` today) |
| `GET` | `/api/local-computer` | Shared Local VM status (runtime, image, hardened flags) |
| `POST` | `/api/local-computer/{pull\|run\|start\|stop\|remove}` | Shared VM lifecycle (JSON + no CORS) |
| `POST` | `/api/local-computer/screenshot` | Shared VM PNG |
| `GET` | `/api/bots/{id}/local-computer` | Per-bot VM status |
| `POST` | `/api/bots/{id}/local-computer/{run\|stop\|remove}` | Per-bot VM lifecycle |
| `POST` | `/api/local-computer/interrupt` | Stop host-local turns + close approvals |
| `GET/POST/DELETE` | `/api/internal/computer-control?botId=` | Hold / help (loopback, `COMMS_TOKEN`) |

SSE `computer` / `computer-control` events drive the panel. LAN auth (Bearer / session) gates `/api/*` except health.

### 2.5 SPA affordances to reuse

- Monitor panel with destination radios, live frames, **Take control** / release, help-reason card.
- Separate **Preview** vs **Enable local control**.
- Honest disabled states (Wayland, missing Docker, engine cannot mount computer MCP).
- Loopback noVNC **not** opened from a LAN tab (fork PRs #9/#11).

### 2.6 What not to copy into Django

- Embedding `cua-driver` in uvicorn (wrong TCC identity; no Electron main).
- Shipping a pinned CUA ELF in the swarm image.
- Cloud Box / Composio / VPS as v1.
- Claude `--permission-prompt-tool` MCP proxy unless a later CLI-wrap Issue needs it.

---

## 3. Evidence: Rakazo (local only)

Matthew’s fork is [matthewhand/rakazo](https://github.com/matthewhand/rakazo) (upstream elie222/rakazo). Agent runtime (Pi) and computer runtime are separate. SaaS providers (E2B, Daytona, Box) are documented only as **deferred**.

### 3.1 Entry points

| Surface | Role | Evidence |
|---|---|---|
| Web Computer UI + mobile `computer.tsx` | Status, screen, takeover | `apps/web`, `apps/mobile` |
| First-run **HostComputerPrompt** | Docker (recommended) vs this Mac / this computer | `apps/web/src/pages/HostComputerPrompt.tsx` |
| `rpc.computer.*` | status / boot / stop / takeover / release / input / files / screenUrl / heartbeat | `packages/contracts/src/rpc.ts` |
| `rpc.bots.setComputer` | Per-bot mode | same |
| `rpc.deployment.update({ computerHost })` | `docker` \| `this-mac` | same |
| Compose | API + worker + **supervisor** + `rakazo/computer:local` | `docs/self-host.md`, `infra/compose/` |

### 3.2 Host vs Docker

| Provider | Isolation | How it runs | Notes |
|---|---|---|---|
| **`docker`** (default) | Sibling containers | Supervisor on the internal network holds the Docker socket. API/worker call HTTP. Image `rakazo/computer:local` (Xvfb / Fluxbox / browser) | Team Computer shared by default; Private optional. Persistent home under `/home/rakazo`. Multi-screen via extra Xvfb. |
| **`desktop` / this-mac** | None | Commands on the API/worker host; graphical tools are **placeholders** (`graphical: false`, `takeover: false`) | Electron asks once. “Runs as you.” Forbidden on a public/shared host. **Not** a CUA desktop. |
| E2B / Daytona / Box | Remote SaaS | `SandboxProvider` adapters | Deferred |

`SANDBOX_PROVIDER=desktop` is an explicit host-shell provider. It is **not** OMB-style GUI control.

### 3.3 Permissions / approvals

- Better Auth on RPC (swarm already hits this: operate needs `RAKAZO_SESSION_COOKIE` / API key).
- Takeover lease: human input and agent input may coexist; “Take control” flips the viewer, does not pause the run. `request_takeover` when the model needs protected input.
- Team Computer: fenced per-bot **screen** lease; `MULTI_SCREEN_UNAVAILABLE` is honest.
- Workspace is the durable boundary; OS packages are disposable.

### 3.4 API surface (local)

`SandboxProvider` (`packages/adapters/src/docker-sandbox.ts`): provision / stop / destroy, `observe`, batched `act`, `execute`, files, `connectScreen`, `setScreenControl`, `sendInput`.

Supervisor HTTP (Bearer `SANDBOX_SUPERVISOR_TOKEN` / `BETTER_AUTH_SECRET`): `/computers`, `/exec`, `/observe`, `/actions`, `/files`, `/screen`, `/screen-mode`, `/input`.

Product RPC (Better Auth session): `computer.status|boot|stop|takeover|release|input|files|readFile|screenUrl|heartbeat`.

Swarm remotes today: `GET /health`, `POST /rpc/bots/list`, `POST /rpc/threads/send`. **No computer RPC.**

### 3.5 SPA affordances to reuse

- First-run “where should bots run?” (Docker vs host) with a warning that host = your account.
- Team vs Private computer.
- Screen URL behind an authenticated proxy (do not leak noVNC secrets into the browser).
- Teach-computer / live viewer (later; not v1).

### 3.6 What not to copy

- E2B / Daytona / Box.
- Making Better Auth the only swarm computer API (we already have Bearer).
- Treating `desktop` provider as “real GUI host control.”
- Giving Django the Docker socket.

---

## 4. Evidence: open-swarm today

### 4.1 Chrome (three stories)

| UI | Mounted? | Story it tells |
|---|---|---|
| `ComputerControlStub` | Yes — Chat header Monitor | “Will use a placed OpenMousBot or Rakazo remote; WIP.” |
| `ComputerControlSheet` + `ComputerControlPane` | Yes — Search / Settings overlay | Browser (this machine) selected; Sandbox / SaaS greyed. Copy: “Desktop OS automation is out of scope.” |
| `BrowserControlPane` (Globe) | **No** (tests only) | Same catalog; “Desktop/OS stays on the #341 stub.” |

Header icon and overlay **disagree**. Stub promises remotes; pane promises Playwright and rules out desktop. REQ-189 must pick one catalog.

Search palette action “Computer control” opens the **overlay**, not the stub modal (`SearchPalette.tsx`).

### 4.2 Browser vs app runtime

| Axis | SoT | Values |
|---|---|---|
| **Browser provider** | `GET /v1/browser-control/` · `swarm.core.browser_control` | `this_machine` (Playwright navigate + snapshot). `sandbox` / `saas` return TODO dicts. `desktop_os: out_of_scope`. |
| **App runtime banner** | `GET /v1/runtime/` · `SWARM_RUNTIME` / `SWARM_RUNTIME_MODE` | `bare-metal` / `sandbox-home` / `sandbox-isolated` / `unknown`. About **this process’s filesystem**, not the computer provider. |

Compose (`docker-compose.yml`) defaults `SWARM_RUNTIME=sandbox-home` and bind-mounts `$HOME` config/state. Playwright “this machine” then means **Chrome inside that container** unless `SWARM_CHROME_CDP` attaches to a host browser. That is easy to lie about in the UI.

Native tools: `browser_control.PlaywrightChrome` plus optional `@playwright/mcp` for blueprints that declare `browser`. Not attached to the header icon.

### 4.3 Approval

REQ-55: API agents only. Websocket `tool_approval` → Safety dialog Allow / Always allow / Deny. Always-allow is **bare tool name** in `localStorage` (`safety.ts`). CLI/remote **must not** be intercepted.

No take/release hold. No `Tool:program` keying. No local-computer scope block.

### 4.4 Remotes

`operate` is `list` | `send` only (`src/swarm/core/remotes.py`). OMB `/api/local-computer*` and Rakazo `rpc.computer.*` are unused. Placing a remote does **not** give swarm a computer.

UI label remains **OpenMousBot** (id `omb`).

---

## 5. Decision — adapt, do not clone

### 5.1 Architecture

```text
SPA Monitor icon ──► ComputerControlSheet (one catalog)
                         │
                         ├─ Browser (this machine) ── Playwright / playwright-mcp
                         │     Safety cards on API agents (REQ-55)
                         │
                         ├─ Sandbox / Docker ── sibling supervisor + computer image
                         │     (copy Rakazo SandboxProvider; or place a local Rakazo)
                         │
                         ├─ This computer (host) ── placed OpenMousBot or Rakazo
                         │     their broker + take/release; swarm does not spawn CUA
                         │
                         └─ SaaS ── greyed TODO (deferred)
```

**Native in open-swarm:** browser tools + Safety + chrome catalog + (later) an optional Docker supervisor **sidecar**.

**Native in the placed harness:** host GUI, Local VM, their approval cards, their screen preview.

**Never in uvicorn:** `cua-driver`, X11/Wayland seats, unrestricted Docker socket.

### 5.2 What to copy / drop

| Pattern | Copy? | Into |
|---|---|---|
| OMB approval cards + Always / Deny | **Yes** (already REQ-55) | Tighten keys / host-scope in a later Issue |
| OMB `Tool:program` Always-allow + destructive/sensitive guards | **Yes** | Safety implement Issue |
| OMB take/release (refuse, don’t queue) + `requestHelp` | **Yes** | Sandbox + remote-host pane |
| OMB preview ≠ control; Auto never picks host | **Yes** | Catalog rules |
| OMB Local VM (Cua-in-container) | **Concept only** | Prefer Rakazo image/contract if we build a sidecar |
| OMB CUA-from-Electron-main | **No** | ADR-003 desktop app *might* later; not Django |
| Rakazo `SandboxProvider` + supervisor-owns-socket | **Yes** | Phase 4 sidecar **or** “place local Rakazo” |
| Rakazo first-run Docker vs host prompt | **Yes** (copy) | First time operator enables computer |
| Rakazo Team vs Private computer | **Yes** (map) | Swarm Team vs per-agent |
| Rakazo `desktop` placeholder GUI | **No** | Host GUI = placed OMB/Rakazo |
| E2B / Daytona / Box / Polar | **No** | SaaS deferred |
| New xdotool / robotjs / third CUA bind | **No** | — |

### 5.3 Bare-metal vs Compose

| Where swarm runs | Browser (this machine) | Sandbox / Docker | This computer (host) |
|---|---|---|---|
| **bare-metal** (`SWARM_RUNTIME_MODE=bare-metal`) | Playwright → host Chrome (or `SWARM_CHROME_CDP`) | Local Docker sibling / placed Rakazo | Placed local OMB (Xorg/macOS) or Rakazo Electron host — explicit opt-in |
| **sandbox-home** (default compose) | Chrome **in the swarm container** or CDP to host — badge which | Sibling supervisor (not this container) | **Fail closed** unless a LAN OMB/Rakazo is placed. Do not claim host GUI. |
| **sandbox-isolated** | Same as home, narrower FS | Same sibling rule | Fail closed |
| **unknown** | Do not claim isolation or host | Do not provision | Do not enable |

App-runtime banners stay as they are. Computer pane must **not** reuse those strings to imply a desktop seat.

### 5.4 Approval UX (one card stack)

For **swarm-owned** tools (Playwright, future sandbox tools on API agents):

- Keep REQ-55 cards: Allow / Always allow / Deny.
- Adopt OMB keying: shell/computer Always-allow is `tool:program` (or `scope:tool:program`), computed server-side, echoed to the client.
- Adopt OMB host-scope: Always-allow **never** covers `local-computer` / host GUI. Auto on host requires the OMB-style warning and still cards destructive/sensitive.
- Timeout deny (already 300s) stays.
- CLI/remote: **no second swarm prompt**. If the computer is a placed OMB/Rakazo, **their** card is the SoT. Swarm may show a status chip (“waiting on OpenMousBot approval”) later; do not re-ask.

Takeover is **not** an approval card. It is a hold: bot computer_act/input returns refused while the person drives.

### 5.5 Chrome unification (implement later)

One Monitor icon in the Chat tools toolbar (keep REQ-93 icon-only). Click opens `ComputerControlSheet` (same pane as Settings → Computer control). **Delete or demote** `ComputerControlStub`’s WIP modal so header and overlay match.

Catalog rows (names locked for implement Issues):

| Row | v1 | Copy |
|---|---|---|
| Browser (this machine) | Enabled | Playwright on the machine that runs the agent. |
| Sandbox / Docker | Grey until Phase 4 | Isolated desktop. Supervisor or placed Rakazo. Not this app container. |
| This computer (host) | Grey until Phase 5 | Requires a placed OpenMousBot or Rakazo with host control ready. Auto never selects this. |
| SaaS | Grey forever in this programme | Deferred. No live paid checkout. |

Do not mount `BrowserControlPane` as a second Globe icon. Merge its catalog into the Monitor pane.

Live preview is **Phase 5+**. v1 can be status + approvals + (browser) navigate/snapshot honesty.

### 5.6 Config / remotes

No new SoT. Per ADR-002:

- Topology (which remotes, later `computer.provider`) lives in `swarm_config.json`.
- Secrets stay env (`OMB_API_KEY`, `RAKAZO_SESSION_COOKIE`, future `SANDBOX_SUPERVISOR_TOKEN`).
- Do not put Docker socket paths or host usernames in UI copy.

New `operate` verbs (Phase 3) are additive: `computer-status`, `computer-screenshot` — fail honestly when the remote has no computer or auth is missing. Do not expand `list`/`send` semantics.

---

## 6. Phased Issues (parked — do not implement here)

CoS files these when Matthew picks. Titles only; #645 stays the **programme** parent (do not close it when a phase merges unless CoS says so).

1. **Unify computer-control chrome** — Header Monitor opens `ComputerControlSheet`. Remove stub modal split. Merge unused `BrowserControlPane`. Honest copy for the four rows. Tests: one dialog; no Globe; e2e header + Settings match.
2. **Playwright as an API-agent tool + Safety** — Attach navigate/snapshot to API agents that opt in. Missing Chrome → structured error (already). Safety cards on concern. Tests: stub driver; CLI/remote skip swarm approval.
3. **Remotes: computer operate (OMB + Rakazo)** — `operate` ops for Local VM / `rpc.computer.status` (and screenshot if cheap). Settings pane shows placed-remote readiness (UP + computer ready / missing / auth). No driver in swarm. Tests: mocked HTTP; never OMB in UI copy.
4. **Docker sandbox sidecar (optional native)** — Compose service: supervisor + `computer` image. API talks HTTP with a token. Copy Rakazo contract (observe / batched act / exec / files / takeover). **Or** document “place a local Rakazo with `SANDBOX_PROVIDER=docker`” and skip a native sidecar if Matthew prefers zero new images. Tests: fake supervisor; no Docker socket on the web service.
5. **Safety tightening for computer/shell** — Server-side Always-allow keys; destructive/sensitive guards; host-scope block; take/release hold. Decision log optional. Tests: `Bash:git` does not grant `Bash:rm`; host click not Always-allowed.
6. **Host desktop via placed remote** — Enable the “This computer” row only when a placed OMB/Rakazo reports host-control ready. Preview ≠ control. Auto never selects. LAN loopback viewer guard. Depends on (3) + (5).
7. **SaaS providers** — Parked. Keep the grey row. No E2B/Daytona/Box keys in v1.

Suggested parent text: “Programme: REQ-189 / #645. This Issue does not close #645.”

---

## 7. Consequences

- Operators get one Monitor story: browser here, isolated Docker, or a placed OpenMousBot/Rakazo for real host GUI.
- Compose stays honest: sandbox-home is not a desktop seat.
- Implementers reuse two proven stacks instead of a third CUA bind.
- SaaS stays a labelled TODO.
- This PR: documentation only. **Does not close #645.**

---

## 8. Non-goals

- Runtime chrome or driver changes in this PR.
- Neon, Oracle, Fly open-litellm remotes.
- Closing #645 from a look-only merge.
- Inventing secrets, host paths, or a sync engine for computer state.
