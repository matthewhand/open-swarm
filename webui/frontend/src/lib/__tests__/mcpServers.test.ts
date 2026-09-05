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
      command: 'uvx',
      args: ['mcp-server-fetch'],
      provides: ['web_fetch'],
      note: 'Non-auth URL fetch.',
    })
    expect(saved).toHaveLength(1)
    expect(saved[0].id).toBe('fetch')
    expect(JSON.stringify(saved)).not.toMatch(/api[_-]?key|token|secret|password/i)
    expect(removeMcpServer('fetch')).toEqual([])
    expect(loadConfiguredMcpServers()).toEqual([])
  })
})
