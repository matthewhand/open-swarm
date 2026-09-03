// Pinokio install — README API quickstart is `docker compose up`.
// Build the image here; start.js brings the stack up. No secrets, no host
// home paths, no pinokio.computer network.

module.exports = {
  run: [
    {
      method: "shell.run",
      params: {
        message: [
          "test -f .env || cp .env.example .env",
          "docker compose build",
          "mkdir -p .pinokio && printf 'installed\\n' > .pinokio/installed",
        ],
      },
    },
  ],
}
