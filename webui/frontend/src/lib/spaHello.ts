/**
 * Backend-advertised SPA version from the chat websocket hello (REQ-78).
 * ChatPage publishes; the rail UpdateChrome subscribes.
 */

export const SPA_HELLO_EVENT = 'swarm:spa-hello'

let current: string | null = null

export function getExpectedSpaVersion(): string | null {
  return current
}

export function resetExpectedSpaVersion(): void {
  current = null
}

export function publishExpectedSpaVersion(version: string): void {
  const trimmed = version.trim()
  current = trimmed || null
  if (typeof window === 'undefined') return
  window.dispatchEvent(
    new CustomEvent<string | null>(SPA_HELLO_EVENT, { detail: current }),
  )
}
