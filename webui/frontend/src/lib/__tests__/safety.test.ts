import { afterEach, describe, expect, it } from 'vitest'
import {
  ALWAYS_ALLOW_STORAGE_KEY,
  isToolAlwaysAllowed,
  rememberAlwaysAllow,
  roleDisplayName,
  shouldPromptForTool,
  usesSwarmApproval,
} from '../safety'

describe('safety policy (REQ-55)', () => {
  afterEach(() => {
    localStorage.removeItem(ALWAYS_ALLOW_STORAGE_KEY)
  })

  it('shows Safety as the user-facing role name', () => {
    expect(roleDisplayName('gate')).toBe('Safety')
    expect(roleDisplayName('safety')).toBe('Safety')
    expect(roleDisplayName('tool_gate')).toBe('Safety')
    expect(roleDisplayName('support')).toBe('Support')
  })

  it('does not use swarm approval on CLI or remote channels', () => {
    expect(usesSwarmApproval('api')).toBe(true)
    expect(usesSwarmApproval('cli')).toBe(false)
    expect(usesSwarmApproval('remote')).toBe(false)
    expect(
      shouldPromptForTool({
        channel: 'cli',
        safetyAssigned: true,
        concerned: true,
      }),
    ).toBe(false)
    expect(
      shouldPromptForTool({
        channel: 'remote',
        safetyAssigned: true,
        concerned: true,
      }),
    ).toBe(false)
  })

  it('prompts only when Safety is assigned and concerned', () => {
    expect(
      shouldPromptForTool({ channel: 'api', safetyAssigned: false, concerned: true }),
    ).toBe(false)
    expect(
      shouldPromptForTool({ channel: 'api', safetyAssigned: true, concerned: false }),
    ).toBe(false)
    expect(
      shouldPromptForTool({ channel: 'api', safetyAssigned: true, concerned: true }),
    ).toBe(true)
  })

  it('always-allow skips the next prompt for that tool on this agent', () => {
    rememberAlwaysAllow('codey', 'write_file')
    expect(isToolAlwaysAllowed('codey', 'write_file')).toBe(true)
    expect(isToolAlwaysAllowed('stewie', 'write_file')).toBe(false)
    expect(
      shouldPromptForTool({
        channel: 'api',
        safetyAssigned: true,
        concerned: true,
        alwaysAllowed: isToolAlwaysAllowed('codey', 'write_file'),
      }),
    ).toBe(false)
  })
})
