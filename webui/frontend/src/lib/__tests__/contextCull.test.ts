import { describe, expect, it } from 'vitest'
import {
  DEFAULT_CULL_FRACTION_PCT,
  DEFAULT_CULL_TRIGGER_PCT,
  START_CONTEXT_FROM_HERE_LABEL,
  START_CONTEXT_FROM_HERE_TOOLTIP,
  lastEventLabel,
  overFullWarningCopy,
  parseContextMeta,
  parseContextStrategy,
  parseCullFractionPct,
  parseCullTriggerPct,
  strategyLabel,
  wouldWarnAfterStart,
} from '../contextCull'

describe('REQ-121 context cull helpers', () => {
  it('defaults strategy to compress and cull knobs to 90 / 50', () => {
    expect(parseContextStrategy(undefined)).toBe('compress')
    expect(parseContextStrategy('cull')).toBe('cull')
    expect(parseCullTriggerPct(undefined)).toBe(DEFAULT_CULL_TRIGGER_PCT)
    expect(parseCullFractionPct(undefined)).toBe(DEFAULT_CULL_FRACTION_PCT)
    expect(parseCullTriggerPct(0)).toBe(1)
    expect(parseCullFractionPct(150)).toBe(99)
  })

  it('warns only when remaining usage is still at or above the cull trigger', () => {
    expect(wouldWarnAfterStart(90, null, 90)).toBe(false)
    expect(wouldWarnAfterStart(89, 100, 90)).toBe(false)
    expect(wouldWarnAfterStart(90, 100, 90)).toBe(true)
    expect(overFullWarningCopy(93, 90)).toContain('93%')
    expect(overFullWarningCopy(93, 90)).toContain('cull trigger 90%')
    expect(overFullWarningCopy(93, 90)).toMatch(/Confirm to proceed or cancel/)
  })

  it('parses context meta and labels last events without prompt text', () => {
    expect(parseContextMeta({ start_offset: 4, last_event: { kind: 'cull', at: '2026-09-05T00:00:00Z' } })).toEqual({
      start_offset: 4,
      last_event: { kind: 'cull', at: '2026-09-05T00:00:00Z' },
    })
    expect(lastEventLabel({ kind: 'start_from_here' })).toBe(START_CONTEXT_FROM_HERE_LABEL)
    expect(lastEventLabel({ kind: 'cull' })).toBe('Auto cull')
    expect(lastEventLabel({ kind: 'compress' })).toBe('Compress')
    expect(strategyLabel('cull')).toBe('Cull')
    expect(START_CONTEXT_FROM_HERE_TOOLTIP).toBe('Start context from here.')
  })
})
