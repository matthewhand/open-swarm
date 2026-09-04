import { afterEach, describe, expect, it } from 'vitest'
import {
  PINNED_AGENTS_STORAGE_KEY,
  loadPinnedAgents,
  pinAgent,
  unpinAgent,
} from '../pinnedAgents'

describe('pinnedAgents persistence', () => {
  afterEach(() => {
    localStorage.removeItem(PINNED_AGENTS_STORAGE_KEY)
  })

  it('starts empty and pins without duplicates', () => {
    expect(loadPinnedAgents()).toEqual([])
    const next = pinAgent({ id: 'codey', name: 'Codey' }, [])
    expect(next).toEqual([{ id: 'codey', name: 'Codey' }])
    expect(pinAgent({ id: 'codey', name: 'Codey' }, next)).toEqual(next)
    expect(loadPinnedAgents()).toEqual([{ id: 'codey', name: 'Codey' }])
  })

  it('unpins a single favourite', () => {
    const pinned = pinAgent({ id: 'stewie', name: 'Stewie' }, [{ id: 'codey', name: 'Codey' }])
    expect(unpinAgent('codey', pinned)).toEqual([{ id: 'stewie', name: 'Stewie' }])
    expect(loadPinnedAgents()).toEqual([{ id: 'stewie', name: 'Stewie' }])
  })
})
