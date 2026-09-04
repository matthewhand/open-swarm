import { describe, expect, it } from 'vitest'
import { BLOB_SHAPES, blobSpecForAgent, wanderEyePose } from '../blobAvatar'

describe('blob spec from agent id', () => {
  it('is deterministic and varies by id', () => {
    expect(blobSpecForAgent('codey')).toEqual(blobSpecForAgent('codey'))
    expect(blobSpecForAgent('codey')).not.toEqual(blobSpecForAgent('stewie'))
    expect(BLOB_SHAPES).toContain(blobSpecForAgent('codey').shape)
  })

  it('keeps idle rest pose stable and active wander inside the blob', () => {
    const spec = blobSpecForAgent('reachy')
    const idle = wanderEyePose(spec, 0)
    expect(idle.x).toBeGreaterThanOrEqual(14)
    expect(idle.x).toBeLessThanOrEqual(26)
    const later = wanderEyePose(spec, 4.5)
    expect(later.x).not.toBe(spec.rest.x)
    expect(later.y).toBeGreaterThanOrEqual(13)
    expect(later.y).toBeLessThanOrEqual(24)
    expect(Math.abs(later.angle)).toBeLessThanOrEqual(28)
  })
})
