import { afterEach, describe, expect, it } from 'vitest'
import {
  PINNED_AGENTS_STORAGE_KEY,
  beginAgentDrag,
  endAgentDrag,
  loadPinnedAgents,
  parseAgentDragPayload,
  peekAgentDrag,
  pinAgent,
  savePinnedAgents,
  unpinAgent,
  writeAgentDragPayload,
} from '../pinnedAgents'

function mockDataTransfer() {
  const store: Record<string, string> = {}
  const types: string[] = []
  return {
    dropEffect: 'none',
    effectAllowed: 'all' as const,
    types,
    setData(type: string, value: string) {
      store[type] = value
      if (!types.includes(type)) types.push(type)
    },
    getData(type: string) {
      return store[type] ?? ''
    },
    clearData() {
      Object.keys(store).forEach((key) => delete store[key])
      types.length = 0
    },
  } as unknown as DataTransfer
}

describe('pinnedAgents persistence', () => {
  afterEach(() => {
    endAgentDrag()
    localStorage.removeItem(PINNED_AGENTS_STORAGE_KEY)
  })

  it('starts empty when nothing is stored', () => {
    expect(loadPinnedAgents()).toEqual([])
  })

  it('pins an agent and persists across a reload-style read', () => {
    const next = pinAgent({ id: 'codey', name: 'Codey' }, [])
    expect(next).toEqual([{ id: 'codey', name: 'Codey' }])
    expect(JSON.parse(localStorage.getItem(PINNED_AGENTS_STORAGE_KEY) || '[]')).toEqual([
      { id: 'codey', name: 'Codey' },
    ])
    expect(loadPinnedAgents()).toEqual([{ id: 'codey', name: 'Codey' }])
  })

  it('is a copy/pin: pinning twice does not duplicate or require hide-all', () => {
    const once = pinAgent({ id: 'codey', name: 'Codey' }, [])
    const twice = pinAgent({ id: 'codey', name: 'Codey' }, once)
    expect(twice).toEqual([{ id: 'codey', name: 'Codey' }])
    const withStewie = pinAgent({ id: 'stewie', name: 'Stewie' }, twice)
    expect(withStewie).toEqual([
      { id: 'codey', name: 'Codey' },
      { id: 'stewie', name: 'Stewie' },
    ])
    expect(unpinAgent('codey', withStewie)).toEqual([{ id: 'stewie', name: 'Stewie' }])
    expect(loadPinnedAgents()).toEqual([{ id: 'stewie', name: 'Stewie' }])
  })

  it('accepts legacy id-only storage and ignores corrupt entries', () => {
    localStorage.setItem(PINNED_AGENTS_STORAGE_KEY, '{not-json')
    expect(loadPinnedAgents()).toEqual([])
    localStorage.setItem(PINNED_AGENTS_STORAGE_KEY, JSON.stringify(['codey', { id: 'stewie', name: 'Stewie' }, 1, '']))
    expect(loadPinnedAgents()).toEqual([
      { id: 'codey', name: 'codey' },
      { id: 'stewie', name: 'Stewie' },
    ])
    expect(pinAgent({ id: '', name: 'Nope' }, [])).toEqual([])
  })

  it('round-trips HTML5 drag payload and the in-memory drag session', () => {
    const dt = mockDataTransfer()
    writeAgentDragPayload(dt, { id: 'codey', name: 'Codey' })
    expect(peekAgentDrag()).toEqual({ id: 'codey', name: 'Codey' })
    expect(parseAgentDragPayload(dt)).toEqual({ id: 'codey', name: 'Codey' })
    endAgentDrag()
    expect(parseAgentDragPayload(dt)).toEqual({ id: 'codey', name: 'Codey' })
    beginAgentDrag({ id: 'stewie', name: 'Stewie' })
    expect(parseAgentDragPayload(dt)).toEqual({ id: 'stewie', name: 'Stewie' })
  })

  it('savePinnedAgents de-duplicates empty and repeated ids', () => {
    savePinnedAgents([
      { id: 'codey', name: 'Codey' },
      { id: 'codey', name: 'Codey 2' },
      { id: '', name: 'skip' },
    ])
    expect(loadPinnedAgents()).toEqual([{ id: 'codey', name: 'Codey' }])
  })
})
