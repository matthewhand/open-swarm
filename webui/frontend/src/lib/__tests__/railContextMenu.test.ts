import { afterEach, describe, expect, it } from 'vitest'
import { conversationIdForAgent } from '../agentChat'
import {
  RAIL_MENU_REASONS,
  copyableConversationId,
  duplicateName,
  isRailMenuKey,
  railMenuItems,
} from '../railContextMenu'

describe('railMenuItems (REQ-82)', () => {
  const base = {
    pinned: false,
    hidden: false,
    unread: false,
  }

  it('puts red Delete last and includes Unpin only when pinned', () => {
    const unpinned = railMenuItems({ ...base, kind: 'api' })
    expect(unpinned.map((item) => item.id)).toEqual([
      'pin',
      'unread',
      'edit',
      'duplicate',
      'copy-id',
      'hide',
      'delete',
    ])
    expect(unpinned.at(-1)).toMatchObject({ id: 'delete', danger: true, label: 'Delete' })
    expect(unpinned.some((item) => item.id === 'unpin')).toBe(false)

    const pinned = railMenuItems({ ...base, kind: 'api', pinned: true })
    expect(pinned[0]).toMatchObject({ id: 'unpin', label: 'Unpin' })
    expect(pinned.some((item) => item.id === 'pin')).toBe(false)
    expect(pinned.at(-1)?.id).toBe('delete')
  })

  it('omits Edit Profile and Duplicate for CLI (honest, not grey lies)', () => {
    const items = railMenuItems({ ...base, kind: 'cli' })
    expect(items.map((item) => item.id)).toEqual(['pin', 'unread', 'copy-id', 'hide', 'delete'])
    expect(items.find((item) => item.id === 'edit')).toBeUndefined()
    expect(items.find((item) => item.id === 'duplicate')).toBeUndefined()
    expect(RAIL_MENU_REASONS.cliNoProfile).toMatch(/no swarm-owned profile/i)
  })

  it('adds Select session for CLI when requested (REQ-104)', () => {
    const items = railMenuItems({ ...base, kind: 'cli', hasSelectSession: true })
    expect(items[0]).toMatchObject({ id: 'select-session', label: 'Select session' })
  })

  it('adds Select session and New session for API when requested (REQ-105)', () => {
    const items = railMenuItems({
      ...base,
      kind: 'api',
      hasSelectSession: true,
      hasNewSession: true,
    })
    expect(items.map((item) => item.id).slice(0, 2)).toEqual(['select-session', 'new-session'])
    expect(items[1]).toMatchObject({ id: 'new-session', label: 'New session' })
  })

  it('keeps Edit / Duplicate for API, team, and remote', () => {
    for (const kind of ['api', 'team', 'remote'] as const) {
      const ids = railMenuItems({ ...base, kind }).map((item) => item.id)
      expect(ids).toContain('edit')
      expect(ids).toContain('duplicate')
      expect(ids.at(-1)).toBe('delete')
    }
  })

  it('disables Copy conversation ID when no swarm-side id exists', () => {
    const items = railMenuItems({ ...base, kind: 'cli', canCopyId: false })
    const copy = items.find((item) => item.id === 'copy-id')
    expect(copy?.disabled).toBe(true)
    expect(copy?.reason).toBe(RAIL_MENU_REASONS.noConversationId)
  })
})

describe('copyableConversationId / isRailMenuKey', () => {
  afterEach(() => {
    localStorage.clear()
  })

  it('returns a stored API conversation id and mints when missing', () => {
    localStorage.setItem('swarm_agent_chat:codey', 'conv-codey-1')
    expect(copyableConversationId('api', 'codey')).toBe('conv-codey-1')
    expect(copyableConversationId('api', 'stewie')).toBe(conversationIdForAgent('stewie'))
  })

  it('disables CLI/remote copy when no swarm-side id exists', () => {
    expect(copyableConversationId('cli', 'cli_agent')).toBeNull()
    expect(copyableConversationId('remote', 'remote:omb', 'omb')).toBeNull()
  })

  it('treats Shift+F10 and ContextMenu as menu keys', () => {
    expect(isRailMenuKey({ key: 'F10', shiftKey: true })).toBe(true)
    expect(isRailMenuKey({ key: 'ContextMenu', shiftKey: false })).toBe(true)
    expect(isRailMenuKey({ key: 'F10', shiftKey: false })).toBe(false)
    expect(isRailMenuKey({ key: 'Enter', shiftKey: true })).toBe(false)
  })

  it('appends copy to a display name', () => {
    expect(duplicateName('Codey')).toBe('Codey copy')
  })
})
