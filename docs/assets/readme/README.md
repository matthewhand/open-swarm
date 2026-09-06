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
| `cli.gif` | #456 | Reserved — CLI kind (e.g. OpenCode / Antigravity / grok). |
| `api.gif` | #456 | Reserved — API / true-inference seat. |
| `remotes.gif` | #456 | Reserved — Hermes / OpenMousBot / Rakazo (label OpenMousBot, not OMB). |
| `combined.gif` | #456 | Reserved — team that mixes CLI + API + remote. May reuse `announce-bridge.gif`. |

Reserved names are the contract. Do not invent placeholder pixels for
#456 in this PR.

## Render (storyboard)

```bash
uv run --with pillow python scripts/render_announce_gif.py
```

Live recapture steps: [docs/ANNOUNCE.md](../../ANNOUNCE.md#recording-checklist).
