// Pinokio start — `docker compose up` (README API quickstart), web UI :8000.
// REQ-45: compose with home mapped is sandbox-home (not bare-metal).
// Values only — no real host paths, usernames, or secrets.

module.exports = {
  daemon: true,
  run: [
    {
      method: "shell.run",
      params: {
        env: {
          SWARM_RUNTIME: "sandbox-home",
          ENABLE_WEBUI: "true",
          DJANGO_DEBUG: "true",
          DJANGO_ALLOWED_HOSTS: "localhost,127.0.0.1",
        },
        message: "docker compose up",
        on: [
          {
            event: "/(Uvicorn running|Application startup complete|http:\\/\\/[0-9.:]+)/i",
            done: true,
          },
        ],
      },
    },
    {
      method: "local.set",
      params: {
        url: "http://127.0.0.1:8000",
      },
    },
  ],
}
