# Follow-up issue draft — live README GIF capture

**Deviation:** The REQ-97 implementer (Cursor cloud, 2026-09-06) could not
open a GitHub Issue (`gh` is read-only on this agent) and could not film
`:8001` / Firefox (task constraint). File this body as a new Issue after
#456 merges. Do not close #456 against live pixels — that Issue is the
slot + poster + checklist pass.

**Suggested title:** `REQ-97 follow-up: capture live README GIFs (CLI / API / OpenMousBot / combined team)`

**Labels:** `docs`, `near-release` (if those exist).

---

## Intent

Replace the four poster SVGs under `docs/assets/readme/` with short secret-free
loops so the README differentiator is obvious in motion.

Parent: [#456](https://github.com/matthewhand/open-swarm/issues/456) (REQ-97).
Slots and checklist already landed. This Issue is **pixels only**.

Not the announce hero — that remains [#529](https://github.com/matthewhand/open-swarm/issues/529).

## Success

1. Four live captures land at the same stems:
   `cli-agents`, `api-agents`, `remote-agents`, `combined-team`
   as small GIFs (or muted mp4 + GIF fallback) under `docs/assets/readme/`.
2. README `<img>` src points at the live files; SVGs stay as posters/fallback.
3. User copy labels **OpenMousBot** (never OMB). Combined team shows
   CLI + API + remote in one handoff / agent-as-tool flow.
4. No secrets, no house-identifying stills, no live LAN IPs in any frame.
5. [RECORDING.md](./RECORDING.md) checklist followed (clean `:8000` Compose
   preview, Demo Mode A names, `scripts/seed_demo_agents.py`, no Neon, no
   Firefox `:8001`).
6. `tests/unit/test_req97_readme_demos.py` still passes. SCREENSHOTS.md dates
   updated.

## Constraints

- GitHub-only. No Neon. No Taskmaster ping unless asked.
- Do not film Matthew’s private chats or the FF `:8001` box.
- Coordinate with #453 before committing large binaries if history is sensitive.
- Own-diff: media + README src + registry dates + the existing path-contract test.

## Owner

Engineer with a clean local preview. Skeptic: links + no secrets in frames
(text-only PASS/FAIL).
