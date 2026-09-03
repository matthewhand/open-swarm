import { describe, expect, it } from 'vitest'
import {
  STACK_FACE_LIMIT,
  WORKING_PULSE_MS,
  isAvatarStack,
  parseStartedAt,
  selectStackedFaces,
  stackAnimationDelayMs,
  stackAnimationDelayStyle,
  type StackFace,
} from '../avatarStack'

function face(id: string, startedAt: number): StackFace {
  return { id, name: id, startedAt }
}

describe('avatarStack (REQ-68 / REQ-66 shared)', () => {
  it('keeps the 3 most recent faces and a remainder for a team of 5', () => {
    const picked = selectStackedFaces([
      face('a', 1000),
      face('b', 2000),
      face('c', 3000),
      face('d', 4000),
      face('e', 5000),
    ])
    expect(STACK_FACE_LIMIT).toBe(3)
    expect(picked.faces.map((row) => row.id)).toEqual(['e', 'd', 'c'])
    expect(picked.remainder).toBe(2)
    expect(isAvatarStack(picked.faces.length, picked.remainder)).toBe(true)
  })

  it('does not stack a single-agent remote', () => {
    const picked = selectStackedFaces([face('hermes', 1000)])
    expect(picked.faces).toHaveLength(1)
    expect(picked.remainder).toBe(0)
    expect(isAvatarStack(picked.faces.length, picked.remainder)).toBe(false)
  })

  it('staggers animation-delay from started_at so 3 faces are not lockstep', () => {
    const delays = [1000, 1400, 1800].map((startedAt) =>
      stackAnimationDelayMs(startedAt, 1000),
    )
    expect(delays).toEqual([0, 400, 800])
    expect(new Set(delays).size).toBe(3)
    expect(stackAnimationDelayStyle(1400, 1000)).toEqual({ animationDelay: '400ms' })
    expect(stackAnimationDelayMs(1000 + WORKING_PULSE_MS + 50, 1000)).toBe(50)
  })

  it('parses ISO started_at and numeric fallbacks', () => {
    expect(parseStartedAt('2026-09-03T00:00:00.000Z')).toBe(Date.parse('2026-09-03T00:00:00.000Z'))
    expect(parseStartedAt(42)).toBe(42)
    expect(parseStartedAt('nope', 7)).toBe(7)
  })
})
