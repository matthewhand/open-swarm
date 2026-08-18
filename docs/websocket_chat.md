# Websocket chat (ASGI / Django Channels)

The chat UI (Django `templates/chat.html` and the SPA ChatPage) streams over a
websocket at:

```
ws(s)://<host>/ws/ai-demo/<conversation_id>/
```

## Wiring

- `src/swarm/asgi.py` — `application` (referenced by
  `settings.ASGI_APPLICATION`): `ProtocolTypeRouter` with `http` → the normal
  Django ASGI app, and `websocket` →
  `AllowedHostsOriginValidator(AuthMiddlewareStack(URLRouter(...)))`.
- `src/swarm/routing.py` — `websocket_urlpatterns` mapping
  `ws/ai-demo/<conversation_id>/` to `swarm.consumers.DjangoChatConsumer`.
- `settings.py` — `daphne` (first, so `manage.py runserver` serves ASGI
  including websockets) and `channels` are in `INSTALLED_APPS`. Both are core
  dependencies in `pyproject.toml`, no extra needed.

## Running

Any of these serve both HTTP and the websocket route:

```bash
python manage.py runserver                      # dev (daphne integration)
daphne -b 0.0.0.0 -p 8000 swarm.asgi:application
uvicorn swarm.asgi:application
```

Notes:

- Connections require an **authenticated Django session cookie** (via
  `AuthMiddlewareStack`). A Settings-page API **bearer token does not**
  authenticate the websocket. Anonymous connects are accept-then-closed
  with close code **4401** (`WS_AUTH_REQUIRED_CODE`) and reason
  `authentication required` so the SPA can show a Sign-in CTA instead of
  an opaque failure. `receive()` re-checks auth so a frame that races the
  close cannot append to a transcript or invoke a blueprint/LLM.
- `Origin` must match `ALLOWED_HOSTS` (AllowedHostsOriginValidator).
- The consumer streams completions from `OPENAI_API_KEY` / `OPENAI_MODEL`
  (optionally `LITELLM_BASE_URL`/`OPENAI_BASE_URL`).
- Frames are HTMx-style HTML partials (`websocket_partials/*.html`); the SPA
  parses the same frames.
- No channel layer is required (the consumer never uses group sends), so
  `CHANNEL_LAYERS`/`channels-redis` configuration is unnecessary for chat.

### Connected vs Unavailable (journey / SPA)

| Badge | Typical cause |
| --- | --- |
| **Connected** | Valid session cookie + ASGI serving `/ws/` |
| **Unavailable — sign in required** | Close code 4401 (no Django session) |
| **Unavailable — websocket unreachable** | Socket never opened (ASGI down, wrong host, origin denied) |

Journey capture (`scripts/capture_user_journey.py`) logs in as `journey-admin`
before `/chat`, then waits for the connection-status badge so a healthy regen
of `spa-chat.png` shows **Connected**. The **checked-in** desktop/mobile frames
may still show **Connecting…** if the wait raced; see [SCREENSHOTS.md](./SCREENSHOTS.md).

Tests: `tests/test_asgi_routing.py` (full-stack routing/auth/round-trip) and
`tests/test_consumers.py` (consumer unit tests).
