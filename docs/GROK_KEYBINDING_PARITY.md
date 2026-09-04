# Grok Bot keybinding parity map

- **Status:** Research (look-only; no runtime change in this PR)
- **Date:** 2026-09-04
- **Issue:** [#552](https://github.com/matthewhand/open-swarm/issues/552) (REQ-150)
- **Related:** [#547](https://github.com/matthewhand/open-swarm/issues/547) (REQ-147 discoverable tips + ⌘K search), [#492](https://github.com/matthewhand/open-swarm/issues/492) (search size)
- **Snapshot:** `origin/main` @ `f6be01cd` (2026-09-04)
- **Supersedes:** none. Complements [ADR-001](./ADR-001-primary-ui.md) (chrome) and [REQ-16 / REQ-17](./archive/requirements/REQ-16.md) (Grok-Bot rail + Search palette).

**Decision for implementers:** stay consistent with **Grok Bot desktop** (xAI / Cursor Grok Bot app) where a binding is documented or owner-verified. Do not invent a second primary launcher. Expand only with chords Grok does not use (Alt/⌥ first). First implement ticket is [#547](https://github.com/matthewhand/open-swarm/issues/547): **⌘K / Ctrl+K opens the main Search palette**.

This document is **feasibility-first**. It records what Grok Bot uses (with sources and uncertainty) and what open-swarm binds today. It does **not** change runtime behaviour.

No secrets are documented here.

---

## 1. Scope and products (do not mix)

Open-swarm’s product chrome is **Grok-Bot**: left rail + selected-agent chat (`App.tsx`, [FEATURE_STATUS.md](../FEATURE_STATUS.md), archived [REQ-16](./archive/requirements/REQ-16.md)). The parity target is that desktop chat UI, not every product named “Grok”.

| Product | What it is | Use for this map |
|---------|------------|------------------|
| **Grok Bot desktop** (macOS / Windows / Linux) | Named-bot messenger: sidebar, Search / command palette, composer, Settings, Agent Computer. Official docs live under [docs.x.ai/grok-bot](https://docs.x.ai/grok-bot). | **Parity target.** |
| **Grok Build TUI** (`grok` CLI) | Terminal coding agent. Shortcuts at [docs.x.ai/build/keyboard-shortcuts](https://docs.x.ai/build/keyboard-shortcuts). | **Out of scope.** Do not copy TUI chords (`Ctrl+P`, `Ctrl+\`, `Ctrl+B` = background, …) into the SPA. |
| **grok.com / Grok chat** | Single-assistant web chat. | Not the Bot rail product. No public shortcut list found. |
| **Unofficial Electron wrappers** | e.g. AnRkey/Grok-Desktop (tabs), krakenunbound/grok-desktop (`Ctrl+K` focuses a sidebar filter). | Not xAI. Cite only as contrast. |
| **open-swarm Agent Router** (`/agents`) | Separate chrome. Nested `AgentSidebar` still binds **Ctrl/⌘+B** and bare `/`. | Not Grok-Bot chrome. Do not promote those chords onto `/` + `/chat` without a Grok source. |

x.ai/bot itself was not reachable from this research environment (Cloudflare block). Bindings below come from official docs, owner verification, community demos, and this repo’s Grok-clone chrome.

---

## 2. Status and confidence

**Status** (open-swarm vs Grok Bot meaning):

| Status | Meaning |
|--------|---------|
| `match` | Same chord, same meaning, already wired on Grok-Bot chrome (`/` + `/chat`). |
| `gap` | Grok Bot uses this chord (or owner-verified equivalent); open-swarm does not, or binds it to the **wrong** surface. |
| `n/a` | No Grok Bot binding found, or open-swarm has no equivalent surface. |
| `expand` | Recommended **open-swarm-only** chord that does not collide with documented / owner-verified Grok chords. |

**Confidence** that Grok Bot actually uses the chord:

| Confidence | Meaning |
|------------|---------|
| **High** | Official Grok Bot docs, or product-owner statement plus independent corroboration. |
| **Medium** | Official docs describe the *action* but not the chord; or a public demo / chrome-clone REQ matches. |
| **Low** | Single unofficial write-up. Treat as tentative until someone re-checks the live app. |

---

## 3. Parity table

Chords are written `Ctrl+…` / `⌘…`. Windows and Linux use Control; macOS uses Command unless a row says otherwise.

| Grok binding | Meaning | open-swarm status | Notes / source |
|--------------|---------|-------------------|----------------|
| **⌘K / Ctrl+K** | Open **Search / command palette** (switch Bots, find messages / files / links / routines, open settings and actions) | **gap** | **Must match.** Owner (Matthew, [#547](https://github.com/matthewhand/open-swarm/issues/547)): “In Grok Bot UI, Ctrl+K / ⌘K opens search agents.” Official docs name the palette but **do not print the chord** ([chat-and-collaboration](https://docs.x.ai/grok-bot/chat-and-collaboration)). Community demo: Command+K jumps to a named Bot and tabs across Messages / Routines / Groups ([YouTube walkthrough](https://www.youtube.com/watch?v=XgkW4A6lrDY), transcript via youtube-distilled). **Today:** `experimental/CommandPalette.tsx` steals ⌘K/Ctrl+K (default **ON**) for leftover operator IA (Home / Blueprints / Teams…). Product `SearchPalette` opens only via rail click / `swarm:open-search` — **no global chord**. Confidence: **High** (owner + demo); official chord **unprinted**. |
| **⌘N / Ctrl+N** | Sidebar **New** → New chat → **Create new agent** (also the New-chat entry for groups) | **gap** | Official: [Create and manage Bots](https://docs.x.ai/grok-bot/bots). Repeated in [Cursor Grok Bot docs](https://cursor.com/docs/grok-bot/work) and [DataCamp tutorial](https://www.datacamp.com/tutorial/grok-bot-tutorial). open-swarm has no New-agent chord on the Grok rail. Confidence: **High**. |
| **⌘, / Ctrl+,** | Open **Settings** | **gap** | Official: [Settings and notifications](https://docs.x.ai/grok-bot/settings-and-notifications). Community: “sidebar account button, Cmd+,, or the command palette item Open settings” ([dennisyu.com playbook](https://dennisyu.com/how-i-use-grok-bot/)). open-swarm Settings is the gear / `swarm:open-settings` sheet only. Confidence: **High**. |
| **Search / command palette** (open) | Switch Bots & groups; find messages, files, links, routines; open settings and common actions; jump to a hit in a conversation | **match** (surface) / **gap** (launcher) | Official: [Find prior work](https://docs.x.ai/grok-bot/chat-and-collaboration). open-swarm `SearchPalette` clones the same tabs: All · Messages · Bots · Groups · Files · Links · Routines · Actions ([REQ-17](./archive/requirements/REQ-17.md), `SEARCH_PALETTE_TABS`). Messages / Files / Links / Routines rows are still mostly empty chrome. Confidence: **High** that the *palette* is the Grok object; **High** that ⌘K should open it (row above). |
| **⌃1 … ⌃9** (palette open) | Choose visible result row *N* | **match** | In-repo Grok-clone contract: “Rows: icon + name + one-line desc + ⌃N” ([REQ-17](./archive/requirements/REQ-17.md)). Implemented in `SearchPalette.tsx` (`Ctrl+1`…`9`; `SessionPicker.tsx` same). Official docs do **not** list this chord. Confidence: **Medium** (clone + tests; not printed by xAI). |
| **↑ / ↓**, **Enter**, **Esc** (palette open) | Move highlight; choose; close (click-outside also closes) | **match** | Same REQ-17 contract; wired in `SearchPalette.tsx`. YouTube demo uses Enter after Command+K. Confidence: **Medium**. |
| **`/` in composer** | Reference a **saved skill** (`/` menu) | **gap** | Official: [Skills and routines](https://docs.x.ai/grok-bot/skills-routines-and-automations), [computer-and-apps](https://docs.x.ai/grok-bot/computer-and-apps). open-swarm Grok composer is a single-line `<input>` with no slash menu. **Do not** reuse leftover Agent Router “bare `/` opens search when not in an input” (`AgentSidebar/AgentSidebar.tsx`) — that collides with Grok’s composer `/`. Confidence: **High**. |
| **`@` in composer** | Mention a Bot, group, routine, or connector | **gap** | Official: same pages as `/`. open-swarm has no mention picker. Confidence: **High**. |
| **Enter** (composer) | Send the message *(not printed by xAI)* | **match** (de facto) | Official docs never say “Enter sends.” Chat UIs almost always do. open-swarm `ChatPage` uses `<form>` + `<input type="text">` so Enter submits. Agent Router also sends on Enter (`AgentRouterPage.tsx`). Confidence that *Grok* uses Enter: **Medium** (undocumented convention). |
| **Shift+Enter** | Newline *(not printed)* | **n/a** | No Grok Bot source found. open-swarm Grok composer is single-line, so Shift+Enter cannot insert a newline today. Do not invent a send/newline split until Grok is re-checked. Confidence: **Low**. |
| **Esc** (composer, idle draft) | Clear the draft *(not printed)* | **expand** (already shipped) | No Grok Bot source. open-swarm `ChatPage` clears a non-empty composer on Escape. Keep it; it does not collide with documented Grok chords. Overlay Esc (menus / palette) is standard and already used. Confidence Grok does the same: **Low**. |
| **⌘⇧I / Ctrl+Shift+I** | Inspect the current Bot (header / conversation details; computer preview in that pane) | **n/a** (tentative) | **Low.** Only [dennisyu.com playbook](https://dennisyu.com/how-i-use-grok-bot/) step 14. Not in official docs. DevTools also uses this chord in Chromium — **re-verify on the live app** before matching. open-swarm Agent Computer is a header stub, not this shortcut. |
| **Pin / Hide / Unhide / Duplicate / Share / Delete** | Sidebar Bot menu actions | **n/a** | Official [bots](https://docs.x.ai/grok-bot/bots) describes **clicks**, not chords. open-swarm already has pin / hide / unhide / Hidden Bots footer (REQ-129). No Grok keyboard to match. |
| **Show hidden chats** | Restore a hidden Bot | **n/a** | Official: “Open Show hidden chats at the bottom of the sidebar.” open-swarm Hidden Bots footer is the analogue. No Grok shortcut found. |
| **New group chat** | New → pick 2–6 Bots | **n/a** | Official: New in the sidebar (no extra chord). Mobile: `+` → New Group Chat. open-swarm group picker is `SessionPicker`, not New. |
| **Reactions / threads / Stop now** | Collaboration, not global shortcuts | **n/a** | Official [chat-and-collaboration](https://docs.x.ai/grok-bot/chat-and-collaboration). Typed “Stop now”; no key chord. |
| **Alt/⌥+1 … Alt/⌥+N** | *(Grok: none found)* Jump favourite tile *N* | **expand** | [#547](https://github.com/matthewhand/open-swarm/issues/547) owner request. Documented Grok chords use ⌘/Ctrl, not Alt. Safe expansion. **Not implemented.** Cap at 9 or displayed pin count. |
| **⌘B / Ctrl+B** | *(Grok Bot: none found)* | **n/a** | Bound on **Agent Router** leftover sidebar (“Toggle sidebar”). Grok **Build TUI** uses Ctrl+B for “send command to background.” Do **not** promote onto Grok-Bot chrome. |
| **Bare `/` outside inputs** | *(Grok Bot: none found)* | **n/a** | Agent Router leftover opens a local SearchPopup. Conflicts with Grok composer `/` = skills. Do not promote. |

---

## 4. What open-swarm actually binds today

Evidence on `main` @ `f6be01cd`. **No fake shortcuts.**

### 4.1 Grok-Bot chrome (`/` + `/chat`)

| Binding | Where | Effect |
|---------|-------|--------|
| *(none)* | `SearchPalette` / `AgentSidebar` | Opening Search is click / focus-on-readonly rail field / `swarm:open-search` only. Placeholder is exactly `Search` (REQ-17). |
| **⌘K / Ctrl+K** | `experimental/CommandPalette.tsx` (mounted from `App.tsx` when `swarm_experimental_command_palette` ≠ `off`; **defaults ON**) | Toggles the **experimental** operator catalog — **not** `SearchPalette`. This is the #547 collision. |
| **Esc**, **↑/↓**, **Enter**, **Ctrl+1–9** | `SearchPalette.tsx` (while open) | Close / move / choose. Row kbd chips render `⌃N`. |
| **Esc**, **↑/↓**, **Enter**, **Ctrl+1–9** | `SessionPicker.tsx` (group session overlay) | Same in-list pattern. |
| **Enter** | `ChatPage` composer `<form>` | Send. |
| **Esc** | `ChatPage` composer | Clear draft if non-empty. |
| **⌘Enter / Ctrl+Enter** | `ChatMessageBubble` edit box | Save an in-place edit. |
| **Esc** | Rail context menu, TeamComposer menu, Support briefing popover | Dismiss. |
| Left-edge swipe / header | `RailChrome` | Restore the rail on narrow viewports. No desktop hide/show chord. |

`ChatComposerDock` (jump-to-bottom / new-message pill) exists as a component but is **not mounted** from `ChatPage` on this snapshot. #547 may tip jump-to-bottom only after a real binding exists.

### 4.2 Agent Router (`/agents`) — not the parity surface

| Binding | Where | Effect |
|---------|-------|--------|
| **Ctrl/⌘+B** | `AgentSidebar/AgentSidebar.tsx` | Toggle sidebar. Tooltip still says “Toggle sidebar (Ctrl+B)”. |
| **`/`** (not in an input) | same | Opens leftover `SearchPopup`, not `SearchPalette`. |
| **Enter** | `AgentRouterPage` composer | Send. |
| **Shift+Tab** | `AgentRouterPage` composer | Cycle session mode. |

### 4.3 Known debt (already written down)

[docs/debt/qa-wave1-webui.md](./debt/qa-wave1-webui.md) and [docs/debt/webui.md](./debt/webui.md): two launchers; experimental ⌘K is leftover operator IA; “If Search stays, delete ⌘K catalog or point ⌘K at `SearchPalette`.” #547 / #552 make that the **product** rule, not optional cleanup.

---

## 5. #547 implementation order

Do not wallpaper the UI. Do not invent unbound tips. Order:

1. **⌘K / Ctrl+K → main `SearchPalette` (Grok match).** Steal the chord from `experimental/CommandPalette`. Retire, merge, or demote that experiment (`off` by default, or fold useful Actions into Search tabs). One launcher.
2. **Tip the Search affordance** with the real binding: rail field / placeholder `Search ⌘K` or `Search Ctrl+K` (platform-aware), plus navbar/icon tooltip if one exists. Same muted kbd-chip chrome already used for `⌃N`.
3. **First-load tips** (empty/welcome, before an agent is selected): dismissible step-through — Search (⌘K), plus 1–2 *already-real* bindings (Enter send, Esc clear draft). Persist dismiss in `localStorage` (Django prefs later, #540).
4. **Lace a small set** of existing bindings only (send, new line *if it exists*, jump-to-bottom *if mounted*, hide/rail *if bound*). No wallpaper.
5. **Then expand:** Alt/⌥+1…N favourites (grid order, cap 9 / displayed count) + hover `⌥N` / `Alt+N` on the tile. Include in the tips step-through.

Park **⌘N / Ctrl+N** (new agent) and **⌘, / Ctrl+,** (settings) for a follow-up implement Issue after #547. They are High-confidence Grok matches but not in the #547 success list.

---

## 6. Recommended open-swarm-only expansions (no Grok collision)

Use **Alt / ⌥** for swarm-only jumps. Documented Grok Bot chords are ⌘/Ctrl (+ Shift on one unverified row). Do not take ⌘K, ⌘N, or ⌘, for anything else.

| Proposed binding | Meaning | Why it does not collide | Notes |
|------------------|---------|-------------------------|-------|
| **Alt/⌥+1 … Alt/⌥+9** | Select favourite / pin *N* in **grid order** | Grok has no Alt+digit map in any source found | [#547](https://github.com/matthewhand/open-swarm/issues/547). Hover-reveal on the tile. Skip hidden pins. If fewer than *N* pins, no-op. |
| **Alt/⌥+0** (optional) | Open **Hidden Bots** | No Grok Alt+0 | Only if a first-class overlay remains after REQ-129. Prefer no binding over a second Hidden entry point. |
| **Alt/⌥+R** (optional) | Focus / open **Remotes** (catalog or first healthy remote) | No Grok Alt+R; remotes are an open-swarm surface | Pair with Settings remotes, not a new palette. |
| **Alt/⌥+C** (optional) | Computer-control stub / pane | Avoids unverified ⌘⇧I | Keep until Agent Computer inspect is confirmed. |
| **Esc** (composer) | Clear draft | Already shipped; no Grok conflict | Tip it only if #547 wants a second real example. |
| **End / Ctrl+End** (optional) | Jump to latest messages | Standard caret/scroll; not a Grok Bot chord | Only after `ChatComposerDock` (or equivalent) is actually mounted. |

**Do not bind (collision or confusion):**

| Chord | Why not |
|-------|---------|
| ⌘K / Ctrl+K | Reserved for Search agents (#547 / this map). |
| ⌘N / Ctrl+N | Grok New agent. Reserve for a later match, or leave unbound. |
| ⌘, / Ctrl+, | Grok Settings. Reserve for a later match. |
| Ctrl+1–9 (global) | Already **in-palette** row jumps (`⌃N`). Global digits would fight the open Search overlay. Favourites use **Alt**, not Ctrl. |
| Bare `/` (global) | Grok composer skill menu. |
| ⌘B / Ctrl+B | Agent Router leftover + Grok Build TUI “background.” |
| Ctrl+P, Ctrl+\, Ctrl+. | Grok **Build TUI** (palette / dashboard / shortcut help). Different product. |
| ⌘⇧I / Ctrl+Shift+I | Unverified Grok inspect **and** Chromium DevTools. Re-check before matching. |

---

## 7. Uncertainty and how to re-verify

Official Grok Bot docs (2026-09-04 crawl) print **only** `Cmd/Ctrl+N` and `Cmd/Ctrl+,`. They describe Search / command palette, `/`, and `@` without a global open chord. ⌘K is therefore **owner-verified + demo-corroborated**, not docs-printed.

This environment could not sign in to the Grok Bot app or x.ai/bot (Cloudflare). Before treating Low/Medium rows as implement-ready:

1. Open Grok Bot desktop → confirm ⌘K / Ctrl+K opens Search (Bots tab / agent results).
2. Note any in-app **Keyboard shortcuts** overlay (none is linked from docs.x.ai/grok-bot).
3. Confirm whether Enter sends and whether Shift+Enter is a newline.
4. Confirm or reject ⌘⇧I for inspect / Agent Computer.
5. Confirm no Alt+digit map on favourite / pin tiles.

If a live check disagrees with this table, **update this file** rather than coding from memory.

---

## 8. Sources

### Official (Grok Bot)

- [Grok Bot overview](https://docs.x.ai/grok-bot/overview)
- [Get started](https://docs.x.ai/grok-bot/get-started)
- [Create and manage Bots](https://docs.x.ai/grok-bot/bots) — `Cmd/Ctrl+N`, pin / hide / unhide (UI)
- [Message and collaborate](https://docs.x.ai/grok-bot/chat-and-collaboration) — Search / command palette contents; `/` and `@`
- [Skills and routines](https://docs.x.ai/grok-bot/skills-routines-and-automations) — `/` skills, `@` mentions
- [Settings and notifications](https://docs.x.ai/grok-bot/settings-and-notifications) — `Cmd/Ctrl+,`
- [Use the computer and apps](https://docs.x.ai/grok-bot/computer-and-apps) — `@` connectors, `/` skills
- [Introducing Grok Bot](https://x.ai/news/introducing-grok-bot) — product framing, no shortcut list
- [Cursor: Work with Grok Bot](https://cursor.com/docs/grok-bot/work) — `Cmd+N` / `Ctrl+N`

### Owner / in-repo

- [#552](https://github.com/matthewhand/open-swarm/issues/552) (this map)
- [#547](https://github.com/matthewhand/open-swarm/issues/547) — ⌘K = search agents; Alt/⌥ favourites; tip lace
- [REQ-16](./archive/requirements/REQ-16.md), [REQ-17](./archive/requirements/REQ-17.md) — rail + Search overlay clone (`⌃N`, Esc, arrows, Enter)
- `webui/frontend/src/components/SearchPalette.tsx`, `App.tsx`, `experimental/CommandPalette.tsx`, `experimental/README.md`, `pages/ChatPage.tsx`
- [docs/debt/qa-wave1-webui.md](./debt/qa-wave1-webui.md) — two-launcher debt

### Community (mark as such)

- [DataCamp: Grok Bot tutorial](https://www.datacamp.com/tutorial/grok-bot-tutorial) — `Cmd/Ctrl+N`
- [How I Use Grok Bot as One Ops Desk](https://dennisyu.com/how-i-use-grok-bot/) — `Cmd+,`; command palette “Open settings”; **Low:** `Cmd+Shift+I`
- [YouTube: Grok Bot Command+K demo](https://www.youtube.com/watch?v=XgkW4A6lrDY) (transcript: youtube-distilled) — Command+K searches agents, messages, routines, groups

### Explicitly not sources for Bot chrome

- [Grok Build keyboard shortcuts](https://docs.x.ai/build/keyboard-shortcuts)
- [Grok Build Agent Dashboard keys](https://docs.x.ai/build/features/dashboard)
- Unofficial `*grok-desktop*` Electron READMEs
