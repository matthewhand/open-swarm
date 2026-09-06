# README / announce media (`docs/assets/readme/`)

**Decided path** for README and announce clips. Issue SoT:

- Hero / fanfare (15–30s): [REQ-136 #529](https://github.com/matthewhand/open-swarm/issues/529) → [docs/ANNOUNCE.md](../../ANNOUNCE.md)
- Broader near-release kit: [REQ-97 #456](https://github.com/matthewhand/open-swarm/issues/456)

Prefer small GIFs (or muted mp4 with a GIF fallback). No secrets, no
house-identifying stills, no live LAN IPs in frames.

Historical CLI+API terminal loop stays at
[`docs/demo/cli-and-api.gif`](../../demo/cli-and-api.gif). Do not put new
README heroes there.

## Slots

| File | Owner | Status |
|---|---|---|
| [`announce-bridge.gif`](./announce-bridge.gif) | #529 | Storyboard hero (spiel captions). Live recapture later. |
| [`announce-bridge.meta.json`](./announce-bridge.meta.json) | #529 | Duration + caption lock. |
| [`cli-agents.svg`](./cli-agents.svg) | #456 | Poster — CLI agents (Grok / OpenCode / agy). GIF pending. |
| [`api-agents.svg`](./api-agents.svg) | #456 | Poster — API agents (OpenAI-compat / owned thread). GIF pending. |
| [`remote-agents.svg`](./remote-agents.svg) | #456 | Poster — Remote agents (**OpenMousBot**, never OMB). GIF pending. |
| [`combined-team.svg`](./combined-team.svg) | #456 | Poster — Combined team (CLI + API + remote). GIF pending. |
| `cli.gif` | #456 | Reserved — live CLI GIF (e.g. OpenCode / Antigravity / grok). |
| `api.gif` | #456 | Reserved — API / true-inference seat. |
| `remotes.gif` | #456 | Reserved — Hermes / OpenMousBot / Rakazo (label OpenMousBot, not OMB). |
| `combined.gif` | #456 | Reserved — team that mixes CLI + API + remote. May reuse `announce-bridge.gif`. |

REQ-97 ships **posters now** (SVG). Live GIFs use the reserved
`cli.gif` / `api.gif` / `remotes.gif` / `combined.gif` names when
[RECORDING.md](./RECORDING.md) is executed. Keep each SVG as a
poster/fallback and point README at the GIF.

Reserved GIF names are the live-capture contract. Do not invent
placeholder pixels for those four GIF stems.

Follow-up Issue body (not filed from the cloud agent): [FOLLOWUP_ISSUE.md](./FOLLOWUP_ISSUE.md).

## Render (storyboard)

```bash
uv run --with pillow python scripts/render_announce_gif.py
```

Live recapture steps: [docs/ANNOUNCE.md](../../ANNOUNCE.md#recording-checklist).
