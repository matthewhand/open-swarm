import { describe, expect, it } from 'vitest'
import { canEditAgentMessages, classifyAgentKind } from '../agentKind'

describe('classifyAgentKind', () => {
  it('treats discovered blueprints as API (including cli_agent)', () => {
    expect(classifyAgentKind('jeeves')).toBe('api')
    expect(classifyAgentKind('cli_agent')).toBe('api')
    expect(classifyAgentKind('support')).toBe('api')
    expect(canEditAgentMessages('codey')).toBe(true)
  })

  it('classifies CLI and remote source prefixes', () => {
    expect(classifyAgentKind('cli:grok')).toBe('cli')
    expect(classifyAgentKind('remote:acp')).toBe('remote')
    expect(classifyAgentKind('placeholder:remote:acp')).toBe('remote')
    expect(canEditAgentMessages('cli:grok')).toBe(false)
    expect(canEditAgentMessages('remote:acp')).toBe(false)
  })

  it('lets an explicit kind win', () => {
    expect(classifyAgentKind('jeeves', 'cli')).toBe('cli')
    expect(classifyAgentKind('cli:grok', 'api')).toBe('api')
  })
})
