import { afterEach, describe, expect, it } from 'vitest'
import {
  MCP_SERVERS_KEY,
  loadConfiguredMcpServers,
  newMcpServerId,
  removeMcpServer,
  upsertMcpServer,
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
})
