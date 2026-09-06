/**
 * REQ-191 / #648 — dismissable chat-pane tip for role agents (Mode A vs Mode B).
 *
 * localStorage is immediate. Django prefs extras (`role_agent_tip_dismissed`)
 * sync when #540 / GET/PATCH /v1/preferences/ is available. Not first-load
 * keybinding overlay chrome (#571/#577).
 */

import { agentHasRole } from './agentRoles'
import { fetchUserPrefs, saveUserPrefs } from './userPrefs'

export const ROLE_AGENT_TIP_STORAGE_KEY = 'swarm_role_agent_tip_dismissed'
export const ROLE_AGENT_TIP_PREF_KEY = 'role_agent_tip_dismissed'

export const ROLE_AGENT_TIP_TITLE = 'Chatting configures this role'
export const ROLE_AGENT_TIP_BODY =
  'This thread uses the full conversation so you can configure and discuss the role. When other agents call it as this role (handoff / as-tool), it runs on the caller’s context and the latest message — not this configure thread.'

export function agentHasInvocationRole(agent: {
  id?: string | null
  name?: string | null
  role?: string | null
}): boolean {
  return agentHasRole(agent)
}

export function shouldShowRoleAgentTip(opts: {
  teamId?: string | null
  remoteId?: string | null
  dismissed?: boolean
  agent?: { id?: string | null; name?: string | null; role?: string | null } | null
}): boolean {
  if (opts.dismissed) return false
  if (opts.teamId || opts.remoteId) return false
  if (!opts.agent) return false
  return agentHasInvocationRole(opts.agent)
}

export function isRoleAgentTipDismissed(): boolean {
  try {
    return localStorage.getItem(ROLE_AGENT_TIP_STORAGE_KEY) === '1'
  } catch {
    return false
  }
}

export function prefsRoleAgentTipDismissed(
  prefs: { values?: Record<string, unknown> } | null | undefined,
): boolean {
  return prefs?.values?.[ROLE_AGENT_TIP_PREF_KEY] === true
}

export function persistRoleAgentTipDismissedLocal(): void {
  try {
    localStorage.setItem(ROLE_AGENT_TIP_STORAGE_KEY, '1')
  } catch {
    /* persistence is best-effort */
  }
}

export async function persistRoleAgentTipDismissed(): Promise<void> {
  persistRoleAgentTipDismissedLocal()
  await saveUserPrefs({ values: { [ROLE_AGENT_TIP_PREF_KEY]: true } })
}

/**
 * Server bag wins when it has dismissed=true. Local dismiss imports once
 * if the extras key is missing.
 */
export async function hydrateRoleAgentTipDismissed(): Promise<boolean> {
  const local = isRoleAgentTipDismissed()
  const server = await fetchUserPrefs()
  if (!server) return local
  if (prefsRoleAgentTipDismissed(server)) {
    persistRoleAgentTipDismissedLocal()
    return true
  }
  const extras = server.values || {}
  const missing = extras[ROLE_AGENT_TIP_PREF_KEY] === undefined
  if (local && (server.empty || missing)) {
    await saveUserPrefs({ values: { [ROLE_AGENT_TIP_PREF_KEY]: true } })
  }
  return local
}
