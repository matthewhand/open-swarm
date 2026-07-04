import { describe, it, expect } from 'vitest'
import {
  resolveCapabilities,
  suggestServer,
  buildToolsConfig,
  type McpServerInfo,
} from '../toolCapabilities'

const mk = (name: string, provides: string[], needs_auth = false, auth_env: string[] = []): McpServerInfo => ({
  name, provides, command: 'x', args: [], needs_auth, auth_env, note: '',
})

const DDG = mk('duckduckgo', ['web_search'])
const BRAVE = mk('brave-search', ['web_search'], true, ['BRAVE_API_KEY'])
const PLAYWRIGHT = mk('playwright', ['browser', 'web_fetch'])

describe('resolveCapabilities', () => {
  it('prefers a non-auth provider', () => {
    const r = resolveCapabilities({ web_search: 'mandatory' }, [BRAVE, DDG])
    expect(r.satisfied.web_search).toBe('duckduckgo')
    expect(r.missingMandatory).toEqual([])
  })

  it('reports a missing mandatory capability', () => {
    const r = resolveCapabilities({ browser: 'mandatory' }, [DDG])
    expect(r.missingMandatory).toEqual(['browser'])
  })

  it('skips an unmet optional capability without blocking', () => {
    const r = resolveCapabilities({ browser: 'optional' }, [DDG])
    expect(r.skippedOptional).toEqual(['browser'])
    expect(r.missingMandatory).toEqual([])
  })

  it('falls back to auth provider only when its key is available', () => {
    expect(resolveCapabilities({ web_search: 'mandatory' }, [BRAVE], () => false).missingMandatory)
      .toEqual(['web_search'])
    expect(resolveCapabilities({ web_search: 'mandatory' }, [BRAVE], () => true).satisfied.web_search)
      .toBe('brave-search')
  })
})

describe('suggestServer', () => {
  it('suggests the non-auth provider', () => {
    expect(suggestServer('web_search', [BRAVE, DDG])?.name).toBe('duckduckgo')
  })
})

describe('buildToolsConfig', () => {
  it('emits mcpServers + tool_requirements; auth server gets an env block', () => {
    const cfg = buildToolsConfig({ browser: 'mandatory' }, [PLAYWRIGHT, BRAVE])
    const servers = cfg.mcpServers as Record<string, { env?: object }>
    expect(servers.playwright.env).toBeUndefined()
    expect(servers['brave-search'].env).toEqual({ BRAVE_API_KEY: '${BRAVE_API_KEY}' })
    expect(cfg.tool_requirements).toEqual({ browser: 'mandatory' })
  })
})
