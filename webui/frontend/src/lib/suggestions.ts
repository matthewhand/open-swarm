/**
 * REQ-85: suggestion chips — UI chrome, not transcript / LLM context.
 *
 * A consumer with **Use suggestions** on shows 2–5 clickable prompts.
 * Bad or empty lists are an honest omission (no chips, no toast).
 */

export const MIN_SUGGESTIONS = 1
export const MAX_SUGGESTIONS = 5
export const MAX_CHIP_CHARS = 80

export const USE_SUGGESTIONS_LABEL = 'Use suggestions'

export const USE_SUGGESTIONS_TOOLTIP =
  'After each turn, show clickable follow-up chips prepared by a suggestions-role agent. Not a second bot in the rail.'

export function parseSuggestions(raw: unknown): string[] {
  if (raw == null) return []
  let items: unknown[]
  if (Array.isArray(raw)) {
    items = raw
  } else if (typeof raw === 'object') {
    const record = raw as Record<string, unknown>
    const nested = record.suggestions ?? record.prompts ?? record.chips ?? record.options
    if (!Array.isArray(nested)) return []
    items = nested
  } else if (typeof raw === 'string') {
    const text = raw.trim()
    if (!text) return []
    try {
      return parseSuggestions(JSON.parse(text) as unknown)
    } catch {
      items = text
        .split('\n')
        .map((line) => line.replace(/^\s*[-*]\s*/, '').trim())
        .filter(Boolean)
    }
  } else {
    return []
  }

  const seen = new Set<string>()
  const out: string[] = []
  for (const item of items) {
    if (item == null) continue
    let chip = String(item).trim().replace(/\s+/g, ' ')
    if (!chip) continue
    if (chip.length > MAX_CHIP_CHARS) {
      chip = `${chip.slice(0, MAX_CHIP_CHARS - 1).trimEnd()}…`
    }
    const key = chip.toLowerCase()
    if (seen.has(key)) continue
    seen.add(key)
    out.push(chip)
    if (out.length >= MAX_SUGGESTIONS) break
  }
  return out.length >= MIN_SUGGESTIONS ? out : []
}

/** Chips render only when the toggle is on and the list is usable. */
export function shouldShowSuggestionChips(opts: {
  enabled: boolean
  chips: readonly string[] | null | undefined
}): boolean {
  if (!opts.enabled) return false
  return parseSuggestions(opts.chips ?? []).length > 0
}

export function suggestionsUrl(
  agentId: string,
  mode: 'kickstart' | 'continue' = 'kickstart',
  conversationId?: string,
): string {
  const id = encodeURIComponent(agentId)
  const params = new URLSearchParams({ mode })
  const conversation = (conversationId || '').trim()
  if (conversation) params.set('conversation_id', conversation)
  return `/v1/agents/${id}/suggestions/?${params}`
}

export async function fetchAgentSuggestions(
  agentId: string,
  mode: 'kickstart' | 'continue' = 'kickstart',
  conversationId?: string,
): Promise<string[]> {
  const agent = (agentId || '').trim()
  if (!agent) return []
  try {
    const response = await fetch(suggestionsUrl(agent, mode, conversationId), {
      headers: { Accept: 'application/json' },
    })
    if (!response.ok) return []
    const body: unknown = await response.json()
    return parseSuggestions(body)
  } catch {
    return []
  }
}
