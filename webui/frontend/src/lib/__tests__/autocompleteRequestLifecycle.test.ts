import { afterEach, expect, it, vi } from 'vitest'
import { enhancePrompt, fetchAutocomplete } from '../api/llm'

afterEach(() => vi.unstubAllGlobals())

it.each(['autocomplete', 'rewrite'])('forwards %s cancellation as a fetch signal, never as model payload', async kind => {
  const controller = new AbortController()
  const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ completion: ' world', enhanced: 'Hello world' }) })
  vi.stubGlobal('fetch', fetchMock)
  if (kind === 'autocomplete') await fetchAutocomplete('Hello', { agent_id: 'api' }, controller.signal)
  else await enhancePrompt('Hello', controller.signal)
  expect(fetchMock).toHaveBeenCalledOnce()
  const init = fetchMock.mock.calls[0][1] as RequestInit
  expect(init.signal).toBe(controller.signal)
  const body = JSON.parse(String(init.body))
  expect(body).not.toHaveProperty('signal')
  expect(body).toEqual(kind === 'autocomplete' ? { prefix: 'Hello', agent_id: 'api' } : { prompt: 'Hello' })
})
