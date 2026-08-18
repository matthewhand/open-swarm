# Auth & trust model

One-page map of how Open Swarm authenticates callers, stamps ownership, and
bounds execution. Operators can reason about **who** can hit which surface and
**what** that principal may see or run.

Canonical code: [`src/swarm/auth.py`](../src/swarm/auth.py),
[`src/swarm/consumers.py`](../src/swarm/consumers.py),
[`src/swarm/core/responses_store.py`](../src/swarm/core/responses_store.py),
[`src/swarm/core/blueprint_sandbox.py`](../src/swarm/core/blueprint_sandbox.py),
workdir helpers under `swarm.core.workdir` / CLI fusion support.

Related: [DEPLOYMENT.md](./DEPLOYMENT.md) · [CONFIGURATION.md](../CONFIGURATION.md) ·
[SESSION_EXPLORER.md](./SESSION_EXPLORER.md) · [websocket_chat.md](./websocket_chat.md) ·
[FEATURE_STATUS.md](../FEATURE_STATUS.md) §10 Security.

---

## Diagram

```text
                    ┌─────────────────────────────────────────────┐
                    │              Client / operator              │
                    └───────────────┬─────────────┬───────────────┘
                                    │             │
              Authorization: Bearer │             │ Django session cookie
              (API_AUTH_TOKEN[S])   │             │ (form login @ /login/)
                                    ▼             ▼
                    ┌───────────────────┐   ┌─────────────────────┐
                    │  REST /v1/*       │   │  WebUI + WS chat    │
                    │  StaticTokenAuth  │   │  @login_required /  │
                    │  → token:<sha24>  │   │  AuthMiddlewareStack│
                    │  (+ session OK)   │   │  → user:<name>      │
                    └─────────┬─────────┘   └──────────┬──────────┘
                              │                        │
                              │  Bearer does NOT       │ anonymous WS
                              │  authenticate WS       │ accept→close 4401
                              ▼                        ▼
                    ┌───────────────────┐   ┌─────────────────────┐
                    │ /v1/responses     │   │ /sessions/ Explorer │
                    │ IDOR: same        │   │ operator bridge:    │
                    │ principal only    │   │ user:* + configured │
                    │ owner_allows()    │   │ token:* (REST stays │
                    │                   │   │ strict)             │
                    └───────────────────┘   └─────────────────────┘

  Workdir: params.workdir/cwd under SWARM_WORKSPACES_DIR
           (ALLOW_UNRESTRICTED_WORKDIR opt-in escape)
  Blueprints: user discovery opt-in; AST sandbox (not OS sandbox)
  Browser: CSRF on login + HTML mutators; prod CSP (self + unsafe-inline)
```

---

## 1. API Bearer → `token:` principals (REST)

| Item | Detail |
|---|---|
| Secrets | `API_AUTH_TOKEN` (primary) / legacy `SWARM_API_KEY`; multi-key `API_AUTH_TOKENS` / `SWARM_API_KEYS` (CSV). |
| Wire format | `Authorization: Bearer <token>` or `X-API-Key: <token>`. |
| Auth class | `StaticTokenAuthentication` — constant-time compare against all accepted keys; returns `(AnonymousUser, provided_token)` so `request.auth` is the presenting credential. |
| Permission | When auth is on: `HasValidTokenOrSession` (Bearer **or** Django session). |
| Principal | `token:<first-24-hex-of-sha256(token)>` via `token_principal` / `request_principal`. Each multi-key secret is a **distinct** owner. |
| Enablement | Django setting `ENABLE_API_AUTH` is **derived** from whether any token is configured at startup — not a standalone env toggle. Production (`DEBUG=False`) refuses to boot without a token unless `SWARM_ALLOW_NO_AUTH=true`. |

### REST IDOR on `/v1/responses`

Stored responses carry an `owner` stamp. With `ENABLE_API_AUTH` on:

- `GET` / cancel / `DELETE` call `_assert_owner_access` → `responses_store.owner_allows(record, principal)`.
- Access requires **exact** principal match (`user:…` or `token:…`).
- Legacy/unowned records are **fail-closed** (denied) when auth is on.
- When auth is off (local debug / `SWARM_ALLOW_NO_AUTH`), ownership checks are skipped.

Session users who hit REST with a cookie get `user:<username>` and the same strict IDOR — they do **not** automatically see other users' or token-stamped responses via `/v1/responses/{id}`.

---

## 2. Django session → operator pages & websocket chat

| Surface | Gate |
|---|---|
| Teams admin / export, blueprint library (browse + mutators), settings, Session Explorer, agent/team creator **mutators** | `@login_required` |
| Public without session | Landing SPA, `/teams/launch/`, `/profiles/`, agent-creator **GET**, login form |
| Websocket chat `ws/ai-demo/<conversation_id>/` | Django **session cookie** via `AuthMiddlewareStack` only |

Anonymous websocket connects are **accept-then-close** with code **4401** (`WS_AUTH_REQUIRED_CODE`) and reason `authentication required`, so the SPA can show a Sign-in CTA instead of an opaque failure.

Login: `/login/` and `/accounts/login/` → `custom_login`. POST is **not** CSRF-exempt; `next` is open-redirect hardened (rooted relative paths only).

---

## 3. Bearer does **not** auth websockets

The Settings-page / `.env` API token authenticates **HTTP REST** only.

- Presenting `Authorization: Bearer …` on the websocket upgrade does nothing useful for `DjangoChatConsumer`.
- Chat needs a form-login session cookie on the same origin.
- See [websocket_chat.md](./websocket_chat.md) for Connected vs 4401 vs unreachable badges.

---

## 4. Session Explorer operator bridge

UI: `/sessions/`, `/sessions/<id>/`, `/api/sessions/` — all `@login_required`.

With `ENABLE_API_AUTH` on, `explorer_owner_allows` lets a logged-in Django operator see:

1. Rows owned by their `user:<username>` principal, **and**
2. Rows stamped with any **currently configured** API-token principal (`token:<sha256-prefix>`), so curl/Bearer-created sessions are visible in the browser.

Foreign `user:…` owners and unowned legacy rows stay hidden in the Explorer.  
**REST `/v1/responses` IDOR is unchanged** — still same-principal only. The bridge is observability for operators, not a privilege escalation on the API.

When API auth is off, the Explorer aligns with open REST (does not fail-closed-hide everything).

---

## 5. Workdir confinement

Per-request `params.workdir` / `params.cwd` (hybrid MoA, MoA orchestrator, CLI fusion consumers) and `swarm-cli moa --workdir` / `--cwd`:

- Resolve under `SWARM_WORKSPACES_DIR` (default XDG `…/swarm/workspaces`).
- Relative paths are fine; **absolute paths outside the root are rejected**.
- Escape hatch: `ALLOW_UNRESTRICTED_WORKDIR=true` — for local CLI power users only; **keep off on API servers**.
- Unset write workdirs get a per-run temp directory under that root.

---

## 6. User blueprint discovery + AST sandbox

| Control | Default | Meaning |
|---|---|---|
| `SWARM_ALLOW_USER_BLUEPRINT_DISCOVERY` | **off** | Creator saves write under the user blueprints dir; **discovery / `exec_module` of that tree is opt-in**. |
| `SWARM_BLUEPRINT_PATHS` | unset | Extra roots (os.pathsep-separated) always eligible for scan; bundled names win on collision. |
| `SWARM_USER_BLUEPRINT_SANDBOX` | **on** | AST + banned-snippet gate (`blueprint_sandbox.py`) before loading user/community roots and on creator validate/save. |

Important trust bound: this is a **static AST filter**, **not an OS sandbox**. It blocks obvious escapes (`subprocess`, write-mode `open` / `Path.open`, selected network clients, reflection helpers, …). Bundled blueprints under `src/swarm/blueprints` are trusted and skip the gate. Running third-party blueprint code remains a code-execution trust decision.

---

## 7. CSRF, cookies, headers (prod CSP)

| Control | Behavior |
|---|---|
| CSRF | Required on `custom_login` POST and HTML mutators (blueprint library, etc.). Token-auth REST views remain CSRF-exempt (Bearer clients have no cookie CSRF cycle). |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Must include scheme+host(+port) for every UI origin (LAN/proxy too). |
| Secure cookies | When `DEBUG=False`, `SESSION_COOKIE_SECURE` / `CSRF_COOKIE_SECURE` default on; opt out with `SWARM_SECURE_COOKIES=false` for HTTP staging. |
| Always-on headers | `X-Content-Type-Options: nosniff`, `X-Frame-Options` (default `DENY`; prod may override via `DJANGO_X_FRAME_OPTIONS`). |
| **CSP** | When `DEBUG=False`, `ContentSecurityPolicyMiddleware` sets `Content-Security-Policy` from `CONTENT_SECURITY_POLICY` (opt out with `SWARM_CSP=false`). Policy is self-centric: `default-src 'self'`, `object-src 'none'`, `frame-ancestors 'none'`, `form-action 'self'`, `font-src 'self'`, `img-src 'self' data: blob:`, `connect-src 'self' ws: wss:` (websocket chat). **No CDN hosts.** Operator UI assets (Bootstrap, Prism, Font Awesome, marked) are vendored under `src/swarm/static/contrib/` and loaded via `{% static %}`. |

### Residual inline needs

Django operator templates still ship **inline `<script>` blocks** (creators, library, teams, sessions) and many **`style=""` attributes**. Until those move to external JS/CSS, prod CSP keeps `script-src 'self' 'unsafe-inline'` and `style-src 'self' 'unsafe-inline'`. That blocks third-party script/style hosts while remaining compatible with the current templates. Prefer extracting inline scripts over adding more `'unsafe-*'` directives.

**Extraction started:** `settings_dashboard.html` page logic now lives in `static/js/settings_dashboard.js` (loaded via `{% static %}`); server data stays in a `json_script` island. Other operator pages and inline `style=""` remain; CSP policy is unchanged until more pages are extracted.

---

## Quick operator checklist

1. Production: set `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, and `API_AUTH_TOKEN` (or multi-key vars).
2. Point OpenAI clients at `/v1` with `Authorization: Bearer $API_AUTH_TOKEN`.
3. Sign in at `/login/` for WebUI, Session Explorer, and websocket chat (session ≠ API token).
4. Keep `ALLOW_UNRESTRICTED_WORKDIR` and `SWARM_ALLOW_USER_BLUEPRINT_DISCOVERY` off unless you intentionally widen trust.
5. Expect prod CSP (`self` + residual `'unsafe-inline'`); rely on CSRF + frame/nosniff + auth gates above. Use `SWARM_CSP=false` only to disable the header.
