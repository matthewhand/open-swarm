import { apiGet, apiPost } from './api'
import type {
  DefinitionContext,
  DefinitionKind,
  DefinitionSummary,
} from './definitionExplain'

export function definitionPath(kind: DefinitionKind, id: string, suffix = ''): string {
  return `/v1/definitions/${encodeURIComponent(kind)}/${encodeURIComponent(id)}${suffix}`
}

export function fetchDefinition(
  kind: DefinitionKind,
  id: string,
  opts?: { extra?: string; role?: string },
): Promise<DefinitionContext> {
  const params = new URLSearchParams()
  if (opts?.extra) params.set('extra', opts.extra)
  if (opts?.role) params.set('role', opts.role)
  const q = params.toString()
  return apiGet<DefinitionContext>(`${definitionPath(kind, id)}${q ? `?${q}` : ''}`)
}

export function summarizeDefinition(
  kind: DefinitionKind,
  id: string,
  body?: { source?: string; extra?: string; role?: string },
): Promise<DefinitionSummary> {
  return apiPost<DefinitionSummary>(definitionPath(kind, id, '/summarize'), body ?? {})
}
