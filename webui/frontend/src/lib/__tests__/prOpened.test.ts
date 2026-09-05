import { describe, expect, it } from 'vitest'
import {
  formatPrFileStats,
  isGithubPrUrl,
  isSameOpenerChat,
  openerChatSearch,
  parsePrOpened,
} from '../prOpened'

const GH = 'https://github.com/matthewhand/open-swarm/pull/416'

describe('isGithubPrUrl', () => {
  it('accepts public GitHub pull URLs only', () => {
    expect(isGithubPrUrl(GH)).toBe(true)
    expect(isGithubPrUrl(`${GH}/files`)).toBe(true)
    expect(isGithubPrUrl('http://github.com/matthewhand/open-swarm/pull/416')).toBe(false)
    expect(isGithubPrUrl('https://gitlab.com/acme/repo/pull/1')).toBe(false)
    expect(isGithubPrUrl('https://github.com/matthewhand/open-swarm/issues/416')).toBe(false)
    expect(isGithubPrUrl('http://127.0.0.1:8001/pull/1')).toBe(false)
    expect(isGithubPrUrl('https://localhost/pull/1')).toBe(false)
    expect(isGithubPrUrl('not-a-url')).toBe(false)
  })
})

describe('parsePrOpened', () => {
  it('parses an explicit pr_opened payload and keeps optional fields', () => {
    expect(
      parsePrOpened({
        type: 'pr_opened',
        url: GH,
        number: 416,
        title: 'REQ-71 card',
        branch: 'cursor/req-71',
        additions: 12,
        deletions: 3,
        files_changed: 4,
        status: 'Done',
        opener: { agent_id: 'codey', name: 'Codey', conversation_id: 'conv-1' },
      }),
    ).toEqual({
      type: 'pr_opened',
      url: GH,
      number: 416,
      title: 'REQ-71 card',
      branch: 'cursor/req-71',
      additions: 12,
      deletions: 3,
      filesChanged: 4,
      status: 'Done',
      opener: { agentId: 'codey', name: 'Codey', conversationId: 'conv-1' },
    })
  })

  it('accepts a GitHub API-shaped tool result without inventing stats', () => {
    expect(
      parsePrOpened({
        html_url: GH,
        number: 416,
        title: 'REQ-71 card',
        head: { ref: 'feat/card' },
      }),
    ).toEqual({
      type: 'pr_opened',
      url: GH,
      number: 416,
      title: 'REQ-71 card',
      branch: 'feat/card',
    })
  })

  it('rejects markdown, lone links, and non-GitHub hosts', () => {
    expect(parsePrOpened(`Opened ${GH}`)).toBeNull()
    expect(parsePrOpened({ html_url: GH })).toBeNull()
    expect(
      parsePrOpened({
        type: 'pr_opened',
        url: 'https://example.com/pull/1',
        number: 1,
        title: 'nope',
      })?.url,
    ).toBeUndefined()
  })

  it('parses JSON status rows used for thread restore', () => {
    const row = JSON.stringify({ type: 'pr_opened', url: GH, number: 416, title: 'REQ-71' })
    expect(parsePrOpened(row)?.number).toBe(416)
  })
})

describe('same-opener chat helpers', () => {
  it('hides jump when already on that agent and thread', () => {
    const opener = { agentId: 'codey', conversationId: 'conv-1' }
    expect(isSameOpenerChat(opener, { agentId: 'codey', conversationId: 'conv-1' })).toBe(true)
    expect(isSameOpenerChat(opener, { agentId: 'support', conversationId: 'conv-1' })).toBe(false)
    expect(isSameOpenerChat(opener, { agentId: 'codey', conversationId: 'other' })).toBe(false)
    expect(isSameOpenerChat(undefined, { agentId: 'codey' })).toBe(true)
  })

  it('builds a blueprint+session jump, not a Cursor remote', () => {
    const params = openerChatSearch({ agentId: 'codey', conversationId: 'sess-9' })
    expect(params.get('blueprint')).toBe('codey')
    expect(params.get('session')).toBe('sess-9')
    expect(params.toString()).not.toMatch(/cursor/i)
  })

  it('formats only supplied +N/-M stats', () => {
    expect(formatPrFileStats({ type: 'pr_opened', additions: 4, deletions: 1 })).toBe('+4 -1')
    expect(formatPrFileStats({ type: 'pr_opened', additions: 4 })).toBe('+4')
    expect(formatPrFileStats({ type: 'pr_opened' })).toBeUndefined()
  })
})
