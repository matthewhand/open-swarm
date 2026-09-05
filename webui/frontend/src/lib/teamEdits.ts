/**
 * Per-team editor overrides (REQ-81).
 *
 * A team seat can be assigned a catalog blueprint. Persistence is
 * localStorage until the roster PUT lands — same best-effort pattern as
 * `swarm_agent_edits`.
 */

export const TEAM_EDITS_KEY = 'swarm_team_edits'
export const TEAM_EDITS_CHANGED_EVENT = 'swarm:team-edits-changed'

export interface TeamEdit {
  name?: string
  blueprintId?: string
}

export type TeamEditMap = Record<string, TeamEdit>

function readMap(): TeamEditMap {
  try {
    const raw = localStorage.getItem(TEAM_EDITS_KEY)
    if (!raw) return {}
    const parsed: unknown = JSON.parse(raw)
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) return {}
    return parsed as TeamEditMap
  } catch {
    return {}
  }
}

function writeMap(map: TeamEditMap): void {
  try {
    localStorage.setItem(TEAM_EDITS_KEY, JSON.stringify(map))
  } catch {
    /* persistence is best-effort */
  }
}

function emitChange(teamId: string): void {
  try {
    window.dispatchEvent(new CustomEvent(TEAM_EDITS_CHANGED_EVENT, { detail: { teamId } }))
  } catch {
    /* jsdom / detached window */
  }
}

export function loadTeamEdit(teamId: string): TeamEdit {
  if (!teamId) return {}
  return readMap()[teamId] ?? {}
}

export function saveTeamEdit(teamId: string, patch: TeamEdit): TeamEdit {
  if (!teamId) return {}
  const map = readMap()
  const current = map[teamId] ?? {}
  const next: TeamEdit = { ...current }
  if (patch.name !== undefined) {
    const name = patch.name.trim()
    if (name) next.name = name
    else delete next.name
  }
  if (patch.blueprintId !== undefined) {
    const blueprintId = patch.blueprintId.trim()
    if (blueprintId) next.blueprintId = blueprintId
    else delete next.blueprintId
  }
  if (Object.keys(next).length === 0) delete map[teamId]
  else map[teamId] = next
  writeMap(map)
  emitChange(teamId)
  return next
}

/** Catalog blueprint this team recipe uses. Empty when none is assigned. */
export function assignedTeamBlueprintId(
  team: { id: string; blueprintId?: string | null; blueprint?: string | null },
  catalogIds?: Iterable<string>,
): string {
  const fromEdit = loadTeamEdit(team.id).blueprintId?.trim()
  if (fromEdit) return fromEdit
  const fromRoster = (team.blueprintId || team.blueprint || '').trim()
  if (fromRoster) return fromRoster
  const ids = catalogIds ? new Set([...catalogIds].map((id) => id.trim()).filter(Boolean)) : null
  if (ids && ids.has(team.id)) return team.id
  return ''
}
