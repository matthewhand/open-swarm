/**
 * Deterministic Blobs avatar spec from an agent id.
 * Shape + solid colour + idle eye rest pose are hashed; no blueprint rewrite.
 */

export const BLOB_SHAPES = [
  'hexagon',
  'circle',
  'teardrop',
  'triangle',
  'pill',
  'cloud',
  'roundedRect',
  'diamond',
] as const

export type BlobShape = (typeof BLOB_SHAPES)[number]

/** Vibrant solids matching Matthew's Blobs spec shot. */
export const BLOB_COLORS = [
  '#7C5CBF',
  '#5CD65C',
  '#E23B3B',
  '#8B7BA8',
  '#3B82F6',
  '#E84A8A',
  '#DC3C3C',
  '#F5A623',
  '#14B8A6',
  '#A855F7',
  '#22C55E',
  '#F97316',
] as const

export interface BlobEyePose {
  /** Pair center X in the 40×40 viewBox. */
  x: number
  /** Pair center Y in the 40×40 viewBox. */
  y: number
  /** Rotation of the pair / gaze, degrees. */
  angle: number
}

export interface BlobSpec {
  shape: BlobShape
  color: string
  rest: BlobEyePose
  wanderPhase: [number, number, number]
}

export function hashAgentId(id: string): number {
  let hash = 2166136261
  const source = id.length > 0 ? id : 'agent'
  for (let i = 0; i < source.length; i += 1) {
    hash ^= source.charCodeAt(i)
    hash = Math.imul(hash, 16777619)
  }
  return hash >>> 0
}

export function blobSpecForAgent(id: string): BlobSpec {
  const h = hashAgentId(id)
  const eyes = hashAgentId(`${id}:eyes`)
  return {
    shape: BLOB_SHAPES[h % BLOB_SHAPES.length],
    color: BLOB_COLORS[(h >>> 8) % BLOB_COLORS.length],
    rest: {
      x: 17 + ((eyes >>> 4) % 70) / 10,
      y: 15.5 + ((eyes >>> 12) % 45) / 10,
      angle: -20 + ((eyes >>> 20) % 41),
    },
    wanderPhase: [
      ((eyes >>> 2) % 628) / 100,
      ((eyes >>> 10) % 628) / 100,
      ((eyes >>> 18) % 628) / 100,
    ],
  }
}

/** Slow wander — several-second periods, small travel. Not a seizure. */
export function wanderEyePose(spec: BlobSpec, elapsedSec: number): BlobEyePose {
  const [p1, p2, p3] = spec.wanderPhase
  const x = spec.rest.x + 3.1 * Math.sin(elapsedSec * 0.52 + p1)
  const y = spec.rest.y + 2.2 * Math.sin(elapsedSec * 0.37 + p2)
  const angle = spec.rest.angle + 12 * Math.sin(elapsedSec * 0.29 + p3)
  return {
    x: clamp(x, 14, 26),
    y: clamp(y, 13, 24),
    angle: clamp(angle, -28, 28),
  }
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value))
}
