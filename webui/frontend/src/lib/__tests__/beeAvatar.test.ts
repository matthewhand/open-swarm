import { describe, expect, it } from 'vitest'
import {
  BEE_ACCENTS,
  BEE_VARIANTS,
  beeSpecForAgent,
  wanderBeeEyePose,
} from '../beeAvatar'

describe('bee spec from agent id', () => {
  it('is deterministic and varies by id', () => {
    expect(beeSpecForAgent('codey')).toEqual(beeSpecForAgent('codey'))
    expect(beeSpecForAgent('codey')).not.toEqual(beeSpecForAgent('stewie'))
    expect(BEE_VARIANTS).toContain(beeSpecForAgent('codey').variant)
    expect(BEE_ACCENTS).toContain(beeSpecForAgent('codey').accent)
  })

  it('assigns both locked variants across a roster', () => {
    const variants = new Set(
      ['codey', 'stewie', 'reachy', 'jeeves', 'atlas', 'nova', 'oriole', 'pip'].map(
        (id) => beeSpecForAgent(id).variant,
      ),
    )
    expect(variants.has('side-on')).toBe(true)
    expect(variants.has('face-only')).toBe(true)
  })

  it('keeps face-only rest gaze aside and wander inside the sclera', () => {
    const face = ['codey', 'stewie', 'reachy', 'jeeves', 'atlas', 'nova'].find(
      (id) => beeSpecForAgent(id).variant === 'face-only',
    )
    expect(face).toBeDefined()
    const spec = beeSpecForAgent(face as string)
    expect(Math.abs(spec.rest.x)).toBeGreaterThan(1)
    expect(spec.gaze === 'left' || spec.gaze === 'right').toBe(true)
    const later = wanderBeeEyePose(spec, 4.5)
    expect(later.x).not.toBe(spec.rest.x)
    expect(Math.abs(later.x)).toBeLessThanOrEqual(2.4)
    expect(Math.abs(later.y)).toBeLessThanOrEqual(2.4)
  })
})
