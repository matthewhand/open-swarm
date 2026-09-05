/**
 * Current-chat identity for per-chat document prefs (not Neon).
 *
 * Matches ChatPage conversation scoping: team thread, remote session,
 * explicit ?session=, or the stable per-agent conversation id.
 */

import { agentIdFromBlueprint, conversationIdForAgent } from './agentChat'
import { defaultBlueprintId } from './supportAgent'
import { teamThreadId } from './teamRosters'

export const CURRENT_CHAT_SCOPE_EVENT = 'swarm:current-chat-scope'
export const CURRENT_CHAT_SCOPE_KEY = 'swarm_current_chat_scope'

export function chatScopeIdFromSearch(search: URLSearchParams): string {
  const team = (search.get('team') ?? '').trim()
  const remote = (search.get('remote') ?? '').trim()
  const session = (search.get('session') ?? '').trim()
  if (team) return teamThreadId(team)
  if (remote) return `remote-${remote}${session ? `-${session}` : ''}`
  if (session) return session
  return conversationIdForAgent(agentIdFromBlueprint(defaultBlueprintId(search.get('blueprint'))))
}

export function publishCurrentChatScope(id: string): void {
  const next = String(id || '').trim()
  if (!next) return
  try {
    localStorage.setItem(CURRENT_CHAT_SCOPE_KEY, next)
  } catch {
    /* private mode */
  }
  try {
    window.dispatchEvent(new CustomEvent(CURRENT_CHAT_SCOPE_EVENT, { detail: { id: next } }))
  } catch {
    /* jsdom / SSR */
  }
}

export function loadCurrentChatScope(): string {
  try {
    return (localStorage.getItem(CURRENT_CHAT_SCOPE_KEY) || '').trim()
  } catch {
    return ''
  }
}

/** Live chat id if ChatPage has published one; otherwise URL-derived scope. */
export function resolveChatScopeId(search: URLSearchParams): string {
  return loadCurrentChatScope() || chatScopeIdFromSearch(search)
}
