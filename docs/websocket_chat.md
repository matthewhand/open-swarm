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

- Connections require an **authenticated Django session** (the consumer
  closes anonymous connections) and an `Origin` header matching
  `ALLOWED_HOSTS`.
- The consumer streams completions using the configured gateway
  (`LITELLM_BASE_URL`) with `LITELLM_API_KEY` / `OPENAI_MODEL`
  (`OPENAI_API_KEY`/`OPENAI_BASE_URL` are honoured as a fallback).
- Frames are HTMx-style HTML partials (`websocket_partials/*.html`); the SPA
  parses the same frames.
- No channel layer is required (the consumer never uses group sends), so
  `CHANNEL_LAYERS`/`channels-redis` configuration is unnecessary for chat.

Tests: `tests/test_asgi_routing.py` (full-stack routing/auth/round-trip) and
`tests/test_consumers.py` (consumer unit tests).
