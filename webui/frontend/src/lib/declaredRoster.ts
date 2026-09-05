/**
 * Declared team roster from a team blueprint (REQ-81 / #433).
 *
 * Distinct from the live “currently working” stack (#394 / #398). Faces come
 * from a static openai-agents parse (count + names). Unknown / unparsable
 * source is one generic face and no invented names.
 */

import type { StackFace } from './avatarStack'
import { assignedTeamBlueprintId } from './teamEdits'
import {
  UNPARSED_PERSONAS,
  normalizePersonaResult,
  type BlueprintPersona,
  type PersonaParseResult,
} from './personaParse'

export interface DeclaredTeamRoster extends PersonaParseResult {
  blueprintId: string
  generic: boolean
}

export function personasFromBlueprint(
  blueprint:
    | { id?: string; persona_count?: number; personas?: BlueprintPersona[] }
    | null
    | undefined,
): PersonaParseResult {
  if (!blueprint) return { ...UNPARSED_PERSONAS }
  return normalizePersonaResult({
    count: blueprint.persona_count,
    personas: blueprint.personas,
  })
}

export function declaredRosterForTeam(
  team: { id: string; blueprintId?: string | null; blueprint?: string | null; personas?: BlueprintPersona[] },
  catalog: Array<{ id: string; persona_count?: number; personas?: BlueprintPersona[] }>,
): DeclaredTeamRoster | null {
  const catalogIds = catalog.map((item) => item.id)
  const blueprintId = assignedTeamBlueprintId(team, catalogIds)
  if (!blueprintId) return null
  const fromTeam = team.personas?.length
    ? normalizePersonaResult({ count: team.personas.length, personas: team.personas })
    : null
  const fromCatalog = personasFromBlueprint(catalog.find((item) => item.id === blueprintId))
  const parsed = fromTeam?.parsed ? fromTeam : fromCatalog
  return {
    blueprintId,
    ...parsed,
    generic: !parsed.parsed,
  }
}

export function facesFromDeclaredRoster(roster: DeclaredTeamRoster, groupId: string): StackFace[] {
  if (!roster.parsed || roster.personas.length === 0) {
    return [
      {
        id: `${groupId}:generic`,
        name: '',
        startedAt: 0,
        markId: groupId,
      },
    ]
  }
  return roster.personas.map((persona, index) => ({
    id: `${groupId}:${slugPersona(persona.name)}`,
    name: persona.name,
    startedAt: index,
    markId: persona.name,
  }))
}

export function slugPersona(name: string): string {
  return name
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '') || 'persona'
}
