# REQ-79 — Survival — CLI/API chat works; prove open-swarm can update itself

https://github.com/matthewhand/open-swarm/issues/424

## Intent

Ensure open-swarm can sustain autonomous self-development without external Grok CoS dependency:
1. **API chat:** From the SPA, select/create an API agent, send a message, get a streamed reply. Reload keeps the thread. No crash if tools are unused.
2. **CLI chat:** From the SPA, select a catalogued CLI agent, send, get a reply. Second send resumes the stored session ID (REQ-52 / #369 / PR 402). If the CLI cannot resume, a bubble-less honest line says a new session started — never a fake restore.
3. **Self-update prove:** From working chat, an in-app autonomous agent opens a real Pull Request on `matthewhand/open-swarm` to prove end-to-end self-modification and contribution capability.
4. **Live SPA hydration:** Live SPA must hydrate cleanly without empty `#root` or hung assets.
