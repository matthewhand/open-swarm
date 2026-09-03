import { afterEach, describe, expect, it } from 'vitest'
import {
  DEFAULT_HIDDEN_AGENT_IDS,
  HIDDEN_AGENTS_STORAGE_KEY,
  agentMarkColor,
  canHideAgent,
  defaultHiddenAgentIds,
  hideAgentId,
  loadHiddenAgentIds,
  loadOrSeedHiddenAgentIds,
  saveHiddenAgentIds,
  unhideAgentId,
} from '../hiddenAgents'

describe('hiddenAgents persistence', () => {
  afterEach(() => {
    localStorage.removeItem(HIDDEN_AGENTS_STORAGE_KEY)
  })

  it('reads empty when nothing is stored (seed is opt-in via loadOrSeed)', () => {
    expect(loadHiddenAgentIds()).toEqual([])
  })

  it('seeds gate and skeptic catalog ids on first load', () => {
    const catalog = [
      { id: 'support', name: 'Support' },
      { id: 'tool_gate', name: 'Gate' },
      { id: 'skeptic', name: 'Skeptic' },
      { id: 'codey', name: 'Codey' },
    ]
    expect(defaultHiddenAgentIds(catalog)).toEqual(['tool_gate', 'skeptic'])
    expect(loadOrSeedHiddenAgentIds(catalog)).toEqual(['tool_gate', 'skeptic'])
    expect(JSON.parse(localStorage.getItem(HIDDEN_AGENTS_STORAGE_KEY) || '[]')).toEqual([
      'tool_gate',
      'skeptic',
    ])
    expect(loadOrSeedHiddenAgentIds(catalog)).toEqual(['tool_gate', 'skeptic'])
  })

  it('falls back to shipped aliases when the catalog has no gate/skeptic yet', () => {
    expect(loadOrSeedHiddenAgentIds([{ id: 'codey', name: 'Codey' }])).toEqual([
      ...DEFAULT_HIDDEN_AGENT_IDS,
    ])
  })

  it('does not re-seed after the user unhides (empty stored list)', () => {
    saveHiddenAgentIds([])
    expect(loadOrSeedHiddenAgentIds([{ id: 'gate', name: 'Gate' }])).toEqual([])
    expect(localStorage.getItem(HIDDEN_AGENTS_STORAGE_KEY)).toBe('[]')
  })

  it('does not overwrite an existing customized hidden list', () => {
    saveHiddenAgentIds(['codey'])
    expect(loadOrSeedHiddenAgentIds([{ id: 'gate', name: 'Gate' }])).toEqual(['codey'])
  })

  it('hides an agent and persists across a reload-style read', () => {
    const next = hideAgentId('codey', [])
    expect(next).toEqual(['codey'])
    expect(JSON.parse(localStorage.getItem(HIDDEN_AGENTS_STORAGE_KEY) || '[]')).toEqual(['codey'])
    expect(loadHiddenAgentIds()).toEqual(['codey'])
  })

  it('does not require hide-all and unhides a single agent', () => {
    saveHiddenAgentIds(['codey', 'stewie'])
    const afterHide = hideAgentId('stewie', ['codey'])
    expect(afterHide).toEqual(['codey', 'stewie'])
    const afterUnhide = unhideAgentId('codey', afterHide)
    expect(afterUnhide).toEqual(['stewie'])
    expect(loadHiddenAgentIds()).toEqual(['stewie'])
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
