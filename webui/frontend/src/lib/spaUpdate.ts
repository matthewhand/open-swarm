/**
 * REQ-78 update chrome: local SPA/backend mismatch vs GitHub newer release.
 *
 * Priority: local mismatch (A, reload) wins over GitHub newer (B, release page).
 * Missing signals never alarm — first paint and API failure stay idle (ⓘ).
 */

export type UpdateChromeKind = 'idle' | 'local' | 'upstream'

export interface UpdateChromeState {
  kind: UpdateChromeKind
  alsoUpstream: boolean
}

export function normalizeVersion(value: string): string {
  return value.trim().replace(/^v/i, '')
}

export function versionsEqual(left: string, right: string): boolean {
  return normalizeVersion(left) === normalizeVersion(right)
}

function parseVersionParts(value: string): number[] | null {
  const normalized = normalizeVersion(value)
  if (!normalized) return null
  const chunks = normalized.split('.')
  const parts: number[] = []
  for (const chunk of chunks) {
    const match = /^(\d+)/.exec(chunk)
    if (!match) return null
    parts.push(Number(match[1]))
  }
  return parts.length > 0 ? parts : null
}

/** True when candidate is a strictly newer dotted version than current. */
export function isNewerVersion(candidate: string, current: string): boolean {
  const left = parseVersionParts(candidate)
  const right = parseVersionParts(current)
  if (!left || !right) return false
  const len = Math.max(left.length, right.length)
  for (let i = 0; i < len; i += 1) {
    const a = left[i] ?? 0
    const b = right[i] ?? 0
    if (a > b) return true
    if (a < b) return false
  }
  return false
}

/**
 * Resolve the single XOR chrome slot.
 * `backendVersion` null = no hello yet (do not treat as mismatch).
 * `githubLatest` null = no upstream signal (fail / not fetched).
 */
export function resolveUpdateChrome(input: {
  bakedVersion: string
  backendVersion: string | null
  githubLatest: string | null
}): UpdateChromeState {
  const baked = input.bakedVersion.trim()
  const backend = input.backendVersion?.trim() || null
  const github = input.githubLatest?.trim() || null

  const localMismatch = Boolean(backend && baked && !versionsEqual(baked, backend))
  const advertised = backend || baked
  const upstreamNewer = Boolean(
    github && advertised && isNewerVersion(github, advertised),
  )

  if (localMismatch) {
    return { kind: 'local', alsoUpstream: upstreamNewer }
  }
  if (upstreamNewer) {
    return { kind: 'upstream', alsoUpstream: false }
  }
  return { kind: 'idle', alsoUpstream: false }
}
