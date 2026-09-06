# README demo recording checklist (REQ-97 / #456)

**Intent:** Replace the four poster SVGs in this folder with short, secret-free
loops that show CLI / API / remote / combined-team in the Grok-like WebUI.

This cloud pass **did not film**. Constraints: no Firefox against `:8001`, no
Neon, no live LAN. Posters are wired so the README slots exist today.

**Follow-up:** file the issue body in [FOLLOWUP_ISSUE.md](./FOLLOWUP_ISSUE.md)
(this agent cannot open GitHub issues — `gh` is read-only). Distinct from the
announce hero clip ([#529](https://github.com/matthewhand/open-swarm/issues/529)).

---

## Target files (overwrite posters; keep the same stems)

| Stem | Caption (user copy) | Poster today | Live capture target |
|---|---|---|---|
| `cli-agents` | CLI agents | `cli-agents.svg` | `cli-agents.gif` (or muted `.mp4` + this GIF fallback) |
| `api-agents` | API agents | `api-agents.svg` | `api-agents.gif` |
| `remote-agents` | Remote agents (**OpenMousBot**, never OMB) | `remote-agents.svg` | `remote-agents.gif` |
| `combined-team` | Combined team (CLI + API + remote) | `combined-team.svg` | `combined-team.gif` |

Keep each SVG as a poster / first-frame fallback after the GIF lands. README
embeds the path that exists; tests lock the four stems.

Prefer **small GIFs** (or muted mp4 + GIF fallback). Aim ≤ 2 MB each, 8–15 s,
looping, no audio.

---

## Machine (clean demo / local preview)

1. Fresh clone of `main` (or the release branch). Not Matthew’s day-to-day box.
2. **Do not** film the Firefox `:8001` operator box. **Do not** use Neon.
3. Local Compose on **`:8000`** (see root README WebUI steps):

   ```bash
   uv sync --all-extras
   cp .env.example .env
   # set OPENAI_API_KEY, API_AUTH_TOKEN, DJANGO_SECRET_KEY — never show these
   cp swarm_config.example.json swarm_config.json
   make frontend
   docker compose up --build
   # open http://localhost:8000
   ```

4. Seed **Demo** rosters only (additive; no day-to-day rename):

   ```bash
   uv run python scripts/seed_demo_agents.py --reset
   ```

   Names: [SHOWOFF_DEMO_AGENTS.md](../../SHOWOFF_DEMO_AGENTS.md) **Mode A** on
   harness rows (`Grok CLI`, `LiteLLM API`, `Hermes Remote`,
   **`OpenMousBot Remote`**). Combined clip uses
   [`demo-bridge.json`](../../examples/openai-agents-handoff-graphs/demo-bridge.json)
   (Chief of Staff + Grok CLI + Hermes Remote) **or** a Mode A roster that
   visibly includes an API seat plus OpenMousBot. Do not invent live hosts.

5. Place remotes from **placeholders** (`placeholder:remote:omb` /
   `placeholder:remote:hermes`). If a real OpenMousBot / Hermes is required
   for motion, use a **lab** instance whose Settings URL is a dummy host
   (`https://example.invalid` or `http://localhost:9xxx`) — never a house LAN
   (`10.x`, `192.168.x`, `172.16–31.x`).

6. Prefer scripted / mock inference where it still looks honest ([#317](https://github.com/matthewhand/open-swarm/issues/317)).
   `SWARM_TEST_MODE=1` is fine for CLI-only beats. Do not paste private chats.

---

## Viewport and chrome

- Desktop **1280×800** (same as `scripts/capture_user_journey.py`).
- Product chrome only: left rail + selected chat (`/` or `/chat`).
- Rebuild `webui/frontend/dist/` so `/` is the Grok SPA, not Django fallback.
- Hide OS dock / personal wallpaper. No house windows, family photos, or
  identifiable street/room stills.
- Before record: Settings sheet closed; no token fields visible; no `.env`
  buffer; no `sk-` / `ghp_` / `github_pat_` in any pixel.

---

## Four beats (script)

Film **four separate clips**. Do not use `swarm-cli moa --team` as the team
story. Do not call `/v1/teams` aliases a Team.

### 1. CLI agents (`cli-agents`)

1. Rail: select **Grok CLI** (or OpenCode / Antigravity CLI if that binary is
   the one on PATH).
2. Send: `What CLIs can you see?`
3. Show the native CLI session in chat (kind-clear name in the header).
4. Optional 2 s: hover the other CLI rows (`OpenCode CLI`, `Antigravity CLI`).

### 2. API agents (`api-agents`)

1. Rail: select **LiteLLM API** (Mode A). Honest mid-flight: if the seat is
   still a leftover blueprint recipe, the caption must say so — do not imply a
   finished “wire this endpoint” seat ([#652](https://github.com/matthewhand/open-swarm/issues/652)).
2. Send a one-line ping. Show the owned thread (editable), not a remote lock.
3. Optional 2 s: a terminal *off to the side is not required*; stay in WebUI.

### 3. Remote agents (`remote-agents`) — label **OpenMousBot**

1. Settings → Remotes (or rail) → **OpenMousBot Remote**.
2. User-facing chrome must say **OpenMousBot**, never `OMB`.
3. List / open a session on that remote. Hermes / Rakazo may appear as other
   rows; the filmed seat is OpenMousBot.
4. No live LAN IP in the URL bar, Settings fields, or chat.

### 4. Combined team (`combined-team`)

1. Rail: **Demo Bridge** (or a Demo team whose roster shows CLI + API + remote).
2. Send one prompt that forces a **handoff** or **agent-as-tool** beat
   (Chief of Staff routes; Grok CLI native; API seat; OpenMousBot or Hermes
   remote).
3. The clip must make the mix obvious: three kinds in one flow.
4. Do **not** film MoA consensus-then-team as this slot.

---

## Encode and drop-in

```bash
# Example: ffmpeg from a raw capture (adjust input name)
ffmpeg -i raw-cli.mov -an -vf "fps=12,scale=640:-1:flags=lanczos" \
  -loop 0 docs/assets/readme/cli-agents.gif
```

- Mute (`-an`). No system audio.
- Scale to ~640 px wide so GitHub README stays compact.
- Scrub every frame: no secrets, no house stills, no live LAN IPs, no `OMB`
  as a user-facing label.
- Update [SCREENSHOTS.md](../../SCREENSHOTS.md) Captured date + Status
  `current` for each stem.
- Swap README `<img>` `src` from `.svg` to `.gif` (keep SVG as
  `poster` / fallback in the figure if you add muted mp4).
- Re-run `uv run pytest tests/unit/test_req97_readme_demos.py`.

---

## Out of scope

- [#529](https://github.com/matthewhand/open-swarm/issues/529) 15–30 s launch
  montage (separate hero).
- Recapturing `docs/screenshots/` journey PNGs / golden-journey.
- Filming Pinokio Discover (Open Swarm is sideload-only).
- Committing production chats or Matthew’s private threads.
