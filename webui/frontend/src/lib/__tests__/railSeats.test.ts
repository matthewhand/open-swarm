import { describe, expect, it } from 'vitest'
import type { Blueprint } from '../api'
import {
  displayNameMatchesBlueprint,
  isCatalogRailSeat,
  isNonCatalogRailPinId,
  isRailSeat,
  railSeatAgents,
} from '../railSeats'

function recipe(id: string, rail?: boolean): Blueprint {
  return {
    id,
    object: 'blueprint',
    name: id,
    description: `${id} recipe`,
    abbreviation: null,
    required_mcp_servers: [],
    tags: [],
    installed: true,
    compiled: true,
    ...(rail === undefined ? {} : { rail }),
  }
}

describe('railSeats (REQ-170)', () => {
  it('default-denies unknown catalog ids when rail is missing or false', () => {
    expect(isCatalogRailSeat(recipe('poets'))).toBe(false)
    expect(isCatalogRailSeat(recipe('codey', false))).toBe(false)
    expect(isCatalogRailSeat({ rail: null })).toBe(false)
    expect(isRailSeat(recipe('chucks_angels'))).toBe(false)
    expect(isRailSeat(recipe('django_chat'))).toBe(false)
    expect(isRailSeat(recipe('moa'))).toBe(false)
    expect(isRailSeat(recipe('cli_fusion'))).toBe(false)
    expect(isRailSeat(recipe('software_dev'))).toBe(false)
  })

  it('allows explicit rail seats and CLI / Herdr / API kind rows', () => {
    expect(isCatalogRailSeat(recipe('support', true))).toBe(true)
    expect(isRailSeat({ rail: true })).toBe(true)
    expect(isRailSeat({ kind: 'cli' })).toBe(true)
    expect(isRailSeat({ kind: 'herdr' })).toBe(true)
    expect(isRailSeat({ kind: 'api' })).toBe(true)
  })

  it('REQ-171B: Add-agent custom seats appear only when the API sets rail true', () => {
    const cliSeat = {
      ...recipe('desk_cli', true),
      kind: 'cli',
      command: 'grok -p',
    }
    const apiSeat = { ...recipe('researcher', true), kind: 'api' }
    const hiddenCustom = { ...recipe('scratch', false), kind: 'api' }
    const agents = railSeatAgents([cliSeat, apiSeat, hiddenCustom, recipe('poets')])
    const ids = agents.map((agent) => agent.id)
    expect(ids).toContain('desk_cli')
    expect(ids).toContain('researcher')
    expect(ids).not.toContain('scratch')
    expect(ids).not.toContain('poets')
    expect(isCatalogRailSeat(cliSeat)).toBe(true)
    expect(isCatalogRailSeat(hiddenCustom)).toBe(false)
  })

  it('railSeatAgents drops the demo catalog and keeps injected role seats', () => {
    const agents = railSeatAgents([
      recipe('poets'),
      recipe('chucks_angels'),
      recipe('django_chat'),
      recipe('moa'),
      recipe('cli_fusion'),
      recipe('codey'),
      recipe('support', true),
    ])
    const ids = agents.map((agent) => agent.id)
    expect(ids).toContain('support')
    expect(ids).toContain('gate')
    expect(ids).toContain('skeptic')
    expect(ids).not.toContain('poets')
    expect(ids).not.toContain('chucks_angels')
    expect(ids).not.toContain('django_chat')
    expect(ids).not.toContain('moa')
    expect(ids).not.toContain('cli_fusion')
    expect(ids).not.toContain('codey')
  })

  it('matches display name to blueprint id or name for the editor rule', () => {
    expect(displayNameMatchesBlueprint('codey', 'codey', 'codey')).toBe(true)
    expect(displayNameMatchesBlueprint('Codey', 'codey', 'Codey')).toBe(true)
    expect(displayNameMatchesBlueprint('Support', 'support', 'Support')).toBe(true)
    expect(displayNameMatchesBlueprint('Desk', 'support', 'Support')).toBe(false)
    expect(displayNameMatchesBlueprint('Support', 'codey', 'Codey')).toBe(false)
    expect(isNonCatalogRailPinId('team:office')).toBe(true)
    expect(isNonCatalogRailPinId('codey')).toBe(false)
  })
})
