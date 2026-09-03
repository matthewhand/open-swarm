/**
 * Remote harness Settings client (REQ-63 Rakazo kind complete).
 *
 * Auth is env-var names only. Never send or display cookies/tokens.
 */
import { apiGet, apiPatch, apiPost } from './api'

export interface RemoteKind {
  id: string
  label: string
  fields: string[]
  ops: string[]
  notes?: string
}

export interface RemoteConnection {
  id: string
  kind: string
  title: string
  label?: string
  host_label: string
  base_url: string
  ui_url: string
  api_key_env: string
  session_cookie_env: string
  api_key_set: boolean
  cookie_set: boolean
  configured: boolean
  notes: string
  source: string
}

export interface RemotesIndex {
  object: 'list'
  data: RemoteConnection[]
  kinds: RemoteKind[]
  vocabulary?: Record<string, string>
  team_members?: Array<Record<string, unknown>>
}

export interface AddRemoteRequest {
  kind: string
  base_url: string
  ui_url?: string
  api_key_env?: string
  session_cookie_env?: string
}

export interface RemoteHealth {
  remote: string
  ok: boolean
  state: string
  detail: string
  http_status?: number | null
  version?: unknown
  latency_ms?: number | null
  url?: string
}

export interface RemoteOperate {
  remote: string
  op: string
  ok: boolean
  detail: string
  http_status?: number | null
  data?: unknown
  gap?: string
}

export interface RemoteBot {
  id: string
  name?: string
}

export function fetchRemotes(): Promise<RemotesIndex> {
  return apiGet<RemotesIndex>('/v1/remotes/')
}

export function addRemote(body: AddRemoteRequest): Promise<RemoteConnection> {
  return apiPost<RemoteConnection>('/v1/remotes/', body)
}

export function patchRemote(
  remoteId: string,
  body: Partial<AddRemoteRequest>,
): Promise<RemoteConnection> {
  return apiPatch<RemoteConnection>(`/v1/remotes/${encodeURIComponent(remoteId)}/`, body)
}

export function probeRemoteHealth(remoteId: string): Promise<RemoteHealth> {
  return apiPost<RemoteHealth>(`/v1/remotes/${encodeURIComponent(remoteId)}/health/`, {})
}

export function operateRemote(
  remoteId: string,
  op: 'list' | 'send',
  opts: { prompt?: string; target?: string } = {},
): Promise<RemoteOperate> {
  return apiPost<RemoteOperate>(`/v1/remotes/${encodeURIComponent(remoteId)}/operate/`, {
    op,
    prompt: opts.prompt || '',
    target: opts.target || '',
  })
}

export function remoteLabel(remote: Pick<RemoteConnection, 'label' | 'title' | 'kind' | 'id'>): string {
  return remote.label || remote.title || remote.kind || remote.id
}

export function kindById(kinds: RemoteKind[] | undefined, kindId: string): RemoteKind | undefined {
  return (kinds || []).find((item) => item.id === kindId)
}

export function botsFromOperate(data: unknown): RemoteBot[] {
  const root =
    data && typeof data === 'object' && data !== null && 'json' in data
      ? (data as { json: unknown }).json
      : data
  if (!Array.isArray(root)) return []
  const bots: RemoteBot[] = []
  for (const item of root) {
    if (typeof item === 'string' && item.trim()) {
      bots.push({ id: item.trim() })
      continue
    }
    if (item && typeof item === 'object') {
      const rec = item as Record<string, unknown>
      const id = String(rec.id || rec.botId || rec.bot_id || '').trim()
      if (!id) continue
      const name = rec.name != null ? String(rec.name) : undefined
      bots.push({ id, name })
    }
  }
  return bots
}

export function looksLikeSecret(value: string): boolean {
  const raw = value.trim()
  if (!raw) return false
  if (/^\$\{[A-Z][A-Z0-9_]*\}$/.test(raw)) return false
  if (/^[A-Z][A-Z0-9_]*$/.test(raw)) return false
  return true
}
