import { describe, expect, it } from 'vitest'
import {
  FALLBACK_CLIS,
  MANAGE_CLI_VALUE,
  MANAGE_MODEL_VALUE,
  MODE_CLI,
  MODE_REMOTE,
  STATUS_ROLE,
  formatDropdownStatus,
  isCliAgentContext,
  isStatusRole,
  modeLabel,
  shouldRecordDropdownChange,
  uniqueCliNames,
} from '../chatStatus'

describe('formatDropdownStatus', () => {
  it('names from → to for every chat dropdown kind', () => {
    expect(formatDropdownStatus('team', 'All members', 'Codey (agent/coder)')).toBe(
      'Team target: All members → Codey (agent/coder)',
    )
    expect(formatDropdownStatus('cli', 'antigravity', 'grok')).toBe('CLI: antigravity → grok')
    expect(formatDropdownStatus('model', 'gpt-4', 'grok-4')).toBe('Model: gpt-4 → grok-4')
    expect(formatDropdownStatus('mode', 'Remote', 'CLI')).toBe('Mode: Remote → CLI')
  })
})

describe('shouldRecordDropdownChange', () => {
  it('skips same-value, empty, and Manage sentinels', () => {
    expect(shouldRecordDropdownChange('all', 'codey')).toBe(true)
    expect(shouldRecordDropdownChange('all', 'all')).toBe(false)
    expect(shouldRecordDropdownChange('', 'grok')).toBe(false)
    expect(shouldRecordDropdownChange('grok', MANAGE_CLI_VALUE)).toBe(false)
    expect(shouldRecordDropdownChange('gpt-4', MANAGE_MODEL_VALUE)).toBe(false)
    expect(shouldRecordDropdownChange('all', '__manage__')).toBe(false)
  })
})

describe('cli context helpers', () => {
  it('detects CLI-agent context from blueprint, mode, or cli query', () => {
    expect(isCliAgentContext({ blueprintId: 'cli_agent' })).toBe(true)
    expect(isCliAgentContext({ blueprintId: 'cli_fusion' })).toBe(true)
    expect(isCliAgentContext({ mode: MODE_CLI })).toBe(true)
    expect(isCliAgentContext({ cli: 'antigravity' })).toBe(true)
    expect(isCliAgentContext({ blueprintId: 'codey' })).toBe(false)
  })

  it('dedupes CLI names and keeps fallbacks', () => {
    expect(uniqueCliNames(['grok', 'grok'], FALLBACK_CLIS).slice(0, 2)).toEqual(['grok', 'antigravity'])
    expect(modeLabel(MODE_REMOTE)).toBe('Remote')
    expect(modeLabel(MODE_CLI)).toBe('CLI')
    expect(isStatusRole(STATUS_ROLE)).toBe(true)
    expect(isStatusRole('assistant')).toBe(false)
  })
})
