import { describe, expect, it } from 'vitest'
import {
  SUPPORT_JOURNEY_FIXTURE,
  SUPPORT_JOURNEY_KICKSTART,
  isSupportJourneyConsumer,
  supportJourneyKickstart,
} from '../supportJourney'

describe('supportJourney (REQ-137)', () => {
  it('locks first-run kickstart phrases', () => {
    const chips = supportJourneyKickstart()
    expect(chips).toEqual([...SUPPORT_JOURNEY_KICKSTART])
    const joined = chips.join(' ').toLowerCase()
    expect(joined).toContain('create a team')
    expect(joined).toContain('ba → engineer → tester')
    expect(joined).toContain('add a remote')
    expect(joined).toContain('wire a cli')
    expect(SUPPORT_JOURNEY_FIXTURE).toBe('ONBOARD_JOURNEY_CLI_API_REMOTE')
  })

  it('recognises Support consumers only', () => {
    expect(isSupportJourneyConsumer('support')).toBe(true)
    expect(isSupportJourneyConsumer('starter-support')).toBe(true)
    expect(isSupportJourneyConsumer('codey')).toBe(false)
    expect(isSupportJourneyConsumer('')).toBe(false)
  })
})
