/**
 * REQ-167 — CLI agent Folder (working directory).
 *
 * Persist lives on the agent edit record (and server settings). Session
 * start / attach send the value as `folder` so the process cwd is explicit.
 */

import { loadAgentEdit } from './agentEdits'

export const FOLDER_FORMAT_ERROR =
  'Please enter a valid directory path (e.g. /path/to/dir or ./dir)'

export function isValidFolderPath(path: string): boolean {
  if (!path.trim()) return true
  if (/[\0*?"<>|\r\n]/.test(path)) return false
  return true
}

export function loadAgentFolder(agentId: string): string {
  if (!agentId) return ''
  return (loadAgentEdit(agentId).folder || '').trim()
}

/** Query/body value for session list + select. Undefined when unset. */
export function folderRequestValue(agentId: string): string | undefined {
  const folder = loadAgentFolder(agentId)
  return folder || undefined
}

/** Chat WS params so cli_agent uses Folder as cwd. */
export function chatFolderParams(agentId: string): { folder: string } | undefined {
  const folder = folderRequestValue(agentId)
  return folder ? { folder } : undefined
}
