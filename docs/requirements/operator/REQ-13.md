# REQ-13

Intent: in development, LAN (and loopback) clients use the operator UI and chat websockets without a login form.

Success:
1. When `DJANGO_DEBUG=true` and the client IP is loopback or RFC1918/link-local, HTTP auto-logs the `swarm-anon-preview` user (session cookie).
2. The same rule applies to `ws/ai-demo/<id>/`: no 4401 close for those clients; `receive()` mints the preview user if the handshake had no session yet.
3. Debug `ALLOWED_HOSTS` default includes `*` so a phone hitting `http://10.x.x.x:8001` is not `DisallowedHost`, and Channels Origin checks allow that host.
4. Production (`DEBUG=False`) still requires login / 4401 unless `SWARM_ALLOW_ANONYMOUS=1`.
5. Pytest stays gated (no implicit LAN auto-login). `SWARM_ALLOW_ANONYMOUS=0` forces login even in debug.

Constraints: Do not trust `X-Forwarded-For` for this gate. Do not enable WAN IPs in debug. Bearer still does not auth websockets.

Owner: open-swarm engineer.
