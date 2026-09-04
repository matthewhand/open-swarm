# ADR-003: Optional 3D robot avatar theme family (Reachy-inspired)

- **Status:** Proposed (look-only; no WebGL / no runtime change in this PR)
- **Date:** 2026-09-04
- **Issue:** [#667](https://github.com/matthewhand/open-swarm/issues/667) (REQ-194)
- **Related:** [#662](https://github.com/matthewhand/open-swarm/issues/662) (REQ-188C-3 one avatar-theme store), [#346](https://github.com/matthewhand/open-swarm/issues/346) (REQ-34 Blobs, closed), [#540](https://github.com/matthewhand/open-swarm/issues/540) (REQ-144 Django prefs), [ADR-001](../ADR-001-primary-ui.md), [ADR-002](./002-config-ownership.md)
- **Inspiration (external):** [matthewhand/reachy-subconscious-expression-app](https://github.com/matthewhand/reachy-subconscious-expression-app) — cited from #667. A sibling look-only agent is auditing that repo. This ADR does **not** invent Reachy internals; see §6 **pending Reachy audit**.
- **Supersedes:** none. Extends the Settings Rail theme family; does not replace Blobs / bland / custom faces.

**Decision:** add an **optional** Settings Rail theme family `robot3d` (“3D robot”) that can play idle / listen / working / dance-style clips **without blocking chat**. Phase 1 hosts the viewer in an **iframe to an extractable package**, not a Three.js import in the SPA main bundle. Multiple body/head meshes may share clips only after they satisfy the **rig contract** (§4). Custom uploaded 2D faces still win. No Neon. No secrets.

This ADR is **Phase 0** of REQ-194. It maps today’s chrome and parks implement work. It does **not** `Fixes` #667 — later phases remain.

Evidence below is from `origin/main` `87da9c93` at writing. No secrets are documented. Use `${VAR}` names only.

---

## Issue quote (REQ-194)

**Intent:** Users can pick a 3D robot theme (not only Blobs / bland / upload) that feels alive like Reachy Mini’s 3D presence; later, swap body/head meshes without rewriting clips.

**Success (phased, from #667):**

1. **Phase 0 — ADRs:** Reachy report (stack, clip/rig contract, licensing) + open-swarm ADR (embed path, perf, theme settings key, event hooks).
2. **Phase 1 — One mesh:** Ship Reachy-like (or licensed) mesh + idle/working clips in SPA theme picker; chat never blocked on WebGL.
3. **Phase 2 — Combos:** Document bone/attachment contract; ≥2 body × ≥2 head that play the same clips.
4. **Phase 3 — Status wire:** Map agent working/listen/error to animation states (optional mood later).

**Constraints (from #667):** Respect Reachy/URDF/Three LICENSE+NOTICE. No secrets. No Neon. Prefer extractable viewer package over forking the whole subconscious app. Coordinate Settings Rail avatar theme (#662 one-store). SaaS N/A.

---

## 1. Feasibility (what exists today)

open-swarm already has a **Settings Rail avatar theme** (REQ-155 / closed #346) and a **second, leftover Agent Router pack store**. Neither is WebGL. The SPA `package.json` has no `three`, no model-viewer, no URDF loader.

A 3D family is feasible as a **new optional key** on the Rail store — not as a rewrite of Blobs, and not as a silent merge into the Agent Router SVG packs. The expensive parts are isolation (chat must not wait on GL) and a **shared rig** so Phase 2 combos do not fork clips.

---

## 2. Today’s avatar map

There are **two** theme systems. #662 exists because they do not share a store. This ADR names both so implementers do not wire `robot3d` into the wrong one.

### 2.1 Settings Rail store (canonical for Grok chrome)

| Item | Value | Evidence |
|---|---|---|
| Keys | `blobs` (default), `bland`, legacy `default` → `bland` | `webui/frontend/src/lib/avatarTheme.ts` |
| Persist | `localStorage.swarm_avatar_theme` | same file; `AVATAR_THEME_STORAGE_KEY` |
| Same-tab event | `swarm:set-avatar-theme` | `AVATAR_THEME_SET_EVENT` |
| Default | `blobs`; storing Blobs **removes** the key | `saveAvatarTheme` / `defaultAvatarTheme` |
| Settings picker | Settings sheet → **Rail** → “Avatar theme” | `SettingsSheet.tsx` `RailPane` + `AvatarThemePicker.tsx` |
| Django twin | `/settings/` select `#os-avatar-theme` | `src/swarm/templates/settings_dashboard.html`; `src/swarm/static/js/chrome_avatar_theme.js` |
| Tests | persist + labels | `avatarTheme.test.ts`; `tests/unit/test_req155_avatar_theme.py`; `e2e/settings-sheet.spec.ts` |

Picker copy (`AvatarThemePicker.tsx`): “Blobs are per-agent shapes with eyes (default). Bland static uses identical grey circles. **Custom uploaded faces always win.**”

Django dashboard copy matches Blobs vs bland and says the choice stays in the browser and does not rewrite blueprints.

### 2.2 How faces render on the rail and in chat

Shared component: `webui/frontend/src/components/AgentAvatar.tsx` (Grok chrome — **not** `AgentSidebar/AgentAvatar.tsx`).

Resolution order:

1. **Custom `src`** (trimmed, non-empty, image not broken) → circular `<img>`, `data-agent-avatar="custom"`.
2. Else **theme `blobs`** → `BlobAvatar` SVG, `data-avatar-theme="blobs"`, `data-eye-state` `active` \| `idle`.
3. Else **theme `bland`** (and migrated `default`) → inline grey circle + silhouette data-URI (`DEFAULT_AGENT_AVATAR_SRC`).

| Surface | Size | What it paints | File |
|---|---|---|---|
| Left-rail conversation row | `sm` | `AgentAvatar` with `src={agent.avatar_path}` | `AgentSidebar.tsx` |
| Favourite tiles | `lg` | same, `src={live?.avatar_path}` | `AgentSidebar.tsx` |
| Chat header (non-team) | `lg` | same, `src={selectedAgent?.avatar_path}`, `active` when streaming **or** WS `status === 'open'` | `ChatPage.tsx` |
| Avatar-only rail (`width ≤ 96px`) | still `sm` faces | names hide; faces stay | `railResize.ts` `AVATAR_ONLY_THRESHOLD`; `data-avatar-only` |

Blobs (`blobAvatar.ts` + `BlobAvatar.tsx` + `index.css`):

- Deterministic **shape + solid colour + idle eye rest** hashed from `agentId` (FNV-style). Shapes: hexagon, circle, teardrop, triangle, pill, cloud, roundedRect, diamond.
- Idle: eyes parked. Active: CSS `@keyframes os-blob-wander` (slow, several-second period).
- `prefers-reduced-motion: reduce` disables wander.
- Chat header currently marks `active` whenever the websocket is `open`, so eyes wander for the whole connected session — not only while a reply streams. Phase 3 must not copy that as “listen” without an explicit remap.

Bland: identical grey person-silhouette for every agent (`AgentAvatar.tsx` data-URI). REQ-6’s Bert-like SVG (`src/swarm/static/img/default-agent-avatar.svg`) is **not** this bland URI; Django library cards still use the Bert SVG. SPA chrome does not.

### 2.3 Custom uploaded faces

There is **no** Settings file-picker for faces. “Upload” in product copy means a **blueprint `avatar_path`** (or `avatar`) that the list API passes through:

- `src/swarm/views/api_views.py` `_metadata_avatar_path` — empty/missing stays `None`; SPA owns the fallback.
- `GET /v1/blueprints/` includes `avatar_path`.
- ComfyUI generate (`src/swarm/utils/comfyui_client.py`) writes `{slug}_avatar.png` under `AVATAR_STORAGE_PATH` and returns `{AVATAR_URL_PREFIX}{filename}` (defaults `/avatars/`).
- Django Blueprint Library “Generate Avatar” is the operator path (`blueprint_library_views.generate_avatar`).
- Broken custom images fall back to the **current** theme (Blobs or bland), not a third art.

**Decision for 3D:** custom 2D `avatar_path` **still wins** over `robot3d`. Do not treat an arbitrary user glTF/URDF upload as Phase 1–2 (XSS / GPU / license risk). Combo picks are catalog ids, not free-form mesh URLs.

### 2.4 What does **not** use the Rail theme

| Surface | What it shows | Notes |
|---|---|---|
| Scale-out / team stacks | Coloured dots + pulse (`AvatarStack`) | REQ-66 / REQ-68. Not `AgentAvatar`. Do not spawn WebGL per stacked face. |
| Grok chat **transcript** | No per-bubble face | `ChatPage` mounts `AgentAvatar` only in the header. |
| Django operator rail | `os-agent-dot` colour marks | `agent_sidebar.js`; not Blobs. |
| Django library cards | custom img or Bert SVG | `blueprint_card.html` |

### 2.5 Leftover Agent Router packs (do not confuse)

`/agents` is still mounted (`App.tsx`) despite [ADR-001](../ADR-001-primary-ui.md) “SPA Chat only” and `webui/README.md` claiming `/` + `/chat` only.

That page uses a **different** `AvatarTheme`: `chassis` \| `pixel` \| `glyph` \| `orb` \| `antenna` \| `cube` \| `mask` \| `beetle` \| `ghost` \| `crystal`, plus eye styles (`lens` / `googly` / …). Persist keys: `agent_avatar_theme`, `agent_avatar_theme_by_agent`, `agent_avatar_eyes`, `agent_avatar_eyes_by_agent` (`agent-store.ts`). Renderer: SVG `RobotAvatar.tsx` — pointer-track eyes, blink, CSS classes `robot-idle` / `robot-working` / `robot-error` / `robot-waiting`. Status type already exists: `AgentStatus = 'idle' \| 'working' \| 'waiting' \| 'error' \| 'happy'`. `AvatarMotion` is declared but unused (`_motion`).

**Do not** add `robot3d` to this pack enum. After #662, one Rail store is the only picker; Router SVG packs either fold into that store or stay a leftover until `/agents` is destaged.

### 2.6 Status signals the 3D viewer may later consume (Phase 3)

Grok chat already has client-side hooks — **no new WS mood channel in Phase 1**.

| Signal | Where | Suggested clip (Phase 3) |
|---|---|---|
| No stream; WS not failed | `ChatPage` `streamingMessage`, `status` | `idle` |
| WS `open`, composer focused / awaiting user | WS status + focus (not wired as `listen` today) | `listen` |
| Assistant streaming, or `tool_status` `running` | `chatWs.ts` `ToolStatus`; header stream timer | `working` |
| WS `failed` / `tool_status` `error` | `chatWs.ts`; Chat header `statusLabel` | `error` |
| Optional celebration | Agent Router `happy` only today | `dance` (opt-in, never auto-loop on every reply) |

Inbound `type: "status"` frames exist on the consumer (`consumers.py`) as **text lines**, not a structured mood enum. Do not invent a server mood SoT until Phase 3 agrees a small event map.

---

## 3. Proposed theme family

### 3.1 Settings key

Add **one** Rail key:

| Persist value | Picker label | Meaning |
|---|---|---|
| `robot3d` | 3D robot | Optional family. Viewer + catalog live behind this key. |

Keep `blobs` / `bland` / legacy `default`. Unknown values still fall back to `blobs` (`isAvatarTheme`).

**#662 coordination:** Phase 1 must extend `AVATAR_THEMES` in `avatarTheme.ts` **and** the Django `#os-avatar-theme` script so Settings ↔ Chat hops stay one key (`swarm_avatar_theme`). Do not introduce `swarm_avatar_theme_3d` or a second picker. Combo selection (Phase 2) is a **sub-key** only while `theme === robot3d`, e.g. `swarm_avatar_robot3d_combo` = `{ "body": "reachy-mini", "head": "reachy-mini" }` — ignored unless the theme is `robot3d`. After #540, both keys move to Django prefs with the rest of the UI prefs.

### 3.2 Presence slot vs tiles

| Slot | Phase 1 | Why |
|---|---|---|
| Chat header (`lg`) | **One** live 3D instance (the presence slot) | Matches Reachy-style “alive” chrome without N canvases |
| Rail rows / fav tiles / avatar-only rail | 2D **poster** (static frame or Blobs-tinted stand-in) | `#497` rail can be 68px; WebGL per row would blow the budget |
| Scale-out stacks | unchanged dots | Already a different widget |
| Transcript bubbles | no face (unchanged) | Do not add GL to the message list |

If WebGL fails, `prefers-reduced-motion` is reduce, or the iframe is still booting: show Blobs (or bland if that was the user’s last 2D theme). Chat chrome stays painted.

### 3.3 Clip set (open-swarm names)

Stable clip ids for the SPA ↔ viewer `postMessage` contract. **Reachy file names / mixer API = pending Reachy audit.**

| Clip id | Loop | When (Phase 1 / 3) |
|---|---|---|
| `idle` | yes | Default; Phase 1 required |
| `working` | yes | Phase 1 required (map from `streamingMessage` or leave a Settings “preview working” until Phase 3) |
| `listen` | yes | Phase 3 (or Phase 1 if the extracted viewer already has it — **pending audit**) |
| `dance` | no (or short loop, user/opt-in) | Phase 1 optional preview; Phase 3 never blocks send |
| `error` | no / hold last | Phase 3 |

Clip changes are **fire-and-forget**. The viewer crossfades; the composer and WS parser do not `await` a frame.

---

## 4. Rig contract (required before Phase 2 catalog)

Phase 1 may ship a **single** locked Reachy-like mesh that already plays `idle` / `working`. Phase 2 **must not** land a second body or head until a machine-checkable manifest passes.

Open-swarm owns the contract. Reachy bone **strings** are filled in after the sibling audit — do not hard-code guessed Pollen / URDF names here.

### 4.1 Manifest (normative shape)

```ts
/** Catalog entry. Unknown extra fields ignored. Missing required fields fail closed. */
export interface Robot3dRigManifest {
  schema: 1
  id: string
  kind: 'body' | 'head' | 'full'
  /** License SPDX + NOTICE path inside the viewer package. No secrets. */
  license: { spdx: string; notice: string }
  /** 1.0 = 1 metre. Pending Reachy audit for authoring scale. */
  units: 'meters'
  /** Rest-pose height of a full robot, metres. Combos must match ±tolerance. */
  restHeight: number
  restHeightTolerance: number
  /**
   * Canonical bone names this mesh binds.
   * Phase 1: copy the list from the Reachy audit (placeholder until then).
   * Phase 2: every body/head combo must include this exact set (or a documented
   * required subset + optional extras that clips do not target).
   */
  bones: string[]
  /**
   * Socket the head mesh attaches to. Body entries MUST export it.
   * Head entries MUST be authored at this joint’s bind pose.
   * Name: pending Reachy audit (do not invent `neck_link` / `HeadSocket` here).
   */
  headAttachment: {
    bone: string
    /** Local offset/rotation from that bone. */
    offset: { x: number; y: number; z: number }
    quaternion: { x: number; y: number; z: number; w: number }
  }
  clips: Partial<Record<'idle' | 'listen' | 'working' | 'dance' | 'error', {
    loop: boolean
    fadeMs: number
    /** Package-relative clip id. Pending Reachy audit for source names. */
    source: string
  }>>
}
```

### 4.2 Mix-and-match rules

1. **One skeleton family.** Clips target **bone names**, not mesh topology. A head swap must not rename bones the clip already uses.
2. **Body owns locomotion + arms + attachment socket.** Head owns face / antenna / visor verts only.
3. **Shared bind-pose scale.** If `restHeight` differs by more than `restHeightTolerance`, reject the combo in the picker (fail closed, keep last valid combo or the Phase 1 full-body).
4. **Clip completeness.** A combo is playable only if **both** parts (or the `full` mesh) declare every clip the viewer is asked to play. Missing `dance` is OK until that clip is requested; missing `idle` or `working` is not shippable for Phase 1.
5. **No runtime retargeter** in Phase 1–2. If a mesh needs retargeting, it is a content bug, not a Three.js IK feature.
6. **Validator** (Phase 2 implement): load manifests, assert bone set + `headAttachment.bone` + scale, refuse to list illegal pairs.

### 4.3 What stays pending Reachy audit

Fill these from the sibling Reachy report before Phase 1 mesh lock:

- Exact engine (owner #667 claim: Three.js + URDF, paths `robot-3d/`, `robot_3d.js` — **unverified here**; this agent cannot see that repo).
- Canonical `bones[]` and `headAttachment.bone`.
- Authoring units and Reachy Mini rest height.
- Whether dances are clip tracks, Mixamo, or procedural (subconscious / expression layer).
- How body vs head are (or are not) already split in that app.
- LICENSE / NOTICE / third-party model terms (Pollen Robotics, Three, URDF assets).
- Recommended extract surface (which files become the viewer package vs app chrome to leave behind).

Until that report lands, Phase 1 implementers treat the first mesh as a **full** `kind: 'full'` entry and do not advertise a combo UI.

---

## 5. Embed WebGL in the SPA vs iframe to a viewer package

#667: prefer an **extractable viewer package** over forking the subconscious app.

| Option | Verdict |
|---|---|
| **A. iframe → extractable viewer** (same-origin static) | **Pick for Phase 1.** Separate JS realm; can tear down on theme change; SPA bundle stays Three-free; chat input / WS parse cannot be blocked by GL compile. `postMessage` for `{ clip, combo, reducedMotion }`. |
| **B. Lazy `import()` embed in the SPA** | Allowed **later** (Phase 2+ or a follow-up) if iframe overhead hurts the single header slot. Still code-split; still one context; same fallback. Do not add `three` to `webui/frontend/package.json` dependencies of the chat graph in Phase 1. |
| **C. Fork the whole Reachy app into `webui/`** | Reject. Operator chrome + subconscious expression UI is out of scope. |
| **D. Cross-origin hosted viewer** | Reject. Needs network + possible keys; #667 forbids secrets; offline `:8001` must work. |
| **E. N WebGL contexts (one per rail tile)** | Reject. Breaks §7 budget. |

Iframe rules:

- Served from the same Django origin as the SPA (`/static/…` or a baked viewer path). No third-party CDN API keys.
- Sandbox: `allow-scripts`; document why `allow-same-origin` is or is not required after the Reachy audit (WebGL + workers).
- First contentful chat paint must not wait on iframe `load`. Header shows the 2D fallback until `ready` is posted.
- `visibilitychange` / unmount → `pause`. Theme switch away from `robot3d` → destroy the iframe (release the GL context).
- `prefers-reduced-motion: reduce` → static poster, no clip loop.

---

## 6. Reachy inspiration (pending sibling audit)

| Claim | Source | This ADR |
|---|---|---|
| Reachy Mini subconscious / dancing / animated presence is the **feel** target | Matthew / #667 | Design intent only |
| That app’s WebUI already has Three.js + URDF (`robot-3d/`, `robot_3d.js`) and dances | #667 owner text | **Pending Reachy audit** — not verified from this checkout (repo 404 to this agent; different tree) |
| Extract a viewer package; do not fork the whole app | #667 constraints | Adopted (§5) |
| LICENSE + NOTICE must be respected | #667 | Phase 1 blocker; copy into the package |

Do not cite bone lists, clip file names, or Three versions as fact until the sibling Reachy ADR/report exists. When it does, amend this ADR (or a short addendum) rather than silently changing the manifest.

---

## 7. Perf budget (SPA on `:8001`)

`:8001` is the native/oracle uvicorn+ASGI host that serves the SPA **and** the chat websocket (`docs/ORACLE_DEPLOY.md`, `docker-compose.dev.yml` comments). Implement PRs still must not **deploy** to the live host; the budget is what that process’s browsers will feel.

| Budget | Cap |
|---|---|
| Main SPA JS | **0** Three/URDF/GLTF parsers unless `robot3d` is selected (then iframe/package only) |
| WebGL contexts | **1** (header presence). Zero when theme is Blobs/bland or a custom 2D face is showing |
| Rail / fav / stack | No GL. Poster or existing 2D |
| Chat first paint / send | Must succeed if the iframe is slow, blocked, or `webglcontextlost` |
| Frame rate | Idle ≤ 30 fps; pause when hidden; no work on `visibilityState === 'hidden'` |
| Payload (Phase 1 target) | One mesh + idle/working: keep **small**; exact MB **pending Reachy audit**. If the extracted assets exceed a reasonable static budget, ship a decimated preview mesh — do not stream a research-size URDF on every header mount |
| CPU vs composer | Viewer runs in the iframe; dropped frames must not stall `<input>` or `chatWs` parse |
| Memory | Destroy iframe on theme-off; no leaked contexts across agent switches (reuse one iframe, `postMessage` combo change) |
| A11y | Decorative (`aria-hidden`) like today’s faces; do not put a second live region on the header |

No Neon. No new env secrets. Viewer config is public static + the Rail theme key.

---

## 8. Phased success (implement parked)

### Phase 0 — this PR

- Map today’s themes and render path (done).
- Pick iframe + extractable package, `robot3d` key, rig contract, perf budget.
- Sibling Reachy report remains a **separate** deliverable; placeholders above stay until it merges.

### Phase 1 — one Reachy-like mesh + idle/working

Suggested implement Issue title: **REQ-194 Phase 1: `robot3d` theme + one licensed mesh (idle/working), chat never blocked**

- Extend `isAvatarTheme` / Django `#os-avatar-theme` / e2e with `robot3d`.
- Header presence iframe; rail posters.
- Custom `avatar_path` still wins.
- Fallback on GL failure / reduced motion.
- Honor LICENSE+NOTICE from the audit.
- Coordinate #662 (one store) — do not add a second persist key for the **theme**.

### Phase 2 — body/head combo catalog

Suggested title: **REQ-194 Phase 2: robot3d catalog — ≥2 bodies × ≥2 heads on one rig**

- Ship the validator + combo sub-key.
- Same clips on every legal pair.
- No retargeter.

### Phase 3 — wire agent status / optional mood

Suggested title: **REQ-194 Phase 3: map chat/WS status to robot3d clips (idle/listen/working/error)**

- Map §2.6 signals; optional `dance` not on every completion.
- Still no blocking `await` on clips.
- Optional later: structured mood events — only if Phase 3 proves inbound `status` text is not enough.

---

## 9. Follow-up implement Issues (titles only)

Do not implement in this PR.

1. **REQ-194 Phase 1: `robot3d` theme + one licensed mesh (idle/working), chat never blocked**
2. **REQ-194 Phase 2: robot3d catalog — ≥2 bodies × ≥2 heads on one rig**
3. **REQ-194 Phase 3: map chat/WS status to robot3d clips (idle/listen/working/error)**
4. **[#662](https://github.com/matthewhand/open-swarm/issues/662) one avatar-theme store** — include `robot3d` in that single key; fold or destage `/agents` SVG packs
5. **Amend ADR-003 after Reachy audit** — fill §4 bone names, units, LICENSE, extract file list
6. **[#540](https://github.com/matthewhand/open-swarm/issues/540) prefs** — migrate `swarm_avatar_theme` (+ combo sub-key) with other UI prefs; localStorage seed-once

---

## 10. Consequences

- Operators: optional 3D presence in the chat header; Blobs remain the default; bland and custom 2D faces unchanged.
- Implementers: no Three on the chat critical path; no N canvases; no combo UI before the rig validator; no secrets; no Neon.
- `/agents` RobotAvatar packs stay a leftover until #662. Do not treat them as the 3D theme.
- This PR: documentation only. **Addresses** #667 (Phase 0). Does not `Fixes` #667.
