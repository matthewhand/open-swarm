/**
 * Settings LLM profiles (REQ-43 / #358).
 *
 * Persistence is the server SoT (`settings.default_llm_profile`). This module
 * only types the payload and flags missing picks for the SPA warning.
 */

import {
  LLM_TASK_CLASSES,
  type LlmProfile,
  type LlmProfilesSettings,
  type LlmTaskClass,
} from './api'

export { LLM_TASK_CLASSES }
export type { LlmProfile, LlmProfilesSettings, LlmTaskClass }

export const TASK_CLASS_LABELS: Record<LlmTaskClass, string> = {
  orchestration: 'User chat / orchestration',
  auxiliary: 'Auxiliary (code summary)',
  delegation: 'Delegation (design / coding)',
}

export function profileIds(settings: LlmProfilesSettings | null | undefined): string[] {
  return (settings?.profiles ?? []).map((profile) => profile.id)
}

export function isKnownProfile(
  id: string | undefined,
  settings: LlmProfilesSettings | null | undefined,
): boolean {
  if (!id) return false
  return profileIds(settings).includes(id)
}

export function missingProfileWarning(
  id: string | undefined,
  settings: LlmProfilesSettings | null | undefined,
  fallback: string,
): string | null {
  if (!id) return null
  if (isKnownProfile(id, settings)) return null
  return `Profile ${id} is not in the connected catalog; falling back to ${fallback}.`
}

export function effectiveTaskProfile(
  taskClass: LlmTaskClass,
  settings: LlmProfilesSettings | null | undefined,
): string {
  const fallback = settings?.default_llm_profile || 'default'
  if (!settings?.override_per_task) return fallback
  return settings.task_llm_profiles?.[taskClass] || fallback
}
