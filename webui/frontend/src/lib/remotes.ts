/**
 * Opt-in remotes catalog (REQ-59).
 *
 * Settings and remote dropdowns list only configured remotes. Kind labels
 * use OpenMousBot for the ``omb`` id — never the letters OMB in UI copy.
 */

import type { RemoteConnection, RemoteKind, RemotesListResponse } from './api'

export const ADD_REMOTE_VALUE = '__add_remote__'

export const FALLBACK_REMOTE_KINDS: RemoteKind[] = [
  { id: 'hermes', label: 'Hermes' },
  { id: 'omb', label: 'OpenMousBot' },
  { id: 'rakazo', label: 'Rakazo' },
  { id: 'herdr', label: 'Herdr' },
  { id: 'open-swarm', label: 'open-swarm' },
]

const FALLBACK_LABELS: Record<string, string> = Object.fromEntries(
  FALLBACK_REMOTE_KINDS.map((kind) => [kind.id, kind.label]),
)

export function remoteKindLabel(id: string, kinds: RemoteKind[] = FALLBACK_REMOTE_KINDS): string {
  const rid = (id || '').trim().toLowerCase()
  const aliases: Record<string, string> = {
    openmausbot: 'omb',
    openmaus: 'omb',
    openmousbot: 'omb',
    openswarm: 'open-swarm',
    open_swarm: 'open-swarm',
  }
  const resolved = aliases[rid] || rid
  const fromKinds = kinds.find((kind) => kind.id === resolved)?.label
  if (fromKinds) return fromKinds
  return FALLBACK_LABELS[resolved] || resolved
}

export function remoteKinds(response?: RemotesListResponse | null): RemoteKind[] {
  const listed = response?.kinds
  if (Array.isArray(listed) && listed.length > 0) {
    return listed.map((kind) => ({
      id: kind.id,
      label: kind.label || remoteKindLabel(kind.id),
    }))
  }
  return FALLBACK_REMOTE_KINDS
}

/**
 * Only remotes the user (or env) has added. Defaults / unused kinds stay out.
 */
export function configuredRemotes(response?: RemotesListResponse | null): RemoteConnection[] {
  if (!response) return []
  if (Array.isArray(response.configured)) {
    return response.configured
  }
  return (response.data ?? []).filter((remote) => remote.source && remote.source !== 'default')
}

export function unusedRemoteKinds(
  response?: RemotesListResponse | null,
): RemoteKind[] {
  const used = new Set(configuredRemotes(response).map((remote) => remote.id))
  return remoteKinds(response).filter((kind) => !used.has(kind.id))
}

export function remoteOptionLabel(remote: RemoteConnection, kinds?: RemoteKind[]): string {
  return remote.label || remoteKindLabel(remote.kind || remote.id, kinds)
}
