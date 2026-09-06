import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  ROLE_AGENT_TIP_PREF_KEY,
  ROLE_AGENT_TIP_STORAGE_KEY,
  hydrateRoleAgentTipDismissed,
  isRoleAgentTipDismissed,
  persistRoleAgentTipDismissed,
  persistRoleAgentTipDismissedLocal,
  prefsRoleAgentTipDismissed,
  shouldShowRoleAgentTip,
} from '../roleAgentTip'

function jsonResponse(body: unknown) {
  return {
    ok: true,
    status: 200,
    json: async () => body,
  } as Response
}

function prefsPayload(values: Record<string, unknown> = {}, empty = false) {
  return {
    object: 'user_preferences',
    principal: 'session:test',
    guest: true,
    empty,
    favourites: [],
    hidden_agents: [],
    hostname_override: '',
    values,
  }
}

describe('roleAgentTip', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    localStorage.clear()
  })

  it('shows only for role seats that are not team/remote and not dismissed', () => {
    expect(
      shouldShowRoleAgentTip({
        agent: { id: 'support', name: 'Support', role: 'support' },
      }),
    ).toBe(true)
    expect(
      shouldShowRoleAgentTip({
        agent: { id: 'gate', name: 'Safety' },
      }),
    ).toBe(true)
    expect(
      shouldShowRoleAgentTip({
        agent: { id: 'codey', name: 'Codey' },
      }),
    ).toBe(false)
    expect(
      shouldShowRoleAgentTip({
        teamId: 'office',
        agent: { id: 'support', role: 'support' },
      }),
    ).toBe(false)
    expect(
      shouldShowRoleAgentTip({
        remoteId: 'hermes',
        agent: { id: 'support', role: 'support' },
      }),
    ).toBe(false)
    expect(
      shouldShowRoleAgentTip({
        dismissed: true,
        agent: { id: 'support', role: 'support' },
      }),
    ).toBe(false)
    expect(shouldShowRoleAgentTip({ agent: null })).toBe(false)
  })

  it('persists dismiss in localStorage', () => {
    expect(isRoleAgentTipDismissed()).toBe(false)
    persistRoleAgentTipDismissedLocal()
    expect(localStorage.getItem(ROLE_AGENT_TIP_STORAGE_KEY)).toBe('1')
    expect(isRoleAgentTipDismissed()).toBe(true)
  })

  it('reads dismissed from prefs extras and PATCHes the extras bag', async () => {
    expect(prefsRoleAgentTipDismissed({ values: { [ROLE_AGENT_TIP_PREF_KEY]: true } })).toBe(true)
    expect(prefsRoleAgentTipDismissed({ values: {} })).toBe(false)

    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse(prefsPayload({ [ROLE_AGENT_TIP_PREF_KEY]: true })),
    )
    vi.stubGlobal('fetch', fetchMock)
    await persistRoleAgentTipDismissed()
    expect(isRoleAgentTipDismissed()).toBe(true)
    expect(fetchMock).toHaveBeenCalled()
    const patchCall = fetchMock.mock.calls.find((call) => String(call[0]).includes('/v1/preferences/'))
    expect(patchCall).toBeTruthy()
  })

  it('hydrates dismissed from the server bag', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(jsonResponse(prefsPayload({ [ROLE_AGENT_TIP_PREF_KEY]: true }))),
    )
    await expect(hydrateRoleAgentTipDismissed()).resolves.toBe(true)
    expect(isRoleAgentTipDismissed()).toBe(true)
  })

  it('imports a local dismiss when the server bag lacks the key', async () => {
    persistRoleAgentTipDismissedLocal()
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(prefsPayload({}, true)))
    vi.stubGlobal('fetch', fetchMock)
    await expect(hydrateRoleAgentTipDismissed()).resolves.toBe(true)
    expect(fetchMock.mock.calls.length).toBeGreaterThan(1)
  })
})
