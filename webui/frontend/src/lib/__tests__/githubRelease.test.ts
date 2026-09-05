import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  GITHUB_API_LATEST,
  GITHUB_API_TAGS,
  GITHUB_RELEASES_URL,
  fetchLatestGithubRelease,
  releasePageUrl,
  resetGithubReleaseCache,
} from '../githubRelease'

describe('githubRelease call-home', () => {
  afterEach(() => {
    resetGithubReleaseCache()
    vi.unstubAllGlobals()
  })

  it('builds an honest release-page URL', () => {
    expect(releasePageUrl('v0.5.5')).toBe(`${GITHUB_RELEASES_URL}/tag/v0.5.5`)
    expect(releasePageUrl('')).toBe(GITHUB_RELEASES_URL)
  })

  it('reads releases/latest and caches for the session', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        tag_name: 'v0.5.5',
        html_url: 'https://github.com/matthewhand/open-swarm/releases/tag/v0.5.5',
      }),
    })
    vi.stubGlobal('fetch', fetchMock)

    const first = await fetchLatestGithubRelease()
    const second = await fetchLatestGithubRelease()
    expect(first).toEqual({
      tag: 'v0.5.5',
      htmlUrl: 'https://github.com/matthewhand/open-swarm/releases/tag/v0.5.5',
    })
    expect(second).toEqual(first)
    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(String(fetchMock.mock.calls[0]?.[0])).toBe(GITHUB_API_LATEST)
    const init = fetchMock.mock.calls[0]?.[1] as RequestInit | undefined
    expect(JSON.stringify(init?.headers || {})).not.toMatch(/authorization/i)
    expect(JSON.stringify(init?.headers || {})).not.toMatch(/token/i)
  })

  it('falls back to tags when latest is missing and treats fetch failure as no signal', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({ ok: false, status: 404, json: async () => ({}) })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => [{ name: 'v0.5.5' }],
      })
    vi.stubGlobal('fetch', fetchMock)
    const hit = await fetchLatestGithubRelease()
    expect(hit).toEqual({
      tag: 'v0.5.5',
      htmlUrl: `${GITHUB_RELEASES_URL}/tag/v0.5.5`,
    })
    expect(String(fetchMock.mock.calls[1]?.[0])).toBe(GITHUB_API_TAGS)

    resetGithubReleaseCache()
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')))
    expect(await fetchLatestGithubRelease()).toBeNull()
  })
})
