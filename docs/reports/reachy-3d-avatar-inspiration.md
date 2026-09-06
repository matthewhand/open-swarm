# Reachy-style 3D presence — stack, pose contract, licensing

- **Date:** 2026-09-06
- **Programme:** [REQ-194 / #667](https://github.com/matthewhand/open-swarm/issues/667)
- **Companion ADR:** [ADR-008](../adr/008-3d-robot-avatar-theme.md)
- **Inspiration repo (private to this agent):** [matthewhand/reachy-subconscious-expression-app](https://github.com/matthewhand/reachy-subconscious-expression-app)
- **Look-only evidence already on that repo:** [PR #10](https://github.com/matthewhand/reachy-subconscious-expression-app/pull/10) — summarised by Matthew on #667
- **Public corroboration (same 3D family):** [pollen-robotics/reachy-mini-desktop-app](https://github.com/pollen-robotics/reachy-mini-desktop-app) (`develop`, Apache-2.0), [pollen-robotics/reachy_mini](https://github.com/pollen-robotics/reachy_mini) SDK URDF/STL

This is the **Phase 0 Reachy report**. It does not vendor meshes, add Three.js, or change chat runtime beyond the optional disabled picker stub described in ADR-008.

No secrets. No Neon. Use `${VAR}` names only.

---

## 0. Provenance (what is fact vs corroboration)

This checkout cannot clone `matthewhand/reachy-subconscious-expression-app` (GitHub 404 to this token). The private-tree facts below are taken from **Matthew’s #667 comment that cites PR #10**, plus the #667 issue body. They are **not** re-invented.

Public Pollen repos were readable and are used only to **corroborate** the same Mini 3D family (URDF pose mirror, not AnimationMixer) and to name licenses this agent could actually open.

| Claim | Source | Weight |
|---|---|---|
| Feel target is Reachy Mini’s alive 3D presence (idle / listen / working / dance-style) | #667 issue | Intent |
| WebUI already has Three.js + URDF at `robot-3d/`, `robot_3d.js` | #667 issue | Owner claim; matches public desktop-app `src/assets/robot-3d/` |
| 3D Mini is a **URDF pose mirror** (`/ws/joints` → Three.js), **not** an AnimationMixer clip player | #667 comment → PR #10 | **Normative for Phase 1** |
| Copying `robot_3d.js` without a `MiniPose` source = static mesh | same | Normative |
| STLs are **gitignored** in the inspiration app — theme must vendor/bake | same | Normative |
| Mix-and-match needs `MiniPose = { body_yaw, head:{pos,quat}, antennas }` + attach offsets, **not** bone-name swap | same | Normative |
| Prefer **lazy WebGL on chat hero**; do **not** iframe Glance | same | Normative (overrides the 2026-09-04 iframe-first draft in ADR-008) |
| Extract a viewer package; do not fork the whole subconscious app | #667 constraints | Adopted |
| Respect LICENSE + NOTICE | #667 constraints | Phase 1 blocker |
| Official desktop viewer: Three + R3F + `urdf-loader`, `headJoints` = `[body_yaw, stewart_1…6]`, `headPose` 4×4, `antennas` `[left, right]`, WASM passive joints, ~10–20 Hz WS | public `reachy-mini-desktop-app` wiki + `URDFRobot` / `robotModelCache.ts` | Corroboration of the pose-mirror model |
| Official SDK serves URDF + STL from `descriptions/reachy_mini/urdf/` (LFS; missing STL is a common clone footgun) | public `reachy_mini` `kinematics.py`, issue #760 | Asset logistics |

If the private PR #10 text and this report ever disagree, **PR #10 wins** for that repo’s internals. Amend this file rather than silently changing ADR-008’s contract.

---

## 1. Stack

### 1.1 Inspiration app (private, via #667 / PR #10)

| Layer | What it is | What it is not |
|---|---|---|
| Renderer | Three.js canvas driven by `robot_3d.js` | Not a CSS/SVG robot; not the leftover `/agents` `RobotAvatar.tsx` packs |
| Model | URDF under `robot-3d/` plus STL meshes | Not a Mixamo FBX; not a glTF AnimationMixer clip library |
| Live input | `/ws/joints` pose stream | Not a named clip playlist |
| Without a pose source | Mesh loads, then sits in rest pose | “Copy the JS and it will dance” is false |
| Glance | Full subconscious / desktop chrome around the canvas | **Not** the extract surface. Do not iframe it into open-swarm |

### 1.2 Public Pollen desktop app (corroboration)

Readable files that match the same architecture:

| Path | Role |
|---|---|
| `src/assets/robot-3d/reachy-mini.urdf` | URDF text, imported `?raw` |
| `src/assets/robot-3d/meshes/*` | STL resolved by `THREE.LoadingManager` URL modifier |
| `src/utils/robotModelCache.ts` | `URDFLoader` parse + STL map + flat-shading prep |
| `src/components/viewer3d/URDFRobot.tsx` (and older `.jsx`) | Apply joints / materials; `applyHeadJoints`, `applyAntennaJoints`, `applyPassiveJoints` |
| `src/components/viewer3d/Viewer3D.tsx` + `Scene.tsx` | R3F `<Canvas>`, camera, lights |
| `useRobotWebSocket` / `useRobotStateWebSocket` | Daemon state at ~10–20 Hz (`ws://127.0.0.1:8000/api/state/ws/full` in that app) |
| `src/utils/kinematics-wasm/` | Client FK for passive joints when the daemon omits them |

Dependencies implied by that tree: `three`, `@react-three/fiber`, `urdf-loader` (gkjohnson). open-swarm’s SPA `package.json` has **none** of these today — keep it that way on the chat critical path.

### 1.3 What open-swarm must **not** copy

- The daemon, USB, Hugging Face app store, emotion-wheel chrome, Glance shell.
- A live `${REACHY_DAEMON}` WebSocket as a Phase 1 requirement. Chat must work offline on a laptop with no robot.
- The whole subconscious expression app as a git subtree.

**Extract surface (recommended):** a small pose-player package that (1) loads one baked/decimated mesh, (2) applies `MiniPose` frames, (3) exposes `play(clipId)` / `pause()`. Leave Glance, daemon, and WASM IK behind unless a later phase proves they are required for a second mesh.

---

## 2. Clip / rig contract (normative)

### 2.1 Headline

**Clips are baked `MiniPose` sequences (or a pose stream), not skeletal AnimationMixer tracks.**

open-swarm still names **semantic clip ids** for chrome (`idle`, `listen`, `working`, `dance`, `error`). The viewer maps those ids onto pose playback. Do not assume a `THREE.AnimationMixer` or Mixamo retargeter exists in the inspiration app — PR #10 says it does not.

### 2.2 `MiniPose` (from PR #10 via #667)

```ts
/** One Reachy-Mini-shaped frame. Units: metres + radians + unit quaternion. */
export interface MiniPose {
  body_yaw: number
  head: {
    pos: { x: number; y: number; z: number }
    quat: { x: number; y: number; z: number; w: number }
  }
  antennas: { left: number; right: number }
}
```

Public desktop-app fields line up:

| MiniPose | Public desktop-app |
|---|---|
| `body_yaw` | `headJoints[0]` / `yawBody` |
| `head.pos` + `head.quat` | `headPose` 4×4 (extract translation + rotation) |
| `antennas.left/right` | `antennas_position` `[left, right]` radians |
| *(not in MiniPose)* | `headJoints[1..6]` Stewart actuators; `passive_joints` (21) via WASM |

Phase 1 **does not** need to stream Stewart + passive arrays if a baked preview mesh is posed only at the MiniPose sockets. If Phase 1 vendors the **full** official URDF, the player must either bake those extra joints into each frame or run the same FK — that is a mesh-choice, not a reason to invent bone-name clips.

### 2.3 Clip file shape (open-swarm owned)

```ts
export interface Robot3dClip {
  schema: 1
  id: 'idle' | 'listen' | 'working' | 'dance' | 'error'
  loop: boolean
  fadeMs: number
  /** Samples/sec. Idle/working target ≤ 30; pause when hidden. */
  hz: number
  frames: MiniPose[]
}
```

| Clip id | Loop | Phase |
|---|---|---|
| `idle` | yes | 1 required |
| `working` | yes | 1 required |
| `listen` | yes | 3 (or 1 if a baked listen already exists) |
| `dance` | no / short | 1 optional preview; 3 never auto-loops on every reply |
| `error` | no / hold last | 3 |

Fire-and-forget: the chat composer and `chatWs` parser must not `await` a frame.

### 2.4 Mix-and-match (Phase 2) — attach offsets, not bone-name swap

PR #10: combos need **`MiniPose` + attach offsets**, not “swap the head bone name and replay the same glTF clip.”

| Part | Owns | Must publish |
|---|---|---|
| Body | `body_yaw`, locomotion/base mesh, **head socket** | `headAttachment` offset + quaternion in rest pose |
| Head | `head.pos/quat` interpretation, face / visor / camera meshes | Bind pose that matches that socket |
| Antennas | `antennas.left/right` | Attachment points on the head (or a documented no-antenna stub) |

Rules:

1. One **pose family**. A second body/head is legal only if it consumes the same `MiniPose` fields (unknown extras ignored; missing required fields fail closed).
2. **No runtime retargeter** in Phase 1–2. If a mesh needs different sockets, it is a content bug.
3. Shared rest height ± tolerance (same idea as the 2026-09-04 draft, but the check is on the socket, not a guessed URDF bone string).
4. A combo is playable only when **both** parts (or a `kind: 'full'` mesh) declare `idle` + `working`.
5. Do **not** hard-code Pollen link names (`stewart_1`, `passive_1_link_x`, …) into the SPA. Those stay inside the viewer package.

### 2.5 Manifest (normative shape)

```ts
export interface Robot3dRigManifest {
  schema: 1
  id: string
  kind: 'body' | 'head' | 'full'
  license: { spdx: string; notice: string }
  units: 'meters'
  restHeight: number
  restHeightTolerance: number
  /** Socket the head mesh attaches to. Body/full MUST export it. */
  headAttachment: {
    offset: { x: number; y: number; z: number }
    quaternion: { x: number; y: number; z: number; w: number }
  }
  clips: Partial<Record<'idle' | 'listen' | 'working' | 'dance' | 'error', {
    loop: boolean
    fadeMs: number
    source: string
  }>>
}
```

Phase 1 ships one `kind: 'full'` entry. Phase 2 must not advertise a combo UI until a validator asserts socket + scale + required clips.

---

## 3. Licensing notes (respect LICENSE + NOTICE)

open-swarm is **MIT** with a root [NOTICE](../../NOTICE) that is the project’s single attribution SoT (no per-file headers). Phase 1 **must** extend that NOTICE when any third-party mesh or viewer file is vendored. Phase 0 vendors nothing.

| Work | License this agent verified | NOTICE / attribution duty |
|---|---|---|
| open-swarm | MIT — [LICENSE](../../LICENSE) | Existing NOTICE |
| `pollen-robotics/reachy-mini-desktop-app` | **Apache-2.0** (`LICENCE`, Copyright 2025 Pollen Robotics). No separate NOTICE file on `develop` at writing | Apache §4: keep license copy, change notices, retain attribution. §4(d) NOTICE copy only if a NOTICE appears in the files we actually take |
| `pollen-robotics/reachy_mini` SDK / URDF / STL | Apache-2.0 on the repo; STLs often via **Git LFS** | Same Apache rules; confirm the specific mesh files we bake are part of that Work |
| `three` | MIT (mrdoob / Three.js contributors) | Name in NOTICE if we ship the script; npm dep is enough if we do not vendor |
| `urdf-loader` / `gkjohnson/urdf-loaders` | Apache-2.0 | Same as other Apache works |
| `@react-three/fiber` | MIT | Prefer **not** taking R3F in Phase 1 (extra React reconciler). Vanilla Three pose-player is enough for one header slot |
| `matthewhand/reachy-subconscious-expression-app` | **Not readable here.** #667 requires respecting that repo’s LICENSE **and** NOTICE | Phase 1 blocker: open LICENSE + NOTICE from the tag we extract; copy required attribution into open-swarm NOTICE; do not take files the NOTICE excludes |

Additional constraints:

1. **Apache §6 trademarks.** “Reachy” and “Pollen” are product names. Picker copy should say **“3D robot”** / “Reachy-inspired”. Do not ship a “Reachy Mini” brand mark without permission.
2. **Do not fork Glance / the whole app.** Extract the pose-player + licensed mesh only. That also keeps NOTICE scope small.
3. **STLs gitignored in the inspiration app.** Shipping `robot_3d.js` alone is not enough and may also be a license miss if meshes are the actual Work. Phase 1 must **vendor or bake** a decimated preview (glTF preferred over raw STL) **after** the license check.
4. **No secrets in mesh hosting.** Same-origin static files. No CDN API keys. No Neon.
5. **User-uploaded glTF/URDF is out of scope** (XSS / GPU / license risk). Catalog ids only.
6. MIT (open-swarm) can depend on Apache-2.0 viewer code. The combined distribution must keep both notices.

---

## 4. Implications for open-swarm (handed to ADR-008)

1. **Playback model:** baked `MiniPose` JSON (or an equivalent pose stream), not AnimationMixer clips.
2. **Embed:** lazy WebGL on the **chat header** of an **extractable package**. Do not iframe Glance.
3. **Settings key:** one Rail store `swarm_avatar_theme` + reserved value `robot3d` (not selectable in Phase 0).
4. **Event hooks:** map existing chat/WS signals onto clip ids (`idle` / `listen` / `working`); see ADR-008 §6.
5. **Assets:** vendor/bake; do not expect STLs to appear from a git clone of the inspiration app.
6. **Combos:** socket + `MiniPose` split, not bone-name swap.

---

## 5. Follow-ups this report does **not** do

- Lock a specific mesh file or decimation budget (Phase 1, after LICENSE+NOTICE of the chosen tag).
- Implement the viewer.
- File GitHub Issues (this agent’s `gh` is read-only). Ready-to-file titles/bodies live in ADR-008 §10.
