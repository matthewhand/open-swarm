import { describe, it, expect } from 'vitest'
import {
  discoverChatClis,
  isCliAgentContext,
  isCliBlueprintId,
  preferredChatCli,
} from '../cliAgentContext'

describe('isCliBlueprintId', () => {
  it('matches cli_agent and the cli_* family', () => {
    expect(isCliBlueprintId('cli_agent')).toBe(true)
    expect(isCliBlueprintId('cli_fusion')).toBe(true)
    expect(isCliBlueprintId('cli_map')).toBe(true)
    expect(isCliBlueprintId('CLI_ORCHESTRATOR')).toBe(true)
  })

  it('rejects blueprint-mode slugs', () => {
    expect(isCliBlueprintId('codey')).toBe(false)
    expect(isCliBlueprintId('hybrid_team')).toBe(false)
    expect(isCliBlueprintId('swarm_ensemble')).toBe(false)
    expect(isCliBlueprintId('')).toBe(false)
  })
})

describe('isCliAgentContext', () => {
  it('detects cli_* blueprint ids', () => {
    expect(isCliAgentContext({ blueprintId: 'cli_agent' })).toBe(true)
    expect(isCliAgentContext({ blueprintId: 'cli_fusion' })).toBe(true)
  })

  it('detects explicit ?mode=cli / ?mode=cli_agent', () => {
    expect(
      isCliAgentContext({ searchParams: new URLSearchParams('mode=cli') }),
    ).toBe(true)
    expect(
      isCliAgentContext({ searchParams: new URLSearchParams('mode=cli_agent') }),
    ).toBe(true)
  })

  it('detects explicit ?cli=<name>', () => {
    expect(
      isCliAgentContext({ searchParams: new URLSearchParams('cli=grok') }),
    ).toBe(true)
  })

  it('stays in blueprint mode without those signals', () => {
    expect(isCliAgentContext({ blueprintId: 'codey' })).toBe(false)
    expect(
      isCliAgentContext({
        blueprintId: 'hybrid_team',
        searchParams: new URLSearchParams('blueprint=hybrid_team'),
      }),
    ).toBe(false)
    expect(isCliAgentContext({ searchParams: new URLSearchParams() })).toBe(false)
    expect(
      isCliAgentContext({ searchParams: new URLSearchParams('cli=') }),
    ).toBe(false)
  })
})

describe('discoverChatClis', () => {
  it('lists only configured names, not every PATH-discovered binary', () => {
    expect(
      discoverChatClis({
        clis: ['claude', 'codex', 'gemini', 'grok', 'opencode'],
        installed: ['grok', 'claude'],
        discovered: ['grok', 'claude'],
        configured: ['grok', 'my_custom_cli'],
        native_consensus: {},
        catalog: {},
      }),
    ).toEqual(['grok', 'my_custom_cli'])
  })

  it('stays empty when nothing is configured (no catalog fallback)', () => {
    expect(
      discoverChatClis({
        clis: ['grok', 'claude'],
        installed: ['grok'],
        discovered: ['grok'],
        configured: [],
        native_consensus: {},
        catalog: {},
      }),
    ).toEqual([])
  })

  it('returns empty when the payload is missing', () => {
    expect(discoverChatClis(undefined)).toEqual([])
  })

  it('includes a selected/running CLI that is outside the static catalog', () => {
    expect(
      discoverChatClis(
        {
          clis: ['claude', 'codex', 'gemini', 'grok', 'opencode'],
          installed: ['grok'],
          configured: ['grok'],
          native_consensus: {},
          catalog: {},
        },
        'antigravity',
      ),
    ).toEqual(['grok', 'antigravity'])
  })

  it('lists only the selected CLI when discovery is empty', () => {
    expect(discoverChatClis(undefined, 'antigravity')).toEqual(['antigravity'])
  })
})

describe('preferredChatCli', () => {
  it('keeps a current selection that is still available', () => {
    expect(preferredChatCli(['claude', 'grok'], 'claude')).toBe('claude')
  })

  it('keeps a running CLI even when it is outside the discovered list', () => {
    expect(preferredChatCli(['grok', 'claude'], 'antigravity')).toBe('antigravity')
  })

  it('prefers grok when nothing is selected', () => {
    expect(preferredChatCli(['claude', 'grok'], '')).toBe('grok')
  })

  it('takes the first name when grok is absent', () => {
    expect(preferredChatCli(['claude', 'gemini'], '')).toBe('claude')
  })
})
