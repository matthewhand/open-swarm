import { afterEach, describe, expect, it } from 'vitest'
import {
  MCP_SERVERS_KEY,
  entryToUpsertBody,
  loadConfiguredMcpServers,
  newMcpServerId,
  normalizeOpenApiSpecSource,
  removeMcpServer,
  upsertMcpServer,
  validateOpenApiWizard,
} from '../mcpServers'

describe('mcpServers document store', () => {
  afterEach(() => {
    localStorage.removeItem(MCP_SERVERS_KEY)
  })

  it('upserts and removes a server without storing secrets', () => {
    const saved = upsertMcpServer({
      id: newMcpServerId('Fetch'),
      name: 'Fetch',
      kind: 'local',
      enabled: true,
      command: 'uvx',
      args: ['mcp-server-fetch'],
      provides: ['web_fetch'],
      tools: [],
      note: 'Non-auth URL fetch.',
    })
    expect(saved).toHaveLength(1)
    expect(saved[0].id).toBe('fetch')
    expect(saved[0].enabled).toBe(true)
    expect(JSON.stringify(saved)).not.toMatch(/api[_-]?key|token|secret|password/i)
    expect(removeMcpServer('fetch')).toEqual([])
    expect(loadConfiguredMcpServers()).toEqual([])
  })

  it('keeps only ${VAR} env and header placeholders', () => {
    const saved = upsertMcpServer({
      id: 'proxy',
      name: 'proxy',
      kind: 'remote',
      enabled: true,
      url: 'https://example.invalid/mcp',
      headers: { Authorization: '${MCP_TOKEN}', leak: 'sk-live' },
      env: { BRAVE_API_KEY: 'BRAVE_API_KEY' },
      provides: [],
      tools: [{ name: 'search_docs', description: 'Search' }],
    })
    expect(saved[0].headers).toEqual({ Authorization: '${MCP_TOKEN}' })
    expect(saved[0].env).toEqual({ BRAVE_API_KEY: '${BRAVE_API_KEY}' })
    expect(JSON.stringify(saved)).not.toMatch(/sk-live/)
    expect(saved[0].tools[0].name).toBe('search_docs')
  })

  it('validates the OpenAPI wizard and keeps spec URLs out of secret fields', () => {
    expect(
      validateOpenApiWizard({
        name: '',
        kind: 'local',
        specSource: 'https://example.invalid/openapi.json',
        url: '',
      }).ok,
    ).toBe(false)
    expect(
      validateOpenApiWizard({
        name: 'Pets',
        kind: 'local',
        specSource: '',
        url: '',
      }),
    ).toMatchObject({ ok: false, error: 'OpenAPI spec required' })
    expect(
      validateOpenApiWizard({
        name: 'Pets',
        kind: 'remote',
        specSource: 'https://example.invalid/openapi.json',
        url: '',
      }),
    ).toMatchObject({ ok: false, error: 'Proxy MCP URL required' })
    expect(
      validateOpenApiWizard({
        name: 'Pets',
        kind: 'local',
        specSource: 'https://user:token@example.invalid/openapi.json',
        url: '',
      }).ok,
    ).toBe(false)
    const localOk = validateOpenApiWizard({
      name: 'Pets',
      kind: 'local',
      specSource: 'https://example.invalid/openapi.json',
      url: '',
    })
    expect(localOk).toEqual({
      ok: true,
      specSource: 'https://example.invalid/openapi.json',
      url: '',
    })
    expect(normalizeOpenApiSpecSource('/tmp/pets.json', 'local')).toBe('file:///tmp/pets.json')
    const saved = upsertMcpServer({
      id: 'pets',
      name: 'Pets',
      kind: 'local',
      source: 'openapi',
      enabled: true,
      command: 'uvx',
      args: ['mcp-openapi-proxy'],
      openapi_spec_url: 'https://example.invalid/openapi.json',
      env: { API_KEY: '${API_KEY}' },
      provides: ['list_pets'],
      tools: [{ name: 'list_pets', description: 'List pets' }],
    })
    const body = entryToUpsertBody(saved[0])
    expect(body.source).toBe('openapi')
    expect(body.openapi_spec_url).toBe('https://example.invalid/openapi.json')
    expect(JSON.stringify(body)).not.toMatch(/sk-|token|password/i)
    expect(body.env).toEqual({ API_KEY: '${API_KEY}' })
  })
})
