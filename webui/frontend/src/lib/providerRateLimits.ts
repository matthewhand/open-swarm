/**
 * REQ-88 / #445 — provider rate-limit rules and countdown chrome.
 *
 * Settings live on the provider (CLI catalog / API profile / remote), not
 * per-agent. Empty = no limit. Countdown copy is UI-only (never LLM context).
 */

export type RateLimitSettingsSection = 'cli-agents' | 'llm-profiles' | 'remotes'

export const RATE_LIMIT_RULE_KEYS = [
  'messages_per_minute',
  'requests_per_minute',
  'tokens_per_minute',
  'tokens_per_day',
] as const

export type RateLimitRuleKey = (typeof RATE_LIMIT_RULE_KEYS)[number]

export const RATE_LIMIT_RULE_LABELS: Record<RateLimitRuleKey, string> = {
  messages_per_minute: 'Messages per minute',
  requests_per_minute: 'Requests per minute',
  tokens_per_minute: 'Tokens per minute',
  tokens_per_day: 'Tokens per day',
}

export type RateLimitRules = Record<RateLimitRuleKey, number | null>

export interface RateLimitSettingsTarget {
  section: RateLimitSettingsSection
  provider_id: string
  focus: 'rate-limits'
  field_id: string
}

export interface RateLimitWait {
  reason: RateLimitRuleKey | string
  remaining_seconds: number
  provider: string
  text?: string
  settings?: RateLimitSettingsTarget
  wait_until_ms?: number
}

export const EMPTY_RATE_LIMIT_RULES: RateLimitRules = {
  messages_per_minute: null,
  requests_per_minute: null,
  tokens_per_minute: null,
  tokens_per_day: null,
}

export function emptyRateLimitRules(): RateLimitRules {
  return { ...EMPTY_RATE_LIMIT_RULES }
}

export function parseLimitInput(raw: unknown): number | null {
  if (raw == null) return null
  if (typeof raw === 'string' && raw.trim() === '') return null
  const n = typeof raw === 'number' ? raw : Number(raw)
  if (!Number.isFinite(n) || n <= 0) return null
  return Math.floor(n)
}

export function parseRateLimitRules(raw: unknown): RateLimitRules {
  const blob = raw && typeof raw === 'object' ? (raw as Record<string, unknown>) : {}
  const out = emptyRateLimitRules()
  for (const key of RATE_LIMIT_RULE_KEYS) {
    out[key] = parseLimitInput(blob[key])
  }
  return out
}

export function normalizeProviderKey(raw: string | undefined | null): string {
  const text = (raw || '').trim()
  if (!text) return ''
  const lowered = text.toLowerCase()
  for (const kind of ['cli', 'llm', 'remote'] as const) {
    const prefix = `${kind}:`
    if (lowered.startsWith(prefix)) {
      const ident = text.slice(prefix.length).trim()
      return ident ? `${kind}:${ident}` : ''
    }
  }
  return text
}

export function providerKind(providerKey: string): 'cli' | 'llm' | 'remote' | '' {
  const key = normalizeProviderKey(providerKey)
  const kind = key.split(':')[0]
  if (kind === 'cli' || kind === 'llm' || kind === 'remote') return kind
  return ''
}

export function providerName(providerKey: string): string {
  const key = normalizeProviderKey(providerKey)
  const idx = key.indexOf(':')
  return idx >= 0 ? key.slice(idx + 1) : key
}

export function settingsSectionForProvider(providerKey: string): RateLimitSettingsSection {
  const kind = providerKind(providerKey)
  if (kind === 'cli') return 'cli-agents'
  if (kind === 'remote') return 'remotes'
  return 'llm-profiles'
}

export function rateLimitFieldId(providerKey: string): string {
  const key = normalizeProviderKey(providerKey) || 'provider'
  return `rate-limits-${key.replace(/:/g, '-')}`
}

export function settingsTargetForProvider(providerKey: string): RateLimitSettingsTarget {
  const key = normalizeProviderKey(providerKey)
  return {
    section: settingsSectionForProvider(key),
    provider_id: key,
    focus: 'rate-limits',
    field_id: rateLimitFieldId(key),
  }
}

export function providerKeyForCatalog(source: string | undefined, id: string, ownedBy?: string): string {
  const kind = (source || '').trim().toLowerCase()
  if (kind === 'cli') return normalizeProviderKey(`cli:${id}`)
  if (kind === 'remote') return normalizeProviderKey(`remote:${ownedBy || id}`)
  return normalizeProviderKey(`llm:${id}`)
}

export function formatRateLimitWait(
  wait: RateLimitWait,
  nowMs: number = Date.now(),
): string {
  const remaining =
    wait.wait_until_ms != null
      ? Math.max(0, Math.ceil((wait.wait_until_ms - nowMs) / 1000))
      : Math.max(0, Math.ceil(wait.remaining_seconds || 0))
  const name = providerName(wait.provider)
  const ruleKey = String(wait.reason || '') as RateLimitRuleKey
  const rule =
    RATE_LIMIT_RULE_LABELS[ruleKey]?.toLowerCase() ||
    String(wait.reason || 'rate limit').replace(/_/g, ' ')
  return `Waiting for ${name} — ${rule} — ${remaining}s`
}

export function isRateLimitWait(value: unknown): value is RateLimitWait {
  if (!value || typeof value !== 'object') return false
  const row = value as RateLimitWait
  return Boolean(row.provider && (row.reason || row.remaining_seconds != null))
}

export function parseRateLimitWaitFromDataset(el: Element): RateLimitWait | undefined {
  if (el.getAttribute('data-rate-limit') !== '1') return undefined
  const provider = el.getAttribute('data-provider') || ''
  const reason = el.getAttribute('data-rule') || ''
  const remaining = Number(el.getAttribute('data-remaining') || 0)
  const waitUntil = Number(el.getAttribute('data-wait-until') || 0)
  const fieldId = el.getAttribute('data-field-id') || rateLimitFieldId(provider)
  if (!provider) return undefined
  return {
    reason,
    remaining_seconds: Number.isFinite(remaining) ? remaining : 0,
    provider,
    wait_until_ms: Number.isFinite(waitUntil) && waitUntil > 0 ? waitUntil : undefined,
    settings: {
      ...settingsTargetForProvider(provider),
      field_id: fieldId,
    },
  }
}
