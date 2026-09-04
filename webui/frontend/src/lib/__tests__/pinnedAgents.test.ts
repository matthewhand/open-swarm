import { afterEach, describe, expect, it } from 'vitest'
import {
  PINNED_AGENTS_STORAGE_KEY,
  excludePinnedFromList,
  loadPinnedAgents,
  movePinnedAgent,
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

  it('reorders favourites and persists the new order', () => {
    const pinned = pinAgent({ id: 'stewie', name: 'Stewie' }, [{ id: 'codey', name: 'Codey' }])
    const next = movePinnedAgent('stewie', 'codey', pinned)
    expect(next.map((pin) => pin.id)).toEqual(['stewie', 'codey'])
    expect(loadPinnedAgents().map((pin) => pin.id)).toEqual(['stewie', 'codey'])
    expect(movePinnedAgent('stewie', 'stewie', next)).toEqual(next)
    expect(movePinnedAgent('missing', 'codey', next)).toEqual(next)
  })

  it('drops favourited ids from the rail list (move, not copy)', () => {
    const rows = [{ id: 'codey' }, { id: 'stewie' }, { id: 'support' }]
    const pins = pinAgent({ id: 'codey', name: 'Codey' }, [])
    expect(excludePinnedFromList(rows, pins).map((row) => row.id)).toEqual(['stewie', 'support'])
    expect(excludePinnedFromList(rows, unpinAgent('codey', pins)).map((row) => row.id)).toEqual([
      'codey',
      'stewie',
      'support',
    ])
  })
})
