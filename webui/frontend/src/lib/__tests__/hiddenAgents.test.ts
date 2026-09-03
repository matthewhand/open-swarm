import { afterEach, describe, expect, it } from 'vitest'
import {
  HIDDEN_AGENTS_STORAGE_KEY,
  agentMarkColor,
  canHideAgent,
  hideAgentId,
  hideAllAgentIds,
  loadHiddenAgentIds,
  saveHiddenAgentIds,
  unhideAgentId,
  unhideAllAgentIds,
} from '../hiddenAgents'

describe('hiddenAgents persistence', () => {
  afterEach(() => {
    localStorage.removeItem(HIDDEN_AGENTS_STORAGE_KEY)
  })

  it('starts empty when nothing is stored', () => {
    expect(loadHiddenAgentIds()).toEqual([])
  })

  it('hides an agent and persists across a reload-style read', () => {
    const next = hideAgentId('codey', [])
    expect(next).toEqual(['codey'])
    expect(JSON.parse(localStorage.getItem(HIDDEN_AGENTS_STORAGE_KEY) || '[]')).toEqual(['codey'])
    expect(loadHiddenAgentIds()).toEqual(['codey'])
  })

  it('hides all ids and unhides a single agent', () => {
    const afterAll = hideAllAgentIds(['codey', 'stewie'])
    expect(afterAll).toEqual(['codey', 'stewie'])
    expect(loadHiddenAgentIds()).toEqual(['codey', 'stewie'])
    const afterUnhide = unhideAgentId('codey', afterAll)
    expect(afterUnhide).toEqual(['stewie'])
    expect(unhideAllAgentIds()).toEqual([])
    expect(loadHiddenAgentIds()).toEqual([])
  })

  it('ignores corrupt storage and empty ids', () => {
    localStorage.setItem(HIDDEN_AGENTS_STORAGE_KEY, '{not-json')
    expect(loadHiddenAgentIds()).toEqual([])
    localStorage.setItem(HIDDEN_AGENTS_STORAGE_KEY, JSON.stringify([1, '', 'ok']))
    expect(loadHiddenAgentIds()).toEqual(['ok'])
    expect(hideAgentId('', ['ok'])).toEqual(['ok'])
  })

  it('assigns a stable small accent per agent id', () => {
    expect(agentMarkColor('codey')).toBe(agentMarkColor('codey'))
    expect(agentMarkColor('codey')).not.toBe(agentMarkColor('stewie'))
  })

  it('does not exempt role agents (support, gate, skeptic) from hide', () => {
    for (const id of ['support', 'gate', 'skeptic', 'codey']) {
      expect(canHideAgent(id)).toBe(true)
      expect(hideAgentId(id, [])).toEqual([id])
    }
  })
})
