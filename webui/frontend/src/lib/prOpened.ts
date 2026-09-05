/**
 * REQ-71: structured GitHub PR-opened tool events (chrome, not markdown).
 * Missing optional fields stay omitted. Stats are never invented.
 */

export const PR_OPENED_TYPE = 'pr_opened' as const

export interface PrOpenedOpener {
  agentId: string
  name?: string
  conversationId?: string
}

export interface PrOpenedEvent {
  type: typeof PR_OPENED_TYPE
  url?: string
  number?: number
  title?: string
  branch?: string
  additions?: number
  deletions?: number
  filesChanged?: number
  status?: string
  opener?: PrOpenedOpener
}

const GITHUB_PR_URL =
  /^https:\/\/github\.com\/[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+\/pull\/\d+(?:\/[A-Za-z0-9._~-]*)?(?:\?[^#]*)?(?:#.*)?$/i

export function isGithubPrUrl(value: unknown): value is string {
  if (typeof value !== 'string') return false
  const text = value.trim()
  if (!text) return false
  const lowered = text.toLowerCase()
  if (lowered.startsWith('http://') || lowered.startsWith('ws://')) return false
  if (lowered.includes('localhost') || lowered.includes('127.0.0.1')) return false
  if (lowered.includes(':8001')) return false
  return GITHUB_PR_URL.test(text)
}

function asInt(value: unknown): number | undefined {
  if (typeof value === 'boolean') return undefined
  if (typeof value === 'number' && Number.isFinite(value)) return Math.trunc(value)
  if (typeof value === 'string' && /^-?\d+$/.test(value.trim())) {
    return Number.parseInt(value.trim(), 10)
  }
  return undefined
}

function asTrimmed(value: unknown): string | undefined {
  if (typeof value !== 'string') return undefined
  const text = value.trim()
  return text || undefined
}

function pickUrl(obj: Record<string, unknown>): string | undefined {
  for (const key of ['url', 'html_url', 'pr_url', 'pull_request_url']) {
    const raw = obj[key]
    if (isGithubPrUrl(raw)) return raw.trim()
  }
  return undefined
}

function pickOpener(obj: Record<string, unknown>): PrOpenedOpener | undefined {
  const raw = obj.opener
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return undefined
  const row = raw as Record<string, unknown>
  const agentId = asTrimmed(row.agentId ?? row.agent_id ?? row.id)
  if (!agentId) return undefined
  const opener: PrOpenedOpener = { agentId }
  const name = asTrimmed(row.name)
  if (name) opener.name = name
  const conversationId = asTrimmed(row.conversationId ?? row.conversation_id)
  if (conversationId) opener.conversationId = conversationId
  return opener
}

function unwrapCandidate(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null
  const obj = value as Record<string, unknown>
  for (const key of ['pull_request', 'pr', 'result', 'data']) {
    const nested = obj[key]
    if (nested && typeof nested === 'object' && !Array.isArray(nested)) {
      const inner = nested as Record<string, unknown>
      if (inner.type === PR_OPENED_TYPE || pickUrl(inner)) return inner
    }
  }
  return obj
}

export function parsePrOpened(value: unknown): PrOpenedEvent | null {
  let raw: unknown = value
  if (typeof raw === 'string') {
    const text = raw.trim()
    if (!text.startsWith('{')) return null
    try {
      raw = JSON.parse(text) as unknown
    } catch {
      return null
    }
  }
  const obj = unwrapCandidate(raw)
  if (!obj) return null

  const explicit = String(obj.type || '').trim() === PR_OPENED_TYPE
  const url = pickUrl(obj)
  const number = asInt(obj.number ?? obj.pr_number ?? obj.pull_number)
  const title = asTrimmed(obj.title ?? obj.name)
  if (!explicit && !url) return null
  if (!explicit && url && number === undefined && !title) return null

  const event: PrOpenedEvent = { type: PR_OPENED_TYPE }
  if (url) event.url = url
  if (number !== undefined) event.number = number
  if (title) event.title = title

  let branch = asTrimmed(obj.branch)
  if (!branch) {
    const head = obj.head
    if (head && typeof head === 'object' && !Array.isArray(head)) {
      branch = asTrimmed((head as Record<string, unknown>).ref)
    } else if (typeof head === 'string' && head.trim() && !head.includes('/')) {
      branch = head.trim()
    } else {
      branch = asTrimmed(obj.head_ref)
    }
  }
  if (branch) event.branch = branch

  const additions = asInt(obj.additions ?? obj.additions_count ?? obj.plus)
  if (additions !== undefined) event.additions = additions
  const deletions = asInt(obj.deletions ?? obj.deletions_count ?? obj.minus)
  if (deletions !== undefined) event.deletions = deletions
  const filesChanged = asInt(obj.files_changed ?? obj.changed_files ?? obj.files)
  if (filesChanged !== undefined) event.filesChanged = filesChanged

  const status = asTrimmed(obj.status ?? obj.state)
  if (status && status !== PR_OPENED_TYPE && status !== 'tool_status') {
    event.status = status
  }

  const opener = pickOpener(obj)
  if (opener) event.opener = opener
  return event
}

export function formatPrFileStats(event: PrOpenedEvent): string | undefined {
  const parts: string[] = []
  if (typeof event.additions === 'number') parts.push(`+${event.additions}`)
  if (typeof event.deletions === 'number') parts.push(`-${event.deletions}`)
  return parts.length ? parts.join(' ') : undefined
}

function normId(value: string | undefined): string {
  return (value || '').trim().toLowerCase()
}

/** True when the card is already on the opener's agent + thread. */
export function isSameOpenerChat(
  opener: PrOpenedOpener | undefined,
  current: { agentId?: string; conversationId?: string },
): boolean {
  if (!opener?.agentId) return true
  if (normId(opener.agentId) !== normId(current.agentId)) return false
  if (opener.conversationId && normId(opener.conversationId) !== normId(current.conversationId)) {
    return false
  }
  return true
}

export function openerChatSearch(opener: PrOpenedOpener): URLSearchParams {
  const params = new URLSearchParams()
  params.set('blueprint', opener.agentId)
  if (opener.conversationId) params.set('session', opener.conversationId)
  return params
}
