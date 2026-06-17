// Pure helpers for the Builder skills picker.

export interface SkillInfo {
  name: string
  description: string
  assets: string[]
}

/** The request snippet that applies a skill to a cli_agent call. */
export function buildSkillRequest(skill: string | null): Record<string, unknown> | null {
  if (!skill) return null
  return { model: 'cli_agent', params: { skill } }
}
