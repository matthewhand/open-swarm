/**
 * Opt-in CLI agents catalog (REQ-157 / #565).
 *
 * Settings and the chat CLI dropdown list only configured CLIs. Startup
 * discovery prepopulates ``discovered`` / ``suggestions`` (PATH / known
 * locations, no auth). One-click Add persists like remotes; Remove drops
 * the name from configured (the binary may still reappear as a suggestion).
 */

import type { CliAgentsInfo } from './api'

/** Last native-select item — navigates to Settings → CLI agents. */
export const ADD_CLI_VALUE = '__add_cli__'

export const KNOWN_CLI_NAMES = [
  'agy',
  'claude',
  'codex',
  'gemini',
  'grok',
  'opencode',
  'pi',
] as const

export function configuredCliNames(info?: CliAgentsInfo | null): string[] {
  const listed = info?.configured
  if (Array.isArray(listed)) {
    return listed.map((name) => String(name).trim()).filter(Boolean)
  }
  return []
}

export function discoveredCliNames(info?: CliAgentsInfo | null): string[] {
  const listed = info?.discovered ?? info?.installed
  if (Array.isArray(listed)) {
    return listed.map((name) => String(name).trim()).filter(Boolean)
  }
  return []
}

export function suggestedCliEntries(
  info?: CliAgentsInfo | null,
): Array<{ name: string; cmd: string[] }> {
  const configured = new Set(configuredCliNames(info))
  const suggestions = info?.suggestions
  if (suggestions && typeof suggestions === 'object') {
    return Object.entries(suggestions)
      .filter(([name]) => name.trim() && !configured.has(name.trim()))
      .map(([name, entry]) => ({
        name,
        cmd: Array.isArray((entry as { cmd?: string[] } | undefined)?.cmd)
          ? ((entry as { cmd: string[] }).cmd)
          : [name],
      }))
      .sort((a, b) => a.name.localeCompare(b.name))
  }
  return discoveredCliNames(info)
    .filter((name) => !configured.has(name))
    .map((name) => {
      const cmd = (info?.catalog?.[name] as { cmd?: string[] } | undefined)?.cmd
      return { name, cmd: Array.isArray(cmd) && cmd.length ? cmd : [name] }
    })
}

export function cliSelectPlaceholder(configuredCount: number, selectedId = ''): string {
  if (configuredCount === 0) return 'No CLI agents'
  if (!selectedId) return 'Pick a CLI'
  return 'CLI'
}
