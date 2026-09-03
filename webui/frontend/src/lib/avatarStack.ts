/**
 * Shared stacked-avatar math for scale-out rails (REQ-66 #394, REQ-68 #398).
 *
 * One rail row shows at most {@link STACK_FACE_LIMIT} faces (most recently
 * active) plus a remainder. Every face in a team/remote stack is animated;
 * phase is staggered from `startedAt` so the stack does not pulse in lockstep.
 *
 * #394 (agent session stacks) should import these helpers and `AvatarStack`
 * rather than forking the widget.
 */

export const STACK_FACE_LIMIT = 3

/** Same period as the working-agent / running-tool pulse. */
export const WORKING_PULSE_MS = 1350

export interface StackFace {
  id: string
  name: string
  startedAt: number
  role?: string
  working?: boolean
}

export interface StackSelection<T extends StackFace = StackFace> {
  faces: T[]
  remainder: number
}

export function parseStartedAt(value: unknown, fallback = 0): number {
  if (typeof value === 'number' && Number.isFinite(value)) return value
  if (typeof value === 'string' && value.trim()) {
    const ms = Date.parse(value)
    if (!Number.isNaN(ms)) return ms
    const asNum = Number(value)
    if (Number.isFinite(asNum)) return asNum
  }
  return fallback
}

/** Most recent `limit` faces, remainder is how many did not fit. */
export function selectStackedFaces<T extends StackFace>(
  faces: T[],
  limit = STACK_FACE_LIMIT,
): StackSelection<T> {
  const sorted = [...faces].sort((a, b) => {
    if (b.startedAt !== a.startedAt) return b.startedAt - a.startedAt
    return a.id.localeCompare(b.id)
  })
  const visible = sorted.slice(0, Math.max(0, limit))
  return {
    faces: visible,
    remainder: Math.max(0, faces.length - visible.length),
  }
}

export function earliestStartedAt(faces: Array<{ startedAt: number }>): number {
  if (faces.length === 0) return 0
  return faces.reduce((min, face) => Math.min(min, face.startedAt), faces[0].startedAt)
}

/**
 * Animation phase offset so a later `startedAt` starts later in the pulse.
 * Same motion language for every face — only the delay changes.
 */
export function stackAnimationDelayMs(
  startedAt: number,
  earliest: number,
  periodMs = WORKING_PULSE_MS,
): number {
  const delta = Math.max(0, startedAt - earliest)
  if (periodMs <= 0) return delta
  return delta % periodMs
}

export function stackAnimationDelayStyle(
  startedAt: number,
  earliest: number,
  periodMs = WORKING_PULSE_MS,
): { animationDelay: string } {
  return { animationDelay: `${stackAnimationDelayMs(startedAt, earliest, periodMs)}ms` }
}

/** A single face is not a stack (no overlap, no remainder chip). */
export function isAvatarStack(faces: number, remainder = 0): boolean {
  return faces > 1 || remainder > 0
}
