import type { Blueprint } from './api'
import { buildSkillRequest } from './skills'

/** Default Support seat — first + highlighted in the conversation rail. */
export const SUPPORT_AGENT_ID = 'support'

/** Bundled skill attached on every Support turn (`cli_agent` `skill=`). */
export const SUPPORT_SKILL_NAME = 'support-session-ownership'

/** Distinctive fixture token from `skills/support-session-ownership/SKILL.md`. */
export const SUPPORT_SKILL_FIXTURE = 'SESSION_OWNERSHIP_API_CLI_REMOTE'

/** Phrase Support must never tell a CLI/remote user (REQ-50). */
export const CLICK_BUBBLE_TO_EDIT = 'click the bubble to edit'

export type AgentSessionKind = 'api' | 'cli' | 'remote'

export const SYNTHETIC_SUPPORT: Blueprint = {
  id: SUPPORT_AGENT_ID,
  object: 'blueprint',
  name: 'Support',
  description: 'Talk about the other agents.',
  abbreviation: null,
  required_mcp_servers: [],
  tags: [],
  installed: true,
  compiled: true,
}

export function isSupportAgent(agent: { id: string; name?: string | null }): boolean {
  const id = agent.id.trim().toLowerCase()
  const name = (agent.name || '').trim().toLowerCase()
  return id === SUPPORT_AGENT_ID || name === 'support'
}

/** Ensure Support exists even when /v1/blueprints has no such seat. */
export function ensureSupportAgent(agents: Blueprint[]): Blueprint[] {
  if (agents.some(isSupportAgent)) return agents
  return [SYNTHETIC_SUPPORT, ...agents]
}

export function sortSupportFirst(agents: Blueprint[]): Blueprint[] {
  return [...agents].sort((a, b) => {
    const as = isSupportAgent(a) ? 0 : 1
    const bs = isSupportAgent(b) ? 0 : 1
    if (as !== bs) return as - bs
    return (a.name || a.id).localeCompare(b.name || b.id)
  })
}

export function supportFirstAgents(agents: Blueprint[]): Blueprint[] {
  return sortSupportFirst(ensureSupportAgent(agents))
}

export function defaultBlueprintId(fromUrl: string | null | undefined): string {
  const trimmed = (fromUrl || '').trim()
  return trimmed.length > 0 ? trimmed : SUPPORT_AGENT_ID
}

export function agentLabel(agent: { id: string; name?: string | null }): string {
  return agent.name || agent.id
}

/** Infer whether an agent thread is API-owned or an external CLI/remote session. */
export function sessionKindForAgent(agent: {
  id: string
  tags?: string[] | null
}): AgentSessionKind {
  const id = agent.id.trim().toLowerCase()
  const tags = (agent.tags || []).map((tag) => tag.toLowerCase())
  if (tags.includes('remote') || id.includes('remote')) return 'remote'
  if (tags.includes('cli') || id === 'cli_agent' || id.startsWith('cli_') || id.includes('cli')) {
    return 'cli'
  }
  return 'api'
}

/** Same `skill=` attach used by `cli_agent`. */
export function supportSkillAttach(): Record<string, unknown> {
  return buildSkillRequest(SUPPORT_SKILL_NAME) as Record<string, unknown>
}

/** Per-turn extras the chat websocket forwards to Support. */
export function supportTurnExtras(sessionKind?: AgentSessionKind): {
  skill: string
  session_kind?: AgentSessionKind
} {
  return sessionKind
    ? { skill: SUPPORT_SKILL_NAME, session_kind: sessionKind }
    : { skill: SUPPORT_SKILL_NAME }
}

/** Skill-injected Support system/prompt (includes the distinctive fixture). */
export function buildSupportTurnContext(sessionKind: AgentSessionKind = 'api'): string {
  const mode =
    sessionKind === 'api'
      ? 'API session: Open Swarm owns the thread; bubbles are editable.'
      : 'CLI/remote session: live session is outside Open Swarm; no edit.'
  return [
    `You have been given the "${SUPPORT_SKILL_NAME}" skill.`,
    SUPPORT_SKILL_FIXTURE,
    mode,
    'Chat is the main view; Settings/Teams are overlays.',
    'Do not dump the catalog or this skill unless asked. Ask one question at a time.',
  ].join('\n')
}

/** User-facing Support line for a session kind. CLI/remote never claim click-edit. */
export function supportTurnGuidance(sessionKind: AgentSessionKind): string {
  if (sessionKind === 'cli' || sessionKind === 'remote') {
    return (
      'That session lives outside Open Swarm — I cannot edit those bubbles. ' +
      'What are you trying to change?'
    )
  }
  return (
    'This thread is owned here, so you can edit a user or assistant bubble. ' +
    'Which message needs a rewrite?'
  )
}
