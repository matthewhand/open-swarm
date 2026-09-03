import { afterEach, describe, expect, it, vi } from 'vitest'
import { addRemote, fetchRemotes, operateRemote, probeRemoteHealth } from '../api'

describe('remotes API client (REQ-61)', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('lists an empty catalog without default cards', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({ object: 'list', data: [], kinds: [{ id: 'hermes', complete: true }] }),
      } as Response),
    )
    const listed = await fetchRemotes()
    expect(listed.data).toEqual([])
    expect(listed.kinds[0]?.id).toBe('hermes')
  })

  it('adds hermes with base URL + api-key-env name only', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        id: 'hermes',
        kind: 'hermes',
        base_url: 'http://127.0.0.1:9',
        api_key_env: 'HERMES_API_KEY',
        added: true,
      }),
    } as Response)
    vi.stubGlobal('fetch', fetchMock)
    const row = await addRemote({
      kind: 'hermes',
      base_url: 'http://127.0.0.1:9',
      api_key_env: 'HERMES_API_KEY',
    })
    expect(row.kind).toBe('hermes')
    expect(JSON.stringify(fetchMock.mock.calls[0]?.[1]?.body)).not.toMatch(/sk-|token/i)
    expect(fetchMock.mock.calls[0]?.[1]?.body).toContain('HERMES_API_KEY')
  })

  it('health and operate post to the documented Hermes routes', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ ok: true, state: 'UP', detail: 'up', op: 'list' }),
    } as Response)
    vi.stubGlobal('fetch', fetchMock)
    await probeRemoteHealth('hermes')
    await operateRemote('hermes', 'list')
    await operateRemote('hermes', 'send', 'status')
    const urls = fetchMock.mock.calls.map((call) => String(call[0]))
    expect(urls[0]).toBe('/v1/remotes/hermes/health/')
    expect(urls[1]).toBe('/v1/remotes/hermes/operate/')
    expect(JSON.parse(String(fetchMock.mock.calls[2]?.[1]?.body))).toEqual({
      op: 'send',
      prompt: 'status',
      target: '',
    })
  })
})
