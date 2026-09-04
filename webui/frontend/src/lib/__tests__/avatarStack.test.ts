import { describe, expect, it } from 'vitest'
import {
  STACK_FACE_LIMIT,
  STACK_PULSE_MS,
  isAvatarStack,
  parseStartedAt,
  selectStackedFaces,
  stackAnimationDelayMs,
  type StackFace,
} from '../avatarStack'

function face(id: string, startedAt: number): StackFace {
  return { id, name: id, startedAt }
}

describe('avatarStack', () => {
  it('caps at 3 faces plus a remainder so #398 can reuse the same plan', () => {
    const five = [1, 2, 3, 4, 5].map((n) => face(`m${n}`, n * 100))
    const plan = selectStackedFaces(five)
    expect(STACK_FACE_LIMIT).toBe(3)
    expect(plan.faces).toHaveLength(3)
    expect(plan.remainder).toBe(2)
    expect(plan.faces.map((row) => row.id)).toEqual(['m5', 'm4', 'm3'])
  })

  it('staggers animation delay by startedAt so four faces do not lockstep', () => {
    const startedAt = [1_000, 1_200, 1_400, 1_600]
    const delays = startedAt.map((value) => stackAnimationDelayMs(value, startedAt[0]))
    expect(delays).toEqual([0, 200, 400, 600])
    expect(new Set(delays).size).toBe(4)
    expect(delays.every((ms) => ms < STACK_PULSE_MS)).toBe(true)
  })

  it('treats a single face with no remainder as not a stack', () => {
    expect(isAvatarStack(1, 0)).toBe(false)
    expect(isAvatarStack(2, 0)).toBe(true)
    expect(isAvatarStack(1, 1)).toBe(true)
  })

  it('parses startedAt from a number, ISO string, or fallback index', () => {
    expect(parseStartedAt(1500, 9)).toBe(1500)
    expect(parseStartedAt('2020-01-01T00:00:00.000Z', 9)).toBe(Date.parse('2020-01-01T00:00:00.000Z'))
    expect(parseStartedAt(undefined, 4)).toBe(4)
  })
})
