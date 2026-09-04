import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { HIDDEN_AGENTS_STORAGE_KEY } from '../hiddenAgents'
import { DEFAULT_PINNED_SUPPORT, PINNED_AGENTS_STORAGE_KEY } from '../pinnedAgents'
import {
  USER_PREFS_PATH,
  hydrateRailPrefs,
  parseUserPrefs,
  saveUserPrefs,
} from '../userPrefs'

function jsonResponse(body: unknown, ok = true) {
  return {
    ok,
    status: ok ? 200 : 400,
    json: async () => body,
  } as Response
}

describe('userPrefs', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    localStorage.clear()
  })

  it('parses a user_preferences payload and rejects other shapes', () => {
    expect(parseUserPrefs({ object: 'list', data: [] })).toBeNull()
    expect(
      parseUserPrefs({
        object: 'user_preferences',
        principal: 'user:alice',
        guest: false,
        empty: false,
        favourites: [{ id: 'codey', name: 'Codey' }, { id: 'codey' }, 'stewie'],
        hidden_agents: ['gate', '', 'skeptic'],
      }),
    ).toEqual({
      object: 'user_preferences',
      principal: 'user:alice',
      guest: false,
      empty: false,
      favourites: [
        { id: 'codey', name: 'Codey' },
        { id: 'stewie', name: 'stewie' },
      ],
      hidden_agents: ['gate', 'skeptic'],
      values: {},
    })
  })

  it('uses the server bag when it is not empty (server wins)', async () => {
    localStorage.setItem(PINNED_AGENTS_STORAGE_KEY, JSON.stringify([{ id: 'old', name: 'Old' }]))
    localStorage.setItem(HIDDEN_AGENTS_STORAGE_KEY, JSON.stringify(['stale']))
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        jsonResponse({
          object: 'user_preferences',
          principal: 'user:alice',
          empty: false,
          favourites: [{ id: 'codey', name: 'Codey' }, { id: 'support', name: 'Support' }],
          hidden_agents: ['gate'],
        }),
      ),
    )

    const next = await hydrateRailPrefs([{ id: 'gate', name: 'Gate' }])
    expect(next.source).toBe('server')
    expect(next.pins.map((pin) => pin.id)).toEqual(['codey', 'support'])
    expect(next.hidden).toEqual(['gate'])
    expect(JSON.parse(localStorage.getItem(PINNED_AGENTS_STORAGE_KEY) || '[]').map((p: { id: string }) => p.id)).toEqual([
      'codey',
      'support',
    ])
    expect(JSON.parse(localStorage.getItem(HIDDEN_AGENTS_STORAGE_KEY) || '[]')).toEqual(['gate'])
  })

  it('imports localStorage once when the server bag is empty', async () => {
    localStorage.setItem(
      PINNED_AGENTS_STORAGE_KEY,
      JSON.stringify([{ id: 'codey', name: 'Codey' }]),
    )
    localStorage.setItem(HIDDEN_AGENTS_STORAGE_KEY, JSON.stringify(['skeptic']))
    const fetchMock = vi.fn().mockImplementation(async (_url: RequestInfo, init?: RequestInit) => {
      if (init?.method === 'PATCH') {
        const body = JSON.parse(String(init.body || '{}'))
        return jsonResponse({
          object: 'user_preferences',
          empty: false,
          favourites: body.favourites,
          hidden_agents: body.hidden_agents,
        })
      }
      return jsonResponse({
        object: 'user_preferences',
        empty: true,
        favourites: [],
        hidden_agents: [],
      })
    })
    vi.stubGlobal('fetch', fetchMock)

    const next = await hydrateRailPrefs()
    expect(next.source).toBe('import')
    expect(next.pins).toEqual([{ id: 'codey', name: 'Codey' }])
    expect(next.hidden).toEqual(['skeptic'])
    const patchCall = fetchMock.mock.calls.find((call) => call[1]?.method === 'PATCH')
    expect(patchCall?.[0]).toContain(USER_PREFS_PATH)
    const sent = JSON.parse(String(patchCall?.[1]?.body || '{}'))
    expect(sent.favourites).toEqual([{ id: 'codey', name: 'Codey' }])
    expect(sent.hidden_agents).toEqual(['skeptic'])
  })

  it('seeds Support + default hidden, then imports, when both stores are empty', async () => {
    const fetchMock = vi.fn().mockImplementation(async (_url: RequestInfo, init?: RequestInit) => {
      if (init?.method === 'PATCH') {
        const body = JSON.parse(String(init.body || '{}'))
        return jsonResponse({
          object: 'user_preferences',
          empty: false,
          favourites: body.favourites,
          hidden_agents: body.hidden_agents,
        })
      }
      return jsonResponse({
        object: 'user_preferences',
        empty: true,
        favourites: [],
        hidden_agents: [],
      })
    })
    vi.stubGlobal('fetch', fetchMock)

    const catalog = [
      { id: 'support', name: 'Support' },
      { id: 'tool_gate', name: 'Gate' },
      { id: 'skeptic', name: 'Skeptic' },
    ]
    const next = await hydrateRailPrefs(catalog)
    expect(next.source).toBe('import')
    expect(next.pins).toEqual([DEFAULT_PINNED_SUPPORT])
    expect(next.hidden).toEqual(['tool_gate', 'skeptic'])
  })

  it('keeps localStorage when the API is offline or the shape is wrong', async () => {
    localStorage.setItem(
      PINNED_AGENTS_STORAGE_KEY,
      JSON.stringify([{ id: 'codey', name: 'Codey' }]),
    )
    localStorage.setItem(HIDDEN_AGENTS_STORAGE_KEY, JSON.stringify(['codey']))
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(jsonResponse({ object: 'list', data: [] })),
    )

    const next = await hydrateRailPrefs()
    expect(next.source).toBe('local')
    expect(next.pins).toEqual([{ id: 'codey', name: 'Codey' }])
    expect(next.hidden).toEqual(['codey'])
  })

  it('saveUserPrefs writes the PATCH body', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({
        object: 'user_preferences',
        empty: false,
        favourites: [{ id: 'support', name: 'Support' }],
        hidden_agents: ['gate'],
      }),
    )
    vi.stubGlobal('fetch', fetchMock)
    const saved = await saveUserPrefs({
      favourites: [{ id: 'support', name: 'Support' }],
      hidden_agents: ['gate'],
    })
    expect(saved?.favourites).toEqual([{ id: 'support', name: 'Support' }])
    expect(fetchMock).toHaveBeenCalled()
    const call = fetchMock.mock.calls.find((entry) => entry[1]?.method === 'PATCH')
    expect(call).toBeTruthy()
    expect(String(call?.[0])).toContain(USER_PREFS_PATH)
  })
})
