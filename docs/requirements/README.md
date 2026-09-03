# Open Swarm REQ backlog

> **This is docs-only.** These pages transcribe the tracked REQ backlog. They
> do not implement features, do not enable Neon, and do not resume oracle.

One markdown file per REQ (REQ-18/25 is one combined page). Do not invent
extra REQs here — only items already tracked in the product chat.

## Template

Every REQ page uses this shape:

| Section | What it holds |
|---|---|
| **Status** | PR number / merged / in flight |
| **Intent** | Why this exists |
| **Success** | What “done” looks like |
| **Constraints** | What must not happen |
| **Owner** | Who does what |

## Owner (same on every REQ)

- **CoS** transcribes
- **cloud** implements
- **engineer** GitHub-merge after skeptic
- **live preview** `10.0.0.30:8001` — guest dirty only

## Honesty (read before acting)

| Claim | Reality on this starting tree (`91dabd64`) |
|---|---|
| Teams | **Live today are LLM-profile aliases** (`/teams/` + `/v1/teams` + `teams.json`). Not a multi-agent roster. Intended composition is a later REQ. |
| Grok-Bot chrome | **Not on `:8001` yet.** REQ-5 dark chrome ≠ the left-rail Bot product (REQ-16). |
| Neon / oracle | **Off.** Do not enable Neon. Do not resume oracle. |

In-flight PRs sit on their own branches. This tree does not include their code.

## Index

| REQ | Title | Status |
|---|---|---|
| [REQ-7](./REQ-7.md) | Support agent (pill, threads, question cards) | PR 313 — in flight |
| [REQ-8](./REQ-8.md) | UX tighten (theme icon, unlabeled dropdowns, toast, hide popup) | PR 312 — in flight |
| [REQ-9](./REQ-9.md) | gate + skeptic roles as-tool | PR 314 — in flight |
| [REQ-10](./REQ-10.md) | Favourites tile grid (left rail, not top chrome) | PR 311 — in flight (wrong place) |
| [REQ-11](./REQ-11.md) | Remotes Hermes / OMB / Rakazo | PR 318 — in flight |
| [REQ-12](./REQ-12.md) | Harness-of-harnesses docs | PR 315 — in flight |
| [REQ-13](./REQ-13.md) | Mock inference fast + >60s | PR 317 — in flight |
| [REQ-14](./REQ-14.md) | Chat JSON persist + Settings retention | PR 319 **merged** `4d554ea5` |
| [REQ-15](./REQ-15.md) | CLI dropdown lists CLIs | PR 316 — in flight |
| [REQ-16](./REQ-16.md) | Grok-Bot left rail chrome | PR 322 — in flight |
| [REQ-17](./REQ-17.md) | Search command palette | inside PR 322 — in flight |
| [REQ-18/25](./REQ-18-25.md) | Support Socratic+MCQ (into 313); hover-edit role → blueprint Python | absorbed / in flight |
| [REQ-19](./REQ-19.md) | DaisyUI settings sheet `modal-end` + Menu + Join | PR 320 — in flight |
| [REQ-20](./REQ-20.md) | Teams composition roster DnD (not LLM aliases) | PR 323 — in flight |
| [REQ-21](./REQ-21.md) | Herdr client localhost default + optional `--remote` | in flight |
| [REQ-23](./REQ-23.md) | Teams in sidepane + send-to-all dropdown | in flight |
| [REQ-24](./REQ-24.md) | Drag any agent incl. roles into Hidden drop zone | in flight |
| [REQ-26](./REQ-26.md) | First load hide gate and skeptic | in flight |
| [REQ-28](./REQ-28.md) | Chief of Staff + team isolation + teams-of-teams | this PR |
| [REQ-37](./REQ-37.md) | Nested conversation compact / summaries | in flight (#350) |

REQ-22 (debt audits) and earlier REQ-5 / REQ-6 chrome/avatar work are **not**
filed here — they were not in this backlog slice.
