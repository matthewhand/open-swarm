// Pinokio install — README API quickstart is `docker compose up`.
// Build the image here; start.js brings the stack up. No secrets and no
// host home paths in this script.

module.exports = {
  run: [
    {
      method: "shell.run",
      params: {
        message: [
          "test -f .env || cp .env.example .env",
          "test -f swarm_config.json || cp swarm_config.example.json swarm_config.json",
          "docker compose build",
          "mkdir -p .pinokio && printf 'installed\\n' > .pinokio/installed",
        ],
      },
    },
  ],
}
