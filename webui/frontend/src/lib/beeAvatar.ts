/**
 * Deterministic Bee avatar spec from an agent id (#801).
 * Variant (side-on | face-only) + brand-family accent are hashed.
 * Geometry comes from the shipped geometric WebUI mark (#778), not a third style.
 */

import { hashAgentId } from './blobAvatar'

export const BEE_VARIANTS = ['side-on', 'face-only'] as const
export type BeeVariant = (typeof BEE_VARIANTS)[number]

/** Golds already shipped on the geometric / minimal brand marks. */
export const BEE_ACCENTS = ['#EFAB22', '#EBA222', '#C48A1C'] as const
export type BeeAccent = (typeof BEE_ACCENTS)[number]

export const BEE_GAZES = ['left', 'right'] as const
export type BeeGaze = (typeof BEE_GAZES)[number]

export interface BeeEyePose {
  /** Pupil offset X inside each sclera (viewBox units). */
  x: number
  /** Pupil offset Y inside each sclera. */
  y: number
}

export interface BeeSpec {
  variant: BeeVariant
  accent: BeeAccent
  flip: boolean
  /** Face-only rest look: both pupils sit aside (googly “looking aside”). */
  gaze: BeeGaze
  rest: BeeEyePose
  wanderPhase: [number, number, number]
}

export function beeSpecForAgent(id: string): BeeSpec {
  const h = hashAgentId(id)
  const eyes = hashAgentId(`${id}:bee-eyes`)
  const variant = BEE_VARIANTS[h % BEE_VARIANTS.length]
  const gaze = BEE_GAZES[(h >>> 3) & 1]
  const aside = variant === 'face-only' ? 1.55 : 0.55
  const dir = gaze === 'left' ? -1 : 1
  return {
    variant,
    accent: BEE_ACCENTS[(h >>> 8) % BEE_ACCENTS.length],
    flip: Boolean((h >>> 16) & 1),
    gaze,
    rest: {
      x: dir * aside + (((eyes >>> 4) % 17) - 8) / 40,
      y: (((eyes >>> 12) % 13) - 6) / 40,
    },
    wanderPhase: [
      ((eyes >>> 2) % 628) / 100,
      ((eyes >>> 10) % 628) / 100,
      ((eyes >>> 18) % 628) / 100,
    ],
  }
}

/** Slow pupil wander — several-second periods, small travel. Same spirit as Blobs. */
export function wanderBeeEyePose(spec: BeeSpec, elapsedSec: number): BeeEyePose {
  const [p1, p2] = spec.wanderPhase
  const travel = spec.variant === 'face-only' ? 1.15 : 0.55
  const x = spec.rest.x + travel * Math.sin(elapsedSec * 0.52 + p1)
  const y = spec.rest.y + travel * 0.7 * Math.sin(elapsedSec * 0.37 + p2)
  const limit = spec.variant === 'face-only' ? 2.4 : 1.1
  return {
    x: clamp(x, -limit, limit),
    y: clamp(y, -limit, limit),
  }
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value))
}
