import { describe, expect, it } from 'vitest'
import {
  formatRateLimitWait,
  parseRateLimitRules,
  parseRateLimitWaitFromDataset,
  providerKeyForCatalog,
  rateLimitFieldId,
  settingsTargetForProvider,
} from '../providerRateLimits'

describe('providerRateLimits', () => {
  it('treats empty values as no limit', () => {
    const rules = parseRateLimitRules({
      messages_per_minute: '',
      requests_per_minute: 0,
      tokens_per_minute: null,
    })
    expect(rules.messages_per_minute).toBeNull()
    expect(rules.requests_per_minute).toBeNull()
    expect(rules.tokens_per_minute).toBeNull()
    expect(parseRateLimitRules({ messages_per_minute: 1 }).messages_per_minute).toBe(1)
  })

  it('targets the provider settings pane, not a per-agent toggle', () => {
    expect(settingsTargetForProvider('cli:grok')).toEqual({
      section: 'cli-agents',
      provider_id: 'cli:grok',
      focus: 'rate-limits',
      field_id: 'rate-limits-cli-grok',
    })
    expect(settingsTargetForProvider('llm:local').section).toBe('llm-profiles')
    expect(settingsTargetForProvider('remote:hermes').section).toBe('remotes')
    expect(rateLimitFieldId('cli:grok')).toBe('rate-limits-cli-grok')
    expect(providerKeyForCatalog('cli', 'grok')).toBe('cli:grok')
    expect(providerKeyForCatalog('config', 'local')).toBe('llm:local')
  })

  it('formats a live countdown without Django copy', () => {
    const text = formatRateLimitWait(
      {
        reason: 'messages_per_minute',
        remaining_seconds: 12,
        provider: 'cli:stub',
        wait_until_ms: Date.now() + 12_000,
      },
      Date.now(),
    )
    expect(text).toMatch(/Waiting for stub/)
    expect(text).toMatch(/messages per minute/)
    expect(text).toMatch(/\d+s/)
    expect(text).not.toMatch(/Django/i)
  })

  it('parses countdown metadata from status chrome', () => {
    const el = document.createElement('div')
    el.setAttribute('data-rate-limit', '1')
    el.setAttribute('data-provider', 'cli:stub')
    el.setAttribute('data-rule', 'messages_per_minute')
    el.setAttribute('data-remaining', '8')
    el.setAttribute('data-wait-until', '1700000008000')
    el.setAttribute('data-field-id', 'rate-limits-cli-stub')
    const wait = parseRateLimitWaitFromDataset(el)
    expect(wait?.provider).toBe('cli:stub')
    expect(wait?.reason).toBe('messages_per_minute')
    expect(wait?.settings?.section).toBe('cli-agents')
  })
})
