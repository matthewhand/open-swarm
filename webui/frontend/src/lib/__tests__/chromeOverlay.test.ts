import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  OPEN_LLM_PROFILES_EVENT,
  OPEN_SETTINGS_EVENT,
  OPEN_TEAMS_EVENT,
  OVERLAY_CLOSED_EVENT,
  notifyOverlayClosed,
  openChromeOverlay,
} from '../chromeOverlay'

describe('chromeOverlay', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('dispatches overlay-open events without using a React route', () => {
    const settings = vi.fn()
    const teams = vi.fn()
    const profiles = vi.fn()
    window.addEventListener(OPEN_SETTINGS_EVENT, settings)
    window.addEventListener(OPEN_TEAMS_EVENT, teams)
    window.addEventListener(OPEN_LLM_PROFILES_EVENT, profiles)
    openChromeOverlay('settings')
    openChromeOverlay('teams')
    openChromeOverlay('llm-profiles')
    expect(settings).toHaveBeenCalledTimes(1)
    expect(teams).toHaveBeenCalledTimes(1)
    expect(profiles).toHaveBeenCalledTimes(1)
    window.removeEventListener(OPEN_SETTINGS_EVENT, settings)
    window.removeEventListener(OPEN_TEAMS_EVENT, teams)
    window.removeEventListener(OPEN_LLM_PROFILES_EVENT, profiles)
  })

  it('notifies Chat when an overlay closes', () => {
    const closed = vi.fn()
    window.addEventListener(OVERLAY_CLOSED_EVENT, closed)
    notifyOverlayClosed()
    expect(closed).toHaveBeenCalledTimes(1)
    window.removeEventListener(OVERLAY_CLOSED_EVENT, closed)
  })
})
